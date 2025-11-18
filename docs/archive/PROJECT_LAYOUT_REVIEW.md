# Project Layout Review & Reorganization Plan

## Current Layout

```
Root/
├── growatt_charger.py              ← ACTIVE: 22:00 main charger (wrapper to src/app.py)
├── morning_soc_check.py            ← ACTIVE: 05:00 morning check
├── view_performance.py             ← ACTIVE: analysis/review script
├── view_morning_soc.py             ← ACTIVE: analysis/review script
├── view_provider_comparison.py     ← ACTIVE: analysis/review script
│
├── bin/                            ← NOT USED: utility scripts
│   ├── get_actual_generation.py
│   ├── sunset_probe.py
│   ├── spa_api_probe.py
│   ├── analyze_thresholds.py       ← NEW (I created this here - WRONG PLACE)
│   └── peak_window_boost.py        ← NEW (I created this here - WRONG PLACE)
│
├── src/                            ← APPLICATION CODE
│   ├── app.py                      ← Main orchestration (called by growatt_charger.py)
│   ├── config/
│   ├── api/
│   └── utils/
│
├── modules/                        ← SHARED LOGIC
│   ├── forecast.py                 ← SOC target calculation
│   ├── forecast_providers/
│   ├── data_logger.py
│   ├── growatt_api.py
│   └── forecast_thresholds.py      ← NEW (I created this here - PROBABLY RIGHT)
│
├── create_*.ps1                    ← Task scheduler setup scripts
├── run_*.bat                       ← Batch wrappers for scheduled tasks
│
└── conf/                           ← Configuration
    └── growatt-charger.ini

```

## Issues with Current Layout

1. **`bin/` directory unused** — all active scripts are in root
2. **My new analysis tools in wrong places:**
   - `bin/analyze_thresholds.py` — Should be in root (for direct use)
   - `bin/peak_window_boost.py` — Should be in root or modules (depends on usage)
   - `modules/forecast_thresholds.py` — Correctly placed (shared logic)

3. **No 14:00 afternoon check yet** — needs to follow the pattern:
   - Root-level entry point: `afternoon_peak_check.py`
   - Task scheduler integration: `create_afternoon_peak_check_task.ps1`
   - Batch wrapper: `run_afternoon_peak_check.bat`

4. **Scheduled tasks pattern unclear** — currently:
   - `growatt_charger.py` → runs `src/app.py` at 22:00
   - `morning_soc_check.py` → standalone script at 05:00
   - Need: `afternoon_peak_check.py` → at 14:00

---

## Proposed Reorganization

### Option A: Keep Root-Level Scripts (Current Pattern - RECOMMENDED)

```
Root/
├── SCHEDULED TASKS (22:00, 05:00, 14:00):
│   ├── growatt_charger.py              ← 22:00: Calculate SOC, apply charge
│   ├── morning_soc_check.py            ← 05:00: Capture post-charge SOC
│   ├── afternoon_peak_check.py         ← NEW 14:00: Decide if boost needed
│   │
│   ├── create_growatt_charger_daily_task.ps1
│   ├── create_morning_soc_task.ps1
│   ├── create_afternoon_peak_task.ps1  ← NEW
│   │
│   ├── run_growatt_charger.bat
│   ├── run_morning_soc_check.bat
│   └── run_afternoon_peak_check.bat    ← NEW
│
├── ANALYSIS/REVIEW SCRIPTS (Manual use):
│   ├── view_performance.py
│   ├── view_morning_soc.py
│   ├── view_provider_comparison.py
│   ├── analyze_thresholds.py           ← MOVE FROM bin/ (weekly/monthly review)
│   └── review_peak_decisions.py        ← NEW (analyze 14:00 boost decisions)
│
├── PROBE/DEBUG SCRIPTS (Utilities):
│   ├── bin/
│   │   ├── get_actual_generation.py
│   │   ├── sunset_probe.py
│   │   └── spa_api_probe.py
│   └── (or move these to root too if used often)
│
├── src/
│   ├── app.py                         ← 22:00 logic (called by growatt_charger.py)
│   ├── app_afternoon_peak_check.py    ← NEW 14:00 logic (called by afternoon_peak_check.py)
│   ├── config/
│   ├── api/
│   └── utils/
│
├── modules/
│   ├── forecast.py                    ← Old coverage-based (keep for reference)
│   ├── forecast_thresholds.py         ← New forecast-based (tunable)
│   ├── forecast_providers/
│   ├── data_logger.py
│   └── growatt_api.py
│
└── conf/
    └── growatt-charger.ini
```

**Rationale:**
- Root-level scripts = "entry points" (run by Windows Task Scheduler)
- `src/` = core business logic called by entry points
- `modules/` = shared utilities imported by `src/`
- `bin/` = optional debug/utility scripts

---

## Immediate Actions

### 1. Move Analysis Scripts to Root

```powershell
# From bin/ to root
Move-Item bin/analyze_thresholds.py analyze_thresholds.py
Move-Item bin/peak_window_boost.py peak_window_boost.py
```

After move, these work as:
```bash
python analyze_thresholds.py              # Weekly review
python peak_window_boost.py               # Test logic
```

### 2. Create Afternoon Peak Check (14:00)

**File:** `afternoon_peak_check.py` (root, entry point)
```python
"""Entry point for 14:00 afternoon peak-window decision."""

from src.app_afternoon_peak_check import main

if __name__ == '__main__':
    main()
```

