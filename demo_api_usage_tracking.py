#!/usr/bin/env python3
"""
Demonstration of enhanced API usage tracking with rolling windows.

Shows:
- Per-provider file storage (no overwrites)
- Rolling window calculations
- Solcast 24-hour tracking
- Forecast.Solar hourly tracking
"""

import time
from datetime import datetime

# Import the enhanced tracker
from modules.api_usage_tracker import can_make_calls, get_global_tracker, record_api_call


def demo_enhanced_tracking():
    """Demonstrate the enhanced API tracking features."""

    print("=" * 80)
    print("ENHANCED API USAGE TRACKER DEMO")
    print("=" * 80)
    print()

    # Initialize tracker with persistence
    tracker = get_global_tracker(persistence_dir="./output")

    print("📊 Simulating API calls to multiple providers...")
    print()

    # === SOLCAST CALLS (24-hour rolling window, limit: 10) ===
    print("=" * 80)
    print("SOLCAST (24-hour rolling window, limit: 10 calls)")
    print("=" * 80)
    print()

    # Simulate a few successful calls
    for i in range(3):
        print(f"✅ Call {i+1}: Successful forecast fetch")
        record_api_call(
            provider="solcast",
            endpoint="rooftop_sites/abc123/forecasts",
            status_code=200,
            quota_remaining=600 - (i + 1),  # Solcast's misleading header
            quota_limit=600,
        )
        time.sleep(0.1)

    # Simulate a failed call (still counts toward quota!)
    print("❌ Call 4: Failed request (401 Unauthorized)")
    record_api_call(
        provider="solcast",
        endpoint="rooftop_sites/abc123/forecasts",
        status_code=401,
        error="Invalid API key",
    )

    print()

    # Check Solcast quota
    print("DEBUG: Solcast go get Quota Status")
    solcast_status = tracker.get_quota_status("solcast")
    print("Solcast Status:")
    print(
        f"  Calls in 24h window: {solcast_status['calls_in_window']}/"
        f"{solcast_status['quota_limit']}"
    )
    print(f"  Remaining: {solcast_status['quota_remaining']}")
    print(f"  Status: {solcast_status['status']}")
    if solcast_status["reset_time"]:
        reset = datetime.fromisoformat(solcast_status["reset_time"])
        print(f"  Next quota available: {reset.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check if we can make more calls
    can_proceed, reason = can_make_calls("solcast", num_calls=3)
    print(f"Can make 3 more Solcast calls? {can_proceed}")
    print(f"Reason: {reason}")
    print()

    # === FORECAST.SOLAR CALLS (1-hour rolling window, limit: 12) ===
    print("=" * 80)
    print("FORECAST.SOLAR (1-hour rolling window, limit: 12 calls)")
    print("=" * 80)
    print()

    # Simulate multiple array fetches (3 arrays = 3 calls)
    arrays = ["East", "South", "West"]
    for i, array in enumerate(arrays, 1):
        print(f"✅ Call {i}: Fetching forecast for {array} array")
        record_api_call(
            provider="forecast.solar",
            endpoint=f"estimate/{array}",
            status_code=200,
            quota_remaining=12 - i,
            quota_limit=12,
        )
        time.sleep(0.1)

    print()

    # Check Forecast.Solar quota
    fs_status = tracker.get_quota_status("forecast.solar")
    print("Forecast.Solar Status:")
    print(f"  Calls in 1h window: {fs_status['calls_in_window']}/{fs_status['quota_limit']}")
    print(f"  Remaining: {fs_status['quota_remaining']}")
    print(f"  Status: {fs_status['status']}")
    if fs_status["reset_time"]:
        reset = datetime.fromisoformat(fs_status["reset_time"])
        print(f"  Resets at: {reset.strftime('%H:%M:%S')}")
    print()

    # === SUMMARY ===
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print()
    tracker.log_summary()
    print()

    # === CHECK FOR ALERTS ===
    print("=" * 80)
    print("QUOTA ALERTS")
    print("=" * 80)
    print()
    alerts = tracker.check_quota_alerts()
    if alerts:
        for provider, alert in alerts.items():
            print(f"{provider}: {alert}")
    else:
        print("✅ No quota alerts - all providers OK")
    print()

    # === FILE STORAGE ===
    print("=" * 80)
    print("PERSISTENCE")
    print("=" * 80)
    print()
    print("✅ Usage data saved to separate files:")
    print("  - output/api_usage_solcast.json")
    print("  - output/api_usage_forecast.solar.json")
    print()
    print("Each provider has its own file, so no overwrites!")
    print()

    # === SIMULATE QUOTA EXHAUSTION ===
    print("=" * 80)
    print("QUOTA EXHAUSTION SCENARIO")
    print("=" * 80)
    print()

    # Simulate making 7 more Solcast calls to approach limit
    print("Simulating 6 more Solcast calls (to reach 10/10 limit)...")
    for i in range(6):
        record_api_call(
            provider="solcast",
            endpoint="rooftop_sites/abc123/forecasts",
            status_code=200,
        )

    # Now check quota
    solcast_status = tracker.get_quota_status("solcast")
    print("\nSolcast Status After 10 Calls:")
    print("  Calls in window: {solcast_status['calls_in_window']}/10")
    print(f"  Remaining: {solcast_status['quota_remaining']}")
    print(
        f"  Status: {solcast_status['status']} "
        f"{'⛔' if solcast_status['status'] == 'EXHAUSTED' else ''}"
    )
    print()

    # Try to make another call
    can_proceed, reason = can_make_calls("solcast", num_calls=1)
    print(f"Can make another Solcast call? {can_proceed}")
    print(f"Reason: {reason}")
    print()

    # === KEY FEATURES ===
    print("=" * 80)
    print("KEY FEATURES DEMONSTRATED")
    print("=" * 80)
    print()
    print("✅ Per-provider file storage (no overwrites)")
    print("✅ Rolling window calculations (24h for Solcast, 1h for Forecast.Solar)")
    print("✅ Accurate quota tracking (ignores Solcast's misleading headers)")
    print("✅ Failed calls counted (they use quota too!)")
    print("✅ Timestamp tracking for all calls")
    print("✅ Automatic cleanup of old calls outside window")
    print("✅ Thread-safe operations")
    print("✅ Pre-flight checks with can_make_calls()")
    print()


if __name__ == "__main__":
    demo_enhanced_tracking()
