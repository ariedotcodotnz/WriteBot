# WriteBot Proxmox Production Deployment

Deploy WriteBot on Proxmox with GPU passthrough, PostgreSQL, and Redis.

## Architecture

```
                     Cloudflare Tunnel
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Proxmox Host                                │
│                                                                  │
│  ┌─────────────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Docker VM (100)   │  │ PostgreSQL   │  │    Redis     │    │
│  │   10.10.10.10       │  │ LXC (101)    │  │  LXC (102)   │    │
│  │                     │  │ 10.10.10.11  │  │ 10.10.10.12  │    │
│  │  ┌───────────────┐  │  │              │  │              │    │
│  │  │   WriteBot    │◄─┼──┼──────────────┼──┤              │    │
│  │  │   Container   │  │  │  Port 5432   │  │  Port 6379   │    │
│  │  │   Port 5000   │  │  │              │  │              │    │
│  │  └───────────────┘  │  └──────────────┘  └──────────────┘    │
│  │         │           │                                         │
│  │    ┌────▼────┐      │                                         │
│  │    │  GPU    │      │                                         │
│  │    │RTX 5090 │      │                                         │
│  │    └─────────┘      │                                         │
│  └─────────────────────┘                                         │
│                                                                  │
│                    Network: vmbr0 (10.10.10.0/24)                │
└──────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Type | IP | Resources | Purpose |
|-----------|------|-----|-----------|---------|
| Docker VM | QEMU VM | 10.10.10.10 | 8 CPU, 16GB RAM, 100GB | WriteBot app + GPU |
| PostgreSQL | LXC | 10.10.10.11 | 2 CPU, 2GB RAM, 20GB | Database |
| Redis | LXC | 10.10.10.12 | 1 CPU, 512MB RAM, 5GB | Cache & rate limiting |

## Prerequisites

- Proxmox VE 7.x or 8.x
- NVIDIA GPU (RTX 30/40/50 series recommended)
- IOMMU enabled for GPU passthrough
- Ubuntu 22.04 LXC template
- Internet connectivity

## Quick Start

### Already Have Docker VM Ready?

If you already have a Docker VM with GPU passthrough working:

```bash
# 1. Create PostgreSQL & Redis LXCs (on Proxmox host)
#    See "Setting Up LXC Containers" section below

# 2. On Docker VM - Clone and configure
cd /opt
sudo git clone https://github.com/ariedotcodotnz/WriteBot.git writebot
cd writebot
sudo cp .env.production.example .env
sudo nano .env  # Set SECRET_KEY, POSTGRES_PASSWORD, IPs

# 3. Deploy
sudo ./deploy/proxmox/proxmox-deploy.sh

# 4. Access at http://localhost:5000
```

### Starting From Scratch?

```bash
# 1. On Proxmox host - Create all infrastructure
./deploy/proxmox/proxmox-setup.sh

# 2. Configure each container (see sections below)

# 3. Deploy WriteBot
sudo ./deploy/proxmox/proxmox-deploy.sh
```

---

## Detailed Setup Guide

### 1. Setting Up LXC Containers

#### Create PostgreSQL LXC (on Proxmox host)

```bash
# Download template if needed
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Create container
pct create 101 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
    --hostname writebot-postgres \
    --memory 2048 --cores 2 \
    --rootfs local-lvm:20 \
    --net0 name=eth0,bridge=vmbr0,ip=10.10.10.11/24,gw=10.10.10.1 \
    --unprivileged 1 --onboot 1

# Start container
pct start 101
```

#### Configure PostgreSQL

```bash
# Enter container
pct enter 101

# Install PostgreSQL
apt update && apt install -y postgresql-15 postgresql-contrib-15

# Configure network access
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" \
    /etc/postgresql/15/main/postgresql.conf

echo "host writebot writebot 10.10.10.0/24 scram-sha-256" >> \
    /etc/postgresql/15/main/pg_hba.conf

systemctl restart postgresql

