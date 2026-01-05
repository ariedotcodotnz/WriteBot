#!/bin/bash
# =============================================================================
# WriteBot Proxmox Infrastructure Setup
# =============================================================================
# Run this ONCE on the Proxmox host to create VMs and LXC containers
#
# Prerequisites:
#   - Proxmox VE 7.x or 8.x
#   - IOMMU enabled in BIOS (Intel VT-d or AMD-Vi)
#   - Ubuntu 22.04 LXC template downloaded
#   - Ubuntu 22.04 ISO for Docker VM
#   - NVIDIA GPU for passthrough
#
# Usage:
#   chmod +x proxmox-setup.sh
#   ./proxmox-setup.sh

set -e

# =============================================================================
# CONFIGURATION - Customize these values for your environment
# =============================================================================

# Network Configuration
BRIDGE="vmbr0"
GATEWAY="10.10.10.1"
SUBNET_MASK="24"
DNS_SERVER="1.1.1.1"

# Docker VM Configuration (QEMU - required for GPU passthrough)
DOCKER_VM_ID=100
DOCKER_VM_IP="10.10.10.10"
DOCKER_VM_RAM=16384          # 16GB RAM
DOCKER_VM_CORES=8            # 8 CPU cores
DOCKER_VM_DISK="100G"        # 100GB disk
DOCKER_VM_NAME="writebot-docker"

# PostgreSQL LXC Configuration
POSTGRES_LXC_ID=101
POSTGRES_LXC_IP="10.10.10.11"
POSTGRES_LXC_RAM=2048        # 2GB RAM
POSTGRES_LXC_CORES=2         # 2 CPU cores
POSTGRES_LXC_DISK="20"       # 20GB disk
POSTGRES_LXC_NAME="writebot-postgres"

# Redis LXC Configuration
REDIS_LXC_ID=102
REDIS_LXC_IP="10.10.10.12"
REDIS_LXC_RAM=512            # 512MB RAM
REDIS_LXC_CORES=1            # 1 CPU core
REDIS_LXC_DISK="5"           # 5GB disk
REDIS_LXC_NAME="writebot-redis"

# Storage Configuration (adjust for your Proxmox setup)
STORAGE="local-lvm"          # Storage pool for VMs/LXCs
ISO_STORAGE="local"          # Storage for ISO files
TEMPLATE_STORAGE="local"     # Storage for LXC templates

# LXC Template (download with: pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst)
LXC_TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"

# GPU PCI Address (find with: lspci -nn | grep -i nvidia)
# Format: bus:device.function (e.g., "01:00" for 01:00.0)
GPU_PCI_ADDRESS="01:00"

# Ubuntu ISO filename (download from ubuntu.com and upload to Proxmox)
UBUNTU_ISO="ubuntu-22.04.4-live-server-amd64.iso"

# =============================================================================
# COLORS FOR OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================
echo ""
echo "=============================================="
echo "  WriteBot Proxmox Infrastructure Setup"
echo "=============================================="
echo ""

log_step "Running pre-flight checks..."

# Check if running on Proxmox
if ! command -v pct &> /dev/null || ! command -v qm &> /dev/null; then
    log_error "This script must be run on a Proxmox VE host"
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root"
    exit 1
fi

# Check IOMMU status
if dmesg | grep -q "IOMMU enabled\|DMAR-IR: Enabled\|AMD-Vi:"; then
    log_info "IOMMU is enabled"
else
    log_warn "IOMMU may not be enabled!"
    log_warn "GPU passthrough requires IOMMU. Add to /etc/default/grub:"
    log_warn "  Intel: GRUB_CMDLINE_LINUX_DEFAULT=\"quiet intel_iommu=on iommu=pt\""
    log_warn "  AMD:   GRUB_CMDLINE_LINUX_DEFAULT=\"quiet amd_iommu=on iommu=pt\""
    log_warn "Then run: update-grub && reboot"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for LXC template
