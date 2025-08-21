"""
Unit tests for the Safety Monitor module.
"""

import unittest
import asyncio
import time
import os
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety_monitor import (
    SafetyMonitor,
    SafetyLevel,
    ThreatType,
    InterventionType,
    AgentMonitor,
    CircuitBreaker,
    SafetyMetrics
)


class TestSafetyMetrics(unittest.TestCase):
    """Test SafetyMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = SafetyMetrics(window_size=10)
        self.assertEqual(len(metrics.cpu_usage), 0)
        self.assertEqual(len(metrics.memory_usage), 0)
        self.assertEqual(metrics.error_count, 0)
    
    def test_metrics_update(self):
        """Test updating metrics."""
        metrics = SafetyMetrics(window_size=10)
        metrics.update(50.0, 60.0, 100.0)
        
        self.assertEqual(len(metrics.cpu_usage), 1)
        self.assertEqual(len(metrics.memory_usage), 1)
        self.assertEqual(len(metrics.response_times), 1)
        self.assertEqual(metrics.cpu_usage[0], 50.0)
        self.assertEqual(metrics.memory_usage[0], 60.0)
    
    def test_metrics_averages(self):
        """Test calculating averages."""
        metrics = SafetyMetrics(window_size=10)
        
        # Add some data
        for i in range(5):
            metrics.update(40 + i * 10, 50 + i * 5, 100 + i * 20)
        
        averages = metrics.get_averages()
        self.assertEqual(averages["avg_cpu"], 60.0)  # (40+50+60+70+80)/5
        self.assertEqual(averages["avg_memory"], 60.0)  # (50+55+60+65+70)/5
        self.assertEqual(averages["avg_response_time"], 140.0)  # (100+120+140+160+180)/5
    
    def test_metrics_window_size(self):
        """Test that window size is respected."""
        metrics = SafetyMetrics(window_size=5)
        
        # Add more data than window size
        for i in range(10):
            metrics.update(i * 10, i * 10, i * 10)
        
        # Should only keep last 5
        self.assertEqual(len(metrics.cpu_usage), 5)
        self.assertEqual(len(metrics.memory_usage), 5)
        self.assertEqual(list(metrics.cpu_usage), [50, 60, 70, 80, 90])
    
    def test_metrics_trends(self):
        """Test trend detection."""
        metrics = SafetyMetrics(window_size=20)
        
        # Add increasing trend
        for i in range(15):
            metrics.update(30 + i * 3, 40 + i * 2, None)
        
        trends = metrics.get_trends()
        self.assertEqual(trends["cpu"], "increasing")
        self.assertEqual(trends["memory"], "increasing")


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker class."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.failure_count, 0)
        self.assertTrue(cb.can_proceed())
    
    def test_circuit_breaker_opening(self):
        """Test circuit breaker opens after threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record failures
        cb.record_failure()
        self.assertEqual(cb.state, "closed")
        cb.record_failure()
        self.assertEqual(cb.state, "closed")
        cb.record_failure()
        self.assertEqual(cb.state, "open")
        self.assertFalse(cb.can_proceed())
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Open the breaker
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, "open")
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should be half-open
        self.assertTrue(cb.can_proceed())
        self.assertEqual(cb.state, "half_open")
        
        # Successful calls should close it
        cb.record_success()
        cb.record_success()
        cb.record_success()
        self.assertEqual(cb.state, "closed")


class TestAgentMonitor(unittest.TestCase):
    """Test AgentMonitor class."""
    
    def test_agent_monitor_initialization(self):
        """Test agent monitor initialization."""
        monitor = AgentMonitor("test-agent")
        self.assertEqual(monitor.agent_id, "test-agent")
        self.assertEqual(monitor.action_count, 0)
        self.assertFalse(monitor.suspended)
    
    def test_agent_activity_tracking(self):
        """Test activity tracking."""
        monitor = AgentMonitor("test-agent")
        initial_time = monitor.last_activity
        
        time.sleep(0.1)
        monitor.update_activity()
        
        self.assertGreater(monitor.last_activity, initial_time)
        self.assertEqual(monitor.action_count, 1)
    
    def test_agent_runtime(self):
        """Test runtime calculation."""
        monitor = AgentMonitor("test-agent")
        time.sleep(0.1)
        
        runtime = monitor.get_runtime()
        self.assertGreater(runtime, 0.1)
        self.assertLess(runtime, 0.2)
    
    def test_agent_idle_time(self):
        """Test idle time calculation."""
        monitor = AgentMonitor("test-agent")
        monitor.update_activity()
        
        time.sleep(0.1)
        idle_time = monitor.get_idle_time()
        
        self.assertGreater(idle_time, 0.1)
        self.assertLess(idle_time, 0.2)


