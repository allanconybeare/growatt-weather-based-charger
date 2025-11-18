"""14:00 afternoon peak-window boost decision logic."""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from modules.api_usage_tracker import get_global_tracker
from modules.data_logger import DataLogger
from modules.forecast_providers import ForecastManager
from modules.peak_window_boost import (
    calculate_peak_window_boost_target,
    should_boost_battery_for_peak_window,
)

from .api import GrowattAPI
from .config import ConfigManager
from .utils import GrowattAPIError, setup_logging


class AfternoonPeakChecker:
    """Checks at 14:00 if battery boost is needed for 16:00-19:00 peak window."""

    def __init__(self, config_path: str):
        """
        Initialize the afternoon peak checker.

        Args:
            config_path: Path to configuration file
        """
        # Set up logging first
        project_root = os.path.dirname(os.path.dirname(config_path))
        log_dir = os.path.join(project_root, "logs")

        # Override for Docker
        if os.path.exists("/.dockerenv"):
            log_dir = "/opt/growatt-charger/logs"

        self.logger = setup_logging(
            log_dir=log_dir,
            log_file="afternoon-peak-check.log",
            additional_fields={"app": "afternoon-peak-check"},
        )

        try:
            # Load configuration
            self.config = ConfigManager(config_path)

            # Initialize API
            self.api = GrowattAPI()

            # Initialize forecast manager
            providers_config = self.config.forecast_providers
            self.logger.info(
                f"Initializing forecast providers: {', '.join(providers_config.providers)}"
            )
            self.forecast_manager = ForecastManager(
                self.config,
                providers=providers_config.providers,
                primary_provider=providers_config.primary_provider,
            )

            # Initialize data logger
            output_dir = os.path.join(project_root, "output")
            self.data_logger = DataLogger(output_dir)

            # Initialize state
            self.plant_id: Optional[str] = None
            self.device_sn: Optional[str] = None

        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            raise

    async def run(self) -> None:
        """Run the afternoon peak-window check at 14:00."""
        try:
            # Login to Growatt API
            await self._login()

            # Get device info if needed
            await self._get_device_info()

            # Get current SOC at 14:00
            current_soc = await self._get_current_soc()

            # Get remaining forecast with fallback chain
            remaining_forecast_wh, forecast_source = await self._get_remaining_forecast()

            # Decide if boost is needed
            should_boost, reason, details = should_boost_battery_for_peak_window(
                remaining_forecast_wh=remaining_forecast_wh,
                current_soc=current_soc,
                battery_capacity_wh=self.config.growatt.battery_capacity_wh,
                average_load_w=self.config.growatt.average_load_w,
            )

            self.logger.info(
                f"14:00 Peak-Window Check: "
                f"Forecast {remaining_forecast_wh/1000:.1f}kWh ({forecast_source}), "
                f"SOC {current_soc:.0f}%, "
                f"Decision: {'BOOST' if should_boost else 'NO BOOST'}"
            )
            self.logger.info(reason)

            # If boost needed, update settings
            if should_boost:
                target_soc, target_reason = calculate_peak_window_boost_target(
                    remaining_forecast_wh=remaining_forecast_wh,
                    current_soc=current_soc,
                    battery_capacity_wh=self.config.growatt.battery_capacity_wh,
                    average_load_w=self.config.growatt.average_load_w,
                    max_soc=self.config.growatt.maximum_charge_pct,
                )

                self.logger.info(f"Boost target: {target_soc}% ({target_reason})")
                await self._apply_boost_settings(target_soc)
            else:
                self.logger.info("No boost needed - battery sufficient for peak window")

            # Log decision for analysis
            self._log_peak_decision(
                current_soc=current_soc,
                remaining_forecast_wh=remaining_forecast_wh,
                forecast_source=forecast_source,
                should_boost=should_boost,
                reason=reason,
                details=details,
            )

        except Exception as e:
            self.logger.error(f"Afternoon peak check failed: {e}")
            raise

    async def _login(self) -> None:
        """Login to Growatt API."""
        try:
            growatt_config = self.config.growatt
            self.api.login(growatt_config.username, growatt_config.password)
            self.logger.info("Successfully logged in to Growatt API")
        except GrowattAPIError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise

    async def _get_device_info(self) -> None:
        """Get device information if not provided in config."""
        try:
            growatt_config = self.config.growatt

            if growatt_config.plant_id and growatt_config.device_sn:
                self.plant_id = growatt_config.plant_id
                self.device_sn = growatt_config.device_sn
                self.logger.info(
                    f"Using configured plant_id: {self.plant_id}, " f"device_sn: {self.device_sn}"
                )
                return

            device_info = self.api.get_device_info()
            self.plant_id = device_info["plant_id"]
            self.device_sn = device_info["device_sn"]

            self.logger.info(
                f"Retrieved device info - plant_id: {self.plant_id}, "
                f"device_sn: {self.device_sn}"
            )

        except GrowattAPIError as e:
            self.logger.error(f"Failed to get device info: {e}")
            raise

    async def _get_current_soc(self) -> float:
        """Get current battery SOC at 14:00."""
        try:
            status = self.api.get_system_status(self.device_sn, self.plant_id)
            current_soc = float(status["SOC"])
            self.logger.debug(f"Current battery SOC: {current_soc}%")
            return current_soc
        except Exception as e:
            self.logger.error(f"Failed to get current SOC: {e}")
            raise

    async def _get_remaining_forecast(self) -> Tuple[float, str]:
        """
        Get remaining solar forecast from 14:00 to sunset.

        Fallback chain:
        1. Try primary forecast provider (typically Solcast with 10 calls/day limit)
        2. Fallback to secondary provider (Forecast.Solar)
        3. Final fallback to yesterday's prediction from predictions.csv

        Returns:
            Tuple of (forecast_wh, source_description)
        """
        try:
            # Try primary provider (e.g., Solcast)
            today = datetime.now()
            try:
                forecast_wh, provider_used = self.forecast_manager.get_forecast_for_date(today)
                self.logger.info(
                    f"Remaining forecast: {forecast_wh/1000:.1f}kWh from {provider_used}"
                )
                return forecast_wh, provider_used

            except Exception as e:
                self.logger.warning(
                    f"Primary forecast provider failed: {e}. " f"Trying fallback to predictions.csv"
                )

        except Exception as e:
            self.logger.warning(f"Forecast provider initialization failed: {e}")

        # Fallback: Use yesterday's prediction as proxy for today
        try:
            forecast_wh = self._get_forecast_from_predictions_csv(today)
            if forecast_wh > 0:
                self.logger.info(
                    f"Using fallback forecast: {forecast_wh/1000:.1f}kWh from "
                    f"yesterday's predictions.csv"
                )
                return forecast_wh, "predictions.csv (fallback)"
        except Exception as e:
            self.logger.warning(f"Failed to read predictions.csv: {e}")

        # Conservative estimate (safe default if all else fails)
        self.logger.warning("All forecast sources failed. Using conservative estimate (3kWh)")
        return 3000, "conservative_estimate"

    def _get_forecast_from_predictions_csv(self, target_date: datetime) -> float:
        """
        Get forecast from predictions.csv as fallback.

        Reads the most recent entry and uses its forecast if date matches.

        Args:
            target_date: Today's date to match

        Returns:
            Forecast in Wh, or 0 if not found/invalid
        """
        try:
            import csv
            import os

            predictions_file = os.path.join(self.data_logger.output_dir, "predictions.csv")

            if not os.path.isfile(predictions_file):
                self.logger.debug("predictions.csv not found")
                return 0

            # Read last line (most recent prediction)
            with open(predictions_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                self.logger.debug("predictions.csv is empty")
                return 0

            last_row = rows[-1]

            # Check if prediction date matches today
            prediction_date_str = last_row.get("Prediction Date", "").strip()
            today_str = target_date.strftime("%Y-%m-%d")

            if prediction_date_str != today_str:
                self.logger.debug(
                    f"Latest prediction is for {prediction_date_str}, " f"not today ({today_str})"
                )
                return 0

            # Extract forecast in Wh
            forecast_wh_str = last_row.get("Forecast (Wh)", "0").strip()
            forecast_wh = float(forecast_wh_str)

            return forecast_wh

        except Exception as e:
            self.logger.debug(f"Error reading predictions.csv: {e}")
            return 0

    async def _apply_boost_settings(self, target_soc: int) -> None:
        """
        Apply boost charge settings to next available slot.

        Smart slot management:
        - Slot 0: Off-peak charging schedule (protected - set by 22:00 task)
        - Slot 1-2: Available for boost (tries slot 1 first)

        This preserves any manual schedules (e.g., free power events) configured
        by user in slot 0, and only uses slot 1 or 2 for the afternoon boost.
        """
        try:
            # Set to quick boost: high charge rate for short duration
            # Assume 2 hours until peak (14:00 to 16:00)
            boost_charge_rate = 80  # Aggressive but sustainable

            # Use slot 1 for afternoon boost (preserve slot 0 for off-peak)
            slot_num = 1

            self.logger.info(
                f"Applying boost to slot {slot_num}: "
                f"Target SOC {target_soc}%, "
                f"Rate {boost_charge_rate}%, "
                f"Duration 14:00-16:00"
            )

            # Get off-peak schedule from config to preserve slot 0
            tariff_config = self.config.tariff
            off_peak_start_hour, off_peak_start_min = map(
                int, tariff_config.off_peak_start_time.split(":")
            )
            off_peak_end_hour, off_peak_end_min = map(
                int, tariff_config.off_peak_end_time.split(":")
            )

            # Call API with slot-specific parameters, preserving slot 0
            self.api.update_charge_settings_with_slot(
                device_sn=self.device_sn,
                charge_rate=boost_charge_rate,
                target_soc=int(target_soc),
                schedule_start=(14, 0),  # Peak boost start
                schedule_end=(16, 0),  # Peak boost end
                slot_number=slot_num,  # Use slot 1
                preserve_slot_0=True,  # Preserve off-peak schedule
                slot_0_start=(off_peak_start_hour, off_peak_start_min),
                slot_0_end=(off_peak_end_hour, off_peak_end_min),
            )

            self.logger.info(
                f"Successfully applied boost settings to slot {slot_num} - "
                f"Target SOC {target_soc}%, "
                f"Rate {boost_charge_rate}%, "
                "Duration 14:00-16:00 (with slot 0 "
                f"{off_peak_start_hour:02d}:{off_peak_start_min:02d}-"
                f"{off_peak_end_hour:02d}:{off_peak_end_min:02d} preserved)"
            )

        except Exception as e:
            self.logger.error(f"Failed to apply boost settings: {e}")
            raise

    def _log_peak_decision(
        self,
        current_soc: float,
        remaining_forecast_wh: float,
        forecast_source: str,
        should_boost: bool,
        reason: str,
        details: Dict[str, Any],
    ) -> None:
        """Log the peak-window decision to file for analysis."""
        try:
            log_file = os.path.join(self.data_logger.output_dir, "peak_decisions.csv")
            file_exists = os.path.isfile(log_file)

            import csv

            with open(log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if not file_exists:
                    writer.writerow(
                        [
                            "Date",
                            "Time",
                            "Current SOC (%)",
                            "Remaining Forecast (Wh)",
                            "Remaining Forecast (kWh)",
                            "Forecast Source",
                            "Peak Consumption (Wh)",
                            "Peak Generation (Wh)",
                            "Peak Shortfall (%)",
                            "Required SOC (%)",
                            "Decision",
                            "Reason",
                        ]
                    )

                now = datetime.now()
                writer.writerow(
                    [
                        now.strftime("%Y-%m-%d"),
                        now.strftime("%H:%M:%S"),
                        round(current_soc, 1),
                        int(remaining_forecast_wh),
                        round(remaining_forecast_wh / 1000, 2),
                        forecast_source,
                        int(details["peak_consumption_wh"]),
                        int(details["estimated_peak_generation_wh"]),
                        round(details["peak_shortfall_pct"], 1),
                        round(details["required_soc_pct"], 1),
                        "BOOST" if should_boost else "NO BOOST",
                        reason,
                    ]
                )

            self.logger.debug(f"Peak decision logged to {log_file}")

        except Exception as e:
            self.logger.error(f"Failed to log peak decision: {e}")


async def main():
    """Entry point for afternoon peak-check script."""

    config_path = sys.argv[1] if len(sys.argv) > 1 else "conf/growatt-charger.ini"

    # Initialize API usage tracker
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(config_path)))
    output_dir = os.path.join(project_root, "output")
    tracker = get_global_tracker(persistence_dir=output_dir)

    try:
        checker = AfternoonPeakChecker(config_path)
        await checker.run()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Log API usage summary before exit
        tracker.log_summary()
        tracker.save_daily_summary()


if __name__ == "__main__":
    asyncio.run(main())
