#!/bin/bash
# ZAZA UAT Deployment Script - System Preparation
# Target: Ubuntu 24.04 LTS (198.18.2.234)
# Purpose: Prepare system for Agent-Zero deployment

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
HOSTNAME="zaza-uat"
DEPLOY_USER="zaza"
DEPLOY_DIR="/opt/zaza"
LOG_DIR="/var/log/zaza"
DATA_DIR="/var/lib/zaza"
BACKUP_DIR="/backup/zaza"

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting ZAZA UAT System Preparation"
    
    # Check if running as root
    check_root
    
    # Update system
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    apt-get dist-upgrade -y
    
    # Install essential packages
    log_info "Installing essential packages..."
    apt-get install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        net-tools \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
        jq \
        tmux \
        ufw \
        fail2ban \
        unzip \
        zip \
        rsync \
        cron \
        systemd-timesyncd
    
    # Set hostname
    log_info "Setting hostname to ${HOSTNAME}..."
    hostnamectl set-hostname ${HOSTNAME}
    echo "127.0.1.1 ${HOSTNAME}" >> /etc/hosts
    
    # Configure timezone
    log_info "Configuring timezone..."
    timedatectl set-timezone UTC
    timedatectl set-ntp true
    
    # Create deployment user
    log_info "Creating deployment user ${DEPLOY_USER}..."
    if ! id -u ${DEPLOY_USER} >/dev/null 2>&1; then
        useradd -m -s /bin/bash ${DEPLOY_USER}
        usermod -aG sudo ${DEPLOY_USER}
        usermod -aG docker ${DEPLOY_USER} 2>/dev/null || true
    fi
    
    # Create directory structure
    log_info "Creating directory structure..."
    mkdir -p ${DEPLOY_DIR}
    mkdir -p ${LOG_DIR}
    mkdir -p ${DATA_DIR}
    mkdir -p ${BACKUP_DIR}
    mkdir -p ${DEPLOY_DIR}/{config,scripts,data,logs,temp}
    mkdir -p ${DATA_DIR}/{postgres,redis,elasticsearch}
    
    # Set permissions
    chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_DIR}
    chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${LOG_DIR}
    chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${DATA_DIR}
    chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${BACKUP_DIR}
    
    # Configure swap
    log_info "Configuring swap space..."
    SWAP_SIZE="64G"  # 2x expected RAM usage
    if [ ! -f /swapfile ]; then
        fallocate -l ${SWAP_SIZE} /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    
    # Configure sysctl for performance
    log_info "Optimizing system parameters..."
    cat >> /etc/sysctl.conf <<EOF

# ZAZA UAT Optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
net.ipv4.tcp_tw_reuse=1
net.ipv4.tcp_fin_timeout=30
net.ipv4.tcp_keepalive_time=300
net.ipv4.tcp_keepalive_probes=5
net.ipv4.tcp_keepalive_intvl=15
fs.file-max=2097152
fs.inotify.max_user_watches=524288
EOF
    sysctl -p
    
    # Configure limits
    log_info "Configuring system limits..."
    cat >> /etc/security/limits.conf <<EOF

# ZAZA UAT Limits
* soft nofile 65535
* hard nofile 65535
* soft nproc 32768
* hard nproc 32768
${DEPLOY_USER} soft nofile 65535
${DEPLOY_USER} hard nofile 65535
EOF
    
    # Configure firewall
    log_info "Configuring firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 8000/tcp  # Control API
    ufw allow 8001/tcp  # Coordination API
    ufw allow 3000/tcp  # Grafana
    ufw allow 9090/tcp  # Prometheus
    ufw --force enable
    
    # Configure fail2ban
    log_info "Configuring fail2ban..."
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Install Python packages
    log_info "Installing Python packages..."
    pip3 install --upgrade pip
    pip3 install \
        docker-compose \
        pyyaml \
        requests \
        python-dotenv \
        colorama \
        tabulate
    
    # Configure log rotation
    log_info "Configuring log rotation..."
    cat > /etc/logrotate.d/zaza <<EOF
${LOG_DIR}/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ${DEPLOY_USER} ${DEPLOY_USER}
    sharedscripts
    postrotate
        docker-compose -f ${DEPLOY_DIR}/docker-compose.yml kill -s USR1
    endscript
}
EOF
    
    # Create system service for ZAZA
    log_info "Creating systemd service..."
    cat > /etc/systemd/system/zaza.service <<EOF
[Unit]
Description=ZAZA UAT Environment
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${DEPLOY_DIR}
ExecStart=/usr/local/bin/docker-compose up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    
    # Setup monitoring directories
    log_info "Setting up monitoring directories..."
    mkdir -p ${DEPLOY_DIR}/monitoring/{prometheus,grafana,loki}
    mkdir -p ${DATA_DIR}/monitoring/{prometheus,grafana,loki}
    
    # Create backup script
    log_info "Creating backup script..."
    cat > ${DEPLOY_DIR}/scripts/backup.sh <<'BACKUP_SCRIPT'
#!/bin/bash
BACKUP_DIR="/backup/zaza"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="zaza_backup_${TIMESTAMP}"

# Create backup
tar -czf ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz \
    /opt/zaza/config \
    /opt/zaza/data \
    /var/lib/zaza

# Keep only last 7 backups
ls -t ${BACKUP_DIR}/zaza_backup_*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: ${BACKUP_NAME}"
BACKUP_SCRIPT
    
    chmod +x ${DEPLOY_DIR}/scripts/backup.sh
    chown ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_DIR}/scripts/backup.sh
    
    # Setup cron for automated backups
    log_info "Setting up automated backups..."
    echo "0 2 * * * ${DEPLOY_USER} ${DEPLOY_DIR}/scripts/backup.sh" > /etc/cron.d/zaza-backup
    
    # System information
    log_info "System preparation complete!"
    log_info "System Information:"
    echo "  Hostname: $(hostname)"
    echo "  IP Address: $(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)"
    echo "  Total Memory: $(free -h | awk '/^Mem:/ {print $2}')"
    echo "  Total Swap: $(free -h | awk '/^Swap:/ {print $2}')"
    echo "  CPU Cores: $(nproc)"
    echo "  Disk Space: $(df -h / | awk 'NR==2 {print $2}')"
    echo ""
    log_info "Deployment Directory: ${DEPLOY_DIR}"
    log_info "Data Directory: ${DATA_DIR}"
    log_info "Log Directory: ${LOG_DIR}"
    log_info "Backup Directory: ${BACKUP_DIR}"
    echo ""
    log_warn "Please reboot the system to apply all changes"
    log_warn "Run: sudo reboot"
}

# Run main function
main "$@"