#!/usr/bin/env python3
"""
HTTPS Local Development Server for LaborLooker Platform
Generates self-signed certificate and runs Flask with SSL
"""

import os
import ssl
import sys
import ipaddress
import datetime
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Set working directory
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

def generate_self_signed_cert():
    """Generate a self-signed certificate for localhost"""
    
    cert_dir = BASE_DIR / "ssl_certs"
    cert_dir.mkdir(exist_ok=True)
    
    cert_file = cert_dir / "localhost.crt"
    key_file = cert_dir / "localhost.key"
    
    if cert_file.exists() and key_file.exists():
        print("✅ SSL certificates already exist")
        return str(cert_file), str(key_file)
    
    print("🔐 Generating self-signed SSL certificate...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LaborLooker Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"✅ SSL certificate created: {cert_file}")
    print(f"✅ SSL private key created: {key_file}")
    
    return str(cert_file), str(key_file)

def start_https_server():
    """Start Flask application with HTTPS"""
    
    try:
        # Generate SSL certificate
        cert_file, key_file = generate_self_signed_cert()
        
        # Import Flask app
        from main import app
        
        print("🚀 Starting LaborLooker Platform with HTTPS...")
        print("🔒 Secure Application URLs:")
        print("   https://localhost:5000")
        print("   https://127.0.0.1:5000")
        print("")
        print("📋 Key Pages:")
        print("   📋 Terms of Service: https://localhost:5000/terms-of-service")
        print("   🔒 Privacy Policy: https://localhost:5000/privacy-policy")
        print("   📄 Contracts: https://localhost:5000/contracts")
        print("")
        print("⚠️  Browser Security Warning:")
        print("   Your browser will show 'Not Secure' for self-signed certificates")
        print("   Click 'Advanced' → 'Proceed to localhost (unsafe)' to continue")
        print("   This is SAFE for local development testing")
        print("")
        print("⏹️  Press Ctrl+C to stop the server")
        print("=" * 70)
        
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        
        # Run Flask with HTTPS
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            ssl_context=context,
            use_reloader=False  # Disable reloader with SSL
        )
        
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting HTTPS server: {e}")
        print("💡 Try running the regular HTTP server instead:")
        print("   python start_app.py")
        sys.exit(1)

if __name__ == "__main__":
    start_https_server()