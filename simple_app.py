from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>LaborLooker - Live Test</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🚀 LaborLooker is Working!</h1>
        <p>Basic deployment successful on Google Cloud Platform</p>
        <p><a href="/health">Health Check</a></p>
        <hr>
        <p>This confirms the deployment pipeline is working.</p>
        <p>Full application will be deployed next.</p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {
        'status': 'healthy',
        'message': 'LaborLooker basic deployment working',
        'platform': 'Google App Engine'
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)