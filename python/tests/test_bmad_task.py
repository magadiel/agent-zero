"""
Test suite for BMAD Task Loading and Execution System
"""

import os
import sys
import unittest
import asyncio
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.task_loader import (
    TaskLoader, TaskStep, TaskDependency, TaskContext, BMADTask, TaskRegistry
)
from tools.bmad_task_executor import BMADTaskExecutor


class TestTaskStep(unittest.TestCase):
    """Test TaskStep class."""
    
    def test_task_step_creation(self):
        """Test creating a task step."""
        step = TaskStep(
            id="step1",
            name="Test Step",
            description="A test step",
            action="test_action",
            params={"param1": "value1"},
            requires=["step0"],
            produces=["artifact1"],
            timeout=60,
            retries=2,
            optional=False
        )
        
        self.assertEqual(step.id, "step1")
        self.assertEqual(step.name, "Test Step")
        self.assertEqual(step.action, "test_action")
        self.assertEqual(step.params["param1"], "value1")
        self.assertEqual(step.timeout, 60)
        self.assertEqual(step.retries, 2)
        self.assertFalse(step.optional)
    
    def test_task_step_to_dict(self):
        """Test converting task step to dictionary."""
        step = TaskStep(
            id="step1",
            name="Test Step",
            description="A test step",
            action="test_action"
        )
        
        step_dict = step.to_dict()
        self.assertIn("id", step_dict)
        self.assertIn("name", step_dict)
        self.assertIn("action", step_dict)
        self.assertEqual(step_dict["id"], "step1")


class TestTaskDependency(unittest.TestCase):
    """Test TaskDependency class."""
    
    def test_dependency_creation(self):
        """Test creating a task dependency."""
        dep = TaskDependency(
            type="template",
            name="prd_template",
            path="templates/prd.yaml",
            lazy_load=True,
            required=True
        )
        
        self.assertEqual(dep.type, "template")
        self.assertEqual(dep.name, "prd_template")
        self.assertEqual(dep.path, "templates/prd.yaml")
        self.assertTrue(dep.lazy_load)
        self.assertTrue(dep.required)
    
    def test_dependency_load_yaml(self):
        """Test loading YAML dependency."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"key": "value"}, f)
            temp_path = f.name
        
        try:
            dep = TaskDependency(
                type="data",
                name="test_data",
                path=temp_path
            )
            
            content = dep.load()
            self.assertEqual(content["key"], "value")
            
        finally:
            os.unlink(temp_path)
    
    def test_dependency_load_json(self):
        """Test loading JSON dependency."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"key": "value"}, f)
            temp_path = f.name
        
        try:
            dep = TaskDependency(
                type="data",
                name="test_data",
                path=temp_path
            )
            
            content = dep.load()
            self.assertEqual(content["key"], "value")
            
        finally:
            os.unlink(temp_path)
    
    def test_dependency_optional_missing(self):
        """Test optional dependency with missing file."""
        dep = TaskDependency(
            type="data",
            name="optional_data",
            path="nonexistent.yaml",
            required=False
        )
        
        content = dep.load()
        self.assertIsNone(content)
    
    def test_dependency_required_missing(self):
        """Test required dependency with missing file."""
        dep = TaskDependency(
            type="data",
            name="required_data",
            path="nonexistent.yaml",
            required=True
        )
        
        with self.assertRaises(FileNotFoundError):
            dep.load()


class TestTaskContext(unittest.TestCase):
    """Test TaskContext class."""
    
    def test_context_creation(self):
        """Test creating task context."""
        context = TaskContext()
        
        self.assertIsInstance(context.sources, dict)
        self.assertIsInstance(context.citations, list)
        self.assertIsInstance(context.artifacts, dict)
        self.assertIsInstance(context.metadata, dict)
    
    def test_add_source(self):
        """Test adding source to context."""
        context = TaskContext()
        
        context.add_source("source1", "content1")
        self.assertEqual(context.get_source("source1"), "content1")
        
        context.add_source(
            "source2",
            "content2",
            {"type": "external", "url": "http://example.com"}
        )
        self.assertEqual(len(context.citations), 1)
        self.assertEqual(context.citations[0]["source"], "source2")
    
    def test_add_artifact(self):
        """Test adding artifact to context."""
        context = TaskContext()
        
        context.add_artifact("artifact1", {"data": "value"})
        self.assertIn("artifact1", context.artifacts)
        self.assertEqual(context.artifacts["artifact1"]["data"], "value")
    
    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = TaskContext()
        context.add_source("source1", "content1")
        context.add_artifact("artifact1", "data1")
        
        context_dict = context.to_dict()
        self.assertIn("sources", context_dict)
        self.assertIn("citations", context_dict)
        self.assertIn("artifacts", context_dict)
        self.assertIn("metadata", context_dict)


