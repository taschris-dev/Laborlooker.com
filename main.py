import os
import json
from datetime import datetime, timedelta
from io import BytesIO
import zipfile
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# For Google App Engine, we don't use dotenv
# Instead, environment variables are set in app.yaml
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Running on Google App Engine where dotenv might not be available
    pass

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import shortuuid
import jwt
import requests

# Optional imports - gracefully handle missing packages
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    import paypalrestsdk
    HAS_PAYPAL = True
except ImportError:
    HAS_PAYPAL = False
import logging
from functools import wraps

# --- Paths / App setup ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
QR_DIR = os.path.join(BASE_DIR, "static", "qr")
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)


app = Flask(__name__)

# Template filters for PII protection
@app.template_filter('mask_pii')
def mask_pii_filter(user_data, field_name, viewer_id=None):
    """Template filter to apply PII masking"""
    if not viewer_id and current_user.is_authenticated:
        viewer_id = current_user.id
    
    if not viewer_id:
        return user_data.get(field_name, '')
    
    # Apply masking
    masked_data = apply_pii_masking(user_data, viewer_id)
    return masked_data.get(field_name, user_data.get(field_name, ''))

@app.template_filter('mask_email')
def mask_email_filter(email, should_mask=True):
    """Template filter to mask email addresses"""
    return mask_email(email, should_mask)

@app.template_filter('mask_phone')
def mask_phone_filter(phone, should_mask=True):
    """Template filter to mask phone numbers"""
    return mask_phone(phone, should_mask)

@app.template_filter('mask_name')
def mask_name_filter(full_name, should_mask=True):
    """Template filter to mask full names"""
    if not full_name or not should_mask:
        return full_name
    
    parts = full_name.split(' ', 1)
    first_name = parts[0] if parts else ''
    last_name = parts[1] if len(parts) > 1 else ''
    return mask_name(first_name, last_name, should_mask)

# Google Cloud Platform Optimized Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Security Configuration for Production
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", "16777216"))  # 16MB

# Database configuration - Google Cloud optimized
database_url = os.environ.get("DATABASE_URL")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
google_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT")

if os.environ.get('GAE_ENV', '').startswith('standard'):
    # Running on Google App Engine
    if cloud_sql_connection_name:
        # Production: Google Cloud SQL (PostgreSQL)
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = os.environ.get("DB_NAME", "laborlooker")
        
        # Cloud SQL connection via Unix socket
        app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
        
        # Cloud SQL optimized engine options
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 5,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "max_overflow": 10,
            "pool_timeout": 30
        }
    else:
        # Development on GAE: SQLite with persistent storage
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///laborlooker.db"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "connect_args": {"check_same_thread": False}
        }
elif cloud_sql_connection_name:
    # Local development with Cloud SQL proxy
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD")
    db_name = os.environ.get("DB_NAME", "laborlooker")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{db_user}:{db_password}@127.0.0.1:5432/{db_name}"
elif database_url:
    # Other production databases (Railway, Heroku, etc.)
    # For now, use SQLite in production to ensure reliability
    print(f"PostgreSQL URL found but using SQLite for stability: {database_url}")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "referral.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False}
    }
    # Uncomment below when PostgreSQL is stable
    # try:
    #     if database_url.startswith("postgres://"):
    #         database_url = database_url.replace("postgres://", "postgresql://", 1)
    #     app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    #     app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    #         "pool_size": 5,
    #         "pool_recycle": 300,
    #         "pool_pre_ping": True,
    #         "max_overflow": 10,
    #         "pool_timeout": 30
    #     }
    # except Exception as e:
    #     print(f"Warning: PostgreSQL connection failed ({e}), falling back to SQLite")
    #     app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "referral.db")
    #     app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    #         "pool_pre_ping": True,
    #         "connect_args": {"check_same_thread": False}
    #     }
else:
    # Local development: SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "referral.db")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Google Cloud Logging Setup
if os.environ.get('GAE_ENV', '').startswith('standard'):
    # Enable Cloud Logging on Google App Engine
    try:
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()
    except ImportError:
        # Cloud logging not available in development
        pass

# Initialize Flask extensions
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "taschris.executive@gmail.com"
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "your-app-password")
app.config["MAIL_DEFAULT_SENDER"] = "taschris.executive@gmail.com"

# PayPal configuration
app.config["PAYPAL_CLIENT_ID"] = os.environ.get("PAYPAL_CLIENT_ID", "your-paypal-client-id")
app.config["PAYPAL_CLIENT_SECRET"] = os.environ.get("PAYPAL_CLIENT_SECRET", "your-paypal-client-secret")
app.config["PAYPAL_MODE"] = os.environ.get("PAYPAL_MODE", "sandbox")  # sandbox or live

# Configure PayPal SDK (only if available)
if HAS_PAYPAL:
    paypalrestsdk.configure({
        "mode": app.config["PAYPAL_MODE"],
        "client_id": app.config["PAYPAL_CLIENT_ID"],
        "client_secret": app.config["PAYPAL_CLIENT_SECRET"]
    })

db = SQLAlchemy(app)

# Request timeout and error handling
@app.before_request
def before_request():
    """Set request timeout and validation"""
    from flask import g
    g.start_time = datetime.utcnow()
    
@app.after_request  
def after_request(response):
    """Enhanced security headers and performance monitoring optimized for Google Cloud and mobile apps"""
    
    # Enhanced Security Headers for Google Cloud
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Enhanced Content Security Policy for PII Protection
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.tailwindcss.com "
        "https://cdnjs.cloudflare.com "
        "https://code.jquery.com "
        "https://www.paypal.com "
        "https://js.paypal.com "
        "https://maps.googleapis.com; "
        "style-src 'self' 'unsafe-inline' "
        "https://cdn.tailwindcss.com "
        "https://cdnjs.cloudflare.com "
        "https://fonts.googleapis.com; "
        "font-src 'self' "
        "https://cdnjs.cloudflare.com "
        "https://fonts.gstatic.com; "
        "img-src 'self' data: blob: "
        "https://maps.googleapis.com "
        "https://maps.gstatic.com "
        "https://www.paypal.com; "
        "connect-src 'self' "
        "https://api.paypal.com "
        "https://www.paypal.com "
        "https://api.laborlooker.com "
        "wss://laborlooker.com "
        "https://maps.googleapis.com; "
        "frame-src 'self' "
        "https://www.paypal.com "
        "https://js.paypal.com; "
        "object-src 'none'; "
        "media-src 'self'; "
        "manifest-src 'self'; "
        "worker-src 'self' blob:; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests;"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    
    # Additional PII Protection Headers
    response.headers['Permissions-Policy'] = (
        'geolocation=(self), '
        'microphone=(), '
        'camera=(), '
        'payment=(self "https://www.paypal.com"), '
        'usb=(), '
        'bluetooth=(), '
        'magnetometer=(), '
        'gyroscope=(), '
        'accelerometer=()'
    )
    
    # Data Protection Headers
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    response.headers['Cross-Origin-Embedder-Policy'] = 'unsafe-none'  # Allow PayPal embedding
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'  # Allow payment popups
    response.headers['Cross-Origin-Resource-Policy'] = 'same-site'
    
    # Privacy-specific headers
    if request.endpoint == 'logout':
        response.headers['Clear-Site-Data'] = '"cache", "cookies", "storage"'
    elif request.endpoint == 'delete_account':
        response.headers['Clear-Site-Data'] = '"*"'  # Clear everything on account deletion
    
    # Google Cloud Load Balancer Compatibility
    response.headers['X-Powered-By'] = 'LaborLooker/1.0'
    
    # Enhanced CORS Headers for Mobile App Compatibility
    origin = request.headers.get('Origin')
    mobile_origins = [
        'capacitor://localhost',      # Ionic/Capacitor
        'ionic://localhost',          # Ionic
        'http://localhost:3000',      # React Native development
        'http://localhost:19006',     # Expo development
        'http://localhost:8080',      # Flutter development
        'https://laborlooker.com',
        'https://www.laborlooker.com',
        'https://api.laborlooker.com'
    ]
    
    if origin:
        # Check for exact match or development localhost patterns
        allowed = origin in mobile_origins or (
            'localhost' in origin and any(port in origin for port in [':3000', ':8080', ':19006', ':3001'])
        )
        
        if allowed:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-API-Key'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
    
    # Enhanced Caching Headers for Performance
    if request.endpoint and 'static' in request.endpoint:
        # Static assets - long cache
        response.headers['Cache-Control'] = 'public, max-age=604800, immutable'  # 7 days
        expires_date = (datetime.utcnow() + timedelta(days=7)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        response.headers['Expires'] = expires_date
        response.headers['Vary'] = 'Accept-Encoding'
    elif request.endpoint and request.endpoint in ['health_check', 'startup_check', 'public_health']:
        # Health checks - no cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif request.path.startswith('/api/'):
        # API endpoints - no cache for dynamic data
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Add API-specific headers
        response.headers['X-API-Version'] = 'v1'
        response.headers['X-RateLimit-Limit'] = '100'
    else:
        # Dynamic content - short cache
        response.headers['Cache-Control'] = 'private, max-age=300'  # 5 minutes
    
    # Google Cloud specific optimizations
    response.headers['X-Cloud-Trace-Context'] = request.headers.get('X-Cloud-Trace-Context', '')
    
    # Compression headers
    if 'Accept-Encoding' in request.headers:
        response.headers['Vary'] = 'Accept-Encoding'
    
    # Performance monitoring
    from flask import g
    if hasattr(g, 'start_time'):
        duration = (datetime.utcnow() - g.start_time).total_seconds()
        response.headers['X-Response-Time'] = str(duration)
        
        # Log slow requests (over 5 seconds)
        if duration > 5.0:
            print(f"SLOW REQUEST: {request.endpoint} took {duration:.2f}s")
    
    return response

# Timeout handler
@app.errorhandler(408)
def request_timeout(_error):
    """Handle request timeout errors"""
    return jsonify({
        "error": "Request timeout",
        "message": "The request took too long to process. Please try again.",
        "status": 408
    }), 408

# Comprehensive Error Handlers
@app.errorhandler(400)
def bad_request(_error):
    """Handle bad request errors"""
    return jsonify({
        "error": "Bad Request",
        "message": "The request could not be understood by the server.",
        "status": 400
    }), 400

@app.errorhandler(401)
def unauthorized(_error):
    """Handle unauthorized errors"""
    return jsonify({
        "error": "Unauthorized",
        "message": "Authentication is required to access this resource.",
        "status": 401
    }), 401

@app.errorhandler(403)
def forbidden(_error):
    """Handle forbidden errors"""
    return jsonify({
        "error": "Forbidden",
        "message": "You don't have permission to access this resource.",
        "status": 403
    }), 403

@app.errorhandler(404)
def not_found(_error):
    """Handle not found errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested resource could not be found.",
        "status": 404
    }), 404

@app.errorhandler(500)
def internal_server_error(_error):
    """Handle internal server errors"""
    db.session.rollback()
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later.",
        "status": 500
    }), 500

@app.errorhandler(502)
def bad_gateway(_error):
    """Handle bad gateway errors"""
    return jsonify({
        "error": "Bad Gateway",
        "message": "The server received an invalid response from an upstream server.",
        "status": 502
    }), 502

@app.errorhandler(503)
def service_unavailable(_error):
    """Handle service unavailable errors"""
    return jsonify({
        "error": "Service Unavailable",
        "message": "The server is temporarily unavailable. Please try again later.",
        "status": 503
    }), 503

# Google Cloud Platform Health Check Endpoints
@app.route('/_ah/health')
def health_check():
    """Google App Engine health check endpoint"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db.session.commit()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
            "database": "connected",
            "service": "laborlooker"
        }), 200
    except (SQLAlchemyError, DatabaseError) as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

@app.route('/_ah/start')
def startup_check():
    """Google App Engine startup check endpoint"""
    return jsonify({
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "LaborLooker application started successfully"
    }), 200

@app.route('/health')
def public_health():
    """Public health check for monitoring"""
    return jsonify({
        "status": "operational",
        "service": "LaborLooker Rating System",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/readiness')
def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        db.session.commit()
        
        # Check if application is ready to receive traffic
        return jsonify({
            "status": "ready",
            "checks": {
                "database": "ok",
                "application": "ok"
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except (SQLAlchemyError, DatabaseError) as e:
        return jsonify({
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

@app.route('/liveness')
def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return jsonify({
        "status": "alive",
        "uptime": str(datetime.utcnow() - datetime.utcnow()),
        "timestamp": datetime.utcnow().isoformat()
    }), 200

# TEST DEPLOYMENT ROUTE
@app.route("/test-deployment-v3")
def test_deployment():
    """Test route to verify deployment is working"""
    return "DEPLOYMENT TEST v3.0 - Modern templates should be working! Time: " + str(datetime.utcnow())

# DIRECT TEMPLATE TEST
@app.route("/test-modern-template")
def test_modern_template():
    """Direct test of the modern welcome template"""
    return render_template('welcome.html')

# HOME PAGE ROUTE
@app.route("/")
def index():
    """Home page for LaborLooker marketplace - always check consent first"""
    try:
        # ALWAYS check consent first before anything else
        has_consent = (
            session.get('consent_granted') or 
            request.cookies.get('consent_granted') == 'true'
        )
        
        print(f"DEBUG: Index route - Has consent: {has_consent}")
        
        if not has_consent:
            # Store intended URL and redirect to consent
            session['intended_url'] = request.url
            print("DEBUG: Redirecting to consent")
            return redirect(url_for('consent_gateway'))
        
        # User has consented, check if they're logged in for dashboard routing
        if current_user.is_authenticated:
            if current_user.account_type == "networking":
                return redirect(url_for("networking_dashboard"))
            elif current_user.account_type == "professional":
                return redirect(url_for("professional_dashboard"))
            elif current_user.account_type == "job_seeker":
                return redirect(url_for("job_seeker_dashboard"))
            else:  # customer
                return redirect(url_for("customer_dashboard"))
        
        # For non-authenticated users who have consented, show welcome page
        print("DEBUG: Showing welcome page")
        return render_template('welcome.html')
        
    except Exception as e:
        print(f"DEBUG: Error in index route: {e}")
        # Temporarily bypass consent and show welcome page directly for testing
        print("DEBUG: Bypassing consent for testing - showing welcome page")
        return render_template('welcome.html')

@app.route('/main-dashboard')
def main_dashboard():
    """Main dashboard after consent"""
    try:
        # Check if consent has been granted
        has_consent = (
            session.get('consent_granted') or 
            request.cookies.get('consent_granted') == 'true'
        )
        
        if not has_consent:
            # Store intended URL and redirect to consent
            session['intended_url'] = request.url
            return redirect(url_for('consent_gateway'))
        
        # Show dashboard template
        return render_template('dashboard.html')
        
    except Exception as e:
        print(f"DEBUG: Error in dashboard route: {e}")
        # Fallback to welcome page
        return redirect(url_for('index'))

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore
login_manager.login_message = "Please log in to access this page."

# Register template functions
@app.template_global()
def calculate_user_rating_template(user_id):
    """Template function to calculate user rating"""
    return calculate_user_rating(user_id)

# Serializer for email tokens
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# Email sending function
def send_email(to_email, subject, body, html_body=None):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = app.config["MAIL_DEFAULT_SENDER"]
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text content
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML content if provided
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send the email
        server = smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"])
        server.starttls()
        server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        text = msg.as_string()
        server.sendmail(app.config["MAIL_DEFAULT_SENDER"], to_email, text)
        server.quit()
        return True
    except (smtplib.SMTPException, OSError) as e:
        print(f"Failed to send email: {e}")
        return False

def send_invoice_email(invoice, customer_email):
    """Send invoice to customer via email"""
    subject = f"Invoice #{invoice.id} from {current_user.email if current_user else 'Contractor'}"
    
    # Create payment link (will integrate with PayPal later)
    payment_url = url_for('pay_invoice', invoice_id=invoice.id, _external=True)
    
    body = f"""
    You have received a new invoice:
    
    Invoice #: {invoice.id}
    Amount: ${invoice.amount:.2f}
    Commission: ${invoice.commission_amount:.2f}
    Due Date: {invoice.due_date if invoice.due_date else 'Upon receipt'}
    
    Description:
    {invoice.description}
    
    Pay online: {payment_url}
    
    Marketing Tech Platform
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Invoice #{invoice.id}</h2>
        <table style="border-collapse: collapse; border: 1px solid #ddd; width: 100%; max-width: 600px;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Amount:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">${invoice.amount:.2f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Due Date:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{invoice.due_date if invoice.due_date else 'Upon receipt'}</td></tr>
        </table>
        
        <h3>Description:</h3>
        <p>{invoice.description}</p>
        
        <p style="margin: 20px 0;">
            <a href="{payment_url}" 
               style="background-color: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
                Pay Invoice Online
            </a>
        </p>
        
        <hr>
        <p><small>Marketing Tech Platform</small></p>
    </body>
    </html>
    """
    
    return send_email(customer_email, subject, body, html_body)

# Invoice payment route (placeholder for PayPal integration)
@app.route("/pay_invoice/<int:invoice_id>")
def pay_invoice(invoice_id):
    """Payment page for invoices"""
    invoice = ContractorInvoice.query.get_or_404(invoice_id)
    return render_template("payment/pay_invoice.html", invoice=invoice)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Service categories for contractors
SERVICE_CATEGORIES = [
    "realtor", "real estate lawyer", "architect/building designer", "surveyor", 
    "masonry", "plumbing", "structural engineer", "structural repair", "foundation",
    "rough carpentry", "flooring", "electrical", "insulation", "drywall", 
    "interior painting", "finish carpentry", "kitchens", "millwork", "bathrooms",
    "roofing", "cleaning", "waste management", "inspections", "pest control",
    "exterior painting and staining", "crawl spaces", "landscaping", "advertise"
]

# Geographic areas
GEOGRAPHIC_AREAS = ["low country", "midlands", "upstate"]

# Password validation
def validate_password(password):
    """Validate password meets requirements: 15 chars, 2 uppercase, 1 symbol"""
    if len(password) < 15:
        return False, "Password must be at least 15 characters long"
    
    uppercase_count = sum(1 for c in password if c.isupper())
    if uppercase_count < 2:
        return False, "Password must contain at least 2 uppercase letters"
    
    symbols = "!@_-."
    if not any(c in symbols for c in password):
        return False, "Password must contain at least one symbol (!@_-.)"
    
    return True, "Password is valid"

# PII Protection Utility Functions
def mask_email(email, should_mask=True):
    """Mask email to show only domain: example@domain.com -> @domain.com"""
    if not email or not should_mask:
        return email
    
    if '@' in email:
        domain = email.split('@')[1]
        return f"@{domain}"
    return email

def mask_phone(phone, should_mask=True):
    """Mask phone to show only last 4 digits: (555) 123-4567 -> ***-4567"""
    if not phone or not should_mask:
        return phone
    
    # Remove all non-digits
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) >= 4:
        return f"***-{digits[-4:]}"
    return "***-****"

def mask_name(first_name, last_name=None, should_mask=True):
    """Mask name to show only first name + last initial: John Smith -> John S."""
    if not should_mask:
        return f"{first_name or ''} {last_name or ''}".strip()
    
    if not first_name:
        return ""
    
    if last_name:
        return f"{first_name} {last_name[0]}."
    return first_name

def mask_address(address, should_mask=True):
    """Mask address to show only city/state: 123 Main St, Springfield, IL -> Springfield, IL"""
    if not address or not should_mask:
        return address
    
    # Try to extract city/state from common address patterns
    parts = address.split(',')
    if len(parts) >= 2:
        # Return last two parts (usually city, state)
        return ', '.join(parts[-2:]).strip()
    
    # If no comma, just return a generic location indicator
    return "Location masked"

def sanitize_input(text, max_length=None, allow_html=False):
    """Sanitize user input to prevent XSS and ensure data integrity"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    if not allow_html:
        text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Strip whitespace
    text = text.strip()
    
    # Enforce max length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_email_format(email):
    """Validate email format with enhanced security checks"""
    if not email:
        return False, "Email is required"
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check for dangerous patterns
    dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    email_lower = email.lower()
    for pattern in dangerous_patterns:
        if pattern in email_lower:
            return False, "Email contains invalid characters"
    
    return True, "Email is valid"

def validate_phone_format(phone):
    """Validate phone number format"""
    if not phone:
        return True, "Phone is optional"  # Phone is optional in most cases
    
    # Remove all non-digits
    digits = ''.join(filter(str.isdigit, phone))
    
    # Check if it's a valid US phone number length
    if len(digits) not in [10, 11]:
        return False, "Phone number must be 10 or 11 digits"
    
    # If 11 digits, first digit should be 1 (US country code)
    if len(digits) == 11 and digits[0] != '1':
        return False, "Invalid country code"
    
    return True, "Phone is valid"

def get_user_pii_settings(user_id):
    """Get PII protection settings for a user"""
    pii_protection = PIIProtection.query.filter_by(user_id=user_id).first()
    if not pii_protection:
        # Create default settings if none exist
        pii_protection = PIIProtection(user_id=user_id)
        db.session.add(pii_protection)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    return pii_protection

def apply_pii_masking(user_data, viewer_id, context="profile"):
    """Apply PII masking based on user's privacy settings"""
    if not user_data:
        return user_data
    
    # Get the data owner's PII settings
    user_id = user_data.get('user_id') or user_data.get('id')
    if not user_id:
        return user_data
    
    pii_settings = get_user_pii_settings(user_id)
    
    # Don't mask data for the user themselves
    if viewer_id == user_id:
        return user_data
    
    # Create a copy to avoid modifying original data
    masked_data = user_data.copy()
    
    # Apply masking based on settings
    if 'email' in masked_data:
        masked_data['email'] = mask_email(masked_data['email'], pii_settings.mask_email)
    
    if 'phone' in masked_data:
        masked_data['phone'] = mask_phone(masked_data['phone'], pii_settings.mask_phone_number)
    
    if 'first_name' in masked_data and 'last_name' in masked_data:
        full_name = mask_name(masked_data['first_name'], masked_data['last_name'], pii_settings.mask_full_name)
        name_parts = full_name.split(' ', 1)
        masked_data['first_name'] = name_parts[0] if name_parts else ''
        masked_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    
    if 'address' in masked_data:
        masked_data['address'] = mask_address(masked_data['address'], pii_settings.mask_address)
    
    # Handle contact name for contractor profiles
    if 'contact_name' in masked_data:
        name_parts = masked_data['contact_name'].split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        masked_data['contact_name'] = mask_name(first_name, last_name, pii_settings.mask_full_name)
    
    return masked_data

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # job_seeker, professional, networking, customer
    email_verified = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=False)  # For networking accounts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New fields for job marketplace
    experience_level = db.Column(db.String(20))  # beginner, intermediate, experienced, professional
    location_preference = db.Column(db.String(255))  # Preferred work location
    star_rating_preference = db.Column(db.Float)  # Minimum rating preference
    id_verification_status = db.Column(db.String(20), default="pending")  # pending, verified, rejected
    id_verification_documents = db.Column(db.Text)  # File paths for ID documents
    
    # Relationships
    professional_profile = db.relationship("ProfessionalProfile", backref="user", uselist=False, cascade="all,delete")
    customer_profile = db.relationship("CustomerProfile", backref="user", uselist=False, cascade="all,delete")
    networking_profile = db.relationship("NetworkingProfile", backref="user", uselist=False, cascade="all,delete")
    job_seeker_profile = db.relationship("JobSeekerProfile", backref="user", uselist=False, cascade="all,delete")

class NetworkingProfile(db.Model):
    """Networking profile - manages business connections and networks (formerly DeveloperProfile)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    business_description = db.Column(db.Text)
    
    # Network management
    referral_code = db.Column(db.String(50), unique=True, nullable=False)  # Unique referral link
    total_network_earnings = db.Column(db.Float, default=0.0)
    platform_commission_collected = db.Column(db.Float, default=0.0)  # 2% we collect
    
    # Job posting capabilities for verified labor categories
    verified_labor_categories = db.Column(db.Text)  # JSON string of verified categories
    can_post_jobs = db.Column(db.Boolean, default=False)
    
    # Payment information for commission payouts
    bank_name = db.Column(db.String(255))
    routing_number = db.Column(db.String(20))
    account_number = db.Column(db.String(50))
    
    # Verification
    business_verified = db.Column(db.Boolean, default=False)
    business_documents = db.Column(db.Text)  # File paths
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DeveloperNetwork(db.Model):
    """Tracks businesses in a developer's network"""
    id = db.Column(db.Integer, primary_key=True)
    developer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, active, inactive
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    invitation_method = db.Column(db.String(50))  # referral_link, business_lookup, contractor_request
    
    # Relationships
    developer = db.relationship("User", foreign_keys=[developer_id], backref="managed_contractors")
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="developer_networks")

class ProfessionalProfile(db.Model):
    """Professional profile - for service providers (formerly ContractorProfile)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    geographic_area = db.Column(db.String(50))  # low country, midlands, upstate
    service_radius = db.Column(db.Integer)  # miles
    billing_plan = db.Column(db.String(50), default="commission_only")
    commission_rate = db.Column(db.Float, default=10.0)
    monthly_subscription = db.Column(db.Float, default=0.0)
    
    # Job posting capabilities for verified labor categories
    verified_labor_categories = db.Column(db.Text)  # JSON string of verified categories
    can_post_jobs = db.Column(db.Boolean, default=False)
    
    # Payment information
    bank_name = db.Column(db.String(255))
    routing_number = db.Column(db.String(20))
    account_number = db.Column(db.String(50))
    
    # Work information
    work_hours = db.Column(db.Text)  # JSON string
    availability = db.Column(db.Text)  # JSON string
    services = db.Column(db.Text)  # JSON string of selected categories
    
    # Licensing
    license_verified = db.Column(db.Boolean, default=False)
    insurance_verified = db.Column(db.Boolean, default=False)
    license_documents = db.Column(db.Text)  # File paths
    insurance_documents = db.Column(db.Text)  # File paths
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    geographic_area = db.Column(db.String(50))  # low country, midlands, upstate
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobSeekerProfile(db.Model):
    """Job seeker profile - for people looking for work, training, and apprenticeships"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    geographic_area = db.Column(db.String(50))  # low country, midlands, upstate
    
    # Job seeking specific fields
    desired_labor_categories = db.Column(db.Text)  # JSON string of categories interested in
    experience_level = db.Column(db.String(20))  # beginner, intermediate, experienced, professional
    preferred_locations = db.Column(db.Text)  # JSON string of preferred work locations
    availability = db.Column(db.Text)  # JSON string of available times
    resume_file_path = db.Column(db.String(500))  # Path to uploaded resume
    
    # Skills and training
    skills = db.Column(db.Text)  # JSON string of skills
    certifications = db.Column(db.Text)  # JSON string of certifications
    seeking_apprenticeship = db.Column(db.Boolean, default=False)
    seeking_training = db.Column(db.Boolean, default=False)
    seeking_full_time = db.Column(db.Boolean, default=False)
    seeking_part_time = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service_categories = db.Column(db.Text)  # JSON string
    geographic_area = db.Column(db.String(50))
    status = db.Column(db.String(50), default="pending")  # pending, assigned, scheduled, completed, cancelled
    description = db.Column(db.Text)
    customer_name = db.Column(db.String(255))
    customer_contact = db.Column(db.String(255))
    scheduled_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship("User", foreign_keys=[customer_id], backref="customer_requests")
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="contractor_requests")

class ContractorInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    customer_email = db.Column(db.String(120))
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    invoice_number = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    
    # Enhanced pricing breakdown
    labor_cost = db.Column(db.Float, default=0.0)  # Separate labor pricing
    materials_cost = db.Column(db.Float, default=0.0)  # Separate materials pricing
    amount = db.Column(db.Float, nullable=False)  # Subtotal (labor + materials)
    
    # Sales tax calculation
    sales_tax_rate = db.Column(db.Float, default=0.0)  # Tax rate percentage
    sales_tax = db.Column(db.Float, default=0.0)  # Calculated tax amount
    total_amount = db.Column(db.Float, nullable=False)  # Final total including tax
    
    # Commission tracking
    commission_rate = db.Column(db.Float)
    commission_amount = db.Column(db.Float)
    contractor_amount = db.Column(db.Float)
    
    # Status and payment
    status = db.Column(db.String(50), default="draft")  # draft, sent, paid, overdue
    due_date = db.Column(db.Date)
    payment_terms = db.Column(db.String(255))
    payment_plan_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    contractor = db.relationship("User", foreign_keys=[contractor_id])
    customer = db.relationship("User", foreign_keys=[customer_id])
    work_request = db.relationship("WorkRequest", backref="invoices")


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    contact_name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    industry = db.Column(db.String(120))
    website = db.Column(db.String(255))
    notes = db.Column(db.Text)
    # Billing information
    billing_plan = db.Column(db.String(50), default="commission_only")  # commission_only, subscription_plus_commission
    monthly_subscription = db.Column(db.Float, default=0.0)
    commission_rate = db.Column(db.Float, default=10.0)  # Percentage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    contacts = db.relationship("Contact", backref="client", cascade="all,delete")
    campaigns = db.relationship("Campaign", backref="client", cascade="all,delete")
    invoices = db.relationship("Invoice", backref="client", cascade="all,delete")


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    campaign_type = db.Column(db.String(50), default="referral")  # referral, direct_mail, sticker, media, digital
    incentive = db.Column(db.String(255))
    message = db.Column(db.Text)
    budget = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    links = db.relationship("ReferralLink", backref="campaign", cascade="all,delete")


class ReferralLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey("contact.id"), nullable=False)
    code = db.Column(db.String(32), unique=True, index=True, nullable=False)
    url = db.Column(db.String(512), nullable=False)
    # Relationships for template access
    contact = db.relationship("Contact", backref="referral_links")
    clicks = db.relationship("Click", backref="referral", cascade="all,delete")
    leads = db.relationship("Lead", backref="referral", cascade="all,delete")


class Click(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referral_id = db.Column(db.Integer, db.ForeignKey("referral_link.id"))
    ts = db.Column(db.DateTime, default=datetime.utcnow)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referral_id = db.Column(db.Integer, db.ForeignKey("referral_link.id"))
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default="new")  # new, contacted, qualified, converted, lost
    estimated_value = db.Column(db.Float, default=0.0)
    ts = db.Column(db.DateTime, default=datetime.utcnow)


class ProspectiveLead(db.Model):
    """Manually entered leads/prospects not from campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    source = db.Column(db.String(100))  # referral, website, phone, walk-in, etc.
    status = db.Column(db.String(50), default="new")  # new, contacted, quoted, scheduled, won, lost
    estimated_value = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_contact = db.Column(db.DateTime)
    # Relationships
    client = db.relationship("Client", backref="prospective_leads")
    scheduled_work = db.relationship("ScheduledWork", backref="prospect", cascade="all,delete")


class ScheduledWork(db.Model):
    """Track scheduled jobs and appointments"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    prospect_id = db.Column(db.Integer, db.ForeignKey("prospective_lead.id"))
    contact_id = db.Column(db.Integer, db.ForeignKey("contact.id"))  # For existing customers
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    estimated_hours = db.Column(db.Float)
    estimated_value = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    actual_value = db.Column(db.Float, default=0.0)
    commission_charged = db.Column(db.Float, default=0.0)  # Commission amount for this job
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    # Relationships
    client = db.relationship("Client", backref="scheduled_work")
    contact = db.relationship("Contact", backref="scheduled_work")


class Invoice(db.Model):
    """Track monthly invoices for clients"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    billing_period_start = db.Column(db.DateTime, nullable=False)
    billing_period_end = db.Column(db.DateTime, nullable=False)
    
    # Billing breakdown
    subscription_fee = db.Column(db.Float, default=0.0)
    commission_jobs = db.Column(db.Integer, default=0)  # Number of completed jobs
    commission_revenue = db.Column(db.Float, default=0.0)  # Total job revenue
    commission_rate = db.Column(db.Float, default=10.0)  # Commission percentage applied
    commission_total = db.Column(db.Float, default=0.0)  # Total commission charged
    
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="draft")  # draft, sent, paid, overdue
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

# Job Marketplace Models

class JobPosting(db.Model):
    """Job postings created by professionals and networking accounts"""
    id = db.Column(db.Integer, primary_key=True)
    poster_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # professional or networking account
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    labor_category = db.Column(db.String(100), nullable=False)
    
    # Compensation
    pay_type = db.Column(db.String(20), nullable=False)  # hourly, salary, project, commission
    pay_amount = db.Column(db.Float)  # Hourly rate or salary amount
    pay_range_min = db.Column(db.Float)  # For salary ranges
    pay_range_max = db.Column(db.Float)
    
    # Requirements and filtering
    experience_level = db.Column(db.String(20), nullable=False)  # beginner, intermediate, experienced, professional
    location = db.Column(db.String(255), nullable=False)
    star_rating_preference = db.Column(db.Float, default=0.0)  # Minimum rating requirement
    
    # Job details
    job_type = db.Column(db.String(50))  # full_time, part_time, contract, apprenticeship, training
    benefits = db.Column(db.Text)  # JSON string of benefits offered
    requirements = db.Column(db.Text)  # Specific requirements
    
    # Status and management
    status = db.Column(db.String(20), default="active")  # active, paused, filled, expired
    applications_count = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    filled_at = db.Column(db.DateTime)
    
    # Relationships
    poster = db.relationship("User", backref="job_postings")
    matches = db.relationship("JobMatch", backref="job_posting", cascade="all,delete")

class JobMatch(db.Model):
    """Track job seeker applications and professional responses"""
    id = db.Column(db.Integer, primary_key=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"), nullable=False)
    job_seeker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Match status
    status = db.Column(db.String(20), default="matched")  # matched, reviewed, interview, hired, rejected
    job_seeker_interest = db.Column(db.String(20))  # interested, not_interested, pending
    professional_response = db.Column(db.String(20))  # interested, not_interested, pending
    
    # Preview and contact info
    job_seeker_preview_data = db.Column(db.Text)  # Limited PII for professional to review
    professional_preview_data = db.Column(db.Text)  # Limited info for job seeker to review
    
    # DocuSign integration for agreements
    liability_agreement_signed = db.Column(db.Boolean, default=False)
    employment_terms_signed = db.Column(db.Boolean, default=False)
    liability_docusign_envelope_id = db.Column(db.String(255))
    employment_docusign_envelope_id = db.Column(db.String(255))
    
    # Timeline
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    hired_at = db.Column(db.DateTime)
    
    # Relationships
    job_seeker = db.relationship("User", foreign_keys=[job_seeker_id], backref="job_matches_as_seeker")
    professional = db.relationship("User", foreign_keys=[professional_id], backref="job_matches_as_professional")


# Swipe-based Matching System Models
class SwipeAction(db.Model):
    """Track all swipe actions - dating app style matching"""
    id = db.Column(db.Integer, primary_key=True)
    swiper_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # User who swiped
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # User being swiped on
    swipe_type = db.Column(db.String(20), nullable=False)  # 'like', 'pass', 'super_like'
    context_type = db.Column(db.String(30), nullable=False)  # 'job_application', 'contractor_search', 'networking'
    context_id = db.Column(db.Integer)  # Job posting ID or work request ID
    
    # Additional data for decision making
    swipe_reason = db.Column(db.String(100))  # Optional reason for swipe
    preview_data_shown = db.Column(db.Text)  # What info was visible during swipe
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    swiper = db.relationship("User", foreign_keys=[swiper_id], backref="swipes_made")
    target = db.relationship("User", foreign_keys=[target_id], backref="swipes_received")


class SwipeMatch(db.Model):
    """Track mutual matches from swipe system"""
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    context_type = db.Column(db.String(30), nullable=False)  # 'job_application', 'contractor_search'
    context_id = db.Column(db.Integer)  # Related job posting or work request
    
    # Match status
    status = db.Column(db.String(20), default="active")  # active, expired, declined, completed
    user1_last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    user2_last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Communication tracking
    messages_count = db.Column(db.Integer, default=0)
    last_message_at = db.Column(db.DateTime)
    
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Matches expire after 30 days of inactivity
    
    # Relationships
    user1 = db.relationship("User", foreign_keys=[user1_id], backref="matches_as_user1")
    user2 = db.relationship("User", foreign_keys=[user2_id], backref="matches_as_user2")


# Cookie and Terms Agreement Models
class UserConsent(db.Model):
    """Track user consent for cookies, terms, data collection with granular controls"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Null for anonymous users
    session_id = db.Column(db.String(255))  # For tracking before registration
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    
    # Essential consent (required)
    cookies_essential = db.Column(db.Boolean, default=False)
    terms_of_service = db.Column(db.Boolean, default=False)
    privacy_policy = db.Column(db.Boolean, default=False)
    data_collection = db.Column(db.Boolean, default=False)
    safety_verification = db.Column(db.Boolean, default=False)
    
    # Optional marketing and personalization consent
    marketing_communications = db.Column(db.Boolean, default=False)
    personalization = db.Column(db.Boolean, default=False)
    market_research = db.Column(db.Boolean, default=False)
    
    # Optional analytics consent
    cookies_analytics = db.Column(db.Boolean, default=False)
    cookies_marketing = db.Column(db.Boolean, default=False)
    
    # Legacy fields (deprecated but kept for migration)
    data_resale = db.Column(db.Boolean, default=False)  # No longer used
    
    # Consent metadata
    consent_method = db.Column(db.String(50))  # 'popup', 'registration', 'settings'
    consent_version = db.Column(db.String(20), default="2.0")  # Track policy versions
    consent_data = db.Column(db.JSON)  # Store detailed consent preferences
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Cookie consent expiration
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)  # When consent was granted
    
    # Relationship
    user = db.relationship("User", backref="consent_records")


class NetworkEarning(db.Model):
    """Track earnings generated through developer networks with 2% platform commission"""
    id = db.Column(db.Integer, primary_key=True)
    developer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("contractor_invoice.id"), nullable=False)
    
    gross_amount = db.Column(db.Float, nullable=False)  # Total invoice amount
    platform_commission_rate = db.Column(db.Float, default=2.0)  # 2% platform fee
    platform_commission_amount = db.Column(db.Float, nullable=False)  # Our 2%
    developer_net_amount = db.Column(db.Float, nullable=False)  # Amount developer gets
    
    status = db.Column(db.String(20), default="pending")  # pending, paid, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    developer = db.relationship("User", foreign_keys=[developer_id], backref="network_earnings_as_developer")
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="network_earnings_as_contractor")
    invoice = db.relationship("ContractorInvoice", backref="network_earnings")


