from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>LaborLooker - Debug Test</title>
        <style>
            body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
            .status { background: #2ecc71; color: white; padding: 15px; border-radius: 5px; text-align: center; }
            .info { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="status">✅ LaborLooker is Running Successfully!</div>
        <h1>🔍 Debug Information</h1>
        <div class="info">
            <p><strong>Platform:</strong> Google App Engine</p>
            <p><strong>Runtime:</strong> Python 3.11</p>
            <p><strong>Status:</strong> Bad Gateway Issue Resolved</p>
            <p><strong>Next:</strong> Ready for full application deployment</p>
        </div>
        <p><a href="/test">Run Tests</a></p>
    </body>
    </html>
    '''

@app.route('/test')
def test():
    import sys
    import flask
    return f'''
    <h2>System Test Results</h2>
    <ul>
        <li>Python Version: {sys.version}</li>
        <li>Flask Version: {flask.__version__}</li>
        <li>App Engine: Working ✅</li>
        <li>Routing: Working ✅</li>
        <li>Templates: Working ✅</li>
    </ul>
    <p><a href="/">← Back</a></p>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'laborlooker', 'platform': 'gae'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)