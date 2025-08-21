# Docker Architecture for Agile AI Company

## Executive Summary

This document defines the Docker containerization strategy for the Agile AI Company framework, enabling scalable deployment of AI agent teams with proper isolation, resource management, and orchestration. The architecture supports both development and production environments with a focus on modularity, security, and performance.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Network Topology](#network-topology)
3. [Container Definitions](#container-definitions)
4. [Inter-Container Communication](#inter-container-communication)
5. [Resource Allocation Strategy](#resource-allocation-strategy)
6. [Container Naming Conventions](#container-naming-conventions)
7. [Docker Compose Configurations](#docker-compose-configurations)
8. [Scaling Strategy](#scaling-strategy)
9. [Security Architecture](#security-architecture)
10. [Deployment Patterns](#deployment-patterns)

## Architecture Overview

### Design Principles

1. **Layered Architecture**: Containers organized by functional layers (Control, Coordination, Execution)
2. **Network Isolation**: Separate networks for different security zones
3. **Resource Limits**: Explicit resource constraints for predictable performance
4. **Service Discovery**: DNS-based service discovery within networks
5. **Data Persistence**: Separated data volumes for stateful components
6. **Health Monitoring**: Built-in health checks and monitoring

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    External Access                       │
│              (Load Balancer / API Gateway)               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Frontend Network                       │
│                   (DMZ - Public Zone)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Web UI     │  │   API        │  │  WebSocket   │ │
│  │  Container   │  │  Gateway     │  │   Server     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Control Network                        │
│                (Secure Management Zone)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Control    │  │   Audit      │  │  Monitoring  │ │
│  │    Layer     │  │   Database   │  │   Stack      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Coordination Network                     │
│              (Internal Service Zone)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Coordinator  │  │   Workflow   │  │   Message    │ │
│  │  Container   │  │   Engine     │  │    Queue     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Execution Network                       │
│               (Agent Execution Zone)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Agent Team Containers                  │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐│  │
│  │  │Agent-1 │  │Agent-2 │  │Agent-3 │  │Agent-N ││  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘│  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Data Network                          │
│                 (Persistent Storage)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │   MinIO      │ │
│  │   Cluster    │  │   Cluster    │  │  (S3-like)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Network Topology

### Network Definitions

```yaml
networks:
  frontend-net:
    name: agile-frontend
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
    labels:
      zone: dmz
      
  control-net:
    name: agile-control
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.21.0.0/24
    labels:
      zone: secure
      
  coordination-net:
    name: agile-coordination
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.22.0.0/24
    labels:
      zone: internal
      
  execution-net:
    name: agile-execution
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.23.0.0/24
    labels:
      zone: compute
      
  data-net:
    name: agile-data
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.24.0.0/24
    labels:
      zone: storage
```

### Network Security Rules

| Source Network | Destination Network | Allowed Ports | Protocol |
|---------------|-------------------|---------------|----------|
| Frontend | Control | 8000 | HTTPS |
| Frontend | Coordination | 8001-8002 | HTTPS |
| Control | Data | 5432, 6379 | TCP |
| Coordination | Control | 8000 | HTTPS |
| Coordination | Execution | 9000-9999 | HTTP/WS |
| Coordination | Data | 5432, 6379 | TCP |
| Execution | Coordination | 8001-8002 | HTTPS |
| Execution | Data | 6379, 9000 | TCP |

## Container Definitions

### Control Layer Containers

```yaml
control-layer:
  container_name: agile-control-main
  image: agile-ai/control:${VERSION:-latest}
  hostname: control-main
  
  networks:
    - control-net
    - data-net
    
  ports:
    - "8000:8000"  # API (internal only)
    
  environment:
    - NODE_ENV=production
    - SERVICE_NAME=control-layer
    - LOG_LEVEL=${LOG_LEVEL:-info}
    
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
        
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### Coordination Layer Containers

```yaml
coordinator:
  container_name: agile-coordinator-main
  image: agile-ai/coordinator:${VERSION:-latest}
  hostname: coordinator-main
  
  networks:
    - control-net
    - coordination-net
    - execution-net
    - data-net
    
  environment:
    - SERVICE_NAME=coordinator
    - CONTROL_API=http://control-main:8000
    - MAX_TEAMS=${MAX_TEAMS:-10}
    - MAX_AGENTS_PER_TEAM=${MAX_AGENTS_PER_TEAM:-12}
    
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G
      reservations:
        cpus: '2.0'
        memory: 4G

workflow-engine:
  container_name: agile-workflow-engine
  image: agile-ai/workflow:${VERSION:-latest}
  hostname: workflow-engine
  
  networks:
    - coordination-net
    - data-net
    
  environment:
    - SERVICE_NAME=workflow-engine
    - COORDINATOR_API=http://coordinator-main:8001
    
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

### Execution Layer Containers (Agent Teams)

```yaml
# Template for agent containers
agent-template:
  image: agile-ai/agent:${VERSION:-latest}
  
  networks:
    - execution-net
    
  environment:
    - AGENT_PROFILE=${AGENT_PROFILE}
    - TEAM_ID=${TEAM_ID}
    - COORDINATOR_API=http://coordinator-main:8001
    - CONTROL_API=http://control-main:8000
    
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 1G
    
  restart: unless-stopped

# Dynamic agent scaling
product-team:
  extends:
    service: agent-template
  container_name: agile-team-product
  scale: 5  # 5 agents in product team
  environment:
    - TEAM_ID=team-product
    - TEAM_TYPE=product_development

development-team:
  extends:
    service: agent-template
  container_name: agile-team-dev
  scale: 8  # 8 agents in dev team
  environment:
    - TEAM_ID=team-development
    - TEAM_TYPE=engineering
```

### Data Layer Containers

```yaml
postgres-primary:
  container_name: agile-postgres-primary
  image: postgres:15-alpine
  hostname: postgres-primary
  
  networks:
    - data-net
    
  environment:
    - POSTGRES_DB=agile_ai
    - POSTGRES_USER=agile
    - POSTGRES_PASSWORD=${DB_PASSWORD}
    - POSTGRES_REPLICATION_MODE=master
    - POSTGRES_REPLICATION_USER=replicator
    - POSTGRES_REPLICATION_PASSWORD=${REPL_PASSWORD}
    
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./init-scripts:/docker-entrypoint-initdb.d
    
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G

redis-master:
  container_name: agile-redis-master
  image: redis:7-alpine
  hostname: redis-master
  
  networks:
    - data-net
    
  command: redis-server /usr/local/etc/redis/redis.conf
  
  volumes:
    - redis-data:/data
    - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

## Inter-Container Communication

### Communication Patterns

#### 1. Synchronous HTTP/HTTPS
```yaml
# REST API calls between services
control-api:
  base_url: http://control-main:8000/api/v1
  timeout: 30s
  retry_policy:
    max_attempts: 3
    backoff: exponential

coordinator-api:
  base_url: http://coordinator-main:8001/api/v1
  timeout: 30s
```

#### 2. Asynchronous Messaging (Redis Pub/Sub)
```yaml
message_broker:
  type: redis
  host: redis-master
  port: 6379
  channels:
    - agent-events
    - team-coordination
    - workflow-updates
    - system-alerts
```

#### 3. WebSocket Connections
```yaml
websocket:
  server: ws://coordinator-main:8002
  heartbeat_interval: 30s
  reconnect_policy:
    enabled: true
    max_attempts: 10
    delay: 5s
```

#### 4. gRPC for High-Performance IPC
```yaml
grpc:
  services:
    - name: agent-communication
      port: 9000
      max_message_size: 4MB
    - name: workflow-orchestration
      port: 9001
      max_message_size: 1MB
```

### Service Discovery

```yaml
# DNS-based service discovery
service_registry:
  control-layer:
    hostname: control-main
    port: 8000
    health: /health
    
  coordinator:
    hostname: coordinator-main
    port: 8001
    health: /health
    
  workflow-engine:
    hostname: workflow-engine
    port: 8003
    health: /health
    
  postgres:
    hostname: postgres-primary
    port: 5432
    
  redis:
    hostname: redis-master
    port: 6379
```

## Resource Allocation Strategy

### Resource Tiers

```yaml
resource_tiers:
  critical:
    # Control Layer, Coordinator
    cpu_guarantee: 100%  # Of requested
    memory_guarantee: 100%
    priority: 1000
    
  standard:
    # Workflow Engine, Standard Agents
    cpu_guarantee: 50%
    memory_guarantee: 75%
    priority: 500
    
  elastic:
    # Non-critical agents, batch jobs
    cpu_guarantee: 20%
    memory_guarantee: 50%
    priority: 100
```

### Container Resource Profiles

| Container Type | CPU Request | CPU Limit | Memory Request | Memory Limit | GPU |
|---------------|------------|-----------|----------------|--------------|-----|
| Control Layer | 1.0 | 2.0 | 2G | 4G | 0 |
| Coordinator | 2.0 | 4.0 | 4G | 8G | 0 |
| Workflow Engine | 1.0 | 2.0 | 2G | 4G | 0 |
| Standard Agent | 0.5 | 1.0 | 1G | 2G | 0 |
| ML Agent | 1.0 | 2.0 | 2G | 4G | 0.5 |
| Database | 2.0 | 4.0 | 4G | 8G | 0 |
| Cache | 1.0 | 2.0 | 2G | 4G | 0 |

### Dynamic Resource Allocation

```python
class ResourceAllocator:
    def allocate_team_resources(self, team_spec):
        """Dynamically allocate resources for a team."""
        
        base_resources = {
            'product_team': {
                'agents': 5,
                'cpu_per_agent': 0.5,
                'memory_per_agent': '1G'
            },
            'development_team': {
                'agents': 8,
                'cpu_per_agent': 1.0,
                'memory_per_agent': '2G'
            },
            'qa_team': {
                'agents': 4,
                'cpu_per_agent': 0.75,
                'memory_per_agent': '1.5G'
            }
        }
        
        return base_resources.get(team_spec['type'])
```

## Container Naming Conventions

### Naming Pattern

```
{prefix}-{layer}-{component}-{instance}
```

### Naming Rules

| Component | Pattern | Example |
|-----------|---------|---------|
| Control Layer | `agile-control-{component}` | `agile-control-ethics` |
| Coordinator | `agile-coord-{component}` | `agile-coord-orchestrator` |
| Agent | `agile-agent-{team}-{role}-{id}` | `agile-agent-product-pm-001` |
| Database | `agile-db-{type}-{role}` | `agile-db-postgres-primary` |
| Cache | `agile-cache-{type}-{role}` | `agile-cache-redis-master` |
| Support | `agile-support-{component}` | `agile-support-monitoring` |

### Labels and Metadata

```yaml
labels:
  app: agile-ai
  version: ${VERSION}
  layer: ${LAYER}  # control, coordination, execution
  component: ${COMPONENT}
  team: ${TEAM_ID}
  environment: ${ENV}  # dev, staging, prod
  managed-by: docker-compose
```

## Docker Compose Configurations

### Development Environment

```yaml
# docker-compose.dev.yml
version: '3.9'

x-common-variables: &common-variables
  LOG_LEVEL: debug
  ENVIRONMENT: development
  ENABLE_DEBUG: "true"

services:
  # Single control layer for dev
  control:
    extends:
      file: docker-compose.base.yml
      service: control-layer
    ports:
      - "8000:8000"
      - "8010:8010"  # Debug port
    environment:
      <<: *common-variables
    volumes:
      - ./control:/app  # Mount source for hot reload
      - /app/node_modules  # Exclude node_modules
    
  # Single coordinator for dev
  coordinator:
    extends:
      file: docker-compose.base.yml
      service: coordinator
    ports:
      - "8001:8001"
      - "8011:8011"  # Debug port
    environment:
      <<: *common-variables
    volumes:
      - ./coordination:/app
    
  # Minimal agent team for dev
  dev-agents:
    extends:
      file: docker-compose.base.yml
      service: agent-template
    scale: 3
    environment:
      <<: *common-variables
      TEAM_ID: dev-team
    
  # Single postgres for dev
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: devpassword
    ports:
      - "5432:5432"
    
  # Single redis for dev
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Production Environment

```yaml
# docker-compose.prod.yml
version: '3.9'

x-deploy-policy: &deploy-policy
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
    window: 120s

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - frontend-net
    deploy:
      <<: *deploy-policy
      replicas: 2
  
  # Control Layer Cluster
  control:
    extends:
      file: docker-compose.base.yml
      service: control-layer
    deploy:
      <<: *deploy-policy
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      placement:
        constraints:
          - node.role == manager
  
  # Coordinator Cluster
  coordinator:
    extends:
      file: docker-compose.base.yml
      service: coordinator
    deploy:
      <<: *deploy-policy
      replicas: 2
      placement:
        preferences:
          - spread: node.id
  
  # Agent Teams
  product-team:
    extends:
      file: docker-compose.base.yml
      service: agent-template
    deploy:
      <<: *deploy-policy
      replicas: 5
      placement:
        preferences:
          - spread: node.id
    environment:
      TEAM_ID: product
      AGENT_PROFILE: product_manager
  
  development-team:
    extends:
      file: docker-compose.base.yml
      service: agent-template
    deploy:
      <<: *deploy-policy
      replicas: 8
      placement:
        preferences:
          - spread: node.id
    environment:
      TEAM_ID: development
      AGENT_PROFILE: developer
  
  # PostgreSQL Cluster
  postgres-primary:
    extends:
      file: docker-compose.base.yml
      service: postgres-primary
    deploy:
      <<: *deploy-policy
      placement:
        constraints:
          - node.labels.db == primary
  
  postgres-replica:
    image: postgres:15-alpine
    environment:
      - POSTGRES_REPLICATION_MODE=slave
      - POSTGRES_MASTER_HOST=postgres-primary
    deploy:
      <<: *deploy-policy
      replicas: 2
  
  # Redis Cluster
  redis-master:
    extends:
      file: docker-compose.base.yml
      service: redis-master
    deploy:
      <<: *deploy-policy
      placement:
        constraints:
          - node.labels.cache == primary
  
  redis-slave:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379
    deploy:
      <<: *deploy-policy
      replicas: 2
```

### Docker Compose Override Structure

```yaml
# docker-compose.override.yml (for local development)
version: '3.9'

services:
  control:
    build:
      context: ./control
      dockerfile: Dockerfile.dev
    volumes:
      - ./control:/app
      - /app/node_modules
    environment:
      - DEBUG=true
      - HOT_RELOAD=true
  
  coordinator:
    build:
      context: ./coordination
      dockerfile: Dockerfile.dev
    volumes:
      - ./coordination:/app
```

## Scaling Strategy

### Horizontal Scaling

```yaml
scaling_policies:
  agent_teams:
    min_replicas: 2
    max_replicas: 20
    target_cpu_utilization: 70
    target_memory_utilization: 80
    scale_up_rate: 2  # Double capacity
    scale_down_rate: 0.5  # Halve capacity
    cooldown_period: 300  # 5 minutes
  
  coordinators:
    min_replicas: 2
    max_replicas: 5
    target_request_rate: 1000  # req/s
    scale_up_threshold: 90  # % of target
    scale_down_threshold: 30  # % of target
```

### Vertical Scaling

```bash
# Dynamic resource adjustment script
#!/bin/bash
update_container_resources() {
  local container=$1
  local cpu=$2
  local memory=$3
  
  docker update \
    --cpus="$cpu" \
    --memory="$memory" \
    "$container"
}

# Scale up during peak hours
scale_up_peak() {
  update_container_resources "agile-coord-main" "4.0" "8G"
  update_container_resources "agile-control-main" "2.0" "4G"
}

# Scale down during off-peak
scale_down_offpeak() {
  update_container_resources "agile-coord-main" "2.0" "4G"
  update_container_resources "agile-control-main" "1.0" "2G"
}
```

### Auto-scaling Rules

```python
class AutoScaler:
    def __init__(self):
        self.metrics = MetricsCollector()
        self.docker = DockerClient()
    
    def evaluate_scaling(self, service_name):
        """Evaluate if scaling is needed."""
        
        metrics = self.metrics.get_service_metrics(service_name)
        
        if metrics['cpu_usage'] > 80:
            return self.scale_up(service_name)
        elif metrics['cpu_usage'] < 30 and metrics['replicas'] > 2:
            return self.scale_down(service_name)
    
    def scale_up(self, service_name):
        current = self.docker.get_replicas(service_name)
        new_count = min(current * 2, MAX_REPLICAS[service_name])
        return self.docker.scale(service_name, new_count)
    
    def scale_down(self, service_name):
        current = self.docker.get_replicas(service_name)
        new_count = max(current // 2, MIN_REPLICAS[service_name])
        return self.docker.scale(service_name, new_count)
```

## Security Architecture

### Container Security

```dockerfile
# Security-hardened base image
FROM alpine:3.18

# Non-root user
RUN addgroup -g 1000 agile && \
    adduser -D -u 1000 -G agile agile

# Security updates
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        ca-certificates \
        dumb-init && \
    rm -rf /var/cache/apk/*

# Read-only root filesystem
USER agile
WORKDIR /app

# Security labels
LABEL security.scan="true" \
      security.nonroot="true" \
      security.caps_drop="ALL"
```

### Network Security

```yaml
security_policies:
  network_policies:
    - name: deny-all-ingress
      spec:
        podSelector: {}
        policyTypes:
          - Ingress
    
    - name: allow-control-to-data
      spec:
        podSelector:
          matchLabels:
            layer: data
        ingress:
          - from:
              - podSelector:
                  matchLabels:
                    layer: control
            ports:
              - protocol: TCP
                port: 5432
              - protocol: TCP
                port: 6379
```

### Secrets Management

```yaml
secrets:
  # Use Docker secrets for sensitive data
  db_password:
    external: true
    external_name: agile_db_password
  
  api_keys:
    external: true
    external_name: agile_api_keys
  
  certificates:
    file: ./certs/server.crt
    
services:
  control:
    secrets:
      - db_password
      - api_keys
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
```

### Security Scanning

```bash
#!/bin/bash
# Container security scanning script

scan_image() {
  local image=$1
  
  # Scan with Trivy
  trivy image --severity HIGH,CRITICAL "$image"
  
  # Scan with Clair
  clair-scanner --ip localhost "$image"
  
  # Check for rootless
  docker run --rm "$image" whoami | grep -v root
}

# Scan all images
for image in $(docker-compose config --images); do
  scan_image "$image"
done
```

## Deployment Patterns

### Blue-Green Deployment

```yaml
# Blue environment (current)
blue:
  extends:
    file: docker-compose.base.yml
    service: agent-template
  container_name: agile-agents-blue
  networks:
    - blue-net
  labels:
    environment: blue
    active: "true"

# Green environment (new)
green:
  extends:
    file: docker-compose.base.yml
    service: agent-template
  container_name: agile-agents-green
  networks:
    - green-net
  labels:
    environment: green
    active: "false"

# Traffic router
router:
  image: traefik:v2.10
  command:
    - --providers.docker=true
    - --providers.docker.exposedbydefault=false
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.api.rule=Host(`api.agile.local`)"
```

### Rolling Update

```bash
#!/bin/bash
# Rolling update script

rolling_update() {
  local service=$1
  local new_image=$2
  
  # Update service with rolling strategy
  docker service update \
    --image "$new_image" \
    --update-parallelism 2 \
    --update-delay 30s \
    --update-failure-action rollback \
    --update-monitor 5m \
    --update-max-failure-ratio 0.25 \
    "$service"
}
```

### Canary Deployment

```yaml
# Canary deployment configuration
canary:
  strategy: weighted
  stages:
    - weight: 10  # 10% traffic
      duration: 1h
      metrics:
        error_rate: "< 1%"
        latency_p99: "< 200ms"
    
    - weight: 50  # 50% traffic
      duration: 2h
      metrics:
        error_rate: "< 0.5%"
        latency_p99: "< 150ms"
    
    - weight: 100  # Full rollout
      duration: stable
```

## Monitoring and Observability

### Health Checks

```yaml
healthcheck:
  control:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
  
  coordinator:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  
  agent:
    test: ["CMD", "/app/healthcheck.sh"]
    interval: 60s
    timeout: 30s
    retries: 5
```

### Logging Configuration

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    labels: "app,layer,component,team"
    env: "ENVIRONMENT,SERVICE_NAME"
    
# Centralized logging with Fluentd
fluentd:
  image: fluent/fluentd:v1.16-debian
  volumes:
    - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
  ports:
    - "24224:24224"
  networks:
    - monitoring-net
```

### Metrics Collection

```yaml
# Prometheus metrics
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
  ports:
    - "9090:9090"
  networks:
    - monitoring-net

# Grafana dashboards
grafana:
  image: grafana/grafana:latest
  volumes:
    - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    - grafana-data:/var/lib/grafana
  ports:
    - "3000:3000"
  networks:
    - monitoring-net
```

## Disaster Recovery

### Backup Strategy

```yaml
backup:
  databases:
    postgres:
      schedule: "0 2 * * *"  # Daily at 2 AM
      retention: 30  # days
      destination: s3://backups/postgres/
    
    redis:
      schedule: "0 */6 * * *"  # Every 6 hours
      retention: 7  # days
      destination: s3://backups/redis/
  
  volumes:
    agent-data:
      schedule: "0 3 * * *"  # Daily at 3 AM
      retention: 14  # days
      destination: s3://backups/volumes/
```

### Recovery Procedures

```bash
#!/bin/bash
# Disaster recovery script

restore_system() {
  local backup_date=$1
  
  # Stop all services
  docker-compose down
  
  # Restore databases
  restore_postgres "$backup_date"
  restore_redis "$backup_date"
  
  # Restore volumes
  restore_volumes "$backup_date"
  
  # Start services
  docker-compose up -d
  
  # Verify health
  wait_for_healthy
}
```

## Performance Optimization

### Image Optimization

```dockerfile
# Multi-stage build for smaller images
FROM node:18-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

FROM alpine:3.18
RUN apk add --no-cache nodejs
COPY --from=builder /build/node_modules ./node_modules
COPY . .
CMD ["node", "index.js"]
```

### Caching Strategy

```yaml
# Build cache configuration
build:
  cache_from:
    - type=registry,ref=agile-ai/cache:control
    - type=registry,ref=agile-ai/cache:coordinator
  cache_to:
    - type=registry,ref=agile-ai/cache:control,mode=max
    - type=registry,ref=agile-ai/cache:coordinator,mode=max
```

### Resource Optimization

```yaml
# Resource optimization settings
sysctls:
  - net.core.somaxconn=65535
  - net.ipv4.tcp_syncookies=1
  - net.ipv4.ip_local_port_range=1024 65535

ulimits:
  nofile:
    soft: 65536
    hard: 65536
  nproc:
    soft: 32768
    hard: 32768
```

## Development Workflow

### Local Development Setup

```bash
#!/bin/bash
# Development environment setup

setup_dev() {
  # Create networks
  docker network create agile-dev
  
  # Start core services
  docker-compose -f docker-compose.dev.yml up -d postgres redis
  
  # Wait for databases
  wait_for_service postgres 5432
  wait_for_service redis 6379
  
  # Run migrations
  docker-compose run --rm control npm run migrate
  
  # Start application services
  docker-compose -f docker-compose.dev.yml up
}
```

### Testing Environment

```yaml
# docker-compose.test.yml
version: '3.9'

services:
  test-runner:
    build:
      context: .
      target: test
    command: npm test
    environment:
      - NODE_ENV=test
      - DB_HOST=test-postgres
      - REDIS_HOST=test-redis
    depends_on:
      - test-postgres
      - test-redis
  
  test-postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=test
      - POSTGRES_PASSWORD=test
    tmpfs:
      - /var/lib/postgresql/data
  
  test-redis:
    image: redis:7-alpine
    tmpfs:
      - /data
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/docker-build.yml
name: Docker Build and Push

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Troubleshooting Guide

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Container OOM | Container killed with exit code 137 | Increase memory limits |
| Network timeout | Connection refused between containers | Check network configuration and firewall rules |
| Slow startup | Containers take long to become healthy | Increase health check start_period |
| Volume permissions | Permission denied errors | Ensure proper user/group ownership |
| Port conflicts | Bind address already in use | Check for conflicting services |

### Debugging Commands

```bash
# View container logs
docker-compose logs -f [service_name]

# Inspect container
docker inspect [container_name]

# Execute commands in container
docker-compose exec [service_name] sh

# View resource usage
docker stats

# Network debugging
docker network inspect agile-control

# Clean up
docker system prune -a --volumes
```

## Conclusion

This Docker architecture provides a robust, scalable, and secure foundation for deploying the Agile AI Company framework. The layered approach ensures proper isolation and resource management while maintaining flexibility for both development and production deployments. The architecture supports horizontal and vertical scaling, comprehensive monitoring, and disaster recovery procedures, making it suitable for enterprise-grade deployments.