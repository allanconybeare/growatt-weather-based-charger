"""Forecast.Solar forecast provider."""

from datetime import datetime
from typing import Dict
import requests

from .base import ForecastProvider, ForecastProviderError, NetworkError


class ForecastSolarProvider(ForecastProvider):
    """Forecast.Solar API forecast provider."""
    
    BASE_URL = "https://api.forecast.solar"
    version = "1.0.0"
    requires_api_key = False
    
    def __init__(self, config):
        """
        Initialize Forecast.Solar provider.
        
        Args:
            config: Configuration object with:
                - latitude: Site latitude
                - longitude: Site longitude
                - declination: Panel angle (0=horizontal, 90=vertical)
                - azimuth: Panel direction (0=south, 90=west, -90=east)
                - kwp: System size in kW peak
                - damping: Damping factor for morning/evening (0-1)
        """
        super().__init__(config)
        
        self.latitude = getattr(config, 'latitude', None)
        self.longitude = getattr(config, 'longitude', None)
        self.declination = getattr(config, 'declination', 30)
        self.azimuth = getattr(config, 'azimuth', 0)
        self.kwp = getattr(config, 'kwp', 5.8)
        self.damping = getattr(config, 'damping', 0.1)
        
        if not self.latitude or not self.longitude:
            raise ForecastProviderError(
                "Latitude and longitude must be configured",
                "Forecast.Solar"
            )
    
    def get_forecast(self) -> Dict:
        """
        Get solar generation forecast from Forecast.Solar.
        
        Returns:
            Dictionary containing forecast data
            
        Raises:
            NetworkError: If API call fails
        """
        # Build URL: /estimate/:lat/:lon/:dec/:az/:kwp
        url = (f"{self.BASE_URL}/estimate/"
               f"{self.latitude}/{self.longitude}/"
               f"{self.declination}/{self.azimuth}/{self.kwp}")
        
        params = {}
        if self.damping:
            params['damping'] = self.damping
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise NetworkError("Request timeout", "Forecast.Solar")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}", "Forecast.Solar")
    
    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Total forecasted generation in watt-hours
        """
        forecast_data = self.get_forecast()
        
        # The API returns 'result' with 'watt_hours_day' containing daily totals
        watt_hours_day = forecast_data.get('result', {}).get('watt_hours_day', {})
        
        # Format date as YYYY-MM-DD to match API response format
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Get the forecast for the target date
        forecast_wh = watt_hours_day.get(date_str, 0)
        
        return float(forecast_wh)
    
    def get_hourly_forecast_for_date(self, target_date: datetime) -> Dict[datetime, float]:
        """
        Get hourly forecast generation for a specific date.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Dictionary mapping datetime to watts for each hour
        """
        forecast_data = self.get_forecast()
        
        # The API returns 'result' with 'watts' containing hourly data
        watts = forecast_data.get('result', {}).get('watts', {})
        
        hourly_forecast = {}
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        for timestamp_str, watts_value in watts.items():
            # Parse timestamp (format: "2025-10-08 14:00:00")
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # Only include hours for the target date
            if timestamp.strftime('%Y-%m-%d') == target_date_str:
                hourly_forecast[timestamp] = float(watts_value)
        
        return hourly_forecast