# Create database
sudo -u postgres psql << EOF
CREATE USER writebot WITH PASSWORD 'your-secure-password';
CREATE DATABASE writebot OWNER writebot;
GRANT ALL PRIVILEGES ON DATABASE writebot TO writebot;
\c writebot
GRANT ALL ON SCHEMA public TO writebot;
EOF

exit
```

#### Create Redis LXC (on Proxmox host)

```bash
pct create 102 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
    --hostname writebot-redis \
    --memory 512 --cores 1 \
    --rootfs local-lvm:5 \
    --net0 name=eth0,bridge=vmbr0,ip=10.10.10.12/24,gw=10.10.10.1 \
    --unprivileged 1 --onboot 1

pct start 102
```

#### Configure Redis

```bash
# Enter container
pct enter 102

# Install Redis
apt update && apt install -y redis-server

# Configure network access
sed -i "s/^bind 127.0.0.1.*/bind 0.0.0.0/" /etc/redis/redis.conf
sed -i "s/^protected-mode yes/protected-mode no/" /etc/redis/redis.conf

systemctl restart redis-server
systemctl enable redis-server

exit
```

### 2. Setting Up Docker VM

If you need to set up the Docker VM from scratch:

```bash
# After Ubuntu 22.04 installation, run:
sudo ./deploy/proxmox/setup-docker-vm.sh
sudo reboot

# Verify GPU after reboot
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi
```

### 3. Configure WriteBot

```bash
cd /opt/writebot
sudo cp .env.production.example .env
sudo nano .env
```

**Required settings:**

```bash
# Generate with: python3 -c 'import secrets; print(secrets.token_hex(32))'
SECRET_KEY=your-generated-secret-key

# PostgreSQL
POSTGRES_HOST=10.10.10.11
POSTGRES_PORT=5432
POSTGRES_DB=writebot
POSTGRES_USER=writebot
POSTGRES_PASSWORD=your-secure-password

# Redis
REDIS_HOST=10.10.10.12
REDIS_PORT=6379
```

### 4. Test Connectivity

```bash
# Test PostgreSQL
psql -h 10.10.10.11 -U writebot -d writebot -c "SELECT 1;"

# Test Redis
redis-cli -h 10.10.10.12 ping

# Test GPU
nvidia-smi
```

### 5. Deploy

```bash
sudo ./deploy/proxmox/proxmox-deploy.sh
```

### 6. Verify Deployment

```bash
# Check containers
docker compose -f docker-compose.production.yml ps

# Check health
curl http://localhost:5000/api/health

# Check GPU in container
docker exec writebot-app-production nvidia-smi

# View logs
docker compose -f docker-compose.production.yml logs -f
```

---

## Cloudflare Tunnel Setup

Expose WriteBot securely without opening ports:

```bash
# Install cloudflared (if not already done)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create writebot

# Note the tunnel ID from the output, then:
mkdir -p ~/.cloudflared

cat > ~/.cloudflared/config.yml << EOF
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/$USER/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: writebot.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
EOF

# Route DNS
cloudflared tunnel route dns writebot writebot.yourdomain.com

# Run as service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Verify
sudo systemctl status cloudflared
```

---

## Deployment Commands

### Daily Operations

```bash
# Start services
docker compose -f docker-compose.production.yml up -d

# Stop services
docker compose -f docker-compose.production.yml down

# View logs
docker compose -f docker-compose.production.yml logs -f

# Restart
docker compose -f docker-compose.production.yml restart
```

### Update Deployment

```bash
cd /opt/writebot
sudo ./deploy/proxmox/proxmox-deploy.sh
```

### Deploy Options

```bash
# Skip git pull (use current code)
sudo ./deploy/proxmox/proxmox-deploy.sh --no-pull

# Skip Docker build (use existing image)
sudo ./deploy/proxmox/proxmox-deploy.sh --no-build

# Force rebuild without cache
sudo ./deploy/proxmox/proxmox-deploy.sh --force

