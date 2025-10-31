#!/usr/bin/env python3
"""
DocuSign Integration Verification Script
Tests all components of the DocuSign integration to ensure everything is properly configured.
"""

import os
import sys

def test_imports():
    """Test that all required packages are installed."""
    print("🔍 Testing Python package imports...")
    
    try:
        import jwt  # noqa: F401
        print("✅ PyJWT package available")
    except ImportError:
        print("❌ PyJWT package missing - run: pip install PyJWT==2.8.0")
        return False
        
    try:
        import docusign_esign  # noqa: F401
        print("✅ DocuSign eSign SDK available")
    except ImportError:
        print("❌ DocuSign SDK missing - run: pip install docusign-esign==3.24.0")
        return False
        
    try:
        from cryptography.hazmat.primitives import serialization  # noqa: F401
        print("✅ Cryptography package available")
    except ImportError:
        print("❌ Cryptography package missing - run: pip install cryptography==41.0.7")
        return False
        
    return True

def test_files():
    """Test that all required files exist."""
    print("\n📂 Testing required files...")
    
    required_files = [
        'docusign_integration.py',
        'docusign_private_key.txt',
        '.env.example',
        'main.py',
        'templates/contracts'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_environment():
    """Test environment configuration."""
    print("\n⚙️  Testing environment configuration...")
    
    if os.path.exists('.env'):
        print("✅ .env file exists")
        
        # Check for DocuSign variables
        with open('.env', 'r') as f:
            env_content = f.read()
            
        required_vars = [
            'DOCUSIGN_INTEGRATION_KEY',
            'DOCUSIGN_USER_ID', 
            'DOCUSIGN_ACCOUNT_ID'
        ]
        
        configured_vars = []
        for var in required_vars:
            if var in env_content and 'your-actual-' not in env_content:
                configured_vars.append(var)
                print(f"✅ {var} configured")
            else:
                print(f"❌ {var} needs configuration")
        
        if len(configured_vars) == len(required_vars):
            print("✅ All environment variables configured")
            return True
        else:
            print(f"❌ {len(required_vars) - len(configured_vars)} environment variables need configuration")
            return False
    else:
        print("❌ .env file missing - copy from .env.example")
        return False

def test_docusign_integration():
    """Test DocuSign integration can be imported."""
    print("\n🔗 Testing DocuSign integration...")
    
    try:
        sys.path.append('.')
        from docusign_integration import DocuSignClient, ContractManager  # noqa: F401
        print("✅ DocuSign integration classes import successfully")
        
        # Test that we can create instances (will fail without real credentials)
        try:
            DocuSignClient()  # Test instantiation
            print("✅ DocuSignClient can be instantiated")
        except Exception as e:
            if "credentials" in str(e).lower() or "integration_key" in str(e).lower():
                print("⚠️  DocuSignClient needs real credentials (expected)")
            else:
                print(f"❌ DocuSignClient error: {e}")
                return False
                
        return True
    except ImportError as e:
        print(f"❌ DocuSign integration import failed: {e}")
        return False

def test_private_key():
    """Test private key file."""
    print("\n🔐 Testing private key configuration...")
    
    if os.path.exists('docusign_private_key.txt'):
        with open('docusign_private_key.txt', 'r') as f:
            key_content = f.read().strip()
            
        if key_content == "# Replace this file content with your actual DocuSign RSA private key":
            print("⚠️  Private key is still template - needs replacement with real key")
            return False
        elif 'BEGIN PRIVATE KEY' in key_content:
            print("✅ Private key file appears to contain real key")
            return True
        else:
            print("❌ Private key file format appears incorrect")
            return False
    else:
        print("❌ Private key file missing")
        return False

def main():
    """Run all tests and provide summary."""
    print("🚀 DocuSign Integration Verification\n")
    
    tests = [
        ("Package Imports", test_imports),
        ("Required Files", test_files), 
        ("Environment Config", test_environment),
        ("DocuSign Integration", test_docusign_integration),
        ("Private Key", test_private_key)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! DocuSign integration is ready to use.")
        print("\n🔥 Next steps:")
        print("   1. Start your Flask app: python main.py")
        print("   2. Go to http://localhost:5000/contracts")
        print("   3. Test contract creation and signing")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the issues above.")
        print("\n📋 Quick fixes:")
        if passed < 3:
            print("   1. Install missing packages: pip install -r requirements.txt")
        if 'Environment Config' in [tests[i][0] for i in range(len(tests)) if not tests[i][1]()]:
            print("   2. Configure .env file with your DocuSign credentials")
        if 'Private Key' in [tests[i][0] for i in range(len(tests)) if not tests[i][1]()]:
            print("   3. Replace docusign_private_key.txt with your actual private key")

if __name__ == "__main__":
    main()