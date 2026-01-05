#!/bin/bash
# =============================================================================
# Redis LXC Container Setup Script
# =============================================================================
# Run this script INSIDE the Redis LXC container after starting it
#
# Usage:
#   pct enter 102  # Enter the container
#   chmod +x setup-redis-lxc.sh
#   ./setup-redis-lxc.sh

set -e

# =============================================================================
# CONFIGURATION - Customize these values
# =============================================================================

# Network configuration
BIND_ADDRESS="0.0.0.0"  # Listen on all interfaces

# Memory configuration (adjust based on container RAM)
MAX_MEMORY="256mb"
EVICTION_POLICY="allkeys-lru"

# Persistence configuration
ENABLE_AOF=true
ENABLE_RDB=true

# Security (optional - set password for Redis)
REDIS_PASSWORD=""  # Leave empty for no password (OK for internal network)

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
echo "  Redis LXC Setup for WriteBot"
echo "=============================================="
echo ""

# =============================================================================
# SYSTEM UPDATE
# =============================================================================
log_step "Updating system packages..."
apt-get update
apt-get upgrade -y

# =============================================================================
# INSTALL REDIS
# =============================================================================
log_step "Installing Redis..."

apt-get install -y redis-server redis-tools

log_info "Redis installed"

# =============================================================================
# CONFIGURE REDIS
# =============================================================================
log_step "Configuring Redis..."

REDIS_CONF="/etc/redis/redis.conf"

# Backup original config
cp ${REDIS_CONF} ${REDIS_CONF}.bak

# Configure bind address (listen on all interfaces)
log_info "Setting bind address to '${BIND_ADDRESS}'..."
sed -i "s/^bind 127.0.0.1.*/bind ${BIND_ADDRESS}/" ${REDIS_CONF}

# Disable protected mode (we use network isolation for security)
log_info "Disabling protected mode..."
sed -i "s/^protected-mode yes/protected-mode no/" ${REDIS_CONF}

# Configure memory limit
log_info "Setting max memory to ${MAX_MEMORY}..."
sed -i "s/^# maxmemory <bytes>/maxmemory ${MAX_MEMORY}/" ${REDIS_CONF}

# Configure eviction policy
log_info "Setting eviction policy to ${EVICTION_POLICY}..."
sed -i "s/^# maxmemory-policy.*/maxmemory-policy ${EVICTION_POLICY}/" ${REDIS_CONF}

# Configure persistence
if [ "$ENABLE_AOF" = true ]; then
    log_info "Enabling AOF persistence..."
    sed -i "s/^appendonly no/appendonly yes/" ${REDIS_CONF}
    sed -i "s/^# appendfsync everysec/appendfsync everysec/" ${REDIS_CONF}
fi

if [ "$ENABLE_RDB" = true ]; then
    log_info "Enabling RDB snapshots..."
    # Default RDB settings are usually fine
fi

# Configure password if set
if [ -n "$REDIS_PASSWORD" ]; then
    log_info "Setting Redis password..."
    sed -i "s/^# requirepass.*/requirepass ${REDIS_PASSWORD}/" ${REDIS_CONF}
fi

# Performance tuning
log_info "Applying performance tuning..."
sed -i "s/^# tcp-keepalive.*/tcp-keepalive 300/" ${REDIS_CONF}
sed -i "s/^tcp-backlog.*/tcp-backlog 511/" ${REDIS_CONF}

# Logging
sed -i "s/^loglevel.*/loglevel notice/" ${REDIS_CONF}

# =============================================================================
# ENABLE AND START SERVICE
# =============================================================================
log_step "Enabling Redis service..."
systemctl enable redis-server
systemctl restart redis-server

# =============================================================================
# VERIFICATION
# =============================================================================
log_step "Verifying installation..."

# Wait for Redis to start
sleep 2

# Check service status
if systemctl is-active --quiet redis-server; then
    log_info "Redis service is running"
else
    log_error "Redis service failed to start"
    journalctl -u redis-server --no-pager -n 20
    exit 1
fi

# Test connection
log_info "Testing Redis connection..."
REDIS_AUTH=""
if [ -n "$REDIS_PASSWORD" ]; then
    REDIS_AUTH="-a ${REDIS_PASSWORD}"
fi

PING_RESULT=$(redis-cli ${REDIS_AUTH} ping 2>/dev/null)
if [ "$PING_RESULT" = "PONG" ]; then
    log_info "Redis connection successful"
else
    log_error "Redis connection failed"
    exit 1
fi

# Get container IP
CONTAINER_IP=$(hostname -I | awk '{print $1}')

# Test network binding
log_info "Testing network binding..."
NETWORK_PING=$(redis-cli -h ${CONTAINER_IP} ${REDIS_AUTH} ping 2>/dev/null)
if [ "$NETWORK_PING" = "PONG" ]; then
    log_info "Network binding successful"
else
    log_warn "Network binding test failed - check firewall settings"
fi

# Show Redis info
log_info "Redis server info:"
redis-cli ${REDIS_AUTH} INFO server | grep -E "redis_version|uptime_in_seconds|tcp_port"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "  Redis Setup Complete!"
echo "=============================================="
echo ""
echo "CONNECTION DETAILS:"
echo "  Host:     ${CONTAINER_IP}"
echo "  Port:     6379"
if [ -n "$REDIS_PASSWORD" ]; then
echo "  Password: <configured>"
else
echo "  Password: <none>"
fi
echo ""
echo "REDIS URLS (for .env file):"
echo "  REDIS_HOST=${CONTAINER_IP}"
echo "  REDIS_PORT=6379"
echo ""
echo "  Rate Limiting: redis://${CONTAINER_IP}:6379/0"
echo "  Cache:         redis://${CONTAINER_IP}:6379/1"
echo "  Celery:        redis://${CONTAINER_IP}:6379/0"
echo ""
echo "TEST CONNECTION FROM DOCKER VM:"
echo "  redis-cli -h ${CONTAINER_IP} ping"
echo ""
echo "CONFIGURATION:"
echo "  Config file:    ${REDIS_CONF}"
echo "  Max memory:     ${MAX_MEMORY}"
echo "  Eviction:       ${EVICTION_POLICY}"
echo "  AOF enabled:    ${ENABLE_AOF}"
echo "  RDB enabled:    ${ENABLE_RDB}"
echo ""
echo "USEFUL COMMANDS:"
echo "  View logs:      journalctl -u redis-server -f"
echo "  Restart:        systemctl restart redis-server"
echo "  Status:         systemctl status redis-server"
echo "  Monitor:        redis-cli monitor"
echo "  Info:           redis-cli info"
echo ""
log_info "Redis is ready for WriteBot!"
