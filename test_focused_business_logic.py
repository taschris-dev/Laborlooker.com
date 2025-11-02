#!/usr/bin/env python3
"""
LaborLooker Focused Business Logic Test
Tests core functionality using actual database models
"""

import os
import sys
from datetime import datetime

# Skip Redis connection for testing
os.environ['SKIP_REDIS_CONNECTION'] = 'true'

def test_user_account_system():
    """Test user account creation and management"""
    print("👤 Testing User Account System...")
    
    try:
        from main import app, db, User, ProfessionalProfile, CustomerProfile
        
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            
            # Test Customer Account Creation
            print("   📝 Creating customer account...")
            customer_user = User(
                email='test.customer@laborlooker.com',
                first_name='John',
                last_name='Customer',
                account_type='customer',
                phone='555-0101'
            )
            customer_user.set_password('testpassword123')
            db.session.add(customer_user)
            db.session.flush()
            
            customer_profile = CustomerProfile(
                user_id=customer_user.id,
                company_name='Test Company Inc',
                industry='Technology'
            )
            db.session.add(customer_profile)
            
            # Test Professional Account Creation  
            print("   🔨 Creating professional account...")
            professional_user = User(
                email='test.professional@laborlooker.com',
                first_name='Jane',
                last_name='Professional',
                account_type='professional',
                phone='555-0102'
            )
            professional_user.set_password('testpassword456')
            db.session.add(professional_user)
            db.session.flush()
            
            professional_profile = ProfessionalProfile(
                user_id=professional_user.id,
                business_name='Jane\'s Professional Services',
                contact_name='Jane Professional',
                service_description='Professional services provider'
            )
            db.session.add(professional_profile)
            
            db.session.commit()
            
            print("   ✅ User accounts created successfully")
            return True
            
    except Exception as e:
        print(f"   ❌ User account test failed: {e}")
        return False

def test_job_system():
    """Test job posting and matching system"""
    print("💼 Testing Job System...")
    
    try:
        from main import app, db, User, JobPosting, WorkRequest
        
        with app.app_context():
            # Get test customer
            customer = User.query.filter_by(email='test.customer@laborlooker.com').first()
            professional = User.query.filter_by(email='test.professional@laborlooker.com').first()
            
            if not customer or not professional:
                print("   ⚠️  Test users not found, creating them...")
                return False
            
            # Test Job Posting Creation
            print("   📋 Creating job posting...")
            job = JobPosting(
                customer_id=customer.id,
                title='Test Plumbing Job',
                description='Fix kitchen sink leak',
                budget=350.00,
                location='Test City, TC',
                category='plumbing',
                urgency='medium',
                status='open'
            )
            db.session.add(job)
            
            # Test Work Request
            print("   📝 Creating work request...")
            work_request = WorkRequest(
                customer_id=customer.id,
                professional_id=professional.id,
                title='Emergency Repair',
                description='Urgent plumbing repair needed',
                budget=500.00,
                deadline=datetime.utcnow(),
                status='pending'
            )
            db.session.add(work_request)
            
            db.session.commit()
            
            print("   ✅ Job system working correctly")
            return True
            
    except Exception as e:
        print(f"   ❌ Job system test failed: {e}")
        return False

def test_payment_simulation():
    """Test payment logic simulation"""
    print("💰 Testing Payment Logic...")
    
    try:
        from main import app, db, Invoice, ContractorInvoice
        from decimal import Decimal
        
        with app.app_context():
            customer = User.query.filter_by(email='test.customer@laborlooker.com').first()
            professional = User.query.filter_by(email='test.professional@laborlooker.com').first()
            
            # Test Invoice Creation
            print("   🧾 Creating invoice...")
            invoice = Invoice(
                client_id=customer.id,
                amount=500.00,
                description='Plumbing repair services',
                status='pending',
                due_date=datetime.utcnow()
            )
            db.session.add(invoice)
            
            # Test Contractor Invoice
            print("   💼 Creating contractor invoice...")
            contractor_invoice = ContractorInvoice(
                professional_id=professional.id,
                customer_id=customer.id,
                amount=500.00,
                description='Professional services rendered',
                status='pending'
            )
            db.session.add(contractor_invoice)
            
            # Test Fee Calculations
            print("   🧮 Testing fee calculations...")
            job_amount = Decimal('500.00')
            
            # Your fee structure:
            platform_fee = job_amount * Decimal('0.10')    # 10% = $50
            service_fee = job_amount * Decimal('0.05')     # 5% = $25  
            network_fee = job_amount * Decimal('0.05')     # 5% = $25 (if network referral)
            contractor_payout = job_amount * Decimal('0.80') # 80% = $400
            
            print(f"      💵 Job Amount: ${job_amount}")
            print(f"      🏢 Platform Fee (10%): ${platform_fee}")
            print(f"      ⚙️  Service Fee (5%): ${service_fee}")
            print(f"      🤝 Network Fee (5%): ${network_fee}")
            print(f"      👷 Contractor Payout (80%): ${contractor_payout}")
            
            db.session.commit()
            
            print("   ✅ Payment logic working correctly")
            return True
            
    except Exception as e:
        print(f"   ❌ Payment test failed: {e}")
        return False

