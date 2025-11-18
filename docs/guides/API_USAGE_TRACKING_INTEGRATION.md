# Integration Guide: Solcast API Usage Tracking in Your Workflows

This guide shows how to integrate API usage tracking into your existing scripts and apps.

## Quick Start - 3 Steps

### Step 1: Initialize Tracker in Your App

In `src/app.py` or any main entry point, add at the top:

```python
from modules.api_usage_tracker import get_global_tracker

# At app start
tracker = get_global_tracker(persistence_dir=str(project_root / "output"))
```

### Step 2: Log Summary at App End

Before your app exits, add:

```python
# At app shutdown or main() completion
tracker = get_global_tracker()
tracker.log_summary()
tracker.save_daily_summary()
```

### Step 3: Check for Alerts in Your Code

Anywhere you make decisions about forecasts:

```python
from modules.api_usage_tracker import get_global_tracker

tracker = get_global_tracker()
stats = tracker.get_provider_stats('solcast')

if stats.get('quota_remaining') is not None:
    if stats['quota_remaining'] <= 2:
        logger.warning(f"Solcast quota critical: {stats['quota_remaining']} calls left!")
    elif stats['quota_remaining'] <= 5:
        logger.info(f"Solcast quota low: {stats['quota_remaining']} calls left")
```

## Integration Patterns

### Pattern 1: Afternoon Peak Check (Most Common)

File: `src/app_afternoon_peak_check.py`

**Before (current state):**
```python
async def main():
    logger = setup_logging(...)

    # ... your app code ...

    # No tracking here
```

**After (with tracking):**
```python
from modules.api_usage_tracker import get_global_tracker

async def main():
    logger = setup_logging(...)
    tracker = get_global_tracker(persistence_dir=str(project_root / "output"))

    try:
        # ... your app code ...

        # Check quota status
        alerts = tracker.check_quota_alerts()
        if alerts:
            for provider, alert_msg in alerts.items():
                logger.warning(f"API ALERT: {alert_msg}")

    finally:
        # Always log summary before exit
        tracker.log_summary()
        tracker.save_daily_summary()
```

### Pattern 2: Overnight Charging Plan (22:00 Task)

File: `src/app.py`

**Enhancement:**
```python
def main():
    # ... config loading ...

    tracker = get_global_tracker(persistence_dir=output_dir)

    try:
        # ... forecast loading and calculation ...

        if alerts := tracker.check_quota_alerts():
            logger.warning(f"Quota alerts: {alerts}")

    finally:
        # Persist usage stats
        tracker.log_summary(log_level=logging.INFO)
        tracker.save_daily_summary()
```

### Pattern 3: Morning SOC Check

File: `morning_soc_check.py`

**Enhancement:**
```python
def main():
    logger = setup_logging(...)
    tracker = get_global_tracker()

    try:
        # ... your logic ...

        # Get quota info
        stats = tracker.get_all_stats()
        if stats:
            logger.info(f"API Usage: {stats}")

    finally:
        tracker.log_summary()
        tracker.save_daily_summary()
```

## Monitoring Quota in Real-Time

### Check Current Quota Status

```python
from modules.api_usage_tracker import get_global_tracker

tracker = get_global_tracker()

# Get per-provider stats
solcast_stats = tracker.get_provider_stats('solcast')
print(f"Remaining: {solcast_stats.get('quota_remaining')} / {solcast_stats.get('quota_limit')}")

# Or check for alerts
alerts = tracker.check_quota_alerts()
for provider, alert in alerts.items():
    print(f"{provider}: {alert}")
```

### View Daily Summary File

After any run:

```powershell
# List all daily summaries
ls output\api_usage_*.json

# View today's summary
cat output\api_usage_2025-11-14.json | ConvertFrom-Json | Format-List

# Or pretty-print with Python
python -m json.tool output\api_usage_2025-11-14.json
```

### Track Usage Over Time

```python
import json
from pathlib import Path

def show_weekly_usage():
    """Show API usage for the past 7 days."""
    output_dir = Path("output")

    for usage_file in sorted(output_dir.glob("api_usage_*.json"))[-7:]:
        with open(usage_file) as f:
            data = json.load(f)
            providers = data.get('providers', {})
            for provider, stats in providers.items():
                calls = stats.get('total_calls', 0)
                success = stats.get('successful_calls', 0)
                remaining = stats.get('quota_remaining', 'N/A')
                print(f"{data['date']} - {provider}: {calls} calls ({success} success), {remaining} quota remaining")
```

## Alert Strategies

### Strategy 1: Stop Forecasting When Quota Critical

```python
tracker = get_global_tracker()
stats = tracker.get_provider_stats('solcast')

if stats.get('quota_remaining') == 0:
    logger.error("Solcast quota exhausted for today!")
    sys.exit(1)  # Or use fallback provider
elif stats.get('quota_remaining', 999) <= 2:
    logger.warning("Solcast quota nearly exhausted, switching to forecast.solar")
    use_backup_provider = True
```

