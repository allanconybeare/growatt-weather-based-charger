#!/usr/bin/env python3
"""
Script to view and analyze per-provider API usage from JSON files.

Usage:
    python view_provider_usage.py                    # Show all providers
    python view_provider_usage.py solcast            # Show Solcast only
    python view_provider_usage.py forecast.solar     # Show Forecast.Solar only
    python view_provider_usage.py --calls            # Show detailed call history
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict


def load_provider_data(provider: str, output_dir: Path) -> Dict:
    """Load usage data for a specific provider."""
    filepath = output_dir / f"api_usage_{provider}.json"

    if not filepath.exists():
        return None

    with open(filepath, "r") as f:
        return json.load(f)


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp for display."""
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def display_provider_summary(provider: str, data: Dict) -> None:
    """Display a summary for a single provider."""
    print(f"\n{'=' * 80}")
    print(f"PROVIDER: {provider.upper()}")
    print(f"{'=' * 80}\n")

    # Basic info
    last_updated = data.get("last_updated")
    if last_updated:
        print(f"Last Updated: {format_timestamp(last_updated)}")

    # Quota model
    quota_model = data.get("quota_model", {})
    window = quota_model.get("window_hours", "unknown")
    limit = quota_model.get("limit", "unknown")
    reset_type = quota_model.get("reset_type", "unknown")

    print(f"Quota Model: {limit} calls per {window}h ({reset_type} window)")
    print()

    # Call history stats
    call_history = data.get("call_history", [])
    total_calls = len(call_history)

    if total_calls == 0:
        print("No API calls recorded.")
        return

    # Count success/failure
    successful = sum(1 for call in call_history if call.get("success", False))
    failed = total_calls - successful
    success_rate = (successful / total_calls * 100) if total_calls > 0 else 0

    print(f"Total Calls (all time): {total_calls}")
    print(f"  Successful: {successful} ({success_rate:.1f}%)")
    print(f"  Failed: {failed}")
    print()

    # Recent calls (last 10)
    print("Recent Calls (last 10):")
    print(f"{'Timestamp':<20} {'Endpoint':<30} {'Status':<10} {'Result':<10}")
    print("-" * 80)

    recent_calls = sorted(call_history, key=lambda c: c["timestamp"], reverse=True)[:10]

    for call in recent_calls:
        timestamp = format_timestamp(call["timestamp"])
        endpoint = call.get("endpoint", "unknown")[:28]
        status = call.get("status_code", "?")
        result = "SUCCESS" if call.get("success", False) else "FAILED"

        print(f"{timestamp:<20} {endpoint:<30} {status:<10} {result:<10}")

    print()


def display_detailed_calls(provider: str, data: Dict, limit: int = 50) -> None:
    """Display detailed call history for a provider."""
    print(f"\n{'=' * 80}")
    print(f"DETAILED CALL HISTORY: {provider.upper()}")
    print(f"{'=' * 80}\n")

    call_history = data.get("call_history", [])

    if not call_history:
        print("No calls recorded.")
        return

    # Show most recent calls first
    recent_calls = sorted(call_history, key=lambda c: c["timestamp"], reverse=True)[:limit]

    for i, call in enumerate(recent_calls, 1):
        timestamp = format_timestamp(call["timestamp"])
        endpoint = call.get("endpoint", "unknown")
        status = call.get("status_code", "?")
        success = call.get("success", False)
        error = call.get("error")

        print(f"Call #{i}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Status: HTTP {status} - {'SUCCESS' if success else 'FAILED'}")

        if error:
            print(f"  Error: {error}")

        # Show quota info if available
        if "quota_remaining" in call:
            print(f"  Quota: {call['quota_remaining']}/{call.get('quota_limit', '?')}")
        elif "reported_remaining" in call:
            print(
                f"  Reported: {call['reported_remaining']}/"
                f"{call.get('reported_limit', '?')} (may be inaccurate)"
            )

        print()


def calculate_window_stats(provider: str, data: Dict) -> Dict:
    """Calculate statistics for calls within the rolling window."""
    quota_model = data.get("quota_model", {})
    window_hours = quota_model.get("window_hours", 24)
    limit = quota_model.get("limit", 10)

    call_history = data.get("call_history", [])

    # Calculate window start time
    now = datetime.now()
    from datetime import timedelta

    window_start = now - timedelta(hours=window_hours)

    # Filter calls in window
    calls_in_window = [
        call for call in call_history if datetime.fromisoformat(call["timestamp"]) > window_start
    ]

    count = len(calls_in_window)
    remaining = max(0, limit - count)

    successful = sum(1 for call in calls_in_window if call.get("success", False))
    failed = count - successful

    # Determine status
    if remaining <= 0:
        status = "EXHAUSTED"
    elif remaining <= 2:
        status = "CRITICAL"
    elif remaining <= 5:
        status = "LOW"
    else:
        status = "OK"

    return {
        "calls_in_window": count,
        "quota_limit": limit,
        "quota_remaining": remaining,
        "successful": successful,
        "failed": failed,
        "status": status,
        "window_hours": window_hours,
    }


def display_window_analysis(provider: str, data: Dict) -> None:
    """Display rolling window analysis."""
    print(f"\n{'=' * 80}")
    print(f"ROLLING WINDOW ANALYSIS: {provider.upper()}")
    print(f"{'=' * 80}\n")

    stats = calculate_window_stats(provider, data)

    print(f"Window: {stats['window_hours']} hours")
    print(f"Calls in window: {stats['calls_in_window']}/{stats['quota_limit']}")
    print(f"Quota remaining: {stats['quota_remaining']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"Status: {stats['status']}", end="")

    if stats["status"] == "EXHAUSTED":
        print(" ⛔")
    elif stats["status"] == "CRITICAL":
        print(" 🔴")
    elif stats["status"] == "LOW":
        print(" 🟡")
    else:
        print(" ✅")

    print()


def main():
    """Main entry point."""
    output_dir = Path("output")

    if not output_dir.exists():
        print("❌ No 'output' directory found. Run the tracker first.")
        sys.exit(1)

    # Parse arguments
    show_calls = "--calls" in sys.argv
    provider_arg = None

    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            provider_arg = arg
            break

    # Find all provider files
    provider_files = list(output_dir.glob("api_usage_*.json"))

    if not provider_files:
        print("❌ No API usage data found.")
        sys.exit(1)

    # Extract provider names
    providers = [f.stem.replace("api_usage_", "") for f in provider_files]

    # Filter to specific provider if requested
    if provider_arg:
        if provider_arg not in providers:
            print(f"❌ Provider '{provider_arg}' not found.")
            print(f"Available providers: {', '.join(providers)}")
            sys.exit(1)
        providers = [provider_arg]

    # Display data for each provider
    for provider in providers:
        data = load_provider_data(provider, output_dir)

        if not data:
            print(f"⚠️  Could not load data for {provider}")
            continue

        display_provider_summary(provider, data)
        display_window_analysis(provider, data)

        if show_calls:
            display_detailed_calls(provider, data)

    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
