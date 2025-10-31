# 🚀 **Going LIVE - Production Deployment Guide**

## 📋 **Pre-Launch Checklist**

### 1. **Security Updates (CRITICAL)**
- [ ] Change `SECRET_KEY` to a random 32+ character string
- [ ] Update Gmail app password for production
- [ ] Switch PayPal from sandbox to live mode
- [ ] Set `FLASK_ENV=production` and `FLASK_DEBUG=0`

### 2. **Database Migration**
- [ ] Choose production database (PostgreSQL recommended)
- [ ] Set up database backup system
- [ ] Configure database connection string

### 3. **Email Setup**
- [ ] Verify Gmail app password works in production
- [ ] Test email delivery to external addresses
- [ ] Set up email monitoring/logging

### 4. **Payment Processing**
- [ ] Complete PayPal business verification
- [ ] Test live payment processing
- [ ] Set up webhook endpoints for payment notifications

## 🌐 **Deployment Options**

### **Option 1: Heroku (Easiest)**
```bash
# Install Heroku CLI
# Create Heroku app
heroku create your-referral-engine

# Add PostgreSQL database
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set SECRET_KEY=your-production-secret-key
heroku config:set MAIL_PASSWORD=your-gmail-app-password
heroku config:set PAYPAL_CLIENT_ID=your-live-paypal-client-id
heroku config:set PAYPAL_CLIENT_SECRET=your-live-paypal-secret
heroku config:set PAYPAL_MODE=live
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main
```

### **Option 2: DigitalOcean App Platform**
- Upload code to GitHub
- Connect DigitalOcean to your repository
- Configure environment variables
- Deploy with 1-click

### **Option 3: AWS/Azure (Advanced)**
- Set up EC2/App Service
- Configure load balancer
- Set up database (RDS/Azure SQL)
- Configure auto-scaling

## ⚙️ **Required Configuration Changes**

### **1. Update app.py for Production**
```python
# Add at the top of app.py
import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

# Production database URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/referral.db')

# Security settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
```

### **2. Create requirements.txt for Production**
```
Flask==3.0.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Werkzeug==3.0.3
itsdangerous==2.2.0
pandas==2.0.3
Pillow==10.0.0
qrcode==7.4.2
shortuuid==1.0.11
python-dotenv==1.0.1
paypalrestsdk==1.13.1
gunicorn==21.2.0
psycopg2-binary==2.9.7
```

### **3. Create Procfile (for Heroku)**
```
web: gunicorn app:app
release: python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### **4. Production Environment Variables**
```env
# Security
SECRET_KEY=your-super-secure-random-32-char-key
FLASK_ENV=production
FLASK_DEBUG=0

# Database (provided by hosting service)
DATABASE_URL=postgresql://...

# Email (Gmail)
MAIL_USERNAME=taschris.executive@gmail.com
MAIL_PASSWORD=your-gmail-app-password

# PayPal (LIVE MODE)
PAYPAL_CLIENT_ID=your-live-paypal-client-id
PAYPAL_CLIENT_SECRET=your-live-paypal-client-secret
PAYPAL_MODE=live
```

## 🔒 **Security Hardening**

### **Required Security Updates:**
1. **Generate new SECRET_KEY:**
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

2. **Update CSRF protection**
3. **Add rate limiting**
4. **Enable HTTPS only**
5. **Set secure cookie flags**

## 💰 **PayPal Live Setup**

### **Switch to Live Mode:**
1. Login to PayPal Business account
2. Go to PayPal Developer Dashboard
3. Create LIVE app (not sandbox)
4. Get live Client ID and Secret
5. Update environment variables:
   ```env
   PAYPAL_MODE=live
   PAYPAL_CLIENT_ID=live-client-id
   PAYPAL_CLIENT_SECRET=live-client-secret
   ```

## 📧 **Email Production Setup**

### **Gmail Configuration:**
1. Ensure 2FA is enabled on taschris.executive@gmail.com
2. Generate new app password for production
3. Test email delivery to external addresses
4. Monitor email sending limits (500/day for Gmail)

## 🏃‍♂️ **Quick Launch Steps (Heroku)**

1. **Prepare for deployment:**
   ```bash
   # Create production files
   echo "web: gunicorn app:app" > Procfile
   pip freeze > requirements.txt
   git add .
   git commit -m "Production ready"
   ```

2. **Deploy to Heroku:**
   ```bash
   heroku create your-app-name
   heroku addons:create heroku-postgresql:mini
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   heroku config:set FLASK_ENV=production
   heroku config:set MAIL_USERNAME=taschris.executive@gmail.com
   heroku config:set MAIL_PASSWORD=your-gmail-app-password
   heroku config:set PAYPAL_CLIENT_ID=your-live-client-id
   heroku config:set PAYPAL_CLIENT_SECRET=your-live-secret
   heroku config:set PAYPAL_MODE=live
   git push heroku main
   ```

3. **Your app will be live at:** `https://your-app-name.herokuapp.com`

## 🎯 **Post-Launch Tasks**

- [ ] Test all functionality on live site
- [ ] Monitor error logs
- [ ] Set up database backups
- [ ] Configure monitoring/alerts
- [ ] Set up custom domain (optional)
- [ ] SSL certificate (automatic on most platforms)

Your referral engine is production-ready! Choose your deployment method and go live! 🚀