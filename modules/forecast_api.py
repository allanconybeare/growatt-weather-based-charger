"""Weather forecast API client."""

from datetime import datetime, timedelta
from typing import Dict, Any, List

import requests

def get_forecast_data(lat: float, lon: float, api_key: str) -> List[Dict[str, Any]]:
    """
    Get solar generation forecast data.
    
    Args:
        lat: Latitude
        lon: Longitude
        api_key: API key for weather service
        
    Returns:
        List of forecast entries
        
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    # Example implementation using a weather API
    url = f"https://api.forecast.solar/v1/{api_key}/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "dec": 30,  # Solar panel declination
        "az": 180,  # Solar panel azimuth (south-facing)
        "kwp": 5.0  # System size in kW
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()["forecast"]