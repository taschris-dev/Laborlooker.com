import os
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

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import pandas as pd
import shortuuid
import qrcode
import paypalrestsdk

# Import our security modules
from id_verification import IDVerificationManager
from docusign_integration import DocuSignClient, ContractManager
from two_factor_auth import TwoFactorAuthManager
from enhanced_job_requirements import JobRequirementsValidator, JobPostingEnhancer, require_enhanced_validation

# --- Paths / App setup ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
QR_DIR = os.path.join(BASE_DIR, "static", "qr")
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)


app = Flask(__name__)

# Production-ready configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Database configuration - supports SQLite (dev), PostgreSQL (production), and Google Cloud SQL
database_url = os.environ.get("DATABASE_URL")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

if cloud_sql_connection_name:
    # Google Cloud SQL configuration
    db_user = os.environ.get("DB_USER", "dbuser")
    db_password = os.environ.get("DB_PASSWORD", "SecurePassword123!")
    db_name = os.environ.get("DB_NAME", "referraldb")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
elif database_url:
    # Other production databases (Heroku, etc.)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Development database (SQLite)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "referral.db")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration
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

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": app.config["PAYPAL_MODE"],
    "client_id": app.config["PAYPAL_CLIENT_ID"],
    "client_secret": app.config["PAYPAL_CLIENT_SECRET"]
})

db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore
login_manager.login_message = "Please log in to access this page."

# Initialize security managers
two_factor_auth = TwoFactorAuthManager()

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
    except Exception as e:
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
    "exterior painting and staining", "crawl spaces", "landscaping"
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

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # developer, contractor, customer
    email_verified = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=False)  # For developer accounts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    contractor_profile = db.relationship("ContractorProfile", backref="user", uselist=False, cascade="all,delete")
    customer_profile = db.relationship("CustomerProfile", backref="user", uselist=False, cascade="all,delete")

class ContractorProfile(db.Model):
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
    
    # Enhanced job requirements fields
    title = db.Column(db.String(255))  # Job title
    budget = db.Column(db.Float)  # Estimated budget
    timeline = db.Column(db.String(255))  # Expected timeline
    image_count = db.Column(db.Integer, default=0)  # Number of uploaded images
    images_validated = db.Column(db.Boolean, default=False)  # Images meet requirements
    description_word_count = db.Column(db.Integer, default=0)  # Description word count
    complexity_level = db.Column(db.String(50))  # Low, Medium, High
    suggested_categories = db.Column(db.Text)  # JSON array of suggested categories
    estimated_duration_days = db.Column(db.Integer)  # Estimated project duration
    validation_errors = db.Column(db.Text)  # JSON array of validation errors
    validation_warnings = db.Column(db.Text)  # JSON array of validation warnings
    enhanced_validated = db.Column(db.Boolean, default=False)  # Meets enhanced requirements
    
    customer = db.relationship("User", foreign_keys=[customer_id], backref="customer_requests")
    contractor = db.relationship("User", foreign_keys=[contractor_id], backref="contractor_requests")

# Enhanced job requirements model for storing uploaded images
class JobImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # Original filename
    stored_filename = db.Column(db.String(255), nullable=False)  # Secure stored filename
    file_path = db.Column(db.String(500), nullable=False)  # Full file path
    file_size = db.Column(db.Integer)  # File size in bytes
    image_width = db.Column(db.Integer)  # Image width in pixels
    image_height = db.Column(db.Integer)  # Image height in pixels
    mime_type = db.Column(db.String(100))  # MIME type
    upload_order = db.Column(db.Integer, default=0)  # Order of upload
    is_primary = db.Column(db.Boolean, default=False)  # Primary/featured image
    description = db.Column(db.Text)  # Optional image description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    work_request = db.relationship("WorkRequest", backref=db.backref("job_images", cascade="all, delete-orphan"))

# Model for tracking job requirements validation history
class JobValidation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"), nullable=False)
    validation_type = db.Column(db.String(50), nullable=False)  # 'creation', 'edit', 'revalidation'
    is_valid = db.Column(db.Boolean, nullable=False)
    errors_count = db.Column(db.Integer, default=0)
    warnings_count = db.Column(db.Integer, default=0)
    errors_json = db.Column(db.Text)  # JSON array of error messages
    warnings_json = db.Column(db.Text)  # JSON array of warning messages
    validator_version = db.Column(db.String(50))  # Version of validation rules
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    
    work_request = db.relationship("WorkRequest", backref=db.backref("validations", cascade="all, delete-orphan"))
    validator = db.relationship("User", backref="performed_validations")

class ContractorInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contractor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    customer_email = db.Column(db.String(120))
    work_request_id = db.Column(db.Integer, db.ForeignKey("work_request.id"))
    invoice_number = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    sales_tax = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    commission_rate = db.Column(db.Float)
    commission_amount = db.Column(db.Float)
    contractor_amount = db.Column(db.Float)
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


# --- Helpers ---
def base_public_url() -> str:
    # For local demo; set BASE_URL if you expose publicly via a tunnel
    return os.environ.get("BASE_URL", "http://localhost:5000")


def generate_qr_png(data: str, filename: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(QR_DIR, filename)
    img.save(path)  # type: ignore
    return path


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
            
            # Check if 2FA is enabled
            from main import TwoFactorAuth
            two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
            
            if two_fa and two_fa.enabled:
                # Send 2FA token and redirect to verification
                token_record, error = two_factor_auth.create_2fa_token(user, 'email')
                if not error and token_record:
                    success, message = two_factor_auth.send_2fa_email(user, token_record.token)
                    if success:
                        session['2fa_user_id'] = user.id
                        flash("Please check your email for the verification code.", "info")
                        return redirect(url_for("two_factor_verify"))
                    else:
                        flash(f"Failed to send verification code: {message}", "error")
                        return redirect(url_for("login"))
                else:
                    flash(f"Failed to create verification code: {error}", "error")
                    return redirect(url_for("login"))
            else:
                # Regular login without 2FA
                login_user(user)
                flash(f"Welcome back, {user.email}!", "success")
                
                # Redirect based on account type
                if user.account_type == "developer":
                    return redirect(url_for("developer_dashboard"))
                elif user.account_type == "contractor":
                    return redirect(url_for("contractor_dashboard"))
                else:  # customer
                    return redirect(url_for("customer_dashboard"))
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("auth/login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        account_type = request.form.get("account_type")
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("register"))
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, "error")
            return redirect(url_for("register"))
        
        # Create user
        user = User(
            email=email,  # type: ignore
            password_hash=generate_password_hash(password),  # type: ignore
            account_type=account_type,  # type: ignore
            approved=account_type != "developer"  # type: ignore  # Auto-approve non-developers
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        send_verification_email(user)
        
        # For developer accounts, send approval request
        if account_type == "developer":
            send_developer_approval_email(user)
            flash("Developer account created! Please check your email for verification and wait for approval.", "success")
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

# --- Two-Factor Authentication Routes ---
@app.route("/two_factor_setup", methods=["GET", "POST"])
@login_required
def two_factor_setup():
    """Set up two-factor authentication"""
    if request.method == "POST":
        phone_number = request.form.get("phone_number")
        
        # Set up 2FA for the user
        backup_codes = two_factor_auth.setup_2fa_for_user(current_user, phone_number)
        
        if backup_codes:
            flash("Two-factor authentication has been enabled for your account.", "success")
            return render_template("two_factor/backup_codes.html", backup_codes=backup_codes)
        else:
            flash("Failed to set up two-factor authentication. Please try again.", "error")
    
    # Check if 2FA is already enabled
    from main import TwoFactorAuth
    existing_2fa = TwoFactorAuth.query.filter_by(user_id=current_user.id).first()
    
    return render_template("two_factor/setup.html", has_2fa=existing_2fa is not None)

@app.route("/two_factor_verify", methods=["GET", "POST"])
def two_factor_verify():
    """Verify 2FA token during login"""
    if request.method == "POST":
        token = request.form.get("token")
        backup_code = request.form.get("backup_code")
        user_id = session.get("2fa_user_id")
        
        if not user_id:
            flash("Session expired. Please log in again.", "error")
            return redirect(url_for("login"))
        
        user = User.query.get(user_id)
        if not user:
            flash("Invalid session. Please log in again.", "error")
            return redirect(url_for("login"))
        
        # Verify token or backup code
        if token and two_factor_auth.verify_2fa_token(user, token):
            # Complete login
            session.pop("2fa_user_id", None)
            login_user(user)
            flash(f"Welcome back, {user.email}!", "success")
            
            # Redirect based on account type
            if user.account_type == "developer":
                return redirect(url_for("developer_dashboard"))
            elif user.account_type == "contractor":
                return redirect(url_for("contractor_dashboard"))
            else:
                return redirect(url_for("customer_dashboard"))
                
        elif backup_code and two_factor_auth.verify_backup_code(user, backup_code):
            # Complete login with backup code
            session.pop("2fa_user_id", None)
            login_user(user)
            flash("Logged in using backup code. Consider regenerating backup codes.", "warning")
            
            # Redirect based on account type
            if user.account_type == "developer":
                return redirect(url_for("developer_dashboard"))
            elif user.account_type == "contractor":
                return redirect(url_for("contractor_dashboard"))
            else:
                return redirect(url_for("customer_dashboard"))
        else:
            flash("Invalid verification code. Please try again.", "error")
    
    return render_template("two_factor/verify.html")

@app.route("/two_factor_resend", methods=["POST"])
def two_factor_resend():
    """Resend 2FA token"""
    user_id = session.get("2fa_user_id")
    
    if not user_id:
        return jsonify({"success": False, "message": "Session expired"})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "Invalid session"})
    
    # Send new token
    token_record, error = two_factor_auth.create_2fa_token(user, 'email')
    if not error and token_record:
        success, message = two_factor_auth.send_2fa_email(user, token_record.token)
        if success:
            return jsonify({"success": True, "message": "New code sent to your email"})
        else:
            return jsonify({"success": False, "message": message})
    else:
        return jsonify({"success": False, "message": error or "Failed to create token"})

