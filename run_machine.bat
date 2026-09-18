@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ==== KIOSK OPENS ON 127.0.0.1; LAN IP IS AUTO-DETECTED FOR STAFF ====
REM This is the kiosk running on the PC next to the bin, so the
REM browser it opens defaults to 127.0.0.1. The server itself always
REM listens on all interfaces, so this script also auto-detects your
REM LAN IPv4 (via "ipconfig") and prints it below so staff elsewhere
REM can open http://<that-IP>:%APP_PORT%/staff remotely.
REM APP_PORT: change if 5069 is already used by something else.
set APP_IP=127.0.0.1
set APP_PORT=5069

set LAN_IP=
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    set "CANDIDATE=%%A"
    set "CANDIDATE=!CANDIDATE: =!"
    echo !CANDIDATE! | findstr /B /C:"169.254." >nul
    if errorlevel 1 (
        if "!LAN_IP!"=="" set "LAN_IP=!CANDIDATE!"
    )
)
REM ================================================================

echo ============================================
echo   Traffy Waste App - MACHINE (bin kiosk)
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check your internet connection / pip setup.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
set FLASK_APP=machine_app.py

echo.
echo Starting MACHINE app on port %APP_PORT%
echo   Kiosk screen (this PC)     : http://%APP_IP%:%APP_PORT%/
if not "%LAN_IP%"=="" echo   Staff review (from network): http://%LAN_IP%:%APP_PORT%/staff
echo   Staff review (this PC)     : http://%APP_IP%:%APP_PORT%/staff
echo Press CTRL+C to stop the server.
echo.

start "" http://%APP_IP%:%APP_PORT%/

python machine_app.py

pause
