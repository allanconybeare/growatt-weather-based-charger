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

:: Housekeeping - clear the log if it exceeds 100KB (100,000 bytes)
if exist "%MYLOGFILE%" for %%F in ("%MYLOGFILE%") do if %%~zF gtr 100000 del "%MYLOGFILE%"

:: Run your script
"%PYTHON_EXE%" "%~dp0morning_soc_check.py" >> "%MYLOGFILE%" 2>&1
set "PYTHON_EXIT=%ERRORLEVEL%"

echo Python exit code: %PYTHON_EXIT% >> "%MYLOGFILE%"
exit /b %PYTHON_EXIT%