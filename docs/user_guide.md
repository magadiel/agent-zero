# Agile AI Company - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [System Architecture](#system-architecture)
4. [Control Layer](#control-layer)
5. [Agent Management](#agent-management)
6. [Workflow System](#workflow-system)
7. [Agile Features](#agile-features)
8. [Quality & Performance](#quality--performance)
9. [Docker Deployment](#docker-deployment)
10. [Common Use Cases](#common-use-cases)
11. [Best Practices](#best-practices)
12. [Support](#support)

## Introduction

Welcome to the Agile AI Company framework built on Agent-Zero. This system transforms Agent-Zero into a comprehensive platform for running autonomous AI companies using agile methodologies, BMAD-style agent definitions, and multi-layer control architecture.

### Key Features
- **Multi-Agent Teams**: Self-organizing AI agent teams with specialized roles
- **Agile Workflows**: Automated sprint planning, daily standups, and retrospectives
- **Quality Gates**: Built-in quality verification at multiple levels
- **Ethics & Safety**: Comprehensive control layer for ethical AI operation
- **Performance Monitoring**: Real-time metrics and KPI tracking
- **Docker Containerization**: Scalable, isolated deployment

### System Philosophy
The system operates on five core principles:
1. **Agent Specialization**: Each agent has a clearly defined role and capabilities
2. **Workflow-Driven Execution**: Projects follow structured multi-agent workflows
3. **Document-Centric Operations**: Knowledge flows through documents between agents
4. **Quality Gates**: Verification mechanisms ensure high-quality output
5. **Self-Sufficiency**: Agents have everything needed to complete tasks autonomously

## Getting Started

### Prerequisites
- Python 3.8+
- Docker and Docker Compose
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### Quick Start

1. **Clone the Repository**
```bash
git clone https://github.com/your-org/agent-zero.git
cd agent-zero
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r control/requirements.txt
pip install -r metrics/requirements.txt
```

3. **Configure Environment**
```bash
cp docker/.env.example docker/.env
# Edit docker/.env with your settings
```

4. **Start the System**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

5. **Verify Installation**
```bash
python tests/test_system_health.py
```

### First Run
After starting the system, you can:
1. Access the web UI at http://localhost:80
2. View the KPI dashboard at http://localhost:8001
3. Monitor workflows at http://localhost:8002

## System Architecture

### Three-Layer Architecture

```
┌─────────────────────────────────────┐
│   CONTROL LAYER (Rigid/Stable)      │
│   • Ethics Engine                   │
│   • Safety Protocols                │
│   • Resource Allocation             │
│   • Audit & Compliance              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   COORDINATION LAYER (Semi-Stable)   │
│   • Agent Orchestrator              │
│   • Workflow Engine                 │
│   • Performance Monitor             │
│   • Learning Synthesizer            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   EXECUTION LAYER (Dynamic/Agile)   │
│   • Autonomous Agent Teams          │
│   • Self-Organizing Cells           │
│   • Rapid Iteration Cycles          │
└─────────────────────────────────────┘
```

### Component Overview
- **Control Layer**: Ensures ethical operation and resource management
- **Coordination Layer**: Orchestrates teams and workflows
- **Execution Layer**: Where agents perform actual work

## Control Layer

### Ethics Engine
The ethics engine validates all agent decisions against configurable ethical constraints.

#### Configuration
Edit `/control/config/ethical_constraints.yaml`:
```yaml
ethical_constraints:
  harm_prevention:
    enabled: true
    severity: critical
  privacy_protection:
    enabled: true
    data_retention: 30  # days
  fairness_metrics:
    bias_threshold: 0.1
```

#### Usage
```python
from control.ethics_engine import EthicsEngine

engine = EthicsEngine()
decision = {"action": "process_data", "target": "user_data"}
result = await engine.validate_decision(decision)
if result.approved:
    # Proceed with action
else:
    # Handle rejection
    print(f"Rejected: {result.reason}")
```

### Safety Monitor
Real-time monitoring with automatic interventions.

#### Thresholds Configuration
Edit `/control/config/safety_thresholds.yaml`:
```yaml
thresholds:
  cpu_usage:
    warning: 70
    critical: 90
  memory_usage:
    warning: 80
    critical: 95
  response_time:
    warning: 1000  # ms
    critical: 5000
```

### Resource Allocator
Manages compute resources across agent teams.

#### Team Resource Limits
```yaml
team_profiles:
  customer_service:
    max_agents: 10
    cpu_limit: "2000m"
    memory_limit: "4Gi"
  development:
    max_agents: 20
    cpu_limit: "4000m"
    memory_limit: "8Gi"
```

## Agent Management

### Agent Types

#### 1. Product Manager
- **Role**: Define product requirements and strategy
- **Commands**: create-prd, prioritize-backlog, validate-epic
- **Usage**:
```python
agent = Agent(profile="product_manager")
await agent.execute_command("create-prd", requirements="...")
```

#### 2. Architect
- **Role**: System design and technical decisions
- **Commands**: create-architecture, review-design
- **Usage**:
```python
agent = Agent(profile="architect")
await agent.execute_command("create-architecture", prd="...")
```

#### 3. Developer
- **Role**: Implementation and testing
- **Commands**: implement-story, run-tests, fix-bugs
- **Usage**:
```python
agent = Agent(profile="developer")
await agent.execute_command("implement-story", story_id="...")
```

#### 4. QA Engineer
- **Role**: Quality assurance and testing
- **Commands**: review-code, execute-tests, create-test-plan
- **Usage**:
```python
agent = Agent(profile="qa_engineer")
await agent.execute_command("review-code", pr_id="...")
```

#### 5. Scrum Master
- **Role**: Facilitate agile ceremonies
- **Commands**: run-standup, plan-sprint, facilitate-retro
- **Usage**:
```python
agent = Agent(profile="scrum_master")
await agent.execute_command("run-standup", team_id="...")
```

### Creating Custom Agents

1. **Create Agent Definition**
Create `/agents/custom_role/agent.md`:
```markdown
---
agent:
  name: Custom Agent
  id: custom-agent
  title: Custom Role
  
persona:
  role: Detailed role description
  style: Communication style
  focus: Primary responsibilities
  
commands:
  - *custom-command: Execute custom task
  
dependencies:
  tasks: [custom-task]
  templates: [custom-template]
---
```

2. **Register Agent**
```python
from python.helpers.bmad_agent import BMADAgentEnhancer

enhancer = BMADAgentEnhancer()
agent = Agent(profile="custom_role")
enhancer.enhance_agent(agent)
```

## Workflow System

### Workflow Types

#### 1. Greenfield Development
New product development from scratch.
```yaml
workflow: greenfield_development
steps:
  - agent: pm
    action: create_prd
  - agent: architect
    action: design_system
  - agent: dev_team
    action: implement
  - agent: qa
    action: test
```

#### 2. Brownfield Development
Maintaining and enhancing existing systems.
```yaml
workflow: brownfield_development
steps:
  - agent: analyst
    action: analyze_existing
  - agent: architect
    action: plan_changes
  - agent: dev_team
    action: implement_changes
  - agent: qa
    action: regression_test
```

#### 3. Customer Service
Automated customer support workflow.
```yaml
workflow: customer_service
steps:
  - agent: support
    action: triage_ticket
  - agent: specialist
    action: resolve_issue
  - agent: qa
    action: verify_resolution
```

### Creating Custom Workflows

1. **Define Workflow**
Create `/workflows/custom_workflow.yaml`:
```yaml
name: Custom Workflow
description: Custom business process
steps:
  - step: step1
    agent: agent1
    action: action1
    creates: document1
  - step: step2
    agent: agent2
    action: action2
    requires: document1
    creates: document2
```

2. **Execute Workflow**
```python
from coordination.workflow_engine import WorkflowEngine

engine = WorkflowEngine()
workflow = await engine.load_workflow("custom_workflow")
result = await engine.execute(workflow, context={})
```

## Agile Features

### Sprint Management

#### Planning a Sprint
```python
from agile.sprint_manager import SprintManager

manager = SprintManager(team_id="dev-team")
sprint = await manager.plan_sprint(
    duration_days=14,
    capacity_points=100
)
```

#### Daily Standup
```python
from agile.standup_facilitator import StandupFacilitator

facilitator = StandupFacilitator(team_id="dev-team")
report = await facilitator.run_standup()
print(report.to_markdown())
```

#### Sprint Retrospective
```python
from agile.retrospective_analyzer import RetrospectiveAnalyzer

analyzer = RetrospectiveAnalyzer()
insights = await analyzer.analyze_sprint(sprint_id="sprint-1")
actions = analyzer.generate_action_items(insights)
```

### Story Management

#### Creating Stories
```python
from agile.story_manager import StoryManager

manager = StoryManager()
story = manager.create_story(
    title="Implement user authentication",
    points=5,
    acceptance_criteria=[
        "Users can register",
        "Users can login",
        "Passwords are encrypted"
    ]
)
```

#### Story States
Stories progress through these states:
- DRAFT → READY → IN_SPRINT → IN_PROGRESS → IN_REVIEW → DONE → ACCEPTED

### Epic Management
```python
from agile.epic_manager import EpicManager

manager = EpicManager()
epic = manager.create_epic(
    title="User Management System",
    stories=["auth-story", "profile-story", "settings-story"]
)
progress = manager.calculate_progress(epic.id)
```

## Quality & Performance

### Quality Gates

#### Defining Gates
```python
from metrics.quality_tracker import QualityTracker

tracker = QualityTracker()
gate = tracker.create_gate(
    name="Story Completion",
    checks=[
        "code_review_passed",
        "tests_passing",
        "documentation_updated"
    ]
)
```

#### Gate Evaluation
```python
result = await tracker.evaluate_gate(gate_id, context)
if result.status == "PASS":
    # Proceed
elif result.status == "CONCERNS":
    # Review concerns
elif result.status == "FAIL":
    # Block progression
```

### Performance Monitoring

#### Key Metrics
```python
from metrics.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
metrics = await monitor.get_metrics(team_id="dev-team")
print(f"Velocity: {metrics.velocity}")
print(f"Cycle Time: {metrics.cycle_time}")
print(f"Throughput: {metrics.throughput}")
```

#### Custom Metrics
```python
monitor.add_metric(
    name="custom_metric",
    calculation=lambda data: sum(data) / len(data),
    threshold_warning=80,
    threshold_critical=95
)
```

### Compliance Tracking
```python
from metrics.compliance_tracker import ComplianceTracker

tracker = ComplianceTracker()
violations = await tracker.check_compliance(team_id="dev-team")
report = tracker.generate_report(format="markdown")
```

## Docker Deployment

### Development Environment
```bash
docker-compose -f docker/docker-compose.dev.yml up
```

### Production Deployment
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Scaling Teams
```bash
# Scale customer service team to 5 agents
docker-compose scale team-customer=5

# Scale development team to 10 agents
docker-compose scale team-development=10
```

### Resource Limits
Configure in `docker-compose.yml`:
```yaml
services:
  team-customer:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Common Use Cases

### 1. Product Development Team
```python
# Form a product development team
orchestrator = TeamOrchestrator()
team = await orchestrator.form_team(
    mission="Develop new feature",
    agents=["pm", "architect", "dev1", "dev2", "qa"]
)

# Execute development workflow
engine = WorkflowEngine()
await engine.execute("greenfield_development", team=team)
```

### 2. Customer Support Automation
```python
# Create support team
team = await orchestrator.form_team(
    mission="Handle customer tickets",
    agents=["support1", "support2", "specialist"]
)

# Process tickets
for ticket in tickets:
    await engine.execute("customer_service", 
                        team=team, 
                        context={"ticket": ticket})
```

### 3. Operations Monitoring
```python
# Create operations team
team = await orchestrator.form_team(
    mission="Monitor system health",
    agents=["ops1", "ops2", "sre"]
)

# Run monitoring workflow
await engine.execute("operations_monitoring", 
                    team=team,
                    continuous=True)
```

## Best Practices

### 1. Agent Design
- Keep agent roles focused and specific
- Define clear command interfaces
- Document all dependencies
- Test agent behaviors in isolation

### 2. Workflow Design
- Start simple, iterate towards complexity
- Include quality gates at critical points
- Plan for failure scenarios
- Document expected outputs

### 3. Team Management
- Right-size teams (5-9 agents typically)
- Define clear team missions
- Rotate team compositions for diversity
- Monitor team performance metrics

### 4. Resource Management
- Set appropriate resource limits
- Monitor resource usage trends
- Plan for peak loads
- Implement auto-scaling policies

### 5. Quality Assurance
- Define acceptance criteria upfront
- Implement automated testing
- Use quality gates liberally
- Track quality metrics over time

### 6. Security
- Regular security audits
- Principle of least privilege
- Encrypt sensitive data
- Monitor for anomalies

## Support

### Getting Help
- **Documentation**: `/docs/` directory
- **API Reference**: `/docs/api_reference.md`
- **Troubleshooting**: `/docs/troubleshooting.md`
- **Examples**: `/demos/` directory

### Monitoring Tools
- **Logs**: `docker-compose logs -f [service]`
- **Metrics**: http://localhost:3000 (Grafana)
- **Health Check**: `curl http://localhost:8000/health`

### Common Commands

#### System Control
```bash
# Start system
docker-compose up -d

# Stop system
docker-compose down

# Restart service
docker-compose restart [service]

# View logs
docker-compose logs -f [service]
```

#### Agent Management
```python
# List agents
orchestrator.list_agents()

# Get agent status
agent.get_status()

# Reset agent
agent.reset()
```

#### Workflow Management
```python
# List workflows
engine.list_workflows()

# Get workflow status
engine.get_status(workflow_id)

# Cancel workflow
engine.cancel(workflow_id)
```

### Performance Tuning

#### Memory Optimization
```python
# Configure memory limits
config.agent_memory_limit = "512M"
config.workflow_cache_size = 100
```

#### CPU Optimization
```python
# Configure CPU limits
config.agent_cpu_limit = "500m"
config.parallel_workflows = 4
```

#### Network Optimization
```python
# Configure timeouts
config.api_timeout = 30  # seconds
config.agent_communication_timeout = 10
```

## Appendix

### Glossary
- **Agent**: Autonomous AI entity with specific role
- **Workflow**: Sequence of agent actions
- **Gate**: Quality checkpoint
- **Sprint**: Fixed time period for work
- **Epic**: Large body of work
- **Story**: Unit of work
- **Backlog**: Prioritized list of work

### Version History
- v1.0.0: Initial release with core features
- v1.1.0: Added BMAD integration
- v1.2.0: Enhanced agile features
- v1.3.0: Improved performance monitoring

### License
This project is licensed under the MIT License.

### Contributing
See CONTRIBUTING.md for guidelines.

---

*For more information, see the [API Reference](./api_reference.md) and [Troubleshooting Guide](./troubleshooting.md).*