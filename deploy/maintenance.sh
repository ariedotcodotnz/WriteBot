#!/bin/bash
# WriteBot Maintenance Script
# Provides common maintenance tasks for production deployment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

APP_DIR="/opt/writebot"
BACKUP_DIR="/opt/writebot-backups"

# Function to show menu
show_menu() {
    echo ""
    echo "======================================"
    echo "WriteBot Maintenance Menu"
    echo "======================================"
    echo "1. View logs"
    echo "2. Restart services"
    echo "3. Backup database"
    echo "4. Restore database"
    echo "5. Check system health"
    echo "6. Update application"
    echo "7. Clean up old backups"
    echo "8. View resource usage"
    echo "9. Database migrations"
    echo "10. Create admin user"
    echo "0. Exit"
    echo "======================================"
    echo -n "Enter your choice: "
}

# View logs
view_logs() {
    log_info "Viewing application logs (Ctrl+C to exit)..."
    cd "$APP_DIR"
    docker-compose logs -f --tail=50
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    cd "$APP_DIR"
    docker-compose restart
    log_info "Services restarted successfully!"
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"

    docker exec writebot-app cp /app/webapp/instance/writebot.db /tmp/writebot_backup.db
    docker cp writebot-app:/tmp/writebot_backup.db "$BACKUP_DIR/writebot_${TIMESTAMP}.db"
    gzip "$BACKUP_DIR/writebot_${TIMESTAMP}.db"

    log_info "Backup created: $BACKUP_DIR/writebot_${TIMESTAMP}.db.gz"
}

# Restore database
restore_database() {
    log_info "Available backups:"
    ls -lh "$BACKUP_DIR" | grep writebot_

    echo -n "Enter backup filename to restore (e.g., writebot_20240101_120000.db.gz): "
    read BACKUP_FILE

    if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        log_error "Backup file not found!"
        return 1
    fi

    log_warn "This will replace your current database!"
    echo -n "Are you sure? (yes/no): "
    read CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled."
        return 0
    fi

    log_info "Restoring database from $BACKUP_FILE..."

    # Decompress if needed
    if [[ $BACKUP_FILE == *.gz ]]; then
        gunzip -c "$BACKUP_DIR/$BACKUP_FILE" > /tmp/restore.db
    else
        cp "$BACKUP_DIR/$BACKUP_FILE" /tmp/restore.db
    fi

    docker cp /tmp/restore.db writebot-app:/app/webapp/instance/writebot.db
    rm /tmp/restore.db

    log_info "Restarting application..."
    cd "$APP_DIR"
    docker-compose restart writebot

    log_info "Database restored successfully!"
}

# Check system health
check_health() {
    log_info "Checking system health..."

    echo ""
    echo "=== Container Status ==="
    cd "$APP_DIR"
    docker-compose ps

    echo ""
    echo "=== Application Health ==="
    curl -s http://localhost/api/health | python3 -m json.tool || echo "Health check failed"

    echo ""
    echo "=== Disk Space ==="
    df -h | grep -E "Filesystem|/dev/"

    echo ""
    echo "=== Memory Usage ==="
    free -h

    echo ""
}

# Update application
update_application() {
    log_warn "This will update the application to the latest version."
    echo -n "Continue? (yes/no): "
    read CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log_info "Update cancelled."
        return 0
    fi

    log_info "Updating application..."
    cd "$APP_DIR"

    # Create backup first
    backup_database

    # Pull latest code
    git pull origin main

    # Run deployment
    bash deploy/deploy.sh

    log_info "Update completed!"
}

# Clean up old backups
cleanup_backups() {
    log_info "Cleaning up backups older than 30 days..."
    find "$BACKUP_DIR" -name "writebot_*.db.gz" -mtime +30 -delete
    log_info "Cleanup completed!"
    ls -lh "$BACKUP_DIR"
}

# View resource usage
view_resources() {
    log_info "Resource usage:"

    echo ""
    echo "=== Docker Container Resources ==="
    docker stats --no-stream

    echo ""
    echo "=== Top Processes ==="
    ps aux | head -11

    echo ""
    echo "=== Network Connections ==="
    netstat -tuln | grep -E ":80|:443|:5000|:6379"
}

# Database migrations
database_migrations() {
    log_info "Database Migration Menu"
    echo "1. View current migration"
    echo "2. View migration history"
    echo "3. Create new migration"
    echo "4. Apply migrations"
    echo -n "Enter choice: "
    read MIGRATION_CHOICE

    case $MIGRATION_CHOICE in
        1)
            docker exec -it writebot-app alembic current
            ;;
        2)
            docker exec -it writebot-app alembic history
            ;;
        3)
            echo -n "Enter migration description: "
            read MIGRATION_DESC
            docker exec -it writebot-app alembic revision --autogenerate -m "$MIGRATION_DESC"
            ;;
        4)
            docker exec -it writebot-app alembic upgrade head
            ;;
        *)
            log_error "Invalid choice"
            ;;
    esac
}

# Create admin user
create_admin() {
    log_info "Creating admin user..."
    docker exec -it writebot-app python webapp/init_db.py
}

# Main loop
main() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root or with sudo"
        exit 1
    fi

    while true; do
        show_menu
        read CHOICE

        case $CHOICE in
            1) view_logs ;;
            2) restart_services ;;
            3) backup_database ;;
            4) restore_database ;;
            5) check_health ;;
            6) update_application ;;
            7) cleanup_backups ;;
            8) view_resources ;;
            9) database_migrations ;;
            10) create_admin ;;
            0)
                log_info "Goodbye!"
                exit 0
                ;;
            *)
                log_error "Invalid choice. Please try again."
                ;;
        esac

        echo ""
        echo -n "Press Enter to continue..."
        read
    done
}

main
