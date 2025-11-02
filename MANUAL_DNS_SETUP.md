# Manual DNS Setup Instructions for LaborLooker.com

## 🎯 Quick Setup Steps

### Step 1: Login to Cloudflare Dashboard
1. Go to https://dash.cloudflare.com
2. Login with: `taschris.executive@gmail.com`
3. Account ID: `53e110a235165a6bf12956639c215d4b`

### Step 2: Select Your Domain
If `laborlooker.com` is not already added:
1. Click "Add a Site"
2. Enter `laborlooker.com`
3. Choose Free plan
4. Follow nameserver setup instructions from your domain registrar

### Step 3: Add DNS Records
Go to DNS > Records and add these **EXACT** records:

```
Record 1 - Root Domain:
Type: A
Name: @ 
Content: 192.0.2.1
Proxy status: 🟠 Proxied
TTL: Auto

Record 2 - WWW Subdomain:
Type: A
Name: www
Content: 192.0.2.1  
Proxy status: 🟠 Proxied
TTL: Auto

Record 3 - App Subdomain:
Type: A
Name: portal
Content: 192.0.2.1
Proxy status: 🟠 Proxied
TTL: Auto

Record 4 - API Subdomain:
Type: A
Name: rest
Content: 192.0.2.1
Proxy status: 🟠 Proxied
TTL: Auto

Record 5 - CDN Subdomain:
Type: CNAME
Name: assets
Content: laborlooker.r2.dev
Proxy status: 🟠 Proxied
TTL: Auto
```

### Step 4: SSL/TLS Configuration
1. Go to SSL/TLS > Overview
2. Set encryption mode to: **"Full (strict)"**
3. Go to SSL/TLS > Edge Certificates
4. Enable "Always Use HTTPS"
5. Enable "HTTP Strict Transport Security (HSTS)"

### Step 5: Enable Worker Routes
After DNS records are saved, we'll enable the Worker routes.

## ⚡ Important Notes:
- The IP `192.0.2.1` is a placeholder - Workers will handle all traffic
- **Orange cloud (🟠 Proxied) is REQUIRED** - don't use DNS Only
- DNS changes can take 5-60 minutes to propagate globally

## 🧪 Verification Commands:
After DNS setup, run these to verify:

```bash
# Check DNS propagation
nslookup laborlooker.com

# Test worker response
curl -I https://chris.taschris-executive.workers.dev

# Check if domain resolves to Cloudflare
dig laborlooker.com +short
```

## 📞 Next Steps:
Once you confirm the DNS records are added in Cloudflare dashboard:
1. Let me know and I'll help enable the Worker routes
2. We'll deploy the updated configuration
3. Test all subdomains are working

---
**Current Status:** DNS records need to be added manually in Cloudflare dashboard
**Time Required:** 5 minutes setup + 5-60 minutes DNS propagation