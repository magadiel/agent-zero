# Agile AI Company - API Reference

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Control Layer API](#control-layer-api)
4. [Coordination API](#coordination-api)
5. [Workflow API](#workflow-api)
6. [Metrics API](#metrics-api)
7. [Agent API](#agent-api)
8. [WebSocket APIs](#websocket-apis)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)

## Overview

The Agile AI Company framework provides comprehensive REST and WebSocket APIs for managing agents, workflows, and system operations.

### Base URLs
- **Control Layer**: `http://localhost:8000/api/v1`
- **Coordination Layer**: `http://localhost:8001/api/v1`
- **Metrics**: `http://localhost:8002/api/v1`
- **WebSocket**: `ws://localhost:8003/ws`

### Content Type
All requests and responses use JSON:
```
Content-Type: application/json
```

### API Versioning
APIs are versioned via URL path: `/api/v1/`, `/api/v2/`, etc.

## Authentication

### JWT Authentication
```http
POST /api/v1/auth/login
```

**Request:**
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token
Include in Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Control Layer API

### Ethics Engine

#### Validate Decision
```http
POST /api/v1/ethics/validate
```

**Request:**
```json
{
  "decision": {
    "action": "process_data",
    "target": "user_information",
    "context": {
      "purpose": "analytics",
      "data_type": "personal"
    }
  },
  "agent_id": "agent-123",
  "priority": "normal"
}
```

**Response:**
```json
{
  "approved": true,
  "risk_score": 0.2,
  "recommendations": [],
  "validation_id": "val-456",
  "timestamp": "2025-08-21T10:00:00Z"
}
```

#### Get Validation History
```http
GET /api/v1/ethics/validations?agent_id=agent-123&limit=10
```

**Response:**
```json
{
  "validations": [
    {
      "id": "val-456",
      "decision": {...},
      "approved": true,
      "risk_score": 0.2,
      "timestamp": "2025-08-21T10:00:00Z"
    }
  ],
  "total": 45,
  "page": 1
}
```

### Safety Monitor

#### Get Safety Status
```http
GET /api/v1/safety/status
```

**Response:**
```json
{
  "overall_status": "healthy",
  "thresholds": {
    "cpu_usage": {
      "current": 45,
      "warning": 70,
      "critical": 90
    },
    "memory_usage": {
      "current": 62,
      "warning": 80,
      "critical": 95
    }
  },
  "active_interventions": [],
  "last_check": "2025-08-21T10:00:00Z"
}
```

#### Emergency Stop
```http
POST /api/v1/safety/emergency-stop
```

**Request:**
```json
{
  "target": "agent-123",
  "reason": "Anomalous behavior detected",
  "severity": "critical"
}
```

**Response:**
```json
{
  "success": true,
  "stopped_agents": ["agent-123"],
  "intervention_id": "int-789"
}
```

### Resource Allocator

#### Allocate Resources
```http
POST /api/v1/resources/allocate
```

**Request:**
```json
{
  "team_id": "team-customer",
  "resources": {
    "agents": 5,
    "cpu": "2000m",
    "memory": "4Gi"
  },
  "priority": "high"
}
```

**Response:**
```json
{
  "allocation_id": "alloc-123",
  "allocated": {
    "agents": 5,
    "cpu": "2000m",
    "memory": "4Gi"
  },
  "pool": "default",
  "expires_at": "2025-08-21T12:00:00Z"
}
```

#### Release Resources
```http
DELETE /api/v1/resources/allocate/{allocation_id}
```

**Response:**
```json
{
  "success": true,
  "released": {
    "agents": 5,
    "cpu": "2000m",
    "memory": "4Gi"
  }
}
```

### Audit Trail

#### Query Audit Logs
```http
GET /api/v1/audit/logs?start_date=2025-08-20&end_date=2025-08-21
```

**Response:**
```json
{
  "logs": [
    {
      "id": "audit-123",
      "timestamp": "2025-08-21T10:00:00Z",
      "event_type": "decision_validation",
      "agent_id": "agent-123",
      "action": "process_data",
      "result": "approved",
      "metadata": {...}
    }
  ],
  "total": 150,
  "page": 1
}
```

## Coordination API

### Team Management

#### Form Team
```http
POST /api/v1/teams
```

**Request:**
```json
{
  "name": "Customer Service Team",
  "mission": "Handle customer inquiries",
  "required_skills": ["nlp", "customer_service", "problem_solving"],
  "size": 5,
  "profile": "customer_service"
}
```

**Response:**
```json
{
  "team_id": "team-456",
  "name": "Customer Service Team",
  "agents": [
    {
      "id": "agent-1",
      "role": "leader",
      "skills": ["nlp", "leadership"]
    },
    {
      "id": "agent-2",
      "role": "member",
      "skills": ["customer_service"]
    }
  ],
  "status": "forming",
  "created_at": "2025-08-21T10:00:00Z"
}
```

#### Get Team Status
```http
GET /api/v1/teams/{team_id}
```

**Response:**
```json
{
  "team_id": "team-456",
  "name": "Customer Service Team",
  "status": "performing",
  "performance": {
    "velocity": 45,
    "efficiency": 0.92,
    "quality": 0.95
  },
  "agents": [...],
  "current_tasks": [...]
}
```

#### Dissolve Team
```http
DELETE /api/v1/teams/{team_id}
```

**Response:**
```json
{
  "success": true,
  "agents_released": 5,
  "final_metrics": {
    "tasks_completed": 234,
    "average_velocity": 42
  }
}
```

### Document Management

#### Create Document
```http
POST /api/v1/documents
```

**Request:**
```json
{
  "title": "Product Requirements",
  "type": "prd",
  "content": "...",
  "owner": "agent-pm-1",
  "metadata": {
    "version": "1.0",
    "epic": "epic-123"
  }
}
```

**Response:**
```json
{
  "document_id": "doc-789",
  "title": "Product Requirements",
  "version": 1,
  "created_at": "2025-08-21T10:00:00Z",
  "owner": "agent-pm-1"
}
```

#### Handoff Document
```http
POST /api/v1/documents/{document_id}/handoff
```

**Request:**
```json
{
  "to_agent": "agent-architect-1",
  "validation_required": true,
  "checklist": "architecture_review"
}
```

**Response:**
```json
{
  "handoff_id": "hand-123",
  "status": "pending",
  "from": "agent-pm-1",
  "to": "agent-architect-1",
  "document_id": "doc-789"
}
```

## Workflow API

### Workflow Management

#### Start Workflow
```http
POST /api/v1/workflows/execute
```

**Request:**
```json
{
  "workflow_name": "greenfield_development",
  "team_id": "team-dev",
  "context": {
    "project": "new-feature",
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "execution_id": "exec-123",
  "workflow": "greenfield_development",
  "status": "running",
  "current_step": "requirements_gathering",
  "started_at": "2025-08-21T10:00:00Z"
}
```

#### Get Workflow Status
```http
GET /api/v1/workflows/executions/{execution_id}
```

**Response:**
```json
{
  "execution_id": "exec-123",
  "status": "running",
  "progress": 45,
  "current_step": "architecture_design",
  "completed_steps": ["requirements_gathering"],
  "documents_created": ["prd-123", "arch-456"],
  "estimated_completion": "2025-08-21T14:00:00Z"
}
```

#### Cancel Workflow
```http
POST /api/v1/workflows/executions/{execution_id}/cancel
```

**Response:**
```json
{
  "success": true,
  "execution_id": "exec-123",
  "final_status": "cancelled",
  "completed_steps": ["requirements_gathering"],
  "cleanup_performed": true
}
```

## Metrics API

### Performance Metrics

#### Get Team Metrics
```http
GET /api/v1/metrics/teams/{team_id}?period=7d
```

**Response:**
```json
{
  "team_id": "team-dev",
  "period": "7d",
  "metrics": {
    "velocity": {
      "current": 42,
      "average": 38,
      "trend": "increasing"
    },
    "cycle_time": {
      "average": "2.5d",
      "median": "2d",
      "p95": "4d"
    },
    "throughput": {
      "stories_completed": 15,
      "bugs_fixed": 23
    },
    "quality": {
      "defect_rate": 0.05,
      "test_coverage": 0.85
    }
  }
}
```

#### Get System Metrics
```http
GET /api/v1/metrics/system
```

**Response:**
```json
{
  "timestamp": "2025-08-21T10:00:00Z",
  "agents": {
    "total": 25,
    "active": 20,
    "idle": 5
  },
  "resources": {
    "cpu_usage": 65,
    "memory_usage": 72,
    "disk_usage": 45
  },
  "workflows": {
    "running": 3,
    "completed_today": 12,
    "average_duration": "3.2h"
  }
}
```

### Quality Metrics

#### Evaluate Quality Gate
```http
POST /api/v1/quality/gates/evaluate
```

**Request:**
```json
{
  "gate_name": "story_completion",
  "context": {
    "story_id": "story-123",
    "checks": {
      "code_review": true,
      "tests_passing": true,
      "documentation": false
    }
  }
}
```

**Response:**
```json
{
  "gate_id": "gate-456",
  "status": "CONCERNS",
  "passed_checks": ["code_review", "tests_passing"],
  "failed_checks": ["documentation"],
  "recommendations": [
    "Update API documentation",
    "Add user guide section"
  ]
}
```

## Agent API

### Agent Management

#### Get Agent Status
```http
GET /api/v1/agents/{agent_id}
```

**Response:**
```json
{
  "agent_id": "agent-123",
  "profile": "developer",
  "status": "busy",
  "current_task": "implement-story-456",
  "team": "team-dev",
  "performance": {
    "tasks_completed": 45,
    "average_time": "2.5h",
    "quality_score": 0.92
  }
}
```

#### Execute Agent Command
```http
POST /api/v1/agents/{agent_id}/commands
```

**Request:**
```json
{
  "command": "implement-story",
  "parameters": {
    "story_id": "story-789",
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "command_id": "cmd-123",
  "status": "executing",
  "agent_id": "agent-123",
  "estimated_duration": "3h"
}
```

### Agent Communication

#### Send Message to Agent
```http
POST /api/v1/agents/{agent_id}/messages
```

**Request:**
```json
{
  "message": "Please review the latest changes",
  "priority": "normal",
  "context": {
    "pr_id": "pr-123"
  }
}
```

**Response:**
```json
{
  "message_id": "msg-456",
  "delivered": true,
  "agent_response": "Acknowledged. Starting review."
}
```

## WebSocket APIs

### Real-time Monitoring

#### Connect to Monitoring Stream
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/monitoring');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['metrics', 'workflows', 'alerts']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

#### Message Types

**Metrics Update:**
```json
{
  "type": "metrics",
  "data": {
    "team_id": "team-dev",
    "velocity": 42,
    "timestamp": "2025-08-21T10:00:00Z"
  }
}
```

**Workflow Event:**
```json
{
  "type": "workflow",
  "event": "step_completed",
  "data": {
    "execution_id": "exec-123",
    "step": "requirements_gathering",
    "next_step": "architecture_design"
  }
}
```

**Alert:**
```json
{
  "type": "alert",
  "severity": "warning",
  "data": {
    "message": "CPU usage above 80%",
    "source": "safety_monitor",
    "timestamp": "2025-08-21T10:00:00Z"
  }
}
```

### Team Communication

#### Join Team Channel
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/teams/team-dev');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'join',
    agent_id: 'agent-123'
  }));
};
```

#### Broadcast to Team
```json
{
  "type": "broadcast",
  "message": "Sprint planning starting in 5 minutes",
  "from": "agent-sm-1"
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Team with ID 'team-999' not found",
    "details": {
      "resource_type": "team",
      "resource_id": "team-999"
    },
    "timestamp": "2025-08-21T10:00:00Z",
    "request_id": "req-123"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Insufficient permissions |
| RESOURCE_NOT_FOUND | 404 | Resource doesn't exist |
| VALIDATION_ERROR | 400 | Invalid request data |
| CONFLICT | 409 | Resource conflict |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily down |

### Retry Strategy
```http
Retry-After: 60
```

For rate limiting and temporary failures, use exponential backoff:
- 1st retry: 1 second
- 2nd retry: 2 seconds
- 3rd retry: 4 seconds
- Maximum: 5 retries

## Rate Limiting

### Limits
- **Default**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **Premium**: 10000 requests per minute

### Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1629540000
```

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

## SDK Examples

### Python
```python
from agile_ai import Client

client = Client(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Form a team
team = client.teams.create(
    name="Dev Team",
    size=5,
    skills=["python", "testing"]
)

# Execute workflow
execution = client.workflows.execute(
    workflow="greenfield_development",
    team_id=team.id
)

# Monitor progress
while execution.status != "completed":
    execution.refresh()
    print(f"Progress: {execution.progress}%")
    time.sleep(5)
```

### JavaScript
```javascript
const AgileAI = require('agile-ai-sdk');

const client = new AgileAI({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Form a team
const team = await client.teams.create({
  name: 'Dev Team',
  size: 5,
  skills: ['javascript', 'react']
});

// Execute workflow
const execution = await client.workflows.execute({
  workflow: 'greenfield_development',
  teamId: team.id
});

// Monitor with WebSocket
client.monitoring.subscribe(['workflows'], (event) => {
  console.log('Workflow update:', event);
});
```

### cURL Examples

#### Authenticate
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

#### Create Team
```bash
curl -X POST http://localhost:8001/api/v1/teams \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Team",
    "size": 3,
    "mission": "Handle support"
  }'
```

#### Get Metrics
```bash
curl -X GET http://localhost:8002/api/v1/metrics/teams/team-dev?period=7d \
  -H "Authorization: Bearer $TOKEN"
```

## API Versioning

### Version Strategy
- **Current**: v1 (stable)
- **Beta**: v2 (preview features)
- **Deprecated**: None

### Migration Guide
When v2 becomes stable:
1. Update base URLs from `/api/v1/` to `/api/v2/`
2. Review breaking changes in migration guide
3. Update SDK to latest version
4. Test thoroughly in staging

## Appendix

### Status Codes Summary
- **2xx**: Success
- **3xx**: Redirection
- **4xx**: Client errors
- **5xx**: Server errors

### Content Types
- `application/json`: Standard JSON
- `application/x-ndjson`: Streaming JSON
- `text/event-stream`: Server-sent events

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### Filtering
```http
GET /api/v1/audit/logs?filter[agent_id]=agent-123&filter[date_from]=2025-08-20
```

### Sorting
```http
GET /api/v1/teams?sort=-created_at,name
```

---

*For implementation details, see the [User Guide](./user_guide.md) and [Troubleshooting Guide](./troubleshooting.md).*