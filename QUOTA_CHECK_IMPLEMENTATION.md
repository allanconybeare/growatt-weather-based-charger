# Pre-Flight Quota Check Implementation

## Overview

A smart pre-flight quota check system has been implemented to prevent wasting API calls when quota is exhausted or critically low. This system works in conjunction with the existing API usage tracker.

## What Was Added

### 1. **Enhanced API Usage Tracker** (`modules/api_usage_tracker.py`)

**New Method: `get_quota_status(provider: str)`**
```python
def get_quota_status(self, provider: str) -> Dict[str, Any]:
    """
    Returns quota status with:
    - quota_remaining: Calls left (None if unknown)
    - quota_limit: Total quota
    - calls_made: Total API attempts
    - successful_calls: Successful ones
    - failed_calls: Failed ones
    - status: "OK" | "LOW" | "CRITICAL" | "EXHAUSTED" | "UNKNOWN"
    """
```

**New Convenience Function: `get_quota_status(provider: str)`**
- Global function to easily query quota status from anywhere in the codebase
- Used by Solcast provider to make pre-flight checks

### 2. **Solcast Provider Enhancements** (`modules/forecast_providers/solcast.py`)

**New Method: `_check_quota_available(required_calls, min_buffer)`**
- Checks if sufficient quota exists before attempting API calls
- Parameters:
  - `required_calls`: How many API calls we plan to make (1 for single resource, 2+ for multiple)
  - `min_buffer`: Reserve to keep (default 1, to avoid hitting exact limit)
- Returns: `True` if safe to proceed, `False` if should skip
- Logs warning when quota is insufficient

**Updated Method: `get_forecast()`**
- Now calls `_check_quota_available()` before making any API requests
- Calculates required calls based on number of resource IDs configured
- Raises `RateLimitError` with descriptive message if quota check fails
- Automatically falls back to other providers (forecast.solar) when Solcast is skipped

**Enhanced Method: `_make_request()`**
- Now records **failed API calls** (401, 429, etc.) with quota information
- Detailed logging when rate-limited (429 status code)
- Tracks error messages and HTTP status codes for debugging

### 3. **Improved Error Handling**

**Rate Limit Detection**
```
When 429 (rate limited):
  - Logs detailed warning with reset time
  - Records the failed call in tracker
  - Raises RateLimitError for graceful fallback
```

**Authentication Error Detection**
```
When 401 (invalid key):
  - Records as failed call
  - Helps identify API key issues
```

## How It Works

### Scenario 1: Quota Available ✅
```
1. App calls get_forecast()
2. Provider calculates: need 1 call for single resource
3. Provider checks: quota_status = {remaining: 8, status: "OK"}
4. Check: 8 >= (1 + 1 buffer) = True
5. Proceeds with API call normally
```

### Scenario 2: Quota Approaching ⚠️
```
1. App calls get_forecast()
2. Provider calculates: need 2 calls for multiple resources
3. Provider checks: quota_status = {remaining: 2, status: "LOW"}
4. Check: 2 >= (2 + 1 buffer) = False (2 < 3)
5. Logs warning: "Insufficient quota: need 2 calls, have 2, skipping"
6. Raises RateLimitError
7. Forecast manager catches it, uses forecast.solar instead
8. No wasted API calls!
```

### Scenario 3: Quota Exhausted ❌
```
1. App calls get_forecast()
2. Provider checks: quota_status = {remaining: 0, status: "EXHAUSTED"}
3. Check: 0 >= (1 + 1 buffer) = False
4. Logs warning immediately
5. Skips Solcast entirely, uses forecast.solar
6. App runs successfully without hitting rate limit
```

## Log Output Examples

### Normal Operation
```
INFO: Solcast API quota: 8/10 calls remaining (20% used) (resets at 2025-11-17 20:15:00)
```

### Quota Check Passing
```
[No warning - proceeds normally]
```

### Quota Check Failing (Prevents Wasted Calls!)
```
WARNING: Solcast quota check: insufficient quota to proceed.
Remaining: 2, Need: 3, Status: LOW.
Skipping Solcast forecast. Will use fallback provider.
```

### Rate Limit Hit (Detailed Info)
```
WARNING: Solcast quota exhausted! Cannot make more calls until 2025-11-17 20:15:00 UTC.
Remaining: 0, Reset: 2025-11-17 20:15:00
```

## Configuration

The quota check is **automatic** - no configuration needed!

**Thresholds (in `get_quota_status()`):**
- `EXHAUSTED`: remaining ≤ 0
- `CRITICAL`: remaining ≤ 2
- `LOW`: remaining ≤ 5  
- `OK`: remaining > 5

**Buffer Logic (in `_check_quota_available()`):**
- Default buffer: 1 call
- For single resource: needs 1 + 1 = 2 remaining to proceed
- For multiple resources: needs N + 1 remaining (where N = number of resources)

You can adjust these by modifying the method parameters.

## Benefits

✅ **Prevents Quota Exhaustion** - Refuses to make calls when quota is low
✅ **Graceful Fallback** - Automatically uses forecast.solar when Solcast is skipped
✅ **Detailed Logging** - You see exactly why calls were skipped
✅ **Thread-Safe** - API tracker uses locks for concurrent access
✅ **First-Run Compatible** - Works even if quota status is unknown
✅ **Minimal Overhead** - Just checks an in-memory status before API call

## Testing After Quota Reset

When quota resets tomorrow (~20:15 UTC):

1. **Single Resource (Current Config)**
   ```
   Remaining: 10 → Check: 10 >= (1 + 1) = True ✅ Proceeds
   After call: Remaining: 9 → Still plenty
   ```

2. **Multiple Resources (Uncommented)**
   ```
   Remaining: 10 → Check: 10 >= (2 + 1) = True ✅ Proceeds  
   After calls: Remaining: 8 → Still OK
   ```

3. **Near Limit**
   ```
   Remaining: 2 → Check: 2 >= (1 + 1) = False ❌ Skips
   Falls back to forecast.solar automatically
   No wasted calls!
   ```

## Code Files Modified

1. **modules/api_usage_tracker.py**
   - Added `get_quota_status()` method to APIUsageTracker class
   - Added `get_quota_status()` convenience function

2. **modules/forecast_providers/solcast.py**
   - Added import: `from ..api_usage_tracker import record_api_call, get_quota_status`
   - Added `_check_quota_available()` method
   - Enhanced `get_forecast()` to check quota before making calls
   - Enhanced `_make_request()` to track failed calls with quota info
   - Improved error logging with reset times

3. **SOLCAST_QUOTA_MANAGEMENT.md**
   - Documented the quota model discovery
   - Explained why previous testing failed
   - Provided recommendations

## Next Steps

- ✅ Task 1-3 Complete: Quota model documented, tracker built, pre-flight check implemented
- ⏳ Task 4: Dashboard/report showing usage patterns (can be added later if needed)

When quota resets, the system will automatically:
1. Start tracking calls with the new quota window
2. Show reset times in logs
3. Skip calls if quota gets too low
4. Use forecast.solar as reliable fallback

You're now protected from accidentally exhausting your Solcast quota!