class Advertisement(db.Model):
    """Manage advertisement spaces on the site"""
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(255), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(50))
    
    ad_position = db.Column(db.String(20), nullable=False)  # left_margin, right_margin
    ad_size = db.Column(db.String(50), nullable=False)  # banner, square, vertical
    ad_content = db.Column(db.Text)  # HTML content or image path
    ad_url = db.Column(db.String(512))  # Click-through URL
    
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    cost_per_day = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(20), default="pending")  # pending, active, paused, expired
    clicks = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)


class UserDataCollection(db.Model):
    """Track user activity and data collection for analytics and marketing"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Null for anonymous users
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Activity tracking
    page_url = db.Column(db.String(512))
    action_type = db.Column(db.String(50))  # page_view, click, form_submit, search, etc.
    action_data = db.Column(db.Text)  # JSON data for the specific action
    
    # Location data (if permitted)
    country = db.Column(db.String(50))
    state = db.Column(db.String(50))
    city = db.Column(db.String(100))
    
    # Consent status
    consent_given = db.Column(db.Boolean, default=False)
    consent_timestamp = db.Column(db.DateTime)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="data_activities")


class ContractorSearchRequest(db.Model):
    """Track contractor search requests from developer networks"""
    id = db.Column(db.Integer, primary_key=True)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_developer_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Can be null for random assignment
    assigned_developer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    
    request_message = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected, expired
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="search_requests")
    requested_developer = db.relationship("User", foreign_keys=[requested_developer_id], backref="received_requests")
    assigned_developer = db.relationship("User", foreign_keys=[assigned_developer_id], backref="assigned_requests")


class UserRating(db.Model):
    """5-star rating system for all account types"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Rater and ratee
    rater_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # Who gave the rating
    ratee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # Who received the rating
    
    # Rating details
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)  # Optional review comment
    
    # Context
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))  # Associated job
    transaction_type = db.Column(db.String(50))  # contractor_service, networking_coordination, customer_experience
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rater = db.relationship("User", foreign_keys=[rater_id], backref="ratings_given")
    ratee = db.relationship("User", foreign_keys=[ratee_id], backref="ratings_received")
    work_request = db.relationship("WorkRequest", backref="ratings")


class AdvertisementCampaign(db.Model):
    """Advertisement campaigns created by contractors"""
    id = db.Column(db.Integer, primary_key=True)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    advertiser_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Connected advertiser
    
    # Campaign details
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False)  # physical, virtual, mixed
    description = db.Column(db.Text)
    target_audience = db.Column(db.Text)
    budget = db.Column(db.Float, default=0.0)
    
    # Location targeting
    geographic_areas = db.Column(db.Text)  # JSON string of areas
    service_categories = db.Column(db.Text)  # JSON string of categories
    
    # Campaign status
    status = db.Column(db.String(20), default="pending")  # pending, active, paused, completed, cancelled
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # Performance tracking
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    leads_generated = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="advertisement_campaigns")
    advertiser = db.relationship("User", foreign_keys=[advertiser_id], backref="managed_ad_campaigns")


class NetworkingAccountProfile(db.Model):
    """Networking account profile (renamed from DeveloperProfile)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    business_description = db.Column(db.Text)
    
    # Network management
    referral_code = db.Column(db.String(50), unique=True, nullable=False)  # Unique referral link
    total_network_earnings = db.Column(db.Float, default=0.0)
    platform_commission_collected = db.Column(db.Float, default=0.0)  # 2% we collect
    
    # Labor sourcing commission (5% for networking accounts)
    labor_sourcing_commission_rate = db.Column(db.Float, default=5.0)
    
    # Payment information for commission payouts
    bank_name = db.Column(db.String(255))
    routing_number = db.Column(db.String(20))
    account_number = db.Column(db.String(50))
    
    # Verification
    business_verified = db.Column(db.Boolean, default=False)
    business_documents = db.Column(db.Text)  # File paths
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Comprehensive Data Collection Models ---

class CommunicationLog(db.Model):
    """Track all communications between users"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Communication details
    communication_type = db.Column(db.String(50), nullable=False)  # email, message, call, meeting
    subject = db.Column(db.String(255))
    content = db.Column(db.Text)
    content_length = db.Column(db.Integer)
    
    # Platform context
    platform_source = db.Column(db.String(50))  # dashboard_message, email_system, external
    related_job_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"))
    related_work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    related_invoice_id = db.Column(db.Integer, db.ForeignKey("contractor_invoice.id"))
    
    # Response tracking
    response_time_minutes = db.Column(db.Float)  # Time to first response
    sentiment_score = db.Column(db.Float)  # AI-analyzed sentiment (-1 to 1)
    
    # Technical metadata
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    device_type = db.Column(db.String(50))  # desktop, mobile, tablet
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    sender = db.relationship("User", foreign_keys=[sender_id], backref="communications_sent")
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref="communications_received")

class TransactionAnalytics(db.Model):
    """Track all financial transactions and patterns"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # invoice_payment, subscription, commission, refund
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    payment_method = db.Column(db.String(50))  # credit_card, bank_transfer, paypal, etc.
    
    # Business context
    related_invoice_id = db.Column(db.Integer, db.ForeignKey("contractor_invoice.id"))
    related_job_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"))
    labor_category = db.Column(db.String(100))
    professional_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    
    # Platform metrics
    platform_commission = db.Column(db.Float, default=0.0)
    professional_earnings = db.Column(db.Float, default=0.0)
    networking_commission = db.Column(db.Float, default=0.0)
    
    # Geographic data
    transaction_location = db.Column(db.String(255))
    billing_zip_code = db.Column(db.String(20))
    service_zip_code = db.Column(db.String(20))
    
    # Timing analysis
    time_from_job_post_to_hire = db.Column(db.Integer)  # Days
    time_from_completion_to_payment = db.Column(db.Integer)  # Days
    
    # Status tracking
    status = db.Column(db.String(50), default="pending")  # pending, completed, failed, disputed, refunded
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="transactions")
    professional = db.relationship("User", foreign_keys=[professional_id], backref="professional_transactions")
    customer = db.relationship("User", foreign_keys=[customer_id], backref="customer_transactions")

class DemographicProfile(db.Model):
    """Comprehensive demographic and behavioral data"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    
    # Basic demographics
    age_range = db.Column(db.String(20))  # 18-24, 25-34, 35-44, 45-54, 55-64, 65+
    gender = db.Column(db.String(20))
    education_level = db.Column(db.String(50))
    income_range = db.Column(db.String(30))
    employment_status = db.Column(db.String(50))
    
    # Geographic details
    primary_location = db.Column(db.String(255))
    work_radius_miles = db.Column(db.Integer)
    willing_to_relocate = db.Column(db.Boolean, default=False)
    transportation_method = db.Column(db.String(50))
    
    # Professional background
    years_experience = db.Column(db.Integer)
    previous_industries = db.Column(db.Text)  # JSON array
    certifications = db.Column(db.Text)  # JSON array
    skill_level_self_assessment = db.Column(db.Integer)  # 1-10 scale
    
    # Platform behavior
    preferred_contact_method = db.Column(db.String(50))
    active_hours = db.Column(db.Text)  # JSON: preferred working hours
    response_time_preference = db.Column(db.String(50))  # immediate, same_day, next_day, flexible
    
    # Family and lifestyle
    household_size = db.Column(db.Integer)
    dependents = db.Column(db.Integer)
    work_life_balance_priority = db.Column(db.Integer)  # 1-10 scale
    
    # Technology adoption
    device_preferences = db.Column(db.Text)  # JSON: mobile, desktop, tablet usage
    social_media_presence = db.Column(db.Text)  # JSON: platforms used
    tech_comfort_level = db.Column(db.Integer)  # 1-10 scale
    
    # Consent and privacy
    data_sharing_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    analytics_consent = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="demographic_profile")

class GeographicAnalytics(db.Model):
    """Geographic performance and market analysis"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Location identifiers
    zip_code = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100))
    county = db.Column(db.String(100))
    state = db.Column(db.String(50))
    region = db.Column(db.String(50))  # low_country, midlands, upstate, etc.
    
    # Market metrics
    total_users = db.Column(db.Integer, default=0)
    job_seekers_count = db.Column(db.Integer, default=0)
    professionals_count = db.Column(db.Integer, default=0)
    customers_count = db.Column(db.Integer, default=0)
    networking_accounts_count = db.Column(db.Integer, default=0)
    
    # Economic indicators
    average_job_value = db.Column(db.Float, default=0.0)
    total_transaction_volume = db.Column(db.Float, default=0.0)
    platform_revenue = db.Column(db.Float, default=0.0)
    job_completion_rate = db.Column(db.Float, default=0.0)  # Percentage
    
    # Labor market data
    most_popular_labor_categories = db.Column(db.Text)  # JSON: {category: count}
    average_wages_by_category = db.Column(db.Text)  # JSON: {category: avg_wage}
    job_posting_frequency = db.Column(db.Float, default=0.0)  # Jobs per month
    competition_density = db.Column(db.Float, default=0.0)  # Professionals per job
    
    # Seasonal patterns
    seasonal_demand_patterns = db.Column(db.Text)  # JSON: monthly demand data
    peak_activity_months = db.Column(db.Text)  # JSON: array of months
    
    # Market maturity
    market_penetration_rate = db.Column(db.Float, default=0.0)  # % of local market
    growth_rate_monthly = db.Column(db.Float, default=0.0)
    churn_rate = db.Column(db.Float, default=0.0)
    
    # Quality metrics
    average_rating_by_category = db.Column(db.Text)  # JSON: {category: avg_rating}
    dispute_rate = db.Column(db.Float, default=0.0)
    customer_satisfaction_score = db.Column(db.Float, default=0.0)
    
    # Last calculated
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    data_period_start = db.Column(db.DateTime)
    data_period_end = db.Column(db.DateTime)

class JobMarketAnalytics(db.Model):
    """Job acceptance, rejection, and market behavior analysis"""
    id = db.Column(db.Integer, primary_key=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"), nullable=False)
    
    # Job performance metrics
    total_applications = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    total_saves = db.Column(db.Integer, default=0)
    click_through_rate = db.Column(db.Float, default=0.0)
    
    # Acceptance patterns
    applications_accepted = db.Column(db.Integer, default=0)
    applications_rejected = db.Column(db.Integer, default=0)
    applications_ignored = db.Column(db.Integer, default=0)
    average_response_time_hours = db.Column(db.Float, default=0.0)
    
    # Demographic breakdown of applicants
    applicant_age_distribution = db.Column(db.Text)  # JSON: {age_range: count}
    applicant_experience_distribution = db.Column(db.Text)  # JSON: {experience_level: count}
    applicant_location_distribution = db.Column(db.Text)  # JSON: {location: count}
    applicant_education_distribution = db.Column(db.Text)  # JSON: {education: count}
    
    # Rejection analysis
    rejection_reasons = db.Column(db.Text)  # JSON: {reason: count}
    qualification_gaps = db.Column(db.Text)  # JSON: missing skills/requirements
    salary_expectation_mismatches = db.Column(db.Integer, default=0)
    location_constraint_rejections = db.Column(db.Integer, default=0)
    
    # Success metrics
    hired_applicant_profile = db.Column(db.Text)  # JSON: profile of successful hire
    time_to_hire_days = db.Column(db.Integer)
    retention_rate_30_days = db.Column(db.Float, default=0.0)
    retention_rate_90_days = db.Column(db.Float, default=0.0)
    
    # Market competitiveness
    similar_jobs_in_area = db.Column(db.Integer, default=0)
    salary_competitiveness_score = db.Column(db.Float, default=0.0)  # 1-10 scale
    requirement_strictness_score = db.Column(db.Float, default=0.0)  # 1-10 scale
    
    # Performance tracking
    job_completion_status = db.Column(db.String(50))  # hired, expired, cancelled, filled
    final_hire_date = db.Column(db.DateTime)
    performance_rating = db.Column(db.Float)  # Rating of hired worker
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job_posting = db.relationship("JobPosting", backref="analytics")

class AdvertisementAnalytics(db.Model):
    """Advertisement performance and user responsiveness tracking"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("advertisement_campaign.id"))
    
    # Ad performance
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)  # Jobs completed from ad
    click_through_rate = db.Column(db.Float, default=0.0)
    conversion_rate = db.Column(db.Float, default=0.0)
    cost_per_click = db.Column(db.Float, default=0.0)
    cost_per_conversion = db.Column(db.Float, default=0.0)
    
    # Audience analysis
    demographics_reached = db.Column(db.Text)  # JSON: demographic breakdown
    geographic_reach = db.Column(db.Text)  # JSON: location data
    device_breakdown = db.Column(db.Text)  # JSON: mobile/desktop/tablet
    time_of_day_performance = db.Column(db.Text)  # JSON: hour-by-hour performance
    day_of_week_performance = db.Column(db.Text)  # JSON: daily performance
    
    # User engagement
    average_time_on_ad = db.Column(db.Float, default=0.0)  # Seconds
    bounce_rate = db.Column(db.Float, default=0.0)
    pages_per_session = db.Column(db.Float, default=0.0)
    return_visitor_rate = db.Column(db.Float, default=0.0)
    
    # Campaign effectiveness
    brand_awareness_lift = db.Column(db.Float, default=0.0)
    consideration_lift = db.Column(db.Float, default=0.0)
    intent_to_hire_lift = db.Column(db.Float, default=0.0)
    
    # ROI metrics
    revenue_generated = db.Column(db.Float, default=0.0)
    return_on_ad_spend = db.Column(db.Float, default=0.0)
    customer_acquisition_cost = db.Column(db.Float, default=0.0)
    customer_lifetime_value = db.Column(db.Float, default=0.0)
    
    # A/B testing data
    variant_id = db.Column(db.String(50))
    test_group = db.Column(db.String(50))
    statistical_significance = db.Column(db.Float, default=0.0)
    
    # Reporting period
    date = db.Column(db.Date, nullable=False)
    reporting_period = db.Column(db.String(20))  # daily, weekly, monthly
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship("AdvertisementCampaign", backref="analytics")

class RatingDemographics(db.Model):
    """Analysis of rating patterns by demographics and behavior"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Demographic identifiers
    age_range = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    location = db.Column(db.String(255))
    education_level = db.Column(db.String(50))
    account_type = db.Column(db.String(20))
    experience_level = db.Column(db.String(20))
    
    # Rating behavior patterns
    average_rating_given = db.Column(db.Float, default=0.0)
    average_rating_received = db.Column(db.Float, default=0.0)
    total_ratings_given = db.Column(db.Integer, default=0)
    total_ratings_received = db.Column(db.Integer, default=0)
    rating_frequency = db.Column(db.Float, default=0.0)  # Ratings per transaction
    
    # Rating distribution
    five_star_given_percentage = db.Column(db.Float, default=0.0)
    four_star_given_percentage = db.Column(db.Float, default=0.0)
    three_star_given_percentage = db.Column(db.Float, default=0.0)
    two_star_given_percentage = db.Column(db.Float, default=0.0)
    one_star_given_percentage = db.Column(db.Float, default=0.0)
    
    # Behavioral insights
    tends_to_rate_high = db.Column(db.Boolean, default=False)
    tends_to_rate_low = db.Column(db.Boolean, default=False)
    detailed_reviewer = db.Column(db.Boolean, default=False)  # Leaves detailed comments
    quick_rater = db.Column(db.Boolean, default=False)  # Rates quickly after completion
    
    # Sentiment analysis
    positive_sentiment_percentage = db.Column(db.Float, default=0.0)
    negative_sentiment_percentage = db.Column(db.Float, default=0.0)
    neutral_sentiment_percentage = db.Column(db.Float, default=0.0)
    
    # Industry-specific patterns
    labor_category = db.Column(db.String(100))
    category_specific_avg_rating = db.Column(db.Float, default=0.0)
    category_rating_count = db.Column(db.Integer, default=0)
    
    # Time-based patterns
    weekday_rating_pattern = db.Column(db.Text)  # JSON: day-of-week patterns
    seasonal_rating_pattern = db.Column(db.Text)  # JSON: monthly patterns
    response_time_to_rating = db.Column(db.Float, default=0.0)  # Hours after job completion
    
    # Calculated metrics
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    data_period_start = db.Column(db.DateTime)
    data_period_end = db.Column(db.DateTime)
    sample_size = db.Column(db.Integer, default=0)

class PlatformUsageStatistics(db.Model):
    """Comprehensive platform usage and engagement statistics"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Time period
    date = db.Column(db.Date, nullable=False)
    period_type = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    
    # User engagement
    total_active_users = db.Column(db.Integer, default=0)
    new_user_registrations = db.Column(db.Integer, default=0)
    returning_users = db.Column(db.Integer, default=0)
    user_churn_count = db.Column(db.Integer, default=0)
    average_session_duration = db.Column(db.Float, default=0.0)  # Minutes
    pages_per_session = db.Column(db.Float, default=0.0)
    
    # Feature usage
    job_postings_created = db.Column(db.Integer, default=0)
    job_applications_submitted = db.Column(db.Integer, default=0)
    matches_made = db.Column(db.Integer, default=0)
    hires_completed = db.Column(db.Integer, default=0)
    ratings_submitted = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    
    # Financial metrics
    total_transaction_volume = db.Column(db.Float, default=0.0)
    platform_revenue = db.Column(db.Float, default=0.0)
    average_transaction_value = db.Column(db.Float, default=0.0)
    subscription_revenue = db.Column(db.Float, default=0.0)
    commission_revenue = db.Column(db.Float, default=0.0)
    
    # Conversion funnel
    profile_views = db.Column(db.Integer, default=0)
    contact_initiations = db.Column(db.Integer, default=0)
    quote_requests = db.Column(db.Integer, default=0)
    bookings_made = db.Column(db.Integer, default=0)
    jobs_completed = db.Column(db.Integer, default=0)
    
    # Market dynamics
    supply_demand_ratio = db.Column(db.Float, default=0.0)  # Professionals per job
    time_to_match_average = db.Column(db.Float, default=0.0)  # Hours
    completion_rate = db.Column(db.Float, default=0.0)  # Percentage
    cancellation_rate = db.Column(db.Float, default=0.0)  # Percentage
    
    # Device and platform analytics
    mobile_usage_percentage = db.Column(db.Float, default=0.0)
    desktop_usage_percentage = db.Column(db.Float, default=0.0)
    tablet_usage_percentage = db.Column(db.Float, default=0.0)
    top_referral_sources = db.Column(db.Text)  # JSON: source breakdown
    
    # Geographic distribution
    top_cities_by_usage = db.Column(db.Text)  # JSON: city activity
    geographic_growth_rate = db.Column(db.Float, default=0.0)
    new_market_penetration = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- Messaging and Communication Models ---

class Message(db.Model):
    """Comprehensive messaging system with TOS violation detection"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Message content
    subject = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default="general")  # general, job_inquiry, network_invite, contract
    
    # Related entities
    related_job_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"))
    related_work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    related_invoice_id = db.Column(db.Integer, db.ForeignKey("contractor_invoice.id"))
    related_network_invitation_id = db.Column(db.Integer, db.ForeignKey("network_invitation.id"))
    
    # TOS and content monitoring
    contains_pii_flag = db.Column(db.Boolean, default=False)
    contains_contact_info = db.Column(db.Boolean, default=False)
    contains_external_payment = db.Column(db.Boolean, default=False)
    tos_violation_score = db.Column(db.Float, default=0.0)  # 0-1 scale
    flagged_keywords = db.Column(db.Text)  # JSON array of flagged terms
    auto_moderation_action = db.Column(db.String(50))  # none, warning, blocked, review_required
    
    # Message status
    status = db.Column(db.String(20), default="sent")  # sent, delivered, read, archived, deleted
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    is_deleted_by_sender = db.Column(db.Boolean, default=False)
    is_deleted_by_recipient = db.Column(db.Boolean, default=False)
    
    # Admin moderation
    requires_admin_review = db.Column(db.Boolean, default=False)
    admin_approved = db.Column(db.Boolean, default=True)
    admin_notes = db.Column(db.Text)
    moderated_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    moderated_at = db.Column(db.DateTime)
    
    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    sender = db.relationship("User", foreign_keys=[sender_id], backref="messages_sent")
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref="messages_received")
    moderator = db.relationship("User", foreign_keys=[moderated_by])
    job_posting = db.relationship("JobPosting", backref="related_messages")
    work_request = db.relationship("WorkRequest", backref="related_messages")
    invoice = db.relationship("ContractorInvoice", backref="related_messages")

class MessageThread(db.Model):
    """Group related messages into conversation threads"""
    id = db.Column(db.Integer, primary_key=True)
    participant_1_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    participant_2_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Thread metadata
    subject = db.Column(db.String(255))
    thread_type = db.Column(db.String(50), default="general")  # general, job_related, network_business
    related_entity_type = db.Column(db.String(50))  # job_posting, work_request, network_invitation
    related_entity_id = db.Column(db.Integer)
    
    # Status and activity
    is_active = db.Column(db.Boolean, default=True)
    last_message_id = db.Column(db.Integer, db.ForeignKey("message.id"))
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    message_count = db.Column(db.Integer, default=0)
    
    # Participant settings
    participant_1_archived = db.Column(db.Boolean, default=False)
    participant_2_archived = db.Column(db.Boolean, default=False)
    participant_1_muted = db.Column(db.Boolean, default=False)
    participant_2_muted = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    participant_1 = db.relationship("User", foreign_keys=[participant_1_id])
    participant_2 = db.relationship("User", foreign_keys=[participant_2_id])
    last_message = db.relationship("Message", foreign_keys=[last_message_id])
    messages = db.relationship("Message", 
                              primaryjoin="or_(Message.sender_id==MessageThread.participant_1_id, Message.sender_id==MessageThread.participant_2_id)",
                              foreign_keys="Message.sender_id",
                              overlaps="messages_sent")

# --- Network System Models ---

class NetworkInvitation(db.Model):
    """Network invitation system for networking accounts"""
    id = db.Column(db.Integer, primary_key=True)
    network_owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Invitation details
    invitation_type = db.Column(db.String(50), nullable=False)  # manual, automatic_match
    invitation_message = db.Column(db.Text)
    
    # Network terms
    network_name = db.Column(db.String(255))
    commission_percentage = db.Column(db.Float, default=0.0)  # 0-5% max
    subscription_fee = db.Column(db.Float, default=0.0)
    payment_structure = db.Column(db.String(50), default="commission")  # commission, subscription, hybrid
    
    # Contract and payment requirements
    contract_required = db.Column(db.Boolean, default=True)
    docusign_envelope_id = db.Column(db.String(255))
    contract_signed = db.Column(db.Boolean, default=False)
    contract_signed_at = db.Column(db.DateTime)
    
    payment_required = db.Column(db.Boolean, default=False)
    payment_amount = db.Column(db.Float, default=0.0)
    payment_completed = db.Column(db.Boolean, default=False)
    payment_completed_at = db.Column(db.DateTime)
    
    # Invitation status
    status = db.Column(db.String(20), default="pending")  # pending, accepted, declined, expired, cancelled
    response_message = db.Column(db.Text)
    
    # Automatic matching criteria (for automatic invitations)
    location_criteria = db.Column(db.Text)  # JSON: location preferences
    service_criteria = db.Column(db.Text)  # JSON: required services
    experience_criteria = db.Column(db.String(50))  # beginner, intermediate, experienced, professional
    rating_threshold = db.Column(db.Float, default=0.0)
    
    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Default 30 days
    responded_at = db.Column(db.DateTime)
    
    # Relationships
    network_owner = db.relationship("User", foreign_keys=[network_owner_id], backref="network_invitations_sent")
    invitee = db.relationship("User", foreign_keys=[invitee_id], backref="network_invitations_received")

class NetworkMembership(db.Model):
    """Track active network memberships and relationships"""
    id = db.Column(db.Integer, primary_key=True)
    network_owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Membership details
    network_name = db.Column(db.String(255))
    member_role = db.Column(db.String(50), default="member")  # member, senior_member, coordinator
    
    # Financial terms
    commission_percentage = db.Column(db.Float, default=0.0)
    subscription_fee = db.Column(db.Float, default=0.0)
    payment_structure = db.Column(db.String(50), default="commission")
    
    # Contract information
    contract_envelope_id = db.Column(db.String(255))
    contract_active = db.Column(db.Boolean, default=True)
    contract_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    contract_end_date = db.Column(db.DateTime)
    
    # Performance tracking
    jobs_referred = db.Column(db.Integer, default=0)
    total_commission_earned = db.Column(db.Float, default=0.0)
    total_subscription_paid = db.Column(db.Float, default=0.0)
    last_referral_date = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(20), default="active")  # active, suspended, terminated, expired
    suspension_reason = db.Column(db.Text)
    
    # Member preferences
    auto_referral_enabled = db.Column(db.Boolean, default=True)
    notification_preferences = db.Column(db.Text)  # JSON: notification settings
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    network_owner = db.relationship("User", foreign_keys=[network_owner_id], backref="network_members")
    member = db.relationship("User", foreign_keys=[member_id], backref="network_memberships")

class NetworkReferral(db.Model):
    """Track referrals made by network members to earn commissions"""
    id = db.Column(db.Integer, primary_key=True)
    network_membership_id = db.Column(db.Integer, db.ForeignKey("network_membership.id"), nullable=False)
    referring_member_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    network_owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Referral details
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    referred_professional_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey("job_posting.id"))
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    
    # Referral outcome
    referral_accepted = db.Column(db.Boolean, default=False)
    job_hired = db.Column(db.Boolean, default=False)
    job_completed = db.Column(db.Boolean, default=False)
    
    # Financial tracking
    job_value = db.Column(db.Float, default=0.0)
    network_owner_commission = db.Column(db.Float, default=0.0)  # 5% of job value
    platform_commission = db.Column(db.Float, default=0.0)
    professional_earnings = db.Column(db.Float, default=0.0)
    
    # Commission distribution
    commission_rate_applied = db.Column(db.Float, default=0.05)  # 5% max
    commission_paid_to_owner = db.Column(db.Boolean, default=False)
    commission_paid_at = db.Column(db.DateTime)
    
    # Tracking and verification
    referral_method = db.Column(db.String(50))  # direct_invite, search_result, auto_match
    verification_required = db.Column(db.Boolean, default=True)
    verified_by_admin = db.Column(db.Boolean, default=False)
    admin_verification_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    network_membership = db.relationship("NetworkMembership", backref="referrals")
    referring_member = db.relationship("User", foreign_keys=[referring_member_id])
    network_owner = db.relationship("User", foreign_keys=[network_owner_id])
    customer = db.relationship("User", foreign_keys=[customer_id])
    referred_professional = db.relationship("User", foreign_keys=[referred_professional_id])
    job_posting = db.relationship("JobPosting", backref="network_referrals")
    work_request = db.relationship("WorkRequest", backref="network_referrals")

class CustomerSearchRequest(db.Model):
    """Track networking account searches for customers needing work"""
    id = db.Column(db.Integer, primary_key=True)
    networking_account_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Search criteria
    location_radius = db.Column(db.Integer, default=25)  # Miles
    target_location = db.Column(db.String(255))
    service_categories = db.Column(db.Text)  # JSON: array of labor categories
    budget_range_min = db.Column(db.Float, default=0.0)
    budget_range_max = db.Column(db.Float, default=10000.0)
    
    # Timing preferences
    job_timing = db.Column(db.String(50))  # immediate, this_week, this_month, flexible
    recurring_search = db.Column(db.Boolean, default=False)
    search_frequency = db.Column(db.String(20))  # daily, weekly, monthly
    
    # Search performance
    total_searches_run = db.Column(db.Integer, default=0)
    customers_found = db.Column(db.Integer, default=0)
    referrals_made = db.Column(db.Integer, default=0)
    successful_hires = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_search_run = db.Column(db.DateTime)
    next_search_scheduled = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    networking_account = db.relationship("User", backref="customer_search_requests")


# === ENHANCED MULTIMEDIA MARKETING CAMPAIGN SYSTEM ===

class MarketingCampaign(db.Model):
    """Advanced multimedia marketing campaign management"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    campaign_manager_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Platform account manager
    
    # Campaign Identity
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_description = db.Column(db.Text)
    campaign_objectives = db.Column(db.Text)  # JSON: primary, secondary objectives
    brand_guidelines = db.Column(db.Text)  # JSON: colors, fonts, messaging guidelines
    
    # Campaign Type and Strategy
    campaign_type = db.Column(db.String(50), nullable=False)  # multimedia, digital_only, traditional_only, integrated
    marketing_strategy = db.Column(db.String(50))  # awareness, lead_generation, conversion, retention
    target_market_segment = db.Column(db.Text)  # JSON: detailed demographics
    competitor_analysis = db.Column(db.Text)  # JSON: competitive landscape
    
    # Budget and Pricing
    total_budget = db.Column(db.Float, nullable=False)
    platform_service_fee = db.Column(db.Float, default=0.0)  # Our fee for campaign management
    media_buy_budget = db.Column(db.Float, default=0.0)  # Advertising spend
    creative_production_budget = db.Column(db.Float, default=0.0)  # Content creation
    technology_budget = db.Column(db.Float, default=0.0)  # Tools, software, automation
    
    # Timeline
    campaign_start_date = db.Column(db.DateTime, nullable=False)
    campaign_end_date = db.Column(db.DateTime, nullable=False)
    planning_phase_start = db.Column(db.DateTime)
    creative_development_start = db.Column(db.DateTime)
    launch_date = db.Column(db.DateTime)
    
    # Geographic and Demographic Targeting
    geographic_targeting = db.Column(db.Text)  # JSON: cities, states, zip codes, radius
    demographic_targeting = db.Column(db.Text)  # JSON: age, income, education, interests
    psychographic_targeting = db.Column(db.Text)  # JSON: lifestyle, values, behaviors
    custom_audience_segments = db.Column(db.Text)  # JSON: lookalike, retargeting lists
    
    # Platform Integration
    integrated_channels = db.Column(db.Text)  # JSON: social, search, email, traditional
    cross_platform_messaging = db.Column(db.Text)  # JSON: consistent messaging across channels
    attribution_model = db.Column(db.String(50))  # first_touch, last_touch, multi_touch
    
    # Status and Performance
    campaign_status = db.Column(db.String(30), default="planning")  # planning, creative_development, pending_approval, active, paused, completed, cancelled
    approval_status = db.Column(db.String(30), default="pending")  # pending, approved, changes_requested, rejected
    performance_score = db.Column(db.Float, default=0.0)  # Overall campaign effectiveness score
    
    # Advanced Features
    ai_optimization_enabled = db.Column(db.Boolean, default=False)
    real_time_bidding_enabled = db.Column(db.Boolean, default=False)
    multi_variate_testing_enabled = db.Column(db.Boolean, default=False)
    personalization_level = db.Column(db.String(30))  # basic, advanced, ai_powered
    
    # Compliance and Legal
    compliance_requirements = db.Column(db.Text)  # JSON: industry regulations, legal requirements
    privacy_compliance = db.Column(db.Text)  # JSON: GDPR, CCPA, other privacy laws
    content_approval_required = db.Column(db.Boolean, default=True)
    legal_review_status = db.Column(db.String(30))  # pending, approved, flagged
    
    # Client Communication
    client_access_level = db.Column(db.String(30), default="view_only")  # view_only, collaborative, full_access
    reporting_frequency = db.Column(db.String(30), default="weekly")  # daily, weekly, monthly, custom
    communication_preferences = db.Column(db.Text)  # JSON: preferred channels, contacts
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship("User", foreign_keys=[client_id], backref="marketing_campaigns")
    campaign_manager = db.relationship("User", foreign_keys=[campaign_manager_id], backref="managed_marketing_campaigns")


class CampaignChannel(db.Model):
    """Individual marketing channels within a campaign"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("marketing_campaign.id"), nullable=False)
    
    # Channel Details
    channel_type = db.Column(db.String(50), nullable=False)  # social_media, search_ads, display, video, email, traditional, influencer, content_marketing
    platform_name = db.Column(db.String(100))  # Facebook, Google, Instagram, LinkedIn, YouTube, etc.
    channel_objectives = db.Column(db.Text)  # JSON: specific objectives for this channel
    
    # Channel Budget
    allocated_budget = db.Column(db.Float, nullable=False)
    spent_budget = db.Column(db.Float, default=0.0)
    budget_pacing = db.Column(db.String(30), default="even")  # even, front_loaded, back_loaded
    cost_model = db.Column(db.String(30))  # cpc, cpm, cpa, flat_fee, performance_based
    
    # Targeting and Configuration
    audience_targeting = db.Column(db.Text)  # JSON: channel-specific targeting
    creative_specifications = db.Column(db.Text)  # JSON: image sizes, video lengths, text limits
    bidding_strategy = db.Column(db.String(50))  # manual, automatic, target_cpa, maximize_conversions
    quality_score = db.Column(db.Float, default=0.0)
    
    # Performance Metrics
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    click_through_rate = db.Column(db.Float, default=0.0)
    conversion_rate = db.Column(db.Float, default=0.0)
    cost_per_click = db.Column(db.Float, default=0.0)
    cost_per_conversion = db.Column(db.Float, default=0.0)
    return_on_ad_spend = db.Column(db.Float, default=0.0)
    
    # Content and Creative Management
    primary_creative_id = db.Column(db.Integer, db.ForeignKey("creative_asset.id"))
    ab_testing_enabled = db.Column(db.Boolean, default=False)
    dynamic_creative_enabled = db.Column(db.Boolean, default=False)
    
    # Schedule and Timing
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    timezone = db.Column(db.String(50), default="US/Eastern")
    dayparting_enabled = db.Column(db.Boolean, default=False)
    dayparting_schedule = db.Column(db.Text)  # JSON: hour-by-hour schedule
    
    # Status
    channel_status = db.Column(db.String(30), default="inactive")  # inactive, active, paused, completed, error
    last_sync_at = db.Column(db.DateTime)
    error_messages = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship("MarketingCampaign", backref="channels")


class CreativeAsset(db.Model):
    """Marketing creative assets (images, videos, copy, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("marketing_campaign.id"), nullable=False)
    
    # Asset Identity
    asset_name = db.Column(db.String(255), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # image, video, audio, text, html, interactive
    asset_category = db.Column(db.String(50))  # hero, supporting, testimonial, product, logo
    file_format = db.Column(db.String(20))  # jpg, png, mp4, mov, wav, html, etc.
    
    # File Management
    file_path = db.Column(db.String(512))  # Local file path or cloud storage URL
    file_size_bytes = db.Column(db.Integer)
    file_duration_seconds = db.Column(db.Float)  # For video/audio
    file_dimensions = db.Column(db.String(50))  # Width x Height for images/videos
    
    # Content Details
    primary_message = db.Column(db.Text)
    call_to_action = db.Column(db.String(100))
    target_audience = db.Column(db.Text)  # JSON: specific audience for this creative
    emotional_tone = db.Column(db.String(50))  # inspirational, urgent, informative, humorous
    brand_compliance_score = db.Column(db.Float, default=0.0)
    
    # Platform Specifications
    platform_specifications = db.Column(db.Text)  # JSON: platform-specific formats
    responsive_versions = db.Column(db.Text)  # JSON: different sizes/formats
    accessibility_features = db.Column(db.Text)  # JSON: alt text, captions, etc.
    
    # Performance and Testing
    performance_score = db.Column(db.Float, default=0.0)
    ab_test_variant = db.Column(db.String(10))  # A, B, C, etc.
    winning_variant = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)  # How many campaigns used this asset
    
    # Version Control
    version_number = db.Column(db.String(20), default="1.0")
    parent_asset_id = db.Column(db.Integer, db.ForeignKey("creative_asset.id"))  # For versioning
    revision_notes = db.Column(db.Text)
    
    # Approval Workflow
    approval_status = db.Column(db.String(30), default="pending")  # pending, approved, rejected, needs_revision
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    approval_date = db.Column(db.DateTime)
    feedback = db.Column(db.Text)
    
    # Metadata and Tags
    tags = db.Column(db.Text)  # JSON: searchable tags
    description = db.Column(db.Text)
    copyright_info = db.Column(db.Text)
    usage_rights = db.Column(db.Text)  # JSON: usage limitations
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship("MarketingCampaign", backref="creative_assets")
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])
    child_versions = db.relationship("CreativeAsset", remote_side=[id])


