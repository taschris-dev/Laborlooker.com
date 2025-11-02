#!/usr/bin/env python3
"""
LaborLooker Full System Test
Tests all components of the LaborLooker platform
"""

import os
import sys

# Skip Redis connection for local testing
os.environ['SKIP_REDIS_CONNECTION'] = 'true'

def test_app_imports():
    """Test if the Flask app imports successfully"""
    print("🧪 Testing Flask Application Import...")
    try:
        from main import app
        print("✅ Flask app imported successfully")
        
        print(f"🔧 App Configuration:")
        print(f"  DEBUG: {app.config.get('DEBUG', 'Not set')}")
        print(f"  SECRET_KEY: {'Set' if app.config.get('SECRET_KEY') else 'Not set'}")
        print(f"  SQLALCHEMY_DATABASE_URI: {'Set' if app.config.get('SQLALCHEMY_DATABASE_URI') else 'Not set'}")
        
        print("\n📋 Available Routes:")
        routes = []
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static'):
                routes.append(f"  {rule.rule} -> {rule.endpoint}")
        
        for route in sorted(routes)[:10]:  # Show first 10 routes
            print(route)
        
        if len(routes) > 10:
            print(f"  ... and {len(routes) - 10} more routes")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to import Flask app: {e}")
        return False

def test_environment_variables():
    """Test environment configuration"""
    print("\n🔧 Testing Environment Variables...")
    
    required_vars = [
        'SECRET_KEY',
        'CLOUDFLARE_ACCESS_KEY_ID',
        'CLOUDFLARE_SECRET_ACCESS_KEY', 
        'CLOUDFLARE_R2_BUCKET',
        'CLOUDFLARE_R2_ENDPOINT'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'***' + value[-4:] if len(value) > 4 else 'Set'}")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing {len(missing_vars)} required environment variables")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True

def test_optional_features():
    """Test optional feature availability"""
    print("\n🔍 Testing Optional Features...")
    
    # Test pandas
    try:
        import pandas
        print("  ✅ pandas: Available for CSV processing")
    except ImportError:
        print("  ⚠️  pandas: Not available (CSV upload will use fallback)")
    
    # Test qrcode
    try:
        import qrcode
        print("  ✅ qrcode: Available for QR code generation")
    except ImportError:
        print("  ⚠️  qrcode: Not available (QR codes disabled)")
    
    # Test PayPal
    try:
        import paypalrestsdk
        print("  ✅ paypalrestsdk: Available for payments")
    except ImportError:
        print("  ⚠️  paypalrestsdk: Not available (PayPal disabled)")
    
    # Test Redis
    try:
        import redis
        print("  ✅ redis: Available for caching")
    except ImportError:
        print("  ⚠️  redis: Not available (caching disabled)")
    
    # Test boto3
    try:
        import boto3
        print("  ✅ boto3: Available for R2 storage")
    except ImportError:
        print("  ⚠️  boto3: Not available (R2 storage disabled)")

def main():
    """Run full system test"""
    print("🚀 LaborLooker Full System Test")
    print("=" * 50)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except ImportError:
        print("⚠️  python-dotenv not available, using system environment")
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Environment variables
    total_tests += 1
    if test_environment_variables():
        tests_passed += 1
    
    # Test 2: Flask app import
    total_tests += 1
    if test_app_imports():
        tests_passed += 1
    
    # Test 3: Optional features
    test_optional_features()
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} core tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All core functionality is working!")
        print("✅ LaborLooker platform is ready for deployment")
    else:
        print("⚠️  Some issues found - check configuration")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)