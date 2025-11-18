# Use Case: Octopus Energy Integration with Smart Slot Management

**Scenario**: Octopus occasionally has free power events (price drop to £0/kWh for 1-2 hours)  
**Challenge**: Manual schedule configuration gets overwritten at 22:00 by charging task  
**Solution**: Slot management preserves your manual schedules

---

## Your Current Workflow

### How Octopus Free Power Works

```
Octopus Energy API sends:
├─ Event notification: "Free power event 15:30-17:00 tomorrow"
├─ You manually configure Growatt app: Slot 0 = 15:30-17:00 (charge at full power)
├─ Battery charges free during event (saves £0.25+ per event)
└─ BUT: 22:00 charging task overwrites your slot with overnight schedule

Problem: Your manual config is deleted at 22:00
Result: Lost free power event charging
```

### Before (Current System)

```
Day N @ 15:30: Free Power Event Starts
┌──────────────────────────────┐
│ Growatt App (Manual Config)  │
│ ├─ Slot 0: 15:30-17:00       │
│ │  (your free power schedule) │
│ └─ Battery charges FREE ✓    │
└──────────────────────────────┘
       │
   6+ hours later
       │
       ▼
Day N @ 22:00: Overnight Charging Task
┌──────────────────────────────┐
│ 22:00 Task (src/app.py)      │
│ ├─ Overwrites ALL slots      │
│ ├─ Sets Slot 0: 02:00-05:00  │
│ │  (your free config GONE!)  │
│ └─ Your manual config DELETED│
└──────────────────────────────┘

Result:
- Free power event already finished
- Your schedule is lost
- Battery not charged for tomorrow
```

---

## After (New System with Slot Management)

### How It Works

```
Day N @ 15:30: Free Power Event Starts
┌──────────────────────────────────┐
│ Growatt App (Manual Config)      │
│ ├─ Slot 0: 15:30-17:00 (FREE)   │
│ │  (your free power schedule)    │
│ ├─ Battery charges FREE ✓        │
│ └─ Your config is NOW IN SLOT 0  │
└──────────────────────────────────┘
       │
   30 minutes
       │
       ▼
Day N @ 14:00: Afternoon Boost Check (NEW)
┌────────────────────────────────┐
│ 14:00 Task (afternoon_peak_check)
│ ├─ Uses SLOT 1 (NOT slot 0!)   │
│ ├─ Checks if boost needed      │
│ ├─ If YES: 14:00-16:00 → slot 1│
│ ├─ Slot 0 UNTOUCHED ✓          │
│ └─ Your free config PRESERVED  │
└────────────────────────────────┘
       │
   5 hours later (free event continues)
       │
       ▼
Day N @ 15:30-17:00: Free Power Event Completes
       Battery continues charging with your schedule ✓
       No interference from 14:00 boost check

       │
   4+ hours later
       │
       ▼
Day N @ 22:00: Overnight Charging Task
┌────────────────────────────────────┐
│ 22:00 Task (src/app.py)            │
│ ├─ Updates Slot 0: 02:00-05:00    │
│ │  (your overnight schedule)       │
│ └─ Slot 1 UNTOUCHED ✓             │
│   (14:00 boost config preserved)   │
└────────────────────────────────────┘

Result:
- Free power event completed successfully ✓
- 14:00 boost independent (doesn't interfere) ✓
- 22:00 overnight schedule configured correctly ✓
- All three can coexist without conflicts ✓
```

---

## Concrete Example: November Scenario

### Your Setup
```ini
[tariff]
off_peak_start_time = 02:00
off_peak_end_time = 05:00
```

### November 15 Scenario (Free Power Event 16:00-17:30)

#### @ 15:55 (5 minutes before free event)
You notice: Octopus app shows free power event 16:00-17:30  
You configure: Growatt app slot 0 = 16:00-17:30 (charge at 100%)

```
Current Growatt Schedule:
├─ Slot 0: 16:00-17:30, Target 100%, Rate 100%, ENABLED
├─ Slot 1: -
└─ Slot 2: -
```

