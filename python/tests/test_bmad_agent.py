"""
Unit tests for BMAD Agent Enhancement Module
"""

import unittest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import tempfile
import yaml
import os

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from python.helpers.bmad_agent import (
    Persona,
    AgentCommand,
    ActivationPhase,
    BMADAgentDefinition,
    BMADAgentLoader,
    BMADAgentEnhancer,
    CommandMapper,
    DependencyType,
    enhance_agent_with_bmad,
    register_command_mapping
)


class TestPersona(unittest.TestCase):
    """Test Persona class"""
    
    def test_persona_creation(self):
        """Test creating a Persona instance"""
        persona = Persona(
            role="Product Manager",
            style="Analytical and data-driven",
            identity="Strategic product leader",
            focus=["User needs", "Market fit"],
            core_principles=["User-centric", "Data-driven"]
        )
        
        self.assertEqual(persona.role, "Product Manager")
        self.assertEqual(persona.style, "Analytical and data-driven")
        self.assertEqual(len(persona.focus), 2)
        self.assertEqual(len(persona.core_principles), 2)
    
    def test_persona_from_dict(self):
        """Test creating Persona from dictionary"""
        data = {
            'role': 'Architect',
            'style': 'Systematic',
            'identity': 'Technical leader',
            'focus': ['Scalability', 'Performance'],
            'core_principles': ['Best practices', 'Security']
        }
        
        persona = Persona.from_dict(data)
        
        self.assertEqual(persona.role, 'Architect')
        self.assertEqual(persona.style, 'Systematic')
        self.assertEqual(len(persona.focus), 2)


class TestAgentCommand(unittest.TestCase):
    """Test AgentCommand class"""
    
    def test_command_creation(self):
        """Test creating an AgentCommand"""
        command = AgentCommand(
            name="create_prd",
            description="Create a Product Requirements Document",
            parameters={"template": "prd.yaml"},
            dependencies=["templates/prd"]
        )
        
        self.assertEqual(command.name, "create_prd")
        self.assertIn("template", command.parameters)
        self.assertEqual(len(command.dependencies), 1)
    
    @patch('asyncio.create_task')
    def test_command_execution_without_handler(self, mock_task):
        """Test command execution without handler raises error"""
        command = AgentCommand(name="test", description="Test command")
        agent = Mock()
        
        async def run_test():
            with self.assertRaises(NotImplementedError):
                await command.execute(agent)
        
        asyncio.run(run_test())
    
    def test_command_execution_with_handler(self):
        """Test command execution with handler"""
        async def test_handler(agent, **kwargs):
            return f"Executed for {agent.name}"
        
        command = AgentCommand(
            name="test",
            description="Test command",
            handler=test_handler
        )
        
        agent = Mock()
        agent.name = "TestAgent"
        
        async def run_test():
            result = await command.execute(agent)
            self.assertEqual(result, "Executed for TestAgent")
        
        asyncio.run(run_test())


class TestActivationPhase(unittest.TestCase):
    """Test ActivationPhase class"""
    
    def test_activation_phase_creation(self):
        """Test creating an ActivationPhase"""
        phase = ActivationPhase(
            name="Initialize",
            description="Initialize agent context",
            actions=["load_templates", "load_checklists"],
            validation="check_resources_loaded"
        )
        
        self.assertEqual(phase.name, "Initialize")
        self.assertEqual(len(phase.actions), 2)
        self.assertEqual(phase.validation, "check_resources_loaded")
    
    def test_activation_phase_from_dict(self):
        """Test creating ActivationPhase from dictionary"""
        data = {
            'name': 'Setup',
            'description': 'Setup agent',
            'actions': ['action1', 'action2'],
            'validation': 'validate_setup'
        }
        
        phase = ActivationPhase.from_dict(data)
        
        self.assertEqual(phase.name, 'Setup')
        self.assertEqual(len(phase.actions), 2)


class TestBMADAgentLoader(unittest.TestCase):
    """Test BMADAgentLoader class"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = BMADAgentLoader(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_loader_initialization(self):
        """Test loader initialization"""
        self.assertEqual(self.loader.base_path, Path(self.temp_dir))
        self.assertEqual(len(self.loader.agents), 0)
        self.assertEqual(len(self.loader.command_registry), 0)
    
    def test_load_nonexistent_agent(self):
        """Test loading a non-existent agent"""
        result = self.loader.load_agent("nonexistent")
        self.assertIsNone(result)
    
    def test_extract_yaml_frontmatter(self):
        """Test extracting YAML frontmatter from markdown"""
        content = """---
agent:
  name: TestAgent
  id: test-agent
persona:
  role: Test Role
---

