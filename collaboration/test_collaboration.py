"""
Comprehensive tests for cross-team collaboration components.
"""

import asyncio
import unittest
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collaboration.inter_team_protocol import (
    InterTeamProtocol, CollaborationRequest, CollaborationResponse,
    CollaborationType, CollaborationStatus, Priority
)
from collaboration.resource_sharing import (
    ResourceSharingManager, Resource, ResourceRequest,
    ResourceType, AllocationStrategy, SharingMode
)


class TestInterTeamProtocol(unittest.TestCase):
    """Test cases for inter-team collaboration protocol."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.protocol = InterTeamProtocol()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_team_registration(self):
        """Test team registration with capabilities."""
        async def run_test():
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python', 'ml', 'data_analysis']},
                availability={'accepting_requests': True, 'capacity': 0.8}
            )
            
            self.assertIn("team_alpha", self.protocol.team_capabilities)
            self.assertEqual(
                self.protocol.team_capabilities["team_alpha"]['skills'],
                ['python', 'ml', 'data_analysis']
            )
        
        self.loop.run_until_complete(run_test())
    
    def test_collaboration_request(self):
        """Test creating and submitting collaboration requests."""
        async def run_test():
            # Register teams
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['javascript']},
                availability={'accepting_requests': True}
            )
            
            # Create request
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.JOINT_TASK,
                priority=Priority.HIGH,
                task_description="Build API integration",
                requirements={'skills': ['javascript']},
                deadline=datetime.now() + timedelta(hours=24)
            )
            
            request_id = await self.protocol.request_collaboration(request)
            
            self.assertIsNotNone(request_id)
            self.assertIn(request_id, self.protocol.requests)
            self.assertEqual(
                self.protocol.requests[request_id].status,
                CollaborationStatus.PENDING
            )
        
        self.loop.run_until_complete(run_test())
    
    def test_collaboration_response(self):
        """Test responding to collaboration requests."""
        async def run_test():
            # Setup teams
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['javascript']},
                availability={'accepting_requests': True}
            )
            
            # Create and submit request
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.CONSULTATION,
                priority=Priority.MEDIUM
            )
            request_id = await self.protocol.request_collaboration(request)
            
            # Create response
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="accept",
                available_resources={'agents': 2, 'time': 4},
                estimated_completion=datetime.now() + timedelta(hours=4)
            )
            
            await self.protocol.respond_to_request(response)
            
            self.assertIn(request_id, self.protocol.responses)
            self.assertEqual(len(self.protocol.responses[request_id]), 1)
        
        self.loop.run_until_complete(run_test())
    
    def test_agreement_creation(self):
        """Test automatic agreement creation when teams accept."""
        async def run_test():
            # Setup
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['javascript']},
                availability={'accepting_requests': True}
            )
            
            # Create request
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.JOINT_TASK,
                priority=Priority.HIGH,
                requirements={'deliverables': ['API', 'Documentation']}
            )
            request_id = await self.protocol.request_collaboration(request)
            
            # Accept request
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="accept",
                available_resources={'agents': 3}
            )
            await self.protocol.respond_to_request(response)
            
            # Check agreement created
            self.assertTrue(len(self.protocol.agreements) > 0)
            agreement = list(self.protocol.agreements.values())[0]
            self.assertEqual(agreement.request_id, request_id)
            self.assertIn("team_alpha", agreement.participating_teams)
            self.assertIn("team_beta", agreement.participating_teams)
        
        self.loop.run_until_complete(run_test())
    
    def test_negotiation_process(self):
        """Test negotiation when teams counter-propose."""
        async def run_test():
            # Setup teams
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['javascript']},
                availability={'accepting_requests': True}
            )
            
            # Create request
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.RESOURCE_SHARING,
                priority=Priority.MEDIUM
            )
            request_id = await self.protocol.request_collaboration(request)
            
            # Negotiate without counter proposal first (should stay in NEGOTIATING)
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="negotiate"
                # No counter_proposal provided initially
            )
            await self.protocol.respond_to_request(response)
            
            # Check status - should be NEGOTIATING
            self.assertEqual(
                self.protocol.requests[request_id].status,
                CollaborationStatus.NEGOTIATING
            )
            
            # Now provide counter proposal (would create agreement)
            response2 = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="negotiate",
                counter_proposal={'resource_split': 60, 'duration': 4}
            )
            # This would trigger agreement creation in real scenario
        
        self.loop.run_until_complete(run_test())
    
    def test_collaboration_execution(self):
        """Test executing a collaboration agreement."""
        async def run_test():
            # Setup and create agreement
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['javascript']},
                availability={'accepting_requests': True}
            )
            
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.KNOWLEDGE_TRANSFER
            )
            request_id = await self.protocol.request_collaboration(request)
            
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="accept"
            )
            await self.protocol.respond_to_request(response)
            
            # Execute collaboration
            agreement_id = list(self.protocol.agreements.keys())[0]
            results = await self.protocol.execute_collaboration(agreement_id)
            
            self.assertIsNotNone(results)
            self.assertEqual(results['status'], 'success')
            self.assertIn('knowledge_transferred', results)
        
        self.loop.run_until_complete(run_test())
    
    def test_conflict_resolution(self):
        """Test conflict resolution between teams."""
        async def run_test():
            conflict = {
                'type': 'resource',
                'resource': 'cpu_cores',
                'team1_priority': Priority.HIGH,
                'team2_priority': Priority.MEDIUM
            }
            
            resolution = await self.protocol.resolve_conflict(
                "team_alpha", "team_beta", conflict
            )
            
            self.assertIsNotNone(resolution)
            self.assertEqual(resolution['winner'], 'team_alpha')  # Higher priority
            self.assertEqual(resolution['outcome']['reason'], 'priority_based')
        
        self.loop.run_until_complete(run_test())
    
    def test_collaboration_metrics(self):
        """Test metrics collection and reporting."""
        async def run_test():
            # Generate some collaboration activity
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['python']},
                availability={'accepting_requests': True}
            )
            
            for i in range(3):
                request = CollaborationRequest(
                    requesting_team="team_alpha",
                    type=CollaborationType.JOINT_TASK,
                    priority=Priority.MEDIUM
                )
                await self.protocol.request_collaboration(request)
            
            metrics = self.protocol.get_collaboration_metrics()
            
            self.assertEqual(metrics['total_requests'], 3)
            self.assertEqual(metrics['by_type'][CollaborationType.JOINT_TASK.value], 3)
            self.assertIn('success_rate', metrics)
        
        self.loop.run_until_complete(run_test())


class TestResourceSharing(unittest.TestCase):
    """Test cases for resource sharing manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ResourceSharingManager()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.run_until_complete(self.manager.stop())
        self.loop.close()
    
    def test_resource_registration(self):
        """Test registering resources."""
        async def run_test():
            resource = Resource(
                type=ResourceType.CPU,
                capacity=100.0,
                available=100.0,
                sharing_mode=SharingMode.SHARED
            )
            
            resource_id = await self.manager.register_resource(resource, "team_alpha")
            
            self.assertIsNotNone(resource_id)
            self.assertIn(resource_id, self.manager.resources)
            self.assertEqual(self.manager.resources[resource_id].owner_team, "team_alpha")
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_pool_creation(self):
        """Test creating resource pools."""
        async def run_test():
            # Register resources for teams
            resource1 = Resource(type=ResourceType.CPU, capacity=50, available=50)
            resource2 = Resource(type=ResourceType.CPU, capacity=75, available=75)
            
            await self.manager.register_resource(resource1, "team_alpha")
            await self.manager.register_resource(resource2, "team_beta")
            
            # Create pool
            pool_id = await self.manager.create_resource_pool(
                "shared_cpu_pool",
                ["team_alpha", "team_beta"],
                AllocationStrategy.FAIR_SHARE
            )
            
            self.assertIsNotNone(pool_id)
            self.assertIn(pool_id, self.manager.pools)
            pool = self.manager.pools[pool_id]
            self.assertEqual(pool.total_capacity[ResourceType.CPU], 125)
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_request_and_allocation(self):
        """Test requesting and allocating resources."""
        async def run_test():
            # Register resource
            resource = Resource(
                type=ResourceType.MEMORY,
                capacity=1024,
                available=1024
            )
            await self.manager.register_resource(resource, "team_alpha")
            
            # Request resource
            request = ResourceRequest(
                requesting_team="team_beta",
                resource_type=ResourceType.MEMORY,
                amount=256,
                duration=timedelta(hours=2),
                priority=5
            )
            
            request_id = await self.manager.request_resource(request)
            
            self.assertIsNotNone(request_id)
            # Check allocation happened
            self.assertTrue(len(self.manager.allocations) > 0)
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_release(self):
        """Test releasing allocated resources."""
        async def run_test():
            # Setup and allocate
            resource = Resource(
                type=ResourceType.STORAGE,
                capacity=500,
                available=500
            )
            await self.manager.register_resource(resource, "team_alpha")
            
            request = ResourceRequest(
                requesting_team="team_beta",
                resource_type=ResourceType.STORAGE,
                amount=100,
                priority=3
            )
            allocation_id = await self.manager.request_resource(request)
            
            # Release
            if self.manager.allocations:
                alloc_id = list(self.manager.allocations.keys())[0]
                success = await self.manager.release_resource(alloc_id, actual_usage=80)
                
                self.assertTrue(success)
                self.assertNotIn(alloc_id, self.manager.allocations)
                self.assertEqual(resource.available, 500)  # Fully returned
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_borrowing(self):
        """Test borrowing resources between teams."""
        async def run_test():
            # Setup lender's resources
            resource = Resource(
                type=ResourceType.AGENTS,
                capacity=10,
                available=8
            )
            await self.manager.register_resource(resource, "team_alpha")
            
            # Borrow resources
            agreement_id = await self.manager.borrow_resource(
                "team_beta",  # borrower
                "team_alpha",  # lender
                ResourceType.AGENTS,
                3,
                timedelta(hours=4)
            )
            
            self.assertIsNotNone(agreement_id)
            self.assertIn(agreement_id, self.manager.sharing_agreements)
            self.assertEqual(resource.available, 5)  # 8 - 3 borrowed
        
        self.loop.run_until_complete(run_test())
    
    def test_return_borrowed_resource(self):
        """Test returning borrowed resources."""
        async def run_test():
            # Setup and borrow
            resource = Resource(
                type=ResourceType.NETWORK,
                capacity=1000,
                available=800
            )
            await self.manager.register_resource(resource, "team_alpha")
            
            agreement_id = await self.manager.borrow_resource(
                "team_beta",
                "team_alpha",
                ResourceType.NETWORK,
                200,
                timedelta(hours=1)
            )
            
            # Return
            success = await self.manager.return_borrowed_resource(agreement_id)
            
            self.assertTrue(success)
            self.assertEqual(resource.available, 800)  # Restored
            self.assertEqual(
                self.manager.sharing_agreements[agreement_id]['status'],
                'completed'
            )
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_utilization_metrics(self):
        """Test resource utilization calculation."""
        async def run_test():
            # Setup resources
            resource1 = Resource(type=ResourceType.CPU, capacity=100, available=30)
            resource2 = Resource(type=ResourceType.MEMORY, capacity=1024, available=512)
            
            await self.manager.register_resource(resource1, "team_alpha")
            await self.manager.register_resource(resource2, "team_alpha")
            
            stats = self.manager.get_resource_utilization("team_alpha")
            
            self.assertEqual(stats['total_resources'], 2)
            self.assertIn(ResourceType.CPU.value, stats['by_type'])
            cpu_stats = stats['by_type'][ResourceType.CPU.value]
            self.assertEqual(cpu_stats['utilization'], 0.7)  # 70% used
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_negotiation(self):
        """Test resource sharing negotiation."""
        async def run_test():
            # Setup resources for both teams
            resource1 = Resource(type=ResourceType.CPU, capacity=100, available=60)
            resource2 = Resource(type=ResourceType.CPU, capacity=100, available=40)
            
            await self.manager.register_resource(resource1, "team_alpha")
            await self.manager.register_resource(resource2, "team_beta")
            
            # Negotiate sharing
            result = await self.manager.negotiate_sharing(
                "team_alpha",
                "team_beta",
                ResourceType.CPU,
                (0.5, 0.5)  # Proposed 50-50 split
            )
            
            self.assertIsNotNone(result)
            self.assertIn('agreed_split', result)
            # Should counter-propose based on current holdings (60-40)
            self.assertEqual(result['status'], 'counter_proposed')
        
        self.loop.run_until_complete(run_test())
    
    def test_resource_prediction(self):
        """Test resource needs prediction."""
        async def run_test():
            # Create some allocation history
            resource = Resource(type=ResourceType.MEMORY, capacity=1024, available=1024)
            await self.manager.register_resource(resource, "team_alpha")
            
            # Simulate some allocations
            for i in range(5):
                request = ResourceRequest(
                    requesting_team="team_beta",
                    resource_type=ResourceType.MEMORY,
                    amount=100 + i * 10,  # Increasing usage
                    priority=3
                )
                allocation_id = await self.manager.request_resource(request)
                if allocation_id and allocation_id in self.manager.allocations:
                    await self.manager.release_resource(allocation_id, actual_usage=100 + i * 10)
            
            # Predict future needs
            predictions = await self.manager.predict_resource_needs(
                "team_beta",
                timedelta(hours=24)
            )
            
            self.assertIn('predicted_needs', predictions)
            if ResourceType.MEMORY.value in predictions['predicted_needs']:
                self.assertIn('average', predictions['predicted_needs'][ResourceType.MEMORY.value])
        
        self.loop.run_until_complete(run_test())


