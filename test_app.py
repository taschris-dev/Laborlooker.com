from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <h1>🚀 LaborLooker Test Deployment</h1>
    <p>If you can see this, the deployment is working!</p>
    <p>The full application will be deployed next.</p>
    '''

@app.route('/health')
def health():
    return {'status': 'ok', 'message': 'LaborLooker test is healthy'}

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)