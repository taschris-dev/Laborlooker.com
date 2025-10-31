#!/usr/bin/env python3
"""
Comprehensive Function Test for Referral Engine
Tests all major functionality to identify issues
"""

print("=== COMPREHENSIVE FUNCTION TEST ===")

# Test 1: Import test
print("\n1. Testing imports...")
try:
    from app import app, db, User, ContractorProfile, ContractorInvoice
    print("✅ Core imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Test 2: Database connection
print("\n2. Testing database connection...")
try:
    with app.app_context():
        db.create_all()
        print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test 3: Model creation test
print("\n3. Testing model creation...")
try:
    with app.app_context():
        # Test ContractorInvoice model
        test_invoice = ContractorInvoice(
            contractor_id=1,
            customer_email='test@example.com',
            description='Test invoice',
            amount=100.0,
            commission_rate=10.0,
            commission_amount=10.0,
            contractor_amount=90.0,
            status='draft'
        )
        print("✅ ContractorInvoice model creation successful")
        print(f"   Invoice amount: ${test_invoice.amount}")
        print(f"   Commission: ${test_invoice.commission_amount}")
        print(f"   Contractor gets: ${test_invoice.contractor_amount}")
except Exception as e:
    print(f"❌ Model creation error: {e}")

# Test 4: Email configuration
print("\n4. Testing email configuration...")
try:
    import os
    mail_password = os.getenv('MAIL_PASSWORD')
    mail_username = os.getenv('MAIL_USERNAME')
    if mail_password and mail_username:
        print("✅ Email environment variables configured")
        print(f"   Email: {mail_username}")
    else:
        print("⚠️ Email environment variables missing")
except Exception as e:
    print(f"❌ Email config error: {e}")

# Test 5: PayPal configuration
print("\n5. Testing PayPal configuration...")
try:
    import os
    paypal_client_id = os.getenv('PAYPAL_CLIENT_ID')
    paypal_client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
    if paypal_client_id and paypal_client_secret:
        print("✅ PayPal environment variables configured")
        print(f"   Client ID: {paypal_client_id[:10]}...")
    else:
        print("⚠️ PayPal environment variables missing")
except Exception as e:
    print(f"❌ PayPal config error: {e}")

# Test 6: Flask app configuration
print("\n6. Testing Flask app configuration...")
try:
    with app.app_context():
        print(f"✅ Flask app configured")
        print(f"   Debug mode: {app.debug}")
        print(f"   Secret key configured: {'SECRET_KEY' in app.config}")
except Exception as e:
    print(f"❌ Flask config error: {e}")

# Test 7: Template files
print("\n7. Testing template files...")
try:
    import os
    template_dir = "templates"
    if os.path.exists(template_dir):
        templates = os.listdir(template_dir)
        print(f"✅ Template directory exists with {len(templates)} files")
        
        # Check key templates
        key_templates = ['base.html', 'landing.html', 'dashboard.html']
        for template in key_templates:
            if template in templates:
                print(f"   ✅ {template} found")
            else:
                print(f"   ❌ {template} missing")
    else:
        print("❌ Template directory missing")
except Exception as e:
    print(f"❌ Template test error: {e}")

# Test 8: Static files
print("\n8. Testing static files...")
try:
    import os
    static_dir = "static"
    if os.path.exists(static_dir):
        static_files = os.listdir(static_dir)
        print(f"✅ Static directory exists with {len(static_files)} items")
        
        # Check for styles.css
        if 'styles.css' in static_files:
            print("   ✅ styles.css found")
        else:
            print("   ❌ styles.css missing")
            
        # Check for qr directory
        if 'qr' in static_files:
            print("   ✅ qr directory found")
        else:
            print("   ❌ qr directory missing")
    else:
        print("❌ Static directory missing")
except Exception as e:
    print(f"❌ Static files test error: {e}")

print("\n=== TEST SUMMARY ===")
print("If all tests show ✅, your application should work properly.")
print("If you see ❌ errors, those need to be fixed before the app will run.")
print("If you see ⚠️ warnings, the app will run but some features may not work.")