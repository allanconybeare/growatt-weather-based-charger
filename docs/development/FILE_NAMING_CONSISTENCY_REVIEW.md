# 📁 File Naming Consistency Review

**Date**: November 14, 2025

---

## Current State

### Naming Patterns Identified

**Pattern 1: `view_*` files** (Analysis/Reporting)
- `view_morning_soc.py` – View morning SOC check results
- `view_performance.py` – View performance summary
- `view_provider_comparison.py` – View forecast provider comparison

**Pattern 2: `test_*` files** (Unit/Integration Tests)
- `test_forecast.py` – Test forecast functionality
- `test_providers.py` – Test provider system
- `test_settings.py` – Test Growatt settings
- `test_peak_window_config.py` – Test peak window config
- `test_growatt_logging.py` – Test Growatt logging
- `test_charge_rate_fix.py` – Test charge rate calculations

**Pattern 3: Named Wrappers** (Primary Application Scripts)
- `afternoon_peak_check.py` – Wrapper for 14:00 peak check
- `morning_soc_check.py` – Wrapper for 05:00 SOC check
- `growatt_charger.py` – Main overnight charging orchestration

**Pattern 4: Inconsistent Naming** (Analysis Scripts)
- `analyze_thresholds.py` ⚠️ (American spelling, no prefix)
- `review_peak_decisions.py` ⚠️ (No prefix, inconsistent naming)

---

## Issues Identified

### 1. Spelling Inconsistency
```
analyze_thresholds.py          ← American spelling "analyze"
view_performance.py            ← British/consistent
view_provider_comparison.py    ← British/consistent
```

**Issue**: Mixed spelling conventions

**Recommendation**: Use British English consistently
- `analyze_thresholds.py` → `analyse_thresholds.py` (or use `view_threshold_performance.py`)

---

### 2. Missing Prefix Pattern
```
view_morning_soc.py            ✓ Has prefix
view_performance.py            ✓ Has prefix
view_provider_comparison.py    ✓ Has prefix
review_peak_decisions.py       ⚠️ No standard prefix
analyze_thresholds.py          ⚠️ No standard prefix
```

**Issue**: Analysis scripts don't follow the `view_` prefix convention

**Recommendation**: Rename to use `view_` prefix:
- `analyze_thresholds.py` → `view_threshold_analysis.py` or `view_threshold_performance.py`
- `review_peak_decisions.py` → `view_peak_boost_decisions.py`

---

### 3. Spelling of "Thresholds"
```
analyze_thresholds.py   ← Current (correct spelling, but see issue above)
```

**Issue**: Spelling is correct ("thresholds" not "threshholds"), but prefix inconsistent

---

## Proposed Changes

### Option A: Full Consistency (Recommended)

```
BEFORE                          AFTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
analyze_thresholds.py       →   view_threshold_performance.py
review_peak_decisions.py    →   view_peak_boost_decisions.py
```

**Benefits:**
- ✅ All analysis scripts follow `view_` pattern
- ✅ Consistent British English spelling
- ✅ Clear naming: `view_` prefix identifies purpose (reporting/analysis)
- ✅ More descriptive names show what each does
- ✅ Easier to find: `ls view_*.py` shows all reporting

**New State:**
```
view_morning_soc.py
view_peak_boost_decisions.py      ← Renamed from review_peak_decisions.py
view_performance.py
view_provider_comparison.py
view_threshold_performance.py     ← Renamed from analyze_thresholds.py
```

---

### Option B: Partial Consistency (Alternative)

```
BEFORE                          AFTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
analyze_thresholds.py       →   analyse_thresholds.py (British spelling)
review_peak_decisions.py    →   review_peak_boost_decisions.py (more descriptive)
```

**Benefits:**
- ✓ Fixes spelling
- ✓ Adds clarity to peak decisions script

**Drawbacks:**
- ✗ Still inconsistent with `view_` pattern
- ✗ Harder to find analysis scripts with `ls view_*.py`

**Not Recommended**: Inconsistent prefixes defeat the purpose

