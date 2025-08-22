#!/bin/bash
# ZAZA UAT Deployment Script - Docker Installation
# Target: Ubuntu 24.04 LTS
# Purpose: Install Docker and Docker Compose

set -e
set -u

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOCKER_COMPOSE_VERSION="2.24.0"
DEPLOY_USER="zaza"

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
    log_info "Starting Docker installation for ZAZA UAT"
    
    check_root
    
    # Remove old Docker versions
    log_info "Removing old Docker versions if present..."
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install Docker dependencies
    log_info "Installing Docker dependencies..."
    apt-get update
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker GPG key
    log_info "Adding Docker GPG key..."
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add Docker repository
    log_info "Adding Docker repository..."
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    log_info "Installing Docker Engine..."
    apt-get update
    apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    # Install Docker Compose standalone
    log_info "Installing Docker Compose v${DOCKER_COMPOSE_VERSION}..."
    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    # Configure Docker daemon
    log_info "Configuring Docker daemon..."
    cat > /etc/docker/daemon.json <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "10"
    },
    "storage-driver": "overlay2",
    "metrics-addr": "127.0.0.1:9323",
    "experimental": true,
    "features": {
        "buildkit": true
    },
    "default-ulimits": {
        "nofile": {
            "Hard": 65535,
            "Soft": 65535
        }
    },
    "live-restore": true,
    "userland-proxy": false
}
EOF
    
    # Create Docker network for ZAZA
    log_info "Creating Docker networks..."
    docker network create zaza-control 2>/dev/null || true
    docker network create zaza-coordination 2>/dev/null || true
    docker network create zaza-execution 2>/dev/null || true
    docker network create zaza-data 2>/dev/null || true
    docker network create zaza-monitoring 2>/dev/null || true
    
    # Add user to docker group
    log_info "Adding ${DEPLOY_USER} to docker group..."
    usermod -aG docker ${DEPLOY_USER}
    
    # Enable and start Docker
    log_info "Enabling Docker service..."
    systemctl enable docker
    systemctl restart docker
    
    # Configure Docker log rotation
    log_info "Configuring Docker log rotation..."
    cat > /etc/logrotate.d/docker <<EOF
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
    
    # Pull base images
    log_info "Pulling base Docker images..."
    docker pull python:3.11-slim
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    docker pull nginx:alpine
    docker pull prom/prometheus:latest
    docker pull grafana/grafana:latest
    docker pull grafana/loki:latest
    docker pull elasticsearch:8.11.0
    
    # Create Docker volume for persistent data
    log_info "Creating Docker volumes..."
    docker volume create zaza-postgres-data
    docker volume create zaza-redis-data
    docker volume create zaza-elasticsearch-data
    docker volume create zaza-prometheus-data
    docker volume create zaza-grafana-data
    docker volume create zaza-loki-data
    docker volume create zaza-control-data
    docker volume create zaza-agent-memory
    
    # Setup Docker Compose environment
    log_info "Setting up Docker Compose environment..."
    mkdir -p /opt/zaza/docker
    
    # Test Docker installation
    log_info "Testing Docker installation..."
    docker --version
    docker-compose --version
    docker run --rm hello-world
    
    # Docker system info
    log_info "Docker System Information:"
    docker system info --format '
    Docker Version: {{.ServerVersion}}
    Storage Driver: {{.Driver}}
    Kernel Version: {{.KernelVersion}}
    Operating System: {{.OperatingSystem}}
    Total Memory: {{.MemTotal}}
    CPUs: {{.NCPU}}'
    
    # Cleanup test container
    docker system prune -f
    
    log_info "Docker installation complete!"
    log_info "Docker is ready for ZAZA deployment"
    echo ""
    log_warn "Please log out and back in for group changes to take effect"
    log_warn "Or run: newgrp docker"
}

# Run main function
main "$@"