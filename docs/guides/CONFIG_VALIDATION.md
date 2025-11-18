# ✅ Peak Window Configuration Validation System

## Overview

We've implemented a comprehensive validation system to ensure the boost check settings are correct and aligned. This document summarizes what we've built and how it works.

---

## What We've Validated

### 1. **Time Format Validation** ✓
**What it checks**: All times are in `HH:MM` format

**Times validated:**
- `off_peak_start_time` (from tariff config)
- `off_peak_end_time` (from tariff config)
- `peak_start_time` (peak window config)
- `peak_end_time` (peak window config)
- `check_time` (peak window config)

**Example:**
```python
# Valid: 14:00, 02:00, 23:59
# Invalid: 2:00, 14h00, 14.00
```

**Location**: `src/config/configuration.py` → `PeakWindowConfig._validate_time_format()`

---

### 2. **Time Ordering Validation** ✓
**What it checks**: Times are in logical order

**Rules enforced:**
1. Off-peak start < Off-peak end (e.g., 02:00 < 04:59) ✓
2. Peak start < Peak end (e.g., 16:00 < 19:00) ✓
3. Check time < Peak start (e.g., 14:00 < 16:00) ✓

**Why it matters:**
- Prevents invalid ranges like "end time before start time"
- Ensures check happens BEFORE peak (gives time to charge)
- Prevents circular logic

**Location**: `src/config/configuration.py` → `PeakWindowConfig._validate_time_order()`

---

### 3. **Window Conflict Validation** ✓
**What it checks**: Off-peak and peak windows don't overlap

**Example scenario:**
```
Off-peak:  02:00 - 04:59  ← Cheap rates, charge here
Peak:      16:00 - 19:00  ← Expensive rates, avoid drawing

Result: ✅ No conflict (4:59 < 16:00)
```

**Problem if overlapping:**
- Can't charge during off-peak if it overlaps peak
- Creates conflicting charging strategies

**Location**: `test_peak_window_config.py` → `PeakWindowValidator._validate_no_conflicts()`

---

### 4. **Peak Window Duration Validation** ✓
**What it checks**: Peak window actually has duration

**Calculates:** Hours between `peak_start_time` and `peak_end_time`

**Example:**
```
peak_start_time = 16:00
peak_end_time = 19:00
Duration = 3.0 hours ✓

peak_start_time = 16:00
peak_end_time = 16:00
Duration = 0 hours ❌ (Invalid)
```

**Location**: `src/config/configuration.py` → `PeakWindowConfig.get_peak_window_duration_hours()`

---

### 5. **Parameter Range Validation** ✓
**What it checks**: Configuration parameters are in valid ranges

| Parameter | Valid Range | Default | Purpose |
|-----------|------------|---------|---------|
| `forecast_reliability` | 0.0 - 1.0 | 0.4 | How much of forecast reaches peak (40% conservative) |
| `soc_safety_margin_pct` | 0.0 - 100.0 | 10.0 | Extra battery buffer (10% safety margin) |

**Example:**
```python
# Valid
forecast_reliability = 0.4  # 40%
soc_safety_margin_pct = 10.0  # 10%

# Invalid
forecast_reliability = 1.5   # Can't be > 100%
soc_safety_margin_pct = -5.0  # Can't be negative
```

**Location**: `src/config/configuration.py` → `PeakWindowConfig._validate_float_range()`

---

## How It's Implemented

### Layer 1: Dataclass Validation (Automatic on Config Load)

**File**: `src/config/configuration.py`

**Classes:**
- `PeakWindowConfig` – Validates peak window settings
- `TariffConfig` – Validates tariff settings
- `GrowattConfig` – Validates Growatt settings
- `ForecastConfig` – Validates forecast settings

**When it runs:**
- Automatically when you call `ConfigManager(config_path)`
- Runs `__post_init__()` methods on each dataclass
- Throws `GrowattConfigError` if invalid

**Example:**
```python
config = ConfigManager('conf/growatt-charger.ini')
# ↓ Automatically validates all configs
# ↓ Throws GrowattConfigError if invalid
config.peak_window  # Already validated!
```

