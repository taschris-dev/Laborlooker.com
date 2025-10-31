#!/usr/bin/env python3
"""
Package Verification Script
Checks if the Marketing Technology Platform is properly installed and configured.
"""

import os
import sys
import importlib

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major != 3 or version.minor < 8:
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_virtual_environment():
    """Check if running in virtual environment."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
        return True
    print("⚠️  Not running in virtual environment (recommended)")
    return True

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'werkzeug',
        'pandas',
        'qrcode',
        'PIL'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                importlib.import_module('PIL')
            else:
                importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - not installed")
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def check_files():
    """Check if all required files exist."""
    required_files = [
        'app.py',
        'requirements.txt',
        'README.md',
        'setup.py',
        'templates/base.html',
        'templates/dashboard.html',
        'templates/auth/login.html',
        'templates/auth/register.html',
        'static/styles.css'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0, missing_files

def check_database():
    """Check if database can be initialized."""
    try:
        # Try to import and initialize the app
        sys.path.insert(0, os.getcwd())
        from app import app, db
        
        with app.app_context():
            # Check if database file exists or can be created
            db_path = os.path.join('instance', 'referral.db')
            if os.path.exists(db_path):
                print(f"✅ Database exists: {db_path}")
            else:
                print(f"ℹ️  Database will be created: {db_path}")
            
            # Try to create tables
            db.create_all()
            print("✅ Database tables can be created")
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_app_startup():
    """Check if the app can start without errors."""
    try:
        sys.path.insert(0, os.getcwd())
        from app import app
        
        with app.app_context():
            # Basic app configuration check
            if app.config.get('SECRET_KEY'):
                print("✅ Secret key configured")
            else:
                print("⚠️  No secret key configured (will use default)")
            
            print(f"✅ App can initialize (Debug: {app.debug})")
        
        return True
    except Exception as e:
        print(f"❌ App startup error: {e}")
        return False

def run_verification():
    """Run all verification checks."""
    print("🔍 Marketing Technology Platform - Package Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", lambda: check_dependencies()[0]),
        ("Required Files", lambda: check_files()[0]),
        ("Database", check_database),
        ("App Startup", check_app_startup)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Your application is ready to run.")
        print("\n🚀 To start the application:")
        print("   python app.py")
        print("   Then visit: http://localhost:5000")
    else:
        print("⚠️  Some issues found. Please review the output above.")
        
        # Suggest fixes for common issues
        print("\n🔧 Common Fixes:")
        if not check_dependencies()[0]:
            print("   - Install dependencies: pip install -r requirements.txt")
        if not check_files()[0]:
            print("   - Ensure all files are present and paths are correct")
        print("   - Run setup.py if not already done: python setup.py")
    
    return passed == total

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)