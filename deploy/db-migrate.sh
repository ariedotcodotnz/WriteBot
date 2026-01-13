#!/bin/bash
# WriteBot Database Migration Script
# Usage: ./deploy/db-migrate.sh [command] [--production]
#
# Commands:
#   upgrade     - Apply all pending migrations (default)
#   downgrade   - Revert last migration
#   current     - Show current migration version
#   history     - Show migration history
#   migrate     - Generate new migration from model changes
#   heads       - Show current head revisions

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
COMMAND="${1:-upgrade}"
PRODUCTION=false

for arg in "$@"; do
    case $arg in
        --production)
            PRODUCTION=true
            ;;
    esac
done

# Set container name based on environment
if [ "$PRODUCTION" = true ]; then
    CONTAINER="writebot-app-production"
    COMPOSE_FILE="docker-compose.production.yml"
else
    CONTAINER="writebot-app"
    COMPOSE_FILE="docker-compose.yml"
fi

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    log_error "Container ${CONTAINER} is not running!"
    exit 1
fi

case $COMMAND in
    upgrade)
        log_info "Applying pending migrations..."
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db upgrade
        log_info "Migrations applied successfully"
        ;;

    downgrade)
        log_warn "This will revert the last migration!"
        read -p "Are you sure? (y/N) " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db downgrade
            log_info "Migration reverted"
        else
            log_info "Cancelled"
        fi
        ;;

    current)
        log_info "Current migration version:"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db current
        ;;

    history)
        log_info "Migration history:"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db history
        ;;

    migrate)
        MESSAGE="${2:-Auto-generated migration}"
        log_info "Generating new migration: ${MESSAGE}"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db migrate -m "${MESSAGE}"
        log_warn "Review the generated migration before applying!"
        log_info "Apply with: $0 upgrade"
        ;;

    heads)
        log_info "Current head revisions:"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db heads
        ;;

    init)
        log_info "Initializing migrations directory..."
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db init
        ;;

    stamp)
        REVISION="${2:-head}"
        log_info "Stamping database with revision: ${REVISION}"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask db stamp ${REVISION}
        ;;

    check)
        log_info "Checking Flask-Migrate installation..."
        echo ""
        echo "1. Checking if Flask-Migrate is installed:"
        docker exec ${CONTAINER} pip show flask-migrate 2>/dev/null || log_error "Flask-Migrate NOT installed!"
        echo ""
        echo "2. Checking available Flask commands:"
        docker exec -e FLASK_APP=webapp.app:app ${CONTAINER} flask --help 2>&1 | grep -E "(db|Commands)" || true
        echo ""
        echo "3. Checking FLASK_APP environment:"
        docker exec ${CONTAINER} printenv | grep FLASK || log_warn "FLASK_APP not in container env"
        echo ""
        echo "4. Checking migrations directory:"
        docker exec ${CONTAINER} ls -la /app/migrations 2>/dev/null || log_error "Migrations directory not found!"
        ;;

    *)
        echo "Usage: $0 [command] [--production]"
        echo ""
        echo "Commands:"
        echo "  upgrade     Apply all pending migrations (default)"
        echo "  downgrade   Revert last migration"
        echo "  current     Show current migration version"
        echo "  history     Show migration history"
        echo "  migrate     Generate new migration from model changes"
        echo "  heads       Show current head revisions"
        echo "  init        Initialize migrations (first time only)"
        echo "  stamp       Mark database at specific revision"
        echo "  check       Verify Flask-Migrate installation and setup"
        echo ""
        echo "Options:"
        echo "  --production  Use production container"
        exit 1
        ;;
esac
