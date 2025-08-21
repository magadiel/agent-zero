"""
Test suite for the BMAD Command System
"""

import sys
import os
import asyncio
import unittest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.command_system import (
    CommandSystem, CommandRegistry, CommandParser, AgentCommand,
    CommandParameter, ParameterType, CommandExecution, CommandStatus
)


class TestCommandParameter(unittest.TestCase):
    """Test command parameter validation"""
    
    def test_required_parameter(self):
        """Test required parameter validation"""
        param = CommandParameter(
            name="test",
            type=ParameterType.STRING,
            required=True
        )
        
        # Should fail if not provided
        valid, error = param.validate(None)
        self.assertFalse(valid)
        self.assertIn("required", error)
        
        # Should pass if provided
        valid, error = param.validate("value")
        self.assertTrue(valid)
        self.assertIsNone(error)
    
    def test_type_validation(self):
        """Test parameter type validation"""
        # String parameter
        param = CommandParameter(name="test", type=ParameterType.STRING)
        valid, _ = param.validate("string")
        self.assertTrue(valid)
        valid, _ = param.validate(123)
        self.assertFalse(valid)
        
        # Integer parameter
        param = CommandParameter(name="test", type=ParameterType.INTEGER)
        valid, _ = param.validate(123)
        self.assertTrue(valid)
        valid, _ = param.validate("string")
        self.assertFalse(valid)
        
        # Boolean parameter
        param = CommandParameter(name="test", type=ParameterType.BOOLEAN)
        valid, _ = param.validate(True)
        self.assertTrue(valid)
        valid, _ = param.validate("true")
        self.assertFalse(valid)
    
    def test_enum_parameter(self):
        """Test enum parameter with choices"""
        param = CommandParameter(
            name="test",
            type=ParameterType.ENUM,
            choices=["option1", "option2", "option3"]
        )
        
        valid, _ = param.validate("option1")
        self.assertTrue(valid)
        
        valid, error = param.validate("invalid")
        self.assertFalse(valid)
        self.assertIn("must be one of", error)
    
    def test_file_parameter(self):
        """Test file parameter validation"""
        param = CommandParameter(name="test", type=ParameterType.FILE)
        
        # Should fail for non-existent file
        valid, error = param.validate("/nonexistent/file.txt")
        self.assertFalse(valid)
        self.assertIn("does not exist", error)
        
        # Should pass for existing file
        with patch('pathlib.Path.exists', return_value=True):
            valid, _ = param.validate("/existing/file.txt")
            self.assertTrue(valid)