if [ ! -f "/var/lib/vz/template/cache/${LXC_TEMPLATE}" ]; then
    log_warn "LXC template not found: ${LXC_TEMPLATE}"
    log_info "Downloading template..."
    pveam download ${TEMPLATE_STORAGE} ${LXC_TEMPLATE} || {
        log_error "Failed to download template. Download manually:"
        log_error "  pveam download ${TEMPLATE_STORAGE} ${LXC_TEMPLATE}"
        exit 1
    }
fi

# Check for Ubuntu ISO
if [ ! -f "/var/lib/vz/template/iso/${UBUNTU_ISO}" ]; then
    log_warn "Ubuntu ISO not found: ${UBUNTU_ISO}"
    log_warn "Download from https://ubuntu.com/download/server and upload to Proxmox"
    log_warn "Or use: wget -P /var/lib/vz/template/iso/ https://releases.ubuntu.com/22.04/${UBUNTU_ISO}"
fi

# Check if VMs/LXCs already exist
for vmid in $DOCKER_VM_ID $POSTGRES_LXC_ID $REDIS_LXC_ID; do
    if qm status $vmid &> /dev/null || pct status $vmid &> /dev/null; then
        log_error "VM/LXC with ID $vmid already exists!"
        log_error "Remove it first or change the ID in this script"
        exit 1
    fi
done

log_info "All pre-flight checks passed"
echo ""

# =============================================================================
# CREATE POSTGRESQL LXC CONTAINER
# =============================================================================
log_step "Creating PostgreSQL LXC container (ID: $POSTGRES_LXC_ID)..."

pct create $POSTGRES_LXC_ID ${TEMPLATE_STORAGE}:vztmpl/${LXC_TEMPLATE} \
    --hostname ${POSTGRES_LXC_NAME} \
    --memory ${POSTGRES_LXC_RAM} \
    --cores ${POSTGRES_LXC_CORES} \
    --rootfs ${STORAGE}:${POSTGRES_LXC_DISK} \
    --net0 name=eth0,bridge=${BRIDGE},ip=${POSTGRES_LXC_IP}/${SUBNET_MASK},gw=${GATEWAY} \
    --nameserver ${DNS_SERVER} \
    --unprivileged 1 \
    --features nesting=0 \
    --onboot 1 \
    --start 0 \
    --password "changeme123"

log_info "PostgreSQL LXC container created successfully"

# =============================================================================
# CREATE REDIS LXC CONTAINER
# =============================================================================
log_step "Creating Redis LXC container (ID: $REDIS_LXC_ID)..."

pct create $REDIS_LXC_ID ${TEMPLATE_STORAGE}:vztmpl/${LXC_TEMPLATE} \
    --hostname ${REDIS_LXC_NAME} \
    --memory ${REDIS_LXC_RAM} \
    --cores ${REDIS_LXC_CORES} \
    --rootfs ${STORAGE}:${REDIS_LXC_DISK} \
    --net0 name=eth0,bridge=${BRIDGE},ip=${REDIS_LXC_IP}/${SUBNET_MASK},gw=${GATEWAY} \
    --nameserver ${DNS_SERVER} \
    --unprivileged 1 \
    --features nesting=0 \
    --onboot 1 \
    --start 0 \
    --password "changeme123"

log_info "Redis LXC container created successfully"

# =============================================================================
# CREATE DOCKER VM (QEMU for GPU Passthrough)
# =============================================================================
log_step "Creating Docker VM with GPU passthrough (ID: $DOCKER_VM_ID)..."

# Create VM
qm create $DOCKER_VM_ID \
    --name ${DOCKER_VM_NAME} \
    --memory ${DOCKER_VM_RAM} \
    --cores ${DOCKER_VM_CORES} \
    --cpu host \
    --net0 virtio,bridge=${BRIDGE} \
    --scsihw virtio-scsi-single \
    --scsi0 ${STORAGE}:${DOCKER_VM_DISK},iothread=1,discard=on \
    --ide2 ${ISO_STORAGE}:iso/${UBUNTU_ISO},media=cdrom \
    --boot order=ide2\;scsi0 \
    --ostype l26 \
    --machine q35 \
    --bios ovmf \
    --efidisk0 ${STORAGE}:1,efitype=4m,pre-enrolled-keys=1 \
    --onboot 1 \
    --agent 1