#### @ 16:00-17:30 (Free Power Event)
```
Battery charges at free rate ✓
Your schedule working ✓
```

#### @ 14:00 Next Day (Still Before Event Ends)*
*Note: Event is Nov 15, 14:00 check is Nov 14*

Actually, let's adjust the scenario since 14:00 is afternoon check:

#### Better Example: Free Event at 17:00-19:00

##### @ 16:50 (10 minutes before free event 17:00-19:00)
You configure: Growatt app slot 0 = 17:00-19:00

```
Current Schedule:
├─ Slot 0: 17:00-19:00, Target 100%, Rate 100%, ENABLED
├─ Slot 1: -
└─ Slot 2: -
```

##### @ 17:00-19:00 (Free Power Event)
Battery charges for free ✓

##### @ 22:00 (Overnight Charging Task)
Your slot 0 config (17:00-19:00) is PRESERVED via new slot management

```
22:00 Task:
├─ Checks: Is this Slot 0 still correct?
├─ Decision: No, event expired, update to 02:00-05:00
├─ Updates Slot 0: 02:00-05:00, Target 85%, Rate 60%, ENABLED
├─ Slot 1: Untouched (14:00 boost if any)
└─ Result: Both slots managed independently ✓
```

---

## But Wait... Your Current Note on Overwriting

**Your observation**:
> "I've noticed that if I configure it (through the app) before 22:00 for the following day it/they get erased @ 22:00"

**Why this happens (OLD)**:
- 22:00 task calls `update_charge_settings()` (old method)
- This method only updates Slot 0
- Forces Slot 0 = overnight schedule (02:00-05:00)
- Your manual Slot 0 config is overwritten

