# Simple LaborLooker Deployment to Google Cloud Run
# This script works with your existing project: laborlooker-2024-476019

Write-Host "🚀 LaborLooker Simple Deployment" -ForegroundColor Green
Write-Host "=" * 50

# Get current GCP project
try {
    $project = gcloud config get-value project 2>$null
    Write-Host "✅ Using GCP Project: $project" -ForegroundColor Green
} catch {
    Write-Host "❌ Could not get GCP project. Run: gcloud auth login" -ForegroundColor Red
    exit 1
}

# Ask for confirmation
$confirm = Read-Host "Deploy LaborLooker to Cloud Run? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Cyan

# Enable APIs
$apis = @(
    "cloudsql.googleapis.com",
    "run.googleapis.com", 
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "Enabling $api..." -ForegroundColor Yellow
    gcloud services enable $api
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to enable $api" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🏗️ Building container..." -ForegroundColor Cyan

# Build container
gcloud builds submit --tag gcr.io/$project/laborlooker --file=Dockerfile.production
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build container" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Cyan

# Deploy to Cloud Run
gcloud run deploy laborlooker `
    --image gcr.io/$project/laborlooker `
    --platform managed `
    --region us-central1 `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --max-instances 10 `
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$project"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to deploy to Cloud Run" -ForegroundColor Red
    exit 1
}

# Get service URL
$serviceUrl = gcloud run services describe laborlooker --region us-central1 --format="value(status.url)" 2>$null

Write-Host ""
Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host "🌐 Your app is live at: $serviceUrl" -ForegroundColor Cyan
Write-Host "🔍 Health check: $serviceUrl/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the deployment by visiting the URL above" -ForegroundColor White
Write-Host "2. Register a test account" -ForegroundColor White
Write-Host "3. Setup your custom domain (optional)" -ForegroundColor White

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")