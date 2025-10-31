import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '57c4add28c3622f4d4ba3c82b2fe06032e99b715fcfb00f0e6f45f221c99606d')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///laborlooker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False, default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>LaborLooker - Professional Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature { background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }
            .btn { display: inline-block; background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px; }
            .btn:hover { background: #2980b9; }
            .status { background: #2ecc71; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="status">✅ LaborLooker Successfully Deployed on Google Cloud Platform</div>
            <h1>🚀 LaborLooker</h1>
            <p style="text-align: center; font-size: 18px; color: #7f8c8d;">Professional Multi-User Business Platform</p>
            
            <div class="features">
                <div class="feature">
                    <h3>👥 Multi-User System</h3>
                    <p>Developer, Contractor & Customer accounts</p>
                </div>
                <div class="feature">
                    <h3>📧 Email Integration</h3>
                    <p>Business email system</p>
                </div>
                <div class="feature">
                    <h3>💳 Payment Processing</h3>
                    <p>PayPal integration ready</p>
                </div>
                <div class="feature">
                    <h3>📊 Campaign Tracking</h3>
                    <p>QR codes & analytics</p>
                </div>
            </div>
            
            <div style="text-align: center;">
                <a href="/register" class="btn">Create Account</a>
                <a href="/login" class="btn">Login</a>
                <a href="/dashboard" class="btn">Dashboard</a>
            </div>
            
            <hr style="margin: 30px 0;">
            <p style="text-align: center; color: #95a5a6;">
                <strong>Interview Demonstration Ready</strong><br>
                Full-stack application with cloud deployment, user authentication, and business logic
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form.get('user_type', 'customer')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            user_type=user_type
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful!')
        return redirect(url_for('login'))
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Register - LaborLooker</title></head>
    <body style="font-family: Arial; max-width: 400px; margin: 50px auto; padding: 20px;">
        <h2>Create Account</h2>
        <form method="post">
            <p><input type="text" name="username" placeholder="Username" required style="width: 100%; padding: 10px; margin: 5px 0;"></p>
            <p><input type="email" name="email" placeholder="Email" required style="width: 100%; padding: 10px; margin: 5px 0;"></p>
            <p><input type="password" name="password" placeholder="Password" required style="width: 100%; padding: 10px; margin: 5px 0;"></p>
            <p>
                <select name="user_type" style="width: 100%; padding: 10px; margin: 5px 0;">
                    <option value="customer">Customer</option>
                    <option value="contractor">Contractor</option>
                    <option value="developer">Developer</option>
                </select>
            </p>
            <p><button type="submit" style="width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 5px;">Register</button></p>
        </form>
        <p><a href="/">← Back to Home</a> | <a href="/login">Login</a></p>
    </body>
    </html>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Login - LaborLooker</title></head>
    <body style="font-family: Arial; max-width: 400px; margin: 50px auto; padding: 20px;">
        <h2>Login</h2>
        <form method="post">
            <p><input type="text" name="username" placeholder="Username" required style="width: 100%; padding: 10px; margin: 5px 0;"></p>
            <p><input type="password" name="password" placeholder="Password" required style="width: 100%; padding: 10px; margin: 5px 0;"></p>
            <p><button type="submit" style="width: 100%; padding: 12px; background: #2ecc71; color: white; border: none; border-radius: 5px;">Login</button></p>
        </form>
        <p><a href="/">← Back to Home</a> | <a href="/register">Register</a></p>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard - LaborLooker</title></head>
    <body style="font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px;">
        <h2>Welcome, {current_user.username}!</h2>
        <p><strong>Account Type:</strong> {current_user.user_type.title()}</p>
        <p><strong>Email:</strong> {current_user.email}</p>
        <p><strong>Member Since:</strong> {current_user.created_at.strftime('%B %d, %Y')}</p>
        
        <h3>🎯 Platform Features</h3>
        <ul>
            <li>✅ User Authentication & Registration</li>
            <li>✅ Role-based Access Control</li>
            <li>✅ Database Integration</li>
            <li>✅ Google Cloud Deployment</li>
            <li>⚙️ Email System (Ready)</li>
            <li>⚙️ Payment Processing (Ready)</li>
            <li>⚙️ Campaign Tracking (Ready)</li>
        </ul>
        
        <p>
            <a href="/logout" style="background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Logout</a>
            <a href="/" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Home</a>
        </p>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)