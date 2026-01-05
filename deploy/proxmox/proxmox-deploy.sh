#!/bin/bash
# =============================================================================
# WriteBot Proxmox Deployment Script
# =============================================================================
# Deploy WriteBot on Proxmox Docker VM with GPU support
#
# Workflow: Git Pull -> Docker Build -> Database Migration -> Start Services
#
# Usage:
#   cd /opt/writebot
#   sudo ./deploy/proxmox/proxmox-deploy.sh
#
# Options:
#   --no-build      Skip Docker build (use existing image)
#   --no-pull       Skip git pull
#   --no-migrate    Skip database migrations
#   --force         Force rebuild without cache
#   --celery        Include Celery worker
#   --help          Show this help message

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================
APP_NAME="writebot"
APP_DIR="/opt/writebot"
BACKUP_DIR="/opt/writebot-backups"
COMPOSE_FILE="docker-compose.production.yml"
LOG_FILE="${APP_DIR}/deploy.log"

# Detect docker compose command (v2 plugin vs v1 standalone)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "Error: Neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

# Deployment options (can be overridden by flags)
DO_GIT_PULL=true
DO_BUILD=true
DO_MIGRATE=true
BUILD_NO_CACHE=false
INCLUDE_CELERY=false

# Timestamp for backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# =============================================================================
# COLORS FOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a ${LOG_FILE}; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a ${LOG_FILE}; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a ${LOG_FILE}; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1" | tee -a ${LOG_FILE}; }
log_debug() { echo -e "${CYAN}[DEBUG]${NC} $1" >> ${LOG_FILE}; }

# =============================================================================
# PARSE COMMAND LINE ARGUMENTS
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-build)
            DO_BUILD=false
            shift
            ;;
        --no-pull)
            DO_GIT_PULL=false
            shift
            ;;
        --no-migrate)
            DO_MIGRATE=false
            shift
            ;;
        --force)
            BUILD_NO_CACHE=true
            shift
            ;;
        --celery)
            INCLUDE_CELERY=true
            shift
            ;;
        --help)
            echo "WriteBot Proxmox Deployment Script"
            echo ""
            echo "Usage: sudo ./deploy/proxmox/proxmox-deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-build      Skip Docker build (use existing image)"
            echo "  --no-pull       Skip git pull"
            echo "  --no-migrate    Skip database migrations"
            echo "  --force         Force rebuild without cache"
            echo "  --celery        Include Celery worker for background tasks"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            log_info "Use --help for usage information"
            exit 1
            ;;
    esac
done

# =============================================================================
# SCRIPT START
# =============================================================================
echo "" | tee -a ${LOG_FILE}
echo "==============================================================================" | tee -a ${LOG_FILE}
echo "  WriteBot Proxmox Deployment" | tee -a ${LOG_FILE}
echo "  $(date)" | tee -a ${LOG_FILE}
echo "==============================================================================" | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================
log_step "Running pre-flight checks..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo ./deploy/proxmox/proxmox-deploy.sh)"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "${APP_DIR}/${COMPOSE_FILE}" ]; then
    log_error "Compose file not found: ${APP_DIR}/${COMPOSE_FILE}"
    log_error "Make sure you're deploying from the correct directory"
    exit 1
fi

# Change to app directory
cd ${APP_DIR}
log_debug "Working directory: $(pwd)"

# Check for .env file
if [ ! -f ".env" ]; then
    log_error ".env file not found!"
    log_info "Create from template: cp .env.production.example .env"
    log_info "Then edit with your configuration: nano .env"
    exit 1
fi

# Validate required environment variables
log_info "Validating environment configuration..."
source .env

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "CHANGE_ME_generate_with_python_secrets_token_hex_32" ]; then
    log_error "SECRET_KEY is not set or still has default value"
    log_info "Generate a new key: python -c 'import secrets; print(secrets.token_hex(32))'"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "CHANGE_ME_your_secure_postgresql_password" ]; then
    log_error "POSTGRES_PASSWORD is not set or still has default value"
    exit 1
