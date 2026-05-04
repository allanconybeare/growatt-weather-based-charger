#!/usr/bin/env python3

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


class ProviderUsage:
    def __init__(self, data):
        self.provider = data.get("provider")
        qm = data.get("quota_model", {})
        self.window_hours = qm.get("window_hours", 1)
        self.limit = qm.get("limit", 0)
        self.reset_type = qm.get("reset_type", "fixed")
        self.last_updated = data.get("last_updated")
        self.call_history = data.get("call_history", [])

    @staticmethod
    def load(path):
        with open(path) as f:
            data = json.load(f)
        return ProviderUsage(data)

    def calls_in_window(self, now):
        window = timedelta(hours=self.window_hours)
        cutoff = now - window
        return [c for c in self.call_history if datetime.fromisoformat(c["timestamp"]) >= cutoff]

    def errors_in_window(self, now):
        return [c for c in self.calls_in_window(now) if not c.get("success")]

    def current_remaining(self, now):
        if self.provider == "solcast":
            used = len(self.calls_in_window(now))
            return max(self.limit - used, 0)
        latest = self.call_history[-1]
        return latest.get("quota_remaining")

    def time_until_reset(self, now):
        if not self.call_history:
            return None
        window = timedelta(hours=self.window_hours)
        window_calls = self.calls_in_window(now)
        if not window_calls:
            return None
        oldest = datetime.fromisoformat(window_calls[0]["timestamp"])
        return oldest + window - now


def print_provider_view(usage):
    now = datetime.utcnow()
    window_calls = usage.calls_in_window(now)
    errors = usage.errors_in_window(now)
    remaining = usage.current_remaining(now)
    reset_in = usage.time_until_reset(now)

    print(f"Provider: {usage.provider}")
    print(f"Last updated: {usage.last_updated}")
    print(f"Quota window: {usage.window_hours}h")
    print(f"Limit: {usage.limit}")
    print(f"Retention window: {usage.window_hours * 2}h")
    print(f"Calls in window: {len(window_calls)}")
    print(f"Errors in window: {len(errors)}")
    print(f"Remaining: {remaining}")

    if reset_in:
        seconds = int(reset_in.total_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        print(f"Next reset in: {hours}h {minutes}m")
    else:
        print("Next reset in: N/A")

    print()
    print("Recent calls:")
    for c in usage.call_history[-5:]:
        ts = c["timestamp"]
        ep = c["endpoint"]
        sc = c["status_code"]
        print(f"  {ts}  {sc}  {ep}")


def print_history(usage):
    print("Full history:")
    for c in usage.call_history:
        ts = c["timestamp"]
        ep = c["endpoint"]
        sc = c["status_code"]
        print(f"{ts}  {sc}  {ep}")


def print_trends(usage):
    buckets = defaultdict(int)
    for c in usage.call_history:
        ts = datetime.fromisoformat(c["timestamp"])
        if usage.provider == "forecast.solar":
            bucket = ts.replace(minute=0, second=0, microsecond=0)
        else:
            bucket = ts.date()
        buckets[bucket] += 1

    print("Trends:")
    for bucket, count in sorted(buckets.items()):
        print(f"{bucket}  {count}")


def main():
    if len(sys.argv) < 2:
        print("Usage: view_api_usage_state.py provider [--history] [--trends]")
        sys.exit(1)

    provider = sys.argv[1]
    path = Path("output") / f"api_usage_{provider}.json"
    if not path.exists():
        print(f"No file for provider: {provider}")
        sys.exit(1)

    usage = ProviderUsage.load(path)

    if "--history" in sys.argv:
        print_history(usage)
        return

    if "--trends" in sys.argv:
        print_trends(usage)
        return

    print_provider_view(usage)


if __name__ == "__main__":
    main()
