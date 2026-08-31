@echo off
REM RefraScan App - Network Configuration Helper
REM This script helps verify network setup for multi-computer deployment

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\Refrascan"

color 0F

echo.
echo ============================================================
echo RefraScan App - Network Setup Verification
echo ============================================================
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️ Virtual environment not found. Run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

REM Get local IP address
echo Detecting IP address...
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr "IPv4 Address"') do (
    set "LOCAL_IP=%%A"
)

if defined LOCAL_IP (
    set "LOCAL_IP=%LOCAL_IP: =%"
    echo ✓ This Computer's IP Address: %LOCAL_IP%
) else (
    echo ⚠ Could not detect IP address
)
echo.

echo Testing network configuration...
echo.

REM Check if .env file exists
if exist ".env" (
    echo ✓ .env file found
    echo.
    echo .env Configuration:
    type .env | findstr /V "^#" | findstr /V "^$"
    echo.
) else (
    echo ⚠ .env file not found!
    echo    Create .env file using .env.example as template
    echo.
)

REM Test network path if configured
echo Testing network paths...
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if "%%A"=="UPLOAD_BASE_PATH" (
            set "UPLOAD_PATH=%%B"
            if "!UPLOAD_PATH!"=="" (
                echo ✓ UPLOAD_BASE_PATH is empty ^(using local folder^)
            ) else (
                echo Testing network path: !UPLOAD_PATH!
                if exist "!UPLOAD_PATH!" (
                    echo ✓ Network path is accessible
                ) else (
                    echo ✗ Network path NOT accessible
                    echo    Make sure mapped drive is connected
                )
            )
        )
    )
) else (
    echo ⚠ Skipping path check because .env is missing.
)

echo.
echo Testing database connection...
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DB_HOST:', os.getenv('DB_HOST')); print('DB_NAME:', os.getenv('DB_NAME')); print('DB_USER:', os.getenv('DB_USER'))" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ .env values loaded
    timeout /t 2 /nobreak >nul
    python -c "from dotenv import load_dotenv; import os; load_dotenv(); import psycopg2; psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT')); print('✓ Database connection successful')" 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo ✓ Database is accessible from this machine
    ) else (
        echo ✗ Database connection failed
        echo    Check: DB_HOST is correct, PostgreSQL is running, network is accessible
    )
) else (
    echo ⚠ Could not load .env values - skipping database test
    echo   (Make sure .env exists and python-dotenv is installed)
)

echo.
echo ============================================================
echo Network Setup Verification Complete
echo ============================================================
echo.
echo Press any key to close this window...
pause >nul