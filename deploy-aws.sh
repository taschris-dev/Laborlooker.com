#!/bin/bash
# AWS Elastic Beanstalk Deployment - Maximum Professional Credibility

echo "🏢 Deploying to AWS Elastic Beanstalk - Enterprise Grade"
echo "=================================================="

# Step 1: Install AWS CLI and EB CLI
echo "📦 Installing AWS tools..."
echo "1. Install AWS CLI: https://aws.amazon.com/cli/"
echo "2. Run: pip install awsebcli"
echo ""

# Step 2: AWS Setup
echo "🔐 AWS Configuration required:"
echo "1. Create AWS account (if needed)"
echo "2. Get AWS Access Key and Secret from IAM"
echo "3. Run: aws configure"
echo ""

# Step 3: Generate secure secret key
echo "🔑 Generating production secret key..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
echo "Secret key generated: $SECRET_KEY"
echo ""

# Step 4: Create production environment file
echo "📄 Creating production environment..."
cat > .env.production << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
FLASK_DEBUG=0
MAIL_USERNAME=taschris.executive@gmail.com
MAIL_PASSWORD=your-gmail-app-password
PAYPAL_CLIENT_ID=your-live-paypal-client-id
PAYPAL_CLIENT_SECRET=your-live-paypal-client-secret
PAYPAL_MODE=live
EOF

echo "✅ Production environment file created"
echo ""

# Step 5: EB Initialization
echo "🚀 Elastic Beanstalk Commands:"
echo "1. eb init"
echo "   - Choose region (us-east-1 recommended)"
echo "   - Application name: referral-engine"
echo "   - Platform: Python 3.11"
echo ""
echo "2. eb create production"
echo "   - Environment name: referral-engine-prod"
echo "   - Load balancer: Application Load Balancer"
echo ""
echo "3. eb setenv (set environment variables):"
echo "   eb setenv SECRET_KEY=$SECRET_KEY"
echo "   eb setenv FLASK_ENV=production"
echo "   eb setenv MAIL_USERNAME=taschris.executive@gmail.com"
echo "   eb setenv MAIL_PASSWORD=your-gmail-app-password"
echo "   eb setenv PAYPAL_CLIENT_ID=your-live-client-id"
echo "   eb setenv PAYPAL_CLIENT_SECRET=your-live-secret"
echo "   eb setenv PAYPAL_MODE=live"
echo ""
echo "4. eb deploy"
echo ""

# Step 6: Database setup
echo "🗄️ Database Setup (RDS):"
echo "1. Go to AWS RDS Console"
echo "2. Create PostgreSQL database"
echo "3. Get connection string"
echo "4. eb setenv DATABASE_URL=postgresql://..."
echo ""

# Step 7: Domain setup
echo "🌐 Professional Domain Setup:"
echo "1. Register domain (Route 53 or external)"
echo "2. Configure DNS in Route 53"
echo "3. Add SSL certificate (Certificate Manager)"
echo "4. Update domain in EB console"
echo ""

echo "📊 Your professional deployment will include:"
echo "✅ AWS Elastic Beanstalk (Enterprise platform)"
echo "✅ Application Load Balancer"
echo "✅ Auto Scaling"
echo "✅ CloudWatch monitoring"
echo "✅ RDS PostgreSQL database"
echo "✅ Route 53 DNS"
echo "✅ SSL Certificate"
echo "✅ Professional domain"
echo ""

echo "💼 Resume/Interview talking points:"
echo "- 'Deployed scalable web application on AWS'"
echo "- 'Implemented enterprise-grade architecture'"
echo "- 'Used AWS services: EB, RDS, Route 53, CloudWatch'"
echo "- 'Configured auto-scaling and load balancing'"
echo ""

echo "🎯 Estimated monthly cost: $25-50"
echo "🚀 Maximum professional credibility achieved!"
echo ""
echo "Your app will be live at: http://referral-engine-prod.region.elasticbeanstalk.com"
echo "With custom domain: https://your-domain.com"