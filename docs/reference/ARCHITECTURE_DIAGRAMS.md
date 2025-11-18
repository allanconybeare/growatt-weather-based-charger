# Architecture: Forecast Fallback & Schedule Slots

## Forecast Retrieval Flowchart (14:00 Check)

```
┌─────────────────────────────────┐
│  14:00 Afternoon Peak Check     │
│  _get_remaining_forecast()      │
└──────────────┬──────────────────┘
               │
               ▼
         ┌─────────────┐
         │ Try Tier 1: │
         │   Solcast   │
         └─────┬───────┘
               │
        ┌──────┴──────┐
        │             │
    Success       Failure
        │             │
        ▼             ▼
    Return     ┌─────────────────┐
    (Wh,       │ Try Tier 2:     │
    "solcast") │ Forecast.Solar  │
               └─────┬───────────┘
                     │
              ┌──────┴──────┐
              │             │
          Success       Failure
              │             │
              ▼             ▼
          Return      ┌──────────────────┐
          (Wh,        │ Try Tier 3:      │
          "forecast.  │ predictions.csv  │
           solar")    │ (yesterday's     │
                      │  forecast)       │
                      └─────┬────────────┘
                            │
                     ┌──────┴──────┐
                     │             │
                 Success       Failure
                     │             │
                     ▼             ▼
                 Return      ┌──────────────────┐
                 (Wh,        │ Tier 4: Default  │
                 "predictions│ Conservative     │
                 .csv")      │ Estimate (3kWh)  │
                             └─────┬────────────┘
                                   │
                                   ▼
                            Return (3000,
                            "conservative_
                             estimate")

                            (NEVER FAILS)
```

---

## Schedule Slot Architecture

```
GROWATT BATTERY - 3 INDEPENDENT CHARGING SCHEDULES
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Param1-2: Charge Rate %, Target SOC % (applies to all slots)  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SLOT 0: Off-Peak Charging (22:00 Task)                        │
│  ├─ Set by: src/app.py at 22:00 every night                   │
│  ├─ Params: param3-7 (start_hr, start_min, end_hr, end_min, en)
│  ├─ Typical: 02:00-05:00 (off-peak hours)                     │
│  ├─ Status: ENABLED (1)                                        │
│  ├─ Target: 85% SOC (based on forecast)                        │
│  └─ Purpose: Prepare battery for overnight consumption          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SLOT 1: Afternoon Boost (14:00 Task) ← NEW                   │
│  ├─ Set by: src/app_afternoon_peak_check.py at 14:00          │
│  ├─ Params: param8-12 (start_hr, start_min, end_hr, end_min, en)
│  ├─ Typical: 14:00-16:00 (before peak window)                 │
│  ├─ Status: ENABLED (1) if boost needed, else DISABLED (0)    │
│  ├─ Target: Calculated to cover peak shortfall                 │
│  └─ Purpose: Boost battery before 16:00-19:00 peak rates       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SLOT 2: Reserved for Future (Not Used Currently)              │
│  ├─ Set by: Reserved for future features                       │
│  ├─ Params: param13-17                                         │
│  ├─ Status: DISABLED (0)                                        │
│  └─ Purpose: Free power events, manual schedules, etc.         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

KEY INSIGHT: Both Slot 0 and Slot 1 can be ACTIVE SIMULTANEOUSLY
             without conflict because they operate on different times:

             Slot 0: 02:00-05:00 (night)
             Slot 1: 14:00-16:00 (afternoon)

             No overlap → No conflicts → Independent control
```

---

## Daily Timeline With New Feature

