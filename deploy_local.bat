@echo off
REM AgriPredictX Local Development Deployment
REM Quick setup script for Windows developers
REM Simply run: deploy_local.bat

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================
echo   AgriPredictX - Local Development Deployment
echo ============================================================
echo.

REM Step 1: Check Python
echo [Step 1] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo OK: %PYVER% detected
echo.

REM Step 2: Install dependencies
echo [Step 2] Installing Python packages...
echo This may take a few minutes on first run...
echo.
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK: All packages installed
echo.

REM Step 3: Check PostgreSQL
echo [Step 3] Checking PostgreSQL...
psql --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: PostgreSQL command not found in PATH
    echo But PostgreSQL might still be running as a service
    echo.
) else (
    for /f "tokens=*" %%i in ('psql --version') do set PGVER=%%i
    echo OK: !PGVER! detected
)
echo.

REM Step 4: Run Python deployment
echo [Step 4] Running deployment script...
echo.
python deploy_local.py
if errorlevel 1 (
    echo.
    echo ERROR: Deployment failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Deployment Complete!
echo ============================================================
echo.
pause
