"""
Standalone test for Performance Monitor - runs without external dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock psutil module for testing
class MockPsutil:
    class Process:
        def __init__(self, pid):
            self.pid = pid
        
        def oneshot(self):
            return self
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def cpu_percent(self):
            return 45.5
        
        def memory_info(self):
            class MemInfo:
                rss = 100 * 1024 * 1024  # 100 MB
            return MemInfo()
        
        def io_counters(self):
            class IOCounters:
                read_bytes = 50 * 1024 * 1024
                write_bytes = 30 * 1024 * 1024
            return IOCounters()
        
        def connections(self):
            return []
        
        def num_threads(self):
            return 5
        
        def open_files(self):
            return []
    
    @staticmethod
    def cpu_percent(interval=None):
        return 55.0
    
    @staticmethod
    def cpu_count():
        return 8
    
    @staticmethod
    def virtual_memory():
        class VirtualMemory:
            total = 16 * 1024 * 1024 * 1024  # 16 GB
            used = 8 * 1024 * 1024 * 1024   # 8 GB
            available = 8 * 1024 * 1024 * 1024
            percent = 50.0
        return VirtualMemory()
    
    @staticmethod
    def disk_usage(path):
        class DiskUsage:
            total = 500 * 1024 * 1024 * 1024  # 500 GB
            used = 200 * 1024 * 1024 * 1024   # 200 GB
            free = 300 * 1024 * 1024 * 1024   # 300 GB
            percent = 40.0
        return DiskUsage()
    
    @staticmethod
    def disk_io_counters():
        class DiskIO:
            read_bytes = 1000 * 1024 * 1024
            write_bytes = 500 * 1024 * 1024
        return DiskIO()
    
    @staticmethod
    def net_io_counters():
        class NetIO:
            bytes_sent = 100 * 1024 * 1024
            bytes_recv = 200 * 1024 * 1024
        return NetIO()
    
    class NoSuchProcess(Exception):
        pass
    
    class AccessDenied(Exception):
        pass

# Replace psutil import in the module
sys.modules['psutil'] = MockPsutil()

# Now import the actual module
from performance_monitor import (
    PerformanceMonitor, MetricType, AlertSeverity, TaskStatus,
    PerformanceThreshold
)
from resource_tracker import ResourceTracker, ResourceType, BottleneckType

import time
import json


def test_performance_monitor():
    """Test basic performance monitoring functionality"""
    print("Testing Performance Monitor...")
    
    # Create monitor
    monitor = PerformanceMonitor(
        retention_hours=24,
        sampling_interval_seconds=1
    )
    
    # Start monitoring
    monitor.start_monitoring()
    print("✓ Monitor started")
    
    # Test metric recording
    monitor.record_metric(MetricType.RESPONSE_TIME, 150, agent_id="agent_1")
    monitor.record_metric(MetricType.CPU_USAGE, 65, agent_id="agent_1")
    monitor.record_metric(MetricType.MEMORY_USAGE, 70, agent_id="agent_1")
    print("✓ Metrics recorded")
    
    # Test task tracking
    task_id = "test_task_1"
    monitor.start_task(task_id, "agent_1", "processing")
    time.sleep(0.1)
    monitor.end_task(task_id, TaskStatus.COMPLETED)
    print("✓ Task tracked")
    
    # Test multiple tasks for statistics
    for i in range(5):
        tid = f"task_{i}"
        monitor.start_task(tid, "agent_1", "processing")
        time.sleep(0.05)
        status = TaskStatus.COMPLETED if i < 4 else TaskStatus.FAILED
        monitor.end_task(tid, status)
    
    # Get statistics
    stats = monitor.get_statistics(MetricType.RESPONSE_TIME, agent_id="agent_1")
    print(f"✓ Response time stats: mean={stats['mean']:.2f}ms")
    
    # Get task statistics
    task_stats = monitor.get_task_statistics(agent_id="agent_1")
    print(f"✓ Task stats: {task_stats['total_tasks']} tasks, "
          f"{task_stats['success_rate']:.1f}% success rate")
    
    # Test alert generation
    threshold = PerformanceThreshold(
        MetricType.CPU_USAGE,
        warning_threshold=60,
        critical_threshold=80,
        duration_seconds=1
    )
    monitor.set_threshold(threshold)
    
    # Trigger high CPU alert
    for _ in range(5):
        monitor.record_metric(MetricType.CPU_USAGE, 85, agent_id="agent_1")
    
    monitor._check_thresholds()
    alerts = monitor.get_alerts(active_only=True)
    if alerts:
        print(f"✓ Alert generated: {alerts[0].message}")
    
    # Get system performance
    sys_perf = monitor.get_system_performance()
    print(f"✓ System performance: {len(sys_perf['active_alerts'])} active alerts")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("✓ Monitor stopped")
    
    return True


def test_resource_tracker():
    """Test resource tracking functionality"""
    print("\nTesting Resource Tracker...")
    
    # Create tracker
    tracker = ResourceTracker(
        sampling_interval_seconds=1,
        history_retention_hours=24
    )
    
    # Start monitoring
    tracker.start_monitoring()
    print("✓ Tracker started")
    
    # Register agents
    tracker.register_agent("agent_1", process_id=os.getpid(), team_id="team_alpha")
    tracker.register_agent("agent_2", process_id=os.getpid(), team_id="team_alpha")
    print("✓ Agents registered")
    
    # Record task completions
    for i in range(5):
        tracker.record_task_completion("agent_1", task_success=True)
        if i % 2 == 0:
            tracker.record_task_completion("agent_2", task_success=True)
    print("✓ Tasks recorded")
    
    # Wait for some monitoring cycles
    time.sleep(3)
    
    # Calculate efficiency
    efficiency = tracker.calculate_efficiency("agent_1", period_minutes=5)
    if efficiency:
        print(f"✓ Efficiency calculated: {efficiency.efficiency_score:.2f}%")
    
    # Get resource summary
    summary = tracker.get_resource_summary("agent_1")
    if "current_usage" in summary:
        print(f"✓ Resource summary: CPU={summary['current_usage']['cpu_percent']:.1f}%")
    
    # Get system overview
    overview = tracker.get_system_resource_overview()
    print(f"✓ System overview: {overview['tracked_entities']['active_agents']} agents tracked")
    
    # Check for bottlenecks
    tracker._detect_bottlenecks()
    bottlenecks = list(tracker.active_bottlenecks.values())
    print(f"✓ Bottleneck detection: {len(bottlenecks)} bottlenecks found")
    
    # Stop monitoring
    tracker.stop_monitoring()
    print("✓ Tracker stopped")
    
    return True


def test_integration():
    """Test integration between monitor and tracker"""
    print("\nTesting Integration...")
    
    # Create both components
    monitor = PerformanceMonitor()
    tracker = ResourceTracker()
    
    # Start both
    monitor.start_monitoring()
    tracker.start_monitoring()
    print("✓ Both systems started")
    
    # Simulate agent workflow
    agent_id = "integration_agent"
    tracker.register_agent(agent_id, process_id=os.getpid(), team_id="team_beta")
    
    # Process tasks
    for i in range(3):
        task_id = f"integration_task_{i}"
        
        # Start task in monitor
        monitor.start_task(task_id, agent_id, "data_processing")
        
        # Record metrics
        monitor.record_metric(MetricType.CPU_USAGE, 40 + i * 10, agent_id=agent_id)
        monitor.record_metric(MetricType.MEMORY_USAGE, 50 + i * 5, agent_id=agent_id)
        
        # Simulate work
        time.sleep(0.1)
        
        # End task
        monitor.end_task(task_id, TaskStatus.COMPLETED)
        
        # Record in tracker
        tracker.record_task_completion(agent_id, task_success=True)
    
    # Wait for processing
    time.sleep(2)
    
    # Get combined metrics
    perf = monitor.get_agent_performance(agent_id)
    resources = tracker.get_resource_summary(agent_id)
    
    print(f"✓ Agent performance: {perf['task_stats']['total_tasks']} tasks completed")
    print(f"✓ Resource usage tracked for agent")
    
    # Export data
    monitor_export = monitor.export_metrics()
    tracker_export = tracker.export_resource_data(entity_id=agent_id)
    
    print(f"✓ Data exported: {len(monitor_export.get('tasks', []))} tasks, "
          f"{len(tracker_export.get('entities', {}))} entities")
    
    # Stop both
    monitor.stop_monitoring()
    tracker.stop_monitoring()
    print("✓ Both systems stopped")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Performance Monitoring System - Standalone Tests")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        if test_performance_monitor():
            tests_passed += 1
            print("✅ Performance Monitor tests passed")
    except Exception as e:
        tests_failed += 1
        print(f"❌ Performance Monitor tests failed: {e}")
    
    try:
        if test_resource_tracker():
            tests_passed += 1
            print("✅ Resource Tracker tests passed")
    except Exception as e:
        tests_failed += 1
        print(f"❌ Resource Tracker tests failed: {e}")
    
    try:
        if test_integration():
            tests_passed += 1
            print("✅ Integration tests passed")
    except Exception as e:
        tests_failed += 1
        print(f"❌ Integration tests failed: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    return tests_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)