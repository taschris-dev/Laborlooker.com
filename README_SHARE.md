# LaborLooker - Professional Multi-User Business Platform

## 🎯 Overview
LaborLooker is a comprehensive Flask-based web application designed for connecting local businesses through different media, marketing, and technology channels. Built for professional demonstration and real-world business use.

## ✨ Key Features

### 👥 Multi-User System
- **Developer Accounts**: Create and manage campaigns
- **Contractor Accounts**: Handle work requests and invoicing
- **Customer Accounts**: Access services and manage requests

### 📧 Email Integration
- Business email system (taschris.executive@gmail.com)
- Email verification for new accounts
- Automated invoice and notification emails
- Contact form submissions

### 💳 Payment Processing
- Live PayPal integration for invoicing
- Commission calculation (5% and 10% tiers)
- Subscription management ready
- Secure payment handling

### 📊 Campaign Management
- QR code generation for campaigns
- Click tracking and analytics
- Campaign assignment to contractors
- Real-time performance monitoring

### 🧾 Invoice System
- Professional invoice generation
- Automated commission calculations
- Payment tracking and status updates
- Customer and contractor dashboards

### 📄 File Processing
- CSV contact uploads
- PDF invoice generation
- Bulk contact management
- Data export capabilities

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment recommended

### Installation
1. Extract the project files
2. Open terminal in project directory
3. Create virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Run the application:
   ```bash
   python main.py
   ```
7. Open browser to: `http://127.0.0.1:8080`

## 🌟 Technical Highlights

### Backend
- **Flask 3.0.3** with modern architecture
- **SQLAlchemy** for robust database management
- **Flask-Login** for secure authentication
- **PayPal REST SDK** for payment processing
- **Pandas** for data processing
- **QRCode** generation for campaigns

### Frontend
- Professional, responsive design
- Clean HTML templates
- Modern CSS styling
- User-friendly interfaces

### Database
- SQLite for development (easily portable)
- Comprehensive relational schema
- User management with roles
- Campaign and contact tracking
- Invoice and payment records

### Security
- Password hashing with Werkzeug
- Session management
- Email verification
- Secure form handling

## 🎯 Business Logic

### Commission Structure
- **Free Tier**: 10% commission
- **Premium Tier**: 5% commission ($30/month)

### User Workflows
1. **Developer**: Creates campaigns, assigns contractors
2. **Contractor**: Accepts work, creates invoices, receives payments
3. **Customer**: Views services, makes payments, tracks requests

### Campaign Process
1. Developer creates campaign with QR code
2. QR code distributed for lead generation
3. Leads tracked and assigned to contractors
4. Work completed and invoiced through system

## 📊 Interview Demonstration Ready

This application showcases:
- ✅ Full-stack development skills
- ✅ Database design and relationships
- ✅ Payment system integration
- ✅ Email system implementation
- ✅ File processing capabilities
- ✅ Security best practices
- ✅ Professional UI/UX design
- ✅ Business logic implementation
- ✅ Scalable architecture

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```
SECRET_KEY=your-secret-key
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYPAL_MODE=sandbox
```

### Email Setup
- Uses Gmail SMTP
- Requires app password for authentication
- Configured for business communications

### PayPal Setup
- Supports both sandbox and live modes
- Configured for business account
- Ready for production transactions

## 🚀 Deployment Ready

The application includes:
- Google Cloud Platform configuration (`app.yaml`)
- Docker configuration (`Dockerfile`)
- Production-ready settings
- Scalable architecture

## 📱 Demo Accounts

Create test accounts for different user types:
1. **Developer**: Full campaign management access
2. **Contractor**: Work and invoice management
3. **Customer**: Service request and payment access

## 💼 Business Model

LaborLooker connects local businesses through:
- Digital marketing campaigns
- Lead generation systems
- Work request management
- Automated invoicing
- Payment processing
- Performance tracking

Perfect for demonstrating real-world business application development skills.

---

**Built with ❤️ for professional demonstration and real business use.**