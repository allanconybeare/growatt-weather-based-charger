#!/usr/bin/env python
"""Debug script to test update_charge_settings_with_slot directly."""

import os
import sys

from src.api import GrowattAPI
from src.config import ConfigManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_slot_update():
    """Test the slot update method with hardcoded parameters."""
    try:
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "conf", "growatt-charger.ini")
        config = ConfigManager(config_path)
        growatt_config = config.growatt

        # Initialize API
        api = GrowattAPI()

        # Login
        print("Logging in...")
        api.login(growatt_config.username, growatt_config.password)
        print("✓ Logged in")

        # Get device info
        print("Getting device info...")
        device_info = api.get_device_info()
        device_sn = device_info["device_sn"]
        print(f"✓ Device SN: {device_sn}")

        # Test updating slot 1 with different parameters
        print("\nTesting slot update...")
        print("Target: Slot 1, 14:00-16:00, rate 80%, SOC 51%")

        response = api.update_charge_settings_with_slot(
            device_sn=device_sn,
            charge_rate=80,
            target_soc=51,
            schedule_start=(14, 0),
            schedule_end=(16, 0),
            slot_number=1,
        )

        print(f"✓ Response: {response}")
        print("✓ SUCCESS - Slot update worked!")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_slot_update())
