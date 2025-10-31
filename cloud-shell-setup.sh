#!/bin/bash
# Quick LaborLooker Cloud Shell Setup Script

echo "🚀 Setting up LaborLooker in Google Cloud Shell"

# Create project directory
mkdir -p ~/laborlooker-app
cd ~/laborlooker-app

# Create app.yaml
cat > app.yaml << 'EOF'
runtime: python311

env_variables:
  SECRET_KEY: "57c4add28c3622f4d4ba3c82b2fe06032e99b715fcfb00f0e6f45f221c99606d"
  FLASK_ENV: "production"
  FLASK_DEBUG: "0"
  MAIL_USERNAME: "taschris.executive@gmail.com"
  MAIL_PASSWORD: "jekqe6-ceqkuv-seZbyg"
  PAYPAL_CLIENT_ID: "AWC4ekd4ChKsiY97ieWyVxAk2QKjMHAGblhTUlGTOtdWRrVtoninTD5v9CKi7G_e3pPpxCZdPp2C9d1i"
  PAYPAL_CLIENT_SECRET: "EG6BFP37JcCZPyq2q2NBsJWwWhUMUTRiiQ2I8FQCI6TK_5zuOuKeRUkUDvZIWCT1723K--xAlcTTRvAI"
  PAYPAL_MODE: "live"

handlers:
- url: /.*
  script: auto

automatic_scaling:
  min_instances: 1
  max_instances: 10
EOF

# Create minimal requirements.txt
cat > requirements.txt << 'EOF'
Flask==3.0.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Werkzeug==3.0.3
itsdangerous==2.2.0
gunicorn==21.2.0
EOF

# Create minimal main.py
cat > main.py << 'EOF'
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <h1>🚀 LaborLooker is Live!</h1>
    <p>Your referral platform is successfully deployed on Google Cloud Platform!</p>
    <p>This is a test deployment. Upload your full application files to complete the setup.</p>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
EOF

echo "✅ Files created. Now run:"
echo "gcloud config set project laborlooker-2024"
echo "gcloud app deploy"
echo "gcloud app browse"