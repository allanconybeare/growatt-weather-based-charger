# Analysis & Optimization Plan

## 1. Proposed Changes to SOC Target Logic

**Current issue:** Coverage-based thresholds don't align with your observed real-world data.

**Your observations:**
- Summer max: 32 kWh
- Below 8 kWh: set to 95% (very conservative)
- 8–25 kWh: scale down linearly
- 25+ kWh: target 30%
- Actual data shows days with 5.5+ kWh still have "juice in the tank" at 23:00 ✓

**Proposed new thresholds (forecast-based, not coverage-based):**
```python
if forecast_wh >= 25000:      # Good day (77% of summer max)
    target_soc = 30
elif forecast_wh >= 15000:    # Decent day
    target_soc = 50
elif forecast_wh >= 8000:     # Moderate day
    target_soc = 75
else:                          # Poor day
    target_soc = 95
```

**Rationale:** Simpler, directly tied to observed behavior, easier to tune monthly.

---

## 2. Performance Analysis Framework

### What We're Collecting (Already Logging)
- **Predictions:** `output/predictions.csv` — forecast, target SOC, charge rate
- **Actuals:** `output/actuals.csv` — actual generation, evening SOC
- **Summary:** `output/performance_summary.csv` — forecast accuracy, charge efficiency

### Key Metrics to Calculate

#### A. Forecast Accuracy
**Already calculated** in `performance_summary.csv` as `Accuracy (%)`:
- Formula: `actual_kwh / forecast_kwh * 100`
- Shows how close predictions are to reality

#### B. Battery Health (SOC Trajectory)
Track whether actual SOC aligns with expectations:
```python
expected_evening_soc = morning_soc_after_charge + (forecast_wh / battery_capacity_wh * 100)
actual_evening_soc = <from API>
soc_error = actual_evening_soc - expected_evening_soc
```

**What this tells us:**
- Positive error: we're being too conservative (set higher targets next time)
- Negative error: we're being too aggressive (lower targets needed)

#### C. Threshold Effectiveness
For each forecast range, calculate:
1. **Accuracy within bracket** — how well did predictions work for this range?
2. **SOC headroom at sunset** — did we still have battery? Did we draw from grid?
3. **Charge efficiency** — did we actually reach the target SOC?

**Example analysis query:**
```
For forecasts between 8–15 kWh:
  - Average forecast accuracy: 72%
  - Average evening SOC: 45% (when target was 50%)
  - Days we exhausted battery before sunset: 2%
  - Days with >70% SOC at 23:00: 35%
```

---

## 3. Proposed Analysis Script

Create `bin/analyze_thresholds.py` to run monthly:

```python
"""Analyze threshold performance and suggest adjustments."""

import csv
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class ThresholdAnalyzer:
    def __init__(self, predictions_file, actuals_file, summary_file):
        self.predictions = self._load_csv(predictions_file)
        self.actuals = self._load_csv(actuals_file)
        self.summary = self._load_csv(summary_file)

    def analyze_by_forecast_range(self, ranges: List[Tuple[int, int, str]]):
        """
        Analyze performance grouped by forecast ranges.

        Args:
            ranges: List of (min_kwh, max_kwh, label) tuples
                   e.g., [(0, 8, "Poor"), (8, 15, "Moderate")]
        """
        results = {}

        for min_kwh, max_kwh, label in ranges:
            matching_days = [
                row for row in self.summary
                if min_kwh <= float(row['Forecast (kWh)']) < max_kwh
            ]

            if not matching_days:
                continue

            # Calculate metrics for this range
            accuracy_pct = self._avg_metric(matching_days, 'Accuracy (%)')
            soc_efficiency = self._avg_metric(matching_days, 'Charge Efficiency (%)')
            exhausted_count = sum(
                1 for row in matching_days
                if float(row.get('SOC at Evening (%)', 0)) < 20
            )

            results[label] = {
                'forecast_range': f"{min_kwh}–{max_kwh} kWh",
                'sample_size': len(matching_days),
                'avg_accuracy': accuracy_pct,
                'avg_charge_efficiency': soc_efficiency,
                'days_critically_low': exhausted_count,
                'recommendation': self._recommend(accuracy_pct, soc_efficiency)
            }

        return results

    def _avg_metric(self, rows, column):
        """Calculate average of numeric column, skipping N/A."""
        values = [
            float(row[column]) for row in rows
            if row[column] != 'N/A'
        ]
        return sum(values) / len(values) if values else 0

    def _recommend(self, accuracy, efficiency):
        """Generate tuning recommendation."""
        if accuracy < 70:
            return "Forecast unreliable for this range; consider widening target SOC"
        elif efficiency < 80:
            return "Targets not being reached; check charge window or rate"
        elif efficiency > 110:
            return "Consistently overcharging; targets may be too high"
        else:
            return "Acceptable; monitor for drift"

    def _load_csv(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

# Example usage in main
if __name__ == '__main__':
    analyzer = ThresholdAnalyzer(
        'output/predictions.csv',
        'output/actuals.csv',
        'output/performance_summary.csv'
    )

    ranges = [
        (0, 8, "Very Poor"),
        (8, 15, "Poor"),
        (15, 20, "Moderate"),
        (20, 25, "Good"),
        (25, 32, "Excellent"),
    ]

    results = analyzer.analyze_by_forecast_range(ranges)

    print("\n=== THRESHOLD PERFORMANCE ANALYSIS ===\n")
    for label, metrics in results.items():
        print(f"{label} ({metrics['forecast_range']}):")
        print(f"  Samples: {metrics['sample_size']}")
        print(f"  Avg Forecast Accuracy: {metrics['avg_accuracy']:.1f}%")
        print(f"  Avg Charge Efficiency: {metrics['avg_charge_efficiency']:.1f}%")
        print(f"  Days Critically Low: {metrics['days_critically_low']}")
        print(f"  Recommendation: {metrics['recommendation']}\n")
```

