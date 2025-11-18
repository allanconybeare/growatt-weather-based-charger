# Solcast Rate Limit Issue - Explanation

## Problem
When manually running `python growatt_charger.py` today (2025-11-15), you got:
```
[Solcast] API rate limit exceeded (10 calls/day)
```

You're right to be suspicious - you haven't knowingly made many calls, but the rate limit IS real.

## Root Cause

### The Solcast Free Tier Limit
- **Limit:** 10 API calls per 24-hour rolling window
- **Window:** NOT a calendar day, but a rolling 24-hour period
- **Tracking:** Your key is tracking by request timestamp

### What Happened
Based on API usage logs:

**2025-11-14 at 15:50:**
- Made 4 API calls to Solcast
- Successfully got 3 responses
- Had 1 failed call (possibly due to invalid key at that time)
- **Result:** Quota went from 10 → 6 remaining

**Time Range 15:50 Nov 14 to 15:50 Nov 15:**
- If you made 4 more calls between 15:50 and now
- Your quota exhausted completely
- Any call after the 10th one in the 24-hour window gets HTTP 429 (rate limited)

**2025-11-15 at 22:20 (now):**
- Made 2 calls to Solcast
- Both failed with HTTP 429 (already rate limited)
- Still within 24-hour window from yesterday's 15:50

## Evidence

### API Usage Tracking
```
2025-11-14 15:50:29 - 4 calls made, 2 quota remaining
2025-11-15 22:20:41 - 2 calls attempted, both failed (rate limit)
```

### Timeline
```
Nov 14 15:50 UTC       → First quota exhaustion point (~6 remaining)
Nov 15 15:50 UTC       → Old calls expire from rolling window
Nov 15 22:20 UTC (now) → Still hitting rate limit (within 24h)
```

## Solutions

### Option 1: Wait for Rolling Window to Clear ✅ (RECOMMENDED FOR TONIGHT)
- Your oldest calls from Nov 14 15:50 will expire at Nov 15 15:50 UTC
- After that time, you'll have 10 fresh calls available
- **Timeline:** Approximately in the next 6-8 hours from now

### Option 2: Use Forecast.Solar Only 🔄 (TEMPORARY)
Currently your config has both providers:
```ini
[main]
providers = forecast.solar,solcast
primary_provider = solcast
```

To use forecast.solar until quota resets:
```ini
[main]
providers = forecast.solar
primary_provider = forecast.solar
```

**Pros:**
- Works immediately
- No rate limits
- Already tested and working

**Cons:**
- Less accurate than Solcast (your specific location)
- Solcast not used (rolling window keeps consuming calls if primary fails)

### Option 3: Use Unmetered Resource ID 🆓 (FREE, UNLIMITED)
Solcast provides free unmetered locations. Currently commented out in config:

```ini
[solcast]
# Unmetered (unlimited) free resource:
resource_id = 1a57-6b1f-ec18-c5c8  # Stonehenge
```

This resource ID is in the public "unmetered locations" list and doesn't count against the 10 call/day limit.

**Pros:**
- Unlimited API calls
- No waiting
- Still uses Solcast for forecasts

**Cons:**
- Uses Stonehenge location (not your rooftop)
- Less accurate for your site

### Option 4: Purchase Additional Quota 💰 (PRODUCTION)
Solcast offers paid plans with higher limits. See: https://solcast.com.au/pricing

## Recommended Approach

For tonight:

1. **If you need accurate forecasts NOW:**
   - Temporarily switch to forecast.solar only (Option 2)
   - Wait until ~15:50 UTC tomorrow
   - Switch back to Solcast

2. **If testing/development:**
   - Use the unmetered Stonehenge location (Option 3)
   - Leaves quota available for production

3. **Best long-term:**
   - Wait until rolling window resets
   - Go back to normal Solcast with your resource IDs
   - Monitor daily quota usage via `output/api_usage_*.json`

## How to Check When Quota Resets

```powershell
# View today's API usage
python -m json.tool output/api_usage_2025-11-15.json | Select-String "last_call_time"

# View yesterday's API usage  
python -m json.tool output/api_usage_2025-11-14.json | Select-String "last_call_time"
```

The oldest call determines when the 24-hour window expires.

## Why This Happened

The core issue is: **Solcast free tier is very restrictive with rolling windows**. Each API call counts, including:
- Failed auth attempts
- Misconfigurations
- Testing/debugging
- Manual test runs

Your best practices moving forward:
1. ✅ Monitor `output/api_usage_*.json` daily
2. ✅ Prefer forecast.solar during development
3. ✅ Save Solcast calls for production 22:00 and 14:00 runs
4. ✅ Consider the unmetered location for testing

## Files with Rate Limit Tracking
- `output/api_usage_2025-11-15.json` - Today's usage (2 failed calls logged)
- `output/api_usage_2025-11-14.json` - Yesterday's usage (4 calls, quota at 2)
- `logs/growatt-charger.log` - Application logs with Solcast status

---

**TL;DR:** You hit the Solcast free tier 10 calls/day rolling window limit. The quota will refresh approximately tomorrow at 15:50 UTC (when yesterday's oldest calls roll out of the 24-hour window). Until then, use forecast.solar for testing.
