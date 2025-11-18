#!/usr/bin/env python
"""Test multi-array forecast functionality."""

import sys

from src.config.configuration import ConfigManager


def test_array_parsing():
    """Test that array configuration parsing works correctly."""

    print("\n" + "=" * 60)
    print("Testing Multi-Array Forecast Configuration")
    print("=" * 60)

    # Test parsing arrays configuration string
    config = ConfigManager("conf/growatt-charger.ini")
    forecast_config = config.forecast

    print(f"\nLocation: {forecast_config.location}")
    print(f"Latitude: {config.forecast.latitude}")
    print(f"Longitude: {config.forecast.longitude}")
    print(f"Damping: {forecast_config.damping}")

    print("\n--- Single Array Config ---")
    print(f"Declination: {forecast_config.declination}°")
    print(f"Azimuth: {forecast_config.azimuth}°")
    print(f"Capacity: {forecast_config.kw_power} kWp")

    if forecast_config.arrays:
        print(f"\n--- Multi-Array Config ({len(forecast_config.arrays)} arrays) ---")
        for idx, array in enumerate(forecast_config.arrays, 1):
            print(f"Array {idx}:")
            print(f"  Declination: {array.declination}°")
            print(f"  Azimuth: {array.azimuth}°")
            print(f"  Capacity: {array.kwp} kWp")
    else:
        print("\n--- No multi-array config (using single array) ---")

    print("\n" + "=" * 60)
    print("✓ Configuration loaded successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_array_parsing()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
