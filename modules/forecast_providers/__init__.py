"""Forecast provider system for solar generation predictions."""

from .base import (
    ForecastProvider,
    ForecastProviderError,
    RateLimitError,
    AuthenticationError,
    NetworkError
)
from .solcast import SolcastProvider
from .forecast_solar import ForecastSolarProvider
from .manager import ForecastManager

__all__ = [
    'ForecastProvider',
    'ForecastProviderError',
    'RateLimitError',
    'AuthenticationError',
    'NetworkError',
    'SolcastProvider',
    'ForecastSolarProvider',
    'ForecastManager',
]
