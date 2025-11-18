# Solcast API Quota Management Guide

## Critical Discovery: Quota Model

### How Solcast Quota Works (Based on Testing)

**⚠️ Important Finding:**
- **Quota resets on a rolling 24-hour window**, NOT a calendar day
- **Each API request counts**, whether successful or failed (401, 429, etc.)
- **The reset time shifts forward with each API call** - it's always 24 hours from the LAST call made
- **Failed authentication (401) still consumes quota** - the API counts the hit even if your key is wrong

### Example Timeline from Nov 16, 2025

```
20:09:30 - Call 1 (success) → Remaining: 599, Reset: 20:10:00 (UTC)
20:09:33 - Call 2 (success) → Remaining: 598, Reset: 20:10:00 (shifted to 24h from this call)
[Quota exhausted - all subsequent calls get 429 Rate Limited]
20:11:04 - Call 3 (failed)  → Remaining: 599, Reset: 20:12:00 (reset timer pushed ANOTHER 24h!)
20:11:04 - Call 4 (failed)  → Remaining: 598, Reset: 20:12:00 (reset timer pushed AGAIN)
```

### Why This Matters

❌ **Old Assumption:** "It's a calendar day, so if I wait until tomorrow 20:15 UTC it'll reset"
✅ **Reality:** The reset time is ALWAYS 24 hours from the last API call (successful or failed)
⚠️ **Problem:** If you're getting rate limited and keep retrying, you keep pushing the reset window further into the future!

## Quota Tracking Implementation

### Current Status
- ✅ `modules/api_usage_tracker.py` exists and tracks calls
- ✅ `_make_request()` in `solcast.py` records successful calls with quota info
- ❌ Failed/rate-limited calls are NOT being tracked (gap in implementation)

### What We Need

1. **Track ALL calls** (successful, failed, rate-limited) with timestamps
2. **Log reset time with each call** to understand the pattern
3. **Pre-flight quota check** to avoid wasting calls
4. **Quota report** showing daily usage pattern

## Usage Logs

Current log output when calling Solcast:
```
2025-11-16 20:09:32,273 INFO: Solcast API rate limit - Limit: unknown, Remaining: 599, Reset: 1763323800 (resets at 2025-11-16 20:10:00)
```

This tells us:
- **Remaining: 599** - We have 599 calls left (out of ~600 free tier)
- **Reset: 1763323800** - Unix timestamp for reset (converts to 2025-11-16 20:10:00)

## Recommendations

### 1. For Current Testing (Before Next Reset)
- **DO NOT retry failed calls** - Each retry wastes a quota slot and pushes reset further
- **Wait until the reset time shown in logs** to attempt again
- **Monitor logs closely** for the moment remaining quota resets

### 2. Long-term Quota Management
- Track failed calls with the same detail as successful ones
- Log reset timestamp with EVERY attempt (not just successful ones)
- Before making a forecast call, check if quota is available
- Consider caching forecasts to avoid redundant calls
- Add warning threshold (e.g., warn if < 2 calls remaining)

### 3. Production Use
- For daily scheduled runs, time them to avoid hitting quota limits
- With 10 calls/day free tier:
  - 1 call per provider ≈ 10 providers possible
  - Multiple calls per provider = need to prioritize
  - Multiple resource IDs = each one is a separate call
- Consider upgrading to paid tier if needing frequent testing

## Current Configuration

`conf/growatt-charger.ini`:
```ini
[solcast]
api_key = <YOUR_SOLCAST_API_KEY>  # Set via SOLCAST_API_KEY env var
resource_id = d367-4a1c-0d79-32b9
# Commented out: cc26-bafb-3efe-7573  # Testing with single ID to conserve quota
```

**Note:** Environment variable takes precedence over config file value, so it's safe to have placeholder in config.

## Files Modified (Nov 16, 2025)

1. **modules/forecast_providers/solcast.py**
   - Changed auth from `X-API-Key` to `Authorization: Bearer` (which actually works!)
   - Added human-readable reset time logging
   - Changed logger to use `growatt-charger` instead of module name for visibility

2. **conf/growatt-charger.ini**
   - Commented out second resource ID to test with single call
   - Placeholder API key with env var override

3. **modules/api_usage_tracker.py**
   - Already exists, can be enhanced to track failures

## Next Steps After Quota Reset

When quota resets (~24 hours after last call):
1. Uncomment second resource ID in config
2. Run app and verify both resource IDs are fetched
3. Enhance tracking to show failed call attempts
4. Consider implementing pre-flight quota check