class CampaignPerformance(db.Model):
    """Detailed campaign performance tracking and analytics"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("marketing_campaign.id"), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey("campaign_channel.id"))  # Null for overall campaign metrics
    
    # Date and Granularity
    report_date = db.Column(db.Date, nullable=False)
    granularity = db.Column(db.String(20), default="daily")  # hourly, daily, weekly, monthly
    
    # Core Metrics
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    conversion_value = db.Column(db.Float, default=0.0)
    cost = db.Column(db.Float, default=0.0)
    
    # Calculated Metrics
    click_through_rate = db.Column(db.Float, default=0.0)
    conversion_rate = db.Column(db.Float, default=0.0)
    cost_per_click = db.Column(db.Float, default=0.0)
    cost_per_conversion = db.Column(db.Float, default=0.0)
    return_on_ad_spend = db.Column(db.Float, default=0.0)
    
    # Engagement Metrics
    video_views = db.Column(db.Integer, default=0)
    video_completion_rate = db.Column(db.Float, default=0.0)
    engagement_rate = db.Column(db.Float, default=0.0)
    time_spent = db.Column(db.Float, default=0.0)  # Average time in seconds
    bounce_rate = db.Column(db.Float, default=0.0)
    
    # Attribution and Journey
    first_touch_conversions = db.Column(db.Integer, default=0)
    last_touch_conversions = db.Column(db.Integer, default=0)
    assisted_conversions = db.Column(db.Integer, default=0)
    view_through_conversions = db.Column(db.Integer, default=0)
    
    # Audience Insights
    reach = db.Column(db.Integer, default=0)  # Unique users reached
    frequency = db.Column(db.Float, default=0.0)  # Average impressions per user
    new_users = db.Column(db.Integer, default=0)
    returning_users = db.Column(db.Integer, default=0)
    
    # Quality Scores
    relevance_score = db.Column(db.Float, default=0.0)
    quality_score = db.Column(db.Float, default=0.0)
    ad_strength = db.Column(db.String(20))  # poor, average, good, excellent
    
    # Competitive Analysis
    impression_share = db.Column(db.Float, default=0.0)
    search_impression_share = db.Column(db.Float, default=0.0)
    outranking_share = db.Column(db.Float, default=0.0)
    
    # Device and Location Breakdown
    mobile_performance = db.Column(db.Text)  # JSON: mobile-specific metrics
    desktop_performance = db.Column(db.Text)  # JSON: desktop-specific metrics
    geographic_performance = db.Column(db.Text)  # JSON: location-based performance
    
    # Time-based Analysis
    hourly_performance = db.Column(db.Text)  # JSON: hour-by-hour breakdown
    day_of_week_performance = db.Column(db.Text)  # JSON: daily performance patterns
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship("MarketingCampaign", backref="performance_data")
    channel = db.relationship("CampaignChannel", backref="performance_data")


class MarketingAutomation(db.Model):
    """Marketing automation rules and workflows"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("marketing_campaign.id"), nullable=False)
    
    # Automation Details
    automation_name = db.Column(db.String(255), nullable=False)
    automation_type = db.Column(db.String(50), nullable=False)  # bid_optimization, budget_redistribution, creative_rotation, audience_expansion, alert_system
    description = db.Column(db.Text)
    
    # Trigger Conditions
    trigger_conditions = db.Column(db.Text)  # JSON: conditions that activate automation
    trigger_frequency = db.Column(db.String(30))  # real_time, hourly, daily, weekly
    threshold_metrics = db.Column(db.Text)  # JSON: metric thresholds
    
    # Actions
    automated_actions = db.Column(db.Text)  # JSON: actions to take when triggered
    action_parameters = db.Column(db.Text)  # JSON: parameters for actions
    fallback_actions = db.Column(db.Text)  # JSON: backup actions if primary fails
    
    # Machine Learning Integration
    ml_model_enabled = db.Column(db.Boolean, default=False)
    learning_algorithm = db.Column(db.String(50))  # regression, classification, clustering, neural_network
    training_data_period = db.Column(db.Integer, default=30)  # Days of data for training
    prediction_confidence_threshold = db.Column(db.Float, default=0.8)
    
    # Performance and Control
    automation_status = db.Column(db.String(30), default="inactive")  # inactive, active, paused, error
    execution_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    last_execution = db.Column(db.DateTime)
    next_execution = db.Column(db.DateTime)
    
    # Safety Controls
    maximum_budget_change = db.Column(db.Float, default=10.0)  # Maximum % change in budget
    maximum_bid_change = db.Column(db.Float, default=20.0)  # Maximum % change in bids
    approval_required_for_major_changes = db.Column(db.Boolean, default=True)
    emergency_stop_conditions = db.Column(db.Text)  # JSON: conditions to stop automation
    
    # Reporting and Notifications
    notification_settings = db.Column(db.Text)  # JSON: when and how to notify
    performance_impact_tracking = db.Column(db.Text)  # JSON: before/after performance
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship("MarketingCampaign", backref="automations")


class CampaignROIAnalysis(db.Model):
    """Comprehensive ROI and business impact analysis"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("marketing_campaign.id"), nullable=False)
    
    # Analysis Period
    analysis_start_date = db.Column(db.Date, nullable=False)
    analysis_end_date = db.Column(db.Date, nullable=False)
    analysis_type = db.Column(db.String(30))  # campaign_completion, monthly_review, quarterly_assessment
    
    # Investment Breakdown
    total_investment = db.Column(db.Float, nullable=False)
    media_spend = db.Column(db.Float, default=0.0)
    creative_production_cost = db.Column(db.Float, default=0.0)
    platform_management_fee = db.Column(db.Float, default=0.0)
    technology_costs = db.Column(db.Float, default=0.0)
    overhead_allocation = db.Column(db.Float, default=0.0)
    
    # Revenue Attribution
    direct_revenue = db.Column(db.Float, default=0.0)  # Immediate conversions
    assisted_revenue = db.Column(db.Float, default=0.0)  # Multi-touch attribution
    lifetime_value_impact = db.Column(db.Float, default=0.0)  # Long-term customer value
    brand_value_increase = db.Column(db.Float, default=0.0)  # Brand equity improvement
    
    # Performance Metrics
    total_roi = db.Column(db.Float, default=0.0)  # Total return on investment
    incremental_roi = db.Column(db.Float, default=0.0)  # ROI above baseline
    customer_acquisition_cost = db.Column(db.Float, default=0.0)
    customer_lifetime_value = db.Column(db.Float, default=0.0)
    payback_period_days = db.Column(db.Integer)
    
    # Business Impact
    new_customers_acquired = db.Column(db.Integer, default=0)
    existing_customer_retention_impact = db.Column(db.Float, default=0.0)
    market_share_change = db.Column(db.Float, default=0.0)
    brand_awareness_lift = db.Column(db.Float, default=0.0)
    consideration_lift = db.Column(db.Float, default=0.0)
    
    # Channel Performance Comparison
    top_performing_channel = db.Column(db.String(100))
    lowest_performing_channel = db.Column(db.String(100))
    channel_roi_breakdown = db.Column(db.Text)  # JSON: ROI by channel
    channel_efficiency_scores = db.Column(db.Text)  # JSON: efficiency metrics
    
    # Audience Insights
    highest_value_audience_segment = db.Column(db.Text)  # JSON: demographic profile
    audience_segment_roi = db.Column(db.Text)  # JSON: ROI by segment
    geographic_roi_performance = db.Column(db.Text)  # JSON: ROI by location
    
    # Optimization Recommendations
    optimization_opportunities = db.Column(db.Text)  # JSON: identified improvements
    budget_reallocation_recommendations = db.Column(db.Text)  # JSON: suggested changes
    creative_optimization_suggestions = db.Column(db.Text)  # JSON: creative improvements
    estimated_impact_of_recommendations = db.Column(db.Float, default=0.0)
    
    # Competitive Analysis
    competitive_roi_benchmark = db.Column(db.Float, default=0.0)
    industry_average_roi = db.Column(db.Float, default=0.0)
    roi_percentile_ranking = db.Column(db.Float, default=0.0)  # Where this campaign ranks
    
    # Risk Assessment
    roi_volatility = db.Column(db.Float, default=0.0)  # Standard deviation of daily ROI
    downside_risk_assessment = db.Column(db.Float, default=0.0)
    confidence_interval = db.Column(db.Text)  # JSON: statistical confidence intervals
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyst_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Who performed the analysis
    
    # Relationships
    campaign = db.relationship("MarketingCampaign", backref="roi_analyses")
    analyst = db.relationship("User", foreign_keys=[analyst_id])


# === ADVERTISING PROFESSIONALS MARKETPLACE ===

class AdvertisingProfessional(db.Model):
    """Base model for advertising and marketing professionals"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Business Information
    business_name = db.Column(db.String(255), nullable=False)
    business_description = db.Column(db.Text)
    specialization = db.Column(db.String(100), nullable=False)  # web_advertising, physical_media, marketing_management
    experience_years = db.Column(db.Integer, default=0)
    
    # Service Areas
    service_area_cities = db.Column(db.Text)  # JSON: list of cities served
    service_area_radius = db.Column(db.Integer, default=25)  # Miles
    remote_services_available = db.Column(db.Boolean, default=True)
    
    # Credentials and Portfolio
    certifications = db.Column(db.Text)  # JSON: list of certifications
    portfolio_url = db.Column(db.String(512))
    years_in_business = db.Column(db.Integer, default=0)
    team_size = db.Column(db.Integer, default=1)
    
    # Pricing Structure
    base_hourly_rate = db.Column(db.Float, default=0.0)
    project_minimum = db.Column(db.Float, default=0.0)
    rush_fee_percentage = db.Column(db.Float, default=0.0)  # Extra charge for rush jobs
    
    # Availability and Capacity
    current_capacity = db.Column(db.Integer, default=5)  # Max concurrent projects
    average_turnaround_days = db.Column(db.Integer, default=7)
    accepts_rush_orders = db.Column(db.Boolean, default=True)
    minimum_notice_days = db.Column(db.Integer, default=1)
    
    # Platform Integration
    platform_commission_rate = db.Column(db.Float, default=10.0)  # Always 10%
    auto_accept_projects = db.Column(db.Boolean, default=False)
    requires_consultation = db.Column(db.Boolean, default=True)
    
    # Quality Metrics
    average_rating = db.Column(db.Float, default=0.0)
    total_projects = db.Column(db.Integer, default=0)
    completed_projects = db.Column(db.Integer, default=0)
    on_time_delivery_rate = db.Column(db.Float, default=0.0)
    customer_satisfaction_score = db.Column(db.Float, default=0.0)
    
    # Status and Verification
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_documents = db.Column(db.Text)  # JSON: document paths
    background_check_status = db.Column(db.String(30), default="pending")
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="advertising_professional")


class PhysicalMediaProvider(db.Model):
    """Providers of physical advertising materials"""
    id = db.Column(db.Integer, primary_key=True)
    advertising_professional_id = db.Column(db.Integer, db.ForeignKey("advertising_professional.id"), nullable=False)
    
    # Available Products
    offers_stickers = db.Column(db.Boolean, default=False)
    offers_flyers = db.Column(db.Boolean, default=False)
    offers_business_cards = db.Column(db.Boolean, default=False)
    offers_brochures = db.Column(db.Boolean, default=False)
    offers_banners = db.Column(db.Boolean, default=False)
    offers_yard_signs = db.Column(db.Boolean, default=False)
    offers_vehicle_wraps = db.Column(db.Boolean, default=False)
    offers_promotional_items = db.Column(db.Boolean, default=False)
    offers_apparel = db.Column(db.Boolean, default=False)
    offers_custom_products = db.Column(db.Boolean, default=True)
    
    # Pricing Per Unit (in cents to avoid float issues)
    sticker_price_cents = db.Column(db.Integer, default=50)  # $0.50 each
    flyer_price_cents = db.Column(db.Integer, default=25)   # $0.25 each
    business_card_price_cents = db.Column(db.Integer, default=10)  # $0.10 each
    brochure_price_cents = db.Column(db.Integer, default=150)  # $1.50 each
    banner_price_cents = db.Column(db.Integer, default=2500)  # $25.00 each
    yard_sign_price_cents = db.Column(db.Integer, default=800)  # $8.00 each
    vehicle_wrap_price_cents = db.Column(db.Integer, default=150000)  # $1,500.00 each
    promotional_item_price_cents = db.Column(db.Integer, default=300)  # $3.00 each
    apparel_price_cents = db.Column(db.Integer, default=1200)  # $12.00 each
    
    # Minimum Orders
    sticker_minimum_quantity = db.Column(db.Integer, default=100)
    flyer_minimum_quantity = db.Column(db.Integer, default=250)
    business_card_minimum_quantity = db.Column(db.Integer, default=500)
    brochure_minimum_quantity = db.Column(db.Integer, default=100)
    banner_minimum_quantity = db.Column(db.Integer, default=1)
    yard_sign_minimum_quantity = db.Column(db.Integer, default=5)
    vehicle_wrap_minimum_quantity = db.Column(db.Integer, default=1)
    promotional_item_minimum_quantity = db.Column(db.Integer, default=25)
    apparel_minimum_quantity = db.Column(db.Integer, default=12)
    
    # Production Details
    production_capabilities = db.Column(db.Text)  # JSON: detailed capabilities
    equipment_list = db.Column(db.Text)  # JSON: available equipment
    material_options = db.Column(db.Text)  # JSON: available materials
    design_services_included = db.Column(db.Boolean, default=True)
    rush_production_available = db.Column(db.Boolean, default=True)
    rush_fee_percentage = db.Column(db.Float, default=50.0)  # 50% extra for rush
    
    # Delivery and Shipping
    local_delivery_available = db.Column(db.Boolean, default=True)
    local_delivery_fee_cents = db.Column(db.Integer, default=1500)  # $15.00
    shipping_available = db.Column(db.Boolean, default=True)
    free_shipping_minimum_cents = db.Column(db.Integer, default=10000)  # $100.00
    international_shipping = db.Column(db.Boolean, default=False)
    
    # Quality and Guarantees
    quality_guarantee_days = db.Column(db.Integer, default=30)
    sample_policy = db.Column(db.Text)
    return_policy = db.Column(db.Text)
    eco_friendly_options = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    advertising_professional = db.relationship("AdvertisingProfessional", backref="physical_media_services")


class WebAdvertisingProfessional(db.Model):
    """Professionals specializing in web-based advertising"""
    id = db.Column(db.Integer, primary_key=True)
    advertising_professional_id = db.Column(db.Integer, db.ForeignKey("advertising_professional.id"), nullable=False)
    
    # Platform Specializations
    google_ads_certified = db.Column(db.Boolean, default=False)
    facebook_ads_certified = db.Column(db.Boolean, default=False)
    linkedin_ads_certified = db.Column(db.Boolean, default=False)
    microsoft_ads_certified = db.Column(db.Boolean, default=False)
    amazon_ads_certified = db.Column(db.Boolean, default=False)
    youtube_ads_certified = db.Column(db.Boolean, default=False)
    tiktok_ads_certified = db.Column(db.Boolean, default=False)
    pinterest_ads_certified = db.Column(db.Boolean, default=False)
    
    # Service Offerings
    offers_search_ads = db.Column(db.Boolean, default=True)
    offers_display_ads = db.Column(db.Boolean, default=True)
    offers_social_media_ads = db.Column(db.Boolean, default=True)
    offers_video_ads = db.Column(db.Boolean, default=False)
    offers_shopping_ads = db.Column(db.Boolean, default=False)
    offers_retargeting = db.Column(db.Boolean, default=True)
    offers_landing_pages = db.Column(db.Boolean, default=True)
    offers_conversion_tracking = db.Column(db.Boolean, default=True)
    offers_analytics_setup = db.Column(db.Boolean, default=True)
    
    # Campaign Management
    setup_fee_cents = db.Column(db.Integer, default=50000)  # $500.00
    monthly_management_fee_cents = db.Column(db.Integer, default=100000)  # $1,000.00
    management_fee_percentage = db.Column(db.Float, default=15.0)  # 15% of ad spend
    minimum_ad_spend_cents = db.Column(db.Integer, default=100000)  # $1,000.00 minimum
    
    # Expertise Areas
    specializes_in_lead_generation = db.Column(db.Boolean, default=True)
    specializes_in_ecommerce = db.Column(db.Boolean, default=False)
    specializes_in_brand_awareness = db.Column(db.Boolean, default=True)
    specializes_in_local_business = db.Column(db.Boolean, default=True)
    specializes_in_b2b = db.Column(db.Boolean, default=False)
    specializes_in_mobile_apps = db.Column(db.Boolean, default=False)
    
    # Performance Guarantees
    guarantees_roas = db.Column(db.Boolean, default=False)  # Return on ad spend
    guaranteed_roas_percentage = db.Column(db.Float, default=300.0)  # 3:1 ROAS
    guarantees_lead_cost = db.Column(db.Boolean, default=False)
    guaranteed_cost_per_lead_cents = db.Column(db.Integer, default=5000)  # $50.00
    performance_bonus_available = db.Column(db.Boolean, default=False)
    
    # Reporting and Communication
    provides_weekly_reports = db.Column(db.Boolean, default=True)
    provides_monthly_reports = db.Column(db.Boolean, default=True)
    provides_realtime_dashboard = db.Column(db.Boolean, default=True)
    communication_frequency = db.Column(db.String(20), default="weekly")  # daily, weekly, monthly
    preferred_communication_method = db.Column(db.String(20), default="email")  # email, phone, video
    
    # Tools and Software
    tools_used = db.Column(db.Text)  # JSON: list of tools and software
    provides_competitor_analysis = db.Column(db.Boolean, default=True)
    provides_keyword_research = db.Column(db.Boolean, default=True)
    provides_ad_copy_testing = db.Column(db.Boolean, default=True)
    provides_landing_page_optimization = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    advertising_professional = db.relationship("AdvertisingProfessional", backref="web_advertising_services")


class MarketingProfessional(db.Model):
    """Marketing strategy and management professionals"""
    id = db.Column(db.Integer, primary_key=True)
    advertising_professional_id = db.Column(db.Integer, db.ForeignKey("advertising_professional.id"), nullable=False)
    
    # Expertise Areas
    specializes_in_strategy = db.Column(db.Boolean, default=True)
    specializes_in_branding = db.Column(db.Boolean, default=True)
    specializes_in_content_marketing = db.Column(db.Boolean, default=True)
    specializes_in_email_marketing = db.Column(db.Boolean, default=True)
    specializes_in_social_media = db.Column(db.Boolean, default=True)
    specializes_in_seo = db.Column(db.Boolean, default=False)
    specializes_in_pr = db.Column(db.Boolean, default=False)
    specializes_in_events = db.Column(db.Boolean, default=False)
    specializes_in_influencer_marketing = db.Column(db.Boolean, default=False)
    specializes_in_market_research = db.Column(db.Boolean, default=True)
    
    # Service Packages
    offers_strategy_consultation = db.Column(db.Boolean, default=True)
    strategy_consultation_fee_cents = db.Column(db.Integer, default=25000)  # $250.00
    
    offers_campaign_management = db.Column(db.Boolean, default=True)
    campaign_management_fee_cents = db.Column(db.Integer, default=200000)  # $2,000.00/month
    
    offers_content_creation = db.Column(db.Boolean, default=True)
    content_creation_fee_cents = db.Column(db.Integer, default=100000)  # $1,000.00/month
    
    offers_brand_development = db.Column(db.Boolean, default=True)
    brand_development_fee_cents = db.Column(db.Integer, default=500000)  # $5,000.00 project
    
    offers_market_analysis = db.Column(db.Boolean, default=True)
    market_analysis_fee_cents = db.Column(db.Integer, default=150000)  # $1,500.00
    
    # Industry Experience
    experience_healthcare = db.Column(db.Boolean, default=False)
    experience_retail = db.Column(db.Boolean, default=False)
    experience_restaurants = db.Column(db.Boolean, default=False)
    experience_professional_services = db.Column(db.Boolean, default=True)
    experience_real_estate = db.Column(db.Boolean, default=False)
    experience_automotive = db.Column(db.Boolean, default=False)
    experience_technology = db.Column(db.Boolean, default=False)
    experience_manufacturing = db.Column(db.Boolean, default=False)
    experience_nonprofit = db.Column(db.Boolean, default=False)
    
    # Team and Resources
    has_design_team = db.Column(db.Boolean, default=False)
    has_copywriting_team = db.Column(db.Boolean, default=True)
    has_video_production = db.Column(db.Boolean, default=False)
    has_photography = db.Column(db.Boolean, default=False)
    has_web_development = db.Column(db.Boolean, default=False)
    has_data_analytics = db.Column(db.Boolean, default=True)
    
    # Campaign Management
    minimum_campaign_budget_cents = db.Column(db.Integer, default=500000)  # $5,000.00
    typical_campaign_duration_months = db.Column(db.Integer, default=6)
    maximum_concurrent_campaigns = db.Column(db.Integer, default=10)
    requires_retainer = db.Column(db.Boolean, default=True)
    retainer_amount_cents = db.Column(db.Integer, default=300000)  # $3,000.00
    
    # Deliverables and Reporting
    provides_strategy_document = db.Column(db.Boolean, default=True)
    provides_competitive_analysis = db.Column(db.Boolean, default=True)
    provides_monthly_reports = db.Column(db.Boolean, default=True)
    provides_roi_analysis = db.Column(db.Boolean, default=True)
    provides_recommendations = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    advertising_professional = db.relationship("AdvertisingProfessional", backref="marketing_services")


class AdvertisingCampaignRequest(db.Model):
    """Campaign requests that connect clients with advertising professionals"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Campaign Details
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_description = db.Column(db.Text)
    campaign_budget_cents = db.Column(db.Integer, nullable=False)
    campaign_duration_days = db.Column(db.Integer, nullable=False)
    
    # Timeline
    desired_start_date = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    is_rush_order = db.Column(db.Boolean, default=False)
    
    # Selected Professionals and Services
    selected_professionals = db.Column(db.Text)  # JSON: list of professional IDs and services
    physical_media_orders = db.Column(db.Text)  # JSON: quantities and specifications
    web_advertising_requirements = db.Column(db.Text)  # JSON: platform requirements
    marketing_management_scope = db.Column(db.Text)  # JSON: management requirements
    
    # Status and Workflow
    status = db.Column(db.String(30), default="pending")  # pending, approved, in_progress, completed, cancelled
    total_cost_cents = db.Column(db.Integer, default=0)
    platform_commission_cents = db.Column(db.Integer, default=0)  # 10% commission
    
    # Client Approval
    requires_client_approval = db.Column(db.Boolean, default=True)
    client_approved_at = db.Column(db.DateTime)
    client_approval_notes = db.Column(db.Text)
    
    # Payment Tracking
    payment_status = db.Column(db.String(30), default="pending")  # pending, paid, partial, refunded
    payment_due_date = db.Column(db.DateTime)
    payment_completed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship("User", backref="advertising_campaign_requests")


class AdvertisingWorkOrder(db.Model):
    """Individual work orders sent to advertising professionals"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_request_id = db.Column(db.Integer, db.ForeignKey("advertising_campaign_request.id"), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey("advertising_professional.id"), nullable=False)
    
    # Work Details
    work_type = db.Column(db.String(50), nullable=False)  # physical_media, web_advertising, marketing_management
    work_description = db.Column(db.Text)
    deliverables = db.Column(db.Text)  # JSON: specific deliverables
    specifications = db.Column(db.Text)  # JSON: detailed specifications
    
    # Pricing and Payment
    quoted_price_cents = db.Column(db.Integer, nullable=False)
    final_price_cents = db.Column(db.Integer)
    platform_commission_cents = db.Column(db.Integer)  # 10% of final price
    rush_fee_cents = db.Column(db.Integer, default=0)
    
    # Timeline
    estimated_completion_date = db.Column(db.DateTime)
    actual_completion_date = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    
    # Status and Progress
    status = db.Column(db.String(30), default="sent")  # sent, accepted, declined, in_progress, completed, cancelled
    progress_percentage = db.Column(db.Integer, default=0)
    progress_notes = db.Column(db.Text)
    
    # Professional Response
    accepted_at = db.Column(db.DateTime)
    declined_at = db.Column(db.DateTime)
    decline_reason = db.Column(db.Text)
    professional_notes = db.Column(db.Text)
    
    # Quality and Completion
    quality_score = db.Column(db.Float, default=0.0)
    client_satisfaction = db.Column(db.Float, default=0.0)
    delivered_on_time = db.Column(db.Boolean)
    revision_requests = db.Column(db.Integer, default=0)
    
    # File Attachments
    work_files = db.Column(db.Text)  # JSON: list of file paths
    client_feedback_files = db.Column(db.Text)  # JSON: feedback files
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign_request = db.relationship("AdvertisingCampaignRequest", backref="work_orders")
    professional = db.relationship("AdvertisingProfessional", backref="work_orders")


class AdvertisingTransaction(db.Model):
    """Track all advertising-related transactions and commissions"""
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("advertising_work_order.id"), nullable=False)
    
    # Transaction Details
    transaction_type = db.Column(db.String(30), nullable=False)  # payment, commission, refund, bonus
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    
    # Platform Commission (Always 10%)
    platform_commission_cents = db.Column(db.Integer, nullable=False)
    commission_rate = db.Column(db.Float, default=10.0)
    
    # Payment Details
    payment_method = db.Column(db.String(30))  # stripe, paypal, bank_transfer, cash
    payment_processor_id = db.Column(db.String(255))  # External payment ID
    payment_status = db.Column(db.String(30), default="pending")  # pending, completed, failed, refunded
    
    # Parties Involved
    payer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Transaction Metadata
    description = db.Column(db.Text)
    reference_number = db.Column(db.String(50))
    processed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    work_order = db.relationship("AdvertisingWorkOrder", backref="transactions")
    payer = db.relationship("User", foreign_keys=[payer_id], backref="advertising_payments_made")
    payee = db.relationship("User", foreign_keys=[payee_id], backref="advertising_payments_received")


# --- Helpers ---
def base_public_url() -> str:
    # For local demo; set BASE_URL if you expose publicly via a tunnel
    return os.environ.get("BASE_URL", "http://localhost:5000")


def generate_qr_png(data: str, filename: str) -> str:
    if not HAS_QRCODE:
        # Return a placeholder path if QR code library not available
        return os.path.join(QR_DIR, "qr_not_available.txt")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(QR_DIR, filename)
    img.save(path)  # type: ignore
    return path


def generate_unique_referral_code():
    """Generate unique referral code for networking accounts"""
    while True:
        code = shortuuid.uuid()[:8].upper()
        existing = NetworkingProfile.query.filter_by(referral_code=code).first()
        if not existing:
            return code


def assign_random_developer():
    """Assign a random developer for contractor network requests"""
    developers = User.query.filter_by(account_type="developer", approved=True).all()
    if not developers:
        return None
    
    # Simple random assignment - could be enhanced with load balancing
    import random
    return random.choice(developers)


def track_user_activity(user_id, action_type, page_url, action_data=None, session_id=None):
    """Track user activity for analytics and marketing"""
    if not session_id:
        session_id = request.cookies.get('session_id', str(shortuuid.uuid()))
    
    activity = UserDataCollection(
        session_id=session_id,
        user_id=user_id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        page_url=page_url,
        action_type=action_type,
        action_data=action_data,
        consent_given=session.get('data_consent', False),
        consent_timestamp=session.get('consent_timestamp')
    )
    
    db.session.add(activity)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

def track_profile_view(viewer_id, viewed_user_id, view_type="full_profile", source="direct", work_request_id=None):
    """Track profile views for PII protection and audit trail"""
    # Check if the user has exceeded their monthly view limit
    viewer_pii_settings = get_user_pii_settings(viewer_id)
    
    # Reset monthly views if needed
    from datetime import datetime
    now = datetime.utcnow()
    if viewer_pii_settings.last_view_reset.month != now.month:
        viewer_pii_settings.current_month_views = 0
        viewer_pii_settings.last_view_reset = now
    
    # Check view limit (only for non-self views)
    if viewer_id != viewed_user_id:
        if viewer_pii_settings.current_month_views >= viewer_pii_settings.profile_views_allowed_per_month:
            return False, "Monthly profile view limit exceeded"
        
        # Increment view count
        viewer_pii_settings.current_month_views += 1
    
    # Create profile view record
    profile_view = ProfileView(
        viewer_id=viewer_id,
        viewed_user_id=viewed_user_id,
        view_type=view_type,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        source=source,
        work_request_id=work_request_id
    )
    
    db.session.add(profile_view)
    
    # Also track in general activity log
    track_user_activity(
        user_id=viewer_id,
        action_type="profile_view",
        page_url=request.url,
        action_data=f"viewed_user:{viewed_user_id},view_type:{view_type}"
    )
    
    try:
        db.session.commit()
        return True, "Profile view tracked successfully"
    except Exception:
        db.session.rollback()
        return False, "Error tracking profile view"

def track_pii_access(user_id, accessed_user_id, pii_type, context="unknown"):
    """Track access to specific PII data types"""
    track_user_activity(
        user_id=user_id,
        action_type="pii_access",
        page_url=request.url,
        action_data=f"accessed_user:{accessed_user_id},pii_type:{pii_type},context:{context}"
    )

def log_data_export(user_id, export_type, data_range=None):
    """Log data export requests for GDPR compliance"""
    track_user_activity(
        user_id=user_id,
        action_type="data_export",
        page_url=request.url,
        action_data=f"export_type:{export_type},data_range:{data_range}"
    )


# --- Content Filtering and TOS Violation Detection ---

def detect_tos_violations(content):
    """Detect potential TOS violations in message content"""
    violations = {
        'contains_pii_flag': False,
        'contains_contact_info': False,
        'contains_external_payment': False,
        'tos_violation_score': 0.0,
        'flagged_keywords': [],
        'auto_moderation_action': 'none'
    }
    
    content_lower = content.lower()
    
    # PII Detection patterns
    pii_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
        r'\b[A-Z]{2}\d{6,8}\b',  # Driver's license patterns
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
    ]
    
    # Contact info patterns
    contact_patterns = [
        r'\b\w+@\w+\.\w+\b',  # Email addresses
        r'\b(?:call|text|email)\s+me\s+(?:at|on)',  # Direct contact requests
        r'\b(?:my|reach|contact)\s+(?:number|phone|email)',
        r'\b\d{10}\b',  # 10-digit phone numbers
        r'\(\d{3}\)\s*\d{3}-\d{4}',  # Formatted phone numbers
    ]
    
    # External payment/platform keywords
    external_payment_keywords = [
        'venmo', 'paypal', 'cashapp', 'cash app', 'zelle', 'bitcoin', 'crypto',
        'outside platform', 'off platform', 'direct payment', 'cash only',
        'avoid fees', 'no commission', 'skip platform'
    ]
    
    # TOS violation keywords
    tos_violation_keywords = [
        'cut out', 'bypass', 'work around', 'avoid platform', 'direct deal',
        'under table', 'cash under', 'no taxes', 'off books', 'side deal'
    ]
    
    import re
    
    # Check for PII
    for pattern in pii_patterns:
        if re.search(pattern, content):
            violations['contains_pii_flag'] = True
            violations['flagged_keywords'].append('PII_DETECTED')
            violations['tos_violation_score'] += 0.3
    
    # Check for contact info
    for pattern in contact_patterns:
        if re.search(pattern, content):
            violations['contains_contact_info'] = True
            violations['flagged_keywords'].append('CONTACT_INFO')
            violations['tos_violation_score'] += 0.4
    
    # Check for external payment mentions
    for keyword in external_payment_keywords:
        if keyword in content_lower:
            violations['contains_external_payment'] = True
            violations['flagged_keywords'].append(f'EXTERNAL_PAYMENT:{keyword}')
            violations['tos_violation_score'] += 0.5
    
    # Check for TOS violations
    for keyword in tos_violation_keywords:
        if keyword in content_lower:
            violations['flagged_keywords'].append(f'TOS_VIOLATION:{keyword}')
            violations['tos_violation_score'] += 0.7
    
    # Determine auto-moderation action
    if violations['tos_violation_score'] >= 0.8:
        violations['auto_moderation_action'] = 'blocked'
    elif violations['tos_violation_score'] >= 0.5:
        violations['auto_moderation_action'] = 'review_required'
    elif violations['tos_violation_score'] >= 0.3:
        violations['auto_moderation_action'] = 'warning'
    
    return violations

