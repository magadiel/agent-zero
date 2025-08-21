"""
Resource Limit Security Tests

Tests for validating resource allocation limits, priority queues,
emergency releases, and resource exhaustion prevention.
"""

import unittest
import asyncio
import json
import sys
import os
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from control.resource_allocator import ResourceAllocator, ResourcePool, PriorityLevel as Priority


class ResourceLimitSecurityTests(unittest.TestCase):
    """Security tests for Resource Limits"""
    
    def setUp(self):
        """Set up test environment"""
        self.allocator = ResourceAllocator()
        self.allocator.initialize()
    
    def tearDown(self):
        """Clean up after tests"""
        # Reset all allocations
        self.allocator.reset_all()
    
    # Test 1: Allocation Limits
    def test_allocation_limit_enforcement(self):
        """Test that allocation limits are enforced"""
        team_id = 'test_team'
        
        # Try to allocate more than allowed
        result = self.allocator.allocate_resources(team_id, {
            'cpu': 200,  # Over 100%
            'memory': 64000,  # Over typical limit
            'storage': 10000,  # GB
            'api_calls': 1000000
        })
        
        self.assertFalse(result['success'])
        self.assertEqual(result['reason'], 'EXCEEDS_LIMITS')
        self.assertIsNone(result.get('allocation_id'))
    
    def test_team_specific_limits(self):
        """Test team-specific resource limits"""
        # Different teams have different limits
        test_cases = [
            ('customer_team', {'cpu': 60, 'memory': 32}, True),
            ('operations_team', {'cpu': 80, 'memory': 48}, True),
            ('innovation_team', {'cpu': 100, 'memory': 64}, True),
            ('unknown_team', {'cpu': 120, 'memory': 128}, False)
        ]
        
        for team_id, resources, should_succeed in test_cases:
            result = self.allocator.allocate_resources(team_id, resources)
            self.assertEqual(result['success'], should_succeed, 
                           f"Failed for team {team_id}")
    
    def test_cumulative_allocation_limits(self):
        """Test that cumulative allocations respect total limits"""
        team_id = 'greedy_team'
        allocations = []
        
        # Make multiple small allocations
        for i in range(10):
            result = self.allocator.allocate_resources(team_id, {
                'cpu': 15,
                'memory': 8
            })
            allocations.append(result)
        
        # Later allocations should fail due to cumulative limit
        successful = [a for a in allocations if a['success']]
        failed = [a for a in allocations if not a['success']]
        
        self.assertGreater(len(successful), 0)
        self.assertGreater(len(failed), 0)
        self.assertLess(len(successful), 10)
    
    # Test 2: Priority Queues
    def test_priority_queue_ordering(self):
        """Test that priority queue respects priority levels"""
        # Fill up resources
        self.allocator.allocate_resources('blocker_team', {
            'cpu': 90,
            'memory': 56
        })
        
        # Queue requests with different priorities
        requests = [
            ('low_priority', Priority.LOW, {'cpu': 20}),
            ('critical', Priority.CRITICAL, {'cpu': 20}),
            ('normal', Priority.NORMAL, {'cpu': 20}),
            ('high', Priority.HIGH, {'cpu': 20})
        ]
        
        queued = []
        for team_id, priority, resources in requests:
            result = self.allocator.queue_request(team_id, resources, priority)
            queued.append((team_id, result['queue_position']))
        
        # Critical should be first, then high, normal, low
        positions = {team: pos for team, pos in queued}
        self.assertLess(positions['critical'], positions['high'])
        self.assertLess(positions['high'], positions['normal'])
        self.assertLess(positions['normal'], positions['low_priority'])
    
    def test_priority_preemption(self):
        """Test that critical priority can preempt lower priority allocations"""
        # Allocate to low priority team
        low_result = self.allocator.allocate_resources('low_team', {
            'cpu': 50,
            'memory': 32
        }, priority=Priority.LOW)
        self.assertTrue(low_result['success'])
        
        # Critical request should preempt
        critical_result = self.allocator.allocate_resources('critical_team', {
            'cpu': 60,
            'memory': 40
        }, priority=Priority.CRITICAL, preempt=True)
        
        self.assertTrue(critical_result['success'])
        self.assertIn('low_team', self.allocator.preempted_teams)
    
    # Test 3: Emergency Releases
    def test_emergency_release_mechanism(self):
        """Test emergency release of resources"""
        # Allocate resources to multiple teams
        teams = ['team1', 'team2', 'team3']
        for team in teams:
            self.allocator.allocate_resources(team, {'cpu': 30, 'memory': 16})
        
        # Trigger emergency release
        released = self.allocator.emergency_release(reason='SECURITY_THREAT')
        
        self.assertTrue(released['success'])
        self.assertEqual(len(released['released_teams']), 3)
        self.assertEqual(self.allocator.get_available_resources()['cpu'], 100)
    
    def test_selective_emergency_release(self):
        """Test selective emergency release based on priority"""
        # Allocate with different priorities
        allocations = [
            ('critical_team', Priority.CRITICAL, {'cpu': 30}),
            ('normal_team', Priority.NORMAL, {'cpu': 30}),
            ('low_team', Priority.LOW, {'cpu': 30})
        ]
        
        for team, priority, resources in allocations:
            self.allocator.allocate_resources(team, resources, priority=priority)
        
        # Emergency release should preserve critical allocations
        released = self.allocator.emergency_release(
            preserve_critical=True,
            reason='RESOURCE_SHORTAGE'
        )
        
        self.assertNotIn('critical_team', released['released_teams'])
        self.assertIn('low_team', released['released_teams'])
    
    # Test 4: Resource Exhaustion
    def test_resource_exhaustion_prevention(self):
        """Test prevention of resource exhaustion attacks"""
        attacker_team = 'attacker_team'
        
        # Attempt rapid resource requests
        exhaustion_prevented = False
        for i in range(1000):
            result = self.allocator.allocate_resources(attacker_team, {
                'cpu': 1,
                'memory': 1
            })
            
            if not result['success'] and result['reason'] == 'RATE_LIMIT_EXCEEDED':
                exhaustion_prevented = True
                break
        
        self.assertTrue(exhaustion_prevented)
        self.assertIn(attacker_team, self.allocator.rate_limited_teams)
    
    def test_memory_leak_detection(self):
        """Test detection of memory leak patterns"""
        team_id = 'leaky_team'
        
        # Simulate memory leak pattern (increasing allocations without releases)
        for i in range(10):
            self.allocator.allocate_resources(team_id, {
                'memory': 2 * (i + 1)  # Increasing memory requests
            })
            time.sleep(0.01)
        
        # Check if leak pattern is detected
        result = self.allocator.analyze_allocation_pattern(team_id)
        self.assertTrue(result['leak_suspected'])
        self.assertIn('memory', result['leaked_resources'])
    
    # Test 5: Burst Allocation
    def test_burst_allocation_limits(self):
        """Test burst allocation within limits"""
        team_id = 'burst_team'
        
        # Request burst allocation
        result = self.allocator.request_burst(team_id, {
            'cpu': 90,
            'memory': 56
        }, duration_seconds=5)
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['burst_id'])
        self.assertEqual(result['duration'], 5)
        
        # Verify burst expires
        time.sleep(6)
        current_allocation = self.allocator.get_team_allocation(team_id)
        self.assertLess(current_allocation['cpu'], 90)
    
    def test_burst_allocation_abuse_prevention(self):
        """Test prevention of burst allocation abuse"""
        team_id = 'burst_abuser'
        
        # Request multiple bursts
        burst_results = []
        for i in range(5):
            result = self.allocator.request_burst(team_id, {
                'cpu': 80,
                'memory': 48
            }, duration_seconds=10)
            burst_results.append(result['success'])
        
        # Should prevent excessive burst requests
        self.assertIn(False, burst_results[2:])  # Later requests should fail
    
    # Test 6: Resource Pools
    def test_resource_pool_isolation(self):
        """Test isolation between resource pools"""
        # Allocate from different pools
        prod_result = self.allocator.allocate_from_pool('production', 'prod_team', {
            'cpu': 50,
            'memory': 32
        })
        
        dev_result = self.allocator.allocate_from_pool('development', 'dev_team', {
            'cpu': 80,
            'memory': 48
        })
        
        # Production allocation should not affect development pool
        self.assertTrue(prod_result['success'])
        self.assertTrue(dev_result['success'])
        
        # Verify isolation
        prod_available = self.allocator.get_pool_resources('production')
        dev_available = self.allocator.get_pool_resources('development')
        
        self.assertLess(prod_available['cpu'], 100)
        self.assertLess(dev_available['cpu'], 50)  # Dev pool is smaller
    
    # Test 7: Deadlock Prevention
    def test_deadlock_prevention(self):
        """Test prevention of resource allocation deadlocks"""
        # Create potential deadlock scenario
        team1_phase1 = self.allocator.allocate_resources('team1', {'cpu': 40})
        team2_phase1 = self.allocator.allocate_resources('team2', {'memory': 32})
        
        # Both teams try to get what the other needs
        team1_phase2 = self.allocator.allocate_resources('team1', 
                                                         {'memory': 32}, 
                                                         timeout=1)
        team2_phase2 = self.allocator.allocate_resources('team2', 
                                                         {'cpu': 40}, 
                                                         timeout=1)
        
        # Deadlock prevention should kick in
        prevented = not (team1_phase2['success'] and team2_phase2['success'])
        self.assertTrue(prevented)
    
    # Test 8: Resource Starvation Prevention
    def test_starvation_prevention(self):
        """Test prevention of resource starvation"""
        starving_team = 'starving_team'
        dominant_team = 'dominant_team'
        
        # Dominant team keeps allocating
        for i in range(10):
            self.allocator.allocate_resources(dominant_team, {'cpu': 70})
            time.sleep(0.1)
            self.allocator.release_resources(dominant_team)
            
            # Starving team tries to allocate
            result = self.allocator.allocate_resources(starving_team, {'cpu': 50})
            if result['success']:
                break
        
        # Starvation prevention should eventually allow starving team
        self.assertTrue(result['success'] or 
                       self.allocator.is_prioritized(starving_team))
    
    # Test 9: Concurrent Access
    def test_concurrent_allocation_safety(self):
        """Test thread-safe concurrent resource allocation"""
        successful_allocations = []
        failed_allocations = []
        
        def allocate_resources(team_id):
            result = self.allocator.allocate_resources(team_id, {
                'cpu': 20,
                'memory': 16
            })
            if result['success']:
                successful_allocations.append(team_id)
            else:
                failed_allocations.append(team_id)
        
        # Concurrent allocation attempts
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(allocate_resources, f'team_{i}')
                futures.append(future)
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Verify no over-allocation occurred
        total_cpu = sum([20 for _ in successful_allocations])
        self.assertLessEqual(total_cpu, 100)
    
    # Test 10: Resource Reservation
    def test_resource_reservation_system(self):
        """Test resource reservation for future use"""
        team_id = 'planning_team'
        
        # Reserve resources for future
        reservation = self.allocator.reserve_resources(team_id, {
            'cpu': 50,
            'memory': 32
        }, start_time=datetime.now() + timedelta(hours=1))
        
        self.assertTrue(reservation['success'])
        self.assertIsNotNone(reservation['reservation_id'])
        
        # Verify resources are held
        available = self.allocator.get_available_resources(
            include_reservations=True
        )
        self.assertLess(available['cpu'], 100)


