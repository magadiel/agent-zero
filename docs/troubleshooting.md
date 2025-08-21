# Agile AI Company - Troubleshooting Guide

## Table of Contents
1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Docker Issues](#docker-issues)
4. [Agent Problems](#agent-problems)
5. [Workflow Issues](#workflow-issues)
6. [Performance Problems](#performance-problems)
7. [API Errors](#api-errors)
8. [Database Issues](#database-issues)
9. [Network Problems](#network-problems)
10. [Security Issues](#security-issues)
11. [Debugging Tools](#debugging-tools)
12. [Log Analysis](#log-analysis)
13. [Recovery Procedures](#recovery-procedures)
14. [Getting Help](#getting-help)

## Common Issues

### System Won't Start

**Symptoms:**
- Docker containers fail to start
- Services show as unhealthy
- Web UI not accessible

**Solutions:**

1. **Check Docker status:**
```bash
docker-compose ps
docker-compose logs
```

2. **Verify prerequisites:**
```bash
docker --version  # Should be 20.10+
docker-compose --version  # Should be 1.29+
python --version  # Should be 3.8+
```

3. **Check resource availability:**
```bash
docker system df
free -h  # Linux
# Ensure at least 4GB RAM free
```

4. **Clean and restart:**
```bash
docker-compose down -v
docker system prune -af
docker-compose up -d
```

### Agent Not Responding

**Symptoms:**
- Agent shows as "unresponsive"
- Commands timeout
- No task progress

**Solutions:**

1. **Check agent status:**
```python
from agent import Agent
agent = Agent.get("agent-123")
print(agent.status)
print(agent.last_heartbeat)
```

2. **Restart agent:**
```python
agent.restart()
# or
docker-compose restart agent-service
```

3. **Check resource limits:**
```bash
docker stats agent-container
```

### Workflow Stuck

**Symptoms:**
- Workflow not progressing
- Steps timing out
- Documents not being created

**Solutions:**

1. **Check workflow status:**
```python
from coordination.workflow_engine import WorkflowEngine
engine = WorkflowEngine()
status = engine.get_status("workflow-123")
print(status.current_step)
print(status.blocked_reason)
```

2. **Force step completion:**
```python
engine.force_complete_step("workflow-123", "stuck-step")
```

3. **Cancel and retry:**
```python
engine.cancel("workflow-123")
new_execution = engine.execute("workflow-name", context)
```

## Installation Problems

### Dependencies Not Installing

**Problem:** `pip install` fails with dependency conflicts

**Solution:**
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install with no cache
pip install --no-cache-dir -r requirements.txt
```

### Permission Denied Errors

**Problem:** Cannot write to directories or execute scripts

**Solution:**
```bash
# Linux/Mac
chmod +x scripts/*.sh
chmod 755 control/
chmod 755 coordination/

# Fix Docker socket permissions
sudo usermod -aG docker $USER
# Log out and back in
```

### Port Already in Use

**Problem:** Cannot bind to port (e.g., 8000, 8001)

**Solution:**
```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Or change port in docker-compose.yml
```

## Docker Issues

### Container Keeps Restarting

**Problem:** Container in restart loop

**Diagnosis:**
```bash
docker logs container-name --tail 50
docker inspect container-name
```

**Common Causes & Solutions:**

1. **Out of memory:**
```yaml
# Increase memory limit in docker-compose.yml
services:
  service-name:
    mem_limit: 2g  # Increase from 1g
```

2. **Missing environment variables:**
```bash
# Check .env file
cat docker/.env
# Ensure all required vars are set
```

3. **Health check failing:**
```yaml
# Adjust health check in docker-compose.yml
healthcheck:
  interval: 60s  # Increase from 30s
  timeout: 10s   # Increase from 5s
  retries: 5     # Increase from 3
```

### Docker Network Issues

**Problem:** Containers cannot communicate

**Solution:**
```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d

# Verify network
docker network inspect agent-zero_default
```

### Volume Mount Problems

**Problem:** Files not persisting or permission errors

**Solution:**
```bash
# Check volume mounts
docker inspect container-name | grep -A 5 Mounts

# Fix permissions
docker exec container-name chown -R 1000:1000 /data

# For Windows, use absolute paths
# C:/Users/username/project:/app
```

## Agent Problems

### Agent Memory Overflow

**Symptoms:**
- Agent consuming excessive memory
- Slow response times
- Out of memory errors

**Solutions:**

1. **Clear agent memory:**
```python
agent.memory.clear_old_entries(days=7)
agent.memory.consolidate()
```

2. **Adjust memory limits:**
```python
agent.config.max_memory_mb = 512
agent.config.max_context_tokens = 4000
```

3. **Enable memory pruning:**
```python
agent.config.auto_prune = True
agent.config.prune_threshold = 0.8
```

### Agent Not Learning

**Symptoms:**
- Repeating same mistakes
- Not improving performance
- Memory not persisting

**Solutions:**

1. **Check learning configuration:**
```python
print(agent.learning_enabled)
print(agent.memory_persistence)
```

2. **Verify memory storage:**
```bash
ls -la agents/agent-name/memory/
```

3. **Force memory save:**
```python
agent.memory.save()
agent.learning.consolidate()
```

### Agent Command Failures

**Symptoms:**
- Commands not recognized
- Parameters rejected
- Execution errors

**Solutions:**

1. **Verify command registration:**
```python
print(agent.available_commands)
```

2. **Check command syntax:**
```python
help(agent.execute_command)
```

3. **Debug command execution:**
```python
agent.debug_mode = True
result = agent.execute_command("command", debug=True)
print(result.trace)
```

## Workflow Issues

### Workflow Definition Errors

**Problem:** Workflow fails to load or parse

**Solution:**
```python
# Validate workflow YAML
from coordination.workflow_parser import WorkflowParser
parser = WorkflowParser()
try:
    workflow = parser.parse_file("workflow.yaml")
    print("Valid workflow")
except Exception as e:
    print(f"Error: {e}")
```

### Document Handoff Failures

**Problem:** Documents not transferring between agents

**Solutions:**

1. **Check handoff queue:**
```python
from coordination.handoff_protocol import HandoffProtocol
protocol = HandoffProtocol()
pending = protocol.get_pending_handoffs()
for handoff in pending:
    print(f"{handoff.id}: {handoff.status}")
```

2. **Force handoff:**
```python
protocol.force_handoff("doc-123", "from-agent", "to-agent")
```

3. **Clear stuck handoffs:**
```python
protocol.clear_stuck_handoffs(older_than_hours=24)
```

### Workflow Performance Issues

**Problem:** Workflows taking too long

**Solutions:**

1. **Identify bottlenecks:**
```python
metrics = engine.get_workflow_metrics("workflow-123")
print(metrics.step_durations)
print(metrics.waiting_times)
```

2. **Optimize parallel execution:**
```yaml
# In workflow YAML
steps:
  - step: parallel_tasks
    parallel: true
    agents: [agent1, agent2, agent3]
```

3. **Adjust timeouts:**
```python
engine.config.step_timeout = 3600  # 1 hour
engine.config.workflow_timeout = 86400  # 24 hours
```

## Performance Problems

### High CPU Usage

**Diagnosis:**
```bash
docker stats
htop  # or top
```

**Solutions:**

1. **Limit agent CPU:**
```yaml
# docker-compose.yml
services:
  agent:
    cpus: '1.0'  # Limit to 1 CPU
```

2. **Optimize agent operations:**
```python
agent.config.batch_size = 10  # Reduce from 50
agent.config.parallel_tasks = 2  # Reduce from 5
```

3. **Enable throttling:**
```python
from control.resource_allocator import ResourceAllocator
allocator = ResourceAllocator()
allocator.enable_throttling(cpu_threshold=80)
```

### Memory Leaks

**Diagnosis:**
```python
import tracemalloc
tracemalloc.start()
# Run operations
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**Solutions:**

1. **Clear caches:**
```python
import gc
gc.collect()
engine.clear_cache()
```

2. **Restart services periodically:**
```bash
# Add to crontab
0 */6 * * * docker-compose restart agent-service
```

### Slow API Responses

**Diagnosis:**
```bash
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/health
```

**Solutions:**

1. **Enable API caching:**
```python
app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379'
```

2. **Optimize database queries:**
```python
# Add indexes
db.create_index("agent_id", "timestamp")
```

3. **Use connection pooling:**
```python
pool = ConnectionPool(max_connections=50)
```

## API Errors

### 401 Unauthorized

**Problem:** Authentication failing

**Solutions:**

1. **Check token expiry:**
```python
import jwt
token = "your-token"
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded['exp'])
```

2. **Refresh token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $OLD_TOKEN"
```

### 429 Rate Limited

**Problem:** Too many requests

**Solutions:**

1. **Check rate limit headers:**
```bash
curl -I http://localhost:8000/api/v1/agents
# Look for X-RateLimit-* headers
```

2. **Implement exponential backoff:**
```python
import time
for attempt in range(5):
    response = make_request()
    if response.status_code != 429:
        break
    time.sleep(2 ** attempt)
```

### 500 Internal Server Error

**Problem:** Server errors

**Diagnosis:**
```bash
docker logs control-api --tail 100
```

**Solutions:**

1. **Check error details:**
```python
response = requests.get(url)
if response.status_code == 500:
    error = response.json()
    print(error['error']['details'])
```

2. **Restart service:**
```bash
docker-compose restart control-api
```

## Database Issues

### Database Connection Errors

**Problem:** Cannot connect to database

**Solutions:**

1. **Check database status:**
```bash
docker exec postgres-container pg_isready
```

2. **Verify credentials:**
```bash
docker exec postgres-container psql -U user -d database -c "SELECT 1"
```

3. **Reset connection pool:**
```python
db.dispose()  # Close all connections
db = create_engine(DATABASE_URL, pool_pre_ping=True)
```

### Data Corruption

**Problem:** Inconsistent or corrupted data

**Solutions:**

1. **Run integrity checks:**
```sql
-- PostgreSQL
VACUUM ANALYZE;
REINDEX DATABASE dbname;
```

2. **Restore from backup:**
```bash
docker exec postgres-container pg_restore -d database backup.sql
```

### Migration Failures

**Problem:** Database migrations not applying

**Solutions:**

1. **Check migration status:**
```bash
alembic current
alembic history
```

2. **Force migration:**
```bash
alembic stamp head
alembic upgrade head
```

## Network Problems

### Service Discovery Issues

**Problem:** Services cannot find each other

**Solutions:**

1. **Verify DNS resolution:**
```bash
docker exec container-name nslookup other-service
```

2. **Use explicit network:**
```yaml
# docker-compose.yml
services:
  service1:
    networks:
      - agile-network
networks:
  agile-network:
    driver: bridge
```

### Timeout Errors

**Problem:** Requests timing out

**Solutions:**

1. **Increase timeouts:**
```python
requests.get(url, timeout=30)  # Increase from default
```

2. **Check network latency:**
```bash
docker exec container-name ping other-container
```

### SSL/TLS Issues

**Problem:** Certificate errors

**Solutions:**

1. **Disable verification (dev only):**
```python
requests.get(url, verify=False)
```

2. **Add custom CA:**
```bash
export REQUESTS_CA_BUNDLE=/path/to/ca.pem
```

## Security Issues

### Permission Denied

**Problem:** Access control errors

**Solutions:**

1. **Check user permissions:**
```python
from control.auth import check_permissions
perms = check_permissions(user_id, resource)
print(perms)
```

2. **Grant permissions:**
```python
grant_permission(user_id, resource, "read")
```

### Audit Trail Gaps

**Problem:** Missing audit logs

**Solutions:**

1. **Verify audit configuration:**
```python
from control.audit_logger import AuditLogger
logger = AuditLogger()
print(logger.is_enabled)
print(logger.retention_policy)
```

2. **Repair audit chain:**
```python
logger.repair_chain()
logger.verify_integrity()
```

## Debugging Tools

### Enable Debug Mode

```python
# Global debug
import logging
logging.basicConfig(level=logging.DEBUG)

# Component debug
agent.debug = True
engine.debug = True
```

### Performance Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# Run code
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Code to profile
    pass
```

### Network Debugging

```bash
# Capture traffic
docker exec container-name tcpdump -i any -w capture.pcap

# Analyze with Wireshark
wireshark capture.pcap
```

## Log Analysis

### Log Locations

- **Control Layer**: `/control/logs/`
- **Agents**: `/agents/{agent-id}/logs/`
- **Workflows**: `/coordination/logs/`
- **Docker**: `docker logs <container>`

### Log Aggregation

```bash
# Collect all logs
docker-compose logs > all_logs.txt

# Filter by timestamp
grep "2025-08-21" all_logs.txt

# Find errors
grep -i error all_logs.txt
```

### Log Monitoring

```bash
# Real-time monitoring
tail -f /var/log/agile-ai/*.log

# With filtering
tail -f /var/log/agile-ai/*.log | grep ERROR
```

## Recovery Procedures

### System Recovery

1. **Backup current state:**
```bash
./scripts/backup.sh
```

2. **Stop all services:**
```bash
docker-compose down
```

3. **Restore from backup:**
```bash
./scripts/restore.sh backup-2025-08-21.tar.gz
```

4. **Restart services:**
```bash
docker-compose up -d
```

### Agent Recovery

```python
# Recover agent from backup
agent = Agent.recover("agent-123", backup_date="2025-08-21")

# Reset to factory defaults
agent.factory_reset()

# Rebuild from profile
agent = Agent.create_from_profile("developer")
```

### Workflow Recovery

```python
# Resume interrupted workflow
engine.resume("workflow-123", from_step="last_completed")

# Replay workflow
engine.replay("workflow-123", with_corrections=True)
```

### Database Recovery

```bash
# Point-in-time recovery
pg_restore -d database -t "2025-08-21 10:00:00" backup.sql

# Repair tables
psql -d database -c "VACUUM FULL; REINDEX DATABASE database;"
```

## Getting Help

### Self-Help Resources

1. **Check logs first:**
```bash
docker-compose logs | grep -C 5 ERROR
```

2. **Run diagnostics:**
```bash
python scripts/diagnose.py
```

3. **Search documentation:**
```bash
grep -r "error message" docs/
```

### Community Support

- **GitHub Issues**: https://github.com/your-org/agent-zero/issues
- **Discord**: https://discord.gg/agent-zero
- **Forum**: https://forum.agent-zero.ai

### Reporting Issues

When reporting issues, include:

1. **System information:**
```bash
python scripts/sysinfo.py > sysinfo.txt
```

2. **Error logs:**
```bash
docker-compose logs --tail 1000 > logs.txt
```

3. **Configuration:**
```bash
cat docker/.env > config.txt
# Remove sensitive information
```

4. **Steps to reproduce:**
- Exact commands run
- Expected behavior
- Actual behavior
- Any error messages

### Emergency Support

For critical production issues:

1. **Emergency shutdown:**
```bash
./scripts/emergency_stop.sh
```

2. **Rollback:**
```bash
./scripts/rollback.sh previous-version
```

3. **Contact support:**
- Email: support@agent-zero.ai
- Phone: +1-800-AGENT-0 (24/7 for critical issues)

## Preventive Maintenance

### Daily Checks

```bash
# Run daily health check
./scripts/daily_health_check.sh
```

### Weekly Maintenance

```bash
# Clean old logs
find /var/log/agile-ai -mtime +7 -delete

# Vacuum database
docker exec postgres-container vacuumdb -a -z

# Update dependencies
pip list --outdated
```

### Monthly Tasks

```bash
# Full backup
./scripts/full_backup.sh

# Security audit
./scripts/security_audit.sh

# Performance baseline
./scripts/performance_baseline.sh
```

---

*For more information, see the [User Guide](./user_guide.md) and [API Reference](./api_reference.md).*