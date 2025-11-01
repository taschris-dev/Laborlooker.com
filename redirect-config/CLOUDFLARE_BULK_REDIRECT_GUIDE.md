# 🔄 Cloudflare Bulk Redirect Implementation Guide

## Step-by-Step Setup Process

### 📋 Prerequisites
- Cloudflare account with your domain added
- DNS pointed to Cloudflare (orange cloud enabled)
- Access to Cloudflare Dashboard

---

## 🎯 Recommended Approach: Start with FREE Page Rules

### **Phase 1: Free Tier (3 Page Rules) - Covers 90% of Traffic**

**Rule Priority Order (Important!):**

#### Rule 1: API Endpoints (Highest Priority)
```
URL Pattern: your-old-domain.com/api/*
Setting: Forwarding URL
Status Code: 301 - Permanent Redirect
Destination URL: https://api.laborlooker.com/api/v1/$1
```

#### Rule 2: Dashboard/App Routes
```
URL Pattern: your-old-domain.com/dashboard*
Setting: Forwarding URL  
Status Code: 301 - Permanent Redirect
Destination URL: https://app.laborlooker.com/dashboard$1
```

#### Rule 3: Catch-All (Everything Else)
```
URL Pattern: your-old-domain.com/*
Setting: Forwarding URL
Status Code: 301 - Permanent Redirect  
Destination URL: https://app.laborlooker.com/$1
```

---

## 💡 Implementation Steps

### Step 1: Access Cloudflare Dashboard
1. Login to cloudflare.com
2. Select your domain
3. Go to **Rules** → **Page Rules**

### Step 2: Create Rules (In This Exact Order!)
```bash
# Rule 1 - API Routes (Most Specific First)
Pattern: your-old-domain.com/api/*
→ https://api.laborlooker.com/api/v1/$1

# Rule 2 - Dashboard Routes  
Pattern: your-old-domain.com/dashboard*
→ https://app.laborlooker.com/dashboard$1

# Rule 3 - Everything Else (Catch-All Last)
Pattern: your-old-domain.com/*
→ https://app.laborlooker.com/$1
```

### Step 3: Test Your Redirects
```bash
# Test in browser or with curl:
curl -I http://your-old-domain.com/api/users
# Should return: 301 → https://api.laborlooker.com/api/v1/users

curl -I http://your-old-domain.com/dashboard
# Should return: 301 → https://app.laborlooker.com/dashboard

curl -I http://your-old-domain.com/profile/123  
# Should return: 301 → https://app.laborlooker.com/profile/123
```

---

## 🚀 Advanced: Pro Tier (20 Page Rules) - $20/month

**If you need more granular control, upgrade to Pro and add these specific rules:**

### Additional Rules (4-20):
```bash
# Authentication Routes
4. your-old-domain.com/login → https://app.laborlooker.com/auth/signin
5. your-old-domain.com/register → https://app.laborlooker.com/auth/signup
6. your-old-domain.com/logout → https://app.laborlooker.com/auth/signout

# Profile Routes
7. your-old-domain.com/profile/* → https://app.laborlooker.com/profiles/$1
8. your-old-domain.com/contractor/* → https://app.laborlooker.com/professionals/$1

# Work Routes
9. your-old-domain.com/jobs → https://app.laborlooker.com/work-requests
10. your-old-domain.com/work-request/* → https://app.laborlooker.com/work/$1
11. your-old-domain.com/post-job → https://app.laborlooker.com/work-requests/new

# Support Routes
12. your-old-domain.com/help → https://app.laborlooker.com/support
13. your-old-domain.com/contact → https://app.laborlooker.com/support/contact

# Legal Routes
14. your-old-domain.com/terms → https://app.laborlooker.com/legal/terms
15. your-old-domain.com/privacy → https://app.laborlooker.com/legal/privacy

# Static Assets
16. your-old-domain.com/static/* → https://cdn.laborlooker.com/assets/$1

# Admin Routes
17. your-old-domain.com/admin/* → https://app.laborlooker.com/admin/$1

# API Documentation
18. your-old-domain.com/docs → https://api.laborlooker.com/docs

# Legacy mobile routes
19. your-old-domain.com/mobile/* → https://app.laborlooker.com/$1

# Catch remaining (should be last)
20. your-old-domain.com/* → https://app.laborlooker.com/$1
```

---

## ⚠️ Important Configuration Notes

### Rule Order Matters!
- **Most specific patterns first**
- **Catch-all patterns last**
- Cloudflare processes rules top-to-bottom

### URL Pattern Syntax:
- `*` = wildcard (matches any characters)
- `$1` = captures the first wildcard match
- Case-insensitive by default

### Testing Commands:
```bash
# Test redirect headers
curl -I http://your-old-domain.com/test-path

# Test redirect with full response
curl -L http://your-old-domain.com/test-path

# Check redirect in browser developer tools:
# Network tab → See 301 responses
```

---

## 📊 Monitoring & Analytics

### Track Redirect Performance:
1. **Cloudflare Analytics** → **Traffic** → View redirect stats
2. **Google Search Console** → Monitor 301 redirects
3. **Server logs** → Check for 404s that need additional redirects

### Common Issues to Watch:
- **Redirect loops** (A→B→A)
- **404 errors** on missed patterns  
- **Performance impact** (should be minimal)

---

## ✅ Recommended Action Plan

### Immediate (Today):
1. **Set up FREE Page Rules** (3 rules above)
2. **Test major user flows** 
3. **Monitor for 48 hours**

### Week 1:
1. **Check analytics** for missed redirects
2. **Add specific rules** if needed (upgrade to Pro)
3. **Update internal links** to new URLs

### Week 2:
1. **Optimize based on data**
2. **Remove unused rules**
3. **Document final configuration**

---

## 💰 Cost Comparison

| Tier | Rules | Cost/Month | Coverage |
|------|-------|------------|----------|
| Free | 3 | $0 | 90%+ |
| Pro | 20 | $20 | 99%+ |
| Business | 50 | $200 | 99.9%+ |

**Recommendation**: Start with **FREE** tier - it covers most use cases!