class TestSafetyMonitor(unittest.TestCase):
    """Test SafetyMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SafetyMonitor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_monitor_initialization(self):
        """Test safety monitor initialization."""
        self.assertIsNotNone(self.monitor)
        self.assertIsNotNone(self.monitor.thresholds)
        self.assertEqual(self.monitor.safety_level, SafetyLevel.NORMAL)
        self.assertFalse(self.monitor.emergency_stop_triggered)
        self.assertTrue(self.monitor.kill_switch_armed)
    
    def test_agent_registration(self):
        """Test agent registration."""
        success = self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        self.assertTrue(success)
        self.assertIn("test-agent-001", self.monitor.agent_monitors)
        
        # Test duplicate registration
        success = self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        self.assertFalse(success)
    
    def test_agent_unregistration(self):
        """Test agent unregistration."""
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        self.loop.run_until_complete(
            self.monitor.unregister_agent("test-agent-001")
        )
        
        self.assertNotIn("test-agent-001", self.monitor.agent_monitors)
    
    def test_agent_activity_reporting(self):
        """Test reporting agent activity."""
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        self.loop.run_until_complete(
            self.monitor.report_agent_activity(
                "test-agent-001",
                cpu=50.0,
                memory=60.0,
                response_time=100.0
            )
        )
        
        monitor = self.monitor.agent_monitors["test-agent-001"]
        self.assertEqual(monitor.action_count, 1)
        self.assertEqual(len(monitor.metrics.cpu_usage), 1)
    
    def test_error_reporting(self):
        """Test error reporting and circuit breaker."""
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        # Report multiple errors
        for _ in range(5):
            self.loop.run_until_complete(
                self.monitor.report_agent_activity(
                    "test-agent-001",
                    error=True
                )
            )
        
        monitor = self.monitor.agent_monitors["test-agent-001"]
        self.assertEqual(monitor.metrics.error_count, 5)
        self.assertEqual(monitor.circuit_breaker.state, "open")
    
    def test_safety_level_updates(self):
        """Test safety level updates."""
        # Add threat
        self.monitor.active_threats.add(ThreatType.THRESHOLD_BREACH)
        self.loop.run_until_complete(
            self.monitor._update_safety_level()
        )
        self.assertEqual(self.monitor.safety_level, SafetyLevel.WARNING)
        
        # Add critical threat
        self.monitor.active_threats.add(ThreatType.RESOURCE_EXHAUSTION)
        self.loop.run_until_complete(
            self.monitor._update_safety_level()
        )
        self.assertEqual(self.monitor.safety_level, SafetyLevel.CRITICAL)
    
    def test_max_concurrent_agents(self):
        """Test maximum concurrent agents limit."""
        max_agents = self.monitor.thresholds["agent_limits"]["max_concurrent_agents"]
        
        # Register up to limit
        for i in range(max_agents):
            success = self.loop.run_until_complete(
                self.monitor.register_agent(f"test-agent-{i:03d}")
            )
            self.assertTrue(success)
        
        # Try to register one more
        success = self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-overflow")
        )
        self.assertFalse(success)
    
    def test_agent_suspension(self):
        """Test agent suspension."""
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        self.loop.run_until_complete(
            self.monitor.pause_agent("test-agent-001")
        )
        
        monitor = self.monitor.agent_monitors["test-agent-001"]
        self.assertTrue(monitor.suspended)
        
        self.loop.run_until_complete(
            self.monitor.resume_agent("test-agent-001")
        )
        
        self.assertFalse(monitor.suspended)
    
    def test_emergency_stop(self):
        """Test emergency stop functionality."""
        # Register some agents
        for i in range(3):
            self.loop.run_until_complete(
                self.monitor.register_agent(f"test-agent-{i:03d}")
            )
        
        # Trigger emergency stop
        self.loop.run_until_complete(
            self.monitor.emergency_stop("Test emergency")
        )
        
        self.assertTrue(self.monitor.emergency_stop_triggered)
        self.assertTrue(self.monitor.shutdown_in_progress)
        self.assertEqual(len(self.monitor.agent_monitors), 0)
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown."""
        # Register some agents
        for i in range(3):
            self.loop.run_until_complete(
                self.monitor.register_agent(f"test-agent-{i:03d}")
            )
        
        # Perform graceful shutdown
        self.loop.run_until_complete(
            self.monitor.graceful_shutdown(timeout_seconds=2)
        )
        
        self.assertTrue(self.monitor.shutdown_in_progress)
        self.assertFalse(self.monitor.kill_switch_armed)
        self.assertEqual(len(self.monitor.agent_monitors), 0)
    
    def test_kill_switch_control(self):
        """Test kill switch arming/disarming."""
        self.assertTrue(self.monitor.kill_switch_armed)
        
        self.loop.run_until_complete(
            self.monitor.disarm_kill_switch()
        )
        self.assertFalse(self.monitor.kill_switch_armed)
        
        self.loop.run_until_complete(
            self.monitor.arm_kill_switch()
        )
        self.assertTrue(self.monitor.kill_switch_armed)
    
    def test_get_status(self):
        """Test getting system status."""
        # Register an agent
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        status = self.loop.run_until_complete(
            self.monitor.get_status()
        )
        
        self.assertIn("safety_level", status)
        self.assertIn("agent_count", status)
        self.assertIn("global_metrics", status)
        self.assertEqual(status["agent_count"], 1)
        self.assertEqual(status["safety_level"], "normal")
    
    def test_get_agent_status(self):
        """Test getting individual agent status."""
        self.loop.run_until_complete(
            self.monitor.register_agent("test-agent-001")
        )
        
        # Report some activity
        self.loop.run_until_complete(
            self.monitor.report_agent_activity(
                "test-agent-001",
                cpu=50.0,
                memory=60.0
            )
        )
        
        status = self.loop.run_until_complete(
            self.monitor.get_agent_status("test-agent-001")
        )
        
        self.assertIsNotNone(status)
        self.assertEqual(status["agent_id"], "test-agent-001")
        self.assertEqual(status["action_count"], 1)
        self.assertIn("metrics", status)
        
        # Test non-existent agent
        status = self.loop.run_until_complete(
            self.monitor.get_agent_status("non-existent")
        )
        self.assertIsNone(status)
    
    def test_intervention_history(self):
        """Test intervention history tracking."""
        # Trigger some interventions
        self.loop.run_until_complete(
            self.monitor._trigger_intervention(
                InterventionType.THROTTLE,
                "Test throttle"
            )
        )
        
        self.assertEqual(len(self.monitor.intervention_history), 1)
        self.assertEqual(
            self.monitor.intervention_history[0]["type"],
            "throttle"
        )