---

### Layer 2: Comprehensive Test Script

**File**: `test_peak_window_config.py`

**Class**: `PeakWindowValidator`

**5 Validation Checks:**
1. Time formats (HH:MM)
2. Time ordering (correct sequence)
3. Window conflicts (no overlap)
4. Peak duration (has length)
5. Parameter ranges (within bounds)

**Runs independently:** Can test config without running app

```bash
python test_peak_window_config.py conf/growatt-charger.ini
```

---

## Configuration Being Validated

**Location**: `conf/growatt-charger.ini`

```ini
[tariff]
off_peak_start_time = 02:00
off_peak_end_time = 04:59

[peak_window]
peak_start_time = 16:00
peak_end_time = 19:00
check_time = 14:00
forecast_reliability = 0.4
soc_safety_margin_pct = 10.0
```

---

## Validation Results Example

When you run the test script:

```
======================================================================
PEAK WINDOW CONFIGURATION VALIDATOR
======================================================================

1. VALIDATING TIME FORMATS
----------------------------------------------------------------------

2. VALIDATING TIME ORDERING
----------------------------------------------------------------------
  ✅ Off-peak: 02:00 < 04:59 ✓
  ✅ Peak:     16:00 < 19:00 ✓
  ✅ Check before peak: 14:00 < 16:00 ✓

3. VALIDATING NO WINDOW CONFLICTS
----------------------------------------------------------------------
  ✅ No conflict: Off-peak (02:00-04:59) doesn't overlap peak (16:00-19:00)

4. VALIDATING PEAK WINDOW DURATION
----------------------------------------------------------------------
  Peak window: 16:00 to 19:00
  Duration:    3.00 hours (180 minutes)
  ✅ Peak window duration is valid

5. VALIDATING PARAMETER RANGES
----------------------------------------------------------------------
  ✅ Forecast reliability: 40.0%
  ✅ SOC safety margin:    10.0%

======================================================================
SUMMARY
======================================================================

✅ INFORMATION:
  ✅ Config loaded from: conf/growatt-charger.ini
  ✅ Off-peak: 02:00 < 04:59 ✓
  ✅ Peak:     16:00 < 19:00 ✓
  ✅ Check before peak: 14:00 < 16:00 ✓
  ✅ No conflict: Off-peak (02:00-04:59) doesn't overlap peak (16:00-19:00)
  ✅ Peak window duration is valid
  ✅ Forecast reliability: 40.0%
  ✅ SOC safety margin:    10.0%

======================================================================
✅ VALIDATION PASSED - All settings correct!
======================================================================
```

---

## Error Detection Examples

### Example 1: Invalid Time Format
```ini
[peak_window]
check_time = 14h00  # ❌ Should be 14:00
```

**Error:**
```
❌ check_time must be in HH:MM format, got 14h00
```

---

### Example 2: Check Time After Peak Start
```ini
[peak_window]
check_time = 17:00    # ❌ After peak start
peak_start_time = 16:00
```

**Error:**
```
❌ check_time (17:00) must be before peak_start_time (16:00)
```

---

### Example 3: Invalid Parameter Range
```ini
[peak_window]
forecast_reliability = 1.5  # ❌ Must be 0.0-1.0
```

**Error:**
```
❌ forecast_reliability must be between 0.0 and 1.0, got 1.5
```

---

## Running the Validation

### Automatic (On App Startup)
```python
# src/app.py
config = ConfigManager('conf/growatt-charger.ini')
# ↑ Automatically validates all configs
# ↑ Exits with error if invalid
```

### Manual (Test Script)
```bash
# From project root
python test_peak_window_config.py conf/growatt-charger.ini
```

### From Python Code
```python
from src.config import ConfigManager
from test_peak_window_config import PeakWindowValidator

# Test current config
validator = PeakWindowValidator('conf/growatt-charger.ini')
if validator.validate():
    print("✅ Config is valid")
else:
    print("❌ Config has errors")

validator.print_configuration_summary()
```

