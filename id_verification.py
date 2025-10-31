"""
ID Verification System for LaborLooker
Handles government ID verification for contractors and clients
"""

from flask import Blueprint, request, jsonify, current_app, session, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime, timedelta
import hashlib
import base64
import requests
from PIL import Image
import pytesseract
import cv2
import numpy as np

id_verification_bp = Blueprint('id_verification', __name__, url_prefix='/id-verification')

# Allowed file extensions for ID documents
ALLOWED_ID_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class IDVerificationStatus:
    PENDING = 'pending'
    PROCESSING = 'processing'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    EXPIRED = 'expired'

class IDDocumentType:
    DRIVERS_LICENSE = 'drivers_license'
    PASSPORT = 'passport'
    STATE_ID = 'state_id'
    MILITARY_ID = 'military_id'
    
    @classmethod
    def get_all(cls):
        return [cls.DRIVERS_LICENSE, cls.PASSPORT, cls.STATE_ID, cls.MILITARY_ID]

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_ID_EXTENSIONS

def generate_verification_id():
    """Generate unique verification ID"""
    return f"VER_{uuid.uuid4().hex[:12].upper()}"

def secure_file_storage(file, verification_id):
    """Securely store uploaded ID document"""
    if not file or not allowed_file(file.filename):
        return None, "Invalid file type"
    
    # Create secure filename
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    secure_filename_final = f"{verification_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
    
    # Create verification directory if it doesn't exist
    verification_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'id_verification')
    os.makedirs(verification_dir, exist_ok=True)
    
    file_path = os.path.join(verification_dir, secure_filename_final)
    
    try:
        file.save(file_path)
        return file_path, None
    except Exception as e:
        return None, f"File upload failed: {str(e)}"

def extract_text_from_id(image_path):
    """Extract text from ID document using OCR"""
    try:
        # Load image
        image = cv2.imread(image_path)
        
        # Preprocess image for better OCR
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get better contrast
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Remove noise
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        img = cv2.medianBlur(img, 3)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        return text.strip(), None
    except Exception as e:
        return None, f"OCR extraction failed: {str(e)}"

def validate_id_format(extracted_text, document_type):
    """Validate ID document format and extract key information"""
    import re
    
    validation_result = {
        'is_valid': False,
        'extracted_data': {},
        'confidence_score': 0.0,
        'validation_errors': []
    }
    
    if not extracted_text:
        validation_result['validation_errors'].append("No text extracted from document")
        return validation_result
    
    text_upper = extracted_text.upper()
    
    try:
        if document_type == IDDocumentType.DRIVERS_LICENSE:
            # Look for driver's license patterns
            dl_patterns = {
                'license_number': r'(?:LIC|LICENSE|DL)[\s#:]*([A-Z0-9]{8,15})',
                'date_of_birth': r'(?:DOB|BIRTH)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'expiration': r'(?:EXP|EXPIRES)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'name': r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)',
                'address': r'(\d+\s+[A-Z\s]+(?:ST|STREET|AVE|AVENUE|RD|ROAD|BLVD|BOULEVARD))'
            }
            
            for field, pattern in dl_patterns.items():
                match = re.search(pattern, text_upper)
                if match:
                    validation_result['extracted_data'][field] = match.group(1).strip()
            
            # Check if essential fields are present
            required_fields = ['license_number', 'date_of_birth', 'name']
            found_fields = sum(1 for field in required_fields if field in validation_result['extracted_data'])
            validation_result['confidence_score'] = found_fields / len(required_fields)
            
            if validation_result['confidence_score'] >= 0.7:
                validation_result['is_valid'] = True
            else:
                validation_result['validation_errors'].append("Insufficient required fields detected")
        
        elif document_type == IDDocumentType.PASSPORT:
            # Look for passport patterns
            passport_patterns = {
                'passport_number': r'(?:PASSPORT|NO)[\s#:]*([A-Z0-9]{6,10})',
                'date_of_birth': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'expiration': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'name': r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)',
                'country': r'(UNITED STATES|USA|US)'
            }
            
            for field, pattern in passport_patterns.items():
                match = re.search(pattern, text_upper)
                if match:
                    validation_result['extracted_data'][field] = match.group(1).strip()
            
            required_fields = ['passport_number', 'name']
            found_fields = sum(1 for field in required_fields if field in validation_result['extracted_data'])
            validation_result['confidence_score'] = found_fields / len(required_fields)
            
            if validation_result['confidence_score'] >= 0.7:
                validation_result['is_valid'] = True
            else:
                validation_result['validation_errors'].append("Insufficient passport fields detected")
        
        elif document_type == IDDocumentType.STATE_ID:
            # Similar to driver's license but look for ID-specific text
            if 'IDENTIFICATION' in text_upper or 'STATE ID' in text_upper:
                validation_result['confidence_score'] = 0.8
                validation_result['is_valid'] = True
                validation_result['extracted_data']['document_type'] = 'STATE_ID'
            else:
                validation_result['validation_errors'].append("State ID document indicators not found")
        
        # Additional validation: Check expiration date
        if 'expiration' in validation_result['extracted_data']:
            try:
                exp_date_str = validation_result['extracted_data']['expiration']
                exp_date = datetime.strptime(exp_date_str.replace('-', '/'), '%m/%d/%Y')
                if exp_date < datetime.now():
                    validation_result['validation_errors'].append("Document has expired")
                    validation_result['confidence_score'] *= 0.5
            except:
                pass
        
    except Exception as e:
        validation_result['validation_errors'].append(f"Validation error: {str(e)}")
    
    return validation_result

