"""
DocuSign Integration for LaborLooker
Handles mandatory contract signing for contractors, clients, and project agreements
"""

import os
import json
import base64
from datetime import datetime, timedelta
import requests
from flask import current_app, url_for
from werkzeug.security import generate_password_hash

class DocuSignClient:
    """DocuSign API client for contract management"""
    
    def __init__(self):
        self.base_url = os.environ.get('DOCUSIGN_BASE_URL', 'https://demo.docusign.net/restapi')
        self.account_id = os.environ.get('DOCUSIGN_ACCOUNT_ID')
        self.client_id = os.environ.get('DOCUSIGN_CLIENT_ID')
        self.client_secret = os.environ.get('DOCUSIGN_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('DOCUSIGN_REDIRECT_URI', 'http://localhost:5000/docusign/callback')
        self.private_key = os.environ.get('DOCUSIGN_PRIVATE_KEY')
        self.user_id = os.environ.get('DOCUSIGN_USER_ID')
        
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self):
        """Get OAuth access token using JWT Bearer"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token
        
        # JWT Bearer token authentication
        import jwt
        
        # Create JWT assertion
        now = datetime.utcnow()
        payload = {
            "iss": self.client_id,
            "sub": self.user_id,
            "aud": "account-d.docusign.com",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "scope": "signature impersonation"
        }
        
        # Sign JWT with private key
        assertion = jwt.encode(payload, self.private_key, algorithm='RS256')
        
        # Request access token
        token_url = "https://account-d.docusign.com/oauth/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")
    
    def create_envelope_from_template(self, template_id, signer_email, signer_name, template_data=None):
        """Create envelope from DocuSign template"""
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare envelope data
        envelope_data = {
            "status": "sent",
            "templateId": template_id,
            "templateRoles": [
                {
                    "email": signer_email,
                    "name": signer_name,
                    "roleName": "Signer",
                    "tabs": {
                        "textTabs": []
                    }
                }
            ],
            "emailSubject": "Please sign your LaborLooker agreement"
        }
        
        # Add template data if provided
        if template_data:
            text_tabs = []
            for key, value in template_data.items():
                text_tabs.append({
                    "tabLabel": key,
                    "value": str(value)
                })
            envelope_data["templateRoles"][0]["tabs"]["textTabs"] = text_tabs
        
        response = requests.post(url, headers=headers, json=envelope_data)
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create envelope: {response.text}")
    
    def get_envelope_status(self, envelope_id):
        """Get envelope status"""
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get envelope status: {response.text}")
    
    def get_envelope_documents(self, envelope_id):
        """Get signed documents from envelope"""
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined"
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.content  # PDF bytes
        else:
            raise Exception(f"Failed to get envelope documents: {response.text}")
    
    def get_templates(self):
        """Get available DocuSign templates"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_path}/v2.1/accounts/{self.account_id}/templates",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get('envelopeTemplates', [])
            else:
                return []
                
        except Exception as e:
            return []
    
    def get_envelope_documents(self, envelope_id):
        """Get envelope documents list"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_path}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get('envelopeDocuments', [])
            else:
                return []
                
        except Exception as e:
            return []
    
    def download_envelope_documents(self, envelope_id):
        """Download all envelope documents as PDF"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Download combined document
            response = requests.get(
                f"{self.base_path}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.content, None
            else:
                return None, f"Failed to download documents: {response.text}"
                
        except Exception as e:
            return None, str(e)
    
    def void_envelope(self, envelope_id, reason):
        """Void an envelope"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "status": "voided",
                "voidedReason": reason
            }
            
            response = requests.put(
                f"{self.base_path}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Failed to void envelope: {response.text}"
                
        except Exception as e:
            return False, str(e)

class ContractManager:
    """Manages contract creation and signing workflows"""
    
    def __init__(self):
        self.docusign_client = DocuSignClient()
        
        # Update references to use docusign_client instead of docusign
        # These methods were originally using self.docusign
        
        # Template IDs for different contract types
        self.templates = {
            'contractor_agreement': os.environ.get('DOCUSIGN_CONTRACTOR_TEMPLATE_ID'),
            'client_terms': os.environ.get('DOCUSIGN_CLIENT_TEMPLATE_ID'),
            'project_contract': os.environ.get('DOCUSIGN_PROJECT_TEMPLATE_ID'),
            'nda_agreement': os.environ.get('DOCUSIGN_NDA_TEMPLATE_ID')
        }
    
    def send_contractor_agreement(self, user):
        """Send contractor agreement for signing"""
        from main import db, ContractDocument
        
        # Prepare contractor data for template
        contractor_profile = user.contractor_profile
        template_data = {
            'contractor_name': contractor_profile.contact_name,
            'business_name': contractor_profile.business_name,
            'phone': contractor_profile.phone or '',
            'address': contractor_profile.location or '',
            'date': datetime.now().strftime('%B %d, %Y'),
            'commission_rate': '10%',
            'platform_fee': '2.5%'
        }
        
        try:
            # Create envelope
            envelope = self.docusign.create_envelope_from_template(
                template_id=self.templates['contractor_agreement'],
                signer_email=user.email,
                signer_name=contractor_profile.contact_name,
                template_data=template_data
            )
            
            # Save contract record
            contract = ContractDocument(
                user_id=user.id,
                envelope_id=envelope['envelopeId'],
                document_type='contractor_agreement',
                template_id=self.templates['contractor_agreement'],
                status='sent',
                document_name='LaborLooker Contractor Agreement',
                sent_at=datetime.utcnow()
            )
            
            db.session.add(contract)
            db.session.commit()
            
            return contract, None
            
        except Exception as e:
            return None, str(e)
    
    def send_client_terms(self, user):
        """Send client terms of service for signing"""
        from main import db, ContractDocument
        
        # Prepare client data for template
        customer_profile = user.customer_profile
        template_data = {
            'client_name': f"{customer_profile.first_name} {customer_profile.last_name}",
            'email': user.email,
            'phone': customer_profile.phone or '',
            'address': customer_profile.location or '',
            'date': datetime.now().strftime('%B %d, %Y'),
            'platform_fee': '3%',
            'dispute_resolution': 'Binding Arbitration'
        }
        
        try:
            envelope = self.docusign.create_envelope_from_template(
                template_id=self.templates['client_terms'],
                signer_email=user.email,
                signer_name=f"{customer_profile.first_name} {customer_profile.last_name}",
                template_data=template_data
            )
            
            contract = ContractDocument(
                user_id=user.id,
                envelope_id=envelope['envelopeId'],
                document_type='client_terms',
                template_id=self.templates['client_terms'],
                status='sent',
                document_name='LaborLooker Client Terms of Service',
                sent_at=datetime.utcnow()
            )
            
            db.session.add(contract)
            db.session.commit()
            
            return contract, None
            
        except Exception as e:
            return None, str(e)
    
    def send_project_contract(self, work_request, contractor_user, customer_user):
        """Send project-specific contract"""
        from main import db, ContractDocument
        
        contractor_profile = contractor_user.contractor_profile
        customer_profile = customer_user.customer_profile
        
        # Prepare project contract data
        template_data = {
            'project_title': work_request.title,
            'project_description': work_request.description,
            'contractor_name': contractor_profile.contact_name,
            'contractor_business': contractor_profile.business_name,
            'client_name': f"{customer_profile.first_name} {customer_profile.last_name}",
            'project_location': work_request.location,
            'estimated_cost': f"${work_request.budget:.2f}" if work_request.budget else "TBD",
            'project_timeline': work_request.timeline or "To be determined",
            'date': datetime.now().strftime('%B %d, %Y'),
            'contract_id': f"LC-{work_request.id}-{datetime.now().strftime('%Y%m%d')}"
        }
        
        try:
            # Send to contractor first
            envelope = self.docusign.create_envelope_from_template(
                template_id=self.templates['project_contract'],
                signer_email=contractor_user.email,
                signer_name=contractor_profile.contact_name,
                template_data=template_data
            )
            
            # Create contract records for both parties
            contractor_contract = ContractDocument(
                user_id=contractor_user.id,
                envelope_id=envelope['envelopeId'],
                document_type='project_contract',
                template_id=self.templates['project_contract'],
                status='sent',
                document_name=f'Project Contract - {work_request.title}',
                work_request_id=work_request.id,
                contract_value=work_request.budget,
                sent_at=datetime.utcnow()
            )
            
            customer_contract = ContractDocument(
                user_id=customer_user.id,
                envelope_id=envelope['envelopeId'],
                document_type='project_contract',
                template_id=self.templates['project_contract'],
                status='sent',
                document_name=f'Project Contract - {work_request.title}',
                work_request_id=work_request.id,
                contract_value=work_request.budget,
                sent_at=datetime.utcnow()
            )
            
            db.session.add(contractor_contract)
            db.session.add(customer_contract)
            db.session.commit()
            
            return (contractor_contract, customer_contract), None
            
        except Exception as e:
            return None, str(e)
    
    def check_contract_status(self, contract_id):
        """Check and update contract status"""
        from main import db, ContractDocument
        
        contract = ContractDocument.query.get(contract_id)
        if not contract:
            return None, "Contract not found"
        
        try:
            # Get current status from DocuSign
            envelope_status = self.docusign.get_envelope_status(contract.envelope_id)
            
            # Update contract status
            old_status = contract.status
            contract.status = envelope_status['status'].lower()
            
            # Update timestamps based on status
            if contract.status == 'delivered' and old_status != 'delivered':
                contract.delivered_at = datetime.utcnow()
            elif contract.status == 'signed' and old_status != 'signed':
                contract.signed_at = datetime.utcnow()
            elif contract.status == 'completed' and old_status != 'completed':
                contract.completed_at = datetime.utcnow()
                
                # Download completed document
                try:
                    pdf_content = self.docusign.get_envelope_documents(contract.envelope_id)
                    
                    # Save to storage
                    import os
                    contracts_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'contracts')
                    os.makedirs(contracts_dir, exist_ok=True)
                    
                    filename = f"{contract.envelope_id}_completed.pdf"
                    file_path = os.path.join(contracts_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    contract.completed_document_url = file_path
                    
                except Exception as e:
                    current_app.logger.error(f"Failed to save completed contract: {e}")
            
            db.session.commit()
            
            return contract, None
            
        except Exception as e:
            return None, str(e)
    
    def is_user_contract_compliant(self, user):
        """Check if user has all required contracts signed"""
        from main import ContractDocument
        
        required_contracts = []
        
        if user.account_type == 'contractor':
            required_contracts = ['contractor_agreement']
        elif user.account_type == 'customer':
            required_contracts = ['client_terms']
        elif user.account_type == 'developer':
            required_contracts = ['nda_agreement']
        
        for contract_type in required_contracts:
            contract = ContractDocument.query.filter_by(
                user_id=user.id,
                document_type=contract_type,
                status='completed'
            ).first()
            
            if not contract:
                return False, f"Missing {contract_type.replace('_', ' ').title()}"
        
        return True, "All contracts signed"
    
    def get_user_contracts(self, user_id):
        """Get all contracts for a user"""
        from main import ContractDocument
        
        contracts = ContractDocument.query.filter_by(user_id=user_id)\
                                         .order_by(ContractDocument.sent_at.desc())\
                                         .all()
        
        return contracts

def require_signed_contract(contract_types):
    """Decorator to require signed contracts for certain actions"""
    from functools import wraps
    from flask import redirect, url_for, flash
    from flask_login import current_user
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            contract_manager = ContractManager()
            
            for contract_type in contract_types:
                from main import ContractDocument
                contract = ContractDocument.query.filter_by(
                    user_id=current_user.id,
                    document_type=contract_type,
                    status='completed'
                ).first()
                
                if not contract:
                    flash(f'You must sign the {contract_type.replace("_", " ").title()} before accessing this feature.', 'warning')
                    return redirect(url_for('contracts_dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_mandatory_contracts_for_user(user):
    """Create mandatory contracts when user completes profile"""
    contract_manager = ContractManager()
    
    try:
        if user.account_type == 'contractor':
            contract, error = contract_manager.send_contractor_agreement(user)
            if error:
                current_app.logger.error(f"Failed to send contractor agreement: {error}")
                return False, error
        
        elif user.account_type == 'customer':
            contract, error = contract_manager.send_client_terms(user)
            if error:
                current_app.logger.error(f"Failed to send client terms: {error}")
                return False, error
        
        return True, "Contract sent successfully"
        
    except Exception as e:
        current_app.logger.error(f"Error creating mandatory contracts: {e}")
        return False, str(e)

    def create_contractor_agreement(self, sender_user, recipient_email, recipient_name, project_details=""):
        """Create contractor agreement contract"""
        try:
            # Use contractor agreement template
            template_data = {
                'contractor_name': recipient_name,
                'contractor_email': recipient_email,
                'platform_name': 'LaborLooker',
                'agreement_date': datetime.now().strftime('%B %d, %Y'),
                'project_details': project_details or 'General contractor services'
            }
            
            envelope_id, error = self.docusign_client.send_envelope_from_template(
                'contractor_agreement_template',
                recipient_email,
                recipient_name,
                template_data
            )
            
            if envelope_id:
                # Store contract record
                self._store_contract_record(
                    envelope_id, sender_user.id, recipient_email, 'contractor_agreement', template_data
                )
                
            return envelope_id, error
            
        except Exception as e:
            return None, str(e)
    
    def create_client_agreement(self, sender_user, recipient_email, recipient_name, project_details=""):
        """Create client agreement contract"""
        try:
            template_data = {
                'client_name': recipient_name,
                'client_email': recipient_email,
                'platform_name': 'LaborLooker',
                'agreement_date': datetime.now().strftime('%B %d, %Y'),
                'service_description': project_details or 'Platform services'
            }
            
            envelope_id, error = self.docusign_client.send_envelope_from_template(
                'client_agreement_template',
                recipient_email,
                recipient_name,
                template_data
            )
            
            if envelope_id:
                self._store_contract_record(
                    envelope_id, sender_user.id, recipient_email, 'client_agreement', template_data
                )
                
            return envelope_id, error
            
        except Exception as e:
            return None, str(e)
    
    def create_project_contract(self, sender_user, recipient_email, recipient_name, work_request_id, project_details):
        """Create project-specific contract"""
        try:
            # Get work request details
            from main import WorkRequest
            work_request = WorkRequest.query.get(work_request_id) if work_request_id else None
            
            template_data = {
                'contractor_name': recipient_name if sender_user.account_type == 'customer' else sender_user.email,
                'client_name': recipient_name if sender_user.account_type == 'contractor' else sender_user.email,
                'project_description': project_details,
                'work_request_id': work_request_id,
                'contract_date': datetime.now().strftime('%B %d, %Y'),
                'service_location': work_request.geographic_area if work_request else 'TBD'
            }
            
            envelope_id, error = self.docusign_client.send_envelope_from_template(
                'project_contract_template',
                recipient_email,
                recipient_name,
                template_data
            )
            
            if envelope_id:
                self._store_contract_record(
                    envelope_id, sender_user.id, recipient_email, 'project_contract', template_data
                )
                
            return envelope_id, error
            
        except Exception as e:
            return None, str(e)
    
    def get_contract_status(self, envelope_id):
        """Get contract status and details"""
        try:
            status, error = self.docusign_client.get_envelope_status(envelope_id)
            if error:
                return None
                
            # Get contract record from database
            contract_record = self._get_contract_record(envelope_id)
            
            return {
                'envelope_id': envelope_id,
                'status': status,
                'contract_record': contract_record,
                'details': self.docusign_client.get_envelope_documents(envelope_id)
            }
            
        except Exception as e:
            return None
    
    def download_completed_contract(self, envelope_id):
        """Download completed contract as PDF"""
        try:
            document_bytes, error = self.docusign_client.download_envelope_documents(envelope_id)
            if error:
                return None, None
                
            filename = f"contract_{envelope_id}.pdf"
            return document_bytes, filename
            
        except Exception as e:
            return None, None
    
    def void_contract(self, envelope_id, reason):
        """Void a contract"""
        try:
            success, error = self.docusign_client.void_envelope(envelope_id, reason)
            
            if success:
                # Update contract record
                self._update_contract_status(envelope_id, 'voided', reason)
                
            return success, error
            
        except Exception as e:
            return False, str(e)
    
    def get_user_contracts(self, user_id):
        """Get all contracts for a user"""
        try:
            from main import ContractDocument
            contracts = ContractDocument.query.filter_by(user_id=user_id).all()
            
            contract_list = []
            for contract in contracts:
                # Get current status from DocuSign
                status, _ = self.docusign_client.get_envelope_status(contract.envelope_id)
                
                contract_list.append({
                    'id': contract.id,
                    'envelope_id': contract.envelope_id,
                    'contract_type': contract.contract_type,
                    'recipient_email': contract.recipient_email,
                    'status': status or contract.status,
                    'created_at': contract.created_at,
                    'template_data': json.loads(contract.template_data) if contract.template_data else {}
                })
                
            return contract_list
            
        except Exception as e:
            return []
    
    def process_webhook_event(self, webhook_data):
        """Process DocuSign webhook events"""
        try:
            envelope_id = webhook_data.get('envelopeId')
            event_type = webhook_data.get('event')
            
            if envelope_id and event_type:
                # Update contract status based on event
                if event_type == 'envelope-completed':
                    self._update_contract_status(envelope_id, 'completed')
                elif event_type == 'envelope-voided':
                    self._update_contract_status(envelope_id, 'voided')
                elif event_type == 'envelope-declined':
                    self._update_contract_status(envelope_id, 'declined')
                    
            return True
            
        except Exception as e:
            current_app.logger.error(f"Webhook processing error: {e}")
            return False
    
    def _store_contract_record(self, envelope_id, user_id, recipient_email, contract_type, template_data):
        """Store contract record in database"""
        try:
            from main import db, ContractDocument
            
            contract = ContractDocument(
                envelope_id=envelope_id,
                user_id=user_id,
                recipient_email=recipient_email,
                contract_type=contract_type,
                template_data=json.dumps(template_data),
                status='sent'
            )
            
            db.session.add(contract)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Failed to store contract record: {e}")
    
    def _get_contract_record(self, envelope_id):
        """Get contract record from database"""
        try:
            from main import ContractDocument
            return ContractDocument.query.filter_by(envelope_id=envelope_id).first()
            
        except Exception as e:
            return None
    
    def _update_contract_status(self, envelope_id, status, notes=""):
        """Update contract status in database"""
        try:
            from main import db, ContractDocument
            
            contract = ContractDocument.query.filter_by(envelope_id=envelope_id).first()
            if contract:
                contract.status = status
                if notes:
                    contract.notes = notes
                db.session.commit()
                
        except Exception as e:
            current_app.logger.error(f"Failed to update contract status: {e}")