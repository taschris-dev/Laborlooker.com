"""
Cloudflare R2 Storage Integration for LaborLooker Platform
Handles file uploads, downloads, and management with R2 S3-compatible API
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import current_app
from werkzeug.utils import secure_filename
import shortuuid
from datetime import datetime

class LaborLookerR2Storage:
    """Cloudflare R2 storage client for LaborLooker platform"""
    
    def __init__(self, app=None):
        self.s3_client = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize R2 storage with Flask app"""
        try:
            # Get R2 configuration from environment
            endpoint_url = os.getenv('CLOUDFLARE_R2_ENDPOINT')
            access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID')
            secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
            
            if not all([endpoint_url, access_key, secret_key]):
                app.logger.warning("R2 storage not fully configured - some environment variables missing")
                return
            
            # Initialize S3 client for R2
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'  # R2 uses 'auto' for region
            )
            
            # Test connection
            self.bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET', 'laborlooker')
            self.public_url_base = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', 'https://cdn.laborlooker.com')
            
            app.logger.info(f"✅ R2 storage initialized for bucket: {self.bucket_name}")
            
        except Exception as e:
            app.logger.error(f"❌ R2 storage initialization failed: {e}")
            self.s3_client = None
    
    def is_available(self):
        """Check if R2 storage is available"""
        return self.s3_client is not None
    
    def upload_file(self, file, folder="uploads", filename=None):
        """
        Upload file to R2 storage
        
        Args:
            file: FileStorage object from Flask request
            folder: Folder path in R2 bucket
            filename: Custom filename (optional)
        
        Returns:
            dict: Upload result with URL and metadata
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'R2 storage not available',
                'fallback': 'local'
            }
        
        try:
            # Generate secure filename
            if filename:
                secure_name = secure_filename(filename)
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = shortuuid.uuid()[:8]
                original_name = secure_filename(file.filename)
                name, ext = os.path.splitext(original_name)
                secure_name = f"{timestamp}_{unique_id}_{name}{ext}"
            
            # Create full object key
            object_key = f"{folder}/{secure_name}"
            
            # Upload to R2
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                object_key,
                ExtraArgs={
                    'ContentType': file.content_type or 'application/octet-stream',
                    'CacheControl': 'public, max-age=31536000',  # 1 year cache
                }
            )
            
            # Generate public URL
            public_url = f"{self.public_url_base}/{object_key}"
            
            return {
                'success': True,
                'url': public_url,
                'key': object_key,
                'filename': secure_name,
                'bucket': self.bucket_name,
                'size': file.content_length or 0
            }
            
        except ClientError as e:
            current_app.logger.error(f"R2 upload failed: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'fallback': 'local'
            }
        except Exception as e:
            current_app.logger.error(f"R2 upload error: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'fallback': 'local'
            }
    
    def delete_file(self, object_key):
        """Delete file from R2 storage"""
        if not self.is_available():
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError as e:
            current_app.logger.error(f"R2 delete failed: {e}")
            return False
    
    def generate_presigned_url(self, object_key, expiration=3600):
        """Generate presigned URL for secure file access"""
        if not self.is_available():
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            current_app.logger.error(f"Presigned URL generation failed: {e}")
            return None
    
    def list_files(self, prefix="", max_keys=100):
        """List files in R2 bucket with optional prefix filter"""
        if not self.is_available():
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'url': f"{self.public_url_base}/{obj['Key']}"
                })
            
            return files
        except ClientError as e:
            current_app.logger.error(f"R2 list files failed: {e}")
            return []

# Global R2 storage instance
r2_storage = LaborLookerR2Storage()

# Decorator for handling file uploads with R2 fallback
def upload_with_fallback(folder="uploads", allowed_extensions=None):
    """Decorator for file upload routes with R2 and local fallback"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, current_app
            
            # Check if file exists in request
            if 'file' not in request.files:
                return func(*args, **kwargs)
            
            file = request.files['file']
            if file.filename == '':
                return func(*args, **kwargs)
            
            # Validate file extension
            if allowed_extensions:
                filename = file.filename.lower()
                if not any(filename.endswith(ext) for ext in allowed_extensions):
                    return func(*args, **kwargs)
            
            # Try R2 upload first
            upload_result = r2_storage.upload_file(file, folder)
            
            if upload_result['success']:
                # Add R2 result to request context
                request.r2_upload = upload_result
                current_app.logger.info(f"File uploaded to R2: {upload_result['url']}")
            else:
                # Fall back to local storage
                current_app.logger.warning(f"R2 upload failed, using local storage: {upload_result.get('error')}")
                request.r2_upload = None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator