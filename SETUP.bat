@echo off
REM RefraScan App Setup Script
REM Run this once to set up the virtual environment and install dependencies

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo ============================================================
echo RefraScan App - First Time Setup
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo ✓ Python found
python --version
echo.

REM Check if .venv already exists
if exist ".venv" (
    echo ✓ Virtual environment already exists
    echo.
    set /p CONTINUE="Do you want to reinstall? (y/n): "
    if /i not "!CONTINUE!"=="y" (
        echo Skipping virtual environment creation
        goto :INSTALL_DEPS
    )
    echo Removing old virtual environment...
    rmdir /s /q .venv
)

echo Creating virtual environment...
python -m venv .venv

if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo ✓ Virtual environment created
echo.

:INSTALL_DEPS
echo Activating virtual environment...
call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✓ Virtual environment activated
echo.

echo Installing dependencies from requirements.txt...
echo This may take a few minutes...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo WARNING: Some packages failed to install
    echo You may need to check your requirements.txt file
    echo.
)

echo.
echo ✓ Setup complete!
echo.
echo You can now run START-APP.bat to start the RefraScan App
echo.
pause

endlocal