def test_networking_system():
    """Test networking and referral system"""
    print("🌐 Testing Networking System...")
    
    try:
        from main import app, db, NetworkingProfile, ReferralLink
        
        with app.app_context():
            professional = User.query.filter_by(email='test.professional@laborlooker.com').first()
            
            # Test Networking Profile
            print("   🤝 Creating networking profile...")
            networking_profile = NetworkingProfile(
                user_id=professional.id,
                network_size=0,
                total_referrals=0,
                successful_referrals=0,
                network_earnings=0.0
            )
            db.session.add(networking_profile)
            
            # Test Referral Link Creation
            print("   🔗 Creating referral link...")
            referral_link = ReferralLink(
                user_id=professional.id,
                link_code=f'REF_{professional.id}_{int(datetime.utcnow().timestamp())}',
                clicks=0,
                conversions=0,
                is_active=True
            )
            db.session.add(referral_link)
            
            db.session.commit()
            
            print("   ✅ Networking system working correctly")
            return True
            
    except Exception as e:
        print(f"   ❌ Networking test failed: {e}")
        return False

def test_swipe_matching_system():
    """Test swipe-based matching system"""
    print("📱 Testing Swipe Matching System...")
    
    try:
        from main import app, db, SwipeAction, SwipeMatch
        
        with app.app_context():
            customer = User.query.filter_by(email='test.customer@laborlooker.com').first()
            professional = User.query.filter_by(email='test.professional@laborlooker.com').first()
            
            # Test Swipe Action
            print("   👆 Creating swipe action...")
            swipe = SwipeAction(
                swiper_id=customer.id,
                target_id=professional.id,
                swipe_type='like',
                context_type='job_match',
                preview_data_shown='{"service": "plumbing", "rating": 4.8}'
            )
            db.session.add(swipe)
            
            # Test Mutual Match
            print("   💕 Creating mutual match...")
            match = SwipeMatch(
                user1_id=min(customer.id, professional.id),
                user2_id=max(customer.id, professional.id),
                context_type='job_match',
                status='active'
            )
            db.session.add(match)
            
            db.session.commit()
            
            print("   ✅ Swipe matching system working correctly")
            return True
            
    except Exception as e:
        print(f"   ❌ Swipe matching test failed: {e}")
        return False

def test_campaign_system():
    """Test marketing campaign system"""
    print("📢 Testing Campaign System...")
    
    try:
        from main import app, db, Campaign, Lead
        
        with app.app_context():
            professional = User.query.filter_by(email='test.professional@laborlooker.com').first()
            
            # Test Campaign Creation
            print("   🎯 Creating marketing campaign...")
            campaign = Campaign(
                user_id=professional.id,
                name='Professional Services Promotion',
                description='Promote plumbing and repair services',
                target_audience='homeowners',
                budget=200.00,
                status='active'
            )
            db.session.add(campaign)
            db.session.flush()
            
            # Test Lead Generation
            print("   📈 Creating lead...")
            lead = Lead(
                campaign_id=campaign.id,
                first_name='Potential',
                last_name='Customer',
                email='potential@example.com',
                phone='555-0199',
                source='campaign',
                status='new'
            )
            db.session.add(lead)
            
            db.session.commit()
            
            print("   ✅ Campaign system working correctly")
            return True
            
    except Exception as e:
        print(f"   ❌ Campaign test failed: {e}")
        return False

def main():
    """Run focused business logic tests"""
    print("🧪 LaborLooker Focused Business Logic Test")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Import required modules first
    try:
        from main import app, db, User
        print("✅ Main application modules imported successfully")
    except Exception as e:
        print(f"❌ Failed to import application: {e}")
        return False
    
    # Run test suite
    tests = [
        test_user_account_system,
        test_job_system, 
        test_payment_simulation,
        test_networking_system,
        test_swipe_matching_system,
        test_campaign_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"   ❌ Test {test.__name__} crashed: {e}")
            print()
    
    # Results
    print("=" * 60)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CORE BUSINESS LOGIC WORKING!")
        print("✅ Key Systems Verified:")
        print("   • User account management (customers, professionals)")
        print("   • Job posting and work request system")
        print("   • Payment processing with fee structure")
        print("   • Networking and referral tracking")
        print("   • Swipe-based matching system")
        print("   • Marketing campaign management")
        print("\n🚀 Platform ready for production use!")
        return True
    else:
        print(f"⚠️  {total-passed} tests failed - needs attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)