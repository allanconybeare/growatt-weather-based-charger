@echo off
:: Force UTF-8 for Windows environment
set PYTHONUTF8=1
chcp 65001 >nul

:: =====================================================
:: Growatt Charger Scheduled Task Runner
:: =====================================================
setlocal enabledelayedexpansion

:: Set the logging directory & file name
set "MYLOGDIR=%~dp0logs"
set "MYLOGFILE=%MYLOGDIR%\scheduled_task.log"

:: Ensure logs folder exists
if not exist "%MYLOGDIR%" mkdir "%MYLOGDIR%"

:: Housekeeping - rotate log if it exceeds 2MB (keep 2 backups)
if exist "%MYLOGFILE%" for %%F in ("%MYLOGFILE%") do if %%~zF gtr 2097152 (
    if exist "%MYLOGFILE%.2" del "%MYLOGFILE%.2"
    if exist "%MYLOGFILE%.1" ren "%MYLOGFILE%.1" "scheduled_task.log.2"
    ren "%MYLOGFILE%" "scheduled_task.log.1"
)

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

:: Start log section
echo ======================================== >> "%MYLOGFILE%"
echo Running Growatt Charger at %date% %time% >> "%MYLOGFILE%"
echo ======================================== >> "%MYLOGFILE%"

:: Config path
set "GROWATT_CONFIG=%SCRIPT_DIR%conf\growatt-charger.ini"

:: Set Solcast API key from environment variable or secure storage
:: The key should be stored as a Windows environment variable: SOLCAST_API_KEY
:: You can set it with: setx SOLCAST_API_KEY "your_key_here" (requires restart to take effect in scheduled tasks)
:: Or in this batch file for this execution only
if not defined SOLCAST_API_KEY (
    echo WARNING: SOLCAST_API_KEY environment variable not set >> "%MYLOGFILE%"
    echo Solcast API will fail unless api_key is in config file >> "%MYLOGFILE%"
)
set "SOLCAST_API_KEY=%SOLCAST_API_KEY%"
echo Working Directory: %CD% >> "%MYLOGFILE%"
echo Script Directory: %SCRIPT_DIR% >> "%MYLOGFILE%"
echo Config Path: %GROWATT_CONFIG% >> "%MYLOGFILE%"

:: Move into project directory
cd /d "%SCRIPT_DIR%"
echo Changed to: %CD% >> "%MYLOGFILE%"

:: Define path to Python executable inside venv
set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"

:: Log which Python path we’ll use
echo Checking Python executable: %PYTHON_EXE% >> "%MYLOGFILE%"

:: Verify Python exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python executable not found at %PYTHON_EXE% >> "%MYLOGFILE%"
    echo HINT: Your virtual environment may not be created or activated properly. >> "%MYLOGFILE%"
    echo Try running these commands manually: >> "%MYLOGFILE%"
    echo    python -m venv venv >> "%MYLOGFILE%"
    echo    venv\Scripts\activate >> "%MYLOGFILE%"
    echo    pip install -r requirements.txt >> "%MYLOGFILE%"
    echo ======================================== >> "%MYLOGFILE%"
    echo. >> "%MYLOGFILE%"
    exit /b 1
)

:: Log which Python will actually run (resolve symlink)
echo Using Python version: >> "%MYLOGFILE%"
"%PYTHON_EXE%" --version >> "%MYLOGFILE%" 2>&1
echo Python path resolved to: >> "%MYLOGFILE%"
"%PYTHON_EXE%" -c "import sys; print(sys.executable)" >> "%MYLOGFILE%" 2>&1

:: Run main Growatt script
echo Running Python script... >> "%MYLOGFILE%"
"%PYTHON_EXE%" "%SCRIPT_DIR%growatt_charger.py" >> "%MYLOGFILE%" 2>&1
set "PYTHON_EXIT=%ERRORLEVEL%"

:: Record exit code
echo Python exit code: %PYTHON_EXIT% >> "%MYLOGFILE%"

:: End section
echo Finished at %date% %time% >> "%MYLOGFILE%"
echo ======================================== >> "%MYLOGFILE%"
echo. >> "%MYLOGFILE%"

exit /b %PYTHON_EXIT%
