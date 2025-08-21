#!/usr/bin/env python3
"""
Load Testing Suite for Agile AI Company Framework

This module provides comprehensive load and stress testing to validate system
scalability, resource limits, and performance under high concurrent load.

Author: Agile AI Framework Team
Date: 2025-08-21
Version: 1.0.0
"""

import asyncio
import time
import psutil
import statistics
import json
import sys
import os
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import traceback
import gc
import signal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import framework components
try:
    from control.ethics_engine import EthicsEngine
    from control.safety_monitor import SafetyMonitor
    from control.resource_allocator import ResourceAllocator
    from control.audit_logger import AuditLogger
    from coordination.team_orchestrator import TeamOrchestrator
    from coordination.workflow_engine import WorkflowEngine
    from coordination.agent_pool import AgentPool
    from coordination.document_manager import DocumentManager
    from agile.sprint_manager import SprintManager
    from agile.product_backlog import ProductBacklog
    from metrics.performance_monitor import PerformanceMonitor
    from python.helpers.team_protocol import TeamProtocol
except ImportError as e:
    print(f"Warning: Some imports failed - {e}")
    print("Running in limited mode with available components")


@dataclass
class LoadTestResult:
    """Store load test results"""
    test_name: str
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    average_latency_ms: float
    peak_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LoadTestRunner:
    """Main load testing framework"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[LoadTestResult] = []
        self.stop_event = threading.Event()
        self.performance_monitor = None
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signal"""
        self.log("Received interrupt signal, shutting down gracefully...", "WARNING")
        self.stop_event.set()
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] [LOAD-{level}] {message}")
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        process = psutil.Process()
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': psutil.virtual_memory().available / (1024**3),
            'disk_io_read_mb': psutil.disk_io_counters().read_bytes / (1024**2) if hasattr(psutil.disk_io_counters(), 'read_bytes') else 0,
            'disk_io_write_mb': psutil.disk_io_counters().write_bytes / (1024**2) if hasattr(psutil.disk_io_counters(), 'write_bytes') else 0,
            'network_sent_mb': psutil.net_io_counters().bytes_sent / (1024**2),
            'network_recv_mb': psutil.net_io_counters().bytes_recv / (1024**2),
            'process_threads': process.num_threads(),
            'process_memory_mb': process.memory_info().rss / (1024**2)
        }
    
    # ============= Agent Spawn Load Test =============
    
    async def test_agent_spawn_load(self, 
                                   target_agents: int = 100,
                                   spawn_rate: int = 10,
                                   duration_seconds: int = 60) -> LoadTestResult:
        """Test system under heavy agent spawn load"""
        self.log(f"Starting agent spawn load test: {target_agents} agents, {spawn_rate}/sec for {duration_seconds}s")
        
        pool = AgentPool(initial_size=0)
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        
        async def spawn_agent(agent_id: int) -> Tuple[bool, float]:
            """Spawn a single agent and measure time"""
            try:
                op_start = time.perf_counter()
                agent = await pool.create_agent(
                    agent_id=f"load_agent_{agent_id}",
                    profile="default",
                    skills=["testing"]
                )
                op_end = time.perf_counter()
                latency = (op_end - op_start) * 1000
                return True, latency
            except Exception as e:
                errors.append(str(e))
                return False, 0
        
        # Resource monitoring
        initial_resources = self.get_system_resources()
        
        # Spawn agents at specified rate
        agents_spawned = 0
        spawn_interval = 1.0 / spawn_rate
        
        while agents_spawned < target_agents and not self.stop_event.is_set():
            if time.time() - start_time > duration_seconds:
                break
            
            # Spawn batch of agents
            batch_size = min(spawn_rate, target_agents - agents_spawned)
            tasks = [spawn_agent(agents_spawned + i) for i in range(batch_size)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, tuple):
                    success, latency = result
                    operations.append(success)
                    if latency > 0:
                        latencies.append(latency)
                else:
                    operations.append(False)
                    errors.append(str(result))
            
            agents_spawned += batch_size
            
            # Rate limiting
            await asyncio.sleep(spawn_interval)
            
            # Progress update
            if agents_spawned % 50 == 0:
                self.log(f"  Spawned {agents_spawned} agents...")
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        final_resources = self.get_system_resources()
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        result = LoadTestResult(
            test_name="Agent Spawn Load Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            resource_usage={
                'initial': initial_resources,
                'final': final_resources,
                'delta': {
                    'cpu_percent': final_resources['cpu_percent'] - initial_resources['cpu_percent'],
                    'memory_percent': final_resources['memory_percent'] - initial_resources['memory_percent']
                }
            },
            errors=errors[:10],  # Keep first 10 errors
            metadata={
                'target_agents': target_agents,
                'spawn_rate': spawn_rate,
                'actual_agents_spawned': agents_spawned
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Agent spawn load test completed: {successful}/{len(operations)} successful")
        return result
    
    # ============= Concurrent Team Operations Load Test =============
    
    async def test_concurrent_teams_load(self,
                                        num_teams: int = 20,
                                        team_size: int = 5,
                                        duration_seconds: int = 120) -> LoadTestResult:
        """Test concurrent team operations under load"""
        self.log(f"Starting concurrent teams load test: {num_teams} teams of {team_size} agents")
        
        orchestrator = TeamOrchestrator()
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        
        async def team_lifecycle(team_id: int) -> Tuple[bool, float]:
            """Complete team lifecycle: form, operate, dissolve"""
            try:
                op_start = time.perf_counter()
                
                # Form team
                team = await orchestrator.form_team(
                    mission=f"Load test mission {team_id}",
                    required_skills=['analysis', 'development'],
                    size=team_size
                )
                
                # Simulate team operations
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Update team status
                team.status = "performing"
                
                # More operations
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Dissolve team
                await orchestrator.dissolve_team(team.id)
                
                op_end = time.perf_counter()
                latency = (op_end - op_start) * 1000
                return True, latency
                
            except Exception as e:
                errors.append(f"Team {team_id}: {str(e)}")
                return False, 0
        
        # Resource monitoring
        initial_resources = self.get_system_resources()
        
        # Run concurrent team operations
        active_tasks = []
        teams_processed = 0
        
        while teams_processed < num_teams and not self.stop_event.is_set():
            if time.time() - start_time > duration_seconds:
                break
            
            # Launch new team
            task = asyncio.create_task(team_lifecycle(teams_processed))
            active_tasks.append(task)
            teams_processed += 1
            
            # Manage active tasks
            if len(active_tasks) >= 10:  # Limit concurrent teams
                done, pending = await asyncio.wait(
                    active_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    result = await task
                    if isinstance(result, tuple):
                        success, latency = result
                        operations.append(success)
                        if latency > 0:
                            latencies.append(latency)
                    active_tasks.remove(task)
            
            # Progress update
            if teams_processed % 5 == 0:
                self.log(f"  Processed {teams_processed} teams...")
        
        # Wait for remaining tasks
        if active_tasks:
            results = await asyncio.gather(*active_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, tuple):
                    success, latency = result
                    operations.append(success)
                    if latency > 0:
                        latencies.append(latency)
                else:
                    operations.append(False)
                    errors.append(str(result))
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        final_resources = self.get_system_resources()
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        result = LoadTestResult(
            test_name="Concurrent Teams Load Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            resource_usage={
                'initial': initial_resources,
                'final': final_resources,
                'delta': {
                    'cpu_percent': final_resources['cpu_percent'] - initial_resources['cpu_percent'],
                    'memory_percent': final_resources['memory_percent'] - initial_resources['memory_percent']
                }
            },
            errors=errors[:10],
            metadata={
                'num_teams': num_teams,
                'team_size': team_size,
                'teams_processed': teams_processed
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Concurrent teams test completed: {successful}/{len(operations)} successful")
        return result
    
    # ============= Workflow Execution Load Test =============
    
    async def test_workflow_execution_load(self,
                                          num_workflows: int = 50,
                                          concurrent_workflows: int = 10) -> LoadTestResult:
        """Test workflow execution under load"""
        self.log(f"Starting workflow execution load test: {num_workflows} workflows")
        
        engine = WorkflowEngine()
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        
        # Define test workflow
        test_workflow = {
            'name': 'load_test_workflow',
            'steps': [
                {
                    'id': 'analyze',
                    'agent': 'analyst',
                    'action': 'analyze_requirements',
                    'creates': 'requirements.md'
                },
                {
                    'id': 'design',
                    'agent': 'architect',
                    'action': 'create_design',
                    'requires': ['requirements.md'],
                    'creates': 'design.md'
                },
                {
                    'id': 'implement',
                    'agent': 'developer',
                    'action': 'implement_solution',
                    'requires': ['design.md'],
                    'creates': 'implementation.md'
                }
            ]
        }
        
        async def execute_workflow(workflow_id: int) -> Tuple[bool, float]:
            """Execute a single workflow"""
            try:
                op_start = time.perf_counter()
                
                workflow = engine.create_workflow({
                    **test_workflow,
                    'name': f"{test_workflow['name']}_{workflow_id}"
                })
                
                # Simulate execution
                for step in workflow.steps:
                    workflow.current_step = step['id']
                    workflow.state = 'executing'
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    workflow.completed_steps.append(step['id'])
                
                workflow.state = 'completed'
                
                op_end = time.perf_counter()
                latency = (op_end - op_start) * 1000
                return True, latency
                
            except Exception as e:
                errors.append(f"Workflow {workflow_id}: {str(e)}")
                return False, 0
        
        # Resource monitoring
        initial_resources = self.get_system_resources()
        
        # Execute workflows with concurrency limit
        semaphore = asyncio.Semaphore(concurrent_workflows)
        
        async def rate_limited_workflow(workflow_id: int):
            async with semaphore:
                return await execute_workflow(workflow_id)
        
        # Launch all workflows
        tasks = [rate_limited_workflow(i) for i in range(num_workflows)]
        
        # Process results as they complete
        for i, task in enumerate(asyncio.as_completed(tasks)):
            if self.stop_event.is_set():
                break
                
            try:
                result = await task
                if isinstance(result, tuple):
                    success, latency = result
                    operations.append(success)
                    if latency > 0:
                        latencies.append(latency)
            except Exception as e:
                operations.append(False)
                errors.append(str(e))
            
            # Progress update
            if (i + 1) % 10 == 0:
                self.log(f"  Completed {i + 1}/{num_workflows} workflows...")
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        final_resources = self.get_system_resources()
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        result = LoadTestResult(
            test_name="Workflow Execution Load Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            resource_usage={
                'initial': initial_resources,
                'final': final_resources
            },
            errors=errors[:10],
            metadata={
                'num_workflows': num_workflows,
                'concurrent_workflows': concurrent_workflows,
                'workflow_steps': len(test_workflow['steps'])
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Workflow load test completed: {successful}/{len(operations)} successful")
        return result
    
    # ============= Decision Validation Stress Test =============
    
    async def test_decision_validation_stress(self,
                                             num_decisions: int = 10000,
                                             concurrent_validators: int = 20) -> LoadTestResult:
        """Stress test the ethics engine with high decision volume"""
        self.log(f"Starting decision validation stress test: {num_decisions} decisions")
        
        ethics_engine = EthicsEngine()
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        
        # Generate test decisions
        decision_types = [
            {'action': 'data_processing', 'risk_level': 0.2},
            {'action': 'system_modification', 'risk_level': 0.5},
            {'action': 'external_communication', 'risk_level': 0.3},
            {'action': 'resource_allocation', 'risk_level': 0.4},
            {'action': 'user_interaction', 'risk_level': 0.1}
        ]
        
        async def validate_decision(decision_id: int) -> Tuple[bool, float]:
            """Validate a single decision"""
            try:
                decision = decision_types[decision_id % len(decision_types)].copy()
                decision.update({
                    'agent_id': f'stress_agent_{decision_id % 100}',
                    'timestamp': datetime.now().isoformat(),
                    'purpose': f'stress_test_{decision_id}'
                })
                
                op_start = time.perf_counter()
                result = await ethics_engine.validate_decision(decision)
                op_end = time.perf_counter()
                
                latency = (op_end - op_start) * 1000
                return result['approved'], latency
                
            except Exception as e:
                errors.append(f"Decision {decision_id}: {str(e)}")
                return False, 0
        
        # Resource monitoring
        initial_resources = self.get_system_resources()
        
        # Execute validations with concurrency limit
        semaphore = asyncio.Semaphore(concurrent_validators)
        
        async def rate_limited_validation(decision_id: int):
            async with semaphore:
                return await validate_decision(decision_id)
        
        # Launch all validations
        tasks = [rate_limited_validation(i) for i in range(num_decisions)]
        
        # Process in batches to avoid memory issues
        batch_size = 1000
        for batch_start in range(0, num_decisions, batch_size):
            if self.stop_event.is_set():
                break
                
            batch_end = min(batch_start + batch_size, num_decisions)
            batch_tasks = tasks[batch_start:batch_end]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, tuple):
                    success, latency = result
                    operations.append(success)
                    if latency > 0:
                        latencies.append(latency)
                else:
                    operations.append(False)
                    errors.append(str(result))
            
            self.log(f"  Processed {batch_end}/{num_decisions} decisions...")
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        final_resources = self.get_system_resources()
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        result = LoadTestResult(
            test_name="Decision Validation Stress Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            resource_usage={
                'initial': initial_resources,
                'final': final_resources
            },
            errors=errors[:10],
            metadata={
                'num_decisions': num_decisions,
                'concurrent_validators': concurrent_validators,
                'decision_types': len(decision_types)
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Decision validation stress test completed: {successful}/{len(operations)} approved")
        return result
    
    # ============= Resource Limit Test =============
    
    async def test_resource_limits(self) -> LoadTestResult:
        """Test system behavior at resource limits"""
        self.log("Starting resource limit test...")
        
        allocator = ResourceAllocator()
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        
        # Try to exhaust resources
        allocated_teams = []
        
        try:
            # Allocate resources until exhausted
            for i in range(100):  # Try to allocate for 100 teams
                try:
                    op_start = time.perf_counter()
                    
                    allocation = await allocator.allocate_resources(
                        team_id=f"limit_team_{i}",
                        requested_resources={
                            'cpu_cores': 4,
                            'memory_gb': 8,
                            'gpu_cores': 1
                        }
                    )
                    
                    op_end = time.perf_counter()
                    latency = (op_end - op_start) * 1000
                    
                    if allocation:
                        allocated_teams.append(f"limit_team_{i}")
                        operations.append(True)
                        latencies.append(latency)
                    else:
                        operations.append(False)
                        break
                        
                except Exception as e:
                    operations.append(False)
                    errors.append(f"Allocation {i}: {str(e)}")
                    break
            
            self.log(f"  Successfully allocated resources for {len(allocated_teams)} teams")
            
            # Test operations at limit
            self.log("  Testing operations at resource limit...")
            
            # Try additional allocations (should fail)
            for i in range(10):
                try:
                    allocation = await allocator.allocate_resources(
                        team_id=f"overflow_team_{i}",
                        requested_resources={'cpu_cores': 2, 'memory_gb': 4}
                    )
                    operations.append(allocation is not None)
                except Exception as e:
                    operations.append(False)
                    errors.append(f"Overflow {i}: {str(e)}")
            
            # Release some resources
            if allocated_teams:
                for team_id in allocated_teams[:5]:  # Release first 5
                    await allocator.release_resources(team_id)
                self.log("  Released resources for 5 teams")
            
            # Try allocation again (should succeed)
            for i in range(5):
                try:
                    allocation = await allocator.allocate_resources(
                        team_id=f"realloc_team_{i}",
                        requested_resources={'cpu_cores': 2, 'memory_gb': 4}
                    )
                    operations.append(allocation is not None)
                except Exception as e:
                    operations.append(False)
                    errors.append(f"Reallocation {i}: {str(e)}")
            
        finally:
            # Clean up all allocations
            for team_id in allocated_teams:
                try:
                    await allocator.release_resources(team_id)
                except:
                    pass
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        result = LoadTestResult(
            test_name="Resource Limit Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            errors=errors[:10],
            metadata={
                'max_teams_allocated': len(allocated_teams),
                'resource_exhaustion_detected': len(allocated_teams) < 100
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Resource limit test completed: {len(allocated_teams)} teams at limit")
        return result
    
    # ============= Sustained Load Test =============
    
    async def test_sustained_load(self, duration_minutes: int = 5) -> LoadTestResult:
        """Test system under sustained load for extended period"""
        self.log(f"Starting sustained load test for {duration_minutes} minutes...")
        
        operations = []
        errors = []
        latencies = []
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        
        # Components to test
        orchestrator = TeamOrchestrator()
        ethics_engine = EthicsEngine()
        
        # Monitoring
        initial_resources = self.get_system_resources()
        resource_samples = []
        
        async def continuous_operations():
            """Run continuous mixed operations"""
            operation_count = 0
            
            while time.time() - start_time < duration_seconds and not self.stop_event.is_set():
                # Mix of different operations
                operation_type = operation_count % 3
                
                try:
                    op_start = time.perf_counter()
                    
                    if operation_type == 0:
                        # Team operation
                        team = await orchestrator.form_team(
                            mission=f"Sustained test {operation_count}",
                            required_skills=['test'],
                            size=3
                        )
                        await orchestrator.dissolve_team(team.id)
                        
                    elif operation_type == 1:
                        # Decision validation
                        decision = {
                            'action': 'test_action',
                            'agent_id': f'test_{operation_count}',
                            'risk_level': 0.3
                        }
                        await ethics_engine.validate_decision(decision)
                        
                    else:
                        # Simulated work
                        await asyncio.sleep(0.1)
                    
                    op_end = time.perf_counter()
                    latency = (op_end - op_start) * 1000
                    
                    operations.append(True)
                    latencies.append(latency)
                    
                except Exception as e:
                    operations.append(False)
                    errors.append(str(e))
                
                operation_count += 1
                
                # Periodic resource sampling
                if operation_count % 100 == 0:
                    resource_samples.append(self.get_system_resources())
                    self.log(f"  Operations: {operation_count}, Success rate: {sum(operations)/len(operations)*100:.1f}%")
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)
        
        # Run sustained operations
        await continuous_operations()
        
        # Final measurements
        end_time = time.time()
        duration = end_time - start_time
        final_resources = self.get_system_resources()
        
        successful = sum(operations)
        failed = len(operations) - successful
        
        # Analyze resource stability
        if resource_samples:
            cpu_samples = [s['cpu_percent'] for s in resource_samples]
            memory_samples = [s['memory_percent'] for s in resource_samples]
            
            resource_stability = {
                'cpu_mean': statistics.mean(cpu_samples),
                'cpu_std': statistics.stdev(cpu_samples) if len(cpu_samples) > 1 else 0,
                'memory_mean': statistics.mean(memory_samples),
                'memory_std': statistics.stdev(memory_samples) if len(memory_samples) > 1 else 0,
                'samples': len(resource_samples)
            }
        else:
            resource_stability = {}
        
        result = LoadTestResult(
            test_name="Sustained Load Test",
            duration_seconds=duration,
            total_operations=len(operations),
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=len(operations) / duration if duration > 0 else 0,
            average_latency_ms=statistics.mean(latencies) if latencies else 0,
            peak_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0,
            resource_usage={
                'initial': initial_resources,
                'final': final_resources,
                'stability': resource_stability
            },
            errors=errors[:10],
            metadata={
                'duration_minutes': duration_minutes,
                'operations_per_minute': (len(operations) / duration * 60) if duration > 0 else 0
            }
        )
        
        self.results.append(result)
        self.log(f"✓ Sustained load test completed: {successful}/{len(operations)} successful")
        return result
    
    # ============= Report Generation =============
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive load test report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_suite': 'Load Testing',
            'results': [r.to_dict() for r in self.results],
            'summary': {
                'total_tests': len(self.results),
                'total_operations': sum(r.total_operations for r in self.results),
                'total_successful': sum(r.successful_operations for r in self.results),
                'total_failed': sum(r.failed_operations for r in self.results),
                'average_success_rate': statistics.mean([r.success_rate for r in self.results]) if self.results else 0
            },
            'recommendations': self._generate_recommendations()
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.log(f"Report saved to {output_file}")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        for result in self.results:
            if result.success_rate < 95:
                recommendations.append(
                    f"{result.test_name}: Success rate {result.success_rate:.1f}% below target (95%). "
                    f"Consider optimizing error handling."
                )
            
            if result.p99_latency_ms > 1000:
                recommendations.append(
                    f"{result.test_name}: P99 latency {result.p99_latency_ms:.0f}ms exceeds 1 second. "
                    f"Consider performance optimization."
                )
            
            if result.resource_usage and 'delta' in result.resource_usage:
                delta = result.resource_usage['delta']
                if delta.get('memory_percent', 0) > 20:
                    recommendations.append(
                        f"{result.test_name}: Memory usage increased by {delta['memory_percent']:.1f}%. "
                        f"Check for memory leaks."
                    )
        
        return recommendations if recommendations else ["All tests performed within acceptable parameters."]
    
    def print_summary(self):
        """Print load test summary"""
        print("\n" + "="*70)
        print("LOAD TEST SUMMARY")
        print("="*70)
        
        for result in self.results:
            print(f"\n{result.test_name}:")
            print(f"  Duration: {result.duration_seconds:.1f} seconds")
            print(f"  Total Operations: {result.total_operations}")
            print(f"  Success Rate: {result.success_rate:.1f}%")
            print(f"  Operations/sec: {result.operations_per_second:.1f}")
            print(f"  Average Latency: {result.average_latency_ms:.1f}ms")
            print(f"  P95 Latency: {result.p95_latency_ms:.1f}ms")
            print(f"  P99 Latency: {result.p99_latency_ms:.1f}ms")
            print(f"  Peak Latency: {result.peak_latency_ms:.1f}ms")
            
            if result.errors:
                print(f"  Sample Errors: {len(result.errors)} errors captured")
        
        print("\n" + "="*70)
        
        # Overall summary
        if self.results:
            total_ops = sum(r.total_operations for r in self.results)
            total_success = sum(r.successful_operations for r in self.results)
            
            print(f"Total Operations: {total_ops}")
            print(f"Total Successful: {total_success}")
            print(f"Overall Success Rate: {total_success/total_ops*100:.1f}%")
            
            recommendations = self._generate_recommendations()
            if recommendations:
                print("\nRecommendations:")
                for rec in recommendations:
                    print(f"  • {rec}")
        
        print("="*70 + "\n")
    
    # ============= Main Test Runner =============
    
    async def run_all_tests(self, quick_mode: bool = False):
        """Run all load tests"""
        self.log("Starting load test suite...")
        self.log("="*70)
        
        try:
            if quick_mode:
                # Quick tests for validation
                await self.test_agent_spawn_load(target_agents=20, spawn_rate=5, duration_seconds=10)
                await self.test_concurrent_teams_load(num_teams=5, team_size=3, duration_seconds=20)
                await self.test_workflow_execution_load(num_workflows=10, concurrent_workflows=3)
                await self.test_decision_validation_stress(num_decisions=1000, concurrent_validators=10)
                await self.test_resource_limits()
                await self.test_sustained_load(duration_minutes=1)
            else:
                # Full load tests
                await self.test_agent_spawn_load()
                await self.test_concurrent_teams_load()
                await self.test_workflow_execution_load()
                await self.test_decision_validation_stress()
                await self.test_resource_limits()
                await self.test_sustained_load()
            
        except KeyboardInterrupt:
            self.log("Load tests interrupted by user", "WARNING")
        except Exception as e:
            self.log(f"Load test suite failed: {str(e)}", "ERROR")
            traceback.print_exc()
        
        # Generate report
        self.print_summary()
        
        # Save report
        report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.generate_report(report_file)
        
        return self.results


# ============= Main Entry Point =============

async def main():
    """Main entry point for load testing"""
    print("Agile AI Company - Load Testing Suite")
    print("="*70)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Load testing for Agile AI Framework')
    parser.add_argument('--quick', action='store_true', help='Run quick validation tests')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    # Run tests
    runner = LoadTestRunner(verbose=args.verbose)
    
    try:
        results = await runner.run_all_tests(quick_mode=args.quick)
        
        # Check results
        if results:
            avg_success_rate = statistics.mean([r.success_rate for r in results])
            if avg_success_rate >= 95:
                print("\n✓ Load tests completed successfully!")
                return 0
            else:
                print(f"\n⚠ Load tests completed with {avg_success_rate:.1f}% success rate")
                return 1
        else:
            print("\n✗ No test results generated")
            return 2
            
    except Exception as e:
        print(f"\n✗ Load test suite failed: {str(e)}")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)