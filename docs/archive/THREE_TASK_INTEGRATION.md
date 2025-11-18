# Three-Task Daily Cycle: Integration Guide

## Overview

The Growatt Weather-Based Charger now runs three coordinated daily tasks:

| Time  | Task | Purpose | Entry Point | Logic Module |
|-------|------|---------|-------------|--------------|
| 22:00 | Overnight Charging | Set battery target & rate for overnight use | `growatt_charger.py` | `src/app.py` |
| 05:00 | Morning SOC Check | Capture actual overnight SOC drop | `morning_soc_check.py` | Standalone |
| 14:00 | Peak-Window Boost | Decide if battery needs boost for 16:00-19:00 peak rates | `afternoon_peak_check.py` | `src/app_afternoon_peak_check.py` |

## Daily Execution Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DAILY CYCLE (24 HOURS)                            │
└─────────────────────────────────────────────────────────────────────────────┘

Day 1 Evening:
  22:00 ──────────────────────────────────────────────────────────────────────
    • Check weather forecast for next 12 hours
    • Calculate target SOC needed for night (min to max) + morning usage
    • Set battery charge target & rate
    • START OVERNIGHT CHARGING

Day 2 Morning:
  04:00-05:00 ───────────────────────────────────────────────────────────────
    • Actual overnight discharge happens naturally
    • Actual solar generation during morning (6:00-11:00)

  05:00 ──────────────────────────────────────────────────────────────────────
    • CAPTURE MORNING SOC
    • Record: [Date], [SOC%], [Forecast], [Actual Generation]
    • Use for accuracy tracking

Day 2 Daytime:
  11:00-13:00 ────────────────────────────────────────────────────────────────
    • Battery naturally charges from daytime solar
    • Evening forecast becomes more accurate

  14:00 ──────────────────────────────────────────────────────────────────────
    • Check remaining forecast (now to sunset, ~4-6 hours)
    • Check current SOC (after daytime solar boost)
    • Decide: Is boost needed for 16:00-19:00 peak?
    • IF YES: Set aggressive charge (80%, target SOC calculated for peak window)
    • IF NO: Leave battery alone, let solar continue naturally

Day 2 Evening:
  16:00-19:00 ────────────────────────────────────────────────────────────────
    • PEAK PRICING WINDOW (high utility rates)
    • Battery supplies power instead of grid (if boost was applied)
    • OR: Uses daytime solar generation (if no boost was needed)

  22:00 ──────────────────────────────────────────────────────────────────────
    • CYCLE REPEATS for Day 3 overnight
    • New forecast gathered
    • New target SOC calculated
    • New overnight charging schedule begins

└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow & Decision Dependencies

### 22:00 Task (Overnight Charging)
**Input**:
- Tomorrow's weather forecast (from Solcast, Forecast.Solar, or other provider)
- Configured battery parameters (capacity, min/max SOC)
- Current battery level (at 22:00)

**Processing** (in `src/app.py`):
1. Load configuration & connect to Growatt API
2. Fetch today's weather forecast from primary provider
3. Get current device status (SOC, temperatures, etc.)
4. Calculate target SOC using `modules/forecast.py`:
   - `get_scaled_soc_target()` returns % based on forecast amount
   - Example: 3kWh forecast → 95% target, 15kWh → 50%, 32kWh → 30%
5. Calculate charge rate needed to reach target by morning
6. Apply settings to battery (if enabled)
7. Log decision to `output/predictions.csv`: [Date, Time, Forecast_Wh, Target_SOC, Charge_Rate]

**Output**:
- Battery target SOC set (e.g., 95%)
- Charge rate set (e.g., 60%)
- 22:00-05:00: Battery charges to target under solar/grid, respects max rate
- Logged: `predictions.csv` for later accuracy checking

---

### 05:00 Task (Morning SOC Check)
**Input**:
- Current battery SOC at 05:00
- Previously logged prediction from 22:00 task
- Today's partial actual solar generation (partially captured)

**Processing** (in `morning_soc_check.py`):
1. Get current battery SOC from Growatt API
2. Read yesterday's prediction from `predictions.csv`
3. Calculate overnight discharge = (SOC at 22:00) - (SOC at 05:00)
4. Estimate morning solar (05:00-14:00) from available data
5. Log actual morning state to `output/actuals.csv`

