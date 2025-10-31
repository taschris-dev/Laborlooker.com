"""
Complete DocuSign Integration for LaborLooker Platform
Functional document management with automatic enforcement
"""

import os
import jwt
import requests
import hashlib
import hmac
from datetime import datetime, timedelta
from flask import current_app, request, jsonify, redirect, url_for, flash
from main import db, User, ContractDocument
import logging

class DocuSignManager:
    """Complete DocuSign integration with automatic document enforcement"""
    
    def __init__(self):
        # DocuSign configuration from .env
        self.integration_key = os.environ.get('DOCUSIGN_INTEGRATION_KEY')
        self.user_id = os.environ.get('DOCUSIGN_USER_ID')
        self.account_id = os.environ.get('DOCUSIGN_ACCOUNT_ID')
        self.base_path = os.environ.get('DOCUSIGN_BASE_PATH', 'https://demo.docusign.net/restapi')
        self.oauth_base_path = os.environ.get('DOCUSIGN_OAUTH_BASE_PATH', 'https://account-d.docusign.com')
        self.redirect_uri = os.environ.get('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/docusign/callback')
        
        # Load private key
        self.private_key = self._load_private_key()
        
        # Document templates (will be created automatically)
        self.templates = {
            'contractor_agreement': 'CONTRACTOR_TEMPLATE_ID',
            'liability_waiver': 'LIABILITY_TEMPLATE_ID', 
            'employment_agreement': 'EMPLOYMENT_TEMPLATE_ID',
            'project_contract': 'PROJECT_TEMPLATE_ID',
            'client_terms': 'CLIENT_TERMS_TEMPLATE_ID'
        }
        
        # Document storage
        self.document_storage_path = os.path.join(os.getcwd(), 'documents', 'signed_contracts')
        os.makedirs(self.document_storage_path, exist_ok=True)
        
        self.access_token = None
        self.token_expires_at = None
        
        # Set up logging
        self.logger = logging.getLogger('docusign_manager')
    
    def _load_private_key(self):
        """Load DocuSign private key"""
        key_path = os.environ.get('DOCUSIGN_PRIVATE_KEY_PATH', './docusign_private_key.txt')
        
        try:
            with open(key_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"DocuSign private key not found at {key_path}")
            return None
    
    def get_access_token(self):
        """Get JWT access token for DocuSign API"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
        
        if not self.private_key:
            raise Exception("DocuSign private key not configured")
        
        # Create JWT assertion
        now = datetime.utcnow()
        payload = {
            "iss": self.integration_key,
            "sub": self.user_id,
            "aud": "account-d.docusign.com",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "scope": "signature impersonation"
        }
        
        # Sign JWT
        assertion = jwt.encode(payload, self.private_key, algorithm='RS256')
        
        # Request access token
        token_url = f"{self.oauth_base_path}/oauth/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            return self.access_token
        else:
            raise Exception(f"Failed to get DocuSign access token: {response.text}")
    
    def require_contractor_documents(self, user):
        """Enforce required documents for contractors"""
        if not user.contractor_profile:
            return False, "No contractor profile found"
        
        # Check required documents
        required_docs = self._get_required_contractor_documents(user)
        missing_docs = []
        
        for doc_type, template_id in required_docs.items():
            contract = ContractDocument.query.filter_by(
                user_id=user.id,
                document_type=doc_type,
                status='completed'
            ).first()
            
            if not contract:
                missing_docs.append(doc_type)
        
        if missing_docs:
            # Automatically send missing documents
            for doc_type in missing_docs:
                self._send_required_document(user, doc_type)
            
            return False, f"Missing required documents: {', '.join(missing_docs)}"
        
        return True, "All required documents completed"
    
    def _get_required_contractor_documents(self, user):
        """Get list of required documents for contractor"""
        required = {
            'contractor_agreement': self.templates['contractor_agreement'],
            'liability_waiver': self.templates['liability_waiver']
        }
        
        # Add employment agreement for contractors with employees
        if user.contractor_profile.has_employees:
            required['employment_agreement'] = self.templates['employment_agreement']
        
        return required
    
    def _send_required_document(self, user, document_type):
        """Send required document for signing"""
        try:
            template_id = self.templates[document_type]
            
            # Prepare document data
            template_data = self._prepare_document_data(user, document_type)
            
            # Create envelope
            envelope_data = self._create_envelope_from_template(
                template_id=template_id,
                signer_email=user.email,
                signer_name=user.name,
                template_data=template_data,
                document_type=document_type
            )
            
            if envelope_data:
                # Save contract record
                contract = ContractDocument(
                    user_id=user.id,
                    envelope_id=envelope_data['envelopeId'],
                    document_type=document_type,
                    template_id=template_id,
                    status='sent',
                    document_name=self._get_document_name(document_type),
                    sent_at=datetime.utcnow(),
                    required=True
                )
                
                db.session.add(contract)
                db.session.commit()
                
                self.logger.info(f"Sent required document {document_type} to {user.email}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to send document {document_type}: {str(e)}")
            return False
    
    def _prepare_document_data(self, user, document_type):
        """Prepare template data for document"""
        base_data = {
            'user_name': user.name,
            'user_email': user.email,
            'date': datetime.now().strftime('%B %d, %Y'),
            'platform_name': 'LaborLooker',
            'platform_fee': '10%',
            'payment_processing_fee': '2.9% + $0.30'
        }
        
        if user.contractor_profile:
            contractor_data = {
                'business_name': user.contractor_profile.business_name or '',
                'contact_name': user.contractor_profile.contact_name or user.name,
                'phone': user.contractor_profile.phone or '',
                'location': user.contractor_profile.location or '',
                'license_number': user.contractor_profile.license_number or '',
                'insurance_company': user.contractor_profile.insurance_company or '',
                'insurance_policy': user.contractor_profile.insurance_policy_number or ''
            }
            base_data.update(contractor_data)
        
        return base_data
    
    def _create_envelope_from_template(self, template_id, signer_email, signer_name, template_data, document_type):
        """Create DocuSign envelope from template"""
        access_token = self.get_access_token()
        
        url = f"{self.base_path}/v2.1/accounts/{self.account_id}/envelopes"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Create text tabs from template data
        text_tabs = []
        for key, value in template_data.items():
            text_tabs.append({
                "tabLabel": key,
                "value": str(value)
            })
        
        envelope_data = {
            "status": "sent",
            "templateId": template_id,
            "templateRoles": [{
                "email": signer_email,
                "name": signer_name,
                "roleName": "Signer",
                "tabs": {
                    "textTabs": text_tabs
                }
            }],
            "emailSubject": f"Required Document: {self._get_document_name(document_type)}",
            "emailBlurb": f"Please sign your required {document_type.replace('_', ' ').title()} for LaborLooker platform access."
        }
        
        response = requests.post(url, headers=headers, json=envelope_data)
        
        if response.status_code == 201:
            return response.json()
        else:
            self.logger.error(f"Failed to create envelope: {response.text}")
            return None
    
    def _get_document_name(self, document_type):
        """Get friendly document name"""
        names = {
            'contractor_agreement': 'Contractor Service Agreement',
            'liability_waiver': 'Liability Waiver and Release',
            'employment_agreement': 'Employment Agreement',
            'project_contract': 'Project Contract',
            'client_terms': 'Client Terms of Service'
        }
        return names.get(document_type, document_type.replace('_', ' ').title())
    
    def handle_webhook(self, webhook_data):
        """Handle DocuSign webhook notifications"""
        try:
            for envelope_data in webhook_data.get('data', []):
                envelope_id = envelope_data.get('envelopeId')
                status = envelope_data.get('status')
                
                if not envelope_id:
                    continue
                
                # Find contract
                contract = ContractDocument.query.filter_by(envelope_id=envelope_id).first()
                if not contract:
                    self.logger.warning(f"Contract not found for envelope: {envelope_id}")
                    continue
                
                # Update status
                old_status = contract.status
                contract.status = status
                contract.updated_at = datetime.utcnow()
                
                # Handle completed documents
                if status == 'completed':
                    self._handle_document_completion(contract)
                elif status == 'declined':
                    self._handle_document_decline(contract)
                elif status == 'voided':
                    self._handle_document_void(contract)
                
                db.session.commit()
                self.logger.info(f"Contract {contract.id} status: {old_status} → {status}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Webhook handling failed: {str(e)}")
            return False
    
    def _handle_document_completion(self, contract):
        """Handle completed document"""
        user = User.query.get(contract.user_id)
        if not user:
            return
        
        # Mark completion time
        contract.completed_at = datetime.utcnow()
        
        # Download and store signed document
        signed_doc = self._download_signed_document(contract.envelope_id)
        if signed_doc:
            storage_path = self._store_signed_document(contract, signed_doc)
            contract.document_url = storage_path
            contract.document_stored = True
        
        # Update user permissions based on document type
        if contract.document_type == 'contractor_agreement':
            if user.contractor_profile:
                user.contractor_profile.agreement_signed = True
                user.contractor_profile.agreement_signed_at = datetime.utcnow()
                
        elif contract.document_type == 'liability_waiver':
            if user.contractor_profile:
                user.contractor_profile.liability_waiver_signed = True
                user.contractor_profile.liability_waiver_signed_at = datetime.utcnow()
        
        # Check if all required documents are complete
        all_complete, message = self.require_contractor_documents(user)
        if all_complete and user.contractor_profile:
            user.contractor_profile.documents_complete = True
            user.contractor_profile.status = 'active'
            
            self.logger.info(f"All required documents completed for {user.email}")
    
    def _handle_document_decline(self, contract):
        """Handle declined document"""
        user = User.query.get(contract.user_id)
        if not user:
            return
        
        contract.declined_at = datetime.utcnow()
        
        # Suspend contractor until documents are signed
        if user.contractor_profile:
            user.contractor_profile.status = 'suspended'
            user.contractor_profile.suspension_reason = f'Declined required document: {contract.document_type}'
        
        self.logger.warning(f"User {user.email} declined document: {contract.document_type}")
    
    def _handle_document_void(self, contract):
        """Handle voided document"""
        contract.voided_at = datetime.utcnow()
        
        # Reset any status changes
        user = User.query.get(contract.user_id)
        if user and user.contractor_profile:
            if contract.document_type == 'contractor_agreement':
                user.contractor_profile.agreement_signed = False
            elif contract.document_type == 'liability_waiver':
                user.contractor_profile.liability_waiver_signed = False
    
    def _download_signed_document(self, envelope_id):
        """Download signed document from DocuSign"""
        try:
            access_token = self.get_access_token()
            
            url = f"{self.base_path}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                self.logger.error(f"Failed to download document: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Document download failed: {str(e)}")
            return None
    
    def _store_signed_document(self, contract, document_bytes):
        """Store signed document securely"""
        filename = f"contract_{contract.user_id}_{contract.document_type}_{contract.envelope_id}.pdf"
        storage_path = os.path.join(self.document_storage_path, filename)
        
        try:
            with open(storage_path, 'wb') as f:
                f.write(document_bytes)
            
            self.logger.info(f"Stored signed document: {storage_path}")
            return storage_path
            
        except Exception as e:
            self.logger.error(f"Failed to store document: {str(e)}")
            return None
    
    def send_project_contract(self, contractor, invitation):
        """Send project contract for specific job invitation"""
        try:
            from main import JobPost, ContractDocument
            
            job = JobPost.query.get(invitation.job_id) if hasattr(invitation, 'job_id') else None
            
            # Prepare project contract data
            template_data = {
                'contractor_name': contractor.contractor_profile.contact_name or contractor.name,
                'customer_name': job.customer.name if job else 'Customer',
                'project_title': job.title if job else 'Project Work',
                'project_description': job.description[:500] if job else 'As specified in job posting',
                'project_budget': f"${invitation.quote_amount}" if hasattr(invitation, 'quote_amount') and invitation.quote_amount else 'TBD',
                'start_date': invitation.proposed_start_date.strftime('%B %d, %Y') if hasattr(invitation, 'proposed_start_date') and invitation.proposed_start_date else 'TBD',
                'completion_date': invitation.estimated_completion.strftime('%B %d, %Y') if hasattr(invitation, 'estimated_completion') and invitation.estimated_completion else 'TBD',
                'payment_terms': 'Net 30 days via LaborLooker platform',
                'platform_fee': '10%',
                'date': datetime.now().strftime('%B %d, %Y'),
                'project_id': str(invitation.id)
            }
            
            # Create envelope
            envelope_data = self._create_envelope_from_template(
                template_id=self.templates['project_contract'],
                signer_email=contractor.email,
                signer_name=contractor.contractor_profile.contact_name or contractor.name,
                template_data=template_data,
                document_type='project_contract'
            )
            
            if envelope_data:
                # Save contract record
                contract = ContractDocument(
                    user_id=contractor.id,
                    envelope_id=envelope_data['envelopeId'],
                    document_type='project_contract',
                    template_id=self.templates['project_contract'],
                    status='sent',
                    document_name=f'Project Contract - {job.title if job else "Project"}',
                    sent_at=datetime.utcnow(),
                    required=True,
                    project_id=invitation.id
                )
                
                db.session.add(contract)
                
                # Update invitation with envelope ID
                if hasattr(invitation, 'docusign_envelope_id'):
                    invitation.docusign_envelope_id = envelope_data['envelopeId']
                
                db.session.commit()
                
                self.logger.info(f"Sent project contract to {contractor.email} for invitation {invitation.id}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to send project contract: {str(e)}")
            return False

    def check_document_requirements(self, user, action=None):
        """Check if user has all required documents for specific action"""
        
        # Different actions require different documents
        requirements = {
            'contractor_registration': ['contractor_agreement', 'liability_waiver'],
            'project_acceptance': ['contractor_agreement', 'liability_waiver'],
            'payment_processing': ['contractor_agreement', 'liability_waiver'],
            'profile_activation': ['contractor_agreement', 'liability_waiver']
        }
        
        required_docs = requirements.get(action, ['contractor_agreement'])
        
        missing_docs = []
        for doc_type in required_docs:
            contract = ContractDocument.query.filter_by(
                user_id=user.id,
                document_type=doc_type,
                status='completed'
            ).first()
            
            if not contract:
                missing_docs.append(doc_type)
        
        return len(missing_docs) == 0, missing_docs

# Global DocuSign manager instance
docusign_manager = DocuSignManager()