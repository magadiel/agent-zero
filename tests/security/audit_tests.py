"""
Audit Trail Security Tests

Tests for validating audit trail immutability, cryptographic signatures,
hash chain integrity, retention policies, and tamper detection.
"""

import unittest
import asyncio
import json
import sys
import os
import time
import hashlib
import hmac
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from control.audit_logger import AuditLogger, RetentionPolicy


class AuditTrailSecurityTests(unittest.TestCase):
    """Security tests for Audit Trail"""
    
    def setUp(self):
        """Set up test environment"""
        # Use temporary directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_audit.db')
        self.audit_logger = AuditLogger(db_path=self.db_path)
        self.audit_logger.initialize()
    
    def tearDown(self):
        """Clean up after tests"""
        # Close database connection
        if hasattr(self.audit_logger, 'conn'):
            self.audit_logger.conn.close()
        
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    # Test 1: Immutability
    def test_audit_trail_immutability(self):
        """Test that audit entries cannot be modified after creation"""
        # Create an audit entry
        entry_id = self.audit_logger.log_event({
            'event_type': 'test_event',
            'agent_id': 'test_agent',
            'action': 'test_action',
            'result': 'success'
        })
        
        # Try to modify the entry directly in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Attempt to update the entry
        cursor.execute("""
            UPDATE audit_log 
            SET action = 'modified_action' 
            WHERE id = ?
        """, (entry_id,))
        conn.commit()
        conn.close()
        
        # Verify modification is detected
        result = self.audit_logger.verify_integrity()
        self.assertFalse(result['valid'])
        self.assertIn('tampered', result['issues'])
    
    def test_entry_deletion_detection(self):
        """Test detection of deleted audit entries"""
        # Create multiple entries
        entry_ids = []
        for i in range(5):
            entry_id = self.audit_logger.log_event({
                'event_type': f'event_{i}',
                'agent_id': 'test_agent',
                'sequence': i
            })
            entry_ids.append(entry_id)
        
        # Delete an entry directly from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_log WHERE id = ?", (entry_ids[2],))
        conn.commit()
        conn.close()
        
        # Verify deletion is detected
        result = self.audit_logger.verify_integrity()
        self.assertFalse(result['valid'])
        self.assertIn('missing_entry', result['issues'])
    
    # Test 2: Cryptographic Signatures
    def test_cryptographic_signature_validation(self):
        """Test validation of cryptographic signatures"""
        # Log an event with signature
        entry_data = {
            'event_type': 'secure_event',
            'agent_id': 'secure_agent',
            'sensitive_data': 'confidential_information'
        }
        
        entry_id = self.audit_logger.log_event(entry_data)
        
        # Retrieve and verify signature
        entry = self.audit_logger.get_entry(entry_id)
        self.assertIsNotNone(entry['signature'])
        
        # Verify signature is correct
        expected_signature = self.audit_logger.calculate_signature(entry_data)
        self.assertEqual(entry['signature'], expected_signature)
    
    def test_signature_tampering_detection(self):
        """Test detection of tampered signatures"""
        # Create an entry
        entry_id = self.audit_logger.log_event({
            'event_type': 'test_event',
            'agent_id': 'test_agent'
        })
        
        # Tamper with the signature
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_log 
            SET signature = 'tampered_signature' 
            WHERE id = ?
        """, (entry_id,))
        conn.commit()
        conn.close()
        
        # Verify tampering is detected
        result = self.audit_logger.verify_entry_signature(entry_id)
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'SIGNATURE_MISMATCH')
    
    # Test 3: Hash Chain Integrity
    def test_hash_chain_continuity(self):
        """Test hash chain continuity across entries"""
        # Create a chain of entries
        entries = []
        for i in range(10):
            entry_id = self.audit_logger.log_event({
                'event_type': f'chain_event_{i}',
                'sequence': i
            })
            entries.append(entry_id)
        
        # Verify chain integrity
        result = self.audit_logger.verify_hash_chain()
        self.assertTrue(result['valid'])
        self.assertEqual(result['chain_length'], 10)
        self.assertEqual(len(result['broken_links']), 0)
    
    def test_hash_chain_break_detection(self):
        """Test detection of broken hash chain"""
        # Create entries
        for i in range(5):
            self.audit_logger.log_event({
                'event_type': f'event_{i}',
                'sequence': i
            })
        
        # Break the chain by modifying a hash
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_log 
            SET previous_hash = 'broken_hash' 
            WHERE id = 3
        """, (self.db_path,))
        conn.commit()
        conn.close()
        
        # Verify break is detected
        result = self.audit_logger.verify_hash_chain()
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['broken_links']), 0)
    
    # Test 4: Retention Policies
    def test_retention_policy_enforcement(self):
        """Test enforcement of retention policies"""
        # Create entries with different retention policies
        permanent_id = self.audit_logger.log_event({
            'event_type': 'critical_security_event',
            'retention': RetentionPolicy.PERMANENT
        })
        
        short_term_id = self.audit_logger.log_event({
            'event_type': 'debug_event',
            'retention': RetentionPolicy.SHORT_TERM
        })
        
        # Simulate time passage
        with patch('control.audit_logger.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(days=8)
            
            # Apply retention policies
            self.audit_logger.apply_retention_policies()
        
        # Verify permanent entry still exists
        permanent_entry = self.audit_logger.get_entry(permanent_id)
        self.assertIsNotNone(permanent_entry)
        
        # Verify short-term entry is archived/removed
        short_term_entry = self.audit_logger.get_entry(short_term_id)
        self.assertTrue(short_term_entry is None or 
                       short_term_entry.get('archived', False))
    
    def test_retention_policy_override_prevention(self):
        """Test that retention policies cannot be overridden"""
        # Create a permanent entry
        entry_id = self.audit_logger.log_event({
            'event_type': 'permanent_event',
            'retention': RetentionPolicy.PERMANENT
        })
        
        # Try to change retention policy
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_log 
            SET retention_policy = ? 
            WHERE id = ?
        """, (RetentionPolicy.SHORT_TERM.value, entry_id))
        conn.commit()
        conn.close()
        
        # Verify change is detected and rejected
        result = self.audit_logger.verify_retention_compliance()
        self.assertFalse(result['compliant'])
        self.assertIn(entry_id, result['policy_violations'])
    
    # Test 5: Tamper Detection
    def test_comprehensive_tamper_detection(self):
        """Test comprehensive tamper detection mechanisms"""
        # Create baseline entries
        for i in range(5):
            self.audit_logger.log_event({
                'event_type': f'baseline_{i}',
                'data': f'value_{i}'
            })
        
        # Various tampering attempts
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tamper 1: Modify timestamp
        cursor.execute("""
            UPDATE audit_log 
            SET timestamp = datetime('now', '+1 day') 
            WHERE id = 2
        """)
        
        # Tamper 2: Insert backdated entry
        cursor.execute("""
            INSERT INTO audit_log (timestamp, event_type, data, signature, previous_hash)
            VALUES (datetime('now', '-1 day'), 'backdated', 'fake', 'fake_sig', 'fake_hash')
        """)
        
        # Tamper 3: Reorder entries
        cursor.execute("""
            UPDATE audit_log 
            SET id = 999 
            WHERE id = 3
        """)
        
        conn.commit()
        conn.close()
        
        # Run comprehensive tamper detection
        result = self.audit_logger.detect_tampering()
        self.assertFalse(result['clean'])
        self.assertGreater(len(result['tampering_indicators']), 0)
        self.assertIn('timestamp_anomaly', result['tampering_indicators'])
        self.assertIn('sequence_break', result['tampering_indicators'])
    
    def test_real_time_tamper_alerts(self):
        """Test real-time tamper detection and alerting"""
        alert_triggered = False
        
        def alert_handler(alert):
            nonlocal alert_triggered
            alert_triggered = True
        
        # Set up alert handler
        self.audit_logger.set_tamper_alert_handler(alert_handler)
        
        # Create an entry
        entry_id = self.audit_logger.log_event({
            'event_type': 'monitored_event'
        })
        
        # Tamper with the entry
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_log 
            SET data = 'tampered_data' 
            WHERE id = ?
        """, (entry_id,))
        conn.commit()
        conn.close()
        
        # Trigger integrity check
        self.audit_logger.verify_integrity()
        
        # Verify alert was triggered
        self.assertTrue(alert_triggered)
    
    # Test 6: Query Integrity
    def test_query_result_integrity(self):
        """Test integrity of query results"""
        # Create entries
        entry_ids = []
        for i in range(10):
            entry_id = self.audit_logger.log_event({
                'event_type': 'query_test',
                'index': i
            })
            entry_ids.append(entry_id)
        
        # Query entries
        results = self.audit_logger.query(filters={'event_type': 'query_test'})
        
        # Verify all results have valid signatures
        for result in results:
            verification = self.audit_logger.verify_entry_signature(result['id'])
            self.assertTrue(verification['valid'])
        
        # Verify result count matches
        self.assertEqual(len(results), 10)
    
    # Test 7: Backup Integrity
    def test_backup_integrity_verification(self):
        """Test integrity of audit trail backups"""
        # Create entries
        for i in range(5):
            self.audit_logger.log_event({
                'event_type': f'backup_test_{i}'
            })
        
        # Create backup
        backup_path = os.path.join(self.temp_dir, 'backup.json')
        result = self.audit_logger.export_to_file(backup_path)
        self.assertTrue(result['success'])
        
        # Verify backup integrity
        verification = self.audit_logger.verify_backup(backup_path)
        self.assertTrue(verification['valid'])
        self.assertEqual(verification['entry_count'], 5)
        self.assertTrue(verification['signatures_valid'])
        self.assertTrue(verification['chain_intact'])
    
    # Test 8: Access Control
    def test_audit_log_access_control(self):
        """Test access control for audit logs"""
        # Create restricted entry
        entry_id = self.audit_logger.log_event({
            'event_type': 'restricted_event',
            'classification': 'CONFIDENTIAL',
            'access_level': 'ADMIN_ONLY'
        })
        
        # Test access with different permission levels
        access_tests = [
            ('admin', True),
            ('user', False),
            ('auditor', True),
            ('guest', False)
        ]
        
        for role, should_access in access_tests:
            result = self.audit_logger.get_entry(entry_id, requester_role=role)
            if should_access:
                self.assertIsNotNone(result)
            else:
                self.assertTrue(result is None or result.get('access_denied', False))
    
    # Test 9: Forensic Analysis
    def test_forensic_analysis_capabilities(self):
        """Test forensic analysis features"""
        # Create pattern of suspicious activities
        for i in range(3):
            self.audit_logger.log_event({
                'event_type': 'login_attempt',
                'agent_id': 'suspicious_agent',
                'success': False,
                'timestamp': datetime.now() + timedelta(seconds=i)
            })
        
        # Successful breach
        self.audit_logger.log_event({
            'event_type': 'login_attempt',
            'agent_id': 'suspicious_agent',
            'success': True,
            'timestamp': datetime.now() + timedelta(seconds=4)
        })
        
        # Data exfiltration
        self.audit_logger.log_event({
            'event_type': 'data_access',
            'agent_id': 'suspicious_agent',
            'volume': 'large',
            'timestamp': datetime.now() + timedelta(seconds=5)
        })
        
        # Run forensic analysis
        analysis = self.audit_logger.forensic_analysis(
            start_time=datetime.now() - timedelta(minutes=1),
            end_time=datetime.now() + timedelta(minutes=1)
        )
        
        self.assertTrue(analysis['suspicious_patterns_found'])
        self.assertIn('brute_force_attempt', analysis['patterns'])
        self.assertIn('data_exfiltration', analysis['patterns'])
        self.assertEqual(analysis['primary_suspect'], 'suspicious_agent')
    
    # Test 10: Compliance Validation
    def test_compliance_validation(self):
        """Test compliance with audit requirements"""
        # Create entries covering required event types
        required_events = [
            'authentication',
            'authorization',
            'data_access',
            'configuration_change',
            'security_event'
        ]
        
        for event_type in required_events:
            self.audit_logger.log_event({
                'event_type': event_type,
                'compliant': True
            })
        
        # Validate compliance
        compliance = self.audit_logger.validate_compliance({
            'required_event_types': required_events,
            'retention_days': 90,
            'signature_required': True,
            'chain_integrity': True
        })
        
        self.assertTrue(compliance['compliant'])
        self.assertEqual(len(compliance['missing_event_types']), 0)
        self.assertTrue(compliance['retention_compliant'])
        self.assertTrue(compliance['signature_compliant'])
        self.assertTrue(compliance['integrity_compliant'])


