"""
Comprehensive Document-Protected Routes for LaborLooker
Every significant action requires signed legal documents before proceeding
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from main import app, db
from comprehensive_documents import (
    comprehensive_doc_manager, 
    require_documents_for_action, 
    job_acceptance_context,
    payment_context,
    job_posting_context
)

# Add the comprehensive documents page route
@app.route('/comprehensive_documents_required')
def comprehensive_documents_required():
    """Display page showing required documents for an action"""
    action = request.args.get('action', 'unknown_action')
    action_desc = comprehensive_doc_manager.get_action_description(action)
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from main import User, ContractDocument
    user = User.query.get(session['user_id'])
    
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
                         user=user)

# Enhanced Registration with Document Requirements
@app.route('/protected_register', methods=['GET', 'POST'])
@require_documents_for_action('account_creation')
def protected_register():
    """Protected registration requiring binding agreements"""
    # This will only run if all required documents are signed
    return redirect(url_for('register'))

# Protected Contractor Registration  
@app.route('/protected_contractor_register', methods=['GET', 'POST'])
@require_documents_for_action('contractor_registration')
def protected_contractor_register():
    """Protected contractor registration with comprehensive agreements"""
    return redirect(url_for('contractor_profile'))

# Protected Quote Scheduling
@app.route('/protected_schedule_quote/<int:work_request_id>', methods=['POST'])
@require_documents_for_action('quote_scheduling')
def protected_schedule_quote(work_request_id):
    """Protected quote scheduling with liability waivers"""
    return redirect(url_for('schedule_quote', work_request_id=work_request_id))

# Protected Job Acceptance
@app.route('/protected_accept_job/<int:work_request_id>', methods=['POST'])
@require_documents_for_action('job_acceptance', job_acceptance_context)
def protected_accept_job(work_request_id):
    """Protected job acceptance with binding work contracts"""
    return redirect(url_for('accept_job', work_request_id=work_request_id))

# Protected Payment Processing
@app.route('/protected_process_payment', methods=['POST'])
@require_documents_for_action('payment_user_to_user', payment_context)
def protected_process_payment():
    """Protected payment processing with financial agreements"""
    return redirect(url_for('process_payment'))

# Protected Job Posting
@app.route('/protected_post_job', methods=['GET', 'POST'])
@require_documents_for_action('job_posting', job_posting_context) 
def protected_post_job():
    """Protected job posting with customer agreements"""
    return redirect(url_for('post_job'))

# Protected PII Collection
@app.route('/protected_collect_pii', methods=['POST'])
@require_documents_for_action('pii_collection')
def protected_collect_pii():
    """Protected PII collection with data consent agreements"""
    return jsonify({"status": "authorized", "message": "PII collection authorized"})

# Protected Company Application
@app.route('/protected_apply_company', methods=['GET', 'POST'])
@require_documents_for_action('company_application')
def protected_apply_company():
    """Protected company application with business verification"""
    return redirect(url_for('company_application'))

# Protected Review Submission
@app.route('/protected_submit_review', methods=['POST'])
@require_documents_for_action('review_submission')
def protected_submit_review():
    """Protected review submission with accuracy oaths"""
    return redirect(url_for('submit_review'))

# Protected Photo Upload
@app.route('/protected_upload_photo', methods=['POST'])
@require_documents_for_action('photo_upload')
def protected_upload_photo():
    """Protected photo upload with rights transfers"""
    return redirect(url_for('upload_photo'))

# Document Enforcement Middleware for specific routes
def add_document_enforcement_to_existing_routes():
    """Add document enforcement to existing routes"""
    
    # Get the original register function
    original_register = app.view_functions.get('register')
    if original_register:
        # Wrap with document requirements
        app.view_functions['register'] = require_documents_for_action('account_creation')(original_register)
    
    # Get the contractor profile function
    original_contractor = app.view_functions.get('contractor_profile')
    if original_contractor:
        app.view_functions['contractor_profile'] = require_documents_for_action('contractor_registration')(original_contractor)
    
    # Get the job posting function
    original_post_job = app.view_functions.get('post_job')
    if original_post_job:
        app.view_functions['post_job'] = require_documents_for_action('job_posting', job_posting_context)(original_post_job)
    
    # Get payment processing functions
    original_process_payment = app.view_functions.get('process_payment')
    if original_process_payment:
        app.view_functions['process_payment'] = require_documents_for_action('payment_user_to_user', payment_context)(original_process_payment)

# API endpoint to check document status for any action
@app.route('/api/check_document_requirements/<action>')
def api_check_document_requirements(action):
    """API endpoint to check if user has required documents for an action"""
    
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    from main import User
    user = User.query.get(session['user_id'])
    
    docs_complete, missing_docs = comprehensive_doc_manager.check_action_requirements(user, action)
    
    return jsonify({
        "action": action,
        "documents_complete": docs_complete,
        "missing_documents": missing_docs,
        "action_description": comprehensive_doc_manager.get_action_description(action)
    })

# API endpoint to get all document requirements for user
@app.route('/api/user_document_status')
def api_user_document_status():
    """Get comprehensive document status for current user"""
    
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    from main import User, ContractDocument
    user = User.query.get(session['user_id'])
    
    # Get all user's documents
    user_docs = ContractDocument.query.filter_by(user_id=user.id).all()
    
    document_status = {}
    for doc in user_docs:
        document_status[doc.document_type] = {
            "status": doc.status,
            "sent_at": doc.sent_at.isoformat() if doc.sent_at else None,
            "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
            "action_context": doc.action_context,
            "document_name": doc.document_name
        }
    
    return jsonify({
        "user_id": user.id,
        "total_documents": len(user_docs),
        "completed_documents": len([d for d in user_docs if d.status == 'completed']),
        "pending_documents": len([d for d in user_docs if d.status == 'sent']),
        "document_details": document_status
    })

# Auto-enforce documents on application startup
with app.app_context():
    add_document_enforcement_to_existing_routes()

print("✅ Comprehensive Document Protection System ACTIVATED")
print("🔒 ALL major actions now require signed legal documents")
print("📋 Document types: Account creation, contractor registration, job posting, payments, PII collection, and more")
print("⚖️ Legal enforceability: Binding contracts, liability waivers, arbitration agreements")