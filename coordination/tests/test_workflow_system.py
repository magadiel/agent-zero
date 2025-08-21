"""
Unit tests for the workflow orchestration system
"""

import unittest
import asyncio
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from coordination.workflow_parser import (
    WorkflowParser,
    WorkflowDefinition,
    WorkflowStep,
    StepType,
    WorkflowCondition,
    WorkflowState
)
from coordination.workflow_engine import (
    WorkflowEngine,
    WorkflowExecution,
    StepExecution,
    StepState,
    DocumentManager,
    AgentPool
)


class TestWorkflowParser(unittest.TestCase):
    """Test workflow parser functionality"""
    
    def test_parse_simple_workflow(self):
        """Test parsing a simple workflow"""
        yaml_content = """
id: test-workflow
name: Test Workflow
description: A simple test workflow
version: 1.0.0
steps:
  - id: step1
    type: agent_task
    name: First Step
    agent: developer
    task: Write code
  - id: step2
    type: agent_task
    name: Second Step
    agent: qa_engineer
    task: Test code
    requires: [step1]
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        self.assertEqual(workflow.id, "test-workflow")
        self.assertEqual(workflow.name, "Test Workflow")
        self.assertEqual(len(workflow.steps), 2)
        self.assertEqual(workflow.steps[0].agent, "developer")
        self.assertEqual(workflow.steps[1].agent, "qa_engineer")
    
    def test_parse_conditional_workflow(self):
        """Test parsing workflow with conditional branching"""
        yaml_content = """
id: conditional-workflow
name: Conditional Workflow
description: Workflow with conditional logic
steps:
  - id: check
    type: conditional
    name: Check Condition
    condition:
      field: status
      operator: "=="
      value: success
    then_steps:
      - id: success_step
        type: agent_task
        name: Success Handler
        agent: developer
        task: Handle success
    else_steps:
      - id: failure_step
        type: agent_task
        name: Failure Handler
        agent: developer
        task: Handle failure
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        self.assertEqual(len(workflow.steps), 1)
        self.assertEqual(workflow.steps[0].type, StepType.CONDITIONAL)
        self.assertIsNotNone(workflow.steps[0].condition)
        self.assertEqual(len(workflow.steps[0].then_steps), 1)
        self.assertEqual(len(workflow.steps[0].else_steps), 1)
    
    def test_parse_parallel_workflow(self):
        """Test parsing workflow with parallel steps"""
        yaml_content = """
id: parallel-workflow
name: Parallel Workflow
description: Workflow with parallel execution
steps:
  - id: parallel
    type: parallel
    name: Parallel Tasks
    parallel_steps:
      - id: task1
        type: agent_task
        name: Task 1
        agent: developer
        task: Do task 1
      - id: task2
        type: agent_task
        name: Task 2
        agent: qa_engineer
        task: Do task 2
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        self.assertEqual(len(workflow.steps), 1)
        self.assertEqual(workflow.steps[0].type, StepType.PARALLEL)
        self.assertEqual(len(workflow.steps[0].parallel_steps), 2)
    
    def test_parse_bmad_style_workflow(self):
        """Test parsing BMAD-style sequence format"""
        yaml_content = """