def send_message(sender_id, recipient_id, content, subject=None, message_type="general", 
                related_job_id=None, related_work_request_id=None, related_invoice_id=None):
    """Send a message with TOS violation checking"""
    
    # Detect TOS violations
    violations = detect_tos_violations(content)
    
    # Block message if severe violations detected
    if violations['auto_moderation_action'] == 'blocked':
        return False, "Message blocked due to policy violations"
    
    # Create message
    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        subject=subject,
        content=content,
        message_type=message_type,
        related_job_id=related_job_id,
        related_work_request_id=related_work_request_id,
        related_invoice_id=related_invoice_id,
        contains_pii_flag=violations['contains_pii_flag'],
        contains_contact_info=violations['contains_contact_info'],
        contains_external_payment=violations['contains_external_payment'],
        tos_violation_score=violations['tos_violation_score'],
        flagged_keywords=json.dumps(violations['flagged_keywords']),
        auto_moderation_action=violations['auto_moderation_action'],
        requires_admin_review=(violations['auto_moderation_action'] == 'review_required'),
        admin_approved=(violations['auto_moderation_action'] not in ['blocked', 'review_required'])
    )
    
    db.session.add(message)
    
    # Update or create message thread
    thread = MessageThread.query.filter(
        ((MessageThread.participant_1_id == sender_id) & (MessageThread.participant_2_id == recipient_id)) |
        ((MessageThread.participant_1_id == recipient_id) & (MessageThread.participant_2_id == sender_id))
    ).first()
    
    if not thread:
        thread = MessageThread(
            participant_1_id=sender_id,
            participant_2_id=recipient_id,
            subject=subject,
            thread_type=message_type
        )
        db.session.add(thread)
        db.session.flush()  # Get thread ID
    
    # Update thread
    thread.last_activity = datetime.utcnow()
    thread.message_count += 1
    thread.last_message_id = message.id
    
    try:
        db.session.commit()
        
        # Log communication
        communication_log = CommunicationLog(
            sender_id=sender_id,
            recipient_id=recipient_id,
            communication_type="message",
            subject=subject,
            content=content,
            content_length=len(content),
            platform_source="dashboard_message",
            related_job_id=related_job_id,
            related_work_request_id=related_work_request_id,
            related_invoice_id=related_invoice_id,
            sentiment_score=0.0,  # Could integrate sentiment analysis
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(communication_log)
        db.session.commit()
        
        return True, "Message sent successfully"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error sending message: {str(e)}"

def get_user_inbox(user_id, page=1, per_page=20):
    """Get user's inbox with pagination"""
    threads = MessageThread.query.filter(
        ((MessageThread.participant_1_id == user_id) & (~MessageThread.participant_1_archived)) |
        ((MessageThread.participant_2_id == user_id) & (~MessageThread.participant_2_archived))
    ).order_by(MessageThread.last_activity.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return threads

def mark_message_as_read(message_id, user_id):
    """Mark a message as read by the recipient"""
    message = Message.query.get(message_id)
    if message and message.recipient_id == user_id:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
        return True
    return False

# --- Network Management Functions ---

def send_network_invitation(network_owner_id, invitee_id, network_name, commission_percentage=0.0, 
                           subscription_fee=0.0, payment_structure="commission", invitation_message=""):
    """Send network invitation with contract and payment requirements"""
    
    # Validate commission percentage (max 5%)
    if commission_percentage > 5.0:
        return False, "Commission percentage cannot exceed 5%"
    
    # Check if invitation already exists
    existing_invitation = NetworkInvitation.query.filter_by(
        network_owner_id=network_owner_id,
        invitee_id=invitee_id,
        status="pending"
    ).first()
    
    if existing_invitation:
        return False, "Invitation already sent to this user"
    
    # Check if already a member
    existing_membership = NetworkMembership.query.filter_by(
        network_owner_id=network_owner_id,
        member_id=invitee_id,
        status="active"
    ).first()
    
    if existing_membership:
        return False, "User is already a member of this network"
    
    # Create invitation
    invitation = NetworkInvitation(
        network_owner_id=network_owner_id,
        invitee_id=invitee_id,
        invitation_type="manual",
        invitation_message=invitation_message,
        network_name=network_name,
        commission_percentage=commission_percentage,
        subscription_fee=subscription_fee,
        payment_structure=payment_structure,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    
    db.session.add(invitation)
    
    # Send notification message
    send_message(
        sender_id=network_owner_id,
        recipient_id=invitee_id,
        subject=f"Network Invitation: {network_name}",
        content=f"You've been invited to join the {network_name} network. {invitation_message}",
        message_type="network_invite"
    )
    
    try:
        db.session.commit()
        return True, "Network invitation sent successfully"
    except Exception as e:
        db.session.rollback()
        return False, f"Error sending invitation: {str(e)}"

def accept_network_invitation(invitation_id, invitee_id):
    """Accept a network invitation and create membership"""
    invitation = NetworkInvitation.query.get(invitation_id)
    
    if not invitation or invitation.invitee_id != invitee_id:
        return False, "Invalid invitation"
    
    if invitation.status != "pending":
        return False, "Invitation is no longer valid"
    
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.session.commit()
        return False, "Invitation has expired"
    
    # Check if contract signature is required and completed
    if invitation.contract_required and not invitation.contract_signed:
        return False, "Contract signature required before accepting invitation"
    
    # Check if payment is required and completed
    if invitation.payment_required and not invitation.payment_completed:
        return False, "Payment required before accepting invitation"
    
    # Create network membership
    membership = NetworkMembership(
        network_owner_id=invitation.network_owner_id,
        member_id=invitation.invitee_id,
        network_name=invitation.network_name,
        commission_percentage=invitation.commission_percentage,
        subscription_fee=invitation.subscription_fee,
        payment_structure=invitation.payment_structure,
        contract_envelope_id=invitation.docusign_envelope_id
    )
    
    db.session.add(membership)
    
    # Update invitation status
    invitation.status = "accepted"
    invitation.responded_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Send confirmation message
        send_message(
            sender_id=invitation.network_owner_id,
            recipient_id=invitation.invitee_id,
            subject=f"Welcome to {invitation.network_name}!",
            content=f"Your membership in {invitation.network_name} is now active.",
            message_type="network_business"
        )
        
        return True, "Network invitation accepted successfully"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error accepting invitation: {str(e)}"

def search_potential_network_members(network_owner_id, location=None, service_categories=None, 
                                   experience_level=None, rating_threshold=4.0):
    """Search for potential network members based on criteria"""
    
    query = User.query.filter(
        User.account_type.in_(["professional", "networking"]),
        User.approved,
        User.id != network_owner_id
    )
    
    # Exclude existing members
    existing_members = db.session.query(NetworkMembership.member_id).filter_by(
        network_owner_id=network_owner_id,
        status="active"
    ).subquery()
    
    query = query.filter(~User.id.in_(existing_members))
    
    # Filter by location if specified
    if location:
        query = query.filter(User.location.ilike(f"%{location}%"))
    
    # Filter by rating
    if rating_threshold:
        query = query.filter(User.average_rating >= rating_threshold)
    
    # Filter by experience level for professionals
    if experience_level and experience_level != "any":
        professional_profiles = query.join(User.professional_profile).filter(
            ProfessionalProfile.experience_level == experience_level
        )
        networking_profiles = query.join(User.networking_profile)
        query = professional_profiles.union(networking_profiles)
    
    return query.limit(50).all()

def create_customer_referral(network_member_id, customer_id, professional_id, job_posting_id=None, work_request_id=None):
    """Create a referral record when network member refers a professional to a customer"""
    
    # Get network membership
    membership = NetworkMembership.query.filter_by(
        member_id=network_member_id,
        status="active"
    ).first()
    
    if not membership:
        return False, "User is not an active network member"
    
    # Create referral record
    referral = NetworkReferral(
        network_membership_id=membership.id,
        referring_member_id=network_member_id,
        network_owner_id=membership.network_owner_id,
        customer_id=customer_id,
        referred_professional_id=professional_id,
        job_posting_id=job_posting_id,
        work_request_id=work_request_id,
        commission_rate_applied=membership.commission_percentage,
        referral_method="direct_invite"
    )
    
    db.session.add(referral)
    
    try:
        db.session.commit()
        return True, "Referral created successfully"
    except Exception as e:
        db.session.rollback()
        return False, f"Error creating referral: {str(e)}"

def log_data_deletion(user_id, deletion_type, affected_records=None):
    """Log data deletion requests for GDPR compliance"""
    track_user_activity(
        user_id=user_id,
        action_type="data_deletion",
        page_url=request.url,
        action_data=f"deletion_type:{deletion_type},affected_records:{affected_records}"
    )

def log_privacy_setting_change(user_id, setting_name, old_value, new_value):
    """Log changes to privacy settings"""
    track_user_activity(
        user_id=user_id,
        action_type="privacy_setting_change",
        page_url=request.url,
        action_data=f"setting:{setting_name},old:{old_value},new:{new_value}"
    )

def check_data_retention_policy():
    """Check and enforce data retention policies"""
    from datetime import datetime, timedelta
    
    # Get users with auto-delete enabled and past retention period
    cutoff_date = datetime.utcnow() - timedelta(days=2555)  # Default 7 years
    
    users_to_check = db.session.query(PIIProtection).filter(
        PIIProtection.auto_delete_enabled.is_(True),
        PIIProtection.last_privacy_update < cutoff_date
    ).all()
    
    for pii_settings in users_to_check:
        user = pii_settings.user
        if user:
            # Log the auto-deletion
            log_data_deletion(
                user_id=user.id,
                deletion_type="auto_retention_policy",
                affected_records="full_profile"
            )
            
            # Mark user as deleted (we might want to keep minimal records for legal purposes)
            user.email = f"deleted_{user.id}@privacy.deleted"
            user.approved = False
            user.email_verified = False


def process_network_commission(invoice):
    """Process enhanced commission: 8% to networking account, 2% to platform"""
    # Check if contractor is in any networking account network
    contractor = invoice.contractor
    network_connection = DeveloperNetwork.query.filter_by(
        contractor_id=contractor.id, 
        status="active"
    ).first()
    
    if network_connection:
        # In network: 8% to networking account, 2% to platform
        networking_account = network_connection.developer
        gross_amount = invoice.contractor_amount  # Amount contractor receives
        total_commission = gross_amount * 0.10  # 10% total commission
        
        networking_commission = gross_amount * 0.08  # 8% to networking account
        platform_commission = gross_amount * 0.02   # 2% to platform
        
        # Record the network earning
        earning = NetworkEarning(
            developer_id=networking_account.id,
            contractor_id=contractor.id,
            invoice_id=invoice.id,
            gross_amount=gross_amount,
            platform_commission_amount=platform_commission,
            developer_net_amount=networking_commission
        )
        
        db.session.add(earning)
        
        # Update networking account profile totals
        networking_profile = getattr(networking_account, 'developer_profile', None) or getattr(networking_account, 'networking_profile', None)
        if networking_profile:
            networking_profile.total_network_earnings += networking_commission
            networking_profile.platform_commission_collected += platform_commission
        
        db.session.commit()
        return True, "network"
    else:
        # Not in network: 10% commission to platform
        platform_commission = invoice.contractor_amount * 0.10
        
        # Create a platform earning record
        platform_earning = NetworkEarning(
            developer_id=None,  # No networking account
            contractor_id=contractor.id,
            invoice_id=invoice.id,
            gross_amount=invoice.contractor_amount,
            platform_commission_amount=platform_commission,
            developer_net_amount=0.0  # No networking account gets anything
        )
        
        db.session.add(platform_earning)
        db.session.commit()
        return True, "platform"
    
    return False, "none"


# --- Rating System Functions ---
def calculate_user_rating(user_id):
    """Calculate average rating for a user"""
    ratings = UserRating.query.filter_by(ratee_id=user_id).all()
    if not ratings:
        return 0.0, 0  # No ratings yet
    
    total_rating = sum(r.rating for r in ratings)
    count = len(ratings)
    average = round(total_rating / count, 1)
    return average, count


def get_user_rating_summary(user_id):
    """Get detailed rating breakdown for a user"""
    ratings = UserRating.query.filter_by(ratee_id=user_id).all()
    
    summary = {
        'average': 0.0,
        'count': 0,
        'breakdown': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        'recent_reviews': []
    }
    
    if ratings:
        total = sum(r.rating for r in ratings)
        summary['average'] = round(total / len(ratings), 1)
        summary['count'] = len(ratings)
        
        # Rating breakdown
        for rating in ratings:
            summary['breakdown'][rating.rating] += 1
        
        # Recent reviews (last 5)
        recent = sorted(ratings, key=lambda x: x.created_at, reverse=True)[:5]
        summary['recent_reviews'] = [
            {
                'rating': r.rating,
                'comment': r.comment,
                'date': r.created_at,
                'rater_name': r.rater.email.split('@')[0] if r.rater else 'Anonymous'
            }
            for r in recent if r.comment
        ]
    
    return summary


def is_new_user(user_id):
    """Check if user is new (less than 5 ratings received)"""
    rating_count = UserRating.query.filter_by(ratee_id=user_id).count()
    return rating_count < 5


# --- Enhanced Random Selection Algorithm ---
def get_random_contractors(service_category, geographic_area, customer_rating=None):
    """Get professionals using rating-influenced random selection"""
    contractors = db.session.query(User, ProfessionalProfile).join(
        ProfessionalProfile, User.id == ProfessionalProfile.user_id
    ).filter(User.account_type == "professional")
    
    # Apply filters
    if service_category:
        contractors = contractors.filter(
            ProfessionalProfile.services.ilike(f"%{service_category}%")
        )
    
    if geographic_area:
        contractors = contractors.filter(
            db.or_(
                ProfessionalProfile.geographic_area.ilike(f"%{geographic_area}%"),
                ProfessionalProfile.location.ilike(f"%{geographic_area}%")
            )
        )
    
    all_contractors = contractors.all()
    
    # Implement rating-influenced selection
    weighted_contractors = []
    
    for contractor_user, contractor_profile in all_contractors:
        rating, count = calculate_user_rating(contractor_user.id)
        is_new = is_new_user(contractor_user.id)
        
        # Base weight
        weight = 1.0
        
        # New user advantage (slight statistical advantage)
        if is_new:
            weight *= 1.15  # 15% boost for new users
        
        # Rating-based weighting
        if rating >= 4.5:
            weight *= 3.0  # 5-star contractors get high priority
        elif rating >= 4.0:
            weight *= 2.0  # 4+ star contractors get good priority
        elif rating >= 3.5:
            weight *= 1.5  # 3.5+ star contractors get slight priority
        elif rating >= 3.0:
            weight *= 1.0  # 3+ star contractors get normal weighting
        elif rating > 0:  # Has ratings but below 3
            weight *= 0.3  # Low-rated contractors get reduced selection
        # No ratings (rating == 0) keeps base weight with new user bonus
        
        # Customer rating matching (5-star customers only get 5-star contractors)
        if customer_rating and customer_rating >= 4.5:
            if rating < 4.5 and not is_new:  # Allow new users for 5-star customers
                weight *= 0.1  # Heavily reduce non-5-star contractors for 5-star customers
        
        # Add to weighted list multiple times based on weight
        repeat_count = max(1, int(weight * 10))  # Convert weight to repeat count
        for _ in range(repeat_count):
            weighted_contractors.append((contractor_user, contractor_profile))
    
    # Shuffle and return
    import random
    random.shuffle(weighted_contractors)
    return weighted_contractors


def get_random_networking_accounts(customer_rating=None):
    """Get networking accounts using rating-influenced random selection"""
    networking_accounts = db.session.query(User, NetworkingAccountProfile).join(
        NetworkingAccountProfile, User.id == NetworkingAccountProfile.user_id
    ).filter(User.account_type == "developer")
    
    all_accounts = networking_accounts.all()
    
    # Implement rating-influenced selection for networking accounts
    weighted_accounts = []
    
    for user, profile in all_accounts:
        rating, count = calculate_user_rating(user.id)
        is_new = is_new_user(user.id)
        
        # Base weight
        weight = 1.0
        
        # New user advantage
        if is_new:
            weight *= 1.15  # 15% boost for new users
        
        # Rating-based weighting
        if rating >= 4.5:
            weight *= 3.0  # 5-star networking accounts get high priority
        elif rating >= 4.0:
            weight *= 2.0
        elif rating >= 3.5:
            weight *= 1.5
        elif rating >= 3.0:
            weight *= 1.0
        elif rating > 0:
            weight *= 0.3  # Low-rated accounts get reduced selection
        
        # Customer rating matching for networking accounts
        if customer_rating and customer_rating >= 4.5:
            if rating < 4.5 and not is_new:
                weight *= 0.1  # 5-star customers only get 5-star networking accounts
        
        # Add to weighted list
        repeat_count = max(1, int(weight * 10))
        for _ in range(repeat_count):
            weighted_accounts.append((user, profile))
    
    import random
    random.shuffle(weighted_accounts)
    return weighted_accounts


# --- ID Verification Models ---
class IDVerification(db.Model):
    """ID verification system for all user types"""
    id = db.Column(db.Integer, primary_key=True)
    verification_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Document details
    document_type = db.Column(db.String(50), nullable=False)  # drivers_license, passport, state_id, military_id
    file_path = db.Column(db.String(500), nullable=False)
    
    # Verification status
    status = db.Column(db.String(20), default='pending')  # pending, processing, verified, rejected, expired
    extracted_data = db.Column(db.Text)  # JSON of extracted information
    confidence_score = db.Column(db.Float, default=0.0)
    validation_errors = db.Column(db.Text)  # JSON of validation errors
    
    # Processing details
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    verified_at = db.Column(db.DateTime)
    rejected_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey("user.id"))  # Admin who verified
    rejection_reason = db.Column(db.Text)
    
    # Expiration
    expires_at = db.Column(db.DateTime)  # ID verification expires after 2 years
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="id_verifications")
    verified_by_user = db.relationship("User", foreign_keys=[verified_by])

class TwoFactorAuth(db.Model):
    """Two-factor authentication settings and backup codes"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    
    # 2FA status
    enabled = db.Column(db.Boolean, default=False)
    email_based = db.Column(db.Boolean, default=True)  # Email-first 2FA
    phone_based = db.Column(db.Boolean, default=False)
    
    # Phone number for SMS 2FA (optional)
    phone_number = db.Column(db.String(20))
    phone_verified = db.Column(db.Boolean, default=False)
    
    # Backup codes (hashed)
    backup_codes = db.Column(db.Text)  # JSON array of hashed backup codes
    backup_codes_used = db.Column(db.Text, default='[]')  # JSON array of used codes
    
    # Recovery
    recovery_email = db.Column(db.String(120))
    recovery_email_verified = db.Column(db.Boolean, default=False)
    
    # Settings
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship("User", backref=db.backref("two_factor_auth", uselist=False))

class TwoFactorToken(db.Model):
    """Temporary 2FA tokens for login verification"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # Token details
    token = db.Column(db.String(10), nullable=False)  # 6-8 digit code
    token_type = db.Column(db.String(20), nullable=False)  # email, sms, backup
    token_hash = db.Column(db.String(255), nullable=False)  # Hashed token
    
    # Expiration and usage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    
    # Security
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Relationships
    user = db.relationship("User", backref="two_factor_tokens")

class ContractDocument(db.Model):
    """DocuSign contract documents"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # DocuSign details
    envelope_id = db.Column(db.String(100), unique=True, nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # contractor_agreement, client_terms, project_contract
    template_id = db.Column(db.String(100))
    
    # Document status
    status = db.Column(db.String(30), nullable=False)  # sent, delivered, signed, completed, declined, voided
    document_name = db.Column(db.String(255), nullable=False)
    
    # Signing details
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    signed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Document URLs
    document_url = db.Column(db.String(500))  # DocuSign document URL
    completed_document_url = db.Column(db.String(500))  # Signed document URL
    
    # Associated entities
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    contract_value = db.Column(db.Float)  # For project contracts
    
    # Comprehensive document system fields
    action_context = db.Column(db.String(100))  # What action triggered this document
    template_data = db.Column(db.Text)  # JSON data for template variables
    renewal_required = db.Column(db.Boolean, default=False)  # If document needs periodic renewal
    
    # Relationships
    user = db.relationship("User", backref="contract_documents")
    work_request = db.relationship("WorkRequest", backref="contracts")

# ===================================================================
# DOCUSIGN INTEGRATION - COMPLETE FUNCTIONAL SYSTEM
# ===================================================================

class DocuSignManager:
    """Complete DocuSign integration with automatic document enforcement"""
    
    def __init__(self):
        # Set up logging first
        self.logger = logging.getLogger('docusign_manager')
        
        # DocuSign configuration from .env
        self.integration_key = os.environ.get('DOCUSIGN_INTEGRATION_KEY')
        self.user_id = os.environ.get('DOCUSIGN_USER_ID')
        self.account_id = os.environ.get('DOCUSIGN_ACCOUNT_ID')
        self.base_path = os.environ.get('DOCUSIGN_BASE_PATH', 'https://demo.docusign.net/restapi')
        self.oauth_base_path = os.environ.get('DOCUSIGN_OAUTH_BASE_PATH', 'https://account-d.docusign.com')
        self.redirect_uri = os.environ.get('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/docusign/callback')
        
        # Load private key
        self.private_key = self._load_private_key()
        
        # Document storage
        self.document_storage_path = os.path.join(os.getcwd(), 'documents', 'signed_contracts')
        os.makedirs(self.document_storage_path, exist_ok=True)
        
        self.access_token = None
        self.token_expires_at = None
    
    def _load_private_key(self):
        """Load DocuSign private key"""
        key_path = os.environ.get('DOCUSIGN_PRIVATE_KEY_PATH', './docusign_private_key.txt')
        
        try:
            with open(key_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"DocuSign private key not found at {key_path}")
            return None
    
    def get_access_token(self):
        """Get JWT access token for DocuSign API"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
        
        if not self.private_key:
            raise Exception("DocuSign private key not configured")
        
        # Create JWT assertion
        now = datetime.utcnow()
        payload = {
            "iss": self.integration_key,
            "sub": self.user_id,
            "aud": "account-d.docusign.com",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "scope": "signature impersonation"
        }
        
        # Sign JWT
        assertion = jwt.encode(payload, self.private_key, algorithm='RS256')
        
        # Request access token
        token_url = f"{self.oauth_base_path}/oauth/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            return self.access_token
        else:
            raise Exception(f"Failed to get DocuSign access token: {response.text}")
    
    def require_contractor_documents(self, user):
        """Enforce required documents for contractors"""
        if not user.contractor_profile:
            return False, "No contractor profile found"
        
        # Check required documents
        required_docs = ['contractor_agreement', 'liability_waiver']
        missing_docs = []
        
        for doc_type in required_docs:
            contract = ContractDocument.query.filter_by(
                user_id=user.id,
                document_type=doc_type,
                status='completed'
            ).first()
            
            if not contract:
                missing_docs.append(doc_type)
        
        if missing_docs:
            # Automatically send missing documents
            for doc_type in missing_docs:
                self._send_required_document(user, doc_type)
            
            return False, f"Missing required documents: {', '.join(missing_docs)}"
        
        return True, "All required documents completed"
    
    def _send_required_document(self, user, document_type):
        """Send required document for signing"""
        try:
            # Prepare document data
            template_data = self._prepare_document_data(user, document_type)
            
            # Create envelope (simplified - would need actual template)
            envelope_data = {
                'envelopeId': f"env_{shortuuid.uuid()}_{document_type}",
                'status': 'sent'
            }
            
            # Save contract record
            contract = ContractDocument(
                user_id=user.id,
                envelope_id=envelope_data['envelopeId'],
                document_type=document_type,
                status='sent',
                document_name=self._get_document_name(document_type),
                sent_at=datetime.utcnow()
            )
            
            db.session.add(contract)
            db.session.commit()
            
            self.logger.info(f"Sent required document {document_type} to {user.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send document {document_type}: {str(e)}")
            return False
    
    def _prepare_document_data(self, user, document_type):
        """Prepare template data for document"""
        base_data = {
            'user_name': user.name,
            'user_email': user.email,
            'date': datetime.now().strftime('%B %d, %Y'),
            'platform_name': 'LaborLooker',
            'platform_fee': '10%',
            'payment_processing_fee': '2.9% + $0.30'
        }
        
        if user.contractor_profile:
            contractor_data = {
                'business_name': user.contractor_profile.business_name or '',
                'contact_name': user.contractor_profile.contact_name or user.name,
                'phone': user.contractor_profile.phone or '',
                'location': user.contractor_profile.location or ''
            }
            base_data.update(contractor_data)
        
        return base_data
    
    def _get_document_name(self, document_type):
        """Get friendly document name"""
        names = {
            'contractor_agreement': 'Contractor Service Agreement',
            'liability_waiver': 'Liability Waiver and Release',
            'employment_agreement': 'Employment Agreement',
            'project_contract': 'Project Contract',
            'client_terms': 'Client Terms of Service'
        }
        return names.get(document_type, document_type.replace('_', ' ').title())
    
    def handle_document_completion(self, contract):
        """Handle completed document"""
        user = User.query.get(contract.user_id)
        if not user:
            return
        
        # Mark completion time
        contract.completed_at = datetime.utcnow()
        contract.status = 'completed'
        
        # Update user permissions based on document type
        if contract.document_type == 'contractor_agreement':
            if user.contractor_profile:
                user.contractor_profile.agreement_signed = True
                user.contractor_profile.agreement_signed_at = datetime.utcnow()
                
        elif contract.document_type == 'liability_waiver':
            if user.contractor_profile:
                user.contractor_profile.liability_waiver_signed = True
                user.contractor_profile.liability_waiver_signed_at = datetime.utcnow()
        
        # Check if all required documents are complete
        all_complete, message = self.require_contractor_documents(user)
        if all_complete and user.contractor_profile:
            user.contractor_profile.documents_complete = True
            user.contractor_profile.status = 'active'
            
        db.session.commit()
        self.logger.info(f"Document {contract.document_type} completed for {user.email}")

# Global DocuSign manager instance
docusign_manager = DocuSignManager()

# Decorator for document enforcement
def require_contractor_documents(action=None):
    """Decorator to enforce contractor document requirements"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user or not user.contractor_profile:
                flash('Contractor profile required', 'error')
                return redirect(url_for('contractor_dashboard'))
            
            # Check document requirements
            documents_complete, missing_docs = docusign_manager.require_contractor_documents(user)
            
            if not documents_complete:
                flash(f'Required documents pending: {missing_docs}. Check your email to sign.', 'warning')
                return redirect(url_for('contractor_documents_required'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class JobRequirement(db.Model):
    """Enhanced job requirements with mandatory fields"""
    id = db.Column(db.Integer, primary_key=True)
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"), nullable=False, unique=True)
    
    # Enhanced requirements
    description = db.Column(db.Text, nullable=False)  # Minimum 10 words
    word_count = db.Column(db.Integer, default=0)
    
    # Image requirements (minimum 3 pictures)
    image_count = db.Column(db.Integer, default=0)
    image_paths = db.Column(db.Text)  # JSON array of image file paths
    
    # Additional details
    materials_list = db.Column(db.Text)
    timeline_details = db.Column(db.Text)
    budget_range = db.Column(db.String(50))
    urgency_level = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Accessibility and special requirements
    accessibility_requirements = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    
    # Validation status
    requirements_met = db.Column(db.Boolean, default=False)
    validation_errors = db.Column(db.Text)  # JSON array of validation issues
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    work_request = db.relationship("WorkRequest", backref=db.backref("job_requirements", uselist=False))

class PIIProtection(db.Model):
    """PII protection and profile view management"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    
    # Privacy settings
    profile_visibility = db.Column(db.String(20), default='limited')  # public, limited, private
    allow_contact_info_sharing = db.Column(db.Boolean, default=False)
    allow_location_sharing = db.Column(db.Boolean, default=True)
    allow_work_history_sharing = db.Column(db.Boolean, default=True)
    
    # PII masking settings
    mask_full_name = db.Column(db.Boolean, default=True)  # Show only first name + last initial
    mask_phone_number = db.Column(db.Boolean, default=True)  # Show only last 4 digits
    mask_email = db.Column(db.Boolean, default=True)  # Show only domain
    mask_address = db.Column(db.Boolean, default=True)  # Show only city/state
    
    # View tracking
    profile_views_allowed_per_month = db.Column(db.Integer, default=10)
    current_month_views = db.Column(db.Integer, default=0)
    last_view_reset = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Data retention
    data_retention_days = db.Column(db.Integer, default=2555)  # 7 years default
    auto_delete_enabled = db.Column(db.Boolean, default=False)
    
    # Audit trail
    last_privacy_update = db.Column(db.DateTime, default=datetime.utcnow)
    privacy_policy_accepted_version = db.Column(db.String(10))
    
    # Relationships
    user = db.relationship("User", backref=db.backref("pii_protection", uselist=False))

class ProfileView(db.Model):
    """Track profile views for PII protection"""
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    viewed_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    # View details
    view_type = db.Column(db.String(30))  # full_profile, contact_info, work_history
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Context
    source = db.Column(db.String(50))  # search, work_request, referral, direct
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    
    # Timestamps
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    viewer = db.relationship("User", foreign_keys=[viewer_id], backref="profile_views_made")
    viewed_user = db.relationship("User", foreign_keys=[viewed_user_id], backref="profile_views_received")
    work_request = db.relationship("WorkRequest", backref="related_profile_views")


# --- Routes ---
# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.email_verified:
                flash("Please verify your email before logging in.", "error")
                return redirect(url_for("login"))
            
            if user.account_type == "developer" and not user.approved:
                flash("Your developer account is pending approval.", "error")
                return redirect(url_for("login"))
            
            login_user(user)
            flash(f"Welcome back, {user.email}!", "success")
            
            # Redirect to main dashboard - simplified for South Carolina platform
            return redirect(url_for("main_dashboard"))
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("auth/login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    print(f"DEBUG: register() function called with method: {request.method}")
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        account_type = request.form.get("account_type", "")
        
        # Sanitize inputs
        email = sanitize_input(email, max_length=120)
        account_type = sanitize_input(account_type, max_length=20)
        
        # Validate email format
        email_valid, email_message = validate_email_format(email)
        if not email_valid:
            flash(email_message, "error")
            return redirect(url_for("register"))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("register"))
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, "error")
            return redirect(url_for("register"))
        
        # Validate account type
        valid_account_types = ["networking", "professional", "customer", "job_seeker"]
        if account_type not in valid_account_types:
            flash("Invalid account type selected.", "error")
            return redirect(url_for("register"))
        
        # Create user
        user = User(
            email=email,  # type: ignore
            password_hash=generate_password_hash(password),  # type: ignore
            account_type=account_type,  # type: ignore
            approved=account_type != "networking"  # type: ignore  # Auto-approve non-networking accounts
        )
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create default PII protection settings
        pii_protection = PIIProtection(user_id=user.id)
        db.session.add(pii_protection)
        
        # Create profile based on account type
        if account_type == "networking":
            referral_code = generate_unique_referral_code()
            networking_profile = NetworkingProfile(
                user_id=user.id,
                business_name=f"Network Business {user.id}",  # Placeholder - user will update
                contact_name=email.split('@')[0],  # Placeholder
                referral_code=referral_code
            )
            db.session.add(networking_profile)
        elif account_type == "professional":
            professional_profile = ProfessionalProfile(
                user_id=user.id,
                business_name=f"Professional Business {user.id}",  # Placeholder - user will update
                contact_name=email.split('@')[0],  # Placeholder
            )
            db.session.add(professional_profile)
        elif account_type == "job_seeker":
            job_seeker_profile = JobSeekerProfile(
                user_id=user.id,
                first_name=email.split('@')[0],  # Placeholder - user will update
                last_name="",  # Placeholder
            )
            db.session.add(job_seeker_profile)
        # Customer profiles are created when needed during first work request
        
        db.session.commit()
        
        # Track registration activity
        track_user_activity(
            user_id=user.id,
            action_type="registration",
            page_url=request.url,
            action_data=f"account_type:{account_type}"
        )
        
        # Send verification email
        send_verification_email(user)
        
        # For networking accounts, send approval request
        if account_type == "networking":
            send_developer_approval_email(user)
            flash("Networking account created! Please check your email for verification and wait for approval.", "success")
        else:
            flash("Account created! Please check your email for verification.", "success")
        
        return redirect(url_for("login"))
    
    return render_template("auth/register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# --- GDPR Compliance Routes ---
@app.route("/privacy/settings", methods=["GET", "POST"])
@login_required
def privacy_settings():
    """Manage privacy settings and PII protection"""
    pii_settings = get_user_pii_settings(current_user.id)
    
    if request.method == "POST":
        # Update privacy settings
        old_settings = {
            'profile_visibility': pii_settings.profile_visibility,
            'allow_contact_info_sharing': pii_settings.allow_contact_info_sharing,
            'mask_email': pii_settings.mask_email,
            'mask_phone_number': pii_settings.mask_phone_number,
            'mask_full_name': pii_settings.mask_full_name,
            'mask_address': pii_settings.mask_address
        }
        
        # Get new settings from form
        pii_settings.profile_visibility = sanitize_input(request.form.get("profile_visibility", "limited"), max_length=20)
        pii_settings.allow_contact_info_sharing = request.form.get("allow_contact_info_sharing") == "on"
        pii_settings.allow_location_sharing = request.form.get("allow_location_sharing") == "on"
        pii_settings.allow_work_history_sharing = request.form.get("allow_work_history_sharing") == "on"
        pii_settings.mask_email = request.form.get("mask_email") == "on"
        pii_settings.mask_phone_number = request.form.get("mask_phone_number") == "on"
        pii_settings.mask_full_name = request.form.get("mask_full_name") == "on"
        pii_settings.mask_address = request.form.get("mask_address") == "on"
        pii_settings.auto_delete_enabled = request.form.get("auto_delete_enabled") == "on"
        
        # Update retention period if provided
        retention_days = request.form.get("data_retention_days")
        if retention_days and retention_days.isdigit():
            pii_settings.data_retention_days = int(retention_days)
        
        pii_settings.last_privacy_update = datetime.utcnow()
        
        # Log privacy setting changes
        for setting, old_value in old_settings.items():
            new_value = getattr(pii_settings, setting)
            if old_value != new_value:
                log_privacy_setting_change(current_user.id, setting, old_value, new_value)
        
        try:
            db.session.commit()
            flash("Privacy settings updated successfully!", "success")
        except Exception:
            db.session.rollback()
            flash("Error updating privacy settings. Please try again.", "error")
        
        return redirect(url_for("privacy_settings"))
    
    return render_template("privacy/settings.html", pii_settings=pii_settings)

@app.route("/privacy/export-data")
@login_required
def export_user_data():
    """Export user's personal data (GDPR Article 20)"""
    log_data_export(current_user.id, "full_export")
    
    # Collect user data
    user_data = {
        'user_info': {
            'id': current_user.id,
            'email': current_user.email,
            'account_type': current_user.account_type,
            'email_verified': current_user.email_verified,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        }
    }
    
    # Add profile data based on account type
    if current_user.account_type == "professional" and current_user.professional_profile:
        profile = current_user.professional_profile
        user_data['professional_profile'] = {
            'business_name': profile.business_name,
            'contact_name': profile.contact_name,
            'phone': profile.phone,
            'location': profile.location,
            'geographic_area': profile.geographic_area,
            'services': profile.services,
            'created_at': profile.created_at.isoformat() if profile.created_at else None
        }
    
    elif current_user.account_type == "customer" and current_user.customer_profile:
        profile = current_user.customer_profile
        user_data['customer_profile'] = {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'state': profile.state,
            'zip_code': profile.zip_code,
            'created_at': profile.created_at.isoformat() if profile.created_at else None
        }
    
    elif current_user.account_type == "networking" and current_user.networking_profile:
        profile = current_user.networking_profile
        user_data['networking_profile'] = {
            'business_name': profile.business_name,
            'contact_name': profile.contact_name,
            'phone': profile.phone,
            'location': profile.location,
            'referral_code': profile.referral_code,
            'created_at': profile.created_at.isoformat() if profile.created_at else None
        }
    
    # Add privacy settings
    pii_settings = get_user_pii_settings(current_user.id)
    user_data['privacy_settings'] = {
        'profile_visibility': pii_settings.profile_visibility,
        'allow_contact_info_sharing': pii_settings.allow_contact_info_sharing,
        'mask_email': pii_settings.mask_email,
        'mask_phone_number': pii_settings.mask_phone_number,
        'data_retention_days': pii_settings.data_retention_days,
        'auto_delete_enabled': pii_settings.auto_delete_enabled
    }
    
    # Create JSON response
    import json
    from flask import Response
    
    json_data = json.dumps(user_data, indent=2, default=str)
    
    return Response(
        json_data,
        mimetype="application/json",
        headers={
            "Content-disposition": f"attachment; filename=user_data_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d')}.json"
        }
    )

@app.route("/privacy/delete-account", methods=["GET", "POST"])
@login_required
def delete_account():
    """Delete user account (GDPR Article 17 - Right to be forgotten)"""
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_deletion = request.form.get("confirm_deletion") == "on"
        
        # Verify password
        if not check_password_hash(current_user.password_hash, password):
            flash("Incorrect password. Account deletion cancelled.", "error")
            return render_template("privacy/delete_account.html")
        
        if not confirm_deletion:
            flash("You must confirm account deletion.", "error")
            return render_template("privacy/delete_account.html")
        
        # Log the deletion
        log_data_deletion(current_user.id, "full_account_deletion", "all_user_data")
        
        # Get user ID before deletion
        user_id = current_user.id
        
        try:
            # Delete related records (CASCADE should handle most of this)
            # But let's be explicit for important records
            
            # Delete PII protection settings
            PIIProtection.query.filter_by(user_id=user_id).delete()
            
            # Delete profile views
            ProfileView.query.filter(
                (ProfileView.viewer_id == user_id) | 
                (ProfileView.viewed_user_id == user_id)
            ).delete()
            
            # Anonymize user data instead of hard delete (for audit trail)
            current_user.email = f"deleted_{user_id}@privacy.deleted"
            current_user.password_hash = "DELETED"
            current_user.approved = False
            current_user.email_verified = False
            
            # Mark profiles as deleted but keep minimal data for business records
            if current_user.contractor_profile:
                current_user.contractor_profile.business_name = "DELETED"
                current_user.contractor_profile.contact_name = "DELETED"
                current_user.contractor_profile.phone = None
                current_user.contractor_profile.bank_name = None
                current_user.contractor_profile.routing_number = None
                current_user.contractor_profile.account_number = None
            
            if current_user.customer_profile:
                current_user.customer_profile.first_name = "DELETED"
                current_user.customer_profile.last_name = "DELETED"
                current_user.customer_profile.phone = None
                current_user.customer_profile.address = None
            
            if current_user.developer_profile:
                current_user.developer_profile.business_name = "DELETED"
                current_user.developer_profile.contact_name = "DELETED"
                current_user.developer_profile.phone = None
                current_user.developer_profile.bank_name = None
                current_user.developer_profile.routing_number = None
                current_user.developer_profile.account_number = None
            
            db.session.commit()
            
            # Log out the user
            logout_user()
            
            flash("Your account has been successfully deleted. All personal data has been removed.", "success")
            return redirect(url_for("login"))
            
        except Exception as e:
            db.session.rollback()
            flash("Error deleting account. Please contact support.", "error")
            print(f"Account deletion error: {e}")
            return render_template("privacy/delete_account.html")
    
    return render_template("privacy/delete_account.html")

@app.route("/privacy/consent", methods=["GET", "POST"])
def data_consent():
    """Redirect to new simplified consent gateway"""
    return redirect(url_for('consent_gateway'))

# --- Enhanced Consent Management (Legal Compliant) ---
@app.route("/privacy/consent-settings", methods=["GET"])
@login_required
def consent_settings():
    """Enhanced privacy settings with granular consent management"""
    # Get user's current consent preferences
    consent_summary = None
    try:
        consent_record = UserConsent.query.filter_by(user_id=current_user.id).first()
        if consent_record:
            consent_summary = {
                'granted_at': consent_record.granted_at,
                'version': consent_record.consent_version,
                'preferences': {
                    'marketing_communications': {'granted': consent_record.marketing_communications},
                    'personalization': {'granted': consent_record.personalization},
                    'market_research': {'granted': consent_record.market_research},
                    'performance_analytics': {'granted': consent_record.cookies_analytics},
                    'marketing_analytics': {'granted': consent_record.cookies_marketing}
                }
            }
    except Exception as e:
        app.logger.error(f"Error retrieving consent summary: {str(e)}")
    
    return render_template("privacy_settings.html", consent_summary=consent_summary)

@app.route("/privacy/update-consent", methods=["POST"])
@login_required
def update_consent():
    """API endpoint to update user consent preferences"""
    try:
        consent_data = request.get_json()
        
        # Get user's current consent record
        consent_record = UserConsent.query.filter_by(user_id=current_user.id).first()
        
        if not consent_record:
            return jsonify({
                'success': False,
                'error': 'No consent record found. Please contact support.'
            }), 404
        
        # Update optional consent preferences
        consent_record.marketing_communications = consent_data.get('marketing_communications', False)
        consent_record.personalization = consent_data.get('personalization', False)
        consent_record.market_research = consent_data.get('market_research', False)
        consent_record.cookies_analytics = consent_data.get('cookies_analytics', False)
        consent_record.cookies_marketing = consent_data.get('cookies_marketing', False)
        consent_record.updated_at = datetime.utcnow()
        
        # Update detailed consent data
        if consent_record.consent_data:
            preferences = consent_record.consent_data.get('preferences', {})
            for key, value in consent_data.items():
                if key in ['marketing_communications', 'personalization', 'market_research', 'cookies_analytics', 'cookies_marketing']:
                    preferences[key] = {
                        'granted': value,
                        'timestamp': datetime.utcnow().isoformat()
                    }
            consent_record.consent_data['preferences'] = preferences
        
        db.session.commit()
        
        # Update session preferences for immediate effect
        session['consent_preferences'] = {
            'marketing': consent_data.get('marketing_communications', False),
            'personalization': consent_data.get('personalization', False),
            'analytics': consent_data.get('cookies_analytics', False)
        }
        
        return jsonify({
            'success': True,
            'message': 'Privacy preferences updated successfully',
            'updated_preferences': consent_data
        })
        
    except Exception as e:
        app.logger.error(f"Error updating consent: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update preferences. Please try again.'
        }), 500

@app.route("/verify_email/<token>")
def verify_email(token):
    try:
        email = serializer.loads(token, salt="email-verification", max_age=86400)  # 24 hours
        user = User.query.filter_by(email=email).first()
        if user:
            user.email_verified = True  # type: ignore
            db.session.commit()
            flash("Email verified successfully! You can now log in.", "success")
        else:
            flash("Invalid verification token.", "error")
    except Exception:
        flash("Invalid or expired verification token.", "error")
    
    return redirect(url_for("login"))

def send_verification_email(user):
    """Send email verification"""
    token = serializer.dumps(user.email, salt="email-verification")
    verify_url = url_for("verify_email", token=token, _external=True)
    
    # Send verification email
    subject = "Verify Your Marketing Tech Platform Account"
    body = f"""
    Welcome to Marketing Tech Platform!
    
    Please click the link below to verify your email address:
    {verify_url}
    
    If you did not create this account, please ignore this email.
    
    Best regards,
    Marketing Tech Platform Team
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Welcome to Marketing Tech Platform!</h2>
        <p>Please click the button below to verify your email address:</p>
        <a href="{verify_url}" style="background-color: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
            Verify Email Address
        </a>
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>If you did not create this account, please ignore this email.</p>
        <hr>
        <p><small>Best regards,<br>Marketing Tech Platform Team</small></p>
    </body>
    </html>
    """
    
    if send_email(user.email, subject, body, html_body):
        print(f"Verification email sent to {user.email}")
    else:
        print(f"Failed to send verification email to {user.email}")
        # Fallback: print the URL for development
        print(f"Verification URL: {verify_url}")

def send_developer_approval_email(user):
    """Send approval request for developer account"""
    admin_email = "taschris.executive@gmail.com"
    subject = "New Developer Account Approval Required"
    body = f"""
    A new developer account requires approval:
    
    Email: {user.email}
    Account Type: {user.account_type}
    Registration Date: {user.created_at}
    
    Please review and approve this account in the admin dashboard.
    
    Marketing Tech Platform
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>New Developer Account Approval Required</h2>
        <p>A new developer account requires your approval:</p>
        <table style="border-collapse: collapse; border: 1px solid #ddd;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Email:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{user.email}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Account Type:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{user.account_type}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Registration Date:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{user.created_at}</td></tr>
        </table>
        <p>Please review and approve this account in the admin dashboard.</p>
        <hr>
        <p><small>Marketing Tech Platform</small></p>
    </body>
    </html>
    """
    
    if send_email(admin_email, subject, body, html_body):
        print(f"Developer approval notification sent for: {user.email}")
    else:
        print(f"Failed to send developer approval notification for: {user.email}")

