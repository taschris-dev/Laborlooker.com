#!/usr/bin/env python3
"""
Comprehensive Stress Test for Labor Lookers Platform
Tests database operations, user flows, and system performance
"""

import os
import sys
import time
import random
import threading
from datetime import datetime, timedelta
import requests
import json

# Add the main directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, db, User, JobPosting, WorkRequest, Message, NetworkInvitation
from main import send_message, send_network_invitation, create_customer_referral

class StressTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = requests.Session()
        self.errors = []
        self.test_results = []
        
    def log_error(self, test_name, error):
        """Log errors for reporting"""
        error_msg = f"❌ {test_name}: {str(error)}"
        self.errors.append(error_msg)
        print(error_msg)
        
    def log_success(self, test_name, duration=None):
        """Log successful tests"""
        success_msg = f"✅ {test_name}"
        if duration:
            success_msg += f" ({duration:.2f}s)"
        self.test_results.append(success_msg)
        print(success_msg)
        
    def test_database_operations(self):
        """Test database CRUD operations under stress"""
        print("\n🗄️  Testing Database Operations...")
        
        try:
            with app.app_context():
                start_time = time.time()
                
                # Test user creation
                for i in range(50):
                    user = User(
                        email=f"stress_test_{i}@test.com",
                        password_hash="test_hash",
                        account_type=random.choice(["professional", "customer", "job_seeker", "networking"]),
                        approved=True
                    )
                    db.session.add(user)
                
                db.session.commit()
                duration = time.time() - start_time
                self.log_success("Database User Creation (50 users)", duration)
                
                # Test bulk queries
                start_time = time.time()
                users = User.query.filter_by(approved=True).all()
                duration = time.time() - start_time
                self.log_success(f"Database Query ({len(users)} users)", duration)
                
                # Test job posting creation
                start_time = time.time()
                professional_users = [u for u in users if u.account_type == "professional"]
                
                for i in range(30):
                    if professional_users:
                        user = random.choice(professional_users)
                        job = JobPosting(
                            title=f"Stress Test Job {i}",
                            description=f"Test job description {i}",
                            labor_category="General Labor",
                            location="Test City, SC",
                            posted_by_user_id=user.id,
                            status="active"
                        )
                        db.session.add(job)
                
                db.session.commit()
                duration = time.time() - start_time
                self.log_success("Job Posting Creation (30 jobs)", duration)
                
        except Exception as e:
            self.log_error("Database Operations", e)
            
    def test_messaging_system(self):
        """Test messaging system under load"""
        print("\n💬 Testing Messaging System...")
        
        try:
            with app.app_context():
                users = User.query.limit(20).all()
                if len(users) < 2:
                    self.log_error("Messaging Test", "Not enough users for testing")
                    return
                
                start_time = time.time()
                
                # Send multiple messages
                for i in range(100):
                    sender = random.choice(users)
                    recipient = random.choice([u for u in users if u.id != sender.id])
                    
                    # Test with potentially problematic content
                    test_messages = [
                        "Hello, I'm interested in your job posting.",
                        "Can we discuss this project?",
                        "My email is test@example.com",  # Should trigger PII detection
                        "Let's use PayPal instead",  # Should trigger external payment detection
                        "Call me at 555-1234",  # Should trigger contact info detection
                        "We can work around the platform fees"  # Should trigger TOS violation
                    ]
                    
                    content = random.choice(test_messages)
                    success, message = send_message(
                        sender_id=sender.id,
                        recipient_id=recipient.id,
                        content=content,
                        subject=f"Stress Test Message {i}"
                    )
                    
                    if not success and "blocked" not in message:
                        self.log_error(f"Message {i}", message)
                
                duration = time.time() - start_time
                self.log_success("Messaging System (100 messages)", duration)
                
        except Exception as e:
            self.log_error("Messaging System", e)
            
    def test_network_operations(self):
        """Test networking system operations"""
        print("\n🌐 Testing Network Operations...")
        
        try:
            with app.app_context():
                networking_users = User.query.filter_by(account_type="networking").all()
                other_users = User.query.filter(User.account_type.in_(["professional", "networking"])).all()
                
                if not networking_users or len(other_users) < 2:
                    self.log_error("Network Operations", "Not enough users for testing")
                    return
                
                start_time = time.time()
                
                # Test network invitations
                for i in range(20):
                    network_owner = random.choice(networking_users)
                    invitee = random.choice([u for u in other_users if u.id != network_owner.id])
                    
                    success, message = send_network_invitation(
                        network_owner_id=network_owner.id,
                        invitee_id=invitee.id,
                        network_name=f"Stress Test Network {i}",
                        commission_percentage=random.uniform(0, 5),
                        invitation_message=f"Join my network for stress test {i}"
                    )
                    
                    if not success:
                        self.log_error(f"Network Invitation {i}", message)
                
                duration = time.time() - start_time
                self.log_success("Network Operations (20 invitations)", duration)
                
        except Exception as e:
            self.log_error("Network Operations", e)
            
    def test_concurrent_operations(self):
        """Test concurrent database operations"""
        print("\n⚡ Testing Concurrent Operations...")
        
        def concurrent_user_creation(thread_id):
            try:
                with app.app_context():
                    for i in range(10):
                        user = User(
                            email=f"concurrent_{thread_id}_{i}@test.com",
                            password_hash="test_hash",
                            account_type="professional",
                            approved=True
                        )
                        db.session.add(user)
                        db.session.commit()
            except Exception as e:
                self.log_error(f"Concurrent Thread {thread_id}", e)
        
        try:
            start_time = time.time()
            threads = []
            
            # Create 5 concurrent threads
            for i in range(5):
                thread = threading.Thread(target=concurrent_user_creation, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            duration = time.time() - start_time
            self.log_success("Concurrent Operations (5 threads, 50 users)", duration)
            
        except Exception as e:
            self.log_error("Concurrent Operations", e)
            
    def test_memory_usage(self):
        """Test for potential memory leaks"""
        print("\n🧠 Testing Memory Usage...")
        
        try:
            import psutil
            process = psutil.Process()
            
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            with app.app_context():
                # Perform memory-intensive operations
                for i in range(1000):
                    users = User.query.all()
                    jobs = JobPosting.query.all()
                    messages = Message.query.limit(100).all()
                    
                    # Force garbage collection periodically
                    if i % 100 == 0:
                        import gc
                        gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            if memory_increase > 100:  # More than 100MB increase
                self.log_error("Memory Usage", f"High memory increase: {memory_increase:.2f}MB")
            else:
                self.log_success(f"Memory Usage (increase: {memory_increase:.2f}MB)")
                
        except ImportError:
            print("⚠️  psutil not available for memory testing")
        except Exception as e:
            self.log_error("Memory Usage", e)
            
    def test_api_endpoints(self):
        """Test API endpoints for errors"""
        print("\n🌐 Testing API Endpoints...")
        
        endpoints_to_test = [
            "/",
            "/register",
            "/login",
            "/find-work",
            "/inbox",
            "/dashboard"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                duration = time.time() - start_time
                
                if response.status_code < 500:  # 500+ indicates server error
                    self.log_success(f"Endpoint {endpoint} ({response.status_code})", duration)
                else:
                    self.log_error(f"Endpoint {endpoint}", f"Status {response.status_code}")
                    
            except Exception as e:
                self.log_error(f"Endpoint {endpoint}", e)
                
    def test_data_validation(self):
        """Test data validation and edge cases"""
        print("\n🔍 Testing Data Validation...")
        
        try:
            with app.app_context():
                # Test edge cases for user creation
                edge_cases = [
                    {"email": "", "account_type": "professional"},  # Empty email
                    {"email": "invalid-email", "account_type": "professional"},  # Invalid email
                    {"email": "test@test.com", "account_type": "invalid_type"},  # Invalid account type
                    {"email": "very_long_email_" + "x" * 200 + "@test.com", "account_type": "professional"},  # Long email
                ]
                
                for i, case in enumerate(edge_cases):
                    try:
                        user = User(
                            email=case["email"],
                            password_hash="test_hash",
                            account_type=case["account_type"],
                            approved=True
                        )
                        db.session.add(user)
                        db.session.commit()
                        
                        # If we get here, validation might be missing
                        self.log_error(f"Validation Case {i}", "Should have failed validation")
                        
                    except Exception:
                        # Expected to fail - this is good
                        db.session.rollback()
                        
                self.log_success("Data Validation Tests")
                
        except Exception as e:
            self.log_error("Data Validation", e)
            
    def run_all_tests(self):
        """Run comprehensive stress test suite"""
        print("🚀 Starting Comprehensive Stress Test for Labor Lookers Platform")
        print("=" * 70)
        
        start_time = time.time()
        
        # Run all test categories
        self.test_database_operations()
        self.test_messaging_system()
        self.test_network_operations()
        self.test_concurrent_operations()
        self.test_memory_usage()
        self.test_api_endpoints()
        self.test_data_validation()
        
        total_duration = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 70)
        
        print(f"⏱️  Total Test Duration: {total_duration:.2f} seconds")
        print(f"✅ Successful Tests: {len(self.test_results)}")
        print(f"❌ Failed Tests: {len(self.errors)}")
        
        if self.test_results:
            print("\n✅ SUCCESSFUL TESTS:")
            for result in self.test_results:
                print(f"   {result}")
                
        if self.errors:
            print("\n❌ ERRORS FOUND:")
            for error in self.errors:
                print(f"   {error}")
            print(f"\n⚠️  {len(self.errors)} issues need attention!")
        else:
            print("\n🎉 ALL TESTS PASSED! No issues found.")
            
        return len(self.errors) == 0

def main():
    """Run stress tests"""
    print("Labor Lookers Platform Stress Test")
    print("This will test the system under various stress conditions")
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        print("✅ Server is running, starting stress tests...")
    except:
        print("❌ Server not running. Please start the application first.")
        print("Run: python main.py")
        return False
    
    tester = StressTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 STRESS TEST COMPLETED SUCCESSFULLY!")
        print("Your platform is ready for production use.")
    else:
        print("\n⚠️  STRESS TEST FOUND ISSUES!")
        print("Please review and fix the errors above.")
        
    return success

if __name__ == "__main__":
    main()