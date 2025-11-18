# Peak Window Configuration Guide

**Date**: November 14, 2025  
**Feature**: Configurable afternoon peak-window checking  
**Status**: ✅ Implemented and validated

---

## Overview

The peak window feature allows you to configure when your electricity grid has high import rates (typically afternoon peak hours). The system checks at a configurable time whether battery boost is needed to avoid drawing from the grid during these expensive rates.

**Default Configuration**:
- **Peak window**: 16:00–19:00 (3 hours)
- **Check time**: 14:00 (2 hours before peak starts)
- **Forecast reliability**: 40% (conservative)
- **SOC safety margin**: 10% (conservative buffer)

---

## Configuration Structure

### Three Key Components to Align

```
┌─────────────────────────────────────────────────────────────────┐
│  SCHEDULED TASK (When to run)                                   │
│  └─ Should match check_time in [peak_window] section             │
│     Example: Task scheduled for 14:00                           │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│  CONFIGURATION FILE (Settings)                                   │
│  └─ [peak_window] section with times and parameters             │
│     ├─ check_time = 14:00                                       │
│     ├─ peak_start_time = 16:00                                  │
│     ├─ peak_end_time = 19:00                                    │
│     ├─ forecast_reliability = 0.4                               │
│     └─ soc_safety_margin_pct = 10.0                             │
└─────────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────┐
│  CHARGING WINDOW (Not conflicting)                               │
│  └─ [tariff] section off-peak times                             │
│     ├─ off_peak_start_time = 02:00                              │
│     └─ off_peak_end_time = 04:59                                │
│        (Used for overnight charging, different from peak)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration File: [peak_window] Section

### Location
File: `conf/growatt-charger.ini`  
Section: `[peak_window]`

### Settings

#### 1. `peak_start_time` (Required)
**When grid rates become expensive**

```ini
peak_start_time = 16:00
```

- Format: `HH:MM` (24-hour)
- Range: 00:00 to 23:59
- Typical UK: 16:00 (afternoon peak)
- Typical AU: 15:00-21:00 (evening peak)

**Use Case**: If your electricity provider charges premium rates from 4 PM, set this to 16:00.

#### 2. `peak_end_time` (Required)
**When grid rates return to normal**

```ini
peak_end_time = 19:00
```

- Format: `HH:MM` (24-hour)
- Range: 00:00 to 23:59
- Must be > `peak_start_time`
- Typical duration: 2–4 hours

**Use Case**: If peak rates end at 7 PM, set this to 19:00.

#### 3. `check_time` (Required)
**When to run the afternoon peak check**

```ini
check_time = 14:00
```

- Format: `HH:MM` (24-hour)
- Range: 00:00 to 23:59
- Must be < `peak_start_time`
- Recommended: 2–3 hours before peak starts (leaves time for battery charging)

**Use Case**: If peak is 16:00–19:00, check at 14:00 gives 2 hours notice.

#### 4. `forecast_reliability` (Optional, default: 0.4)
**How much of the afternoon forecast will actually happen during peak**

```ini
forecast_reliability = 0.4
```

- Range: 0.0 to 1.0
- 0.4 = assume only 40% of afternoon forecast generates during peak
- **Lower values** = more conservative (requires higher boost)
- **Higher values** = less conservative (requires lower boost)

**Use Cases**:
- `0.3` – Very cloudy region, very conservative
- `0.4` – UK typical, conservative (default)
- `0.5` – Mixed cloud, moderate
- `0.6` – Sunny region, less conservative

**Why it exists**: The afternoon forecast is for hours until sunset (maybe 5-6 hours). But peak window is only 2-4 hours. Many clouds can appear in that time, so we discount the forecast.

#### 5. `soc_safety_margin_pct` (Optional, default: 10.0)
**Extra battery cushion above required minimum**

```ini
soc_safety_margin_pct = 10.0
```

- Range: 0.0 to 100.0
- Percentage points to add as safety buffer
- **Higher values** = require higher pre-peak SOC (more conservative)
- **Lower values** = require lower pre-peak SOC (less conservative)

**Use Cases**:
- `5.0` – Minimal margin (less boosting)
- `10.0` – Typical (default, balanced)
- `15.0` – High margin (more boosting)
- `20.0` – Very conservative (always well-protected)

**Why it exists**: Real consumption varies. The 10% buffer ensures you're unlikely to fall short during peak even if consumption is higher than expected.

---

## Complete Example Configurations

### Scenario 1: UK Octopus Energy (Peak 16:00–19:00)

```ini
[peak_window]
peak_start_time = 16:00
peak_end_time = 19:00
check_time = 14:00
forecast_reliability = 0.4
soc_safety_margin_pct = 10.0
```

**Explanation**:
- Checks at 14:00 if boost needed
- Peak rates 16:00–19:00 (3 hours)
- Conservative forecast (40% reliability)
- 10% safety cushion

### Scenario 2: Australian Evening Peak (17:00–21:00)

```ini
[peak_window]
peak_start_time = 17:00
peak_end_time = 21:00
check_time = 14:30
forecast_reliability = 0.5
soc_safety_margin_pct = 12.0
```

**Explanation**:
- Longer peak window (4 hours)
- Checks 2.5 hours before
- Less conservative (50% forecast reliability, sunnier)
- Slightly higher margin

### Scenario 3: Aggressive Optimization (Less Boosting)

```ini
[peak_window]
peak_start_time = 16:00
peak_end_time = 19:00
check_time = 14:00
forecast_reliability = 0.5
soc_safety_margin_pct = 5.0
```

**Explanation**:
- Higher forecast reliability (50%)
- Lower safety margin (5%)
- Result: Less frequent boosting
- Use if: You want to minimize use of expensive energy

### Scenario 4: Conservative (More Boosting)

```ini
[peak_window]
peak_start_time = 16:00
peak_end_time = 19:00
check_time = 14:00
forecast_reliability = 0.3
soc_safety_margin_pct = 15.0
```

**Explanation**:
- Lower forecast reliability (30%, very conservative)
- Higher safety margin (15%)
- Result: More frequent boosting
- Use if: You prioritize avoiding grid import regardless of cost

---

## Alignment Checklist

### 1. Configuration File ✓
- [ ] `[peak_window]` section exists in `conf/growatt-charger.ini`
- [ ] `peak_start_time` set to your peak rate start (e.g., 16:00)
- [ ] `peak_end_time` set to your peak rate end (e.g., 19:00)
- [ ] `check_time` set before peak (e.g., 14:00)
- [ ] `check_time` < `peak_start_time`
- [ ] `peak_start_time` < `peak_end_time`

### 2. Scheduled Task ✓
- [ ] Task scheduled to run at `check_time` (e.g., 14:00)
- [ ] Task runs `src/app_afternoon_peak_check.py`
- [ ] Task runs daily
- [ ] Task has access to config file

### 3. No Conflicts ✓
- [ ] Peak window (16:00–19:00) doesn't overlap off-peak (02:00–04:59)
- [ ] Check time (14:00) is before peak start (16:00)
- [ ] All times use same format (HH:MM)

### 4. Validation ✓
- [ ] Run `python test_peak_window_config.py conf/growatt-charger.ini`
- [ ] All checks pass (should show ✅ VALIDATION PASSED)

---

## Testing Your Configuration

### Validation Test

```bash
# Test that configuration is correct
python test_peak_window_config.py conf/growatt-charger.ini
```

**Expected output**: ✅ VALIDATION PASSED

### Manual Test (Without Actual Battery)

```bash
# Test the decision logic with sample values
python -c "
from modules.peak_window_boost import should_boost_battery_for_peak_window

