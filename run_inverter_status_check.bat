@echo off
:: Inverter status check wrapper.
:: Run this directly or via Task Scheduler to detect when the inverter goes offline.
:: Exit code 0 = healthy, 1 = offline/fault, 2 = script error.

set "MYLOGDIR=%~dp0logs"
set "MYLOGFILE=%MYLOGDIR%\inverter_status_check.log"

:: Ensure logs folder exists
if not exist "%MYLOGDIR%" mkdir "%MYLOGDIR%"

echo ======================================== >> "%MYLOGFILE%"
echo Running Inverter Status Check at %date% %time% >> "%MYLOGFILE%"
echo ======================================== >> "%MYLOGFILE%"

:: Force UTF-8
set PYTHONUTF8=1
chcp 65001 >nul

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"

:: Housekeeping - trim log if it exceeds 500KB
if exist "%MYLOGFILE%" for %%F in ("%MYLOGFILE%") do if %%~zF gtr 500000 del "%MYLOGFILE%"

:: Run the check
"%PYTHON_EXE%" "%~dp0check_inverter_status.py" >> "%MYLOGFILE%" 2>&1
set "PYTHON_EXIT=%ERRORLEVEL%"

echo Python exit code: %PYTHON_EXIT% >> "%MYLOGFILE%"

:: -----------------------------------------------------------------------
:: Optional: send a Windows toast notification when the inverter is offline.
:: Uncomment the block below if you want a pop-up alert on this machine.
:: -----------------------------------------------------------------------
:: if %PYTHON_EXIT% == 1 (
::     powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Growatt inverter is OFFLINE or has lost communication. Check the solar board switch.', 'Inverter Alert', 'OK', 'Warning')"
:: )

exit /b %PYTHON_EXIT%
