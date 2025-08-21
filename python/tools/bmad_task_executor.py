"""
BMAD Task Executor Tool

This tool executes BMAD-style tasks with sequential step execution, context gathering,
source citation tracking, and comprehensive validation.
"""

import os
import asyncio
import time
import traceback
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import yaml

from python.helpers.tool import Tool, Response
from python.helpers.task_loader import (
    TaskLoader, BMADTask, TaskStep, TaskContext, TaskDependency
)
from python.helpers.print_style import PrintStyle


class BMADTaskExecutor(Tool):
    """
    Executes BMAD-style tasks with full support for sequential execution,
    context gathering, source citations, and validation.
    """
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute a BMAD task.
        
        Args:
            task_id: ID of registered task to execute
            task_path: Path to task YAML file
            task_data: Task definition as dictionary
            params: Parameters for task execution
            resume_from: Step ID to resume from
            dry_run: Whether to perform dry run only
            
        Returns:
            Response with execution results
        """
        # Initialize loader and context if not already done
        if not hasattr(self, 'loader'):
            self.loader = TaskLoader(base_path=os.getcwd())
        if not hasattr(self, 'context'):
            self.context = TaskContext()
            self.execution_log = []
            self.current_task = None
            self.interrupted = False
            
        try:
            # Load the task
            task = await self._load_task(kwargs)
            if not task:
                return Response(
                    message="Please provide task_id, task_path, or task_data",
                    break_loop=False
                )
            
            self.current_task = task
            
            # Validate task
            validation_issues = task.validate()
            if validation_issues:
                return Response(
                    message=f"Task validation failed: {', '.join(validation_issues)}",
                    break_loop=False
                )
            
            # Dry run mode
            if kwargs.get('dry_run', False):
                result = await self._dry_run(task)
                return Response(
                    message=f"Dry run completed: {json.dumps(result, indent=2)}",
                    break_loop=False
                )
            
            # Execute task
            result = await self._execute_task(
                task,
                params=kwargs.get('params', {}),
                resume_from=kwargs.get('resume_from')
            )
            
            return Response(
                message=f"Task {task.name} completed: {result.get('message', 'Success')}",
                break_loop=False
            )
            
        except Exception as e:
            return Response(
                message=f"Task execution failed: {str(e)}",
                break_loop=False
            )
    
    async def _load_task(self, kwargs: Dict) -> Optional[BMADTask]:
        """Load task from various sources."""
        if 'task_id' in kwargs:
            # Load from registry (would need to implement registry)
            return None  # Placeholder
            
        elif 'task_path' in kwargs:
            return self.loader.load_task(kwargs['task_path'])
            
        elif 'task_data' in kwargs:
            return self.loader.load_task_from_dict(kwargs['task_data'])
            
        return None
    
    async def _dry_run(self, task: BMADTask) -> Dict:
        """Perform dry run validation of task."""
        report = {
            "task_id": task.id,
            "task_name": task.name,
            "category": task.category,
            "sequential": task.sequential,
            "steps_count": len(task.steps),
            "dependencies_count": len(task.dependencies),
            "validation": "PASSED",
            "steps": [],
            "dependencies": []
        }
        
        # Analyze steps
        for step in task.steps:
            step_info = {
                "id": step.id,
                "name": step.name,
                "action": step.action,
                "optional": step.optional,
                "requires": step.requires,
                "produces": step.produces,
                "has_validation": step.validation is not None
            }
            report["steps"].append(step_info)
        
        # Check dependencies
        for dep in task.dependencies:
            dep_info = {
                "type": dep.type,
                "name": dep.name,
                "required": dep.required,
                "path": dep.path,
                "exists": False
            }
            
            if dep.path:
                full_path = Path(self.loader.base_path) / dep.path
                dep_info["exists"] = full_path.exists()
                
            report["dependencies"].append(dep_info)
        
        return report
    
    async def _execute_task(self, task: BMADTask, params: Dict, resume_from: Optional[str] = None) -> Dict:
        """Execute the task steps."""
        result = {
            "task_id": task.id,
            "task_name": task.name,
            "start_time": datetime.now().isoformat(),
            "params": params,
            "steps_executed": [],
            "context": None,
            "success": False,
            "message": ""
        }
        
        # Load dependencies if needed
        if task.dependencies:
            PrintStyle().print(f"Loading {len(task.dependencies)} dependencies...")
            dependencies = self.loader.load_dependencies(task, lazy=False)
            self.context.metadata['dependencies'] = dependencies
        
        # Gather initial context if required
        if task.gather_context:
            PrintStyle().print("Gathering task context...")
            await self._gather_context(task, params)
        
        # Execute steps
        steps_to_execute = task.steps
        if resume_from:
            # Find resume point
            resume_index = next(
                (i for i, s in enumerate(task.steps) if s.id == resume_from),
                0
            )
            steps_to_execute = task.steps[resume_index:]
            PrintStyle().print(f"Resuming from step: {resume_from}")
        
        if task.sequential:
            # Sequential execution
            for step in steps_to_execute:
                if self.interrupted:
                    result["message"] = "Task execution interrupted"
                    break
                    
                step_result = await self._execute_step(step, task)
                result["steps_executed"].append(step_result)
                
                if not step_result["success"] and not step.optional:
                    result["message"] = f"Step {step.id} failed: {step_result.get('error', 'Unknown error')}"
                    break
        else:
            # Parallel execution (respecting dependencies)
            step_results = await self._execute_parallel_steps(steps_to_execute, task)
            result["steps_executed"] = step_results
        
        # Perform final validation if specified
        if task.validation and not self.interrupted:
            PrintStyle().print("Performing task validation...")
            validation_result = await self._validate_task(task, result)
            result["validation"] = validation_result
            
        # Set final status
        all_success = all(
            s["success"] or s.get("optional", False) 
            for s in result["steps_executed"]
        )
        result["success"] = all_success and not self.interrupted
        
        if result["success"]:
            result["message"] = "Task completed successfully"
        
        # Add context to result
        result["context"] = self.context.to_dict()
        result["end_time"] = datetime.now().isoformat()
        
        return result
    
    async def _gather_context(self, task: BMADTask, params: Dict):
        """Gather initial context for task execution."""
        # This would integrate with agent's knowledge base and memory
        # For now, we'll add some placeholder context
        
        # Add task metadata as context
        self.context.add_source(
            "task_definition",
            json.dumps(task.to_dict(), indent=2),
            {"type": "internal", "description": "Task definition"}
        )
        
        # Add parameters as context
        if params:
            self.context.add_source(
                "task_params",
                json.dumps(params, indent=2),
                {"type": "input", "description": "Task parameters"}
            )
        
        # In real implementation, would gather from:
        # - Agent's memory/knowledge base
        # - Related documents
        # - Previous task executions
        # - External sources
    
    async def _execute_step(self, step: TaskStep, task: BMADTask) -> Dict:
        """Execute a single task step."""
        step_result = {
            "step_id": step.id,
            "step_name": step.name,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "optional": step.optional,
            "output": None,
            "error": None
        }
        
        PrintStyle().print(f"Executing step: {step.name}")
        
        try:
            # Check requirements
            for req in step.requires:
                if req not in [s["step_id"] for s in self.execution_log if s.get("success")]:
                    raise ValueError(f"Required step {req} not completed")
            
            # Execute action with retries
            max_attempts = step.retries + 1
            for attempt in range(max_attempts):
                try:
                    output = await self._execute_action(step.action, step.params, step.timeout)
                    step_result["output"] = output
                    
                    # Perform step validation if specified
                    if step.validation:
                        if not await self._validate_step(step, output):
                            raise ValueError("Step validation failed")
                    
                    step_result["success"] = True
                    break
                    
                except Exception as e:
                    if attempt < max_attempts - 1:
                        PrintStyle().print(f"Attempt {attempt + 1} failed, retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise
            
            # Track produced artifacts
            for artifact_name in step.produces:
                self.context.add_artifact(artifact_name, output)
            
            # Add source citation if required
            if task.cite_sources and output:
                self.context.add_source(
                    f"step_{step.id}_output",
                    str(output),
                    {
                        "type": "step_output",
                        "step_id": step.id,
                        "step_name": step.name
                    }
                )
            
        except Exception as e:
            step_result["error"] = str(e)
            PrintStyle().print(f"Step {step.id} failed: {str(e)}")
            
        step_result["end_time"] = datetime.now().isoformat()
        self.execution_log.append(step_result)
        
        return step_result
    
    async def _execute_parallel_steps(self, steps: List[TaskStep], task: BMADTask) -> List[Dict]:
        """Execute steps in parallel, respecting dependencies."""
        # Build dependency graph and execute in topological order
        # This is a simplified version - full implementation would use proper graph algorithms
        
        completed = set()
        results = []
        
        while len(completed) < len(steps):
            # Find steps that can be executed
            executable = []
            for step in steps:
                if step.id not in completed:
                    # Check if all dependencies are satisfied
                    if all(req in completed for req in step.requires):
                        executable.append(step)
            
            if not executable:
                # No steps can be executed - circular dependency or error
                break
            
            # Execute available steps in parallel
            tasks = [self._execute_step(step, task) for step in executable]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for step, result in zip(executable, step_results):
                if isinstance(result, Exception):
                    result = {
                        "step_id": step.id,
                        "step_name": step.name,
                        "success": False,
                        "error": str(result)
                    }
                results.append(result)
                completed.add(step.id)
        
        return results
    
    async def _execute_action(self, action: str, params: Dict, timeout: int) -> Any:
        """Execute a specific action."""
        # This would integrate with the agent's tool system
        # For now, we'll simulate different action types
        
        if action == "gather_data":
            # Simulate data gathering
            await asyncio.sleep(0.5)
            return {"data": "gathered", "params": params}
            
        elif action == "process":
            # Simulate processing
            await asyncio.sleep(0.3)
            return {"processed": True, "input": params}
            
        elif action == "validate":
            # Simulate validation
            await asyncio.sleep(0.2)
            return {"valid": True, "checked": params}
            
        elif action == "generate":
            # Simulate generation
            await asyncio.sleep(0.4)
            return {"generated": "output", "from": params}
            
        elif action == "tool":
            # Execute an agent tool
            tool_name = params.get("tool")
            tool_params = params.get("params", {})
            
            # Find and execute tool
            if hasattr(self.agent, 'tools'):
                for tool in self.agent.tools:
                    if tool.name == tool_name:
                        result = await tool.execute(**tool_params)
                        return result.message
            
            return {"error": f"Tool {tool_name} not found"}
            
        else:
            # Unknown action
            return {"action": action, "params": params, "executed": True}
    
    async def _validate_step(self, step: TaskStep, output: Any) -> bool:
        """Validate step output."""
        if not step.validation:
            return True
            
        validation = step.validation
        
        # Check output structure
        if "required_fields" in validation:
            if not isinstance(output, dict):
                return False
            for field in validation["required_fields"]:
                if field not in output:
                    return False
        
        # Check output values
        if "conditions" in validation:
            for condition in validation["conditions"]:
                # Simple condition checking
                # Full implementation would support complex conditions
                if not self._check_condition(output, condition):
                    return False
        
        return True
    
    async def _validate_task(self, task: BMADTask, result: Dict) -> Dict:
        """Perform final task validation."""
        validation_result = {
            "performed": True,
            "passed": False,
            "checks": []
        }
        
        if not task.validation:
            validation_result["passed"] = True
            return validation_result
        
        # Check required artifacts
        if "required_artifacts" in task.validation:
            for artifact in task.validation["required_artifacts"]:
                check = {
                    "type": "artifact",
                    "name": artifact,
                    "passed": artifact in self.context.artifacts
                }
                validation_result["checks"].append(check)
        
        # Check success criteria
        if "success_criteria" in task.validation:
            for criterion in task.validation["success_criteria"]:
                check = {
                    "type": "criterion",
                    "description": criterion.get("description", ""),
                    "passed": self._evaluate_criterion(criterion, result)
                }
                validation_result["checks"].append(check)
        
        # Overall validation status
        validation_result["passed"] = all(
            check["passed"] for check in validation_result["checks"]
        )
        
        return validation_result
    
    def _check_condition(self, output: Any, condition: Dict) -> bool:
        """Check a simple condition against output."""
        # Simplified condition checking
        # Full implementation would support complex expressions
        
        field = condition.get("field")
        operator = condition.get("operator", "equals")
        value = condition.get("value")
        
        if field and isinstance(output, dict):
            actual = output.get(field)
            
            if operator == "equals":
                return actual == value
            elif operator == "not_equals":
                return actual != value
            elif operator == "contains":
                return value in str(actual)
            elif operator == "exists":
                return field in output
        
        return True
    
    def _evaluate_criterion(self, criterion: Dict, result: Dict) -> bool:
        """Evaluate a success criterion."""
        # Simplified criterion evaluation
        criterion_type = criterion.get("type", "")
        
        if criterion_type == "all_steps_success":
            return all(s["success"] for s in result["steps_executed"])
            
        elif criterion_type == "step_success":
            step_id = criterion.get("step_id")
            return any(
                s["step_id"] == step_id and s["success"]
                for s in result["steps_executed"]
            )
            
        elif criterion_type == "artifact_exists":
            artifact = criterion.get("artifact")
            return artifact in self.context.artifacts
            
        return True
    
    def interrupt(self):
        """Interrupt task execution."""
        self.interrupted = True
        PrintStyle().print("Task execution interrupted by user")
    
    def get_execution_log(self) -> List[Dict]:
        """Get the execution log."""
        if not hasattr(self, 'execution_log'):
            self.execution_log = []
        return self.execution_log
    
    def get_context(self) -> TaskContext:
        """Get the current task context."""
        if not hasattr(self, 'context'):
            self.context = TaskContext()
        return self.context
    
    def reset(self):
        """Reset the executor state."""
        self.context = TaskContext()
        self.execution_log = []
        self.current_task = None
        self.interrupted = False