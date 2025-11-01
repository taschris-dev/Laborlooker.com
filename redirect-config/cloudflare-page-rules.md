# Cloudflare Page Rules for LaborLooker Migration

## 🔄 Bulk Redirect Configuration

### Free Tier (3 Page Rules)
```
1. Redirect old API endpoints:
   Pattern: oldsite.com/api/*
   Redirect: 301 → https://api.laborlooker.com/api/v1/$1

2. Redirect dashboard/app pages:
   Pattern: oldsite.com/dashboard*
   Redirect: 301 → https://app.laborlooker.com/dashboard$1

3. Redirect main site:
   Pattern: oldsite.com/*
   Redirect: 301 → https://app.laborlooker.com/$1
```

### Pro Tier ($20/month - 20 Page Rules)
```
More granular redirects:

1. API v1 → v1
   oldsite.com/api/v1/* → api.laborlooker.com/api/v1/$1

2. User profiles
   oldsite.com/profile/* → app.laborlooker.com/profile/$1

3. Work requests
   oldsite.com/work/* → app.laborlooker.com/work/$1

4. Authentication
   oldsite.com/login → app.laborlooker.com/auth/signin
   oldsite.com/register → app.laborlooker.com/auth/signup

5. Dashboard sections
   oldsite.com/dashboard/jobs → app.laborlooker.com/dashboard/work-requests
   oldsite.com/dashboard/profile → app.laborlooker.com/dashboard/profile
   oldsite.com/dashboard/payments → app.laborlooker.com/dashboard/payments

6. Static assets
   oldsite.com/static/* → cdn.laborlooker.com/assets/$1

7. Admin routes
   oldsite.com/admin/* → app.laborlooker.com/admin/$1

8. Help/Support
   oldsite.com/help → app.laborlooker.com/support
   oldsite.com/contact → app.laborlooker.com/contact

9. Legal pages
   oldsite.com/terms → app.laborlooker.com/legal/terms
   oldsite.com/privacy → app.laborlooker.com/legal/privacy

10. API documentation
    oldsite.com/docs → api.laborlooker.com/docs

And 10 more rules for specific endpoints...
```

## 🚀 Implementation Steps

### 1. Set up Cloudflare Page Rules
```bash
# In Cloudflare Dashboard:
1. Go to Rules → Page Rules
2. Create new rule
3. Enter URL pattern: oldsite.com/*
4. Add Setting: Forwarding URL
5. Status Code: 301 (Permanent Redirect)
6. Destination: https://app.laborlooker.com/$1
7. Save and Deploy
```

### 2. Test Redirects
```bash
# Test key URLs:
curl -I http://oldsite.com/profile/123
# Should return: 301 → https://app.laborlooker.com/profile/123

curl -I http://oldsite.com/api/users
# Should return: 301 → https://api.laborlooker.com/api/v1/users
```

### 3. Monitor Redirect Analytics
- Track redirect performance in Cloudflare Analytics
- Monitor 404 errors for missed redirects
- Adjust rules based on user traffic patterns