fi

# Check GPU availability
log_info "Checking GPU availability..."
if nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
    log_info "GPU detected: ${GPU_INFO}"
else
    log_warn "GPU not available. Make sure NVIDIA drivers are installed."
    read -p "Continue without GPU? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check connectivity to PostgreSQL
log_info "Checking PostgreSQL connectivity..."
POSTGRES_HOST=${POSTGRES_HOST:-10.10.10.11}
if timeout 5 bash -c "echo > /dev/tcp/${POSTGRES_HOST}/5432" 2>/dev/null; then
    log_info "PostgreSQL is reachable at ${POSTGRES_HOST}:5432"
else
    log_warn "Cannot reach PostgreSQL at ${POSTGRES_HOST}:5432"
    log_warn "Make sure the PostgreSQL LXC container is running"
fi

# Check connectivity to Redis
log_info "Checking Redis connectivity..."
REDIS_HOST=${REDIS_HOST:-10.10.10.12}
if timeout 5 bash -c "echo > /dev/tcp/${REDIS_HOST}/6379" 2>/dev/null; then
    log_info "Redis is reachable at ${REDIS_HOST}:6379"
else
    log_warn "Cannot reach Redis at ${REDIS_HOST}:6379"
    log_warn "Make sure the Redis LXC container is running"
fi

log_info "Pre-flight checks completed"

# =============================================================================
# BACKUP
# =============================================================================
log_step "Creating backup..."

mkdir -p ${BACKUP_DIR}

# Backup .env file
cp .env "${BACKUP_DIR}/.env_${TIMESTAMP}"
log_info "Environment file backed up to ${BACKUP_DIR}/.env_${TIMESTAMP}"

# Backup any local changes
if [ -d ".git" ] && [ -n "$(git status --porcelain)" ]; then
    log_warn "Uncommitted changes detected, creating stash..."
    git stash save "Auto-stash before deployment ${TIMESTAMP}" || true
fi

# =============================================================================
# GIT PULL
# =============================================================================
if [ "$DO_GIT_PULL" = true ]; then
    log_step "Pulling latest code from repository..."

    if [ -d ".git" ]; then
        # Get current branch
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        log_info "Current branch: ${CURRENT_BRANCH}"

        # Fetch and pull
        git fetch origin
        git pull origin ${CURRENT_BRANCH}

        # Show latest commit
        LATEST_COMMIT=$(git log -1 --pretty=format:"%h - %s (%cr)")
        log_info "Latest commit: ${LATEST_COMMIT}"
    else
        log_warn "Not a git repository. Skipping git pull."
    fi
else
    log_info "Skipping git pull (--no-pull flag)"
fi

# =============================================================================
# STOP EXISTING CONTAINERS
# =============================================================================
log_step "Stopping existing containers..."

${DOCKER_COMPOSE} -f ${COMPOSE_FILE} down --remove-orphans 2>/dev/null || true
log_info "Existing containers stopped"

# =============================================================================
# DOCKER BUILD
# =============================================================================
if [ "$DO_BUILD" = true ]; then
    log_step "Building Docker images..."

    BUILD_ARGS=""
    if [ "$BUILD_NO_CACHE" = true ]; then
        BUILD_ARGS="--no-cache"
        log_info "Building without cache (--force flag)"
    fi

    # Build main application
    ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} build ${BUILD_ARGS} writebot

    # Build Celery worker if requested
    if [ "$INCLUDE_CELERY" = true ]; then
        log_info "Building Celery worker..."
        ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} --profile celery build ${BUILD_ARGS}
    fi

    log_info "Docker images built successfully"
else
    log_info "Skipping Docker build (--no-build flag)"
fi

# =============================================================================
# DATABASE MIGRATIONS
# =============================================================================
if [ "$DO_MIGRATE" = true ]; then
    log_step "Running database migrations..."

    # Run migrations in a temporary container
    ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} run --rm writebot python webapp/init_db.py --auto 2>&1 | tee -a ${LOG_FILE}

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_info "Database migrations completed"
    else
        log_warn "Migration returned non-zero exit code (may be OK if no migrations needed)"
    fi
