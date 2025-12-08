@echo off
setlocal enabledelayedexpansion

REM DEBUG VERSION - Shows all errors

cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo   olmOCR - ONE-COMMAND DEPLOYMENT (DEBUG MODE)
echo ═══════════════════════════════════════════════════════════════
echo.

REM Get your settings
set /p PARASAIL_KEY="Paste your Parasail API key: "
set /p PROJECT_NAME="Enter your GCP project name (juniper-core): "

if "%PROJECT_NAME%"=="" set PROJECT_NAME=juniper-core

echo.
echo Using project: %PROJECT_NAME%
echo.
pause

echo.
echo [1/6] Setting project...
gcloud config set project %PROJECT_NAME%
echo.

echo [2/6] Enabling APIs...
gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com firestore.googleapis.com
echo.

echo [3/6] Creating storage bucket...
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do set TIMESTAMP=%%a%%b%%c%%d
set BUCKET_NAME=%PROJECT_NAME%-pdfs-%TIMESTAMP%

echo   Bucket name will be: %BUCKET_NAME%
echo   Running: gsutil mb -l us-central1 gs://%BUCKET_NAME%
echo.

gsutil mb -l us-central1 gs://%BUCKET_NAME%
if %errorlevel% neq 0 (
    echo.
    echo   ^^^ BUCKET CREATION FAILED ^^^
    echo.
    echo   Trying alternate name...
    set BUCKET_NAME=%PROJECT_NAME%-olmocr-%TIMESTAMP%
    echo   New name: %BUCKET_NAME%
    gsutil mb -l us-central1 gs://%BUCKET_NAME%
)

if %errorlevel% neq 0 (
    echo.
    echo STOP: Bucket creation failed twice.
    echo.
    echo Possible issues:
    echo   1. Quota exceeded
    echo   2. Permissions issue
    echo   3. Storage API not fully enabled yet (wait 1 minute and try again)
    echo.
    echo Try manually:
    echo   gsutil mb -l us-central1 gs://%PROJECT_NAME%-test-bucket
    echo.
    pause
    exit /b 1
)

echo   Bucket created: %BUCKET_NAME%
echo.

echo [4/6] Creating Firestore...
gcloud firestore databases create --location=us-central1 --type=firestore-native 2>nul
if %errorlevel% equ 0 (
    echo   Created new Firestore database
) else (
    echo   Firestore already exists or error - continuing...
)
echo.

echo [5/6] Configuring app...
(
echo PARASAIL_API_KEY=%PARASAIL_KEY%
echo PORT=8080
echo GCP_PROJECT_ID=%PROJECT_NAME%
echo GCS_BUCKET=%BUCKET_NAME%
echo REGION=us-central1
) > simple-ocr-app\.env
echo   Configuration saved to simple-ocr-app\.env
echo.

echo [6/6] Deploying to Cloud Run...
echo   This takes 3-5 minutes...
echo.

cd simple-ocr-app

gcloud run deploy olmocr ^
    --source . ^
    --region us-central1 ^
    --platform managed ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 2 ^
    --timeout 300 ^
    --set-env-vars "PARASAIL_API_KEY=%PARASAIL_KEY%,GCP_PROJECT_ID=%PROJECT_NAME%,GCS_BUCKET=%BUCKET_NAME%,REGION=us-central1"

if %errorlevel% neq 0 (
    echo.
    echo DEPLOYMENT FAILED
    echo.
    echo Common issues:
    echo   1. Missing Dockerfile in simple-ocr-app/
    echo   2. Cloud Build API not enabled
    echo   3. Insufficient permissions
    echo.
    cd ..
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('gcloud run services describe olmocr --region us-central1 --format "value(status.url)"') do set SERVICE_URL=%%i

cd ..

echo.
echo.
echo ═══════════════════════════════════════════════════════════════
echo   SUCCESS!
echo ═══════════════════════════════════════════════════════════════
echo.
echo Your app is live at:
echo.
echo %SERVICE_URL%
echo.
echo.
pause
