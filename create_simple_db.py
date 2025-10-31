#!/usr/bin/env python3
"""
Simple Database Creation Script - Direct SQLite approach
Creates a working database for sign-in functionality
"""

import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

def create_simple_database():
    """Create a basic SQLite database with User table"""
    
    # Set up paths
    BASE_DIR = Path(__file__).parent
    instance_dir = BASE_DIR / "instance"
    db_path = instance_dir / "referral.db"
    
    # Ensure instance directory exists
    instance_dir.mkdir(exist_ok=True)
    
    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()
        print(f"🗑️  Removed existing database: {db_path}")
    
    # Create new database
    print(f"📁 Creating database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create User table with all required fields matching the Flask model
    cursor.execute("""
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            account_type VARCHAR(20) NOT NULL,
            email_verified BOOLEAN DEFAULT 0,
            approved BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create a test admin user
    admin_password = generate_password_hash('password123')
    cursor.execute("""
        INSERT INTO user (email, password_hash, account_type, email_verified, approved)
        VALUES (?, ?, ?, ?, ?)
    """, ('admin@laborlooker.com', admin_password, 'developer', 1, 1))
    
    # Create a test contractor user  
    contractor_password = generate_password_hash('contractor123')
    cursor.execute("""
        INSERT INTO user (email, password_hash, account_type, email_verified, approved)
        VALUES (?, ?, ?, ?, ?)
    """, ('contractor@laborlooker.com', contractor_password, 'contractor', 1, 1))
    
    # Create a test customer user
    customer_password = generate_password_hash('customer123')
    cursor.execute("""
        INSERT INTO user (email, password_hash, account_type, email_verified, approved)
        VALUES (?, ?, ?, ?, ?)
    """, ('customer@laborlooker.com', customer_password, 'customer', 1, 1))
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print("✅ Database created successfully!")
    print("👤 Test users created:")
    print("   Admin/Developer - Email: admin@laborlooker.com, Password: password123")
    print("   Contractor      - Email: contractor@laborlooker.com, Password: contractor123")
    print("   Customer        - Email: customer@laborlooker.com, Password: customer123")
    
    return str(db_path)

def test_database_connection(db_path):
    """Test that we can query the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM user")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT email FROM user")
        users = cursor.fetchall()
        
        conn.close()
        
        print(f"✅ Database test passed: {count} users found")
        for user in users:
            print(f"   - {user[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    print("🔧 Simple Database Creation for LaborLooker")
    print("=" * 50)
    
    try:
        # Create the database
        db_path = create_simple_database()
        
        # Test it
        if test_database_connection(db_path):
            print("\n🎉 SUCCESS: Database is ready!")
            print("\n🚀 Next steps:")
            print("   1. Start the application: python start_app.py")
            print("   2. Go to: http://localhost:5000/login")
            print("   3. Sign in with admin@laborlooker.com / password123")
        else:
            print("\n❌ Database test failed")
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()