"""
Test suite for Performance Monitor
"""

import unittest
import time
from datetime import datetime, timedelta
import threading
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance_monitor import (
    PerformanceMonitor, MetricType, AlertSeverity, TaskStatus,
    PerformanceThreshold, PerformanceMetric, TaskPerformance
)


class TestPerformanceMonitor(unittest.TestCase):
    """Test cases for PerformanceMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = PerformanceMonitor(
            retention_hours=1,
            sampling_interval_seconds=1,
            alert_callback=None
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.monitor._monitoring:
            self.monitor.stop_monitoring()
    
    def test_initialization(self):
        """Test monitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.retention_hours, 1)
        self.assertEqual(self.monitor.sampling_interval_seconds, 1)
        self.assertFalse(self.monitor._monitoring)
        self.assertTrue(len(self.monitor.thresholds) > 0)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor._monitoring)
        self.assertIsNotNone(self.monitor._monitor_thread)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor._monitoring)
    
    def test_record_metric(self):
        """Test recording performance metrics"""
        # Record a metric
        self.monitor.record_metric(
            MetricType.RESPONSE_TIME,
            150.5,
            agent_id="agent_1",
            task_id="task_1"
        )
        
        # Check metric was recorded
        metrics = list(self.monitor.metrics[MetricType.RESPONSE_TIME])
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].value, 150.5)
        self.assertEqual(metrics[0].agent_id, "agent_1")
        self.assertEqual(metrics[0].task_id, "task_1")
        
        # Check agent-specific metrics
        agent_metrics = list(self.monitor.agent_metrics["agent_1"][MetricType.RESPONSE_TIME])
        self.assertEqual(len(agent_metrics), 1)
    
    def test_task_tracking(self):
        """Test task performance tracking"""
        # Start a task
        task = self.monitor.start_task(
            task_id="test_task",
            agent_id="agent_1",
            task_type="processing"
        )
        
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "test_task")
        self.assertEqual(task.agent_id, "agent_1")
        self.assertEqual(task.status, TaskStatus.STARTED)
        self.assertIn("test_task", self.monitor.active_tasks)
        
        # Simulate some work
        time.sleep(0.1)
        
        # End the task
        self.monitor.end_task("test_task", TaskStatus.COMPLETED)
        
        # Check task was moved to completed
        self.assertNotIn("test_task", self.monitor.active_tasks)
        self.assertEqual(len(self.monitor.completed_tasks), 1)
        
        completed_task = self.monitor.completed_tasks[0]
        self.assertEqual(completed_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(completed_task.duration_ms)
        self.assertGreater(completed_task.duration_ms, 0)
    
    def test_alert_generation(self):
        """Test alert generation for threshold breaches"""
        alerts_generated = []
        
        def alert_callback(alert):
            alerts_generated.append(alert)
        
        self.monitor.alert_callback = alert_callback
        
        # Set a low CPU threshold
        threshold = PerformanceThreshold(
            MetricType.CPU_USAGE,
            warning_threshold=50,
            critical_threshold=80,
            duration_seconds=1,
            consecutive_breaches=1
        )
        self.monitor.set_threshold(threshold)
        
        # Record high CPU usage
        for _ in range(5):
            self.monitor.record_metric(MetricType.CPU_USAGE, 85)
            time.sleep(0.01)
        
        # Manually trigger threshold check
        self.monitor._check_thresholds()
        
        # Check alert was generated
        self.assertTrue(len(self.monitor.active_alerts) > 0)
        self.assertTrue(len(alerts_generated) > 0)
        
        alert = alerts_generated[0]
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertEqual(alert.metric_type, MetricType.CPU_USAGE)
        self.assertGreaterEqual(alert.current_value, 80)
    
    def test_statistics_calculation(self):
        """Test metric statistics calculation"""
        # Record multiple metrics
        values = [100, 200, 150, 300, 250]
        for value in values:
            self.monitor.record_metric(
                MetricType.RESPONSE_TIME,
                value,
                agent_id="agent_1"
            )
        
        # Get statistics
        stats = self.monitor.get_statistics(
            MetricType.RESPONSE_TIME,
            agent_id="agent_1"
        )
        
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["mean"], 200)
        self.assertEqual(stats["median"], 200)
        self.assertEqual(stats["min"], 100)
        self.assertEqual(stats["max"], 300)
        self.assertGreater(stats["std_dev"], 0)
    
    def test_task_statistics(self):
        """Test task completion statistics"""
        # Create and complete several tasks
        for i in range(10):
            task_id = f"task_{i}"
            self.monitor.start_task(task_id, "agent_1", "processing")
            time.sleep(0.01)
            
            if i < 8:
                self.monitor.end_task(task_id, TaskStatus.COMPLETED)
            else:
                self.monitor.end_task(task_id, TaskStatus.FAILED)
        
        # Get task statistics
        stats = self.monitor.get_task_statistics(agent_id="agent_1")
        
        self.assertEqual(stats["total_tasks"], 10)
        self.assertEqual(stats["success_rate"], 80.0)
        self.assertEqual(stats["failure_rate"], 20.0)
        self.assertGreater(stats["avg_duration_ms"], 0)
        self.assertEqual(stats["tasks_by_status"]["completed"], 8)
        self.assertEqual(stats["tasks_by_status"]["failed"], 2)
    
    def test_agent_performance(self):
        """Test agent performance tracking"""
        agent_id = "test_agent"
        
        # Record metrics for the agent
        self.monitor.record_metric(MetricType.RESPONSE_TIME, 100, agent_id=agent_id)
        self.monitor.record_metric(MetricType.RESPONSE_TIME, 200, agent_id=agent_id)
        
        # Start and complete a task
        self.monitor.start_task("task_1", agent_id, "processing")
        time.sleep(0.05)
        self.monitor.end_task("task_1", TaskStatus.COMPLETED)
        
        # Get agent performance
        performance = self.monitor.get_agent_performance(agent_id)
        
        self.assertEqual(performance["agent_id"], agent_id)
        self.assertIn("response_time_stats", performance)
        self.assertIn("task_duration_stats", performance)
        self.assertIn("task_stats", performance)
        self.assertEqual(performance["response_time_stats"]["count"], 2)
    
    def test_system_performance(self):
        """Test system performance overview"""
        # Start monitoring to collect system metrics
        self.monitor.start_monitoring()
        time.sleep(2)
        
        # Get system performance
        perf = self.monitor.get_system_performance()
        
        self.assertIn("timestamp", perf)
        self.assertIn("system_metrics", perf)
        self.assertIn("performance_stats", perf)
        self.assertIn("task_stats", perf)
        self.assertIn("active_alerts", perf)
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment and resolution"""
        # Generate an alert
        self.monitor._generate_alert(
            severity=AlertSeverity.WARNING,
            metric_type=MetricType.CPU_USAGE,
            current_value=85,
            threshold_value=80
        )
        
        # Get the alert
        alerts = self.monitor.get_alerts(active_only=True)
        self.assertEqual(len(alerts), 1)
        alert_id = alerts[0].alert_id
        
        # Acknowledge the alert
        self.monitor.acknowledge_alert(alert_id)
        alert = self.monitor.active_alerts[alert_id]
        self.assertTrue(alert.acknowledged)
        
        # Resolve the alert
        self.monitor.resolve_alert(alert_id)
        self.assertNotIn(alert_id, self.monitor.active_alerts)
    
    def test_metric_cleanup(self):
        """Test cleanup of old metrics"""
        # Record old metrics
        old_time = datetime.now() - timedelta(hours=2)
        metric = PerformanceMetric(
            metric_type=MetricType.CPU_USAGE,
            value=50,
            timestamp=old_time
        )
        self.monitor.metrics[MetricType.CPU_USAGE].append(metric)
        
        # Record recent metric
        self.monitor.record_metric(MetricType.CPU_USAGE, 60)
        
        # Run cleanup
        self.monitor._cleanup_old_data()
        
        # Check old metric was removed
        remaining_metrics = list(self.monitor.metrics[MetricType.CPU_USAGE])
        self.assertTrue(all(m.timestamp > old_time for m in remaining_metrics))
    
    def test_export_metrics(self):
        """Test metrics export functionality"""
        # Record some metrics
        for i in range(5):
            self.monitor.record_metric(
                MetricType.RESPONSE_TIME,
                100 + i * 10,
                agent_id="agent_1"
            )
            time.sleep(0.01)
        
        # Export metrics
        export = self.monitor.export_metrics()
        
        self.assertIn("export_time", export)
        self.assertIn("time_range", export)
        self.assertIn("metrics", export)
        
        if MetricType.RESPONSE_TIME.value in export["metrics"]:
            metrics = export["metrics"][MetricType.RESPONSE_TIME.value]
            self.assertEqual(len(metrics), 5)
    
    def test_percentile_calculation(self):
        """Test percentile calculation"""
        values = list(range(1, 101))  # 1 to 100
        
        p50 = self.monitor._percentile(values, 50)
        p95 = self.monitor._percentile(values, 95)
        p99 = self.monitor._percentile(values, 99)
        
        self.assertEqual(p50, 50)
        self.assertEqual(p95, 95)
        self.assertEqual(p99, 99)
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access"""
        errors = []
        
        def record_metrics():
            try:
                for i in range(100):
                    self.monitor.record_metric(
                        MetricType.RESPONSE_TIME,
                        i,
                        agent_id=f"agent_{threading.current_thread().name}"
                    )
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check no errors occurred
        self.assertEqual(len(errors), 0)
        
        # Check metrics were recorded
        total_metrics = sum(len(metrics) for metrics in self.monitor.metrics.values())
        self.assertGreater(total_metrics, 0)
    
    def test_threshold_updates(self):
        """Test updating performance thresholds"""
        # Set initial threshold
        threshold1 = PerformanceThreshold(
            MetricType.MEMORY_USAGE,
            warning_threshold=70,
            critical_threshold=90
        )
        self.monitor.set_threshold(threshold1)
        
        # Update threshold
        threshold2 = PerformanceThreshold(
            MetricType.MEMORY_USAGE,
            warning_threshold=60,
            critical_threshold=80
        )
        self.monitor.set_threshold(threshold2)
        
        # Check only one threshold exists for this metric
        memory_thresholds = [
            t for t in self.monitor.thresholds 
            if t.metric_type == MetricType.MEMORY_USAGE
        ]
        self.assertEqual(len(memory_thresholds), 1)
        self.assertEqual(memory_thresholds[0].warning_threshold, 60)
    
    def test_cache_invalidation(self):
        """Test statistics cache invalidation"""
        # Record initial metrics
        self.monitor.record_metric(MetricType.CPU_USAGE, 50)
        
        # Get statistics (should cache)
        stats1 = self.monitor.get_statistics(MetricType.CPU_USAGE)
        
        # Record new metric
        self.monitor.record_metric(MetricType.CPU_USAGE, 100)
        
        # Get statistics again (should recalculate)
        stats2 = self.monitor.get_statistics(MetricType.CPU_USAGE)
        
        # Stats should be different
        self.assertNotEqual(stats1["mean"], stats2["mean"])
        self.assertEqual(stats2["count"], 2)


