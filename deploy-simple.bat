@echo off
echo 🚀 LaborLooker Simple Deployment
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
echo 🔧 Enabling required APIs...

REM Enable APIs
echo Enabling cloudsql.googleapis.com...
gcloud services enable cloudsql.googleapis.com
if errorlevel 1 (
    echo ❌ Failed to enable cloudsql.googleapis.com
    exit /b 1
)

echo Enabling run.googleapis.com...
gcloud services enable run.googleapis.com
if errorlevel 1 (
    echo ❌ Failed to enable run.googleapis.com
    exit /b 1
)

echo Enabling cloudbuild.googleapis.com...
gcloud services enable cloudbuild.googleapis.com
if errorlevel 1 (
    echo ❌ Failed to enable cloudbuild.googleapis.com
    exit /b 1
)

echo Enabling secretmanager.googleapis.com...
gcloud services enable secretmanager.googleapis.com
if errorlevel 1 (
    echo ❌ Failed to enable secretmanager.googleapis.com
    exit /b 1
)

echo.
echo 🏗️ Building container...

REM Build container
gcloud builds submit --tag gcr.io/%PROJECT_ID%/laborlooker --file=Dockerfile.production
if errorlevel 1 (
    echo ❌ Failed to build container
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
    exit /b 1
)

echo.
echo 🎉 Deployment completed successfully!
echo.
echo To get your service URL, run:
echo gcloud run services describe laborlooker --region us-central1 --format="value(status.url)"
echo.
echo Next steps:
echo 1. Get the service URL using the command above
echo 2. Test the deployment by visiting the URL
echo 3. Register a test account
echo 4. Setup your custom domain (optional)
echo.
pause