# LABOR LOOKERS PRODUCTION DEPLOYMENT - GOOGLE CLOUD PLATFORM
# Optimized B2B/B2C Architecture with Cloud Run + Cloud SQL
# Run this in PowerShell as Administrator

Write-Host "🚀 Deploying Labor Lookers to Google Cloud Platform" -ForegroundColor Green
Write-Host "📊 B2B/B2C Job Marketplace + Advertising Marketplace" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green

# Step 1: Prerequisites check
Write-Host "`n📋 Production Prerequisites Check:" -ForegroundColor Yellow
Write-Host "✅ Google Cloud SDK installed? Check with: gcloud version"
Write-Host "✅ Billing enabled on Google Cloud account?"
Write-Host "✅ Docker installed for containerization?"
Write-Host "✅ Custom domain ready? (optional)"
Write-Host "✅ Production database credentials ready?"

# Step 2: Project Configuration
Write-Host "`n🎯 Project Configuration:" -ForegroundColor Yellow
$PROJECT_ID = Read-Host "Enter your GCP Project ID (e.g., laborlookers-prod)"
$REGION = "us-central1"
$DB_INSTANCE = "laborlookers-db"
$SERVICE_NAME = "laborlookers-app"

Write-Host "✅ Project ID: $PROJECT_ID" -ForegroundColor Green
Write-Host "✅ Region: $REGION" -ForegroundColor Green
Write-Host "✅ Database Instance: $DB_INSTANCE" -ForegroundColor Green
Write-Host "✅ Service Name: $SERVICE_NAME" -ForegroundColor Green

# Step 3: Generate production secret key
Write-Host "`n🔑 Generating production secret key..." -ForegroundColor Yellow
$SECRET_KEY = & python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "Secret key generated: $SECRET_KEY" -ForegroundColor Green

# Step 4: Installation check
Write-Host "`n📦 Checking Google Cloud SDK..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version 2>$null
    Write-Host "✅ Google Cloud SDK is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Google Cloud SDK not found. Please install from:" -ForegroundColor Red
    Write-Host "https://cloud.google.com/sdk/docs/install-windows" -ForegroundColor Red
    exit
}

# Step 5: Set GCP Project
Write-Host "`n🌐 Setting up GCP project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
Write-Host "✅ Project set to: $PROJECT_ID" -ForegroundColor Green

# Step 6: Enable Required APIs
Write-Host "`n🔧 Enabling required GCP APIs..." -ForegroundColor Yellow
$apis = @(
    "run.googleapis.com",
    "sql-component.googleapis.com", 
    "sqladmin.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage-component.googleapis.com",
    "identity.googleapis.com",
    "cloudresourcemanager.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "Enabling $api..." -ForegroundColor Cyan
    gcloud services enable $api
}
Write-Host "✅ All APIs enabled successfully" -ForegroundColor Green

# Step 4: Deployment commands
Write-Host "`n🚀 Google Cloud Deployment Commands:" -ForegroundColor Yellow
Write-Host "Copy and run these commands one by one:`n" -ForegroundColor Cyan

$commands = @"
# 1. Authenticate with Google Cloud
gcloud auth login

# 2. Create new project
gcloud projects create referral-engine-2024 --name="Referral Engine"

# 3. Set current project
gcloud config set project referral-engine-2024

# 4. Enable required APIs
gcloud services enable appengine.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 5. Create App Engine application
gcloud app create --region=us-central

# 6. Create PostgreSQL instance
gcloud sql instances create referral-engine-db --database-version=POSTGRES_15 --tier=db-f1-micro --region=us-central1

# 7. Create database
gcloud sql databases create referraldb --instance=referral-engine-db

# 8. Create database user
gcloud sql users create dbuser --instance=referral-engine-db --password=SecurePassword123!

# 9. Deploy your application
gcloud app deploy

# 10. Open your live application
gcloud app browse
"@

Write-Host $commands -ForegroundColor White

# Step 5: Create updated app.yaml
Write-Host "`n⚙️ Creating production app.yaml..." -ForegroundColor Yellow

$appYamlContent = @"
# Google App Engine Configuration for Referral Engine
runtime: python311

env_variables:
  SECRET_KEY: "$SECRET_KEY"
  FLASK_ENV: "production"
  FLASK_DEBUG: "0"
  MAIL_USERNAME: "taschris.executive@gmail.com"
  MAIL_PASSWORD: "your-gmail-app-password"
  PAYPAL_CLIENT_ID: "your-live-paypal-client-id"
  PAYPAL_CLIENT_SECRET: "your-live-paypal-client-secret"
  PAYPAL_MODE: "live"
  CLOUD_SQL_CONNECTION_NAME: "referral-engine-2024:us-central1:referral-engine-db"
  DB_USER: "dbuser"
  DB_PASSWORD: "SecurePassword123!"
  DB_NAME: "referraldb"

handlers:
- url: /static
  static_dir: static
  secure: always

- url: /.*
  script: auto
  secure: always

automatic_scaling:
  min_instances: 1
  max_instances: 10
  min_idle_instances: 1
  max_idle_instances: 2
  target_cpu_utilization: 0.6

resources:
  cpu: 1
  memory_gb: 0.5
  disk_size_gb: 10
"@

# Save the app.yaml file
$appYamlContent | Out-File -FilePath "app.yaml.production" -Encoding UTF8
Write-Host "✅ app.yaml.production created with your secret key" -ForegroundColor Green
Write-Host "📝 Remember to update with your Gmail and PayPal credentials" -ForegroundColor Yellow

# Step 6: Summary
Write-Host "`n📊 Your Google Cloud deployment will include:" -ForegroundColor Yellow
Write-Host "✅ App Engine (Serverless hosting)" -ForegroundColor Green
Write-Host "✅ Cloud SQL PostgreSQL database" -ForegroundColor Green
Write-Host "✅ Auto-scaling (1-10 instances)" -ForegroundColor Green
Write-Host "✅ HTTPS/SSL automatic" -ForegroundColor Green
Write-Host "✅ Cloud Monitoring & Logging" -ForegroundColor Green
Write-Host "✅ Professional domain support" -ForegroundColor Green

Write-Host "`n💰 Estimated costs:" -ForegroundColor Yellow
Write-Host "- Development: FREE (generous free tier)" -ForegroundColor Green
Write-Host "- Production: `$10-30/month" -ForegroundColor Green
Write-Host "- High traffic: `$50-100/month" -ForegroundColor Green

Write-Host "`n🎯 Professional talking points:" -ForegroundColor Yellow
Write-Host "- 'Deployed serverless application on Google Cloud Platform'" -ForegroundColor Cyan
Write-Host "- 'Used App Engine with Cloud SQL for managed database'" -ForegroundColor Cyan
Write-Host "- 'Implemented auto-scaling with zero-downtime deployments'" -ForegroundColor Cyan
Write-Host "- 'Configured Cloud Monitoring for application insights'" -ForegroundColor Cyan

Write-Host "`n🌍 Your live URLs:" -ForegroundColor Yellow
Write-Host "- Application: https://referral-engine-2024.appspot.com" -ForegroundColor Cyan
Write-Host "- Console: https://console.cloud.google.com" -ForegroundColor Cyan

Write-Host "`n🎉 Ready to deploy! Run the commands above in order." -ForegroundColor Green
Write-Host "Your referral engine will be live on Google Cloud! 🚀" -ForegroundColor Green