class TestAgentCommand(unittest.TestCase):
    """Test agent command execution"""
    
    def setUp(self):
        self.agent = Mock()
        self.agent.get_tool = Mock(return_value=None)
        self.agent.get_command = Mock(return_value=None)
    
    async def test_command_with_handler(self):
        """Test command execution with custom handler"""
        async def test_handler(agent, execution, **kwargs):
            execution.log("Handler called")
            return {"result": kwargs.get("param1", "default")}
        
        command = AgentCommand(
            name="test",
            description="Test command",
            handler=test_handler,
            parameters=[
                CommandParameter(name="param1", type=ParameterType.STRING)
            ]
        )
        
        execution = await command.execute(self.agent, param1="value")
        
        self.assertEqual(execution.status, CommandStatus.SUCCESS)
        self.assertEqual(execution.result["result"], "value")
        self.assertIn("Handler called", execution.logs[1])
    
    async def test_command_with_tool_mapping(self):
        """Test command execution with tool mapping"""
        mock_tool = AsyncMock()
        mock_tool.execute = AsyncMock(return_value={"tool_result": "success"})
        self.agent.get_tool = Mock(return_value=mock_tool)
        
        command = AgentCommand(
            name="test",
            description="Test command",
            tool_mapping="test_tool"
        )
        
        execution = await command.execute(self.agent, param1="value")
        
        self.assertEqual(execution.status, CommandStatus.SUCCESS)
        self.agent.get_tool.assert_called_with("test_tool")
        mock_tool.execute.assert_called_once()
    
    async def test_command_parameter_validation(self):
        """Test command parameter validation during execution"""
        command = AgentCommand(
            name="test",
            description="Test command",
            parameters=[
                CommandParameter(
                    name="required_param",
                    type=ParameterType.STRING,
                    required=True
                )
            ],
            handler=AsyncMock(return_value="success")
        )
        
        # Should fail without required parameter
        execution = await command.execute(self.agent)
        self.assertEqual(execution.status, CommandStatus.FAILED)
        self.assertIn("required", execution.error)
        
        # Should succeed with required parameter
        execution = await command.execute(self.agent, required_param="value")
        self.assertEqual(execution.status, CommandStatus.SUCCESS)
    
    async def test_command_retry_logic(self):
        """Test command retry on failure"""
        call_count = 0
        
        async def failing_handler(agent, execution, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        command = AgentCommand(
            name="test",
            description="Test command",
            handler=failing_handler,
            retries=2
        )
        
        execution = await command.execute(self.agent)
        
        self.assertEqual(execution.status, CommandStatus.SUCCESS)
        self.assertEqual(call_count, 3)  # Initial + 2 retries


class TestCommandRegistry(unittest.TestCase):
    """Test command registry"""
    
    def setUp(self):
        self.registry = CommandRegistry()
        self.agent = Mock()
    
    def test_register_command(self):
        """Test registering a command"""
        command = AgentCommand(
            name="test",
            description="Test command"
        )
        
        self.registry.register(command)
        
        self.assertIn("test", self.registry.list_commands())
        self.assertEqual(self.registry.get("test"), command)
    
    def test_unregister_command(self):
        """Test unregistering a command"""
        command = AgentCommand(name="test", description="Test")
        self.registry.register(command)
        
        self.registry.unregister("test")
        
        self.assertNotIn("test", self.registry.list_commands())
        self.assertIsNone(self.registry.get("test"))
    
    def test_get_command_info(self):
        """Test getting command information"""
        command = AgentCommand(
            name="test",
            description="Test command",
            parameters=[
                CommandParameter(
                    name="param1",
                    type=ParameterType.STRING,
                    required=True,
                    description="Test parameter"
                )
            ],
            dependencies=["dep1", "dep2"]
        )
        
        self.registry.register(command)
        info = self.registry.get_command_info("test")
        
        self.assertEqual(info["name"], "test")
        self.assertEqual(info["description"], "Test command")
        self.assertEqual(len(info["parameters"]), 1)
        self.assertEqual(info["parameters"][0]["name"], "param1")
        self.assertEqual(info["dependencies"], ["dep1", "dep2"])
    
    async def test_execute_command(self):
        """Test executing a command through registry"""
        command = AgentCommand(
            name="test",
            description="Test",
            handler=AsyncMock(return_value="result")
        )
        
        self.registry.register(command)
        execution = await self.registry.execute(self.agent, "test", param="value")
        
        self.assertEqual(execution.status, CommandStatus.SUCCESS)
        self.assertIn(execution, self.registry.executions)
    
    def test_execution_history(self):
        """Test getting execution history"""
        # Create some mock executions
        for i in range(5):
            exec = CommandExecution(
                command_name=f"cmd{i}",
                parameters={"index": i}
            )
            self.registry.executions.append(exec)
        
        history = self.registry.get_execution_history(limit=3)
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[-1]["command"], "cmd4")


class TestCommandParser(unittest.TestCase):
    """Test command parser"""
    
    def test_parse_from_markdown(self):
        """Test parsing commands from markdown"""
        markdown = """
## Commands

### create-prd
**Description**: Create a Product Requirements Document
**Parameters**:
- `product_name` (required): Name of the product
- `scope`: Scope of the PRD
**Execution**:
1. Gather requirements
2. Create document
3. Review and finalize
**Dependencies**: template_system, checklist_executor

### analyze-metrics
**Description**: Analyze product metrics
**Parameters**:
- `metric_type`: Type of metric to analyze
"""
        
        commands = CommandParser.parse_from_markdown(markdown)
        
        self.assertEqual(len(commands), 2)
        
        # Check first command
        cmd1 = commands[0]
        self.assertEqual(cmd1.name, "create-prd")
        self.assertIn("Product Requirements Document", cmd1.description)
        self.assertEqual(len(cmd1.parameters), 2)
        self.assertTrue(cmd1.parameters[0].required)
        self.assertFalse(cmd1.parameters[1].required)
        self.assertEqual(len(cmd1.execution_steps), 3)
        self.assertIn("template_system", cmd1.dependencies)
        
        # Check second command
        cmd2 = commands[1]
        self.assertEqual(cmd2.name, "analyze-metrics")
        self.assertEqual(len(cmd2.parameters), 1)
    
    def test_parse_empty_commands_section(self):
        """Test parsing with no commands section"""
        markdown = """
## Overview
This is an agent definition without commands.
"""
        
        commands = CommandParser.parse_from_markdown(markdown)
        self.assertEqual(len(commands), 0)


