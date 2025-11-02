#!/usr/bin/env python3
"""
R2 Permissions Diagnostic Tool
Helps identify specific permission issues with Cloudflare R2 access
"""

import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def diagnose_r2_permissions():
    """Diagnose R2 permission issues step by step"""
    
    print("🔍 LaborLooker R2 Permissions Diagnostic")
    print("=" * 60)
    
    # Get R2 configuration
    endpoint_url = os.getenv('CLOUDFLARE_R2_ENDPOINT')
    access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID') 
    secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET', 'laborlooker')
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    
    print(f"Account ID: {account_id}")
    print(f"R2 Endpoint: {endpoint_url}")
    print(f"Bucket Name: {bucket_name}")
    print(f"Access Key: {'***' + access_key[-4:] if access_key and len(access_key) > 4 else 'Not set'}")
    print(f"Secret Key: {'***' + secret_key[-4:] if secret_key and len(secret_key) > 4 else 'Not set'}")
    print()
    
    if not all([endpoint_url, access_key, secret_key]):
        print("❌ Missing R2 credentials!")
        return False
    
    try:
        # Initialize S3 client for R2
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'
        )
        
        print("🧪 Testing individual R2 permissions...")
        print()
        
        # Test 1: List buckets (requires account-level read)
        print("1️⃣ Testing bucket listing permissions...")
        try:
            response = s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
            print(f"   ✅ Can list buckets: {buckets}")
            
            if bucket_name in buckets:
                print(f"   ✅ Target bucket '{bucket_name}' exists")
            else:
                print(f"   ⚠️  Target bucket '{bucket_name}' not found")
                print(f"   Available buckets: {buckets}")
                
        except ClientError as e:
            print(f"   ❌ Cannot list buckets: {e.response['Error']['Code']}")
            print(f"   This might be okay if token is bucket-scoped")
        
        print()
        
        # Test 2: Bucket head (basic bucket access)
        print("2️⃣ Testing bucket access permissions...")
        try:
            response = s3_client.head_bucket(Bucket=bucket_name)
            print(f"   ✅ Can access bucket '{bucket_name}'")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"   ❌ Cannot access bucket: {error_code}")
            if error_code == 'NoSuchBucket':
                print(f"   💡 Bucket '{bucket_name}' doesn't exist - create it in Cloudflare dashboard")
            elif error_code == 'AccessDenied':
                print(f"   💡 Token doesn't have access to bucket '{bucket_name}'")
            return False
        
        print()
        
        # Test 3: List objects (read permission)
        print("3️⃣ Testing object listing permissions...")
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            object_count = response.get('KeyCount', 0)
            print(f"   ✅ Can list objects: {object_count} objects found")
        except ClientError as e:
            print(f"   ❌ Cannot list objects: {e.response['Error']['Code']}")
            return False
        
        print()
        
        # Test 4: Write permission
        print("4️⃣ Testing object write permissions...")
        try:
            test_key = "diagnostic/write_test.txt"
            test_content = b"R2 Write Test"
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=test_content,
                ContentType='text/plain'
            )
            print(f"   ✅ Can write objects: {test_key}")
            
            # Test 5: Read permission
            print("5️⃣ Testing object read permissions...")
            response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
            downloaded_content = response['Body'].read()
            
            if downloaded_content == test_content:
                print(f"   ✅ Can read objects successfully")
            else:
                print(f"   ⚠️  Read content mismatch")
            
            # Test 6: Delete permission
            print("6️⃣ Testing object delete permissions...")
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print(f"   ✅ Can delete objects")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"   ❌ Cannot write/read/delete objects: {error_code}")
            
            if error_code == 'AccessDenied':
                print(f"   💡 Token needs R2:Write permission")
            return False
        
        print()
        print("🎉 All R2 permissions are working correctly!")
        print("✅ Token has full read/write access to the bucket")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def show_token_requirements():
    """Show what permissions the R2 token needs"""
    print()
    print("📋 Required R2 Token Permissions")
    print("=" * 40)
    print("When creating your R2 token in Cloudflare:")
    print()
    print("1. Account permissions:")
    print("   - Cloudflare R2:Read")
    print("   - Cloudflare R2:Edit")
    print()
    print("2. Zone permissions: None required")
    print()
    print("3. Account resources:")
    print("   - Include: All accounts")
    print("   - OR specific account ID")
    print()
    print("4. Zone resources: None required")
    print()
    print("Alternative: Use account-level API token with:")
    print("   - Account ID: All accounts (or specific)")
    print("   - Permissions: R2:Read, R2:Edit")

if __name__ == "__main__":
    success = diagnose_r2_permissions()
    if not success:
        show_token_requirements()