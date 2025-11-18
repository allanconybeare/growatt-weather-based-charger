#!/usr/bin/env python3
"""Test script to debug Solcast API issues."""

import os
import sys
from datetime import datetime

from modules.forecast_providers.manager import ForecastManager
from src.config import ConfigManager

sys.path.insert(0, os.getcwd())

print("Testing Solcast Provider Configuration")
print("=" * 70)

# Load config
try:
    config = ConfigManager("conf/growatt-charger.ini")
    print("✓ Config loaded successfully")
except Exception as e:
    print(f"✗ Failed to load config: {e}")
    sys.exit(1)

# Try to initialize Solcast provider via manager (like the real app does)
try:
    manager = ForecastManager(
        config, providers=["solcast", "forecast.solar"], primary_provider="solcast"
    )
    print("✓ Provider manager initialized successfully")
    provider = manager.providers.get("solcast")
    if not provider:
        print("✗ Solcast provider not available in manager")
        sys.exit(1)
except Exception as e:
    print(f"✗ Failed to initialize provider: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nProvider Details:")
print(f"  Resource IDs: {provider.resource_ids}")
print(f"  API Key present: {bool(provider.api_key)}")
print(f"  API Key length: {len(provider.api_key) if provider.api_key else 0}")
print(f"  Latitude: {provider.latitude}")
print(f"  Longitude: {provider.longitude}")

# Try to get forecast
print("\nTesting Forecast Retrieval:")
try:
    print("  Fetching forecast for today...")
    forecast_data = provider.get_forecast()
    print("  ✓ Got forecast data")
    print(f"  Number of forecast points: {len(forecast_data.get('forecasts', []))}")

    # Try to get daily total
    today_forecast = provider.get_forecast_for_date(datetime.now())
    print(f"  ✓ Today's forecast: {today_forecast:.0f}Wh ({today_forecast/1000:.2f}kWh)")

except Exception as e:
    print(f"  ✗ Failed to get forecast: {e}")
    import traceback

    traceback.print_exc()

print("\nDone!")
