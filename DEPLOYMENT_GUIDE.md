# 🚀 LaborLookers Modern Deployment Guide

This guide will help you deploy the modernized LaborLookers platform using the new cloud-native architecture.

## 📋 Architecture Overview

- **API Service**: NestJS API with PostgreSQL + Prisma
- **Web App**: Next.js with App Router and TypeScript
- **WebSocket Service**: Socket.IO for real-time features
- **Worker Service**: BullMQ for background job processing
- **Database**: PostgreSQL with Prisma ORM
- **Cache**: Redis for sessions and job queues
- **Deployment**: Railway with Cloudflare CDN
- **CI/CD**: GitHub Actions

## 🔧 Prerequisites

1. **Node.js 20+** and **pnpm 8+**
2. **Railway CLI** installed globally
3. **Cloudflare account** with domain
4. **GitHub repository** for CI/CD
5. **SMTP provider** for emails (Gmail recommended)

## 🛠️ Local Development Setup

### 1. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd modern-deployment
pnpm install
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Start local PostgreSQL and Redis
docker-compose up -d

# Generate Prisma client and run migrations
pnpm --filter=@laborlookers/api prisma generate
pnpm --filter=@laborlookers/api prisma db push
```

### 4. Start Development Services

```bash
# Start all services in development mode
pnpm dev

# Or start individual services
pnpm --filter=@laborlookers/api dev     # API on :3000
pnpm --filter=@laborlookers/web dev     # Web on :3001
pnpm --filter=@laborlookers/ws dev      # WebSocket on :3002
pnpm --filter=@laborlookers/worker dev  # Worker on :3003
```

## 🌍 Production Deployment

### 1. Railway Setup

```bash
# Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# Login to Railway
railway login

# Link to your Railway project
railway link

# Deploy
railway up
```

### 2. Domain Configuration

Add these domains in Railway:
- `api.laborlookers.com` → API Service
- `app.laborlookers.com` → Web Service  
- `ws.laborlookers.com` → WebSocket Service

### 3. Environment Variables

Set these in Railway dashboard:

#### Database & Cache
- `DATABASE_URL` - Railway PostgreSQL connection string
- `REDIS_URL` - Railway Redis connection string

#### Security
- `JWT_SECRET` - Strong random string (32+ chars)
- `NEXTAUTH_SECRET` - Strong random string (32+ chars)

#### Email
- `SMTP_HOST` - smtp.gmail.com
- `SMTP_PORT` - 587
- `SMTP_USER` - your-email@gmail.com
- `SMTP_PASS` - Gmail app password
- `SMTP_FROM` - noreply@laborlookers.com

#### Cloudflare
- `CLOUDFLARE_ACCOUNT_ID` - Your account ID
- `CLOUDFLARE_API_TOKEN` - API token with R2 permissions
- `CLOUDFLARE_R2_BUCKET` - laborlookers-assets

### 4. Database Migration

```bash
# Generate and apply database schema
railway run pnpm --filter=@laborlookers/api prisma generate
railway run pnpm --filter=@laborlookers/api prisma db push
```

## 🔐 Cloudflare R2 Setup

### 1. Create R2 Bucket

```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create R2 bucket
wrangler r2 bucket create laborlookers-assets
```

### 2. Configure Custom Domain

1. Go to Cloudflare Dashboard → R2 → Your Bucket
2. Add custom domain: `cdn.laborlookers.com`
3. Update DNS records as instructed

### 3. Set CORS Policy

```json
[
  {
    "AllowedOrigins": ["https://app.laborlookers.com", "https://laborlookers.com"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

## 🔄 CI/CD Setup

### 1. GitHub Secrets

Add these secrets to your GitHub repository:

- `RAILWAY_TOKEN` - Railway deployment token
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications (optional)

### 2. Get Railway Token

```bash
railway login
railway whoami --token
```

### 3. Automatic Deployments

The GitHub Actions workflow will:
- Run tests on every PR
- Deploy to Railway on main branch pushes
- Send Slack notifications on completion

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- API: `https://api.laborlookers.com/health`
- Web: `https://app.laborlookers.com/health`
- WebSocket: `https://ws.laborlookers.com/health`
- Worker: Internal health check in Railway

### Logging

All services use structured logging with Pino:
- Check Railway logs for service-specific issues
- Logs are automatically collected and searchable

## 🔧 Troubleshooting

### Common Issues

**Build Failures**
```bash
# Clear dependencies and reinstall
rm -rf node_modules packages/*/node_modules apps/*/node_modules
pnpm install --frozen-lockfile
```

**Database Connection Issues**
```bash
# Check DATABASE_URL format
# Ensure Railway PostgreSQL addon is connected
railway variables
```

**WebSocket Connection Issues**
- Verify CORS configuration
- Check JWT token validity
- Ensure WebSocket service is running

### Service Dependencies

Start order for local development:
1. PostgreSQL & Redis (docker-compose)
2. API Service (database dependent)
3. Worker Service (database + Redis dependent)
4. WebSocket Service (JWT dependent)
5. Web App (API dependent)

## 📈 Scaling Considerations

### Current Setup (Hobby Plan)
- PostgreSQL: 1GB storage, 100 connections
- Redis: 25MB memory
- Services: 512MB RAM each

### Production Scaling
- Upgrade Railway plan for more resources
- Enable Redis persistence for job queue reliability
- Consider CDN for static assets
- Implement database connection pooling

## 🔐 Security Checklist

- [ ] Strong JWT secrets (32+ characters)
- [ ] HTTPS everywhere (Railway provides automatically)
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Environment variables secured
- [ ] Database connection encrypted
- [ ] File upload restrictions in place
- [ ] Email verification enabled

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)
- [Prisma Deployment Guide](https://www.prisma.io/docs/guides/deployment)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Socket.IO Production](https://socket.io/docs/v4/deploying-production/)

## 🆘 Support

For deployment issues:
1. Check Railway service logs
2. Verify environment variables
3. Test health endpoints
4. Review GitHub Actions workflow

---

**Happy Deploying! 🎉**