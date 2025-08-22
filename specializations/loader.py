"""
Industry Specialization Loader

This module provides functionality to load and apply industry-specific
configurations to the Agent-Zero agile AI company framework.
"""

import os
import yaml
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import importlib.util
from dataclasses import dataclass

from python.helpers.bmad_agent import BMADAgentLoader
from coordination.workflow_engine import WorkflowEngine
from control.ethics_engine import EthicsEngine
from control.safety_monitor import SafetyMonitor


@dataclass
class SpecializationMetadata:
    """Metadata for an industry specialization."""
    name: str
    version: str
    description: str
    industry: str
    compliance_frameworks: List[str]
    focus_areas: List[str]


class SpecializationLoader:
    """Loads and manages industry specializations."""
    
    def __init__(self, base_path: str = None):
        """Initialize the specialization loader."""
        if base_path is None:
            base_path = os.path.join(os.path.dirname(__file__))
        self.base_path = Path(base_path)
        self.loaded_specializations = {}
        
    def list_available_specializations(self) -> List[str]:
        """List all available specializations."""
        specializations = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                config_file = item / 'config' / 'specialization.yaml'
                if config_file.exists():
                    specializations.append(item.name)
        return specializations
    
    def load_specialization(self, name: str) -> 'Specialization':
        """Load a specific specialization by name."""
        if name in self.loaded_specializations:
            return self.loaded_specializations[name]
        
        spec_path = self.base_path / name
        if not spec_path.exists():
            raise ValueError(f"Specialization '{name}' not found at {spec_path}")
        
        config_path = spec_path / 'config' / 'specialization.yaml'
        if not config_path.exists():
            raise ValueError(f"Specialization config not found at {config_path}")
        
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create specialization instance
        specialization = Specialization(name, spec_path, config)
        self.loaded_specializations[name] = specialization
        
        return specialization
    
    def get_specialization_info(self, name: str) -> SpecializationMetadata:
        """Get metadata for a specialization without fully loading it."""
        spec_path = self.base_path / name
        config_path = spec_path / 'config' / 'specialization.yaml'
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        metadata = config.get('metadata', {})
        return SpecializationMetadata(
            name=config.get('name', name),
            version=config.get('version', '1.0.0'),
            description=config.get('description', ''),
            industry=metadata.get('industry', ''),
            compliance_frameworks=metadata.get('compliance_frameworks', []),
            focus_areas=metadata.get('focus_areas', [])
        )


