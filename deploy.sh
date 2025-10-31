#!/bin/bash
# Quick Heroku Deployment Script

echo "🚀 Deploying Referral Engine to Production..."

# Step 1: Generate a secure secret key
echo "📄 Generating secure secret key..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Step 2: Create Heroku app (replace 'your-app-name' with desired name)
echo "🌐 Creating Heroku app..."
heroku create your-referral-engine-2024

# Step 3: Add PostgreSQL database
echo "🗄️ Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini

# Step 4: Set environment variables
echo "⚙️ Setting environment variables..."
heroku config:set SECRET_KEY=$SECRET_KEY
heroku config:set FLASK_ENV=production
heroku config:set FLASK_DEBUG=0
heroku config:set MAIL_USERNAME=taschris.executive@gmail.com
heroku config:set MAIL_PASSWORD=your-gmail-app-password
heroku config:set PAYPAL_CLIENT_ID=your-live-paypal-client-id
heroku config:set PAYPAL_CLIENT_SECRET=your-live-paypal-client-secret
heroku config:set PAYPAL_MODE=live

# Step 5: Deploy to Heroku
echo "📦 Deploying to Heroku..."
git add .
git commit -m "Production deployment"
git push heroku main

echo "✅ Deployment complete!"
echo "🌍 Your app is live at: https://your-referral-engine-2024.herokuapp.com"
echo ""
echo "🔧 Next steps:"
echo "1. Update PayPal credentials with live values"
echo "2. Test all functionality on live site"
echo "3. Set up custom domain (optional)"