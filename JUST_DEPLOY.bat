@echo off
REM Super simple - just deploy the damn thing

cls
echo.
echo ========================================
echo   olmOCR - SIMPLE DEPLOY
echo ========================================
echo.

REM Get API key
set /p API_KEY="Your Parasail API key: "

REM Set project
echo.
echo Setting project to juniper-core...
gcloud config set project juniper-core

REM Create .env
echo.
echo Creating .env file...
echo PARASAIL_API_KEY=%API_KEY%> simple-ocr-app\.env
echo PORT=8080>> simple-ocr-app\.env

REM Deploy
echo.
echo Deploying to Cloud Run (this takes 3-5 minutes)...
echo.

cd simple-ocr-app

gcloud run deploy olmocr --source . --region us-central1 --platform managed --allow-unauthenticated --memory 2Gi --cpu 2 --timeout 300 --set-env-vars PARASAIL_API_KEY=%API_KEY%

if errorlevel 1 (
    echo.
    echo DEPLOYMENT FAILED!
    echo.
    cd ..
    pause
    exit /b 1
)

echo.
echo Getting your app URL...
for /f "tokens=*" %%i in ('gcloud run services describe olmocr --region us-central1 --format "value(status.url)"') do set URL=%%i

cd ..

echo.
echo.
echo ========================================
echo   SUCCESS!
echo ========================================
echo.
echo Your app is live at:
echo %URL%
echo.
echo Open that URL in your browser!
echo.
pause
