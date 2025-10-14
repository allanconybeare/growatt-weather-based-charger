"""Weather forecast API client using Forecast.Solar."""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests


class ForecastSolarAPI:
    """Client for Forecast.Solar API."""
    
    BASE_URL = "https://api.forecast.solar"
    
    def __init__(self, lat: float, lon: float, declination: float, 
                 azimuth: float, kwp: float, damping: float = 0.1):
        """
        Initialize the Forecast.Solar API client.
        
        Args:
            lat: Latitude of installation
            lon: Longitude of installation
            declination: Panel angle (0=horizontal, 90=vertical)
            azimuth: Panel direction (0=south, 90=west, -90=east, 180=north)
            kwp: System size in kW peak
            damping: Damping factor for morning/evening (0-1, default 0.1)
        """
        self.lat = lat
        self.lon = lon
        self.declination = declination
        self.azimuth = azimuth
        self.kwp = kwp
        self.damping = damping
    
    def get_forecast(self) -> Dict[str, Any]:
        """
        Get solar generation forecast.
        
        Returns:
            Dictionary containing forecast data with timestamps and watt-hours
            
        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        # Build URL: /estimate/:lat/:lon/:dec/:az/:kwp
        url = (f"{self.BASE_URL}/estimate/"
               f"{self.lat}/{self.lon}/"
               f"{self.declination}/{self.azimuth}/{self.kwp}")
        
        params = {}
        if self.damping:
            params['damping'] = self.damping
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Total forecasted generation in watt-hours for that date
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
            Dictionary mapping datetime to watt-hours for each hour
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


def get_forecast_data_from_config(config) -> ForecastSolarAPI:
    """
    Create a ForecastSolarAPI instance from configuration.
    
    Args:
        config: Configuration object with forecast settings
        
    Returns:
        Configured ForecastSolarAPI instance
    """
    # Parse location - can be either "lat,lon" or an address
    location = config.forecast.location
    
    if ',' in location:
        # Assume it's lat,lon format
        lat, lon = map(float, location.split(','))
    else:
        # For address-based location, you'd need geocoding
        # For now, raise an error to indicate lat,lon is required
        raise ValueError(
            "Location must be in 'latitude,longitude' format. "
            f"Got: {location}"
        )
    
    return ForecastSolarAPI(
        lat=lat,
        lon=lon,
        declination=config.forecast.declination,
        azimuth=config.forecast.azimuth,
        kwp=config.forecast.kw_power,
        damping=config.forecast.damping
    )