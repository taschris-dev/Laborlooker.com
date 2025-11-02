#!/usr/bin/env python3
"""
LaborLooker PostgreSQL Extensions Setup Script
Configures essential extensions for optimal platform performance
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_postgresql_extensions():
    """Set up essential PostgreSQL extensions for LaborLooker"""
    
    print("🔧 LaborLooker PostgreSQL Extensions Setup")
    print("=" * 60)
    
    # Get database connection details
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"🔗 Connecting to PostgreSQL database...")
    print(f"   Database: {database_url.split('@')[1] if '@' in database_url else 'Railway PostgreSQL'}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        print()
        
        # Essential extensions for LaborLooker
        extensions = [
            {
                'name': 'uuid-ossp',
                'description': 'UUID generation for secure IDs',
                'priority': 'CRITICAL',
                'use_case': 'Referral links, payment IDs, session tokens'
            },
            {
                'name': 'pgcrypto', 
                'description': 'Advanced encryption and hashing',
                'priority': 'CRITICAL',
                'use_case': 'Secure data storage, password hashing'
            },
            {
                'name': 'pg_trgm',
                'description': 'Fuzzy text search and matching',
                'priority': 'HIGH',
                'use_case': 'Intelligent contractor/job search'
            },
            {
                'name': 'hstore',
                'description': 'Key-value data storage',
                'priority': 'HIGH', 
                'use_case': 'User preferences, flexible metadata'
            },
            {
                'name': 'btree_gin',
                'description': 'Advanced indexing for performance',
                'priority': 'MEDIUM',
                'use_case': 'Complex multi-column searches'
            },
            {
                'name': 'pg_stat_statements',
                'description': 'Query performance monitoring',
                'priority': 'MEDIUM',
                'use_case': 'Database optimization and monitoring'
            },
            {
                'name': 'postgis',
                'description': 'Geographic data and spatial queries',
                'priority': 'HIGH',
                'use_case': 'Location-based matching, service areas'
            }
        ]
        
        print("📦 Installing PostgreSQL Extensions...")
        print()
        
        installed_count = 0
        failed_count = 0
        
        for ext in extensions:
            try:
                print(f"   Installing {ext['name']}...")
                
                # Check if extension is already installed
                cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension 
                        WHERE extname = %s
                    );
                """, (ext['name'],))
                
                already_installed = cursor.fetchone()[0]
                
                if already_installed:
                    print(f"      ✅ {ext['name']} already installed")
                else:
                    # Install extension
                    cursor.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext["name"]}";')
                    print(f"      ✅ {ext['name']} installed successfully")
                
                print(f"         Priority: {ext['priority']}")
                print(f"         Use Case: {ext['use_case']}")
                print()
                
                installed_count += 1
                
            except psycopg2.Error as e:
                print(f"      ❌ Failed to install {ext['name']}: {e}")
                print(f"         This extension might not be available on your PostgreSQL version")
                print()
                failed_count += 1
                continue
        
        # Create useful indexes for LaborLooker
        print("🔍 Creating LaborLooker-Specific Indexes...")
        print()
        
        indexes = [
            {
                'name': 'idx_users_email_verified',
                'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_verified ON "user" (email, email_verified);',
                'description': 'Fast user authentication lookups'
            },
            {
                'name': 'idx_users_account_type',
                'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_account_type ON "user" (account_type, approved);',
                'description': 'Account type filtering'
            },
            {
                'name': 'idx_job_postings_status_budget',
                'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_postings_status_budget ON job_posting (status, budget, created_at);',
                'description': 'Job search optimization'
            },
            {
                'name': 'idx_professional_search',
                'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_professional_search ON professional_profile USING GIN (business_name gin_trgm_ops);',
                'description': 'Fuzzy professional name search'
            }
        ]
        
        for idx in indexes:
            try:
                print(f"   Creating {idx['name']}...")
                cursor.execute(idx['sql'])
                print(f"      ✅ {idx['description']}")
            except psycopg2.Error as e:
                # Index might already exist or table might not exist yet
                print(f"      ⚠️  Skipped: {e.diag.message_primary}")
            print()
        
        # Summary
        print("=" * 60)
        print("📊 EXTENSION SETUP SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully installed: {installed_count} extensions")
        if failed_count > 0:
            print(f"❌ Failed to install: {failed_count} extensions")
        
        print("\n🚀 NEXT STEPS:")
        print("1. Extensions are now available for use in your application")
        print("2. Update your models to leverage new capabilities:")
        print("   • Use UUID fields for secure IDs")
        print("   • Implement HSTORE for user preferences")
        print("   • Add PostGIS for location features")
        print("3. Monitor performance with pg_stat_statements")
        
        # Show available extensions
        print("\n📋 AVAILABLE EXTENSIONS:")
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            ORDER BY extname;
        """)
        
        available_extensions = cursor.fetchall()
        for ext_name, ext_version in available_extensions:
            print(f"   • {ext_name} (v{ext_version})")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 PostgreSQL extensions setup complete!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def generate_optimized_queries():
    """Generate example optimized queries using the new extensions"""
    
    print("\n💡 OPTIMIZED QUERY EXAMPLES")
    print("=" * 40)
    
    queries = [
        {
            'title': 'Fuzzy Contractor Search',
            'sql': """
-- Find contractors with similar business names (typo-tolerant)
SELECT business_name, similarity(business_name, 'plumer services') as score
FROM professional_profile 
WHERE business_name % 'plumer services'
ORDER BY score DESC
LIMIT 10;
            """
        },
        {
            'title': 'Location-Based Job Matching (PostGIS)',
            'sql': """
-- Find jobs within contractor's service radius
SELECT j.title, j.location, ST_Distance(
    ST_Point(j.longitude, j.latitude)::geography,
    ST_Point(c.longitude, c.latitude)::geography
) / 1609.34 as distance_miles
FROM job_posting j, professional_profile c
WHERE ST_DWithin(
    ST_Point(j.longitude, j.latitude)::geography,
    ST_Point(c.longitude, c.latitude)::geography,
    c.max_travel_distance * 1609.34  -- Convert miles to meters
)
ORDER BY distance_miles;
            """
        },
        {
            'title': 'User Preferences with HSTORE',
            'sql': """
-- Query users with specific preferences
SELECT email, preferences
FROM "user" 
WHERE preferences ? 'notification_frequency'
  AND preferences -> 'notification_frequency' = 'daily';
            """
        },
        {
            'title': 'Secure UUID Generation',
            'sql': """
-- Generate secure referral links
INSERT INTO referral_link (user_id, link_code, created_at)
VALUES (123, uuid_generate_v4(), NOW());
            """
        }
    ]
    
    for query in queries:
        print(f"\n{query['title']}:")
        print(query['sql'])

if __name__ == "__main__":
    success = setup_postgresql_extensions()
    
    if success:
        generate_optimized_queries()
        print("\n🚀 Your LaborLooker database is now optimized for production!")
    else:
        print("\n⚠️  Some extensions may need manual installation via Railway dashboard")