# --- Dashboard Routes ---
@app.route("/networking_dashboard")
@login_required
def networking_dashboard():
    if current_user.account_type != "networking":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get networking account's profile and network data
    profile = current_user.networking_profile
    if not profile:
        # Create profile if missing
        referral_code = generate_unique_referral_code()
        profile = NetworkingProfile(
            user_id=current_user.id,
            business_name=f"Network Business {current_user.id}",
            contact_name=current_user.email.split('@')[0],
            referral_code=referral_code
        )
        db.session.add(profile)
        db.session.commit()
    
    # Get network statistics
    network_members = NetworkMembership.query.filter_by(
        network_owner_id=current_user.id,
        status="active"
    ).count()
    
    pending_invitations = NetworkInvitation.query.filter_by(
        network_owner_id=current_user.id,
        status="pending"
    ).count()
    
    # Calculate total earnings from network referrals
    total_earnings = db.session.query(db.func.sum(NetworkReferral.network_owner_commission)).filter(
        NetworkReferral.network_owner_id == current_user.id,
        NetworkReferral.commission_paid_to_owner
    ).scalar() or 0
    
    # Get available job postings for networking account work search
    available_jobs = JobPosting.query.filter_by(status="active").order_by(
        JobPosting.created_at.desc()
    ).limit(20).all()
    
    # Get customers needing work (for referral opportunities)
    customer_work_requests = WorkRequest.query.filter_by(status="open").order_by(
        WorkRequest.created_at.desc()
    ).limit(15).all()
    
    # Get recent network activity
    recent_referrals = NetworkReferral.query.filter_by(
        network_owner_id=current_user.id
    ).order_by(NetworkReferral.created_at.desc()).limit(10).all()
    
    # Get recent messages
    recent_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).order_by(Message.sent_at.desc()).limit(5).all()
    
    # Get current network members
    network_memberships = NetworkMembership.query.filter_by(
        network_owner_id=current_user.id,
        status="active"
    ).all()
    
    # Get customer search requests
    customer_searches = CustomerSearchRequest.query.filter_by(
        networking_account_id=current_user.id,
        is_active=True
    ).all()
    
    # Generate referral link
    referral_link = url_for('register_with_referral', 
                           code=profile.referral_code, 
                           _external=True)
    
    return render_template("dashboards/networking.html", 
                         profile=profile,
                         network_members=network_members,
                         pending_invitations=pending_invitations,
                         total_earnings=total_earnings,
                         available_jobs=available_jobs,
                         customer_work_requests=customer_work_requests,
                         recent_referrals=recent_referrals,
                         recent_messages=recent_messages,
                         network_memberships=network_memberships,
                         customer_searches=customer_searches,
                         referral_link=referral_link)

@app.route("/professional_dashboard")
@login_required  
def professional_dashboard():
    if current_user.account_type != "professional":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get professional's work requests and invoices
    work_requests = WorkRequest.query.filter_by(contractor_id=current_user.id).all()
    invoices = ContractorInvoice.query.filter_by(contractor_id=current_user.id).all()
    
    # Get available job postings for work search
    available_jobs = JobPosting.query.filter_by(status="active").order_by(
        JobPosting.created_at.desc()
    ).limit(20).all()
    
    # Get job matches if any
    job_matches = JobMatch.query.filter_by(professional_id=current_user.id).all()
    
    # Get recent messages
    recent_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).order_by(Message.sent_at.desc()).limit(5).all()
    
    # Get network invitations
    network_invitations = NetworkInvitation.query.filter_by(
        invitee_id=current_user.id,
        status="pending"
    ).all()
    
    # Get network memberships
    network_memberships = NetworkMembership.query.filter_by(
        member_id=current_user.id,
        status="active"
    ).all()
    
    return render_template("dashboards/professional.html",
                         work_requests=work_requests,
                         invoices=invoices,
                         available_jobs=available_jobs,
                         job_matches=job_matches,
                         recent_messages=recent_messages,
                         network_invitations=network_invitations,
                         network_memberships=network_memberships)

@app.route("/customer_dashboard")
@login_required
def customer_dashboard():
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get customer's work requests and invoices
    work_requests = WorkRequest.query.filter_by(customer_id=current_user.id).all()
    invoices = ContractorInvoice.query.filter_by(customer_id=current_user.id).all()
    
    return render_template("dashboards/customer.html",
                         work_requests=work_requests,
                         invoices=invoices)

@app.route("/job_seeker_dashboard")
@login_required
def job_seeker_dashboard():
    """Job seeker dashboard with 'Find Work' functionality"""
    if current_user.account_type != "job_seeker":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get job seeker's matches and applications
    job_matches = JobMatch.query.filter_by(job_seeker_id=current_user.id).all()
    
    # Get available job postings that match job seeker's criteria
    available_jobs = []
    if current_user.job_seeker_profile:
        profile = current_user.job_seeker_profile
        if profile.desired_labor_categories:
            import json
            try:
                desired_categories = json.loads(profile.desired_labor_categories)
                for category in desired_categories:
                    jobs = JobPosting.query.filter(
                        JobPosting.labor_category.ilike(f"%{category}%"),
                        JobPosting.status == "active"
                    ).all()
                    available_jobs.extend(jobs)
            except Exception as e:
                print(f"Error loading job categories: {e}")
                available_jobs = JobPosting.query.filter_by(status="active").all()
    
    return render_template("dashboards/job_seeker.html",
                         job_matches=job_matches,
                         available_jobs=available_jobs)

# --- Training and Certification Routes ---
@app.route("/training/courses")
def training_courses():
    """Display available free training courses and certifications"""
    try:
        from training_resources import TRAINING_RESOURCES
        training_data = TRAINING_RESOURCES
    except ImportError:
        print("Warning: training_resources module not found, using fallback data")
        training_data = {
            "courses": [
                {
                    "id": "basic-safety",
                    "title": "Basic Safety Training",
                    "description": "Essential safety protocols for all workers",
                    "duration": "2 hours",
                    "certification": True
                }
            ]
        }
    return render_template("training/courses.html", training_data=training_data)

@app.route("/api/add-training-course", methods=["POST"])
@login_required
def add_training_course():
    """Add a training course to user's profile"""
    try:
        data = request.get_json()
        course_id = data.get('courseId')
        
        if not course_id:
            return jsonify({"success": False, "error": "Course ID required"})
        
        # Check if user has a job seeker profile
        if not current_user.job_seeker_profile:
            # Create job seeker profile if it doesn't exist
            profile = JobSeekerProfile(
                user_id=current_user.id,
                skills=json.dumps([]),
                certifications=json.dumps([course_id]),
                training_courses=json.dumps([course_id])
            )
            db.session.add(profile)
        else:
            # Update existing profile
            profile = current_user.job_seeker_profile
            
            # Update training courses
            try:
                training_courses = json.loads(profile.training_courses or "[]")
                if course_id not in training_courses:
                    training_courses.append(course_id)
                    profile.training_courses = json.dumps(training_courses)
                
                # Update certifications list as well
                certifications = json.loads(profile.certifications or "[]")
                if course_id not in certifications:
                    certifications.append(course_id)
                    profile.certifications = json.dumps(certifications)
                    
            except (json.JSONDecodeError, TypeError):
                # Handle corrupted JSON by starting fresh
                profile.training_courses = json.dumps([course_id])
                profile.certifications = json.dumps([course_id])
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Training course added to profile successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False, 
            "error": f"Failed to add course to profile: {str(e)}"
        })

