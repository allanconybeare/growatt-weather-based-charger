#!/usr/bin/env python
"""Debug script to explore inverter_detail method."""

import json
import os
import sys

from src.api import GrowattAPI
from src.config import ConfigManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def explore_inverter_detail():
    """Explore what inverter_detail returns."""
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
        print("✓ Logged in\n")

        # Get device info
        print("Getting device info...")
        device_info = api.get_device_info()
        plant_id = device_info["plant_id"]
        device_sn = device_info["device_sn"]
        print(f"✓ Plant ID: {plant_id}")
        print(f"✓ Device SN: {device_sn}\n")

        # Try inverter_detail
        print("Calling inverter_detail()...")
        try:
            result = api._api.inverter_detail(device_sn)
            print("✓ inverter_detail() returned:")
            print(json.dumps(result, indent=2, default=str)[:2000])
            print("...\n")
        except Exception as e:
            print(f"✗ inverter_detail() failed: {e}\n")

        # Try inverter_detail_two
        print("Calling inverter_detail_two()...")
        try:
            result = api._api.inverter_detail_two(device_sn)
            print("✓ inverter_detail_two() returned:")
            print(json.dumps(result, indent=2, default=str)[:2000])
            print("...\n")
        except Exception as e:
            print(f"✗ inverter_detail_two() failed: {e}\n")

        # Try plant_settings
        print("Calling plant_settings()...")
        try:
            result = api._api.plant_settings(plant_id)
            print("✓ plant_settings() returned:")
            print(json.dumps(result, indent=2, default=str)[:2000])
            print("...\n")
        except Exception as e:
            print(f"✗ plant_settings() failed: {e}\n")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(explore_inverter_detail())
