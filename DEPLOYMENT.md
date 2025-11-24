# WriteBot Production Deployment Guide

This guide covers deploying WriteBot to a production VM server with automated CI/CD using GitHub Actions.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Server Setup](#initial-server-setup)
- [GitHub Configuration](#github-configuration)
- [Deployment Methods](#deployment-methods)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Server Requirements

- Ubuntu 20.04 LTS or later (or compatible Linux distribution)
- Minimum 4GB RAM (8GB recommended for TensorFlow models)
- 20GB+ disk space
- SSH access with sudo privileges
- Domain name (optional, for HTTPS)

### Local Requirements

- Git installed
- SSH key pair for GitHub and server access
- Access to your GitHub repository

## Initial Server Setup

### 1. Run the Server Setup Script

SSH into your VM and run the automated setup script:

```bash
# Clone the repository (or download the setup script)
git clone https://github.com/yourusername/WriteBot.git /opt/writebot
cd /opt/writebot

# Run the setup script
sudo bash deploy/setup-server.sh
```

This script will:
- Install Docker and Docker Compose
- Configure the firewall (UFW)
- Create necessary directories
- Set up the application structure

### 2. Configure Environment Variables

Edit the `.env` file with your production settings:

```bash
sudo nano /opt/writebot/.env
```

Key variables to configure:

```env
# Flask Configuration
SECRET_KEY=your-super-secret-key-here  # Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
FLASK_ENV=production

# Database Configuration
# For PostgreSQL (recommended):
DATABASE_URL=postgresql://user:password@localhost:5432/writebot
# For SQLite (simpler):
DATABASE_URL=sqlite:///instance/writebot.db

# Server Configuration
HOST=0.0.0.0
PORT=5000

# Gunicorn Configuration
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
```

### 3. Set Up SSL Certificates

For HTTPS support, add your SSL certificates:

```bash
# If using Let's Encrypt:
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to the deploy directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/writebot/deploy/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/writebot/deploy/ssl/key.pem
```

Or for self-signed certificates (development/testing):

```bash
cd /opt/writebot/deploy/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem
```

### 4. Initial Deployment

Run the deployment script:

```bash
sudo bash /opt/writebot/deploy/deploy.sh
```

### 5. Create Admin User

After initial deployment, create an admin user:

```bash
docker exec -it writebot-app python webapp/init_db.py
```

## GitHub Configuration

### 1. Set Up Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

- `SSH_PRIVATE_KEY`: Your SSH private key for accessing the server
- `SERVER_HOST`: Your server's IP address or domain name
- `SERVER_USER`: SSH username (usually `root` or `ubuntu`)

### 2. Generate SSH Key for Deployment

On your local machine:

```bash
# Generate a dedicated deployment key
ssh-keygen -t ed25519 -C "writebot-deploy" -f ~/.ssh/writebot-deploy

# Copy the public key to your server
ssh-copy-id -i ~/.ssh/writebot-deploy.pub user@your-server-ip

# Copy the private key content for GitHub secrets
cat ~/.ssh/writebot-deploy
```

Add the private key content to GitHub as `SSH_PRIVATE_KEY`.

### 3. Create Production Environment

In your GitHub repository:

1. Go to Settings → Environments
2. Create a new environment called `production`
3. Add protection rules (optional):
   - Required reviewers
   - Wait timer
   - Deployment branches (main only)

## Deployment Methods

### Automatic Deployment (Recommended)

Every push to the `main` branch automatically triggers deployment:

1. Make your changes locally
2. Commit and push to main:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. GitHub Actions will automatically:
   - Run tests
   - Build Docker images
   - Deploy to your server
   - Run health checks

### Manual Deployment via GitHub Actions

1. Go to Actions → Deploy to Production
2. Click "Run workflow"
3. Select the branch to deploy
4. Click "Run workflow"

### Direct Server Deployment

SSH into your server and run:

```bash
cd /opt/writebot
sudo bash deploy/deploy.sh
```

## Deployment Workflows

### CI/CD Pipeline (`.github/workflows/ci.yml`)

Runs on every push and pull request:
- Runs Python tests
- Linting with flake8
- Checks database migrations
- Builds Docker images
- Security scanning with Trivy

### Deployment (`.github/workflows/deploy.yml`)

Runs on push to main branch:
- Deploys to production server
- Runs database migrations
- Restarts services
- Performs health checks

### Automated Backups (`.github/workflows/backup.yml`)

Runs daily at 2 AM UTC:
- Creates database backup
- Compresses and stores on server
- Keeps last 30 days of backups
- Uploads to GitHub artifacts (optional)

## Docker Architecture

The application uses Docker Compose with three services:

### writebot (Main Application)
- Python/Flask application
- Gunicorn WSGI server
- TensorFlow for handwriting synthesis
- Port: 5000

### redis (Caching & Rate Limiting)
- Redis 7 Alpine
- Persistent data storage
- Port: 6379

### nginx (Reverse Proxy)
- NGINX Alpine
- SSL/TLS termination
- Static file serving
- Rate limiting
- Ports: 80, 443

## Maintenance

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f writebot

# Last 100 lines
docker-compose logs --tail=100
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart writebot
```

### Updating the Application

```bash
cd /opt/writebot
git pull origin main
sudo bash deploy/deploy.sh
```

### Database Migrations

```bash
# Create a new migration
docker exec -it writebot-app alembic revision --autogenerate -m "Description"

# Apply migrations
docker exec -it writebot-app alembic upgrade head

# View migration history
docker exec -it writebot-app alembic history
```

### Manual Database Backup

```bash
# Backup database
docker exec writebot-app cp /app/webapp/instance/writebot.db /tmp/backup.db
docker cp writebot-app:/tmp/backup.db ./backup-$(date +%Y%m%d).db

# Restore database
docker cp ./backup-20240101.db writebot-app:/tmp/restore.db
docker exec writebot-app cp /tmp/restore.db /app/webapp/instance/writebot.db
docker-compose restart writebot
```

### Scaling

To handle more traffic, adjust the Gunicorn workers:

```bash
# Edit .env file
GUNICORN_WORKERS=8
GUNICORN_THREADS=4

# Restart application
docker-compose restart writebot
```

## Monitoring

### Health Check

```bash
curl http://your-server/api/health
```

Expected response:
```json
{
  "status": "ok",
  "model_ready": true,
  "version": 1
}
```

### Container Status

```bash
docker-compose ps
```

### Resource Usage

```bash
# Overall system
htop

# Docker containers
docker stats
```

## Troubleshooting

### Application Won't Start

1. Check logs:
   ```bash
   docker-compose logs writebot
   ```

2. Verify environment variables:
   ```bash
   docker-compose config
   ```

3. Check database connectivity:
   ```bash
   docker exec -it writebot-app python -c "from webapp.app import db; print(db)"
   ```

### Database Migration Issues

1. Check current migration version:
   ```bash
   docker exec -it writebot-app alembic current
   ```

2. Reset migrations (caution - data loss):
   ```bash
   docker exec -it writebot-app alembic downgrade base
   docker exec -it writebot-app alembic upgrade head
   ```

### SSL Certificate Issues

1. Check certificate expiration:
   ```bash
   openssl x509 -in /opt/writebot/deploy/ssl/cert.pem -noout -dates
   ```

2. Renew Let's Encrypt certificates:
   ```bash
   sudo certbot renew
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/writebot/deploy/ssl/cert.pem
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/writebot/deploy/ssl/key.pem
   docker-compose restart nginx
   ```

### High Memory Usage

TensorFlow models can use significant memory. To reduce:

1. Reduce Gunicorn workers in `.env`:
   ```env
   GUNICORN_WORKERS=2
   ```

2. Restart the application:
   ```bash
   docker-compose restart writebot
   ```

### Deployment Failures

1. Check GitHub Actions logs
2. Verify SSH connectivity:
   ```bash
   ssh user@your-server-ip
   ```
3. Ensure server has enough disk space:
   ```bash
   df -h
   ```

## Security Best Practices

1. **Change default SECRET_KEY**: Generate a strong random key
2. **Use HTTPS**: Always use SSL/TLS in production
3. **Keep dependencies updated**: Regularly update Docker images and Python packages
4. **Firewall configuration**: Only allow necessary ports (22, 80, 443)
5. **Database backups**: Regular automated backups (already configured)
6. **Monitor logs**: Check application and security logs regularly
7. **Rate limiting**: Configured in NGINX and Flask-Limiter
8. **Strong passwords**: Use strong passwords for admin users

## Performance Optimization

1. **Enable Redis caching**: Already configured in docker-compose
2. **Static file caching**: NGINX serves static files with long cache headers
3. **Gzip compression**: Enabled in NGINX
4. **Connection pooling**: Configure in DATABASE_URL if using PostgreSQL
5. **Worker tuning**: Adjust Gunicorn workers based on CPU cores (2-4 × CPU cores)

## Rollback Procedure

If a deployment fails:

1. Check backups directory:
   ```bash
   ls -lh /opt/writebot-backups/
   ```

2. Restore previous version:
   ```bash
   cd /opt/writebot
   git log  # Find previous commit
   git reset --hard <previous-commit-hash>
   sudo bash deploy/deploy.sh
   ```

3. Restore database if needed:
   ```bash
   # Find latest backup
   ls -lh /opt/writebot-backups/
   # Restore it
   docker cp /opt/writebot-backups/writebot_TIMESTAMP.db writebot-app:/app/webapp/instance/writebot.db
   docker-compose restart writebot
   ```

## Support

For issues or questions:
- Check the logs: `docker-compose logs -f`
- Review this documentation
- Check GitHub Issues
- Contact the development team

## Quick Reference

```bash
# Deploy
sudo bash /opt/writebot/deploy/deploy.sh

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop all
docker-compose down

# Start all
docker-compose up -d

# Database backup
docker exec writebot-app cp /app/webapp/instance/writebot.db /tmp/backup.db
docker cp writebot-app:/tmp/backup.db ./backup-$(date +%Y%m%d).db

# Health check
curl http://localhost/api/health
```