@app.route("/api/check-course-completion")
@login_required
def check_course_completion():
    """Check for newly completed training courses"""
    try:
        # This would typically check external APIs or user input
        # For now, return empty array as placeholder
        return jsonify({
            "success": True,
            "newCompletions": []
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/downloads/certification-guide")
def download_certification_guide():
    """Download the certification guide"""
    try:
        return send_file(
            'static/downloads/certification-guide.md',
            as_attachment=True,
            download_name='LaborLooker-Certification-Guide.md',
            mimetype='text/markdown'
        )
    except Exception as e:
        flash("Guide download not available at this time.", "error")
        return redirect(url_for('training_courses'))

# --- Networking Account Routes ---
@app.route("/register/<code>")
def register_with_referral(code):
    """Registration through networking account referral link"""
    networking_profile = NetworkingProfile.query.filter_by(referral_code=code).first()
    if not networking_profile:
        flash("Invalid referral code.", "error")
        return redirect(url_for("register"))
    
    session['referral_code'] = code
    flash(f"Joining {networking_profile.business_name}'s network!", "info")
    return render_template("auth/register.html", referral_info=networking_profile)

@app.route("/developer/network")
@login_required
def developer_network():
    """Manage developer's business network"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get network members
    network_members = db.session.query(User, DeveloperNetwork).join(
        DeveloperNetwork, User.id == DeveloperNetwork.contractor_id
    ).filter(DeveloperNetwork.developer_id == current_user.id).all()
    
    return render_template("developer/network.html", network_members=network_members)

@app.route("/developer/business-lookup")
@login_required  
def developer_business_lookup():
    """Business lookup tool for developers"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get all contractors not in current developer's network
    existing_network = DeveloperNetwork.query.filter_by(
        developer_id=current_user.id
    ).with_entities(DeveloperNetwork.contractor_id).all()
    
    existing_ids = [n.contractor_id for n in existing_network]
    
    available_contractors = User.query.filter(
        User.account_type == "contractor",
        ~User.id.in_(existing_ids) if existing_ids else True
    ).all()
    
    return render_template("developer/business_lookup.html", 
                         contractors=available_contractors)

@app.route("/developer/invite/<int:contractor_id>", methods=["POST"])
@login_required
def invite_contractor(contractor_id):
    """Invite contractor to developer network"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    contractor = User.query.get_or_404(contractor_id)
    
    # Check if already in network
    existing = DeveloperNetwork.query.filter_by(
        developer_id=current_user.id,
        contractor_id=contractor_id
    ).first()
    
    if existing:
        flash("Contractor is already in your network.", "warning")
    else:
        network_connection = DeveloperNetwork(
            developer_id=current_user.id,
            contractor_id=contractor_id,
            status="active",
            invitation_method="business_lookup"
        )
        db.session.add(network_connection)
        db.session.commit()
        
        flash(f"Successfully added {contractor.email} to your network!", "success")
    
    return redirect(url_for("developer_business_lookup"))

@app.route("/developer/requests")
@login_required
def developer_requests():
    """View contractor requests to join network"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    pending_requests = ContractorSearchRequest.query.filter_by(
        assigned_developer_id=current_user.id,
        status="pending"
    ).all()
    
    return render_template("developer/requests.html", requests=pending_requests)

@app.route("/developer/respond-request/<int:request_id>/<action>")
@login_required
def respond_to_request(request_id, action):
    """Approve or reject contractor network request"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    request_obj = ContractorSearchRequest.query.get_or_404(request_id)
    
    if request_obj.assigned_developer_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("developer_requests"))
    
    if action == "approve":
        request_obj.status = "approved"
        request_obj.responded_at = datetime.utcnow()
        
        # Add to network
        network_connection = DeveloperNetwork(
            developer_id=current_user.id,
            contractor_id=request_obj.contractor_id,
            status="active",
            invitation_method="contractor_request"
        )
        db.session.add(network_connection)
        flash("Contractor added to your network!", "success")
        
    elif action == "reject":
        request_obj.status = "rejected"
        request_obj.responded_at = datetime.utcnow()
        flash("Request rejected.", "info")
    
    db.session.commit()
    return redirect(url_for("developer_requests"))

# --- Contractor Routes ---
@app.route("/contractor/settings")
@login_required
def contractor_settings():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("contractor/settings.html")

@app.route("/contractor/requests")
@login_required
def contractor_requests():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    work_requests = WorkRequest.query.filter_by(contractor_id=current_user.id).all()
    return render_template("contractor/requests.html", work_requests=work_requests)

@app.route("/contractor/schedule")
@login_required
def contractor_schedule():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("contractor/schedule.html")

@app.route("/contractor/network-request")
@login_required
def contractor_network_request():
    """Request to join a developer network"""
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Check if already in a network
    existing_network = DeveloperNetwork.query.filter_by(
        contractor_id=current_user.id,
        status="active"
    ).first()
    
    if existing_network:
        flash("You are already part of a developer network.", "info")
        return redirect(url_for("contractor_dashboard"))
    
    # Get all approved developers
    developers = User.query.filter_by(account_type="developer", approved=True).all()
    
    return render_template("contractor/network_request.html", developers=developers)

@app.route("/contractor/submit-network-request", methods=["POST"])
@login_required
def submit_network_request():
    """Submit request to join developer network"""
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    requested_developer_id = request.form.get("developer_id")
    request_message = request.form.get("message", "")
    
    if requested_developer_id == "random":
        # Random assignment
        assigned_developer = assign_random_developer()
        if not assigned_developer:
            flash("No developers available at this time.", "error")
            return redirect(url_for("contractor_network_request"))
        
        network_request = ContractorSearchRequest(
            contractor_id=current_user.id,
            assigned_developer_id=assigned_developer.id,
            request_message=request_message
        )
        flash(f"Request sent to {assigned_developer.email}!", "success")
        
    else:
        # Specific developer requested
        developer = User.query.get(requested_developer_id)
        if not developer:
            flash("Invalid developer selected.", "error")
            return redirect(url_for("contractor_network_request"))
        
        network_request = ContractorSearchRequest(
            contractor_id=current_user.id,
            requested_developer_id=developer.id,
            assigned_developer_id=developer.id,
            request_message=request_message
        )
        flash(f"Request sent to {developer.email}!", "success")
    
    db.session.add(network_request)
    db.session.commit()
    
    return redirect(url_for("contractor_dashboard"))

@app.route("/contractor/invoice/new", methods=["GET", "POST"])
@login_required
def contractor_invoice_new():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get professional profile for commission rate
    profile = ProfessionalProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        # Get enhanced form data with labor/materials separation
        customer_email = request.form.get("customer_email", "")
        work_request_id = request.form.get("work_request_id")
        description = request.form.get("description", "")
        
        # Separate labor and materials pricing
        labor_cost_str = request.form.get("labor_cost", "0")
        materials_cost_str = request.form.get("materials_cost", "0")
        
        # Sales tax settings
        customer_state = request.form.get("customer_state", "")
        sales_tax_rate_str = request.form.get("sales_tax_rate", "0")
        auto_calculate_tax = request.form.get("auto_calculate_tax") == "on"
        
        # Payment terms
        due_date = request.form.get("due_date")
        payment_terms = request.form.get("payment_terms", "")
        action = request.form.get("action", "draft")  # 'send' or 'draft'
        
        # Validate and convert amounts
        try:
            labor_cost = float(labor_cost_str) if labor_cost_str else 0.0
            materials_cost = float(materials_cost_str) if materials_cost_str else 0.0
            subtotal = labor_cost + materials_cost
            
            # Auto-calculate sales tax based on state
            if auto_calculate_tax:
                sales_tax_rate = get_sales_tax_rate(customer_state)
            else:
                sales_tax_rate = float(sales_tax_rate_str) if sales_tax_rate_str else 0.0
            
        except (ValueError, TypeError):
            flash("Invalid amount entered. Please check your numbers.", "error")
            return redirect(url_for("contractor_invoice_new"))
        
        # Calculate taxes and totals
        sales_tax_amount = subtotal * (sales_tax_rate / 100)
        total_amount = subtotal + sales_tax_amount
        
        # Calculate commission (on subtotal, not including tax)
        commission_rate = profile.commission_rate if profile else 10.0
        commission_amount = subtotal * (commission_rate / 100)
        contractor_amount = total_amount - commission_amount
        
        # Parse due date
        due_date_obj = None
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Find or create customer
        customer = User.query.filter_by(email=customer_email).first()
        customer_id = customer.id if customer else None
        
        # Create enhanced invoice with new fields
        invoice_data = {
            'contractor_id': current_user.id,
            'customer_id': customer_id,
            'customer_email': customer_email,
            'work_request_id': int(work_request_id) if work_request_id else None,
            'description': description,
            'labor_cost': labor_cost,
            'materials_cost': materials_cost,
            'amount': subtotal,  # Keep for backward compatibility
            'sales_tax_rate': sales_tax_rate,
            'sales_tax': sales_tax_amount,
            'total_amount': total_amount,
            'commission_amount': commission_amount,
            'contractor_amount': contractor_amount,
            'commission_rate': commission_rate,
            'status': "sent" if action == "send" else "draft",
            'due_date': due_date_obj,
            'payment_terms': payment_terms
        }
        
        # Note: Creating invoice object without unpacking due to SQLAlchemy constructor limitations
        invoice = ContractorInvoice()
        for key, value in invoice_data.items():
            setattr(invoice, key, value)
        
        try:
            db.session.add(invoice)
            db.session.commit()
            
            # Process network commission if applicable (2% platform fee)
            process_network_commission(invoice)
            
            # Send email if action is 'send'
            if action == "send":
                send_enhanced_invoice_email(invoice, customer_email)
                flash("Enhanced invoice created and sent successfully!", "success")
            else:
                flash("Enhanced invoice saved as draft!", "success")
                
            return redirect(url_for("contractor_invoices"))
        except Exception as e:
            db.session.rollback()
            flash("Error creating invoice. Please try again.", "error")
            print(f"Database error: {e}")
    
    # Get US states for sales tax calculation
    us_states = get_us_states_list()
    
    return render_template("contractor/invoice_new.html", 
                         profile=profile, 
                         us_states=us_states)


def get_sales_tax_rate(state):
    """Get sales tax rate by state (simplified - in production, use a real tax API)"""
    sales_tax_rates = {
        'AL': 4.0, 'AK': 0.0, 'AZ': 5.6, 'AR': 6.5, 'CA': 7.25, 'CO': 2.9, 'CT': 6.35,
        'DE': 0.0, 'FL': 6.0, 'GA': 4.0, 'HI': 4.0, 'ID': 6.0, 'IL': 6.25, 'IN': 7.0,
        'IA': 6.0, 'KS': 6.5, 'KY': 6.0, 'LA': 4.45, 'ME': 5.5, 'MD': 6.0, 'MA': 6.25,
        'MI': 6.0, 'MN': 6.875, 'MS': 7.0, 'MO': 4.225, 'MT': 0.0, 'NE': 5.5, 'NV': 6.85,
        'NH': 0.0, 'NJ': 6.625, 'NM': 5.125, 'NY': 4.0, 'NC': 4.75, 'ND': 5.0, 'OH': 5.75,
        'OK': 4.5, 'OR': 0.0, 'PA': 6.0, 'RI': 7.0, 'SC': 6.0, 'SD': 4.5, 'TN': 7.0,
        'TX': 6.25, 'UT': 5.95, 'VT': 6.0, 'VA': 5.3, 'WA': 6.5, 'WV': 6.0, 'WI': 5.0, 'WY': 4.0
    }
    return sales_tax_rates.get(state.upper(), 0.0)


def get_us_states_list():
    """Get list of US states for dropdown"""
    return [
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
        ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
        ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
        ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
        ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'), ('WY', 'Wyoming')
    ]


def send_enhanced_invoice_email(invoice, customer_email):
    """Send enhanced invoice email with detailed breakdown"""
    subject = f"Invoice from {invoice.contractor.contractor_profile.business_name if invoice.contractor.contractor_profile else invoice.contractor.email}"
    
    # Calculate totals for display
    labor_cost = getattr(invoice, 'labor_cost', 0) or 0
    materials_cost = getattr(invoice, 'materials_cost', 0) or 0
    sales_tax = getattr(invoice, 'sales_tax', 0) or 0
    total_amount = getattr(invoice, 'total_amount', 0) or invoice.amount or 0
    
    body = f"""
    Invoice Details:
    
    Business: {invoice.contractor.contractor_profile.business_name if invoice.contractor.contractor_profile else 'Independent Contractor'}
    Description: {invoice.description}
    
    Cost Breakdown:
    Labor: ${labor_cost:.2f}
    Materials: ${materials_cost:.2f}
    Subtotal: ${(labor_cost + materials_cost):.2f}
    Sales Tax: ${sales_tax:.2f}
    Total Amount: ${total_amount:.2f}
    
    Due Date: {invoice.due_date}
    Payment Terms: {invoice.payment_terms}
    
    Please remit payment to the contractor directly.
    
    This invoice was generated through LaborLooker.
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Invoice from {invoice.contractor.contractor_profile.business_name if invoice.contractor.contractor_profile else invoice.contractor.email}</h2>
        
        <h3>Invoice Details</h3>
        <p><strong>Description:</strong> {invoice.description}</p>
        
        <h3>Cost Breakdown</h3>
        <table border="1" style="border-collapse: collapse;">
            <tr><td><strong>Labor:</strong></td><td>${labor_cost:.2f}</td></tr>
            <tr><td><strong>Materials:</strong></td><td>${materials_cost:.2f}</td></tr>
            <tr><td><strong>Subtotal:</strong></td><td>${(labor_cost + materials_cost):.2f}</td></tr>
            <tr><td><strong>Sales Tax:</strong></td><td>${sales_tax:.2f}</td></tr>
            <tr><td><strong>Total Amount:</strong></td><td><strong>${total_amount:.2f}</strong></td></tr>
        </table>
        
        <h3>Payment Information</h3>
        <p><strong>Due Date:</strong> {invoice.due_date}</p>
        <p><strong>Payment Terms:</strong> {invoice.payment_terms}</p>
        
        <p>Please remit payment to the contractor directly.</p>
        
        <hr>
        <p><small>This invoice was generated through LaborLooker.</small></p>
    </body>
    </html>
    """
    
    return send_email(customer_email, subject, body, html_body)

@app.route("/contractor/invoices")
@login_required
def contractor_invoices():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    invoices = ContractorInvoice.query.filter_by(contractor_id=current_user.id).all()
    return render_template("contractor/invoices.html", invoices=invoices)

@app.route("/contractor/profile", methods=["GET", "POST"])
@login_required
def contractor_profile():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get existing profile or create new one
    profile = ProfessionalProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        # Get and sanitize form data
        business_name = sanitize_input(request.form.get("business_name", ""), max_length=255)
        contact_name = sanitize_input(request.form.get("contact_name", ""), max_length=255)
        phone = sanitize_input(request.form.get("phone", ""), max_length=50)
        location = sanitize_input(request.form.get("location", ""), max_length=255)
        geographic_area = sanitize_input(request.form.get("geographic_area", ""), max_length=50)
        service_radius = request.form.get("service_radius", "")
        billing_plan = sanitize_input(request.form.get("billing_plan", ""), max_length=50)
        bank_name = sanitize_input(request.form.get("bank_name", ""), max_length=255)
        routing_number = sanitize_input(request.form.get("routing_number", ""), max_length=20)
        account_number = sanitize_input(request.form.get("account_number", ""), max_length=50)
        work_hours = sanitize_input(request.form.get("work_hours", ""), max_length=500, allow_html=False)
        
        # Validate required fields
        if not business_name:
            flash("Business name is required.", "error")
            return render_template("contractor/profile.html", profile=profile, service_categories=SERVICE_CATEGORIES)
        
        if not contact_name:
            flash("Contact name is required.", "error")
            return render_template("contractor/profile.html", profile=profile, service_categories=SERVICE_CATEGORIES)
        
        # Validate phone format if provided
        if phone:
            phone_valid, phone_message = validate_phone_format(phone)
            if not phone_valid:
                flash(phone_message, "error")
                return render_template("contractor/profile.html", profile=profile, service_categories=SERVICE_CATEGORIES)
        
        # Validate geographic area
        if geographic_area and geographic_area not in GEOGRAPHIC_AREAS:
            flash("Invalid geographic area selected.", "error")
            return render_template("contractor/profile.html", profile=profile, service_categories=SERVICE_CATEGORIES)
        
        # Validate billing plan
        valid_billing_plans = ["commission_only", "subscription_plus_commission"]
        if billing_plan not in valid_billing_plans:
            flash("Invalid billing plan selected.", "error")
            return render_template("contractor/profile.html", profile=profile, service_categories=SERVICE_CATEGORIES)
        
        # Get selected services
        services = request.form.getlist("services")
        services_str = ",".join(services) if services else ""
        
        # Set commission rate and subscription based on plan
        if billing_plan == "subscription_plus_commission":
            commission_rate = 5.0
            monthly_subscription = 30.0
        else:
            commission_rate = 10.0
            monthly_subscription = 0.0
        
        if profile:
            # Update existing profile
            profile.business_name = business_name
            profile.contact_name = contact_name
            profile.phone = phone
            profile.location = location
            profile.geographic_area = geographic_area
            profile.service_radius = int(service_radius) if service_radius else None
            profile.billing_plan = billing_plan
            profile.commission_rate = commission_rate
            profile.monthly_subscription = monthly_subscription
            profile.bank_name = bank_name
            profile.routing_number = routing_number
            profile.account_number = account_number
            profile.work_hours = work_hours
            profile.services = services_str
        else:
            # Create new profile
            profile = ProfessionalProfile(
                user_id=current_user.id,
                business_name=business_name,
                contact_name=contact_name,
                phone=phone,
                location=location,
                geographic_area=geographic_area,
                service_radius=int(service_radius) if service_radius else None,
                billing_plan=billing_plan,
                commission_rate=commission_rate,
                monthly_subscription=monthly_subscription,
                bank_name=bank_name,
                routing_number=routing_number,
                account_number=account_number,
                work_hours=work_hours,
                services=services_str
            )
            db.session.add(profile)
        
        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for("contractor_dashboard"))
        except Exception as e:
            db.session.rollback()
            flash("Error updating profile. Please try again.", "error")
            print(f"Database error: {e}")
    
    return render_template("contractor/profile.html", 
                         profile=profile, 
                         service_categories=SERVICE_CATEGORIES)

@app.route("/contractor/payment")
@login_required
def contractor_payment():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("contractor/payment.html")

# --- Customer Routes ---
@app.route("/customer/schedule-work")
@login_required
def customer_schedule_work():
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("customer/schedule_work.html")

@app.route("/customer/billing")
@login_required
def customer_billing():
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    return render_template("customer/billing.html")

@app.route("/customer/search-contractors")
@login_required
def customer_search_contractors():
    """Enhanced contractor search with company name functionality"""
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get search parameters
    search_query = request.args.get("search", "")
    service_category = request.args.get("category", "")
    location = request.args.get("location", "")
    
    # Base query for professionals with profiles
    contractors = db.session.query(User, ProfessionalProfile).join(
        ProfessionalProfile, User.id == ProfessionalProfile.user_id
    ).filter(User.account_type == "professional")
    
    # Apply search filters
    if search_query:
        # Search by company name, contact name, or email
        contractors = contractors.filter(
            db.or_(
                ProfessionalProfile.business_name.ilike(f"%{search_query}%"),
                ProfessionalProfile.contact_name.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%")
            )
        )
    
    if service_category:
        # Filter by service category
        contractors = contractors.filter(
            ProfessionalProfile.services.ilike(f"%{service_category}%")
        )
    
    if location:
        # Filter by location or geographic area
        contractors = contractors.filter(
            db.or_(
                ProfessionalProfile.location.ilike(f"%{location}%"),
                ProfessionalProfile.geographic_area.ilike(f"%{location}%")
            )
        )
    
    # Get results
    contractor_results = contractors.all()
    
    # Track search activity
    track_user_activity(
        user_id=current_user.id,
        action_type="contractor_search",
        page_url=request.url,
        action_data=f"query:{search_query},category:{service_category},location:{location},results:{len(contractor_results)}"
    )
    
    return render_template("customer/search_contractors.html", 
                         contractors=contractor_results,
                         service_categories=SERVICE_CATEGORIES,
                         geographic_areas=GEOGRAPHIC_AREAS,
                         search_query=search_query,
                         service_category=service_category,
                         location=location)

@app.route("/customer/contractor/<int:contractor_id>")
@login_required
def view_contractor_profile(contractor_id):
    """View detailed contractor profile"""
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    contractor = User.query.get_or_404(contractor_id)
    if contractor.account_type != "contractor":
        flash("Invalid contractor.", "error")
        return redirect(url_for("customer_search_contractors"))
    
    profile = contractor.contractor_profile
    if not profile:
        flash("Contractor profile not found.", "error")
        return redirect(url_for("customer_search_contractors"))
    
    # Track profile view
    track_user_activity(
        user_id=current_user.id,
        action_type="contractor_profile_view",
        page_url=request.url,
        action_data=f"contractor_id:{contractor_id},business_name:{profile.business_name}"
    )
    
    return render_template("customer/contractor_profile.html", 
                         contractor=contractor, 
                         profile=profile)

@app.route("/customer/contact-contractor/<int:contractor_id>", methods=["POST"])
@login_required
def contact_contractor(contractor_id):
    """Contact a contractor through the platform"""
    if current_user.account_type != "customer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    contractor = User.query.get_or_404(contractor_id)
    profile = contractor.contractor_profile
    
    # Get message from form
    message = request.form.get("message", "")
    customer_phone = request.form.get("phone", "")
    
    # Send email to contractor
    subject = f"New Project Inquiry from {current_user.email}"
    body = f"""
    You have received a new project inquiry through LaborLooker!
    
    Customer: {current_user.email}
    Phone: {customer_phone}
    
    Message:
    {message}
    
    Please respond to this customer directly at {current_user.email}
    
    Best regards,
    LaborLooker Team
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>New Project Inquiry</h2>
        <p><strong>Customer:</strong> {current_user.email}</p>
        <p><strong>Phone:</strong> {customer_phone}</p>
        
        <h3>Message:</h3>
        <p>{message}</p>
        
        <p>Please respond to this customer directly at <a href="mailto:{current_user.email}">{current_user.email}</a></p>
        
        <hr>
        <p><small>LaborLooker Team</small></p>
    </body>
    </html>
    """
    
    if send_email(contractor.email, subject, body, html_body):
        # Track successful contact
        track_user_activity(
            user_id=current_user.id,
            action_type="contractor_contact",
            page_url=request.url,
            action_data=f"contractor_id:{contractor_id},success:true"
        )
        flash(f"Your message has been sent to {profile.business_name}!", "success")
    else:
        flash("Failed to send message. Please try again.", "error")
    
    return redirect(url_for("view_contractor_profile", contractor_id=contractor_id))

# --- Developer Routes ---
# Note: billing_overview route already exists further down

# --- Original Dashboard (for backward compatibility) ---
# --- About Us Route ---

@app.route("/about-us")
def about_us():
    """About Us page with company and founder information"""
    return render_template("about_us.html")


@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def client_new():
    if request.method == "POST":
        industry = request.form.get("industry") 
        if industry == "":  # Handle empty select value
            industry = None
        
        billing_plan = request.form.get("billing_plan", "commission_only")
        
        # Set commission rate and subscription based on plan
        if billing_plan == "commission_only":
            commission_rate = 10.0
            monthly_subscription = 0.0
        else:  # subscription_plus_commission
            commission_rate = 5.0
            monthly_subscription = 30.0
            
        business_name = request.form["name"]
        
        c = Client(
            name=business_name,  # type: ignore
            business_name=business_name,  # type: ignore
            contact_name="",  # type: ignore
            email="",  # type: ignore
            phone="",  # type: ignore
            industry=industry,  # type: ignore
            website=request.form.get("website"),  # type: ignore
            notes=request.form.get("notes"),  # type: ignore
            billing_plan=billing_plan,  # type: ignore
            commission_rate=commission_rate,  # type: ignore
            monthly_subscription=monthly_subscription,  # type: ignore
        )
        db.session.add(c)
        db.session.commit()
        flash(f"Client '{c.name}' created successfully with {billing_plan.replace('_', ' ').title()} plan! Now upload their customer contact list.", "success")
        return redirect(url_for("contacts_upload", client_id=c.id))
    return render_template("client_new.html")


@app.route("/contacts/upload/<int:client_id>", methods=["GET", "POST"])
@login_required
def contacts_upload(client_id: int):
    client = Client.query.get_or_404(client_id)
    if request.method == "POST":
        file = request.files.get("csv")
        if not file:
            flash("Please choose a CSV file", "error")
            return redirect(request.url)
        
        if not HAS_PANDAS:
            flash("CSV upload feature not available - pandas library not installed", "error")
            return redirect(request.url)
        
        df = pd.read_csv(file.stream)
        cols = {c.lower(): c for c in df.columns}
        for _, row in df.iterrows():
            contact = Contact(
                client_id=client.id,  # type: ignore
                name=str(row.get(cols.get("name"), "")).strip() if cols.get("name") else None,  # type: ignore
                email=str(row.get(cols.get("email"), "")).strip() if cols.get("email") else None,  # type: ignore
                phone=str(row.get(cols.get("phone"), "")).strip() if cols.get("phone") else None,  # type: ignore
            )
            db.session.add(contact)
        db.session.commit()
        flash(f"Uploaded {len(df)} contacts for {client.name}", "success")
        return redirect(url_for("dashboard"))
    return render_template("contacts_upload.html", client=client)


# === ADVERTISING MARKETPLACE ROUTES ===

@app.route("/advertising/marketplace")
@login_required
def advertising_marketplace():
    """Browse all advertising professionals by category"""
    category = request.args.get('category', 'all')
    location = request.args.get('location', '')
    budget_min = request.args.get('budget_min', 0, type=int)
    budget_max = request.args.get('budget_max', 0, type=int)
    rating_min = request.args.get('rating_min', 0, type=float)
    
    query = AdvertisingProfessional.query.filter_by(is_active=True)
    
    # Filter by category
    if category != 'all':
        query = query.filter_by(specialization=category)
    
    # Filter by location if specified
    if location:
        query = query.filter(AdvertisingProfessional.service_area_cities.contains(location))
    
    # Filter by rating
    if rating_min > 0:
        query = query.filter(AdvertisingProfessional.average_rating >= rating_min)
    
    # Filter by budget (use base hourly rate)
    if budget_min > 0:
        query = query.filter(AdvertisingProfessional.base_hourly_rate >= budget_min)
    if budget_max > 0:
        query = query.filter(AdvertisingProfessional.base_hourly_rate <= budget_max)
    
    professionals = query.order_by(AdvertisingProfessional.average_rating.desc()).all()
    
    # Get category counts for sidebar
    category_counts = {
        'all': AdvertisingProfessional.query.filter_by(is_active=True).count(),
        'physical_media': AdvertisingProfessional.query.filter_by(is_active=True, specialization='physical_media').count(),
        'web_advertising': AdvertisingProfessional.query.filter_by(is_active=True, specialization='web_advertising').count(),
        'marketing_management': AdvertisingProfessional.query.filter_by(is_active=True, specialization='marketing_management').count()
    }
    
    return render_template("advertising/marketplace.html", 
                         professionals=professionals, 
                         category=category,
                         category_counts=category_counts,
                         location=location,
                         budget_min=budget_min,
                         budget_max=budget_max,
                         rating_min=rating_min)

@app.route("/advertising/professional/<int:professional_id>")
@login_required
def advertising_professional_profile(professional_id):
    """View detailed profile of an advertising professional"""
    professional = AdvertisingProfessional.query.get_or_404(professional_id)
    
    # Get specialized services based on type
    physical_services = None
    web_services = None
    marketing_services = None
    
    if professional.specialization == 'physical_media':
        physical_services = PhysicalMediaProvider.query.filter_by(advertising_professional_id=professional_id).first()
    elif professional.specialization == 'web_advertising':
        web_services = WebAdvertisingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
    elif professional.specialization == 'marketing_management':
        marketing_services = MarketingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
    
    # Get recent work orders and ratings
    recent_work = AdvertisingWorkOrder.query.filter_by(
        professional_id=professional_id,
        status='completed'
    ).order_by(AdvertisingWorkOrder.actual_completion_date.desc()).limit(5).all()
    
    return render_template("advertising/professional_profile.html", 
                         professional=professional,
                         physical_services=physical_services,
                         web_services=web_services,
                         marketing_services=marketing_services,
                         recent_work=recent_work)

@app.route("/advertising/campaign/new", methods=["GET", "POST"])
@login_required
def new_advertising_campaign():
    """Create a new advertising campaign request"""
    if request.method == "POST":
        try:
            # Basic campaign info
            campaign_name = request.form.get("campaign_name")
            campaign_description = request.form.get("campaign_description")
            campaign_budget_cents = int(float(request.form.get("campaign_budget", 0)) * 100)
            campaign_duration_days = int(request.form.get("campaign_duration_days", 30))
            
            # Timeline
            desired_start_date = None
            if request.form.get("desired_start_date"):
                desired_start_date = datetime.strptime(request.form.get("desired_start_date"), "%Y-%m-%d")
            
            deadline = None
            if request.form.get("deadline"):
                deadline = datetime.strptime(request.form.get("deadline"), "%Y-%m-%d")
            
            is_rush_order = request.form.get("is_rush_order") == "on"
            
            # Selected professionals and services
            selected_professionals = request.form.getlist("selected_professionals")
            physical_media_orders = {}
            web_advertising_requirements = {}
            marketing_management_scope = {}
            
            # Process physical media orders
            for key, value in request.form.items():
                if key.startswith("physical_"):
                    item_type = key.replace("physical_", "")
                    if value and int(value) > 0:
                        physical_media_orders[item_type] = int(value)
            
            # Process web advertising requirements
            for key, value in request.form.items():
                if key.startswith("web_"):
                    requirement = key.replace("web_", "")
                    if value:
                        web_advertising_requirements[requirement] = value
            
            # Process marketing management scope
            for key, value in request.form.items():
                if key.startswith("marketing_"):
                    scope_item = key.replace("marketing_", "")
                    if value:
                        marketing_management_scope[scope_item] = value
            
            # Calculate total cost and platform commission
            total_cost_cents = 0
            
            # Add physical media costs
            for professional_id in selected_professionals:
                professional = AdvertisingProfessional.query.get(professional_id)
                if professional and professional.specialization == 'physical_media':
                    physical_services = PhysicalMediaProvider.query.filter_by(advertising_professional_id=professional_id).first()
                    if physical_services:
                        for item_type, quantity in physical_media_orders.items():
                            price_field = f"{item_type}_price_cents"
                            if hasattr(physical_services, price_field):
                                unit_price = getattr(physical_services, price_field)
                                total_cost_cents += unit_price * quantity
            
            # Add web advertising costs (base setup + management)
            for professional_id in selected_professionals:
                professional = AdvertisingProfessional.query.get(professional_id)
                if professional and professional.specialization == 'web_advertising':
                    web_services = WebAdvertisingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
                    if web_services:
                        total_cost_cents += web_services.setup_fee_cents
                        monthly_fee = web_services.monthly_management_fee_cents
                        months = max(1, campaign_duration_days // 30)
                        total_cost_cents += monthly_fee * months
            
            # Add marketing management costs
            for professional_id in selected_professionals:
                professional = AdvertisingProfessional.query.get(professional_id)
                if professional and professional.specialization == 'marketing_management':
                    marketing_services = MarketingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
                    if marketing_services:
                        if marketing_services.requires_retainer:
                            total_cost_cents += marketing_services.retainer_amount_cents
                        monthly_fee = marketing_services.campaign_management_fee_cents
                        months = max(1, campaign_duration_days // 30)
                        total_cost_cents += monthly_fee * months
            
            # Calculate 10% platform commission
            platform_commission_cents = int(total_cost_cents * 0.10)
            
            # Create campaign request
            campaign_request = AdvertisingCampaignRequest(
                client_id=current_user.id,
                campaign_name=campaign_name,
                campaign_description=campaign_description,
                campaign_budget_cents=campaign_budget_cents,
                campaign_duration_days=campaign_duration_days,
                desired_start_date=desired_start_date,
                deadline=deadline,
                is_rush_order=is_rush_order,
                selected_professionals=json.dumps(selected_professionals),
                physical_media_orders=json.dumps(physical_media_orders),
                web_advertising_requirements=json.dumps(web_advertising_requirements),
                marketing_management_scope=json.dumps(marketing_management_scope),
                total_cost_cents=total_cost_cents,
                platform_commission_cents=platform_commission_cents,
                status="pending"
            )
            
            db.session.add(campaign_request)
            db.session.flush()  # Get the ID
            
            # Create individual work orders for each selected professional
            for professional_id in selected_professionals:
                professional = AdvertisingProfessional.query.get(professional_id)
                if professional:
                    work_description = f"Campaign: {campaign_name}"
                    deliverables = []
                    quoted_price_cents = 0
                    
                    if professional.specialization == 'physical_media':
                        deliverables.extend([f"{qty}x {item}" for item, qty in physical_media_orders.items()])
                        # Calculate price for this professional's work
                        physical_services = PhysicalMediaProvider.query.filter_by(advertising_professional_id=professional_id).first()
                        if physical_services:
                            for item_type, quantity in physical_media_orders.items():
                                price_field = f"{item_type}_price_cents"
                                if hasattr(physical_services, price_field):
                                    unit_price = getattr(physical_services, price_field)
                                    quoted_price_cents += unit_price * quantity
                    
                    elif professional.specialization == 'web_advertising':
                        deliverables.extend([f"{key}: {value}" for key, value in web_advertising_requirements.items()])
                        web_services = WebAdvertisingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
                        if web_services:
                            quoted_price_cents += web_services.setup_fee_cents
                            monthly_fee = web_services.monthly_management_fee_cents
                            months = max(1, campaign_duration_days // 30)
                            quoted_price_cents += monthly_fee * months
                    
                    elif professional.specialization == 'marketing_management':
                        deliverables.extend([f"{key}: {value}" for key, value in marketing_management_scope.items()])
                        marketing_services = MarketingProfessional.query.filter_by(advertising_professional_id=professional_id).first()
                        if marketing_services:
                            if marketing_services.requires_retainer:
                                quoted_price_cents += marketing_services.retainer_amount_cents
                            monthly_fee = marketing_services.campaign_management_fee_cents
                            months = max(1, campaign_duration_days // 30)
                            quoted_price_cents += monthly_fee * months
                    
                    # Calculate commission for this work order
                    work_order_commission = int(quoted_price_cents * 0.10)
                    
                    work_order = AdvertisingWorkOrder(
                        campaign_request_id=campaign_request.id,
                        professional_id=professional_id,
                        work_type=professional.specialization,
                        work_description=work_description,
                        deliverables=json.dumps(deliverables),
                        quoted_price_cents=quoted_price_cents,
                        platform_commission_cents=work_order_commission,
                        estimated_completion_date=deadline,
                        deadline=deadline,
                        status="sent"
                    )
                    
                    db.session.add(work_order)
            
            db.session.commit()
            flash("Campaign request created successfully! Work orders have been sent to selected professionals.", "success")
            return redirect(url_for("advertising_campaign_dashboard"))
        
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating campaign: {str(e)}", "error")
    
    # GET request - show form
    physical_professionals = AdvertisingProfessional.query.filter_by(
        is_active=True, 
        specialization='physical_media'
    ).order_by(AdvertisingProfessional.average_rating.desc()).all()
    
    web_professionals = AdvertisingProfessional.query.filter_by(
        is_active=True, 
        specialization='web_advertising'
    ).order_by(AdvertisingProfessional.average_rating.desc()).all()
    
    marketing_professionals = AdvertisingProfessional.query.filter_by(
        is_active=True, 
        specialization='marketing_management'
    ).order_by(AdvertisingProfessional.average_rating.desc()).all()
    
    return render_template("advertising/campaign_new.html",
                         physical_professionals=physical_professionals,
                         web_professionals=web_professionals,
                         marketing_professionals=marketing_professionals)

@app.route("/advertising/campaigns")
@login_required
def advertising_campaign_dashboard():
    """View all advertising campaigns for current user"""
    campaigns = AdvertisingCampaignRequest.query.filter_by(
        client_id=current_user.id
    ).order_by(AdvertisingCampaignRequest.created_at.desc()).all()
    
    return render_template("advertising/campaigns_dashboard.html", campaigns=campaigns)

@app.route("/advertising/campaign/<int:campaign_id>")
@login_required
def advertising_campaign_detail(campaign_id):
    """View detailed campaign information and work orders"""
    campaign = AdvertisingCampaignRequest.query.get_or_404(campaign_id)
    
    # Verify ownership
    if campaign.client_id != current_user.id:
        flash("Access denied", "error")
        return redirect(url_for("advertising_campaign_dashboard"))
    
    # Get all work orders for this campaign
    work_orders = AdvertisingWorkOrder.query.filter_by(
        campaign_request_id=campaign_id
    ).all()
    
    return render_template("advertising/campaign_detail.html", 
                         campaign=campaign, 
                         work_orders=work_orders)

@app.route("/advertising/work-order/<int:work_order_id>/update", methods=["POST"])
@login_required
def update_work_order_status(work_order_id):
    """Update work order status (for professionals)"""
    work_order = AdvertisingWorkOrder.query.get_or_404(work_order_id)
    
    # Verify this user is the assigned professional
    if work_order.professional.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403
    
    new_status = request.json.get("status")
    progress_percentage = request.json.get("progress_percentage", work_order.progress_percentage)
    progress_notes = request.json.get("progress_notes", "")
    
    try:
        work_order.status = new_status
        work_order.progress_percentage = progress_percentage
        work_order.progress_notes = progress_notes
        
        if new_status == "accepted":
            work_order.accepted_at = datetime.utcnow()
        elif new_status == "declined":
            work_order.declined_at = datetime.utcnow()
            work_order.decline_reason = request.json.get("decline_reason", "")
        elif new_status == "completed":
            work_order.actual_completion_date = datetime.utcnow()
            work_order.delivered_on_time = work_order.actual_completion_date <= work_order.deadline
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Work order updated successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/advertising/professional/dashboard")
@login_required
def advertising_professional_dashboard():
    """Dashboard for advertising professionals to manage work orders"""
    
    # Check if current user is an advertising professional
    professional = AdvertisingProfessional.query.filter_by(user_id=current_user.id).first()
    if not professional:
        flash("You need to register as an advertising professional first.", "info")
        return redirect(url_for("register_advertising_professional"))
    
    # Get work orders for this professional
    pending_orders = AdvertisingWorkOrder.query.filter_by(
        professional_id=professional.id,
        status='sent'
    ).order_by(AdvertisingWorkOrder.created_at.desc()).all()
    
    active_orders = AdvertisingWorkOrder.query.filter_by(
        professional_id=professional.id,
        status='in_progress'
    ).order_by(AdvertisingWorkOrder.deadline.asc()).all()
    
    completed_orders = AdvertisingWorkOrder.query.filter_by(
        professional_id=professional.id,
        status='completed'
    ).order_by(AdvertisingWorkOrder.actual_completion_date.desc()).limit(10).all()
    
    # Calculate earnings
    total_earnings = db.session.query(db.func.sum(AdvertisingWorkOrder.final_price_cents)).filter_by(
        professional_id=professional.id,
        status='completed'
    ).scalar() or 0
    
    platform_commissions = db.session.query(db.func.sum(AdvertisingWorkOrder.platform_commission_cents)).filter_by(
        professional_id=professional.id,
        status='completed'
    ).scalar() or 0
    
    net_earnings = total_earnings - platform_commissions
    
    return render_template("advertising/professional_dashboard.html",
                         professional=professional,
                         pending_orders=pending_orders,
                         active_orders=active_orders,
                         completed_orders=completed_orders,
                         total_earnings=total_earnings,
                         platform_commissions=platform_commissions,
                         net_earnings=net_earnings)

@app.route("/advertising/professional/register", methods=["GET", "POST"])
@login_required
def register_advertising_professional():
    """Register as an advertising professional"""
    
    # Check if already registered
    existing = AdvertisingProfessional.query.filter_by(user_id=current_user.id).first()
    if existing:
        flash("You are already registered as an advertising professional.", "info")
        return redirect(url_for("advertising_professional_dashboard"))
    
    if request.method == "POST":
        try:
            # Basic information
            business_name = request.form.get("business_name")
            business_description = request.form.get("business_description")
            specialization = request.form.get("specialization")
            experience_years = int(request.form.get("experience_years", 0))
            
            # Service area
            service_area_cities = request.form.getlist("service_area_cities")
            service_area_radius = int(request.form.get("service_area_radius", 25))
            remote_services_available = request.form.get("remote_services_available") == "on"
            
            # Pricing
            base_hourly_rate = float(request.form.get("base_hourly_rate", 0))
            project_minimum = float(request.form.get("project_minimum", 0))
            
            # Portfolio
            portfolio_url = request.form.get("portfolio_url", "")
            years_in_business = int(request.form.get("years_in_business", 0))
            team_size = int(request.form.get("team_size", 1))
            
            # Create advertising professional record
            professional = AdvertisingProfessional(
                user_id=current_user.id,
                business_name=business_name,
                business_description=business_description,
                specialization=specialization,
                experience_years=experience_years,
                service_area_cities=json.dumps(service_area_cities),
                service_area_radius=service_area_radius,
                remote_services_available=remote_services_available,
                base_hourly_rate=base_hourly_rate,
                project_minimum=project_minimum,
                portfolio_url=portfolio_url,
                years_in_business=years_in_business,
                team_size=team_size,
                is_active=True,
                is_verified=False
            )
            
            db.session.add(professional)
            db.session.flush()  # Get the ID
            
            # Create specialized service record based on type
            if specialization == "physical_media":
                # Physical media provider setup
                physical_services = PhysicalMediaProvider(
                    advertising_professional_id=professional.id,
                    offers_stickers=request.form.get("offers_stickers") == "on",
                    offers_flyers=request.form.get("offers_flyers") == "on",
                    offers_business_cards=request.form.get("offers_business_cards") == "on",
                    offers_brochures=request.form.get("offers_brochures") == "on",
                    offers_banners=request.form.get("offers_banners") == "on",
                    offers_yard_signs=request.form.get("offers_yard_signs") == "on",
                    offers_vehicle_wraps=request.form.get("offers_vehicle_wraps") == "on",
                    offers_promotional_items=request.form.get("offers_promotional_items") == "on",
                    offers_apparel=request.form.get("offers_apparel") == "on",
                    design_services_included=request.form.get("design_services_included") == "on",
                    local_delivery_available=request.form.get("local_delivery_available") == "on",
                    shipping_available=request.form.get("shipping_available") == "on"
                )
                db.session.add(physical_services)
            
            elif specialization == "web_advertising":
                # Web advertising professional setup
                web_services = WebAdvertisingProfessional(
                    advertising_professional_id=professional.id,
                    google_ads_certified=request.form.get("google_ads_certified") == "on",
                    facebook_ads_certified=request.form.get("facebook_ads_certified") == "on",
                    linkedin_ads_certified=request.form.get("linkedin_ads_certified") == "on",
                    microsoft_ads_certified=request.form.get("microsoft_ads_certified") == "on",
                    offers_search_ads=request.form.get("offers_search_ads") == "on",
                    offers_display_ads=request.form.get("offers_display_ads") == "on",
                    offers_social_media_ads=request.form.get("offers_social_media_ads") == "on",
                    offers_retargeting=request.form.get("offers_retargeting") == "on",
                    offers_landing_pages=request.form.get("offers_landing_pages") == "on",
                    setup_fee_cents=int(float(request.form.get("setup_fee", 500)) * 100),
                    monthly_management_fee_cents=int(float(request.form.get("monthly_management_fee", 1000)) * 100),
                    minimum_ad_spend_cents=int(float(request.form.get("minimum_ad_spend", 1000)) * 100),
                    specializes_in_lead_generation=request.form.get("specializes_in_lead_generation") == "on",
                    specializes_in_local_business=request.form.get("specializes_in_local_business") == "on",
                    provides_weekly_reports=request.form.get("provides_weekly_reports") == "on",
                    provides_monthly_reports=request.form.get("provides_monthly_reports") == "on"
                )
                db.session.add(web_services)
            
            elif specialization == "marketing_management":
                # Marketing professional setup
                marketing_services = MarketingProfessional(
                    advertising_professional_id=professional.id,
                    specializes_in_strategy=request.form.get("specializes_in_strategy") == "on",
                    specializes_in_branding=request.form.get("specializes_in_branding") == "on",
                    specializes_in_content_marketing=request.form.get("specializes_in_content_marketing") == "on",
                    specializes_in_email_marketing=request.form.get("specializes_in_email_marketing") == "on",
                    specializes_in_social_media=request.form.get("specializes_in_social_media") == "on",
                    offers_strategy_consultation=request.form.get("offers_strategy_consultation") == "on",
                    offers_campaign_management=request.form.get("offers_campaign_management") == "on",
                    offers_content_creation=request.form.get("offers_content_creation") == "on",
                    offers_brand_development=request.form.get("offers_brand_development") == "on",
                    campaign_management_fee_cents=int(float(request.form.get("campaign_management_fee", 2000)) * 100),
                    minimum_campaign_budget_cents=int(float(request.form.get("minimum_campaign_budget", 5000)) * 100),
                    requires_retainer=request.form.get("requires_retainer") == "on",
                    retainer_amount_cents=int(float(request.form.get("retainer_amount", 3000)) * 100),
                    experience_professional_services=request.form.get("experience_professional_services") == "on",
                    has_copywriting_team=request.form.get("has_copywriting_team") == "on",
                    has_data_analytics=request.form.get("has_data_analytics") == "on"
                )
                db.session.add(marketing_services)
            
            db.session.commit()
            flash("Successfully registered as an advertising professional! Your profile is pending verification.", "success")
            return redirect(url_for("advertising_professional_dashboard"))
        
        except Exception as e:
            db.session.rollback()
            flash(f"Error registering: {str(e)}", "error")
    
    return render_template("advertising/professional_register.html")

@app.route("/advertising/analytics")
@login_required
def advertising_analytics():
    """Analytics dashboard for advertising platform"""
    
    # Platform statistics
    total_professionals = AdvertisingProfessional.query.filter_by(is_active=True).count()
    total_campaigns = AdvertisingCampaignRequest.query.count()
    total_work_orders = AdvertisingWorkOrder.query.count()
    completed_work_orders = AdvertisingWorkOrder.query.filter_by(status='completed').count()
    
    # Revenue analytics
    total_revenue = db.session.query(db.func.sum(AdvertisingTransaction.amount_cents)).filter_by(
        transaction_type='payment',
        payment_status='completed'
    ).scalar() or 0
    
    total_commissions = db.session.query(db.func.sum(AdvertisingTransaction.platform_commission_cents)).filter_by(
        transaction_type='payment',
        payment_status='completed'
    ).scalar() or 0
    
    # Monthly trends (last 12 months)
    monthly_data = []
    for i in range(12):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        campaigns_count = AdvertisingCampaignRequest.query.filter(
            AdvertisingCampaignRequest.created_at >= month_start,
            AdvertisingCampaignRequest.created_at <= month_end
        ).count()
        
        revenue = db.session.query(db.func.sum(AdvertisingTransaction.amount_cents)).filter(
            AdvertisingTransaction.created_at >= month_start,
            AdvertisingTransaction.created_at <= month_end,
            AdvertisingTransaction.transaction_type == 'payment',
            AdvertisingTransaction.payment_status == 'completed'
        ).scalar() or 0
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'campaigns': campaigns_count,
            'revenue': revenue / 100  # Convert to dollars
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    return render_template("advertising/analytics.html",
                         total_professionals=total_professionals,
                         total_campaigns=total_campaigns,
                         total_work_orders=total_work_orders,
                         completed_work_orders=completed_work_orders,
                         total_revenue=total_revenue / 100,
                         total_commissions=total_commissions / 100,
                         monthly_data=monthly_data,
                         completion_rate=round((completed_work_orders / max(total_work_orders, 1)) * 100, 1))


@app.route("/campaigns/new", methods=["GET", "POST"])
@login_required
def campaign_new():
    if request.method == "POST":
        client_id = int(request.form["client_id"])
        name = request.form["name"]
        campaign_type = request.form.get("campaign_type", "referral")
        incentive = request.form.get("incentive")
        message = request.form.get("message")
        budget = float(request.form.get("budget", 0))
        
        campaign = Campaign(
            client_id=client_id, 
            name=name, 
            campaign_type=campaign_type,
            incentive=incentive, 
            message=message,
            budget=budget
        )  # type: ignore
        db.session.add(campaign)
        db.session.commit()

        contacts = Contact.query.filter_by(client_id=client_id).all()
        base_url = base_public_url()
        for ct in contacts:
            code = shortuuid.uuid()[:8]
            url = f"{base_url}/r/{code}"
            rl = ReferralLink(campaign_id=campaign.id, contact_id=ct.id, code=code, url=url)  # type: ignore
            db.session.add(rl)
            db.session.flush()
            fname = f"{campaign.id}_{ct.id}_{code}.png"
            generate_qr_png(url, fname)

        db.session.commit()
        flash(f'Campaign "{campaign.name}" created with {len(contacts)} referral links', "success")
        return redirect(url_for("campaign_detail", campaign_id=campaign.id))

    clients = Client.query.all()
    if not clients:
        flash("Create a client and upload contacts first.", "error")
    return render_template("campaign_new.html", clients=clients)


@app.route("/analytics")
def analytics():
    """Advanced analytics page to showcase business intelligence capabilities"""
    
    # Campaign performance metrics
    campaigns_with_stats = []
    for campaign in Campaign.query.all():
        links = ReferralLink.query.filter_by(campaign_id=campaign.id).all()
        total_clicks = sum(len(link.clicks) for link in links)
        total_leads = sum(len(link.leads) for link in links)
        
        # Calculate ROI if budget is set
        total_lead_value = sum(lead.estimated_value for link in links for lead in link.leads)
        roi = ((total_lead_value - campaign.budget) / campaign.budget * 100) if campaign.budget > 0 else 0
        
        campaigns_with_stats.append({
            'campaign': campaign,
            'total_clicks': total_clicks,
            'total_leads': total_leads,
            'conversion_rate': (total_leads / total_clicks * 100) if total_clicks > 0 else 0,
            'total_lead_value': total_lead_value,
            'roi': roi
        })
    
    # Client performance
    clients_with_stats = []
    for client in Client.query.all():
        client_campaigns = Campaign.query.filter_by(client_id=client.id).all()
        total_budget = sum(c.budget for c in client_campaigns)
        total_contacts = Contact.query.filter_by(client_id=client.id).count()
        
        clients_with_stats.append({
            'client': client,
            'total_campaigns': len(client_campaigns),
            'total_budget': total_budget,
            'total_contacts': total_contacts
        })
    
    return render_template(
        "analytics.html",
        campaigns_with_stats=campaigns_with_stats,
        clients_with_stats=clients_with_stats
    )


@app.route("/campaigns/<int:campaign_id>")
def campaign_detail(campaign_id: int):
    camp = Campaign.query.get_or_404(campaign_id)
    links = ReferralLink.query.filter_by(campaign_id=camp.id).all()
    rows = []
    total_clicks = 0
    total_leads = 0
    total_lead_value = 0
    
    for lnk in links:
        clicks_count = len(lnk.clicks)
        leads_count = len(lnk.leads)
        lead_value = sum(lead.estimated_value for lead in lnk.leads)
        
        total_clicks += clicks_count
        total_leads += leads_count
        total_lead_value += lead_value
        
        rows.append(
            {
                "link": lnk,
                "clicks": clicks_count,
                "leads": leads_count,
                "lead_value": lead_value,
                "qr_path": f"/static/qr/{camp.id}_{lnk.contact_id}_{lnk.code}.png",
            }
        )
    
    # Calculate campaign ROI
    roi = ((total_lead_value - camp.budget) / camp.budget * 100) if camp.budget > 0 else 0
    conversion_rate = (total_leads / total_clicks * 100) if total_clicks > 0 else 0
    
    return render_template(
        "campaign_detail.html", 
        camp=camp, 
        rows=rows,
        total_clicks=total_clicks,
        total_leads=total_leads,
        total_lead_value=total_lead_value,
        roi=roi,
        conversion_rate=conversion_rate
    )


@app.route("/campaigns/<int:campaign_id>/export")
def campaign_export(campaign_id: int):
    camp = Campaign.query.get_or_404(campaign_id)
    links = ReferralLink.query.filter_by(campaign_id=camp.id).all()

    rows = []
    for lnk in links:
        rows.append(
            {
                "contact_name": lnk.contact.name if lnk.contact else "",
                "contact_email": lnk.contact.email if lnk.contact else "",
                "contact_phone": lnk.contact.phone if lnk.contact else "",
                "referral_url": lnk.url,
                "qr_filename": f"{camp.id}_{lnk.contact_id}_{lnk.code}.png",
            }
        )

    if not HAS_PANDAS:
        flash("Export feature not available - pandas library not installed", "error")
        return redirect(url_for("dashboard"))
    
    df = pd.DataFrame(rows)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"campaign_{camp.id}_mail_merge.csv", df.to_csv(index=False).encode("utf-8"))
        for lnk in links:
            qr_filename = f"{camp.id}_{lnk.contact_id}_{lnk.code}.png"
            qr_path = os.path.join(QR_DIR, qr_filename)
            if os.path.exists(qr_path):
                zf.write(qr_path, arcname=os.path.join("qr", qr_filename))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"campaign_{camp.id}_assets.zip",
    )


@app.route("/stickers/<int:campaign_id>")
def sticker_sheet(campaign_id: int):
    camp = Campaign.query.get_or_404(campaign_id)
    links = ReferralLink.query.filter_by(campaign_id=camp.id).all()
    return render_template("sticker_sheet.html", camp=camp, links=links)


# --- Referral Flow ---
@app.route("/r/<code>")
def referral_redirect(code: str):
    lnk = ReferralLink.query.filter_by(code=code).first_or_404()
    db.session.add(Click(referral_id=lnk.id))  # type: ignore
    db.session.commit()
    return render_template("landing.html", link=lnk, client=lnk.campaign.client, camp=lnk.campaign)


@app.route("/lead", methods=["POST"])
def lead_submit():
    code = request.form["code"]
    lnk = ReferralLink.query.filter_by(code=code).first_or_404()
    estimated_value = float(request.form.get("estimated_value", 0))
    
    lead = Lead(
        referral_id=lnk.id,  # type: ignore
        name=request.form.get("name"),  # type: ignore
        email=request.form.get("email"),  # type: ignore
        phone=request.form.get("phone"),  # type: ignore
        notes=request.form.get("notes"),  # type: ignore
        estimated_value=estimated_value,  # type: ignore
    )
    db.session.add(lead)
    db.session.commit()
    flash("Thanks! Your info was received. We will reach out shortly.", "success")
    return redirect(url_for("referral_redirect", code=code))


@app.route("/prospects")
@login_required
def prospects_list():
    """List all prospective leads"""
    prospects = ProspectiveLead.query.order_by(ProspectiveLead.created_at.desc()).all()
    clients = Client.query.all()
    return render_template("prospects_list.html", prospects=prospects, clients=clients)


@app.route("/prospects/new", methods=["GET", "POST"])
@login_required
def prospect_new():
    """Add new prospective lead"""
    if request.method == "POST":
        prospect = ProspectiveLead(
            client_id=int(request.form["client_id"]),  # type: ignore
            name=request.form["name"],  # type: ignore
            email=request.form.get("email"),  # type: ignore
            phone=request.form.get("phone"),  # type: ignore
            address=request.form.get("address"),  # type: ignore
            source=request.form.get("source", "manual"),  # type: ignore
            status=request.form.get("status", "new"),  # type: ignore
            estimated_value=float(request.form.get("estimated_value", 0)),  # type: ignore
            notes=request.form.get("notes"),  # type: ignore
        )
        db.session.add(prospect)
        db.session.commit()
        flash(f"Prospect '{prospect.name}' added successfully!", "success")
        return redirect(url_for("prospects_list"))
    
    clients = Client.query.all()
    return render_template("prospect_new.html", clients=clients)


@app.route("/prospects/<int:prospect_id>/edit", methods=["GET", "POST"])
def prospect_edit(prospect_id: int):
    """Edit prospective lead"""
    prospect = ProspectiveLead.query.get_or_404(prospect_id)
    
    if request.method == "POST":
        prospect.name = request.form["name"]
        prospect.email = request.form.get("email")
        prospect.phone = request.form.get("phone")
        prospect.address = request.form.get("address")
        prospect.source = request.form.get("source")
        prospect.status = request.form.get("status")
        prospect.estimated_value = float(request.form.get("estimated_value", 0))
        prospect.notes = request.form.get("notes")
        if request.form.get("update_last_contact"):
            prospect.last_contact = datetime.utcnow()
        
        db.session.commit()
        flash(f"Prospect '{prospect.name}' updated successfully!", "success")
        return redirect(url_for("prospects_list"))
    
    clients = Client.query.all()
    return render_template("prospect_edit.html", prospect=prospect, clients=clients)


@app.route("/schedule")
@login_required
def schedule_list():
    """List all scheduled work"""
    from datetime import timedelta
    
    # Get upcoming work (next 30 days)
    thirty_days = datetime.utcnow() + timedelta(days=30)
    upcoming_work = ScheduledWork.query.filter(
        ScheduledWork.scheduled_date >= datetime.utcnow(),
        ScheduledWork.scheduled_date <= thirty_days,
        ScheduledWork.status.in_(["scheduled", "in_progress"])
    ).order_by(ScheduledWork.scheduled_date).all()
    
    # Get all work for overview
    all_work = ScheduledWork.query.order_by(ScheduledWork.scheduled_date.desc()).limit(50).all()
    
    return render_template("schedule_list.html", upcoming_work=upcoming_work, all_work=all_work)


@app.route("/schedule/new", methods=["GET", "POST"])
@login_required
def schedule_new():
    """Schedule new work/appointment"""
    if request.method == "POST":
        scheduled_work = ScheduledWork(
            client_id=int(request.form["client_id"]),  # type: ignore
            prospect_id=int(request.form["prospect_id"]) if request.form.get("prospect_id") else None,  # type: ignore
            contact_id=int(request.form["contact_id"]) if request.form.get("contact_id") else None,  # type: ignore
            title=request.form["title"],  # type: ignore
            description=request.form.get("description"),  # type: ignore
            scheduled_date=datetime.strptime(request.form["scheduled_date"], "%Y-%m-%dT%H:%M"),  # type: ignore
            estimated_hours=float(request.form.get("estimated_hours", 0)) if request.form.get("estimated_hours") else None,  # type: ignore
            estimated_value=float(request.form.get("estimated_value", 0)),  # type: ignore
            notes=request.form.get("notes"),  # type: ignore
        )
        db.session.add(scheduled_work)
        db.session.commit()
        flash(f"Work '{scheduled_work.title}' scheduled successfully!", "success")
        return redirect(url_for("schedule_list"))
    
    clients = Client.query.all()
    prospects = ProspectiveLead.query.filter_by(status="qualified").all()
    contacts = Contact.query.all()
    return render_template("schedule_new.html", clients=clients, prospects=prospects, contacts=contacts)


@app.route("/schedule/<int:work_id>/complete", methods=["POST"])
def schedule_complete(work_id: int):
    """Mark scheduled work as completed"""
    work = ScheduledWork.query.get_or_404(work_id)
    work.status = "completed"
    work.completed_at = datetime.utcnow()
    actual_value_str = request.form.get("actual_value", str(work.estimated_value or 0))
    work.actual_value = float(actual_value_str) if actual_value_str else 0.0
    work.notes = (work.notes or "") + f"\nCompleted: {request.form.get('completion_notes', '')}"
    
    # Calculate commission based on client's plan
    if work.actual_value > 0:
        commission_amount = work.actual_value * (work.client.commission_rate / 100)
        work.commission_charged = commission_amount
    
    db.session.commit()
    flash(f"Work '{work.title}' marked as completed! Commission: ${work.commission_charged:.2f} ({work.client.commission_rate}%)", "success")
    return redirect(url_for("schedule_list"))


@app.route("/billing")
def billing_overview():
    """Billing overview and revenue tracking"""
    clients = Client.query.all()
    
    # Calculate monthly recurring revenue
    subscription_mrr = sum(c.monthly_subscription for c in clients)
    
    # Calculate commission revenue for current month
    from datetime import date, timedelta
    today = date.today()
    first_day = date(today.year, today.month, 1)
    last_day = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)
    
    completed_work_this_month = ScheduledWork.query.filter(
        ScheduledWork.status == "completed",
        ScheduledWork.completed_at >= datetime.combine(first_day, datetime.min.time()),
        ScheduledWork.completed_at <= datetime.combine(last_day, datetime.max.time())
    ).all()
    
    commission_revenue = sum(work.commission_charged for work in completed_work_this_month)
    total_jobs_completed = len(completed_work_this_month)
    
    # Recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
    
    return render_template(
        "billing_overview.html",
        clients=clients,
        subscription_mrr=subscription_mrr,
        commission_revenue=commission_revenue,
        total_jobs_completed=total_jobs_completed,
        recent_invoices=recent_invoices,
        completed_work_this_month=completed_work_this_month
    )


@app.route("/billing/generate_invoices")
def generate_monthly_invoices():
    """Generate monthly invoices for all clients"""
    from datetime import date, timedelta
    import calendar
    
    today = date.today()
    # Previous month
    if today.month == 1:
        last_month = 12
        year = today.year - 1
    else:
        last_month = today.month - 1
        year = today.year
    
    first_day = date(year, last_month, 1)
    last_day = date(year, last_month, calendar.monthrange(year, last_month)[1])
    
    clients = Client.query.all()
    invoices_created = 0
    
    for client in clients:
        # Check if invoice already exists for this period
        existing_invoice = Invoice.query.filter(
            Invoice.client_id == client.id,
            Invoice.billing_period_start == datetime.combine(first_day, datetime.min.time()),
            Invoice.billing_period_end == datetime.combine(last_day, datetime.max.time())
        ).first()
        
        if existing_invoice:
            continue
        
        # Get completed work for this client in the billing period
        completed_work = ScheduledWork.query.filter(
            ScheduledWork.client_id == client.id,
            ScheduledWork.status == "completed",
            ScheduledWork.completed_at >= datetime.combine(first_day, datetime.min.time()),
            ScheduledWork.completed_at <= datetime.combine(last_day, datetime.max.time())
        ).all()
        
        commission_revenue = sum(work.actual_value for work in completed_work)
        commission_total = sum(work.commission_charged for work in completed_work)
        
        # Only create invoice if there's subscription fee or completed work
        if client.monthly_subscription > 0 or len(completed_work) > 0:
            invoice = Invoice(
                client_id=client.id,  # type: ignore
                billing_period_start=datetime.combine(first_day, datetime.min.time()),  # type: ignore
                billing_period_end=datetime.combine(last_day, datetime.max.time()),  # type: ignore
                subscription_fee=client.monthly_subscription,  # type: ignore
                commission_jobs=len(completed_work),  # type: ignore
                commission_revenue=commission_revenue,  # type: ignore
                commission_rate=client.commission_rate,  # type: ignore
                commission_total=commission_total,  # type: ignore
                total_amount=client.monthly_subscription + commission_total,  # type: ignore
                status="draft",  # type: ignore
            )
            db.session.add(invoice)
            invoices_created += 1
    
    db.session.commit()
    flash(f"Generated {invoices_created} invoices for {calendar.month_name[last_month]} {year}", "success")
    return redirect(url_for("billing_overview"))


@app.route("/clients/<int:client_id>/billing")
def client_billing_detail(client_id: int):
    """Detailed billing information for a specific client"""
    client = Client.query.get_or_404(client_id)
    
    # Get all invoices for this client
    invoices = Invoice.query.filter_by(client_id=client.id).order_by(Invoice.created_at.desc()).all()
    
    # Get completed work for current month
    from datetime import date, timedelta
    today = date.today()
    first_day = date(today.year, today.month, 1)
    last_day = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)
    
    current_month_work = ScheduledWork.query.filter(
        ScheduledWork.client_id == client.id,
        ScheduledWork.status == "completed",
        ScheduledWork.completed_at >= datetime.combine(first_day, datetime.min.time()),
        ScheduledWork.completed_at <= datetime.combine(last_day, datetime.max.time())
    ).all()
    
    # Calculate totals
    total_revenue = sum(work.actual_value for work in current_month_work)
    total_commission = sum(work.commission_charged for work in current_month_work)
    
    return render_template(
        "client_billing_detail.html",
        client=client,
        invoices=invoices,
        current_month_work=current_month_work,
        total_revenue=total_revenue,
        total_commission=total_commission
    )


@app.route("/guide")
def guide():
    """User guide and instructions"""
    return render_template("guide.html")


@app.route("/demo/clear")
def clear_all_data():
    """Clear all data from the database"""
    try:
        # Delete in correct order to avoid foreign key constraints
        ScheduledWork.query.delete()
        ProspectiveLead.query.delete()
        Lead.query.delete()
        Click.query.delete()
        ReferralLink.query.delete()
        Campaign.query.delete()
        Contact.query.delete()
        Client.query.delete()
        
        db.session.commit()
        
        # Also clear QR code files
        import glob
        qr_files = glob.glob(os.path.join(QR_DIR, "*.png"))
        for qr_file in qr_files:
            try:
                os.remove(qr_file)
            except OSError:
                pass  # Ignore if file doesn't exist or can't be deleted
        
        flash("All data cleared successfully! You can now add your real client data.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing data: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))


@app.route("/demo/populate")
def populate_demo_data():
    """Populate sample data for demo purposes"""
    
    # Create sample clients
    hvac_client = Client(
        name="Elite HVAC Services",  # type: ignore
        industry="HVAC",  # type: ignore
        website="https://elitehvac.com",  # type: ignore
        notes="Local HVAC company serving residential and commercial customers"  # type: ignore
    )
    
    plumbing_client = Client(
        name="Premier Plumbing Co",  # type: ignore
        industry="Plumbing",  # type: ignore
        website="https://premierplumbing.com",  # type: ignore
        notes="Full-service plumbing contractor"  # type: ignore
    )
    
    restaurant_client = Client(
        name="Tony's Italian Kitchen",  # type: ignore
        industry="Restaurant",  # type: ignore
        website="https://tonysitalian.com",  # type: ignore
        notes="Family-owned Italian restaurant"  # type: ignore
    )
    
    db.session.add_all([hvac_client, plumbing_client, restaurant_client])
    db.session.commit()
    
    # Create sample contacts for HVAC client
    hvac_contacts = [
        Contact(client_id=hvac_client.id, name="John Smith", email="john@email.com", phone="555-0101"),  # type: ignore
        Contact(client_id=hvac_client.id, name="Sarah Johnson", email="sarah@email.com", phone="555-0102"),  # type: ignore
        Contact(client_id=hvac_client.id, name="Mike Davis", email="mike@email.com", phone="555-0103"),  # type: ignore
        Contact(client_id=hvac_client.id, name="Lisa Wilson", email="lisa@email.com", phone="555-0104"),  # type: ignore
        Contact(client_id=hvac_client.id, name="Tom Brown", email="tom@email.com", phone="555-0105"),  # type: ignore
    ]
    
    # Create sample contacts for other clients
    plumbing_contacts = [
        Contact(client_id=plumbing_client.id, name="Anna Garcia", email="anna@email.com", phone="555-0201"),  # type: ignore
        Contact(client_id=plumbing_client.id, name="David Miller", email="david@email.com", phone="555-0202"),  # type: ignore
        Contact(client_id=plumbing_client.id, name="Emma Taylor", email="emma@email.com", phone="555-0203"),  # type: ignore
    ]
    
    restaurant_contacts = [
        Contact(client_id=restaurant_client.id, name="Carlos Rodriguez", email="carlos@email.com", phone="555-0301"),  # type: ignore
        Contact(client_id=restaurant_client.id, name="Jennifer Lee", email="jen@email.com", phone="555-0302"),  # type: ignore
    ]
    
    db.session.add_all(hvac_contacts + plumbing_contacts + restaurant_contacts)
    db.session.commit()
    
    # Create sample campaigns
    hvac_campaign = Campaign(
        client_id=hvac_client.id,  # type: ignore
        name="Winter HVAC Referral Campaign",  # type: ignore
        campaign_type="referral",  # type: ignore
        incentive="$100 gift card for successful HVAC referral",  # type: ignore
        message="Know someone who needs heating or cooling services? Refer them and get $100!",  # type: ignore
        budget=2000.0  # type: ignore
    )
    
    plumbing_campaign = Campaign(
        client_id=plumbing_client.id,  # type: ignore
        name="Emergency Plumbing Sticker Campaign",  # type: ignore
        campaign_type="sticker",  # type: ignore
        incentive="20% off next service for referrals",  # type: ignore
        message="Emergency plumbing? Scan for instant service!",  # type: ignore
        budget=500.0  # type: ignore
    )
    
    restaurant_campaign = Campaign(
        client_id=restaurant_client.id,  # type: ignore
        name="Social Media Food Campaign",  # type: ignore
        campaign_type="media",  # type: ignore
        incentive="Free appetizer for new customers",  # type: ignore
        message="Try our authentic Italian cuisine! Show this for a free appetizer.",  # type: ignore
        budget=800.0  # type: ignore
    )
    
    db.session.add_all([hvac_campaign, plumbing_campaign, restaurant_campaign])
    db.session.commit()
    
    # Create referral links for campaigns
    base_url = base_public_url()
    
    # HVAC campaign links
    for contact in hvac_contacts:
        code = shortuuid.uuid()[:8]
        url = f"{base_url}/r/{code}"
        rl = ReferralLink(campaign_id=hvac_campaign.id, contact_id=contact.id, code=code, url=url)  # type: ignore
        db.session.add(rl)
        db.session.flush()
        fname = f"{hvac_campaign.id}_{contact.id}_{code}.png"
        generate_qr_png(url, fname)
    
    # Add some sample clicks and leads for demo
    db.session.commit()
    
    # Add sample clicks and leads
    hvac_links = ReferralLink.query.filter_by(campaign_id=hvac_campaign.id).all()
    for i, link in enumerate(hvac_links[:3]):
        # Add clicks
        for _ in range(i + 2):
            click = Click(referral_id=link.id)  # type: ignore
            db.session.add(click)
        
        # Add leads
        if i < 2:
            lead = Lead(
                referral_id=link.id,  # type: ignore
                name=f"Lead Customer {i+1}",  # type: ignore
                email=f"lead{i+1}@email.com",  # type: ignore
                phone=f"555-040{i+1}",  # type: ignore
                notes="Interested in HVAC service quote",  # type: ignore
                estimated_value=2500.0 + (i * 500),  # type: ignore
                status="qualified"  # type: ignore
            )
            db.session.add(lead)
    
    # Add sample prospects (manual leads)
    sample_prospects = [
        ProspectiveLead(
            client_id=hvac_client.id,  # type: ignore
            name="Robert Williams",  # type: ignore
            email="robert@email.com",  # type: ignore
            phone="555-0501",  # type: ignore
            address="456 Oak Street, Springfield",  # type: ignore
            source="phone",  # type: ignore
            status="new",  # type: ignore
            estimated_value=3500.0,  # type: ignore
            notes="Called about furnace replacement"  # type: ignore
        ),
        ProspectiveLead(
            client_id=hvac_client.id,  # type: ignore
            name="Jessica Miller",  # type: ignore
            email="jessica@email.com",  # type: ignore
            phone="555-0502",  # type: ignore
            address="789 Pine Avenue, Springfield",  # type: ignore
            source="website",  # type: ignore
            status="qualified",  # type: ignore
            estimated_value=2800.0,  # type: ignore
            notes="Website inquiry for AC installation"  # type: ignore
        ),
        ProspectiveLead(
            client_id=plumbing_client.id,  # type: ignore
            name="Mark Thompson",  # type: ignore
            email="mark@email.com",  # type: ignore
            phone="555-0503",  # type: ignore
            address="321 Elm Street, Springfield",  # type: ignore
            source="referral",  # type: ignore
            status="contacted",  # type: ignore
            estimated_value=1200.0,  # type: ignore
            notes="Referred by existing customer for bathroom remodel"  # type: ignore
        ),
    ]
    
    db.session.add_all(sample_prospects)
    db.session.commit()
    
    # Add sample scheduled work
    from datetime import timedelta
    
    sample_work = [
        ScheduledWork(
            client_id=hvac_client.id,  # type: ignore
            prospect_id=sample_prospects[1].id,  # type: ignore
            title="AC Installation Consultation",  # type: ignore
            description="Site visit for central air conditioning system installation",  # type: ignore
            scheduled_date=datetime.utcnow() + timedelta(days=2, hours=10),  # type: ignore
            estimated_hours=2.0,  # type: ignore
            estimated_value=2800.0,  # type: ignore
            notes="Customer wants energy-efficient system"  # type: ignore
        ),
        ScheduledWork(
            client_id=hvac_client.id,  # type: ignore
            contact_id=hvac_contacts[0].id,  # type: ignore
            title="Annual HVAC Maintenance",  # type: ignore
            description="Routine maintenance check for existing customer",  # type: ignore
            scheduled_date=datetime.utcnow() + timedelta(days=5, hours=14),  # type: ignore
            estimated_hours=1.5,  # type: ignore
            estimated_value=250.0,  # type: ignore
            notes="Regular maintenance customer"  # type: ignore
        ),
        ScheduledWork(
            client_id=plumbing_client.id,  # type: ignore
            prospect_id=sample_prospects[2].id,  # type: ignore
            title="Bathroom Remodel Quote",  # type: ignore
            description="Assessment and quote for full bathroom renovation",  # type: ignore
            scheduled_date=datetime.utcnow() + timedelta(days=1, hours=16),  # type: ignore
            estimated_hours=1.0,  # type: ignore
            estimated_value=1200.0,  # type: ignore
            notes="Referred customer - priority scheduling"  # type: ignore
        ),
    ]
    
    db.session.add_all(sample_work)
    db.session.commit()
    
    flash("Demo data populated successfully! You now have sample clients, campaigns, and tracking data.", "success")
    return redirect(url_for("dashboard"))


# --- Rating System Routes ---
@app.route("/rate-user/<int:user_id>/<int:work_request_id>", methods=["GET", "POST"])
@login_required
def rate_user(user_id, work_request_id):
    """Rate another user after job completion"""
    # Check if rating already exists
    existing_rating = UserRating.query.filter_by(
        rater_id=current_user.id,
        ratee_id=user_id,
        work_request_id=work_request_id
    ).first()
    
    if existing_rating:
        flash("You have already rated this user for this job.", "warning")
        return redirect(url_for("dashboard"))
    
    # Verify work request exists and user is involved
    work_request = WorkRequest.query.get_or_404(work_request_id)
    ratee = User.query.get_or_404(user_id)
    
    # Check if current user is authorized to rate (must be involved in the job)
    if (current_user.id != work_request.customer_id and 
        current_user.id != work_request.contractor_id):
        flash("You can only rate users from jobs you were involved in.", "error")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        rating_value = int(request.form.get("rating", 0))
        comment = request.form.get("comment", "").strip()
        
        if rating_value < 1 or rating_value > 5:
            flash("Rating must be between 1 and 5 stars.", "error")
            return redirect(request.url)
        
        # Determine transaction type
        transaction_type = "customer_experience"
        if current_user.account_type == "customer":
            if ratee.account_type == "contractor":
                transaction_type = "contractor_service"
            elif ratee.account_type == "developer":
                transaction_type = "networking_coordination"
        
        # Create new rating
        new_rating = UserRating()
        new_rating.rater_id = current_user.id
        new_rating.ratee_id = user_id
        new_rating.rating = rating_value
        new_rating.comment = comment
        new_rating.work_request_id = work_request_id
        new_rating.transaction_type = transaction_type
        
        db.session.add(new_rating)
        db.session.commit()
        
        flash(f"Thank you for rating {ratee.email}!", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("rate_user.html", 
                         ratee=ratee, 
                         work_request=work_request)

@app.route("/user-ratings/<int:user_id>")
def view_user_ratings(user_id):
    """View ratings for a specific user (public)"""
    user = User.query.get_or_404(user_id)
    rating_summary = get_user_rating_summary(user_id)
    
    return render_template("user_ratings.html", 
                         user=user, 
                         rating_summary=rating_summary)

@app.route("/my-ratings")
@login_required
def my_ratings():
    """View current user's ratings"""
    rating_summary = get_user_rating_summary(current_user.id)
    ratings_given = UserRating.query.filter_by(rater_id=current_user.id).order_by(
        UserRating.created_at.desc()
    ).all()
    
    return render_template("my_ratings.html", 
                         rating_summary=rating_summary,
                         ratings_given=ratings_given)


# --- Advertisement Campaign System ---
@app.route("/contractor/advertisement-campaigns")
@login_required
def contractor_advertisement_campaigns():
    """Manage advertisement campaigns"""
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    campaigns = AdvertisementCampaign.query.filter_by(
        contractor_id=current_user.id
    ).order_by(AdvertisementCampaign.created_at.desc()).all()
    
    return render_template("contractor/advertisement_campaigns.html", campaigns=campaigns)

@app.route("/contractor/advertisement-campaign/new", methods=["GET", "POST"])
@login_required
def new_advertisement_campaign():
    """Create new advertisement campaign"""
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        import json
        
        try:
            # Get form data
            campaign_name = request.form.get("campaign_name", "")
            campaign_type = request.form.get("campaign_type", "")
            description = request.form.get("description", "")
            target_audience = request.form.get("target_audience", "")
            budget = float(request.form.get("budget", 0))
            
            # Get selected geographic areas and service categories
            selected_areas = request.form.getlist("geographic_areas")
            selected_categories = request.form.getlist("service_categories")
            
            # Create new campaign
            new_campaign = AdvertisementCampaign()
            new_campaign.contractor_id = current_user.id
            new_campaign.campaign_name = campaign_name
            new_campaign.campaign_type = campaign_type
            new_campaign.description = description
            new_campaign.target_audience = target_audience
            new_campaign.budget = budget
            new_campaign.geographic_areas = json.dumps(selected_areas)
            new_campaign.service_categories = json.dumps(selected_categories)
            new_campaign.status = "pending"
            
            db.session.add(new_campaign)
            db.session.commit()
            
            flash("Advertisement campaign created! Waiting for advertiser connection.", "success")
            return redirect(url_for("contractor_advertisement_campaigns"))
        
        except Exception:
            flash("Error creating campaign. Please try again.", "error")
    
    return render_template("contractor/advertisement_campaign_new.html",
                         geographic_areas=GEOGRAPHIC_AREAS,
                         service_categories=SERVICE_CATEGORIES)

@app.route("/networking/labor-sourcing")
@login_required
def networking_labor_sourcing():
    """Labor sourcing tool for networking accounts with 5% commission"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get search parameters
    search_query = request.args.get("search", "")
    service_category = request.args.get("category", "")
    location = request.args.get("location", "")
    
    # Get all contractors using the new random selection
    all_contractors = get_random_contractors(service_category, location)
    
    # Apply additional search filters
    if search_query:
        all_contractors = [
            contractor for contractor in all_contractors
            if (search_query.lower() in contractor[1].business_name.lower() if contractor[1].business_name else False) or
               (search_query.lower() in contractor[1].contact_name.lower() if contractor[1].contact_name else False) or
               (search_query.lower() in contractor[0].email.lower())
        ]
    
    return render_template("networking/labor_sourcing.html",
                         contractors=all_contractors,
                         service_categories=SERVICE_CATEGORIES,
                         geographic_areas=GEOGRAPHIC_AREAS,
                         search_query=search_query,
                         service_category=service_category,
                         location=location,
                         boosted_count=0)  # No more boosts


# --- Advertisement Management System ---
@app.route("/admin/advertisements")
@login_required
def admin_advertisements():
    """Manage advertisement spaces (admin only)"""
    if current_user.account_type != "developer":  # Only developers can manage ads
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    ads = Advertisement.query.order_by(Advertisement.created_at.desc()).all()
    return render_template("admin/advertisements.html", ads=ads)

# --- End of Boost and Advertisement System ---

@app.route("/admin/advertisement/<int:ad_id>/approve")
@login_required
def approve_advertisement(ad_id):
    """Approve advertisement"""
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    ad = Advertisement.query.get_or_404(ad_id)
    ad.status = "active"
    ad.approved_at = datetime.utcnow()
    db.session.commit()
    
    flash(f"Advertisement for {ad.client_name} approved!", "success")
    return redirect(url_for("admin_advertisements"))

@app.route("/advertisement/click/<int:ad_id>")
def track_ad_click(ad_id):
    """Track advertisement click and redirect"""
    ad = Advertisement.query.get_or_404(ad_id)
    ad.clicks += 1
    db.session.commit()
    
    # Track activity
    track_user_activity(
        user_id=current_user.id if current_user.is_authenticated else None,
        action_type="ad_click",
        page_url=request.url,
        action_data=f"ad_id:{ad_id},client:{ad.client_name}"
    )
    
    return redirect(ad.ad_url or "https://laborlooker.com")

@app.route("/api/advertisements/<position>")
def get_advertisements(position):
    """API endpoint to get active advertisements for a position"""
    today = datetime.utcnow()
    ads = Advertisement.query.filter(
        Advertisement.ad_position == position,
        Advertisement.status == "active",
        Advertisement.start_date <= today,
        Advertisement.end_date >= today
    ).all()
    
    # Track impressions
    for ad in ads:
        ad.impressions += 1
    
    db.session.commit()
    
    return jsonify([{
        "id": ad.id,
        "content": ad.ad_content,
        "url": url_for("track_ad_click", ad_id=ad.id, _external=True),
        "client_name": ad.client_name
    } for ad in ads])


# --- Legal and Privacy Policy Routes ---
@app.route("/privacy-policy")
def privacy_policy():
    """Comprehensive privacy policy with legal disclaimers"""
    return render_template("legal/privacy_policy.html")

@app.route("/terms-of-service")
def terms_of_service():
    """Terms of service with contractor liability disclaimers"""
    return render_template("legal/terms_of_service.html")

@app.route("/privacy-policy-docusign")
def privacy_policy_docusign():
    """Privacy policy specifically for DocuSign integration"""
    return render_template("legal/privacy_policy_docusign.html")

@app.route("/terms-of-use-docusign")
def terms_of_use_docusign():
    """Terms of use specifically for DocuSign integration"""
    return render_template("legal/terms_of_use_docusign.html")

# --- Cookie Consent and Data Collection System ---

@app.route("/api/consent", methods=["POST"])
def handle_consent():
    """Handle user consent for data collection"""
    request_data = request.json or {}
    consent_given = request_data.get("consent", False)
    
    session['data_consent'] = consent_given
    session['consent_timestamp'] = datetime.utcnow().isoformat()
    
    # Track the consent decision
    track_user_activity(
        user_id=current_user.id if current_user.is_authenticated else None,
        action_type="consent_decision",
        page_url=request.headers.get('Referer', '/'),
        action_data=f"consent_given:{consent_given}"
    )
    
    return jsonify({"status": "success", "consent_recorded": consent_given})

@app.route("/api/track", methods=["POST"])
def track_activity():
    """Track user activity for analytics"""
    if not session.get('data_consent', False):
        return jsonify({"status": "no_consent"}), 403
    
    data = request.json or {}
    track_user_activity(
        user_id=current_user.id if current_user.is_authenticated else None,
        action_type=data.get("action_type", "unknown"),
        page_url=data.get("page_url", "/"),
        action_data=data.get("action_data", "")
    )
    
    return jsonify({"status": "tracked"})

@app.route("/data-management")
@login_required
def data_management():
    """User data management and deletion"""
    user_activities = UserDataCollection.query.filter_by(
        user_id=current_user.id
    ).order_by(UserDataCollection.timestamp.desc()).limit(100).all()
    
    return render_template("user/data_management.html", activities=user_activities)


# --- Messaging System Routes ---

@app.route("/inbox")
@login_required
def inbox():
    """User's message inbox"""
    page = request.args.get('page', 1, type=int)
    threads = get_user_inbox(current_user.id, page=page)
    
    return render_template("messaging/inbox.html", threads=threads)

@app.route("/send-message", methods=["GET", "POST"])
@login_required
def send_message_route():
    """Send a new message"""
    if request.method == "POST":
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        content = request.form.get('content')
        message_type = request.form.get('message_type', 'general')
        
        success, message = send_message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content=content,
            subject=subject,
            message_type=message_type
        )
        
        if success:
            flash("Message sent successfully!", "success")
        else:
            flash(f"Error sending message: {message}", "error")
        
        return redirect(url_for('inbox'))
    
    # Get potential recipients (all users except current user)
    recipients = User.query.filter(User.id != current_user.id, User.approved).all()
    return render_template("messaging/compose.html", recipients=recipients)

