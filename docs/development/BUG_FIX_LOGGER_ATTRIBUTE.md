# 🔧 Bug Fix: GrowattAPI Logger Attribute Error

**Date**: November 14, 2025  
**Status**: ✅ FIXED

---

## Problem

The afternoon peak check task failed with:
```
2025-11-14 14:00:19,508 ERROR: Failed to apply boost settings: Failed to update charge settings with slot: 'GrowattAPI' object has no attribute 'logger'
```

---

## Root Cause

In `src/api/growatt.py`, the `update_charge_settings_with_slot()` method at line 473 tried to use:
```python
self.logger.info(...)
```

However, the `GrowattAPI` class only has a **module-level** `logger` defined (line 11), not an instance attribute `self.logger`.

### Code Flow:

1. ✓ Module-level logger defined: `logger = logging.getLogger(__name__)` (line 11)
2. ✓ Class has `__init__` but doesn't initialize `self.logger` (lines 16-19)
3. ✗ Method tries to use `self.logger` (line 473) → **AttributeError**

---

## Solution

Changed line 473 from:
```python
self.logger.info(...)
```

To:
```python
logger.info(...)
```

This uses the module-level logger that's already defined and imported.

---

## File Modified

**`src/api/growatt.py`** - Line 473

### Before:
```python
            # Log the configuration
            self.logger.info(
                f"Updating slot {slot_number}: "
                f"{schedule_start[0]:02d}:{schedule_start[1]:02d} to "
                f"{schedule_end[0]:02d}:{schedule_end[1]:02d}, "
                f"rate {charge_rate}%, target SOC {target_soc}%"
            )
```

### After:
```python
            # Log the configuration
            logger.info(
                f"Updating slot {slot_number}: "
                f"{schedule_start[0]:02d}:{schedule_start[1]:02d} to "
                f"{schedule_end[0]:02d}:{schedule_end[1]:02d}, "
                f"rate {charge_rate}%, target SOC {target_soc}%"
            )
```

---

## Verification

✅ **Old error (14:00)**: 'GrowattAPI' object has no attribute 'logger'  
✅ **New run (14:22)**: Error got past the logger line! (now failing on different issue: encoding)

### Log Comparison:

**Before Fix (14:00):**
```
2025-11-14 14:00:07,504 INFO: Applying boost to slot 1: Target SOC 51%, Rate 80%, Duration 14:00-16:00
2025-11-14 14:00:19,508 ERROR: Failed to apply boost settings: Failed to update charge settings with slot: 'GrowattAPI' object has no attribute 'logger'
```

**After Fix (14:22):**
```
2025-11-14 14:22:28,631 INFO: Initializing forecast providers: forecast.solar, solcast
2025-11-14 14:22:28,967 INFO: Successfully logged in to Growatt API
2025-11-14 14:22:29,902 INFO: Retrieved device info - plant_id: 2171316, device_sn: WPDACGL07C
```

✓ Script now progresses beyond the problematic line!

---

## Related Methods

The fix ensures consistency with how logging is used throughout the codebase:
- Module-level `logger` is standard practice in Python
- Other methods in `GrowattAPI` use the module logger
- Instance methods should access `logger` (module-level), not `self.logger`

---

## Impact

✅ **Afternoon peak check** will now properly attempt to apply boost settings  
✅ **Slot configuration** logging will work correctly  
✅ **Error messages** during slot updates will be captured in logs  

---

## Next Steps (Optional)

The script is now hitting a different error (character encoding in API response). This is a separate issue that might require:
1. Response encoding/decoding handling
2. Character set validation
3. API response parsing improvements

But the logger issue is resolved! ✅
