@echo off
setlocal enabledelayedexpansion

REM #####################################################################
REM  olmOCR - ONE-COMMAND DEPLOYMENT (WINDOWS)
REM  This script does EVERYTHING. Just run it.
REM #####################################################################

cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo   olmOCR - ONE-COMMAND DEPLOYMENT
echo.
echo   This script will:
echo     1. Set up Google Cloud
echo     2. Deploy your OCR app
echo     3. Give you a working URL
echo.
echo   You only need to answer 2 questions.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI is not installed.
    echo.
    echo Install it from: https://cloud.google.com/sdk/docs/install
    echo.
    pause
    exit /b 1
)

REM Question 1: Parasail API Key
echo Question 1 of 2: Get your Parasail API key
echo.
echo Visit: https://parasail.io
echo Sign up (free), then copy your API key.
echo.
set /p PARASAIL_KEY="Paste your Parasail API key here: "

if "%PARASAIL_KEY%"=="" (
    echo Error: API key is required
    pause
    exit /b 1
)

REM Question 2: Project name
echo.
echo Question 2 of 2: Choose a project name
echo.
echo This will be your GCP project ID (lowercase, no spaces)
echo Example: my-ocr-app, company-pdf-reader, etc.
echo.
set /p PROJECT_NAME="Project name: "

if "%PROJECT_NAME%"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set TODAY=%%a%%b%%c
    set PROJECT_NAME=olmocr-!TODAY!
    echo Using auto-generated name: !PROJECT_NAME!
)

echo.
echo ════════════════════════════════════════════════════════════════
echo Ready to deploy!
echo.
echo   Project Name: %PROJECT_NAME%
echo   API Key:      %PARASAIL_KEY:~0,10%...
echo.
echo ════════════════════════════════════════════════════════════════
echo.
pause

echo.
echo [1/6] Setting up Google Cloud project...

REM Check if project exists, create if not
gcloud projects describe %PROJECT_NAME% >nul 2>nul
if %errorlevel% neq 0 (
    echo   Creating project %PROJECT_NAME%...
    gcloud projects create %PROJECT_NAME% --name="olmOCR App" --quiet
)

gcloud config set project %PROJECT_NAME% --quiet
echo [OK] Project ready

echo.
echo [2/6] Enabling required Google Cloud services...
gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com firestore.googleapis.com --quiet
echo [OK] Services enabled

echo.
echo [3/6] Creating storage bucket...

REM Add timestamp to make bucket name unique
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do set TIMESTAMP=%%a%%b%%c%%d
set BUCKET_NAME=%PROJECT_NAME%-pdfs-%TIMESTAMP%

echo   Checking billing status...
gcloud beta billing projects describe %PROJECT_NAME% >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo   BILLING NOT ENABLED
    echo ============================================================
    echo.
    echo   Google Cloud requires billing to be enabled.
    echo   Don't worry - you won't be charged much:
    echo     - First 5GB storage: FREE
    echo     - Cloud Run: Pay only when used (cents per request)
    echo.
    echo   Enable billing:
    echo   1. Go to: https://console.cloud.google.com/billing
    echo   2. Link a billing account to project: %PROJECT_NAME%
    echo   3. Run this script again
    echo.
    echo ============================================================
    pause
    exit /b 1
)

echo   Creating bucket: %BUCKET_NAME%
gsutil mb -l us-central1 gs://%BUCKET_NAME%
if %errorlevel% neq 0 (
    echo.
    echo   Error creating bucket. Trying with different name...
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATESTR=%%a%%b%%c
    set BUCKET_NAME=%PROJECT_NAME%-pdfs-%DATESTR%-%TIMESTAMP%
    gsutil mb -l us-central1 gs://%BUCKET_NAME%
)
echo [OK] Storage bucket ready: %BUCKET_NAME%

echo.
echo [4/6] Creating Firestore database...
gcloud firestore databases describe --database="(default)" >nul 2>nul
if %errorlevel% neq 0 (
    gcloud firestore databases create --location=us-central1 --type=firestore-native --quiet
)
echo [OK] Database ready

echo.
echo [5/6] Configuring the application...

REM Create .env file
(
echo # olmOCR Configuration
echo PARASAIL_API_KEY=%PARASAIL_KEY%
echo PORT=8080
echo GCP_PROJECT_ID=%PROJECT_NAME%
echo GCS_BUCKET=%BUCKET_NAME%
echo REGION=us-central1
echo MAX_CONCURRENT_PAGES=100
echo MAX_CONCURRENT_JOBS=10
echo RENDER_DPI=300
echo IMAGE_QUALITY=85
) > simple-ocr-app\.env

echo [OK] Configuration complete

echo.
echo [6/6] Deploying to Cloud Run...
echo   This may take 3-5 minutes...

cd simple-ocr-app

gcloud run deploy olmocr --source . --region us-central1 --platform managed --allow-unauthenticated --memory 2Gi --cpu 2 --timeout 300 --set-env-vars "PARASAIL_API_KEY=%PARASAIL_KEY%,GCP_PROJECT_ID=%PROJECT_NAME%,GCS_BUCKET=%BUCKET_NAME%,REGION=us-central1" --quiet

REM Get the URL
for /f "tokens=*" %%i in ('gcloud run services describe olmocr --region us-central1 --format "value(status.url)"') do set SERVICE_URL=%%i

cd ..

echo.
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo   [OK] DEPLOYMENT COMPLETE!
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo Your olmOCR app is live at:
echo.
echo %SERVICE_URL%
echo.
echo.
echo How to use:
echo   1. Click the URL above (or copy/paste to browser)
echo   2. Drag and drop a PDF file
echo   3. Wait for processing
echo   4. Download your Markdown result
echo.
echo Cost estimate: ~$0.05 - $0.50 per document (pay only when used)
echo.
echo Save this URL - it's your permanent app address!
echo.
echo.
echo Need help?
echo   View logs: gcloud run services logs read olmocr --region us-central1
echo   Delete app: gcloud run services delete olmocr --region us-central1
echo.
pause
