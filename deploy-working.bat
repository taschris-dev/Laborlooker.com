@echo off
echo 🚀 LaborLooker Simple Deployment (No API Management)
echo ================================================

REM Get current GCP project
for /f %%i in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%i
echo ✅ Using GCP Project: %PROJECT_ID%

REM Ask for confirmation
set /p CONFIRM="Deploy LaborLooker to Cloud Run? (yes/no): "
if not "%CONFIRM%"=="yes" (
    echo Deployment cancelled.
    exit /b 0
)

echo.
echo ℹ️ Note: Make sure Cloud Run and Cloud Build APIs are enabled in your GCP project
echo    Visit: https://console.cloud.google.com/apis/enableflow?apiid=run.googleapis.com,cloudbuild.googleapis.com
echo.

echo 🏗️ Building container...

REM Build container using default Dockerfile
gcloud builds submit --tag gcr.io/%PROJECT_ID%/laborlooker .
if errorlevel 1 (
    echo ❌ Failed to build container
    echo Make sure Cloud Build API is enabled: https://console.cloud.google.com/apis/enableflow?apiid=cloudbuild.googleapis.com
    exit /b 1
)

echo.
echo 🚀 Deploying to Cloud Run...

REM Deploy to Cloud Run
gcloud run deploy laborlooker ^
    --image gcr.io/%PROJECT_ID%/laborlooker ^
    --platform managed ^
    --region us-central1 ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 2 ^
    --max-instances 10 ^
    --set-env-vars="GOOGLE_CLOUD_PROJECT=%PROJECT_ID%"

if errorlevel 1 (
    echo ❌ Failed to deploy to Cloud Run
    echo Make sure Cloud Run API is enabled: https://console.cloud.google.com/apis/enableflow?apiid=run.googleapis.com
    exit /b 1
)

echo.
echo 🎉 Deployment completed successfully!
echo.
echo Getting service URL...
for /f %%i in ('gcloud run services describe laborlooker --region us-central1 --format="value(status.url)" 2^>nul') do set SERVICE_URL=%%i
echo 🌐 Your app is live at: %SERVICE_URL%
echo 🔍 Health check: %SERVICE_URL%/health
echo.
echo Next steps:
echo 1. Test the deployment by visiting the URL above
echo 2. Register a test account
echo 3. Setup your custom domain (optional)
echo.
pause