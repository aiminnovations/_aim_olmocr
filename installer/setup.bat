@echo off
REM olmOCR Windows Installer
REM Double-click this file to start the installation

echo ============================================
echo olmOCR Automated Installer for Windows
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if gcloud is installed
gcloud --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Google Cloud SDK is not installed.
    echo.
    echo Opening download page...
    start https://cloud.google.com/sdk/docs/install
    echo.
    echo Please install Google Cloud SDK and run this installer again.
    pause
    exit /b 1
)

REM Set environment variables
set GCP_PROJECT_ID=juniper-core
set PARASAIL_API_KEY=psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP
set GCP_REGION=us-central1

REM Run the Python installer
echo Starting installation...
echo.
python "%~dp0install.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Installation encountered an error.
    pause
    exit /b 1
)

echo.
echo Installation complete!
pause
