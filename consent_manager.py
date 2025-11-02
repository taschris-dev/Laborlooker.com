# LaborLooker Consent Management System
# Legal-compliant data collection with granular user control

from datetime import datetime, timedelta
from flask import request, jsonify, session
from functools import wraps

class ConsentManager:
    """
    Manages user consent preferences for GDPR/CCPA compliance
    """
    
    # Consent types and their purposes
    CONSENT_TYPES = {
        'essential': {
            'required': True,
            'purpose': 'Core platform functionality, safety, and legal compliance',
            'includes': ['profile_data', 'safety_verification', 'payment_processing', 'legal_compliance']
        },
        'marketing_communications': {
            'required': False,
            'purpose': 'Personalized job alerts, recommendations, and platform updates',
            'includes': ['email_marketing', 'push_notifications', 'sms_alerts']
        },
        'personalization': {
            'required': False,
            'purpose': 'AI-powered matching, customized experience, smart recommendations',
            'includes': ['behavior_tracking', 'preference_learning', 'ai_recommendations']
        },
        'market_research': {
            'required': False,
            'purpose': 'Anonymized insights for platform development and industry analysis',
            'includes': ['usage_analytics', 'market_insights', 'product_research']
        },
        'performance_analytics': {
            'required': False,
            'purpose': 'Platform optimization, bug fixes, and performance monitoring',
            'includes': ['error_tracking', 'performance_monitoring', 'usage_statistics']
        },
        'marketing_analytics': {
            'required': False,
            'purpose': 'Campaign effectiveness and content optimization',
            'includes': ['campaign_tracking', 'content_optimization', 'engagement_metrics']
        }
    }

    @staticmethod
    def process_consent_form(form_data, user_id):
        """
        Process consent form submission and store preferences
        """
        consent_record = {
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            'user_agent': request.headers.get('User-Agent'),
            'consent_version': '2.0',  # Track consent form version
            'preferences': {}
        }
        
        # Process each consent type
        for consent_type, config in ConsentManager.CONSENT_TYPES.items():
            if config['required']:
                # Required consents must be checked
                field_name = 'data_collection' if consent_type == 'essential' else consent_type
                if form_data.get(field_name) or form_data.get('safety_verification'):
                    consent_record['preferences'][consent_type] = {
                        'granted': True,
                        'timestamp': datetime.utcnow()
                    }
                else:
                    return {'error': f'Required consent for {consent_type} not provided', 'code': 400}
            else:
                # Optional consents
                field_name = consent_type
                if consent_type == 'performance_analytics':
                    field_name = 'cookies_analytics'
                elif consent_type == 'marketing_analytics':
                    field_name = 'cookies_marketing'
                
                granted = bool(form_data.get(field_name))
                consent_record['preferences'][consent_type] = {
                    'granted': granted,
                    'timestamp': datetime.utcnow()
                }
        
        # Store in database (UserConsent model)
        try:
            from main import UserConsent, db
            
            # Remove existing consent record for this user
            UserConsent.query.filter_by(user_id=user_id).delete()
            
            # Create new consent record
            new_consent = UserConsent(
                user_id=user_id,
                consent_data=consent_record,
                granted_at=datetime.utcnow(),
                version='2.0'
            )
            db.session.add(new_consent)
            db.session.commit()
            
            return {'success': True, 'consent_id': new_consent.id}
            
        except Exception as e:
            return {'error': f'Failed to store consent: {str(e)}', 'code': 500}

    @staticmethod
    def check_consent(user_id, consent_type):
        """
        Check if user has granted specific consent
        """
        try:
            from main import UserConsent
            
            consent_record = UserConsent.query.filter_by(user_id=user_id).first()
            if not consent_record:
                return False
                
            preferences = consent_record.consent_data.get('preferences', {})
            consent_info = preferences.get(consent_type, {})
            
            return consent_info.get('granted', False)
            
        except Exception:
            return False

    @staticmethod
    def get_user_consent_summary(user_id):
        """
        Get summary of user's consent choices
        """
        try:
            from main import UserConsent
            
            consent_record = UserConsent.query.filter_by(user_id=user_id).first()
            if not consent_record:
                return None
                
            summary = {
                'granted_at': consent_record.granted_at,
                'version': consent_record.version,
                'preferences': {}
            }
            
            preferences = consent_record.consent_data.get('preferences', {})
            for consent_type, config in ConsentManager.CONSENT_TYPES.items():
                consent_info = preferences.get(consent_type, {})
                summary['preferences'][consent_type] = {
                    'granted': consent_info.get('granted', False),
                    'required': config['required'],
                    'purpose': config['purpose']
                }
            
            return summary
            
        except Exception:
            return None

    @staticmethod
    def update_consent(user_id, consent_type, granted):
        """
        Update specific consent preference
        """
        if ConsentManager.CONSENT_TYPES.get(consent_type, {}).get('required', False):
            return {'error': 'Cannot withdraw required consent', 'code': 400}
            
        try:
            from main import UserConsent, db
            
            consent_record = UserConsent.query.filter_by(user_id=user_id).first()
            if not consent_record:
                return {'error': 'No consent record found', 'code': 404}
            
            # Update the specific consent
            consent_data = consent_record.consent_data
            if 'preferences' not in consent_data:
                consent_data['preferences'] = {}
            
            consent_data['preferences'][consent_type] = {
                'granted': granted,
                'timestamp': datetime.utcnow()
            }
            
            consent_record.consent_data = consent_data
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            return {'error': f'Failed to update consent: {str(e)}', 'code': 500}


