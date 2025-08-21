# BMAD Task Loading System Documentation

## Overview

The BMAD Task Loading System implements a comprehensive framework for executing BMAD-style tasks within Agent-Zero. It provides sequential and parallel task execution, context gathering, source citation tracking, and validation mechanisms that enable agents to execute complex, multi-step workflows with full transparency and auditability.

## Architecture

### Core Components

#### 1. Task Loader (`/python/helpers/task_loader.py`)
Manages the loading, parsing, and validation of BMAD task definitions from various sources.

**Key Classes:**
- `TaskStep`: Represents individual execution steps within a task
- `TaskDependency`: Manages task dependencies (templates, checklists, data)
- `TaskContext`: Tracks sources, citations, and artifacts during execution
- `BMADTask`: Complete task definition with steps and dependencies
- `TaskLoader`: Loads tasks from files or dictionaries
- `TaskRegistry`: Manages multiple tasks and enables search/categorization

#### 2. Task Executor (`/python/tools/bmad_task_executor.py`)
Executes BMAD tasks with support for sequential/parallel execution, validation, and integration with Agent-Zero's tool system.

**Key Features:**
- Sequential and parallel step execution
- Context gathering and source citation
- Step validation and retry mechanisms
- Dry run capability for validation
- Integration with agent tools
- Interrupt and resume support

## Task Definition Format

### YAML Structure

```yaml
id: "task_id"
name: "Task Name"
description: "Task description"
category: "execution|validation|analysis|creation"
sequential: true  # Sequential or parallel execution
gather_context: true  # Gather context before execution
cite_sources: true  # Track source citations

steps:
  - id: "step1"
    name: "Step Name"
    description: "Step description"
    action: "gather_data|process|validate|generate|tool"
    params:
      key: value
    requires: []  # Step dependencies (step IDs)
    produces: ["artifact1"]  # Artifacts produced
    validation:
      required_fields: ["field1", "field2"]
      conditions:
        - field: "status"
          operator: "equals"
          value: "success"
    timeout: 300  # seconds
    retries: 2
    optional: false

dependencies:
  - type: "template|checklist|data|workflow"
    name: "dependency_name"
    path: "path/to/resource.yaml"
    lazy_load: true
    required: true

validation:
  required_artifacts: ["final_output"]
  success_criteria:
    - type: "all_steps_success"
      description: "All steps must complete successfully"
```

## Usage Examples

### 1. Loading and Executing a Task from File

```python
from python.helpers.task_loader import TaskLoader
from python.tools.bmad_task_executor import BMADTaskExecutor

# Load task
loader = TaskLoader(base_path="/path/to/tasks")
task = loader.load_task("my_task.yaml")

# Execute task
executor = BMADTaskExecutor(agent)
response = await executor.execute(
    task_path="my_task.yaml",
    params={"input": "value"}
)
```

### 2. Creating and Executing a Task Programmatically

```python
task_definition = {
    "id": "dynamic_task",
    "name": "Dynamic Task",
    "description": "Created at runtime",
    "category": "execution",
    "steps": [
        {
            "id": "s1",
            "name": "Gather Data",
            "description": "Collect required data",
            "action": "gather_data",
            "produces": ["data"]
        },
        {
            "id": "s2",
            "name": "Process",
            "description": "Process the data",
            "action": "process",
            "requires": ["s1"],
            "params": {"method": "analyze"}
        }
    ]
}

response = await executor.execute(
    task_data=task_definition,
    params={"source": "database"}
)
```

### 3. Dry Run Validation

```python
# Validate task without execution
response = await executor.execute(
    task_path="complex_task.yaml",
    dry_run=True
)

# Response contains validation report
print(response.message)
```

### 4. Resume from Checkpoint

```python
# Resume execution from specific step
response = await executor.execute(
    task_path="long_task.yaml",
    resume_from="step3"
)
```

## Task Actions

### Built-in Actions

1. **gather_data**: Collect data from various sources
2. **process**: Process or transform data
3. **validate**: Validate data or results
4. **generate**: Generate new content or artifacts
5. **tool**: Execute an agent tool

### Custom Tool Integration

```python
# Use agent tools within tasks
step = {
    "id": "use_tool",
    "name": "Execute Tool",
    "action": "tool",
    "params": {
        "tool": "code_execution",
        "params": {
            "code": "print('Hello')",
            "language": "python"
        }
    }
}
```

## Context and Citations

### Context Gathering
Tasks can gather context from multiple sources:
- Agent's memory and knowledge base
- Previous task executions
- External documents
- User-provided parameters

### Source Citations
All data sources are tracked with citations:

```python
context.add_source(
    name="source_name",
    content="source content",
    citation={
        "type": "external",
        "url": "http://example.com",
        "timestamp": "2024-01-01T00:00:00"
    }
)
```