```
DAY N-1 EVENING
22:00 ┌──────────────────────────────────────────────────┐
      │ OVERNIGHT CHARGING TASK (src/app.py)             │
      │ 1. Get forecast for tomorrow                      │
      │ 2. Calculate target SOC based on forecast         │
      │ 3. Update SLOT 0 (02:00-05:00)                   │
      │    └─ Sets: charge rate, target SOC             │
      └──────────────────────────────────────────────────┘

      Overnight charging begins when sun goes down

DAY N MORNING
05:00 ┌──────────────────────────────────────────────────┐
      │ MORNING SOC CHECK (morning_soc_check.py)         │
      │ 1. Capture actual overnight drop                 │
      │ 2. Log to actuals.csv                            │
      │ 3. Used for accuracy tracking                    │
      └──────────────────────────────────────────────────┘

      Daytime: Solar charges battery naturally

DAY N AFTERNOON
14:00 ┌──────────────────────────────────────────────────┐
      │ PEAK WINDOW BOOST DECISION (app_afternoon_peak_  │
      │                            check.py) ← NEW       │
      │ 1. Get remaining forecast (14:00 to sunset)     │
      │    ├─ Try Solcast (primary)                      │
      │    ├─ Fallback to Forecast.Solar                │
      │    ├─ Fallback to predictions.csv                │
      │    └─ Fallback to 3kWh conservative              │
      │ 2. Read current SOC                              │
      │ 3. Calculate: Peak consumption - peak generation │
      │ 4. Decision: Boost needed?                       │
      │ 5. If YES: Update SLOT 1 (14:00-16:00)          │
      │    └─ Sets: charge rate 80%, target SOC 68-85%  │
      │ 6. Log decision to peak_decisions.csv            │
      └──────────────────────────────────────────────────┘

      14:00-16:00: Aggressive charging (if boost enabled)
      16:00-19:00: Peak pricing window (use battery/solar)

REPEAT NEXT DAY
```

---

## API Method Structure

```
OLD (Before):
╔═══════════════════════════════════════╗
║  update_charge_settings()             ║
║  └─ Always updates SLOT 0 only        ║
║  └─ Problem: No multi-slot support    ║
╚═══════════════════════════════════════╝

NEW (After):
╔═══════════════════════════════════════╗
║  update_charge_settings_with_slot()   ║
║  ├─ Slot 0: Off-peak (22:00 task)    ║
║  ├─ Slot 1: Boost (14:00 task) ← NEW ║
║  ├─ Slot 2: Reserved                  ║
║  └─ Feature: Independent scheduling   ║
╚═══════════════════════════════════════╝

Both methods available:
- Old method still works (backward compat)
- New method used for 14:00 task
- Can coexist without issues
```

---

## Parameter Mapping

```
API Call: update_ac_inverter_setting(device_sn, 'spa_ac_charge_time_period', params)

params = {
    'param1': '80',          ← Charge Rate (%)
    'param2': '68',          ← Stop SOC (%)

    # SLOT 0 (Off-peak overnight)
    'param3': '02',          ← Start Hour
    'param4': '00',          ← Start Minute
    'param5': '05',          ← End Hour
    'param6': '00',          ← End Minute
    'param7': '1',           ← Enable (1=yes, 0=no)

    # SLOT 1 (Afternoon boost) ← NEW
    'param8': '14',          ← Start Hour
    'param9': '00',          ← Start Minute
    'param10': '16',         ← End Hour
    'param11': '00',         ← End Minute
    'param12': '1',          ← Enable (1=yes, 0=no)

    # SLOT 2 (Reserved)
    'param13': '00',         ← Start Hour
    'param14': '00',         ← Start Minute
    'param15': '00',         ← End Hour
    'param16': '00',         ← End Minute
    'param17': '0',          ← Enable (1=yes, 0=no)
}

When multiple slots are enabled:
- Battery uses the first matching schedule
- If 14:00 is in SLOT 1 range: Use SLOT 1 settings
- If 02:00 is in SLOT 0 range: Use SLOT 0 settings
- Never conflict (different times)
```

---

## Forecast Source Tracking

