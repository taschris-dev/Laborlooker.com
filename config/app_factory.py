from flask import Flask, jsonify, request, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
import os
import logging
from datetime import datetime, timedelta
import redis
import importlib

def create_app(config_name='development'):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    
    # Load configuration based on environment
    if config_name == 'production':
        config_module = importlib.import_module('config.production')
    else:
        config_module = importlib.import_module('config.development')
    
    # Apply configuration to app
    for setting in dir(config_module):
        if setting.isupper():
            setattr(app, setting, getattr(config_module, setting))
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, getattr(app, 'LOG_LEVEL', 'INFO')),
        format=getattr(app, 'LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Configure error handlers
    configure_error_handlers(app)
    
    # Configure security headers and middleware
    configure_security(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions."""
    
    # Configure CORS
    CORS(app, 
         origins=getattr(app, 'CORS_ORIGINS', ['http://localhost:3000']),
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         supports_credentials=True)
    
    # Configure rate limiting
    if getattr(app, 'RATE_LIMIT_ENABLED', False):
        limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=[getattr(app, 'RATE_LIMIT_DEFAULT', '100 per hour')],
            storage_uri="redis://localhost:6379/2"
        )
        app.limiter = limiter
    
    # Configure caching
    cache_type = getattr(app, 'CACHE_TYPE', 'simple')
    if cache_type == "redis":
        try:
            cache = Cache(app, config={
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': 'redis://localhost:6379/3',
                'CACHE_DEFAULT_TIMEOUT': getattr(app, 'CACHE_DEFAULT_TIMEOUT', 300),
                'CACHE_KEY_PREFIX': getattr(app, 'CACHE_KEY_PREFIX', 'laborlooker:')
            })
            app.cache = cache
        except Exception as e:
            logging.warning(f"Redis cache not available, falling back to simple cache: {e}")
            cache = Cache(app, config={'CACHE_TYPE': 'simple'})
            app.cache = cache
    else:
        cache = Cache(app, config={'CACHE_TYPE': 'simple'})
        app.cache = cache

def register_blueprints(app):
    """Register application blueprints."""
    
    # Main application routes
    from routes.main import main_bp
    app.register_blueprint(main_bp)
    
    # API routes
    from routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix=f'/api/{API_VERSION}')
    
    # Authentication routes
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Admin routes
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

def configure_error_handlers(app):
    """Configure error handlers for the application."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def rate_limit_error(error):
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': str(error.description)
            }), 429
        return render_template('errors/429.html'), 429

def configure_security(app):
    """Configure security headers and middleware."""
    
    @app.after_request
    def after_request(response):
        from datetime import timedelta
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add Content Security Policy
        csp_parts = [
            f"default-src {CSP_DEFAULT_SRC}",
            f"script-src {CSP_SCRIPT_SRC}",
            f"style-src {CSP_STYLE_SRC}",
            f"font-src {CSP_FONT_SRC}",
            f"img-src {CSP_IMG_SRC}",
            f"connect-src {CSP_CONNECT_SRC}"
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_parts)
        
        # CORS headers for mobile apps
        origin = request.headers.get('Origin')
        if origin in CORS_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        # Caching headers
        if request.endpoint and 'static' in request.endpoint:
            response.headers['Cache-Control'] = f'public, max-age={CDN_CACHE_TIMEOUT}'
            response.headers['Expires'] = (datetime.utcnow() + timedelta(seconds=CDN_CACHE_TIMEOUT)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        elif request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # Google Cloud Load Balancer compatibility
        if TRUST_PROXY_HEADERS:
            response.headers['X-Forwarded-Proto'] = request.headers.get('X-Forwarded-Proto', 'https')
        
        return response
    
    # Configure proxy fix for Google Cloud Load Balancer
    if TRUST_PROXY_HEADERS:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=PROXY_FIX_X_FOR,
            x_proto=PROXY_FIX_X_PROTO,
            x_host=PROXY_FIX_X_HOST,
            x_prefix=PROXY_FIX_X_PREFIX
        )

# Health check endpoint for Google Cloud Load Balancer
def configure_health_checks(app):
    """Configure health check endpoints."""
    
    @app.route('/health')
    @app.route('/_health')
    def health_check():
        from flask import jsonify
        try:
            # Check database connection
            # db.session.execute('SELECT 1')
            
            # Check Redis connection if available
            if hasattr(app, 'cache') and hasattr(app.cache.cache, '_write_client'):
                app.cache.cache._write_client.ping()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': API_VERSION
            }), 200
            
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    
    @app.route('/readiness')
    def readiness_check():
        from flask import jsonify
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    configure_health_checks(app)
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)