## Validation System

### Step Validation
Validate individual step outputs:

```yaml
validation:
  required_fields: ["status", "result"]
  conditions:
    - field: "status"
      operator: "equals"
      value: "success"
    - field: "result"
      operator: "exists"
```

### Task Validation
Validate overall task completion:

```yaml
validation:
  required_artifacts: ["final_report", "processed_data"]
  success_criteria:
    - type: "all_steps_success"
    - type: "artifact_exists"
      artifact: "final_report"
```

## Error Handling

### Retry Mechanism
Steps can be configured with automatic retry:

```yaml
steps:
  - id: "retry_step"
    retries: 3  # Retry up to 3 times
    timeout: 60  # Timeout after 60 seconds
```

### Optional Steps
Mark steps as optional to continue on failure:

```yaml
steps:
  - id: "optional_step"
    optional: true  # Task continues even if this fails
```

## Task Registry

### Managing Multiple Tasks

```python
from python.helpers.task_loader import TaskRegistry

registry = TaskRegistry()

# Register tasks
registry.register_from_file("task1.yaml")
registry.register_from_file("task2.yaml")

# Search tasks
analysis_tasks = registry.get_tasks_by_category("analysis")
matching_tasks = registry.search_tasks("data processing")

# Get specific task
task = registry.get_task("task_id")
```

## Integration with BMAD Agents

The task system integrates seamlessly with BMAD-enhanced agents:

```python
# Agent with BMAD enhancements can execute tasks
if hasattr(agent, 'bmad_profile'):
    # Load agent-specific tasks
    for task_name in agent.bmad_profile.dependencies.get('tasks', []):
        task = loader.load_task(f"tasks/{task_name}.yaml")
        # Execute task with agent context
        response = await executor.execute(
            task_data=task.to_dict(),
            params={"agent_context": agent.context}
        )
```

## Performance Considerations

### Lazy Loading
Dependencies are loaded only when needed:

```yaml
dependencies:
  - name: "large_dataset"
    path: "data/large.json"
    lazy_load: true  # Load only when accessed
```

### Caching
Tasks are cached to avoid repeated loading:

```python
loader = TaskLoader()
task1 = loader.load_task("task.yaml")  # Loads from file
task2 = loader.load_task("task.yaml")  # Uses cache
```

### Parallel Execution
Non-sequential tasks execute steps in parallel:

```yaml
sequential: false  # Enable parallel execution
steps:
  - id: "parallel1"
    # No dependencies, executes immediately
  - id: "parallel2"
    # No dependencies, executes immediately
  - id: "dependent"
    requires: ["parallel1", "parallel2"]
    # Waits for both to complete
```

## Testing

### Unit Tests
Comprehensive test suite in `/python/tests/test_bmad_task.py`:

```bash
python3 -m unittest python.tests.test_bmad_task
```

### Test Coverage
- Task loading and parsing
- Step execution (sequential and parallel)
- Validation mechanisms
- Error handling and retries
- Context and citation tracking
- Dependency management

## Best Practices

### 1. Task Design
- Keep steps focused and atomic
- Use clear, descriptive IDs and names
- Define dependencies explicitly
- Include validation where appropriate

### 2. Error Handling
- Mark non-critical steps as optional
- Configure appropriate retry counts
- Set reasonable timeouts
- Provide clear error messages

### 3. Context Management
- Gather context early in the task
- Cite all sources appropriately
- Track artifacts throughout execution
- Clean up resources after completion

### 4. Performance
- Use lazy loading for large dependencies
- Enable parallel execution where possible
- Cache frequently used tasks
- Monitor resource usage

## Future Enhancements

### Planned Features
1. **Visual Task Designer**: GUI for creating task definitions
2. **Task Templates**: Reusable task patterns
3. **Advanced Validation**: Complex validation rules and expressions
4. **Task Versioning**: Track task definition changes
5. **Distributed Execution**: Execute steps across multiple agents
6. **Real-time Monitoring**: Live task execution dashboard
7. **Task Marketplace**: Share and discover task definitions

### Integration Roadmap
1. **Workflow Engine**: Connect with Phase 3 workflow system
2. **Quality Gates**: Integrate with Phase 5 quality system
3. **Agile Ceremonies**: Support sprint planning and retrospectives
4. **Learning System**: Feed execution data to learning synthesizer

## Conclusion

The BMAD Task Loading System provides a robust foundation for executing complex, multi-step tasks within Agent-Zero. Its support for sequential and parallel execution, comprehensive validation, and full audit trails makes it ideal for building autonomous AI teams that can execute sophisticated workflows while maintaining transparency and control.

The system's integration with BMAD agent profiles and Agent-Zero's existing tool ecosystem enables powerful automation capabilities while preserving the framework's core principles of transparency, customization, and control.