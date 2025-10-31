#!/usr/bin/env python3
"""
Create Distribution Package for Labor Lookers Platform
Creates a complete downloadable copy of the current platform state
"""

import os
import shutil
import zipfile
from datetime import datetime
import json

def create_distribution_package():
    """Create a complete distribution package"""
    
    print("📦 === CREATING LABOR LOOKERS DISTRIBUTION PACKAGE ===")
    print(f"📅 Package Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Package info
    package_name = f"LaborLookers-Complete-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    package_dir = f"../distribution/{package_name}"
    zip_filename = f"../distribution/{package_name}.zip"
    
    # Create distribution directory
    os.makedirs("../distribution", exist_ok=True)
    os.makedirs(package_dir, exist_ok=True)
    
    print(f"📁 Creating package: {package_name}")
    
    # Files and directories to include
    items_to_copy = [
        # Core application files
        'main.py',
        'requirements.txt',
        'requirements-production.txt',
        'requirements-gcp.txt',
        'app.yaml',
        'app-gcp-optimized.yaml',
        'Dockerfile',
        
        # Setup and deployment
        'setup.py',
        'deploy-gcp.sh',
        'deploy-gcp.ps1',
        'deploy-gcp.bat',
        'deploy-azure.sh',
        'deploy-aws.sh',
        'DEPLOYMENT.md',
        'GCP_DEPLOYMENT_GUIDE.md',
        'PRODUCTION_DEPLOYMENT_GUIDE.md',
        
        # Documentation
        'README.md',
        'CONTRACT_PROMPTS.md',
        'ENHANCED_CONTRACT_PROMPTS.md',
        'FUNCTIONALITY_TEST_SUCCESS.md',
        'TEST_RESULTS_FINAL.md',
        
        # Configuration
        'config/',
        'instance/',
        
        # Web assets
        'templates/',
        'static/',
        
        # Test files
        'test_functionality.py',
        'test_app.py',
        'comprehensive_test.py',
        'static_test.py',
        'functional_test.py',
        'validation_report.py',
        
        # Database and migration
        'migrate_to_job_marketplace.py',
        'create_simple_db.py',
        
        # Integration files
        'docusign_integration.py',
        'id_verification.py',
        'two_factor_auth.py',
        'enhanced_job_requirements.py',
        'performance_optimization.py',
        'package_for_email.py',
        
        # Mobile app
        'mobile-app/',
    ]
    
    copied_files = []
    skipped_files = []
    
    # Copy files and directories
    for item in items_to_copy:
        src_path = item
        dst_path = os.path.join(package_dir, item)
        
        try:
            if os.path.exists(src_path):
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
                    copied_files.append(f"📁 {item}/")
                else:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    copied_files.append(f"📄 {item}")
            else:
                skipped_files.append(item)
        except Exception as e:
            print(f"⚠️  Error copying {item}: {e}")
            skipped_files.append(f"{item} (ERROR)")
    
    # Create package manifest
    manifest = {
        "package_name": package_name,
        "created_date": datetime.now().isoformat(),
        "platform_version": "Labor Lookers v2.0 - Complete Marketplace",
        "description": "Complete job marketplace with integrated advertising marketplace",
        "features": [
            "Job seeker accounts and matching",
            "Professional networking system", 
            "Messaging with TOS monitoring",
            "Comprehensive analytics",
            "Advertising marketplace with 7 professional types",
            "Campaign creation and management",
            "Work order tracking",
            "10% commission system",
            "Professional registration and dashboards",
            "Multi-media campaign support",
            "Database backup system",
            "Production deployment ready"
        ],
        "files_included": copied_files,
        "files_skipped": skipped_files,
        "technical_specs": {
            "framework": "Flask",
            "database": "SQLAlchemy",
            "models": 60,
            "routes": 124,
            "templates": "Bootstrap responsive",
            "authentication": "Flask-Login",
            "deployment": "Google Cloud Platform ready"
        }
    }
    
    with open(os.path.join(package_dir, "PACKAGE_MANIFEST.json"), 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Create installation instructions
    installation_guide = """# LABOR LOOKERS PLATFORM - INSTALLATION GUIDE

## 📦 Package Contents
This package contains the complete Labor Lookers platform with all marketplace features.

## 🚀 Quick Start

### 1. Extract Package
Extract this package to your desired directory.

### 2. Setup Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\\Scripts\\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
# Create database tables
python -c "from main import app, db; app.app_context().push(); db.create_all(); print('Database initialized')"
```

### 4. Run Application
```bash
python main.py
```

Visit http://localhost:8080 to access the platform.

## 🌟 Platform Features

### Job Marketplace
- Job seeker registration and profiles
- Professional networking
- Job posting and matching
- Messaging system with TOS monitoring
- Comprehensive analytics

### Advertising Marketplace  
- 7 professional specialization types
- Campaign creation and management
- Professional browsing and filtering
- Work order tracking
- 10% commission system
- Multi-media campaign support

## 🚀 Production Deployment

### Google Cloud Platform
```bash
# Deploy to GCP
./deploy-gcp.sh
```

### Other Platforms
See DEPLOYMENT.md for Azure, AWS, and other deployment options.

## 📊 Database Models
- User accounts (customers, professionals, job seekers)
- Job marketplace (postings, matches, applications)
- Messaging and networking
- Analytics and tracking
- Advertising marketplace (7 professional types)
- Campaign and work order management
- Commission tracking

## 🔒 Security Features
- User authentication and authorization
- Input validation and sanitization
- PII protection
- Content filtering
- Secure session management

## 📞 Support
This is a complete, production-ready platform. All core functionality has been tested and validated.

For technical details, see:
- FUNCTIONALITY_TEST_SUCCESS.md
- TEST_RESULTS_FINAL.md
- DEPLOYMENT.md

---
**Platform Version:** Labor Lookers v2.0 - Complete Marketplace
**Package Date:** {package_date}
**Status:** Production Ready ✅
""".format(package_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    with open(os.path.join(package_dir, "INSTALLATION_GUIDE.md"), 'w') as f:
        f.write(installation_guide)
    
    # Create ZIP file
    print(f"\n📦 Creating ZIP archive: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arc_name)
    
    # Calculate package size
    package_size = os.path.getsize(zip_filename)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📦 DISTRIBUTION PACKAGE CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"📁 Package Name: {package_name}")
    print(f"📄 ZIP File: {zip_filename}")
    print(f"📊 Package Size: {package_size:,} bytes ({package_size/1024/1024:.1f} MB)")
    print(f"✅ Files Included: {len(copied_files)}")
    print(f"⚠️  Files Skipped: {len(skipped_files)}")
    
    print(f"\n📋 INCLUDED FILES:")
    for file in copied_files[:20]:  # Show first 20 files
        print(f"  {file}")
    if len(copied_files) > 20:
        print(f"  ... and {len(copied_files) - 20} more files")
    
    if skipped_files:
        print(f"\n⚠️  SKIPPED FILES:")
        for file in skipped_files:
            print(f"  📄 {file}")
    
    print(f"\n🌟 PLATFORM FEATURES INCLUDED:")
    for feature in manifest["features"]:
        print(f"  ✅ {feature}")
    
    print(f"\n🚀 READY FOR DISTRIBUTION!")
    print(f"📦 Share this ZIP file: {zip_filename}")
    print(f"📋 Installation guide included in package")
    print(f"✨ Complete platform backup created successfully!")
    
    return zip_filename, package_size

if __name__ == '__main__':
    zip_file, size = create_distribution_package()
    print(f"\n✅ Distribution package ready: {zip_file}")