class TestBMADTask(unittest.TestCase):
    """Test BMADTask class."""
    
    def test_task_creation(self):
        """Test creating a BMAD task."""
        steps = [
            TaskStep(id="s1", name="Step 1", description="First", action="action1"),
            TaskStep(id="s2", name="Step 2", description="Second", action="action2", requires=["s1"])
        ]
        
        deps = [
            TaskDependency(type="template", name="template1", path="t1.yaml")
        ]
        
        task = BMADTask(
            id="task1",
            name="Test Task",
            description="A test task",
            category="execution",
            steps=steps,
            dependencies=deps
        )
        
        self.assertEqual(task.id, "task1")
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(len(task.steps), 2)
        self.assertEqual(len(task.dependencies), 1)
        self.assertTrue(task.sequential)
        self.assertTrue(task.gather_context)
    
    def test_task_validation_success(self):
        """Test successful task validation."""
        steps = [
            TaskStep(id="s1", name="Step 1", description="First", action="action1"),
            TaskStep(id="s2", name="Step 2", description="Second", action="action2", requires=["s1"])
        ]
        
        task = BMADTask(
            id="task1",
            name="Test Task",
            description="A test task",
            category="execution",
            steps=steps
        )
        
        issues = task.validate()
        self.assertEqual(len(issues), 0)
    
    def test_task_validation_duplicate_step(self):
        """Test task validation with duplicate step IDs."""
        steps = [
            TaskStep(id="s1", name="Step 1", description="First", action="action1"),
            TaskStep(id="s1", name="Step 2", description="Second", action="action2")
        ]
        
        task = BMADTask(
            id="task1",
            name="Test Task",
            description="A test task",
            category="execution",
            steps=steps
        )
        
        issues = task.validate()
        self.assertIn("Duplicate step ID: s1", issues)
    
    def test_task_validation_missing_dependency(self):
        """Test task validation with missing step dependency."""
        steps = [
            TaskStep(id="s1", name="Step 1", description="First", action="action1", requires=["s0"]),
            TaskStep(id="s2", name="Step 2", description="Second", action="action2")
        ]
        
        task = BMADTask(
            id="task1",
            name="Test Task",
            description="A test task",
            category="execution",
            steps=steps
        )
        
        issues = task.validate()
        self.assertIn("Step s1 requires unknown step: s0", issues)
    
    def test_get_dependency(self):
        """Test getting dependency by name."""
        deps = [
            TaskDependency(type="template", name="template1", path="t1.yaml"),
            TaskDependency(type="checklist", name="checklist1", path="c1.yaml")
        ]
        
        task = BMADTask(
            id="task1",
            name="Test Task",
            description="A test task",
            category="execution",
            steps=[],
            dependencies=deps
        )
        
        dep = task.get_dependency("template1")
        self.assertIsNotNone(dep)
        self.assertEqual(dep.type, "template")
        
        dep = task.get_dependency("checklist1", dep_type="checklist")
        self.assertIsNotNone(dep)
        
        dep = task.get_dependency("nonexistent")
        self.assertIsNone(dep)