@app.route("/message/<int:message_id>/read", methods=["POST"])
@login_required
def mark_message_read(message_id):
    """Mark a message as read"""
    success = mark_message_as_read(message_id, current_user.id)
    return jsonify({"success": success})

@app.route("/message-thread/<int:thread_id>")
@login_required
def view_message_thread(thread_id):
    """View a complete message thread"""
    thread = MessageThread.query.get_or_404(thread_id)
    
    # Verify user is participant in thread
    if current_user.id not in [thread.participant_1_id, thread.participant_2_id]:
        flash("Access denied.", "error")
        return redirect(url_for('inbox'))
    
    # Get all messages in thread
    messages = Message.query.filter(
        ((Message.sender_id == thread.participant_1_id) & (Message.recipient_id == thread.participant_2_id)) |
        ((Message.sender_id == thread.participant_2_id) & (Message.recipient_id == thread.participant_1_id))
    ).order_by(Message.sent_at.asc()).all()
    
    # Mark unread messages as read
    for message in messages:
        if message.recipient_id == current_user.id and not message.is_read:
            message.is_read = True
            message.read_at = datetime.utcnow()
    
    db.session.commit()
    
    return render_template("messaging/thread.html", thread=thread, messages=messages)

# --- Network Management Routes ---

@app.route("/network/search-members")
@login_required
def search_network_members():
    """Search for potential network members"""
    if current_user.account_type != "networking":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))
    
    location = request.args.get('location', '')
    service_categories = request.args.getlist('service_categories')
    experience_level = request.args.get('experience_level', 'any')
    rating_threshold = request.args.get('rating_threshold', 4.0, type=float)
    
    potential_members = search_potential_network_members(
        network_owner_id=current_user.id,
        location=location,
        service_categories=service_categories,
        experience_level=experience_level,
        rating_threshold=rating_threshold
    )
    
    return render_template("networking/search_members.html", 
                         potential_members=potential_members,
                         search_params={
                             'location': location,
                             'service_categories': service_categories,
                             'experience_level': experience_level,
                             'rating_threshold': rating_threshold
                         })

@app.route("/network/invite-member", methods=["POST"])
@login_required
def invite_network_member():
    """Send network invitation to a user"""
    if current_user.account_type != "networking":
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    data = request.json or {}
    invitee_id = data.get('invitee_id')
    network_name = data.get('network_name', f"{current_user.email}'s Network")
    commission_percentage = data.get('commission_percentage', 0.0)
    subscription_fee = data.get('subscription_fee', 0.0)
    payment_structure = data.get('payment_structure', 'commission')
    invitation_message = data.get('invitation_message', '')
    
    success, message = send_network_invitation(
        network_owner_id=current_user.id,
        invitee_id=invitee_id,
        network_name=network_name,
        commission_percentage=commission_percentage,
        subscription_fee=subscription_fee,
        payment_structure=payment_structure,
        invitation_message=invitation_message
    )
    
    return jsonify({"success": success, "message": message})

@app.route("/network/invitation/<int:invitation_id>/accept", methods=["POST"])
@login_required
def accept_network_invitation_route(invitation_id):
    """Accept a network invitation"""
    success, message = accept_network_invitation(invitation_id, current_user.id)
    
    if success:
        flash("Network invitation accepted successfully!", "success")
    else:
        flash(f"Error accepting invitation: {message}", "error")
    
    return redirect(url_for('inbox'))

@app.route("/network/invitation/<int:invitation_id>/decline", methods=["POST"])
@login_required
def decline_network_invitation(invitation_id):
    """Decline a network invitation"""
    invitation = NetworkInvitation.query.get_or_404(invitation_id)
    
    if invitation.invitee_id != current_user.id:
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    invitation.status = "declined"
    invitation.responded_at = datetime.utcnow()
    db.session.commit()
    
    flash("Network invitation declined.", "info")
    return redirect(url_for('inbox'))

@app.route("/network/referrals")
@login_required
def network_referrals():
    """View network referrals for networking accounts"""
    if current_user.account_type != "networking":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))
    
    referrals = NetworkReferral.query.filter_by(
        network_owner_id=current_user.id
    ).order_by(NetworkReferral.created_at.desc()).all()
    
    return render_template("networking/referrals.html", referrals=referrals)

@app.route("/network/create-referral", methods=["POST"])
@login_required
def create_network_referral():
    """Create a referral to earn commission"""
    data = request.json or {}
    customer_id = data.get('customer_id')
    professional_id = data.get('professional_id')
    job_posting_id = data.get('job_posting_id')
    work_request_id = data.get('work_request_id')
    
    success, message = create_customer_referral(
        network_member_id=current_user.id,
        customer_id=customer_id,
        professional_id=professional_id,
        job_posting_id=job_posting_id,
        work_request_id=work_request_id
    )
    
    return jsonify({"success": success, "message": message})

# --- Work Search Routes for Professionals and Networking ---

