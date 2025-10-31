#!/usr/bin/env python3
"""
Railway Deployment Script for LaborLooker Platform
Automates Docker build and Railway deployment
"""

import subprocess
import os
import sys
import time
from pathlib import Path

class RailwayDeployer:
    def __init__(self):
        self.project_path = Path(__file__).parent
        self.image_name = "laborlooker"
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def run_command(self, command, description, check=True):
        """Run a command and log the result"""
        self.log(f"Running: {description}")
        self.log(f"Command: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, check=check, capture_output=True, text=True, cwd=self.project_path)
            if result.stdout:
                self.log(f"Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Error: {e.stderr.strip()}", "ERROR")
            return False
    
    def check_requirements(self):
        """Check if Docker and Railway CLI are installed"""
        self.log("🔍 Checking deployment requirements...")
        
        # Check Docker
        if not self.run_command(["docker", "--version"], "Checking Docker installation", check=False):
            self.log("❌ Docker is not installed. Please install Docker Desktop.", "ERROR")
            return False
        self.log("✅ Docker is installed")
        
        # Check Railway CLI
        if not self.run_command(["railway", "--version"], "Checking Railway CLI", check=False):
            self.log("❌ Railway CLI is not installed. Installing...", "WARNING")
            if not self.install_railway_cli():
                return False
        self.log("✅ Railway CLI is installed")
        
        return True
    
    def install_railway_cli(self):
        """Install Railway CLI"""
        self.log("📦 Installing Railway CLI...")
        
        if os.name == 'nt':  # Windows
            return self.run_command(["npm", "install", "-g", "@railway/cli"], "Installing Railway CLI via npm")
        else:  # Unix/Linux/Mac
            return self.run_command(["sh", "-c", "curl -fsSL https://railway.app/install.sh | sh"], "Installing Railway CLI")
    
    def build_docker_image(self):
        """Build Docker image"""
        self.log("🐳 Building Docker image...")
        
        if not self.run_command(["docker", "build", "-t", self.image_name, "."], "Building Docker image"):
            return False
        
        self.log("✅ Docker image built successfully")
        return True
    
    def test_docker_image(self):
        """Test Docker image locally"""
        self.log("🧪 Testing Docker image locally...")
        
        # Stop any existing test container
        self.run_command(["docker", "stop", "laborlooker-test"], "Stopping existing test container", check=False)
        self.run_command(["docker", "rm", "laborlooker-test"], "Removing existing test container", check=False)
        
        # Start test container
        if not self.run_command([
            "docker", "run", "-d", 
            "--name", "laborlooker-test",
            "-p", "8080:8080",
            "-e", "SECRET_KEY=test-secret-key",
            "-e", "DATABASE_URL=sqlite:///instance/test.db",
            self.image_name
        ], "Starting test container"):
            return False
        
        # Wait for container to start
        self.log("⏳ Waiting for container to start...")
        time.sleep(10)
        
        # Test health endpoint
        try:
            import requests
            response = requests.get("http://localhost:8080/health", timeout=10)
            if response.status_code == 200:
                self.log("✅ Health check passed")
                success = True
            else:
                self.log(f"❌ Health check failed: {response.status_code}", "ERROR")
                success = False
        except Exception as e:
            self.log(f"❌ Health check failed: {e}", "ERROR")
            success = False
        
        # Cleanup
        self.run_command(["docker", "stop", "laborlooker-test"], "Stopping test container", check=False)
        self.run_command(["docker", "rm", "laborlooker-test"], "Removing test container", check=False)
        
        return success
    
    def check_railway_login(self):
        """Check if logged into Railway"""
        self.log("🔐 Checking Railway authentication...")
        
        result = subprocess.run(["railway", "whoami"], capture_output=True, text=True, cwd=self.project_path)
        if result.returncode != 0:
            self.log("❌ Not logged into Railway. Please login...", "WARNING")
            if not self.run_command(["railway", "login"], "Logging into Railway"):
                return False
        
        self.log("✅ Railway authentication confirmed")
        return True
    
    def deploy_to_railway(self):
        """Deploy to Railway"""
        self.log("🚂 Deploying to Railway...")
        
        if not self.run_command(["railway", "up"], "Deploying to Railway"):
            return False
        
        self.log("✅ Deployment to Railway completed")
        return True
    
    def show_deployment_info(self):
        """Show deployment information"""
        self.log("📊 Getting deployment information...")
        
        # Get service URL
        result = subprocess.run(["railway", "status"], capture_output=True, text=True, cwd=self.project_path)
        if result.returncode == 0:
            self.log("🌐 Deployment Status:")
            self.log(result.stdout)
    
    def deploy(self):
        """Main deployment process"""
        self.log("🚀 Starting LaborLooker Railway Deployment")
        self.log("=" * 50)
        
        steps = [
            ("Check Requirements", self.check_requirements),
            ("Build Docker Image", self.build_docker_image),
            ("Test Docker Image", self.test_docker_image),
            ("Check Railway Login", self.check_railway_login),
            ("Deploy to Railway", self.deploy_to_railway),
            ("Show Deployment Info", self.show_deployment_info)
        ]
        
        for step_name, step_func in steps:
            self.log(f"\n📋 Step: {step_name}")
            if not step_func():
                self.log(f"❌ Deployment failed at step: {step_name}", "ERROR")
                return False
        
        self.log("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
        self.log("🌐 Your LaborLooker platform is now live on Railway!")
        self.log("💡 Use 'railway logs' to monitor your application")
        
        return True

def main():
    """Main entry point"""
    deployer = RailwayDeployer()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--build-only":
        # Build and test only
        if deployer.check_requirements() and deployer.build_docker_image() and deployer.test_docker_image():
            print("✅ Docker image built and tested successfully!")
        else:
            print("❌ Build/test failed!")
            sys.exit(1)
    else:
        # Full deployment
        if not deployer.deploy():
            sys.exit(1)

if __name__ == "__main__":
    main()