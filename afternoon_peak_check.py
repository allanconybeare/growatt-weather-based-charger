#!/usr/bin/env python
"""Wrapper script for 14:00 afternoon peak-window boost decision."""

import asyncio
import os
import sys

from src.app_afternoon_peak_check import main

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    asyncio.run(main())
