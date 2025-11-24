# Deployment Files

This directory contains all the necessary files for deploying WriteBot to production.

## Files Overview

### Configuration Files

- **nginx.conf**: NGINX reverse proxy configuration with SSL, caching, and security headers
- **ssl/**: Directory for SSL certificates (cert.pem, key.pem)

### Deployment Scripts

- **setup-server.sh**: Initial server setup script (run once on fresh VM)
- **deploy.sh**: Main deployment script (run for updates and deployments)

## Quick Start

### First-Time Setup

1. Run the server setup script:
   ```bash
   sudo bash deploy/setup-server.sh
   ```

2. Configure environment variables:
   ```bash
   nano .env
   ```

3. Add SSL certificates to `deploy/ssl/`

4. Run initial deployment:
   ```bash
   sudo bash deploy/deploy.sh
   ```

### Subsequent Deployments

Just run:
```bash
sudo bash deploy/deploy.sh
```

Or use GitHub Actions for automated deployment.

## File Details

### setup-server.sh

Prepares a fresh VM for running WriteBot:
- Installs Docker and Docker Compose
- Configures firewall
- Creates application directories
- Sets up initial .env file
- Provides SSL setup instructions

Run this script **once** when setting up a new server.

### deploy.sh

Handles deployment and updates:
- Backs up database and configuration
- Pulls latest code from Git
- Builds Docker images
- Runs database migrations
- Restarts services
- Performs health checks
- Cleans up old Docker images

Run this script whenever you want to deploy updates.

### nginx.conf

Production-ready NGINX configuration:
- HTTP to HTTPS redirect
- SSL/TLS configuration
- Security headers
- Gzip compression
- Rate limiting
- Static file caching
- Reverse proxy to Flask application

## SSL Certificates

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy to deploy directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deploy/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem deploy/ssl/key.pem
```

### Using Self-Signed Certificates (Development)

```bash
cd deploy/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem
```

## Environment Variables

Required in `.env` file:

```env
SECRET_KEY=your-secret-key
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/writebot.db  # or PostgreSQL URL
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
```

## Automated Deployment with GitHub Actions

See `../.github/workflows/deploy.yml` for automated deployment configuration.

Required GitHub secrets:
- `SSH_PRIVATE_KEY`: SSH key for server access
- `SERVER_HOST`: Server IP or domain
- `SERVER_USER`: SSH username

## Troubleshooting

### Deployment Script Fails

Check the logs:
```bash
docker-compose logs -f
```

### Services Won't Start

Verify configuration:
```bash
docker-compose config
```

### SSL Issues

Check certificate validity:
```bash
openssl x509 -in deploy/ssl/cert.pem -noout -dates
```

## Backup and Recovery

Backups are stored in `/opt/writebot-backups/`

To restore a backup:
```bash
docker cp /opt/writebot-backups/writebot_TIMESTAMP.db writebot-app:/app/webapp/instance/writebot.db
docker-compose restart writebot
```

## Support

For detailed documentation, see `../DEPLOYMENT.md`
