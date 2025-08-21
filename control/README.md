# Control Layer - Ethics, Safety, and Governance

## Overview
The Control Layer implements ethics, safety, and governance systems for the Agile AI Company framework. This layer ensures all agent decisions and actions comply with ethical constraints, safety thresholds, and regulatory requirements.

## ✅ Implemented Components

### Ethics Engine (`ethics_engine.py`) - COMPLETED
The core ethics validation system that evaluates all agent decisions against predefined ethical constraints.

**Key Features:**
- ✅ Real-time decision validation
- ✅ Multi-dimensional ethical assessment (harm, privacy, fairness, transparency)
- ✅ Risk scoring and recommendation generation
- ✅ Immutable audit trail with file logging
- ✅ Emergency shutdown capabilities
- ✅ Comprehensive test coverage (16 tests passing)

**Usage Example:**
```python
from control.ethics_engine import EthicsEngine, AgentDecision, DecisionType

# Initialize the engine
engine = EthicsEngine()

# Create a decision for validation
decision = AgentDecision(
    agent_id="agent-001",
    decision_type=DecisionType.TASK_EXECUTION,
    action="process_user_data",
    context={
        "explanation": "Analyzing user feedback",
        "personal_data": False,
        "consent": True
    },
    resources_required={"cpu_percent": 30, "memory_mb": 1024}
)

# Validate the decision
result = await engine.validate_decision(decision)

if result.approved:
    print(f"Decision approved: {result.reasoning}")
else:
    print(f"Decision rejected: {result.reasoning}")
```

### Ethical Constraints Configuration (`config/ethical_constraints.yaml`) - COMPLETED
Comprehensive configuration file with 11 categories of ethical rules including:
- Harm prevention policies
- Privacy protection (GDPR compliant)
- Fairness and non-discrimination rules
- Transparency requirements
- Resource limits
- Accountability chains
- Safety mechanisms (kill switches, circuit breakers)
- Learning constraints
- Manipulation prevention
- Sustainability guidelines

### Safety Monitor (`safety_monitor.py`) - COMPLETED
The real-time safety monitoring system that tracks agent behavior and enforces safety thresholds.

**Key Features:**
- ✅ Real-time resource monitoring (CPU, memory, response times)
- ✅ Multi-level safety thresholds (normal, warning, critical, emergency)
- ✅ Kill switch mechanisms (emergency stop & graceful shutdown)
- ✅ Circuit breaker pattern for fault tolerance
- ✅ Agent-specific monitoring and intervention
- ✅ Comprehensive threat detection (resource exhaustion, runaway agents, cascading failures)
- ✅ Intervention system (throttle, pause, terminate, restart, isolate)

**Usage Example:**
```python
from control.safety_monitor import SafetyMonitor

# Initialize monitor
monitor = SafetyMonitor()

# Start monitoring
await monitor.start_monitoring()

# Register agents
await monitor.register_agent("agent-001")

# Report agent activity
await monitor.report_agent_activity(
    "agent-001",
    cpu=45.0,
    memory=60.0,
    response_time=150.0
)

# Check status
status = await monitor.get_status()
print(f"Safety Level: {status['safety_level']}")

# Emergency stop if needed
await monitor.emergency_stop("Critical threat detected")
```

### Safety Thresholds Configuration (`config/safety_thresholds.yaml`) - COMPLETED
Comprehensive configuration with:
- Resource limits (CPU, memory, disk I/O, network)
- Response time thresholds
- Error rate limits
- Agent and team limits
- Circuit breaker settings
- Kill switch configurations
- Anomaly detection patterns
- Escalation policies

### Resource Allocator (`resource_allocator.py`) - COMPLETED
The resource management system that allocates computational resources to agent teams.

**Key Features:**
- ✅ Resource pool management (CPU, memory, GPU, disk, network)
- ✅ Priority-based allocation with queue management  
- ✅ Team-specific resource quotas and limits
- ✅ Automatic resource reclamation for expired allocations
- ✅ Real-time usage tracking and monitoring
- ✅ Emergency release mechanisms
- ✅ Comprehensive audit logging
- ✅ Full test coverage (20+ tests passing)

**Usage Example:**
```python
from control.resource_allocator import ResourceAllocator, ResourceType, PriorityLevel

# Initialize allocator
allocator = ResourceAllocator()

# Request resources for a team
request_id, status = await allocator.request_resources(
    team_id="product_team",
    resources={
        ResourceType.CPU_CORES: 4,
        ResourceType.MEMORY_GB: 16,
        ResourceType.GPU_COUNT: 1
    },
    priority=PriorityLevel.HIGH,
    duration_minutes=60
)

# Check allocation status
status = await allocator.get_allocation_status(f"alloc_{request_id}")
print(f"Allocation status: {status['status']}")

# Get team usage
usage = await allocator.get_team_usage("product_team")
print(f"Team usage: {usage}")

# Release resources when done
await allocator.release_resources(f"alloc_{request_id}")
```

### Audit Logger (`audit_logger.py`) - COMPLETED
The immutable audit trail system that records all agent decisions, actions, and system events with cryptographic verification.