# Example: 50% SOC, 6000Wh forecast
should_boost, reason, details = should_boost_battery_for_peak_window(
    remaining_forecast_wh=6000,
    current_soc=50,
    average_load_w=850
)

print(f'Boost decision: {should_boost}')
print(f'Reason: {reason}')
"
```

### Live Testing

1. **Tomorrow at check_time (e.g., 14:00)**:
   - Check logs: `tail -f logs/afternoon-peak-check.log`
   - Should see decision logged with config-based peak window

2. **Review output**:
   - Check `output/peak_decisions.csv`
   - Should have entry with correct peak window times

---

## How It All Works Together

### Daily Timeline

```
02:00–04:59    Off-peak charging (22:00 task, overnight)
    │
    │ Battery charges to 85% using off-peak rates
    │
    ├─ Uses [tariff] section config
    │  ├─ off_peak_start_time = 02:00
    │  └─ off_peak_end_time = 04:59
    │
    ↓
14:00          Peak-window check (NEW - afternoon boost decision)
    │
    │ Afternoon peak-check app runs
    │
    ├─ Uses [peak_window] section config
    │  ├─ check_time = 14:00 (when to run)
    │  ├─ peak_start_time = 16:00 (when rates get expensive)
    │  ├─ peak_end_time = 19:00 (when rates return to normal)
    │  ├─ forecast_reliability = 0.4 (how much forecast will actually occur)
    │  └─ soc_safety_margin_pct = 10.0 (safety cushion)
    │
    │ Decision: "Will battery (current SOC) handle 16:00–19:00?"
    │   └─ If NO: Boost to 80–85% before 16:00
    │   └─ If YES: Leave as-is
    │
    ↓
