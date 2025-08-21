"""
Workflow Orchestration Engine for Agent-Zero

This module provides the core workflow execution engine that orchestrates
multi-agent workflows, manages state, handles conditional branching,
and coordinates document handoffs between agents.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

from coordination.workflow_parser import (
    WorkflowDefinition, 
    WorkflowStep, 
    WorkflowState,
    StepType,
    WorkflowCondition
)

# Import Agent-Zero components
from agent import Agent, AgentContext, UserMessage
from initialize import initialize_agent
from python.helpers.files import get_abs_path, make_dirs, read_file, write_file
from python.helpers.print_style import PrintStyle
from python.tools.call_subordinate import Delegation


class StepState(str, Enum):
    """States of a workflow step execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class StepExecution:
    """Tracks execution state of a workflow step"""
    step_id: str
    state: StepState = StepState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    agent_id: Optional[str] = None
    documents_created: List[str] = field(default_factory=list)
    documents_used: List[str] = field(default_factory=list)
    retry_count: int = 0


@dataclass
class WorkflowExecution:
    """Tracks overall workflow execution state"""
    workflow_id: str
    execution_id: str
    state: WorkflowState = WorkflowState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    step_executions: Dict[str, StepExecution] = field(default_factory=dict)
    documents: Dict[str, str] = field(default_factory=dict)  # document_name -> path
    agents: Dict[str, Agent] = field(default_factory=dict)  # agent_role -> Agent instance
    error: Optional[str] = None


class DocumentManager:
    """Manages document creation, storage, and handoffs between agents"""
    
    def __init__(self, base_path: str = "tmp/workflows/documents"):
        self.base_path = get_abs_path(base_path)
        make_dirs(self.base_path)
    
    def save_document(self, workflow_id: str, doc_name: str, content: str) -> str:
        """
        Save a document and return its path
        
        Args:
            workflow_id: ID of the workflow
            doc_name: Name of the document
            content: Document content
            
        Returns:
            Path to saved document
        """
        doc_path = os.path.join(self.base_path, workflow_id, f"{doc_name}")
        make_dirs(doc_path)
        write_file(doc_path, content)
        return doc_path
    
    def load_document(self, doc_path: str) -> str:
        """
        Load a document from path
        
        Args:
            doc_path: Path to document
            
        Returns:
            Document content
        """
        if os.path.exists(doc_path):
            return read_file(doc_path)
        raise FileNotFoundError(f"Document not found: {doc_path}")
    
    def document_exists(self, doc_path: str) -> bool:
        """Check if a document exists"""
        return os.path.exists(doc_path)


class AgentPool:
    """Manages a pool of agents for workflow execution"""
    
    def __init__(self, max_agents: int = 5):
        self.max_agents = max_agents
        self.available_agents: List[Agent] = []
        self.allocated_agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
        self.printer = PrintStyle(italic=True, font_color="blue", padding=False)
    
    async def get_agent(self, role: str, profile: Optional[str] = None, context: Optional[AgentContext] = None) -> Agent:
        """
        Get an agent for the specified role
        
        Args:
            role: Role/profile of the agent
            profile: Agent profile to use
            context: Agent context to use
            
        Returns:
            Agent instance
        """
        async with self._lock:
            # Check if we already have an agent for this role
            if role in self.allocated_agents:
                return self.allocated_agents[role]
            
            # Try to reuse an available agent
            if self.available_agents:
                agent = self.available_agents.pop(0)
                self.printer.print(f"Reusing agent for role: {role}")
            else:
                # Create a new agent
                config = initialize_agent()
                if profile:
                    config.profile = profile
                
                # Create new context if not provided
                if not context:
                    context = AgentContext(config, id=str(uuid.uuid4()), name=f"workflow_agent_{role}")
                
                agent = Agent(0, config, context)
                self.printer.print(f"Created new agent for role: {role}")
            
            # Allocate agent to role
            self.allocated_agents[role] = agent
            return agent
    
    async def release_agent(self, role: str):
        """
        Release an agent back to the pool
        
        Args:
            role: Role of the agent to release
        """
        async with self._lock:
            if role in self.allocated_agents:
                agent = self.allocated_agents.pop(role)
                if len(self.available_agents) < self.max_agents:
                    self.available_agents.append(agent)
                    self.printer.print(f"Released agent for role: {role}")
    
    async def release_all(self):
        """Release all allocated agents"""
        async with self._lock:
            for role in list(self.allocated_agents.keys()):
                agent = self.allocated_agents.pop(role)
                if len(self.available_agents) < self.max_agents:
                    self.available_agents.append(agent)
            self.printer.print("Released all agents")