---

## Impact Analysis

### Files to Rename

| Current Name | New Name | Reason |
|---|---|---|
| `analyze_thresholds.py` | `view_threshold_performance.py` | Prefix consistency + descriptiveness |
| `review_peak_decisions.py` | `view_peak_boost_decisions.py` | Prefix consistency + clarity |

### Files NOT Renamed

| File | Status | Reason |
|---|---|---|
| `test_*.py` (5 files) | No change | Correct pattern for unit tests |
| `view_*.py` (3 files) | No change | Already consistent |
| `afternoon_peak_check.py` | No change | Primary app wrapper, purpose clear |
| `morning_soc_check.py` | No change | Primary app wrapper, purpose clear |
| `growatt_charger.py` | No change | Primary app, well-known name |

### Related Files to Update

When renaming Python files, also update:
- Batch scripts: `run_*.bat` (if they call these scripts)
- PowerShell scripts: `*.ps1` (if they call these scripts)
- Documentation: References to old names
- Comments: Any references in code

---

## Implementation Plan

### Step 1: Rename Files
```bash
# Rename Python files
mv analyze_thresholds.py view_threshold_performance.py
mv review_peak_decisions.py view_peak_boost_decisions.py
```

### Step 2: Update Imports/References
Check for any imports or references:
```bash
grep -r "analyze_thresholds" .
grep -r "review_peak_decisions" .
```

### Step 3: Update Documentation
- Update any README references
- Update any scripts that call these files
- Update any configuration that references these

### Step 4: Create Migration Guide
Document the change for users

---

## File Organization After Changes

### By Category

**Primary Applications** (Main orchestration)
```
growatt_charger.py
afternoon_peak_check.py
morning_soc_check.py
```

**Reporting & Analysis** (View results)
```
view_morning_soc.py
view_peak_boost_decisions.py              ← Renamed
view_performance.py
view_provider_comparison.py
view_threshold_performance.py             ← Renamed
```

**Unit Tests** (Validation)
```
test_charge_rate_fix.py
test_forecast.py
test_growatt_logging.py
test_peak_window_config.py
test_providers.py
test_settings.py
```

**Configuration & Support**
```
conf/
defaults/
modules/
src/
```

---

## Naming Conventions Summary

| Prefix | Purpose | Examples |
|--------|---------|----------|
| `test_` | Unit/integration tests | `test_forecast.py`, `test_providers.py` |
| `view_` | Analysis/reporting/dashboards | `view_morning_soc.py`, `view_performance.py` |
| *(none)* | Primary applications | `growatt_charger.py`, `morning_soc_check.py` |

**Spelling:**
- British English preferred: `analyse`, `colour` (but Python modules may vary)
- For clarity: Use clear, descriptive names

**Descriptiveness:**
- `view_peak_boost_decisions.py` is better than `review_peak_decisions.py`
- `view_threshold_performance.py` is better than `analyze_thresholds.py`

---

## Recommendation Summary

### **I recommend Option A: Full Consistency**

**Rationale:**
1. ✅ All analysis scripts visible with `ls view_*.py`
2. ✅ Consistent with existing patterns
3. ✅ More descriptive names
4. ✅ Easier to organize and find files
5. ✅ Professional naming convention
6. ✅ Scales well as project grows

**Changes Required:**
- Rename: `analyze_thresholds.py` → `view_threshold_performance.py`
- Rename: `review_peak_decisions.py` → `view_peak_boost_decisions.py`
- Update any references in code/docs

**Effort:**
- Low (2 file renames)
- Check for references (~10-20 lines to update)
- Documentation update

**Impact:**
- Positive: Better organization, consistency
- Risk: Low (simple renames, should have tests)

---

## Next Steps

1. Review this recommendation
2. Decide: Option A (Full) or Option B (Partial)
3. If approved, I can:
   - Rename files
   - Update all references
   - Create migration guide
   - Update documentation

---

**Status**: Analysis Complete  
**Recommendation**: Option A (Full Consistency)  
**Ready to Implement**: Yes
