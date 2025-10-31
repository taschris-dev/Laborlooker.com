#!/usr/bin/env python3
"""
Simple LaborLooker Deployment Script
Works with your existing GCP project: laborlooker-2024-476019
"""

import os
import sys
import subprocess
from datetime import datetime

def log(message, level="INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def run_command(command, check_output=False):
    """Run shell command with error handling"""
    try:
        log(f"Running: {command}")
        if check_output:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return result.strip()
        else:
            subprocess.check_call(command, shell=True)
            return True
    except subprocess.CalledProcessError as e:
        log(f"Command failed: {e}", "ERROR")
        return False

def main():
    """Main deployment function"""
    log("🚀 Starting LaborLooker deployment to your existing GCP project...")
    
    # Get current project
    try:
        project_id = run_command("gcloud config get-value project", check_output=True)
        log(f"Using GCP Project: {project_id}")
    except:
        log("❌ Could not get GCP project. Make sure gcloud is configured.", "ERROR")
        return False
    
    # Enable required APIs
    log("Enabling required Google Cloud APIs...")
    apis = [
        "cloudsql.googleapis.com",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "secretmanager.googleapis.com"
    ]
    
    for api in apis:
        log(f"Enabling {api}...")
        if not run_command(f"gcloud services enable {api}"):
            log(f"Failed to enable {api}", "ERROR")
            return False
    
    # Build and deploy to Cloud Run
    log("Building and deploying to Cloud Run...")
    
    # Use the existing Dockerfile.production
    if not run_command(f"gcloud builds submit --tag gcr.io/{project_id}/laborlooker"):
        log("Failed to build container", "ERROR")
        return False
    
    # Deploy to Cloud Run
    if not run_command(f"""
        gcloud run deploy laborlooker \\
            --image gcr.io/{project_id}/laborlooker \\
            --platform managed \\
            --region us-central1 \\
            --allow-unauthenticated \\
            --memory 2Gi \\
            --cpu 2 \\
            --max-instances 10 \\
            --set-env-vars="GOOGLE_CLOUD_PROJECT={project_id}"
    """):
        log("Failed to deploy to Cloud Run", "ERROR")
        return False
    
    # Get service URL
    service_url = run_command(f"""
        gcloud run services describe laborlooker \\
            --region us-central1 \\
            --format 'value(status.url)'
    """, check_output=True)
    
    log("🎉 Deployment completed successfully!", "SUCCESS")
    log(f"🌐 Your app is live at: {service_url}")
    log(f"🔍 Health check: {service_url}/health")
    
    return True

if __name__ == "__main__":
    print("🚀 Simple LaborLooker Deployment")
    print("=" * 50)
    
    confirm = input("Deploy to Cloud Run? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Deployment cancelled.")
        sys.exit(0)
    
    success = main()
    if success:
        print("\n✅ Deployment successful!")
    else:
        print("\n❌ Deployment failed!")
        sys.exit(1)