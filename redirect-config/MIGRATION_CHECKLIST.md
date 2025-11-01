# 📋 LaborLooker Migration Redirect Checklist

## Quick Setup Checklist

### ✅ Pre-Migration Setup
- [ ] Domain added to Cloudflare
- [ ] DNS records pointing to Cloudflare (orange cloud)
- [ ] SSL/TLS configured (Full or Full Strict)
- [ ] New Railway deployment live and tested

### ✅ Cloudflare Page Rules Setup

#### Rule 1: API Redirects (Priority: 1)
```
Pattern: OLD-DOMAIN.com/api/*
Setting: Forwarding URL (301)
Destination: https://api.laborlooker.com/api/v1/$1
Status: [ ] Created [ ] Tested
```

#### Rule 2: Dashboard Redirects (Priority: 2)  
```
Pattern: OLD-DOMAIN.com/dashboard*
Setting: Forwarding URL (301)
Destination: https://app.laborlooker.com/dashboard$1
Status: [ ] Created [ ] Tested
```

#### Rule 3: Catch-All Redirects (Priority: 3)
```
Pattern: OLD-DOMAIN.com/*
Setting: Forwarding URL (301)  
Destination: https://app.laborlooker.com/$1
Status: [ ] Created [ ] Tested
```

### ✅ Testing Checklist

#### Critical User Paths:
- [ ] Homepage: `OLD-DOMAIN.com` → `app.laborlooker.com`
- [ ] Login: `OLD-DOMAIN.com/login` → `app.laborlooker.com/auth/signin`
- [ ] Dashboard: `OLD-DOMAIN.com/dashboard` → `app.laborlooker.com/dashboard`
- [ ] API: `OLD-DOMAIN.com/api/users` → `api.laborlooker.com/api/v1/users`
- [ ] Profile: `OLD-DOMAIN.com/profile/123` → `app.laborlooker.com/profile/123`

#### Testing Commands:
```bash
# Replace OLD-DOMAIN.com with your actual old domain
curl -I http://OLD-DOMAIN.com/
curl -I http://OLD-DOMAIN.com/dashboard
curl -I http://OLD-DOMAIN.com/api/users
curl -I http://OLD-DOMAIN.com/profile/test
```

### ✅ Post-Migration Monitoring

#### Week 1:
- [ ] Check Cloudflare Analytics for redirect volume
- [ ] Monitor Railway logs for 404 errors
- [ ] Review Google Search Console for crawl errors
- [ ] Test user-reported issues

#### Week 2:
- [ ] Optimize redirect rules based on data
- [ ] Add specific rules for high-traffic patterns
- [ ] Update internal documentation
- [ ] Train support team on new URLs

### ✅ SEO Preservation
- [ ] Submit updated sitemap to Google Search Console
- [ ] Update Google Business Profile URLs
- [ ] Update social media profile links
- [ ] Notify email subscribers of URL changes
- [ ] Update marketing materials

---

## 🚨 Emergency Rollback Plan

If issues arise:

1. **Disable Page Rules**: Turn off redirect rules in Cloudflare
2. **DNS Rollback**: Point DNS back to old server temporarily  
3. **Communication**: Notify users via email/social media
4. **Fix and Re-enable**: Address issues and re-enable redirects

---

## 📞 Support Contacts

- **Cloudflare Support**: Available 24/7 for Pro+ plans
- **Railway Support**: Available via Discord/Email
- **Team Lead**: [Your contact info]

---

## 📈 Success Metrics

Target metrics to track:

- **Redirect Success Rate**: >99%
- **Page Load Time**: <500ms additional latency
- **SEO Rankings**: Maintain within 2 weeks
- **User Complaints**: <1% of active users

**Ready to implement? Start with the FREE Page Rules setup! 🚀**