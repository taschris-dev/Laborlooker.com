# Performance and Security Configuration for Google Cloud Deployment

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DEFAULT = "100 per hour"
RATE_LIMIT_LOGIN = "10 per minute"
RATE_LIMIT_API = "200 per hour"

# Caching Configuration
CACHE_TYPE = "redis"  # Use Redis for Google Cloud Memorystore
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
CACHE_KEY_PREFIX = "laborlooker:"

# Security Configuration
SECRET_KEY_MIN_LENGTH = 32
BCRYPT_LOG_ROUNDS = 12
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days

# Google Cloud SQL Configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "max_overflow": 20,
    "pool_pre_ping": True
}

# CORS Configuration for Mobile Apps
CORS_ORIGINS = [
    "https://laborlooker.com",
    "https://www.laborlooker.com",
    "https://api.laborlooker.com",
    "capacitor://localhost",  # Ionic/Capacitor
    "ionic://localhost",      # Ionic
    "http://localhost:3000",  # React Native development
    "http://localhost:19006", # Expo development
    "http://localhost:8080",  # Flutter development
]

# Security Headers Configuration
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(self), microphone=()"
}

# Content Security Policy
CSP_DEFAULT_SRC = "'self'"
CSP_SCRIPT_SRC = "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://code.jquery.com"
CSP_STYLE_SRC = "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com"
CSP_FONT_SRC = "'self' https://fonts.gstatic.com"
CSP_IMG_SRC = "'self' data: https: blob:"
CSP_CONNECT_SRC = "'self' https://api.laborlooker.com wss://laborlooker.com"

# API Configuration
API_VERSION = "v1"
API_RATE_LIMIT = "200 per hour"
API_TIMEOUT = 30

# File Upload Configuration
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

# Google Cloud Storage Configuration
GCS_BUCKET_NAME = "laborlooker-uploads"
GCS_UPLOAD_TIMEOUT = 60

# Monitoring and Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
ENABLE_METRICS = True
METRICS_PORT = 8080

# Mobile App Configuration
MOBILE_API_ENABLED = True
MOBILE_PUSH_NOTIFICATIONS = True
MOBILE_OFFLINE_SYNC = True

# Google Cloud Load Balancer Configuration
TRUST_PROXY_HEADERS = True
PROXY_FIX_X_FOR = 1
PROXY_FIX_X_PROTO = 1
PROXY_FIX_X_HOST = 1
PROXY_FIX_X_PREFIX = 1

# Health Check Configuration
HEALTH_CHECK_TIMEOUT = 5
HEALTH_CHECK_INTERVAL = 30

# Session Configuration
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True
SESSION_KEY_PREFIX = "laborlooker:"
SESSION_REDIS = True
PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes

# Email Configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_DEFAULT_SENDER = "noreply@laborlooker.com"

# Pagination Configuration
POSTS_PER_PAGE = 20
MAX_SEARCH_RESULTS = 100

# Background Task Configuration
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"

# Google Cloud CDN Configuration
CDN_ENABLED = True
CDN_CACHE_TIMEOUT = 3600
STATIC_URL_PREFIX = "https://cdn.laborlooker.com"

# Database Connection Pooling
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600

# API Documentation
SWAGGER_ENABLED = True
SWAGGER_URL = "/api/docs"
API_DOCS_URL = "/api/v1/docs"