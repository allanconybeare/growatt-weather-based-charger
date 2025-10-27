"""Base interface for solar forecast providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional


class ForecastProvider(ABC):
    """Abstract base class for forecast providers."""
    
    def __init__(self, config):
        """
        Initialize the forecast provider.
        
        Args:
            config: Configuration object with provider-specific settings
        """
        self.config = config
        self.name = self.__class__.__name__.replace('Provider', '')
    
    @abstractmethod
    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Total forecasted generation in watt-hours
            
        Raises:
            ForecastProviderError: If forecast fetch fails
        """
        pass
    
    @abstractmethod
    def get_hourly_forecast_for_date(self, target_date: datetime) -> Dict[datetime, float]:
        """
        Get hourly forecast generation for a specific date.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Dictionary mapping datetime to watt-hours for each hour
            
        Raises:
            ForecastProviderError: If forecast fetch fails
        """
        pass
    
    def get_provider_info(self) -> Dict[str, str]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary with provider metadata
        """
        return {
            'name': self.name,
            'version': getattr(self, 'version', 'unknown'),
            'requires_api_key': getattr(self, 'requires_api_key', False)
        }
    
    def test_connection(self) -> bool:
        """
        Test if the provider can successfully connect and fetch data.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get tomorrow's forecast as a test
            tomorrow = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            result = self.get_forecast_for_date(tomorrow)
            return result is not None and result >= 0
        except Exception:
            return False


class ForecastProviderError(Exception):
    """Base exception for forecast provider errors."""
    
    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)


class RateLimitError(ForecastProviderError):
    """Raised when API rate limit is exceeded."""
    pass


class AuthenticationError(ForecastProviderError):
    """Raised when API authentication fails."""
    pass


class NetworkError(ForecastProviderError):
    """Raised when network request fails."""
    pass
