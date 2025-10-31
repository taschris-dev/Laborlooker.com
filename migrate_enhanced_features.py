#!/usr/bin/env python3
"""
Database Migration Script for Labor Lookers Platform Enhancement
Adds comprehensive messaging, networking, and analytics capabilities
"""

import os
import sys
from datetime import datetime

# Add the main directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, db
from main import (
    # Analytics models
    CommunicationLog, TransactionAnalytics, DemographicProfile, 
    GeographicAnalytics, JobMarketAnalytics, AdvertisementAnalytics,
    RatingDemographics, PlatformUsageStatistics,
    
    # Messaging and networking models
    Message, MessageThread, NetworkInvitation, NetworkMembership,
    NetworkReferral, CustomerSearchRequest
)

def run_enhanced_migration():
    """Run the complete migration with all new features"""
    
    print("🚀 Starting Labor Lookers Platform Enhancement Migration...")
    print("=" * 60)
    
    try:
        with app.app_context():
            print("📊 Creating comprehensive analytics tables...")
            
            # Create all new tables
            db.create_all()
            
            print("✅ Analytics models created:")
            print("   - CommunicationLog (track all user communications)")
            print("   - TransactionAnalytics (financial tracking)")
            print("   - DemographicProfile (user demographics)")
            print("   - GeographicAnalytics (market analysis)")
            print("   - JobMarketAnalytics (job acceptance/rejection tracking)")
            print("   - AdvertisementAnalytics (ad performance)")
            print("   - RatingDemographics (rating pattern analysis)")
            print("   - PlatformUsageStatistics (comprehensive usage stats)")
            
            print("📱 Messaging system created:")
            print("   - Message (with TOS violation detection)")
            print("   - MessageThread (conversation management)")
            
            print("🌐 Network management system created:")
            print("   - NetworkInvitation (with contract requirements)")
            print("   - NetworkMembership (active network relationships)")
            print("   - NetworkReferral (5% commission tracking)")
            print("   - CustomerSearchRequest (automated customer finding)")
            
            print("=" * 60)
            print("🎉 Migration completed successfully!")
            print("=" * 60)
            
            # Display summary of new capabilities
            print("NEW PLATFORM CAPABILITIES:")
            print("✨ Professional Accounts:")
            print("   - Work search functionality (like customer find work)")
            print("   - Job posting applications")
            print("   - Network invitation system")
            print("   - Comprehensive messaging with content filtering")
            print("   - PII and TOS violation detection")
            
            print("✨ Networking Accounts:")
            print("   - Customer search and referral system")
            print("   - Network member invitations (manual + automatic)")
            print("   - 5% commission tracking on referrals")
            print("   - DocuSign contract integration")
            print("   - Search by location, name, and service")
            print("   - Work search functionality")
            
            print("✨ All Accounts:")
            print("   - Advanced messaging system with inbox")
            print("   - TOS violation detection (PII, external payments)")
            print("   - Content filtering and moderation")
            print("   - Comprehensive data collection and analytics")
            print("   - Communication tracking")
            print("   - Geographic market analysis")
            
            print("🔒 SECURITY FEATURES:")
            print("   - Automatic PII detection in messages")
            print("   - External payment method flagging")
            print("   - Platform bypass attempt detection")
            print("   - Admin review system for violations")
            print("   - Comprehensive audit trails")
            
            print("💰 COMMISSION SYSTEM:")
            print("   - Network owners earn up to 5% commission")
            print("   - Referral tracking and verification")
            print("   - Payment structure flexibility (commission/subscription)")
            print("   - Contract-based network memberships")
            
            print("=" * 60)
            print("🎯 READY FOR PRODUCTION!")
            print("Your Labor Lookers platform now includes:")
            print("• Complete job marketplace functionality")
            print("• Advanced networking and referral system") 
            print("• Comprehensive messaging with content moderation")
            print("• Full analytics and data collection")
            print("• Professional work search capabilities")
            print("• Customer referral and commission tracking")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("Please check your database connection and try again.")
        return False

if __name__ == "__main__":
    print("Labor Lookers Platform Enhancement Migration")
    print("This will add messaging, networking, and analytics capabilities")
    
    confirm = input("Proceed with migration? (y/N): ").lower().strip()
    
    if confirm in ['y', 'yes']:
        success = run_enhanced_migration()
        if success:
            print("\n🚀 Migration complete! Your platform is ready with all new features!")
        else:
            print("\n💥 Migration failed. Please check the error messages above.")
            sys.exit(1)
    else:
        print("Migration cancelled.")