**Output**:
- Morning SOC logged: `actuals.csv`
- Data used for accuracy analysis
- Decision quality metrics stored for later tuning

**Feedback Loop to 22:00 Task**:
- `analyze_thresholds.py` reads 22:00 predictions + 05:00 actuals
- Calculates forecast accuracy, charge efficiency, evening SOC
- Outputs tuning recommendations
- User reviews and adjusts SOC thresholds in `modules/forecast.py` if needed

---

### 14:00 Task (Peak-Window Boost) — NEW
**Input**:
- Remaining forecast from now (14:00) to sunset (~18:00)
- Current battery SOC at 14:00 (after morning solar boost + daytime charging)
- Average daytime load (e.g., 850W)

**Processing** (in `src/app_afternoon_peak_check.py`):
1. Load configuration & connect to Growatt API
2. Fetch today's weather forecast from primary provider
3. Get current device status (SOC at 14:00)
4. Use `modules/peak_window_boost.py` to decide:
   - Peak consumption in 16:00-19:00 window = 850W × 3h = 2.55 kWh
   - Estimate peak generation from remaining forecast
   - If shortfall > battery headroom: **BOOST**
   - If sufficient: **NO BOOST**
5. If boosting: set charge target SOC & 80% rate until 16:00
6. Log decision to `output/peak_decisions.csv`: [Date, SOC, Forecast, Decision, Reason]

**Output**:
- Battery optionally boosted (high charge rate 14:00-16:00)
- Logged: `peak_decisions.csv` for analysis
- Ready for 16:00-19:00 peak window

**Feedback Loop to 22:00 Task**:
- `review_peak_decisions.py` reads peak decisions + actuals
- Calculates boost effectiveness, accuracy metrics
- Outputs recommendations for 22:00 thresholds
- User reviews and adjusts if needed

---

## Configuration & Tuning Workflow

### Initial Setup (One Time)
```powershell
# Register all three tasks in Windows Task Scheduler
.\create_growatt_charger_daily_task.ps1        # 22:00 task
.\create_morning_soc_task.ps1                   # 05:00 task
.\create_afternoon_peak_check_task.ps1          # 14:00 task (NEW)
```

### Weekly Tuning Process (After 7+ Days of Data)

1. **Analyze overnight accuracy** (22:00 task effectiveness):
   ```powershell
   python analyze_thresholds.py
   ```
   Output: Forecast accuracy, evening SOC, charge efficiency by range

   → Review "Recommendations" section
   → If many days with critical low SOC: increase thresholds in `modules/forecast.py`
   → If many days with wasted charge: decrease thresholds

2. **Analyze peak boost effectiveness** (14:00 task effectiveness):
   ```powershell
   python review_peak_decisions.py
   ```
   Output: Boost rate by forecast range, average SOC at decision, effectiveness

   → Review boost rates by forecast range
   → If too many boosts for sunny days: increase shortfall threshold in `modules/peak_window_boost.py`
   → If not enough boosts for cloudy days: decrease threshold

3. **Adjust thresholds as needed**:
   - `modules/forecast.py` → `get_scaled_soc_target()` tiers
   - `modules/forecast_thresholds.py` → Forecast-based tiers (alternative)
   - `modules/peak_window_boost.py` → Peak shortfall thresholds

### Emergency Adjustments (If Critical Issues)

**Overnight charging not sufficient** (battery dies overnight):
- Increase minimum overnight target SOC
- Add 10% to the 22:00 target calculation
- Temporarily edit `modules/forecast.py` line: `minimum_charge_pct = 50` → `60`

**Too much daytime boost** (wasting solar):
- Reduce peak boost trigger threshold
- Edit `modules/peak_window_boost.py`: `PEAK_SHORTFALL_THRESHOLD = 0.15` → `0.20`

**Peak window not covered** (using grid during peak):
- 14:00 task not running or API connection failing
- Check logs: `type logs\afternoon-peak-check.log`
- Manually run: `python afternoon_peak_check.py conf\growatt-charger.ini`

---

## Key Files by Task

### 22:00 Overnight Task
```
growatt_charger.py                              # Entry wrapper
src/app.py                                      # Main logic
modules/forecast.py                             # SOC calculation
modules/forecast_providers/                     # Weather forecasts
modules/data_logger.py                          # CSV logging
output/predictions.csv                          # Logged decisions
logs/growatt-charger.log                        # Execution log
```

