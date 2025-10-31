#!/usr/bin/env python3
"""
Simple Flask App Launcher for Local Testing
"""

import os
import sys
from pathlib import Path

# Set working directory
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

# Import and run the application
if __name__ == "__main__":
    try:
        from main import app
        print("🚀 Starting LaborLooker Platform...")
        print("🌐 Application will be available at: http://localhost:5000")
        print("📋 Terms of Service: http://localhost:5000/terms-of-service")
        print("🔒 Privacy Policy: http://localhost:5000/privacy-policy")
        print("📄 Contracts: http://localhost:5000/contracts")
        print("\n⏹️  Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Run the Flask application
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
        
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)