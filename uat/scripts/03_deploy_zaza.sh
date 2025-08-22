#!/bin/bash
# ZAZA UAT Deployment Script - Deploy ZAZA Environment
# Target: Ubuntu 24.04 LTS
# Purpose: Deploy Agent-Zero framework as ZAZA Enterprises

set -e
set -u

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DEPLOY_DIR="/opt/zaza"
DEPLOY_USER="zaza"
GIT_REPO="https://github.com/magadiel/agent-zero.git"
GIT_BRANCH="main"
ZAZA_VERSION="1.0.0-uat"

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_user() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should NOT be run as root"
        log_info "Please run as ${DEPLOY_USER} user"
        exit 1
    fi
    
    if [[ $(whoami) != "${DEPLOY_USER}" ]]; then
        log_error "This script must be run as ${DEPLOY_USER} user"
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting ZAZA Enterprises UAT Deployment"
    log_info "Version: ${ZAZA_VERSION}"
    echo ""
    
    check_user
    
    # Change to deployment directory
    cd ${DEPLOY_DIR}
    
    # Clone repository
    log_step "1/10: Cloning Agent-Zero repository..."
    if [ -d "agent-zero" ]; then
        log_warn "Repository already exists, updating..."
        cd agent-zero
        git fetch origin
        git checkout ${GIT_BRANCH}
        git pull origin ${GIT_BRANCH}
        cd ..
    else
        git clone ${GIT_REPO}
        cd agent-zero
        git checkout ${GIT_BRANCH}
        cd ..
    fi
    
    # Create ZAZA-specific configuration
    log_step "2/10: Creating ZAZA configuration..."
    mkdir -p ${DEPLOY_DIR}/zaza-config
    
    # Copy base configuration
    cp -r agent-zero/* ${DEPLOY_DIR}/
    
    # Create ZAZA environment file
    log_step "3/10: Configuring environment..."
    cat > ${DEPLOY_DIR}/.env <<EOF
# ZAZA Enterprises UAT Configuration
COMPANY_NAME=ZAZA Enterprises
COMPANY_TYPE=Digital Marketing Agency
ENVIRONMENT=UAT
VERSION=${ZAZA_VERSION}

# System Configuration
DEPLOY_DIR=${DEPLOY_DIR}
DATA_DIR=/var/lib/zaza
LOG_DIR=/var/log/zaza

# Network Configuration
HOST_IP=198.18.2.234
CONTROL_PORT=8000
COORDINATION_PORT=8001
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=zaza_uat
POSTGRES_USER=zaza_admin
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$(openssl rand -base64 32)

# Elasticsearch Configuration
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_PASSWORD=$(openssl rand -base64 32)

# Security Configuration
JWT_SECRET=$(openssl rand -base64 64)
ETHICS_KEY=$(openssl rand -base64 32)
AUDIT_KEY=$(openssl rand -base64 32)

# Team Configuration
MARKETING_TEAM_SIZE=5
CREATIVE_TEAM_SIZE=3
ANALYTICS_TEAM_SIZE=3
OPERATIONS_TEAM_SIZE=3

# Resource Limits
MAX_CPU_PER_AGENT=2
MAX_MEMORY_PER_AGENT=4G
MAX_AGENTS=20

# Monitoring
ENABLE_MONITORING=true
METRICS_RETENTION_DAYS=30
LOG_LEVEL=INFO
EOF
    
    # Create ZAZA-specific agent profiles
    log_step "4/10: Creating ZAZA agent profiles..."
    mkdir -p ${DEPLOY_DIR}/agents/zaza
    
    # Create Marketing Director agent
    cat > ${DEPLOY_DIR}/agents/zaza/marketing_director.md <<'AGENT_EOF'
# Marketing Director Agent - ZAZA Enterprises

## Agent Configuration
```yaml
agent:
  name: Marketing Director
  id: zaza-mkt-director
  type: marketing_leadership
  company: ZAZA Enterprises
```

## Persona
I am the Marketing Director at ZAZA Enterprises, responsible for overall marketing strategy, campaign oversight, and team leadership. I ensure our digital marketing services deliver exceptional value to clients through innovative strategies and data-driven decisions.

### Core Responsibilities
- Develop comprehensive marketing strategies
- Oversee campaign execution
- Manage marketing team performance
- Client relationship management
- Budget allocation and ROI optimization

### Communication Style
Professional, strategic, and results-oriented. I communicate with clarity and always back decisions with data.

## Commands
* create-marketing-strategy
* review-campaign-performance
* allocate-marketing-budget
* approve-content-calendar
* conduct-team-review
* generate-client-report

## Workflows
- Campaign planning and execution
- Client onboarding
- Performance review cycles
- Strategy development
AGENT_EOF
    
    # Create Content Manager agent
    cat > ${DEPLOY_DIR}/agents/zaza/content_manager.md <<'AGENT_EOF'
# Content Manager Agent - ZAZA Enterprises

## Agent Configuration
```yaml
agent:
  name: Content Manager
  id: zaza-content-mgr
  type: content_operations
  company: ZAZA Enterprises
```

## Persona
I am the Content Manager at ZAZA Enterprises, responsible for content pipeline management, quality assurance, and content strategy implementation. I ensure consistent, high-quality content delivery across all client projects.

### Core Responsibilities
- Manage content production pipeline
- Ensure content quality standards
- Coordinate with creative team
- Optimize content for SEO
- Track content performance metrics

### Communication Style
Detail-oriented, creative, and collaborative. I focus on clarity and maintaining brand voice consistency.

## Commands
* create-content-calendar
* review-content-quality
* assign-content-tasks
* optimize-seo-content
* track-content-metrics
* manage-editorial-workflow

## Workflows
- Content production workflow
- Quality review process
- SEO optimization workflow
- Content distribution
AGENT_EOF
    
    # Create ZAZA-specific workflows
    log_step "5/10: Creating ZAZA workflows..."
    mkdir -p ${DEPLOY_DIR}/workflows/zaza
    
    cat > ${DEPLOY_DIR}/workflows/zaza/client_onboarding.yaml <<'WORKFLOW_EOF'
name: ZAZA Client Onboarding
description: Onboard new digital marketing client
version: 1.0.0

agents:
  - client_success
  - marketing_director
  - content_manager
  - analytics_specialist
  - project_manager

sequence:
  - step: initial_consultation
    agent: client_success
    action: gather_requirements
    creates:
      - client_brief.md
      - requirements.yaml
    
  - step: strategy_development
    agent: marketing_director
    action: create_marketing_strategy
    requires:
      - client_brief.md
    creates:
      - marketing_strategy.md
      - budget_proposal.yaml
    
  - step: content_planning
    agent: content_manager
    action: create_content_calendar
    requires:
      - marketing_strategy.md
    creates:
      - content_calendar.md
      - editorial_guidelines.md
    
  - step: analytics_setup
    agent: analytics_specialist
    action: configure_tracking
    requires:
      - marketing_strategy.md
    creates:
      - analytics_config.yaml
      - kpi_dashboard.json
    
  - step: project_kickoff
    agent: project_manager
    action: initialize_project
    requires:
      - marketing_strategy.md
      - content_calendar.md
      - analytics_config.yaml
    creates:
      - project_plan.md
      - team_assignments.yaml
      - kickoff_deck.md

quality_gates:
  - after: strategy_development
    checker: marketing_director
    criteria:
      - budget_approved
      - goals_defined
      - timeline_realistic
  
  - after: project_kickoff
    checker: client_success
    criteria:
      - client_approval_received
      - contracts_signed
      - team_assigned
WORKFLOW_EOF
    
    # Create Docker Compose for ZAZA
    log_step "6/10: Creating Docker Compose configuration..."
    cat > ${DEPLOY_DIR}/docker-compose.zaza.yml <<'COMPOSE_EOF'
version: '3.8'

x-common-variables: &common-variables
  COMPANY_NAME: ${COMPANY_NAME}
  ENVIRONMENT: ${ENVIRONMENT}
  LOG_LEVEL: ${LOG_LEVEL}

x-resource-limits: &resource-limits
  cpus: '${MAX_CPU_PER_AGENT}'
  memory: ${MAX_MEMORY_PER_AGENT}

services:
  # Control Layer
  control:
    build:
      context: ./control
      dockerfile: Dockerfile
    container_name: zaza-control
    hostname: zaza-control
    environment:
      <<: *common-variables
      ETHICS_KEY: ${ETHICS_KEY}
      AUDIT_KEY: ${AUDIT_KEY}
      POSTGRES_CONNECTION: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    ports:
      - "${CONTROL_PORT}:8000"
    networks:
      - zaza-control
      - zaza-data
    volumes:
      - ./control/config:/app/config:ro
      - control-data:/app/data
    deploy:
      resources:
        limits:
          <<: *resource-limits
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Coordination Layer
  coordinator:
    build:
      context: ./
      dockerfile: Dockerfile
    container_name: zaza-coordinator
    hostname: zaza-coordinator
    environment:
      <<: *common-variables
      ROLE: coordinator
      CONTROL_API: http://control:8000
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
    ports:
      - "${COORDINATION_PORT}:8001"
    networks:
      - zaza-control
      - zaza-coordination
      - zaza-data
    volumes:
      - ./coordination:/app/coordination:ro
      - ./workflows/zaza:/app/workflows:ro
      - coordinator-data:/app/data
    deploy:
      resources:
        limits:
          <<: *resource-limits
    depends_on:
      - control
      - redis
    restart: unless-stopped

  # Marketing Team Leader
  marketing-director:
    build:
      context: ./
      dockerfile: Dockerfile
    container_name: zaza-marketing-director
    hostname: marketing-director
    environment:
      <<: *common-variables
      ROLE: execution
      AGENT_PROFILE: zaza/marketing_director
      TEAM: marketing
      COORDINATOR_API: http://coordinator:8001
    networks:
      - zaza-coordination
      - zaza-execution
    volumes:
      - ./agents/zaza:/app/agents:ro
      - agent-memory:/app/memory
    deploy:
      resources:
        limits:
          <<: *resource-limits
    depends_on:
      - coordinator
    restart: unless-stopped

  # Content Manager
  content-manager:
    build:
      context: ./
      dockerfile: Dockerfile
    container_name: zaza-content-manager
    hostname: content-manager
    environment:
      <<: *common-variables
      ROLE: execution
      AGENT_PROFILE: zaza/content_manager
      TEAM: marketing
      COORDINATOR_API: http://coordinator:8001
    networks:
      - zaza-coordination
      - zaza-execution
    volumes:
      - ./agents/zaza:/app/agents:ro
      - agent-memory:/app/memory
    deploy:
      resources:
        limits:
          <<: *resource-limits
    depends_on:
      - coordinator
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: zaza-postgres
    hostname: postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"
    ports:
      - "5432:5432"
    networks:
      - zaza-data
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: zaza-redis
    hostname: redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    networks:
      - zaza-data
    volumes:
      - redis-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Elasticsearch
  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: zaza-elasticsearch
    hostname: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - xpack.security.enabled=true
    ports:
      - "9200:9200"
    networks:
      - zaza-data
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: zaza-prometheus
    hostname: prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=${METRICS_RETENTION_DAYS}d'
    ports:
      - "${PROMETHEUS_PORT}:9090"
    networks:
      - zaza-monitoring
      - zaza-control
      - zaza-coordination
      - zaza-execution
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    restart: unless-stopped

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: zaza-grafana
    hostname: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=redis-datasource
    ports:
      - "${GRAFANA_PORT}:3000"
    networks:
      - zaza-monitoring
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

networks:
  zaza-control:
    driver: bridge
  zaza-coordination:
    driver: bridge
  zaza-execution:
    driver: bridge
  zaza-data:
    driver: bridge
  zaza-monitoring:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  elasticsearch-data:
  prometheus-data:
  grafana-data:
  control-data:
  coordinator-data:
  agent-memory:
COMPOSE_EOF
    
    # Create monitoring configuration
    log_step "7/10: Setting up monitoring..."
    mkdir -p ${DEPLOY_DIR}/monitoring/prometheus
    mkdir -p ${DEPLOY_DIR}/monitoring/grafana/provisioning/{dashboards,datasources}
    mkdir -p ${DEPLOY_DIR}/monitoring/grafana/dashboards
    
    cat > ${DEPLOY_DIR}/monitoring/prometheus/prometheus.yml <<'PROM_EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'zaza-control'
    static_configs:
      - targets: ['control:8000']
        labels:
          layer: 'control'
          
  - job_name: 'zaza-coordinator'
    static_configs:
      - targets: ['coordinator:8001']
        labels:
          layer: 'coordination'
          
  - job_name: 'zaza-agents'
    static_configs:
      - targets: 
        - 'marketing-director:9000'
        - 'content-manager:9001'
        labels:
          layer: 'execution'
          
  - job_name: 'docker'
    static_configs:
      - targets: ['host.docker.internal:9323']
        labels:
          component: 'docker'
PROM_EOF
    
    # Create startup script
    log_step "8/10: Creating startup scripts..."
    cat > ${DEPLOY_DIR}/scripts/start_zaza.sh <<'START_EOF'
#!/bin/bash
cd /opt/zaza
source .env

echo "Starting ZAZA Enterprises UAT Environment..."
echo "Company: ${COMPANY_NAME}"
echo "Environment: ${ENVIRONMENT}"
echo "Version: ${VERSION}"

# Start services
docker-compose -f docker-compose.zaza.yml up -d

# Wait for services to be healthy
echo "Waiting for services to become healthy..."
sleep 10

# Check service health
docker-compose -f docker-compose.zaza.yml ps

echo ""
echo "ZAZA UAT Environment is starting up!"
echo "Access points:"
echo "  Control API: http://198.18.2.234:${CONTROL_PORT}"
echo "  Coordination API: http://198.18.2.234:${COORDINATION_PORT}"
echo "  Grafana Dashboard: http://198.18.2.234:${GRAFANA_PORT}"
echo "  Prometheus: http://198.18.2.234:${PROMETHEUS_PORT}"
echo ""
echo "Default Grafana credentials: admin/admin"
START_EOF
    
    chmod +x ${DEPLOY_DIR}/scripts/start_zaza.sh
    
    # Create health check script
    cat > ${DEPLOY_DIR}/scripts/health_check.sh <<'HEALTH_EOF'
#!/bin/bash
cd /opt/zaza

echo "=== ZAZA Health Check ==="
echo ""

# Check Docker services
echo "Docker Services Status:"
docker-compose -f docker-compose.zaza.yml ps

echo ""
echo "Container Health:"
for container in $(docker ps --format "table {{.Names}}" | tail -n +2); do
    health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "no health check")
    echo "  $container: $health"
done

echo ""
echo "Resource Usage:"
docker stats --no-stream

echo ""
echo "Network Connectivity:"
for network in zaza-control zaza-coordination zaza-execution zaza-data zaza-monitoring; do
    count=$(docker network inspect $network --format='{{len .Containers}}' 2>/dev/null || echo "0")
    echo "  $network: $count containers"
done

echo ""
echo "API Endpoints:"
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "  Control API: ✓ Healthy" || echo "  Control API: ✗ Unhealthy"
curl -s http://localhost:8001/health > /dev/null 2>&1 && echo "  Coordination API: ✓ Healthy" || echo "  Coordination API: ✗ Unhealthy"

echo ""
echo "=== Health Check Complete ==="
HEALTH_EOF
    
    chmod +x ${DEPLOY_DIR}/scripts/health_check.sh
    
    # Create emergency shutdown script
    log_step "9/10: Creating emergency procedures..."
    cat > ${DEPLOY_DIR}/scripts/emergency_shutdown.sh <<'SHUTDOWN_EOF'
#!/bin/bash
cd /opt/zaza

echo "!!! EMERGENCY SHUTDOWN INITIATED !!!"
echo "Stopping all ZAZA services..."

# Stop all services
docker-compose -f docker-compose.zaza.yml down

# Stop all ZAZA containers (failsafe)
docker ps -a | grep zaza | awk '{print $1}' | xargs -r docker stop

echo "All services stopped."
echo "To restart, run: ./scripts/start_zaza.sh"
SHUTDOWN_EOF
    
    chmod +x ${DEPLOY_DIR}/scripts/emergency_shutdown.sh
    
    # Create SQL initialization
    log_step "10/10: Creating database initialization..."
    mkdir -p ${DEPLOY_DIR}/sql
    cat > ${DEPLOY_DIR}/sql/init.sql <<'SQL_EOF'
-- ZAZA UAT Database Initialization

-- Create schemas
CREATE SCHEMA IF NOT EXISTS control;
CREATE SCHEMA IF NOT EXISTS coordination;
CREATE SCHEMA IF NOT EXISTS execution;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Control layer tables
CREATE TABLE IF NOT EXISTS control.audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    agent_id VARCHAR(255),
    details JSONB,
    severity VARCHAR(20),
    hash VARCHAR(128) NOT NULL,
    previous_hash VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS control.ethics_violations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_id VARCHAR(255) NOT NULL,
    violation_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    details JSONB,
    resolution VARCHAR(50)
);

-- Coordination layer tables
CREATE TABLE IF NOT EXISTS coordination.teams (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(255) UNIQUE NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    team_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50),
    members JSONB
);

CREATE TABLE IF NOT EXISTS coordination.workflows (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    steps JSONB,
    results JSONB
);

-- Execution layer tables
CREATE TABLE IF NOT EXISTS execution.agent_states (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    state VARCHAR(50),
    memory JSONB,
    metrics JSONB
);

CREATE TABLE IF NOT EXISTS execution.tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    task_type VARCHAR(100),
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    input JSONB,
    output JSONB,
    error TEXT
);

-- Monitoring tables
CREATE TABLE IF NOT EXISTS monitoring.metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC,
    labels JSONB,
    PRIMARY KEY (timestamp, metric_name)
);

-- Create indexes
CREATE INDEX idx_audit_timestamp ON control.audit_log(timestamp DESC);
CREATE INDEX idx_audit_agent ON control.audit_log(agent_id);
CREATE INDEX idx_ethics_agent ON control.ethics_violations(agent_id);
CREATE INDEX idx_teams_status ON coordination.teams(status);
CREATE INDEX idx_workflows_status ON coordination.workflows(status);
CREATE INDEX idx_agent_states_agent ON execution.agent_states(agent_id);
CREATE INDEX idx_tasks_agent ON execution.tasks(agent_id);
CREATE INDEX idx_tasks_status ON execution.tasks(status);
CREATE INDEX idx_metrics_name ON monitoring.metrics(metric_name);

-- Create views
CREATE OR REPLACE VIEW monitoring.system_overview AS
SELECT 
    (SELECT COUNT(*) FROM coordination.teams WHERE status = 'active') as active_teams,
    (SELECT COUNT(*) FROM execution.tasks WHERE status = 'running') as running_tasks,
    (SELECT COUNT(*) FROM control.ethics_violations WHERE timestamp > NOW() - INTERVAL '24 hours') as recent_violations,
    (SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FROM execution.tasks WHERE completed_at IS NOT NULL AND started_at IS NOT NULL) as avg_task_duration;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA control TO zaza_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA coordination TO zaza_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA execution TO zaza_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO zaza_admin;
SQL_EOF
    
    log_info "ZAZA Deployment preparation complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Review configuration in ${DEPLOY_DIR}/.env"
    echo "  2. Build Docker images: docker-compose -f docker-compose.zaza.yml build"
    echo "  3. Start ZAZA: ./scripts/start_zaza.sh"
    echo "  4. Check health: ./scripts/health_check.sh"
    echo ""
    log_warn "Important: Save the generated passwords from .env file!"
}

# Run main function
main "$@"