**Key Features:**
- ✅ Append-only logging with SQLite backend
- ✅ Cryptographic signatures (HMAC-SHA512) for integrity verification
- ✅ Hash chain for tamper detection
- ✅ Query interface with comprehensive filtering
- ✅ Retention policies (PERMANENT, LONG_TERM, STANDARD, SHORT_TERM)
- ✅ Automatic archival and cleanup
- ✅ Export functionality (JSON, CSV)
- ✅ Real-time statistics and monitoring
- ✅ Integration mixins for Ethics, Safety, and Resource components
- ✅ Full test coverage (25 tests passing)

**Usage Example:**
```python
from control.audit_logger import (
    AuditLogger, EventType, EventCategory, 
    Severity, ActorType, DecisionResult
)

# Initialize logger
logger = AuditLogger(db_path="control/storage/audit.db")

# Log an event
event_id = logger.log_event(
    event_type=EventType.DECISION,
    event_category=EventCategory.ETHICS,
    severity=Severity.HIGH,
    actor_type=ActorType.AGENT,
    actor_id="agent-001",
    event_description="Ethical decision validated"
)

# Log a decision
logger.log_decision(
    actor_id="agent-001",
    decision_type="TASK_ALLOCATION",
    decision_result=DecisionResult.APPROVED,
    reasoning="Resources available, priority high"
)

# Query logs
recent_logs = logger.query_logs(
    event_category=EventCategory.ETHICS,
    severity=Severity.HIGH,
    limit=10
)

# Verify integrity
is_valid, errors = logger.verify_integrity()
print(f"Audit trail integrity: {'Valid' if is_valid else 'Invalid'}")

# Get statistics
stats = logger.get_statistics()
print(f"Total audit records: {stats['total_records']}")

# Export for compliance
logger.export_logs("audit_export.json", format="json")
```

### Audit Storage (`storage/audit_schema.sql`) - COMPLETED
Comprehensive SQL schema for audit trail storage with:
- Main audit log table with 30+ fields
- Cryptographic integrity fields (hashes, signatures)
- Retention policy management
- Query optimization indexes
- Audit metadata tracking
- Query log for compliance
- Predefined views for common queries
- Stored procedures for integrity verification

## ✅ Completed Components

## Configuration

All control layer components are configured through YAML files in the `/control/config/` directory:
- ✅ `ethical_constraints.yaml` - Ethical rules and principles (COMPLETED)
- ✅ `safety_thresholds.yaml` - Safety limits and triggers (COMPLETED)
- ✅ `resource_limits.yaml` - Resource allocation policies (COMPLETED)

## Testing

Run the comprehensive test suite:
```bash
cd /home/magadiel/Desktop/agent-zero
python3 -m unittest control.tests.test_ethics_engine -v
python3 -m unittest control.tests.test_safety_monitor -v
python3 -m unittest control.tests.test_resource_allocator -v
python3 -m unittest control.tests.test_audit_logger -v
```

Current test coverage:
- ✅ Ethics Engine: 16 unit tests + 2 integration tests passing
- ✅ Safety Monitor: 20+ unit tests passing
- ✅ Resource Allocator: 22 unit tests passing
- ✅ Audit Logger: 25 unit tests passing
- Test scenarios include: harm prevention, privacy violations, fairness checks, transparency requirements, resource limits, emergency shutdown, resource allocation, priority queueing, team limits enforcement, audit trail integrity, hash chain verification, retention policies

## API

The Control Layer will expose a REST API (port 8000) for:
- ✅ Ethics validation requests (logic complete, API pending)
- ✅ Safety status monitoring (logic complete, API pending)
- ✅ Resource allocation management (logic complete, API pending)
- ⏳ Audit trail queries (pending)

## Security

Current security features:
- ✅ Immutable audit logging
- ✅ Emergency shutdown mechanisms
- ✅ Resource limit enforcement
- ✅ Validation of all decisions

Planned security enhancements:
- ⏳ TLS encryption for all communications
- ⏳ Authentication for API endpoints
- ⏳ Role-based access control (RBAC)
- ⏳ Cryptographic signing of audit logs

## Integration

The Control Layer integrates with:
- Coordination Layer - for team orchestration approval
- Execution Teams - for decision validation
- Metrics Layer - for performance monitoring
- Agent-Zero Core - through decision hooks and validation

## Project Status

| Component | Status | Files |
|-----------|--------|-------|
| Ethics Engine | ✅ COMPLETED | `ethics_engine.py` |
| Ethical Constraints | ✅ COMPLETED | `config/ethical_constraints.yaml` |
| Safety Monitor | ✅ COMPLETED | `safety_monitor.py` |
| Safety Thresholds | ✅ COMPLETED | `config/safety_thresholds.yaml` |
| Resource Allocator | ✅ COMPLETED | `resource_allocator.py` |
| Resource Limits Config | ✅ COMPLETED | `config/resource_limits.yaml` |
| Audit Logger | ✅ COMPLETED | `audit_logger.py` |
| Audit Schema | ✅ COMPLETED | `storage/audit_schema.sql` |
| Unit Tests (Ethics) | ✅ COMPLETED | `tests/test_ethics_engine.py` |
| Unit Tests (Safety) | ✅ COMPLETED | `tests/test_safety_monitor.py` |
| Unit Tests (Resource) | ✅ COMPLETED | `tests/test_resource_allocator.py` |
| Unit Tests (Audit) | ✅ COMPLETED | `tests/test_audit_logger.py` |
| Documentation | ✅ COMPLETED | `README.md` |
| Control API | ⏳ PENDING | `api.py` |
| Docker Container | ⏳ PENDING | `Dockerfile` |