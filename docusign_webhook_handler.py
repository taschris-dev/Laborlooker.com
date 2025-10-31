"""
DocuSign Webhook Handler for LaborLooker Platform
Handles envelope status updates and contract completions
"""

import os
import hashlib
import hmac
from flask import request, jsonify
from main import app, db, ContractDocument, User
from datetime import datetime

# DocuSign webhook secret (set in environment)
DOCUSIGN_WEBHOOK_SECRET = os.environ.get('DOCUSIGN_WEBHOOK_SECRET', '')

@app.route('/docusign/webhook', methods=['POST'])
def docusign_webhook():
    """Handle DocuSign webhook notifications"""
    
    # Verify webhook signature
    if not verify_webhook_signature(request):
        return jsonify({'error': 'Invalid signature'}), 401
    
    try:
        # Parse webhook data
        webhook_data = request.get_json()
        
        # Process each envelope status change
        for envelope_data in webhook_data.get('data', []):
            process_envelope_update(envelope_data)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        app.logger.error(f"DocuSign webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

def verify_webhook_signature(request):
    """Verify DocuSign webhook signature"""
    if not DOCUSIGN_WEBHOOK_SECRET:
        # Skip verification in development
        return True
    
    # Get signature from headers
    signature = request.headers.get('X-DocuSign-Signature-1')
    if not signature:
        return False
    
    # Calculate expected signature
    body = request.get_data()
    expected = hmac.new(
        DOCUSIGN_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def process_envelope_update(envelope_data):
    """Process individual envelope status update"""
    
    envelope_id = envelope_data.get('envelopeId')
    status = envelope_data.get('status')
    
    if not envelope_id:
        return
    
    # Find contract document
    contract = ContractDocument.query.filter_by(envelope_id=envelope_id).first()
    if not contract:
        app.logger.warning(f"Contract not found for envelope: {envelope_id}")
        return
    
    # Update contract status
    old_status = contract.status
    contract.status = status
    contract.updated_at = datetime.utcnow()
    
    # Handle specific status changes
    if status == 'completed':
        contract.completed_at = datetime.utcnow()
        handle_contract_completion(contract)
        
    elif status == 'declined':
        contract.declined_at = datetime.utcnow()
        handle_contract_decline(contract)
        
    elif status == 'voided':
        contract.voided_at = datetime.utcnow()
        handle_contract_void(contract)
    
    # Save changes
    db.session.commit()
    
    app.logger.info(f"Contract {contract.id} status: {old_status} → {status}")

def handle_contract_completion(contract):
    """Handle completed contract"""
    
    user = User.query.get(contract.user_id)
    if not user:
        return
    
    # Update user based on contract type
    if contract.document_type == 'contractor_agreement':
        # Mark contractor as agreement signed
        if user.contractor_profile:
            user.contractor_profile.agreement_signed = True
            user.contractor_profile.agreement_signed_at = datetime.utcnow()
            
            # Send welcome email
            send_contractor_welcome_email(user)
            
    elif contract.document_type == 'client_terms':
        # Mark client terms accepted
        if user.customer_profile:
            user.customer_profile.terms_accepted = True
            user.customer_profile.terms_accepted_at = datetime.utcnow()
            
    elif contract.document_type == 'project_contract':
        # Enable project to proceed
        handle_project_contract_completion(contract)
    
    # Download and store signed document
    try:
        from docusign_integration import DocuSignClient
        docusign = DocuSignClient()
        
        signed_doc = docusign.get_envelope_documents(contract.envelope_id)
        if signed_doc:
            # Store document (implement your storage logic)
            store_signed_document(contract, signed_doc)
            
    except Exception as e:
        app.logger.error(f"Failed to download signed document: {str(e)}")

def handle_contract_decline(contract):
    """Handle declined contract"""
    
    user = User.query.get(contract.user_id)
    if not user:
        return
    
    # Send decline notification
    send_contract_decline_notification(user, contract)
    
    # Take appropriate action based on contract type
    if contract.document_type == 'contractor_agreement':
        # Suspend contractor account until resolved
        if user.contractor_profile:
            user.contractor_profile.status = 'suspended'
            
    elif contract.document_type == 'project_contract':
        # Notify project stakeholders
        handle_project_contract_decline(contract)

def handle_contract_void(contract):
    """Handle voided contract"""
    
    app.logger.info(f"Contract {contract.id} voided")
    
    # Reset any status changes that were made
    user = User.query.get(contract.user_id)
    if user and contract.document_type == 'contractor_agreement':
        if user.contractor_profile:
            user.contractor_profile.agreement_signed = False
            user.contractor_profile.agreement_signed_at = None

def handle_project_contract_completion(contract):
    """Handle project contract completion"""
    
    # Find related project/job invitation
    from main import JobInvitation
    
    invitation = JobInvitation.query.filter_by(
        docusign_envelope_id=contract.envelope_id
    ).first()
    
    if invitation:
        invitation.contract_signed = True
        invitation.contract_signed_at = datetime.utcnow()
        
        # Enable payment processing
        invitation.payment_enabled = True
        
        # Notify project stakeholders
        send_project_contract_signed_notification(invitation)

def handle_project_contract_decline(contract):
    """Handle project contract decline"""
    
    from main import JobInvitation
    
    invitation = JobInvitation.query.filter_by(
        docusign_envelope_id=contract.envelope_id
    ).first()
    
    if invitation:
        invitation.status = 'contract_declined'
        
        # Notify customer and platform
        send_project_contract_decline_notification(invitation)

def store_signed_document(contract, document_bytes):
    """Store signed document securely"""
    
    # Implement your document storage logic here
    # Options: AWS S3, Google Cloud Storage, local filesystem
    
    filename = f"contract_{contract.id}_{contract.envelope_id}.pdf"
    
    # Example: Save to local storage
    storage_path = os.path.join(app.config.get('DOCUMENT_STORAGE_PATH', 'documents'), filename)
    
    try:
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        with open(storage_path, 'wb') as f:
            f.write(document_bytes)
        
        # Update contract with document path
        contract.document_url = storage_path
        contract.document_stored = True
        
        app.logger.info(f"Stored signed document: {storage_path}")
        
    except Exception as e:
        app.logger.error(f"Failed to store document: {str(e)}")

def send_contractor_welcome_email(user):
    """Send welcome email to contractor after agreement signed"""
    
    # Implement email sending logic
    app.logger.info(f"Sending welcome email to contractor: {user.email}")

def send_contract_decline_notification(user, contract):
    """Send notification when contract is declined"""
    
    app.logger.info(f"Contract declined by {user.email}: {contract.document_type}")

def send_project_contract_signed_notification(invitation):
    """Send notification when project contract is signed"""
    
    app.logger.info(f"Project contract signed for invitation: {invitation.id}")

def send_project_contract_decline_notification(invitation):
    """Send notification when project contract is declined"""
    
    app.logger.info(f"Project contract declined for invitation: {invitation.id}")

# Webhook status mappings
ENVELOPE_STATUS_MAPPING = {
    'created': 'draft',
    'sent': 'sent', 
    'delivered': 'delivered',
    'completed': 'completed',
    'declined': 'declined',
    'voided': 'voided',
    'expired': 'expired'
}