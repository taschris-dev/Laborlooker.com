"""
Mobile API Endpoints for LaborLooker App
Provides REST API for React Native and Flutter mobile applications
"""

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import jwt
import json
from functools import wraps

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api/v1')

# JWT token configuration
JWT_SECRET = app.config['SECRET_KEY']
JWT_EXPIRATION_HOURS = 24

def generate_jwt_token(user_id):
    """Generate JWT token for mobile authentication"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token and return user ID"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def mobile_auth_required(f):
    """Decorator for mobile API authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_jwt_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Add user to request context
        request.current_mobile_user = user
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# Health check endpoint
@api.route('/health')
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# Authentication endpoints
@api.route('/auth/login', methods=['POST'])
def mobile_login():
    """Mobile user login"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.email_verified:
        return jsonify({'error': 'Email not verified'}), 401
    
    if user.account_type == 'developer' and not user.approved:
        return jsonify({'error': 'Account pending approval'}), 401
    
    # Generate JWT token
    token = generate_jwt_token(user.id)
    
    # Get user profile data
    profile_data = None
    if user.account_type == 'contractor' and user.contractor_profile:
        profile = user.contractor_profile
        profile_data = {
            'business_name': profile.business_name,
            'contact_name': profile.contact_name,
            'phone': profile.phone,
            'location': profile.location,
            'geographic_area': profile.geographic_area,
            'services': profile.services.split(',') if profile.services else []
        }
    elif user.account_type == 'customer' and user.customer_profile:
        profile = user.customer_profile
        profile_data = {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'state': profile.state,
            'zip_code': profile.zip_code,
            'geographic_area': profile.geographic_area
        }
    
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'account_type': user.account_type,
            'profile': profile_data
        }
    })

@api.route('/auth/register', methods=['POST'])
def mobile_register():
    """Mobile user registration"""
    data = request.get_json()
    
    required_fields = ['email', 'password', 'account_type']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Email, password, and account_type required'}), 400
    
    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Validate password
    is_valid, message = validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': message}), 400
    
    # Create user
    from werkzeug.security import generate_password_hash
    user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        account_type=data['account_type'],
        approved=data['account_type'] != 'developer'
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Registration successful. Please verify your email.',
        'user_id': user.id
    }), 201

# User profile endpoints
@api.route('/users/profile', methods=['GET'])
@mobile_auth_required
def get_user_profile():
    """Get current user profile"""
    user = request.current_mobile_user
    
    profile_data = {
        'id': user.id,
        'email': user.email,
        'account_type': user.account_type,
        'email_verified': user.email_verified,
        'created_at': user.created_at.isoformat()
    }
    
    if user.account_type == 'contractor' and user.contractor_profile:
        profile = user.contractor_profile
        profile_data['contractor_profile'] = {
            'business_name': profile.business_name,
            'contact_name': profile.contact_name,
            'phone': profile.phone,
            'location': profile.location,
            'geographic_area': profile.geographic_area,
            'service_radius': profile.service_radius,
            'billing_plan': profile.billing_plan,
            'commission_rate': profile.commission_rate,
            'services': profile.services.split(',') if profile.services else [],
            'work_hours': json.loads(profile.work_hours) if profile.work_hours else {},
            'license_verified': profile.license_verified,
            'insurance_verified': profile.insurance_verified
        }
    elif user.account_type == 'customer' and user.customer_profile:
        profile = user.customer_profile
        profile_data['customer_profile'] = {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'state': profile.state,
            'zip_code': profile.zip_code,
            'geographic_area': profile.geographic_area
        }
    
    return jsonify(profile_data)

@api.route('/users/profile', methods=['PUT'])
@mobile_auth_required
def update_user_profile():
    """Update user profile"""
    user = request.current_mobile_user
    data = request.get_json()
    
    if user.account_type == 'contractor':
        profile = user.contractor_profile
        if not profile:
            profile = ContractorProfile(user_id=user.id)
            db.session.add(profile)
        
        # Update contractor profile fields
        if 'business_name' in data:
            profile.business_name = data['business_name']
        if 'contact_name' in data:
            profile.contact_name = data['contact_name']
        if 'phone' in data:
            profile.phone = data['phone']
        if 'location' in data:
            profile.location = data['location']
        if 'geographic_area' in data:
            profile.geographic_area = data['geographic_area']
        if 'service_radius' in data:
            profile.service_radius = data['service_radius']
        if 'services' in data:
            profile.services = ','.join(data['services']) if isinstance(data['services'], list) else data['services']
        if 'work_hours' in data:
            profile.work_hours = json.dumps(data['work_hours'])
        
    elif user.account_type == 'customer':
        profile = user.customer_profile
        if not profile:
            profile = CustomerProfile(user_id=user.id)
            db.session.add(profile)
        
        # Update customer profile fields
        if 'first_name' in data:
            profile.first_name = data['first_name']
        if 'last_name' in data:
            profile.last_name = data['last_name']
        if 'phone' in data:
            profile.phone = data['phone']
        if 'address' in data:
            profile.address = data['address']
        if 'city' in data:
            profile.city = data['city']
        if 'state' in data:
            profile.state = data['state']
        if 'zip_code' in data:
            profile.zip_code = data['zip_code']
        if 'geographic_area' in data:
            profile.geographic_area = data['geographic_area']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

# Work requests endpoints
@api.route('/work-requests', methods=['GET'])
@mobile_auth_required
def get_work_requests():
    """Get work requests for current user"""
    user = request.current_mobile_user
    
    if user.account_type == 'contractor':
        requests = WorkRequest.query.filter_by(contractor_id=user.id).all()
    elif user.account_type == 'customer':
        requests = WorkRequest.query.filter_by(customer_id=user.id).all()
    else:
        return jsonify({'error': 'Unauthorized'}), 403
    
    requests_data = []
    for req in requests:
        req_data = {
            'id': req.id,
            'status': req.status,
            'description': req.description,
            'title': req.title,
            'budget': req.budget,
            'timeline': req.timeline,
            'service_categories': json.loads(req.service_categories) if req.service_categories else [],
            'geographic_area': req.geographic_area,
            'created_at': req.created_at.isoformat(),
            'scheduled_date': req.scheduled_date.isoformat() if req.scheduled_date else None,
            'completed_date': req.completed_date.isoformat() if req.completed_date else None
        }
        
        # Add customer/contractor info based on user type
        if user.account_type == 'contractor' and req.customer:
            req_data['customer'] = {
                'email': req.customer.email,
                'name': req.customer_name
            }
        elif user.account_type == 'customer' and req.contractor:
            contractor_profile = req.contractor.contractor_profile
            req_data['contractor'] = {
                'email': req.contractor.email,
                'business_name': contractor_profile.business_name if contractor_profile else None,
                'contact_name': contractor_profile.contact_name if contractor_profile else None
            }
        
        requests_data.append(req_data)
    
    return jsonify(requests_data)

@api.route('/work-requests', methods=['POST'])
@mobile_auth_required
def create_work_request():
    """Create new work request (customers only)"""
    user = request.current_mobile_user
    
    if user.account_type != 'customer':
        return jsonify({'error': 'Only customers can create work requests'}), 403
    
    data = request.get_json()
    required_fields = ['title', 'description', 'service_categories', 'geographic_area']
    
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Create work request
    work_request = WorkRequest(
        customer_id=user.id,
        title=data['title'],
        description=data['description'],
        service_categories=json.dumps(data['service_categories']),
        geographic_area=data['geographic_area'],
        budget=data.get('budget'),
        timeline=data.get('timeline'),
        customer_name=data.get('customer_name'),
        customer_contact=data.get('customer_contact')
    )
    
    db.session.add(work_request)
    db.session.commit()
    
    return jsonify({
        'message': 'Work request created successfully',
        'id': work_request.id
    }), 201

@api.route('/work-requests/<int:request_id>', methods=['PUT'])
@mobile_auth_required
def update_work_request():
    """Update work request status"""
    user = request.current_mobile_user
    data = request.get_json()
    
    work_request = WorkRequest.query.get_or_404(request_id)
    
    # Check permissions
    if user.account_type == 'customer' and work_request.customer_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    elif user.account_type == 'contractor' and work_request.contractor_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Update allowed fields
    if 'status' in data:
        work_request.status = data['status']
    if 'scheduled_date' in data and data['scheduled_date']:
        work_request.scheduled_date = datetime.fromisoformat(data['scheduled_date'])
    if 'completed_date' in data and data['completed_date']:
        work_request.completed_date = datetime.fromisoformat(data['completed_date'])
    
    db.session.commit()
    
    return jsonify({'message': 'Work request updated successfully'})

# Contractor search endpoints
@api.route('/contractors/search', methods=['POST'])
@mobile_auth_required
def search_contractors():
    """Search for contractors based on criteria"""
    data = request.get_json()
    
    query = db.session.query(ContractorProfile).join(User)
    
    # Filter by service categories
    if data.get('service_categories'):
        services = data['service_categories']
        for service in services:
            query = query.filter(ContractorProfile.services.contains(service))
    
    # Filter by geographic area
    if data.get('geographic_area'):
        query = query.filter(ContractorProfile.geographic_area == data['geographic_area'])
    
    # Filter by service radius (if location provided)
    if data.get('location') and data.get('max_distance'):
        # For now, we'll use a simple filter - in production, use proper geo queries
        query = query.filter(ContractorProfile.service_radius >= data['max_distance'])
    
    contractors = query.all()
    
    results = []
    for contractor in contractors:
        results.append({
            'id': contractor.user_id,
            'business_name': contractor.business_name,
            'contact_name': contractor.contact_name,
            'location': contractor.location,
            'geographic_area': contractor.geographic_area,
            'services': contractor.services.split(',') if contractor.services else [],
            'license_verified': contractor.license_verified,
            'insurance_verified': contractor.insurance_verified,
            'commission_rate': contractor.commission_rate
        })
    
    return jsonify(results)

# Application configuration endpoints
@api.route('/config', methods=['GET'])
def get_app_config():
    """Get mobile app configuration"""
    return jsonify({
        'service_categories': SERVICE_CATEGORIES,
        'geographic_areas': GEOGRAPHIC_AREAS,
        'version': '1.0.0',
        'min_password_length': 15
    })

# Invoices endpoints
@api.route('/invoices', methods=['GET'])
@mobile_auth_required
def get_invoices():
    """Get invoices for current user"""
    user = request.current_mobile_user
    
    if user.account_type == 'contractor':
        invoices = ContractorInvoice.query.filter_by(contractor_id=user.id).all()
    elif user.account_type == 'customer':
        invoices = ContractorInvoice.query.filter_by(customer_id=user.id).all()
    else:
        return jsonify({'error': 'Unauthorized'}), 403
    
    invoices_data = []
    for invoice in invoices:
        invoices_data.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'description': invoice.description,
            'amount': invoice.amount,
            'total_amount': invoice.total_amount,
            'status': invoice.status,
            'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
            'created_at': invoice.created_at.isoformat(),
            'paid_at': invoice.paid_at.isoformat() if invoice.paid_at else None
        })
    
    return jsonify(invoices_data)

# Statistics endpoints
@api.route('/stats', methods=['GET'])
@mobile_auth_required
def get_user_stats():
    """Get user statistics"""
    user = request.current_mobile_user
    
    if user.account_type == 'contractor':
        total_requests = WorkRequest.query.filter_by(contractor_id=user.id).count()
        completed_requests = WorkRequest.query.filter_by(
            contractor_id=user.id, 
            status='completed'
        ).count()
        pending_requests = WorkRequest.query.filter_by(
            contractor_id=user.id, 
            status='pending'
        ).count()
        
        return jsonify({
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'completion_rate': (completed_requests / total_requests * 100) if total_requests > 0 else 0
        })
    
    elif user.account_type == 'customer':
        total_requests = WorkRequest.query.filter_by(customer_id=user.id).count()
        completed_requests = WorkRequest.query.filter_by(
            customer_id=user.id, 
            status='completed'
        ).count()
        
        return jsonify({
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'active_requests': total_requests - completed_requests
        })
    
    return jsonify({'error': 'No stats available'}), 400

# Register the blueprint with the main app
def register_mobile_api(app):
    """Register mobile API blueprint with Flask app"""
    app.register_blueprint(api)
