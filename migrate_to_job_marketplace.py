#!/usr/bin/env python3
"""
Migration script to transform Labor Lookers into job marketplace
- Renames contractor to professional, developer to networking
- Adds job_seeker account type
- Creates new job marketplace models
- Updates existing data to new schema
"""

import os
import sys
import sqlite3
from datetime import datetime

def backup_database():
    """Create backup of current database"""
    if os.path.exists("instance/referral.db"):
        backup_name = f"instance/referral_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy2("instance/referral.db", backup_name)
        print(f"✅ Database backed up to: {backup_name}")
        return backup_name
    return None

def create_new_tables(conn):
    """Create new job marketplace tables"""
    cursor = conn.cursor()
    
    # Create JobSeekerProfile table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_seeker_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            phone VARCHAR(50),
            address VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(50),
            zip_code VARCHAR(20),
            geographic_area VARCHAR(50),
            desired_labor_categories TEXT,
            experience_level VARCHAR(20),
            preferred_locations TEXT,
            availability TEXT,
            resume_file_path VARCHAR(500),
            skills TEXT,
            certifications TEXT,
            seeking_apprenticeship BOOLEAN DEFAULT 0,
            seeking_training BOOLEAN DEFAULT 0,
            seeking_full_time BOOLEAN DEFAULT 0,
            seeking_part_time BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
    """)
    
    # Create JobPosting table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_posting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poster_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            labor_category VARCHAR(100) NOT NULL,
            pay_type VARCHAR(20) NOT NULL,
            pay_amount FLOAT,
            pay_range_min FLOAT,
            pay_range_max FLOAT,
            experience_level VARCHAR(20) NOT NULL,
            location VARCHAR(255) NOT NULL,
            star_rating_preference FLOAT DEFAULT 0.0,
            job_type VARCHAR(50),
            benefits TEXT,
            requirements TEXT,
            status VARCHAR(20) DEFAULT 'active',
            applications_count INTEGER DEFAULT 0,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            filled_at DATETIME,
            FOREIGN KEY (poster_id) REFERENCES user (id)
        )
    """)
    
    # Create JobMatch table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_match (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_posting_id INTEGER NOT NULL,
            job_seeker_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'matched',
            job_seeker_interest VARCHAR(20),
            professional_response VARCHAR(20),
            job_seeker_preview_data TEXT,
            professional_preview_data TEXT,
            liability_agreement_signed BOOLEAN DEFAULT 0,
            employment_terms_signed BOOLEAN DEFAULT 0,
            liability_docusign_envelope_id VARCHAR(255),
            employment_docusign_envelope_id VARCHAR(255),
            matched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_at DATETIME,
            hired_at DATETIME,
            FOREIGN KEY (job_posting_id) REFERENCES job_posting (id),
            FOREIGN KEY (job_seeker_id) REFERENCES user (id),
            FOREIGN KEY (professional_id) REFERENCES user (id)
        )
    """)
    
    print("✅ Created new job marketplace tables")

def rename_existing_tables(conn):
    """Rename existing tables to new naming convention"""
    cursor = conn.cursor()
    
    # Rename contractor_profile to professional_profile
    try:
        cursor.execute("ALTER TABLE contractor_profile RENAME TO professional_profile")
        print("✅ Renamed contractor_profile to professional_profile")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("ℹ️ contractor_profile table doesn't exist, skipping rename")
        else:
            print(f"❌ Error renaming contractor_profile: {e}")
    
    # Rename developer_profile to networking_profile
    try:
        cursor.execute("ALTER TABLE developer_profile RENAME TO networking_profile")
        print("✅ Renamed developer_profile to networking_profile")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("ℹ️ developer_profile table doesn't exist, skipping rename")
        else:
            print(f"❌ Error renaming developer_profile: {e}")
    
    # Rename developer_network to networking_network
    try:
        cursor.execute("ALTER TABLE developer_network RENAME TO networking_network")
        print("✅ Renamed developer_network to networking_network")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("ℹ️ developer_network table doesn't exist, skipping rename")
        else:
            print(f"❌ Error renaming developer_network: {e}")

def add_new_user_columns(conn):
    """Add new columns to user table"""
    cursor = conn.cursor()
    
    new_columns = [
        ("experience_level", "VARCHAR(20)"),
        ("location_preference", "VARCHAR(255)"),
        ("star_rating_preference", "FLOAT"),
        ("id_verification_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("id_verification_documents", "TEXT")
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(user)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE user ADD COLUMN {column_name} {column_type}")
                print(f"✅ Added {column_name} column to user table")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding {column_name}: {e}")

def add_job_posting_columns_to_profiles(conn):
    """Add job posting capability columns to profile tables"""
    cursor = conn.cursor()
    
    # Add to professional_profile
    job_columns = [
        ("verified_labor_categories", "TEXT"),
        ("can_post_jobs", "BOOLEAN DEFAULT 0")
    ]
    
    for table in ["professional_profile", "networking_profile"]:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            for column_name, column_type in job_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Added {column_name} to {table}")
                    except sqlite3.OperationalError as e:
                        print(f"❌ Error adding {column_name} to {table}: {e}")
        except sqlite3.OperationalError:
            print(f"ℹ️ Table {table} doesn't exist yet")

def update_account_types(conn):
    """Update account types from old names to new names"""
    cursor = conn.cursor()
    
    # Update account types
    updates = [
        ("contractor", "professional"),
        ("developer", "networking")
    ]
    
    for old_type, new_type in updates:
        cursor.execute("UPDATE user SET account_type = ? WHERE account_type = ?", (new_type, old_type))
        affected = cursor.rowcount
        if affected > 0:
            print(f"✅ Updated {affected} users from {old_type} to {new_type}")

def main():
    """Main migration function"""
    print("🔄 Starting Labor Lookers job marketplace migration...")
    
    # Backup database
    backup_file = backup_database()
    
    # Connect to database
    if not os.path.exists("instance/referral.db"):
        print("❌ Database file not found. Please ensure the application has been run at least once.")
        return
    
    conn = sqlite3.connect("instance/referral.db")
    
    try:
        # Execute migration steps
        print("\n📝 Step 1: Adding new columns to user table...")
        add_new_user_columns(conn)
        
        print("\n📝 Step 2: Creating new job marketplace tables...")
        create_new_tables(conn)
        
        print("\n📝 Step 3: Renaming existing tables...")
        rename_existing_tables(conn)
        
        print("\n📝 Step 4: Adding job posting columns to profiles...")
        add_job_posting_columns_to_profiles(conn)
        
        print("\n📝 Step 5: Updating account types...")
        update_account_types(conn)
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"📁 Database backup: {backup_file}")
        print("\n🎯 Next steps:")
        print("1. Update main.py to use new model names")
        print("2. Update templates and routes")
        print("3. Test the application")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        if backup_file:
            print(f"💾 You can restore from backup: {backup_file}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()