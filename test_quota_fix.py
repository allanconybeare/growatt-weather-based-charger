#!/usr/bin/env python
"""Quick test to verify quota calculation fix."""

from modules.api_usage_tracker import get_global_tracker

# Simulate that 2 calls have been made (as shown in the JSON)
tracker = get_global_tracker()

# Record 2 calls with the same X-Rate-Limit-Remaining header value (599)
tracker.record_call("solcast", "rooftop_sites/d367-4a1c-0d79-32b9/forecasts", 200, 599, None)
tracker.record_call("solcast", "rooftop_sites/d367-4a1c-0d79-32b9/forecasts", 200, 599, None)

# Check status
status = tracker.get_quota_status("solcast")
print("\n=== Quota Status After 2 API Calls ===")
print(f"Total calls made: {status['calls_made']}")
print(f"Successful calls: {status['successful_calls']}")
print(f"Failed calls: {status['failed_calls']}")
print(f"Quota remaining: {status['quota_remaining']}")
print(f"Quota limit: {status['quota_limit']}")
print(f"Status: {status['status']}")

# Verify the calculation
expected_remaining = 10 - status["calls_made"]
print(f"\nExpected remaining (10 - {status['calls_made']}): {expected_remaining}")
print(f"Matches expected: {status['quota_remaining'] == expected_remaining}")
