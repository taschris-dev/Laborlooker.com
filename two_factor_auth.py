"""
Two-Factor Authentication System for LaborLooker
Implements email-based 2FA with backup codes and secure login flow
"""

import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

class TwoFactorAuthManager:
    """Manages two-factor authentication for users"""
    
    def __init__(self):
        self.token_length = 6
        self.token_expiry_minutes = 10
        self.backup_codes_count = 10
        
    def generate_token(self):
        """Generate a secure 6-digit token"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.token_length)])
    
    def generate_backup_codes(self):
        """Generate backup codes for account recovery"""
        codes = []
        for _ in range(self.backup_codes_count):
            # Generate 8-character alphanumeric codes
            code = secrets.token_hex(4).upper()
            codes.append(code)
        return codes
    
    def hash_code(self, code):
        """Hash a code for secure storage"""
        return generate_password_hash(code)
    
    def verify_code(self, code, hashed_code):
        """Verify a code against its hash"""
        return check_password_hash(hashed_code, code)
    
    def setup_2fa_for_user(self, user, phone_number=None):
        """Set up 2FA for a user"""
        from main import db, TwoFactorAuth
        
        # Check if 2FA already exists
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        
        if not two_fa:
            two_fa = TwoFactorAuth(user_id=user.id)
            db.session.add(two_fa)
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        hashed_codes = [self.hash_code(code) for code in backup_codes]
        
        # Update 2FA settings
        two_fa.enabled = True
        two_fa.email_based = True
        two_fa.phone_number = phone_number
        two_fa.phone_based = bool(phone_number)
        two_fa.backup_codes = json.dumps(hashed_codes)
        two_fa.backup_codes_used = json.dumps([])
        
        try:
            db.session.commit()
            return backup_codes, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    def disable_2fa_for_user(self, user):
        """Disable 2FA for a user"""
        from main import db, TwoFactorAuth, TwoFactorToken
        
        try:
            # Remove 2FA settings
            two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
            if two_fa:
                db.session.delete(two_fa)
            
            # Remove any pending tokens
            TwoFactorToken.query.filter_by(user_id=user.id).delete()
            
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    def is_2fa_enabled(self, user):
        """Check if 2FA is enabled for a user"""
        from main import TwoFactorAuth
        
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id, enabled=True).first()
        return two_fa is not None
    
    def create_2fa_token(self, user, token_type='email'):
        """Create a 2FA token for login verification"""
        from main import db, TwoFactorToken
        
        # Remove any existing unused tokens
        TwoFactorToken.query.filter_by(user_id=user.id, used=False).delete()
        
        # Generate new token
        token = self.generate_token()
        token_hash = self.hash_code(token)
        
        # Create token record
        two_fa_token = TwoFactorToken(
            user_id=user.id,
            token=token,  # Store plain token for email sending (will be removed after sending)
            token_type=token_type,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=self.token_expiry_minutes)
        )
        
        try:
            db.session.add(two_fa_token)
            db.session.commit()
            return two_fa_token, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)
    
    def verify_2fa_token(self, user, provided_token, token_type='email'):
        """Verify a 2FA token"""
        from main import db, TwoFactorToken
        
        # Find valid token
        token_record = TwoFactorToken.query.filter_by(
            user_id=user.id,
            token_type=token_type,
            used=False
        ).filter(
            TwoFactorToken.expires_at > datetime.utcnow()
        ).first()
        
        if not token_record:
            return False, "No valid token found or token expired"
        
        # Verify token
        if self.verify_code(provided_token, token_record.token_hash):
            # Mark token as used
            token_record.used = True
            token_record.used_at = datetime.utcnow()
            
            try:
                db.session.commit()
                return True, "Token verified successfully"
            except Exception as e:
                db.session.rollback()
                return False, f"Database error: {str(e)}"
        else:
            return False, "Invalid token"
    
    def verify_backup_code(self, user, provided_code):
        """Verify a backup code"""
        from main import db, TwoFactorAuth
        
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id, enabled=True).first()
        if not two_fa:
            return False, "2FA not enabled"
        
        try:
            backup_codes = json.loads(two_fa.backup_codes)
            used_codes = json.loads(two_fa.backup_codes_used)
        except:
            return False, "Invalid backup codes data"
        
        # Check if code is valid and not used
        for i, hashed_code in enumerate(backup_codes):
            if i not in used_codes and self.verify_code(provided_code, hashed_code):
                # Mark code as used
                used_codes.append(i)
                two_fa.backup_codes_used = json.dumps(used_codes)
                
                try:
                    db.session.commit()
                    return True, "Backup code verified successfully"
                except Exception as e:
                    db.session.rollback()
                    return False, f"Database error: {str(e)}"
        
        return False, "Invalid backup code"
    
    def send_2fa_email(self, user, token):
        """Send 2FA token via email"""
        try:
            # Email configuration
            smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('MAIL_USERNAME')
            smtp_password = current_app.config.get('MAIL_PASSWORD')
            
            if not all([smtp_username, smtp_password]):
                return False, "Email configuration missing"
            
            # Create email content
            subject = "LaborLooker - Two-Factor Authentication Code"
            
            email_template = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                    <h1>LaborLooker Security</h1>
                </div>
                
                <div style="padding: 30px;">
                    <h2>Two-Factor Authentication Code</h2>
                    
                    <p>Hello,</p>
                    
                    <p>Someone is trying to sign in to your LaborLooker account. If this was you, please use the verification code below:</p>
                    
                    <div style="background-color: #f8f9fa; border: 2px solid #007bff; padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #007bff; letter-spacing: 8px; margin: 0; font-size: 36px;">{{ token }}</h1>
                    </div>
                    
                    <p><strong>This code will expire in 10 minutes.</strong></p>
                    
                    <p>If you didn't try to sign in, please:</p>
                    <ul>
                        <li>Ignore this email</li>
                        <li>Consider changing your password</li>
                        <li>Contact support if you're concerned</li>
                    </ul>
                    
                    <div style="border-top: 1px solid #dee2e6; margin-top: 30px; padding-top: 20px;">
                        <p style="color: #6c757d; font-size: 14px;">
                            <strong>Security Tips:</strong><br>
                            • Never share this code with anyone<br>
                            • LaborLooker will never ask for this code via phone or email<br>
                            • Always verify you're on laborlooker.com before entering codes
                        </p>
                    </div>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d;">
                    <p>This is an automated message from LaborLooker. Please do not reply to this email.</p>
                    <p>© 2025 LaborLooker. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
            
            html_content = render_template_string(email_template, token=token)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_username
            msg['To'] = user.email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            return True, "Email sent successfully"
            
        except Exception as e:
            current_app.logger.error(f"Failed to send 2FA email: {str(e)}")
            return False, f"Failed to send email: {str(e)}"
    
    def get_unused_backup_codes_count(self, user):
        """Get count of unused backup codes"""
        from main import TwoFactorAuth
        
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id, enabled=True).first()
        if not two_fa:
            return 0
        
        try:
            backup_codes = json.loads(two_fa.backup_codes)
            used_codes = json.loads(two_fa.backup_codes_used)
            return len(backup_codes) - len(used_codes)
        except:
            return 0
    
    def regenerate_backup_codes(self, user):
        """Regenerate backup codes for a user"""
        from main import db, TwoFactorAuth
        
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id, enabled=True).first()
        if not two_fa:
            return None, "2FA not enabled"
        
        # Generate new backup codes
        backup_codes = self.generate_backup_codes()
        hashed_codes = [self.hash_code(code) for code in backup_codes]
        
        # Update 2FA settings
        two_fa.backup_codes = json.dumps(hashed_codes)
        two_fa.backup_codes_used = json.dumps([])
        
        try:
            db.session.commit()
            return backup_codes, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

def require_2fa_verification(f):
    """Decorator to require 2FA verification for sensitive actions"""
    from functools import wraps
    from flask import session, redirect, url_for, flash, request
    from flask_login import current_user
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Check if 2FA is required but not verified in this session
        two_fa_manager = TwoFactorAuthManager()
        
        if two_fa_manager.is_2fa_enabled(current_user):
            # Check if 2FA was verified in this session
            if not session.get('2fa_verified'):
                flash('Two-factor authentication required for this action.', 'warning')
                session['2fa_redirect_url'] = request.url
                return redirect(url_for('two_factor_verify'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_2fa_required_on_login(user):
    """Check if 2FA is required during login"""
    two_fa_manager = TwoFactorAuthManager()
    return two_fa_manager.is_2fa_enabled(user)

def send_2fa_token_on_login(user):
    """Send 2FA token during login process"""
    two_fa_manager = TwoFactorAuthManager()
    
    # Create token
    token_record, error = two_fa_manager.create_2fa_token(user, 'email')
    if error:
        return False, error
    
    # Send email
    success, message = two_fa_manager.send_2fa_email(user, token_record.token)
    
    # Remove plain token from database for security
    if token_record:
        token_record.token = None  # Clear plain token
        from main import db
        db.session.commit()
    
    return success, message