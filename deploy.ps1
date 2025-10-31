# LaborLooker Deployment Script for Windows PowerShell

Write-Host "🚀 Starting LaborLooker deployment..." -ForegroundColor Green

# Set up environment
$env:PATH = "$env:PATH;$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
Set-Location "c:\HEC demo program\referal-engine"

Write-Host "📦 Setting project..." -ForegroundColor Yellow
gcloud config set project laborlooker-2024-476019

Write-Host "🔧 Deploying application..." -ForegroundColor Yellow
$deployResult = gcloud app deploy --quiet
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "🌐 Opening LaborLooker..." -ForegroundColor Green
    gcloud app browse
} else {
    Write-Host "❌ Deployment failed. Checking logs..." -ForegroundColor Red
    gcloud app logs tail
}

Write-Host "🏁 Deployment process complete." -ForegroundColor Blue