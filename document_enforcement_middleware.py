"""
Comprehensive Document Enforcement Middleware
Automatically checks and enforces document requirements for all protected actions
"""

from flask import request, session, redirect, url_for, flash, render_template
from main import app
from comprehensive_documents import comprehensive_doc_manager

# Define routes that require specific document types
PROTECTED_ROUTES = {
    'register': 'account_creation',
    'contractor_profile': 'contractor_registration', 
    'post_job': 'job_posting',
    'schedule_quote': 'quote_scheduling',
    'accept_job': 'job_acceptance',
    'process_payment': 'payment_user_to_user',
    'upload_photo': 'photo_upload',
    'submit_review': 'review_submission',
    'company_application': 'company_application',
    'collect_pii': 'pii_collection',
    'data_sharing': 'data_sharing',
    'business_profile': 'business_profile_creation',
    'hire_contractor': 'contractor_hiring',
    'refund_processing': 'refund_processing'
}

# Routes that involve sensitive PII collection
PII_COLLECTION_ROUTES = [
    'register', 'contractor_profile', 'business_profile', 
    'upload_photo', 'personal_info', 'billing_info'
]

# Routes that involve financial transactions
FINANCIAL_ROUTES = [
    'process_payment', 'refund_processing', 'billing',
    'payout', 'escrow', 'payment_method'
]

@app.before_request
def enforce_comprehensive_documents():
    """Middleware to enforce document requirements before protected actions"""
    
    # Skip enforcement for static files, API docs, and auth pages
    if (request.endpoint in ['static', None] or 
        request.path.startswith('/static/') or
        request.path.startswith('/api/check_document') or
        request.path.startswith('/comprehensive_documents') or
        request.endpoint in ['login', 'logout', 'health_check']):
        return
    
    # Skip if user is not logged in (let normal auth handle this)
    if 'user_id' not in session:
        return
    
    # Get current user
    from main import User
    user = User.query.get(session['user_id'])
    if not user:
        return
    
    # Determine if this request needs document enforcement
    endpoint = request.endpoint
    action_needed = None
    
    # Check if this is a protected route
    if endpoint in PROTECTED_ROUTES:
        action_needed = PROTECTED_ROUTES[endpoint]
    
    # Check for PII collection routes
    elif endpoint in PII_COLLECTION_ROUTES:
        action_needed = 'pii_collection'
    
    # Check for financial routes
    elif endpoint in FINANCIAL_ROUTES:
        action_needed = 'payment_user_to_user'
    
    # Special handling for POST requests (form submissions)
    elif request.method == 'POST':
        # Any POST request that could modify data requires basic platform agreements
        action_needed = 'account_creation'
    
    # If no action needed, proceed normally
    if not action_needed:
        return
    
    # Check if user has required documents for this action
    docs_complete, missing_docs = comprehensive_doc_manager.check_action_requirements(
        user, action_needed, _extract_request_context()
    )
    
    if not docs_complete:
        # Store the original destination to redirect back after signing
        session['document_redirect_after'] = request.url
        
        action_desc = comprehensive_doc_manager.get_action_description(action_needed)
        flash(f'Please sign the required legal documents for "{action_desc}" before proceeding.', 'warning')
        
        return redirect(url_for('comprehensive_documents_required', action=action_needed))

def _extract_request_context():
    """Extract context information from the current request"""
    context = {}
    
    # Get form data
    if request.form:
        context.update({
            'amount': request.form.get('amount'),
            'job_title': request.form.get('title') or request.form.get('job_title'),
            'quote_amount': request.form.get('quote_amount'),
            'start_date': request.form.get('start_date'),
            'completion_date': request.form.get('completion_date'),
            'payment_method': request.form.get('payment_method'),
            'address': request.form.get('address'),
            'description': request.form.get('description'),
            'budget': request.form.get('budget')
        })
    
    # Get URL parameters
    if request.args:
        context.update({
            'job_id': request.args.get('job_id'),
            'work_request_id': request.args.get('work_request_id'),
            'user_id': request.args.get('user_id')
        })
    
    # Get view arguments (from URL path)
    if request.view_args:
        context.update(request.view_args)
    
    return context

# Override the documents required page to handle redirects back
def enhanced_documents_required():
    """Enhanced documents required page with redirect handling"""
    action = request.args.get('action', 'unknown_action')
    action_desc = comprehensive_doc_manager.get_action_description(action)
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from main import User, ContractDocument
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    # Check if documents are now complete
    docs_complete, missing_docs = comprehensive_doc_manager.check_action_requirements(user, action)
    
    if docs_complete and 'document_redirect_after' in session:
        # Documents are complete, redirect to original destination
        redirect_url = session.pop('document_redirect_after')
        flash('All required documents have been signed. You may now proceed.', 'success')
        return redirect(redirect_url)
    
    # Get pending documents for this action
    pending_docs = ContractDocument.query.filter_by(
        user_id=user.id,
        action_context=action,
        status='sent'
    ).all()
    
    return render_template('comprehensive_documents_required.html', 
                         action=action,
                         action_description=action_desc,
                         pending_documents=pending_docs,
                         user=user,
                         missing_documents=missing_docs)

# Replace the existing route function with our enhanced version
try:
    app.view_functions['comprehensive_documents_required'] = enhanced_documents_required
except Exception:
    pass

print("🛡️ COMPREHENSIVE DOCUMENT ENFORCEMENT MIDDLEWARE ACTIVATED")
print("📋 ALL routes now automatically protected with legal document requirements")
print("⚖️ Users cannot proceed with ANY significant action until documents are signed")