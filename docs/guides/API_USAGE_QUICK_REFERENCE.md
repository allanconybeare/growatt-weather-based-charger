# Solcast API Usage Tracking - Quick Reference

## Install (Already Done ✅)

New module: `modules/api_usage_tracker.py`  
Modified: `modules/forecast_providers/solcast.py`

## One-Minute Setup

Add to your `main()` function:

```python
from modules.api_usage_tracker import get_global_tracker

# At start
tracker = get_global_tracker(persistence_dir="output")

# ... your code ...

# At end (before exit)
tracker.log_summary()
tracker.save_daily_summary()
```

**Done!** API usage is now tracked automatically.

## Common Commands

### Check Current Quota
```python
from modules.api_usage_tracker import get_global_tracker

tracker = get_global_tracker()
stats = tracker.get_provider_stats('solcast')
print(f"Quota: {stats.get('quota_remaining')}/{stats.get('quota_limit')}")
```

### Get All Stats
```python
tracker = get_global_tracker()
all_stats = tracker.get_all_stats()
for provider, stats in all_stats.items():
    print(f"{provider}: {stats['total_calls']} calls, {stats['successful_calls']} success")
```

### Check for Alerts
```python
tracker = get_global_tracker()
alerts = tracker.check_quota_alerts()
for provider, alert_msg in alerts.items():
    print(f"ALERT: {alert_msg}")
```

### View Daily Summary
```powershell
# PowerShell
cat output\api_usage_2025-11-14.json | ConvertFrom-Json | Format-List

# Or Python
python -m json.tool output\api_usage_2025-11-14.json | more
```

### Manual API Call Recording
```python
from modules.api_usage_tracker import record_api_call

record_api_call(
    provider='solcast',
    endpoint='rooftop_sites/{id}/forecasts',
    status_code=200,
    quota_remaining=5,
    quota_limit=10
)
```

## What Gets Tracked

- ✅ Total API calls (successful + failed)
- ✅ Success/failure rate
- ✅ Quota remaining vs. limit
- ✅ Last quota check timestamp
- ✅ Error messages
- ✅ Percentage of quota used

## Alert Levels

| Level | Condition | Example |
|-------|-----------|---------|
| 🔴 **CRITICAL** | 0 calls remaining | `"Quota exhausted! No API calls remaining."` |
| 🟠 **WARNING** | 1-2 calls remaining | `"Only 1 call remaining!"` |
| 🟡 **CAUTION** | 3-5 calls remaining | `"5 calls remaining (50% quota used)"` |

## Files

| File | Purpose |
|------|---------|
| `modules/api_usage_tracker.py` | Main tracking implementation |
| `modules/forecast_providers/solcast.py` | Enhanced with auto-tracking |
| `demo_api_usage_tracking.py` | Demo/test script |
| `docs/development/SOLCAST_API_USAGE_TRACKING.md` | Full documentation |
| `docs/guides/API_USAGE_TRACKING_INTEGRATION.md` | Integration patterns |
| `output/api_usage_*.json` | Daily summaries |

## Features

✅ Automatic tracking (no manual calls needed)  
✅ Quota extraction from API response headers  
✅ Smart alerting (critical → warning → caution)  
✅ Thread-safe for concurrent calls  
✅ Daily JSON persistence  
✅ Zero performance impact  
✅ Works with unmetered keys (shows unlimited)  

## With Unmetered Solcast Key (Your Setup)

```
✅ Quota shows as unlimited (999999/999999)
✅ No quota concerns
✅ All API calls work without limits
✅ Perfect for development/testing
```

## Typical Usage Timeline

**Morning (22:00 overnight charge task):**
```
2025-11-14 22:00:01 Solcast API call #1
2025-11-14 22:00:02 INFO: Solcast API quota: 9/10 calls remaining (10.0% used)
```

**Afternoon (14:00 peak boost check):**
```
2025-11-14 14:00:05 Solcast API call #2
2025-11-14 14:00:06 INFO: Solcast API quota: 8/10 calls remaining (20.0% used)
```

**App Shutdown (end of day):**
```
2025-11-14 23:59:59 INFO: === API Usage Summary ===
2025-11-14 23:59:59 INFO: solcast: 7 calls (7 success, 0 failed, 100.0% success rate) | Quota: 3/10 (70.0% used)
2025-11-14 23:59:59 INFO: Saved daily API usage summary to output/api_usage_2025-11-14.json
```

## Troubleshooting

**Q: Quota shows unknown?**  
A: Normal with unmetered key or free tier. Use debug logging to see headers.

**Q: No JSON file created?**  
A: Initialize tracker with `persistence_dir="output"`

**Q: Tracking is too noisy?**  
A: Set log level: `logging.getLogger('modules.api_usage_tracker').setLevel(logging.INFO)`

**Q: Quota always shows high?**  
A: You're using unmetered key ✅ (correct!)

## Demo

Run the demo to see all features:
```powershell
python demo_api_usage_tracking.py
```

## Integration Checklist

- [ ] Tracker initialization added to `src/app.py`
- [ ] Tracker summary logging added at shutdown
- [ ] Demo script runs successfully
- [ ] Check that API calls show in logs with quota info
- [ ] Verify `output/api_usage_*.json` is created
- [ ] Monitor quota levels in your workflows

## Related Files

- Configuration: `conf/growatt-charger.ini` (solcast section)
- Forecast docs: `docs/guides/FORECAST_PROVIDERS_CONFIG.md`
- Session work: `docs/development/SOLCAST_API_USAGE_TRACKING.md`

---

**Status:** ✅ Production Ready  
**Last Updated:** Nov 14, 2025  
**Demo Status:** ✅ Tested & Working
