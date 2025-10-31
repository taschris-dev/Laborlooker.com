# Setting Up www.laborlooker.com - Complete Deployment Guide

## 🌐 **DOMAIN SETUP PROCESS**

### **Step 1: Domain Registration**
1. **Purchase the domain** `laborlooker.com` from a registrar:
   - **Recommended:** Namecheap, Google Domains, or Cloudflare
   - **Cost:** ~$10-15/year
   - **Make sure to get:** Both `laborlooker.com` and `www.laborlooker.com`

### **Step 2: Choose Hosting Platform**

#### **Option A: Google Cloud Platform (Recommended)**
```bash
# Deploy URL will be: https://laborlooker-platform.uc.r.appspot.com
# Then map custom domain to: https://www.laborlooker.com
```

#### **Option B: Heroku**
```bash
# Deploy URL will be: https://laborlooker-platform.herokuapp.com  
# Then map custom domain to: https://www.laborlooker.com
```

#### **Option C: DigitalOcean/AWS/Azure**
```bash
# Deploy to VPS/Container service
# Map custom domain to: https://www.laborlooker.com
```

### **Step 3: DNS Configuration**

#### **For Google Cloud Platform:**
1. Deploy your app to Google App Engine
2. Go to Google Cloud Console → App Engine → Settings → Custom Domains
3. Add custom domain: `www.laborlooker.com`
4. Update your domain registrar DNS with provided records:
   ```
   Type: CNAME
   Name: www
   Value: ghs.googlehosted.com
   
   Type: A
   Name: @
   Value: [Google's IP addresses]
   ```

#### **For Other Hosting Providers:**
1. Get your hosting provider's IP address or CNAME target
2. Update DNS records at your domain registrar:
   ```
   Type: A
   Name: www
   Value: [Your server IP]
   
   Type: A  
   Name: @
   Value: [Your server IP]
   ```

## 🚀 **DEPLOYMENT STEPS**

### **Step 1: Prepare Production Environment**
```bash
# 1. Copy production environment file
cp .env.production .env

# 2. Update production values in .env:
#    - Generate new SECRET_KEY
#    - Set production database URL
#    - Configure live PayPal credentials
#    - Set DocuSign production URLs
```

### **Step 2: Update Application Configuration**

#### **A. Generate Production Secret Key:**
```python
# Run this to generate a secure secret key:
python -c "import secrets; print(secrets.token_hex(32))"
```

#### **B. Update DocuSign for Production:**
1. **In DocuSign Developer Console:**
   - Add redirect URI: `https://www.laborlooker.com/docusign/callback`
   - Switch from demo to production environment
   - Update your `.env` file with production DocuSign URLs

#### **C. Update Email Configuration:**
```bash
# In .env file:
MAIL_DEFAULT_SENDER=noreply@laborlooker.com
```

### **Step 3: Database Setup**

#### **For Production Database:**
```bash
# Option 1: PostgreSQL (Recommended)
DATABASE_URL=postgresql://username:password@host:port/laborlooker_prod

# Option 2: MySQL
DATABASE_URL=mysql://username:password@host:port/laborlooker_prod
```

### **Step 4: Deploy Application**

#### **Google Cloud Platform:**
```bash
# 1. Install Google Cloud SDK
# 2. Initialize project
gcloud init

# 3. Deploy application
gcloud app deploy app.yaml

# 4. Map custom domain
gcloud app domain-mappings create www.laborlooker.com
```

#### **Heroku:**
```bash
# 1. Install Heroku CLI
# 2. Create Heroku app
heroku create laborlooker-platform

# 3. Set environment variables
heroku config:set SECRET_KEY=your-production-secret-key
heroku config:set FLASK_ENV=production

# 4. Deploy
git push heroku main

# 5. Add custom domain
heroku domains:add www.laborlooker.com
```

## 🔒 **SSL/HTTPS SETUP**

### **Automatic SSL (Recommended):**
- **Google Cloud:** SSL automatically provided for custom domains
- **Heroku:** SSL automatically provided for custom domains
- **Cloudflare:** Free SSL certificate + CDN

### **Manual SSL:**
If using VPS/custom hosting:
```bash
# Use Let's Encrypt for free SSL
sudo certbot --nginx -d www.laborlooker.com -d laborlooker.com
```

## 📧 **EMAIL DOMAIN SETUP**

### **Option 1: Gmail for Business**
1. Set up Google Workspace for `laborlooker.com`
2. Create email: `noreply@laborlooker.com`
3. Use for system emails

### **Option 2: Keep Current Gmail**
```bash
# Continue using: taschris.executive@gmail.com
# But set sender name as: LaborLooker Platform
```

## 🧪 **TESTING PRODUCTION SETUP**

### **Before Going Live:**
1. **Test on staging domain:** `staging.laborlooker.com`
2. **Verify all features work:**
   - User registration/login
   - Contract creation and DocuSign integration
   - Payment processing with PayPal
   - Email notifications
3. **Check SSL certificate** is properly installed
4. **Test mobile responsiveness**

### **Launch Checklist:**
- [ ] Domain DNS propagated (24-48 hours)
- [ ] SSL certificate active
- [ ] All environment variables configured
- [ ] Database migrations completed
- [ ] DocuSign integration tested
- [ ] PayPal payments working
- [ ] Email notifications sending
- [ ] Analytics/monitoring setup

## 🎯 **POST-LAUNCH TASKS**

### **SEO & Analytics:**
1. **Google Analytics:** Add tracking code
2. **Google Search Console:** Submit sitemap
3. **Social Media:** Update business profiles with new domain

### **Marketing Updates:**
1. **Business cards** with www.laborlooker.com
2. **Email signatures** with new domain
3. **Social media profiles** updated
4. **Redirect old domains** if applicable

## 💰 **ESTIMATED COSTS**

```
Domain Registration: $12/year
Google Cloud Hosting: $20-50/month
SSL Certificate: FREE (auto-provided)
Email (Google Workspace): $6/month/user
Total: ~$30-70/month
```

## 🆘 **SUPPORT RESOURCES**

- **Domain Issues:** Contact your registrar support
- **Hosting Issues:** Check platform-specific documentation
- **SSL Issues:** Use SSL checker tools online
- **DNS Issues:** Use DNS propagation checker tools

**Your www.laborlooker.com site will be live once you complete these steps!**