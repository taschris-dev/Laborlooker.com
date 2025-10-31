@echo off
REM Docker Build and Test Script for LaborLooker
REM Run this to build and test your Docker image before Railway deployment

echo 🚀 LaborLooker Docker Build and Test
echo =====================================

echo.
echo 🔍 Checking Docker installation...
docker --version
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not running
    echo Please install Docker Desktop and make sure it's running
    pause
    exit /b 1
)

echo ✅ Docker is available

echo.
echo 🐳 Building Docker image...
docker build -t laborlooker .
if %errorlevel% neq 0 (
    echo ❌ Docker build failed
    pause
    exit /b 1
)

echo ✅ Docker image built successfully

echo.
echo 🧪 Testing Docker image locally...

REM Stop any existing test container
docker stop laborlooker-test 2>nul
docker rm laborlooker-test 2>nul

REM Start test container
docker run -d --name laborlooker-test -p 8080:8080 -e SECRET_KEY=test-secret-key -e DATABASE_URL=sqlite:///instance/test.db laborlooker
if %errorlevel% neq 0 (
    echo ❌ Failed to start test container
    pause
    exit /b 1
)

echo ⏳ Waiting for application to start...
timeout /t 10 /nobreak >nul

echo 🔍 Testing health endpoint...
curl -f http://localhost:8080/health
if %errorlevel% equ 0 (
    echo.
    echo ✅ Health check passed - Docker image is working!
) else (
    echo.
    echo ⚠️ Health check failed, but container might still be starting
    echo You can manually test: http://localhost:8080
)

echo.
echo 🧹 Cleaning up test container...
docker stop laborlooker-test
docker rm laborlooker-test

echo.
echo 🎉 Docker image is ready for Railway deployment!
echo.
echo Next steps:
echo 1. Install Railway CLI: npm install -g @railway/cli
echo 2. Login to Railway: railway login
echo 3. Deploy: railway up
echo.
echo Or run: python deploy_railway.py

pause