# Control Layer API Documentation

## Overview

The Control Layer API provides REST endpoints for ethics validation, safety monitoring, resource allocation, and audit logging in the Agile AI Company framework.

## Features

- **Ethics Validation**: Validate agent decisions against ethical constraints
- **Safety Monitoring**: Real-time monitoring with threat detection and interventions
- **Resource Management**: Allocate and manage resources for agent teams
- **Audit Logging**: Comprehensive logging with immutable audit trail
- **Authentication**: JWT-based authentication for secure access

## Installation

### Requirements

```bash
pip install -r requirements.txt
```

### Running the API

```bash
# Development mode
python api.py

# Or with uvicorn directly
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Authentication

#### Login
```
POST /auth/login
Body: {"username": "admin", "password": "secret"}
Response: {"access_token": "...", "token_type": "bearer"}
```

### Ethics Endpoints

#### Validate Decision
```
POST /ethics/validate
Headers: Authorization: Bearer <token>
Body: {
    "agent_id": "agent-1",
    "decision_type": "data_processing",
    "decision_data": {...},
    "context": {...}
}
```

#### Get Ethical Constraints
```
GET /ethics/constraints
Headers: Authorization: Bearer <token>
Query: ?category=privacy
```

#### Risk Assessment
```
GET /ethics/risk-assessment/{agent_id}
Headers: Authorization: Bearer <token>
Query: ?time_window=3600
```

### Safety Endpoints

#### Safety Check
```
POST /safety/check
Headers: Authorization: Bearer <token>
Body: {
    "agent_id": "agent-1",
    "metrics": {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "response_time": 150.0
    },
    "check_type": "standard"
}
```

#### Emergency Stop
```
POST /safety/emergency-stop/{agent_id}
Headers: Authorization: Bearer <token>
```

#### Active Threats
```
GET /safety/threats/active
Headers: Authorization: Bearer <token>
```

### Resource Endpoints

#### Allocate Resources
```
POST /resources/allocate
Headers: Authorization: Bearer <token>
Body: {
    "team_id": "team-1",
    "resource_type": "compute",
    "amount": 4.0,
    "priority": 3,
    "duration": 3600
}
```

#### Release Resources
```
DELETE /resources/release/{team_id}
Headers: Authorization: Bearer <token>
```

#### Get Resource Usage
```
GET /resources/usage/{team_id}
Headers: Authorization: Bearer <token>
```

#### Available Resources
```
GET /resources/available
Headers: Authorization: Bearer <token>
```

#### Resource Utilization
```
GET /resources/utilization
Headers: Authorization: Bearer <token>
Query: ?pool_name=default
```

### Audit Endpoints

#### Query Logs
```
GET /audit/logs
Headers: Authorization: Bearer <token>
Query: ?agent_id=agent-1&event_type=ethics&limit=100
```

#### Get Statistics
```
GET /audit/stats
Headers: Authorization: Bearer <token>
```

#### Export Logs
```
POST /audit/export
Headers: Authorization: Bearer <token>
Query: ?format=json
```

#### Analyze Patterns
```
GET /audit/analysis/patterns
Headers: Authorization: Bearer <token>
Query: ?time_window=86400
```

### Admin Endpoints

#### System Status
```
GET /admin/status
Headers: Authorization: Bearer <token>
```

#### Update Configuration
```
POST /admin/configuration/update
Headers: Authorization: Bearer <token>
Body: {
    "component": "ethics_engine",
    "settings": {...},
    "apply_immediately": false
}
```

## Decision Types

Valid decision types for ethics validation:
- `data_processing`: Data handling and processing decisions
- `resource_allocation`: Resource management decisions
- `communication`: External communication decisions
- `learning_update`: Model and learning updates
- `safety_intervention`: Safety-related interventions
- `configuration_change`: System configuration changes

## Resource Types

Available resource types:
- `compute`: CPU cores
- `memory`: RAM in GB
- `storage`: Disk space in GB
- `network`: Network bandwidth in Mbps
- `gpu`: GPU units
- `api_calls`: API call quota
- `concurrent_tasks`: Concurrent task limit

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Invalid input parameters"
}
```

### 401 Unauthorized
```json
{
    "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
    "detail": "Admin privileges required"
}
```

### 404 Not Found
```json
{
    "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "detail": "Internal server error"
}
```

## Configuration Files

### Ethical Constraints
Location: `/control/config/ethical_constraints.yaml`

Defines ethical rules and constraints across 11 categories including privacy, safety, fairness, transparency, and more.

### Safety Thresholds
Location: `/control/config/safety_thresholds.yaml`

Configures safety monitoring thresholds for metrics like CPU usage, memory, response time, error rates, etc.

### Resource Limits
Location: `/control/config/resource_limits.yaml`

Defines resource pools and team-specific resource allocation limits.

## Testing

### Run Unit Tests
```bash
pytest tests/test_api.py -v
```

### Run Integration Tests
```bash
pytest tests/test_api.py::TestIntegration -v
```

### Run Load Tests
```bash
# Using locust or similar tool
locust -f tests/load_test.py --host=http://localhost:8000
```

## Docker Deployment

### Build Image
```bash
docker build -t agile-ai-control-api .
```

### Run Container
```bash
docker run -d \
  --name control-api \
  -p 8000:8000 \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/storage:/app/storage \
  agile-ai-control-api
```

## Security Considerations

1. **Authentication**: Always use strong JWT secret keys in production
2. **HTTPS**: Deploy behind HTTPS proxy in production
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Input Validation**: All inputs are validated using Pydantic models
5. **Audit Trail**: All critical operations are logged to immutable audit trail
6. **CORS**: Configure CORS appropriately for your deployment

## Performance

- Agent spawn time: < 500ms
- Inter-agent communication latency: < 100ms
- Decision validation time: < 50ms
- System uptime target: > 99.9%

## API Documentation

When running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For issues and questions, please refer to the main project documentation or create an issue in the repository.