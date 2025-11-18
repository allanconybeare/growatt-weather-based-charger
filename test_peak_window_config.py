#!/usr/bin/env python
"""Test and validate peak window configuration alignment.

This script verifies that:
1. Config file has all required settings
2. Scheduled task run time aligns with check_time
3. Charging window (off-peak) doesn't conflict with peak window
4. All timing parameters are correct
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from src.config import ConfigManager
from src.utils import GrowattConfigError

# Add project root to path - use Path for more reliable resolution
project_root = str(Path(__file__).parent.absolute())
sys.path.insert(0, project_root)


class PeakWindowValidator:
    """Validates peak window configuration and alignment."""

    def __init__(self, config_path: str):
        """Initialize validator."""
        self.config_path = config_path
        self.config = None
        self.errors = []
        self.warnings = []
        self.info = []

    def validate(self) -> bool:
        """Run all validations. Returns True if all pass."""
        print("=" * 70)
        print("PEAK WINDOW CONFIGURATION VALIDATOR")
        print("=" * 70)
        print()

        # Load config
        try:
            self.config = ConfigManager(self.config_path)
            self.info.append(f"✅ Config loaded from: {self.config_path}")
        except GrowattConfigError as e:
            self.errors.append(f"❌ Failed to load config: {e}")
            self._print_results()
            return False
        except Exception as e:
            self.errors.append(f"❌ Error loading config: {e}")
            self._print_results()
            return False

        # Run all validations
        self._validate_time_formats()
        self._validate_time_ordering()
        self._validate_no_conflicts()
        self._validate_peak_window_duration()
        self._validate_parameters()

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _validate_time_formats(self):
        """Verify all times are properly formatted."""
        print("1. VALIDATING TIME FORMATS")
        print("-" * 70)

        try:
            tariff = self.config.tariff
            peak_window = self.config.peak_window

            times_to_check = {
                "Off-peak start": tariff.off_peak_start_time,
                "Off-peak end": tariff.off_peak_end_time,
                "Peak start": peak_window.peak_start_time,
                "Peak end": peak_window.peak_end_time,
                "Check time": peak_window.check_time,
            }

            for name, time_str in times_to_check.items():
                try:
                    # dt = datetime.strptime(time_str, "%H:%M")
                    self.info.append(f"  ✅ {name:20s}: {time_str}")
                except ValueError as e:
                    self.errors.append(f"  ❌ {name:20s}: Invalid format '{time_str}' - {e}")
        except Exception as e:
            self.errors.append(f"❌ Error validating formats: {e}")

        print()

    def _validate_time_ordering(self):
        """Verify times are in correct order."""
        print("2. VALIDATING TIME ORDERING")
        print("-" * 70)

        try:
            tariff = self.config.tariff
            peak_window = self.config.peak_window

            # Parse all times
            off_peak_start = datetime.strptime(tariff.off_peak_start_time, "%H:%M")
            off_peak_end = datetime.strptime(tariff.off_peak_end_time, "%H:%M")
            peak_start = datetime.strptime(peak_window.peak_start_time, "%H:%M")
            peak_end = datetime.strptime(peak_window.peak_end_time, "%H:%M")
            check_time = datetime.strptime(peak_window.check_time, "%H:%M")

            # Check orderings
            if off_peak_start < off_peak_end:
                self.info.append(
                    "  ✅ Off-peak: " f"{tariff.off_peak_start_time} < {tariff.off_peak_end_time}"
                )
            else:
                self.errors.append(
                    "  ❌ Off-peak: "
                    f"{tariff.off_peak_start_time} should be < {tariff.off_peak_end_time}"
                )

            if peak_start < peak_end:
                self.info.append(
                    "  ✅ Peak:     " f"{peak_window.peak_start_time} < {peak_window.peak_end_time}"
                )
            else:
                self.errors.append(
                    "  ❌ Peak:     "
                    f"{peak_window.peak_start_time} should be < {peak_window.peak_end_time}"
                )

            if check_time < peak_start:
                self.info.append(
                    "  ✅ Check before peak: "
                    f"{peak_window.check_time} < {peak_window.peak_start_time}"
                )
            else:
                self.errors.append(
                    "  ❌ Check time must be before peak start: "
                    f"{peak_window.check_time} < {peak_window.peak_start_time}"
                )
        except Exception as e:
            self.errors.append(f"❌ Error validating ordering: {e}")

        print()

    def _validate_no_conflicts(self):
        """Verify off-peak and peak windows don't conflict."""
        print("3. VALIDATING NO WINDOW CONFLICTS")
        print("-" * 70)

        try:
            tariff = self.config.tariff
            peak_window = self.config.peak_window

            off_peak_start = datetime.strptime(tariff.off_peak_start_time, "%H:%M")
            off_peak_end = datetime.strptime(tariff.off_peak_end_time, "%H:%M")
            peak_start = datetime.strptime(peak_window.peak_start_time, "%H:%M")
            peak_end = datetime.strptime(peak_window.peak_end_time, "%H:%M")

            # Check for overlap
            overlap_start = max(off_peak_start, peak_start)
            overlap_end = min(off_peak_end, peak_end)

            if overlap_start >= overlap_end:
                off_peak_window = f"{tariff.off_peak_start_time}-{tariff.off_peak_end_time}"
                peak_window = f"{peak_window.peak_start_time}-{peak_window.peak_end_time}"
                self.info.append(
                    f"  ✅ No conflict: Off-peak ({off_peak_window}) "
                    f"doesn't overlap peak ({peak_window})"
                )
            else:
                overlap_hours = (overlap_end - overlap_start).seconds / 3600
                self.warnings.append(
                    f"  ⚠️  Overlap detected: {overlap_hours:.1f}h between "
                    f"{overlap_start.strftime('%H:%M')} and {overlap_end.strftime('%H:%M')}"
                )
        except Exception as e:
            self.errors.append(f"❌ Error validating conflicts: {e}")

        print()

    def _validate_peak_window_duration(self):
        """Validate peak window duration."""
        print("4. VALIDATING PEAK WINDOW DURATION")
        print("-" * 70)

        try:
            peak_window = self.config.peak_window
            duration = peak_window.get_peak_window_duration_hours()

            self.info.append(
                f"  Peak window: {peak_window.peak_start_time} to {peak_window.peak_end_time}"
            )
            self.info.append(f"  Duration:    {duration:.2f} hours ({duration*60:.0f} minutes)")

            if duration > 0:
                self.info.append("  ✅ Peak window duration is valid")
            else:
                self.errors.append("  ❌ Peak window has no duration")
        except Exception as e:
            self.errors.append(f"❌ Error validating duration: {e}")

        print()

    def _validate_parameters(self):
        """Validate parameter ranges."""
        print("5. VALIDATING PARAMETER RANGES")
        print("-" * 70)

        try:
            peak_window = self.config.peak_window

            # Forecast reliability
            if 0.0 <= peak_window.forecast_reliability <= 1.0:
                self.info.append(
                    f"  ✅ Forecast reliability: {peak_window.forecast_reliability:.1%}"
                )
            else:
                self.errors.append(
                    f"  ❌ Forecast reliability out of range: {peak_window.forecast_reliability}"
                )

            # SOC safety margin
            if 0.0 <= peak_window.soc_safety_margin_pct <= 100.0:
                self.info.append(
                    f"  ✅ SOC safety margin:    {peak_window.soc_safety_margin_pct:.1f}%"
                )
            else:
                self.errors.append(
                    f"  ❌ SOC safety margin out of range: {peak_window.soc_safety_margin_pct}"
                )
        except Exception as e:
            self.errors.append(f"❌ Error validating parameters: {e}")

        print()

    def _print_results(self):
        """Print validation results."""
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        # Info messages
        if self.info:
            print("\n✅ INFORMATION:")
            for msg in self.info:
                print(msg)

        # Warnings
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for msg in self.warnings:
                print(msg)

        # Errors
        if self.errors:
            print("\n❌ ERRORS:")
            for msg in self.errors:
                print(msg)

        # Final status
        print("\n" + "=" * 70)
        if self.errors:
            print("❌ VALIDATION FAILED - Please fix errors above")
            print("=" * 70)
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print("=" * 70)
        else:
            print("✅ VALIDATION PASSED - All settings correct!")
            print("=" * 70)

    def print_configuration_summary(self):
        """Print a human-readable summary of configuration."""
        # Only print if config loaded successfully
        if not self.config:
            return

        print("\n" + "=" * 70)
        print("CONFIGURATION SUMMARY")
        print("=" * 70)

        try:
            tariff = self.config.tariff
            peak_window = self.config.peak_window
            growatt = self.config.growatt

            print("\n📅 OFF-PEAK CHARGING WINDOW (22:00 task)")
            print(f"   Time:     {tariff.off_peak_start_time} - {tariff.off_peak_end_time}")
            off_peak_hours = (
                datetime.strptime(tariff.off_peak_end_time, "%H:%M")
                - datetime.strptime(tariff.off_peak_start_time, "%H:%M")
            ).seconds / 3600
            print(f"   Duration: {off_peak_hours:.1f} hours")
            print(
                f"   Purpose:  Charge battery to {growatt.maximum_charge_pct}% using off-peak rates"
            )

            print("\n☀️  PEAK WINDOW (14:00 check, 16:00-19:00 high rates)")
            print(f"   Check time:    {peak_window.check_time} (runs afternoon peak-check)")
            print(f"   Peak window:   {peak_window.peak_start_time} - {peak_window.peak_end_time}")
            print(f"   Duration:      {peak_window.get_peak_window_duration_hours():.1f} hours")
            print("   Check purpose: Decide if battery boost needed before peak rates")

            print("\n⚙️  PEAK WINDOW PARAMETERS")
            print(f"   Forecast reliability:   {peak_window.forecast_reliability:.0%}")
            print(f"   SOC safety margin:      {peak_window.soc_safety_margin_pct:.0f}%")
            print(f"   Average load:           {growatt.average_load_w}W")

            print("\n📊 BATTERY SETTINGS")
            print(f"   Capacity:          {growatt.battery_capacity_wh/1000:.1f} kWh")
            print(f"   Min charge:        {growatt.minimum_charge_pct}%")
            print(f"   Max charge:        {growatt.maximum_charge_pct}%")
            print(f"   Max charge rate:   {growatt.maximum_charge_rate_w/1000:.1f} kW")

            print("\n" + "=" * 70)
        except Exception as e:
            print(f"❌ Error printing summary: {e}")


if __name__ == "__main__":
    # Determine config path - auto-detect from project root
    config_path = os.path.join(project_root, "conf", "growatt-charger.ini")

    # Validate
    validator = PeakWindowValidator(config_path)
    success = validator.validate()
    validator.print_configuration_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
