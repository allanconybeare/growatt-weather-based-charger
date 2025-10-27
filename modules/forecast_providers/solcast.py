"""Solcast solar forecast provider."""

from datetime import datetime, timedelta
from typing import Dict
import requests

from .base import ForecastProvider, ForecastProviderError, RateLimitError, AuthenticationError, NetworkError


class SolcastProvider(ForecastProvider):
    """Solcast API forecast provider."""
    
    BASE_URL = "https://api.solcast.com.au"
    version = "1.0.0"
    requires_api_key = True
    
    def __init__(self, config):
        """
        Initialize Solcast provider.
        
        Args:
            config: Configuration object with:
                - api_key: Solcast API key
                - resource_id: Single resource ID or comma-separated list
                - latitude: Site latitude
                - longitude: Site longitude
                - azimuth: Panel azimuth (Forecast.Solar format: 0=South)
        """
        super().__init__(config)
        
        # Get Solcast-specific config
        self.api_key = getattr(config, 'api_key', None)
        resource_id_str = getattr(config, 'resource_id', None)
        
        # Parse resource IDs (can be comma-separated for multiple arrays)
        if resource_id_str:
            self.resource_ids = [rid.strip() for rid in resource_id_str.split(',')]
        else:
            self.resource_ids = []
        
        # Fallback to main forecast config for location
        self.latitude = getattr(config, 'latitude', None)
        self.longitude = getattr(config, 'longitude', None)
        
        # Convert azimuth from Forecast.Solar format to Solcast format
        # Forecast.Solar: 0=South, 90=West, -90=East, -180=North
        # Solcast: 0=North, 90=West, -90=East, 180=South
        forecast_solar_azimuth = getattr(config, 'azimuth', 0)
        self.azimuth = self._convert_azimuth(forecast_solar_azimuth)
        
        self.tilt = getattr(config, 'declination', 30)  # Solcast uses 'tilt' instead of 'declination'
        self.capacity = getattr(config, 'kwp', 5.8)
        
        if not self.api_key:
            raise ForecastProviderError("Solcast API key not configured", "Solcast")
        
        # Resource IDs are optional - if not provided, we'll use lat/lon
        # (but lat/lon requires paid tier)
        if not self.resource_ids and (not self.latitude or not self.longitude):
            raise ForecastProviderError(
                "Either resource_id or latitude/longitude must be configured", 
                "Solcast"
            )
    
    @property
    def resource_id(self):
        """Backwards compatibility property for single resource_id access."""
        return self.resource_ids[0] if self.resource_ids else None
    
    def _convert_azimuth(self, forecast_solar_azimuth: float) -> float:
        """
        Convert azimuth from Forecast.Solar format to Solcast format.
        
        Forecast.Solar: -180=North, -90=East, 0=South, 90=West
        Solcast: 0=North, -90=East, 180/-180=South, 90=West
        
        Args:
            forecast_solar_azimuth: Azimuth in Forecast.Solar format
            
        Returns:
            Azimuth in Solcast format
        """
        # Simple conversion: add 180 degrees, then normalize to [-180, 180]
        solcast_azimuth = forecast_solar_azimuth + 180
        
        # Normalize to [-180, 180]
        if solcast_azimuth > 180:
            solcast_azimuth -= 360
        
        return solcast_azimuth
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make an authenticated request to Solcast API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response
            
        Raises:
            Various ForecastProviderError subclasses
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Check for rate limiting
            if response.status_code == 429:
                raise RateLimitError("API rate limit exceeded (10 calls/day)", "Solcast")
            
            # Check for authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key", "Solcast")
            
            # Check for other errors
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise NetworkError("Request timeout", "Solcast")
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                raise NetworkError(f"HTTP {response.status_code}: {str(e)}", "Solcast")
            raise NetworkError(f"Request failed: {str(e)}", "Solcast")
    
    def get_forecast(self) -> Dict:
        """
        Get full forecast from Solcast.
        If multiple resource IDs configured, fetches and combines them.
        
        Returns:
            Raw forecast data from Solcast (combined if multiple resources)
        """
        if self.resource_ids:
            # If multiple resources, fetch each and combine
            if len(self.resource_ids) == 1:
                return self._get_resource_forecast(self.resource_ids[0])
            else:
                return self._get_combined_forecast()
        else:
            # Use world radiation endpoint (requires paid tier)
            endpoint = "world_pv_power/forecasts"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'capacity': self.capacity,
                'tilt': self.tilt,
                'azimuth': self.azimuth,
                'format': 'json'
            }
            return self._make_request(endpoint, params)
    
    def _get_resource_forecast(self, resource_id: str) -> Dict:
        """Get forecast for a single resource."""
        endpoint = f"rooftop_sites/{resource_id}/forecasts"
        params = {'format': 'json'}
        return self._make_request(endpoint, params)
    
    def _get_combined_forecast(self) -> Dict:
        """
        Fetch and combine forecasts from multiple resources (arrays).
        
        Returns:
            Combined forecast with summed pv_estimate values
        """
        all_forecasts = []
        
        # Fetch each resource
        for resource_id in self.resource_ids:
            forecast = self._get_resource_forecast(resource_id)
            all_forecasts.append(forecast.get('forecasts', []))
        
        if not all_forecasts:
            return {'forecasts': []}
        
        # Combine forecasts by period_end timestamp
        combined_by_time = {}
        
        for resource_forecasts in all_forecasts:
            for entry in resource_forecasts:
                period_end = entry['period_end']
                pv_estimate = entry.get('pv_estimate', 0)
                
                if period_end in combined_by_time:
                    # Sum the estimates
                    combined_by_time[period_end]['pv_estimate'] += pv_estimate
                else:
                    # Create new entry
                    combined_by_time[period_end] = {
                        'period_end': period_end,
                        'pv_estimate': pv_estimate,
                        'period': entry.get('period', 'PT30M')
                    }
        
        # Convert back to list
        combined_forecasts = sorted(
            combined_by_time.values(),
            key=lambda x: x['period_end']
        )
        
        return {'forecasts': combined_forecasts}
    
    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Total forecasted generation in watt-hours
        """
        forecast_data = self.get_forecast()
        
        # Solcast returns 'forecasts' array with period_end times and pv_estimate
        forecasts = forecast_data.get('forecasts', [])
        
        # Format target date for comparison
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        total_wh = 0
        for entry in forecasts:
            # Parse period_end: "2025-10-14T00:30:00.0000000Z"
            period_end = datetime.fromisoformat(entry['period_end'].replace('Z', '+00:00'))
            
            # Check if this period is on our target date
            if period_end.strftime('%Y-%m-%d') == target_date_str:
                # pv_estimate is in kW for the period (typically 30 min periods)
                pv_kw = entry.get('pv_estimate', 0)
                
                # Convert to Wh (assuming 30-minute periods)
                # kW * 0.5 hours = kWh, * 1000 = Wh
                wh = pv_kw * 0.5 * 1000
                total_wh += wh
        
        return total_wh
    
    def get_hourly_forecast_for_date(self, target_date: datetime) -> Dict[datetime, float]:
        """
        Get hourly forecast generation for a specific date.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Dictionary mapping datetime to watts for each hour
        """
        forecast_data = self.get_forecast()
        forecasts = forecast_data.get('forecasts', [])
        
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # Aggregate 30-min periods into hourly
        hourly_data = {}
        
        for entry in forecasts:
            period_end = datetime.fromisoformat(entry['period_end'].replace('Z', '+00:00'))
            
            if period_end.strftime('%Y-%m-%d') == target_date_str:
                # Round to hour
                hour_key = period_end.replace(minute=0, second=0, microsecond=0)
                
                # pv_estimate is in kW
                pv_kw = entry.get('pv_estimate', 0)
                pv_w = pv_kw * 1000  # Convert to watts
                
                # Average the 30-min periods within the hour
                if hour_key in hourly_data:
                    hourly_data[hour_key] = (hourly_data[hour_key] + pv_w) / 2
                else:
                    hourly_data[hour_key] = pv_w
        
        return hourly_data