**File:** `src/app_afternoon_peak_check.py` (core logic)
```python
"""14:00 peak-window boost decision logic."""

import os
import sys
import asyncio
from datetime import datetime

from .api import GrowattAPI
from .config import ConfigManager
from .utils import setup_logging, get_logger
from modules.forecast_providers import ForecastManager
from bin.peak_window_boost import (
    should_boost_battery_for_peak_window,
    calculate_peak_window_boost_target
)
from modules.data_logger import DataLogger

class AfternoonPeakChecker:
    """Checks at 14:00 if battery boost is needed for 16:00-19:00 peak window."""

    def __init__(self, config_path: str):
        # Initialize logging, config, API, forecast manager
        pass

    async def run(self) -> None:
        """Main logic: fetch forecast, current SOC, decide if boost."""
        # Login
        # Get remaining forecast (14:00 to sunset)
        # Get current SOC
        # Call should_boost_battery_for_peak_window()
        # If boost: update charge settings
        # Log decision
        pass

async def main():
    checker = AfternoonPeakChecker('conf/growatt-charger.ini')
    await checker.run()

if __name__ == '__main__':
    asyncio.run(main())
```

### 3. Create Task Scheduler Integration

**File:** `create_afternoon_peak_check_task.ps1`
```powershell
# Register scheduled task for 14:00 (similar to existing create_*.ps1 files)
$TaskName = "GrowattAfternoonPeakCheck"
$Time = "14:00"
$ScriptPath = "C:\Path\To\run_afternoon_peak_check.bat"

# (Use same pattern as create_growatt_charger_daily_task.ps1)
```

**File:** `run_afternoon_peak_check.bat`
```batch
@echo off
REM Run afternoon peak check at 14:00
cd /d "%~dp0"
python afternoon_peak_check.py
```

### 4. Create Review Script for Peak Decisions

**File:** `review_peak_decisions.py` (root, manual use)
```python
"""Review and analyze 14:00 peak-boost decisions."""

import csv
from pathlib import Path
from datetime import datetime, timedelta

def review_peak_boost_decisions(days: int = 7):
    """Show decisions and outcomes from last N days."""
    # Read peak_decisions log
    # Group by: [Boost Decision] [Actual Generation] [Afternoon SOC Change] [Outcome]
    # Calculate: "How many times did boost prevent grid import?"
    pass

if __name__ == '__main__':
    review_peak_boost_decisions(7)
```

---

## Updated File Structure (After Reorganization)

```
Root/
├── Scheduled Tasks (Windows Task Scheduler):
│   ├── growatt_charger.py              ← 22:00: overnight charging
│   ├── morning_soc_check.py            ← 05:00: capture post-charge SOC
│   ├── afternoon_peak_check.py         ← NEW 14:00: decide peak boost
│   │
│   ├── create_growatt_charger_daily_task.ps1
│   ├── create_morning_soc_task.ps1
│   ├── create_afternoon_peak_check_task.ps1  ← NEW
│   │
│   ├── run_growatt_charger.bat
│   ├── run_morning_soc_check.bat
│   └── run_afternoon_peak_check.bat    ← NEW
│
├── Analysis/Review Scripts:
│   ├── view_performance.py             ← Manual: weekly performance review
│   ├── view_morning_soc.py             ← Manual: morning captures
│   ├── view_provider_comparison.py     ← Manual: forecast provider comparison
│   ├── analyze_thresholds.py           ← MOVED: weekly threshold analysis
│   └── review_peak_decisions.py        ← NEW: weekly peak-boost review
│
├── bin/ (Optional Utilities):
│   ├── get_actual_generation.py
│   ├── sunset_probe.py
│   └── spa_api_probe.py
│
├── src/
│   ├── app.py                          ← 22:00 orchestration
│   ├── app_afternoon_peak_check.py     ← NEW 14:00 orchestration
│   ├── config/
│   ├── api/
│   └── utils/
│
├── modules/
│   ├── forecast.py                     ← Legacy (reference)
│   ├── forecast_thresholds.py          ← New forecast-based thresholds
│   ├── forecast_providers/
│   ├── data_logger.py
│   ├── growatt_api.py
│   └── peak_window_boost.py            ← MOVED: peak-boost logic
│
├── conf/
│   └── growatt-charger.ini
│
└── output/
    ├── predictions.csv
    ├── actuals.csv
    ├── performance_summary.csv
    ├── peak_decisions.csv              ← NEW: log of 14:00 decisions
    └── threshold_analysis_report.csv
```

---

## Implementation Order

**Week 1:**
1. [ ] Move `analyze_thresholds.py` to root
2. [ ] Move `peak_window_boost.py` to modules (it's helper logic)
3. [ ] Update imports in both files
4. [ ] Test both still work from new locations

**Week 2:**
1. [ ] Create `src/app_afternoon_peak_check.py`
2. [ ] Create `afternoon_peak_check.py` (root entry point)
3. [ ] Test logic manually

**Week 3:**
1. [ ] Create task scheduler integration files
2. [ ] Test scheduled execution
3. [ ] Create `review_peak_decisions.py`

**Week 4:**
1. [ ] Ongoing: weekly reviews
2. [ ] Monitor peak-boost decisions + outcomes

---

## Summary

**Current state:** All scheduled tasks in root, `bin/` not used, analysis scripts also in root. This is CORRECT!

**What I got wrong:** Put new analysis tools in `bin/` instead of root.

**Fix:**
- Move `analyze_thresholds.py` → root (for weekly manual use)
- Move `peak_window_boost.py` → modules/ (as shared logic)
- Create new `afternoon_peak_check.py` → root (14:00 entry point)
- Create new `src/app_afternoon_peak_check.py` → logic
- Create task scheduler integration files

**Result:** Clean, consistent pattern where all scheduled tasks are root entry points, all core logic is in `src/`, all shared utilities in `modules/`.

Does this make sense? Should I start the reorganization?
