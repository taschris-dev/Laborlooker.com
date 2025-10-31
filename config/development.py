# Development Configuration for Local Testing

# Rate Limiting Configuration (more permissive for development)
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DEFAULT = "1000 per hour"
RATE_LIMIT_LOGIN = "50 per minute"
RATE_LIMIT_API = "500 per hour"

# Caching Configuration (local Redis or in-memory)
CACHE_TYPE = "simple"  # Use simple cache for development
CACHE_DEFAULT_TIMEOUT = 60  # 1 minute for faster development
CACHE_KEY_PREFIX = "dev_laborlooker:"

# Security Configuration (relaxed for development)
SECRET_KEY_MIN_LENGTH = 16
BCRYPT_LOG_ROUNDS = 4  # Faster for development
JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 hours
JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days

# Local Database Configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 5,
    "pool_timeout": 10,
    "pool_recycle": 3600,
    "max_overflow": 10,
    "pool_pre_ping": True
}

# CORS Configuration for Development (more permissive)
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://localhost:19006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "capacitor://localhost",
    "ionic://localhost"
]

# Security Headers Configuration (relaxed for development)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block"
}

# Content Security Policy (relaxed for development)
CSP_DEFAULT_SRC = "'self' 'unsafe-inline' 'unsafe-eval'"
CSP_SCRIPT_SRC = "'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com"
CSP_STYLE_SRC = "'self' 'unsafe-inline' https://fonts.googleapis.com"
CSP_FONT_SRC = "'self' https://fonts.gstatic.com"
CSP_IMG_SRC = "'self' data: https: blob:"
CSP_CONNECT_SRC = "'self' http://localhost:* https://api.laborlooker.com"

# API Configuration
API_VERSION = "v1"
API_RATE_LIMIT = "1000 per hour"
API_TIMEOUT = 60

# File Upload Configuration
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB for development
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Local File Storage Configuration
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"

# Monitoring and Logging
LOG_LEVEL = "DEBUG"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
ENABLE_METRICS = False
METRICS_PORT = 8081

# Mobile App Configuration
MOBILE_API_ENABLED = True
MOBILE_PUSH_NOTIFICATIONS = False  # Disabled for development
MOBILE_OFFLINE_SYNC = True

# Development Server Configuration
DEBUG = True
TESTING = False
TRUST_PROXY_HEADERS = False

# Health Check Configuration
HEALTH_CHECK_TIMEOUT = 10
HEALTH_CHECK_INTERVAL = 60

# Session Configuration
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True
SESSION_KEY_PREFIX = "dev_laborlooker:"
SESSION_REDIS = False  # Use filesystem sessions for development
PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

# Email Configuration (development/testing)
MAIL_SERVER = "localhost"
MAIL_PORT = 1025  # MailHog or similar
MAIL_USE_TLS = False
MAIL_DEFAULT_SENDER = "dev@laborlooker.com"

# Pagination Configuration
POSTS_PER_PAGE = 10
MAX_SEARCH_RESULTS = 50

# Background Task Configuration (local Redis)
CELERY_BROKER_URL = "redis://localhost:6379/1"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"

# CDN Configuration (disabled for development)
CDN_ENABLED = False
CDN_CACHE_TIMEOUT = 0
STATIC_URL_PREFIX = "/static"

# Database Configuration
DATABASE_POOL_SIZE = 5
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_TIMEOUT = 10
DATABASE_POOL_RECYCLE = 1800

# API Documentation
SWAGGER_ENABLED = True
SWAGGER_URL = "/api/docs"
API_DOCS_URL = "/api/v1/docs"

# Flask Development Configuration
FLASK_ENV = "development"
FLASK_DEBUG = True
TEMPLATES_AUTO_RELOAD = True
SEND_FILE_MAX_AGE_DEFAULT = 0

# Hot Reload Configuration
RELOAD_ON_CHANGE = True
WATCH_TEMPLATE_CHANGES = True