---

## What Gets Validated at Each Stage

### Stage 1: Configuration File Parsing
**Checks:**
- File exists and readable
- Valid INI format
- All required sections present

### Stage 2: Section Validation
**Checks:**
- `[tariff]` section has: off_peak_start_time, off_peak_end_time
- `[peak_window]` section has: peak_start_time, peak_end_time, check_time
- Optional fields have sensible defaults

### Stage 3: Dataclass Initialization
**Checks:**
- Time formats (HH:MM)
- Time ordering
- Parameter ranges
- Numeric ranges

### Stage 4: Cross-Config Validation
**Checks:**
- No window conflicts
- Peak duration exists
- All pieces align

---

## Configuration Validation Cascade

```
1. Load INI File
   ↓
2. Parse [tariff] Section
   ↓ Validate TariffConfig
   ├─ off_peak_start_time format
   ├─ off_peak_end_time format
   └─ off_peak_start < off_peak_end

3. Parse [peak_window] Section
   ↓ Validate PeakWindowConfig
   ├─ peak_start_time format
   ├─ peak_end_time format
   ├─ check_time format
   ├─ peak_start < peak_end
   ├─ check_time < peak_start
   ├─ forecast_reliability ∈ [0.0, 1.0]
   └─ soc_safety_margin_pct ∈ [0, 100]

4. Cross-Config Validation (test script)
   ├─ No off-peak/peak overlap
   └─ Peak window has duration > 0

5. Configuration Summary
   └─ Print human-readable results
```

---

## Implementation Files

| File | Purpose | Key Function |
|------|---------|--------------|
| `src/config/configuration.py` | Config dataclasses & validation | `PeakWindowConfig.__post_init__()` |
| `test_peak_window_config.py` | Comprehensive test script | `PeakWindowValidator.validate()` |
| `conf/growatt-charger.ini` | Configuration file | `[peak_window]` section |
| `src/utils/exceptions.py` | Exception classes | `GrowattConfigError` |

---

## Testing Your Configuration

### Quick Test
```bash
# Validates config in ~1 second
python test_peak_window_config.py conf/growatt-charger.ini
```

### Full Test
```bash
# Runs all unit tests including config validation
pytest test_peak_window_config.py -v
```

### In Application
```bash
# Runs app with automatic config validation
python -m src.app conf/growatt-charger.ini
# Will exit with error if config invalid
```

---

## Configuration Safety Guarantees

✅ **Format Validation**: Times must be HH:MM  
✅ **Logic Validation**: check_time < peak_start_time < peak_end_time  
✅ **Range Validation**: Parameters in valid ranges  
✅ **Conflict Validation**: Windows don't overlap  
✅ **Duration Validation**: Peak window has meaningful duration  
✅ **Error Reporting**: Clear error messages  
✅ **Fail-Fast**: Errors caught at startup, not runtime  

---

## What Happens If Config Is Invalid

### If Invalid on Startup
```
$ python -m src.app conf/growatt-charger.ini

GrowattConfigError: check_time (17:00) must be before peak_start_time (16:00)
```

**Result**: App exits, doesn't run, prevents bad charging decisions

### If Invalid in Test
```
$ python test_peak_window_config.py conf/growatt-charger.ini

❌ ERRORS:
  ❌ check_time (17:00) must be before peak_start_time (16:00)

❌ VALIDATION FAILED - Please fix errors above
```

---

## Summary

We've implemented a **4-layer validation system**:

1. **Dataclass Validation** – Automatic on config load
2. **Test Script** – Comprehensive manual validation
3. **Cross-Config Checks** – No overlaps, correct alignment
4. **Error Reporting** – Clear, actionable messages

**Status**: ✅ Comprehensive validation in place  
**Testing**: Run `python test_peak_window_config.py conf/growatt-charger.ini`  
**Safety**: Config errors caught at startup, prevents runtime failures  

---

**Last Updated**: November 14, 2025  
**Status**: ✅ Complete & Active
