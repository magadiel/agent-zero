# Agile AI Company Demo Scenarios

This directory contains demonstration scenarios showcasing the capabilities of the Agile AI Company framework built on Agent-Zero. Each demo illustrates different aspects of autonomous AI teams working in agile methodologies.

## Available Demos

### 1. Product Development Demo
**Location**: `/demos/product_development/`
**Scenario**: AI-Powered Task Management Application

Demonstrates:
- Greenfield development workflow
- Multi-agent team collaboration (PM, Architect, Developer, QA, SM)
- Sprint planning and execution
- Quality gates and testing
- Document flow from PRD to implementation

[View Demo →](./product_development/README.md)

### 2. Customer Service Demo
**Location**: `/demos/customer_service/`
**Scenario**: Automated Support Ticket Resolution System

Demonstrates:
- Customer service workflow
- Ticket classification and routing
- Multi-tier support escalation
- Knowledge base integration
- Performance metrics tracking

[View Demo →](./customer_service/README.md)

### 3. Operations Demo
**Location**: `/demos/operations/`
**Scenario**: System Performance Optimization

Demonstrates:
- Operations monitoring workflow
- Performance bottleneck detection
- Capacity planning
- Automated remediation
- Continuous improvement cycles

[View Demo →](./operations/README.md)

## Running the Demos

### Prerequisites

1. Ensure all Docker containers are running:
```bash
cd /home/magadiel/Desktop/agent-zero/docker
docker-compose up -d
```

2. Verify system health:
```bash
./docker/integration-tests.sh
```

### Quick Start

Each demo can be run independently:

```bash
# Product Development Demo
cd demos/product_development
python run_demo.py

# Customer Service Demo
cd demos/customer_service
python run_demo.py

# Operations Demo
cd demos/operations
python run_demo.py
```

### Interactive Mode

For step-by-step execution with explanations:

```bash
python run_demo.py --interactive
```

### Validation

Each demo includes validation scripts to verify outputs:

```bash
python validate_demo.py
```

## Demo Architecture

All demos follow a consistent structure:

```
demo_name/
├── README.md              # Demo documentation
├── scenario.yaml          # Scenario configuration
├── inputs/               # Input data and requirements
│   ├── requirements.md   # Business requirements
│   └── constraints.yaml  # Constraints and parameters
├── workflows/            # Workflow definitions
│   └── main.yaml        # Primary workflow
├── outputs/             # Generated outputs (created during execution)
├── run_demo.py          # Demo execution script
└── validate_demo.py     # Output validation script
```

## Key Features Demonstrated

### Agile Methodology
- Sprint planning with capacity calculation
- Daily standups with blocker tracking
- Sprint retrospectives with action items
- Velocity tracking and forecasting

### Multi-Agent Collaboration
- Team formation based on requirements
- Inter-agent communication protocols
- Document handoffs with validation
- Parallel task execution

### Quality Assurance
- Multi-level quality gates
- Automated testing at each stage
- Checklist validation
- Performance metrics

### Control & Governance
- Ethics engine validation
- Safety monitoring
- Resource allocation
- Audit trail generation

### Learning & Adaptation
- Pattern recognition from feedback
- Knowledge base updates
- Process improvement suggestions
- Cross-team learning synthesis

## Customization

### Creating Your Own Demo

1. Copy the demo template:
```bash
cp -r demos/template demos/my_demo
```

2. Modify the scenario configuration:
```yaml
# demos/my_demo/scenario.yaml
name: "My Custom Demo"
description: "Description of your scenario"
workflow: "workflow_type"
teams:
  - name: "team_name"
    size: 5
    roles: ["PM", "Architect", "Developer", "QA", "SM"]
```

3. Define your requirements:
```markdown
# demos/my_demo/inputs/requirements.md
Your business requirements here...
```

4. Run your demo:
```bash
cd demos/my_demo
python run_demo.py
```

### Modifying Existing Demos

Each demo's behavior can be customized through:
- `scenario.yaml`: Change team composition, workflow selection
- `inputs/constraints.yaml`: Adjust resource limits, timeframes
- `workflows/main.yaml`: Modify workflow steps and conditions

## Monitoring & Metrics

During demo execution, you can monitor:

### Real-time Dashboard
Open in browser: http://localhost:8001/dashboard

### Metrics API
```bash
curl http://localhost:8002/api/metrics/teams
```

### Workflow Status
```bash
curl http://localhost:8002/api/workflows/status
```

## Troubleshooting

### Common Issues

1. **Docker containers not running**
   - Solution: Run `docker-compose up -d` from `/docker` directory

2. **Permission denied errors**
   - Solution: Ensure proper file permissions with `chmod +x run_demo.py`

3. **Resource allocation failures**
   - Solution: Check resource limits in `docker-compose.yml`

4. **Workflow execution hangs**
   - Solution: Check agent logs with `docker logs team-<name>`

### Debug Mode

Run demos with debug output:
```bash
python run_demo.py --debug
```

### Log Files

Logs are available at:
- Control Layer: `/control/logs/`
- Coordination: `/coordination/logs/`
- Team Agents: `/docker/logs/teams/`

## Support

For issues or questions:
1. Check the troubleshooting guide above
2. Review logs for error messages
3. Consult the main documentation at `/docs/`
4. Report issues in the project repository

## Next Steps

After running the demos:
1. Explore the generated outputs in each demo's `outputs/` directory
2. Review the metrics and performance data
3. Experiment with customization options
4. Create your own scenarios
5. Integrate with your existing workflows

## License

These demos are part of the Agile AI Company framework and follow the same license as the main project.