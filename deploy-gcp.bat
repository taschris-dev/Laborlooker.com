@echo off
REM LaborLooker Google Cloud Deployment Script for Windows
REM This script automates the deployment process to Google Cloud Platform

echo 🚀 LaborLooker Google Cloud Deployment Script
echo ==============================================

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Google Cloud SDK not found. Please install it first:
    echo    https://cloud.google.com/sdk/docs/install
    exit /b 1
)

echo ✅ Google Cloud SDK found

REM Check authentication
gcloud auth list --filter=status:ACTIVE --format="value(account)" | findstr "@" >nul
if %errorlevel% neq 0 (
    echo 🔐 Please log in to Google Cloud:
    gcloud auth login
)

echo ✅ Google Cloud authentication verified

REM Get current project
for /f "tokens=*" %%i in ('gcloud config get-value project') do set PROJECT_ID=%%i
echo 📂 Current project: %PROJECT_ID%

REM Deployment options
echo.
echo Select deployment type:
echo 1) Development (SQLite database)
echo 2) Production (Cloud SQL database)
echo 3) Custom configuration
set /p DEPLOY_TYPE="Enter choice (1-3): "

if "%DEPLOY_TYPE%"=="1" (
    echo 🔧 Deploying with SQLite Development...
    set CONFIG_FILE=app.yaml
) else if "%DEPLOY_TYPE%"=="2" (
    echo 🔧 Deploying with Cloud SQL Production...
    set CONFIG_FILE=app-gcp-optimized.yaml
    echo ⚠️  Make sure you have:
    echo    - Created Cloud SQL instance
    echo    - Updated connection string in %CONFIG_FILE%
    echo    - Set up Secret Manager for passwords
    set /p CONTINUE="Continue? (y/N): "
    if /i not "%CONTINUE%"=="y" exit /b 0
) else if "%DEPLOY_TYPE%"=="3" (
    set /p CONFIG_FILE="Enter config file name: "
) else (
    echo ❌ Invalid choice
    exit /b 1
)

REM Verify config file exists
if not exist "%CONFIG_FILE%" (
    echo ❌ Configuration file %CONFIG_FILE% not found
    exit /b 1
)

echo ✅ Using configuration: %CONFIG_FILE%

REM Confirm deployment
echo.
set /p CONFIRM="🚀 Deploy to Google Cloud? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo ❌ Deployment cancelled
    exit /b 0
)

REM Deploy
echo 🚀 Starting deployment...
echo    Config: %CONFIG_FILE%
echo    Project: %PROJECT_ID%
echo.

gcloud app deploy "%CONFIG_FILE%" --promote --stop-previous-version

if %errorlevel% equ 0 (
    echo.
    echo ✅ Deployment successful!
    echo.
    echo 🌐 Your app is available at:
    gcloud app browse --no-launch-browser
    echo.
    echo 📊 View logs:
    echo    gcloud app logs tail -s default
    echo.
    echo 🎯 Next steps:
    echo    - Test your application
    echo    - Set up monitoring
    echo    - Configure custom domain optional
) else (
    echo.
    echo ❌ Deployment failed
    echo 📊 Check logs for details:
    echo    gcloud app logs tail -s default
    exit /b 1
)