16:00–19:00    Peak rates (if boost needed, battery ready)
    │
    │ Battery powers house during peak
    │ Avoids expensive grid import
    │
    ↓
22:00          Overnight charging task (repeats)
    │
    └─ Back to step 1
```

---

## Parameter Impact Examples

### Example 1: Same Peak, Different Settings

**Scenario**: Peak 16:00–19:00, current SOC 50%, forecast 5000Wh

```
A) forecast_reliability = 0.3, margin = 10%
   └─ Boost needed? YES (conservative)

B) forecast_reliability = 0.4, margin = 10%
   └─ Boost needed? YES (default)

C) forecast_reliability = 0.5, margin = 10%
   └─ Boost needed? MAYBE (less conservative)

D) forecast_reliability = 0.5, margin = 5%
   └─ Boost needed? NO (aggressive optimization)
```

### Example 2: Adjusting for Your Energy Costs

If peak rates are 3× normal rates:
- Use `forecast_reliability = 0.3` (conservative, avoid peak import)
- Use `soc_safety_margin_pct = 15.0` (ensure battery works)

If peak rates are only 1.5× normal:
- Use `forecast_reliability = 0.5` (less conservative, okay to draw some)
- Use `soc_safety_margin_pct = 5.0` (minimal over-protection)

---

## Troubleshooting

### "Validation Failed"

Run: `python test_peak_window_config.py conf/growatt-charger.ini`

**Common issues**:
- Missing `[peak_window]` section in config
- Time format wrong (should be HH:MM)
- `check_time` >= `peak_start_time` (should be before)
- `peak_start_time` >= `peak_end_time` (should be before)

### Peak Check Not Running

**Check 1**: Is scheduled task running at `check_time`?
```bash
# Check scheduled task
Get-ScheduledTask | Select-Object TaskName, NextRunTime | grep -i peak
```

**Check 2**: Is config file readable?
```bash
python test_peak_window_config.py conf/growatt-charger.ini
```

### Peak Check Running But Decision Wrong

**Check**: Are your parameters reasonable?
```bash
python test_peak_window_config.py conf/growatt-charger.ini
```

Look at:
- Forecast reliability: Too low? Too high?
- Safety margin: Too high (boosting too much)? Too low (not protecting)?

---

## Configuration Reference

```ini
[peak_window]
# Peak window timing (when grid rates are high)
peak_start_time = 16:00    # When peak rates START
peak_end_time = 19:00      # When peak rates END

# Decision timing
check_time = 14:00         # When to CHECK if boost needed (must be before peak_start_time)

# Decision parameters
forecast_reliability = 0.4 # How much of forecast reaches peak (0.0-1.0, lower=conservative)
soc_safety_margin_pct = 10.0  # Extra battery cushion (0-100%, higher=conservative)
```

---

## Next Steps

1. ✅ Add `[peak_window]` section to your config (if not already there)
2. ✅ Set your peak window times (when rates are high)
3. ✅ Set your check time (2-3 hours before peak)
4. ✅ Adjust `forecast_reliability` and `soc_safety_margin_pct` for your needs
5. ✅ Run validation: `python test_peak_window_config.py conf/growatt-charger.ini`
6. ✅ Schedule task at `check_time` (if not already scheduled)
7. ✅ Monitor logs at `check_time` to see decisions

---

**Status**: ✅ Ready to use  
**Testing**: Run `python test_peak_window_config.py conf/growatt-charger.ini`  
**Next**: Wait for next `check_time` and check `logs/afternoon-peak-check.log`
