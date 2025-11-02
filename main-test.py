#!/usr/bin/env python3
"""
Minimal Flask App for Railway Deployment Test
Tests basic Flask + Redis functionality
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "LaborLooker API is running!",
        "version": "1.0.0",
        "redis_configured": bool(os.environ.get('REDIS_URL'))
    })

@app.route('/health')
def health():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "service": "laborlooker-api"
    })

@app.route('/redis-test')
def redis_test():
    """Test Redis connection"""
    try:
        # Try importing and connecting to Redis
        import redis
        
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            return jsonify({
                "status": "error",
                "message": "Redis URL not configured"
            }), 500
        
        # Test Redis connection
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        
        # Test set/get
        test_key = "test:connection"
        r.set(test_key, "Redis is working!", ex=60)
        value = r.get(test_key)
        
        return jsonify({
            "status": "success",
            "message": "Redis connection successful",
            "test_value": value,
            "redis_url": redis_url.split('@')[0] + '@[HIDDEN]'  # Hide credentials
        })
        
    except ImportError:
        return jsonify({
            "status": "error",
            "message": "Redis library not installed"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Redis connection failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)