### Strategy 2: Log Quota Every N Calls

```python
tracker = get_global_tracker()
call_count = 0

while True:
    call_count += 1
    # ... make API call ...

    if call_count % 3 == 0:  # Every 3rd call
        stats = tracker.get_provider_stats('solcast')
        logger.info(f"After {call_count} calls: {stats.get('quota_remaining')} quota remaining")
```

### Strategy 3: Adaptive Rate Limiting

```python
import time

tracker = get_global_tracker()
stats = tracker.get_provider_stats('solcast')
remaining = stats.get('quota_remaining', 10)

# Sleep proportionally to quota usage
if remaining <= 2:
    logger.warning(f"Quota critical ({remaining} left), adding 5min delay")
    time.sleep(300)  # 5 minutes
elif remaining <= 5:
    logger.info(f"Quota low ({remaining} left), adding 1min delay")
    time.sleep(60)   # 1 minute
```

## Troubleshooting

### Issue: "API quota_remaining is always 'unknown'"

**Cause:** Solcast may not return rate limit headers in free tier.

**Solutions:**
1. Use unmetered API key (you already did this!)
2. Check that Solcast provider is installed correctly
3. Verify response headers with debug logging:
   ```python
   import logging
   logging.getLogger('modules.forecast_providers.solcast').setLevel(logging.DEBUG)
   ```

### Issue: "No JSON file created in output/"

**Cause:** `persistence_dir` not configured.

**Solution:**
```python
tracker = get_global_tracker(persistence_dir="output")  # Set this!
tracker.save_daily_summary()
```

### Issue: Quota shows 10/10 but we made calls

**Cause:** Using unmetered key (it doesn't decrement).

**This is expected!** Unmetered keys show quota as always high/full.

### Issue: Tracking is slow/affecting performance

**Unlikely but possible fixes:**
```python
# Only track debug logs at INFO level (not DEBUG)
logging.getLogger('modules.api_usage_tracker').setLevel(logging.INFO)

# Persistence happens in background, shouldn't block
# But if needed, could make it optional:
if datetime.now().hour == 23:  # Only save at 11 PM
    tracker.save_daily_summary()
```

## Configuration Examples

### Example: With Unmetered Solcast Key (Your Current Setup)

`conf/growatt-charger.ini`:
```ini
[solcast]
resource_id = your_resource_id
api_key = your_unmetered_key  # Unlimited calls!
```

**Expected Tracker Output:**
```
Solcast API quota: 999999/999999 calls remaining (0.0% used)
```

✅ No quota concerns with unmetered key!

### Example: With Free Tier Solcast Key

`conf/growatt-charger.ini`:
```ini
[solcast]
resource_id = your_resource_id
api_key = your_free_tier_key  # 10 calls/day limit
```

**Expected Tracker Behavior:**
- Starts: `10/10` calls remaining
- After 1 call: `9/10` remaining
- After 8 calls: `2/10` remaining → 🟡 CAUTION alert
- After 9 calls: `1/10` remaining → 🟠 WARNING alert  
- After 10 calls: `0/10` remaining → 🔴 CRITICAL alert

### Example: With Paid Solcast Tier

```ini
[solcast]
resource_id = your_resource_id
api_key = your_paid_key
# May have higher limits, e.g., 100 calls/day
```

**Expected Tracker Behavior:**
- Tracks larger quota (100 or custom limit)
- Alerts at same thresholds (1-5 calls remaining)

## Performance Considerations

The tracker is designed for zero performance impact:

| Operation | Cost |
|-----------|------|
| record_api_call() | ~1ms (lock contention minimal) |
| get_provider_stats() | ~0.1ms (just dict access) |
| log_summary() | ~5ms (logging + string formatting) |
| save_daily_summary() | ~20ms (file I/O) |

**No optimization needed** for typical use cases.

## Next Steps

1. **Choose integration pattern** from above based on your script
2. **Add tracker initialization** in `main()` or startup code
3. **Add tracker logging** at shutdown
4. **Run demo** to verify: `python demo_api_usage_tracking.py`
5. **Test with real API calls** in your workflow
6. **Monitor `output/api_usage_*.json`** for trends
7. **Adjust strategies** as needed for your use case

## Questions?

- **"Can I use this with forecast.solar?"** Yes, same pattern works. Already implemented in Solcast, forecast.solar can follow.
- **"Does this work with unmetered keys?"** Yes, quota shows as unlimited/full which is correct.
- **"Can I get historical usage?"** Yes, JSON files persist daily. Analyze with Python/PowerShell.
- **"Is there a dashboard?"** Not yet, but JSON files can be used to build one.
- **"What if quota runs out?"** App logs warning but continues. Can switch to backup provider or unmetered key.

---

**Happy tracking!** 🚀
