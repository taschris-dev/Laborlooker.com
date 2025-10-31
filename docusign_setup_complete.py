"""
DocuSign Setup Guide for LaborLooker Platform
Complete step-by-step configuration instructions
"""

import os
from docusign_integration import DocuSignClient, ContractManager

def check_docusign_requirements():
    """Check if all DocuSign requirements are met"""
    print("🔍 Checking DocuSign Requirements...")
    
    # Check required environment variables
    required_vars = [
        'DOCUSIGN_CLIENT_ID',
        'DOCUSIGN_ACCOUNT_ID', 
        'DOCUSIGN_USER_ID',
        'DOCUSIGN_PRIVATE_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_docusign_connection():
    """Test DocuSign API connection"""
    print("\n🔗 Testing DocuSign Connection...")
    
    try:
        client = DocuSignClient()
        token = client.get_access_token()
        
        if token:
            print("✅ DocuSign authentication successful")
            print(f"   Token length: {len(token)} characters")
            return True
        else:
            print("❌ Failed to get DocuSign access token")
            return False
            
    except Exception as e:
        print(f"❌ DocuSign connection failed: {str(e)}")
        return False

def test_template_access():
    """Test access to DocuSign templates"""
    print("\n📋 Testing Template Access...")
    
    try:
        contract_manager = ContractManager()
        templates = contract_manager.template_ids
        
        print("📋 Configured templates:")
        for template_type, template_id in templates.items():
            if template_id:
                print(f"   ✅ {template_type}: {template_id}")
            else:
                print(f"   ⚠️ {template_type}: Not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Template access failed: {str(e)}")
        return False

def setup_instructions():
    """Display setup instructions"""
    print("\n" + "="*60)
    print("📋 DOCUSIGN SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\n1️⃣ CREATE DOCUSIGN DEVELOPER ACCOUNT:")
    print("   • Go to https://developers.docusign.com/")
    print("   • Sign up for a developer account (free)")
    print("   • Complete email verification")
    
    print("\n2️⃣ CREATE INTEGRATION APPLICATION:")
    print("   • Log into DocuSign Admin")
    print("   • Go to Apps & Keys > Create App")
    print("   • Choose 'JWT Auth' or 'Authorization Code Grant'")
    print("   • App Name: 'LaborLooker Platform'")
    print("   • Copy Integration Key (this is your CLIENT_ID)")
    
    print("\n3️⃣ CONFIGURE AUTHENTICATION:")
    print("   • Generate RSA keypair in DocuSign admin")
    print("   • Copy private key content to DOCUSIGN_PRIVATE_KEY")
    print("   • Note your User ID from DocuSign admin")
    print("   • Set redirect URI: https://laborlooker.net/docusign/callback")
    
    print("\n4️⃣ SET PERMISSIONS:")
    print("   • Enable these scopes in your DocuSign app:")
    print("     ✅ signature")
    print("     ✅ impersonation") 
    print("     ✅ envelope_read")
    print("     ✅ envelope_write")
    print("     ✅ template_read")
    print("     ✅ template_write")
    print("     ✅ user_read")
    
    print("\n5️⃣ CREATE CONTRACT TEMPLATES:")
    print("   • Log into DocuSign web interface")
    print("   • Go to Templates > Create Template")
    print("   • Create these templates:")
    print("     📄 Contractor Agreement (DOCUSIGN_CONTRACTOR_TEMPLATE_ID)")
    print("     📄 Client Terms (DOCUSIGN_CLIENT_TEMPLATE_ID)")
    print("     📄 Project Contract (DOCUSIGN_PROJECT_TEMPLATE_ID)")
    print("     📄 NDA Agreement (DOCUSIGN_NDA_TEMPLATE_ID)")
    
    print("\n6️⃣ CONFIGURE ENVIRONMENT:")
    print("   • Copy values from docusign_config_template.txt")
    print("   • Set environment variables or create .env file")
    print("   • Update redirect URI for production deployment")
    
    print("\n7️⃣ DOMAIN VERIFICATION:")
    print("   • Add DNS TXT record for laborlooker.net domain claiming")
    print("   • Format: TXT record with DocuSign verification string")
    
    print("\n8️⃣ TEST INTEGRATION:")
    print("   • Run: python docusign_setup_complete.py")
    print("   • Verify all tests pass before going live")

def main():
    """Main setup verification"""
    print("🚀 DocuSign Integration Setup for LaborLooker")
    print("=" * 50)
    
    # Check if environment is configured
    if not check_docusign_requirements():
        setup_instructions()
        return
    
    # Test connection
    if not test_docusign_connection():
        print("\n❌ Setup incomplete - connection failed")
        return
    
    # Test templates
    test_template_access()
    
    print("\n" + "="*50)
    print("🎉 DOCUSIGN SETUP STATUS")
    print("="*50)
    print("✅ Environment variables configured")
    print("✅ API connection working")
    print("✅ Ready for contract management")
    
    print("\n📋 NEXT STEPS:")
    print("1. Create contract templates in DocuSign admin")
    print("2. Update template IDs in environment variables")
    print("3. Test contract sending with real users")
    print("4. Deploy to production with live credentials")
    
    print("\n🔐 SECURITY NOTES:")
    print("• Never commit private keys to version control")
    print("• Use environment variables for all credentials")
    print("• Enable webhook signature verification")
    print("• Monitor DocuSign usage and billing")

if __name__ == "__main__":
    main()