#!/usr/bin/env python3
"""
Database Fix and Initialization for LaborLooker Platform
Creates and initializes the database properly for sign-in functionality
"""

import os
import sys
from pathlib import Path

# Set working directory to the script location
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

def fix_database():
    """Initialize the Flask database properly"""
    try:
        # Import the main application
        from main import app, db
        
        print("🚀 Fixing LaborLooker Database...")
        
        # Create application context
        with app.app_context():
            print("📊 Creating all database tables...")
            
            # Drop and recreate all tables to ensure clean state
            db.drop_all()
            db.create_all()
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✅ Successfully created {len(tables)} tables:")
            for table in sorted(tables):
                print(f"   - {table}")
            
            # Create a test user to verify everything works
            from main import User
            from werkzeug.security import generate_password_hash
            
            # Check if admin user already exists
            admin_user = User.query.filter_by(email='admin@laborlooker.com').first()
            if not admin_user:
                admin_user = User(
                    email='admin@laborlooker.com',
                    username='admin',
                    password_hash=generate_password_hash('password123'),
                    first_name='Admin',
                    last_name='User',
                    user_type='admin',
                    is_verified=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Created admin test user:")
                print("   Email: admin@laborlooker.com")
                print("   Password: password123")
            else:
                print("✅ Admin user already exists")
                
            print("\n🎉 Database initialization completed successfully!")
            print("🌐 You can now start the application and sign in.")
            
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database connectivity and user queries"""
    try:
        from main import app, db, User
        
        with app.app_context():
            # Test basic connectivity
            user_count = User.query.count()
            print(f"📊 Database test: Found {user_count} users")
            
            # Test user lookup (this is what was failing in sign-in)
            test_user = User.query.filter_by(email='admin@laborlooker.com').first()
            if test_user:
                print("✅ User query test passed")
                return True
            else:
                print("⚠️  No test user found, but query worked")
                return True
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    print("🔧 LaborLooker Database Fix Utility")
    print("=" * 50)
    
    # Check if database file exists
    db_path = BASE_DIR / "instance" / "laborlooker.db"
    print(f"📁 Database location: {db_path}")
    
    if db_path.exists():
        print(f"✅ Database file exists ({db_path.stat().st_size} bytes)")
    else:
        print("❌ Database file missing")
        return
    
    # Initialize/fix database
    if fix_database():
        print("\n🧪 Testing database functionality...")
        if test_database():
            print("\n🎯 SUCCESS: Database is ready for use!")
            print("\n🚀 Next steps:")
            print("   1. Start the application: python start_app.py")
            print("   2. Go to: http://localhost:5000/login")
            print("   3. Sign in with:")
            print("      Email: admin@laborlooker.com")
            print("      Password: password123")
        else:
            print("\n❌ Database test failed - check configuration")
    else:
        print("\n❌ Database initialization failed")

if __name__ == "__main__":
    main()