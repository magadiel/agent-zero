# Multi-Container Integration Documentation

## Overview

This document describes the multi-container integration for the Agile AI Company system built on Agent-Zero. The integration combines three layers of functionality with supporting services to create a complete autonomous AI organization.

## Architecture

### Layer Structure

```
┌─────────────────────────────────────────┐
│         CONTROL LAYER                    │
│   Ethics | Safety | Audit | Resources    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       COORDINATION LAYER                 │
│  Workflows | Teams | Documents | Agile   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        EXECUTION LAYER                   │
│    Agent Teams | Task Execution          │
└─────────────────────────────────────────┘
```

### Network Topology

- **control-network** (172.20.0.0/24): Control layer and databases
- **coordination-network** (172.21.0.0/24): Coordination services
- **execution-network** (172.22.0.0/24): Agent teams
- **monitoring-network** (172.23.0.0/24): Metrics and observability

## Components

### Control Layer
- **Container**: `agile-ai-control`
- **Port**: 8000
- **Features**: Ethics validation, safety monitoring, resource allocation, audit logging
- **Resources**: 2 CPU cores, 2GB memory

### Coordination Layer
- **Container**: `agile-ai-coordinator`
- **Port**: 8001 (WebUI), 8002 (API), 9001 (A2A)
- **Features**: Workflow orchestration, team management, document handoffs
- **Resources**: 2 CPU cores, 3GB memory

### Execution Teams

#### Customer Value Team (5 agents)
- Product Manager
- Developer
- QA Engineer
- Architect
- Scrum Master

#### Operations Team (3 agents)
- Scrum Master
- Developer
- QA Engineer

#### Innovation Lab (7 agents, scalable)
- Research-focused agents
- Can scale horizontally: `docker-compose up -d --scale team-innovation=10`

### Supporting Services

#### Redis
- **Container**: `agile-ai-redis`
- **Port**: 6379
- **Purpose**: Caching, pub/sub messaging, inter-service communication

#### PostgreSQL
- **Container**: `agile-ai-postgres`
- **Port**: 5432
- **Purpose**: Audit trail, persistent data storage

#### Nginx
- **Container**: `agile-ai-nginx`
- **Ports**: 80, 443
- **Purpose**: Reverse proxy, load balancing

#### Prometheus
- **Container**: `agile-ai-prometheus`
- **Port**: 9090
- **Purpose**: Metrics collection

#### Grafana
- **Container**: `agile-ai-grafana`
- **Port**: 3000
- **Purpose**: Metrics visualization

## Quick Start

### 1. Build and Start All Services

```bash
# Build all containers
docker-compose -f docker/docker-compose.yml build

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps
```

### 2. Verify Services

```bash
# Run integration tests
./docker/integration-tests.sh

# Or use Python test suite
python3 docker/test_communication.py
```

### 3. Access Services

- Control API: http://localhost:8000
- Coordinator WebUI: http://localhost:8001
- Grafana Dashboard: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## Testing

### Integration Tests

The `integration-tests.sh` script tests:
1. Container health checks
2. API endpoint accessibility
3. Inter-container communication
4. Resource allocation limits
5. Network isolation
6. Data persistence volumes
7. Security features
8. Scaling capabilities

### Communication Tests

The `test_communication.py` script provides:
- Container status verification
- HTTP endpoint testing
- Container-to-container communication
- Database connectivity
- Network membership validation
- Volume persistence checks

## Configuration

### Environment Variables

Create a `.env` file in the docker directory:

```env
# Control Layer
CONTROL_ENV=production
CONTROL_API_KEY=your-secure-api-key
JWT_SECRET=your-jwt-secret

# Database
POSTGRES_DB=agile_ai_db
POSTGRES_USER=agile_user
POSTGRES_PASSWORD=secure_password

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_admin_password

# Logging
LOG_LEVEL=INFO
```

### Resource Limits

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## Operations

### Scaling Teams

```bash
# Scale innovation team to 10 agents
docker-compose -f docker/docker-compose.yml up -d --scale team-innovation=10

# Scale down
docker-compose -f docker/docker-compose.yml up -d --scale team-innovation=5
```

### Monitoring

Access Grafana at http://localhost:3000 to view:
- Team performance metrics
- Resource utilization
- Task completion rates
- System health

### Logs

```bash
# View logs for specific service
docker-compose -f docker/docker-compose.yml logs -f control-layer

# View all logs
docker-compose -f docker/docker-compose.yml logs -f

# Save logs to file
docker-compose -f docker/docker-compose.yml logs > system.log
```

### Backup

```bash
# Backup volumes
docker run --rm -v control-storage:/data -v $(pwd):/backup alpine tar czf /backup/control-backup.tar.gz /data
docker run --rm -v postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore volumes
docker run --rm -v control-storage:/data -v $(pwd):/backup alpine tar xzf /backup/control-backup.tar.gz -C /
```

## Troubleshooting

### Container Won't Start

1. Check logs: `docker-compose logs <service-name>`
2. Verify port availability: `netstat -an | grep <port>`
3. Check Docker resources: `docker system df`

### Communication Failures

1. Verify network connectivity: `docker network ls`
2. Test from inside container: `docker exec -it <container> ping <target>`
3. Check firewall rules

### Performance Issues

1. Monitor resources: `docker stats`
2. Check Prometheus metrics: http://localhost:9090
3. Review container limits in docker-compose.yml

## Security Considerations

1. **Network Isolation**: Services are segregated into different networks
2. **Resource Limits**: Each container has CPU and memory limits
3. **Read-Only Volumes**: Configuration files mounted as read-only
4. **Authentication**: JWT tokens for API access
5. **Audit Trail**: All actions logged to immutable audit log

## Development Mode

For development with hot-reload:

```bash
# Use development override
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

## Production Deployment

For production:

1. Use environment-specific `.env` files
2. Enable SSL/TLS in Nginx configuration
3. Set up proper backup strategies
4. Configure monitoring alerts
5. Implement log aggregation
6. Set up container orchestration (Kubernetes/Swarm)

## Next Steps

1. Configure SSL certificates for HTTPS
2. Set up monitoring alerts in Prometheus
3. Create custom Grafana dashboards
4. Implement automated backups
5. Add health check endpoints to all services
6. Configure log aggregation with ELK stack

## Support

For issues or questions:
- Check container logs
- Run integration tests
- Review this documentation
- Consult the main project documentation