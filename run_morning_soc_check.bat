@echo off
:: Set the logging directory & file name
set "MYLOGDIR=%~dp0logs"
set "MYLOGFILE=%MYLOGDIR%\morning_soc.log"

:: Ensure logs folder exists
if not exist "%MYLOGDIR%" mkdir "%MYLOGDIR%"

echo ======================================== >> "%MYLOGFILE%"
echo Running Morning SOC Check at %date% %time% >> "%MYLOGFILE%"
echo SCRIPT_DIR=%~dp0 >> "%MYLOGFILE%"
echo ======================================== >> "%MYLOGFILE%"

:: Force UTF-8
set PYTHONUTF8=1
chcp 65001 >nul

:: Python path
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"

:: Housekeeping - rotate log if it exceeds 2MB (keep 2 backups)
if exist "%MYLOGFILE%" for %%F in ("%MYLOGFILE%") do if %%~zF gtr 2097152 (
    if exist "%MYLOGFILE%.2" del "%MYLOGFILE%.2"
    if exist "%MYLOGFILE%.1" ren "%MYLOGFILE%.1" "morning_soc.log.2"
    ren "%MYLOGFILE%" "morning_soc.log.1"
)

:: Run your script
"%PYTHON_EXE%" "%~dp0morning_soc_check.py" >> "%MYLOGFILE%" 2>&1
set "PYTHON_EXIT=%ERRORLEVEL%"

echo Python exit code: %PYTHON_EXIT% >> "%MYLOGFILE%"
exit /b %PYTHON_EXIT%
