# 🚀 Marketing Technology Platform

A comprehensive SaaS platform for connecting local businesses with contractors through technology-driven marketing campaigns and CRM integration.

## 📋 Table of Contents

- [Features](#features)
- [Demo & Screenshots](#demo--screenshots)
- [Installation](#installation)
- [Usage](#usage)
- [Account Types](#account-types)
- [Architecture](#architecture)
- [Development](#development)
- [Deployment](#deployment)
- [Interview Demo](#interview-demo)

## ✨ Features

### 🎯 Core Platform Features
- **Multi-User System**: Developer, Contractor, and Customer accounts
- **Campaign Management**: QR codes, referral links, tracking analytics
- **CRM Integration**: Customer lists, prospect management, lead tracking
- **Work Scheduling**: Job management, calendar integration
- **Billing System**: Dual pricing models (commission-only vs subscription)
- **Invoice Management**: Automated billing, payment tracking
- **Analytics Dashboard**: ROI tracking, performance metrics

### 🔐 Authentication & Security
- **Secure Authentication**: 15+ character passwords with complexity requirements
- **Email Verification**: Account verification via email tokens
- **Role-Based Access**: Different interfaces and permissions per account type
- **Developer Approval**: Special approval process for admin accounts

### 💼 Business Model
- **Commission-Only Plan**: 10% commission per successful job
- **Subscription Plan**: 5% commission + $30/month subscription
- **Geographic Targeting**: Low Country, Midlands, Upstate regions
- **Service Categories**: 25+ professional service categories

## 🎬 Demo & Screenshots

### Live Demo
```bash
# Start the application
python app.py
# Visit http://127.0.0.1:5000
```

### Account Types Demo
1. **Developer Dashboard**: Full platform administration
2. **Contractor Interface**: Work requests, invoicing, profile management
3. **Customer Portal**: Schedule work, billing, calendar view

## 🛠️ Installation

### Prerequisites
- Python 3.11+ 
- pip (Python package manager)

### Quick Start
```bash
# Clone or download the project
cd referral-engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized!')"

# Start the application
python app.py
```

## 🎯 Usage

### First Time Setup
1. **Start Application**: `python app.py`
2. **Create Developer Account**: 
   - Visit `/register`
   - Select "Developer" account type
   - Use email verification link (check console output)
3. **Access Full Platform**: Login with developer credentials

### Creating Test Accounts
```python
# Developer account for full access
Email: admin@example.com
Password: DevPassword123!
Type: Developer

# Contractor account for business testing
Email: contractor@example.com  
Password: ContractorPass456@
Type: Contractor

# Customer account for client testing
Email: customer@example.com
Password: CustomerPass789_
Type: Customer
```

## 👥 Account Types

### 🔧 Developer Account
**Purpose**: Platform administration and development
**Features**:
- Full platform access and user management
- Project download functionality  
- All billing and revenue data access
- System analytics and reports
- Legacy demo features access

**Access**: Requires email approval from taschris.executive@gmail.com

### 🏗️ Contractor Account  
**Purpose**: Service providers and professionals
**Features**:
- Business profile management
- Work request notifications
- Invoice creation and management
- Schedule and calendar integration
- Commission tracking (5% or 10%)

**Setup Requirements**:
- Business information and credentials
- Geographic service area selection
- Service category specification
- License and insurance verification
- Bank account for payments

### 🏠 Customer Account
**Purpose**: Clients requesting services
**Features**:
- Schedule work requests
- Billing portal and payment history
- Calendar view of appointments
- Message system with contractors
- Help and support portal

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask 3.0.3, Python 3.11+
- **Database**: SQLAlchemy with SQLite
- **Authentication**: Flask-Login, Werkzeug security
- **Frontend**: Jinja2 templates, TailwindCSS
- **File Processing**: Pandas (CSV), Pillow (QR codes)

### Project Structure
```
referral-engine/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── instance/             # Database and config files
├── static/              # CSS, images, QR codes
├── templates/           # HTML templates
│   ├── auth/           # Login, register pages
│   ├── dashboards/     # User-specific dashboards
│   └── *.html         # Feature pages
└── .venv/              # Virtual environment
```

## 🔧 Development

### Local Development
```bash
# Enable debug mode (automatic)
python app.py

# Manual database reset
python -c "
import os
os.remove('instance/referral.db') if os.path.exists('instance/referral.db') else None
from app import app, db
app.app_context().push()
db.create_all()
print('Database recreated!')
"
```

### Adding Features
1. **Database Changes**: Update models in `app.py`, recreate database
2. **New Routes**: Add to `app.py` with proper authentication decorators
3. **Templates**: Create in `templates/` following existing structure
4. **Styling**: Use TailwindCSS classes for consistency

## 🚀 Deployment

### Production Checklist
1. **Environment Variables**:
   ```bash
   export SECRET_KEY="your-production-secret-key"
   export FLASK_ENV="production"
   ```

2. **Database Migration** (for production):
   ```bash
   # For PostgreSQL
   pip install psycopg2-binary
   # Update SQLALCHEMY_DATABASE_URI in app.py
   ```

3. **WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

### Cloud Deployment
- **Heroku**: Ready for `git push heroku main`
- **AWS/Google Cloud/Azure**: Compatible with all major platforms
- **Docker**: Containerization-ready

## 🎯 Interview Demo

### Business Model Demonstration
This platform showcases:
- **SaaS Architecture**: Multi-tenant with role-based access
- **Revenue Models**: Commission and subscription pricing  
- **Marketplace Functionality**: Connecting service providers with customers
- **Regional Business Logic**: Geographic-based contractor matching
- **Professional Services**: B2B marketplace for home services

### Technical Highlights
- **Full-Stack Development**: Python backend, responsive frontend
- **Security Best Practices**: Authentication, authorization, input validation
- **Database Design**: Normalized schema with proper relationships
- **User Experience**: Intuitive workflows for different user types
- **Scalable Architecture**: Production-ready design patterns

### Demo Script
1. **Business Overview**: Local services marketplace concept
2. **Authentication Demo**: Multiple account types with different access
3. **Customer Journey**: Schedule work, contractor matching process
4. **Contractor Tools**: Profile management, invoicing, work tracking
5. **Business Intelligence**: Revenue tracking, analytics, reporting
6. **Technical Discussion**: Architecture, scalability, deployment

### Key Demo Points
- **Problem Solved**: Connecting local businesses with qualified contractors
- **Market Opportunity**: Home services industry digitization
- **Revenue Model**: Platform takes commission on successful transactions
- **Technical Execution**: Modern web application with production considerations
- **Business Scalability**: Regional expansion and category growth potential

---

**Perfect for demonstrating full-stack development skills and business understanding**

This platform demonstrates comprehensive technical capabilities while solving real business problems in the local services marketplace.

For questions or support, contact: taschris.executive@gmail.com