else
    log_info "Skipping database migrations (--no-migrate flag)"
fi

# =============================================================================
# START SERVICES
# =============================================================================
log_step "Starting services..."

if [ "$INCLUDE_CELERY" = true ]; then
    log_info "Starting with Celery worker..."
    ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} --profile celery up -d
else
    ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} up -d writebot
fi

log_info "Services started"

# =============================================================================
# HEALTH CHECK
# =============================================================================
log_step "Running health checks..."

# Wait for containers to be ready
log_info "Waiting for services to initialize..."
sleep 10

# Check container status
CONTAINER_STATUS=$(${DOCKER_COMPOSE} -f ${COMPOSE_FILE} ps --format json 2>/dev/null | head -1)
if echo "$CONTAINER_STATUS" | grep -q "running"; then
    log_info "Containers are running"
else
    log_warn "Container status check returned unexpected result"
    ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} ps
fi

# Health check loop
MAX_RETRIES=12
RETRY_INTERVAL=5
HEALTH_URL="http://localhost:${APP_PORT:-5000}/api/health"

log_info "Checking application health at ${HEALTH_URL}..."

for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
        log_info "Health check passed!"
        HEALTH_RESPONSE=$(curl -s "${HEALTH_URL}")
        log_debug "Health response: ${HEALTH_RESPONSE}"
        break
    else
        if [ $i -eq $MAX_RETRIES ]; then
            log_error "Health check failed after ${MAX_RETRIES} attempts"
            log_error "Check logs: ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} logs"
            ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} logs --tail=50
            exit 1
        fi
        log_info "Waiting for application to start (attempt ${i}/${MAX_RETRIES})..."
        sleep ${RETRY_INTERVAL}
    fi
done

# =============================================================================
# CLEANUP
# =============================================================================
log_step "Cleaning up..."

# Remove old Docker images
log_info "Removing unused Docker images..."
docker image prune -f > /dev/null 2>&1

# Clean up old backups (keep last 10)
log_info "Cleaning up old backups..."
cd ${BACKUP_DIR}
ls -t .env_* 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
cd ${APP_DIR}

log_info "Cleanup completed"

# =============================================================================
# SUMMARY
# =============================================================================
echo "" | tee -a ${LOG_FILE}
echo "==============================================================================" | tee -a ${LOG_FILE}
echo "  Deployment Complete!" | tee -a ${LOG_FILE}
echo "==============================================================================" | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}

# Show container status
echo "CONTAINER STATUS:" | tee -a ${LOG_FILE}
${DOCKER_COMPOSE} -f ${COMPOSE_FILE} ps | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}

# Show GPU status
echo "GPU STATUS:" | tee -a ${LOG_FILE}
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | tee -a ${LOG_FILE} || echo "GPU info not available" | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}

# Show application info
echo "APPLICATION INFO:" | tee -a ${LOG_FILE}
echo "  URL:        http://localhost:${APP_PORT:-5000}" | tee -a ${LOG_FILE}
echo "  Health:     http://localhost:${APP_PORT:-5000}/api/health" | tee -a ${LOG_FILE}
echo "  Logs:       ${DOCKER_COMPOSE} -f ${COMPOSE_FILE} logs -f" | tee -a ${LOG_FILE}
echo "  Deploy log: ${LOG_FILE}" | tee -a ${LOG_FILE}
echo "" | tee -a ${LOG_FILE}

# Show git info
if [ -d ".git" ]; then
    echo "GIT INFO:" | tee -a ${LOG_FILE}
    echo "  Branch: $(git rev-parse --abbrev-ref HEAD)" | tee -a ${LOG_FILE}
    echo "  Commit: $(git log -1 --pretty=format:'%h - %s')" | tee -a ${LOG_FILE}
    echo "" | tee -a ${LOG_FILE}
fi

log_info "WriteBot is now running!"
log_info "Access via Cloudflare Tunnel or http://localhost:${APP_PORT:-5000}"