@app.route("/two_factor_disable", methods=["POST"])
@login_required
def two_factor_disable():
    """Disable two-factor authentication"""
    password = request.form.get("password")
    
    if not check_password_hash(current_user.password_hash, password):
        flash("Incorrect password. Cannot disable two-factor authentication.", "error")
        return redirect(url_for("two_factor_settings"))
    
    if two_factor_auth.disable_2fa_for_user(current_user):
        flash("Two-factor authentication has been disabled.", "success")
    else:
        flash("Failed to disable two-factor authentication.", "error")
    
    return redirect(url_for("two_factor_settings"))

@app.route("/two_factor_regenerate_codes", methods=["POST"])
@login_required
def two_factor_regenerate_codes():
    """Regenerate backup codes"""
    password = request.form.get("password")
    
    if not check_password_hash(current_user.password_hash, password):
        flash("Incorrect password. Cannot regenerate backup codes.", "error")
        return redirect(url_for("two_factor_settings"))
    
    backup_codes = two_factor_auth.regenerate_backup_codes(current_user)
    if backup_codes:
        flash("Backup codes have been regenerated. Old codes are no longer valid.", "success")
        return render_template("two_factor/backup_codes.html", backup_codes=backup_codes)
    else:
        flash("Failed to regenerate backup codes.", "error")
        return redirect(url_for("two_factor_settings"))

@app.route("/two_factor_settings")
@login_required
def two_factor_settings():
    """Two-factor authentication settings page"""
    from main import TwoFactorAuth
    two_fa = TwoFactorAuth.query.filter_by(user_id=current_user.id).first()
    
    return render_template("two_factor/settings.html", two_fa=two_fa)

# --- DocuSign Contract Integration Routes ---
@app.route("/contracts")
@login_required
def contracts_dashboard():
    """Contract management dashboard"""
    # Initialize DocuSign client
    docusign_client = DocuSignClient()
    contract_manager = ContractManager()
    
    # Get user's contracts
    user_contracts = contract_manager.get_user_contracts(current_user.id)
    
    # Get contract statistics
    stats = {
        'total': len(user_contracts),
        'pending': len([c for c in user_contracts if c['status'] == 'sent']),
        'completed': len([c for c in user_contracts if c['status'] == 'completed']),
        'voided': len([c for c in user_contracts if c['status'] == 'voided'])
    }
    
    return render_template("contracts/dashboard.html", 
                         contracts=user_contracts, 
                         stats=stats,
                         user_type=current_user.account_type)

