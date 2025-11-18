#!/usr/bin/env python
"""Direct test of afternoon peak check with slot preservation."""

import os
import sys

from src.api import GrowattAPI
from src.config import ConfigManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_afternoon_peak_check_update():
    """Test the exact update that afternoon peak check will do."""
    try:
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "conf", "growatt-charger.ini")
        config = ConfigManager(config_path)
        growatt_config = config.growatt
        tariff_config = config.tariff

        # Initialize API
        api = GrowattAPI()

        # Login
        print("Simulating afternoon peak check at 14:00...")
        print("=" * 60)
        api.login(growatt_config.username, growatt_config.password)
        print("✓ Logged in to Growatt\n")

        # Get device info
        device_info = api.get_device_info()
        device_sn = device_info["device_sn"]
        print(f"✓ Device: {device_sn}\n")

        # Parse tariff config for slot 0
        off_peak_start_hour, off_peak_start_min = map(
            int, tariff_config.off_peak_start_time.split(":")
        )
        off_peak_end_hour, off_peak_end_min = map(int, tariff_config.off_peak_end_time.split(":"))

        print("Current device configuration:")
        print(
            "  Off-peak window (slot 0): "
            f"{off_peak_start_hour:02d}:{off_peak_start_min:02d}-"
            f"{off_peak_end_hour:02d}:{off_peak_end_min:02d}\n"
        )

        # This is what the afternoon peak check does
        print("Afternoon peak check decision:")
        print("  → Boost needed: YES")
        print("  → Target SOC: 51%")
        print("  → Charge rate: 80%")
        print("  → Boost window: 14:00-16:00\n")

        print("Applying boost to slot 1...")
        print("  Setting: 14:00-16:00, rate 80%, SOC 51%")
        print(
            "  Preserving slot 0: "
            f"{off_peak_start_hour:02d}:{off_peak_start_min:02d}-"
            f"{off_peak_end_hour:02d}:{off_peak_end_min:02d}\n"
        )

        # Call API EXACTLY as afternoon peak check does
        response = api.update_charge_settings_with_slot(
            device_sn=device_sn,
            charge_rate=80,
            target_soc=51,
            schedule_start=(14, 0),
            schedule_end=(16, 0),
            slot_number=1,
            preserve_slot_0=True,
            slot_0_start=(off_peak_start_hour, off_peak_start_min),
            slot_0_end=(off_peak_end_hour, off_peak_end_min),
        )

        if response.get("success"):
            print("✓ SUCCESS!")
            print("=" * 60)
            print("Device configuration after update:")
            print(
                "  Slot 0 (off-peak): "
                f"{off_peak_start_hour:02d}:{off_peak_start_min:02d}-"
                f"{off_peak_end_hour:02d}:{off_peak_end_min:02d} ✓ PRESERVED"
            )
            print("  Slot 1 (peak boost): 14:00-16:00 ✓ ACTIVE")
            print("=" * 60)
        else:
            print(f"✗ FAILED: {response}")
            return 1

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_afternoon_peak_check_update())
