"""Forecast provider manager for handling multiple providers."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from .base import ForecastProvider, ForecastProviderError
from .solcast import SolcastProvider
from .forecast_solar import ForecastSolarProvider


logger = logging.getLogger(__name__)


class ForecastManager:
    """Manages multiple forecast providers with fallback and comparison capabilities."""
    
    # Registry of available providers
    PROVIDERS = {
        'solcast': SolcastProvider,
        'forecast.solar': ForecastSolarProvider,
    }
    
    def __init__(self, config, providers: List[str] = None, primary_provider: str = None):
        """
        Initialize forecast manager.
        
        Args:
            config: Configuration object
            providers: List of provider names to use (e.g. ['solcast', 'forecast.solar'])
            primary_provider: Name of primary provider (used for charging decisions)
        """
        self.config = config
        self.providers = {}
        self.primary_provider_name = primary_provider
        
        # If no providers specified, use only the primary
        if not providers and primary_provider:
            providers = [primary_provider]
        elif not providers:
            providers = ['forecast.solar']  # Default fallback
        
        # Initialize requested providers
        for provider_name in providers:
            try:
                self.providers[provider_name] = self._create_provider(provider_name)
                logger.info(f"Initialized forecast provider: {provider_name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {e}")
        
        if not self.providers:
            raise ForecastProviderError("No forecast providers could be initialized")
        
        # Set primary provider (or first available)
        if primary_provider and primary_provider in self.providers:
            self.primary_provider_name = primary_provider
        else:
            self.primary_provider_name = list(self.providers.keys())[0]
            logger.warning(
                f"Primary provider not available, using {self.primary_provider_name}"
            )
    
    def _create_provider(self, provider_name: str) -> ForecastProvider:
        """
        Create a provider instance.
        
        Args:
            provider_name: Name of provider to create
            
        Returns:
            Initialized provider instance
            
        Raises:
            ForecastProviderError: If provider unknown or initialization fails
        """
        if provider_name not in self.PROVIDERS:
            raise ForecastProviderError(f"Unknown provider: {provider_name}")
        
        provider_class = self.PROVIDERS[provider_name]
        
        # Get provider-specific config
        provider_config = self._get_provider_config(provider_name)
        
        return provider_class(provider_config)
    
    def _get_provider_config(self, provider_name: str):
        """
        Get configuration for a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Configuration object with provider-specific settings
        """
        # Create a simple config object that combines main forecast config
        # with provider-specific config
        class ProviderConfig:
            pass
        
        config_obj = ProviderConfig()
        
        # Add main forecast config
        if hasattr(self.config, 'forecast'):
            forecast_cfg = self.config.forecast
            
            # Parse location if it's lat,lon format
            location = getattr(forecast_cfg, 'location', '')
            if ',' in location:
                lat, lon = map(float, location.split(','))
                config_obj.latitude = lat
                config_obj.longitude = lon
            
            config_obj.declination = getattr(forecast_cfg, 'declination', 30)
            config_obj.azimuth = getattr(forecast_cfg, 'azimuth', 0)
            config_obj.kwp = getattr(forecast_cfg, 'kw_power', 5.8)
            config_obj.damping = getattr(forecast_cfg, 'damping', 0.1)
        
        # Add provider-specific config
        if provider_name == 'solcast' and hasattr(self.config, 'solcast'):
            solcast_cfg = self.config.solcast
            config_obj.api_key = getattr(solcast_cfg, 'api_key', None)
            config_obj.resource_id = getattr(solcast_cfg, 'resource_id', None)
        
        return config_obj
    
    def get_forecast_for_date(
        self, 
        target_date: datetime,
        use_primary: bool = True
    ) -> Tuple[float, str]:
        """
        Get forecast for a date, with automatic fallback.
        
        Args:
            target_date: Date to get forecast for
            use_primary: If True, use primary provider first
            
        Returns:
            Tuple of (forecast_wh, provider_name)
        """
        # Try primary provider first
        if use_primary and self.primary_provider_name:
            try:
                provider = self.providers[self.primary_provider_name]
                forecast = provider.get_forecast_for_date(target_date)
                return forecast, self.primary_provider_name
            except Exception as e:
                logger.warning(
                    f"Primary provider {self.primary_provider_name} failed: {e}"
                )
        
        # Try other providers as fallback
        for name, provider in self.providers.items():
            if name == self.primary_provider_name:
                continue  # Already tried
            
            try:
                forecast = provider.get_forecast_for_date(target_date)
                logger.info(f"Using fallback provider: {name}")
                return forecast, name
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
        
        raise ForecastProviderError("All forecast providers failed")
    
    def get_all_forecasts_for_date(
        self, 
        target_date: datetime
    ) -> Dict[str, float]:
        """
        Get forecasts from all providers for comparison.
        
        Args:
            target_date: Date to get forecasts for
            
        Returns:
            Dictionary mapping provider name to forecast (Wh)
        """
        forecasts = {}
        
        for name, provider in self.providers.items():
            try:
                forecast = provider.get_forecast_for_date(target_date)
                forecasts[name] = forecast
            except Exception as e:
                logger.error(f"Provider {name} failed: {e}")
                forecasts[name] = None
        
        return forecasts
    
    def get_hourly_forecast_for_date(
        self,
        target_date: datetime
    ) -> Tuple[Dict[datetime, float], str]:
        """
        Get hourly forecast, with automatic fallback.
        
        Args:
            target_date: Date to get forecast for
            
        Returns:
            Tuple of (hourly_data, provider_name)
        """
        # Try primary provider
        if self.primary_provider_name:
            try:
                provider = self.providers[self.primary_provider_name]
                hourly = provider.get_hourly_forecast_for_date(target_date)
                return hourly, self.primary_provider_name
            except Exception as e:
                logger.warning(
                    f"Primary provider {self.primary_provider_name} failed: {e}"
                )
        
        # Fallback
        for name, provider in self.providers.items():
            if name == self.primary_provider_name:
                continue
            
            try:
                hourly = provider.get_hourly_forecast_for_date(target_date)
                logger.info(f"Using fallback provider for hourly: {name}")
                return hourly, name
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
        
        raise ForecastProviderError("All forecast providers failed")
    
    def test_all_providers(self) -> Dict[str, bool]:
        """
        Test connection to all configured providers.
        
        Returns:
            Dictionary mapping provider name to success status
        """
        results = {}
        
        for name, provider in self.providers.items():
            try:
                results[name] = provider.test_connection()
                logger.info(f"Provider {name}: {'OK' if results[name] else 'FAILED'}")
            except Exception as e:
                results[name] = False
                logger.error(f"Provider {name} test failed: {e}")
        
        return results
