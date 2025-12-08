@echo off
REM ABSOLUTE SIMPLEST DEPLOYMENT - NO NONSENSE

cls
set /p KEY="Your Parasail API key: "

echo.
echo Deploying... (takes 3-5 minutes)
echo.

cd simple-ocr-app

gcloud run deploy olmocr --source=. --region=us-central1 --project=juniper-core --allow-unauthenticated --set-env-vars=PARASAIL_API_KEY=%KEY%

echo.
echo DONE!
echo.
echo Your app URL:
gcloud run services describe olmocr --region=us-central1 --project=juniper-core --format="value(status.url)"
echo.
pause
