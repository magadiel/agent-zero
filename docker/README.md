# Control Layer Docker Setup

This directory contains Docker configurations for containerizing the Agile AI Control Layer.

## Architecture

The Control Layer runs in a multi-container Docker environment with the following services:

- **control-layer**: Main API service providing ethics, safety, resource, and audit functionality
- **redis**: In-memory data store for caching and pub/sub messaging
- **postgres**: Production database for audit trails (optional, SQLite by default)
- **nginx**: Reverse proxy for load balancing and SSL termination (production only)

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB available RAM
- 10GB available disk space

### Development Setup

1. **Clone and navigate to docker directory:**
```bash
cd agent-zero/docker
```

2. **Copy environment file:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and start containers:**
```bash
./build.sh
# Or for development mode:
./build.sh --dev
```

4. **Verify installation:**
```bash
python3 test_container.py
```

5. **Access the API:**
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Main API: http://localhost:8000/api/v1/

### Production Setup

1. **Configure environment:**
```bash
cp .env.example .env
# Update with production values:
# - Set strong API_KEY and JWT_SECRET
# - Configure DATABASE_URL for PostgreSQL
# - Set appropriate resource limits
```

2. **Build for production:**
```bash
./build.sh --production
```

3. **Configure SSL (optional):**
- Add SSL certificates to `nginx/certs/`
- Update `nginx/conf.d/control-api.conf` with SSL configuration

## Container Management

### Starting Containers

```bash
# Development
docker-compose -f docker-compose.control.yml -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.control.yml up -d
```

### Stopping Containers

```bash
docker-compose -f docker-compose.control.yml down

# Remove volumes (warning: deletes data)
docker-compose -f docker-compose.control.yml down -v
```

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.control.yml logs -f

# Specific service
docker-compose -f docker-compose.control.yml logs -f control-layer
```

### Scaling Services

```bash
# Scale control layer to 3 instances
docker-compose -f docker-compose.control.yml up -d --scale control-layer=3
```

## Configuration

### Environment Variables

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| CONTROL_API_KEY | API authentication key | `default-dev-key` |
| JWT_SECRET | JWT signing secret | `change-me-in-production` |
| DATABASE_URL | Database connection string | `sqlite:///app/control/storage/audit.db` |
| REDIS_URL | Redis connection string | `redis://redis:6379/0` |
| LOG_LEVEL | Logging level | `INFO` |
| MAX_WORKERS | Number of API workers | `4` |

### Resource Limits

Default resource limits per container:

- **Control Layer**: 2 CPU cores, 2GB RAM
- **Redis**: 1 CPU core, 512MB RAM
- **PostgreSQL**: 2 CPU cores, 1GB RAM

Adjust in `docker-compose.control.yml` under `deploy.resources`.

### Networking

The setup uses two networks:

- **agile-network** (172.20.0.0/16): External-facing network
- **control-network**: Internal network for database access

### Volumes

Persistent data is stored in named volumes:

- `control-storage`: SQLite database and persistent files
- `control-logs`: Application logs
- `redis-data`: Redis persistence
- `postgres-data`: PostgreSQL data (if used)

## Testing

### Run Container Tests

```bash
python3 test_container.py
```

This tests:
- Health check endpoint
- API documentation
- Ethics validation
- Safety monitoring
- Resource allocation
- Audit logging
- Authentication

### Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils

# Run load test
ab -n 1000 -c 10 -H "X-API-Key: your-api-key" http://localhost:8000/health
```

## Monitoring

### Health Checks

The control layer includes built-in health checks:

```bash
# Check health
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "timestamp": "2025-08-21T12:00:00Z",
  "components": {
    "api": "up",
    "database": "up",
    "redis": "up"
  }
}
```

### Metrics

Prometheus-compatible metrics available at:
```bash
curl http://localhost:8000/metrics
```

### Logs

Logs are stored in JSON format for easy parsing:

```bash
# View logs
docker logs agile-ai-control

# Parse JSON logs
docker logs agile-ai-control | jq '.'
```

## Troubleshooting

### Container Won't Start

1. Check logs:
```bash
docker-compose -f docker-compose.control.yml logs control-layer
```

2. Verify ports are available:
```bash
netstat -tulpn | grep -E '8000|6379|5432'
```

3. Check disk space:
```bash
docker system df
```

### API Returns 401 Unauthorized

1. Verify API key in `.env`
2. Include header in requests:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/audit/logs
```

### Database Connection Issues

1. For SQLite, verify volume mount:
```bash
docker exec agile-ai-control ls -la /app/control/storage/
```

2. For PostgreSQL, check connection:
```bash
docker exec agile-ai-postgres pg_isready
```

### Performance Issues

1. Check resource usage:
```bash
docker stats agile-ai-control
```

2. Increase resource limits in `docker-compose.control.yml`

3. Scale horizontally:
```bash
docker-compose -f docker-compose.control.yml up -d --scale control-layer=3
```

## Security Considerations

### Production Checklist

- [ ] Change default API keys and secrets
- [ ] Enable SSL/TLS with valid certificates
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up log rotation
- [ ] Configure backup strategy
- [ ] Implement rate limiting
- [ ] Use PostgreSQL instead of SQLite
- [ ] Run containers as non-root user
- [ ] Enable Docker security options (AppArmor/SELinux)

### Secret Management

For production, use Docker secrets or external secret management:

```yaml
# docker-compose with secrets
secrets:
  api_key:
    external: true
  jwt_secret:
    external: true
```

## Backup and Recovery

### Backup

```bash
# Backup volumes
docker run --rm -v control-storage:/data -v $(pwd):/backup alpine tar czf /backup/control-backup.tar.gz /data

# Backup database (PostgreSQL)
docker exec agile-ai-postgres pg_dump -U control_user control_db > backup.sql
```

### Restore

```bash
# Restore volumes
docker run --rm -v control-storage:/data -v $(pwd):/backup alpine tar xzf /backup/control-backup.tar.gz -C /

# Restore database (PostgreSQL)
docker exec -i agile-ai-postgres psql -U control_user control_db < backup.sql
```

## Integration with Other Services

### Connecting Coordination Layer

Add to coordination layer's docker-compose:

```yaml
networks:
  - agile-network

environment:
  CONTROL_API_URL: http://control-layer:8000
```

### Connecting Execution Teams

Configure agent containers:

```yaml
environment:
  CONTROL_API_URL: http://control-layer:8000
  CONTROL_API_KEY: ${CONTROL_API_KEY}
```

## Development

### Local Development

For local development without Docker:

```bash
cd ../control
pip install -r requirements.txt
uvicorn api:app --reload
```

### Adding New Dependencies

1. Update `control/requirements.txt`
2. Rebuild container:
```bash
docker-compose -f docker-compose.control.yml build --no-cache control-layer
```

### Debugging

Enable debug mode:

```yaml
# docker-compose.dev.yml
environment:
  - DEBUG=true
  - LOG_LEVEL=DEBUG
```

Attach to running container:
```bash
docker exec -it agile-ai-control /bin/bash
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review this README
3. Check `/control/README.md` for API documentation
4. Submit issues to the project repository

## License

This Docker configuration is part of the Agent-Zero Agile AI project.