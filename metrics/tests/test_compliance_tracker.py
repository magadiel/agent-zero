"""
Test suite for Compliance Tracker
"""

import unittest
import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from metrics.compliance_tracker import (
    ComplianceTracker, Violation, ComplianceThreshold, ComplianceMetrics,
    ViolationType, ViolationSeverity, ViolationStatus, ComplianceStatus
)


class TestComplianceTracker(unittest.TestCase):
    """Test compliance tracker functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_compliance.db')
        self.tracker = ComplianceTracker(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test tracker initialization"""
        self.assertIsNotNone(self.tracker)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertGreater(len(self.tracker.thresholds), 0)
    
    def test_record_violation(self):
        """Test recording a violation"""
        violation = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.HIGH,
            agent_id='test_agent',
            description='Test violation',
            details={'test': 'data'},
            detected_by='test_system'
        )
        
        self.assertIsNotNone(violation)
        self.assertEqual(violation.type, ViolationType.ETHICAL)
        self.assertEqual(violation.severity, ViolationSeverity.HIGH)
        self.assertEqual(violation.status, ViolationStatus.OPEN)
        self.assertEqual(violation.agent_id, 'test_agent')
    
    def test_threshold_violation(self):
        """Test threshold checking"""
        # Test CPU threshold violation
        violation = self.tracker.check_threshold(
            metric='cpu_percent',
            value=95.0,
            agent_id='test_agent',
            team_id='test_team'
        )
        
        self.assertIsNotNone(violation)
        self.assertEqual(violation.type, ViolationType.SAFETY)
        self.assertEqual(violation.severity, ViolationSeverity.MEDIUM)
        self.assertIn('cpu', violation.description.lower())
    
    def test_threshold_no_violation(self):
        """Test threshold when not violated"""
        violation = self.tracker.check_threshold(
            metric='cpu_percent',
            value=50.0,
            agent_id='test_agent'
        )
        
        self.assertIsNone(violation)
    
    def test_update_violation_status(self):
        """Test updating violation status"""
        # Create violation
        violation = self.tracker.record_violation(
            type=ViolationType.SAFETY,
            severity=ViolationSeverity.MEDIUM,
            agent_id='test_agent',
            description='Test violation',
            details={},
            detected_by='test_system'
        )
        
        # Update to resolved
        self.tracker.update_violation_status(
            violation.id,
            ViolationStatus.RESOLVED,
            resolution='Test resolution',
            resolved_by='test_resolver'
        )
        
        # Verify update
        updated = self.tracker.get_violation(violation.id)
        self.assertEqual(updated.status, ViolationStatus.RESOLVED)
        self.assertEqual(updated.resolution, 'Test resolution')
        self.assertEqual(updated.resolved_by, 'test_resolver')
        self.assertIsNotNone(updated.resolved_at)
    
    def test_waive_violation(self):
        """Test waiving a violation"""
        # Create violation
        violation = self.tracker.record_violation(
            type=ViolationType.QUALITY,
            severity=ViolationSeverity.LOW,
            agent_id='test_agent',
            description='Test violation',
            details={},
            detected_by='test_system'
        )
        
        # Waive violation
        self.tracker.update_violation_status(
            violation.id,
            ViolationStatus.WAIVED,
            waiver_reason='Acceptable for testing',
            waived_by='test_admin'
        )
        
        # Verify waiver
        updated = self.tracker.get_violation(violation.id)
        self.assertEqual(updated.status, ViolationStatus.WAIVED)
        self.assertEqual(updated.waiver_reason, 'Acceptable for testing')
        self.assertEqual(updated.waived_by, 'test_admin')
    
    def test_escalate_violation(self):
        """Test escalating a violation"""
        # Create violation
        violation = self.tracker.record_violation(
            type=ViolationType.SECURITY,
            severity=ViolationSeverity.HIGH,
            agent_id='test_agent',
            description='Security breach attempt',
            details={},
            detected_by='security_system'
        )
        
        # Escalate
        self.tracker.escalate_violation(violation.id, 'Requires management attention')
        
        # Verify escalation
        updated = self.tracker.get_violation(violation.id)
        self.assertEqual(updated.status, ViolationStatus.ESCALATED)
    
    def test_get_violations_filtered(self):
        """Test getting violations with filters"""
        # Create multiple violations
        v1 = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.HIGH,
            agent_id='agent_1',
            team_id='team_a',
            description='Violation 1',
            details={},
            detected_by='system'
        )
        
        v2 = self.tracker.record_violation(
            type=ViolationType.SAFETY,
            severity=ViolationSeverity.LOW,
            agent_id='agent_2',
            team_id='team_b',
            description='Violation 2',
            details={},
            detected_by='system'
        )
        
        v3 = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.CRITICAL,
            agent_id='agent_1',
            team_id='team_a',
            description='Violation 3',
            details={},
            detected_by='system'
        )
        
        # Test filters
        ethical_violations = self.tracker.get_violations(type=ViolationType.ETHICAL)
        self.assertEqual(len(ethical_violations), 2)
        
        agent1_violations = self.tracker.get_violations(agent_id='agent_1')
        self.assertEqual(len(agent1_violations), 2)
        
        team_a_violations = self.tracker.get_violations(team_id='team_a')
        self.assertEqual(len(team_a_violations), 2)
        
        critical_violations = self.tracker.get_violations(severity=ViolationSeverity.CRITICAL)
        self.assertEqual(len(critical_violations), 1)
    
    def test_calculate_metrics(self):
        """Test metrics calculation"""
        # Create violations
        v1 = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.HIGH,
            agent_id='agent_1',
            description='Violation 1',
            details={},
            detected_by='system'
        )
        
        v2 = self.tracker.record_violation(
            type=ViolationType.SAFETY,
            severity=ViolationSeverity.MEDIUM,
            agent_id='agent_2',
            description='Violation 2',
            details={},
            detected_by='system'
        )
        
        # Resolve one violation
        self.tracker.update_violation_status(
            v1.id,
            ViolationStatus.RESOLVED,
            resolution='Fixed',
            resolved_by='admin'
        )
        
        # Calculate metrics
        metrics = self.tracker.calculate_metrics()
        
        self.assertEqual(metrics.total_violations, 2)
        self.assertEqual(metrics.open_violations, 1)
        self.assertEqual(metrics.resolved_violations, 1)
        self.assertEqual(metrics.violations_by_type['ethical'], 1)
        self.assertEqual(metrics.violations_by_type['safety'], 1)
        self.assertEqual(metrics.violations_by_severity['high'], 1)
        self.assertEqual(metrics.violations_by_severity['medium'], 1)
        self.assertIsNotNone(metrics.compliance_score)
        self.assertIsNotNone(metrics.compliance_status)
    
    def test_compliance_score_calculation(self):
        """Test compliance score calculation"""
        # No violations - should be 100
        metrics = self.tracker.calculate_metrics()
        self.assertEqual(metrics.compliance_score, 100.0)
        
        # Add critical violation
        self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.CRITICAL,
            agent_id='agent_1',
            description='Critical violation',
            details={},
            detected_by='system'
        )
        
        metrics = self.tracker.calculate_metrics()
        self.assertLess(metrics.compliance_score, 100.0)
        self.assertGreater(metrics.compliance_score, 0.0)
    
    def test_compliance_status_determination(self):
        """Test compliance status determination"""
        # No violations - should be compliant
        metrics = self.tracker.calculate_metrics()
        self.assertEqual(metrics.compliance_status, ComplianceStatus.COMPLIANT)
        
        # Add critical violation
        self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.CRITICAL,
            agent_id='agent_1',
            description='Critical violation',
            details={},
            detected_by='system'
        )
        
        metrics = self.tracker.calculate_metrics()
        self.assertEqual(metrics.compliance_status, ComplianceStatus.CRITICAL)
        
        # Add many open violations
        for i in range(15):
            self.tracker.record_violation(
                type=ViolationType.PERFORMANCE,
                severity=ViolationSeverity.LOW,
                agent_id=f'agent_{i}',
                description=f'Violation {i}',
                details={},
                detected_by='system'
            )
        
        metrics = self.tracker.calculate_metrics()
        self.assertIn(metrics.compliance_status, 
                     [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.CRITICAL])
    
    def test_trends_calculation(self):
        """Test trends calculation"""
        # Create violations over time
        now = datetime.now()
        
        # Old violation
        old_violation = self.tracker.record_violation(
            type=ViolationType.PERFORMANCE,
            severity=ViolationSeverity.LOW,
            agent_id='agent_1',
            description='Old violation',
            details={},
            detected_by='system'
        )
        
        # Recent violation
        recent_violation = self.tracker.record_violation(
            type=ViolationType.PERFORMANCE,
            severity=ViolationSeverity.LOW,
            agent_id='agent_2',
            description='Recent violation',
            details={},
            detected_by='system'
        )
        
        # Calculate metrics
        metrics = self.tracker.calculate_metrics()
        
        self.assertIn('trends', metrics.__dict__)
        self.assertIsInstance(metrics.trends, dict)
        
        # Check for violation rate trends
        if 'violation_rate_7d' in metrics.trends:
            self.assertIsInstance(metrics.trends['violation_rate_7d'], (int, float))
    
    def test_generate_summary(self):
        """Test summary generation"""
        # Create some violations
        self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.HIGH,
            agent_id='agent_1',
            description='Ethical violation',
            details={},
            detected_by='system'
        )
        
        self.tracker.record_violation(
            type=ViolationType.SAFETY,
            severity=ViolationSeverity.CRITICAL,
            agent_id='agent_2',
            description='Safety violation',
            details={},
            detected_by='system'
        )
        
        # Generate summary
        summary = self.tracker.generate_summary()
        
        self.assertIsInstance(summary, str)
        self.assertIn('Compliance Summary', summary)
        self.assertIn('Status', summary)
        self.assertIn('Score', summary)
        self.assertIn('Violations', summary)
        self.assertIn('By Severity', summary)
        self.assertIn('By Type', summary)
    
    def test_export_violations(self):
        """Test violations export"""
        # Create violations
        for i in range(3):
            self.tracker.record_violation(
                type=ViolationType.PERFORMANCE,
                severity=ViolationSeverity.LOW,
                agent_id=f'agent_{i}',
                description=f'Violation {i}',
                details={'index': i},
                detected_by='system'
            )
        
        # Export as JSON
        json_export = self.tracker.export_violations(format='json')
        data = json.loads(json_export)
        self.assertEqual(len(data), 3)
        self.assertIn('id', data[0])
        self.assertIn('type', data[0])
        self.assertIn('severity', data[0])
        
        # Export as CSV
        csv_export = self.tracker.export_violations(format='csv')
        self.assertIn('id,type,severity', csv_export.replace(' ', ''))
        lines = csv_export.strip().split('\n')
        self.assertEqual(len(lines), 4)  # Header + 3 violations
    
    def test_violation_relationships(self):
        """Test related violations"""
        # Create parent violation
        parent = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.HIGH,
            agent_id='agent_1',
            description='Parent violation',
            details={},
            detected_by='system'
        )
        
        # Create related violation
        child = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.MEDIUM,
            agent_id='agent_1',
            description='Related violation',
            details={'parent_id': parent.id},
            detected_by='system'
        )
        
        # Manually set relationship
        child.related_violations = [parent.id]
        
        self.assertIn(parent.id, child.related_violations)
    
    def test_mean_resolution_time(self):
        """Test mean resolution time calculation"""
        # Create and immediately resolve violations
        for i in range(3):
            v = self.tracker.record_violation(
                type=ViolationType.PERFORMANCE,
                severity=ViolationSeverity.LOW,
                agent_id=f'agent_{i}',
                description=f'Violation {i}',
                details={},
                detected_by='system'
            )
            
            # Resolve after different delays
            self.tracker.update_violation_status(
                v.id,
                ViolationStatus.RESOLVED,
                resolution=f'Resolution {i}',
                resolved_by='admin'
            )
        
        # Calculate metrics
        metrics = self.tracker.calculate_metrics()
        
        # Mean resolution time should be very small (near 0)
        if metrics.mean_resolution_time:
            self.assertGreaterEqual(metrics.mean_resolution_time, 0)
            self.assertLess(metrics.mean_resolution_time, 10)  # Less than 10 seconds
    
    def test_custom_thresholds(self):
        """Test loading custom thresholds"""
        # Create custom config
        config_path = os.path.join(self.temp_dir, 'thresholds.json')
        config = {
            'thresholds': {
                'custom_metric': {
                    'category': 'performance',
                    'metric': 'custom_metric',
                    'operator': '>',
                    'value': 100,
                    'severity': 'high',
                    'description': 'Custom metric exceeded',
                    'enabled': True,
                    'auto_escalate': True
                }
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Create tracker with custom config
        tracker = ComplianceTracker(
            db_path=os.path.join(self.temp_dir, 'test2.db'),
            config_path=config_path
        )
        
        # Test custom threshold
        violation = tracker.check_threshold(
            metric='custom_metric',
            value=150,
            agent_id='test_agent'
        )
        
        self.assertIsNotNone(violation)
        self.assertEqual(violation.type, ViolationType.PERFORMANCE)
        self.assertEqual(violation.severity, ViolationSeverity.HIGH)
        self.assertIn('Custom metric', violation.description)


class TestComplianceIntegration(unittest.TestCase):
    """Test compliance tracker integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_compliance.db')
        
        # Create mock components
        self.mock_ethics_engine = MockEthicsEngine()
        self.mock_safety_monitor = MockSafetyMonitor()
        self.mock_audit_logger = MockAuditLogger()
        
        self.tracker = ComplianceTracker(
            db_path=self.db_path,
            ethics_engine=self.mock_ethics_engine,
            safety_monitor=self.mock_safety_monitor,
            audit_logger=self.mock_audit_logger
        )
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_ethics_engine_integration(self):
        """Test integration with ethics engine"""
        # Record ethical violation
        violation = self.tracker.record_violation(
            type=ViolationType.ETHICAL,
            severity=ViolationSeverity.CRITICAL,
            agent_id='test_agent',
            description='Ethical breach',
            details={},
            detected_by='ethics_engine'
        )
        
        # Check audit logger was called
        self.assertTrue(self.mock_audit_logger.logged)
        self.assertEqual(self.mock_audit_logger.last_event_type, 'COMPLIANCE_VIOLATION')
    
    def test_safety_monitor_integration(self):
        """Test integration with safety monitor"""
        # Record critical violation
        violation = self.tracker.record_violation(
            type=ViolationType.SAFETY,
            severity=ViolationSeverity.CRITICAL,
            agent_id='test_agent',
            description='Safety breach',
            details={},
            detected_by='safety_monitor'
        )
        
        # Check safety monitor was alerted
        self.assertTrue(self.mock_safety_monitor.alerted)
        self.assertEqual(self.mock_safety_monitor.last_alert_type, 'compliance_violation')
    
    def test_escalation_integration(self):
        """Test escalation with integrated components"""
        # Create and escalate violation
        violation = self.tracker.record_violation(
            type=ViolationType.SECURITY,
            severity=ViolationSeverity.HIGH,
            agent_id='test_agent',
            description='Security issue',
            details={},
            detected_by='security_system'
        )
        
        self.tracker.escalate_violation(violation.id, 'Requires attention')
        
        # Check integrations
        self.assertTrue(self.mock_audit_logger.logged)
        self.assertTrue(self.mock_safety_monitor.alerted)


class MockEthicsEngine:
    """Mock ethics engine for testing"""
    def __init__(self):
        self.validated = False
        self.last_decision = None


class MockSafetyMonitor:
    """Mock safety monitor for testing"""
    def __init__(self):
        self.alerted = False
        self.last_alert_type = None
        self.last_severity = None
    
    def trigger_alert(self, alert_type, severity, details):
        self.alerted = True
        self.last_alert_type = alert_type
        self.last_severity = severity


class MockAuditLogger:
    """Mock audit logger for testing"""
    def __init__(self):
        self.logged = False
        self.last_event_type = None
        self.last_details = None
    
    def log_event(self, event_type, agent_id, details, severity='INFO'):
        self.logged = True
        self.last_event_type = event_type
        self.last_details = details


if __name__ == '__main__':
    unittest.main()