# LaborLooker Production Deployment Script (PowerShell)
# Quick deployment to Google Cloud Platform

Write-Host "🚀 LaborLooker Production Deployment" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Gray

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found! Please install Python 3.7+ first." -ForegroundColor Red
    exit 1
}

# Check if Google Cloud SDK is available
try {
    $gcloudVersion = gcloud version --format="value(Google Cloud SDK)" 2>&1
    Write-Host "✅ Google Cloud SDK found" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK not found!" -ForegroundColor Red
    Write-Host "Please install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is available
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check required files
$requiredFiles = @(
    "main.py",
    "requirements-production.txt", 
    "Dockerfile.production",
    "deploy_to_production.py"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🔧 All prerequisites met!" -ForegroundColor Green
Write-Host ""

# Confirm deployment
$confirm = Read-Host "⚠️  This will deploy LaborLooker to PRODUCTION on Google Cloud Platform. Continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🚀 Starting production deployment..." -ForegroundColor Cyan
Write-Host ""

# Run the Python deployment script
try {
    python deploy_to_production.py
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "🎉 Production deployment completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Configure your custom domain DNS" -ForegroundColor White
        Write-Host "2. Update PayPal credentials in Secret Manager" -ForegroundColor White
        Write-Host "3. Test your production deployment" -ForegroundColor White
        Write-Host "4. Setup monitoring alerts" -ForegroundColor White
        Write-Host ""
        Write-Host "📋 Check the deployment report file for detailed information!" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "❌ Deployment failed!" -ForegroundColor Red
        Write-Host "Check the error messages above and try again." -ForegroundColor Yellow
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error running deployment script: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")