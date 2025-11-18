# ✅ SLOT PRESERVATION - FULLY RESOLVED

**Date**: November 14, 2025  
**Status**: ✅ COMPLETE AND TESTED

---

## Problem Summary

When the 14:00 afternoon peak check updated slot 1 (peak boost), slot 0 (off-peak charging) was being reset to disabled and 00:00-00:00.

```
Before:  Slot 0 = 02:00-05:00 (ENABLED) ✓
Action:  Update slot 1 to 14:00-16:00
After:   Slot 0 = 00:00-00:00 (DISABLED) ✗
```

This happened because the API requires ALL parameters (param1-17) in every request, and if not explicitly set, they default to disabled.

---

## Root Cause

The Growatt API:
1. **Requires ALL parameters** (param1-17) to be sent in every update
2. **Has no "read current state"** method to get existing slot configurations
3. **Defaults slots to disabled** if not included in the update

The previous fix sent all parameters but initialized all slots to disabled before enabling only the target slot, which destroyed slot 0's configuration.

---

## Solution: Preserve Slot 0 Explicitly

Added new parameters to `update_charge_settings_with_slot()`:

```python
def update_charge_settings_with_slot(
    self,
    device_sn: str,
    charge_rate: int,
    target_soc: int,
    schedule_start: tuple,
    schedule_end: tuple,
    slot_number: int = 0,
    preserve_slot_0: bool = False,           # ← NEW
    slot_0_start: tuple = None,             # ← NEW
    slot_0_end: tuple = None                # ← NEW
) -> Dict[str, Any]:
```

### How It Works

**With `preserve_slot_0=False` (default - clears other slots):**
```python
api.update_charge_settings_with_slot(
    device_sn=device_sn,
    charge_rate=80,
    target_soc=51,
    schedule_start=(14, 0),
    schedule_end=(16, 0),
    slot_number=1
)
# Result: Slot 0 = disabled, Slot 1 = 14:00-16:00
```

**With `preserve_slot_0=True` (preserves slot 0):**
```python
api.update_charge_settings_with_slot(
    device_sn=device_sn,
    charge_rate=80,
    target_soc=51,
    schedule_start=(14, 0),
    schedule_end=(16, 0),
    slot_number=1,
    preserve_slot_0=True,
    slot_0_start=(2, 0),
    slot_0_end=(5, 0)
)
# Result: Slot 0 = 02:00-05:00 (ENABLED), Slot 1 = 14:00-16:00 (ENABLED)
```

---

## Implementation

### 1. Updated `src/api/growatt.py`

**Method**: `update_charge_settings_with_slot()` (lines 389-502)

**Changes**:
- Added 3 new parameters: `preserve_slot_0`, `slot_0_start`, `slot_0_end`
- Updated docstring with clear documentation
- Added validation: if `preserve_slot_0=True`, require slot_0 times
- Added logic: if preserving, configure slot 0 after initializing all slots

**Key Code**:
```python
# If requested, preserve slot 0 with provided schedule
if preserve_slot_0 and slot_number != 0:
    slot_0_cfg = slot_configs[0]
    idx = slot_0_cfg["start_idx"]
    params[f'param{idx}'] = f"{slot_0_start[0]:02d}"     # Start hour
    params[f'param{idx + 1}'] = f"{slot_0_start[1]:02d}" # Start minute
    params[f'param{idx + 2}'] = f"{slot_0_end[0]:02d}"   # End hour
    params[f'param{idx + 3}'] = f"{slot_0_end[1]:02d}"   # End minute
    params[f'param{slot_0_cfg["enable_idx"]}'] = "1"     # Enable slot 0
```

### 2. Updated `src/app_afternoon_peak_check.py`

**Method**: `_apply_boost_settings()` (lines 310-340)

**Changes**:
- Get off-peak times from tariff config
- Pass `preserve_slot_0=True` to API call
- Pass slot 0 schedule to preserve

**Key Code**:
```python
# Get off-peak schedule from config to preserve slot 0
tariff_config = self.config.tariff
off_peak_start_hour, off_peak_start_min = map(int, tariff_config.off_peak_start_time.split(':'))
off_peak_end_hour, off_peak_end_min = map(int, tariff_config.off_peak_end_time.split(':'))

# Call API with slot-specific parameters, preserving slot 0
self.api.update_charge_settings_with_slot(
    device_sn=self.device_sn,
    charge_rate=boost_charge_rate,
    target_soc=int(target_soc),
    schedule_start=(14, 0),
    schedule_end=(16, 0),
    slot_number=slot_num,
    preserve_slot_0=True,    # ← NEW
    slot_0_start=(off_peak_start_hour, off_peak_start_min),
    slot_0_end=(off_peak_end_hour, off_peak_end_min)
)
```

---

## Verification Tests

