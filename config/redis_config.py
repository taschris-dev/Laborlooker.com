"""
Redis Configuration for LaborLooker Platform
Handles Redis connection and common operations for caching and sessions
"""

import os
import redis
import json
from datetime import timedelta
from functools import wraps

class LaborLookerRedis:
    """Redis client wrapper for LaborLooker platform"""
    
    def __init__(self, app=None):
        self.redis_client = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Redis with Flask app"""
        try:
            # Get Redis configuration
            redis_url = os.getenv('REDIS_URL')
            
            if redis_url:
                self.redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
            else:
                # Fallback to individual settings
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD', None),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
            
            # Test connection
            self.redis_client.ping()
            app.logger.info("✅ Redis connected successfully")
            
        except Exception as e:
            app.logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self):
        """Check if Redis is connected"""
        try:
            return self.redis_client and self.redis_client.ping()
        except:
            return False
    
    # Session Management
    def set_session(self, session_id, data, expire_hours=24):
        """Store session data"""
        if not self.redis_client:
            return False
        try:
            key = f"session:{session_id}"
            return self.redis_client.setex(
                key, 
                timedelta(hours=expire_hours), 
                json.dumps(data)
            )
        except Exception as e:
            print(f"Session set error: {e}")
            return False
    
    def get_session(self, session_id):
        """Get session data"""
        if not self.redis_client:
            return None
        try:
            key = f"session:{session_id}"
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Session get error: {e}")
            return None
    
    def delete_session(self, session_id):
        """Delete session"""
        if not self.redis_client:
            return False
        try:
            key = f"session:{session_id}"
            return self.redis_client.delete(key)
        except Exception as e:
            print(f"Session delete error: {e}")
            return False
    
    # Rate Limiting
    def check_rate_limit(self, key, limit=100, window_seconds=3600):
        """Check rate limit for a key"""
        if not self.redis_client:
            return True  # Allow if Redis unavailable
        
        try:
            current = self.redis_client.get(f"rate_limit:{key}")
            if current is None:
                # First request
                self.redis_client.setex(f"rate_limit:{key}", window_seconds, 1)
                return True
            elif int(current) < limit:
                # Under limit
                self.redis_client.incr(f"rate_limit:{key}")
                return True
            else:
                # Over limit
                return False
        except Exception as e:
            print(f"Rate limit error: {e}")
            return True  # Allow if error
    
    # Caching
    def cache_set(self, key, value, expire_seconds=3600):
        """Cache a value"""
        if not self.redis_client:
            return False
        try:
            cache_key = f"cache:{key}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.redis_client.setex(cache_key, expire_seconds, value)
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def cache_get(self, key):
        """Get cached value"""
        if not self.redis_client:
            return None
        try:
            cache_key = f"cache:{key}"
            data = self.redis_client.get(cache_key)
            if data:
                try:
                    return json.loads(data)
                except:
                    return data
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def cache_delete(self, key):
        """Delete cached value"""
        if not self.redis_client:
            return False
        try:
            cache_key = f"cache:{key}"
            return self.redis_client.delete(cache_key)
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

# Global Redis instance
redis_client = LaborLookerRedis()

# Decorator for caching
def cache_result(key_prefix, expire_seconds=3600):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = redis_client.cache_get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.cache_set(cache_key, result, expire_seconds)
            return result
        return wrapper
    return decorator

# Decorator for rate limiting
def rate_limit(limit=100, window_seconds=3600, key_func=None):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:default"
            
            # Check rate limit
            if not redis_client.check_rate_limit(key, limit, window_seconds):
                from flask import abort
                abort(429)  # Too Many Requests
            
            return func(*args, **kwargs)
        return wrapper
    return decorator