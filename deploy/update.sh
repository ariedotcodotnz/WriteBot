#!/bin/bash
# WriteBot Update Script for Docker Deployments
# Usage: ./deploy/update.sh [--production]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Determine compose file and container name
if [ "$1" == "--production" ]; then
    COMPOSE_FILE="docker-compose.production.yml"
    CONTAINER="writebot-app-production"
    log_info "Using production configuration"
else
    COMPOSE_FILE="docker-compose.yml"
    CONTAINER="writebot-app"
    log_info "Using development configuration"
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    log_error "Container ${CONTAINER} is not running!"
    log_info "Start it with: docker compose -f ${COMPOSE_FILE} up -d"
    exit 1
fi

log_info "Starting update process..."

# Step 1: Pull latest code (if using git)
if [ -d ".git" ]; then
    log_info "Pulling latest code..."
    git pull origin main
fi

# Step 2: Rebuild containers with new code
log_info "Rebuilding containers..."
docker compose -f ${COMPOSE_FILE} build

# Step 3: Run database migrations
log_info "Running database migrations..."
docker exec ${CONTAINER} flask db upgrade

# Step 4: Restart services with new code
log_info "Restarting services..."
docker compose -f ${COMPOSE_FILE} up -d

# Step 5: Verify health
log_info "Waiting for health check..."
sleep 10

if docker exec ${CONTAINER} python -c "import requests; r = requests.get('http://localhost:5000/api/health', timeout=5); exit(0 if r.status_code == 200 else 1)" 2>/dev/null; then
    log_info "Health check passed!"
else
    log_warn "Health check failed - check logs with: docker logs ${CONTAINER}"
fi

# Step 6: Restart Celery workers (if using job queue)
if docker ps --format '{{.Names}}' | grep -q "writebot-celery"; then
    log_info "Restarting Celery workers..."
    docker compose -f ${COMPOSE_FILE} restart celery-worker celery-beat 2>/dev/null || true
fi

log_info "Update complete!"
echo ""
echo "Useful commands:"
echo "  View logs:     docker logs -f ${CONTAINER}"
echo "  Check status:  docker compose -f ${COMPOSE_FILE} ps"
echo "  Run shell:     docker exec -it ${CONTAINER} bash"
