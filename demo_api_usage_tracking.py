#!/usr/bin/env python3
"""
Demonstration of Solcast API usage tracking and quota monitoring.

This script shows how API usage is automatically tracked and reported.
"""

import logging
import sys
from pathlib import Path

from modules.api_usage_tracker import get_global_tracker, record_api_call

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# Setup logging to see tracker messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def demo_tracking():
    """Demonstrate API usage tracking functionality."""

    print("=" * 70)
    print("Solcast API Usage Tracking Demo")
    print("=" * 70)
    print()

    # Get the global tracker with persistence enabled
    tracker = get_global_tracker(persistence_dir=str(project_root / "output"))

    print("📊 Simulating API calls to Solcast...")
    print()

    # Simulate successful API calls with quota info
    print("✅ Call 1: Successful forecast API call")
    record_api_call(
        provider="solcast",
        endpoint="rooftop_sites/{resource_id}/forecasts",
        status_code=200,
        quota_remaining=8,
        quota_limit=10,
    )
    print()

    print("✅ Call 2: Another successful call")
    record_api_call(
        provider="solcast",
        endpoint="rooftop_sites/{resource_id}/forecasts",
        status_code=200,
        quota_remaining=7,
        quota_limit=10,
    )
    print()

    print("⚠️  Call 3: Call with low quota warning")
    record_api_call(
        provider="solcast",
        endpoint="rooftop_sites/{resource_id}/forecasts",
        status_code=200,
        quota_remaining=2,
        quota_limit=10,
    )
    print()

    print("❌ Call 4: Failed API call")
    record_api_call(
        provider="solcast",
        endpoint="world_pv_power/forecasts",
        status_code=401,
        quota_remaining=2,
        quota_limit=10,
        error="Invalid API key",
    )
    print()

    # Show stats
    print("=" * 70)
    print("📈 Usage Statistics:")
    print("=" * 70)
    print()

    stats = tracker.get_provider_stats("solcast")
    print(f"Total API calls:      {stats.get('total_calls', 0)}")
    print(f"Successful calls:     {stats.get('successful_calls', 0)}")
    print(f"Failed calls:         {stats.get('failed_calls', 0)}")
    print(f"Quota remaining:      {stats.get('quota_remaining', 'unknown')}")
    print(f"Quota limit:          {stats.get('quota_limit', 'unknown')}")
    print(f"Last quota check:     {stats.get('last_quota_check', 'never')}")
    print()

    # Log summary
    print("=" * 70)
    print("📋 Summary Report:")
    print("=" * 70)
    print()
    tracker.log_summary()
    print()

    # Check for alerts
    print("=" * 70)
    print("🚨 Quota Alerts:")
    print("=" * 70)
    print()
    alerts = tracker.check_quota_alerts()
    if alerts:
        for provider, alert in alerts.items():
            print(f"{provider}: {alert}")
    else:
        print("No quota alerts")
    print()

    # Save daily summary
    print("=" * 70)
    print("💾 Saving daily summary...")
    print("=" * 70)
    print()
    filepath = tracker.save_daily_summary()
    if filepath:
        print(f"✅ Summary saved to: {filepath}")
        print()
        # Show the contents
        with open(filepath) as f:
            import json

            data = json.load(f)
            print("File contents:")
            print(json.dumps(data, indent=2))
    else:
        print("❌ Failed to save summary")

    print()
    print("=" * 70)
    print("Demo complete!")
    print("=" * 70)
    print()
    print("💡 Key Features:")
    print("  • Automatic tracking of all API calls (when integrated)")
    print("  • Captures quota information from response headers")
    print("  • Alerts when quota is running low (1-5 calls remaining)")
    print("  • Thread-safe for concurrent API calls")
    print("  • Optional daily summary persistence to JSON")
    print()
    print("📌 How it's used:")
    print("  • Solcast provider automatically calls record_api_call()")
    print("  • Integrates with forecast.solar provider (similar)")
    print("  • Access stats: tracker.get_provider_stats('solcast')")
    print("  • Manual recording: record_api_call(...)")


if __name__ == "__main__":
    demo_tracking()