@app.route("/contracts/new", methods=["GET", "POST"])
@login_required
def create_contract():
    """Create a new contract"""
    if request.method == "POST":
        contract_type = request.form.get("contract_type")
        recipient_email = request.form.get("recipient_email")
        recipient_name = request.form.get("recipient_name")
        project_details = request.form.get("project_details", "")
        
        # Initialize contract manager
        contract_manager = ContractManager()
        
        # Create contract based on type
        try:
            if contract_type == "contractor_agreement":
                envelope_id, error = contract_manager.create_contractor_agreement(
                    current_user, recipient_email, recipient_name, project_details
                )
            elif contract_type == "client_agreement":
                envelope_id, error = contract_manager.create_client_agreement(
                    current_user, recipient_email, recipient_name, project_details
                )
            elif contract_type == "project_contract":
                work_request_id = request.form.get("work_request_id")
                envelope_id, error = contract_manager.create_project_contract(
                    current_user, recipient_email, recipient_name, work_request_id, project_details
                )
            else:
                flash("Invalid contract type selected.", "error")
                return redirect(url_for("create_contract"))
                
            if envelope_id:
                flash("Contract sent successfully! Tracking ID: " + envelope_id, "success")
                return redirect(url_for("contracts_dashboard"))
            else:
                flash(f"Failed to send contract: {error}", "error")
                
        except Exception as e:
            flash(f"Error creating contract: {str(e)}", "error")
    
    # Get work requests for project contracts
    work_requests = []
    if current_user.account_type in ["contractor", "customer"]:
        if current_user.account_type == "contractor":
            work_requests = WorkRequest.query.filter_by(contractor_id=current_user.id).all()
        else:
            work_requests = WorkRequest.query.filter_by(customer_id=current_user.id).all()
    
    return render_template("contracts/new.html", 
                         work_requests=work_requests,
                         user_type=current_user.account_type)

@app.route("/contracts/<envelope_id>")
@login_required
def view_contract(envelope_id):
    """View contract details"""
    contract_manager = ContractManager()
    
    # Get contract details
    contract_details = contract_manager.get_contract_status(envelope_id)
    
    if not contract_details:
        flash("Contract not found or access denied.", "error")
        return redirect(url_for("contracts_dashboard"))
    
    return render_template("contracts/view.html", contract=contract_details)

