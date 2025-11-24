#!/bin/bash
# WriteBot Deployment Script for VM Server

set -e  # Exit on error

echo "======================================"
echo "WriteBot Deployment Script"
echo "======================================"

# Configuration
APP_NAME="writebot"
APP_DIR="/opt/writebot"
BACKUP_DIR="/opt/writebot-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Create application directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    log_info "Creating application directory: $APP_DIR"
    mkdir -p "$APP_DIR"
fi

# Navigate to application directory
cd "$APP_DIR"

# Backup current installation if it exists
if [ -d "$APP_DIR/.git" ]; then
    log_info "Creating backup of current installation..."
    mkdir -p "$BACKUP_DIR"

    # Backup database
    if [ -f "$APP_DIR/webapp/instance/writebot.db" ]; then
        cp "$APP_DIR/webapp/instance/writebot.db" "$BACKUP_DIR/writebot_${TIMESTAMP}.db"
        log_info "Database backed up to $BACKUP_DIR/writebot_${TIMESTAMP}.db"
    fi

    # Backup .env file
    if [ -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env" "$BACKUP_DIR/.env_${TIMESTAMP}"
        log_info "Environment file backed up"
    fi
fi

# Pull latest code from git
log_info "Pulling latest code from repository..."
if [ -d "$APP_DIR/.git" ]; then
    git pull origin main
else
    log_warn "Not a git repository. Skipping git pull."
fi

# Load environment variables
if [ -f "$APP_DIR/.env" ]; then
    log_info "Loading environment variables..."
    export $(cat "$APP_DIR/.env" | grep -v '^#' | xargs)
else
    log_warn ".env file not found. Using default configuration."
fi

# Stop running containers
log_info "Stopping running containers..."
docker-compose down || true

# Pull latest images
log_info "Pulling latest Docker images..."
docker-compose pull || true

# Build application
log_info "Building application..."
docker-compose build --no-cache

# Run database migrations
log_info "Running database migrations..."
docker-compose run --rm writebot python webapp/init_db.py --auto || log_warn "Migration failed or not needed"

# Start services
log_info "Starting services..."
docker-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    log_info "Services are running!"
    docker-compose ps
else
    log_error "Services failed to start!"
    docker-compose logs --tail=50
    exit 1
fi

# Clean up old Docker images
log_info "Cleaning up old Docker images..."
docker image prune -f

# Show logs
log_info "Recent logs:"
docker-compose logs --tail=20

echo ""
log_info "======================================"
log_info "Deployment completed successfully!"
log_info "======================================"
log_info "Application is running at: http://localhost"
log_info "To view logs: docker-compose logs -f"
log_info "To stop: docker-compose down"
echo ""