# Agent Content
"""
        
        yaml_content = self.loader._extract_yaml_frontmatter(content)
        self.assertIsNotNone(yaml_content)
        self.assertIn("agent:", yaml_content)
        self.assertIn("persona:", yaml_content)
    
    def test_parse_dependencies(self):
        """Test parsing dependencies"""
        deps_data = {
            'tasks': ['task1', 'task2'],
            'templates': ['template1'],
            'checklists': ['checklist1']
        }
        
        dependencies = self.loader._parse_dependencies(deps_data)
        
        self.assertEqual(len(dependencies[DependencyType.TASK]), 2)
        self.assertEqual(len(dependencies[DependencyType.TEMPLATE]), 1)
        self.assertEqual(len(dependencies[DependencyType.CHECKLIST]), 1)


class TestBMADAgentEnhancer(unittest.TestCase):
    """Test BMADAgentEnhancer class"""
    
    def setUp(self):
        """Set up test environment"""
        self.loader = Mock(spec=BMADAgentLoader)
        self.enhancer = BMADAgentEnhancer(self.loader)
    
    def test_enhancer_initialization(self):
        """Test enhancer initialization"""
        self.assertEqual(self.enhancer.loader, self.loader)
    
    def test_enhance_agent_without_profile(self):
        """Test enhancing agent without profile"""
        agent = Mock()
        agent.config = Mock()
        agent.config.profile = ""
        
        result = self.enhancer.enhance_agent(agent)
        self.assertFalse(result)
    
    def test_enhance_agent_with_profile(self):
        """Test enhancing agent with valid profile"""
        # Create mock agent
        agent = Mock()
        agent.config = Mock()
        agent.config.profile = "test_profile"
        agent.agent_name = "TestAgent"
        
        # Create mock BMAD definition
        bmad_def = Mock(spec=BMADAgentDefinition)
        bmad_def.persona = Mock(spec=Persona)
        
        # Configure loader mock
        self.loader.load_agent.return_value = bmad_def
        
        # Enhance agent
        result = self.enhancer.enhance_agent(agent)
        
        # Verify enhancement
        self.assertTrue(result)
        self.assertTrue(hasattr(agent, 'bmad_definition'))
        self.assertTrue(hasattr(agent, 'bmad_activated'))
        self.assertTrue(hasattr(agent, 'execute_bmad_command'))
        self.assertTrue(hasattr(agent, 'activate_bmad'))
        self.assertTrue(hasattr(agent, 'load_bmad_dependency'))
        self.assertEqual(agent.persona, bmad_def.persona)
    
    def test_get_dependency_type(self):
        """Test converting string to DependencyType"""
        # Test with enum value
        result = self.enhancer._get_dependency_type("tasks")
        self.assertEqual(result, DependencyType.TASK)
        
        # Test with enum name
        result = self.enhancer._get_dependency_type("TEMPLATE")
        self.assertEqual(result, DependencyType.TEMPLATE)
        
        # Test with invalid string
        result = self.enhancer._get_dependency_type("invalid")
        self.assertIsNone(result)


class TestCommandMapper(unittest.TestCase):
    """Test CommandMapper class"""
    
    def setUp(self):
        """Set up test environment"""
        self.mapper = CommandMapper()
    
    def test_register_mapping(self):
        """Test registering command-to-tool mapping"""
        self.mapper.register_mapping("create_prd", "CreatePRDTool")
        
        self.assertIn("create_prd", self.mapper.mappings)
        self.assertEqual(self.mapper.mappings["create_prd"], "CreatePRDTool")
    
    def test_get_tool_for_command(self):
        """Test getting tool for command"""
        self.mapper.register_mapping("test_command", "TestTool")
        
        result = self.mapper.get_tool_for_command("test_command")
        self.assertEqual(result, "TestTool")
        
        result = self.mapper.get_tool_for_command("unknown_command")
        self.assertIsNone(result)
    
    def test_create_tool_wrapper(self):
        """Test creating tool wrapper"""
        command = Mock(spec=AgentCommand)
        command.name = "test_command"
        
        wrapper = self.mapper.create_tool_wrapper(command, "TestTool")
        
        self.assertTrue(callable(wrapper))
        self.assertTrue(asyncio.iscoroutinefunction(wrapper))


class TestIntegration(unittest.TestCase):
    """Integration tests for BMAD agent system"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test agent directory structure
        agent_dir = Path(self.temp_dir) / "test_agent"
        agent_dir.mkdir()
        
        # Create agent definition file
        agent_file = agent_dir / "agent.md"
        agent_content = """---
agent:
  name: TestAgent
  id: test-agent
  title: Test Agent
  icon: 🧪
  whenToUse: For testing
persona:
  role: Tester
  style: Methodical
  identity: Quality assurance
  focus:
    - Testing
    - Validation
  core_principles:
    - Thoroughness
    - Accuracy
activation-instructions:
  - name: Initialize
    description: Initialize test agent
    actions:
      - load_templates
    validation: check_initialized
dependencies:
  templates:
    - test_template
---

# Test Agent Definition
"""
        agent_file.write_text(agent_content)
        
        # Create commands directory
        (agent_dir / "commands").mkdir()
        
        # Create dependencies directory
        deps_dir = agent_dir / "dependencies"
        deps_dir.mkdir()
        (deps_dir / "templates").mkdir()
        
        # Create a test template
        template_file = deps_dir / "templates" / "test_template.yaml"
        template_file.write_text("name: Test Template\ncontent: Template content")
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_agent_loading(self):
        """Test loading a complete BMAD agent"""
        loader = BMADAgentLoader(self.temp_dir)
        
        agent_def = loader.load_agent("test_agent")
        
        self.assertIsNotNone(agent_def)
        self.assertEqual(agent_def.name, "TestAgent")
        self.assertEqual(agent_def.id, "test-agent")
        self.assertEqual(agent_def.persona.role, "Tester")
        self.assertEqual(len(agent_def.activation_phases), 1)
        self.assertIn(DependencyType.TEMPLATE, agent_def.dependencies)
    
    def test_dependency_loading(self):
        """Test loading agent dependencies"""
        loader = BMADAgentLoader(self.temp_dir)
        agent_def = loader.load_agent("test_agent")
        
        # Create the template file in the correct location
        template_path = Path(self.temp_dir) / "TestAgent" / "dependencies" / "templates"
        template_path.mkdir(parents=True, exist_ok=True)
        template_file = template_path / "test_template.yaml"
        template_file.write_text("name: Test Template\ncontent: Template content")
        
        async def run_test():
            templates = await loader.load_dependencies(agent_def, DependencyType.TEMPLATE)
            self.assertIn("test_template", templates)
            self.assertEqual(templates["test_template"]["name"], "Test Template")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()