@app.route("/contracts/<envelope_id>/download")
@login_required
def download_contract(envelope_id):
    """Download completed contract"""
    contract_manager = ContractManager()
    
    # Get contract document
    document_bytes, filename = contract_manager.download_completed_contract(envelope_id)
    
    if document_bytes:
        return send_file(
            BytesIO(document_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )
    else:
        flash("Contract not available for download.", "error")
        return redirect(url_for("view_contract", envelope_id=envelope_id))

@app.route("/contracts/<envelope_id>/void", methods=["POST"])
@login_required
def void_contract(envelope_id):
    """Void a contract"""
    reason = request.form.get("reason", "Voided by user")
    
    contract_manager = ContractManager()
    success, error = contract_manager.void_contract(envelope_id, reason)
    
    if success:
        flash("Contract has been voided successfully.", "success")
    else:
        flash(f"Failed to void contract: {error}", "error")
    
    return redirect(url_for("view_contract", envelope_id=envelope_id))

@app.route("/docusign/callback")
def docusign_callback():
    """Handle DocuSign OAuth callback"""
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        flash("DocuSign authorization failed.", "error")
        return redirect(url_for("contracts_dashboard"))
    
    # Store authorization code in session for later use
    session["docusign_auth_code"] = code
    flash("DocuSign authorization successful.", "success")
    
    return redirect(url_for("contracts_dashboard"))

@app.route("/contracts/templates")
@login_required
def contract_templates():
    """View available contract templates"""
    docusign_client = DocuSignClient()
    
    # Get available templates
    templates = docusign_client.get_templates()
    
    return render_template("contracts/templates.html", templates=templates)

@app.route("/contracts/webhook", methods=["POST"])
def docusign_webhook():
    """Handle DocuSign webhook notifications"""
    try:
        # Verify webhook authenticity (implement signature verification)
        data = request.get_json()
        
        # Process webhook events
        contract_manager = ContractManager()
        contract_manager.process_webhook_event(data)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

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
    except:
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
@app.route("/developer_dashboard")
@login_required
def developer_dashboard():
    if current_user.account_type != "developer":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get all users and statistics
    total_users = User.query.count()
    contractors = User.query.filter_by(account_type="contractor").count()
    customers = User.query.filter_by(account_type="customer").count()
    pending_approvals = User.query.filter_by(account_type="developer", approved=False).count()
    
    return render_template("dashboards/developer.html", 
                         total_users=total_users,
                         contractors=contractors,
                         customers=customers,
                         pending_approvals=pending_approvals)

@app.route("/contractor_dashboard")
@login_required
def contractor_dashboard():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get contractor's work requests and invoices
    work_requests = WorkRequest.query.filter_by(contractor_id=current_user.id).all()
    invoices = ContractorInvoice.query.filter_by(contractor_id=current_user.id).all()
    
    return render_template("dashboards/contractor.html",
                         work_requests=work_requests,
                         invoices=invoices)

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

@app.route("/contractor/invoice/new", methods=["GET", "POST"])
@login_required
def contractor_invoice_new():
    if current_user.account_type != "contractor":
        flash("Access denied.", "error")
        return redirect(url_for("login"))
    
    # Get contractor profile for commission rate
    profile = ContractorProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        # Get form data with validation
        customer_email = request.form.get("customer_email", "")
        work_request_id = request.form.get("work_request_id")
        description = request.form.get("description", "")
        subtotal_str = request.form.get("subtotal", "0")
        due_date = request.form.get("due_date")
        payment_terms = request.form.get("payment_terms", "")
        action = request.form.get("action", "draft")  # 'send' or 'draft'
        
        # Validate and convert subtotal
        try:
            subtotal = float(subtotal_str) if subtotal_str else 0.0
        except (ValueError, TypeError):
            flash("Invalid subtotal amount.", "error")
            return redirect(url_for("contractor_invoice_new"))
        
        # Calculate commission
        commission_rate = profile.commission_rate if profile else 10.0
        commission_amount = subtotal * (commission_rate / 100)
        contractor_amount = subtotal - commission_amount
        
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
        
        # Create invoice
        invoice = ContractorInvoice(
            contractor_id=current_user.id,
            customer_id=customer_id,
            customer_email=customer_email,
            work_request_id=int(work_request_id) if work_request_id else None,
            description=description,
            amount=subtotal,
            commission_amount=commission_amount,
            contractor_amount=contractor_amount,
            commission_rate=commission_rate,
            status="sent" if action == "send" else "draft",
            due_date=due_date_obj,
            payment_terms=payment_terms
        )
        
        try:
            db.session.add(invoice)
            db.session.commit()
            
            # Send email if action is 'send'
            if action == "send":
                send_invoice_email(invoice, customer_email)
                flash("Invoice created and sent successfully!", "success")
            else:
                flash("Invoice saved as draft!", "success")
                
            return redirect(url_for("contractor_invoices"))
        except Exception as e:
            db.session.rollback()
            flash("Error creating invoice. Please try again.", "error")
            print(f"Database error: {e}")
    
    return render_template("contractor/invoice_new.html", profile=profile)

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
    profile = ContractorProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        # Get form data
        business_name = request.form.get("business_name")
        contact_name = request.form.get("contact_name")
        phone = request.form.get("phone")
        location = request.form.get("location")
        geographic_area = request.form.get("geographic_area")
        service_radius = request.form.get("service_radius")
        billing_plan = request.form.get("billing_plan")
        bank_name = request.form.get("bank_name")
        routing_number = request.form.get("routing_number")
        account_number = request.form.get("account_number")
        work_hours = request.form.get("work_hours")
        
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
            profile = ContractorProfile(
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

# --- Developer Routes ---
# Note: billing_overview route already exists further down

# --- Original Dashboard (for backward compatibility) ---
@app.route("/")
def dashboard():
    # If user is logged in, redirect to their appropriate dashboard
    if current_user.is_authenticated:
        if current_user.account_type == "developer":
            return redirect(url_for("developer_dashboard"))
        elif current_user.account_type == "contractor":
            return redirect(url_for("contractor_dashboard"))
        else:  # customer
            return redirect(url_for("customer_dashboard"))
    
    # For non-authenticated users, show a welcome/landing page
    return render_template("welcome.html")


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


if __name__ == "__main__":
    # Ensure tables exist before first request
    with app.app_context():
        db.create_all()
    # For App Engine, use host='0.0.0.0' and port from environment
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

# For Google App Engine
# Create tables when the module is imported
try:
    with app.app_context():
        db.create_all()
except Exception:
    # Ignore errors during import - tables will be created on first request
    pass