id: bmad-workflow
name: BMAD Style Workflow
description: Using BMAD sequence format
sequence:
  - agent: analyst
    creates: project-brief.md
    optional_steps: [brainstorming, market_research]
  - agent: pm
    creates: prd.md
    requires: [project-brief.md]
  - agent: architect
    creates: architecture.md
    requires: [prd.md]
  - agent: po
    validates: all_artifacts
    uses: po-master-checklist
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        self.assertEqual(len(workflow.steps), 4)
        self.assertEqual(workflow.steps[0].agent, "analyst")
        self.assertEqual(workflow.steps[0].creates, "project-brief.md")
        self.assertEqual(workflow.steps[3].type, StepType.QUALITY_GATE)
    
    def test_workflow_validation(self):
        """Test workflow validation"""
        # Missing required fields
        yaml_content = """
name: Invalid Workflow
steps: []
"""
        with self.assertRaises(ValueError) as context:
            WorkflowParser.parse(yaml_content)
        self.assertIn("Workflow ID is required", str(context.exception))
        
        # Empty steps
        yaml_content = """
id: empty-workflow
name: Empty Workflow
description: No steps
steps: []
"""
        with self.assertRaises(ValueError) as context:
            WorkflowParser.parse(yaml_content)
        self.assertIn("must have at least one step", str(context.exception))
    
    def test_condition_evaluation(self):
        """Test workflow condition evaluation"""
        condition = WorkflowCondition(
            field="status.code",
            operator="==",
            value=200
        )
        
        context = {"status": {"code": 200}}
        self.assertTrue(condition.evaluate(context))
        
        context = {"status": {"code": 404}}
        self.assertFalse(condition.evaluate(context))
        
        # Test other operators
        condition = WorkflowCondition(field="count", operator=">", value=5)
        self.assertTrue(condition.evaluate({"count": 10}))
        self.assertFalse(condition.evaluate({"count": 3}))
        
        condition = WorkflowCondition(field="name", operator="contains", value="test")
        self.assertTrue(condition.evaluate({"name": "test_workflow"}))
        self.assertFalse(condition.evaluate({"name": "workflow"}))
        
        condition = WorkflowCondition(field="optional", operator="exists", value=None)
        self.assertTrue(condition.evaluate({"optional": "value"}))
        self.assertFalse(condition.evaluate({}))


