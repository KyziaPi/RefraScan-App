@echo off
REM RefraScan App Launcher for Windows
REM This script activates the virtual environment and starts the app

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if .venv exists
if not exist ".venv" (
    echo.
    echo ERROR: Virtual environment not found!
    echo Please run SETUP.bat first to create and initialize the virtual environment.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Run the app
echo.
python run-app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to close this window...
    pause
)

endlocal
