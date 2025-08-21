"""
BMAD Agent Enhancement Module

This module extends Agent-Zero's profile system with BMAD-style agent definitions,
including personas, commands, dependencies, and activation instructions.
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import importlib.util
from enum import Enum

# Import Agent-Zero components
from python.helpers import files
import python.helpers.log as Log

# Try to import PrintStyle, but make it optional for testing
try:
    from python.helpers.print_style import PrintStyle
except ImportError:
    # Create a mock PrintStyle for testing without dependencies
    class PrintStyle:
        def __init__(self, **kwargs):
            pass
        def print(self, text):
            print(text)


class DependencyType(Enum):
    """Types of dependencies that BMAD agents can have"""
    TASK = "tasks"
    TEMPLATE = "templates"
    CHECKLIST = "checklists"
    DATA = "data"
    WORKFLOW = "workflows"


@dataclass
class Persona:
    """BMAD Agent Persona definition"""
    role: str
    style: str
    identity: str
    focus: List[str]
    core_principles: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Persona':
        """Create Persona from dictionary"""
        return cls(
            role=data.get('role', ''),
            style=data.get('style', ''),
            identity=data.get('identity', ''),
            focus=data.get('focus', []),
            core_principles=data.get('core_principles', [])
        )


@dataclass
class AgentCommand:
    """Represents a BMAD agent command"""
    name: str
    description: str
    handler: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    async def execute(self, agent: Any, **kwargs) -> Any:
        """Execute the command"""
        if self.handler:
            return await self.handler(agent, **kwargs)
        else:
            raise NotImplementedError(f"Command {self.name} has no handler")


@dataclass
class ActivationPhase:
    """Represents a phase in the activation instruction sequence"""
    name: str
    description: str
    actions: List[str]
    validation: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivationPhase':
        """Create ActivationPhase from dictionary"""
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            actions=data.get('actions', []),
            validation=data.get('validation')
        )


@dataclass
class BMADAgentDefinition:
    """Complete BMAD agent definition"""
    # Basic agent info
    name: str
    id: str
    title: str
    icon: str
    when_to_use: str
    
    # Core components
    persona: Persona
    commands: List[AgentCommand]
    activation_phases: List[ActivationPhase]
    
    # Dependencies
    dependencies: Dict[DependencyType, List[str]] = field(default_factory=dict)
    
    # Loaded resources
    loaded_tasks: Dict[str, Any] = field(default_factory=dict)
    loaded_templates: Dict[str, Any] = field(default_factory=dict)
    loaded_checklists: Dict[str, Any] = field(default_factory=dict)
    loaded_data: Dict[str, Any] = field(default_factory=dict)
    loaded_workflows: Dict[str, Any] = field(default_factory=dict)


class BMADAgentLoader:
    """Loads and manages BMAD agent definitions"""
    
    def __init__(self, base_path: str = "agents"):
        self.base_path = Path(base_path)
        self.agents: Dict[str, BMADAgentDefinition] = {}
        self.command_registry: Dict[str, AgentCommand] = {}
        
    def load_agent(self, agent_name: str) -> Optional[BMADAgentDefinition]:
        """Load a BMAD agent definition from disk"""
        agent_path = self.base_path / agent_name
        
        if not agent_path.exists():
            PrintStyle(font_color="red").print(f"Agent path not found: {agent_path}")
            return None
            
        # Check for BMAD agent definition file
        agent_file = agent_path / "agent.md"
        if not agent_file.exists():
            # Fall back to classic Agent-Zero profile
            return None
            
        try:
            # Parse the BMAD agent definition
            agent_def = self._parse_agent_definition(agent_file)
            
            # Load commands
            agent_def.commands = self._load_commands(agent_path / "commands")
            
            # Store in cache
            self.agents[agent_name] = agent_def
            
            return agent_def
            
        except Exception as e:
            PrintStyle(font_color="red").print(f"Error loading BMAD agent {agent_name}: {e}")
            return None
    
    def _parse_agent_definition(self, agent_file: Path) -> BMADAgentDefinition:
        """Parse BMAD agent definition from markdown file"""
        content = agent_file.read_text()
        
        # Extract YAML frontmatter
        yaml_content = self._extract_yaml_frontmatter(content)
        agent_data = yaml.safe_load(yaml_content) if yaml_content else {}
        
        # Parse persona
        persona = Persona.from_dict(agent_data.get('persona', {}))
        
        # Parse activation phases
        activation_phases = [
            ActivationPhase.from_dict(phase)
            for phase in agent_data.get('activation-instructions', [])
        ]
        
        # Create agent definition
        agent_info = agent_data.get('agent', {})
        agent_def = BMADAgentDefinition(
            name=agent_info.get('name', ''),
            id=agent_info.get('id', ''),
            title=agent_info.get('title', ''),
            icon=agent_info.get('icon', ''),
            when_to_use=agent_info.get('whenToUse', ''),
            persona=persona,
            commands=[],  # Will be loaded separately
            activation_phases=activation_phases,
            dependencies=self._parse_dependencies(agent_data.get('dependencies', {}))
        )
        
        return agent_def
    
    def _extract_yaml_frontmatter(self, content: str) -> Optional[str]:
        """Extract YAML frontmatter from markdown content"""
        lines = content.split('\n')
        
        if not lines or lines[0].strip() != '---':
            return None
            
        yaml_lines = []
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                break
            yaml_lines.append(lines[i])
            
        return '\n'.join(yaml_lines)
    
    def _parse_dependencies(self, deps_data: Dict[str, Any]) -> Dict[DependencyType, List[str]]:
        """Parse dependencies from agent definition"""
        dependencies = {}
        
        for dep_type in DependencyType:
            if dep_type.value in deps_data:
                dependencies[dep_type] = deps_data[dep_type.value]
                
        return dependencies
    
    def _load_commands(self, commands_path: Path) -> List[AgentCommand]:
        """Load command implementations from the commands directory"""
        commands = []
        
        if not commands_path.exists():
            return commands
            
        for cmd_file in commands_path.glob("*.py"):
            try:
                # Load the command module
                spec = importlib.util.spec_from_file_location(
                    f"command_{cmd_file.stem}",
                    cmd_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for command definition
                    if hasattr(module, 'COMMAND'):
                        cmd_def = module.COMMAND
                        command = AgentCommand(
                            name=cmd_def.get('name', cmd_file.stem),
                            description=cmd_def.get('description', ''),
                            handler=getattr(module, 'execute', None),
                            parameters=cmd_def.get('parameters', {}),
                            dependencies=cmd_def.get('dependencies', [])
                        )
                        commands.append(command)
                        self.command_registry[command.name] = command
                        
            except Exception as e:
                PrintStyle(font_color="yellow").print(
                    f"Warning: Could not load command from {cmd_file}: {e}"
                )
                
        return commands
    
    async def load_dependencies(self, agent_def: BMADAgentDefinition, dep_type: DependencyType) -> Dict[str, Any]:
        """Lazy load dependencies for an agent"""
        loaded = {}
        
        if dep_type not in agent_def.dependencies:
            return loaded
            
        agent_path = self.base_path / agent_def.name
        dep_path = agent_path / "dependencies" / dep_type.value
        
        for dep_name in agent_def.dependencies[dep_type]:
            dep_file = dep_path / f"{dep_name}.yaml"
            if dep_file.exists():
                try:
                    with open(dep_file, 'r') as f:
                        loaded[dep_name] = yaml.safe_load(f)
                except Exception as e:
                    PrintStyle(font_color="yellow").print(
                        f"Warning: Could not load {dep_type.value} dependency {dep_name}: {e}"
                    )
                    
        # Cache loaded dependencies
        if dep_type == DependencyType.TASK:
            agent_def.loaded_tasks.update(loaded)
        elif dep_type == DependencyType.TEMPLATE:
            agent_def.loaded_templates.update(loaded)
        elif dep_type == DependencyType.CHECKLIST:
            agent_def.loaded_checklists.update(loaded)
        elif dep_type == DependencyType.DATA:
            agent_def.loaded_data.update(loaded)
        elif dep_type == DependencyType.WORKFLOW:
            agent_def.loaded_workflows.update(loaded)
            
        return loaded


class BMADAgentEnhancer:
    """Enhances Agent-Zero agents with BMAD capabilities"""
    
    def __init__(self, loader: Optional[BMADAgentLoader] = None):
        self.loader = loader or BMADAgentLoader()
        
    def enhance_agent(self, agent: Any) -> bool:
        """
        Enhance an Agent-Zero agent with BMAD capabilities
        
        Returns True if BMAD enhancement was applied, False otherwise
        """
        # Check if agent has a profile
        if not hasattr(agent, 'config') or not hasattr(agent.config, 'profile'):
            return False
            
        profile_name = agent.config.profile
        if not profile_name:
            return False
            
        # Try to load BMAD definition
        bmad_def = self.loader.load_agent(profile_name)
        if not bmad_def:
            return False
            
        # Enhance the agent with BMAD capabilities
        agent.bmad_definition = bmad_def
        agent.bmad_activated = False
        agent.bmad_activation_phase = 0
        
        # Add BMAD methods to the agent
        agent.execute_bmad_command = lambda cmd, **kwargs: self._execute_command(agent, cmd, **kwargs)
        agent.activate_bmad = lambda: self._activate_agent(agent)
        agent.load_bmad_dependency = lambda dep_type: self.loader.load_dependencies(bmad_def, dep_type)
        
        # Add persona to agent context
        if bmad_def.persona:
            agent.persona = bmad_def.persona
            
        PrintStyle(font_color="green").print(
            f"Enhanced agent {agent.agent_name} with BMAD profile: {profile_name}"
        )
        
        return True
    
    async def _execute_command(self, agent: Any, command_name: str, **kwargs) -> Any:
        """Execute a BMAD command for an agent"""
        if not hasattr(agent, 'bmad_definition'):
            raise ValueError("Agent is not BMAD-enhanced")
            
        command = self.loader.command_registry.get(command_name)
        if not command:
            raise ValueError(f"Command {command_name} not found")
            
        # Load required dependencies
        for dep in command.dependencies:
            dep_type = self._get_dependency_type(dep)
            if dep_type:
                await self.loader.load_dependencies(agent.bmad_definition, dep_type)
                
        # Execute the command
        return await command.execute(agent, **kwargs)
    
    async def _activate_agent(self, agent: Any) -> bool:
        """
        Run activation instructions for a BMAD agent
        
        Returns True if activation successful, False otherwise
        """
        if not hasattr(agent, 'bmad_definition'):
            return False
            
        if agent.bmad_activated:
            return True
            
        bmad_def = agent.bmad_definition
        
        try:
            # Execute each activation phase
            for i, phase in enumerate(bmad_def.activation_phases):
                agent.bmad_activation_phase = i
                
                PrintStyle(font_color="cyan").print(
                    f"Executing activation phase: {phase.name}"
                )
                
                # Execute phase actions
                for action in phase.actions:
                    # Actions could be commands or other operations
                    if action.startswith("load_"):
                        # Load dependency
                        dep_type_str = action.replace("load_", "")
                        dep_type = self._get_dependency_type(dep_type_str)
                        if dep_type:
                            await self.loader.load_dependencies(bmad_def, dep_type)
                    elif action in self.loader.command_registry:
                        # Execute command
                        await self._execute_command(agent, action)
                        
                # Run validation if specified
                if phase.validation:
                    # TODO: Implement validation logic
                    pass
                    
            agent.bmad_activated = True
            PrintStyle(font_color="green").print(
                f"BMAD activation complete for agent {agent.agent_name}"
            )
            return True
            
        except Exception as e:
            PrintStyle(font_color="red").print(
                f"BMAD activation failed for agent {agent.agent_name}: {e}"
            )
            return False
    
    def _get_dependency_type(self, type_str: str) -> Optional[DependencyType]:
        """Convert string to DependencyType enum"""
        for dep_type in DependencyType:
            if dep_type.value == type_str or dep_type.name.lower() == type_str.lower():
                return dep_type
        return None


class CommandMapper:
    """Maps BMAD commands to Agent-Zero tools"""
    
    def __init__(self):
        self.mappings: Dict[str, str] = {}
        
    def register_mapping(self, command_name: str, tool_name: str):
        """Register a command-to-tool mapping"""
        self.mappings[command_name] = tool_name
        
    def get_tool_for_command(self, command_name: str) -> Optional[str]:
        """Get the tool name for a command"""
        return self.mappings.get(command_name)
        
    def create_tool_wrapper(self, command: AgentCommand, tool_name: str) -> Callable:
        """Create a wrapper function that calls an Agent-Zero tool"""
        async def wrapper(agent: Any, **kwargs):
            # Find the tool in agent's available tools
            tool = None
            for t in agent.tools:
                if t.__class__.__name__ == tool_name:
                    tool = t
                    break
                    
            if not tool:
                raise ValueError(f"Tool {tool_name} not found for command {command.name}")
                
            # Execute the tool
            return await tool.execute(**kwargs)
            
        return wrapper


# Global instances
_loader = BMADAgentLoader()
_enhancer = BMADAgentEnhancer(_loader)
_command_mapper = CommandMapper()


def enhance_agent_with_bmad(agent: Any) -> bool:
    """
    Public function to enhance an Agent-Zero agent with BMAD capabilities
    
    Args:
        agent: An Agent-Zero agent instance
        
    Returns:
        True if enhancement was successful, False otherwise
    """
    return _enhancer.enhance_agent(agent)


def register_command_mapping(command_name: str, tool_name: str):
    """
    Register a mapping between a BMAD command and an Agent-Zero tool
    
    Args:
        command_name: Name of the BMAD command
        tool_name: Name of the Agent-Zero tool class
    """
    _command_mapper.register_mapping(command_name, tool_name)