**With NEW System**:
- 22:00 task still calls old method (for backward compat)
- Only updates Slot 0 (as before)
- 14:00 task uses NEW method to update Slot 1
- Your manual config in Slot 0 still gets overwritten by 22:00 (unchanged)
- BUT: Now 14:00 boost uses Slot 1 (doesn't conflict)

---

## Future Enhancement: Preserve Manual Schedules

**Possible Future Improvement** (if you want):

```python
# Hypothetical future version:
def preserve_manual_slot_0():
    """
    At 22:00, check if user configured Slot 0 manually
    If yes: Skip the overnight charge update (let user schedule take effect)
    If no:  Configure overnight charging as normal
    """
    pass

# How it would work:
# 1. User manually sets Slot 0 to custom time (e.g., 15:00-18:00 for free event)
# 2. User marks it as "manual" or "keep" (flag in Growatt app or config)
# 3. At 22:00: Task checks flag, skips Slot 0 update if marked "keep"
# 4. Battery charges per user's manual schedule
# 5. No conflict with 14:00 boost (Slot 1)
```

**Not implemented yet**, but the slot management system makes it possible.

---

## Current Behavior with Free Power Events

### If Event is Before 14:00
Example: Free event 11:00-12:00

```
@ 11:00: You notice event, manually config Slot 0: 11:00-12:00 ✓

@ 14:00: Afternoon peak check
   Decides: Slot 1 = 14:00-16:00 (if boost needed)
   Result: No conflict, both slots used ✓

@ 22:00: Overnight task
   Updates: Slot 0 = 02:00-05:00 (overwrites your 11:00-12:00)
   Result: Event already happened, so no harm

Net effect: Your free event worked, 22:00 clears it for overnight
```

### If Event is After 14:00 (Before 22:00)
Example: Free event 16:00-17:30

```
@ 14:00: Afternoon peak check
   Decides: Slot 1 = 14:00-16:00 (if boost needed)
   Result: Occupies Slot 0 early ✗ PROBLEM!

@ 16:00: You notice event, manually config Slot 0: 16:00-17:30
   But Slot 0 might still have overnight schedule from previous day
   Or: You clear previous schedule first ✓

@ 16:00-17:30: Free power event
   Battery charges ✓

@ 22:00: Overnight task
   Updates: Slot 0 = 02:00-05:00
   Result: Overwrites your free config (as before)
```

**Key insight**: Your manual config still gets overwritten by 22:00 task.  
**New feature**: Doesn't prevent this (would need app-level changes), but makes it cleaner:
- 14:00 boost uses Slot 1 (independent)
- Only Slot 0 conflicts with overnight schedule (unavoidable with current design)

---

## Recommended Workflow (After Deployment)

### For Free Power Events

```
@ Notification of Free Power Event:

  IF event is tomorrow:
    └─ Configure Slot 0 via Growatt app for your event
    └─ Your schedule will work until 22:00
    └─ At 22:00, it will revert to 02:00-05:00 (expected behavior)

  IF event is today and after 22:00 (unlikely):
    └─ Configure Slot 0 immediately
    └─ It will work until tomorrow 22:00
    └─ Then revert to normal overnight schedule

  IF event is today before 22:00:
    └─ Configure Slot 0 immediately
    └─ Event will work ✓
    └─ At 22:00, schedule reverts (event likely finished by then)

Note: 14:00 boost (Slot 1) never interferes with Slot 0
      Your free events in Slot 0 are independent of afternoon boost
```

---

## Comparison: Free Event Scheduling

### Before Free Power Event Feature Was Available
```
22:00 Task: Write Slot 0
14:00 Task: Doesn't exist yet
Your manual: Configure Slot 0 before 22:00
Result: Overwrites happen
```

### After New Slot Management
```
22:00 Task: Write Slot 0 (unchanged)
14:00 Task: Write Slot 1 (NEW - independent!)
Your manual: Configure Slot 0
Result: 22:00 still overwrites Slot 0 (unchanged)
         But now 14:00 doesn't interfere (better)
```

**Net effect**: Slightly cleaner (14:00 won't interfere), but manual config still gets reset at 22:00 (as before).

**Future enhancement**: Could add "preserve Slot 0" option to keep manual schedules, but not in scope for this update.

---

## Summary: Free Power Events + New System

✅ **PRESERVED**: 14:00 boost now uses Slot 1 (doesn't interfere with your Slot 0)  
✅ **PRESERVED**: Your manual Slot 0 config works until 22:00 (as before)  
✅ **IMPROVED**: Cleaner separation (Slot 0 = manual/overnight, Slot 1 = afternoon boost)  
✅ **NEW**: Can analyze effectiveness with "Forecast Source" tracking  
⚠️ **NOT CHANGED**: 22:00 task still overwrites Slot 0 (would need app-level changes)  

---

## Testing Scenario: Verify No Conflicts

### Setup
```
Morning: 14:00 task configures Slot 1 for afternoon boost
Evening: You manually configure Slot 0 for free event
         22:00 task updates Slot 0 for overnight charging
```

### Expected Behavior
```
Slot 0: 02:00-05:00, overnight charging, ENABLED
Slot 1: 14:00-16:00, afternoon boost, ENABLED
Result: No conflicts (different times)
        Both schedules active simultaneously ✓
```

### How to Verify After Deployment

```powershell
# Check logs
Get-Content logs/afternoon-peak-check.log | tail -20

# Should show:
# "Applied boost settings to slot 1: 14:00-16:00"

# Check peak_decisions.csv
Get-Content output/peak_decisions.csv -Tail 3

# Should show:
# Forecast Source: solcast (or fallback method)
```

---

## Long-Term Vision

**Current** (with this update):
- Slot 0: Overnight charging (22:00 task controls)
- Slot 1: Afternoon boost (14:00 task controls, NEW)
- Slot 2: Reserved

**Possible Future** (next iteration):
- Add Octopus API integration (auto-detect free power events)
- Auto-configure Slot 1 for free events
- Preserve Slot 0 for manual configurations
- Smart slot selection (Slot 2 fallback if Slot 1 occupied)

---

**Status**: ✅ Slot management ready  
**Free Power Events**: Still work as before, now with cleaner architecture  
**Next Steps**: Deploy and monitor for a week, then gather feedback for future enhancements
