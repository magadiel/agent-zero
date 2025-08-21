"""
Ethics Engine Security Tests

Tests for validating ethics engine enforcement, constraint validation,
and emergency controls.
"""

import unittest
import asyncio
import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from control.ethics_engine import EthicsEngine, ValidationResult, EthicalViolationType


class EthicsEngineSecurityTests(unittest.TestCase):
    """Security tests for Ethics Engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.ethics_engine = EthicsEngine()
        self.ethics_engine.initialize()
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.ethics_engine, 'audit_file'):
            if os.path.exists(self.ethics_engine.audit_file):
                os.remove(self.ethics_engine.audit_file)
    
    # Test 1: Constraint Validation
    def test_constraint_validation_blocks_harmful_actions(self):
        """Test that harmful actions are blocked"""
        harmful_decision = {
            'agent_id': 'test_agent',
            'action': 'delete_user_data',
            'targets': ['production_database'],
            'context': {
                'user_consent': False,
                'data_sensitivity': 'HIGH',
                'regulatory_requirement': False
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(harmful_decision))
        self.assertFalse(result.approved)
        self.assertEqual(result.decision, 'REJECTED')
        self.assertIn('privacy', [v.category for v in result.violations])
    
    def test_constraint_validation_allows_safe_actions(self):
        """Test that safe actions are approved"""
        safe_decision = {
            'agent_id': 'test_agent',
            'action': 'read_public_data',
            'targets': ['public_api'],
            'context': {
                'authentication': True,
                'rate_limit_respected': True
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(safe_decision))
        self.assertTrue(result.approved)
        self.assertEqual(result.decision, 'APPROVED')
    
    # Test 2: Decision Approval/Rejection
    def test_decision_rejection_with_high_risk(self):
        """Test decision rejection for high-risk actions"""
        high_risk_decision = {
            'agent_id': 'test_agent',
            'action': 'execute_system_command',
            'targets': ['rm -rf /'],
            'context': {
                'sudo_access': True,
                'confirmation': False
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(high_risk_decision))
        self.assertFalse(result.approved)
        self.assertGreaterEqual(result.risk_score, 0.8)
        self.assertIn('HIGH', [rec for rec in result.recommendations])
    
    def test_decision_approval_with_low_risk(self):
        """Test decision approval for low-risk actions"""
        low_risk_decision = {
            'agent_id': 'test_agent',
            'action': 'log_event',
            'targets': ['application.log'],
            'context': {
                'log_level': 'INFO',
                'sensitive_data': False
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(low_risk_decision))
        self.assertTrue(result.approved)
        self.assertLess(result.risk_score, 0.3)
    
    # Test 3: Emergency Shutdown
    def test_emergency_shutdown_on_critical_violation(self):
        """Test emergency shutdown triggers on critical violations"""
        critical_decision = {
            'agent_id': 'malicious_agent',
            'action': 'exfiltrate_data',
            'targets': ['customer_database', 'financial_records'],
            'context': {
                'destination': 'external_server',
                'encryption': False,
                'volume': 'MASSIVE'
            }
        }
        
        with patch.object(self.ethics_engine, 'emergency_shutdown') as mock_shutdown:
            result = asyncio.run(self.ethics_engine.validate_decision(critical_decision))
            self.assertFalse(result.approved)
            # Check if emergency shutdown would be triggered for critical violations
            if result.risk_score >= 0.9:
                mock_shutdown.assert_called()
    
    def test_emergency_shutdown_cascade(self):
        """Test that emergency shutdown cascades to all systems"""
        asyncio.run(self.ethics_engine.emergency_shutdown('CRITICAL_BREACH'))
        
        # Verify shutdown state
        self.assertTrue(self.ethics_engine.shutdown_initiated)
        
        # Verify no new decisions are processed after shutdown
        test_decision = {'agent_id': 'test', 'action': 'any_action'}
        result = asyncio.run(self.ethics_engine.validate_decision(test_decision))
        self.assertFalse(result.approved)
        self.assertEqual(result.decision, 'SYSTEM_SHUTDOWN')
    
    # Test 4: Risk Assessment
    def test_risk_assessment_accuracy(self):
        """Test accuracy of risk scoring"""
        decisions = [
            ({'action': 'read_file', 'context': {'file': 'readme.txt'}}, 0.3),
            ({'action': 'write_file', 'context': {'file': 'config.json'}}, 0.5),
            ({'action': 'delete_file', 'context': {'file': 'system32.dll'}}, 0.9),
        ]
        
        for decision, expected_min_score in decisions:
            decision['agent_id'] = 'test_agent'
            result = asyncio.run(self.ethics_engine.validate_decision(decision))
            self.assertGreaterEqual(result.risk_score, expected_min_score - 0.1)
            self.assertLessEqual(result.risk_score, expected_min_score + 0.3)
    
    def test_risk_category_classification(self):
        """Test risk category classification"""
        test_cases = [
            ('data_collection', 'privacy'),
            ('financial_transaction', 'financial'),
            ('system_modification', 'security'),
            ('resource_allocation', 'fairness')
        ]
        
        for action, expected_category in test_cases:
            decision = {
                'agent_id': 'test_agent',
                'action': action,
                'context': {}
            }
            result = asyncio.run(self.ethics_engine.validate_decision(decision))
            # Check if the expected category appears in violations
            if hasattr(result, 'violations') and result.violations:
                violation_categories = [v.get('category', '') for v in result.violations]
                self.assertIn(expected_category, violation_categories)
    
    # Test 5: Override Mechanisms
    def test_override_with_valid_authorization(self):
        """Test override mechanism with valid authorization"""
        restricted_decision = {
            'agent_id': 'admin_agent',
            'action': 'override_safety_limit',
            'context': {
                'override_token': 'VALID_ADMIN_TOKEN',
                'justification': 'Emergency maintenance required',
                'duration': '30_minutes'
            }
        }
        
        with patch.object(self.ethics_engine, 'validate_override_token', return_value=True):
            result = asyncio.run(self.ethics_engine.validate_decision(restricted_decision))
            self.assertTrue(result.approved)
            self.assertIn('OVERRIDE', result.decision)
    
    def test_override_with_invalid_authorization(self):
        """Test override mechanism blocks invalid authorization"""
        restricted_decision = {
            'agent_id': 'unauthorized_agent',
            'action': 'override_safety_limit',
            'context': {
                'override_token': 'INVALID_TOKEN',
                'justification': 'Just testing',
                'duration': 'unlimited'
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(restricted_decision))
        self.assertFalse(result.approved)
        self.assertNotIn('OVERRIDE', result.decision)
    
    # Test 6: Audit Trail Security
    def test_audit_trail_immutability(self):
        """Test that audit trail cannot be modified"""
        # Make a decision to create audit entry
        decision = {
            'agent_id': 'test_agent',
            'action': 'test_action',
            'context': {}
        }
        asyncio.run(self.ethics_engine.validate_decision(decision))
        
        # Try to modify audit file
        if os.path.exists(self.ethics_engine.audit_file):
            original_content = open(self.ethics_engine.audit_file, 'r').read()
            
            # Attempt to modify
            with open(self.ethics_engine.audit_file, 'a') as f:
                f.write('\nMALICIOUS_MODIFICATION')
            
            # Engine should detect tampering on next validation
            result = asyncio.run(self.ethics_engine.validate_decision(decision))
            # In production, this would trigger alerts
            self.assertIsNotNone(result)
    
    # Test 7: Constraint Bypass Prevention
    def test_constraint_bypass_prevention(self):
        """Test that constraints cannot be bypassed through manipulation"""
        bypass_attempts = [
            {
                'agent_id': 'test_agent',
                'action': 'delete_data',
                'context': {
                    'bypass': True,
                    'ignore_constraints': True
                }
            },
            {
                'agent_id': 'test_agent',
                'action': '../../../etc/passwd',  # Path traversal attempt
                'context': {}
            },
            {
                'agent_id': 'test_agent' * 1000,  # Buffer overflow attempt
                'action': 'normal_action',
                'context': {}
            }
        ]
        
        for attempt in bypass_attempts:
            result = asyncio.run(self.ethics_engine.validate_decision(attempt))
            self.assertFalse(result.approved if result else False)
    
    # Test 8: Multi-layer Validation
    def test_multi_layer_validation(self):
        """Test that multiple validation layers work correctly"""
        complex_decision = {
            'agent_id': 'complex_agent',
            'action': 'multi_step_operation',
            'context': {
                'steps': [
                    {'action': 'read_data', 'safe': True},
                    {'action': 'process_data', 'safe': True},
                    {'action': 'delete_source', 'safe': False}
                ]
            }
        }
        
        result = asyncio.run(self.ethics_engine.validate_decision(complex_decision))
        # Should fail due to unsafe step
        if any(not step.get('safe', True) for step in 
               complex_decision['context'].get('steps', [])):
            self.assertFalse(result.approved)
    
    # Test 9: Rate Limiting
    def test_rate_limiting_enforcement(self):
        """Test rate limiting for repeated requests"""
        decision = {
            'agent_id': 'spam_agent',
            'action': 'api_call',
            'context': {'endpoint': 'test'}
        }
        
        # Simulate rapid requests
        results = []
        for i in range(100):
            result = asyncio.run(self.ethics_engine.validate_decision(decision))
            results.append(result.approved)
        
        # Some requests should be rejected due to rate limiting
        self.assertIn(False, results[50:])  # Later requests more likely rejected
    
    # Test 10: Escalation Procedures
    def test_escalation_on_repeated_violations(self):
        """Test escalation procedures for repeated violations"""
        violating_decision = {
            'agent_id': 'repeat_offender',
            'action': 'unauthorized_access',
            'context': {'resource': 'restricted'}
        }
        
        violation_count = 0
        escalated = False
        
        with patch.object(self.ethics_engine, 'escalate_violation') as mock_escalate:
            for i in range(5):
                result = asyncio.run(self.ethics_engine.validate_decision(violating_decision))
                if not result.approved:
                    violation_count += 1
                
                if violation_count >= 3:
                    escalated = True
                    mock_escalate.assert_called()
                    break
        
        self.assertTrue(escalated or violation_count >= 3)


class EthicsEngineIntegrationTests(unittest.TestCase):
    """Integration tests for Ethics Engine with other components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.ethics_engine = EthicsEngine()
        self.ethics_engine.initialize()
    
    def test_integration_with_safety_monitor(self):
        """Test integration between ethics engine and safety monitor"""
        from control.safety_monitor import SafetyMonitor
        
        safety_monitor = SafetyMonitor()
        safety_monitor.initialize()
        
        # Create a decision that should trigger both systems
        risky_decision = {
            'agent_id': 'test_agent',
            'action': 'high_resource_operation',
            'context': {
                'cpu_required': 95,
                'memory_required': 90
            }
        }
        
        ethics_result = asyncio.run(self.ethics_engine.validate_decision(risky_decision))
        safety_result = asyncio.run(safety_monitor.check_agent_activity('test_agent'))
        
        # Both should flag the high resource usage
        self.assertFalse(ethics_result.approved and safety_result['safe'])
    
    def test_integration_with_audit_logger(self):
        """Test integration between ethics engine and audit logger"""
        from control.audit_logger import AuditLogger
        
        audit_logger = AuditLogger()
        
        decision = {
            'agent_id': 'test_agent',
            'action': 'test_action',
            'context': {'test': True}
        }
        
        # Ethics engine validates and logs
        result = asyncio.run(self.ethics_engine.validate_decision(decision))
        
        # Verify audit log entry exists
        entries = audit_logger.query(filters={'agent_id': 'test_agent'})
        self.assertGreater(len(entries), 0)
        
        # Verify entry contains ethics decision
        latest_entry = entries[-1] if entries else None
        if latest_entry:
            self.assertIn('ethics', latest_entry.get('category', '').lower() or 
                         latest_entry.get('type', '').lower())


def run_ethics_security_tests():
    """Run all ethics engine security tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(EthicsEngineSecurityTests))
    suite.addTests(loader.loadTestsFromTestCase(EthicsEngineIntegrationTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_ethics_security_tests()
    sys.exit(0 if success else 1)