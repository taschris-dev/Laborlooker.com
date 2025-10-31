# 🚀 Deployment Guide

This guide covers different deployment options for the Marketing Technology Platform.

## 🔧 Local Development

### Quick Start
```bash
# Install and run setup
python setup.py

# Start the application
python app.py
# OR use the generated startup script:
# Windows: start.bat
# Unix/Linux/Mac: ./start.sh
```

### Manual Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Start application
python app.py
```

## 🌐 Production Deployment

### Environment Variables
```bash
export SECRET_KEY="your-secure-secret-key-here"
export FLASK_ENV="production"
export DATABASE_URL="postgresql://user:pass@host:port/dbname"  # Optional
```

### Using Gunicorn (Recommended)
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app

# With SSL (recommended)
gunicorn -w 4 -b 0.0.0.0:443 --certfile=cert.pem --keyfile=key.pem app:app
```

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## ☁️ Cloud Platforms

### Heroku
```bash
# Install Heroku CLI
# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
heroku open
```

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway link
railway up
```

### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize and deploy
eb init
eb create production
eb deploy
```

### Google Cloud Platform
```bash
# Create app.yaml
echo "runtime: python311" > app.yaml

# Deploy
gcloud app deploy
```

### Azure App Service
```bash
# Create requirements.txt with all dependencies
# Deploy via Azure Portal or CLI
az webapp up --name your-app-name --resource-group your-rg
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN python -c "from app import app, db; app.app_context().push(); db.create_all()"

EXPOSE 5000

CMD ["python", "app.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=your-secret-key
      - FLASK_ENV=production
    volumes:
      - ./instance:/app/instance
```

### Build and Run
```bash
# Build image
docker build -t marketing-platform .

# Run container
docker run -p 5000:5000 marketing-platform

# Or with docker-compose
docker-compose up
```

## 🔒 Security Considerations

### Production Checklist
- [ ] Set strong SECRET_KEY
- [ ] Use HTTPS/SSL certificates
- [ ] Configure proper firewall rules
- [ ] Set up database backups
- [ ] Monitor application logs
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting
- [ ] Configure CORS if needed

### Environment Security
```bash
# Create .env file (never commit to git)
SECRET_KEY=your-very-long-random-secret-key
DATABASE_URL=your-database-connection-string
MAIL_PASSWORD=your-email-password
```

## 📊 Monitoring & Maintenance

### Log Management
```bash
# View application logs
tail -f /var/log/your-app/app.log

# With systemd
journalctl -u your-app -f
```

### Database Backup
```bash
# SQLite backup
cp instance/referral.db instance/backup-$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump your_database > backup-$(date +%Y%m%d).sql
```

### Health Checks
```python
# Add to app.py
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
```

## 🔧 Troubleshooting

### Common Issues

**Database Permission Errors**
```bash
# Fix SQLite permissions
chmod 664 instance/referral.db
chmod 775 instance/
```

**Port Already in Use**
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
```

**Module Import Errors**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Database Migration Issues**
```bash
# Reset database
rm instance/referral.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## 📈 Scaling

### Database Scaling
- Migrate from SQLite to PostgreSQL
- Add connection pooling
- Implement read replicas
- Use database caching (Redis)

### Application Scaling
- Use multiple Gunicorn workers
- Deploy across multiple servers
- Implement load balancing
- Add CDN for static assets

### Monitoring
- Application Performance Monitoring (APM)
- Error tracking (Sentry)
- Log aggregation (ELK stack)
- Uptime monitoring

---

**For interview demonstrations, local development is sufficient. For production use, follow the production deployment guidelines.**