# New Features: Threshold Analysis & Peak-Charge Logic

## Summary

You now have a complete framework for:
1. **Understanding** your SOC target thresholds (old vs new approach)
2. **Analyzing** what's working and what isn't
3. **Learning** from historical data to improve future performance
4. **Deciding** at 14:00 whether to boost the battery for peak-rate hours (16:00–19:00)

---

## What Was Delivered

### Code (3 New Modules)

| File | Purpose | Usage |
|------|---------|-------|
| `modules/forecast_thresholds.py` | Simpler forecast-based threshold calculation | `get_scaled_soc_target_by_forecast(forecast_wh)` |
| `bin/analyze_thresholds.py` | Performance analyzer (run weekly/monthly) | `python bin/analyze_thresholds.py [--export]` |
| `bin/peak_window_boost.py` | 14:00 decision logic for peak-charge boost | `should_boost_battery_for_peak_window(...)` |

### Documentation (4 Files)

| File | Purpose |
|------|---------|
| **`QUICK_REFERENCE.md`** | START HERE — practical usage examples and commands |
| **`ANALYSIS_PLAN.md`** | Full strategy for threshold tuning and analysis |
| **`IMPLEMENTATION_SUMMARY.md`** | What was created, what to do next, checklist |
| **`OLD_VS_NEW_THRESHOLDS.md`** | Detailed comparison of old coverage-based vs new forecast-based |

### Bug Fix

Also fixed the earlier issue where hardcoded 85% ceiling was preventing `maximum_charge_pct = 95` from being respected in `modules/forecast.py`.

---

## Quick Start

### 1. See Your Threshold Performance (Right Now)

```bash
python bin/analyze_thresholds.py
```

**Example output:**
```
Very Poor (0–8 kWh):    22 samples, 85% accuracy, 18.8% evening SOC
Poor (8–15 kWh):        10 samples, 68% accuracy, 18.8% evening SOC
Moderate (15–20 kWh):    3 samples, 46% accuracy, 35.0% evening SOC
```

Tells you: "In the 0–8 kWh range, forecasts were 85% accurate and evening SOC was 18.8%"

### 2. Test New Forecast-Based Thresholds

```bash
python modules/forecast_thresholds.py
```

**Example output:**
```
    3 kWh -> 95%  (Very poor forecast (<8 kWh) - charge to max)
    8 kWh -> 75%  (Poor forecast (8-15 kWh) - conservative charge)
   15 kWh -> 50%  (Moderate forecast (15-20 kWh) - balanced charge)
   20 kWh -> 40%  (Good forecast (20-25 kWh) - low charge needed)
   25 kWh -> 35%  (Excellent forecast (25+ kWh) - minimal charge)
   32 kWh -> 35%  (Excellent forecast (25+ kWh) - minimal charge)
```

This is your new threshold logic. Compare with what you currently get from the old coverage-based approach.

### 3. Test Peak-Charge Boost Logic

```bash
python bin/peak_window_boost.py
```

**Example output:**
```
Low forecast, low SOC:
  Forecast: 3.0kWh, SOC: 35%
  Shortfall: 20%, Need: 30%
  Decision: NO BOOST (but marginal)

Moderate forecast, low SOC:
  Forecast: 6.0kWh, SOC: 35%
  Shortfall: 2%, Need: 12%
  Decision: NO BOOST

Good forecast, moderate SOC:
  Forecast: 10.0kWh, SOC: 60%
  Shortfall: 0%, Need: 10%
  Decision: NO BOOST
```

Shows you how decisions would play out in different scenarios.

---

## Key Insights from Your Data (Nov 2025)

**Current performance (old thresholds):**
- Most days < 8 kWh forecast → targeting 95% (or was 85% before the fix)
- Evening SOC: average 18.8% (meaning battery is still available at sunset ✓)
- Forecast accuracy: 68–85% in most ranges

**New thresholds would:**
- Below 8 kWh → still 95% (same as old)
- But rules now clearer and more tunable
- Better alignment with your 8/15/25 kWh breakpoints

**Peak-charge logic:**
- At 14:00, with typical 3–6 kWh afternoon forecast, usually **no boost needed**
- Unless SOC drops below 30% AND forecast very low
- This protects you from 16:00–19:00 peak rates

---

## Implementation Options

### Option A: Start Analyzing Now (Recommended)
```bash
# Week 1: Run analysis weekly
python bin/analyze_thresholds.py --export

# Review the CSV each week in Excel
# Look for patterns: "Which ranges are underperforming?"
# Document findings in: output/threshold_tuning_log.md
```

### Option B: Switch Thresholds Immediately
If you're confident in the 8/15/20/25 kWh breakpoints:
1. Integrate `get_scaled_soc_target_by_forecast()` into `src/app.py`
2. Deploy
3. Monitor for 2 weeks
4. Use analyzer to confirm improvement

### Option C: Run Both in Parallel
1. Keep old coverage-based function
2. Add new forecast-based function
3. Log which one would have been used each day
4. After 2 weeks, compare performance
5. Pick the winner

---

## Next Decision Points

**This Week:**
- [ ] Read QUICK_REFERENCE.md
- [ ] Run `python bin/analyze_thresholds.py` on your Nov data
- [ ] Review the output — any surprises?

**This Month:**
- [ ] Decide on threshold migration (Option A/B/C above)
- [ ] Set up weekly analysis reviews
- [ ] Start 14:00 peak-boost testing

**Longer Term:**
- [ ] Monthly threshold tuning based on analyzer recommendations
- [ ] Seasonal adjustments (Nov–Mar vs Apr–Sep)
- [ ] Track actual peak-rate grid imports avoided by boost logic

---

## Files to Review in Order

1. **`QUICK_REFERENCE.md`** ← Start here (practical examples)
2. **`IMPLEMENTATION_SUMMARY.md`** ← Understanding what was built
3. **`OLD_VS_NEW_THRESHOLDS.md`** ← Technical comparison
4. **`ANALYSIS_PLAN.md`** ← Full strategy document

---

## Questions?

Key things to clarify:
- Should I integrate new thresholds into `src/app.py` now?
- When do you want the 14:00 peak-check to run?
- Which forecast provider is more accurate (Solcast vs Forecast.Solar)?
- Any seasonal patterns you've noticed (Oct–Mar different from Apr–Sep)?

---

## Bug Fixed

**Before:** Hardcoded 85% ceiling prevented `maximum_charge_pct = 95` from being used
```python
# OLD (bad):
practical_max = min(maximum_charge_pct, 85)  # Always took 85!

# NEW (good):
target_soc = max(minimum_charge_pct, min(maximum_charge_pct, target_soc))  # Respects 95!
```

This means your config setting `maximum_charge_pct = 95` now actually works.

---

Generated: November 13, 2025
