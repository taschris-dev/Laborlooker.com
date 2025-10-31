#!/bin/bash
# Google Cloud Platform Deployment Script - Professional Grade

echo "🌐 Deploying Referral Engine to Google Cloud Platform"
echo "=================================================="

# Step 1: Check prerequisites
echo "📋 Prerequisites Check:"
echo "✅ Google Cloud SDK installed? (run: gcloud version)"
echo "✅ Billing enabled on Google Cloud account?"
echo "✅ Gmail app password ready?"
echo "✅ PayPal live credentials ready?"
echo ""

# Step 2: Generate secure secret key
echo "🔑 Generating production secret key..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
echo "Secret key generated: $SECRET_KEY"
echo ""

# Step 3: Project setup
echo "🏗️ Google Cloud Project Setup:"
echo "Run these commands in order:"
echo ""

echo "1. Authenticate with Google Cloud:"
echo "gcloud auth login"
echo ""

echo "2. Create new project:"
echo "gcloud projects create referral-engine-2024 --name=\"Referral Engine\""
echo ""

echo "3. Set current project:"
echo "gcloud config set project referral-engine-2024"
echo ""

echo "4. Enable required APIs:"
echo "gcloud services enable appengine.googleapis.com"
echo "gcloud services enable sqladmin.googleapis.com"
echo "gcloud services enable cloudbuild.googleapis.com"
echo ""

echo "5. Create App Engine application:"
echo "gcloud app create --region=us-central"
echo ""

# Step 4: Database setup
echo "🗄️ Database Setup (Cloud SQL):"
echo "6. Create PostgreSQL instance:"
echo "gcloud sql instances create referral-engine-db \\"
echo "    --database-version=POSTGRES_15 \\"
echo "    --tier=db-f1-micro \\"
echo "    --region=us-central1"
echo ""

echo "7. Create database:"
echo "gcloud sql databases create referraldb \\"
echo "    --instance=referral-engine-db"
echo ""

echo "8. Create database user:"
echo "gcloud sql users create dbuser \\"
echo "    --instance=referral-engine-db \\"
echo "    --password=SecurePassword123!"
echo ""

echo "9. Get connection name (save this):"
echo "gcloud sql instances describe referral-engine-db \\"
echo "    --format=\"value(connectionName)\""
echo ""

# Step 5: Update app.yaml
echo "⚙️ Configuration:"
echo "10. Update app.yaml with your credentials:"
cat > app.yaml.template << EOF
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
EOF

echo "✅ app.yaml template created - update with your credentials"
echo ""

# Step 6: Deploy
echo "🚀 Deployment:"
echo "11. Deploy your application:"
echo "gcloud app deploy"
echo ""

echo "12. Open your live application:"
echo "gcloud app browse"
echo ""

# Step 7: Custom domain (optional)
echo "🌐 Custom Domain (Optional):"
echo "13. Verify domain ownership:"
echo "gcloud domains verify your-domain.com"
echo ""

echo "14. Map custom domain:"
echo "gcloud app domain-mappings create your-domain.com"
echo ""

# Results
echo "📊 Your Google Cloud deployment will include:"
echo "✅ App Engine (Serverless hosting)"
echo "✅ Cloud SQL PostgreSQL database"
echo "✅ Auto-scaling (1-10 instances)"
echo "✅ HTTPS/SSL automatic"
echo "✅ Cloud Monitoring & Logging"
echo "✅ Professional domain support"
echo ""

echo "💰 Estimated costs:"
echo "- Development: FREE (generous free tier)"
echo "- Production: $10-30/month"
echo "- High traffic: $50-100/month"
echo ""

echo "🎯 Professional talking points:"
echo "- 'Deployed serverless application on Google Cloud Platform'"
echo "- 'Used App Engine with Cloud SQL for managed database'"
echo "- 'Implemented auto-scaling with zero-downtime deployments'"
echo "- 'Configured Cloud Monitoring for application insights'"
echo ""

echo "🌍 Your live URLs:"
echo "- Application: https://referral-engine-2024.appspot.com"
echo "- Custom domain: https://your-domain.com (if configured)"
echo "- Console: https://console.cloud.google.com"
echo ""

echo "🎉 Ready to deploy! Run the commands above in order."
echo "Your referral engine will be live on Google Cloud! 🚀"