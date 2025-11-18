#!/usr/bin/env python3
"""
Script to view and analyze Solcast API usage summaries from JSON files.

Usage:
    python view_api_usage_summaries.py          # Show today's summary
    python view_api_usage_summaries.py --all    # Show all available
    python view_api_usage_summaries.py --trends # Show 7-day trend
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def format_percentage(used: int, total: int) -> str:
    """Format usage as percentage."""
    if total == 0:
        return "N/A"
    pct = (used / total) * 100
    return f"{pct:.1f}%"


def show_single_summary(filepath: Path) -> None:
    """Display a single API usage summary file."""
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    with open(filepath) as f:
        data = json.load(f)

    date = data.get("date", "Unknown")
    timestamp = data.get("timestamp", "Unknown")

    print(f"\n{'='*70}")
    print(f"API Usage Summary: {date}")
    print(f"Recorded: {timestamp}")
    print(f"{'='*70}\n")

    providers = data.get("providers", {})

    if not providers:
        print("No API usage recorded.")
        return

    for provider_name, stats in providers.items():
        print(f"📊 Provider: {provider_name.upper()}")
        print(f"   Total API calls:      {stats.get('total_calls', 0)}")
        print(f"   Successful:           {stats.get('successful_calls', 0)}")
        print(f"   Failed:               {stats.get('failed_calls', 0)}")

        # Calculate success rate
        total = stats.get("total_calls", 0)
        success = stats.get("successful_calls", 0)
        if total > 0:
            success_rate = (success / total) * 100
            print(f"   Success rate:         {success_rate:.1f}%")

        # Quota info
        remaining = stats.get("quota_remaining")
        limit = stats.get("quota_limit")

        if remaining is not None and limit is not None:
            used = limit - remaining
            pct = format_percentage(used, limit)
            print(f"   Quota remaining:      {remaining}/{limit}")
            print(f"   Quota used:           {used}/{limit} ({pct})")

            # Alert status
            if remaining == 0:
                print("   Status:               🔴 CRITICAL - Quota exhausted!")
            elif remaining <= 2:
                print(f"   Status:               🟠 WARNING - Only {remaining} calls left!")
            elif remaining <= 5:
                print(f"   Status:               🟡 CAUTION - {remaining} calls left")
            else:
                print("   Status:               ✅ OK")

        # Last check time
        last_check = stats.get("last_quota_check")
        if last_check:
            print(f"   Last quota check:     {last_check}")

        # Errors if any
        errors = stats.get("errors", [])
        if errors:
            print(f"   Errors:               {len(errors)}")
            for error in errors[-3:]:  # Show last 3 errors
                print(
                    f"     • [{error.get('timestamp')}] {error.get('error')} "
                    f"(HTTP {error.get('status_code')})"
                )
            if len(errors) > 3:
                print(f"     ... and {len(errors) - 3} more errors")

        print()


def show_all_summaries(output_dir: Path) -> None:
    """Show all available API usage summaries."""
    summaries = sorted(output_dir.glob("api_usage_*.json"))

    if not summaries:
        print("No API usage summaries found in output/")
        return

    print(f"\n{'='*70}")
    print("Available API Usage Summaries")
    print(f"{'='*70}\n")

    for filepath in summaries:
        with open(filepath) as f:
            data = json.load(f)

        date = data.get("date", "Unknown")
        providers = data.get("providers", {})

        # Build summary line
        provider_summary = []
        for provider_name, stats in providers.items():
            calls = stats.get("total_calls", 0)
            # success = stats.get("successful_calls", 0)
            remaining = stats.get("quota_remaining")

            if remaining is not None:
                provider_summary.append(f"{provider_name}: {calls} calls, {remaining} quota")
            else:
                provider_summary.append(f"{provider_name}: {calls} calls")

        print(f"{date}  •  {' | '.join(provider_summary)}")

    print(f"\nTotal: {len(summaries)} daily summaries available")
    print("\nTo view a specific file:")
    print("  cat output\\api_usage_YYYY-MM-DD.json | ConvertFrom-Json | Format-List")


def show_trends(output_dir: Path, days: int = 7) -> None:
    """Show API usage trends over the past N days."""
    summaries = sorted(output_dir.glob("api_usage_*.json"))[-days:]

    if not summaries:
        print("No API usage summaries found for trend analysis.")
        return

    print(f"\n{'='*70}")
    print(f"API Usage Trends (Last {len(summaries)} Days)")
    print(f"{'='*70}\n")

    # Collect data by provider
    provider_trends: Dict[str, List[Dict[str, Any]]] = {}

    for filepath in summaries:
        with open(filepath) as f:
            data = json.load(f)

        date = data.get("date", "Unknown")
        providers = data.get("providers", {})

        for provider_name, stats in providers.items():
            if provider_name not in provider_trends:
                provider_trends[provider_name] = []

            provider_trends[provider_name].append(
                {
                    "date": date,
                    "total_calls": stats.get("total_calls", 0),
                    "successful_calls": stats.get("successful_calls", 0),
                    "failed_calls": stats.get("failed_calls", 0),
                    "quota_remaining": stats.get("quota_remaining"),
                    "quota_limit": stats.get("quota_limit"),
                }
            )

    # Display trends
    for provider_name, trend_data in provider_trends.items():
        print(f"📈 {provider_name.upper()}")
        print(f"{'Date':<12} {'Calls':<8} {'Success':<10} {'Failed':<8} {'Quota':<15}")
        print(f"{'-'*60}")

        for entry in trend_data:
            date = entry["date"]
            calls = entry["total_calls"]
            success = entry["successful_calls"]
            failed = entry["failed_calls"]

            if entry["quota_remaining"] is not None:
                remaining = entry["quota_remaining"]
                limit = entry["quota_limit"]
                quota_str = f"{remaining}/{limit}"
            else:
                quota_str = "N/A"

            print(f"{date:<12} {calls:<8} {success:<10} {failed:<8} {quota_str:<15}")

        # Calculate average calls per day
        avg_calls = sum(e["total_calls"] for e in trend_data) / len(trend_data)
        print(f"{'-'*60}")
        print(f"Average calls per day: {avg_calls:.1f}")

        # Predict quota exhaustion
        if trend_data[-1]["quota_remaining"] is not None:
            remaining = trend_data[-1]["quota_remaining"]
            avg_daily_calls = avg_calls

            if avg_daily_calls > 0:
                days_until_exhausted = remaining / avg_daily_calls
                if days_until_exhausted < 1:
                    print(f"⚠️  Quota will exhaust in {days_until_exhausted*24:.1f} hours!")
                elif days_until_exhausted < 30:
                    print(f"⚠️  Quota will exhaust in {days_until_exhausted:.1f} days")
                else:
                    print(f"✅ Quota OK for {days_until_exhausted:.0f}+ days at current usage")

        print()


def main():
    """Main entry point."""
    output_dir = Path("output")

    if not output_dir.exists():
        print("❌ No 'output' directory found. Run the app first to generate summaries.")
        sys.exit(1)

    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == "--all":
            show_all_summaries(output_dir)
        elif arg == "--trends":
            show_trends(output_dir, days=7)
        elif arg == "--help" or arg == "-h":
            print(__doc__)
        else:
            print(f"Unknown argument: {arg}")
            print("Use --all, --trends, or --help")
            sys.exit(1)
    else:
        # Show today's summary
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = output_dir / f"api_usage_{today}.json"

        if filepath.exists():
            show_single_summary(filepath)
        else:
            print(f"No summary found for today ({today}).")
            print("Run the app to generate summaries, or use --all to see available dates.")


if __name__ == "__main__":
    main()
