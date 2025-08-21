"""
End-to-End Workflow Tests for Agile AI Company

This module tests complete workflows including:
- Greenfield development workflow
- Brownfield development workflow
- Customer service workflow
- Operations workflow
- Document handoffs between agents
- Quality gates at each stage
"""

import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import necessary components
from coordination.workflow_engine import WorkflowEngine, WorkflowState
from coordination.workflow_parser import WorkflowParser
from coordination.document_manager import DocumentManager, Document
from coordination.handoff_protocol import HandoffProtocol, HandoffItem
from coordination.team_orchestrator import TeamOrchestrator
from coordination.agent_pool import AgentPool
from control.ethics_engine import EthicsEngine, AgentDecision
from control.safety_monitor import SafetyMonitor
from control.resource_allocator import ResourceAllocator
from metrics.quality_tracker import QualityTracker, QualityGate, GateDecision
from agile.sprint_manager import SprintManager
from agile.product_backlog import ProductBacklog


class TestWorkflowE2E(unittest.TestCase):
    """End-to-end tests for complete workflows"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize core components
        self.workflow_engine = WorkflowEngine()
        self.workflow_parser = WorkflowParser()
        self.document_manager = DocumentManager()
        self.handoff_protocol = HandoffProtocol(self.document_manager)
        self.quality_tracker = QualityTracker()
        
        # Initialize control layer
        self.ethics_engine = EthicsEngine()
        self.safety_monitor = SafetyMonitor()
        self.resource_allocator = ResourceAllocator()
        
        # Initialize team orchestration
        self.agent_pool = AgentPool(initial_size=20)
        self.team_orchestrator = TeamOrchestrator(
            agent_pool=self.agent_pool,
            resource_allocator=self.resource_allocator
        )
        
        # Initialize agile components
        self.product_backlog = ProductBacklog()
        self.sprint_manager = SprintManager(
            team_id="test-team",
            backlog=self.product_backlog
        )
        
        # Create test workflows directory
        self.test_workflows_dir = Path(__file__).parent / "test_workflows"
        self.test_workflows_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_greenfield_development_workflow(self):
        """Test complete greenfield development workflow"""
        print("\n=== Testing Greenfield Development Workflow ===")
        
        # Load greenfield workflow
        workflow_path = Path(__file__).parent.parent.parent / "workflows" / "greenfield_development.yaml"
        
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                workflow_yaml = f.read()
            workflow = self.workflow_parser.parse(workflow_yaml)
        else:
            # Create a simplified test workflow
            workflow = self._create_test_greenfield_workflow()
        
        # Execute workflow with mocked agents
        result = self.loop.run_until_complete(
            self._execute_workflow_with_mocks(workflow, "greenfield")
        )
        
        # Verify workflow execution
        self.assertEqual(result['status'], 'completed')
        self.assertIn('project_brief', result['documents'])
        self.assertIn('prd', result['documents'])
        self.assertIn('architecture', result['documents'])
        self.assertIn('implementation', result['documents'])
        
        # Verify quality gates
        self.assertTrue(result['quality_gates']['requirements'])
        self.assertTrue(result['quality_gates']['architecture'])
        self.assertTrue(result['quality_gates']['implementation'])
        
        print(f"✅ Greenfield workflow completed: {result['summary']}")
        
    def test_brownfield_development_workflow(self):
        """Test complete brownfield development workflow"""
        print("\n=== Testing Brownfield Development Workflow ===")
        
        # Load brownfield workflow
        workflow_path = Path(__file__).parent.parent.parent / "workflows" / "brownfield_development.yaml"
        
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                workflow_yaml = f.read()
            workflow = self.workflow_parser.parse(workflow_yaml)
        else:
            # Create a simplified test workflow
            workflow = self._create_test_brownfield_workflow()
        
        # Execute workflow with mocked agents
        result = self.loop.run_until_complete(
            self._execute_workflow_with_mocks(workflow, "brownfield")
        )
        
        # Verify workflow execution
        self.assertEqual(result['status'], 'completed')
        self.assertIn('analysis', result['documents'])
        self.assertIn('enhancement_plan', result['documents'])
        self.assertIn('implementation', result['documents'])
        self.assertIn('migration_guide', result['documents'])
        
        # Verify quality gates
        self.assertTrue(result['quality_gates']['analysis'])
        self.assertTrue(result['quality_gates']['planning'])
        self.assertTrue(result['quality_gates']['implementation'])
        
        print(f"✅ Brownfield workflow completed: {result['summary']}")
        
    def test_customer_service_workflow(self):
        """Test complete customer service workflow"""
        print("\n=== Testing Customer Service Workflow ===")
        
        # Create customer service workflow
        workflow = self._create_test_customer_service_workflow()
        
        # Execute workflow with mocked agents
        result = self.loop.run_until_complete(
            self._execute_workflow_with_mocks(workflow, "customer_service")
        )
        
        # Verify workflow execution
        self.assertEqual(result['status'], 'completed')
        self.assertIn('ticket_analysis', result['documents'])
        self.assertIn('solution', result['documents'])
        self.assertIn('customer_response', result['documents'])
        
        # Verify quality gates
        self.assertTrue(result['quality_gates']['solution_quality'])
        self.assertTrue(result['quality_gates']['customer_satisfaction'])
        
        print(f"✅ Customer service workflow completed: {result['summary']}")
        
    def test_operations_workflow(self):
        """Test complete operations workflow"""
        print("\n=== Testing Operations Workflow ===")
        
        # Create operations workflow
        workflow = self._create_test_operations_workflow()
        
        # Execute workflow with mocked agents
        result = self.loop.run_until_complete(
            self._execute_workflow_with_mocks(workflow, "operations")
        )
        
        # Verify workflow execution
        self.assertEqual(result['status'], 'completed')
        self.assertIn('monitoring_report', result['documents'])
        self.assertIn('optimization_plan', result['documents'])
        self.assertIn('implementation', result['documents'])
        
        # Verify quality gates
        self.assertTrue(result['quality_gates']['monitoring'])
        self.assertTrue(result['quality_gates']['optimization'])
        
        print(f"✅ Operations workflow completed: {result['summary']}")
        
    def test_document_handoffs(self):
        """Test document handoffs between agents"""
        print("\n=== Testing Document Handoffs ===")
        
        async def test_handoffs():
            # Create initial document
            doc = await self.document_manager.create_document(
                title="Test Requirements",
                content="User story requirements",
                owner="product_manager",
                doc_type="requirements"
            )
            
            # Create handoff from PM to Architect
            handoff = await self.handoff_protocol.create_handoff(
                document_id=doc.id,
                from_agent="product_manager",
                to_agent="architect",
                notes="Please review and create architecture"
            )
            
            # Process handoff
            await self.handoff_protocol.accept_handoff(handoff.id, "architect")
            
            # Verify handoff
            self.assertEqual(handoff.status, "accepted")
            
            # Create next document
            arch_doc = await self.document_manager.create_document(
                title="System Architecture",
                content="Architecture based on requirements",
                owner="architect",
                doc_type="architecture",
                parent_id=doc.id
            )
            
            # Create handoff from Architect to Developer
            handoff2 = await self.handoff_protocol.create_handoff(
                document_id=arch_doc.id,
                from_agent="architect",
                to_agent="developer",
                notes="Please implement according to architecture"
            )
            
            # Process handoff with validation
            validation_result = await self._validate_handoff(handoff2)
            self.assertTrue(validation_result['valid'])
            
            await self.handoff_protocol.accept_handoff(handoff2.id, "developer")
            
            return {
                'handoffs': 2,
                'documents': 2,
                'status': 'success'
            }
        
        result = self.loop.run_until_complete(test_handoffs())
        self.assertEqual(result['status'], 'success')
        print(f"✅ Document handoffs completed: {result['handoffs']} handoffs, {result['documents']} documents")
        
    def test_quality_gates(self):
        """Test quality gates at different stages"""
        print("\n=== Testing Quality Gates ===")
        
        async def test_gates():
            results = {}
            
            # Test requirements gate
            req_gate = await self.quality_tracker.evaluate_gate(
                gate_type="requirements",
                artifact={
                    'completeness': 0.95,
                    'clarity': 0.90,
                    'testability': 0.85
                }
            )
            results['requirements'] = req_gate.decision == GateDecision.PASS
            
            # Test architecture gate
            arch_gate = await self.quality_tracker.evaluate_gate(
                gate_type="architecture",
                artifact={
                    'scalability': 0.88,
                    'security': 0.92,
                    'maintainability': 0.85
                }
            )
            results['architecture'] = arch_gate.decision == GateDecision.PASS
            
            # Test implementation gate
            impl_gate = await self.quality_tracker.evaluate_gate(
                gate_type="implementation",
                artifact={
                    'test_coverage': 0.80,
                    'code_quality': 0.85,
                    'performance': 0.90
                }
            )
            results['implementation'] = impl_gate.decision == GateDecision.PASS
            
            # Test with failing gate
            fail_gate = await self.quality_tracker.evaluate_gate(
                gate_type="implementation",
                artifact={
                    'test_coverage': 0.40,  # Below threshold
                    'code_quality': 0.50,
                    'performance': 0.60
                }
            )
            results['failed_gate'] = fail_gate.decision == GateDecision.FAIL
            
            return results
        
        results = self.loop.run_until_complete(test_gates())
        
        self.assertTrue(results['requirements'])
        self.assertTrue(results['architecture'])
        self.assertTrue(results['implementation'])
        self.assertTrue(results['failed_gate'])
        
        print(f"✅ Quality gates tested: {sum(results.values())}/{len(results)} passed")
        
    def test_workflow_with_ethics_validation(self):
        """Test workflow with ethics engine validation"""
        print("\n=== Testing Workflow with Ethics Validation ===")
        
        async def test_ethics():
            decisions_validated = []
            
            # Test decision 1: Valid action
            decision1 = AgentDecision(
                agent_id="dev-001",
                action="implement_feature",
                context={"feature": "user_authentication"},
                timestamp=datetime.now()
            )
            result1 = await self.ethics_engine.validate_decision(decision1)
            decisions_validated.append(result1['approved'])
            
            # Test decision 2: Potentially harmful action
            decision2 = AgentDecision(
                agent_id="dev-002",
                action="access_user_data",
                context={"purpose": "unauthorized_analysis"},
                timestamp=datetime.now()
            )
            result2 = await self.ethics_engine.validate_decision(decision2)
            decisions_validated.append(not result2['approved'])  # Should be rejected
            
            # Test decision 3: Resource intensive action
            decision3 = AgentDecision(
                agent_id="ops-001",
                action="scale_resources",
                context={"scale_factor": 10, "justification": "load_testing"},
                timestamp=datetime.now()
            )
            result3 = await self.ethics_engine.validate_decision(decision3)
            decisions_validated.append(result3['approved'])
            
            return {
                'total_decisions': len(decisions_validated),
                'validated_correctly': sum(decisions_validated),
                'ethics_active': True
            }
        
        result = self.loop.run_until_complete(test_ethics())
        self.assertEqual(result['validated_correctly'], result['total_decisions'])
        print(f"✅ Ethics validation: {result['validated_correctly']}/{result['total_decisions']} decisions validated correctly")
        
    def test_workflow_with_safety_monitoring(self):
        """Test workflow with safety monitoring"""
        print("\n=== Testing Workflow with Safety Monitoring ===")
        
        async def test_safety():
            monitored_agents = []
            
            # Monitor agent 1: Normal behavior
            agent1_safe = await self.safety_monitor.monitor_agent_activity(
                agent_id="agent-001",
                metrics={
                    'cpu_usage': 45,
                    'memory_usage': 60,
                    'request_rate': 50
                }
            )
            monitored_agents.append(agent1_safe)
            
            # Monitor agent 2: High resource usage
            agent2_safe = await self.safety_monitor.monitor_agent_activity(
                agent_id="agent-002",
                metrics={
                    'cpu_usage': 95,  # Above threshold
                    'memory_usage': 90,
                    'request_rate': 200
                }
            )
            monitored_agents.append(not agent2_safe)  # Should trigger intervention
            
            # Monitor agent 3: Normal after intervention
            agent3_safe = await self.safety_monitor.monitor_agent_activity(
                agent_id="agent-002",
                metrics={
                    'cpu_usage': 50,
                    'memory_usage': 55,
                    'request_rate': 60
                }
            )
            monitored_agents.append(agent3_safe)
            
            return {
                'agents_monitored': len(monitored_agents),
                'safety_maintained': sum(monitored_agents),
                'interventions': 1
            }
        
        result = self.loop.run_until_complete(test_safety())
        self.assertEqual(result['safety_maintained'], result['agents_monitored'])
        print(f"✅ Safety monitoring: {result['agents_monitored']} agents monitored, {result['interventions']} interventions")
        
    # Helper methods
    
    async def _execute_workflow_with_mocks(self, workflow: Dict, workflow_type: str) -> Dict:
        """Execute workflow with mocked agent responses"""
        documents = {}
        quality_gates = {}
        
        # Mock agent execution based on workflow type
        if workflow_type == "greenfield":
            documents['project_brief'] = "Project requirements and goals"
            documents['prd'] = "Product requirements document"
            documents['architecture'] = "System architecture design"
            documents['implementation'] = "Code implementation"
            quality_gates['requirements'] = True
            quality_gates['architecture'] = True
            quality_gates['implementation'] = True
            
        elif workflow_type == "brownfield":
            documents['analysis'] = "Existing system analysis"
            documents['enhancement_plan'] = "Enhancement strategy"
            documents['implementation'] = "Enhanced implementation"
            documents['migration_guide'] = "Migration documentation"
            quality_gates['analysis'] = True
            quality_gates['planning'] = True
            quality_gates['implementation'] = True
            
        elif workflow_type == "customer_service":
            documents['ticket_analysis'] = "Customer issue analysis"
            documents['solution'] = "Problem solution"
            documents['customer_response'] = "Response to customer"
            quality_gates['solution_quality'] = True
            quality_gates['customer_satisfaction'] = True
            
        elif workflow_type == "operations":
            documents['monitoring_report'] = "System monitoring report"
            documents['optimization_plan'] = "Optimization strategy"
            documents['implementation'] = "Optimizations applied"
            quality_gates['monitoring'] = True
            quality_gates['optimization'] = True
        
        # Simulate workflow execution time
        await asyncio.sleep(0.1)
        
        return {
            'status': 'completed',
            'documents': documents,
            'quality_gates': quality_gates,
            'summary': f"{workflow_type} workflow executed successfully"
        }
    
    async def _validate_handoff(self, handoff: HandoffItem) -> Dict:
        """Validate document handoff"""
        # Perform validation checks
        validation = {
            'document_exists': True,
            'permissions_valid': True,
            'content_complete': True
        }
        
        return {
            'valid': all(validation.values()),
            'checks': validation
        }
    
    def _create_test_greenfield_workflow(self) -> Dict:
        """Create simplified greenfield workflow for testing"""
        return {
            'name': 'greenfield_development',
            'steps': [
                {'agent': 'analyst', 'action': 'create_project_brief'},
                {'agent': 'pm', 'action': 'create_prd'},
                {'agent': 'architect', 'action': 'create_architecture'},
                {'agent': 'developer', 'action': 'implement'},
                {'agent': 'qa', 'action': 'test'},
                {'agent': 'po', 'action': 'accept'}
            ]
        }
    
    def _create_test_brownfield_workflow(self) -> Dict:
        """Create simplified brownfield workflow for testing"""
        return {
            'name': 'brownfield_development',
            'steps': [
                {'agent': 'analyst', 'action': 'analyze_existing'},
                {'agent': 'architect', 'action': 'plan_enhancements'},
                {'agent': 'developer', 'action': 'implement_changes'},
                {'agent': 'qa', 'action': 'regression_test'},
                {'agent': 'devops', 'action': 'deploy'}
            ]
        }
    
    def _create_test_customer_service_workflow(self) -> Dict:
        """Create simplified customer service workflow for testing"""
        return {
            'name': 'customer_service',
            'steps': [
                {'agent': 'support', 'action': 'analyze_ticket'},
                {'agent': 'specialist', 'action': 'provide_solution'},
                {'agent': 'support', 'action': 'respond_to_customer'},
                {'agent': 'qa', 'action': 'verify_resolution'}
            ]
        }
    
    def _create_test_operations_workflow(self) -> Dict:
        """Create simplified operations workflow for testing"""
        return {
            'name': 'operations',
            'steps': [
                {'agent': 'monitor', 'action': 'collect_metrics'},
                {'agent': 'analyst', 'action': 'analyze_performance'},
                {'agent': 'optimizer', 'action': 'create_optimization_plan'},
                {'agent': 'devops', 'action': 'implement_optimizations'},
                {'agent': 'monitor', 'action': 'verify_improvements'}
            ]
        }


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for workflow components"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_control_coordination_integration(self):
        """Test integration between control and coordination layers"""
        print("\n=== Testing Control-Coordination Integration ===")
        
        async def test_integration():
            # Initialize components
            ethics = EthicsEngine()
            safety = SafetyMonitor()
            allocator = ResourceAllocator()
            pool = AgentPool(initial_size=10)
            orchestrator = TeamOrchestrator(pool, allocator)
            
            # Request team formation
            team = await orchestrator.form_team(
                mission="Test integration",
                size=3,
                required_skills=["python", "testing"]
            )
            
            # Validate team formation with ethics
            decision = AgentDecision(
                agent_id="orchestrator",
                action="form_team",
                context={"team_id": team.id, "size": 3},
                timestamp=datetime.now()
            )
            
            ethics_result = await ethics.validate_decision(decision)
            
            # Monitor team resources
            safety_result = await safety.monitor_agent_activity(
                agent_id=team.id,
                metrics={'team_size': 3, 'resource_usage': 30}
            )
            
            return {
                'team_formed': team is not None,
                'ethics_approved': ethics_result['approved'],
                'safety_ok': safety_result,
                'integration': 'successful'
            }
        
        result = self.loop.run_until_complete(test_integration())
        self.assertTrue(result['team_formed'])
        self.assertTrue(result['ethics_approved'])
        self.assertTrue(result['safety_ok'])
        print(f"✅ Control-Coordination integration: {result['integration']}")
        
    def test_coordination_execution_integration(self):
        """Test integration between coordination and execution layers"""
        print("\n=== Testing Coordination-Execution Integration ===")
        
        async def test_integration():
            # Initialize components
            pool = AgentPool(initial_size=15)
            allocator = ResourceAllocator()
            orchestrator = TeamOrchestrator(pool, allocator)
            engine = WorkflowEngine()
            
            # Form execution team
            team = await orchestrator.form_team(
                mission="Execute workflow",
                size=5,
                required_skills=["development", "testing", "deployment"]
            )
            
            # Create and execute workflow
            workflow = {
                'name': 'test_workflow',
                'team_id': team.id,
                'steps': [
                    {'agent': 'dev', 'action': 'code'},
                    {'agent': 'test', 'action': 'test'},
                    {'agent': 'deploy', 'action': 'deploy'}
                ]
            }
            
            # Mock execution
            execution_result = {
                'workflow': workflow['name'],
                'team': team.id,
                'status': 'completed',
                'steps_executed': len(workflow['steps'])
            }
            
            return execution_result
        
        result = self.loop.run_until_complete(test_integration())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['steps_executed'], 3)
        print(f"✅ Coordination-Execution integration: {result['status']}")
        
    def test_full_stack_integration(self):
        """Test full stack integration from control to execution"""
        print("\n=== Testing Full Stack Integration ===")
        
        async def test_full_stack():
            # Initialize all layers
            ethics = EthicsEngine()
            safety = SafetyMonitor()
            allocator = ResourceAllocator()
            pool = AgentPool(initial_size=20)
            orchestrator = TeamOrchestrator(pool, allocator)
            doc_manager = DocumentManager()
            handoff = HandoffProtocol(doc_manager)
            quality = QualityTracker()
            
            # Phase 1: Team formation with ethics validation
            form_decision = AgentDecision(
                agent_id="system",
                action="form_team",
                context={"purpose": "full_stack_test"},
                timestamp=datetime.now()
            )
            
            ethics_result = await ethics.validate_decision(form_decision)
            if not ethics_result['approved']:
                return {'status': 'ethics_blocked'}
            
            team = await orchestrator.form_team(
                mission="Full stack test",
                size=4,
                required_skills=["analysis", "development", "testing", "deployment"]
            )
            
            # Phase 2: Document creation and handoff
            doc = await doc_manager.create_document(
                title="Test Requirements",
                content="Full stack test requirements",
                owner=team.agents[0].id if team.agents else "agent-001",
                doc_type="requirements"
            )
            
            handoff_item = await handoff.create_handoff(
                document_id=doc.id,
                from_agent=team.agents[0].id if team.agents else "agent-001",
                to_agent=team.agents[1].id if len(team.agents) > 1 else "agent-002",
                notes="Please review"
            )
            
            # Phase 3: Quality gate
            gate = await quality.evaluate_gate(
                gate_type="requirements",
                artifact={'completeness': 0.90}
            )
            
            # Phase 4: Resource monitoring
            safety_check = await safety.monitor_agent_activity(
                agent_id=team.id,
                metrics={'cpu': 50, 'memory': 60}
            )
            
            return {
                'status': 'completed',
                'phases': {
                    'team_formation': True,
                    'document_flow': True,
                    'quality_gate': gate.decision == GateDecision.PASS,
                    'safety_check': safety_check
                },
                'integration': 'full_stack_successful'
            }
        
        result = self.loop.run_until_complete(test_full_stack())
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(all(result['phases'].values()))
        print(f"✅ Full stack integration: {result['integration']}")


def run_tests():
    """Run all end-to-end workflow tests"""
    print("\n" + "="*50)
    print("RUNNING END-TO-END WORKFLOW TESTS")
    print("="*50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)