def require_consent(consent_type):
    """
    Decorator to check if user has granted specific consent
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
                
            if not ConsentManager.check_consent(current_user.id, consent_type):
                return jsonify({
                    'error': f'Consent required for {consent_type}',
                    'consent_type': consent_type,
                    'purpose': ConsentManager.CONSENT_TYPES.get(consent_type, {}).get('purpose', ''),
                    'manage_url': '/privacy/settings'
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_allowed_features(user_id):
    """
    Get list of features available to user based on consent
    """
    features = {
        'core_platform': True,  # Always available
        'basic_matching': True,  # Always available
        'payment_processing': True,  # Always available
        'safety_features': True,  # Always available
    }
    
    # Optional features based on consent
    if ConsentManager.check_consent(user_id, 'marketing_communications'):
        features.update({
            'job_alerts': True,
            'email_recommendations': True,
            'platform_updates': True
        })
    
    if ConsentManager.check_consent(user_id, 'personalization'):
        features.update({
            'ai_recommendations': True,
            'smart_matching': True,
            'customized_dashboard': True,
            'behavioral_insights': True
        })
    
    if ConsentManager.check_consent(user_id, 'performance_analytics'):
        features.update({
            'performance_tracking': True,
            'error_reporting': True,
            'usage_optimization': True
        })
    
    if ConsentManager.check_consent(user_id, 'marketing_analytics'):
        features.update({
            'campaign_tracking': True,
            'content_personalization': True,
            'engagement_metrics': True
        })
    
    return features


# Usage examples in route handlers:

"""
@app.route('/api/job-recommendations')
@login_required
@require_consent('personalization')
def get_job_recommendations():
    # This endpoint only works if user consented to personalization
    return jsonify(get_ai_recommendations(current_user.id))

@app.route('/api/send-job-alert', methods=['POST'])
@login_required  
@require_consent('marketing_communications')
def send_job_alert():
    # This endpoint only works if user consented to marketing
    return jsonify(send_alert(current_user.id))

@app.route('/api/track-engagement', methods=['POST'])
@login_required
def track_engagement():
    # Only track if user consented
    if ConsentManager.check_consent(current_user.id, 'marketing_analytics'):
        track_user_engagement(current_user.id, request.json)
    return jsonify({'status': 'ok'})
"""