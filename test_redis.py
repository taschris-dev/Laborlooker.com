#!/usr/bin/env python3
"""
Redis Connection Test for LaborLooker Platform
Tests the Railway Redis connection and basic operations
"""

import os
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_redis_connection():
    """Test Redis connection and basic operations"""
    try:
        # Get Redis configuration from environment
        redis_url = os.getenv('REDIS_URL')
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        
        print("🔧 LaborLooker Redis Connection Test")
        print("=" * 50)
        print(f"Redis Host: {redis_host}")
        print(f"Redis Port: {redis_port}")
        print(f"Redis URL: {redis_url}")
        print(f"Has Password: {'Yes' if redis_password else 'No'}")
        print()
        
        # Try connection with URL first
        if redis_url:
            print("🔗 Connecting via Redis URL...")
            r = redis.from_url(redis_url)
        else:
            print("🔗 Connecting via host/port...")
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
        
        # Test basic operations
        print("📡 Testing Redis connection...")
        
        # Ping test
        response = r.ping()
        print(f"✅ Ping test: {response}")
        
        # Set/Get test
        test_key = "laborlooker:test"
        test_value = "Redis connection successful!"
        
        r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
        retrieved_value = r.get(test_key)
        print(f"✅ Set/Get test: {retrieved_value}")
        
        # Redis info
        info = r.info('server')
        print(f"✅ Redis version: {info.get('redis_version', 'Unknown')}")
        print(f"✅ Uptime: {info.get('uptime_in_seconds', 0)} seconds")
        
        # Clean up
        r.delete(test_key)
        print("✅ Cleanup completed")
        
        print()
        print("🎉 Redis connection test PASSED!")
        print("Redis is ready for LaborLooker production use!")
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("Check your Redis configuration and network connectivity")
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        print("Check your Redis configuration and credentials")

if __name__ == "__main__":
    test_redis_connection()