# Add GPU passthrough (PCI device)
log_info "Adding GPU passthrough..."
qm set $DOCKER_VM_ID --hostpci0 ${GPU_PCI_ADDRESS},pcie=1,rombar=1

log_info "Docker VM created successfully"
log_warn "Note: Static IP (${DOCKER_VM_IP}) must be configured during Ubuntu installation"

# =============================================================================
# COPY SETUP SCRIPTS TO CONTAINERS
# =============================================================================
log_step "Preparing setup scripts..."

# Create temporary script directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# The setup scripts will be copied after containers start

# =============================================================================
# SUMMARY AND NEXT STEPS
# =============================================================================
echo ""
echo "=============================================="
echo "  Proxmox Infrastructure Created!"
echo "=============================================="
echo ""
echo "CONTAINERS CREATED:"
echo "  Docker VM:    ID=${DOCKER_VM_ID}, IP=${DOCKER_VM_IP}, RAM=${DOCKER_VM_RAM}MB, Cores=${DOCKER_VM_CORES}"
echo "  PostgreSQL:   ID=${POSTGRES_LXC_ID}, IP=${POSTGRES_LXC_IP}, RAM=${POSTGRES_LXC_RAM}MB, Cores=${POSTGRES_LXC_CORES}"
echo "  Redis:        ID=${REDIS_LXC_ID}, IP=${REDIS_LXC_IP}, RAM=${REDIS_LXC_RAM}MB, Cores=${REDIS_LXC_CORES}"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. START LXC CONTAINERS:"
echo "   pct start ${POSTGRES_LXC_ID}"
echo "   pct start ${REDIS_LXC_ID}"
echo ""
echo "2. CONFIGURE POSTGRESQL (run inside container):"
echo "   pct enter ${POSTGRES_LXC_ID}"
echo "   # Upload and run setup-postgresql-lxc.sh"
echo "   # Default root password: changeme123"
echo ""
echo "3. CONFIGURE REDIS (run inside container):"
echo "   pct enter ${REDIS_LXC_ID}"
echo "   # Upload and run setup-redis-lxc.sh"
echo "   # Default root password: changeme123"
echo ""
echo "4. INSTALL UBUNTU ON DOCKER VM:"
echo "   qm start ${DOCKER_VM_ID}"
echo "   # Access via Proxmox console or VNC"
echo "   # During install, set static IP: ${DOCKER_VM_IP}/${SUBNET_MASK}"
echo "   # Gateway: ${GATEWAY}"
echo "   # After install, run setup-docker-vm.sh"
echo ""
echo "5. CONFIGURE GPU PASSTHROUGH (if not working):"
echo "   # Check PCI address: lspci -nn | grep -i nvidia"
echo "   # Current setting: ${GPU_PCI_ADDRESS}"
echo "   # Update: qm set ${DOCKER_VM_ID} --hostpci0 <new-address>,pcie=1"
echo ""
echo "NETWORK LAYOUT:"
echo "  +-----------------+     +-----------------+     +-----------------+"
echo "  | Docker VM       |     | PostgreSQL LXC  |     | Redis LXC       |"
echo "  | ${DOCKER_VM_IP}    |<--->| ${POSTGRES_LXC_IP}    |<--->| ${REDIS_LXC_IP}    |"
echo "  | Port 5000       |     | Port 5432       |     | Port 6379       |"
echo "  | GPU: RTX 5090   |     |                 |     |                 |"
echo "  +-----------------+     +-----------------+     +-----------------+"
echo "                              |"
echo "                        vmbr0 (${GATEWAY})"
echo ""
log_info "Setup complete! Follow the next steps above."
