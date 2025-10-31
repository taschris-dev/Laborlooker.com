# Package LaborLooker for Sharing
# This script creates a clean, shareable version of the application

import os
import shutil
import zipfile
from datetime import datetime

def create_package():
    """Create a clean package of LaborLooker for sharing"""
    
    # Create package directory
    package_name = f"LaborLooker_Package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    package_dir = f"C:\\Users\\{os.getenv('USERNAME')}\\Desktop\\{package_name}"
    
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)
    
    # Essential files to include
    files_to_copy = [
        'main.py',           # Main application file
        'requirements.txt',   # Dependencies
        'README_SHARE.md',   # Documentation
        '.env.example',      # Environment template
        'app.yaml',          # Cloud deployment config
    ]
    
    # Directories to copy
    dirs_to_copy = [
        'templates',         # HTML templates
        'static',           # CSS, JS, images
    ]
    
    # Copy files
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
            print(f"✓ Copied {file}")
    
    # Copy directories
    for dir_name in dirs_to_copy:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(package_dir, dir_name))
            print(f"✓ Copied {dir_name}/ directory")
    
    # Create instance directory
    instance_dir = os.path.join(package_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    # Create setup instructions
    setup_content = """# LaborLooker Setup Instructions

## Quick Start (5 minutes)

1. **Install Python 3.11+** (if not already installed)
   - Download from: https://python.org

2. **Open Terminal/Command Prompt in this folder**

3. **Create Virtual Environment:**
   ```
   python -m venv .venv
   ```

4. **Activate Virtual Environment:**
   - Windows: `.venv\\Scripts\\activate`
   - Mac/Linux: `source .venv/bin/activate`

5. **Install Dependencies:**
   ```
   pip install -r requirements.txt
   ```

6. **Run Application:**
   ```
   python main.py
   ```

7. **Open Browser:** http://127.0.0.1:8080

## Features Ready to Demo

✅ Multi-user registration (Developer, Contractor, Customer)
✅ User authentication and dashboards
✅ Campaign creation and management
✅ Contact management system
✅ Invoice generation with commission calculation
✅ Email integration (configure .env for live email)
✅ PayPal payment processing (configure .env for live payments)
✅ QR code generation for campaigns
✅ File upload and processing
✅ Professional business logic

## Create Test Accounts

1. Register as Developer → Create campaigns
2. Register as Contractor → Handle work requests
3. Register as Customer → View services

## For Production Use

1. Copy `.env.example` to `.env`
2. Add your email and PayPal credentials
3. Deploy to Google Cloud with `gcloud app deploy`

---
**Professional Flask Application - Interview Ready!**
"""
    
    with open(os.path.join(package_dir, 'SETUP.md'), 'w') as f:
        f.write(setup_content)
    
    # Create zip file
    zip_path = f"{package_dir}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arc_name)
    
    print(f"\n🎉 Package created successfully!")
    print(f"📁 Location: {zip_path}")
    print(f"📧 Ready to email!")
    
    return zip_path

if __name__ == "__main__":
    create_package()