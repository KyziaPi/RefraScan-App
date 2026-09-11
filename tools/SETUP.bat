@echo off
REM RefraScan App Setup Script
REM Run this once to set up the virtual environment and install dependencies

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\Refrascan"

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

REM ============================================================
REM Check and Create .env File with Uploaded Template Structure
REM ============================================================
echo.
echo Checking .env configuration...
if not exist ".env" (
    echo Creating .env file from template...
    python -c "import secrets; key = secrets.token_hex(32); template = '''# RefraScan App .env\n# Configure this file with your database and network settings (optional).\n\n# ========================================\n# DATABASE CONFIGURATION\n# ========================================\n\n# Database name (default: refrascandb)\nDB_NAME=refrascandb\n\n# PostgreSQL username (default: postgres)\nDB_USER=postgres\n\n# PostgreSQL password (change to your password^!)\nDB_PASSWORD=your_password_here\n\n# Database host\n# For LOCAL only:   127.0.0.1 or localhost\n# For NETWORK:      Server IP address (e.g., 192.168.1.100)\nDB_HOST=127.0.0.1\n\n# PostgreSQL port (default: 5432)\nDB_PORT=5432\n\n# ========================================\n# NETWORK SHARED FOLDER (Optional)\n# ========================================\n\n# Leave empty to use local uploads folder\n# For network shared folder, use mapped drive or UNC path\n# Examples:\n#   Z:\\                          (mapped network drive)\n#   \\\\192.168.1.100\\uploads\\     (UNC path with IP)\n#   \\\\SERVER-PC\\uploads\\         (UNC path with computer name)\nUPLOAD_BASE_PATH=\n\n\n# ========================================\n# NOTES\n# ========================================\n# - For network setup: update DB_HOST and UPLOAD_BASE_PATH\n# - Make sure network paths end with backslash\n# - Database must be created first before app starts\n\n# ========================================\n# OTHER CONFIGURATION (LEAVE AS IS)\n# ========================================\nSECRET_KEY={}\nMAIL_SERVER=smtp.gmail.com\nMAIL_PORT=587\nMAIL_USE_TLS=True\nMAIL_USERNAME=refrascan@gmail.com\nMAIL_PASSWORD=bmev hrwr rzho lyjw\n'''.format(key); open('.env', 'w', encoding='utf-8').write(template); print('✓ .env file created')"
) else (
    echo ✓ .env file already exists
)

echo.
echo ✓ Setup complete!
echo.
echo You must first configure the .env file inside RefraScan folder before running START-APP.bat to start the RefraScan App
echo.
pause

endlocal