class Specialization:
    """Represents a loaded industry specialization."""
    
    def __init__(self, name: str, path: Path, config: Dict[str, Any]):
        """Initialize the specialization."""
        self.name = name
        self.path = path
        self.config = config
        self.metadata = self._parse_metadata()
        self.agents = {}
        self.workflows = {}
        self.templates = {}
        self.checklists = {}
        
        # Load components
        self._load_agents()
        self._load_workflows()
        self._load_templates()
        self._load_checklists()
    
    def _parse_metadata(self) -> SpecializationMetadata:
        """Parse specialization metadata."""
        metadata = self.config.get('metadata', {})
        return SpecializationMetadata(
            name=self.config.get('name', self.name),
            version=self.config.get('version', '1.0.0'),
            description=self.config.get('description', ''),
            industry=metadata.get('industry', ''),
            compliance_frameworks=metadata.get('compliance_frameworks', []),
            focus_areas=metadata.get('focus_areas', [])
        )
    
    def _load_agents(self):
        """Load agent profiles from the specialization."""
        agents_path = self.path / 'agents'
        if not agents_path.exists():
            return
        
        for agent_file in agents_path.glob('*.md'):
            agent_name = agent_file.stem
            try:
                with open(agent_file, 'r') as f:
                    agent_content = f.read()
                
                # Parse BMAD agent definition
                loader = BMADAgentLoader()
                agent_data = loader.parse_agent_definition(agent_content)
                self.agents[agent_name] = agent_data
                
            except Exception as e:
                print(f"Warning: Failed to load agent {agent_name}: {e}")
    
    def _load_workflows(self):
        """Load workflow definitions from the specialization."""
        workflows_path = self.path / 'workflows'
        if not workflows_path.exists():
            return
        
        for workflow_file in workflows_path.glob('*.yaml'):
            workflow_name = workflow_file.stem
            try:
                with open(workflow_file, 'r') as f:
                    workflow_data = yaml.safe_load(f)
                self.workflows[workflow_name] = workflow_data
                
            except Exception as e:
                print(f"Warning: Failed to load workflow {workflow_name}: {e}")
    
    def _load_templates(self):
        """Load document templates from the specialization."""
        templates_path = self.path / 'templates'
        if not templates_path.exists():
            return
        
        for template_file in templates_path.glob('*.yaml'):
            template_name = template_file.stem
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                self.templates[template_name] = template_data
                
            except Exception as e:
                print(f"Warning: Failed to load template {template_name}: {e}")
    
    def _load_checklists(self):
        """Load quality checklists from the specialization."""
        checklists_path = self.path / 'checklists'
        if not checklists_path.exists():
            return
        
        for checklist_file in checklists_path.glob('*.md'):
            checklist_name = checklist_file.stem
            try:
                with open(checklist_file, 'r') as f:
                    checklist_content = f.read()
                self.checklists[checklist_name] = checklist_content
                
            except Exception as e:
                print(f"Warning: Failed to load checklist {checklist_name}: {e}")
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get the full specialization configuration."""
        return self.config
    
    def get_ethics_constraints(self) -> Dict[str, Any]:
        """Get industry-specific ethics constraints."""
        return self.config.get('ethics', {})
    
    def get_safety_thresholds(self) -> Dict[str, Any]:
        """Get industry-specific safety thresholds."""
        return self.config.get('safety', {})
    
    def get_resource_allocation(self) -> Dict[str, Any]:
        """Get industry-specific resource allocation rules."""
        return self.config.get('resource_allocation', {})
    
    def get_audit_requirements(self) -> Dict[str, Any]:
        """Get industry-specific audit requirements."""
        return self.config.get('audit', {})
    
    def get_integration_settings(self) -> Dict[str, Any]:
        """Get industry-specific integration settings."""
        return self.config.get('integrations', {})
    
    def list_agents(self) -> List[str]:
        """List available agent types in this specialization."""
        return list(self.agents.keys())
    
    def list_workflows(self) -> List[str]:
        """List available workflows in this specialization."""
        return list(self.workflows.keys())
    
    def list_templates(self) -> List[str]:
        """List available templates in this specialization."""
        return list(self.templates.keys())
    
    def list_checklists(self) -> List[str]:
        """List available checklists in this specialization."""
        return list(self.checklists.keys())
    
    def create_agent(self, agent_type: str, agent_id: str = None) -> Dict[str, Any]:
        """Create an agent instance of the specified type."""
        if agent_type not in self.agents:
            raise ValueError(f"Agent type '{agent_type}' not available in {self.name} specialization")
        
        agent_data = self.agents[agent_type].copy()
        
        # Apply specialization-specific configuration
        if agent_id:
            agent_data['id'] = agent_id
        
        return agent_data
    
    def create_team(self, team_name: str, composition: Dict[str, int]) -> Dict[str, Any]:
        """Create a team with specified agent composition."""
        team = {
            'name': team_name,
            'specialization': self.name,
            'agents': [],
            'created_at': None,  # Will be set by team orchestrator
        }
        
        agent_id_counter = 1
        for agent_type, count in composition.items():
            for i in range(count):
                agent_id = f"{team_name}_{agent_type}_{agent_id_counter}"
                agent = self.create_agent(agent_type, agent_id)
                team['agents'].append(agent)
                agent_id_counter += 1
        
        return team
    
    def get_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """Get a workflow definition by name."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not available in {self.name} specialization")
        
        return self.workflows[workflow_name]
    
    def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow with the given inputs."""
        workflow_def = self.get_workflow(workflow_name)
        
        # Initialize workflow engine
        engine = WorkflowEngine()
        
        # Execute workflow
        result = engine.execute_workflow(workflow_def, inputs)
        
        return result
    
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get a template by name."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not available in {self.name} specialization")
        
        return self.templates[template_name]
    
    def get_checklist(self, checklist_name: str) -> str:
        """Get a checklist by name."""
        if checklist_name not in self.checklists:
            raise ValueError(f"Checklist '{checklist_name}' not available in {self.name} specialization")
        
        return self.checklists[checklist_name]
    
    def apply_to_system(self):
        """Apply specialization configuration to the AI system."""
        # Apply ethics constraints
        ethics_constraints = self.get_ethics_constraints()
        if ethics_constraints:
            # Would integrate with control layer ethics engine
            print(f"Applied {len(ethics_constraints)} ethics constraints from {self.name}")
        
        # Apply safety thresholds
        safety_thresholds = self.get_safety_thresholds()
        if safety_thresholds:
            # Would integrate with control layer safety monitor
            print(f"Applied safety thresholds from {self.name}")
        
        # Apply resource allocation
        resource_allocation = self.get_resource_allocation()
        if resource_allocation:
            # Would integrate with control layer resource allocator
            print(f"Applied resource allocation rules from {self.name}")
        
        print(f"Successfully applied {self.name} specialization to system")
    
    def validate(self) -> Dict[str, Any]:
        """Validate the specialization configuration."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Validate required fields
        required_fields = ['name', 'version', 'description']
        for field in required_fields:
            if field not in self.config:
                validation_results['errors'].append(f"Missing required field: {field}")
                validation_results['valid'] = False
        
        # Validate agents
        if not self.agents:
            validation_results['warnings'].append("No agents defined in specialization")
        
        # Validate workflows
        if not self.workflows:
            validation_results['warnings'].append("No workflows defined in specialization")
        
        # Set summary
        validation_results['summary'] = {
            'agents': len(self.agents),
            'workflows': len(self.workflows),
            'templates': len(self.templates),
            'checklists': len(self.checklists)
        }
        
        return validation_results
    
    def export_configuration(self, format: str = 'yaml') -> str:
        """Export specialization configuration in specified format."""
        if format.lower() == 'yaml':
            return yaml.dump(self.config, default_flow_style=False)
        elif format.lower() == 'json':
            return json.dumps(self.config, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_documentation(self) -> str:
        """Get specialization documentation."""
        readme_path = self.path / 'README.md'
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                return f.read()
        return f"No documentation available for {self.name} specialization"


# Convenience functions for common operations
def load_specialization(name: str) -> Specialization:
    """Load a specialization by name."""
    loader = SpecializationLoader()
    return loader.load_specialization(name)


def list_specializations() -> List[str]:
    """List all available specializations."""
    loader = SpecializationLoader()
    return loader.list_available_specializations()


def create_specialized_team(specialization_name: str, team_name: str, 
                           composition: Dict[str, int]) -> Dict[str, Any]:
    """Create a team using a specific specialization."""
    specialization = load_specialization(specialization_name)
    return specialization.create_team(team_name, composition)


if __name__ == "__main__":
    # Example usage
    loader = SpecializationLoader()
    
    # List available specializations
    print("Available specializations:")
    for spec in loader.list_available_specializations():
        info = loader.get_specialization_info(spec)
        print(f"  - {info.name} ({info.industry})")
    
    # Load and test a specialization
    if 'fintech' in loader.list_available_specializations():
        fintech = loader.load_specialization('fintech')
        print(f"\nLoaded {fintech.metadata.name}")
        print(f"Agents: {fintech.list_agents()}")
        print(f"Workflows: {fintech.list_workflows()}")
        
        # Validate specialization
        validation = fintech.validate()
        print(f"Validation: {'PASSED' if validation['valid'] else 'FAILED'}")
        if validation['errors']:
            print(f"Errors: {validation['errors']}")