class TestIntegration(unittest.TestCase):
    """Integration tests for PerformanceMonitor"""
    
    def test_full_workflow(self):
        """Test complete monitoring workflow"""
        # Create monitor with alert callback
        alerts = []
        monitor = PerformanceMonitor(
            sampling_interval_seconds=1,
            alert_callback=lambda a: alerts.append(a)
        )
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Simulate agent workflow
        agent_id = "integration_agent"
        
        # Process multiple tasks
        for i in range(5):
            task_id = f"task_{i}"
            
            # Start task
            monitor.start_task(task_id, agent_id, "data_processing")
            
            # Record metrics during task
            monitor.record_metric(
                MetricType.CPU_USAGE,
                30 + i * 10,
                agent_id=agent_id
            )
            
            # Simulate work
            time.sleep(0.1)
            
            # End task
            status = TaskStatus.COMPLETED if i < 4 else TaskStatus.FAILED
            monitor.end_task(task_id, status)
        
        # Wait for monitoring cycles
        time.sleep(2)
        
        # Get comprehensive report
        system_perf = monitor.get_system_performance()
        agent_perf = monitor.get_agent_performance(agent_id)
        task_stats = monitor.get_task_statistics(agent_id=agent_id)
        
        # Verify results
        self.assertIsNotNone(system_perf)
        self.assertEqual(agent_perf["agent_id"], agent_id)
        self.assertEqual(task_stats["total_tasks"], 5)
        self.assertEqual(task_stats["success_rate"], 80.0)
        
        # Stop monitoring
        monitor.stop_monitoring()


if __name__ == "__main__":
    unittest.main()