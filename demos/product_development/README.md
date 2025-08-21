# Product Development Demo: AI-Powered Task Management Application

## Overview

This demo showcases a complete product development cycle for an AI-powered task management application. It demonstrates how autonomous AI agents collaborate in an agile environment to design, develop, and deliver a software product.

## Scenario Description

**Product**: TaskFlow AI - An intelligent task management system that uses AI to:
- Automatically prioritize tasks based on context and deadlines
- Suggest task breakdowns and time estimates
- Identify dependencies between tasks
- Provide intelligent reminders and scheduling

**Team Composition**:
- Product Manager (PM): Defines requirements and priorities
- System Architect: Designs technical architecture
- 2 Developers: Implement features
- QA Engineer: Ensures quality and testing
- Scrum Master: Facilitates agile process

## Demo Flow

### Phase 1: Product Definition (15 minutes)
1. **PM Agent** creates Product Requirements Document (PRD)
2. **Architect Agent** reviews PRD and creates system architecture
3. **Team Formation** based on technical requirements

### Phase 2: Sprint Planning (10 minutes)
1. **PM Agent** creates and prioritizes product backlog
2. **Scrum Master** facilitates sprint planning
3. **Team** commits to sprint backlog based on velocity

### Phase 3: Development Sprint (30 minutes)
1. **Daily Standup** - Team members report progress
2. **Developers** implement user stories in parallel
3. **QA Engineer** creates test plans and executes tests
4. **Architect** reviews code for architectural compliance

### Phase 4: Sprint Review & Retrospective (10 minutes)
1. **Sprint Review** - Demo completed features
2. **Retrospective** - Team identifies improvements
3. **Metrics Analysis** - Velocity and quality metrics

## Running the Demo

### Quick Start
```bash
cd /home/magadiel/Desktop/agent-zero/demos/product_development
python run_demo.py
```

### Interactive Mode
```bash
python run_demo.py --interactive
```
This mode pauses at key points for explanation and allows you to inspect intermediate outputs.

### Custom Configuration
```bash
python run_demo.py --config custom_scenario.yaml
```

## Expected Outputs

After running the demo, you'll find the following in the `outputs/` directory:

### Documents Generated
1. **PRD.md** - Product Requirements Document
2. **architecture.md** - System Architecture Document
3. **sprint_backlog.md** - Sprint planning results
4. **user_stories/** - Individual user story files
5. **test_plans/** - QA test plans and results
6. **code/** - Simulated code implementations

### Reports
1. **sprint_report.md** - Sprint completion summary
2. **velocity_metrics.json** - Team velocity data
3. **quality_report.md** - Code quality metrics
4. **retrospective.md** - Team retrospective findings

### Metrics
- Story points completed: 21
- Sprint velocity: 21 points
- Quality score: 94%
- Test coverage: 87%
- Defect escape rate: 2%

## Key Features Demonstrated

### 1. Agile Ceremonies
- ✅ Sprint Planning with capacity-based commitment
- ✅ Daily Standups with blocker identification
- ✅ Sprint Review with stakeholder feedback
- ✅ Retrospective with action items

### 2. Multi-Agent Collaboration
- ✅ Document handoffs between agents
- ✅ Parallel development work
- ✅ Cross-functional team coordination
- ✅ Real-time communication

### 3. Quality Gates
- ✅ PRD approval before development
- ✅ Architecture review gate
- ✅ Code review process
- ✅ Testing sign-off

### 4. BMAD Integration
- ✅ Agent activation with personas
- ✅ Task execution with checklists
- ✅ Template-based document generation
- ✅ Quality verification

## Customization Options

### Modify Team Size
Edit `scenario.yaml`:
```yaml
teams:
  development:
    size: 7  # Increase team size
    roles:
      - PM: 1
      - Architect: 1
      - Developer: 3  # Add more developers
      - QA: 1
      - SM: 1
```

### Change Product Requirements
Edit `inputs/requirements.md` to define different features or constraints.

### Adjust Sprint Duration
```yaml
sprint:
  duration: 14  # days
  capacity_percentage: 80  # Account for meetings, etc.
```

## Validation

Run the validation script to verify demo outputs:
```bash
python validate_demo.py
```

Validation checks:
- ✅ All required documents generated
- ✅ Workflow completed successfully
- ✅ Quality gates passed
- ✅ Metrics within expected ranges
- ✅ No critical errors in logs

## Monitoring During Execution

### Real-time Dashboard
Open: http://localhost:8001/dashboard/product-dev

### Team Activity
```bash
# Watch team communication
docker logs -f team-product-development

# Monitor workflow progress
curl http://localhost:8002/api/workflows/product-dev/status
```

### Metrics Tracking
```bash
# Get current sprint metrics
curl http://localhost:8002/api/metrics/sprint/current

# Team performance
curl http://localhost:8002/api/metrics/teams/product-development
```

## Troubleshooting

### Issue: Demo fails at sprint planning
**Solution**: Check that all required agents are running:
```bash
docker ps | grep team-product
```

### Issue: Documents not being generated
**Solution**: Verify file permissions:
```bash
ls -la outputs/
chmod 755 outputs/
```

### Issue: Quality gates failing
**Solution**: Review gate criteria in `workflows/main.yaml` and adjust thresholds if needed.

## Learning Points

This demo illustrates:

1. **Autonomous Planning**: Agents independently break down high-level requirements into actionable tasks
2. **Self-Organization**: Teams dynamically allocate work based on skills and capacity
3. **Continuous Quality**: Multiple quality checkpoints throughout the process
4. **Adaptive Behavior**: Agents learn from retrospectives and improve over time
5. **Scalable Collaboration**: Framework handles increasing team sizes and complexity

## Next Steps

1. **Extend the Demo**: Add more complex features or multiple sprints
2. **Integrate with IDE**: Connect to actual development tools
3. **Add Custom Agents**: Create specialized agents for your domain
4. **Production Deployment**: Use learnings to deploy in real environment

## Files Structure

```
product_development/
├── README.md                 # This file
├── scenario.yaml            # Demo configuration
├── inputs/
│   ├── requirements.md      # Product requirements
│   ├── constraints.yaml     # Technical constraints
│   └── personas.yaml        # User personas
├── workflows/
│   ├── main.yaml           # Primary workflow
│   └── sprint.yaml         # Sprint workflow
├── templates/
│   ├── prd.yaml           # PRD template
│   ├── story.yaml         # User story template
│   └── test_plan.yaml     # Test plan template
├── outputs/               # Generated during demo
│   ├── PRD.md
│   ├── architecture.md
│   ├── sprint_backlog.md
│   ├── user_stories/
│   ├── test_plans/
│   └── metrics/
├── run_demo.py            # Execution script
├── validate_demo.py       # Validation script
└── config.yaml           # Default configuration
```

## Related Documentation

- [Main Demo Guide](../README.md)
- [Workflow Documentation](/coordination/README.md)
- [Agent Profiles](/agents/README.md)
- [BMAD Methodology](/docs/bmad-methodology-analysis.md)