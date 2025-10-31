"""
Comprehensive Document Requirements System for LaborLooker
Binding legal documents required for every impactful platform action
"""

from datetime import datetime, timedelta
from main import db, User, ContractDocument
from functools import wraps
from flask import session, redirect, url_for, flash, request

class ComprehensiveDocumentManager:
    """Manages all required documents for every platform action"""
    
    def __init__(self):
        # Document requirements mapped to specific actions
        self.action_documents = {
            # ACCOUNT MANAGEMENT
            'account_creation': [
                'platform_terms_of_service',
                'privacy_policy_agreement', 
                'data_collection_consent',
                'user_conduct_agreement',
                'liability_disclaimer'
            ],
            
            # CONTRACTOR ACTIONS
            'contractor_registration': [
                'contractor_service_agreement',
                'liability_waiver_release',
                'insurance_verification_form',
                'background_check_consent',
                'platform_commission_agreement',
                'work_quality_standards',
                'dispute_resolution_agreement'
            ],
            
            'quote_scheduling': [
                'site_visit_liability_waiver',
                'property_access_agreement',
                'quote_terms_conditions',
                'customer_information_consent'
            ],
            
            'job_acceptance': [
                'project_contract_template',
                'scope_of_work_agreement',
                'payment_terms_acceptance',
                'completion_timeline_commitment',
                'quality_guarantee_acknowledgment',
                'change_order_procedures'
            ],
            
            'payment_processing': [
                'payment_authorization_form',
                'tax_information_consent',
                'platform_fee_acknowledgment',
                'dispute_resolution_waiver',
                'direct_deposit_authorization'
            ],
            
            # CUSTOMER ACTIONS
            'customer_registration': [
                'customer_terms_of_service',
                'payment_processing_agreement',
                'contractor_selection_waiver',
                'property_information_consent',
                'dispute_resolution_agreement'
            ],
            
            'job_posting': [
                'job_posting_terms',
                'contractor_vetting_disclaimer',
                'payment_escrow_agreement',
                'property_access_authorization',
                'work_supervision_waiver'
            ],
            
            'contractor_hiring': [
                'contractor_selection_acknowledgment',
                'work_supervision_responsibility',
                'payment_release_authorization',
                'quality_dispute_procedures',
                'completion_acceptance_terms'
            ],
            
            # PII AND DATA ACTIONS
            'pii_collection': [
                'personal_information_consent',
                'data_processing_agreement',
                'third_party_sharing_consent',
                'data_retention_acknowledgment',
                'rights_and_remedies_notice'
            ],
            
            'data_sharing': [
                'data_sharing_authorization',
                'third_party_disclosure_consent',
                'marketing_communications_opt_in',
                'analytics_data_consent'
            ],
            
            # FINANCIAL TRANSACTIONS
            'payment_user_to_user': [
                'peer_to_peer_payment_agreement',
                'transaction_fee_disclosure',
                'dispute_resolution_waiver',
                'chargeback_liability_agreement',
                'tax_reporting_consent'
            ],
            
            'refund_processing': [
                'refund_policy_acknowledgment',
                'dispute_mediation_agreement',
                'platform_fee_non_refundable_notice'
            ],
            
            # BUSINESS ACTIONS  
            'company_application': [
                'business_verification_consent',
                'corporate_liability_agreement',
                'business_insurance_verification',
                'employee_background_check_consent',
                'commercial_terms_agreement'
            ],
            
            'business_profile_creation': [
                'business_information_accuracy_oath',
                'license_verification_consent',
                'insurance_certificate_sharing',
                'employee_conduct_responsibility'
            ],
            
            # PLATFORM FEATURES
            'review_submission': [
                'review_accuracy_oath',
                'defamation_liability_waiver',
                'content_ownership_transfer'
            ],
            
            'messaging_system': [
                'communication_monitoring_consent',
                'harassment_prevention_agreement',
                'content_moderation_acceptance'
            ],
            
            'photo_upload': [
                'image_rights_transfer',
                'property_photography_consent',
                'privacy_expectations_waiver'
            ]
        }
        
        # Document templates with legal enforceability
        self.document_templates = {
            'platform_terms_of_service': {
                'name': 'LaborLooker Platform Terms of Service',
                'template_id': 'TERMS_TEMPLATE_ID',
                'enforceability': 'binding_contract',
                'renewal_period': 365  # days
            },
            
            'privacy_policy_agreement': {
                'name': 'Privacy Policy and Data Collection Agreement', 
                'template_id': 'PRIVACY_TEMPLATE_ID',
                'enforceability': 'legal_consent',
                'renewal_period': 180
            },
            
            'contractor_service_agreement': {
                'name': 'Contractor Service Agreement',
                'template_id': 'CONTRACTOR_TEMPLATE_ID', 
                'enforceability': 'binding_contract',
                'renewal_period': 365
            },
            
            'liability_waiver_release': {
                'name': 'Comprehensive Liability Waiver and Release',
                'template_id': 'LIABILITY_TEMPLATE_ID',
                'enforceability': 'liability_waiver',
                'renewal_period': 365
            },
            
            'project_contract_template': {
                'name': 'Project-Specific Work Contract',
                'template_id': 'PROJECT_TEMPLATE_ID',
                'enforceability': 'binding_contract',
                'renewal_period': 0  # Per-project basis
            },
            
            'payment_authorization_form': {
                'name': 'Payment Processing Authorization',
                'template_id': 'PAYMENT_TEMPLATE_ID',
                'enforceability': 'financial_authorization',
                'renewal_period': 180
            },
            
            'data_collection_consent': {
                'name': 'Data Collection and Processing Consent',
                'template_id': 'DATA_TEMPLATE_ID',
                'enforceability': 'gdpr_consent',
                'renewal_period': 365
            },
            
            'dispute_resolution_agreement': {
                'name': 'Binding Arbitration and Dispute Resolution',
                'template_id': 'DISPUTE_TEMPLATE_ID',
                'enforceability': 'arbitration_agreement',
                'renewal_period': 730  # 2 years
            }
        }
    
    def check_action_requirements(self, user, action, context=None):
        """Check if user has all required documents for specific action"""
        
        if action not in self.action_documents:
            return True, []  # No requirements for unknown actions
        
        required_docs = self.action_documents[action]
        missing_docs = []
        expired_docs = []
        
        for doc_type in required_docs:
            # Check if document exists and is current
            contract = ContractDocument.query.filter_by(
                user_id=user.id,
                document_type=doc_type,
                status='completed'
            ).order_by(ContractDocument.completed_at.desc()).first()
            
            if not contract:
                missing_docs.append(doc_type)
            else:
                # Check if document has expired
                template_info = self.document_templates.get(doc_type, {})
                renewal_period = template_info.get('renewal_period', 0)
                
                if renewal_period > 0:
                    expiry_date = contract.completed_at + timedelta(days=renewal_period)
                    if datetime.utcnow() > expiry_date:
                        expired_docs.append(doc_type)
        
        all_missing = missing_docs + expired_docs
        
        if all_missing:
            # Automatically send missing/expired documents
            self._send_required_documents(user, all_missing, action, context)
            return False, all_missing
        
        return True, []
    
    def _send_required_documents(self, user, document_types, action, context):
        """Send required documents via DocuSign"""
        
        for doc_type in document_types:
            template_info = self.document_templates.get(doc_type, {})
            
            if not template_info:
                continue
            
            # Prepare document data based on action context
            template_data = self._prepare_action_specific_data(user, action, doc_type, context)
            
            # Create DocuSign envelope (simplified for now)
            envelope_data = {
                'envelopeId': f"env_{doc_type}_{user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'status': 'sent'
            }
            
            # Save contract record
            contract = ContractDocument(
                user_id=user.id,
                envelope_id=envelope_data['envelopeId'],
                document_type=doc_type,
                status='sent',
                document_name=template_info['name'],
                sent_at=datetime.utcnow(),
                action_context=action,
                template_data=str(template_data)  # Store as JSON string
            )
            
            db.session.add(contract)
        
        db.session.commit()
    
    def _prepare_action_specific_data(self, user, action, doc_type, context):
        """Prepare document data specific to the action being performed"""
        
        base_data = {
            'user_name': user.name,
            'user_email': user.email,
            'action_context': action,
            'date': datetime.now().strftime('%B %d, %Y'),
            'platform_name': 'LaborLooker'
        }
        
        # Add action-specific data
        if action == 'job_acceptance' and context:
            base_data.update({
                'project_title': context.get('job_title', ''),
                'project_value': context.get('quote_amount', ''),
                'customer_name': context.get('customer_name', ''),
                'start_date': context.get('start_date', ''),
                'completion_date': context.get('completion_date', '')
            })
        
        elif action == 'payment_processing' and context:
            base_data.update({
                'payment_amount': context.get('amount', ''),
                'payment_method': context.get('method', ''),
                'transaction_id': context.get('transaction_id', '')
            })
        
        elif action == 'job_posting' and context:
            base_data.update({
                'job_title': context.get('title', ''),
                'job_budget': context.get('budget', ''),
                'property_address': context.get('address', ''),
                'job_description': context.get('description', '')
            })
        
        # Add user-specific data
        if user.contractor_profile:
            base_data.update({
                'business_name': user.contractor_profile.business_name or '',
                'license_number': user.contractor_profile.license_number or '',
                'insurance_company': user.contractor_profile.insurance_company or ''
            })
        
        return base_data
    
    def get_action_description(self, action):
        """Get user-friendly description of action"""
        descriptions = {
            'account_creation': 'Creating your LaborLooker account',
            'contractor_registration': 'Registering as a contractor',
            'quote_scheduling': 'Scheduling a quote appointment',
            'job_acceptance': 'Accepting a job project',
            'payment_processing': 'Processing payment transactions',
            'customer_registration': 'Registering as a customer',
            'job_posting': 'Posting a job opening',
            'contractor_hiring': 'Hiring a contractor',
            'pii_collection': 'Collecting personal information',
            'data_sharing': 'Sharing data with partners',
            'payment_user_to_user': 'Processing user-to-user payments',
            'company_application': 'Applying to join as a business',
            'business_profile_creation': 'Creating business profile',
            'review_submission': 'Submitting reviews and ratings',
            'messaging_system': 'Using platform messaging',
            'photo_upload': 'Uploading photos and media'
        }
        return descriptions.get(action, action.replace('_', ' ').title())