### 05:00 Morning Task
```
morning_soc_check.py                            # Standalone script
output/actuals.csv                              # Logged morning SOC
logs/morning-soc-check.log                      # Execution log
```

### 14:00 Afternoon Task
```
afternoon_peak_check.py                         # Entry wrapper
src/app_afternoon_peak_check.py                 # Main logic
modules/peak_window_boost.py                    # Boost decision logic
output/peak_decisions.csv                       # Logged decisions
logs/afternoon-peak-check.log                   # Execution log
```

### Analysis & Review Tools
```
analyze_thresholds.py                           # 22:00 effectiveness analysis
review_peak_decisions.py                        # 14:00 effectiveness analysis (NEW)
output/peak_decisions_analysis.csv              # Analysis export (NEW)
```

---

## Typical Week Overview

### Day 1 (Very Cloudy, 2 kWh forecast)
```
22:00: Forecast 2kWh → Target SOC 95% (low generation expected)
05:00: Morning SOC 45% (charged well overnight from grid)
14:00: Remaining forecast low → Decision: BOOST (ensure peak coverage)
16:00-19:00: Battery supplies most power (peak rates avoided)
```

### Day 2 (Partly Cloudy, 8 kWh forecast)
```
22:00: Forecast 8kWh → Target SOC 75% (moderate generation expected)
05:00: Morning SOC 68% (charged partially, not forced to max)
14:00: Remaining forecast adequate → Decision: NO BOOST (natural solar continues)
16:00-19:00: Natural solar + battery covers most peak consumption
```

### Day 3 (Sunny, 32 kWh forecast)
```
22:00: Forecast 32kWh → Target SOC 30% (high generation expected)
05:00: Morning SOC 32% (barely charged, preserves battery for peak)
14:00: Remaining forecast very high → Decision: NO BOOST (overkill)
16:00-19:00: Abundant solar, battery stays above 50% all evening
```

---

## Debugging & Monitoring

### Check All Three Tasks Running
```powershell
Get-ScheduledTask -TaskName "GrowattChargerDaily" | Select State, LastRunTime
Get-ScheduledTask -TaskName "MorningSocCheck" | Select State, LastRunTime
Get-ScheduledTask -TaskName "GrowattAfternoonPeakCheck" | Select State, LastRunTime
```

### View Recent Logs
```powershell
# 22:00 task log
Get-Content logs\growatt-charger.log -Tail 50

# 05:00 task log
Get-Content logs\morning-soc-check.log -Tail 50

# 14:00 task log
Get-Content logs\afternoon-peak-check.log -Tail 50
```

### Manually Trigger a Task
```powershell
Start-ScheduledTask -TaskName "GrowattAfternoonPeakCheck"
Start-ScheduledTask -TaskName "MorningSocCheck"
Start-ScheduledTask -TaskName "GrowattChargerDaily"
```

### Verify CSV Data Updates
```powershell
# Check latest 22:00 decision
Get-Content output\predictions.csv -Tail 1

# Check latest morning reading
Get-Content output\actuals.csv -Tail 1

# Check latest 14:00 decision
Get-Content output\peak_decisions.csv -Tail 1
```

---

## Performance Summary

| Metric | 22:00 Task | 05:00 Task | 14:00 Task |
|--------|-----------|-----------|-----------|
| Runtime | ~10-15s | ~5-10s | ~5-10s |
| API Calls | 4-5 | 2 | 4-5 |
| Disk I/O | ~2KB CSV | ~2KB CSV | ~2KB CSV |
| Battery Impact | High (boost) | None | Medium (optional boost) |
| Monthly Cost (API) | <$5 | <$2 | <$3 |

---

## Next Steps

1. **Register all three tasks**: Run the `.ps1` scripts as Administrator
2. **Wait 7 days**: Let all three tasks run through a full week
3. **Analyze results**:
   - Run `analyze_thresholds.py`
   - Run `review_peak_decisions.py`
4. **Adjust thresholds**: Based on recommendations
5. **Repeat monthly**: As seasons change (Jan vs Jul forecasts very different)

---

**Created**: 2024-11-15  
**Feature**: Three-task daily cycle integration  
**Status**: Ready for deployment
