@echo off
REM Minimal deployment - just deploys the app without creating resources

set /p PARASAIL_KEY="Paste your Parasail API key: "
set PROJECT_NAME=juniper-core

echo.
echo Deploying to project: %PROJECT_NAME%
echo.

gcloud config set project %PROJECT_NAME%

echo.
echo Creating minimal .env file...
(
echo PARASAIL_API_KEY=%PARASAIL_KEY%
echo PORT=8080
) > simple-ocr-app\.env

echo.
echo Deploying to Cloud Run...
cd simple-ocr-app

gcloud run deploy olmocr ^
    --source . ^
    --region us-central1 ^
    --platform managed ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 2 ^
    --timeout 300 ^
    --set-env-vars "PARASAIL_API_KEY=%PARASAIL_KEY%,PORT=8080"

for /f "tokens=*" %%i in ('gcloud run services describe olmocr --region us-central1 --format "value(status.url)"') do set URL=%%i

cd ..

echo.
echo.
echo SUCCESS! Your app is at:
echo %URL%
echo.
pause