### Test 1: Basic Slot Preservation
```bash
python test_slot_preservation_with_flag.py
```

**Result**: ✅ PASSED
- Slot 0 set to 02:00-05:00
- Slot 1 set to 14:00-16:00 WITH preservation
- Both slots active on device

### Test 2: Afternoon Peak Check Update
```bash
python test_afternoon_peak_check_update.py
```

**Result**: ✅ PASSED
- Simulates 14:00 peak check
- Applies boost to slot 1
- Preserves slot 0 from tariff config
- Output shows correct parameters sent

### Parameters Comparison

**Without Preservation** (OLD - BROKEN):
```
'param3': '00', 'param4': '00', 'param5': '00', 'param6': '00', 'param7': '0'  ← Slot 0 disabled
'param8': '14', 'param9': '00', 'param10': '16', 'param11': '00', 'param12': '1'
```

**With Preservation** (NEW - FIXED):
```
'param3': '02', 'param4': '00', 'param5': '05', 'param6': '00', 'param7': '1'  ← Slot 0 preserved!
'param8': '14', 'param9': '00', 'param10': '16', 'param11': '00', 'param12': '1'
```

---

## Device Behavior After Fix

### Timeline

```
22:00 (Previous day - Overnight charging task):
  → Sets slot 0 (02:00-05:00)
  → Device charging: 02:00-05:00 ✓

14:00 (Afternoon peak check - THIS FIX):
  → Checks if peak boost needed
  → If YES: Updates slot 1 (14:00-16:00) + PRESERVES slot 0
  → Device charging: 14:00-16:00 (peak boost active)
  → Device memory: Slot 0 still configured for tomorrow

16:01 (After peak boost ends):
  → Device reverts to default charging (slot 1 disabled)
  → Device still remembers slot 0 for tomorrow

Next day 02:00 (Overnight charging):
  → Device activates slot 0 (02:00-05:00)
  → Charging works correctly ✓

Next day 22:00 (Overnight charging task):
  → Re-establishes slot 0 (could refresh if needed)
  → Device still has slot 0 from yesterday anyway
```

---

## Impact

✅ **Slot 0 now PRESERVED** when updating slot 1  
✅ **Both schedules coexist** - no conflicts  
✅ **Peak boost works** - afternoon charging when needed  
✅ **Off-peak charging continues** - overnight charging unaffected  
✅ **No data loss** - slot 0 never cleared unexpectedly  
✅ **Backward compatible** - old calls still work (default behavior unchanged)  

---

## Usage

### For Afternoon Peak Check (Automatic)

The afternoon peak check now automatically preserves slot 0:
```python
# Called from src/app_afternoon_peak_check.py
self.api.update_charge_settings_with_slot(
    device_sn=device_sn,
    charge_rate=80,
    target_soc=51,
    schedule_start=(14, 0),
    schedule_end=(16, 0),
    slot_number=1,
    preserve_slot_0=True,
    slot_0_start=(2, 0),
    slot_0_end=(5, 0)
)
```

### For Other Uses

You can now control preservation:

```python
# Clear all slots (old behavior)
api.update_charge_settings_with_slot(
    ...,
    preserve_slot_0=False  # or omit (default)
)

# Preserve slot 0 (new behavior)
api.update_charge_settings_with_slot(
    ...,
    preserve_slot_0=True,
    slot_0_start=(2, 0),
    slot_0_end=(5, 0)
)
```

---

## Files Modified

1. **`src/api/growatt.py`**
   - Enhanced `update_charge_settings_with_slot()` method
   - Added preservation logic
   - Updated docstring

2. **`src/app_afternoon_peak_check.py`**
   - Updated call to use preservation
   - Now reads tariff config for slot 0 times
   - Better logging with slot info

---

## Test Files Created

1. **`test_slot_preservation_with_flag.py`**
   - Tests basic preservation functionality
   - Shows parameters before/after

2. **`test_afternoon_peak_check_update.py`**
   - Simulates exact afternoon peak check scenario
   - Verifies slot preservation in realistic use case

3. **`test_slot_preservation.py`** (existing)
   - Original test (still works)

---

## Summary

**What Was Fixed:**
- Added `preserve_slot_0` parameter to preserve slot 0 when updating other slots
- Afternoon peak check now uses this parameter automatically
- Slot 0 remains active after slot 1 updates

**How It Works:**
- Method now accepts explicit slot 0 configuration
- If preserving, includes slot 0 params in API call
- Both slots can be active simultaneously

**Result:**
- ✅ Slot 0 (off-peak) no longer cleared
- ✅ Slot 1 (peak boost) works as intended
- ✅ Both schedules coexist properly
- ✅ Device behavior is now correct

**Testing:**
- ✅ Direct API test: PASSED
- ✅ Afternoon peak check simulation: PASSED
- ✅ Parameter verification: PASSED

**Status**: Ready for production! 🚀
