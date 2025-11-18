# Solcast API Usage Tracking Implementation

**Date Created:** November 14, 2025  
**Status:** ✅ COMPLETE  
**Related Issue:** Solcast API quota monitoring and rate limit tracking

## Overview

This document describes the implementation of comprehensive API usage tracking for the Growatt Weather-Based Charger, specifically designed to monitor Solcast API quota usage and prevent hitting rate limits.

## Problem Statement

The user needed a way to:
- Track API calls to Solcast to avoid hitting daily rate limits
- Monitor quota remaining vs. quota limit
- Get alerts when approaching limits (1-5 calls remaining)
- Log usage statistics for debugging and optimization
- Persist daily summaries for historical tracking

Previously, there was **no mechanism** to track API usage or warn about approaching quotas.

## Solution Architecture

### 1. API Usage Tracker Module (`modules/api_usage_tracker.py`)

A thread-safe utility module providing:

#### Key Classes
- **`APIUsageTracker`**: Main class for tracking API usage
  - In-memory statistics for each provider
  - Thread-safe operations using `threading.Lock()`
  - Optional persistence to JSON files
  - Quota tracking and alerting

#### Key Methods

```python
tracker = APIUsageTracker(persistence_dir="output")

# Record an API call
tracker.record_call(
    provider='solcast',
    endpoint='rooftop_sites/{resource_id}/forecasts',
    status_code=200,
    quota_remaining=8,
    quota_limit=10
)

# Get statistics
stats = tracker.get_provider_stats('solcast')
all_stats = tracker.get_all_stats()

# Log summary
tracker.log_summary(log_level=logging.INFO)

# Check for alerts
alerts = tracker.check_quota_alerts()  # Returns dict with alert messages

# Persist daily summary
filepath = tracker.save_daily_summary()  # Saves to JSON file
```

#### Global Convenience Functions

```python
from modules.api_usage_tracker import get_global_tracker, record_api_call

# Use global tracker
tracker = get_global_tracker(persistence_dir="output")

# Convenience function for recording
record_api_call(
    provider='solcast',
    endpoint='forecast',
    status_code=200,
    quota_remaining=5,
    quota_limit=10
)
```

### 2. Solcast Provider Integration (`modules/forecast_providers/solcast.py`)

The Solcast provider was enhanced to:

#### Extract Rate Limit Headers

Solcast API includes rate limit information in response headers:
- `x-rate-limit-limit`: Total calls allowed per day (typically 10 for free tier)
- `x-rate-limit-remaining`: Calls remaining today
- `x-rate-limit-reset`: Unix timestamp of quota reset time

#### Automatic Usage Recording

