# BMAD Agent Enhancement Documentation

## Overview

The BMAD Agent Enhancement module extends Agent-Zero's simple profile system with comprehensive BMAD-style agent definitions. This enhancement provides structured personas, command systems, dependency management, and activation instructions while maintaining full backward compatibility with existing Agent-Zero profiles.

## Features

### 1. Enhanced Agent Profiles
- **Personas**: Detailed role definitions with identity, style, focus areas, and core principles
- **Commands**: Agent-specific capabilities mapped to tools and tasks
- **Dependencies**: Lazy-loaded resources (tasks, templates, checklists, data, workflows)
- **Activation Instructions**: Multi-phase initialization sequences

### 2. Backward Compatibility
- Existing Agent-Zero profiles continue to work unchanged
- BMAD enhancement is opt-in per agent profile
- Graceful fallback when BMAD features are not available

### 3. Lazy Loading
- Dependencies are loaded only when needed
- Reduces memory footprint and startup time
- Improves performance for large agent ecosystems

## Architecture

### Core Components

#### BMADAgentDefinition
Complete agent definition including:
- Basic info (name, id, title, icon, when_to_use)
- Persona definition
- Command list
- Activation phases
- Dependencies mapping
- Loaded resources cache

#### BMADAgentLoader
Manages loading and caching of BMAD agent definitions:
- Parses agent.md files with YAML frontmatter
- Loads command implementations from Python modules
- Manages dependency loading
- Maintains agent and command registries

#### BMADAgentEnhancer
Enhances Agent-Zero agents with BMAD capabilities:
- Attaches BMAD definition to agent instance
- Adds BMAD-specific methods to agents
- Manages activation sequence execution
- Handles command execution

#### CommandMapper
Maps BMAD commands to Agent-Zero tools:
- Registers command-to-tool mappings
- Creates wrapper functions for tool execution
- Enables seamless integration with existing tools

## Usage

### Creating a BMAD Agent Profile

1. Create agent directory structure:
```
agents/
└── product_manager/
    ├── agent.md           # BMAD agent definition
    ├── commands/          # Command implementations
    │   ├── create_prd.py
    │   └── prioritize_backlog.py
    ├── dependencies/      # Agent-specific resources
    │   ├── tasks/
    │   ├── templates/
    │   └── checklists/
    └── prompts/          # Agent-Zero compatible prompts
        └── agent.system.main.role.md
```

2. Define agent in `agent.md`:
```markdown
---
agent:
  name: ProductManager
  id: product-manager
  title: Product Manager
  icon: 📊
  whenToUse: For product strategy and requirements

persona:
  role: Strategic product leader
  style: Analytical and data-driven
  identity: Customer advocate and business strategist
  focus:
    - User needs analysis
    - Market positioning
    - Feature prioritization
  core_principles:
    - User-centric design
    - Data-driven decisions
    - Continuous iteration

commands:
  - create_prd
  - prioritize_backlog
  - analyze_metrics

activation-instructions:
  - name: Initialize
    description: Load core resources
    actions:
      - load_templates
      - load_checklists
    validation: check_resources

dependencies:
  templates:
    - prd_template
    - feature_spec
  checklists:
    - product_review
---

# Product Manager Agent

Specialized agent for product management tasks...
```

3. Implement commands in `commands/create_prd.py`:
```python
COMMAND = {
    'name': 'create_prd',
    'description': 'Create a Product Requirements Document',
    'parameters': {
        'title': 'string',
        'features': 'list'
    },
    'dependencies': ['templates/prd_template']
}

async def execute(agent, title, features):
    # Load PRD template
    templates = await agent.load_bmad_dependencies('templates')
    prd_template = templates.get('prd_template')
    
    # Generate PRD content
    prd_content = generate_prd(title, features, prd_template)
    
    # Return result
    return prd_content
```

### Using BMAD-Enhanced Agents

1. Agent automatically enhanced when profile is specified:
```python
config = AgentConfig(
    profile="product_manager",  # BMAD profile name
    # ... other config
)
agent = Agent(0, config)
# Agent is automatically BMAD-enhanced if profile exists
```

2. Activate BMAD profile:
```python
if agent.bmad_enhanced:
    await agent.activate_bmad_profile()
```

3. Execute BMAD commands:
```python
if agent.bmad_enhanced:
    result = await agent.execute_bmad_command_wrapper(
        "create_prd",
        title="New Feature",
        features=["Feature 1", "Feature 2"]
    )
```

4. Access persona information:
```python
if agent.bmad_enhanced:
    persona = agent.get_bmad_persona()
    print(f"Role: {persona.role}")
    print(f"Principles: {persona.core_principles}")
```

5. Load dependencies on demand:
```python
if agent.bmad_enhanced:
    templates = await agent.load_bmad_dependencies("templates")
    checklists = await agent.load_bmad_dependencies("checklists")
```

## Integration with Agent-Zero

### Modified Files

1. **agent.py**
   - Added BMAD enhancement during agent initialization
   - Added BMAD-specific methods to Agent class
   - Maintains full backward compatibility

2. **python/helpers/bmad_agent.py** (New)
   - Complete BMAD implementation
   - All BMAD-specific logic isolated here
   - No impact on existing Agent-Zero functionality

### Testing

Comprehensive test suite in `python/tests/test_bmad_agent.py`:
- Unit tests for all BMAD components
- Integration tests for full agent loading
- Mock support for testing without dependencies
- 20 tests covering all functionality

Run tests:
```bash
python3 -m unittest python.tests.test_bmad_agent
```

## Benefits

1. **Structured Agent Definitions**: Clear, comprehensive agent specifications
2. **Reusable Components**: Templates, checklists, and tasks shared across agents
3. **Quality Assurance**: Built-in validation and verification mechanisms
4. **Scalability**: Lazy loading and efficient resource management
5. **Maintainability**: Separation of concerns with modular design
6. **Flexibility**: Easy to extend and customize per agent
7. **Backward Compatibility**: Existing agents continue to work unchanged

## Migration Guide

### Converting Existing Agents to BMAD

1. Keep existing prompt files for compatibility
2. Create `agent.md` with BMAD definition
3. Gradually migrate functionality to commands
4. Add dependencies as needed
5. Test both classic and BMAD modes

### Example Migration

From classic Agent-Zero profile:
```
agents/developer/
├── _context.md
└── prompts/
    └── agent.system.main.role.md
```

To BMAD-enhanced profile:
```
agents/developer/
├── _context.md                    # Keep for compatibility
├── agent.md                        # Add BMAD definition
├── commands/                       # Add command implementations
│   ├── implement_feature.py
│   └── review_code.py
├── dependencies/                   # Add resources
│   └── checklists/
│       └── code_review.yaml
└── prompts/                       # Keep existing
    └── agent.system.main.role.md
```

## Future Enhancements

1. **Workflow Integration**: Connect BMAD agents with workflow engine
2. **Team Formation**: Use BMAD definitions for team composition
3. **Command Discovery**: Automatic command registration from filesystem
4. **Visual Editor**: GUI for creating and editing BMAD agents
5. **Agent Marketplace**: Share and reuse agent definitions
6. **Performance Metrics**: Track command execution and success rates
7. **Learning Integration**: Agents learn and improve their personas

## Conclusion

The BMAD Agent Enhancement successfully extends Agent-Zero with enterprise-grade agent definition capabilities while maintaining the framework's philosophy of transparency and flexibility. This creates a foundation for building sophisticated multi-agent systems with clear roles, responsibilities, and quality assurance mechanisms.