class WorkflowEngine:
    """Main workflow execution engine"""
    
    def __init__(self, 
                 max_parallel_agents: int = 5,
                 workflow_storage_path: str = "tmp/workflows"):
        self.max_parallel_agents = max_parallel_agents
        self.workflow_storage_path = get_abs_path(workflow_storage_path)
        self.document_manager = DocumentManager()
        self.agent_pool = AgentPool(max_parallel_agents)
        self.printer = PrintStyle(italic=True, font_color="green", padding=False)
        self.executions: Dict[str, WorkflowExecution] = {}
        
        # Create storage directories
        make_dirs(self.workflow_storage_path)
    
    async def execute_workflow(self, 
                              workflow: WorkflowDefinition,
                              initial_context: Optional[Dict[str, Any]] = None,
                              execution_id: Optional[str] = None) -> WorkflowExecution:
        """
        Execute a workflow
        
        Args:
            workflow: Workflow definition to execute
            initial_context: Initial context for workflow execution
            execution_id: Optional execution ID (will be generated if not provided)
            
        Returns:
            WorkflowExecution object with results
        """
        # Create execution tracking
        execution_id = execution_id or str(uuid.uuid4())
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            execution_id=execution_id,
            state=WorkflowState.RUNNING,
            started_at=datetime.now(timezone.utc),
            context=initial_context or {}
        )
        
        self.executions[execution_id] = execution
        
        self.printer.print(f"Starting workflow execution: {workflow.name} ({execution_id})")
        
        try:
            # Execute workflow steps sequentially
            for step in workflow.steps:
                if execution.state != WorkflowState.RUNNING:
                    break
                
                await self._execute_step(step, workflow, execution)
            
            # Mark workflow as completed if still running
            if execution.state == WorkflowState.RUNNING:
                execution.state = WorkflowState.COMPLETED
                execution.completed_at = datetime.now(timezone.utc)
                self.printer.print(f"Workflow completed successfully: {workflow.name}")
            
        except Exception as e:
            execution.state = WorkflowState.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            self.printer.print(f"Workflow failed: {workflow.name} - {str(e)}")
            
            # Clean up agents
            await self.agent_pool.release_all()
            
            raise
        
        finally:
            # Save execution state
            await self._save_execution(execution)
            
            # Release all agents
            await self.agent_pool.release_all()
        
        return execution
    
    async def _execute_step(self, 
                           step: WorkflowStep,
                           workflow: WorkflowDefinition,
                           execution: WorkflowExecution) -> StepExecution:
        """
        Execute a single workflow step
        
        Args:
            step: Step to execute
            workflow: Parent workflow definition
            execution: Workflow execution context
            
        Returns:
            StepExecution object with results
        """
        # Create step execution tracking
        step_exec = StepExecution(
            step_id=step.id,
            state=StepState.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        execution.step_executions[step.id] = step_exec
        
        self.printer.print(f"Executing step: {step.name} (type: {step.type})")
        
        try:
            # Execute based on step type
            if step.type == StepType.AGENT_TASK:
                await self._execute_agent_task(step, workflow, execution, step_exec)
            elif step.type == StepType.CONDITIONAL:
                await self._execute_conditional(step, workflow, execution, step_exec)
            elif step.type == StepType.PARALLEL:
                await self._execute_parallel(step, workflow, execution, step_exec)
            elif step.type == StepType.DOCUMENT_CREATE:
                await self._execute_document_create(step, workflow, execution, step_exec)
            elif step.type == StepType.QUALITY_GATE:
                await self._execute_quality_gate(step, workflow, execution, step_exec)
            elif step.type == StepType.WAIT:
                await self._execute_wait(step, workflow, execution, step_exec)
            else:
                raise ValueError(f"Unknown step type: {step.type}")
            
            # Mark step as completed
            step_exec.state = StepState.COMPLETED
            step_exec.completed_at = datetime.now(timezone.utc)
            
            # Update execution context with step outputs
            execution.context[f"step_{step.id}"] = step_exec.output
            
            self.printer.print(f"Step completed: {step.name}")
            
        except Exception as e:
            step_exec.state = StepState.FAILED
            step_exec.error = str(e)
            step_exec.completed_at = datetime.now(timezone.utc)
            
            self.printer.print(f"Step failed: {step.name} - {str(e)}")
            
            # Handle step failure based on optional flag
            if not step.optional:
                execution.state = WorkflowState.FAILED
                execution.error = f"Step {step.name} failed: {str(e)}"
                raise
            else:
                # Mark as skipped and continue
                step_exec.state = StepState.SKIPPED
                self.printer.print(f"Optional step failed, continuing: {step.name}")
        
        return step_exec
    
    async def _execute_agent_task(self, 
                                 step: WorkflowStep,
                                 workflow: WorkflowDefinition,
                                 execution: WorkflowExecution,
                                 step_exec: StepExecution):
        """Execute an agent task step"""
        # Get agent for this role
        agent_profile = step.agent or "default"
        agent_config = workflow.agents.get(agent_profile, {})
        
        agent = await self.agent_pool.get_agent(
            role=agent_profile,
            profile=agent_config.get('profile', agent_profile)
        )
        
        step_exec.agent_id = agent_profile
        
        # Prepare task prompt with context
        task_prompt = step.task or step.name
        
        # Add required documents to prompt
        if step.requires:
            task_prompt += "\n\n## Required Documents:\n"
            for doc_name in step.requires:
                if doc_name in execution.documents:
                    doc_path = execution.documents[doc_name]
                    doc_content = self.document_manager.load_document(doc_path)
                    task_prompt += f"\n### {doc_name}:\n{doc_content}\n"
                    step_exec.documents_used.append(doc_name)
        
        # Add inputs to prompt
        if step.inputs:
            task_prompt += "\n\n## Inputs:\n"
            for key, value in step.inputs.items():
                # Resolve value from context if it's a reference
                if isinstance(value, str) and value.startswith("$"):
                    context_key = value[1:]  # Remove $ prefix
                    value = execution.context.get(context_key, value)
                task_prompt += f"- {key}: {value}\n"
        
        # Execute agent task
        self.printer.print(f"Agent {agent_profile} executing: {task_prompt[:100]}...")
        
        # Add message to agent
        agent.hist_add_user_message(UserMessage(
            message=task_prompt,
            system_message=[f"You are executing workflow step: {step.name}"],
            attachments=[]
        ))
        
        # Run agent monologue
        result = await agent.monologue()
        
        # Store output
        step_exec.output = {
            "result": result,
            "agent": agent_profile,
            "task": step.task
        }
        
        # Handle document creation if specified
        if step.creates:
            doc_path = self.document_manager.save_document(
                workflow_id=execution.workflow_id,
                doc_name=step.creates,
                content=result
            )
            execution.documents[step.creates] = doc_path
            step_exec.documents_created.append(step.creates)
            self.printer.print(f"Created document: {step.creates}")
    
    async def _execute_conditional(self,
                                  step: WorkflowStep,
                                  workflow: WorkflowDefinition,
                                  execution: WorkflowExecution,
                                  step_exec: StepExecution):
        """Execute a conditional step"""
        if not step.condition:
            raise ValueError(f"Conditional step {step.id} has no condition")
        
        # Evaluate condition
        condition_result = step.condition.evaluate(execution.context)
        
        self.printer.print(f"Condition evaluated: {condition_result}")
        step_exec.output["condition_result"] = condition_result
        
        # Execute appropriate branch
        if condition_result and step.then_steps:
            self.printer.print(f"Executing THEN branch with {len(step.then_steps)} steps")
            for sub_step in step.then_steps:
                await self._execute_step(sub_step, workflow, execution)
        elif not condition_result and step.else_steps:
            self.printer.print(f"Executing ELSE branch with {len(step.else_steps)} steps")
            for sub_step in step.else_steps:
                await self._execute_step(sub_step, workflow, execution)
    
    async def _execute_parallel(self,
                               step: WorkflowStep,
                               workflow: WorkflowDefinition,
                               execution: WorkflowExecution,
                               step_exec: StepExecution):
        """Execute parallel steps"""
        if not step.parallel_steps:
            return
        
        self.printer.print(f"Executing {len(step.parallel_steps)} steps in parallel")
        
        # Create tasks for parallel execution
        tasks = []
        for sub_step in step.parallel_steps:
            task = asyncio.create_task(
                self._execute_step(sub_step, workflow, execution)
            )
            tasks.append(task)
        
        # Wait for all parallel tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for failures
        failures = [r for r in results if isinstance(r, Exception)]
        if failures and not workflow.allow_partial_success:
            raise failures[0]
        
        step_exec.output["parallel_results"] = [
            str(r) if isinstance(r, Exception) else "success" 
            for r in results
        ]
    
    async def _execute_document_create(self,
                                      step: WorkflowStep,
                                      workflow: WorkflowDefinition,
                                      execution: WorkflowExecution,
                                      step_exec: StepExecution):
        """Execute document creation step"""
        if not step.creates:
            raise ValueError(f"Document creation step {step.id} has no 'creates' field")
        
        # Prepare content from template or inputs
        content = ""
        
        if step.template:
            # Load template (simplified - real implementation would use template system)
            template_path = get_abs_path(f"templates/{step.template}")
            if os.path.exists(template_path):
                content = read_file(template_path)
        
        # Add inputs to content
        if step.inputs:
            for key, value in step.inputs.items():
                # Resolve value from context if it's a reference
                if isinstance(value, str) and value.startswith("$"):
                    context_key = value[1:]
                    value = execution.context.get(context_key, value)
                content = content.replace(f"{{{key}}}", str(value))
        
        # Save document
        doc_path = self.document_manager.save_document(
            workflow_id=execution.workflow_id,
            doc_name=step.creates,
            content=content
        )
        
        execution.documents[step.creates] = doc_path
        step_exec.documents_created.append(step.creates)
        step_exec.output["document"] = step.creates
        
        self.printer.print(f"Created document: {step.creates}")
    
    async def _execute_quality_gate(self,
                                   step: WorkflowStep,
                                   workflow: WorkflowDefinition,
                                   execution: WorkflowExecution,
                                   step_exec: StepExecution):
        """Execute quality gate step"""
        if not step.checklist:
            raise ValueError(f"Quality gate step {step.id} has no checklist")
        
        # Get agent to run checklist (could be specialized QA agent)
        agent = await self.agent_pool.get_agent(
            role="qa_engineer",
            profile="qa_engineer"
        )
        
        # Prepare checklist execution prompt
        prompt = f"Execute quality checklist: {step.checklist}\n\n"
        
        # Add required documents
        if step.requires:
            prompt += "## Documents to Review:\n"
            for doc_name in step.requires:
                if doc_name in execution.documents:
                    doc_path = execution.documents[doc_name]
                    doc_content = self.document_manager.load_document(doc_path)
                    prompt += f"\n### {doc_name}:\n{doc_content}\n"
        
        # Execute checklist
        agent.hist_add_user_message(UserMessage(
            message=prompt,
            system_message=["You are performing a quality gate check"],
            attachments=[]
        ))
        
        result = await agent.monologue()
        
        # Parse gate result (simplified - real implementation would use ChecklistExecutor)
        gate_result = "PASS"  # Default
        if "FAIL" in result.upper():
            gate_result = "FAIL"
        elif "CONCERNS" in result.upper():
            gate_result = "CONCERNS"
        
        step_exec.output = {
            "gate_result": gate_result,
            "checklist": step.checklist,
            "details": result
        }
        
        # Fail workflow if gate fails and not optional
        if gate_result == "FAIL" and not step.optional:
            raise ValueError(f"Quality gate failed: {step.checklist}")
        
        self.printer.print(f"Quality gate result: {gate_result}")
    
    async def _execute_wait(self,
                           step: WorkflowStep,
                           workflow: WorkflowDefinition,
                           execution: WorkflowExecution,
                           step_exec: StepExecution):
        """Execute wait step"""
        wait_time = step.timeout or 1
        self.printer.print(f"Waiting for {wait_time} seconds")
        await asyncio.sleep(wait_time)
        step_exec.output["waited"] = wait_time
    
    async def _save_execution(self, execution: WorkflowExecution):
        """Save workflow execution state to disk"""
        execution_path = os.path.join(
            self.workflow_storage_path,
            "executions",
            f"{execution.execution_id}.json"
        )
        
        make_dirs(execution_path)
        
        # Convert execution to serializable format
        execution_data = {
            "workflow_id": execution.workflow_id,
            "execution_id": execution.execution_id,
            "state": execution.state,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "context": execution.context,
            "documents": execution.documents,
            "error": execution.error,
            "step_executions": {
                step_id: {
                    "step_id": step_exec.step_id,
                    "state": step_exec.state,
                    "started_at": step_exec.started_at.isoformat() if step_exec.started_at else None,
                    "completed_at": step_exec.completed_at.isoformat() if step_exec.completed_at else None,
                    "output": step_exec.output,
                    "error": step_exec.error,
                    "agent_id": step_exec.agent_id,
                    "documents_created": step_exec.documents_created,
                    "documents_used": step_exec.documents_used,
                    "retry_count": step_exec.retry_count
                }
                for step_id, step_exec in execution.step_executions.items()
            }
        }
        
        write_file(execution_path, json.dumps(execution_data, indent=2))
        self.printer.print(f"Saved execution state: {execution_path}")
    
    async def load_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Load workflow execution state from disk"""
        execution_path = os.path.join(
            self.workflow_storage_path,
            "executions",
            f"{execution_id}.json"
        )
        
        if not os.path.exists(execution_path):
            return None
        
        execution_data = json.loads(read_file(execution_path))
        
        # Reconstruct execution object
        execution = WorkflowExecution(
            workflow_id=execution_data["workflow_id"],
            execution_id=execution_data["execution_id"],
            state=WorkflowState(execution_data["state"]),
            started_at=datetime.fromisoformat(execution_data["started_at"]) if execution_data["started_at"] else None,
            completed_at=datetime.fromisoformat(execution_data["completed_at"]) if execution_data["completed_at"] else None,
            context=execution_data["context"],
            documents=execution_data["documents"],
            error=execution_data["error"]
        )
        
        # Reconstruct step executions
        for step_id, step_data in execution_data["step_executions"].items():
            step_exec = StepExecution(
                step_id=step_data["step_id"],
                state=StepState(step_data["state"]),
                started_at=datetime.fromisoformat(step_data["started_at"]) if step_data["started_at"] else None,
                completed_at=datetime.fromisoformat(step_data["completed_at"]) if step_data["completed_at"] else None,
                output=step_data["output"],
                error=step_data["error"],
                agent_id=step_data["agent_id"],
                documents_created=step_data["documents_created"],
                documents_used=step_data["documents_used"],
                retry_count=step_data["retry_count"]
            )
            execution.step_executions[step_id] = step_exec
        
        return execution
    
    async def resume_workflow(self, execution_id: str) -> WorkflowExecution:
        """Resume a paused or failed workflow execution"""
        execution = await self.load_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # TODO: Implement workflow resumption logic
        # This would require loading the workflow definition,
        # finding the last completed step, and continuing from there
        
        raise NotImplementedError("Workflow resumption not yet implemented")
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow execution"""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            return {
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "state": execution.state,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "error": execution.error,
                "steps_completed": sum(1 for s in execution.step_executions.values() if s.state == StepState.COMPLETED),
                "steps_total": len(execution.step_executions)
            }
        return None