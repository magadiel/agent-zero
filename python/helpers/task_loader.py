"""
BMAD Task Loader Module

This module provides functionality to load, parse, and validate BMAD-style task definitions.
It supports YAML-based task files with sequential execution steps, context gathering,
and dependency management.
"""

import os
import yaml
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
from datetime import datetime


@dataclass
class TaskStep:
    """Represents a single step in a task execution sequence."""
    id: str
    name: str
    description: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    requires: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    validation: Optional[Dict[str, Any]] = None
    timeout: int = 300  # seconds
    retries: int = 0
    optional: bool = False
    
    def to_dict(self) -> Dict:
        """Convert step to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'action': self.action,
            'params': self.params,
            'requires': self.requires,
            'produces': self.produces,
            'validation': self.validation,
            'timeout': self.timeout,
            'retries': self.retries,
            'optional': self.optional
        }


@dataclass 
class TaskDependency:
    """Represents a task dependency (template, checklist, data source)."""
    type: str  # 'template', 'checklist', 'data', 'workflow'
    name: str
    path: Optional[str] = None
    lazy_load: bool = True
    required: bool = True
    content: Optional[Any] = None
    
    def load(self, base_path: str = None) -> Any:
        """Load the dependency content."""
        if self.content is not None:
            return self.content
            
        if not self.path:
            return None
            
        full_path = Path(base_path) / self.path if base_path else Path(self.path)
        
        if not full_path.exists():
            if self.required:
                raise FileNotFoundError(f"Required dependency not found: {full_path}")
            return None
            
        with open(full_path, 'r') as f:
            if full_path.suffix in ['.yaml', '.yml']:
                self.content = yaml.safe_load(f)
            elif full_path.suffix == '.json':
                self.content = json.load(f)
            else:
                self.content = f.read()
                
        return self.content


@dataclass
class TaskContext:
    """Context information gathered during task execution."""
    sources: Dict[str, str] = field(default_factory=dict)  # source_name -> content
    citations: List[Dict[str, str]] = field(default_factory=list)  # List of citations
    artifacts: Dict[str, Any] = field(default_factory=dict)  # Generated artifacts
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def add_source(self, name: str, content: str, citation: Optional[Dict] = None):
        """Add a source with optional citation."""
        self.sources[name] = content
        if citation:
            citation['source'] = name
            citation['timestamp'] = datetime.now().isoformat()
            self.citations.append(citation)
    
    def get_source(self, name: str) -> Optional[str]:
        """Retrieve a source by name."""
        return self.sources.get(name)
    
    def add_artifact(self, name: str, content: Any):
        """Add a generated artifact."""
        self.artifacts[name] = content
    
    def to_dict(self) -> Dict:
        """Convert context to dictionary."""
        return {
            'sources': self.sources,
            'citations': self.citations,
            'artifacts': self.artifacts,
            'metadata': self.metadata
        }


@dataclass
class BMADTask:
    """Represents a complete BMAD task definition."""
    id: str
    name: str
    description: str
    category: str  # 'analysis', 'creation', 'validation', 'execution'
    sequential: bool = True
    gather_context: bool = True
    cite_sources: bool = True
    steps: List[TaskStep] = field(default_factory=list)
    dependencies: List[TaskDependency] = field(default_factory=list)
    validation: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Validate the task structure and return any issues."""
        issues = []
        
        # Check required fields
        if not self.id:
            issues.append("Task ID is required")
        if not self.name:
            issues.append("Task name is required")
        if not self.steps:
            issues.append("Task must have at least one step")
            
        # Validate steps
        step_ids = set()
        for step in self.steps:
            if step.id in step_ids:
                issues.append(f"Duplicate step ID: {step.id}")
            step_ids.add(step.id)
            
            # Check step dependencies
            for req in step.requires:
                if req not in step_ids:
                    issues.append(f"Step {step.id} requires unknown step: {req}")
        
        # Validate dependencies
        for dep in self.dependencies:
            if dep.type not in ['template', 'checklist', 'data', 'workflow']:
                issues.append(f"Invalid dependency type: {dep.type}")
        
        return issues
    
    def get_dependency(self, name: str, dep_type: Optional[str] = None) -> Optional[TaskDependency]:
        """Get a specific dependency by name and optionally type."""
        for dep in self.dependencies:
            if dep.name == name and (dep_type is None or dep.type == dep_type):
                return dep
        return None
    
    def to_dict(self) -> Dict:
        """Convert task to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name, 
            'description': self.description,
            'category': self.category,
            'sequential': self.sequential,
            'gather_context': self.gather_context,
            'cite_sources': self.cite_sources,
            'steps': [step.to_dict() for step in self.steps],
            'dependencies': [
                {
                    'type': dep.type,
                    'name': dep.name,
                    'path': dep.path,
                    'lazy_load': dep.lazy_load,
                    'required': dep.required
                }
                for dep in self.dependencies
            ],
            'validation': self.validation,
            'metadata': self.metadata
        }


class TaskLoader:
    """Loads and manages BMAD task definitions."""
    
    def __init__(self, base_path: str = None):
        """
        Initialize the task loader.
        
        Args:
            base_path: Base path for resolving relative paths in tasks
        """
        self.base_path = base_path or os.getcwd()
        self.cache: Dict[str, BMADTask] = {}
        
    def load_task(self, task_path: str, use_cache: bool = True) -> BMADTask:
        """
        Load a task from a YAML file.
        
        Args:
            task_path: Path to the task YAML file
            use_cache: Whether to use cached tasks
            
        Returns:
            Loaded BMADTask instance
        """
        # Generate cache key
        cache_key = self._get_cache_key(task_path)
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        # Load task file
        full_path = Path(self.base_path) / task_path if not Path(task_path).is_absolute() else Path(task_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"Task file not found: {full_path}")
        
        with open(full_path, 'r') as f:
            task_data = yaml.safe_load(f)
        
        # Parse task
        task = self._parse_task(task_data)
        
        # Validate task
        issues = task.validate()
        if issues:
            raise ValueError(f"Task validation failed: {', '.join(issues)}")
        
        # Cache task
        if use_cache:
            self.cache[cache_key] = task
        
        return task
    
    def load_task_from_dict(self, task_data: Dict) -> BMADTask:
        """
        Load a task from a dictionary.
        
        Args:
            task_data: Task definition as dictionary
            
        Returns:
            Loaded BMADTask instance
        """
        task = self._parse_task(task_data)
        
        # Validate task
        issues = task.validate()
        if issues:
            raise ValueError(f"Task validation failed: {', '.join(issues)}")
        
        return task
    
    def _parse_task(self, data: Dict) -> BMADTask:
        """Parse task data into BMADTask instance."""
        # Parse steps
        steps = []
        for step_data in data.get('steps', []):
            step = TaskStep(
                id=step_data.get('id', ''),
                name=step_data.get('name', ''),
                description=step_data.get('description', ''),
                action=step_data.get('action', ''),
                params=step_data.get('params', {}),
                requires=step_data.get('requires', []),
                produces=step_data.get('produces', []),
                validation=step_data.get('validation'),
                timeout=step_data.get('timeout', 300),
                retries=step_data.get('retries', 0),
                optional=step_data.get('optional', False)
            )
            steps.append(step)
        
        # Parse dependencies
        dependencies = []
        for dep_data in data.get('dependencies', []):
            dep = TaskDependency(
                type=dep_data.get('type', ''),
                name=dep_data.get('name', ''),
                path=dep_data.get('path'),
                lazy_load=dep_data.get('lazy_load', True),
                required=dep_data.get('required', True)
            )
            dependencies.append(dep)
        
        # Create task
        task = BMADTask(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            category=data.get('category', 'execution'),
            sequential=data.get('sequential', True),
            gather_context=data.get('gather_context', True),
            cite_sources=data.get('cite_sources', True),
            steps=steps,
            dependencies=dependencies,
            validation=data.get('validation'),
            metadata=data.get('metadata', {})
        )
        
        return task
    
    def load_dependencies(self, task: BMADTask, lazy: bool = True) -> Dict[str, Any]:
        """
        Load all dependencies for a task.
        
        Args:
            task: The task to load dependencies for
            lazy: Whether to respect lazy loading flags
            
        Returns:
            Dictionary mapping dependency names to their content
        """
        loaded = {}
        
        for dep in task.dependencies:
            if not lazy or not dep.lazy_load:
                try:
                    content = dep.load(self.base_path)
                    if content is not None:
                        loaded[dep.name] = content
                except FileNotFoundError as e:
                    if dep.required:
                        raise
                    # Optional dependency not found, skip
                    
        return loaded
    
    def _get_cache_key(self, task_path: str) -> str:
        """Generate a cache key for a task path."""
        full_path = Path(self.base_path) / task_path if not Path(task_path).is_absolute() else Path(task_path)
        return hashlib.md5(str(full_path).encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the task cache."""
        self.cache.clear()
    
    def list_cached_tasks(self) -> List[str]:
        """List all cached task IDs."""
        return [task.id for task in self.cache.values()]


class TaskRegistry:
    """Registry for managing multiple tasks."""
    
    def __init__(self, loader: Optional[TaskLoader] = None):
        """
        Initialize the task registry.
        
        Args:
            loader: TaskLoader instance to use
        """
        self.loader = loader or TaskLoader()
        self.tasks: Dict[str, BMADTask] = {}
        
    def register_task(self, task: BMADTask):
        """Register a task in the registry."""
        self.tasks[task.id] = task
        
    def register_from_file(self, task_path: str):
        """Load and register a task from file."""
        task = self.loader.load_task(task_path)
        self.register_task(task)
        
    def get_task(self, task_id: str) -> Optional[BMADTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[str]:
        """List all registered task IDs."""
        return list(self.tasks.keys())
    
    def get_tasks_by_category(self, category: str) -> List[BMADTask]:
        """Get all tasks in a specific category."""
        return [task for task in self.tasks.values() if task.category == category]
    
    def search_tasks(self, query: str) -> List[BMADTask]:
        """Search tasks by name or description."""
        query_lower = query.lower()
        results = []
        
        for task in self.tasks.values():
            if (query_lower in task.name.lower() or 
                query_lower in task.description.lower()):
                results.append(task)
                
        return results