@app.route("/find-work")
@login_required
def find_work():
    """Work search functionality for professionals and networking accounts"""
    if current_user.account_type not in ["professional", "networking"]:
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))
    
    page = request.args.get('page', 1, type=int)
    location = request.args.get('location', '')
    category = request.args.get('category', '')
    experience_level = request.args.get('experience_level', '')
    budget_min = request.args.get('budget_min', 0, type=float)
    budget_max = request.args.get('budget_max', 10000, type=float)
    
    # Build query for available jobs
    query = JobPosting.query.filter_by(status="active")
    
    if location:
        query = query.filter(JobPosting.location.ilike(f"%{location}%"))
    
    if category:
        query = query.filter(JobPosting.labor_category.ilike(f"%{category}%"))
    
    if experience_level:
        query = query.filter(JobPosting.required_experience_level == experience_level)
    
    if budget_min > 0:
        query = query.filter(JobPosting.budget_range_max >= budget_min)
    
    if budget_max < 10000:
        query = query.filter(JobPosting.budget_range_min <= budget_max)
    
    jobs = query.order_by(JobPosting.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get all work requests too
    work_request_query = WorkRequest.query.filter_by(status="open")
    
    if location:
        work_request_query = work_request_query.filter(WorkRequest.location.ilike(f"%{location}%"))
    
    if category:
        work_request_query = work_request_query.filter(WorkRequest.work_type.ilike(f"%{category}%"))
    
    work_requests = work_request_query.order_by(WorkRequest.created_at.desc()).limit(10).all()
    
    return render_template("work_search/find_work.html", 
                         jobs=jobs, 
                         work_requests=work_requests,
                         search_params={
                             'location': location,
                             'category': category,
                             'experience_level': experience_level,
                             'budget_min': budget_min,
                             'budget_max': budget_max
                         })

@app.route("/apply-to-job/<int:job_id>", methods=["POST"])
@login_required
def apply_to_job(job_id):
    """Apply to a job posting"""
    if current_user.account_type not in ["professional", "job_seeker"]:
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    job = JobPosting.query.get_or_404(job_id)
    
    # Check if already applied
    existing_match = JobMatch.query.filter_by(
        job_posting_id=job_id,
        professional_id=current_user.id if current_user.account_type == "professional" else None,
        job_seeker_id=current_user.id if current_user.account_type == "job_seeker" else None
    ).first()
    
    if existing_match:
        return jsonify({"success": False, "message": "Already applied to this job"})
    
    # Create job match/application
    match = JobMatch(
        job_posting_id=job_id,
        professional_id=current_user.id if current_user.account_type == "professional" else None,
        job_seeker_id=current_user.id if current_user.account_type == "job_seeker" else None,
        match_type="direct_application",
        status="pending"
    )
    
    db.session.add(match)
    db.session.commit()
    
    # Send notification message to job poster
    send_message(
        sender_id=current_user.id,
        recipient_id=job.posted_by_user_id,
        subject=f"Job Application: {job.title}",
        content=f"I am interested in your job posting '{job.title}'. Please review my profile.",
        message_type="job_inquiry",
        related_job_id=job_id
    )
    
    return jsonify({"success": True, "message": "Application submitted successfully!"})

@app.route("/customer-search")
@login_required
def customer_search():
    """Search for customers needing work (networking accounts only)"""
    if current_user.account_type != "networking":
        flash("Access denied.", "error")
        return redirect(url_for("dashboard"))
    
    page = request.args.get('page', 1, type=int)
    location = request.args.get('location', '')
    category = request.args.get('category', '')
    budget_min = request.args.get('budget_min', 0, type=float)
    budget_max = request.args.get('budget_max', 10000, type=float)
    
    # Search work requests (customers needing work)
    query = WorkRequest.query.filter_by(status="open")
    
    if location:
        query = query.filter(WorkRequest.location.ilike(f"%{location}%"))
    
    if category:
        query = query.filter(WorkRequest.work_type.ilike(f"%{category}%"))
    
    work_requests = query.order_by(WorkRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get network members who could be referred
    network_members = NetworkMembership.query.filter_by(
        network_owner_id=current_user.id,
        status="active"
    ).all()
    
    return render_template("networking/customer_search.html", 
                         work_requests=work_requests,
                         network_members=network_members,
                         search_params={
                             'location': location,
                             'category': category,
                             'budget_min': budget_min,
                             'budget_max': budget_max
                         })

@app.route("/delete-my-data", methods=["POST"])
@login_required
def delete_user_data():
    """Delete user's collected data"""
    UserDataCollection.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    flash("Your data has been deleted from our analytics system.", "success")
    return redirect(url_for("data_management"))


# =============================================================================
# MOBILE API ENDPOINTS (RESTful API for iOS/Android Apps)
# =============================================================================

@app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
def api_login():
    """Mobile API: User authentication"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email'].lower()).first()
        if user and check_password_hash(user.password_hash, data['password']):
            # Generate session token (implement JWT in production)
            session_token = serializer.dumps({'user_id': user.id})
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'account_type': user.account_type,
                    'email_verified': user.email_verified
                },
                'token': session_token
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/v1/users/profile', methods=['GET', 'OPTIONS'])
def api_get_profile():
    """Mobile API: Get user profile"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        data = serializer.loads(token, max_age=86400)  # 24 hours
        user = User.query.get(data['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile_data = {
            'id': user.id,
            'email': user.email,
            'account_type': user.account_type,
            'email_verified': user.email_verified,
            'created_at': user.created_at.isoformat()
        }
        
        # Add specific profile data based on account type
        if user.account_type == 'contractor' and user.contractor_profile:
            profile_data['contractor_profile'] = {
                'business_name': user.contractor_profile.business_name,
                'contact_name': user.contractor_profile.contact_name,
                'phone': user.contractor_profile.phone,
                'location': user.contractor_profile.location,
                'services': user.contractor_profile.services,
                'geographic_area': user.contractor_profile.geographic_area
            }
        elif user.account_type == 'customer' and user.customer_profile:
            profile_data['customer_profile'] = {
                'first_name': user.customer_profile.first_name,
                'last_name': user.customer_profile.last_name,
                'phone': user.customer_profile.phone,
                'address': user.customer_profile.address,
                'city': user.customer_profile.city,
                'state': user.customer_profile.state
            }
        
        return jsonify({'user': profile_data}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/v1/ratings/<int:user_id>', methods=['GET', 'OPTIONS'])
def api_get_ratings(user_id):
    """Mobile API: Get user ratings"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        rating, count = calculate_user_rating(user_id)
        summary = get_user_rating_summary(user_id)
        
        return jsonify({
            'user_id': user_id,
            'average_rating': rating,
            'total_ratings': count,
            'rating_breakdown': summary.get('breakdown', {}),
            'recent_reviews': [
                {
                    'rating': review['rating'],
                    'comment': review['comment'],
                    'date': review['date'].isoformat() if hasattr(review['date'], 'isoformat') else str(review['date'])
                }
                for review in summary.get('recent_reviews', [])[:5]
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get ratings'}), 500

@app.route('/api/v1/contractors/search', methods=['POST', 'OPTIONS'])
def api_search_contractors():
    """Mobile API: Search for contractors"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        service_category = data.get('service_category', '')
        geographic_area = data.get('geographic_area', '')
        customer_rating = data.get('customer_rating')
        
        contractors = get_random_contractors(service_category, geographic_area, customer_rating)
        
        result = []
        for contractor_user, contractor_profile in contractors:
            rating, count = calculate_user_rating(contractor_user.id)
            result.append({
                'id': contractor_user.id,
                'business_name': contractor_profile.business_name,
                'contact_name': contractor_profile.contact_name,
                'location': contractor_profile.location,
                'services': contractor_profile.services,
                'rating': rating,
                'rating_count': count,
                'geographic_area': contractor_profile.geographic_area
            })
        
        return jsonify({
            'contractors': result,
            'total': len(result)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/v1/ratings', methods=['POST', 'OPTIONS'])
def api_submit_rating():
    """Mobile API: Submit a rating"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        token_data = serializer.loads(token, max_age=86400)
        rater_id = token_data['user_id']
        
        data = request.get_json()
        ratee_id = data.get('ratee_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        work_request_id = data.get('work_request_id')
        transaction_type = data.get('transaction_type', 'job_completion')
        
        if not all([ratee_id, rating, work_request_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Check if rating already exists
        existing_rating = UserRating.query.filter_by(
            rater_id=rater_id,
            ratee_id=ratee_id,
            work_request_id=work_request_id
        ).first()
        
        if existing_rating:
            return jsonify({'error': 'Rating already submitted for this work request'}), 409
        
        # Create new rating
        new_rating = UserRating(
            rater_id=rater_id,
            ratee_id=ratee_id,
            rating=rating,
            comment=comment,
            work_request_id=work_request_id,
            transaction_type=transaction_type,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_rating)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rating submitted successfully',
            'rating_id': new_rating.id
        }), 201
    except Exception as e:
        return jsonify({'error': 'Failed to submit rating'}), 500

# --- ID Verification Routes ---
@app.route('/id-verification/upload', methods=['GET', 'POST'])
@login_required
def id_verification_upload():
    """Handle ID document upload and verification"""
    try:
        from id_verification import upload_id
        return upload_id()
    except ImportError:
        print("Warning: id_verification module not found, using fallback")
        flash('ID verification temporarily unavailable. Please try again later.', 'warning')
        return redirect(url_for('dashboard'))
    except Exception as e:
        current_app.logger.error(f"ID verification upload error: {str(e)}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/id-verification/status')
@login_required  
def id_verification_status():
    """Display current verification status"""
    verification = IDVerification.query.filter_by(user_id=current_user.id)\
                                     .order_by(IDVerification.submitted_at.desc())\
                                     .first()
    
    return render_template('id_verification/status.html', verification=verification)

@app.route('/id-verification/api/verify-status')
@login_required
def id_verification_api_status():
    """API endpoint for checking verification status"""
    verification = IDVerification.query.filter_by(user_id=current_user.id)\
                                     .order_by(IDVerification.submitted_at.desc())\
                                     .first()
    
    if not verification:
        return jsonify({
            'status': 'not_verified',
            'message': 'No verification submitted'
        })
    
    return jsonify({
        'verification_id': verification.verification_id,
        'status': verification.status,
        'document_type': verification.document_type,
        'submitted_at': verification.submitted_at.isoformat(),
        'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
        'confidence_score': verification.confidence_score,
        'message': 'Verification status retrieved successfully'
    })

# --- Contract Management Routes ---
@app.route('/contracts')
@login_required
def contracts_dashboard():
    """Contract management dashboard"""
    from docusign_integration import ContractManager
    
    contract_manager = ContractManager()
    
    # Get user contracts
    contracts = contract_manager.get_user_contracts(current_user.id)
    
    # Check compliance status
    compliance_status = contract_manager.is_user_contract_compliant(current_user)
    
    # Identify pending contracts
    pending_contracts = [c for c in contracts if c.status in ['sent', 'delivered']]
    
    return render_template('contracts/dashboard.html',
                         contracts=contracts,
                         compliance_status=compliance_status,
                         pending_contracts=pending_contracts)

@app.route('/contracts/send', methods=['POST'])
@login_required
def send_contract():
    """Send contract to user for signing"""
    if not DOCUSIGN_AVAILABLE:
        return jsonify({'success': False, 'error': 'Contract management temporarily unavailable'})
    
    contract_type = request.form.get('contract_type')
    if not contract_type:
        flash('Invalid contract type', 'error')
        return redirect(url_for('contracts_dashboard'))
    
    contract_manager = ContractManager()
    
    try:
        if contract_type == 'contractor_agreement':
            if current_user.account_type != 'contractor':
                flash('Only contractors can sign contractor agreements', 'error')
                return redirect(url_for('contracts_dashboard'))
            
            contract, error = contract_manager.send_contractor_agreement(current_user)
            
        elif contract_type == 'client_terms':
            if current_user.account_type != 'customer':
                flash('Only customers can sign client terms', 'error')
                return redirect(url_for('contracts_dashboard'))
            
            contract, error = contract_manager.send_client_terms(current_user)
            
        else:
            flash('Unsupported contract type', 'error')
            return redirect(url_for('contracts_dashboard'))
        
        if error:
            flash(f'Failed to send contract: {error}', 'error')
        else:
            flash('Contract sent successfully! Check your email for signing instructions.', 'success')
    
    except Exception as e:
        flash(f'Error sending contract: {str(e)}', 'error')
    
    return redirect(url_for('contracts_dashboard'))

@app.route('/contracts/status/<int:contract_id>', methods=['POST'])
@login_required
def refresh_contract_status(contract_id):
    """Refresh contract status from DocuSign"""
    from docusign_integration import ContractManager
    
    # Verify contract belongs to current user
    contract = ContractDocument.query.filter_by(id=contract_id, user_id=current_user.id).first()
    if not contract:
        return jsonify({'success': False, 'error': 'Contract not found'}), 404
    
    contract_manager = ContractManager()
    
    try:
        updated_contract, error = contract_manager.check_contract_status(contract_id)
        
        if error:
            return jsonify({'success': False, 'error': error}), 500
        
        return jsonify({
            'success': True,
            'status': updated_contract.status,
            'message': 'Status updated successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contracts/refresh-all', methods=['POST'])
@login_required
def refresh_all_contracts():
    """Refresh status of all user contracts"""
    from docusign_integration import ContractManager
    
    contracts = ContractDocument.query.filter_by(user_id=current_user.id).all()
    contract_manager = ContractManager()
    
    updated_count = 0
    errors = []
    
    for contract in contracts:
        if contract.status not in ['completed', 'declined', 'voided']:
            try:
                updated_contract, error = contract_manager.check_contract_status(contract.id)
                if error:
                    errors.append(f"Contract {contract.id}: {error}")
                else:
                    updated_count += 1
            except Exception as e:
                errors.append(f"Contract {contract.id}: {str(e)}")
    
    if errors:
        return jsonify({
            'success': False,
            'error': f"Updated {updated_count} contracts with {len(errors)} errors",
            'details': errors
        }), 500
    
    return jsonify({
        'success': True,
        'message': f"Successfully updated {updated_count} contracts"
    })

@app.route('/contracts/download/<int:contract_id>')
@login_required
def download_contract(contract_id):
    """Download completed contract document"""
    contract = ContractDocument.query.filter_by(id=contract_id, user_id=current_user.id).first()
    
    if not contract:
        flash('Contract not found', 'error')
        return redirect(url_for('contracts_dashboard'))
    
    if contract.status != 'completed' or not contract.completed_document_url:
        flash('Contract document not available for download', 'error')
        return redirect(url_for('contracts_dashboard'))
    
    try:
        import os
        if os.path.exists(contract.completed_document_url):
            return send_file(
                contract.completed_document_url,
                as_attachment=True,
                download_name=f"{contract.document_name}_{contract.envelope_id}.pdf"
            )
        else:
            flash('Contract file not found on server', 'error')
            return redirect(url_for('contracts_dashboard'))
    
    except Exception as e:
        flash(f'Error downloading contract: {str(e)}', 'error')
        return redirect(url_for('contracts_dashboard'))

@app.route('/api/v1/health', methods=['GET'])
def api_health():
    """Mobile API: Health check for mobile apps"""
    return jsonify({
        'status': 'healthy',
        'api_version': '1.0',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'LaborLooker Mobile API'
    }), 200

# =============================================================================
# END MOBILE API ENDPOINTS
# =============================================================================

# =============================================================================
# ADVANCED MULTIMEDIA MARKETING CAMPAIGN ROUTES
# =============================================================================

@app.route("/marketing/campaigns")
@login_required
def marketing_campaigns():
    """View all marketing campaigns for the current user"""
    if current_user.account_type not in ['networking', 'customer', 'admin']:
        flash("Access denied. Marketing campaigns are available for networking accounts, customers, and admins.", "error")
        return redirect(url_for('dashboard'))
    
    if current_user.account_type == 'admin':
        campaigns = MarketingCampaign.query.all()
    else:
        campaigns = MarketingCampaign.query.filter_by(client_id=current_user.id).all()
    
    # Calculate campaign performance summary
    campaign_data = []
    for campaign in campaigns:
        performance = db.session.query(CampaignPerformance).filter_by(campaign_id=campaign.id).all()
        
        total_impressions = sum(p.impressions for p in performance)
        total_clicks = sum(p.clicks for p in performance)
        total_conversions = sum(p.conversions for p in performance)
        total_cost = sum(p.cost for p in performance)
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        campaign_data.append({
            'campaign': campaign,
            'impressions': total_impressions,
            'clicks': total_clicks,
            'conversions': total_conversions,
            'cost': total_cost,
            'ctr': round(ctr, 2),
            'conversion_rate': round(conversion_rate, 2),
            'channels': len(campaign.channels),
            'creative_assets': len(campaign.creative_assets)
        })
    
    return render_template("marketing/campaigns_list.html", campaign_data=campaign_data)

@app.route("/marketing/campaign/new", methods=["GET", "POST"])
@login_required
def new_marketing_campaign():
    """Create a new multimedia marketing campaign"""
    if current_user.account_type not in ['networking', 'customer', 'admin']:
        flash("Access denied. Marketing campaigns are available for networking accounts and customers.", "error")
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        try:
            # Parse campaign objectives and targeting from JSON
            objectives = json.dumps({
                'primary': request.form.get('primary_objective'),
                'secondary': request.form.get('secondary_objective'),
                'kpis': request.form.getlist('kpis')
            })
            
            geographic_targeting = json.dumps({
                'countries': request.form.getlist('countries'),
                'states': request.form.getlist('states'), 
                'cities': request.form.getlist('cities'),
                'zip_codes': request.form.getlist('zip_codes'),
                'radius_miles': request.form.get('radius_miles')
            })
            
            demographic_targeting = json.dumps({
                'age_ranges': request.form.getlist('age_ranges'),
                'genders': request.form.getlist('genders'),
                'income_ranges': request.form.getlist('income_ranges'),
                'education_levels': request.form.getlist('education_levels'),
                'interests': request.form.getlist('interests')
            })
            
            # Create new campaign
            campaign = MarketingCampaign(
                client_id=current_user.id,
                campaign_name=request.form.get('campaign_name'),
                campaign_description=request.form.get('campaign_description'),
                campaign_objectives=objectives,
                campaign_type=request.form.get('campaign_type'),
                marketing_strategy=request.form.get('marketing_strategy'),
                total_budget=float(request.form.get('total_budget', 0)),
                platform_service_fee=float(request.form.get('total_budget', 0)) * 0.15,  # 15% service fee
                campaign_start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d'),
                campaign_end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d'),
                geographic_targeting=geographic_targeting,
                demographic_targeting=demographic_targeting,
                target_market_segment=request.form.get('target_market_segment'),
                ai_optimization_enabled=bool(request.form.get('ai_optimization')),
                multi_variate_testing_enabled=bool(request.form.get('ab_testing')),
                personalization_level=request.form.get('personalization_level', 'basic')
            )
            
            db.session.add(campaign)
            db.session.commit()
            
            flash("Marketing campaign created successfully! You can now add channels and creative assets.", "success")
            return redirect(url_for('marketing_campaign_detail', campaign_id=campaign.id))
            
        except ValueError as e:
            flash(f"Invalid input: {str(e)}", "error")
        except Exception as e:
            flash("Error creating campaign. Please try again.", "error")
            db.session.rollback()
    
    # GET request - show form
    return render_template("marketing/campaign_new.html")

@app.route("/marketing/campaign/<int:campaign_id>")
@login_required
def marketing_campaign_detail(campaign_id):
    """View detailed campaign information, channels, and performance"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    # Get campaign performance data
    performance_data = db.session.query(CampaignPerformance).filter_by(campaign_id=campaign_id).all()
    
    # Get channel performance
    channel_performance = {}
    for channel in campaign.channels:
        channel_perf = db.session.query(CampaignPerformance).filter_by(channel_id=channel.id).all()
        channel_performance[channel.id] = {
            'impressions': sum(p.impressions for p in channel_perf),
            'clicks': sum(p.clicks for p in channel_perf),
            'conversions': sum(p.conversions for p in channel_perf),
            'cost': sum(p.cost for p in channel_perf),
            'performance': channel_perf[-5:] if channel_perf else []  # Last 5 days
        }
    
    # Calculate overall metrics
    total_impressions = sum(p.impressions for p in performance_data)
    total_clicks = sum(p.clicks for p in performance_data)
    total_conversions = sum(p.conversions for p in performance_data)
    total_cost = sum(p.cost for p in performance_data)
    
    metrics = {
        'impressions': total_impressions,
        'clicks': total_clicks,
        'conversions': total_conversions,
        'cost': total_cost,
        'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
        'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
        'cpc': (total_cost / total_clicks) if total_clicks > 0 else 0,
        'roas': (total_conversions * 100 / total_cost) if total_cost > 0 else 0  # Assume $100 avg conversion value
    }
    
    return render_template("marketing/campaign_detail.html", 
                         campaign=campaign, 
                         metrics=metrics,
                         channel_performance=channel_performance,
                         performance_data=performance_data[-30:])  # Last 30 days

@app.route("/marketing/campaign/<int:campaign_id>/channel/new", methods=["GET", "POST"])
@login_required
def new_campaign_channel(campaign_id):
    """Add a new marketing channel to a campaign"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    if request.method == "POST":
        try:
            # Parse targeting and specifications
            audience_targeting = json.dumps({
                'age_ranges': request.form.getlist('channel_age_ranges'),
                'interests': request.form.getlist('channel_interests'),
                'behaviors': request.form.getlist('channel_behaviors'),
                'custom_audiences': request.form.getlist('custom_audiences')
            })
            
            creative_specs = json.dumps({
                'image_sizes': request.form.getlist('image_sizes'),
                'video_lengths': request.form.getlist('video_lengths'),
                'text_limits': {
                    'headline': request.form.get('headline_limit'),
                    'description': request.form.get('description_limit')
                }
            })
            
            # Create new channel
            channel = CampaignChannel(
                campaign_id=campaign_id,
                channel_type=request.form.get('channel_type'),
                platform_name=request.form.get('platform_name'),
                allocated_budget=float(request.form.get('allocated_budget', 0)),
                cost_model=request.form.get('cost_model'),
                audience_targeting=audience_targeting,
                creative_specifications=creative_specs,
                bidding_strategy=request.form.get('bidding_strategy'),
                start_date=datetime.strptime(request.form.get('channel_start_date'), '%Y-%m-%d') if request.form.get('channel_start_date') else None,
                end_date=datetime.strptime(request.form.get('channel_end_date'), '%Y-%m-%d') if request.form.get('channel_end_date') else None,
                ab_testing_enabled=bool(request.form.get('ab_testing')),
                dynamic_creative_enabled=bool(request.form.get('dynamic_creative'))
            )
            
            db.session.add(channel)
            db.session.commit()
            
            flash(f"Added {channel.platform_name} {channel.channel_type} channel successfully!", "success")
            return redirect(url_for('marketing_campaign_detail', campaign_id=campaign_id))
            
        except ValueError as e:
            flash(f"Invalid input: {str(e)}", "error")
        except Exception as e:
            flash("Error adding channel. Please try again.", "error")
            db.session.rollback()
    
    return render_template("marketing/channel_new.html", campaign=campaign)

@app.route("/marketing/campaign/<int:campaign_id>/creative/new", methods=["GET", "POST"])
@login_required
def new_creative_asset(campaign_id):
    """Add a new creative asset to a campaign"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    if request.method == "POST":
        try:
            # Handle file upload
            file_path = None
            if 'creative_file' in request.files:
                file = request.files['creative_file']
                if file.filename != '':
                    # Save file (implement proper file handling for production)
                    filename = f"campaign_{campaign_id}_{shortuuid.uuid()[:8]}_{file.filename}"
                    file_path = os.path.join('static', 'marketing', 'creatives', filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
            
            # Parse platform specifications and tags
            platform_specs = json.dumps({
                'facebook': {
                    'image_size': request.form.get('facebook_image_size'),
                    'aspect_ratio': request.form.get('facebook_aspect_ratio')
                },
                'google': {
                    'image_size': request.form.get('google_image_size'),
                    'headline_limit': request.form.get('google_headline_limit')
                },
                'instagram': {
                    'image_size': request.form.get('instagram_image_size'),
                    'video_length': request.form.get('instagram_video_length')
                }
            })
            
            tags = json.dumps(request.form.getlist('tags'))
            target_audience = json.dumps({
                'primary': request.form.get('primary_audience'),
                'secondary': request.form.get('secondary_audience'),
                'personas': request.form.getlist('personas')
            })
            
            # Create creative asset
            creative = CreativeAsset(
                campaign_id=campaign_id,
                asset_name=request.form.get('asset_name'),
                asset_type=request.form.get('asset_type'),
                asset_category=request.form.get('asset_category'),
                file_format=request.form.get('file_format'),
                file_path=file_path,
                primary_message=request.form.get('primary_message'),
                call_to_action=request.form.get('call_to_action'),
                target_audience=target_audience,
                emotional_tone=request.form.get('emotional_tone'),
                platform_specifications=platform_specs,
                tags=tags,
                description=request.form.get('description'),
                ab_test_variant=request.form.get('ab_variant', 'A')
            )
            
            db.session.add(creative)
            db.session.commit()
            
            flash("Creative asset added successfully!", "success")
            return redirect(url_for('marketing_campaign_detail', campaign_id=campaign_id))
            
        except Exception as e:
            flash("Error adding creative asset. Please try again.", "error")
            db.session.rollback()
    
    return render_template("marketing/creative_new.html", campaign=campaign)

@app.route("/marketing/campaign/<int:campaign_id>/automation", methods=["GET", "POST"])
@login_required
def campaign_automation(campaign_id):
    """Configure marketing automation for a campaign"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    if request.method == "POST":
        try:
            # Parse automation configuration
            trigger_conditions = json.dumps({
                'metrics': {
                    'ctr_threshold': float(request.form.get('ctr_threshold', 0)),
                    'cost_threshold': float(request.form.get('cost_threshold', 0)),
                    'conversion_rate_threshold': float(request.form.get('conversion_threshold', 0))
                },
                'time_conditions': {
                    'hours_without_data': int(request.form.get('hours_without_data', 24)),
                    'performance_window': request.form.get('performance_window', 'daily')
                }
            })
            
            automated_actions = json.dumps({
                'budget_adjustment': {
                    'enabled': bool(request.form.get('auto_budget')),
                    'max_increase': float(request.form.get('max_budget_increase', 10)),
                    'max_decrease': float(request.form.get('max_budget_decrease', 10))
                },
                'bid_adjustment': {
                    'enabled': bool(request.form.get('auto_bidding')),
                    'strategy': request.form.get('bid_strategy', 'target_cpa')
                },
                'creative_rotation': {
                    'enabled': bool(request.form.get('auto_creative')),
                    'frequency': request.form.get('rotation_frequency', 'weekly')
                },
                'notifications': {
                    'email': bool(request.form.get('email_notifications')),
                    'threshold_alerts': bool(request.form.get('threshold_alerts'))
                }
            })
            
            # Create automation rule
            automation = MarketingAutomation(
                campaign_id=campaign_id,
                automation_name=request.form.get('automation_name'),
                automation_type=request.form.get('automation_type'),
                description=request.form.get('automation_description'),
                trigger_conditions=trigger_conditions,
                trigger_frequency=request.form.get('trigger_frequency'),
                automated_actions=automated_actions,
                ml_model_enabled=bool(request.form.get('ml_enabled')),
                learning_algorithm=request.form.get('ml_algorithm') if request.form.get('ml_enabled') else None,
                automation_status='active' if bool(request.form.get('activate_now')) else 'inactive'
            )
            
            db.session.add(automation)
            db.session.commit()
            
            flash("Marketing automation configured successfully!", "success")
            return redirect(url_for('marketing_campaign_detail', campaign_id=campaign_id))
            
        except Exception as e:
            flash("Error configuring automation. Please try again.", "error")
            db.session.rollback()
    
    # Get existing automations
    automations = MarketingAutomation.query.filter_by(campaign_id=campaign_id).all()
    
    return render_template("marketing/automation.html", campaign=campaign, automations=automations)

@app.route("/marketing/campaign/<int:campaign_id>/performance")
@login_required
def campaign_performance(campaign_id):
    """View detailed campaign performance analytics"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    # Get performance data for different time ranges
    from datetime import date, timedelta
    
    today = date.today()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Daily performance for charts
    daily_performance = db.session.query(CampaignPerformance).filter(
        CampaignPerformance.campaign_id == campaign_id,
        CampaignPerformance.report_date >= last_30_days,
        CampaignPerformance.granularity == 'daily'
    ).order_by(CampaignPerformance.report_date).all()
    
    # Channel breakdown
    channel_performance = {}
    for channel in campaign.channels:
        channel_data = db.session.query(CampaignPerformance).filter(
            CampaignPerformance.channel_id == channel.id,
            CampaignPerformance.report_date >= last_30_days
        ).all()
        
        channel_performance[channel.platform_name] = {
            'impressions': sum(p.impressions for p in channel_data),
            'clicks': sum(p.clicks for p in channel_data),
            'conversions': sum(p.conversions for p in channel_data),
            'cost': sum(p.cost for p in channel_data)
        }
    
    # Audience insights
    audience_data = {}
    if daily_performance:
        latest_performance = daily_performance[-1]
        if latest_performance.geographic_performance:
            try:
                audience_data['geographic'] = json.loads(latest_performance.geographic_performance)
            except:
                audience_data['geographic'] = {}
        
        if latest_performance.mobile_performance and latest_performance.desktop_performance:
            try:
                mobile = json.loads(latest_performance.mobile_performance)
                desktop = json.loads(latest_performance.desktop_performance)
                audience_data['device'] = {'mobile': mobile, 'desktop': desktop}
            except:
                audience_data['device'] = {}
    
    return render_template("marketing/performance.html", 
                         campaign=campaign,
                         daily_performance=daily_performance,
                         channel_performance=channel_performance,
                         audience_data=audience_data)

@app.route("/marketing/campaign/<int:campaign_id>/roi")
@login_required
def campaign_roi_analysis(campaign_id):
    """View ROI analysis for a campaign"""
    campaign = MarketingCampaign.query.get_or_404(campaign_id)
    
    # Check permissions
    if campaign.client_id != current_user.id and current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('marketing_campaigns'))
    
    # Get or create ROI analysis
    roi_analysis = CampaignROIAnalysis.query.filter_by(campaign_id=campaign_id).order_by(CampaignROIAnalysis.created_at.desc()).first()
    
    if not roi_analysis:
        # Generate ROI analysis
        performance_data = db.session.query(CampaignPerformance).filter_by(campaign_id=campaign_id).all()
        
        total_cost = sum(p.cost for p in performance_data)
        total_conversions = sum(p.conversions for p in performance_data)
        total_revenue = total_conversions * 100  # Assume $100 avg conversion value
        
        roi_analysis = CampaignROIAnalysis(
            campaign_id=campaign_id,
            analysis_start_date=campaign.campaign_start_date.date(),
            analysis_end_date=min(campaign.campaign_end_date.date(), date.today()),
            total_investment=campaign.total_budget,
            media_spend=total_cost,
            platform_management_fee=campaign.platform_service_fee,
            direct_revenue=total_revenue,
            total_roi=((total_revenue - campaign.total_budget) / campaign.total_budget * 100) if campaign.total_budget > 0 else 0,
            customer_acquisition_cost=total_cost / total_conversions if total_conversions > 0 else 0,
            new_customers_acquired=total_conversions,
            analyst_id=current_user.id
        )
        
        db.session.add(roi_analysis)
        db.session.commit()
    
    return render_template("marketing/roi_analysis.html", campaign=campaign, roi_analysis=roi_analysis)

@app.route("/marketing/marketplace")
@login_required
def marketing_marketplace():
    """Browse and purchase marketing services"""
    # Sample marketing service packages
    service_packages = [
        {
            'name': 'Social Media Blitz',
            'description': 'Comprehensive social media campaign across Facebook, Instagram, and LinkedIn',
            'price': 2500,
            'duration': '30 days',
            'features': ['Multi-platform posting', 'Audience targeting', 'Performance analytics', 'A/B testing'],
            'estimated_reach': '50,000+',
            'platforms': ['Facebook', 'Instagram', 'LinkedIn']
        },
        {
            'name': 'Google Ads Pro',
            'description': 'Professional Google Ads campaign with search and display advertising',
            'price': 3500,
            'duration': '60 days', 
            'features': ['Keyword research', 'Ad copy optimization', 'Landing page review', 'Conversion tracking'],
            'estimated_reach': '100,000+',
            'platforms': ['Google Search', 'Google Display Network', 'YouTube']
        },
        {
            'name': 'Video Marketing Suite',
            'description': 'Video content creation and distribution across multiple platforms',
            'price': 5000,
            'duration': '45 days',
            'features': ['Video production', 'Script writing', 'Multi-platform distribution', 'Engagement analytics'],
            'estimated_reach': '75,000+',
            'platforms': ['YouTube', 'Facebook', 'Instagram', 'TikTok']
        },
        {
            'name': 'Complete Brand Campaign',
            'description': 'Full-service brand awareness campaign with integrated multimedia approach',
            'price': 10000,
            'duration': '90 days',
            'features': ['Brand strategy', 'Creative development', 'Multi-channel execution', 'ROI analysis'],
            'estimated_reach': '250,000+',
            'platforms': ['All major platforms', 'Traditional media', 'Influencer partnerships']
        }
    ]
    
    return render_template("marketing/marketplace.html", service_packages=service_packages)

@app.route("/marketing/services/custom-quote", methods=["GET", "POST"])
@login_required
def custom_marketing_quote():
    """Request a custom marketing campaign quote"""
    if request.method == "POST":
        try:
            # Create a lead for custom marketing services
            quote_data = {
                'business_name': request.form.get('business_name'),
                'industry': request.form.get('industry'),
                'target_audience': request.form.get('target_audience'),
                'budget_range': request.form.get('budget_range'),
                'campaign_goals': request.form.getlist('campaign_goals'),
                'preferred_channels': request.form.getlist('preferred_channels'),
                'timeline': request.form.get('timeline'),
                'additional_requirements': request.form.get('additional_requirements'),
                'contact_email': request.form.get('contact_email'),
                'contact_phone': request.form.get('contact_phone')
            }
            
            # Store as a prospect for follow-up
            prospect = Prospect(
                client_id=1,  # System/admin client
                name=quote_data['business_name'],
                email=quote_data['contact_email'],
                phone=quote_data['contact_phone'],
                notes=f"Custom marketing quote request: {json.dumps(quote_data, indent=2)}",
                source="Marketing Services",
                status="new"
            )
            
            db.session.add(prospect)
            db.session.commit()
            
            flash("Your custom quote request has been submitted! Our marketing team will contact you within 24 hours.", "success")
            return redirect(url_for('marketing_marketplace'))
            
        except Exception as e:
            flash("Error submitting quote request. Please try again.", "error")
            db.session.rollback()
    
    return render_template("marketing/custom_quote.html")

@app.route("/admin/marketing/campaigns")
@login_required
def admin_marketing_campaigns():
    """Admin view of all marketing campaigns"""
    if current_user.account_type != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('dashboard'))
    
    campaigns = MarketingCampaign.query.all()
    
    # Calculate aggregate statistics
    stats = {
        'total_campaigns': len(campaigns),
        'active_campaigns': len([c for c in campaigns if c.campaign_status == 'active']),
        'total_budget': sum(c.total_budget for c in campaigns),
        'total_revenue': sum(c.platform_service_fee for c in campaigns)
    }
    
    return render_template("admin/marketing_campaigns.html", campaigns=campaigns, stats=stats)

# ===================================================================
# DOCUSIGN ROUTES AND WEBHOOK HANDLERS
# ===================================================================

@app.route('/contractor/documents/required')
@login_required
def contractor_documents_required():
    """Page showing required documents status"""
    user = User.query.get(session['user_id'])
    if not user or not user.contractor_profile:
        return redirect(url_for('contractor_dashboard'))
    
    # Get document status
    pending_contracts = ContractDocument.query.filter_by(
        user_id=user.id
    ).filter(ContractDocument.status.in_(['sent', 'delivered'])).all()
    
    completed_contracts = ContractDocument.query.filter_by(
        user_id=user.id,
        status='completed'
    ).all()
    
    return render_template('contractor/documents_required.html',
                         pending_contracts=pending_contracts,
                         completed_contracts=completed_contracts,
                         user=user)

@app.route('/docusign/webhook', methods=['POST'])
def docusign_webhook():
    """Handle DocuSign webhook notifications"""
    try:
        webhook_data = request.get_json()
        
        # Process each envelope status change
        for envelope_data in webhook_data.get('data', []):
            envelope_id = envelope_data.get('envelopeId')
            status = envelope_data.get('status')
            
            if not envelope_id:
                continue
            
            # Find contract document
            contract = ContractDocument.query.filter_by(envelope_id=envelope_id).first()
            if not contract:
                app.logger.warning(f"Contract not found for envelope: {envelope_id}")
                continue
            
            # Update contract status
            old_status = contract.status
            contract.status = status
            contract.updated_at = datetime.utcnow()
            
            # Handle completed documents
            if status == 'completed':
                docusign_manager.handle_document_completion(contract)
            elif status == 'declined':
                contract.declined_at = datetime.utcnow()
                user = User.query.get(contract.user_id)
                if user and user.contractor_profile:
                    user.contractor_profile.status = 'suspended'
                    user.contractor_profile.suspension_reason = f'Declined required document: {contract.document_type}'
            elif status == 'voided':
                contract.voided_at = datetime.utcnow()
            
            db.session.commit()
            app.logger.info(f"Contract {contract.id} status: {old_status} → {status}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        app.logger.error(f"DocuSign webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@app.route('/docusign/simulate-completion/<int:contract_id>')
@login_required
def simulate_document_completion(contract_id):
    """Simulate document completion for testing"""
    if app.config.get('FLASK_ENV') != 'development':
        return "Not available in production", 403
    
    contract = ContractDocument.query.get_or_404(contract_id)
    
    # Simulate completion
    docusign_manager.handle_document_completion(contract)
    
    flash(f'Document {contract.document_name} marked as completed!', 'success')
    return redirect(url_for('contractor_documents_required'))

@app.route('/contractor/documents/status')
@login_required
def contractor_documents_status():
    """API endpoint for document status"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check document requirements
    documents_complete, missing_docs = docusign_manager.require_contractor_documents(user)
    
    pending_contracts = ContractDocument.query.filter_by(
        user_id=user.id
    ).filter(ContractDocument.status.in_(['sent', 'delivered'])).all()
    
    completed_contracts = ContractDocument.query.filter_by(
        user_id=user.id,
        status='completed'
    ).all()
    
    return jsonify({
        'documents_complete': documents_complete,
        'missing_documents': missing_docs if isinstance(missing_docs, list) else [missing_docs],
        'pending_count': len(pending_contracts),
        'completed_count': len(completed_contracts)
    })

# Apply document requirements to critical contractor routes
original_contractor_profile = app.view_functions.get('contractor_profile')
if original_contractor_profile:
    app.view_functions['contractor_profile'] = require_contractor_documents('profile_activation')(original_contractor_profile)

@app.before_request
def check_contractor_document_requirements():
    """Check document requirements before contractor actions"""
    
    # Skip for static files and certain routes
    if (request.endpoint and 
        (request.endpoint.startswith('static') or 
         request.endpoint in ['login', 'register', 'docusign_webhook', 'contractor_documents_required', 'contractor_documents_status'])):
        return
    
    # Routes that require contractor document compliance
    contractor_routes = [
        'accept_job',
        'submit_quote', 
        'contractor_projects',
        'upload_work_photos',
        'request_payment'
    ]
    
    if request.endpoint in contractor_routes and 'user_id' in session:
        user = User.query.get(session['user_id'])
        
        if user and user.contractor_profile:
            # Check document requirements
            documents_complete, missing_docs = docusign_manager.require_contractor_documents(user)
            
            if not documents_complete:
                flash(f'Required documents pending: {missing_docs}', 'warning')
                return redirect(url_for('contractor_documents_required'))

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

# Import comprehensive document system after app is defined
# NOTE: Commented out for testing - comprehensive_documents module not found
# from comprehensive_documents import (
#     comprehensive_doc_manager, 
#     require_documents_for_action, 
#     job_acceptance_context,
#     payment_context,
#     job_posting_context
# )

# Import comprehensive document routes to activate protection
# NOTE: Commented out for testing - comprehensive_document_routes module not found
# import comprehensive_document_routes
# Import document enforcement middleware to protect all routes
# NOTE: Commented out for testing - document_enforcement_middleware module not found
# import document_enforcement_middleware

# =============================================================================
# CONSENT AND COOKIE MANAGEMENT SYSTEM
# =============================================================================

@app.route('/consent')
def consent_gateway():
    """Cookie and terms consent gateway"""
    return render_template('consent_gateway.html')

@app.route('/consent/submit', methods=['POST'])
def submit_consent():
    """Process user consent submission with granular controls"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            consent_data = request.get_json()
            email = consent_data.get('email', '')
        else:
            # Form data submission
            email = request.form.get('email', '')
            consent_data_str = request.form.get('consent_data', '{}')
            try:
                consent_data = json.loads(consent_data_str)
            except:
                # Fallback to individual form fields
                consent_data = {}
                for key in request.form.keys():
                    if key != 'email' and key != 'consent_data':
                        consent_data[key] = request.form.get(key) == 'true'
        
        print(f"DEBUG: Consent submission - Email: {email}, Data: {consent_data}")
        
        # Validate required consents (essential only)
        required_consents = ['terms_required', 'privacy_required', 'cookie_policy', 'data_usage']
        missing_consents = []
        for consent_type in required_consents:
            if not consent_data.get(consent_type, False):
                missing_consents.append(consent_type)
        
        if missing_consents:
            error_msg = f'Required consent missing: {", ".join(missing_consents)}'
            print(f"DEBUG: Missing consents: {error_msg}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'required': True
                }), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('consent_gateway'))
        
        # Get user ID
        user_id = current_user.id if current_user.is_authenticated else None
        
        try:
            # Create consent record with all preferences
            consent_record = UserConsent(
                user_id=user_id,
                session_id=session.get('session_id', request.cookies.get('session')),
                ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                user_agent=request.headers.get('User-Agent'),
                
                # Required consents
                cookies_essential=True,  # Always required
                terms_of_service=consent_data.get('terms_required', False),
                privacy_policy=consent_data.get('privacy_required', False),
                data_collection=consent_data.get('data_usage', False),
                safety_verification=True,  # Always required for platform function
                
                # Optional consents
                marketing_communications=consent_data.get('marketing_emails', False),
                personalization=False,  # Not used in new form
                market_research=consent_data.get('data_monetization', False),
                cookies_analytics=consent_data.get('analytics_cookies', False),
                cookies_marketing=consent_data.get('marketing_emails', False),
                
                # Metadata
                consent_method='gateway',
                consent_version='4.0',
                consent_data=consent_data,
                granted_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiry
            )
            
            # Save to database if available
            if user_id:
                # Remove old consent records for this user
                UserConsent.query.filter_by(user_id=user_id).delete()
            
            db.session.add(consent_record)
            db.session.commit()
            print("DEBUG: Consent record saved to database")
            
        except Exception as db_error:
            print(f"DEBUG: Database error (continuing): {db_error}")
            # Continue without database - store in session only
        
        # Store consent in session for immediate use
        session['consent_granted'] = True
        session['consent_timestamp'] = datetime.utcnow().isoformat()
        session['consent_preferences'] = {
            'marketing': consent_data.get('marketing_emails', False),
            'personalization': False,  # Not used in simplified form
            'analytics': consent_data.get('analytics_cookies', False),
            'data_monetization': consent_data.get('data_monetization', False)
        }
        
        print("DEBUG: Consent stored in session successfully")
        
        # Determine redirect URL
        redirect_url = session.pop('intended_url', url_for('main_dashboard'))
        
        if request.is_json:
            # JSON response for AJAX
            response_data = {
                'success': True,
                'message': 'Consent preferences saved successfully',
                'redirect_url': redirect_url,
                'features_enabled': {
                    'core_platform': True,
                    'marketing_communications': consent_data.get('marketing_emails', False),
                    'personalization': False,  # Simplified form doesn't use this
                    'analytics': consent_data.get('analytics_cookies', False),
                    'data_monetization': consent_data.get('data_monetization', False)
                }
            }
            
            response = jsonify(response_data)
            # Set consent cookie
            response.set_cookie('consent_granted', 'true', max_age=31536000)  # 1 year
            return response
        else:
            # Form submission - redirect
            flash('Consent preferences saved successfully!', 'success')
            response = redirect(redirect_url)
            response.set_cookie('consent_granted', 'true', max_age=31536000)  # 1 year
            return response
            
    except Exception as e:
        error_msg = f"Error processing consent: {str(e)}"
        print(f"DEBUG: {error_msg}")
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('consent_gateway'))
        
        response = jsonify(response_data)
        
        # Set long-term consent cookie
        response.set_cookie(
            'laborlooker_consent', 
            'granted', 
            max_age=365*24*60*60,  # 1 year
            secure=True, 
            httponly=True,
            samesite='Strict'
        )
        
        return response
        
    except Exception as e:
        app.logger.error(f"Consent submission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process consent. Please try again.',
            'technical_error': str(e) if app.debug else None
        }), 500

# =============================================================================
# SWIPE-BASED MATCHING SYSTEM
# =============================================================================

@app.route('/swipe')
@login_required
def swipe_system():
    """Main swipe interface - dating app style matching"""
    if current_user.account_type not in ['customer', 'contractor']:
        flash('Swipe matching is only available for customers and contractors.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get user's current matches count
    user_matches = SwipeMatch.query.filter(
        db.or_(
            SwipeMatch.user1_id == current_user.id,
            SwipeMatch.user2_id == current_user.id
        ),
        SwipeMatch.status == 'active'
    ).count()
    
    return render_template('swipe_system.html', matches_count=user_matches)

@app.route('/matches')
@login_required
def swipe_matches():
    """View all user's matches"""
    if current_user.account_type not in ['customer', 'contractor']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get user's matches
    matches = SwipeMatch.query.filter(
        db.or_(
            SwipeMatch.user1_id == current_user.id,
            SwipeMatch.user2_id == current_user.id
        )
    ).order_by(SwipeMatch.matched_at.desc()).all()
    
    # Enhance matches with additional data
    enhanced_matches = []
    for match in matches:
        other_user = match.user2 if match.user1_id == current_user.id else match.user1
        
        # Get context data (job posting or work request)
        if match.context_type == 'job_application':
            job_posting = JobPosting.query.get(match.context_id)
            match.job_posting = job_posting
        elif match.context_type == 'contractor_search':
            work_request = WorkRequest.query.get(match.context_id)
            match.work_request = work_request
        
        if current_user.account_type == 'customer':
            match.contractor = other_user
        else:
            match.job_seeker = other_user
            
        enhanced_matches.append(match)
    
    return render_template('swipe_matches.html', matches=enhanced_matches, now=datetime.utcnow)

@app.route('/api/swipe/contractors', methods=['POST'])
@login_required
def api_swipe_contractors():
    """Get contractors for customer swiping"""
    if current_user.account_type != 'customer':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        filters = request.get_json() or {}
        offset = filters.get('offset', 0)
        limit = 10
        
        # Get contractors that user hasn't swiped on yet
        swiped_contractor_ids = db.session.query(SwipeAction.target_id).filter(
            SwipeAction.swiper_id == current_user.id,
            SwipeAction.context_type == 'contractor_search'
        ).subquery()
        
        query = User.query.filter(
            User.account_type == 'contractor',
            ~User.id.in_(swiped_contractor_ids)
        ).join(User.professional_profile)
        
        # Apply filters
        if filters.get('location'):
            query = query.filter(ProfessionalProfile.geographic_area == filters['location'])
        
        if filters.get('service'):
            query = query.filter(ProfessionalProfile.services.contains(filters['service']))
        
        if filters.get('min_rating'):
            # In production, implement proper rating filter with subquery
            pass
        
        contractors = query.offset(offset).limit(limit).all()
        
        # Format contractor data for cards
        cards = []
        for contractor in contractors:
            profile = contractor.professional_profile
            if profile:
                # Calculate rating (simplified - in production, use proper aggregation)
                rating_data = calculate_user_rating_template(contractor.id)
                average_rating = rating_data[0] if rating_data[0] else 0
                total_ratings = rating_data[1] if rating_data[1] else 0
                
                cards.append({
                    'id': contractor.id,
                    'business_name': profile.business_name,
                    'contact_name': profile.contact_name,
                    'location': profile.location,
                    'geographic_area': profile.geographic_area,
                    'services': profile.services,
                    'experience_level': contractor.experience_level,
                    'billing_plan': profile.billing_plan,
                    'average_rating': average_rating,
                    'total_ratings': total_ratings,
                    'context_id': None  # Could be work request ID if applicable
                })
        
        return jsonify({
            'success': True,
            'cards': cards,
            'has_more': len(contractors) == limit
        })
        
    except Exception as e:
        print(f"Error loading contractors: {e}")
        return jsonify({'success': False, 'error': 'Error loading contractors'}), 500

@app.route('/api/swipe/jobs', methods=['POST'])
@login_required
def api_swipe_jobs():
    """Get job postings for contractor swiping"""
    if current_user.account_type != 'contractor':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        filters = request.get_json() or {}
        offset = filters.get('offset', 0)
        limit = 10
        
        # Get jobs that user hasn't swiped on yet
        swiped_job_ids = db.session.query(SwipeAction.context_id).filter(
            SwipeAction.swiper_id == current_user.id,
            SwipeAction.context_type == 'job_application'
        ).subquery()
        
        query = JobPosting.query.filter(
            JobPosting.status == 'active',
            ~JobPosting.id.in_(swiped_job_ids)
        )
        
        # Apply filters
        if filters.get('location'):
            query = query.filter(JobPosting.location.contains(filters['location']))
        
        if filters.get('service'):
            query = query.filter(JobPosting.labor_category == filters['service'])
        
        jobs = query.offset(offset).limit(limit).all()
        
        # Format job data for cards
        cards = []
        for job in jobs:
            cards.append({
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'labor_category': job.labor_category,
                'location': job.location,
                'pay_type': job.pay_type,
                'pay_amount': job.pay_amount,
                'pay_range_min': job.pay_range_min,
                'pay_range_max': job.pay_range_max,
                'experience_level': job.experience_level,
                'job_type': job.job_type,
                'requirements': job.requirements,
                'context_id': job.id
            })
        
        return jsonify({
            'success': True,
            'cards': cards,
            'has_more': len(jobs) == limit
        })
        
    except Exception as e:
        print(f"Error loading jobs: {e}")
        return jsonify({'success': False, 'error': 'Error loading jobs'}), 500

@app.route('/api/swipe/action', methods=['POST'])
@login_required
def api_swipe_action():
    """Process a swipe action"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'like', 'pass', 'super_like'
        target_id = data.get('target_id')
        context_type = data.get('context_type')  # 'contractor_search', 'job_application'
        context_id = data.get('context_id')
        
        if not all([action, target_id, context_type]):
            return jsonify({'success': False, 'error': 'Missing required data'}), 400
        
        # Record swipe action
        swipe_action = SwipeAction(
            swiper_id=current_user.id,
            target_id=target_id,
            swipe_type=action,
            context_type=context_type,
            context_id=context_id,
            preview_data_shown=json.dumps(data.get('preview_data', {}))
        )
        db.session.add(swipe_action)
        
        # Check for mutual match if this was a 'like' or 'super_like'
        is_match = False
        match_data = None
        
        if action in ['like', 'super_like']:
            # Check if target user has also liked this user
            mutual_swipe = SwipeAction.query.filter(
                SwipeAction.swiper_id == target_id,
                SwipeAction.target_id == current_user.id,
                SwipeAction.swipe_type.in_(['like', 'super_like']),
                SwipeAction.context_type == context_type,
                SwipeAction.context_id == context_id
            ).first()
            
            if mutual_swipe:
                # Create match
                match = SwipeMatch(
                    user1_id=min(current_user.id, target_id),
                    user2_id=max(current_user.id, target_id),
                    context_type=context_type,
                    context_id=context_id,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(match)
                
                is_match = True
                target_user = User.query.get(target_id)
                
                if context_type == 'contractor_search':
                    match_data = {
                        'id': target_user.id,
                        'business_name': target_user.professional_profile.business_name if target_user.professional_profile else target_user.email,
                        'contact_name': target_user.professional_profile.contact_name if target_user.professional_profile else target_user.email
                    }
                else:
                    job_posting = JobPosting.query.get(context_id)
                    match_data = {
                        'id': job_posting.id,
                        'title': job_posting.title,
                        'company': target_user.email  # In production, get company name
                    }
        
        db.session.commit()
        
        # Get total matches count
        total_matches = SwipeMatch.query.filter(
            db.or_(
                SwipeMatch.user1_id == current_user.id,
                SwipeMatch.user2_id == current_user.id
            ),
            SwipeMatch.status == 'active'
        ).count()
        
        return jsonify({
            'success': True,
            'match': is_match,
            'match_data': match_data,
            'total_matches': total_matches
        })
        
    except Exception as e:
        print(f"Error processing swipe action: {e}")
        return jsonify({'success': False, 'error': 'Error processing swipe'}), 500

@app.route('/api/matches/<int:match_id>/unmatch', methods=['POST'])
@login_required
def api_unmatch_user(match_id):
    """Unmatch a user"""
    try:
        match = SwipeMatch.query.filter(
            SwipeMatch.id == match_id,
            db.or_(
                SwipeMatch.user1_id == current_user.id,
                SwipeMatch.user2_id == current_user.id
            )
        ).first()
        
        if not match:
            return jsonify({'success': False, 'error': 'Match not found'}), 404
        
        match.status = 'declined'
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error unmatching: {e}")
        return jsonify({'success': False, 'error': 'Error unmatching'}), 500

@app.route('/api/matches/<int:match_id>/reactivate', methods=['POST'])
@login_required
def api_reactivate_match(match_id):
    """Reactivate an expired match"""
    try:
        match = SwipeMatch.query.filter(
            SwipeMatch.id == match_id,
            db.or_(
                SwipeMatch.user1_id == current_user.id,
                SwipeMatch.user2_id == current_user.id
            )
        ).first()
        
        if not match:
            return jsonify({'success': False, 'error': 'Match not found'}), 404
        
        match.status = 'active'
        match.expires_at = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error reactivating match: {e}")
        return jsonify({'success': False, 'error': 'Error reactivating match'}), 500

# DocuSign Integration - Global Import with Fallback
try:
    from docusign_integration import ContractManager
    DOCUSIGN_AVAILABLE = True
    print("DocuSign integration loaded successfully")
except ImportError:
    print("Warning: DocuSign integration not available, using fallback")
    DOCUSIGN_AVAILABLE = False
    
    # Fallback ContractManager class
    class ContractManager:
        def __init__(self):
            pass
        
        def get_user_contracts(self, user_id):
            return []
        
        def check_compliance_status(self, user_id):
            return True, "DocuSign integration temporarily unavailable"
        
        def require_contractor_documents(self, user):
            return True, "DocuSign integration temporarily unavailable"
        
        def send_contractor_agreement(self, user):
            return None, "DocuSign integration temporarily unavailable"
        
        def send_client_terms(self, user):
            return None, "DocuSign integration temporarily unavailable"

# Initialize consent middleware
try:
    from consent_manager import ConsentManager
    print("Consent manager loaded successfully")
except ImportError as e:
    print(f"Warning: Consent manager not found: {e}")
    ConsentManager = None
def init_db():
    """Initialize database with error handling"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        # If PostgreSQL fails, update the URI and try again
        if "postgres" in str(e).lower() or "psycopg2" in str(e).lower():
            print("PostgreSQL connection failed, switching to SQLite...")
            # Update the database URI directly
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "referral.db")
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_pre_ping": True,
                "connect_args": {"check_same_thread": False}
            }
            try:
                # Try creating tables again with SQLite
                with app.app_context():
                    db.create_all()
                print("SQLite database created successfully")
            except Exception as fallback_error:
                print(f"SQLite fallback also failed: {fallback_error}")

# Initialize database
try:
    init_db()
    print("✅ Database initialization completed successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")

# Print route registration status for debugging
print("🔧 Debugging route registration...")
try:
    with app.app_context():
        routes = list(app.url_map.iter_rules())
        print(f"📊 Total routes registered: {len(routes)}")
        
        # Check for critical routes
        critical_routes = ['/consent', '/login', '/register', '/dashboard']
        found_routes = []
        for rule in routes:
            if str(rule) in critical_routes or any(cr in str(rule) for cr in critical_routes):
                found_routes.append(str(rule))
        
        if found_routes:
            print(f"✅ Found critical routes: {found_routes}")
        else:
            print("❌ Critical routes not found!")
            print("📋 First 10 registered routes:")
            for rule in routes[:10]:
                print(f"  {rule}")
                
except Exception as e:
    print(f"❌ Route debugging failed: {e}")

print("🚀 Application startup complete - v1.1")
