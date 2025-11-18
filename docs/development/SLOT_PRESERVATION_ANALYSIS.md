# 🔍 Slot Preservation Analysis

**Date**: November 14, 2025

## Problem Statement (Original)

> "There is an issue though, slot #0 was reset to disabled and 00:00 - 00:00, I don't know what that cleared down"

## Architecture

**22:00 Task** (off-peak charging overnight):
- Calls: `api.update_charge_settings()`
- Sets: Slot 0 to off-peak window (e.g., 02:00-04:59)
- Side effect: Clears slots 1-2 (by design)

**14:00 Task** (afternoon peak boost):
- Calls: `api.update_charge_settings_with_slot(slot_number=1)`
- Sets: Slot 1 to peak window (e.g., 14:00-16:00)
- Question: Does this clear slot 0?

## Analysis

### Current Code Behavior

In `update_charge_settings_with_slot()`:

```python
# Initialize all slots with disabled state
for slot in range(3):
    # ... sets all slots to disabled

# Then enable and configure ONLY the specified slot
params[f'param{start_idx}'] = ...  # Configure target slot only
```

### Does This Clear Slot 0?

**YES - But Only When Slot 0 Was Set!**

Timeline:
```
22:00 → Set Slot 0 (02:00-04:59) ✓
14:00 → Set Slot 1 (14:00-16:00)
        Initializes ALL slots to disabled
        Then enables slot 1
        Result: Slot 0 = CLEARED ✗
```

## Root Cause

The method initializes all slots to disabled before enabling target slot. This is necessary because **the API requires all parameters** (param3-17) to be sent in every request.

If we don't send all parameters, the API returns **error 509**.

## The Dilemma

**Option A**: Send all parameters, initialize untouched slots to disabled
- ✓ API accepts the request (no 509 error)
- ✗ Clears other slots (destroys existing schedules)

**Option B**: Send only target slot parameters, skip others
- ✓ Preserves other slots
- ✗ API returns error 509 (invalid parameters)

**Option C**: Read current state first, then update one slot preserving others
- ✓ Preserves all slots
- ✗ No API method to read current slot configuration

## Solution Options

### Option 1: Accept the Current Behavior (Current Implementation)
- Pro: Simple, works, no 509 errors
- Con: Tasks overwrite each other's slots
- When: OK if 22:00 task always runs after 14:00 task finishes

### Option 2: Coordinate Slot Usage by Time
- Pro: Each task knows when to preserve
- Con: Complex coordination logic
- Approach: 14:00 task updates slot 1, but 22:00 task ALSO includes slot 1 config (disabled)

### Option 3: Use Single Slot Architecture
- Pro: Simplest - one task, one slot
- Con: Need to redesign peak boost logic
- Approach: Use only slot 0, update rate/SOC  based on time of day

### Option 4: Request Growatt API Enhancement
- Get API method to: Read current slot config OR Update single slot without affecting others
- Timeline: Would need coordination with Growatt

## Recommendation

**For now: Accept Option 1 (current behavior) because:**

1. **Execution sequence is correct**: 14:00 task runs FIRST in the afternoon, 22:00 task runs LATER
2. **Temporary schedule is OK**: Afternoon boost (slot 1) is temporary - only needed 14:00-16:00
3. **Off-peak is re-set daily**: The 22:00 task will re-establish slot 0 anyway before it's needed
4. **No data loss**: Users don't lose anything - both schedules work as designed

Timeline that works:
```
14:00 → Set slot 1 (afternoon boost 14:00-16:00) ✓
16:01 → Afternoon boost ends, device uses default
...
22:00 → Set slot 0 (off-peak 02:00-04:59) ✓
        Clears slot 1 (which is fine - already used)
02:00 → Off-peak charging starts as scheduled ✓
```

## Alternative: Better Architecture

If separation is truly needed, consider:
- **Always include both slots** in every update call
- Task that updates slot 1 also preserves slot 0 info by re-sending last known slot 0 config
- But this requires remembering/tracking state between calls

Or simpler:
- **22:00 task includes**: slot 0 (off-peak) + slot 1 (disabled)
- **14:00 task includes**: slot 0 (copy of 22:00 config) + slot 1 (peak boost)
- But this requires 14:00 task to know what 22:00 will set!

## Conclusion

**Current implementation is acceptable** because the execution order and timing work in the users' favor. The "clearing" is actually just inactive schedule slots being reset to disabled, which is harmless.

To truly preserve without losing state, would need either:
1. State persistence between tasks (file/DB storage)
2. Growatt API enhancement to read current config
3. Different architectural approach (single slot with time-based rate/SOC adjustment)

---

**Status**: Current implementation working as designed ✓
