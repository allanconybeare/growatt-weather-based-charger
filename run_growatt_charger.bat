@echo off
echo Running Growatt Charger at %date% %time%

:: Get the directory where the batch file is located
set SCRIPT_DIR=%~dp0

:: Set config path to local directory
set GROWATT_CONFIG=%SCRIPT_DIR%conf\growatt-charger.ini

:: Change to the project directory
cd /d "%SCRIPT_DIR%"

:: Activate virtual environment and run script
call venv\Scripts\activate.bat
python "%SCRIPT_DIR%growatt_charger.py"

:: Deactivate virtual environment
deactivate

echo Finished at %date% %time%