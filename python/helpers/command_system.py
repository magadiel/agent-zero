"""
BMAD Command System for Agent-Zero

This module implements the command system that allows BMAD-style agents to execute
predefined commands that map to Agent-Zero tools and actions.
"""

import re
import yaml
import json
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from pathlib import Path
from enum import Enum
import inspect
from datetime import datetime

# Import Agent-Zero components
try:
    from python.helpers.print_style import PrintStyle
    from python.helpers import files
    import python.helpers.log as Log
except ImportError:
    # Create mock classes for testing
    class PrintStyle:
        def __init__(self, **kwargs):
            pass
        def print(self, text):
            print(text)
    
    class Log:
        @staticmethod
        def log(level, module, message):
            print(f"[{level}] {module}: {message}")


class CommandStatus(Enum):
    """Status of command execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParameterType(Enum):
    """Types of command parameters"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    FILE = "file"
    ENUM = "enum"


@dataclass
class CommandParameter:
    """Definition of a command parameter"""
    name: str
    type: ParameterType
    required: bool = False
    default: Any = None
    description: str = ""
    validation: Optional[Callable] = None
    choices: List[Any] = field(default_factory=list)
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate parameter value"""
        # Check if required
        if self.required and value is None:
            return False, f"Parameter '{self.name}' is required"
        
        # Skip validation if not provided and not required
        if value is None:
            return True, None
        
        # Type validation
        if self.type == ParameterType.STRING:
            if not isinstance(value, str):
                return False, f"Parameter '{self.name}' must be a string"
        elif self.type == ParameterType.INTEGER:
            if not isinstance(value, int):
                return False, f"Parameter '{self.name}' must be an integer"
        elif self.type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return False, f"Parameter '{self.name}' must be a number"
        elif self.type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Parameter '{self.name}' must be a boolean"
        elif self.type == ParameterType.LIST:
            if not isinstance(value, list):
                return False, f"Parameter '{self.name}' must be a list"
        elif self.type == ParameterType.DICT:
            if not isinstance(value, dict):
                return False, f"Parameter '{self.name}' must be a dictionary"
        elif self.type == ParameterType.FILE:
            if not isinstance(value, str):
                return False, f"Parameter '{self.name}' must be a file path"
            # Check if file exists
            if not Path(value).exists():
                return False, f"File '{value}' does not exist"
        elif self.type == ParameterType.ENUM:
            if self.choices and value not in self.choices:
                return False, f"Parameter '{self.name}' must be one of: {self.choices}"
        
        # Custom validation
        if self.validation:
            try:
                if not self.validation(value):
                    return False, f"Parameter '{self.name}' failed custom validation"
            except Exception as e:
                return False, f"Parameter '{self.name}' validation error: {str(e)}"
        
        return True, None


@dataclass
class CommandExecution:
    """Represents a command execution instance"""
    command_name: str
    parameters: Dict[str, Any]
    status: CommandStatus = CommandStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def log(self, message: str):
        """Add log message"""
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "command": self.command_name,
            "parameters": self.parameters,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "logs": self.logs
        }


@dataclass
class AgentCommand:
    """Definition of an agent command"""
    name: str
    description: str
    parameters: List[CommandParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    tool_mapping: Optional[str] = None  # Maps to Agent-Zero tool name
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300  # seconds
    retries: int = 0
    
    async def execute(self, agent: Any, **kwargs) -> CommandExecution:
        """Execute the command"""
        execution = CommandExecution(
            command_name=self.name,
            parameters=kwargs
        )
        
        try:
            # Start execution
            execution.status = CommandStatus.RUNNING
            execution.started_at = datetime.now()
            execution.log(f"Starting command execution: {self.name}")
            
            # Validate parameters
            for param in self.parameters:
                value = kwargs.get(param.name, param.default)
                valid, error = param.validate(value)
                if not valid:
                    raise ValueError(error)
            
            # Execute with retry logic
            attempts = 0
            while attempts <= self.retries:
                try:
                    if self.handler:
                        # Use custom handler
                        if asyncio.iscoroutinefunction(self.handler):
                            result = await self.handler(agent, execution, **kwargs)
                        else:
                            result = self.handler(agent, execution, **kwargs)
                    elif self.tool_mapping:
                        # Map to Agent-Zero tool
                        result = await self._execute_tool(agent, execution, **kwargs)
                    elif self.execution_steps:
                        # Execute predefined steps
                        result = await self._execute_steps(agent, execution, **kwargs)
                    else:
                        raise NotImplementedError(f"Command {self.name} has no implementation")
                    
                    # Success
                    execution.result = result
                    execution.status = CommandStatus.SUCCESS
                    execution.log(f"Command completed successfully")
                    break
                    
                except Exception as e:
                    attempts += 1
                    if attempts > self.retries:
                        raise
                    execution.log(f"Attempt {attempts} failed: {str(e)}")
                    await asyncio.sleep(2 ** attempts)  # Exponential backoff
            
        except Exception as e:
            execution.status = CommandStatus.FAILED
            execution.error = str(e)
            execution.log(f"Command failed: {str(e)}")
            Log.log("error", "command_system", f"Command {self.name} failed: {str(e)}")
        
        finally:
            execution.completed_at = datetime.now()
            
        return execution
    
    async def _execute_tool(self, agent: Any, execution: CommandExecution, **kwargs) -> Any:
        """Execute command by mapping to Agent-Zero tool"""
        execution.log(f"Mapping to tool: {self.tool_mapping}")
        
        # Get the tool from agent
        tool = agent.get_tool(self.tool_mapping)
        if not tool:
            raise ValueError(f"Tool '{self.tool_mapping}' not found")
        
        # Prepare tool parameters
        tool_params = {}
        for param in self.parameters:
            if param.name in kwargs:
                tool_params[param.name] = kwargs[param.name]
        
        # Execute tool
        result = await tool.execute(**tool_params)
        execution.log(f"Tool execution completed")
        
        return result
    
    async def _execute_steps(self, agent: Any, execution: CommandExecution, **kwargs) -> Any:
        """Execute predefined steps"""
        results = []
        
        for i, step in enumerate(self.execution_steps, 1):
            execution.log(f"Executing step {i}: {step.get('name', 'Unnamed')}")
            
            step_type = step.get('type')
            if step_type == 'tool':
                # Execute a tool
                tool_name = step.get('tool')
                tool_params = step.get('parameters', {})
                
                # Substitute parameters
                for key, value in tool_params.items():
                    if isinstance(value, str) and value.startswith('$'):
                        param_name = value[1:]
                        if param_name in kwargs:
                            tool_params[key] = kwargs[param_name]
                
                tool = agent.get_tool(tool_name)
                if tool:
                    result = await tool.execute(**tool_params)
                    results.append(result)
                    
            elif step_type == 'command':
                # Execute another command
                cmd_name = step.get('command')
                cmd_params = step.get('parameters', {})
                
                command = agent.get_command(cmd_name)
                if command:
                    sub_execution = await command.execute(agent, **cmd_params)
                    results.append(sub_execution.result)
                    
            elif step_type == 'condition':
                # Conditional execution
                condition = step.get('condition')
                if_steps = step.get('if', [])
                else_steps = step.get('else', [])
                
                # Evaluate condition (simplified)
                if self._evaluate_condition(condition, kwargs, results):
                    for if_step in if_steps:
                        self.execution_steps.append(if_step)
                else:
                    for else_step in else_steps:
                        self.execution_steps.append(else_step)
                        
            elif step_type == 'loop':
                # Loop execution
                items = step.get('items', [])
                loop_steps = step.get('steps', [])
                
                for item in items:
                    for loop_step in loop_steps:
                        # Add loop variable
                        loop_step_copy = loop_step.copy()
                        loop_step_copy['loop_item'] = item
                        self.execution_steps.append(loop_step_copy)
        
        return results
    
    def _evaluate_condition(self, condition: str, params: Dict, results: List) -> bool:
        """Evaluate a simple condition"""
        # This is a simplified condition evaluator
        # In production, you'd want a more robust expression evaluator
        try:
            # Replace parameter references
            for key, value in params.items():
                condition = condition.replace(f"${key}", str(value))
            
            # Evaluate
            return eval(condition)
        except:
            return False


class CommandRegistry:
    """Registry for managing available commands"""
    
    def __init__(self):
        self.commands: Dict[str, AgentCommand] = {}
        self.executions: List[CommandExecution] = []
        
    def register(self, command: AgentCommand):
        """Register a command"""
        self.commands[command.name] = command
        Log.log("info", "command_system", f"Registered command: {command.name}")
    
    def unregister(self, command_name: str):
        """Unregister a command"""
        if command_name in self.commands:
            del self.commands[command_name]
            Log.log("info", "command_system", f"Unregistered command: {command_name}")
    
    def get(self, command_name: str) -> Optional[AgentCommand]:
        """Get a command by name"""
        return self.commands.get(command_name)
    
    def list_commands(self) -> List[str]:
        """List all registered commands"""
        return list(self.commands.keys())
    
    def get_command_info(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get command information"""
        command = self.get(command_name)
        if not command:
            return None
        
        return {
            "name": command.name,
            "description": command.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                    "choices": p.choices
                }
                for p in command.parameters
            ],
            "dependencies": command.dependencies,
            "timeout": command.timeout,
            "retries": command.retries
        }
    
    async def execute(self, agent: Any, command_name: str, **kwargs) -> CommandExecution:
        """Execute a command"""
        command = self.get(command_name)
        if not command:
            raise ValueError(f"Command '{command_name}' not found")
        
        execution = await command.execute(agent, **kwargs)
        self.executions.append(execution)
        
        return execution
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get execution history"""
        return [e.to_dict() for e in self.executions[-limit:]]


class CommandParser:
    """Parse commands from BMAD agent definitions"""
    
    @staticmethod
    def parse_from_markdown(content: str) -> List[AgentCommand]:
        """Parse commands from markdown content"""
        commands = []
        
        # Find Commands section
        commands_section = re.search(r'## Commands\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if not commands_section:
            return commands
        
        # Split by ### to find individual commands
        cmd_text = commands_section.group(1)
        # Handle first command that may not have \n before ###
        if cmd_text.startswith('###'):
            cmd_text = '\n' + cmd_text
        
        sections = re.split(r'\n###\s+', cmd_text)
        
        for section in sections:
            if not section.strip():
                continue
                
            # Parse command name and content
            lines = section.split('\n', 1)
            if not lines[0].strip():
                continue
                
            command_name = lines[0].strip()
            # Remove ### if it was captured
            if command_name.startswith('###'):
                command_name = command_name[3:].strip()
            
            command_content = lines[1] if len(lines) > 1 else ""
            
            # Parse command details
            command = CommandParser._parse_command_details(command_name, command_content)
            if command:
                commands.append(command)
        
        return commands
    
    @staticmethod
    def _parse_command_details(name: str, content: str) -> Optional[AgentCommand]:
        """Parse individual command details"""
        try:
            # Extract description
            desc_match = re.search(r'\*\*Description\*\*:\s*(.+)', content)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract parameters
            parameters = []
            params_section = re.search(r'\*\*Parameters\*\*:(.*?)(?=\*\*|$)', content, re.DOTALL)
            if params_section:
                param_pattern = r'- `(\w+)`\s*(?:\((\w+)\))?\s*:\s*(.+)'
                for param_match in re.finditer(param_pattern, params_section.group(1)):
                    param_name = param_match.group(1)
                    param_req = param_match.group(2) == "required"
                    param_desc = param_match.group(3)
                    
                    # Determine parameter type from description
                    param_type = ParameterType.STRING  # Default
                    if "number" in param_desc.lower() or "integer" in param_desc.lower():
                        param_type = ParameterType.INTEGER
                    elif "boolean" in param_desc.lower() or "true/false" in param_desc.lower():
                        param_type = ParameterType.BOOLEAN
                    elif "list" in param_desc.lower() or "array" in param_desc.lower():
                        param_type = ParameterType.LIST
                    elif "file" in param_desc.lower() or "path" in param_desc.lower():
                        param_type = ParameterType.FILE
                    
                    parameters.append(CommandParameter(
                        name=param_name,
                        type=param_type,
                        required=param_req,
                        description=param_desc
                    ))
            
            # Extract execution steps
            execution_steps = []
            exec_section = re.search(r'\*\*Execution\*\*:(.*?)(?=\*\*|$)', content, re.DOTALL)
            if exec_section:
                step_pattern = r'\d+\.\s*(.+)'
                for step_match in re.finditer(step_pattern, exec_section.group(1)):
                    step_text = step_match.group(1).strip()
                    execution_steps.append({
                        "type": "action",
                        "description": step_text
                    })
            
            # Extract dependencies
            dependencies = []
            deps_match = re.search(r'\*\*Dependencies\*\*:\s*(.+)', content)
            if deps_match:
                deps_text = deps_match.group(1)
                dependencies = [d.strip() for d in deps_text.split(',')]
            
            return AgentCommand(
                name=name,
                description=description,
                parameters=parameters,
                execution_steps=execution_steps,
                dependencies=dependencies
            )
            
        except Exception as e:
            Log.log("error", "command_parser", f"Failed to parse command {name}: {str(e)}")
            return None


class CommandSystem:
    """Main command system interface"""
    
    def __init__(self):
        self.registry = CommandRegistry()
        self.parser = CommandParser()
        self._load_builtin_commands()
    
    def _load_builtin_commands(self):
        """Load built-in commands"""
        # Add some common commands that map to Agent-Zero tools
        
        # Memory commands
        self.registry.register(AgentCommand(
            name="save-memory",
            description="Save information to agent memory",
            parameters=[
                CommandParameter(
                    name="content",
                    type=ParameterType.STRING,
                    required=True,
                    description="Content to save"
                ),
                CommandParameter(
                    name="category",
                    type=ParameterType.STRING,
                    default="general",
                    description="Memory category"
                )
            ],
            tool_mapping="memory_save"
        ))
        
        self.registry.register(AgentCommand(
            name="recall-memory",
            description="Recall information from agent memory",
            parameters=[
                CommandParameter(
                    name="query",
                    type=ParameterType.STRING,
                    required=True,
                    description="Query to search memory"
                )
            ],
            tool_mapping="memory_query"
        ))
        
        # Code execution commands
        self.registry.register(AgentCommand(
            name="execute-code",
            description="Execute code in the environment",
            parameters=[
                CommandParameter(
                    name="code",
                    type=ParameterType.STRING,
                    required=True,
                    description="Code to execute"
                ),
                CommandParameter(
                    name="language",
                    type=ParameterType.ENUM,
                    choices=["python", "javascript", "bash"],
                    default="python",
                    description="Programming language"
                )
            ],
            tool_mapping="code_execution"
        ))
        
        # File operations
        self.registry.register(AgentCommand(
            name="read-file",
            description="Read a file from the filesystem",
            parameters=[
                CommandParameter(
                    name="path",
                    type=ParameterType.FILE,
                    required=True,
                    description="Path to the file"
                )
            ],
            tool_mapping="read_file"
        ))
        
        self.registry.register(AgentCommand(
            name="write-file",
            description="Write content to a file",
            parameters=[
                CommandParameter(
                    name="path",
                    type=ParameterType.STRING,
                    required=True,
                    description="Path to the file"
                ),
                CommandParameter(
                    name="content",
                    type=ParameterType.STRING,
                    required=True,
                    description="Content to write"
                )
            ],
            tool_mapping="write_file"
        ))
    
    def load_agent_commands(self, agent_path: Path) -> List[AgentCommand]:
        """Load commands from agent definition"""
        agent_file = agent_path / "agent.md"
        if not agent_file.exists():
            return []
        
        try:
            with open(agent_file, 'r') as f:
                content = f.read()
            
            commands = self.parser.parse_from_markdown(content)
            
            # Register commands
            for command in commands:
                self.registry.register(command)
            
            return commands
            
        except Exception as e:
            Log.log("error", "command_system", f"Failed to load commands from {agent_path}: {str(e)}")
            return []
    
    def create_command(self, name: str, description: str, handler: Callable) -> AgentCommand:
        """Create a custom command"""
        # Inspect handler to determine parameters
        sig = inspect.signature(handler)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'agent', 'execution']:
                continue
            
            param_type = ParameterType.STRING  # Default
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default
            
            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = ParameterType.INTEGER
                elif param.annotation == float:
                    param_type = ParameterType.FLOAT
                elif param.annotation == bool:
                    param_type = ParameterType.BOOLEAN
                elif param.annotation == list:
                    param_type = ParameterType.LIST
                elif param.annotation == dict:
                    param_type = ParameterType.DICT
            
            parameters.append(CommandParameter(
                name=param_name,
                type=param_type,
                required=required,
                default=default,
                description=f"Parameter {param_name}"
            ))
        
        command = AgentCommand(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )
        
        self.registry.register(command)
        return command
    
    async def execute(self, agent: Any, command_name: str, **kwargs) -> CommandExecution:
        """Execute a command"""
        return await self.registry.execute(agent, command_name, **kwargs)
    
    def get_available_commands(self) -> List[str]:
        """Get list of available commands"""
        return self.registry.list_commands()
    
    def get_command_help(self, command_name: str) -> Optional[str]:
        """Get help text for a command"""
        info = self.registry.get_command_info(command_name)
        if not info:
            return None
        
        help_text = f"Command: {info['name']}\n"
        help_text += f"Description: {info['description']}\n"
        
        if info['parameters']:
            help_text += "\nParameters:\n"
            for param in info['parameters']:
                req = " (required)" if param['required'] else f" (default: {param['default']})"
                help_text += f"  - {param['name']} [{param['type']}]{req}: {param['description']}\n"
                if param['choices']:
                    help_text += f"    Choices: {', '.join(map(str, param['choices']))}\n"
        
        if info['dependencies']:
            help_text += f"\nDependencies: {', '.join(info['dependencies'])}\n"
        
        return help_text


# Global command system instance
command_system = CommandSystem()