---

## 4. 14:00 Peak-Charge Decision Logic

### Problem
Between 16:00–19:00, grid import costs spike. You want to decide at 14:00 whether to boost the battery to avoid this.

### Decision Rule (Proposed)
```python
def should_boost_at_14(forecast_wh: float, current_soc: float) -> Tuple[bool, str]:
    """
    Decide if battery should be boosted to avoid peak-rate grid import.

    Peak window: 16:00–19:00 (3 hours, 12.75 kWh exposure at 850W)

    Args:
        forecast_wh: Remaining generation forecast from 14:00 to sunset (~6 hours in Nov)
        current_soc: Current battery SOC at 14:00

    Returns:
        (should_boost, reason)
    """
    battery_capacity_wh = 6900
    peak_window_consumption_wh = 850 * 3  # 2550 Wh

    # Conservative estimate: only ~40% of afternoon forecast reaches peak window
    peak_window_forecast_wh = forecast_wh * 0.4

    # Will forecast alone cover the peak window?
    if peak_window_forecast_wh < peak_window_consumption_wh:
        shortfall_wh = peak_window_consumption_wh - peak_window_forecast_wh
        shortfall_pct = (shortfall_wh / battery_capacity_wh) * 100

        # If we need >X% of battery to cover peak window
        if current_soc <= (shortfall_pct + 10):  # +10% safety margin
            return True, f"Forecast {forecast_wh/1000:.1f}kWh insufficient for peak window; boost needed"

    return False, f"Forecast {forecast_wh/1000:.1f}kWh sufficient; no boost needed"

# Usage at 14:00:
# should_boost, reason = should_boost_at_14(remaining_forecast, current_soc)
# if should_boost:
#     logger.info(reason)
#     api.update_charge_settings(target_soc=85, charge_rate=50)  # Quick boost
```

### Implementation Notes
- **Forecast update:** Fetch latest 14:00 forecast from your provider
- **Trigger:** Add this to a new scheduled task (e.g., `morning_soc_check.py` pattern but at 14:00)
- **Logging:** Log the decision and actual outcome (did we avoid peak-window grid import?)
- **Tuning:** Track whether boosts were effective; adjust threshold based on real results

---

## 5. Recommended Implementation Order

1. **Week 1:** Implement new forecast-based thresholds (simpler than coverage-based)
   - File: `modules/forecast.py` → new function `get_scaled_soc_target_by_forecast()`
   - Keep old function for comparison
   - Update data logger to log which function was used

2. **Week 2:** Create analysis script
   - File: `bin/analyze_thresholds.py`
   - Run it manually each week; review recommendations
   - Document findings in `output/threshold_tuning_log.md`

3. **Week 3:** Implement 14:00 peak-charge logic
   - File: Create `bin/afternoon_peak_check.py`
   - Schedule with Windows Task Scheduler
   - Log all decisions to compare with actuals

4. **Ongoing:** Review `threshold_tuning_log.md` monthly
   - Adjust forecast thresholds based on analyzer recommendations
   - Track boost effectiveness
   - Seasonal adjustments (Nov–Mar vs Apr–Sep)

---

## 6. Quick Wins (Do This Week)

1. **Update thresholds immediately** in `get_scaled_soc_target()`:
   - Replace coverage-based with forecast-based
   - Your 8/15/25 kWh breakpoints are solid

2. **Add a logging flag** in predictions CSV:
   - Log actual evening SOC alongside target
   - Makes manual review easier

3. **Create a simple monthly review checklist**:
   ```markdown
   - [ ] Review performance_summary.csv last 30 days
   - [ ] Identify forecast ranges with poor accuracy
   - [ ] Check if any days exhausted battery before sunset
   - [ ] Recommend threshold adjustment
   ```

---

## Questions for You

1. **Forecast provider:** Which is more accurate for your location, solcast or forecast.solar?
2. **Peak window exact times:** Is 16:00–19:00 fixed, or does it vary?
3. **Data retention:** How many months of data do you want to keep for analysis?
4. **Seasonal patterns:** Do you notice Oct–Mar significantly different from Apr–Sep?