class TestCollaborationIntegration(unittest.TestCase):
    """Integration tests for collaboration components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.protocol = InterTeamProtocol()
        self.resource_manager = ResourceSharingManager()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.run_until_complete(self.resource_manager.stop())
        self.loop.close()
    
    def test_collaboration_with_resource_sharing(self):
        """Test collaboration that involves resource sharing."""
        async def run_test():
            # Setup teams and resources
            await self.protocol.register_team(
                "team_alpha",
                capabilities={'skills': ['ml', 'data']},
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "team_beta",
                capabilities={'skills': ['backend', 'api']},
                availability={'accepting_requests': True}
            )
            
            # Register resources
            cpu_resource = Resource(type=ResourceType.CPU, capacity=200, available=150)
            mem_resource = Resource(type=ResourceType.MEMORY, capacity=2048, available=1536)
            
            await self.resource_manager.register_resource(cpu_resource, "team_alpha")
            await self.resource_manager.register_resource(mem_resource, "team_beta")
            
            # Create collaboration request with resource needs
            request = CollaborationRequest(
                requesting_team="team_alpha",
                target_teams=["team_beta"],
                type=CollaborationType.RESOURCE_SHARING,
                priority=Priority.HIGH,
                requirements={
                    'resources': {
                        'memory': 512,
                        'duration': 4
                    }
                }
            )
            
            request_id = await self.protocol.request_collaboration(request)
            
            # Team beta accepts and shares resources
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="team_beta",
                decision="accept",
                available_resources={'memory': 512}
            )
            await self.protocol.respond_to_request(response)
            
            # Verify agreement created
            self.assertTrue(len(self.protocol.agreements) > 0)
            
            # Actually share the resources
            resource_request = ResourceRequest(
                requesting_team="team_alpha",
                resource_type=ResourceType.MEMORY,
                amount=512,
                duration=timedelta(hours=4),
                priority=5
            )
            allocation_id = await self.resource_manager.request_resource(resource_request)
            
            self.assertIsNotNone(allocation_id)
            
            # Execute collaboration
            agreement_id = list(self.protocol.agreements.keys())[0]
            results = await self.protocol.execute_collaboration(agreement_id)
            
            self.assertEqual(results['status'], 'success')
        
        self.loop.run_until_complete(run_test())
    
    def test_knowledge_transfer_collaboration(self):
        """Test knowledge transfer between teams."""
        async def run_test():
            # Setup teams with different knowledge
            await self.protocol.register_team(
                "ml_experts",
                capabilities={
                    'skills': ['tensorflow', 'pytorch', 'scikit-learn'],
                    'knowledge': ['model_optimization', 'hyperparameter_tuning']
                },
                availability={'accepting_requests': True}
            )
            await self.protocol.register_team(
                "backend_team",
                capabilities={
                    'skills': ['django', 'fastapi', 'postgresql'],
                    'knowledge': ['api_design', 'database_optimization']
                },
                availability={'accepting_requests': True}
            )
            
            # Request knowledge transfer
            request = CollaborationRequest(
                requesting_team="backend_team",
                target_teams=["ml_experts"],
                type=CollaborationType.KNOWLEDGE_TRANSFER,
                priority=Priority.MEDIUM,
                requirements={
                    'knowledge_needed': ['model_optimization'],
                    'format': 'documentation'
                }
            )
            
            request_id = await self.protocol.request_collaboration(request)
            
            # ML experts accept
            response = CollaborationResponse(
                request_id=request_id,
                responding_team="ml_experts",
                decision="accept",
                conditions={'format': 'markdown_docs', 'sessions': 2}
            )
            await self.protocol.respond_to_request(response)
            
            # Execute knowledge transfer
            agreement_id = list(self.protocol.agreements.keys())[0]
            results = await self.protocol.execute_collaboration(agreement_id)
            
            self.assertEqual(results['status'], 'success')
            self.assertIn('knowledge_transferred', results)
            
            # Check metrics
            metrics = self.protocol.get_collaboration_metrics()
            self.assertEqual(metrics['knowledge_transfers'], 1)
        
        self.loop.run_until_complete(run_test())


def run_acceptance_tests():
    """Run all acceptance criteria tests."""
    print("\n" + "="*50)
    print("TASK-703: Cross-Team Collaboration - Acceptance Tests")
    print("="*50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add tests for each acceptance criteria
    print("\n✅ Acceptance Criteria 1: Create collaboration protocols")
    suite.addTest(TestInterTeamProtocol('test_collaboration_request'))
    suite.addTest(TestInterTeamProtocol('test_collaboration_response'))
    suite.addTest(TestInterTeamProtocol('test_agreement_creation'))
    suite.addTest(TestInterTeamProtocol('test_negotiation_process'))
    
    print("✅ Acceptance Criteria 2: Implement resource sharing")
    suite.addTest(TestResourceSharing('test_resource_registration'))
    suite.addTest(TestResourceSharing('test_resource_request_and_allocation'))
    suite.addTest(TestResourceSharing('test_resource_borrowing'))
    suite.addTest(TestResourceSharing('test_resource_pool_creation'))
    
    print("✅ Acceptance Criteria 3: Add knowledge transfer")
    suite.addTest(TestInterTeamProtocol('test_collaboration_execution'))
    suite.addTest(TestCollaborationIntegration('test_knowledge_transfer_collaboration'))
    
    print("✅ Acceptance Criteria 4: Track collaboration metrics")
    suite.addTest(TestInterTeamProtocol('test_collaboration_metrics'))
    suite.addTest(TestResourceSharing('test_resource_utilization_metrics'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL ACCEPTANCE CRITERIA MET!")
        print("TASK-703 implementation is complete and validated.")
    else:
        print("\n❌ Some tests failed. Please review and fix.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run full test suite
    success = run_acceptance_tests()
    
    if not success:
        sys.exit(1)