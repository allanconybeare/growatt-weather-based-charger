#!/usr/bin/env python
"""Wrapper script for 14:00 afternoon peak-window boost decision."""

import asyncio
import os
import sys
import traceback
from datetime import datetime

from src.app_afternoon_peak_check import main

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        with open("logs/afternoon-peak-check-fatal.log", "a") as f:
            f.write(f"{datetime.now()}\n")
            f.write(f"error: {e}\n")
            f.write(traceback.format_exc())
            f.write("\n")
        raise
