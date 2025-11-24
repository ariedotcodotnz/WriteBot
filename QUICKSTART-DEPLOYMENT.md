# WriteBot Production Deployment - Quick Start

Get WriteBot running in production in under 15 minutes!

## Prerequisites

- A VM server with Ubuntu 20.04+ (4GB RAM minimum, 8GB recommended)
- SSH access to your server
- A GitHub account with this repository

## Step 1: Server Setup (5 minutes)

SSH into your server and run:

```bash
# Clone the repository
git clone https://github.com/yourusername/WriteBot.git /opt/writebot
cd /opt/writebot

# Run the setup script
sudo bash deploy/setup-server.sh
```

When prompted, enter your GitHub repository URL.

## Step 2: Configure Environment (2 minutes)

Edit the environment file:

```bash
sudo nano /opt/writebot/.env
```

Change these key settings:

```env
SECRET_KEY=<generate-with-command-below>
DATABASE_URL=sqlite:///instance/writebot.db
FLASK_ENV=production
```

Generate a secure secret key:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Save and exit (Ctrl+X, Y, Enter).

## Step 3: SSL Certificates (3 minutes)

### Option A: Self-Signed (Quick for testing)

```bash
cd /opt/writebot/deploy/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem
```

### Option B: Let's Encrypt (Recommended for production)

```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/writebot/deploy/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/writebot/deploy/ssl/key.pem
```

## Step 4: Deploy (5 minutes)

```bash
cd /opt/writebot
sudo bash deploy/deploy.sh
```

Wait for the deployment to complete. You'll see:
```
✓ Deployment completed successfully!
```

## Step 5: Create Admin User

```bash
docker exec -it writebot-app python webapp/init_db.py
```

Answer the prompts to create your admin account.

## Step 6: Access Your Application

Open your browser and go to:
- **HTTP**: `http://your-server-ip`
- **HTTPS**: `https://your-server-ip` (or your domain)

Login with the admin credentials you just created!

## GitHub Actions Setup (Optional - 10 minutes)

For automated deployments on every push to main:

### 1. Generate SSH Key

On your local machine:

```bash
ssh-keygen -t ed25519 -C "writebot-deploy" -f ~/.ssh/writebot-deploy
ssh-copy-id -i ~/.ssh/writebot-deploy.pub user@your-server-ip
cat ~/.ssh/writebot-deploy  # Copy this for next step
```

### 2. Add GitHub Secrets

Go to your repository on GitHub → Settings → Secrets and variables → Actions

Add these secrets:
- **SSH_PRIVATE_KEY**: The private key you just copied
- **SERVER_HOST**: Your server IP address or domain
- **SERVER_USER**: Your SSH username (usually `root` or `ubuntu`)

### 3. Enable Workflows

Go to Actions → Enable workflows

Now every push to `main` will automatically deploy to your server!

## Quick Commands

```bash
# View logs
docker-compose logs -f

# Restart application
docker-compose restart writebot

# Check status
docker-compose ps

# Health check
curl http://localhost/api/health

# Update application
cd /opt/writebot && git pull && sudo bash deploy/deploy.sh
```

## Troubleshooting

### Application won't start?
```bash
docker-compose logs writebot
```

### Can't access the website?
Check firewall:
```bash
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Database issues?
Reset database:
```bash
docker-compose down
docker-compose up -d
docker exec -it writebot-app python webapp/init_db.py
```

## Next Steps

- Set up automated backups (already configured in GitHub Actions)
- Configure a domain name and proper SSL
- Review the full [DEPLOYMENT.md](DEPLOYMENT.md) guide
- Monitor your application with `docker stats`

## Support

Need help? Check:
- Full documentation: [DEPLOYMENT.md](DEPLOYMENT.md)
- Application logs: `docker-compose logs -f`
- GitHub Issues: Create an issue in the repository

---

**Congratulations!** Your WriteBot application is now running in production! 🎉
