"""
BMAD-style Workflow Parser for Agent-Zero

This module provides YAML workflow parsing capabilities for orchestrating
multi-agent workflows with conditional branching and document handoffs.
"""

import yaml
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class StepType(str, Enum):
    """Types of workflow steps"""
    AGENT_TASK = "agent_task"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    DOCUMENT_CREATE = "document_create"
    QUALITY_GATE = "quality_gate"
    WAIT = "wait"


class WorkflowState(str, Enum):
    """States of a workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowCondition:
    """Represents a conditional expression in workflow"""
    field: str  # Field to check (e.g., "output.status", "document.exists")
    operator: str  # Operator (e.g., "==", "!=", ">", "<", "contains", "exists")
    value: Any  # Value to compare against
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate the condition against the given context
        
        Args:
            context: Dictionary containing workflow execution context
            
        Returns:
            Boolean result of condition evaluation
        """
        # Navigate nested fields using dot notation
        field_value = context
        for part in self.field.split('.'):
            if isinstance(field_value, dict) and part in field_value:
                field_value = field_value[part]
            else:
                field_value = None
                break
        
        # Evaluate based on operator
        if self.operator == "==":
            return field_value == self.value
        elif self.operator == "!=":
            return field_value != self.value
        elif self.operator == ">":
            return field_value > self.value if field_value is not None else False
        elif self.operator == "<":
            return field_value < self.value if field_value is not None else False
        elif self.operator == ">=":
            return field_value >= self.value if field_value is not None else False
        elif self.operator == "<=":
            return field_value <= self.value if field_value is not None else False
        elif self.operator == "contains":
            return self.value in field_value if field_value is not None else False
        elif self.operator == "exists":
            return field_value is not None
        elif self.operator == "not_exists":
            return field_value is None
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    type: StepType
    name: str
    description: Optional[str] = None
    
    # Agent task specific
    agent: Optional[str] = None  # Agent profile/role
    task: Optional[str] = None  # Task to execute
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)  # Expected outputs
    
    # Document specific
    creates: Optional[str] = None  # Document to create
    requires: List[str] = field(default_factory=list)  # Required documents
    template: Optional[str] = None  # Template to use
    
    # Conditional specific
    condition: Optional[WorkflowCondition] = None
    then_steps: List['WorkflowStep'] = field(default_factory=list)
    else_steps: List['WorkflowStep'] = field(default_factory=list)
    
    # Parallel specific
    parallel_steps: List['WorkflowStep'] = field(default_factory=list)
    
    # Quality gate specific
    checklist: Optional[str] = None
    gate_type: Optional[str] = None  # PASS, CONCERNS, FAIL, WAIVED
    
    # Common
    timeout: Optional[int] = None  # Timeout in seconds
    retry_count: int = 0
    retry_delay: int = 5  # Delay between retries in seconds
    optional: bool = False  # Whether step failure should stop workflow
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create WorkflowStep from dictionary"""
        step = cls(
            id=data.get('id', ''),
            type=StepType(data.get('type', 'agent_task')),
            name=data.get('name', ''),
            description=data.get('description'),
            agent=data.get('agent'),
            task=data.get('task'),
            inputs=data.get('inputs', {}),
            outputs=data.get('outputs', []),
            creates=data.get('creates'),
            requires=data.get('requires', []),
            template=data.get('template'),
            checklist=data.get('checklist'),
            gate_type=data.get('gate_type'),
            timeout=data.get('timeout'),
            retry_count=data.get('retry_count', 0),
            retry_delay=data.get('retry_delay', 5),
            optional=data.get('optional', False)
        )
        
        # Parse condition if present
        if 'condition' in data:
            cond = data['condition']
            step.condition = WorkflowCondition(
                field=cond.get('field', ''),
                operator=cond.get('operator', '=='),
                value=cond.get('value')
            )
        
        # Parse nested steps for conditional
        if 'then_steps' in data:
            step.then_steps = [cls.from_dict(s) for s in data['then_steps']]
        if 'else_steps' in data:
            step.else_steps = [cls.from_dict(s) for s in data['else_steps']]
        
        # Parse parallel steps
        if 'parallel_steps' in data:
            step.parallel_steps = [cls.from_dict(s) for s in data['parallel_steps']]
        
        return step


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    
    # Workflow metadata
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    
    # Workflow configuration
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Agent configurations
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # Workflow dependencies
    
    # Workflow steps
    steps: List[WorkflowStep] = field(default_factory=list)
    
    # Workflow settings
    max_parallel_agents: int = 5
    default_timeout: int = 3600  # 1 hour default
    allow_partial_success: bool = False
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'WorkflowDefinition':
        """Parse workflow definition from YAML string"""
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'WorkflowDefinition':
        """Parse workflow definition from YAML file"""
        with open(file_path, 'r') as f:
            return cls.from_yaml(f.read())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        """Create WorkflowDefinition from dictionary"""
        workflow = cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author'),
            tags=data.get('tags', []),
            agents=data.get('agents', {}),
            dependencies=data.get('dependencies', {}),
            max_parallel_agents=data.get('max_parallel_agents', 5),
            default_timeout=data.get('default_timeout', 3600),
            allow_partial_success=data.get('allow_partial_success', False)
        )
        
        # Parse timestamps
        if 'created_at' in data:
            workflow.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            workflow.updated_at = datetime.fromisoformat(data['updated_at'])
        
        # Parse steps
        if 'steps' in data:
            workflow.steps = [WorkflowStep.from_dict(s) for s in data['steps']]
        elif 'sequence' in data:
            # Support BMAD-style sequence format
            workflow.steps = cls._parse_bmad_sequence(data['sequence'])
        
        return workflow
    
    @staticmethod
    def _parse_bmad_sequence(sequence: List[Dict[str, Any]]) -> List[WorkflowStep]:
        """Parse BMAD-style sequence into workflow steps"""
        steps = []
        for idx, item in enumerate(sequence):
            step = WorkflowStep(
                id=f"step_{idx+1}",
                type=StepType.AGENT_TASK,
                name=item.get('name', f"Step {idx+1}"),
                agent=item.get('agent'),
                task=item.get('task', item.get('action')),
                creates=item.get('creates'),
                requires=item.get('requires', []),
                optional=item.get('optional', False)
            )
            
            # Handle optional steps
            if 'optional_steps' in item:
                step.optional = True
                step.outputs = item['optional_steps']
            
            # Handle validation steps
            if 'validates' in item:
                step.type = StepType.QUALITY_GATE
                step.checklist = item.get('uses')
                step.requires = [item['validates']]
            
            steps.append(step)
        
        return steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow definition to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': self.tags,
            'agents': self.agents,
            'dependencies': self.dependencies,
            'steps': [self._step_to_dict(s) for s in self.steps],
            'max_parallel_agents': self.max_parallel_agents,
            'default_timeout': self.default_timeout,
            'allow_partial_success': self.allow_partial_success
        }
    
    def _step_to_dict(self, step: WorkflowStep) -> Dict[str, Any]:
        """Convert workflow step to dictionary"""
        result = {
            'id': step.id,
            'type': step.type.value,
            'name': step.name
        }
        
        # Add optional fields
        if step.description:
            result['description'] = step.description
        if step.agent:
            result['agent'] = step.agent
        if step.task:
            result['task'] = step.task
        if step.inputs:
            result['inputs'] = step.inputs
        if step.outputs:
            result['outputs'] = step.outputs
        if step.creates:
            result['creates'] = step.creates
        if step.requires:
            result['requires'] = step.requires
        if step.template:
            result['template'] = step.template
        if step.checklist:
            result['checklist'] = step.checklist
        if step.gate_type:
            result['gate_type'] = step.gate_type
        if step.timeout:
            result['timeout'] = step.timeout
        if step.retry_count:
            result['retry_count'] = step.retry_count
        if step.retry_delay:
            result['retry_delay'] = step.retry_delay
        if step.optional:
            result['optional'] = step.optional
        
        # Add condition
        if step.condition:
            result['condition'] = {
                'field': step.condition.field,
                'operator': step.condition.operator,
                'value': step.condition.value
            }
        
        # Add nested steps
        if step.then_steps:
            result['then_steps'] = [self._step_to_dict(s) for s in step.then_steps]
        if step.else_steps:
            result['else_steps'] = [self._step_to_dict(s) for s in step.else_steps]
        if step.parallel_steps:
            result['parallel_steps'] = [self._step_to_dict(s) for s in step.parallel_steps]
        
        return result
    
    def to_yaml(self) -> str:
        """Convert workflow definition to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
    
    def validate(self) -> List[str]:
        """
        Validate workflow definition
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.id:
            errors.append("Workflow ID is required")
        if not self.name:
            errors.append("Workflow name is required")
        if not self.steps:
            errors.append("Workflow must have at least one step")
        
        # Validate steps
        step_ids = set()
        for step in self.steps:
            # Check for duplicate IDs
            if step.id in step_ids:
                errors.append(f"Duplicate step ID: {step.id}")
            step_ids.add(step.id)
            
            # Validate step based on type
            if step.type == StepType.AGENT_TASK:
                if not step.agent:
                    errors.append(f"Step {step.id}: agent is required for agent_task")
                if not step.task:
                    errors.append(f"Step {step.id}: task is required for agent_task")
            elif step.type == StepType.CONDITIONAL:
                if not step.condition:
                    errors.append(f"Step {step.id}: condition is required for conditional step")
            elif step.type == StepType.PARALLEL:
                if not step.parallel_steps:
                    errors.append(f"Step {step.id}: parallel_steps are required for parallel step")
            elif step.type == StepType.QUALITY_GATE:
                if not step.checklist:
                    errors.append(f"Step {step.id}: checklist is required for quality_gate")
        
        # Validate agent references
        for step in self.steps:
            if step.agent and step.agent not in self.agents:
                # Allow agents not in config (they might be system agents)
                pass
        
        # Validate document dependencies
        created_docs = set()
        for step in self.steps:
            if step.creates:
                created_docs.add(step.creates)
            for req_doc in step.requires:
                # Check if required document will be created before this step
                # This is a simplified check - full dependency resolution would be more complex
                pass
        
        return errors


class WorkflowParser:
    """Main workflow parser class"""
    
    @staticmethod
    def parse(yaml_content: str) -> WorkflowDefinition:
        """
        Parse YAML workflow definition
        
        Args:
            yaml_content: YAML string containing workflow definition
            
        Returns:
            WorkflowDefinition object
            
        Raises:
            ValueError: If workflow validation fails
        """
        workflow = WorkflowDefinition.from_yaml(yaml_content)
        
        # Validate workflow
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed:\n" + "\n".join(errors))
        
        return workflow
    
    @staticmethod
    def parse_file(file_path: str) -> WorkflowDefinition:
        """
        Parse YAML workflow definition from file
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            WorkflowDefinition object
            
        Raises:
            ValueError: If workflow validation fails
            FileNotFoundError: If file doesn't exist
        """
        workflow = WorkflowDefinition.from_yaml_file(file_path)
        
        # Validate workflow
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed:\n" + "\n".join(errors))
        
        return workflow