The `_make_request()` method now:
1. **Extracts** quota info from response headers
2. **Logs** rate limit information (with warnings if quota is low)
3. **Records** the API call to the global tracker
4. **Handles** graceful failures (tracking errors don't break API calls)

#### New Method: `_get_header_int()`

Helper method to safely extract integer values from response headers:
```python
def _get_header_int(self, response, header_name: str) -> Optional[int]:
    """Get an integer value from response headers."""
```

#### Updated Imports

Added imports for usage tracking:
```python
from typing import Dict, Optional
from ..api_usage_tracker import record_api_call
```

## Features Implemented

### ✅ Core Features

1. **Automatic API Call Tracking**
   - Every Solcast API call is automatically recorded
   - Captures: provider name, endpoint, HTTP status, timestamp
   - Thread-safe for concurrent calls

2. **Quota Monitoring**
   - Extracts rate limit info from API response headers
   - Tracks remaining calls vs. limit
   - Shows percentage of quota used
   - Stores last quota check timestamp

3. **Intelligent Alerting**
   - **🔴 CRITICAL**: 0 calls remaining (quota exhausted)
   - **🟠 WARNING**: 1-2 calls remaining
   - **🟡 CAUTION**: 3-5 calls remaining
   - Logged at appropriate log levels (WARNING/INFO)

4. **Logging Integration**
   - Info-level logs: Successful calls with quota status
   - Warning-level logs: Low quota alerts
   - Debug-level logs: Header parsing details
   - Graceful handling of logging failures

5. **Statistics & Reporting**
   - Total calls (successful + failed)
   - Success rate percentage
   - Error tracking with timestamps and messages
   - Per-provider statistics

6. **Daily Summary Persistence**
   - Optional JSON file output
   - Stores date, timestamp, and all provider stats
   - File format: `api_usage_YYYY-MM-DD.json`
   - Useful for historical analysis

7. **Thread Safety**
   - Uses `threading.Lock()` for all state access
   - Safe for concurrent API calls from multiple threads
   - Global tracker singleton pattern with double-checked locking

## File Changes

### Modified Files

1. **`modules/forecast_providers/solcast.py`**
   - Added `Optional` to imports
   - Added `from ..api_usage_tracker import record_api_call`
   - Enhanced `_make_request()` to extract and record quota info
   - Added `_get_header_int()` helper method
   - Enhanced `_log_rate_limit_info()` for better warnings

### New Files

1. **`modules/api_usage_tracker.py`** (~230 lines)
   - Complete tracking implementation
   - Thread-safe APIUsageTracker class
   - Global tracker singleton
   - Convenience functions

2. **`demo_api_usage_tracking.py`** (test/demo script)
   - Shows all tracker features
   - Simulates API calls with quota info
   - Demonstrates alerting system
   - Shows output persistence

## Usage Examples

### Example 1: Checking Quota in Your Own Code

```python
from modules.api_usage_tracker import get_global_tracker

tracker = get_global_tracker()
stats = tracker.get_provider_stats('solcast')

if stats.get('quota_remaining') and stats['quota_remaining'] <= 3:
    print(f"⚠️  Low Solcast quota: {stats['quota_remaining']} calls remaining")
```

### Example 2: Logging a Summary at App Shutdown

```python
from modules.api_usage_tracker import get_global_tracker

# At end of app execution
tracker = get_global_tracker()
tracker.log_summary(log_level=logging.INFO)
tracker.save_daily_summary()
```

### Example 3: Checking for Alerts

```python
from modules.api_usage_tracker import get_global_tracker

tracker = get_global_tracker()
alerts = tracker.check_quota_alerts()

for provider, alert_message in alerts.items():
    print(f"ALERT for {provider}: {alert_message}")
```

### Example 4: Integration in Main App (Future Enhancement)

In `src/app.py` or `src/app_afternoon_peak_check.py`:

```python
from modules.api_usage_tracker import get_global_tracker
import logging

# Initialize tracker at app start
tracker = get_global_tracker(persistence_dir="output")

# ... run forecasting ...

# At app end, log and persist
logger = logging.getLogger(__name__)
tracker.log_summary(log_level=logging.INFO)
tracker.save_daily_summary()

# Check for critical alerts
alerts = tracker.check_quota_alerts()
if alerts:
    for provider, msg in alerts.items():
        logger.warning(f"API quota alert: {msg}")
```

## How Solcast API Quota Works

### Rate Limits by Tier

| Tier | Daily Limit | Reset Time |
|------|------------|-----------|
| Free | 10 calls | UTC 00:00 |
| Unmetered | Unlimited | N/A |
| Paid | Custom | Custom |

### Response Header Example

```
HTTP/1.1 200 OK
x-rate-limit-limit: 10
x-rate-limit-remaining: 7
x-rate-limit-reset: 1731571200
Content-Type: application/json
...
```

### When You Added Unmetered Key

You mentioned adding an unmetered Solcast key to `conf/growatt-charger.ini`. With an unmetered key:
- `x-rate-limit-limit` will be much higher (or 999999)
- `x-rate-limit-remaining` will not decrease
- **No quota concerns** for API calls
- Perfect for development and testing

## Output Example

Running `demo_api_usage_tracking.py` produces:

```
======================================================================
📈 Usage Statistics:
======================================================================

Total API calls:      4
Successful calls:     3
Failed calls:         1
Quota remaining:      2
Quota limit:          10

======================================================================
🚨 Quota Alerts:
======================================================================

solcast: 🟠 WARNING: Only 2 calls remaining
```

And creates JSON persistence:

```json
{
  "date": "2025-11-14",
  "timestamp": "2025-11-14T15:37:52.768707",
  "providers": {
    "solcast": {
      "total_calls": 4,
      "successful_calls": 3,
      "failed_calls": 1,
      "quota_remaining": 2,
      "quota_limit": 10,
      "last_quota_check": "2025-11-14T15:37:52.767821"
    }
  }
}
```

## Testing

### Run the Demo
```powershell
python demo_api_usage_tracking.py
```

Output shows:
- ✅ Successful API calls
- ⚠️ Low quota warnings
- ❌ Failed calls
- Usage statistics
- Quota alerts
- Daily summary persistence

### Integration Testing

When Solcast provider makes real API calls:
1. Rate limit headers are extracted from responses
2. `record_api_call()` is called automatically
3. Quota info is logged (visible in `logs/` directory)
4. Warnings appear if quota is low

## Future Enhancements

### Possible Additions

1. **Quota Predictor**: Estimate when quota will be exhausted based on call frequency
2. **Retry Strategy**: Automatically retry failed calls or defer calls when quota is low
3. **Provider Switching**: Automatically switch to forecast.solar if Solcast quota exhausted
4. **Notifications**: Email/SMS alerts when quota critical
5. **Dashboard**: Web interface showing live quota usage
6. **Analytics**: Hourly/daily usage patterns and trends

### Recommended Next Steps

1. **Integrate into main app startup** (`src/app.py`):
   ```python
   tracker = get_global_tracker(persistence_dir=config_dir / "output")
   ```

2. **Add tracker logging at app shutdown**:
   ```python
   tracker.log_summary()
   tracker.save_daily_summary()
   ```

3. **Test with real Solcast calls** in your environment

4. **Monitor `output/api_usage_*.json` files** for daily patterns

## Thread Safety Notes

The tracker is fully thread-safe:
- Uses `threading.Lock()` for state access
- Safe for concurrent forecast calls
- Safe for concurrent tracking calls
- Global singleton pattern prevents duplicate instances

## Error Handling

The implementation is defensive:
- **Tracking failures don't break API calls**: Try/except wrapper catches tracker errors
- **Header parsing is safe**: Invalid headers return None, not exceptions
- **Logging is optional**: If logging fails, API calls continue
- **Persistence is optional**: If JSON save fails, in-memory stats remain valid

## Summary

✅ **Solcast API usage is now fully tracked and monitored**

- Every API call is recorded automatically
- Quota information is extracted from response headers
- Alerts warn when approaching limits
- Daily summaries persist to JSON files
- Thread-safe for production use
- No breaking changes to existing code
- Ready for integration into main app

The user can now:
- See exact API quota usage in logs
- Get warnings before hitting limits
- Track historical usage via JSON files
- Plan API consumption with accurate data
- Switch strategies if quota gets low (use unmetered key, wait for reset, etc.)
