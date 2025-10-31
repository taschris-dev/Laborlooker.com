#!/usr/bin/env python3
"""
Database Initialization Script for LaborLooker Platform
Creates database and all necessary tables for local testing
"""

import os
import sys
from pathlib import Path

# Ensure we're in the correct directory
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

# Import main application
try:
    from main import app, db
    print("✅ Successfully imported Flask app and database")
except ImportError as e:
    print(f"❌ Error importing application: {e}")
    sys.exit(1)

def initialize_database():
    """Initialize the database with all tables"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Verify tables were created
            tables = db.engine.table_names()
            print(f"✅ Created {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
                
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def check_database():
    """Check if database exists and is accessible"""
    db_path = BASE_DIR / "instance" / "laborlooker.db"
    
    if db_path.exists():
        print(f"✅ Database file exists: {db_path}")
        print(f"   Size: {db_path.stat().st_size} bytes")
        return True
    else:
        print(f"⚠️  Database file not found: {db_path}")
        return False

def main():
    print("🚀 LaborLooker Database Initialization")
    print("=" * 50)
    
    # Check directories
    instance_dir = BASE_DIR / "instance"
    if not instance_dir.exists():
        print("📁 Creating instance directory...")
        instance_dir.mkdir(exist_ok=True)
    else:
        print("✅ Instance directory exists")
    
    # Initialize database
    print("\n📊 Initializing database...")
    if initialize_database():
        print("\n🔍 Verifying database...")
        check_database()
        print("\n🎉 Database initialization complete!")
        print("\n🌐 You can now start the application:")
        print("   python main.py")
        print("\n🔗 Then visit: http://localhost:5000")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()