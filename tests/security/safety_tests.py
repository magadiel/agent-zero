"""
Safety Monitor Security Tests

Tests for validating safety thresholds, automatic interventions,
kill switches, and anomaly detection.
"""

import unittest
import asyncio
import json
import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from control.safety_monitor import SafetyMonitor, InterventionType, ThreatType


class SafetyMonitorSecurityTests(unittest.TestCase):
    """Security tests for Safety Monitor"""
    
    def setUp(self):
        """Set up test environment"""
        self.safety_monitor = SafetyMonitor()
        self.safety_monitor.initialize()
    
    def tearDown(self):
        """Clean up after tests"""
        # Reset any emergency stops
        self.safety_monitor.emergency_stopped = False
        self.safety_monitor.circuit_breakers.clear()
    
    # Test 1: Threshold Monitoring
    def test_threshold_breach_detection(self):
        """Test detection of threshold breaches"""
        agent_id = 'test_agent'
        
        # Simulate high resource usage
        self.safety_monitor.resource_usage[agent_id] = {
            'cpu': 95.0,  # Above threshold
            'memory': 85.0,  # Above threshold
            'api_calls': 1000,  # Above threshold
            'timestamp': datetime.now()
        }
        
        result = asyncio.run(self.safety_monitor.check_agent_activity(agent_id))
        self.assertFalse(result['safe'])
        self.assertIn('threshold_breach', result['violations'])
    
    def test_multi_level_threshold_escalation(self):
        """Test multi-level threshold escalation"""
        agent_id = 'test_agent'
        
        # Test different severity levels
        test_cases = [
            ({'cpu': 75}, 'warning'),
            ({'cpu': 85}, 'critical'),
            ({'cpu': 95}, 'emergency')
        ]
        
        for usage, expected_level in test_cases:
            self.safety_monitor.resource_usage[agent_id] = {
                **usage,
                'timestamp': datetime.now()
            }
            
            result = asyncio.run(self.safety_monitor.check_thresholds(agent_id))
            self.assertEqual(result['severity'], expected_level)
    
    # Test 2: Automatic Interventions
    def test_automatic_intervention_on_violation(self):
        """Test automatic interventions trigger on violations"""
        agent_id = 'violating_agent'
        
        # Simulate continuous violations
        for i in range(5):
            self.safety_monitor.resource_usage[agent_id] = {
                'cpu': 95.0,
                'memory': 90.0,
                'timestamp': datetime.now()
            }
            
            result = asyncio.run(self.safety_monitor.monitor_agent(agent_id))
            
            if i >= 2:  # After multiple violations
                self.assertTrue(result['intervention_applied'])
                self.assertIn(result['intervention_type'], 
                            [InterventionType.THROTTLE, 
                             InterventionType.SUSPEND,
                             InterventionType.TERMINATE])
    
    def test_intervention_escalation_path(self):
        """Test intervention escalation from throttle to terminate"""
        agent_id = 'escalating_agent'
        interventions = []
        
        # Simulate sustained violations
        for i in range(10):
            self.safety_monitor.resource_usage[agent_id] = {
                'cpu': 100.0,
                'memory': 95.0,
                'timestamp': datetime.now()
            }
            
            result = asyncio.run(self.safety_monitor.apply_intervention(agent_id))
            interventions.append(result['type'])
        
        # Verify escalation path
        self.assertEqual(interventions[0], InterventionType.THROTTLE)
        self.assertIn(InterventionType.SUSPEND, interventions[2:5])
        self.assertIn(InterventionType.TERMINATE, interventions[5:])
    
    # Test 3: Kill Switches
    def test_emergency_kill_switch(self):
        """Test emergency kill switch functionality"""
        # Trigger emergency stop
        asyncio.run(self.safety_monitor.emergency_stop('CRITICAL_THREAT'))
        
        # Verify all agents are stopped
        self.assertTrue(self.safety_monitor.emergency_stopped)
        
        # Verify no new operations are allowed
        result = asyncio.run(self.safety_monitor.check_agent_activity('any_agent'))
        self.assertFalse(result['safe'])
        self.assertEqual(result['reason'], 'EMERGENCY_STOP_ACTIVE')
    
    def test_graceful_kill_switch(self):
        """Test graceful shutdown with task completion"""
        agent_id = 'graceful_agent'
        
        # Start a task
        self.safety_monitor.active_tasks[agent_id] = {
            'task_id': 'test_task',
            'critical': True,
            'started': datetime.now()
        }
        
        # Trigger graceful shutdown
        asyncio.run(self.safety_monitor.graceful_shutdown(agent_id))
        
        # Verify agent is marked for shutdown but critical task continues
        self.assertIn(agent_id, self.safety_monitor.shutdown_queue)
        self.assertIn('test_task', self.safety_monitor.active_tasks[agent_id])
    
    # Test 4: Circuit Breakers
    def test_circuit_breaker_activation(self):
        """Test circuit breaker activation on repeated failures"""
        agent_id = 'failing_agent'
        
        # Simulate repeated failures
        for i in range(5):
            asyncio.run(self.safety_monitor.record_failure(agent_id, 'test_operation'))
        
        # Check circuit breaker status
        breaker_status = self.safety_monitor.circuit_breakers.get(agent_id, {})
        self.assertEqual(breaker_status.get('state'), 'OPEN')
        
        # Verify operations are blocked
        result = asyncio.run(self.safety_monitor.check_circuit_breaker(agent_id))
        self.assertFalse(result['allowed'])
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after cooldown"""
        agent_id = 'recovering_agent'
        
        # Open circuit breaker
        self.safety_monitor.circuit_breakers[agent_id] = {
            'state': 'OPEN',
            'failures': 5,
            'opened_at': datetime.now() - timedelta(minutes=5)
        }
        
        # Check if breaker transitions to half-open
        result = asyncio.run(self.safety_monitor.check_circuit_breaker(agent_id))
        self.assertEqual(self.safety_monitor.circuit_breakers[agent_id]['state'], 
                        'HALF_OPEN')
        
        # Successful operation should close breaker
        asyncio.run(self.safety_monitor.record_success(agent_id, 'test_operation'))
        self.assertEqual(self.safety_monitor.circuit_breakers[agent_id]['state'], 
                        'CLOSED')
    
    # Test 5: Anomaly Detection
    def test_anomaly_detection_patterns(self):
        """Test detection of anomalous behavior patterns"""
        agent_id = 'anomalous_agent'
        
        # Normal baseline
        for i in range(10):
            self.safety_monitor.record_metric(agent_id, 'api_calls', 10)
        
        # Sudden spike (anomaly)
        self.safety_monitor.record_metric(agent_id, 'api_calls', 1000)
        
        result = asyncio.run(self.safety_monitor.detect_anomaly(agent_id))
        self.assertTrue(result['anomaly_detected'])
        self.assertGreater(result['deviation_score'], 3.0)  # > 3 std deviations
    
    def test_behavioral_anomaly_detection(self):
        """Test detection of behavioral anomalies"""
        agent_id = 'behavioral_agent'
        
        # Establish normal behavior pattern
        normal_actions = ['read_file', 'process_data', 'write_result']
        for action in normal_actions * 10:
            self.safety_monitor.record_action(agent_id, action)
        
        # Anomalous behavior
        anomalous_actions = ['delete_database', 'export_secrets', 'disable_logging']
        for action in anomalous_actions:
            self.safety_monitor.record_action(agent_id, action)
            
        result = asyncio.run(self.safety_monitor.analyze_behavior(agent_id))
        self.assertTrue(result['suspicious'])
        self.assertIn('unusual_action_sequence', result['flags'])
    
    # Test 6: Resource Exhaustion Prevention
    def test_resource_exhaustion_prevention(self):
        """Test prevention of resource exhaustion attacks"""
        agent_id = 'resource_hog'
        
        # Attempt to consume excessive resources
        for i in range(100):
            result = asyncio.run(self.safety_monitor.request_resources(
                agent_id, 
                cpu=50, 
                memory=50
            ))
            
            if i > 10:  # After initial allocations
                self.assertFalse(result['granted'])
                self.assertEqual(result['reason'], 'RESOURCE_EXHAUSTION_PREVENTION')
    
    # Test 7: Threat Detection
    def test_threat_type_classification(self):
        """Test classification of different threat types"""
        test_cases = [
            ('data_exfiltration_attempt', ThreatType.DATA_EXFILTRATION),
            ('privilege_escalation', ThreatType.PRIVILEGE_ESCALATION),
            ('resource_hijacking', ThreatType.RESOURCE_ABUSE),
            ('malicious_code_execution', ThreatType.MALICIOUS_CODE)
        ]
        
        for behavior, expected_threat in test_cases:
            result = asyncio.run(self.safety_monitor.classify_threat(behavior))
            self.assertEqual(result['threat_type'], expected_threat)
            self.assertGreater(result['confidence'], 0.7)
    
    # Test 8: Intervention Validation
    def test_intervention_effectiveness(self):
        """Test that interventions effectively mitigate threats"""
        agent_id = 'mitigated_agent'
        
        # Apply throttling intervention
        asyncio.run(self.safety_monitor.apply_intervention(
            agent_id, 
            InterventionType.THROTTLE
        ))
        
        # Verify resource consumption is limited
        result = asyncio.run(self.safety_monitor.get_resource_limit(agent_id))
        self.assertLess(result['cpu_limit'], 50)
        self.assertLess(result['memory_limit'], 50)
        self.assertLess(result['api_rate_limit'], 100)
    
    # Test 9: Coordinated Response
    def test_coordinated_threat_response(self):
        """Test coordinated response to security threats"""
        threat_event = {
            'type': ThreatType.COORDINATED_ATTACK,
            'agents': ['agent1', 'agent2', 'agent3'],
            'severity': 'CRITICAL'
        }
        
        result = asyncio.run(self.safety_monitor.respond_to_threat(threat_event))
        
        # Verify coordinated response
        self.assertTrue(result['lockdown_initiated'])
        self.assertEqual(len(result['isolated_agents']), 3)
        self.assertTrue(result['alert_sent'])
        self.assertTrue(result['audit_logged'])
    
    # Test 10: Recovery Procedures
    def test_recovery_after_incident(self):
        """Test recovery procedures after security incident"""
        # Simulate incident response
        self.safety_monitor.emergency_stopped = True
        self.safety_monitor.quarantined_agents = {'agent1', 'agent2'}
        
        # Initiate recovery
        result = asyncio.run(self.safety_monitor.initiate_recovery())
        
        # Verify recovery steps
        self.assertTrue(result['diagnostics_complete'])
        self.assertTrue(result['systems_validated'])
        self.assertFalse(self.safety_monitor.emergency_stopped)
        self.assertEqual(len(self.safety_monitor.quarantined_agents), 0)


class SafetyMonitorIntegrationTests(unittest.TestCase):
    """Integration tests for Safety Monitor with other components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.safety_monitor = SafetyMonitor()
        self.safety_monitor.initialize()
    
    def test_integration_with_resource_allocator(self):
        """Test integration between safety monitor and resource allocator"""
        from control.resource_allocator import ResourceAllocator
        
        allocator = ResourceAllocator()
        agent_id = 'test_agent'
        team_id = 'test_team'
        
        # Safety monitor detects high usage
        self.safety_monitor.resource_usage[agent_id] = {
            'cpu': 90.0,
            'memory': 85.0,
            'timestamp': datetime.now()
        }
        
        # Should affect resource allocation
        allocation = allocator.allocate_resources(team_id, {
            'cpu': 50,
            'memory': 50
        })
        
        # Allocation should be restricted due to safety concerns
        self.assertLess(allocation.get('cpu', 0), 50)
    
    def test_integration_with_audit_logger(self):
        """Test integration between safety monitor and audit logger"""
        from control.audit_logger import AuditLogger
        
        audit_logger = AuditLogger()
        agent_id = 'test_agent'
        
        # Trigger safety intervention
        asyncio.run(self.safety_monitor.apply_intervention(
            agent_id, 
            InterventionType.SUSPEND
        ))
        
        # Verify audit log entry
        entries = audit_logger.query(filters={'agent_id': agent_id})
        safety_entries = [e for e in entries if 'safety' in e.get('category', '').lower()]
        self.assertGreater(len(safety_entries), 0)


def run_safety_security_tests():
    """Run all safety monitor security tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(SafetyMonitorSecurityTests))
    suite.addTests(loader.loadTestsFromTestCase(SafetyMonitorIntegrationTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_safety_security_tests()
    sys.exit(0 if success else 1)