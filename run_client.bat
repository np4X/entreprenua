@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ==== LAN IP IS AUTO-DETECTED BELOW ====
REM Picks the first non-APIPA (169.254.x.x), non-loopback IPv4 address
REM reported by "ipconfig" so your phone can reach it on the same
REM Wi-Fi. The server itself always listens on all interfaces, so
REM this only controls which URL gets opened/displayed.
REM
REM If it picks the wrong adapter (e.g. you have a VPN active), set
REM FORCE_IP below to override it, e.g.:  set FORCE_IP=10.203.162.67
set FORCE_IP=
set APP_PORT=5067

set APP_IP=
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    set "CANDIDATE=%%A"
    set "CANDIDATE=!CANDIDATE: =!"
    echo !CANDIDATE! | findstr /B /C:"169.254." >nul
    if errorlevel 1 (
        if "!APP_IP!"=="" set "APP_IP=!CANDIDATE!"
    )
)
if not "%FORCE_IP%"=="" set APP_IP=%FORCE_IP%
if "%APP_IP%"=="" set APP_IP=127.0.0.1
REM ================================================================

echo ============================================
echo   Traffy Waste App - CLIENT (phone)
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
set FLASK_APP=client_app.py

echo.
echo Detected LAN IP: %APP_IP%
echo Starting CLIENT app on %APP_IP%:%APP_PORT%
echo   Open on your phone: http://%APP_IP%:%APP_PORT%/
echo   (Make sure the MACHINE app is also running - see run_machine.bat)
echo   (Wrong IP? Set FORCE_IP near the top of this file to override it)
echo Press CTRL+C to stop the server.
echo.

start "" http://%APP_IP%:%APP_PORT%/

python client_app.py

pause
