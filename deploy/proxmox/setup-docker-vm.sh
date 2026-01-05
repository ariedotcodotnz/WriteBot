#!/bin/bash
# =============================================================================
# Docker VM Setup Script with GPU Support
# =============================================================================
# Run this script INSIDE the Docker VM after installing Ubuntu
#
# Prerequisites:
#   - Ubuntu 22.04 installed with static IP (10.10.10.10)
#   - GPU passed through from Proxmox
#   - Internet connectivity
#
# Usage:
#   chmod +x setup-docker-vm.sh
#   sudo ./setup-docker-vm.sh

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

# NVIDIA Driver version (550+ recommended for RTX 5090/5080 Blackwell)
NVIDIA_DRIVER_VERSION="550"

# Application directory
APP_DIR="/opt/writebot"
BACKUP_DIR="/opt/writebot-backups"

# Git repository (update with your repo URL)
GIT_REPO="https://github.com/ariedotcodotnz/WriteBot.git"

# =============================================================================
# COLORS FOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================
echo ""
echo "=============================================="
echo "  Docker VM Setup for WriteBot"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo ./setup-docker-vm.sh)"
    exit 1
fi

# Check for GPU
log_step "Checking for NVIDIA GPU..."
if lspci | grep -i nvidia > /dev/null; then
    log_info "NVIDIA GPU detected:"
    lspci | grep -i nvidia
else
    log_warn "No NVIDIA GPU detected. GPU passthrough may not be configured correctly."
    read -p "Continue without GPU? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# =============================================================================
# SYSTEM UPDATE
# =============================================================================
log_step "Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# =============================================================================
# INSTALL NVIDIA DRIVERS
# =============================================================================
log_step "Installing NVIDIA drivers (version ${NVIDIA_DRIVER_VERSION})..."

# Install prerequisites
apt-get install -y software-properties-common build-essential dkms

# Add NVIDIA PPA
add-apt-repository -y ppa:graphics-drivers/ppa
apt-get update

# Install NVIDIA driver
DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-driver-${NVIDIA_DRIVER_VERSION}

log_info "NVIDIA driver ${NVIDIA_DRIVER_VERSION} installed"
log_warn "A REBOOT is required before the GPU will be available"

# =============================================================================
# INSTALL DOCKER
# =============================================================================
log_step "Installing Docker..."

# Install prerequisites
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add current user to docker group (if not root)
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker $SUDO_USER
    log_info "Added user '$SUDO_USER' to docker group"
fi

log_info "Docker installed successfully"

# =============================================================================
# INSTALL NVIDIA CONTAINER TOOLKIT
# =============================================================================
log_step "Installing NVIDIA Container Toolkit..."

# Add NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
apt-get update
apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
nvidia-ctk runtime configure --runtime=docker

# Restart Docker to apply changes
systemctl restart docker

log_info "NVIDIA Container Toolkit installed"

# =============================================================================
# INSTALL CLOUDFLARE TUNNEL (cloudflared)
# =============================================================================
log_step "Installing Cloudflare Tunnel (cloudflared)..."

# Download and install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
dpkg -i /tmp/cloudflared.deb
rm /tmp/cloudflared.deb

log_info "Cloudflare Tunnel installed"
log_info "Configure with: cloudflared tunnel login"

# =============================================================================
# INSTALL ADDITIONAL TOOLS
# =============================================================================
log_step "Installing additional tools..."

apt-get install -y \
    git \
    htop \
    curl \
    wget \
    jq \
    vim \
    net-tools \
    postgresql-client \
    redis-tools

log_info "Additional tools installed"

# =============================================================================
# CREATE APPLICATION DIRECTORIES
# =============================================================================
log_step "Creating application directories..."

mkdir -p ${APP_DIR}
mkdir -p ${BACKUP_DIR}

# Set ownership if running with sudo
if [ -n "$SUDO_USER" ]; then
    chown -R $SUDO_USER:$SUDO_USER ${APP_DIR}
    chown -R $SUDO_USER:$SUDO_USER ${BACKUP_DIR}
fi

log_info "Application directories created"

# =============================================================================
# CONFIGURE FIREWALL
# =============================================================================
log_step "Configuring firewall (UFW)..."

apt-get install -y ufw

# Reset and configure UFW
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22/tcp comment 'SSH'

# Allow Flask app (for Cloudflare Tunnel)
ufw allow 5000/tcp comment 'Flask/WriteBot'

# Enable firewall
ufw --force enable

log_info "Firewall configured"
ufw status verbose

# =============================================================================
# CONFIGURE SYSTEM LIMITS
# =============================================================================
log_step "Configuring system limits for Docker..."

# Increase file limits for Docker
cat >> /etc/security/limits.conf << EOF

# Docker container limits
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
EOF

# Configure sysctl for better performance
cat >> /etc/sysctl.conf << EOF

# Docker and network performance
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.max_map_count = 262144
EOF

sysctl -p

log_info "System limits configured"

# =============================================================================
# CLONE REPOSITORY (Optional)
# =============================================================================
read -p "Clone WriteBot repository now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_step "Cloning WriteBot repository..."

    if [ -d "${APP_DIR}/.git" ]; then
        log_warn "Repository already exists, pulling latest..."
        cd ${APP_DIR}
        git pull origin main
    else
        git clone ${GIT_REPO} ${APP_DIR}
    fi

    # Set ownership
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER ${APP_DIR}
    fi

    log_info "Repository cloned to ${APP_DIR}"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "  Docker VM Setup Complete!"
echo "=============================================="
echo ""
echo "IMPORTANT: REBOOT REQUIRED"
echo "  The NVIDIA drivers require a reboot to activate."
echo "  Run: sudo reboot"
echo ""
echo "AFTER REBOOT, VERIFY GPU:"
echo "  nvidia-smi"
echo "  docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi"
echo ""
echo "SETUP CLOUDFLARE TUNNEL:"
echo "  cloudflared tunnel login"
echo "  cloudflared tunnel create writebot"
echo "  cloudflared tunnel route dns writebot your-domain.com"
echo ""
echo "DEPLOY WRITEBOT:"
echo "  cd ${APP_DIR}"
echo "  cp .env.production.example .env"
echo "  nano .env  # Configure with PostgreSQL and Redis IPs"
echo "  ./deploy/proxmox/proxmox-deploy.sh"
echo ""
echo "DIRECTORIES:"
echo "  Application: ${APP_DIR}"
echo "  Backups:     ${BACKUP_DIR}"
echo ""
echo "NETWORK CONNECTIONS:"
echo "  PostgreSQL: 10.10.10.11:5432"
echo "  Redis:      10.10.10.12:6379"
echo ""
echo "USEFUL COMMANDS:"
echo "  GPU status:       nvidia-smi"
echo "  Docker status:    docker ps"
echo "  View logs:        docker compose -f docker-compose.production.yml logs -f"
echo ""
log_warn "Please reboot now: sudo reboot"
