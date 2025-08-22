# ZAZA Enterprises UAT Installation Instructions
## Complete Setup Guide for Ubuntu 24.04 LTS Server

### Prerequisites
- Ubuntu 24.04 LTS server (fresh installation)
- Server IP: 198.18.2.234
- Root or sudo access
- Minimum 8 CPU cores, 32GB RAM, 500GB storage
- Internet connectivity for package downloads

---

## Installation Steps

### Step 1: Initial Server Access
```bash
# From your local machine, SSH into the server
ssh root@198.18.2.234

# Or if using a different user with sudo
ssh your_user@198.18.2.234
```

### Step 2: Download Installation Scripts
```bash
# Create temporary directory for scripts
mkdir -p /tmp/zaza-install
cd /tmp/zaza-install

# Download the installation package (you'll need to transfer these files)
# Option 1: Using SCP from your local machine
scp -r /path/to/agent-zero/uat/scripts/* root@198.18.2.234:/tmp/zaza-install/

# Option 2: Using git (if you've pushed to repository)
git clone https://github.com/magadiel/agent-zero.git
cp -r agent-zero/uat/scripts/* /tmp/zaza-install/

# Make scripts executable
chmod +x *.sh
```

### Step 3: Run System Preparation
```bash
# Run as root
sudo ./01_prepare_system.sh

# This script will:
# - Update system packages
# - Install essential tools
# - Create zaza user
# - Configure swap space
# - Setup firewall
# - Optimize system parameters
# Expected duration: 15-20 minutes

# After completion, reboot the system
sudo reboot
```

### Step 4: Install Docker
```bash
# SSH back into the server after reboot
ssh root@198.18.2.234

cd /tmp/zaza-install

# Run Docker installation
sudo ./02_install_docker.sh

# This script will:
# - Install Docker Engine
# - Install Docker Compose
# - Configure Docker daemon
# - Create Docker networks
# - Pull base images
# Expected duration: 10-15 minutes

# Verify Docker installation
docker --version
docker-compose --version
```

### Step 5: Deploy ZAZA Environment
```bash
# Switch to zaza user
sudo su - zaza

# Copy deployment script
cp /tmp/zaza-install/03_deploy_zaza.sh /opt/zaza/
cd /opt/zaza
chmod +x 03_deploy_zaza.sh

# Run deployment
./03_deploy_zaza.sh

# This script will:
# - Clone Agent-Zero repository
# - Create ZAZA configuration
# - Setup agent profiles
# - Configure workflows
# - Create Docker Compose files
# - Setup monitoring
# Expected duration: 20-30 minutes
```

### Step 6: Build Docker Images
```bash
# As zaza user in /opt/zaza
cd /opt/zaza

# Build all Docker images
docker-compose -f docker-compose.zaza.yml build

# This will build:
# - Control layer image
# - Coordination layer image
# - Agent execution images
# Expected duration: 15-20 minutes
```

### Step 7: Initialize Database
```bash
# Start only the database service first
docker-compose -f docker-compose.zaza.yml up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Verify database is running
docker-compose -f docker-compose.zaza.yml exec postgres psql -U zaza_admin -d zaza_uat -c "SELECT 1;"
```

### Step 8: Start ZAZA Services
```bash
# Start all services
./scripts/start_zaza.sh

# Monitor startup logs
docker-compose -f docker-compose.zaza.yml logs -f

# Press Ctrl+C to exit log viewing (services continue running)
```

### Step 9: Verify Installation
```bash
# Run health check
./scripts/health_check.sh

# Check individual services
docker-compose -f docker-compose.zaza.yml ps

# Test API endpoints
curl http://localhost:8000/health  # Control API
curl http://localhost:8001/health  # Coordination API
```

### Step 10: Access Web Interfaces
From your local machine, access:
- **Control API**: http://198.18.2.234:8000
- **Coordination API**: http://198.18.2.234:8001
- **Grafana Dashboard**: http://198.18.2.234:3000 (admin/admin)
- **Prometheus**: http://198.18.2.234:9090

---

## Post-Installation Configuration

### 1. Change Default Passwords
```bash
# Edit .env file
nano /opt/zaza/.env

# Update these passwords:
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - ELASTIC_PASSWORD
# - Grafana admin password (through web UI)

# Restart services after password changes
docker-compose -f docker-compose.zaza.yml restart
```

### 2. Configure SSL/TLS (Optional but Recommended)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d zaza-uat.yourdomain.com

# Update Docker Compose to use SSL
# Add SSL configuration to nginx/proxy settings
```

### 3. Setup Backup Schedule
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/zaza/scripts/backup.sh

# Verify cron job
crontab -l
```

### 4. Configure Monitoring Alerts
```bash
# Access Grafana
# http://198.18.2.234:3000

# Configure alert channels:
# 1. Go to Alerting > Notification channels
# 2. Add email/Slack/webhook notifications
# 3. Create alert rules for critical metrics
```

---

## Running UAT Tests

