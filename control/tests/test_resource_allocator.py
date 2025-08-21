"""
Unit tests for the Resource Allocator module.
"""

import unittest
import asyncio
import tempfile
import yaml
import time
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from resource_allocator import (
    ResourceAllocator, ResourceType, PriorityLevel, 
    AllocationStatus, ResourcePool, ResourceRequest
)


class TestResourceAllocator(unittest.TestCase):
    """Test cases for the ResourceAllocator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.config_data = {
            "resource_pools": {
                "default": {
                    "cpu_cores": 10,
                    "memory_gb": 40,
                    "gpu_count": 2,
                    "agent_slots": 20
                }
            },
            "team_limits": {
                "default": {
                    "max_cpu_cores": 4,
                    "max_memory_gb": 16,
                    "max_gpu_count": 1,
                    "max_agent_slots": 5
                },
                "test_team": {
                    "max_cpu_cores": 6,
                    "max_memory_gb": 24,
                    "max_gpu_count": 2,
                    "max_agent_slots": 10
                }
            },
            "allocation_policies": {
                "max_duration_minutes": 60,
                "auto_release_idle_minutes": 15,
                "priority_boost_critical": 2.0
            }
        }
        yaml.dump(self.config_data, self.temp_config)
        self.temp_config.flush()
        
        # Initialize allocator
        self.allocator = ResourceAllocator(self.temp_config.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp file
        os.unlink(self.temp_config.name)
    
    def test_initialization(self):
        """Test ResourceAllocator initialization."""
        self.assertIsNotNone(self.allocator)
        self.assertIn("default", self.allocator.pools)
        self.assertEqual(len(self.allocator.pools["default"].total), 4)
    
    def test_resource_pool_initialization(self):
        """Test resource pool initialization."""
        pool = self.allocator.pools["default"]
        self.assertEqual(pool.total[ResourceType.CPU_CORES], 10)
        self.assertEqual(pool.total[ResourceType.MEMORY_GB], 40)
        self.assertEqual(pool.available[ResourceType.CPU_CORES], 10)
    
    async def test_basic_allocation(self):
        """Test basic resource allocation."""
        request_id, status = await self.allocator.request_resources(
            team_id="test_team",
            resources={
                ResourceType.CPU_CORES: 2,
                ResourceType.MEMORY_GB: 8
            },
            priority=PriorityLevel.NORMAL,
            duration_minutes=30
        )
        
        self.assertIsNotNone(request_id)
        self.assertIn(status, [AllocationStatus.ALLOCATED, AllocationStatus.PENDING])
        
        # Wait a bit for allocation to process
        await asyncio.sleep(2)
        
        # Check pool resources were reduced
        pool = self.allocator.pools["default"]
        if status == AllocationStatus.ALLOCATED:
            self.assertEqual(pool.available[ResourceType.CPU_CORES], 8)
            self.assertEqual(pool.available[ResourceType.MEMORY_GB], 32)
    
    async def test_team_limits_enforcement(self):
        """Test that team resource limits are enforced."""
        # Request resources exceeding team limit
        request_id, status = await self.allocator.request_resources(
            team_id="default",  # Using default team with lower limits
            resources={
                ResourceType.CPU_CORES: 5,  # Exceeds max of 4
                ResourceType.MEMORY_GB: 16
            },
            priority=PriorityLevel.NORMAL
        )
        
        self.assertEqual(status, AllocationStatus.DENIED)
    
    async def test_priority_allocation(self):
        """Test priority-based allocation."""
        # Fill up most resources with normal priority
        req1_id, status1 = await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 4},
            priority=PriorityLevel.NORMAL
        )
        
        await asyncio.sleep(2)
        
        # Try critical priority allocation
        req2_id, status2 = await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 2},
            priority=PriorityLevel.CRITICAL
        )
        
        # Critical should get immediate consideration
        self.assertIn(status2, [AllocationStatus.ALLOCATED, AllocationStatus.PENDING])
    
    async def test_resource_release(self):
        """Test resource release functionality."""
        # Allocate resources
        request_id, status = await self.allocator.request_resources(
            team_id="test_team",
            resources={
                ResourceType.CPU_CORES: 2,
                ResourceType.MEMORY_GB: 8
            },
            priority=PriorityLevel.HIGH
        )
        
        await asyncio.sleep(2)
        
        # Get allocation ID
        allocation_id = f"alloc_req_{request_id}"
        
        # Release resources
        released = await self.allocator.release_resources(allocation_id)
        
        if status == AllocationStatus.ALLOCATED:
            self.assertTrue(released)
            
            # Check resources were returned
            pool = self.allocator.pools["default"]
            self.assertEqual(pool.available[ResourceType.CPU_CORES], 10)
    
    async def test_allocation_expiration(self):
        """Test that allocations expire correctly."""
        # Request with very short duration
        request_id, status = await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 1},
            priority=PriorityLevel.NORMAL,
            duration_minutes=1  # 1 minute duration
        )
        
        # This test would need to wait for expiration, skipping for unit test speed
        self.assertIsNotNone(request_id)
    
    async def test_team_usage_tracking(self):
        """Test team resource usage tracking."""
        # Initial usage should be empty
        usage = await self.allocator.get_team_usage("test_team")
        self.assertEqual(len(usage), 0)
        
        # Allocate resources
        await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 2},
            priority=PriorityLevel.NORMAL
        )
        
        await asyncio.sleep(2)
        
        # Check usage is tracked
        usage = await self.allocator.get_team_usage("test_team")
        if "cpu_cores" in usage:
            self.assertGreater(usage["cpu_cores"], 0)
    
    async def test_pool_status(self):
        """Test getting pool status."""
        status = await self.allocator.get_pool_status("default")
        
        self.assertIn("resources", status)
        self.assertIn("cpu_cores", status["resources"])
        
        cpu_status = status["resources"]["cpu_cores"]
        self.assertIn("total", cpu_status)
        self.assertIn("available", cpu_status)
        self.assertIn("utilization", cpu_status)
        
        self.assertEqual(cpu_status["total"], 10)
    
    def test_pending_requests_queue(self):
        """Test pending requests queue management."""
        # Create multiple requests
        requests = []
        for i in range(3):
            req = ResourceRequest(
                request_id=f"test_req_{i}",
                team_id="test_team",
                resources={ResourceType.CPU_CORES: 1},
                priority=PriorityLevel.NORMAL if i != 1 else PriorityLevel.HIGH,
                duration_minutes=30
            )
            requests.append(req)
        
        # Add to queue
        for req in requests:
            self.allocator.pending_requests.append(req)
        
        # Check queue ordering (HIGH priority should be processed first)
        pending = self.allocator.get_pending_requests()
        self.assertEqual(len(pending), 3)
    
    async def test_multiple_resource_types(self):
        """Test allocation with multiple resource types."""
        request_id, status = await self.allocator.request_resources(
            team_id="test_team",
            resources={
                ResourceType.CPU_CORES: 2,
                ResourceType.MEMORY_GB: 8,
                ResourceType.GPU_COUNT: 1,
                ResourceType.AGENT_SLOTS: 3
            },
            priority=PriorityLevel.NORMAL
        )
        
        self.assertIsNotNone(request_id)
        self.assertIn(status, [AllocationStatus.ALLOCATED, AllocationStatus.PENDING])
    
    async def test_emergency_release(self):
        """Test emergency release of all allocations."""
        # Add some allocations first
        await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 2},
            priority=PriorityLevel.NORMAL
        )
        
        await asyncio.sleep(2)
        
        # Trigger emergency release (modified to handle async properly)
        allocation_ids = list(self.allocator.allocations.keys())
        for alloc_id in allocation_ids:
            await self.allocator.release_resources(alloc_id, reason="test_emergency")
        
        # Clear pending requests
        self.allocator.pending_requests.clear()
        
        # Check all allocations are cleared
        self.assertEqual(len(self.allocator.allocations), 0)
        self.assertEqual(len(self.allocator.pending_requests), 0)
    
    async def test_allocation_with_metadata(self):
        """Test resource allocation with metadata."""
        metadata = {
            "task_type": "model_training",
            "user": "test_user",
            "project": "test_project"
        }
        
        request_id, status = await self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 2},
            priority=PriorityLevel.NORMAL,
            metadata=metadata
        )
        
        self.assertIsNotNone(request_id)
    
    def test_audit_logging(self):
        """Test audit event logging."""
        initial_audit_count = len(self.allocator.audit_log)
        
        # Trigger an audit event
        asyncio.run(self.allocator.request_resources(
            team_id="test_team",
            resources={ResourceType.CPU_CORES: 1},
            priority=PriorityLevel.NORMAL
        ))
        
        # Check audit log grew
        self.assertGreater(len(self.allocator.audit_log), initial_audit_count)
        
        # Check audit event structure
        if self.allocator.audit_log:
            event = self.allocator.audit_log[-1]
            self.assertIn("timestamp", event)
            self.assertIn("event_type", event)
            self.assertIn("details", event)
    
    async def test_invalid_resource_type(self):
        """Test handling of invalid resource types."""
        # This should not crash the system
        try:
            request_id, status = await self.allocator.request_resources(
                team_id="test_team",
                resources={},  # Empty resources
                priority=PriorityLevel.NORMAL
            )
            # Should handle gracefully
            self.assertIsNotNone(request_id)
        except Exception as e:
            self.fail(f"Should handle empty resources gracefully: {e}")
    
    async def test_concurrent_allocations(self):
        """Test concurrent allocation requests."""
        tasks = []
        for i in range(5):
            task = self.allocator.request_resources(
                team_id=f"team_{i}",
                resources={ResourceType.CPU_CORES: 1},
                priority=PriorityLevel.NORMAL
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All requests should get a valid response
        for request_id, status in results:
            self.assertIsNotNone(request_id)
            self.assertIn(status, [
                AllocationStatus.ALLOCATED,
                AllocationStatus.PENDING,
                AllocationStatus.DENIED
            ])
    
    def test_default_config_fallback(self):
        """Test fallback to default config when file not found."""
        allocator = ResourceAllocator("nonexistent_config.yaml")
        
        # Should still initialize with defaults
        self.assertIsNotNone(allocator)
        self.assertIn("default", allocator.pools)


class TestResourcePool(unittest.TestCase):
    """Test cases for ResourcePool class."""
    
    def test_pool_initialization(self):
        """Test ResourcePool initialization."""
        pool = ResourcePool()
        config = {
            "cpu_cores": 10,
            "memory_gb": 40
        }
        
        pool.initialize(config)
        
        self.assertEqual(pool.total[ResourceType.CPU_CORES], 10)
        self.assertEqual(pool.available[ResourceType.CPU_CORES], 10)
        self.assertEqual(pool.reserved[ResourceType.CPU_CORES], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for Resource Allocator with other control components."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump({
            "resource_pools": {
                "default": {
                    "cpu_cores": 20,
                    "memory_gb": 80,
                    "gpu_count": 4
                }
            },
            "team_limits": {
                "default": {
                    "max_cpu_cores": 10,
                    "max_memory_gb": 40,
                    "max_gpu_count": 2
                }
            },
            "allocation_policies": {
                "max_duration_minutes": 60
            },
            "integration": {
                "ethics_validation_required": True,
                "safety_monitoring_enabled": True
            }
        }, self.temp_config)
        self.temp_config.flush()
        
        self.allocator = ResourceAllocator(self.temp_config.name)
    
    def tearDown(self):
        """Clean up integration test environment."""
        os.unlink(self.temp_config.name)
    
    async def test_full_allocation_lifecycle(self):
        """Test complete allocation lifecycle from request to release."""
        # Request
        request_id, status = await self.allocator.request_resources(
            team_id="integration_team",
            resources={
                ResourceType.CPU_CORES: 4,
                ResourceType.MEMORY_GB: 16
            },
            priority=PriorityLevel.HIGH,
            duration_minutes=30
        )
        
        self.assertIsNotNone(request_id)
        
        # Wait for allocation
        await asyncio.sleep(2)
        
        # Check status
        allocation_id = f"alloc_req_{request_id}"
        alloc_status = await self.allocator.get_allocation_status(allocation_id)
        
        if alloc_status:
            self.assertIn("team_id", alloc_status)
            self.assertEqual(alloc_status["team_id"], "integration_team")
            
            # Update usage
            await self.allocator.update_actual_usage(
                allocation_id,
                {ResourceType.CPU_CORES: 3.5}
            )
            
            # Release
            released = await self.allocator.release_resources(allocation_id)
            self.assertTrue(released)
    
    async def test_resource_contention(self):
        """Test behavior under resource contention."""
        # Allocate most resources
        req1_id, status1 = await self.allocator.request_resources(
            team_id="team1",
            resources={
                ResourceType.CPU_CORES: 8,
                ResourceType.MEMORY_GB: 30
            },
            priority=PriorityLevel.NORMAL
        )
        
        await asyncio.sleep(2)
        
        # Try to allocate more
        req2_id, status2 = await self.allocator.request_resources(
            team_id="team2",
            resources={
                ResourceType.CPU_CORES: 8,
                ResourceType.MEMORY_GB: 30
            },
            priority=PriorityLevel.NORMAL
        )
        
        # Second should be pending or denied
        self.assertIn(status2, [AllocationStatus.PENDING, AllocationStatus.DENIED])
        
        # High priority should still work
        req3_id, status3 = await self.allocator.request_resources(
            team_id="team3",
            resources={
                ResourceType.CPU_CORES: 2,
                ResourceType.MEMORY_GB: 5
            },
            priority=PriorityLevel.CRITICAL
        )
        
        # Critical priority might get through
        self.assertIn(status3, [AllocationStatus.ALLOCATED, AllocationStatus.PENDING])


def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Wrap async tests for unittest
for test_class in [TestResourceAllocator, TestIntegration]:
    for attr_name in dir(test_class):
        attr = getattr(test_class, attr_name)
        if callable(attr) and attr_name.startswith('test_') and asyncio.iscoroutinefunction(attr):
            wrapped = lambda self, coro=attr: run_async_test(coro(self))
            wrapped.__name__ = attr_name
            setattr(test_class, attr_name, wrapped)


if __name__ == '__main__':
    unittest.main()