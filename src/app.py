"""Main application module for the Growatt Weather Based Charger."""

import os
import sys
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .api import GrowattAPI
from .config import ConfigManager
from .utils import (
    setup_logging,
    get_logger,
    GrowattError,
    GrowattAPIError,
    GrowattAuthError,
    GrowattConfigError
)

class GrowattCharger:
    """Main application class for the Growatt Weather Based Charger."""
    
    def __init__(self, config_path: str):
        """
        Initialize the Growatt Charger application.
        
        Args:
            config_path: Path to configuration file
        """
        # Set up logging first
        # Determine if we're running in Docker by checking for a specific environment marker
        project_root = os.path.dirname(os.path.dirname(config_path))
        
        # In a standard installation, use the project's logs directory
        log_dir = os.path.join(project_root, 'logs')
        
        # Override for Docker environment
        if os.path.exists('/.dockerenv'):  # This file exists only inside Docker containers
            log_dir = '/opt/growatt-charger/logs'
            
        self.logger = setup_logging(
            log_dir=log_dir,
            log_file='growatt-charger.log',
            additional_fields={'app': 'growatt-charger'}
        )
        
        try:
            # Load configuration
            self.config = ConfigManager(config_path)
            
            # Initialize API client
            self.api = GrowattAPI()
            
            # Initialize state
            self.plant_id: Optional[str] = None
            self.device_sn: Optional[str] = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            raise

    async def run(self) -> None:
        """Run the main application logic."""
        try:
            # Login to Growatt API
            await self._login()
            
            # Get device information if not provided in config
            await self._get_device_info()
            
            # Get current charge status
            current_charge = await self._get_current_charge()
            
            # Calculate target charge
            target_charge = await self._calculate_target_charge()
            
            # Update charge settings if needed
            if self._should_update_settings(current_charge, target_charge):
                await self._update_charge_settings(target_charge)
                
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise

    async def _login(self) -> None:
        """Login to Growatt API."""
        try:
            growatt_config = self.config.growatt
            response = self.api.login(growatt_config.username, growatt_config.password)
            self.logger.info("Successfully logged in to Growatt API")
            
        except GrowattAuthError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected error during login: {e}")
            raise

    async def _get_device_info(self) -> None:
        """Get device information if not provided in config."""
        try:
            growatt_config = self.config.growatt
            
            # Use config values if provided
            if growatt_config.plant_id and growatt_config.device_sn:
                self.plant_id = growatt_config.plant_id
                self.device_sn = growatt_config.device_sn
                self.logger.info(
                    f"Using configured plant_id: {self.plant_id}, "
                    f"device_sn: {self.device_sn}"
                )
                return
            
            # Otherwise fetch from API
            device_info = self.api.get_device_info()
            self.plant_id = device_info['plant_id']
            self.device_sn = device_info['device_sn']
            
            self.logger.info(
                f"Retrieved device info - plant_id: {self.plant_id}, "
                f"device_sn: {self.device_sn}"
            )
            
        except GrowattAPIError as e:
            self.logger.error(f"Failed to get device info: {e}")
            raise
            
        except Exception as e:
            self.logger.error(f"Unexpected error getting device info: {e}")
            raise

    async def _get_current_charge(self) -> float:
        """
        Get current battery charge level.
        
        Returns:
            Current charge percentage
        """
        try:
            status = self.api.get_system_status(self.device_sn, self.plant_id)
            current_charge = float(status['SOC'])
            
            self.logger.info(f"Current battery charge: {current_charge}%")
            return current_charge
            
        except Exception as e:
            self.logger.error(f"Failed to get current charge: {e}")
            raise

    async def _calculate_target_charge(self) -> float:
        """
        Calculate target charge level based on configuration and forecasts.
        
        Returns:
            Target charge percentage
        """
        growatt_config = self.config.growatt
        
        # For now, use simple configuration-based target
        # TODO: Implement more sophisticated calculation using solar forecasts
        target_charge = growatt_config.maximum_charge_pct
        
        self.logger.info(f"Calculated target charge: {target_charge}%")
        return float(target_charge)

    def _should_update_settings(self, current_charge: float, target_charge: float) -> bool:
        """
        Determine if charge settings should be updated.
        
        Args:
            current_charge: Current battery charge percentage
            target_charge: Target charge percentage
            
        Returns:
            True if settings should be updated
        """
        # Add your logic here for when to update settings
        # For now, always update if there's a difference
        should_update = abs(current_charge - target_charge) > 1
        
        if should_update:
            self.logger.info(
                f"Settings update needed - current: {current_charge}%, "
                f"target: {target_charge}%"
            )
        else:
            self.logger.info("No settings update needed")
            
        return should_update

    async def _update_charge_settings(self, target_charge: float) -> None:
        """
        Update charge settings on the device.
        
        Args:
            target_charge: Target charge percentage
        """
        try:
            growatt_config = self.config.growatt
            tariff_config = self.config.tariff
            
            # Parse time strings
            start_hour, start_minute = map(int, tariff_config.off_peak_start_time.split(':'))
            end_hour, end_minute = map(int, tariff_config.off_peak_end_time.split(':'))
            
            # Convert maximum charge rate from watts to percentage (assuming 3000W is 100%)
            charge_rate_pct = min(100, (growatt_config.maximum_charge_rate_w / 3000.0) * 100)
            
            # Update charge settings
            self.api.update_charge_settings(
                device_sn=self.device_sn,
                charge_rate=int(charge_rate_pct),
                target_soc=int(target_charge),
                schedule_start=(start_hour, start_minute),
                schedule_end=(end_hour, end_minute)
            )
            
            self.logger.info("Successfully updated charge settings")
            
        except Exception as e:
            self.logger.error(f"Failed to update charge settings: {e}")
            raise

def main():
    """Main entry point for the application."""
    # Get config path from environment or use default
    config_path = os.getenv(
        'GROWATT_CONFIG',
        '/opt/growatt-charger/conf/growatt-charger.ini'
    )
    
    try:
        app = GrowattCharger(config_path)
        asyncio.run(app.run())
        
    except Exception as e:
        print(f"Application failed: {e}")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())