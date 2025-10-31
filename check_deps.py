#!/usr/bin/env python3
"""
LaborLooker Dependency and Configuration Checker
Comprehensive check for missing dependencies and configuration issues
"""

print("🔍 LaborLooker Dependency & Configuration Checker")
print("=" * 60)

# Test 1: Core imports
print("\n📦 Testing Core Imports...")
try:
    import os
    import sys
    from datetime import datetime
    print("✅ Standard library imports: OK")
except Exception as e:
    print(f"❌ Standard library error: {e}")

# Test 2: Flask and extensions
print("\n🌐 Testing Flask Framework...")
try:
    from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
    from flask_sqlalchemy import SQLAlchemy
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    from werkzeug.security import generate_password_hash, check_password_hash
    print("✅ Flask framework: OK")
except Exception as e:
    print(f"❌ Flask error: {e}")

# Test 3: Data processing
print("\n📊 Testing Data Processing Libraries...")
try:
    import pandas as pd
    import numpy as np
    print("✅ Data processing: OK")
except Exception as e:
    print(f"❌ Data processing error: {e}")

# Test 4: QR code and image processing
print("\n🖼️ Testing Image Processing...")
try:
    import qrcode
    from PIL import Image
    print("✅ Image processing: OK")
except Exception as e:
    print(f"❌ Image processing error: {e}")

# Test 5: PayPal integration
print("\n💳 Testing PayPal Integration...")
try:
    import paypalrestsdk
    print("✅ PayPal SDK: OK")
except Exception as e:
    print(f"❌ PayPal error: {e}")

# Test 6: Email functionality
print("\n📧 Testing Email Functionality...")
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    print("✅ Email functionality: OK")
except Exception as e:
    print(f"❌ Email error: {e}")

# Test 7: Security and utilities
print("\n🔐 Testing Security & Utilities...")
try:
    from itsdangerous import URLSafeTimedSerializer
    import shortuuid
    print("✅ Security & utilities: OK")
except Exception as e:
    print(f"❌ Security error: {e}")

# Test 8: Environment loading
print("\n🌍 Testing Environment Configuration...")
try:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loading: OK (dotenv available)")
    except ImportError:
        print("⚠️ Environment loading: dotenv not available (OK for production)")
except Exception as e:
    print(f"❌ Environment error: {e}")

# Test 9: App import
print("\n🚀 Testing App Import...")
try:
    from app import app, db
    print("✅ App import: OK")
    
    # Test app configuration
    print(f"   Secret key set: {'✅' if app.config.get('SECRET_KEY') else '❌'}")
    print(f"   Database URI set: {'✅' if app.config.get('SQLALCHEMY_DATABASE_URI') else '❌'}")
    print(f"   Mail username set: {'✅' if app.config.get('MAIL_USERNAME') else '❌'}")
    print(f"   PayPal client ID set: {'✅' if app.config.get('PAYPAL_CLIENT_ID') else '❌'}")
    
except Exception as e:
    print(f"❌ App import error: {e}")

# Test 10: Database creation
print("\n🗄️ Testing Database Creation...")
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print("✅ Database creation: OK")
except Exception as e:
    print(f"❌ Database error: {e}")

print("\n" + "=" * 60)
print("🏁 Dependency check complete!")
print("\nIf all tests show ✅, your application is ready for deployment.")
print("If any show ❌, install the missing dependencies.")