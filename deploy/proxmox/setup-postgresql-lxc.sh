#!/bin/bash
# =============================================================================
# PostgreSQL LXC Container Setup Script
# =============================================================================
# Run this script INSIDE the PostgreSQL LXC container after starting it
#
# Usage:
#   pct enter 101  # Enter the container
#   chmod +x setup-postgresql-lxc.sh
#   ./setup-postgresql-lxc.sh

set -e

# =============================================================================
# CONFIGURATION - Customize these values
# =============================================================================
POSTGRES_VERSION=15

# Database configuration
DB_NAME="writebot"
DB_USER="writebot"
DB_PASSWORD=""  # Will prompt if empty

# Network configuration
BIND_ADDRESS="0.0.0.0"  # Listen on all interfaces
ALLOWED_NETWORK="10.10.10.0/24"  # Allow connections from this subnet

# Performance tuning (adjust based on available RAM)
SHARED_BUFFERS="512MB"
EFFECTIVE_CACHE_SIZE="1536MB"
WORK_MEM="16MB"
MAINTENANCE_WORK_MEM="128MB"

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
# SCRIPT START
# =============================================================================
echo ""
echo "=============================================="
echo "  PostgreSQL LXC Setup for WriteBot"
echo "=============================================="
echo ""

# =============================================================================
# GET DATABASE PASSWORD
# =============================================================================
if [ -z "$DB_PASSWORD" ]; then
    while true; do
        read -sp "Enter password for database user '${DB_USER}': " DB_PASSWORD
        echo
        read -sp "Confirm password: " DB_PASSWORD_CONFIRM
        echo
        if [ "$DB_PASSWORD" = "$DB_PASSWORD_CONFIRM" ]; then
            if [ ${#DB_PASSWORD} -lt 8 ]; then
                log_error "Password must be at least 8 characters"
                continue
            fi
            break
        else
            log_error "Passwords do not match. Try again."
        fi
    done
fi

# =============================================================================
# SYSTEM UPDATE
# =============================================================================
log_step "Updating system packages..."
apt-get update
apt-get upgrade -y

# =============================================================================
# INSTALL POSTGRESQL
# =============================================================================
log_step "Installing PostgreSQL ${POSTGRES_VERSION}..."

# Install PostgreSQL
apt-get install -y postgresql-${POSTGRES_VERSION} postgresql-contrib-${POSTGRES_VERSION}

log_info "PostgreSQL ${POSTGRES_VERSION} installed"

# =============================================================================
# CONFIGURE POSTGRESQL
# =============================================================================
log_step "Configuring PostgreSQL..."

PG_CONF="/etc/postgresql/${POSTGRES_VERSION}/main/postgresql.conf"
PG_HBA="/etc/postgresql/${POSTGRES_VERSION}/main/pg_hba.conf"

# Backup original configs
cp ${PG_CONF} ${PG_CONF}.bak
cp ${PG_HBA} ${PG_HBA}.bak

# Configure listen_addresses
log_info "Setting listen_addresses to '${BIND_ADDRESS}'..."
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '${BIND_ADDRESS}'/" ${PG_CONF}

# Performance tuning
log_info "Applying performance tuning..."
sed -i "s/^shared_buffers = .*/shared_buffers = ${SHARED_BUFFERS}/" ${PG_CONF}
sed -i "s/^#effective_cache_size = .*/effective_cache_size = ${EFFECTIVE_CACHE_SIZE}/" ${PG_CONF}
sed -i "s/^#work_mem = .*/work_mem = ${WORK_MEM}/" ${PG_CONF}
sed -i "s/^#maintenance_work_mem = .*/maintenance_work_mem = ${MAINTENANCE_WORK_MEM}/" ${PG_CONF}

# Enable logging
sed -i "s/^#log_statement = .*/log_statement = 'ddl'/" ${PG_CONF}
sed -i "s/^#log_min_duration_statement = .*/log_min_duration_statement = 1000/" ${PG_CONF}

# Configure client authentication (pg_hba.conf)
log_info "Configuring client authentication..."
cat >> ${PG_HBA} << EOF

# WriteBot application access
# Allow connections from the Proxmox network
host    ${DB_NAME}      ${DB_USER}      ${ALLOWED_NETWORK}      scram-sha-256
EOF

# =============================================================================
# CREATE DATABASE AND USER
# =============================================================================
log_step "Creating database and user..."

# Restart PostgreSQL to apply config changes
systemctl restart postgresql

# Create user and database
sudo -u postgres psql << EOF
-- Create user with password
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';

-- Create database owned by user
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Connect to database and set up schema permissions
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
EOF

log_info "Database '${DB_NAME}' and user '${DB_USER}' created"

# =============================================================================
# ENABLE AND START SERVICE
# =============================================================================
log_step "Enabling PostgreSQL service..."
systemctl enable postgresql
systemctl restart postgresql

# =============================================================================
# VERIFICATION
# =============================================================================
log_step "Verifying installation..."

# Check service status
if systemctl is-active --quiet postgresql; then
    log_info "PostgreSQL service is running"
else
    log_error "PostgreSQL service failed to start"
    journalctl -u postgresql --no-pager -n 20
    exit 1
fi

# Test connection
log_info "Testing database connection..."
PGPASSWORD="${DB_PASSWORD}" psql -h localhost -U ${DB_USER} -d ${DB_NAME} -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_info "Database connection successful"
else
    log_error "Database connection failed"
    exit 1
fi

# Get container IP
CONTAINER_IP=$(hostname -I | awk '{print $1}')

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "  PostgreSQL Setup Complete!"
echo "=============================================="
echo ""
echo "CONNECTION DETAILS:"
echo "  Host:     ${CONTAINER_IP}"
echo "  Port:     5432"
echo "  Database: ${DB_NAME}"
echo "  Username: ${DB_USER}"
echo "  Password: <the password you entered>"
echo ""
echo "CONNECTION STRING (for .env file):"
echo "  DATABASE_URL=postgresql://${DB_USER}:<password>@${CONTAINER_IP}:5432/${DB_NAME}"
echo ""
echo "TEST CONNECTION FROM DOCKER VM:"
echo "  psql -h ${CONTAINER_IP} -U ${DB_USER} -d ${DB_NAME}"
echo ""
echo "CONFIGURATION FILES:"
echo "  Main config:    ${PG_CONF}"
echo "  Auth config:    ${PG_HBA}"
echo "  Backups:        ${PG_CONF}.bak, ${PG_HBA}.bak"
echo ""
echo "USEFUL COMMANDS:"
echo "  View logs:      journalctl -u postgresql -f"
echo "  Restart:        systemctl restart postgresql"
echo "  Status:         systemctl status postgresql"
echo ""
log_info "PostgreSQL is ready for WriteBot!"