def create_verification_record(user_id, document_type, file_path, validation_result):
    """Create verification record in database"""
    from main import db, IDVerification
    
    verification = IDVerification(
        verification_id=generate_verification_id(),
        user_id=user_id,
        document_type=document_type,
        file_path=file_path,
        status=IDVerificationStatus.PROCESSING,
        extracted_data=json.dumps(validation_result['extracted_data']),
        confidence_score=validation_result['confidence_score'],
        validation_errors=json.dumps(validation_result['validation_errors']),
        submitted_at=datetime.utcnow()
    )
    
    # Automatically approve if confidence is high
    if validation_result['confidence_score'] >= 0.9 and not validation_result['validation_errors']:
        verification.status = IDVerificationStatus.VERIFIED
        verification.verified_at = datetime.utcnow()
    elif validation_result['confidence_score'] < 0.5 or validation_result['validation_errors']:
        verification.status = IDVerificationStatus.REJECTED
        verification.rejected_at = datetime.utcnow()
        verification.rejection_reason = '; '.join(validation_result['validation_errors'])
    
    try:
        db.session.add(verification)
        db.session.commit()
        return verification, None
    except Exception as e:
        db.session.rollback()
        return None, f"Database error: {str(e)}"

@id_verification_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_id():
    """Handle ID document upload and verification"""
    if request.method == 'GET':
        return render_template('id_verification/upload.html', 
                             document_types=IDDocumentType.get_all())
    
    try:
        # Check if user already has verified ID
        from main import IDVerification
        existing = IDVerification.query.filter_by(
            user_id=current_user.id,
            status=IDVerificationStatus.VERIFIED
        ).first()
        
        if existing:
            flash('You already have a verified ID on file.', 'info')
            return redirect(url_for('id_verification.status'))
        
        # Validate form data
        document_type = request.form.get('document_type')
        if document_type not in IDDocumentType.get_all():
            flash('Invalid document type selected.', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        # Check if file is present
        if 'id_document' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        file = request.files['id_document']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        # Check file size
        if len(file.read()) > MAX_FILE_SIZE:
            flash('File size too large. Maximum 10MB allowed.', 'error')
            return redirect(url_for('id_verification.upload_id'))
        file.seek(0)  # Reset file pointer
        
        # Generate verification ID and store file
        verification_id = generate_verification_id()
        file_path, error = secure_file_storage(file, verification_id)
        
        if error:
            flash(f'File upload failed: {error}', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        # Extract and validate document
        extracted_text, ocr_error = extract_text_from_id(file_path)
        if ocr_error:
            flash(f'Document processing failed: {ocr_error}', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        validation_result = validate_id_format(extracted_text, document_type)
        
        # Create verification record
        verification, db_error = create_verification_record(
            current_user.id, document_type, file_path, validation_result
        )
        
        if db_error:
            flash(f'Verification record creation failed: {db_error}', 'error')
            return redirect(url_for('id_verification.upload_id'))
        
        # Provide user feedback
        if verification.status == IDVerificationStatus.VERIFIED:
            flash('Your ID has been automatically verified!', 'success')
        elif verification.status == IDVerificationStatus.REJECTED:
            flash(f'ID verification failed: {verification.rejection_reason}', 'error')
        else:
            flash('Your ID is being processed. You will be notified once verification is complete.', 'info')
        
        return redirect(url_for('id_verification.status'))
        
    except Exception as e:
        current_app.logger.error(f"ID verification upload error: {str(e)}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('id_verification.upload_id'))

@id_verification_bp.route('/status')
@login_required
def status():
    """Display current verification status"""
    from main import IDVerification
    
    verification = IDVerification.query.filter_by(user_id=current_user.id)\
                                     .order_by(IDVerification.submitted_at.desc())\
                                     .first()
    
    return render_template('id_verification/status.html', verification=verification)

@id_verification_bp.route('/api/verify-status')
@login_required
def api_verify_status():
    """API endpoint for checking verification status"""
    from main import IDVerification
    
    verification = IDVerification.query.filter_by(user_id=current_user.id)\
                                     .order_by(IDVerification.submitted_at.desc())\
                                     .first()
    
    if not verification:
        return jsonify({
            'status': 'not_verified',
            'message': 'No verification submitted'
        })
    
    return jsonify({
        'verification_id': verification.verification_id,
        'status': verification.status,
        'document_type': verification.document_type,
        'submitted_at': verification.submitted_at.isoformat(),
        'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
        'confidence_score': verification.confidence_score,
        'message': 'Verification status retrieved successfully'
    })

@id_verification_bp.route('/admin/pending')
@login_required
def admin_pending():
    """Admin view for pending verifications"""
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    from main import IDVerification, User
    
    pending_verifications = db.session.query(IDVerification, User)\
        .join(User, IDVerification.user_id == User.id)\
        .filter(IDVerification.status == IDVerificationStatus.PROCESSING)\
        .order_by(IDVerification.submitted_at.desc())\
        .all()
    
    return render_template('id_verification/admin_pending.html', 
                         verifications=pending_verifications)

@id_verification_bp.route('/admin/approve/<verification_id>', methods=['POST'])
@login_required
def admin_approve(verification_id):
    """Admin approval of ID verification"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    from main import IDVerification, db
    
    verification = IDVerification.query.filter_by(verification_id=verification_id).first()
    if not verification:
        return jsonify({'error': 'Verification not found'}), 404
    
    try:
        verification.status = IDVerificationStatus.VERIFIED
        verification.verified_at = datetime.utcnow()
        verification.verified_by = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Verification approved successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Approval failed: {str(e)}'}), 500

@id_verification_bp.route('/admin/reject/<verification_id>', methods=['POST'])
@login_required
def admin_reject(verification_id):
    """Admin rejection of ID verification"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    from main import IDVerification, db
    
    data = request.get_json()
    rejection_reason = data.get('reason', 'Manual rejection by admin')
    
    verification = IDVerification.query.filter_by(verification_id=verification_id).first()
    if not verification:
        return jsonify({'error': 'Verification not found'}), 404
    
    try:
        verification.status = IDVerificationStatus.REJECTED
        verification.rejected_at = datetime.utcnow()
        verification.rejection_reason = rejection_reason
        verification.verified_by = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Verification rejected successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Rejection failed: {str(e)}'}), 500

def is_user_verified(user_id):
    """Check if user has verified ID"""
    from main import IDVerification
    
    verification = IDVerification.query.filter_by(
        user_id=user_id,
        status=IDVerificationStatus.VERIFIED
    ).first()
    
    return verification is not None

def require_verified_id(f):
    """Decorator to require verified ID for certain actions"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if not is_user_verified(current_user.id):
            flash('You must complete ID verification to access this feature.', 'warning')
            return redirect(url_for('id_verification.upload_id'))
        
        return f(*args, **kwargs)
    return decorated_function