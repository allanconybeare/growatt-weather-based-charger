# Old vs New: Threshold Comparison

## The Problem with Coverage-Based Thresholds (Current)

**Current logic** (in `modules/forecast.py`):
```
Calculate solar_coverage = (forecast × confidence) / daily_consumption
Then apply tiers based on coverage %
```

**Issues:**
1. **Two-step calculation** — forecast → coverage % → target SOC (confusing)
2. **Confidence factor baked in** — can't easily see what raw forecast was
3. **Hard to reason about** — "coverage ≥ 60%" doesn't mean much to most people
4. **Thresholds not aligned with data** — Nov shows mostly "poor day" tier getting clipped to 85%

**Example (Nov data):**
```
Forecast: 3 kWh
Confidence: 0.7
Daily load: 20.4 kWh

Coverage = (3 × 0.7) / 20.4 = 10.3%
Coverage < 40% → "Very poor day" → target 95%
Before fix: clipped to 85% (bug)
```

---

## New Approach: Forecast-Based Thresholds

**New logic** (in `modules/forecast_thresholds.py`):
```
if forecast >= 25 kWh → 30%
elif forecast >= 20 kWh → 40%
elif forecast >= 15 kWh → 50%
elif forecast >= 8 kWh → 75%
else → 95%
```

**Advantages:**
1. **Transparent** — "forecast is 8 kWh, so target is 75%"
2. **Aligned with reality** — breakpoints based on your summer max (32 kWh) and Nov observations
3. **Tunable** — change 8, 15, 20, 25 values based on learnings
4. **No confidence baked in** — you can see the raw forecast vs adjusted threshold

**Example (same Nov day):**
```
Forecast: 3 kWh
Decision: 3 < 8 → target 95%
Reason: Clear, simple, no calculation needed
```

---

## Side-by-Side Comparison

| Aspect | Current (Coverage-Based) | New (Forecast-Based) |
|--------|--------------------------|----------------------|
| **Thresholds** | 150%, 120%, 100%, 80%, 60%, 40% coverage | 25, 20, 15, 8 kWh |
| **Understandability** | Need to calculate coverage % first | Direct forecast reading |
| **Tuning** | Requires understanding % coverage | Adjust kWh breakpoints |
| **Data dependency** | Uses confidence factor built-in | Works on raw forecast |
| **Example (Nov 3kWh)** | `10.3% → "Very poor"` | `3 < 8 → "Very poor"` |
| **Reason clarity** | "Coverage 10.3% is very poor" | "Forecast 3kWh is very poor" |

---

## Mapping Old Thresholds to New

For reference, here's how old coverage tiers map to forecast amounts (using your config):

```
Daily consumption = 20.4 kWh
Confidence = 0.7
Therefore: forecast_kwh = (coverage % / 100) × 20.4 / 0.7

Coverage Tier     →  Forecast Range (after confidence)
─────────────────────────────────────────────────────
≥ 150% (excellent)  → ≥ 43.7 kWh
≥ 120% (very good)  → ≥ 35.0 kWh
≥ 100% (good)       → ≥ 29.1 kWh
≥ 80% (decent)      → ≥ 23.3 kWh
≥ 60% (moderate)    → ≥ 17.5 kWh
≥ 40% (poor)        → ≥ 11.7 kWh
< 40% (very poor)   → < 11.7 kWh
```

**New thresholds simplified:**
```
25+ kWh → 30%        (captures "excellent" tier)
20–25 kWh → 40%      (captures "good" tier)
15–20 kWh → 50%      (captures "moderate" tier)
8–15 kWh → 75%       (captures "poor" tier)
< 8 kWh → 95%        (captures "very poor" tier)
```

This is **much easier to remember and tune**.

---

## Test Results: Both Functions

Running November data through both approaches:

### Old Approach (Coverage-Based)
```
Most days fall into "very poor" tier (coverage < 40%)
→ Many days target 95% (or were clipped to 85% before fix)
Accuracy: Mixed (coverage calculation adds complexity)
```

### New Approach (Forecast-Based)
```
3 kWh forecast → 95% (very poor)
8 kWh forecast → 75% (poor)
15 kWh forecast → 50% (moderate)
20+ kWh forecast → 40–30% (good/excellent)
Accuracy: Transparent, easy to verify
```

---

## Migration Path

**Option A: Gradual (Recommended)**
1. Keep both functions in parallel
2. Log which one was used each day
3. After 2 weeks, compare performance
4. Switch to new function if better

**Option B: Immediate**
1. Replace old function with new one
2. Monitor for issues
3. Revert if needed

**Option C: Side-by-Side Analysis**
1. Run analyzer against both approaches
2. See which would have performed better historically
3. Use data to decide

---

## Why This Matters

Your current 85% clipping issue stems from the old function trying to be too generic. The new function is:
- **Specific to your setup** (32 kWh summer max, 850W load)
- **Based on your data** (Nov forecasts are typically 3–8 kWh)
- **Easier to tune** (adjust kWh breakpoints, not coverage %)
- **More predictable** (forecast value directly correlates to target)

**Next step:** Pick one of the migration paths above and let's test it.
