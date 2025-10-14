"""Main application module for the Growatt Weather Based Charger."""

import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
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
from modules.forecast_api import get_forecast_data_from_config
from modules.forecast import ForecastCalculator
from modules.data_logger import DataLogger


class GrowattCharger:
    """Main application class for the Growatt Weather Based Charger."""
    
    def __init__(self, config_path: str):
        """
        Initialize the Growatt Charger application.
        
        Args:
            config_path: Path to configuration file
        """
        # Set up logging first
        project_root = os.path.dirname(os.path.dirname(config_path))
        
        # In a standard installation, use the project's logs directory
        log_dir = os.path.join(project_root, 'logs')
        
        # Override for Docker environment
        if os.path.exists('/.dockerenv'):
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
            
            # Initialize forecast API and calculator
            self.forecast_api = get_forecast_data_from_config(self.config)
            self.forecast_calculator = ForecastCalculator(
                self.forecast_api, 
                self.config
            )
            
            # Initialize data logger
            project_root = os.path.dirname(os.path.dirname(config_path))
            output_dir = os.path.join(project_root, 'output')
            self.data_logger = DataLogger(output_dir)
            
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
            
            # Log yesterday's actual generation (if this is a new day)
            self._log_previous_day_actual()
            
            # Get current charge status
            current_charge = await self._get_current_charge()
            
            # Calculate target charge using forecast
            charge_plan = await self._calculate_target_charge(current_charge)
            
            # Log the prediction for tomorrow
            self._log_prediction(current_charge, charge_plan)
            
            # Log the charging plan
            self.logger.info(
                f"Charge plan calculated - "
                f"Forecast: {charge_plan['forecast_wh']:.0f}Wh, "
                f"Solar coverage: {charge_plan['solar_coverage_pct']:.1f}%, "
                f"Target SOC: {charge_plan['target_soc']}%, "
                f"Charge rate: {charge_plan['charge_rate_pct']}%"
            )
            
            # Update charge settings if needed
            if self._should_update_settings(current_charge, charge_plan['target_soc']):
                await self._update_charge_settings(charge_plan)
            else:
                self.logger.info(
                    f"No update needed - current SOC ({current_charge:.1f}%) "
                    f"is close to target ({charge_plan['target_soc']}%)"
                )
            
            # Generate performance summary
            self.data_logger.generate_performance_summary()
            self.data_logger.print_recent_summary(days=7)
                
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

    async def _calculate_target_charge(self, current_soc: float) -> Dict[str, Any]:
        """
        Calculate target charge level based on configuration and forecasts.
        
        Args:
            current_soc: Current battery charge percentage
            
        Returns:
            Dictionary containing charge plan details
        """
        try:
            # Get tomorrow's forecast and calculate optimal charge plan
            self.logger.info("Fetching tomorrow's solar forecast...")
            charge_plan = self.forecast_calculator.calculate_optimal_charge_plan(
                current_soc=current_soc
            )
            
            return charge_plan
            
        except Exception as e:
            self.logger.error(f"Failed to calculate target charge: {e}")
            self.logger.warning("Falling back to maximum charge configuration")
            
            # Fallback to simple configuration-based approach
            growatt_config = self.config.growatt
            tariff_config = self.config.tariff
            
            # Parse times for off-peak duration
            start = datetime.strptime(tariff_config.off_peak_start_time, '%H:%M')
            end = datetime.strptime(tariff_config.off_peak_end_time, '%H:%M')
            off_peak_hours = (end - start).seconds / 3600
            
            return {
                'target_soc': growatt_config.maximum_charge_pct,
                'charge_rate_pct': 100,
                'forecast_wh': 0,
                'solar_coverage_pct': 0,
                'off_peak_hours': off_peak_hours
            }

    def _should_update_settings(self, current_charge: float, target_charge: float) -> bool:
        """
        Determine if charge settings should be updated.
        
        Args:
            current_charge: Current battery charge percentage
            target_charge: Target charge percentage
            
        Returns:
            True if settings should be updated
        """
        # Update if target is higher than current (need to charge)
        # or if there's a significant difference (more than 5%)
        should_update = (target_charge > current_charge) or \
                       (abs(current_charge - target_charge) > 5)
        
        if should_update:
            self.logger.info(
                f"Settings update needed - current: {current_charge}%, "
                f"target: {target_charge}%"
            )
        else:
            self.logger.info("No settings update needed")
            
        return should_update

    async def _update_charge_settings(self, charge_plan: Dict[str, Any]) -> None:
        """
        Update charge settings on the device.
        
        Args:
            charge_plan: Dictionary containing target_soc and charge_rate_pct
        """
        try:
            growatt_config = self.config.growatt
            tariff_config = self.config.tariff
            
            # Parse time strings
            start_hour, start_minute = map(int, tariff_config.off_peak_start_time.split(':'))
            end_hour, end_minute = map(int, tariff_config.off_peak_end_time.split(':'))
            
            # Get charge rate from plan with efficiency compensation
            # Based on collected data, actual charge is ~50-60% of expected
            # Apply 2x multiplier to compensate
            max_rate_pct = (growatt_config.maximum_charge_rate_w / 3000.0) * 100
            charge_rate_pct = min(100, int(charge_plan['charge_rate_pct'] * 2.0))
            charge_rate_pct = min(charge_rate_pct, max_rate_pct)
            
            self.logger.info(
                f"Charge rate calculated: {charge_plan['charge_rate_pct']}%, "
                f"adjusted to {charge_rate_pct}% (2x efficiency compensation)"
            )
            
            # Update charge settings
            self.api.update_charge_settings(
                device_sn=self.device_sn,
                charge_rate=int(charge_rate_pct),
                target_soc=int(charge_plan['target_soc']),
                schedule_start=(start_hour, start_minute),
                schedule_end=(end_hour, end_minute)
            )
            
            self.logger.info(
                f"Successfully updated charge settings - "
                f"Rate: {charge_rate_pct:.0f}%, SOC: {charge_plan['target_soc']}%, "
                f"Schedule: {start_hour:02d}:{start_minute:02d} to {end_hour:02d}:{end_minute:02d}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update charge settings: {e}")
            raise

    def _log_previous_day_actual(self) -> None:
        """Log yesterday's actual generation data."""
        try:
            # Get plant info which contains today's generation and charge data
            plant_info = self.api.get_plant_info(self.plant_id)
            
            # todayEnergy is in kWh as a string
            today_energy_kwh = float(plant_info.get('todayEnergy', 0))
            today_energy_wh = today_energy_kwh * 1000
            
            # Get charge energy from storage list
            storage_list = plant_info.get('storageList', [])
            charge_energy_kwh = 0
            if storage_list:
                charge_energy_str = storage_list[0].get('eChargeToday', '0')
                charge_energy_kwh = float(charge_energy_str)
            charge_energy_wh = charge_energy_kwh * 1000
            
            # We run at 22:00, so "today" in the API is the day we're logging actuals for
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Get current SOC as "evening SOC"
            status = self.api.get_system_status(self.device_sn, self.plant_id)
            evening_soc = float(status.get('SOC', 0))
            
            # Try to get morning SOC from yesterday's prediction
            # The morning SOC should be close to current evening SOC
            # since charging happens between 02:00-05:00
            morning_soc = None
            expected_soc = None
            actual_soc_increase = None
            
            try:
                import csv
                if os.path.isfile(self.data_logger.predictions_file):
                    with open(self.data_logger.predictions_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row['Prediction Date'] == today:
                                morning_soc = float(row['Current SOC (%)'])  # SOC when prediction was made (before charging)
                                expected_soc = float(row['Target SOC (%)'])  # Expected SOC after charging
                                break
                
                # Now we need to estimate SOC after charging (this morning)
                # We can calculate this from charge energy
                if charge_energy_wh > 0 and morning_soc is not None:
                    battery_capacity = self.config.growatt.battery_capacity_wh
                    soc_from_charge = (charge_energy_wh / battery_capacity) * 100
                    estimated_morning_after_charge = morning_soc + soc_from_charge
                    actual_soc_increase = soc_from_charge  # This is the actual increase from charging
                    
                    self.logger.info(
                        f"Charge analysis - Started: {morning_soc:.1f}%, "
                        f"Charged {charge_energy_wh:.0f}Wh ({soc_from_charge:.1f}%), "
                        f"Should be at: {estimated_morning_after_charge:.1f}%, "
                        f"Target was: {expected_soc:.1f}%"
                    )
                    
            except Exception as e:
                self.logger.debug(f"Could not calculate charge increase: {e}")
            
            if today_energy_wh > 0:  # Only log if we have actual data
                log_time = datetime.now().strftime("%H:%M")
                self.data_logger.log_actual(
                    actual_date=today,  # Log for TODAY, not yesterday
                    actual_generation_wh=today_energy_wh,
                    soc_at_sunset=evening_soc,
                    soc_at_morning=morning_soc,
                    charge_energy_wh=charge_energy_wh,
                    actual_soc_increase=actual_soc_increase,
                    notes=f"Logged at {log_time}"
                )
                
                log_msg = (f"Logged yesterday's actuals - "
                          f"Generated: {today_energy_wh:.0f}Wh, "
                          f"Charged: {charge_energy_wh:.0f}Wh, "
                          f"SOC: {evening_soc:.1f}%")
                if actual_soc_increase:
                    log_msg += f" (increased {actual_soc_increase:.1f}%)"
                
                self.logger.info(log_msg)
            
        except Exception as e:
            self.logger.warning(f"Could not log previous day actual: {e}")
            # Don't raise - this is optional logging

    def _log_prediction(self, current_soc: float, charge_plan: Dict[str, Any]) -> None:
        """
        Log the prediction for tomorrow.
        
        Args:
            current_soc: Current battery SOC
            charge_plan: Calculated charge plan
        """
        try:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            tariff_config = self.config.tariff
            growatt_config = self.config.growatt
            
            self.data_logger.log_prediction(
                prediction_date=tomorrow,
                forecast_wh=charge_plan['forecast_wh'],
                solar_coverage_pct=charge_plan['solar_coverage_pct'],
                current_soc=current_soc,
                target_soc=charge_plan['target_soc'],
                charge_rate_pct=charge_plan['charge_rate_pct'],
                off_peak_start=tariff_config.off_peak_start_time,
                off_peak_end=tariff_config.off_peak_end_time,
                battery_capacity_wh=growatt_config.battery_capacity_wh,
                average_load_w=growatt_config.average_load_w
            )
            
            self.logger.info(f"Logged prediction for {tomorrow}")
            
        except Exception as e:
            self.logger.warning(f"Could not log prediction: {e}")
            # Don't raise - this is optional logging


def main():
    """Main entry point for the application."""
    # Get config path from environment or use default
    config_path = os.getenv(
        'GROWATT_CONFIG',
        '/opt/growatt-charger/conf/growatt-charger.ini'
    )
    
    # Also check for local config file
    if not os.path.exists(config_path):
        local_config = 'conf/growatt-charger.ini'
        if os.path.exists(local_config):
            config_path = local_config
    
    try:
        app = GrowattCharger(config_path)
        asyncio.run(app.run())
        
    except Exception as e:
        print(f"Application failed: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())