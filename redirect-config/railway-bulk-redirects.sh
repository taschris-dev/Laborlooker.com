#!/bin/bash
# railway-bulk-redirects.sh
# Environment-based redirect configuration for Railway deployment

echo "Setting up bulk redirects for LaborLooker migration..."

# Set environment variables for legacy URL mapping
railway variables set LEGACY_DOMAIN="old-laborlookers.herokuapp.com"
railway variables set NEW_API_DOMAIN="api.laborlooker.com"  
railway variables set NEW_WEB_DOMAIN="app.laborlooker.com"

# Configure redirect mappings
railway variables set REDIRECT_MAPPINGS='{
  "/dashboard": "/dashboard/overview",
  "/profile/": "/profiles/",
  "/work-request/": "/work/",
  "/login": "/auth/signin",
  "/register": "/auth/signup",
  "/jobs": "/work-requests",
  "/contractors": "/professionals",
  "/help": "/support",
  "/contact": "/support/contact",
  "/terms": "/legal/terms",
  "/privacy": "/legal/privacy",
  "/api/v1/": "/api/"
}'

echo "✅ Railway redirect configuration complete!"
echo "🔄 Redirects will be handled by Next.js and Cloudflare"