@echo off
REM run_afternoon_peak_check.bat
REM Wrapper for afternoon peak-window check executed by Task Scheduler at 14:00

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run the afternoon peak check script
python afternoon_peak_check.py conf\growatt-charger.ini

if errorlevel 1 (
    echo Afternoon peak check failed with exit code %errorlevel%
    exit /b %errorlevel%
)

exit /b 0