# Global document manager instance
comprehensive_doc_manager = ComprehensiveDocumentManager()

def require_documents_for_action(action, context_extractor=None):
    """Decorator to enforce document requirements for specific actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user:
                return redirect(url_for('login'))
            
            # Extract context if function provided
            context = {}
            if context_extractor:
                context = context_extractor(request, *args, **kwargs)
            
            # Check document requirements for this action
            docs_complete, missing_docs = comprehensive_doc_manager.check_action_requirements(
                user, action, context
            )
            
            if not docs_complete:
                action_desc = comprehensive_doc_manager.get_action_description(action)
                flash(f'Required documents for "{action_desc}" have been sent to your email. Please sign them to continue.', 'warning')
                return redirect(url_for('comprehensive_documents_required', action=action))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Context extractors for specific actions
def job_acceptance_context(request, *args, **kwargs):
    """Extract context for job acceptance"""
    return {
        'job_id': kwargs.get('job_id') or request.form.get('job_id'),
        'quote_amount': request.form.get('quote_amount'),
        'start_date': request.form.get('start_date'),
        'completion_date': request.form.get('completion_date')
    }

def payment_context(request, *args, **kwargs):
    """Extract context for payment processing"""
    return {
        'amount': request.form.get('amount'),
        'method': request.form.get('payment_method'),
        'recipient': request.form.get('recipient_id')
    }

def job_posting_context(request, *args, **kwargs):
    """Extract context for job posting"""
    return {
        'title': request.form.get('title'),
        'budget': request.form.get('budget'),
        'address': request.form.get('address'),
        'description': request.form.get('description')
    }