class TestCommandSystem(unittest.TestCase):
    """Test the main command system"""
    
    def setUp(self):
        self.command_system = CommandSystem()
        self.agent = Mock()
    
    def test_builtin_commands(self):
        """Test that built-in commands are loaded"""
        commands = self.command_system.get_available_commands()
        
        self.assertIn("save-memory", commands)
        self.assertIn("recall-memory", commands)
        self.assertIn("execute-code", commands)
        self.assertIn("read-file", commands)
        self.assertIn("write-file", commands)
    
    def test_create_custom_command(self):
        """Test creating a custom command"""
        def custom_handler(agent, execution, param1: str, param2: int = 10):
            return f"Executed with {param1} and {param2}"
        
        command = self.command_system.create_command(
            name="custom",
            description="Custom command",
            handler=custom_handler
        )
        
        self.assertEqual(command.name, "custom")
        self.assertEqual(len(command.parameters), 2)
        self.assertIn("custom", self.command_system.get_available_commands())
    
    def test_get_command_help(self):
        """Test getting command help text"""
        help_text = self.command_system.get_command_help("save-memory")
        
        self.assertIn("save-memory", help_text)
        self.assertIn("Save information to agent memory", help_text)
        self.assertIn("content", help_text)
        self.assertIn("required", help_text)
    
    def test_load_agent_commands(self):
        """Test loading commands from agent definition"""
        # Create a temporary agent definition
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir)
            agent_file = agent_path / "agent.md"
            
            agent_file.write_text("""
## Commands

### test-command
**Description**: Test command for testing
**Parameters**:
- `param1` (required): Test parameter
""")
            
            commands = self.command_system.load_agent_commands(agent_path)
            
            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0].name, "test-command")
            self.assertIn("test-command", self.command_system.get_available_commands())


class TestCommandExecution(unittest.TestCase):
    """Test command execution tracking"""
    
    def test_execution_logging(self):
        """Test execution logging"""
        execution = CommandExecution(
            command_name="test",
            parameters={"param": "value"}
        )
        
        execution.log("Test message")
        
        self.assertEqual(len(execution.logs), 1)
        self.assertIn("Test message", execution.logs[0])
    
    def test_execution_to_dict(self):
        """Test converting execution to dictionary"""
        execution = CommandExecution(
            command_name="test",
            parameters={"param": "value"},
            status=CommandStatus.SUCCESS,
            result={"output": "result"},
            error=None
        )
        
        data = execution.to_dict()
        
        self.assertEqual(data["command"], "test")
        self.assertEqual(data["parameters"]["param"], "value")
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["result"]["output"], "result")
        self.assertIsNone(data["error"])


def run_async_test(coro):
    """Helper to run async tests"""
    return asyncio.run(coro)


# Wrap async tests
class AsyncTestCase(unittest.TestCase):
    """Base class for async tests"""
    
    def test_async_command_execution(self):
        test_case = TestAgentCommand()
        test_case.setUp()
        run_async_test(test_case.test_command_with_handler())
    
    def test_async_tool_mapping(self):
        test_case = TestAgentCommand()
        test_case.setUp()
        run_async_test(test_case.test_command_with_tool_mapping())
    
    def test_async_parameter_validation(self):
        test_case = TestAgentCommand()
        test_case.setUp()
        run_async_test(test_case.test_command_parameter_validation())
    
    def test_async_retry_logic(self):
        test_case = TestAgentCommand()
        test_case.setUp()
        run_async_test(test_case.test_command_retry_logic())
    
    def test_async_registry_execute(self):
        test_case = TestCommandRegistry()
        test_case.setUp()
        run_async_test(test_case.test_execute_command())


if __name__ == "__main__":
    unittest.main()