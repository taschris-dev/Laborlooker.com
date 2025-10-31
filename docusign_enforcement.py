"""
DocuSign Enforcement Middleware for LaborLooker
Automatically enforces document requirements at all critical points
"""

from functools import wraps
from datetime import datetime
from flask import request, redirect, url_for, flash, session
from main import db, User
from docusign_functional import docusign_manager
import logging

logger = logging.getLogger('docusign_enforcement')

def require_contractor_documents(action=None):
    """Decorator to enforce contractor document requirements"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user or not user.contractor_profile:
                flash('Contractor profile required', 'error')
                return redirect(url_for('contractor_dashboard'))
            
            # Check document requirements
            documents_complete, missing_docs = docusign_manager.check_document_requirements(user, action)
            
            if not documents_complete:
                # Automatically send missing documents
                for doc_type in missing_docs:
                    docusign_manager._send_required_document(user, doc_type)
                
                flash(f'Required documents pending: {", ".join(missing_docs)}. Check your email to sign.', 'warning')
                return redirect(url_for('contractor_documents_required'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_project_contract_required():
    """Decorator for project-related actions requiring signed contracts"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract project/job ID from route parameters
            project_id = kwargs.get('project_id') or request.form.get('project_id') or request.args.get('project_id')
            
            if project_id and 'user_id' in session:
                user = User.query.get(session['user_id'])
                
                # Check if project contract exists and is signed
                from main import ContractDocument, JobInvitation
                
                invitation = JobInvitation.query.filter_by(
                    id=project_id,
                    contractor_id=user.id
                ).first()
                
                if invitation and not invitation.contract_signed:
                    # Send project contract
                    contract_sent = docusign_manager.send_project_contract(user, invitation)
                    if contract_sent:
                        flash('Project contract sent for signing. Please check your email.', 'info')
                        return redirect(url_for('contractor_projects'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class DocumentEnforcementMiddleware:
    """Middleware to automatically enforce document requirements"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        app.before_request(self.before_request)
        
        # Add routes for document handling
        app.add_url_rule('/contractor/documents/required', 
                        'contractor_documents_required', 
                        self.documents_required_page, 
                        methods=['GET'])
        
        app.add_url_rule('/docusign/webhook', 
                        'docusign_webhook', 
                        self.handle_webhook, 
                        methods=['POST'])
    
    def before_request(self):
        """Check document requirements before each request"""
        
        # Skip for static files and certain routes
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint in ['login', 'register', 'docusign_webhook', 'contractor_documents_required'])):
            return
        
        # Check contractor document requirements for specific routes
        contractor_routes = [
            'contractor_dashboard',
            'accept_job',
            'submit_quote',
            'contractor_profile',
            'contractor_projects',
            'upload_work_photos',
            'request_payment'
        ]
        
        if request.endpoint in contractor_routes and 'user_id' in session:
            user = User.query.get(session['user_id'])
            
            if user and user.contractor_profile:
                # Determine required action
                action_map = {
                    'accept_job': 'project_acceptance',
                    'submit_quote': 'project_acceptance', 
                    'request_payment': 'payment_processing',
                    'contractor_profile': 'profile_activation'
                }
                
                action = action_map.get(request.endpoint, 'contractor_registration')
                
                documents_complete, missing_docs = docusign_manager.check_document_requirements(user, action)
                
                if not documents_complete:
                    # Auto-send missing documents
                    for doc_type in missing_docs:
                        docusign_manager._send_required_document(user, doc_type)
                    
                    flash(f'Required documents pending: {", ".join(missing_docs)}', 'warning')
                    return redirect(url_for('contractor_documents_required'))
    
    def documents_required_page(self):
        """Page showing required documents status"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            return redirect(url_for('login'))
        
        # Get document status
        from main import ContractDocument, render_template
        
        pending_contracts = ContractDocument.query.filter_by(
            user_id=user.id,
            required=True
        ).filter(ContractDocument.status.in_(['sent', 'delivered'])).all()
        
        completed_contracts = ContractDocument.query.filter_by(
            user_id=user.id,
            status='completed'
        ).all()
        
        return render_template('contractor/documents_required.html',
                             pending_contracts=pending_contracts,
                             completed_contracts=completed_contracts,
                             user=user)
    
    def handle_webhook(self):
        """Handle DocuSign webhook"""
        webhook_data = request.get_json()
        
        if docusign_manager.handle_webhook(webhook_data):
            return {'status': 'success'}, 200
        else:
            return {'error': 'Webhook processing failed'}, 500

# Auto-enforcement functions for specific workflows

def enforce_contractor_registration(user):
    """Enforce document requirements during contractor registration"""
    if not user.contractor_profile:
        return False, "No contractor profile"
    
    # Check and send required documents
    documents_complete, missing_docs = docusign_manager.require_contractor_documents(user)
    
    if not documents_complete:
        logger.info(f"Sent required documents to new contractor: {user.email}")
        return False, f"Required documents sent: {', '.join(missing_docs)}"
    
    return True, "All documents complete"

def enforce_project_contract(invitation):
    """Enforce project contract signing"""
    from main import ContractDocument
    
    # Check if project contract exists
    contract = ContractDocument.query.filter_by(
        user_id=invitation.contractor_id,
        document_type='project_contract'
    ).filter(ContractDocument.template_data.contains(f'"project_id": "{invitation.id}"')).first()
    
    if not contract or contract.status != 'completed':
        # Send project contract
        contractor = User.query.get(invitation.contractor_id)
        if contractor:
            docusign_manager.send_project_contract(contractor, invitation)
            return False, "Project contract sent for signing"
    
    return True, "Project contract signed"

def enforce_payment_authorization(user, amount):
    """Enforce payment processing requirements"""
    
    # Check contractor documents
    documents_complete, missing_docs = docusign_manager.check_document_requirements(user, 'payment_processing')
    
    if not documents_complete:
        return False, f"Missing payment authorization documents: {', '.join(missing_docs)}"
    
    # Check for high-value payment requirements
    if amount > 5000:  # $5000+ requires additional verification
        high_value_contract = ContractDocument.query.filter_by(
            user_id=user.id,
            document_type='high_value_authorization',
            status='completed'
        ).first()
        
        if not high_value_contract:
            docusign_manager._send_required_document(user, 'high_value_authorization')
            return False, "High-value payment authorization required"
    
    return True, "Payment authorized"

# Template data generators for different document types

def generate_contractor_agreement_data(user):
    """Generate data for contractor agreement template"""
    contractor = user.contractor_profile
    
    return {
        'contractor_name': contractor.contact_name or user.name,
        'business_name': contractor.business_name or 'Individual Contractor',
        'business_address': contractor.location or '',
        'phone': contractor.phone or '',
        'email': user.email,
        'license_number': contractor.license_number or 'N/A',
        'insurance_company': contractor.insurance_company or '',
        'insurance_policy': contractor.insurance_policy_number or '',
        'date': datetime.now().strftime('%B %d, %Y'),
        'platform_fee': '10%',
        'payment_processing_fee': '2.9% + $0.30',
        'commission_rate': '10%',
        'territory': contractor.service_areas or 'As specified in profile'
    }

def generate_project_contract_data(user, invitation):
    """Generate data for project contract template"""
    from main import JobPost
    
    job = JobPost.query.get(invitation.job_id)
    
    return {
        'contractor_name': user.contractor_profile.contact_name or user.name,
        'customer_name': job.customer.name if job else 'Customer',
        'project_title': job.title if job else 'Project',
        'project_description': job.description if job else '',
        'project_budget': f"${invitation.quote_amount}" if invitation.quote_amount else 'TBD',
        'start_date': invitation.proposed_start_date.strftime('%B %d, %Y') if invitation.proposed_start_date else 'TBD',
        'completion_date': invitation.estimated_completion.strftime('%B %d, %Y') if invitation.estimated_completion else 'TBD',
        'payment_terms': 'Net 30 days via LaborLooker platform',
        'platform_fee': '10%',
        'date': datetime.now().strftime('%B %d, %Y')
    }