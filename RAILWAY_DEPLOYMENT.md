# 🚀 Railway Deployment Guide for LaborLooker

## Quick Deployment Steps

### 1. Build and Test Docker Image
```bash
# Run the build script
build_docker.bat

# Or manually:
docker build -t laborlooker .
docker run -d --name test -p 8080:8080 -e SECRET_KEY=test-key -e DATABASE_URL=sqlite:///instance/test.db laborlooker
```

### 2. Install Railway CLI
```bash
npm install -g @railway/cli
```

### 3. Deploy to Railway
```bash
# Login to Railway
railway login

# Deploy your application
railway up
```

## Automated Deployment
Use the automated deployment script:
```bash
python deploy_railway.py
```

## Environment Variables to Set in Railway

### Required Environment Variables
```bash
# Core Flask settings
SECRET_KEY=your-super-secret-key-here
PORT=8080
FLASK_ENV=production

# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://username:password@host:port/database

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=taschris.executive@gmail.com
MAIL_PASSWORD=owyg mxkz evho yalf
MAIL_DEFAULT_SENDER=taschris.executive@gmail.com

# DocuSign Configuration
DOCUSIGN_INTEGRATION_KEY=b5beac54-1015-493e-a392-4972312eddae
DOCUSIGN_USER_ID=dd2adf51-c85c-4229-8a6c-0fcb4d2f8896
DOCUSIGN_ACCOUNT_ID=bacc8ebe-0fec-437e-8c30-f0630c21b258
DOCUSIGN_BASE_PATH=https://demo.docusign.net/restapi
DOCUSIGN_OAUTH_BASE_PATH=https://account-d.docusign.com
DOCUSIGN_REDIRECT_URI=https://your-railway-domain.railway.app/docusign/callback

# PayPal Configuration
PAYPAL_CLIENT_ID=AWC4ekd4ChKsiY97ieWyVxAk2QKjMHAGblhTUlGTOtdWRrVtoninTD5v9CKi7G_e3pPpxCZdPp2C9d1i
PAYPAL_CLIENT_SECRET=EG6BFP37JcCZPyq2q2NBsJWwWhUMUTRiiQ2I8FQCI6TK_5zuOuKeRUkUDvZIWCT1723K--xAlcTTRvAI
PAYPAL_MODE=live

# Security Settings
SESSION_COOKIE_SECURE=true
CSRF_PROTECTION_ENABLED=true
PII_ENCRYPTION_ENABLED=true
```

## Railway Setup Steps

### 1. Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Choose "Deploy from GitHub repo" or "Empty Project"
4. Connect your repository

### 2. Add PostgreSQL Database
1. In your Railway project dashboard
2. Click "New" → "Database" → "PostgreSQL"
3. Railway will automatically set DATABASE_URL

### 3. Configure Environment Variables
1. Go to your service settings
2. Click "Variables" tab
3. Add all the environment variables listed above

### 4. Deploy
```bash
railway up
```

## Monitoring Your Deployment

### View Logs
```bash
railway logs
```

### Check Status
```bash
railway status
```

### Open in Browser
```bash
railway open
```

## Health Check Endpoints
- `/health` - Application health status
- `/ready` - Readiness check
- `/_ah/health` - Google Cloud compatible health check

## Docker Image Details
- **Base Image**: python:3.11-slim
- **Port**: 8080 (configurable via PORT env var)
- **Server**: Gunicorn with 2 workers, 4 threads
- **Health Check**: Built-in health monitoring
- **Security**: Non-root user, minimal attack surface

## Troubleshooting

### Build Issues
- Ensure all dependencies are in requirements.txt
- Check Docker Desktop is running
- Verify .dockerignore excludes unnecessary files

### Runtime Issues
- Check Railway logs: `railway logs`
- Verify environment variables are set
- Ensure DATABASE_URL is configured
- Check health endpoint: `https://your-app.railway.app/health`

### Database Issues
- Railway PostgreSQL is automatically configured
- Database tables will be created on first run
- Check database connection in health endpoint

## Production Readiness Checklist
- ✅ Docker image optimized
- ✅ Health checks implemented
- ✅ Environment variables configured
- ✅ Database connected
- ✅ Static files served
- ✅ Security headers enabled
- ✅ Error handling implemented
- ✅ Logging configured

Your LaborLooker platform is now ready for production deployment on Railway! 🎉