### Test Scenario 1: System Smoke Test
```bash
cd /opt/zaza

# Run basic smoke test
./tests/smoke_test.sh

# Expected: All services responding, no errors
```

### Test Scenario 2: Client Onboarding
```bash
# Trigger client onboarding workflow
curl -X POST http://localhost:8001/api/workflows/start \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": "client_onboarding",
    "client": "test_client_001",
    "requirements": {
      "service": "digital_marketing",
      "budget": 10000,
      "duration": "3_months"
    }
  }'

# Monitor workflow progress
curl http://localhost:8001/api/workflows/status/{workflow_id}
```

### Test Scenario 3: Team Communication
```bash
# Test inter-team communication
./tests/test_team_communication.sh

# Monitor in Grafana dashboard
# Check message latency and success rates
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Services Won't Start
```bash
# Check Docker logs
docker-compose -f docker-compose.zaza.yml logs [service_name]

# Check resource availability
free -h
df -h
docker system df

# Clean up if needed
docker system prune -a
```

#### 2. Database Connection Issues
```bash
# Test database connection
docker-compose -f docker-compose.zaza.yml exec postgres \
  psql -U zaza_admin -d zaza_uat

# Check database logs
docker-compose -f docker-compose.zaza.yml logs postgres
```

#### 3. High Memory Usage
```bash
# Check memory usage by container
docker stats

# Adjust memory limits in docker-compose.zaza.yml
# Restart affected services
docker-compose -f docker-compose.zaza.yml restart [service_name]
```

#### 4. Network Connectivity Issues
```bash
# Check Docker networks
docker network ls
docker network inspect zaza-control

# Test inter-container connectivity
docker-compose -f docker-compose.zaza.yml exec control \
  ping coordinator
```

#### 5. Agent Not Responding
```bash
# Check agent status
docker-compose -f docker-compose.zaza.yml ps

# Restart specific agent
docker-compose -f docker-compose.zaza.yml restart marketing-director

# Check agent logs
docker-compose -f docker-compose.zaza.yml logs marketing-director
```

---

## Maintenance Procedures

### Daily Tasks
1. Check system health: `./scripts/health_check.sh`
2. Review error logs: `grep ERROR /var/log/zaza/*.log`
3. Monitor resource usage in Grafana

### Weekly Tasks
1. Review metrics and performance trends
2. Check backup integrity
3. Update agent learnings
4. Review security logs

### Monthly Tasks
1. System updates: `sudo apt update && sudo apt upgrade`
2. Docker image updates
3. Performance optimization review
4. Capacity planning assessment

---

## Emergency Procedures

### Emergency Shutdown
```bash
# Immediate shutdown of all services
/opt/zaza/scripts/emergency_shutdown.sh

# This will stop all ZAZA containers immediately
```

### Data Backup
```bash
# Manual backup
/opt/zaza/scripts/backup.sh

# Backup location: /backup/zaza/
```

### System Recovery
```bash
# Restore from backup
cd /opt/zaza
tar -xzf /backup/zaza/zaza_backup_[timestamp].tar.gz -C /

# Restart services
./scripts/start_zaza.sh
```

---

## Support Information

### Log Locations
- System logs: `/var/log/zaza/`
- Docker logs: `docker-compose logs [service]`
- Application logs: `/opt/zaza/logs/`

### Configuration Files
- Main configuration: `/opt/zaza/.env`
- Docker Compose: `/opt/zaza/docker-compose.zaza.yml`
- Agent profiles: `/opt/zaza/agents/zaza/`
- Workflows: `/opt/zaza/workflows/zaza/`

### Useful Commands Reference
```bash
# View all running containers
docker ps

# View service logs
docker-compose -f docker-compose.zaza.yml logs -f [service]

# Restart a service
docker-compose -f docker-compose.zaza.yml restart [service]

# Execute command in container
docker-compose -f docker-compose.zaza.yml exec [service] [command]

# View resource usage
docker stats

# Clean up unused resources
docker system prune -a
```

---

## Final Checklist

Before considering the installation complete:

- [ ] All services are running (check with `docker-compose ps`)
- [ ] APIs are responding (test health endpoints)
- [ ] Grafana dashboard is accessible
- [ ] Database is initialized and accessible
- [ ] Monitoring is collecting metrics
- [ ] Backup script is scheduled
- [ ] Firewall rules are configured
- [ ] Default passwords have been changed
- [ ] Documentation has been reviewed
- [ ] Emergency procedures are understood

---

## Next Steps

After successful installation:

1. **Run UAT Test Suite**: Execute all test scenarios
2. **Monitor Performance**: Watch metrics for 24-48 hours
3. **Document Issues**: Track any problems or improvements
4. **Train Users**: Ensure team knows how to operate system
5. **Plan Production**: Use UAT results to plan production deployment

---

*Installation Guide Version: 1.0*
*Last Updated: 2025-08-22*
*For ZAZA Enterprises UAT Environment*