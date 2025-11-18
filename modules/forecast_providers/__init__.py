"""Forecast provider system for solar generation predictions."""

from .base import (
    AuthenticationError,
    ForecastProvider,
    ForecastProviderError,
    NetworkError,
    RateLimitError,
)
from .forecast_solar import ForecastSolarProvider
from .manager import ForecastManager
from .solcast import SolcastProvider

__all__ = [
    "ForecastProvider",
    "ForecastProviderError",
    "RateLimitError",
    "AuthenticationError",
    "NetworkError",
    "SolcastProvider",
    "ForecastSolarProvider",
    "ForecastManager",
]