class TestSafetyMonitorIntegration(unittest.TestCase):
    """Integration tests for Safety Monitor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SafetyMonitor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_monitoring_loop(self):
        """Test the monitoring loop."""
        # Start monitoring
        self.loop.run_until_complete(
            self.monitor.start_monitoring()
        )
        
        self.assertTrue(self.monitor.monitoring)
        
        # Let it run briefly
        time.sleep(0.5)
        
        # Stop monitoring
        self.loop.run_until_complete(
            self.monitor.stop_monitoring()
        )
        
        self.assertFalse(self.monitor.monitoring)
    
    def test_resource_exhaustion_scenario(self):
        """Test handling of resource exhaustion."""
        # Register agents
        for i in range(3):
            self.loop.run_until_complete(
                self.monitor.register_agent(f"test-agent-{i:03d}")
            )
        
        # Simulate high resource usage
        for _ in range(5):
            for i in range(3):
                self.loop.run_until_complete(
                    self.monitor.report_agent_activity(
                        f"test-agent-{i:03d}",
                        cpu=90.0,
                        memory=90.0
                    )
                )
        
        # Check that threats are detected
        self.loop.run_until_complete(
            self.monitor._check_thresholds()
        )
        
        # Should have intervention history
        self.assertGreater(len(self.monitor.intervention_history), 0)
    
    def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures."""
        # Register parent agent
        self.loop.run_until_complete(
            self.monitor.register_agent("parent-agent")
        )
        
        # Try to spawn many child agents rapidly
        for i in range(10):
            self.loop.run_until_complete(
                self.monitor.report_agent_activity(
                    "parent-agent",
                    cpu=30.0,
                    memory=30.0
                )
            )
            
            # Try to register child
            success = self.loop.run_until_complete(
                self.monitor.register_agent(f"child-agent-{i:03d}")
            )
            
            if i < self.monitor.thresholds["agent_limits"]["max_concurrent_agents"] - 1:
                self.assertTrue(success)
            else:
                # Should hit limit
                break
        
        # Verify limits were enforced
        self.assertLessEqual(
            len(self.monitor.agent_monitors),
            self.monitor.thresholds["agent_limits"]["max_concurrent_agents"]
        )


if __name__ == "__main__":
    unittest.main()