class TestDocumentManager(unittest.TestCase):
    """Test document management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.doc_manager = DocumentManager(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_document(self):
        """Test saving and loading documents"""
        workflow_id = "test-workflow"
        doc_name = "test-doc.md"
        content = "# Test Document\nThis is test content."
        
        # Save document
        doc_path = self.doc_manager.save_document(workflow_id, doc_name, content)
        self.assertTrue(os.path.exists(doc_path))
        
        # Load document
        loaded_content = self.doc_manager.load_document(doc_path)
        self.assertEqual(loaded_content, content)
    
    def test_document_exists(self):
        """Test document existence check"""
        workflow_id = "test-workflow"
        doc_name = "test-doc.md"
        content = "Test content"
        
        doc_path = self.doc_manager.save_document(workflow_id, doc_name, content)
        self.assertTrue(self.doc_manager.document_exists(doc_path))
        
        fake_path = os.path.join(self.temp_dir, "fake-doc.md")
        self.assertFalse(self.doc_manager.document_exists(fake_path))
    
    def test_load_nonexistent_document(self):
        """Test loading non-existent document raises error"""
        fake_path = os.path.join(self.temp_dir, "nonexistent.md")
        with self.assertRaises(FileNotFoundError):
            self.doc_manager.load_document(fake_path)


class TestWorkflowEngine(unittest.TestCase):
    """Test workflow engine functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = WorkflowEngine(workflow_storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_create_workflow_execution(self):
        """Test creating workflow execution"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="Test"
        )
        
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            execution_id="test-exec-1",
            state=WorkflowState.PENDING
        )
        
        self.assertEqual(execution.workflow_id, "test-workflow")
        self.assertEqual(execution.state, WorkflowState.PENDING)
        self.assertEqual(len(execution.step_executions), 0)
    
    def test_step_execution_tracking(self):
        """Test step execution state tracking"""
        step_exec = StepExecution(
            step_id="step1",
            state=StepState.PENDING
        )
        
        self.assertEqual(step_exec.state, StepState.PENDING)
        self.assertIsNone(step_exec.started_at)
        
        # Update state
        step_exec.state = StepState.RUNNING
        step_exec.started_at = datetime.now()
        self.assertEqual(step_exec.state, StepState.RUNNING)
        self.assertIsNotNone(step_exec.started_at)
        
        # Complete step
        step_exec.state = StepState.COMPLETED
        step_exec.completed_at = datetime.now()
        step_exec.output = {"result": "success"}
        
        self.assertEqual(step_exec.state, StepState.COMPLETED)
        self.assertIsNotNone(step_exec.completed_at)
        self.assertEqual(step_exec.output["result"], "success")
    
    @unittest.skipIf(not os.path.exists("../agent.py"), "Requires Agent-Zero components")
    async def test_simple_workflow_execution(self):
        """Test executing a simple workflow (integration test)"""
        yaml_content = """
id: simple-test
name: Simple Test Workflow
description: Basic workflow for testing
steps:
  - id: wait1
    type: wait
    name: Wait Step
    timeout: 1
  - id: doc1
    type: document_create
    name: Create Document
    creates: test-output.md
    inputs:
      content: "Test document content"
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        # Execute workflow
        execution = await self.engine.execute_workflow(workflow)
        
        self.assertEqual(execution.state, WorkflowState.COMPLETED)
        self.assertEqual(len(execution.step_executions), 2)
        self.assertIn("test-output.md", execution.documents)
    
    async def test_conditional_workflow_execution(self):
        """Test executing workflow with conditional logic"""
        yaml_content = """
id: conditional-test
name: Conditional Test
description: Test conditional branching
steps:
  - id: set_value
    type: wait
    name: Set Value
    timeout: 0
  - id: check
    type: conditional
    name: Check Value
    condition:
      field: step_set_value.waited
      operator: "=="
      value: 0
    then_steps:
      - id: then_step
        type: wait
        name: Then Branch
        timeout: 1
    else_steps:
      - id: else_step
        type: wait
        name: Else Branch
        timeout: 2
"""
        workflow = WorkflowParser.parse(yaml_content)
        
        # Execute workflow
        execution = await self.engine.execute_workflow(workflow)
        
        self.assertEqual(execution.state, WorkflowState.COMPLETED)
        # Should have executed the "then" branch
        self.assertIn("step_set_value", execution.context)
    
    def test_execution_serialization(self):
        """Test saving and loading workflow execution"""
        execution = WorkflowExecution(
            workflow_id="test-workflow",
            execution_id="test-exec-1",
            state=WorkflowState.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        
        # Add step execution
        step_exec = StepExecution(
            step_id="step1",
            state=StepState.COMPLETED,
            output={"result": "success"}
        )
        execution.step_executions["step1"] = step_exec
        
        # Save execution
        asyncio.run(self.engine._save_execution(execution))
        
        # Load execution
        loaded = asyncio.run(self.engine.load_execution("test-exec-1"))
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.workflow_id, "test-workflow")
        self.assertEqual(loaded.state, WorkflowState.COMPLETED)
        self.assertIn("step1", loaded.step_executions)
        self.assertEqual(loaded.step_executions["step1"].output["result"], "success")
    
    def test_get_execution_status(self):
        """Test getting workflow execution status"""
        execution = WorkflowExecution(
            workflow_id="test-workflow",
            execution_id="test-exec-1",
            state=WorkflowState.RUNNING,
            started_at=datetime.now()
        )
        
        # Add to engine's executions
        self.engine.executions["test-exec-1"] = execution
        
        # Get status
        status = self.engine.get_execution_status("test-exec-1")
        
        self.assertIsNotNone(status)
        self.assertEqual(status["execution_id"], "test-exec-1")
        self.assertEqual(status["workflow_id"], "test-workflow")
        self.assertEqual(status["state"], WorkflowState.RUNNING)
        
        # Non-existent execution
        status = self.engine.get_execution_status("non-existent")
        self.assertIsNone(status)


class TestAgentPool(unittest.TestCase):
    """Test agent pool functionality"""
    
    @unittest.skipIf(not os.path.exists("../agent.py"), "Requires Agent-Zero components")
    async def test_agent_allocation(self):
        """Test agent allocation and release"""
        pool = AgentPool(max_agents=2)
        
        # Get agent for role
        agent1 = await pool.get_agent("developer")
        self.assertIsNotNone(agent1)
        self.assertIn("developer", pool.allocated_agents)
        
        # Get same role should return same agent
        agent1_again = await pool.get_agent("developer")
        self.assertEqual(agent1, agent1_again)
        
        # Get different role
        agent2 = await pool.get_agent("qa_engineer")
        self.assertIsNotNone(agent2)
        self.assertIn("qa_engineer", pool.allocated_agents)
        
        # Release agent
        await pool.release_agent("developer")
        self.assertNotIn("developer", pool.allocated_agents)
        self.assertEqual(len(pool.available_agents), 1)
        
        # Release all
        await pool.release_all()
        self.assertEqual(len(pool.allocated_agents), 0)


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == "__main__":
    # Run tests
    unittest.main()