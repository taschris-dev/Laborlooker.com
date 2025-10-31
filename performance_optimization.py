"""
Performance optimization module for Google Cloud deployment.
This module enhances the main application with production-ready features.
"""

from flask import request, jsonify
from datetime import datetime, timedelta
import logging
import os

class PerformanceOptimizer:
    """Handles performance optimization and security enhancements."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the performance optimizer with the Flask app."""
        self.app = app
        
        # Configure security headers
        self.configure_security_headers()
        
        # Configure caching headers
        self.configure_caching()
        
        # Configure CORS for mobile apps
        self.configure_mobile_cors()
        
        # Configure Google Cloud Load Balancer compatibility
        self.configure_load_balancer()
        
        # Add health check endpoints
        self.add_health_checks()
    
    def configure_security_headers(self):
        """Configure security headers for production deployment."""
        
        @self.app.after_request
        def add_security_headers(response):
            # Basic security headers
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
            
            # Add HSTS in production
            if not self.app.debug:
                security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            
            # Content Security Policy
            csp_parts = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://code.jquery.com",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https: blob:",
                "connect-src 'self' https://api.laborlooker.com wss://laborlooker.com"
            ]
            
            # Relaxed CSP for development
            if self.app.debug:
                csp_parts = [
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com",
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                    "connect-src 'self' http://localhost:* https://api.laborlooker.com"
                ]
            
            security_headers["Content-Security-Policy"] = "; ".join(csp_parts)
            
            # Apply all headers
            for header, value in security_headers.items():
                response.headers[header] = value
            
            return response
    
    def configure_caching(self):
        """Configure caching headers for optimal performance."""
        
        @self.app.after_request
        def add_caching_headers(response):
            # Static files caching
            if request.endpoint and 'static' in request.endpoint:
                if self.app.debug:
                    response.headers['Cache-Control'] = 'no-cache'
                else:
                    response.headers['Cache-Control'] = 'public, max-age=3600'
                    expires_time = datetime.utcnow() + timedelta(seconds=3600)
                    response.headers['Expires'] = expires_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # API responses - no caching
            elif request.path.startswith('/api/'):
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            
            return response
    
    def configure_mobile_cors(self):
        """Configure CORS headers for mobile app compatibility."""
        
        # Mobile app origins
        mobile_origins = [
            'capacitor://localhost',  # Ionic/Capacitor
            'ionic://localhost',      # Ionic
            'http://localhost:3000',  # React Native development
            'http://localhost:19006', # Expo development
            'http://localhost:8080',  # Flutter development
            'https://laborlooker.com',
            'https://www.laborlooker.com'
        ]
        
        @self.app.after_request
        def add_cors_headers(response):
            origin = request.headers.get('Origin')
            
            # Check if origin is allowed
            if origin and (origin in mobile_origins or self.app.debug):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Max-Age'] = '3600'
            
            return response
    
    def configure_load_balancer(self):
        """Configure headers for Google Cloud Load Balancer compatibility."""
        
        @self.app.after_request
        def add_load_balancer_headers(response):
            # Google Cloud Load Balancer compatibility
            if not self.app.debug:
                response.headers['X-Forwarded-Proto'] = request.headers.get('X-Forwarded-Proto', 'https')
                
                # Health check response optimization
                if request.path in ['/health', '/_health', '/readiness']:
                    response.headers['Cache-Control'] = 'no-cache'
                    response.headers['Connection'] = 'close'
            
            return response
    
    def add_health_checks(self):
        """Add health check endpoints for Google Cloud Load Balancer."""
        
        @self.app.route('/health')
        @self.app.route('/_health')
        def health_check():
            """Health check endpoint for load balancer."""
            try:
                # Basic health check
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0'
                }), 200
                
            except Exception as e:
                logging.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503
        
        @self.app.route('/readiness')
        def readiness_check():
            """Readiness check endpoint."""
            return jsonify({
                'status': 'ready',
                'timestamp': datetime.utcnow().isoformat()
            }), 200
    
    def add_mobile_api_endpoints(self):
        """Add mobile-optimized API endpoints."""
        
        @self.app.route('/api/v1/health')
        def api_health():
            """Mobile API health check."""
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat(),
                'mobile_api': True
            })
        
        @self.app.route('/api/v1/auth/login', methods=['POST', 'OPTIONS'])
        def mobile_login():
            """Mobile-optimized login endpoint."""
            if request.method == 'OPTIONS':
                return '', 200
            
            # This would integrate with your existing auth system
            return jsonify({
                'status': 'success',
                'message': 'Mobile login endpoint ready',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        @self.app.route('/api/v1/contractors/search', methods=['GET', 'OPTIONS'])
        def mobile_contractor_search():
            """Mobile-optimized contractor search."""
            if request.method == 'OPTIONS':
                return '', 200
            
            # This would integrate with your existing search functionality
            return jsonify({
                'status': 'success',
                'contractors': [],
                'total': 0,
                'page': 1,
                'timestamp': datetime.utcnow().isoformat()
            })

def create_optimized_app():
    """Create an optimized Flask app with all performance enhancements."""
    from flask import Flask
    
    app = Flask(__name__)
    
    # Configure based on environment
    if os.getenv('FLASK_ENV') == 'production':
        app.debug = False
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'production-secret-key')
    else:
        app.debug = True
        app.config['SECRET_KEY'] = 'development-secret-key'
    
    # Initialize performance optimizer
    optimizer = PerformanceOptimizer(app)
    optimizer.add_mobile_api_endpoints()
    
    return app

if __name__ == '__main__':
    app = create_optimized_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.debug)