class AuditLoggerIntegrationTests(unittest.TestCase):
    """Integration tests for Audit Logger with other components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_audit.db')
        self.audit_logger = AuditLogger(db_path=self.db_path)
        self.audit_logger.initialize()
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.audit_logger, 'conn'):
            self.audit_logger.conn.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_integration_with_ethics_engine(self):
        """Test integration between audit logger and ethics engine"""
        from control.ethics_engine import EthicsEngine
        
        ethics_engine = EthicsEngine()
        ethics_engine.set_audit_logger(self.audit_logger)
        
        # Make ethical decision
        decision = {
            'agent_id': 'test_agent',
            'action': 'test_action'
        }
        
        result = asyncio.run(ethics_engine.validate_decision(decision))
        
        # Verify audit trail
        entries = self.audit_logger.query(filters={'agent_id': 'test_agent'})
        self.assertGreater(len(entries), 0)
        
        # Verify entry contains ethics decision
        latest_entry = entries[-1]
        self.assertIn('ethics', latest_entry.get('category', '').lower())
        self.assertEqual(latest_entry['decision'], result.decision)
    
    def test_integration_with_all_control_components(self):
        """Test comprehensive integration with all control layer components"""
        from control.ethics_engine import EthicsEngine
        from control.safety_monitor import SafetyMonitor
        from control.resource_allocator import ResourceAllocator
        
        # Initialize all components with shared audit logger
        ethics = EthicsEngine()
        safety = SafetyMonitor()
        resources = ResourceAllocator()
        
        for component in [ethics, safety, resources]:
            component.set_audit_logger(self.audit_logger)
            component.initialize()
        
        # Perform actions across all components
        asyncio.run(ethics.validate_decision({
            'agent_id': 'test_agent',
            'action': 'test'
        }))
        
        asyncio.run(safety.check_agent_activity('test_agent'))
        
        resources.allocate_resources('test_team', {
            'cpu': 50,
            'memory': 32
        })
        
        # Verify comprehensive audit trail
        all_entries = self.audit_logger.query()
        
        # Should have entries from all components
        categories = set(e.get('category', '') for e in all_entries)
        self.assertIn('ethics', ' '.join(categories).lower())
        self.assertIn('safety', ' '.join(categories).lower())
        self.assertIn('resource', ' '.join(categories).lower())


def run_audit_security_tests():
    """Run all audit trail security tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(AuditTrailSecurityTests))
    suite.addTests(loader.loadTestsFromTestCase(AuditLoggerIntegrationTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_audit_security_tests()
    sys.exit(0 if success else 1)