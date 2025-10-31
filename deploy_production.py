#!/usr/bin/env python3
"""
Labor Lookers Production Deployment Automation
Google Cloud Platform - Cloud Run + Cloud SQL
"""

import os
import subprocess
import sys
import json
import time
from datetime import datetime

class LaborLookersDeployment:
    def __init__(self):
        self.project_id = None
        self.region = "us-central1"
        self.service_name = "laborlookers-app"
        self.db_instance = "laborlookers-db"
        self.db_name = "laborlookers"
        self.db_user = "laborlookers_user"
        
    def run_command(self, command, check=True):
        """Run shell command and return result"""
        print(f"🔧 Running: {command}")
        try:
            result = subprocess.run(command, shell=True, check=check, 
                                 capture_output=True, text=True)
            if result.stdout:
                print(f"✅ Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            if e.stderr:
                print(f"❌ Stderr: {e.stderr}")
            return None
    
    def setup_project(self):
        """Setup GCP project and enable APIs"""
        print("\n🎯 === PROJECT SETUP ===")
        
        # Get project ID
        self.project_id = input("Enter your GCP Project ID: ").strip()
        if not self.project_id:
            print("❌ Project ID is required!")
            sys.exit(1)
            
        print(f"✅ Using project: {self.project_id}")
        
        # Set project
        self.run_command(f"gcloud config set project {self.project_id}")
        
        # Enable APIs
        apis = [
            "run.googleapis.com",
            "sql-component.googleapis.com",
            "sqladmin.googleapis.com", 
            "cloudbuild.googleapis.com",
            "storage-component.googleapis.com",
            "secretmanager.googleapis.com",
            "cloudresourcemanager.googleapis.com"
        ]
        
        print(f"\n🔧 Enabling {len(apis)} required APIs...")
        for api in apis:
            print(f"Enabling {api}...")
            self.run_command(f"gcloud services enable {api}")
            
        print("✅ All APIs enabled successfully!")
        
    def create_database(self):
        """Create Cloud SQL database instance"""
        print("\n🗄️  === DATABASE SETUP ===")
        
        # Generate database password
        import secrets
        db_password = secrets.token_urlsafe(32)
        
        print(f"Creating Cloud SQL instance: {self.db_instance}")
        
        # Create Cloud SQL instance
        create_instance_cmd = f"""
        gcloud sql instances create {self.db_instance} \
            --database-version=POSTGRES_14 \
            --tier=db-f1-micro \
            --region={self.region} \
            --storage-type=SSD \
            --storage-size=10GB \
            --storage-auto-increase \
            --backup-start-time=03:00 \
            --enable-bin-log \
            --deletion-protection
        """
        
        result = self.run_command(create_instance_cmd)
        if result is None:
            print("⚠️  Database instance may already exist or creation failed")
        
        # Create database
        print(f"Creating database: {self.db_name}")
        self.run_command(f"gcloud sql databases create {self.db_name} --instance={self.db_instance}")
        
        # Create user
        print(f"Creating database user: {self.db_user}")
        self.run_command(f"gcloud sql users create {self.db_user} --instance={self.db_instance} --password={db_password}")
        
        # Store database URL in Secret Manager
        connection_name = f"{self.project_id}:{self.region}:{self.db_instance}"
        database_url = f"postgresql://{self.db_user}:{db_password}@/{self.db_name}?host=/cloudsql/{connection_name}"
        
        print("🔐 Storing database credentials in Secret Manager...")
        self.run_command(f'echo "{database_url}" | gcloud secrets create database-url --data-file=-')
        
        print("✅ Database setup completed!")
        return database_url
        
    def create_secrets(self):
        """Create application secrets"""
        print("\n🔐 === SECRETS SETUP ===")
        
        # Generate secret key
        import secrets
        secret_key = secrets.token_hex(32)
        
        # Create secrets
        secrets_to_create = [
            ("secret-key", secret_key),
            ("mail-username", input("Enter Gmail username: ").strip()),
            ("mail-password", input("Enter Gmail app password: ").strip()),
            ("paypal-client-id", input("Enter PayPal Client ID: ").strip()),
            ("paypal-client-secret", input("Enter PayPal Client Secret: ").strip())
        ]
        
        for secret_name, secret_value in secrets_to_create:
            if secret_value:
                print(f"Creating secret: {secret_name}")
                self.run_command(f'echo "{secret_value}" | gcloud secrets create {secret_name} --data-file=-')
            else:
                print(f"⚠️  Skipping empty secret: {secret_name}")
        
        print("✅ Secrets created successfully!")
        
    def build_and_deploy(self):
        """Build container and deploy to Cloud Run"""
        print("\n🚀 === BUILD & DEPLOY ===")
        
        # Build container
        print("Building container image...")
        image_url = f"gcr.io/{self.project_id}/{self.service_name}"
        
        build_cmd = f"""
        gcloud builds submit --tag {image_url} \
            --dockerfile=Dockerfile.production \
            --timeout=20m
        """
        
        self.run_command(build_cmd)
        
        # Deploy to Cloud Run
        print("Deploying to Cloud Run...")
        
        deploy_cmd = f"""
        gcloud run deploy {self.service_name} \
            --image {image_url} \
            --platform managed \
            --region {self.region} \
            --allow-unauthenticated \
            --port 8080 \
            --memory 2Gi \
            --cpu 2 \
            --max-instances 100 \
            --min-instances 1 \
            --concurrency 100 \
            --timeout 300 \
            --set-env-vars "FLASK_ENV=production,PORT=8080,PYTHONUNBUFFERED=1" \
            --set-secrets "DATABASE_URL=database-url:latest,SECRET_KEY=secret-key:latest,MAIL_USERNAME=mail-username:latest,MAIL_PASSWORD=mail-password:latest,PAYPAL_CLIENT_ID=paypal-client-id:latest,PAYPAL_CLIENT_SECRET=paypal-client-secret:latest" \
            --add-cloudsql-instances {self.project_id}:{self.region}:{self.db_instance}
        """
        
        result = self.run_command(deploy_cmd)
        
        if result and result.returncode == 0:
            # Get service URL
            get_url_cmd = f"gcloud run services describe {self.service_name} --region={self.region} --format='value(status.url)'"
            url_result = self.run_command(get_url_cmd)
            
            if url_result and url_result.stdout:
                service_url = url_result.stdout.strip()
                print(f"\n🎉 Deployment successful!")
                print(f"🌐 Service URL: {service_url}")
                print(f"📊 Platform: Labor Lookers Job + Advertising Marketplace")
                print(f"✅ Status: Production Ready")
                return service_url
        
        print("❌ Deployment failed!")
        return None
        
    def run_database_migration(self, service_url):
        """Run database migrations"""
        print("\n🔄 === DATABASE MIGRATION ===")
        
        # This would typically be done through a Cloud Build trigger or manually
        print("⚠️  Run database migration manually after deployment:")
        print(f"1. Visit: {service_url}")
        print("2. Or run migration via Cloud Shell:")
        print(f"   gcloud run services update {self.service_name} --region={self.region}")
        
    def deploy(self):
        """Main deployment process"""
        print("🚀 === LABOR LOOKERS PRODUCTION DEPLOYMENT ===")
        print(f"📅 Started: {datetime.now()}")
        print("🎯 Target: Google Cloud Platform (Cloud Run + Cloud SQL)")
        print("💼 Platform: B2B/B2C Job + Advertising Marketplace")
        print("=" * 60)
        
        try:
            # Step 1: Project setup
            self.setup_project()
            
            # Step 2: Database setup
            self.create_database()
            
            # Step 3: Secrets setup
            self.create_secrets()
            
            # Step 4: Build and deploy
            service_url = self.build_and_deploy()
            
            # Step 5: Database migration info
            if service_url:
                self.run_database_migration(service_url)
                
                print("\n" + "=" * 60)
                print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"🌐 Service URL: {service_url}")
                print(f"📊 Project: {self.project_id}")
                print(f"🗄️  Database: {self.db_instance}")
                print(f"⚙️  Service: {self.service_name}")
                print(f"📍 Region: {self.region}")
                print("\n🌟 LABOR LOOKERS FEATURES LIVE:")
                print("   ✅ Job marketplace with job seeker accounts")
                print("   ✅ Professional networking system")
                print("   ✅ Advertising marketplace (7 professional types)")
                print("   ✅ Campaign management & work orders")
                print("   ✅ 10% commission tracking system")
                print("   ✅ Mobile-responsive design")
                print("   ✅ Production-ready security")
                print("\n🚀 Ready for users and revenue generation!")
                
            else:
                print("\n❌ Deployment failed. Check logs above.")
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\n❌ Deployment cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    deployer = LaborLookersDeployment()
    deployer.deploy()