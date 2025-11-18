# Quick Reference: View Solcast API Usage

## Easiest Way (Copy-Paste Ready)

```powershell
# View today's summary
python view_api_usage_summaries.py

# View 7-day trend
python view_api_usage_summaries.py --trends

# View all available dates
python view_api_usage_summaries.py --all

# View raw JSON
python -m json.tool output\api_usage_2025-11-15.json
```

## Where to Look

| Data | Location | Command |
|------|----------|---------|
| **Daily Summaries** | `output/api_usage_YYYY-MM-DD.json` | `python view_api_usage_summaries.py` |
| **Real-time Logs** | `logs/growatt-charger.log` | `Select-String "quota" logs\*.log` |
| **Peak Check Logs** | `logs/afternoon-peak-check.log` | `tail -f logs/afternoon-peak-check.log` |
| **7-Day Trends** | Multiple JSON files | `python view_api_usage_summaries.py --trends` |

## What Each Shows

### `python view_api_usage_summaries.py`
Shows today's summary:
- Total API calls
- Success/failure rate
- Quota remaining vs. limit
- Alert status (🔴 CRITICAL, 🟠 WARNING, 🟡 CAUTION, ✅ OK)

### `python view_api_usage_summaries.py --trends`
Shows 7-day trend:
- Daily API call counts
- Success rates per day
- Quota progression
- Days until quota exhaustion

### `logs/growatt-charger.log`
Real-time quota warnings:
```
2025-11-15 22:00:15 DEBUG: Solcast API quota: 9/10 calls remaining
2025-11-15 22:00:15 INFO: Charge plan calculated - Forecast...
```

### `output/api_usage_2025-11-15.json`
Raw data (JSON format):
```json
{
  "total_calls": 2,
  "successful_calls": 2,
  "quota_remaining": 8,
  "quota_limit": 10
}
```

## When Data is Created

| Time | App | Data File |
|------|-----|-----------|
| 22:00 | `src/app.py` | `api_usage_YYYY-MM-DD.json` (created/updated) |
| 14:00 | `src/app_afternoon_peak_check.py` | `api_usage_YYYY-MM-DD.json` (appended) |

## Typical Output Example

```powershell
> python view_api_usage_summaries.py

======================================================================
API Usage Summary: 2025-11-15
Recorded: 2025-11-15T22:00:15.123456
======================================================================

📊 Provider: SOLCAST
   Total API calls:      2
   Successful:           2
   Failed:               0
   Success rate:         100.0%
   Quota remaining:      8/10
   Quota used:           2/10 (20.0%)
   Status:               ✅ OK
   Last quota check:     2025-11-15T22:00:15.123456
```

## Alerts You Might See

```
🔴 CRITICAL - Quota exhausted! No API calls remaining.
🟠 WARNING  - Only 1 call remaining!
🟡 CAUTION  - 5 calls remaining (50% quota used)
✅ OK       - Quota status normal
```

## Troubleshooting Quick Fixes

### "No data for today"
- Your scheduled tasks haven't run yet
- Next run at 22:00 or 14:00
- Or run manually: `python -m src.app conf/growatt-charger.ini`

### "File not found: api_usage_2025-11-15.json"
- App hasn't run yet (it creates the file)
- Check `output/` directory exists
- Verify app ran successfully in logs

### "JSON file shows no data"
- Wait for next app run
- Check logs for errors during forecast fetch

## Commands by Use Case

**I want to see current quota:**
```powershell
python view_api_usage_summaries.py
```

**I want to see if I'm getting low on quota:**
```powershell
python view_api_usage_summaries.py --trends
```

**I want to see all dates available:**
```powershell
python view_api_usage_summaries.py --all
```

**I want to see quota warnings in real-time:**
```powershell
Get-Content logs/afternoon-peak-check.log -Tail 20
```

**I want the raw data:**
```powershell
python -m json.tool output\api_usage_2025-11-15.json | more
```

**I want to see today's logs:**
```powershell
Select-String "Solcast\|quota" logs/growatt-charger.log
```

## Data Format

### JSON File Structure
```json
{
  "date": "2025-11-15",
  "timestamp": "2025-11-15T22:00:15.123456",
  "providers": {
    "solcast": {
      "total_calls": 2,
      "successful_calls": 2,
      "failed_calls": 0,
      "quota_remaining": 8,
      "quota_limit": 10,
      "last_quota_check": "2025-11-15T22:00:15.123456",
      "errors": []
    }
  }
}
```

## With Unmetered Key

Your quota will show as:
- `quota_remaining: 999999`
- `quota_limit: 999999`
- Status: ✅ OK (unlimited)

This is **correct** - unlimited means no quota concerns!

## Next Check Point

After your next scheduled run (22:00 or 14:00):
```powershell
python view_api_usage_summaries.py
```

You'll see your first real API usage recorded!
