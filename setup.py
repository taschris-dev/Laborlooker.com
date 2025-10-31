#!/usr/bin/env python3
"""
Setup script for Marketing Technology Platform
Automates the installation and initialization process
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return None

def create_virtual_environment():
    """Create and setup virtual environment"""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("🔄 Creating virtual environment...")
    try:
        venv.create(".venv", with_pip=True)
        print("✅ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating virtual environment: {e}")
        return False

def get_python_executable():
    """Get the path to the Python executable in the virtual environment"""
    if os.name == 'nt':  # Windows
        return ".venv\\Scripts\\python.exe"
    else:  # Unix/Linux/macOS
        return ".venv/bin/python"

def install_dependencies():
    """Install required Python packages"""
    python_exe = get_python_executable()
    
    # Install packages
    packages = [
        "Flask==3.0.3",
        "Flask-SQLAlchemy==3.1.1", 
        "Flask-Login==0.6.3",
        "werkzeug==3.0.3",
        "itsdangerous==2.2.0",
        "pandas==2.2.3",
        "qrcode[pil]==7.4.2",
        "Pillow==10.4.0",
        "shortuuid"
    ]
    
    for package in packages:
        result = run_command(f"{python_exe} -m pip install {package}", f"Installing {package}")
        if result is None:
            return False
    
    return True

def initialize_database():
    """Initialize the database with all tables"""
    python_exe = get_python_executable()
    
    init_command = f'{python_exe} -c "from app import app, db; app.app_context().push(); db.create_all(); print(\'Database initialized successfully!\')"'
    
    result = run_command(init_command, "Initializing database")
    return result is not None

def create_sample_env_file():
    """Create a sample .env file"""
    env_content = """# Environment Configuration
# Copy this file to .env and update with your values

# Security
SECRET_KEY=your-secret-key-here-change-in-production

# Email Configuration (optional)
MAIL_PASSWORD=your-email-password-for-notifications

# Database (optional - defaults to SQLite)
# DATABASE_URL=sqlite:///instance/referral.db

# Application Settings
FLASK_ENV=development
DEBUG=True
"""
    
    try:
        with open(".env.example", "w") as f:
            f.write(env_content)
        print("✅ Created .env.example file")
        return True
    except Exception as e:
        print(f"❌ Error creating .env.example: {e}")
        return False

def create_start_script():
    """Create a startup script for the application"""
    if os.name == 'nt':  # Windows
        script_content = """@echo off
echo Starting Marketing Technology Platform...
.venv\\Scripts\\python.exe app.py
pause
"""
        script_name = "start.bat"
    else:  # Unix/Linux/macOS
        script_content = """#!/bin/bash
echo "Starting Marketing Technology Platform..."
.venv/bin/python app.py
"""
        script_name = "start.sh"
    
    try:
        with open(script_name, "w") as f:
            f.write(script_content)
        
        if os.name != 'nt':
            os.chmod(script_name, 0o755)  # Make executable on Unix systems
        
        print(f"✅ Created {script_name} startup script")
        return True
    except Exception as e:
        print(f"❌ Error creating startup script: {e}")
        return False

def print_success_message():
    """Print success message with next steps"""
    python_exe = get_python_executable()
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\n📋 NEXT STEPS:")
    print("\n1. Start the application:")
    if os.name == 'nt':
        print("   • Double-click start.bat")
        print("   • OR run: .venv\\Scripts\\python.exe app.py")
    else:
        print("   • Run: ./start.sh")
        print("   • OR run: .venv/bin/python app.py")
    
    print("\n2. Open your browser:")
    print("   • Visit: http://127.0.0.1:5000")
    
    print("\n3. Create your first account:")
    print("   • Go to: http://127.0.0.1:5000/register")
    print("   • Choose 'Developer' for full access")
    print("   • Use a 15+ character password with 2 uppercase and 1 symbol")
    
    print("\n4. Explore the platform:")
    print("   • Developer: Full admin access and analytics")
    print("   • Contractor: Business profile and invoicing")  
    print("   • Customer: Schedule work and billing")
    
    print("\n📁 PROJECT STRUCTURE:")
    print("   • app.py - Main application")
    print("   • instance/ - Database files")
    print("   • templates/ - HTML templates")
    print("   • static/ - CSS and generated files")
    
    print("\n🎯 FOR INTERVIEWS:")
    print("   • Demonstrates full-stack development")
    print("   • Shows SaaS business model understanding")
    print("   • Includes authentication and role-based access")
    print("   • Features billing, invoicing, and analytics")
    
    print("\n💡 DEMO CREDENTIALS:")
    print("   Email: admin@example.com")
    print("   Password: DevPassword123!")
    print("   Type: Developer")
    
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🚀 Marketing Technology Platform Setup")
    print("="*50)
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Setup steps
    steps = [
        (create_virtual_environment, "Create virtual environment"),
        (install_dependencies, "Install dependencies"),
        (initialize_database, "Initialize database"),
        (create_sample_env_file, "Create configuration files"),
        (create_start_script, "Create startup script")
    ]
    
    for step_func, step_name in steps:
        if not step_func():
            print(f"\n❌ Setup failed at: {step_name}")
            print("Please check the error messages above and try again.")
            sys.exit(1)
    
    print_success_message()

if __name__ == "__main__":
    main()