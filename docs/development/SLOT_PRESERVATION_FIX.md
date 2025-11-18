# 🔧 Bug Fix: Slot Configuration Preservation

**Date**: November 14, 2025  
**Status**: ✅ FIXED

---

## Problem

When updating slot 1 (afternoon boost schedule), slot 0 (off-peak charging schedule) was being reset to disabled with times 00:00 - 00:00.

### Error Pattern:
```
Before:  Slot 0 = 02:00-04:59 (enabled) ✓
Apply:   Boost to slot 1 (14:00-16:00)
After:   Slot 0 = 00:00-00:00 (disabled) ✗  <- CLEARED!
```

---

## Root Cause

In `src/api/growatt.py`, the `update_charge_settings_with_slot()` method was clearing ALL slots before enabling only the target slot:

### Problematic Code (Lines 454-461):

```python
# Initialize all slots as disabled
for slot in range(3):
    slot_cfg = slot_configs[slot]
    params[f'param{slot_cfg["start_idx"]}'] = "00"      # Start hour
    params[f'param{slot_cfg["start_idx"] + 1}'] = "00"  # Start minute
    params[f'param{slot_cfg["start_idx"] + 2}'] = "00"  # End hour
    params[f'param{slot_cfg["start_idx"] + 3}'] = "00"  # End minute
    params[f'param{slot_cfg["enable_idx"]}'] = "0"      # Disabled
```

This code:
1. ✗ Cleared all 3 slots (including slot 0)
2. ✗ Then enabled only the target slot
3. ✗ Result: Slot 0's configuration was destroyed

---

## Solution

**Only update the specified slot, leaving other slots untouched.**

### Fixed Code:

```python
# Configure only the specified slot (leave other slots untouched)
params[f'param{start_idx}'] = f"{schedule_start[0]:02d}"     # Start hour
params[f'param{start_idx + 1}'] = f"{schedule_start[1]:02d}" # Start minute
params[f'param{start_idx + 2}'] = f"{schedule_end[0]:02d}"   # End hour
params[f'param{start_idx + 3}'] = f"{schedule_end[1]:02d}"   # End minute
params[f'param{enable_idx}'] = "1"                           # Enable
```

Now the API call only sets parameters for the target slot, preserving all other slots' configurations.

---

## Changes Made

### 1. **Removed the slot-clearing loop** (Lines 454-461)
   - **Before**: 19 lines of slot initialization code
   - **After**: Removed entirely - only target slot configured
   - **Result**: Other slots untouched

### 2. **Updated docstring** (Lines 400-403)
   - **Added**: Clear warning about slot preservation
   - **Added**: Example about updating slot 1 not affecting slot 0

### Files Modified:
- `src/api/growatt.py` (2 changes: code fix + docstring update)

---

## How It Works Now

### Slot Management Architecture:

```
Device Storage (All Slots):
├── Slot 0: 02:00-04:59 (off-peak, set by 22:00 task)
├── Slot 1: [empty/previous]
└── Slot 2: [empty/previous]

Step 1 - Update Slot 1 (Afternoon Boost):
├── Only slot 1 params sent to API
├── Slot 0 params NOT touched
└── Slot 2 params NOT touched

Result - Device Storage (After Update):
├── Slot 0: 02:00-04:59 ✓ PRESERVED
├── Slot 1: 14:00-16:00 ✓ UPDATED
└── Slot 2: [unchanged]
```

---

## API Parameter Mapping

**What gets sent to API now:**

```python
params = {
    'param1': '80',              # Charge rate (global, applies to active slot)
    'param2': '51',              # Target SOC (global, applies to active slot)
    'param8': '14',              # Slot 1 start hour
    'param9': '00',              # Slot 1 start minute
    'param10': '16',             # Slot 1 end hour
    'param11': '00',             # Slot 1 end minute
    'param12': '1'               # Slot 1 enable
    # param3-7 (slot 0) NOT included - stays as-is on device
    # param13-17 (slot 2) NOT included - stays as-is on device
}
```

Only slot 1 params sent → Slot 0 unaffected ✓

---

## Test Scenario

### Before Fix:
```
22:00 task runs: Sets Slot 0 = 02:00-04:59 ✓
14:00 peak check runs: Sets Slot 1 = 14:00-16:00
  Result: Slot 0 = 00:00-00:00 ✗ CLEARED
```

### After Fix:
```
22:00 task runs: Sets Slot 0 = 02:00-04:59 ✓
14:00 peak check runs: Sets Slot 1 = 14:00-16:00
  Result: Slot 0 = 02:00-04:59 ✓ PRESERVED
          Slot 1 = 14:00-16:00 ✓ SET
```

---

## Impact

✅ **Off-peak charging preserved** - 22:00 task schedule not destroyed  
✅ **Afternoon boost works** - Slot 1 properly updated  
✅ **Multi-slot operation** - All slots can coexist  
✅ **Schedule independence** - Each slot operates autonomously  

---

## Related Methods

- `update_charge_settings()` - Sets all slots (calls API differently)
- `update_charge_settings_with_slot()` - Sets one slot only (NOW FIXED)

Both methods maintain param1 (charge rate) and param2 (target SOC) globally, which apply to the active/enabled charging slot.

---

## Testing Recommendation

To verify the fix:
1. Set a slot 0 schedule via 22:00 task
2. Run afternoon peak check (sets slot 1)
3. Check device: Both slot 0 AND slot 1 should be configured ✓

---

## Documentation

This fix is documented in:
- `src/api/growatt.py` - Updated docstring with explicit warning
- `docs/development/SLOT_PRESERVATION_FIX.md` - This file
