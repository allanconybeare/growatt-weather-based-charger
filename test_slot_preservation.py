#!/usr/bin/env python
"""Debug script to test slot preservation."""

import os
import sys

from src.api import GrowattAPI
from src.config import ConfigManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_slot_preservation():
    """Test that updating slot 1 doesn't reset slot 0."""
    try:
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "conf", "growatt-charger.ini")
        config = ConfigManager(config_path)
        growatt_config = config.growatt
        tariff_config = config.tariff

        # Initialize API
        api = GrowattAPI()

        # Login
        print("Logging in...")
        api.login(growatt_config.username, growatt_config.password)
        print("✓ Logged in\n")

        # Get device info
        print("Getting device info...")
        device_info = api.get_device_info()
        device_sn = device_info["device_sn"]
        print(f"✓ Device SN: {device_sn}\n")

        # Step 1: Set slot 0 (off-peak charging) using update_charge_settings
        print("=" * 60)
        print("STEP 1: Setting slot 0 (off-peak) via update_charge_settings")
        print("=" * 60)
        start_hour, start_minute = map(int, tariff_config.off_peak_start_time.split(":"))
        end_hour, end_minute = map(int, tariff_config.off_peak_end_time.split(":"))

        print(
            f"Setting slot 0: {start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"
        )
        print("  Rate: 100%, SOC: 90%")

        response1 = api.update_charge_settings(
            device_sn=device_sn,
            charge_rate=100,
            target_soc=90,
            schedule_start=(start_hour, start_minute),
            schedule_end=(end_hour, end_minute),
        )
        print(f"✓ Response: {response1}\n")

        # Step 2: Now set slot 1 (afternoon boost)
        print("=" * 60)
        print("STEP 2: Setting slot 1 (afternoon boost) via update_charge_settings_with_slot")
        print("=" * 60)
        print("Setting slot 1: 14:00-16:00")
        print("  Rate: 80%, SOC: 51%")

        response2 = api.update_charge_settings_with_slot(
            device_sn=device_sn,
            charge_rate=80,
            target_soc=51,
            schedule_start=(14, 0),
            schedule_end=(16, 0),
            slot_number=1,
        )
        print(f"✓ Response: {response2}\n")

        print("=" * 60)
        print("RESULT:")
        print("=" * 60)
        print("✓ Slot 0 (off-peak) should still be active: 02:00-04:59, rate 100%, SOC 90%")
        print("✓ Slot 1 (peak boost) should now be active: 14:00-16:00, rate 80%, SOC 51%")
        print("\nTo verify, check the device settings manually.")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_slot_preservation())
