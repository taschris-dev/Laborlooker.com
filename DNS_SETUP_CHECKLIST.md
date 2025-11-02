# DNS Setup Checklist for LaborLooker.com

## ✅ Prerequisites Verification
- [x] Railway Backend: `https://laborlookercom-production.up.railway.app`
- [x] Cloudflare Worker: `https://chris.taschris-executive.workers.dev`
- [x] Domain: `laborlooker.com` (assumed - confirm ownership)
- [x] Cloudflare Account: Active with Worker deployed

## 🔧 Step 1: Cloudflare DNS Records Setup

### Required DNS Records:
Copy these settings into your Cloudflare DNS dashboard:

```
Record 1:
Type: A
Name: @
Content: 192.0.2.1
Proxy status: Proxied (🟠)
TTL: Auto

Record 2:
Type: A  
Name: www
Content: 192.0.2.1
Proxy status: Proxied (🟠)
TTL: Auto

Record 3:
Type: A
Name: app
Content: 192.0.2.1
Proxy status: Proxied (🟠)
TTL: Auto

Record 4:
Type: A
Name: api
Content: 192.0.2.1
Proxy status: Proxied (🟠)
TTL: Auto

Record 5:
Type: CNAME
Name: cdn
Content: laborlooker.r2.dev
Proxy status: Proxied (🟠)
TTL: Auto
```

## 🔧 Step 2: Enable Worker Routes

After DNS records are created, uncomment routes in wrangler.toml:

```toml
[[routes]]
pattern = "laborlooker.com/*"
zone_name = "laborlooker.com"

[[routes]]
pattern = "www.laborlooker.com/*"  
zone_name = "laborlooker.com"

[[routes]]
pattern = "app.laborlooker.com/*"
zone_name = "laborlooker.com"

[[routes]]
pattern = "api.laborlooker.com/*"
zone_name = "laborlooker.com"
```

## 🔧 Step 3: SSL/TLS Configuration

In Cloudflare Dashboard:
1. Go to SSL/TLS → Overview
2. Set encryption mode to: **Full (strict)**
3. Enable "Always Use HTTPS"
4. Enable "HTTP Strict Transport Security (HSTS)"

## 🔧 Step 4: Deploy Updated Worker

After enabling routes, redeploy the worker:
```bash
cd modern-deployment/cloudflare-workers
wrangler deploy
```

## 🔧 Step 5: Page Rules (Optional Performance Optimization)

Add these Page Rules in Cloudflare:
1. `laborlooker.com/static/*` - Cache Everything, Edge Cache TTL: 30 days
2. `laborlooker.com/api/*` - Cache Level: Bypass
3. `laborlooker.com/uploads/*` - Cache Everything, Edge Cache TTL: 7 days

## 🧪 Step 6: Testing Checklist

After setup, test these URLs:
- [ ] `https://laborlooker.com` - Main site loads
- [ ] `https://www.laborlooker.com` - Redirects to main domain
- [ ] `https://app.laborlooker.com` - App interface loads
- [ ] `https://api.laborlooker.com/health` - API health check
- [ ] `https://cdn.laborlooker.com` - CDN serves static files

## 🔧 Commands to Run:

1. **Check current Cloudflare zones:**
   ```bash
   wrangler zone list
   ```

2. **Deploy worker with routes:**
   ```bash
   cd modern-deployment/cloudflare-workers
   wrangler deploy
   ```

3. **Test worker functionality:**
   ```bash
   curl -I https://chris.taschris-executive.workers.dev
   ```

## 📝 Notes:
- DNS propagation can take 5-60 minutes
- The 192.0.2.1 IP is a placeholder - Workers handle all traffic
- Orange cloud (Proxied) is REQUIRED for Workers
- Keep Railway URL as fallback during migration

## 🚨 Rollback Plan:
If issues occur, comment out routes in wrangler.toml and redeploy:
```bash
wrangler deploy
```
Users will fall back to Railway direct access.