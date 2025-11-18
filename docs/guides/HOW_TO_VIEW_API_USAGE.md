# How to View Solcast API Usage Data

Now that the tracker has been integrated into your apps, here's where to find your Solcast API usage:

## Quick View (Easiest)

### View Today's Summary
```powershell
python view_api_usage_summaries.py
```

Output shows:
- Total API calls made
- Success/failure rate
- Quota remaining vs. limit
- Percentage of quota used
- Alert status (CRITICAL/WARNING/CAUTION/OK)

### View All Available Dates
```powershell
python view_api_usage_summaries.py --all
```

Lists all daily summaries available.

### View 7-Day Trends
```powershell
python view_api_usage_summaries.py --trends
```

Shows:
- API calls per day
- Success rates
- Quota remaining for each day
- Predictions of when quota will exhaust

## Where the Data is Stored

### JSON Files (Raw Data)
Location: `output/api_usage_YYYY-MM-DD.json`

Example: `output/api_usage_2025-11-15.json`

View with:
```powershell
cat output\api_usage_2025-11-15.json | ConvertFrom-Json | Format-List
```

Or pretty-print:
```powershell
python -m json.tool output\api_usage_2025-11-15.json
```

### Log Files (Real-Time Warnings)
Location: `logs/growatt-charger.log` and `logs/afternoon-peak-check.log`

Grep for quota warnings:
```powershell
Select-String "Solcast API quota" logs\*.log
Select-String "WARNING.*quota" logs\*.log
```

## What Gets Recorded

For each day, the JSON file contains:

```json
{
  "date": "2025-11-15",
  "timestamp": "2025-11-15T22:00:15.123456",
  "providers": {
    "solcast": {
      "total_calls": 2,           ← API calls made today
      "successful_calls": 2,      ← How many succeeded
      "failed_calls": 0,          ← How many failed
      "quota_remaining": 8,       ← Calls left today
      "quota_limit": 10,          ← Daily limit
      "last_quota_check": "ISO timestamp",
      "last_call_time": "datetime",
      "errors": []                ← Any error details
    }
  }
}
```

## When Data is Created

✅ **22:00 (Overnight Charge Task)**
- `src/app.py` runs
- Gets forecast for tomorrow
- Records 1 API call
- Updates `output/api_usage_YYYY-MM-DD.json`

✅ **14:00 (Afternoon Peak Check)**
- `src/app_afternoon_peak_check.py` runs
- Gets remaining forecast
- Records 1 API call
- Updates `output/api_usage_YYYY-MM-DD.json`

So you should see 1-2 API calls recorded per day (more if apps run multiple times).

## Example Output

### From view_api_usage_summaries.py:

```
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

### For a low quota scenario:

```
   Quota remaining:      2/10
   Quota used:           8/10 (80.0%)
   Status:               🟠 WARNING - Only 2 calls left!
```

## Monitoring Your Usage Over Time

```powershell
# View last 7 days of usage
python view_api_usage_summaries.py --trends

# Output includes:
# - Daily call counts
# - Success rates  
# - Quota tracking
# - Days until quota exhaustion at current usage rate
```

## What to Expect

### With Unmetered Key (Your Current Setup)
- Quota shows as 999999/999999 (unlimited)
- No quota concerns
- All API calls succeed

### With Free Tier Key
- Quota: 10 calls per day
- Reset: Daily at UTC 00:00
- Alerts at: 5 calls (CAUTION), 2 calls (WARNING), 0 calls (CRITICAL)

### Typical Daily Pattern
```
22:00 - Overnight charge task: 1 API call
14:00 - Peak window check: 1 API call
Total: ~2 API calls/day
```

At 2 calls/day with 10-call limit, you're using 20% of daily quota ✅

## Troubleshooting

### "No data for today"
- Run one of your scheduled tasks (22:00 or 14:00)
- Check that apps ran successfully in logs
- Try running manually: `python -m src.app conf/growatt-charger.ini`

### "Quota shows unknown"
- This is normal with some API responses
- Check logs for detailed quota info
- Enable debug logging for more details

### "JSON file not created"
- Make sure `output/` directory exists
- Check app logs for errors
- Verify tracker initialization in code

## Next Steps

1. **Run the next scheduled task** (22:00 or 14:00)
2. **Check the JSON file** with: `python view_api_usage_summaries.py`
3. **Monitor trends** with: `python view_api_usage_summaries.py --trends`
4. **Set up alerts** if quota gets low (can be added to tasks)

## Integration Status

✅ `src/app.py` - Tracker integrated, records API calls at 22:00
✅ `src/app_afternoon_peak_check.py` - Tracker integrated, records API calls at 14:00  
✅ Demo script - `demo_api_usage_tracking.py` for testing
✅ View tool - `view_api_usage_summaries.py` to analyze data

**You're all set!** Just run your scheduled tasks and check the output files.