class TestTaskLoader(unittest.TestCase):
    """Test TaskLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = TaskLoader(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_task_from_dict(self):
        """Test loading task from dictionary."""
        task_data = {
            "id": "test_task",
            "name": "Test Task",
            "description": "A test task",
            "category": "execution",
            "steps": [
                {
                    "id": "step1",
                    "name": "Step 1",
                    "description": "First step",
                    "action": "action1"
                }
            ]
        }
        
        task = self.loader.load_task_from_dict(task_data)
        
        self.assertEqual(task.id, "test_task")
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(len(task.steps), 1)
    
    def test_load_task_from_file(self):
        """Test loading task from YAML file."""
        task_data = {
            "id": "file_task",
            "name": "File Task",
            "description": "Task from file",
            "category": "validation",
            "sequential": False,
            "steps": [
                {
                    "id": "s1",
                    "name": "Step 1",
                    "description": "First",
                    "action": "validate",
                    "optional": True
                }
            ],
            "dependencies": [
                {
                    "type": "template",
                    "name": "template1",
                    "path": "template.yaml",
                    "required": False
                }
            ]
        }
        
        task_file = os.path.join(self.temp_dir, "task.yaml")
        with open(task_file, 'w') as f:
            yaml.dump(task_data, f)
        
        task = self.loader.load_task("task.yaml")
        
        self.assertEqual(task.id, "file_task")
        self.assertFalse(task.sequential)
        self.assertTrue(task.steps[0].optional)
        self.assertEqual(len(task.dependencies), 1)
    
    def test_task_cache(self):
        """Test task caching."""
        task_data = {
            "id": "cached_task",
            "name": "Cached Task",
            "description": "Task for caching",
            "category": "execution",
            "steps": [
                {
                    "id": "s1",
                    "name": "Step",
                    "description": "Step",
                    "action": "action"
                }
            ]
        }
        
        task_file = os.path.join(self.temp_dir, "cached.yaml")
        with open(task_file, 'w') as f:
            yaml.dump(task_data, f)
        
        # First load
        task1 = self.loader.load_task("cached.yaml")
        
        # Second load (should use cache)
        task2 = self.loader.load_task("cached.yaml")
        
        # Should be the same object
        self.assertIs(task1, task2)
        
        # Load without cache
        task3 = self.loader.load_task("cached.yaml", use_cache=False)
        self.assertIsNot(task1, task3)
    
    def test_load_dependencies(self):
        """Test loading task dependencies."""
        # Create dependency files
        template_data = {"template": "content"}
        template_file = os.path.join(self.temp_dir, "template.yaml")
        with open(template_file, 'w') as f:
            yaml.dump(template_data, f)
        
        task = BMADTask(
            id="task_with_deps",
            name="Task with Dependencies",
            description="Test",
            category="execution",
            steps=[],
            dependencies=[
                TaskDependency(
                    type="template",
                    name="template1",
                    path="template.yaml",
                    lazy_load=False
                )
            ]
        )
        
        deps = self.loader.load_dependencies(task, lazy=False)
        
        self.assertIn("template1", deps)
        self.assertEqual(deps["template1"]["template"], "content")


class TestTaskRegistry(unittest.TestCase):
    """Test TaskRegistry class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = TaskRegistry()
    
    def test_register_task(self):
        """Test registering a task."""
        task = BMADTask(
            id="task1",
            name="Task 1",
            description="Test task",
            category="execution",
            steps=[]
        )
        
        self.registry.register_task(task)
        
        self.assertIn("task1", self.registry.list_tasks())
        self.assertEqual(self.registry.get_task("task1"), task)
    
    def test_get_tasks_by_category(self):
        """Test getting tasks by category."""
        task1 = BMADTask(id="t1", name="T1", description="", category="execution", steps=[])
        task2 = BMADTask(id="t2", name="T2", description="", category="validation", steps=[])
        task3 = BMADTask(id="t3", name="T3", description="", category="execution", steps=[])
        
        self.registry.register_task(task1)
        self.registry.register_task(task2)
        self.registry.register_task(task3)
        
        execution_tasks = self.registry.get_tasks_by_category("execution")
        self.assertEqual(len(execution_tasks), 2)
        self.assertIn(task1, execution_tasks)
        self.assertIn(task3, execution_tasks)
    
    def test_search_tasks(self):
        """Test searching tasks."""
        task1 = BMADTask(id="t1", name="Data Processing", description="Process data", category="execution", steps=[])
        task2 = BMADTask(id="t2", name="Validation", description="Validate results", category="validation", steps=[])
        task3 = BMADTask(id="t3", name="Report", description="Generate data report", category="reporting", steps=[])
        
        self.registry.register_task(task1)
        self.registry.register_task(task2)
        self.registry.register_task(task3)
        
        results = self.registry.search_tasks("data")
        self.assertEqual(len(results), 2)
        self.assertIn(task1, results)
        self.assertIn(task3, results)


