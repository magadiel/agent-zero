#!/usr/bin/env python3
"""
Performance Benchmark Suite for Agile AI Company Framework

This module provides comprehensive performance testing for all system components,
measuring key metrics like agent spawn times, communication latency, decision
validation speed, and resource usage.

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
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import traceback
import gc

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import framework components
try:
    from control.ethics_engine import EthicsEngine
    from control.safety_monitor import SafetyMonitor
    from control.resource_allocator import ResourceAllocator
    from coordination.team_orchestrator import TeamOrchestrator
    from coordination.workflow_engine import WorkflowEngine
    from coordination.agent_pool import AgentPool
    from python.helpers.bmad_agent import BMADAgentEnhancer
    from python.helpers.team_protocol import TeamProtocol
    from agent import Agent, AgentContext
except ImportError as e:
    print(f"Warning: Some imports failed - {e}")
    print("Running in limited mode with available components")


@dataclass
class BenchmarkResult:
    """Store benchmark test results"""
    test_name: str
    metric: str
    value: float
    unit: str
    target: Optional[float] = None
    passed: Optional[bool] = None
    samples: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.target and self.passed is None:
            self.passed = self.value <= self.target
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceBenchmark:
    """Main performance benchmark suite"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[BenchmarkResult] = []
        self.start_time = None
        self.end_time = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log benchmark messages"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] [{level}] {message}")
    
    def measure_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of a function"""
        gc.collect()  # Clean up before measurement
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, (end - start) * 1000  # Return time in milliseconds
    
    async def measure_async_time(self, coro) -> Tuple[Any, float]:
        """Measure execution time of an async coroutine"""
        gc.collect()  # Clean up before measurement
        start = time.perf_counter()
        result = await coro
        end = time.perf_counter()
        return result, (end - start) * 1000  # Return time in milliseconds
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage"""
        process = psutil.Process()
        return {
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'threads': process.num_threads(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0
        }
    
    # ============= Agent Spawn Tests =============
    
    async def test_agent_spawn_time(self, samples: int = 10) -> BenchmarkResult:
        """Test agent spawn time"""
        self.log("Testing agent spawn time...")
        times = []
        
        for i in range(samples):
            try:
                gc.collect()
                start = time.perf_counter()
                
                # Create agent context and agent
                context = AgentContext(
                    config={'name': f'test_agent_{i}'},
                    id=f"test_{i}",
                    agent0=None,
                    log=[]
                )
                agent = Agent(context=context, number=i)
                
                end = time.perf_counter()
                spawn_time = (end - start) * 1000
                times.append(spawn_time)
                
                self.log(f"  Sample {i+1}: {spawn_time:.2f}ms")
                
                # Clean up
                del agent
                del context
                
            except Exception as e:
                self.log(f"  Sample {i+1} failed: {str(e)}", "ERROR")
        
        if times:
            avg_time = statistics.mean(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            result = BenchmarkResult(
                test_name="Agent Spawn Time",
                metric="average_spawn_time",
                value=avg_time,
                unit="ms",
                target=500,  # Target: < 500ms
                samples=times,
                metadata={
                    'std_dev': std_dev,
                    'min': min(times),
                    'max': max(times),
                    'samples': len(times)
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Average spawn time: {avg_time:.2f}ms (target: <500ms)")
            return result
        else:
            self.log("✗ No successful samples", "ERROR")
            return None
    
    # ============= Communication Latency Tests =============
    
    async def test_communication_latency(self, samples: int = 20) -> BenchmarkResult:
        """Test inter-agent communication latency"""
        self.log("Testing communication latency...")
        times = []
        
        try:
            # Create team protocol for testing
            protocol = TeamProtocol("test_team")
            
            # Create test agents
            for i in range(2):
                agent_id = f"agent_{i}"
                protocol.add_member(agent_id, {'name': f'Agent {i}'})
            
            # Test message passing
            for i in range(samples):
                message = f"Test message {i}"
                
                start = time.perf_counter()
                # Simulate message broadcast
                await protocol.broadcast("Test broadcast", exclude_sender="agent_0")
                end = time.perf_counter()
                
                latency = (end - start) * 1000
                times.append(latency)
                
                if i % 5 == 0:
                    self.log(f"  Sample {i+1}: {latency:.2f}ms")
            
            avg_latency = statistics.mean(times)
            
            result = BenchmarkResult(
                test_name="Communication Latency",
                metric="average_latency",
                value=avg_latency,
                unit="ms",
                target=100,  # Target: < 100ms
                samples=times,
                metadata={
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                    'p50': statistics.median(times),
                    'p95': statistics.quantiles(times, n=20)[18] if len(times) > 1 else times[0],
                    'p99': statistics.quantiles(times, n=100)[98] if len(times) > 1 else times[0]
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Average latency: {avg_latency:.2f}ms (target: <100ms)")
            return result
            
        except Exception as e:
            self.log(f"✗ Communication test failed: {str(e)}", "ERROR")
            return None
    
    # ============= Decision Validation Tests =============
    
    async def test_decision_validation_time(self, samples: int = 50) -> BenchmarkResult:
        """Test ethics engine decision validation time"""
        self.log("Testing decision validation time...")
        times = []
        
        try:
            # Initialize ethics engine
            ethics_engine = EthicsEngine()
            
            # Test decisions
            test_decisions = [
                {
                    'action': 'process_data',
                    'target': 'user_data',
                    'purpose': 'analytics',
                    'agent_id': 'test_agent',
                    'risk_level': 0.3
                },
                {
                    'action': 'modify_system',
                    'target': 'configuration',
                    'purpose': 'optimization',
                    'agent_id': 'test_agent',
                    'risk_level': 0.5
                },
                {
                    'action': 'communicate',
                    'target': 'external_api',
                    'purpose': 'data_fetch',
                    'agent_id': 'test_agent',
                    'risk_level': 0.2
                }
            ]
            
            for i in range(samples):
                decision = test_decisions[i % len(test_decisions)].copy()
                decision['timestamp'] = datetime.now().isoformat()
                
                _, validation_time = await self.measure_async_time(
                    ethics_engine.validate_decision(decision)
                )
                
                times.append(validation_time)
                
                if i % 10 == 0:
                    self.log(f"  Sample {i+1}: {validation_time:.2f}ms")
            
            avg_time = statistics.mean(times)
            
            result = BenchmarkResult(
                test_name="Decision Validation",
                metric="average_validation_time",
                value=avg_time,
                unit="ms",
                target=50,  # Target: < 50ms
                samples=times,
                metadata={
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                    'min': min(times),
                    'max': max(times),
                    'samples': len(times)
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Average validation time: {avg_time:.2f}ms (target: <50ms)")
            return result
            
        except Exception as e:
            self.log(f"✗ Decision validation test failed: {str(e)}", "ERROR")
            return None
    
    # ============= Concurrent Operations Tests =============
    
    async def test_concurrent_team_operations(self, num_teams: int = 5) -> BenchmarkResult:
        """Test concurrent team operations"""
        self.log(f"Testing concurrent operations with {num_teams} teams...")
        
        try:
            orchestrator = TeamOrchestrator()
            operation_times = []
            
            # Record initial resources
            initial_resources = self.get_resource_usage()
            
            async def create_and_operate_team(team_id: int):
                """Create a team and perform operations"""
                start = time.perf_counter()
                
                # Form team
                team = await orchestrator.form_team(
                    mission=f"Test mission {team_id}",
                    required_skills=['testing', 'analysis'],
                    size=3
                )
                
                # Simulate team operations
                await asyncio.sleep(0.1)  # Simulate work
                
                # Dissolve team
                await orchestrator.dissolve_team(team.id)
                
                end = time.perf_counter()
                return (end - start) * 1000
            
            # Run concurrent team operations
            start_concurrent = time.perf_counter()
            tasks = [create_and_operate_team(i) for i in range(num_teams)]
            operation_times = await asyncio.gather(*tasks)
            end_concurrent = time.perf_counter()
            
            total_time = (end_concurrent - start_concurrent) * 1000
            avg_operation_time = statistics.mean(operation_times)
            
            # Record final resources
            final_resources = self.get_resource_usage()
            
            result = BenchmarkResult(
                test_name="Concurrent Team Operations",
                metric="total_operation_time",
                value=total_time,
                unit="ms",
                samples=operation_times,
                metadata={
                    'num_teams': num_teams,
                    'avg_per_team': avg_operation_time,
                    'parallelism_efficiency': (sum(operation_times) / total_time) * 100,
                    'resource_delta': {
                        'cpu': final_resources['cpu_percent'] - initial_resources['cpu_percent'],
                        'memory_mb': final_resources['memory_mb'] - initial_resources['memory_mb'],
                        'threads': final_resources['threads'] - initial_resources['threads']
                    }
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Concurrent operations completed in {total_time:.2f}ms")
            self.log(f"  Average per team: {avg_operation_time:.2f}ms")
            return result
            
        except Exception as e:
            self.log(f"✗ Concurrent operations test failed: {str(e)}", "ERROR")
            traceback.print_exc()
            return None
    
    # ============= Resource Usage Tests =============
    
    async def test_resource_allocation_performance(self, samples: int = 20) -> BenchmarkResult:
        """Test resource allocation performance"""
        self.log("Testing resource allocation performance...")
        times = []
        
        try:
            allocator = ResourceAllocator()
            
            for i in range(samples):
                team_id = f"team_{i}"
                
                _, alloc_time = await self.measure_async_time(
                    allocator.allocate_resources(
                        team_id=team_id,
                        requested_resources={
                            'cpu_cores': 2,
                            'memory_gb': 4,
                            'gpu_cores': 1
                        }
                    )
                )
                
                times.append(alloc_time)
                
                # Clean up
                await allocator.release_resources(team_id)
                
                if i % 5 == 0:
                    self.log(f"  Sample {i+1}: {alloc_time:.2f}ms")
            
            avg_time = statistics.mean(times)
            
            result = BenchmarkResult(
                test_name="Resource Allocation",
                metric="average_allocation_time",
                value=avg_time,
                unit="ms",
                target=100,  # Target: < 100ms
                samples=times,
                metadata={
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                    'min': min(times),
                    'max': max(times)
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Average allocation time: {avg_time:.2f}ms")
            return result
            
        except Exception as e:
            self.log(f"✗ Resource allocation test failed: {str(e)}", "ERROR")
            return None
    
    # ============= Workflow Performance Tests =============
    
    async def test_workflow_execution_performance(self) -> BenchmarkResult:
        """Test workflow execution performance"""
        self.log("Testing workflow execution performance...")
        
        try:
            engine = WorkflowEngine()
            
            # Create simple test workflow
            test_workflow = {
                'name': 'test_workflow',
                'steps': [
                    {
                        'id': 'step1',
                        'agent': 'analyst',
                        'action': 'analyze',
                        'creates': 'analysis.md'
                    },
                    {
                        'id': 'step2',
                        'agent': 'pm',
                        'action': 'plan',
                        'requires': ['analysis.md'],
                        'creates': 'plan.md'
                    }
                ]
            }
            
            # Measure workflow execution
            start = time.perf_counter()
            workflow = engine.create_workflow(test_workflow)
            
            # Simulate execution
            await asyncio.sleep(0.5)  # Simulate actual work
            
            end = time.perf_counter()
            execution_time = (end - start) * 1000
            
            result = BenchmarkResult(
                test_name="Workflow Execution",
                metric="execution_time",
                value=execution_time,
                unit="ms",
                metadata={
                    'workflow_steps': len(test_workflow['steps']),
                    'workflow_name': test_workflow['name']
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Workflow executed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            self.log(f"✗ Workflow execution test failed: {str(e)}", "ERROR")
            return None
    
    # ============= Memory Tests =============
    
    async def test_memory_usage_under_load(self, num_agents: int = 20) -> BenchmarkResult:
        """Test memory usage under load"""
        self.log(f"Testing memory usage with {num_agents} agents...")
        
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        agents = []
        try:
            # Create multiple agents
            for i in range(num_agents):
                context = AgentContext(
                    config={'name': f'load_test_agent_{i}'},
                    id=f"load_{i}",
                    agent0=None,
                    log=[]
                )
                agent = Agent(context=context, number=i)
                agents.append(agent)
            
            # Measure peak memory
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_per_agent = (peak_memory - initial_memory) / num_agents
            
            result = BenchmarkResult(
                test_name="Memory Usage",
                metric="memory_per_agent",
                value=memory_per_agent,
                unit="MB",
                metadata={
                    'num_agents': num_agents,
                    'initial_memory_mb': initial_memory,
                    'peak_memory_mb': peak_memory,
                    'total_increase_mb': peak_memory - initial_memory
                }
            )
            
            self.results.append(result)
            self.log(f"✓ Memory per agent: {memory_per_agent:.2f}MB")
            
            # Clean up
            agents.clear()
            gc.collect()
            
            return result
            
        except Exception as e:
            self.log(f"✗ Memory test failed: {str(e)}", "ERROR")
            return None
    
    # ============= Report Generation =============
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r and r.passed)
        failed_tests = sum(1 for r in self.results if r and not r.passed)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': str(self.end_time - self.start_time) if self.end_time else None,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'pass_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'results': [r.to_dict() for r in self.results if r],
            'performance_targets': {
                'agent_spawn_time': '< 500ms',
                'communication_latency': '< 100ms',
                'decision_validation': '< 50ms',
                'resource_allocation': '< 100ms'
            }
        }
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.log(f"Report saved to {output_file}")
        
        return report
    
    def print_summary(self):
        """Print performance test summary"""
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("="*60)
        
        for result in self.results:
            if result:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                print(f"\n{result.test_name}:")
                print(f"  Status: {status}")
                print(f"  Metric: {result.metric}")
                print(f"  Value: {result.value:.2f} {result.unit}")
                if result.target:
                    print(f"  Target: < {result.target} {result.unit}")
                if result.metadata:
                    for key, value in result.metadata.items():
                        if isinstance(value, float):
                            print(f"  {key}: {value:.2f}")
                        else:
                            print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        
        # Overall summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r and r.passed)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {passed/total*100:.1f}%" if total > 0 else "N/A")
        print("="*60 + "\n")
    
    # ============= Main Benchmark Runner =============
    
    async def run_all_benchmarks(self):
        """Run all performance benchmarks"""
        self.start_time = datetime.now()
        self.log("Starting performance benchmark suite...")
        self.log("="*60)
        
        # Run individual benchmarks
        benchmarks = [
            self.test_agent_spawn_time,
            self.test_communication_latency,
            self.test_decision_validation_time,
            self.test_resource_allocation_performance,
            self.test_concurrent_team_operations,
            self.test_workflow_execution_performance,
            self.test_memory_usage_under_load
        ]
        
        for benchmark in benchmarks:
            try:
                await benchmark()
            except Exception as e:
                self.log(f"Benchmark failed: {str(e)}", "ERROR")
                traceback.print_exc()
            
            # Small delay between tests
            await asyncio.sleep(0.5)
            print()  # Visual separator
        
        self.end_time = datetime.now()
        
        # Generate and display report
        self.print_summary()
        
        # Save report to file
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.generate_report(report_file)
        
        return self.results


# ============= Standalone Execution =============

async def main():
    """Main entry point for standalone execution"""
    print("Agile AI Company - Performance Benchmark Suite")
    print("="*60)
    
    benchmark = PerformanceBenchmark(verbose=True)
    
    try:
        results = await benchmark.run_all_benchmarks()
        
        # Check if all critical tests passed
        critical_tests = ['Agent Spawn Time', 'Communication Latency', 'Decision Validation']
        critical_passed = all(
            any(r.test_name == test and r.passed for r in results if r)
            for test in critical_tests
        )
        
        if critical_passed:
            print("\n✓ All critical performance targets met!")
            return 0
        else:
            print("\n✗ Some critical performance targets not met.")
            return 1
            
    except Exception as e:
        print(f"\n✗ Benchmark suite failed: {str(e)}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)