class ResourceAllocatorIntegrationTests(unittest.TestCase):
    """Integration tests for Resource Allocator with other components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.allocator = ResourceAllocator()
        self.allocator.initialize()
    
    def test_integration_with_safety_monitor(self):
        """Test integration between resource allocator and safety monitor"""
        from control.safety_monitor import SafetyMonitor
        
        safety_monitor = SafetyMonitor()
        safety_monitor.initialize()
        
        # Allocate resources
        team_id = 'test_team'
        allocation = self.allocator.allocate_resources(team_id, {
            'cpu': 80,
            'memory': 48
        })
        
        # Safety monitor should be aware of allocation
        usage = safety_monitor.get_team_resource_usage(team_id)
        self.assertEqual(usage['cpu'], 80)
        self.assertEqual(usage['memory'], 48)
    
    def test_integration_with_audit_logger(self):
        """Test integration between resource allocator and audit logger"""
        from control.audit_logger import AuditLogger
        
        audit_logger = AuditLogger()
        team_id = 'audit_team'
        
        # Make allocation
        self.allocator.allocate_resources(team_id, {
            'cpu': 40,
            'memory': 24
        })
        
        # Verify audit trail
        entries = audit_logger.query(filters={'team_id': team_id})
        resource_entries = [e for e in entries if 'resource' in e.get('category', '').lower()]
        self.assertGreater(len(resource_entries), 0)


def run_resource_security_tests():
    """Run all resource limit security tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(ResourceLimitSecurityTests))
    suite.addTests(loader.loadTestsFromTestCase(ResourceAllocatorIntegrationTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_resource_security_tests()
    sys.exit(0 if success else 1)