class TestBMADTaskExecutor(unittest.IsolatedAsyncioTestCase):
    """Test BMADTaskExecutor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = Mock()
        self.agent.tools = []
        self.executor = BMADTaskExecutor(self.agent)
    
    async def test_dry_run(self):
        """Test dry run validation."""
        task_data = {
            "id": "test_task",
            "name": "Test Task",
            "description": "Test",
            "category": "execution",
            "steps": [
                {
                    "id": "s1",
                    "name": "Step 1",
                    "description": "First",
                    "action": "test"
                }
            ]
        }
        
        response = await self.executor.execute(
            task_data=task_data,
            dry_run=True
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.data["task_id"], "test_task")
        self.assertEqual(response.data["validation"], "PASSED")
    
    async def test_execute_sequential_task(self):
        """Test executing a sequential task."""
        task_data = {
            "id": "seq_task",
            "name": "Sequential Task",
            "description": "Test sequential execution",
            "category": "execution",
            "sequential": True,
            "gather_context": False,
            "steps": [
                {
                    "id": "s1",
                    "name": "Step 1",
                    "description": "First",
                    "action": "gather_data",
                    "produces": ["data1"]
                },
                {
                    "id": "s2",
                    "name": "Step 2",
                    "description": "Second",
                    "action": "process",
                    "requires": ["s1"],
                    "produces": ["result"]
                }
            ]
        }
        
        response = await self.executor.execute(task_data=task_data)
        
        self.assertTrue(response.success)
        self.assertEqual(len(response.data["steps_executed"]), 2)
        self.assertTrue(response.data["steps_executed"][0]["success"])
        self.assertTrue(response.data["steps_executed"][1]["success"])
    
    async def test_execute_with_optional_step(self):
        """Test executing task with optional failing step."""
        task_data = {
            "id": "optional_task",
            "name": "Task with Optional Step",
            "description": "Test optional step",
            "category": "execution",
            "gather_context": False,
            "steps": [
                {
                    "id": "s1",
                    "name": "Required Step",
                    "description": "Must succeed",
                    "action": "validate"
                },
                {
                    "id": "s2",
                    "name": "Optional Step",
                    "description": "Can fail",
                    "action": "unknown_action",
                    "optional": True
                }
            ]
        }
        
        response = await self.executor.execute(task_data=task_data)
        
        self.assertTrue(response.success)  # Should succeed despite optional step
    
    async def test_context_gathering(self):
        """Test context gathering during execution."""
        task_data = {
            "id": "context_task",
            "name": "Context Task",
            "description": "Test context gathering",
            "category": "analysis",
            "gather_context": True,
            "cite_sources": True,
            "steps": [
                {
                    "id": "s1",
                    "name": "Generate",
                    "description": "Generate output",
                    "action": "generate",
                    "produces": ["output"]
                }
            ]
        }
        
        response = await self.executor.execute(
            task_data=task_data,
            params={"input": "test"}
        )
        
        self.assertTrue(response.success)
        context = response.data["context"]
        self.assertIn("task_definition", context["sources"])
        self.assertIn("task_params", context["sources"])
        self.assertIn("output", context["artifacts"])
    
    async def test_step_validation(self):
        """Test step validation."""
        task_data = {
            "id": "validation_task",
            "name": "Validation Task",
            "description": "Test step validation",
            "category": "validation",
            "gather_context": False,
            "steps": [
                {
                    "id": "s1",
                    "name": "Validate Step",
                    "description": "Step with validation",
                    "action": "validate",
                    "validation": {
                        "required_fields": ["valid"],
                        "conditions": [
                            {
                                "field": "valid",
                                "operator": "equals",
                                "value": True
                            }
                        ]
                    }
                }
            ]
        }
        
        response = await self.executor.execute(task_data=task_data)
        
        self.assertTrue(response.success)
        self.assertTrue(response.data["steps_executed"][0]["success"])
    
    def test_interrupt(self):
        """Test task interruption."""
        self.executor.interrupt()
        self.assertTrue(self.executor.interrupted)
    
    def test_reset(self):
        """Test resetting executor state."""
        self.executor.context.add_source("test", "data")
        self.executor.execution_log.append({"test": "log"})
        
        self.executor.reset()
        
        self.assertEqual(len(self.executor.context.sources), 0)
        self.assertEqual(len(self.executor.execution_log), 0)
        self.assertIsNone(self.executor.current_task)
        self.assertFalse(self.executor.interrupted)


if __name__ == '__main__':
    unittest.main()