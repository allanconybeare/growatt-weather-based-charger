# Quick Reference: New Tools & Usage

## 1. Run Threshold Analyzer (Weekly)

**See how your thresholds are performing:**

```bash
cd c:\Users\acony\Development\growatt-weather-based-charger
python bin/analyze_thresholds.py
```

**Output:** Performance grouped by forecast range
```
Very Poor (0–8 kWh):    22 samples, 85% accuracy, 18.8% evening SOC
Poor (8–15 kWh):        10 samples, 68% accuracy, 18.8% evening SOC
Moderate (15–20 kWh):    3 samples, 46% accuracy, 35.0% evening SOC
```

**To save to CSV:**
```bash
python bin/analyze_thresholds.py --export
# Creates: output/threshold_analysis_report.csv
```

---

## 2. Test Forecast-Based Thresholds

**See what target SOC a given forecast would produce:**

```python
from modules.forecast_thresholds import get_scaled_soc_target_by_forecast

# Tomorrow's forecast is 12 kWh
target_soc, reason = get_scaled_soc_target_by_forecast(forecast_wh=12000)
print(f"Target: {target_soc}% ({reason})")
# Output: Target: 75% (Poor forecast (8-15 kWh) - conservative charge)
```

**Or run the test suite:**
```bash
python modules/forecast_thresholds.py
```

---

## 3. Test Peak-Window Boost Logic

**Decide whether to boost at 14:00:**

```python
from bin.peak_window_boost import should_boost_battery_for_peak_window

# At 14:00: remaining forecast is 6 kWh, current SOC is 35%
should_boost, reason, details = should_boost_battery_for_peak_window(
    remaining_forecast_wh=6000,
    current_soc=35
)

print(f"Boost: {should_boost}")
print(f"Reason: {reason}")
print(f"Details: {details}")
```

**Or run the test suite:**
```bash
python bin/peak_window_boost.py
```

---

## 4. Get Recommended Target SOC for Peak Boost

**Calculate the target SOC to boost to:**

```python
from bin.peak_window_boost import calculate_peak_window_boost_target

target_soc, reason = calculate_peak_window_boost_target(
    remaining_forecast_wh=6000,
    current_soc=35
)

print(f"Target: {target_soc}% ({reason})")
if target_soc > 35:
    api.update_charge_settings(target_soc=target_soc, charge_rate=50)
```

---

## 5. Integration into Existing Code

### Option A: Use New Thresholds in 22:00 App

In `src/app.py`, replace the forecast-to-SOC logic:

```python
# OLD (line ~205)
target_soc = get_scaled_soc_target(
    total_forecast_wh=forecast_wh,
    battery_capacity_wh=growatt_config.battery_capacity_wh,
    minimum_charge_pct=growatt_config.minimum_charge_pct,
    maximum_charge_pct=growatt_config.maximum_charge_pct,
    average_load_w=growatt_config.average_load_w,
    confidence=self.config.forecast.confidence
)

# NEW
from modules.forecast_thresholds import get_scaled_soc_target_by_forecast
target_soc, reason = get_scaled_soc_target_by_forecast(
    total_forecast_wh=forecast_wh,
    minimum_charge_pct=growatt_config.minimum_charge_pct,
    maximum_charge_pct=growatt_config.maximum_charge_pct
)
self.logger.info(f"Target SOC: {target_soc}% ({reason})")
```

### Option B: Create 14:00 Afternoon Check

Create new file `src/app_afternoon_peak_check.py`:

```python
"""14:00 peak-window boost check."""

import sys
from datetime import datetime, timedelta
from .api import GrowattAPI
from .config import ConfigManager
from .utils import setup_logging, get_logger
from bin.peak_window_boost import should_boost_battery_for_peak_window, calculate_peak_window_boost_target

class AfternoonPeakChecker:
    def __init__(self, config_path):
        # (similar init to GrowattCharger)
        pass

    async def run(self):
        # Login
        await self._login()

        # Get current SOC at 14:00
        current_soc = await self._get_current_charge()

        # Get remaining forecast (14:00 to sunset)
        remaining_forecast_wh = self._get_afternoon_forecast()

        # Decide if boost needed
        should_boost, reason, details = should_boost_battery_for_peak_window(
            remaining_forecast_wh=remaining_forecast_wh,
            current_soc=current_soc
        )

        self.logger.info(reason)

        if should_boost:
            target_soc, target_reason = calculate_peak_window_boost_target(
                remaining_forecast_wh=remaining_forecast_wh,
                current_soc=current_soc
            )

            await self._update_charge_settings(target_soc)
            self.logger.info(f"Boosting to {target_soc}% for peak window")

        # Log decision to file for analysis
        self._log_peak_window_decision(
            current_soc=current_soc,
            remaining_forecast_wh=remaining_forecast_wh,
            should_boost=should_boost,
            reason=reason
        )
```

---

## 6. Documentation Files

All new documentation:
- **`ANALYSIS_PLAN.md`** — Full strategy document
- **`IMPLEMENTATION_SUMMARY.md`** — What was created and next steps
- **`OLD_VS_NEW_THRESHOLDS.md`** — Detailed comparison
- **`QUICK_REFERENCE.md`** — This file

---

## 7. File Locations

**New modules:**
```
modules/forecast_thresholds.py          # New forecast-based thresholds
bin/analyze_thresholds.py              # Performance analyzer
bin/peak_window_boost.py               # 14:00 peak-window logic
```

**Documentation:**
```
ANALYSIS_PLAN.md                       # Full implementation plan
IMPLEMENTATION_SUMMARY.md              # Summary + next steps
OLD_VS_NEW_THRESHOLDS.md              # Detailed comparison
QUICK_REFERENCE.md                     # This file
```

---

## 8. Troubleshooting

### "ModuleNotFoundError" when importing

```bash
# Make sure you're in the right directory
cd c:\Users\acony\Development\growatt-weather-based-charger

# Make sure venv is activated
.\.venv\Scripts\Activate.ps1

# Then run
python -c "from modules.forecast_thresholds import get_scaled_soc_target_by_forecast; print('OK')"
```

### Analyzer shows "Insufficient data"

This means no days fell into that forecast range. Either:
- Run with more data (wait until you have 30+ days)
- Adjust range boundaries to match your actual forecast distribution

### Charge efficiency showing 0%

This might indicate:
1. Charging didn't occur
2. SOC data not captured properly
3. Data logging issue in predictions/actuals

Let me know if you see this and I can investigate.

---

## 9. Decision Checklist

Before integrating new code:

- [ ] Run `bin/analyze_thresholds.py` on current Nov data
- [ ] Review ANALYSIS_PLAN.md and IMPLEMENTATION_SUMMARY.md
- [ ] Decide: use new thresholds immediately or run both in parallel?
- [ ] Decide: when to deploy 14:00 peak-check logic?
- [ ] Set up monthly review schedule for threshold tuning
- [ ] Document any custom adjustments in `output/threshold_tuning_log.md`

---

## 10. Next Meeting/Discussion

Bring answers to:
1. Which forecast provider is more accurate for your location (Solcast vs Forecast.Solar)?
2. Is peak window always 16:00–19:00, or does it vary?
3. Should new thresholds replace old ones immediately or run in parallel first?
4. How often can you review threshold performance (weekly/monthly)?
