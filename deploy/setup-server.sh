#!/bin/bash
# WriteBot Server Initial Setup Script
# Run this once on a fresh VM to prepare it for deployment

set -e  # Exit on error

echo "======================================"
echo "WriteBot Server Setup Script"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Update system
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
log_info "Installing required packages..."
apt-get install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    ufw \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
log_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    log_info "Docker installed successfully"
else
    log_info "Docker is already installed"
fi

# Install Docker Compose (standalone)
log_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log_info "Docker Compose installed successfully"
else
    log_info "Docker Compose is already installed"
fi

# Start Docker service
log_info "Starting Docker service..."
systemctl start docker
systemctl enable docker

# Configure firewall
log_info "Configuring firewall..."
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw status

# Create application directory
log_info "Creating application directory..."
mkdir -p /opt/writebot
mkdir -p /opt/writebot-backups

# Clone repository (if git URL is provided)
read -p "Enter GitHub repository URL (or press Enter to skip): " REPO_URL
if [ ! -z "$REPO_URL" ]; then
    log_info "Cloning repository..."
    cd /opt
    if [ -d "/opt/writebot/.git" ]; then
        log_warn "Repository already exists, skipping clone"
    else
        git clone "$REPO_URL" writebot
    fi
fi

# Create .env file
log_info "Creating environment file..."
cd /opt/writebot
if [ ! -f ".env" ]; then
    cp .env.example .env

    # Generate secret key
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    sed -i "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" .env

    log_info ".env file created. Please edit it with your production settings:"
    log_info "nano /opt/writebot/.env"
else
    log_warn ".env file already exists, skipping creation"
fi

# Create SSL directory
log_info "Creating SSL directory..."
mkdir -p /opt/writebot/deploy/ssl

log_info "======================================"
log_info "Server setup completed!"
log_info "======================================"
log_info ""
log_info "Next steps:"
log_info "1. Edit the .env file: nano /opt/writebot/.env"
log_info "2. Add SSL certificates to: /opt/writebot/deploy/ssl/"
log_info "   - cert.pem (certificate)"
log_info "   - key.pem (private key)"
log_info "3. Run the deployment script: /opt/writebot/deploy/deploy.sh"
log_info ""
log_info "To set up automatic deployments from GitHub:"
log_info "1. Generate an SSH key: ssh-keygen -t ed25519 -C 'writebot-deploy'"
log_info "2. Add the public key to GitHub as a deploy key"
log_info "3. Configure GitHub Actions with your server details"
log_info ""