# Include Celery worker for background tasks
sudo ./deploy/proxmox/proxmox-deploy.sh --celery

# Combine options
sudo ./deploy/proxmox/proxmox-deploy.sh --no-pull --celery
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | - | Flask secret key (required) |
| `POSTGRES_HOST` | 10.10.10.11 | PostgreSQL server IP |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | writebot | Database name |
| `POSTGRES_USER` | writebot | Database user |
| `POSTGRES_PASSWORD` | - | Database password (required) |
| `REDIS_HOST` | 10.10.10.12 | Redis server IP |
| `REDIS_PORT` | 6379 | Redis port |
| `CUDA_VISIBLE_DEVICES` | 0 | GPU device index |
| `GUNICORN_WORKERS` | 2 | Number of Gunicorn workers |
| `GUNICORN_THREADS` | 4 | Threads per worker |
| `GUNICORN_TIMEOUT` | 180 | Request timeout (seconds) |
| `APP_PORT` | 5000 | Application port |

### Docker Build Arguments

Customize at build time:

```bash
docker compose -f docker-compose.production.yml build \
    --build-arg CUDA_VERSION=12.3.1 \
    --build-arg GUNICORN_WORKERS=4
```

---

## Troubleshooting

### GPU Not Detected in Container

```bash
# Check host GPU
nvidia-smi

# Check NVIDIA Container Toolkit
nvidia-ctk --version

# Reconfigure Docker runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test GPU in Docker
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi
```

### Cannot Connect to PostgreSQL

```bash
# From Docker VM, test connection
psql -h 10.10.10.11 -U writebot -d writebot

# Check PostgreSQL is listening
pct enter 101
ss -tlnp | grep 5432
cat /etc/postgresql/15/main/pg_hba.conf | grep writebot

# Check firewall
ufw status
```

### Cannot Connect to Redis

```bash
# From Docker VM, test connection
redis-cli -h 10.10.10.12 ping

# Check Redis is listening
pct enter 102
ss -tlnp | grep 6379
grep "^bind" /etc/redis/redis.conf
```

### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.production.yml logs writebot

# Check container status
docker compose -f docker-compose.production.yml ps -a

# Try running manually
docker compose -f docker-compose.production.yml run --rm writebot bash
```

### Health Check Failing

```bash
# Check if app is running
curl -v http://localhost:5000/api/health

# Check container logs
docker compose -f docker-compose.production.yml logs --tail=100 writebot

# Enter container and debug
docker exec -it writebot-app-production bash
python -c "from webapp.app import app; print('App loads OK')"
```

---

## Backup & Recovery

### Backup Database

```bash
# On Docker VM
pg_dump -h 10.10.10.11 -U writebot writebot > backup_$(date +%Y%m%d).sql

# Or from PostgreSQL LXC
pct enter 101
sudo -u postgres pg_dump writebot > /root/backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# On Docker VM
psql -h 10.10.10.11 -U writebot writebot < backup_20240101.sql
```

### Backup Redis

```bash
# Redis automatically saves to /var/lib/redis/dump.rdb
pct enter 102
cp /var/lib/redis/dump.rdb /root/redis_backup_$(date +%Y%m%d).rdb
```

---

## Files Reference

```
deploy/proxmox/
├── README.md                    # This file
├── proxmox-setup.sh            # Create VMs/LXCs on Proxmox host
├── setup-postgresql-lxc.sh     # Configure PostgreSQL in LXC
├── setup-redis-lxc.sh          # Configure Redis in LXC
├── setup-docker-vm.sh          # Configure Docker VM with GPU
└── proxmox-deploy.sh           # Deploy WriteBot (git pull, build, run)

# Root directory
├── docker-compose.production.yml   # Production compose file
├── .env.production.example         # Environment template
└── Dockerfile.gpu                  # GPU-enabled Dockerfile
```

---

## Support

- **Repository:** https://github.com/ariedotcodotnz/WriteBot
- **Issues:** https://github.com/ariedotcodotnz/WriteBot/issues
