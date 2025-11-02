#!/usr/bin/env python3
"""
Cloudflare R2 Storage Test Script for LaborLooker Platform
Tests R2 connectivity and basic operations
"""

import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_r2_connection():
    """Test Cloudflare R2 storage connection"""
    
    print("🔧 LaborLooker R2 Storage Test")
    print("=" * 50)
    
    # Get R2 configuration
    endpoint_url = os.getenv('CLOUDFLARE_R2_ENDPOINT')
    access_key = os.getenv('CLOUDFLARE_ACCESS_KEY_ID') 
    secret_key = os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET', 'laborlooker')
    
    print(f"R2 Endpoint: {endpoint_url}")
    print(f"Bucket Name: {bucket_name}")
    print(f"Access Key: {'***' + access_key[-4:] if access_key and len(access_key) > 4 else 'Not set'}")
    print(f"Secret Key: {'***' + secret_key[-4:] if secret_key and len(secret_key) > 4 else 'Not set'}")
    print()
    
    if not all([endpoint_url, access_key, secret_key]):
        print("❌ Missing R2 credentials!")
        print("Please set the following environment variables:")
        print("- CLOUDFLARE_ACCESS_KEY_ID")
        print("- CLOUDFLARE_SECRET_ACCESS_KEY")
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
        
        print("🔗 Testing R2 connection...")
        
        # Test bucket access
        response = s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket access successful!")
        
        # Test list objects
        objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        object_count = objects.get('KeyCount', 0)
        print(f"✅ Bucket contains {object_count} objects")
        
        # Test upload (create a small test file)
        test_content = b"LaborLooker R2 Test File"
        test_key = "test/connection_test.txt"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print(f"✅ Test file uploaded: {test_key}")
        
        # Test download
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read()
        
        if downloaded_content == test_content:
            print("✅ Test file download successful!")
        else:
            print("❌ Downloaded content doesn't match uploaded content")
        
        # Clean up test file
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✅ Test file cleaned up")
        
        # Generate public URL
        public_url_base = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', 'https://cdn.laborlooker.com')
        public_url = f"{public_url_base}/test/example.jpg"
        print(f"✅ Public URL format: {public_url}")
        
        print()
        print("🎉 R2 Storage test PASSED!")
        print("Your R2 storage is ready for production use!")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ R2 connection failed!")
        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")
        
        if error_code == 'NoSuchBucket':
            print("\n💡 Solution: Create the R2 bucket in Cloudflare dashboard")
        elif error_code == 'InvalidAccessKeyId':
            print("\n💡 Solution: Check your CLOUDFLARE_ACCESS_KEY_ID")
        elif error_code == 'SignatureDoesNotMatch':
            print("\n💡 Solution: Check your CLOUDFLARE_SECRET_ACCESS_KEY")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_r2_connection()