```
peak_decisions.csv columns (new "Forecast Source"):

┌────────┬──────┬───────────────────────────────────────┐
│ Date   │ Time │ Forecast Source                       │
├────────┼──────┼───────────────────────────────────────┤
│ 11-14  │ 14:00│ solcast                               │
│ 11-15  │ 14:00│ forecast.solar (fallback)             │
│ 11-16  │ 14:00│ predictions.csv (fallback)            │
│ 11-17  │ 14:00│ conservative_estimate                 │
│ 11-18  │ 14:00│ solcast                               │
└────────┴──────┴───────────────────────────────────────┘

Analysis:
- If most entries are "solcast" → Primary provider working well
- If many "forecast.solar (fallback)" → Primary provider issues
- If "predictions.csv (fallback)" appears → All live APIs failed
- If "conservative_estimate" appears → System was offline/blocked

Tells you:
1. Which provider was used
2. When fallbacks were needed
3. If there are API reliability issues
4. Overall system health
```

---

## Error Recovery Flowchart

```
┌─────────────────────────┐
│  14:00 Check Starts     │
└────────────┬────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Try Solcast API    │
    └────────┬───────────┘
             │
        ┌────┴────┐
        │         │
       YES       NO
        │         │
        ▼         ▼
   SUCCESS    WARN LOG
              │
              ▼
      ┌────────────────────┐
      │ Try Forecast.Solar │
      └────────┬───────────┘
               │
          ┌────┴────┐
          │         │
         YES       NO
          │         │
          ▼         ▼
       SUCCESS    WARN LOG
                  │
                  ▼
        ┌─────────────────────┐
        │ Try predictions.csv │
        └────────┬─────────────┘
                 │
            ┌────┴────┐
            │         │
           YES       NO
            │         │
            ▼         ▼
         SUCCESS    WARN LOG
                    │
                    ▼
        ┌─────────────────────────┐
        │ Use Conservative Est.   │
        │ (3 kWh, safe default)   │
        └─────┬───────────────────┘
              │
              ▼
        ┌─────────────────┐
        │ Decision Made   │
        │ (Never Failed)  │
        └─────────────────┘

Key: System ALWAYS completes with valid forecast
     No blocking or failures even if all APIs down
```

---

## Comparison: Before vs After

```
BEFORE (14:00 Check):
┌──────────────┐
│ Try Solcast  │
└──────┬───────┘
       │
    ┌──┴──┐
    │     │
  YES    NO
    │     │
    ▼     ▼
  Use   FAIL
  It    │
        ▼
     Error

Problem: If Solcast rate-limited, task fails
Result: No boost decision made at critical time

AFTER (14:00 Check):
┌──────────────┐
│ Try Solcast  │
└──────┬───────┘
       │
    ┌──┴──┐
    │     │
  YES    NO
    ▼     ▼
  Use   Try Forecast.Solar
  It      │
       ┌──┴──┐
       │     │
      YES    NO
       ▼     ▼
      Use   Try predictions.csv
      It      │
           ┌──┴──┐
           │     │
          YES    NO
           ▼     ▼
          Use   Use Conservative
          It  
              │
              ▼
            (3 kWh safe)

Result: Decision ALWAYS made, resilient to failures
```

---

## Key Benefits Summary

```
FORECAST FALLBACK CHAIN:
✅ Never blocked by Solcast rate limit
✅ Automatic fallback to secondary provider
✅ Emergency fallback to historical data
✅ Conservative estimate safety net
✅ Decision ALWAYS made (never fails)

SLOT MANAGEMENT:
✅ Independent scheduling (no conflicts)
✅ Preserve off-peak charging (slot 0)
✅ Afternoon boost isolated (slot 1)
✅ Reserve for future features (slot 2)
✅ User can manually edit slot 0 without 14:00 interference

DATA TRACKING:
✅ Forecast source logged (diagnostics)
✅ Can analyze provider reliability
✅ Detect when fallbacks are used
✅ Improve system based on patterns
```

---

**Architecture**: Resilient forecast + multi-slot independent scheduling  
**Status**: ✅ READY
