"""
Unit tests for the Ethics Engine module.
"""

import unittest
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ethics_engine import (
    EthicsEngine, 
    AgentDecision, 
    DecisionType,
    EthicalViolationType,
    ValidationResult
)


class TestEthicsEngine(unittest.TestCase):
    """Test suite for Ethics Engine functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = EthicsEngine()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_engine_initialization(self):
        """Test that the engine initializes correctly."""
        self.assertIsNotNone(self.engine)
        self.assertIsNotNone(self.engine.constraints)
        self.assertIn('harm_prevention', self.engine.constraints)
        self.assertIn('privacy_protection', self.engine.constraints)
        self.assertIn('fairness', self.engine.constraints)
        self.assertIn('transparency', self.engine.constraints)
    
    def test_valid_decision_approval(self):
        """Test that valid decisions are approved."""
        decision = AgentDecision(
            agent_id="test-agent-001",
            decision_type=DecisionType.TASK_EXECUTION,
            action="process_public_data",
            context={
                "explanation": "Processing publicly available data for analysis",
                "personal_data": False,
                "disclosed_ai": True
            },
            resources_required={
                "cpu_percent": 30,
                "memory_mb": 1024
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertTrue(result.approved)
        self.assertEqual(len(result.violations), 0)
        self.assertLess(result.risk_score, 0.3)
    
    def test_harmful_action_rejection(self):
        """Test that harmful actions are rejected."""
        decision = AgentDecision(
            agent_id="test-agent-002",
            decision_type=DecisionType.TASK_EXECUTION,
            action="delete_user_data_permanently",
            context={
                "target": "user_profile",
                "explanation": "Deleting user data without consent"
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.HARM_PREVENTION, result.violations)
        self.assertGreater(result.risk_score, 0)
    
    def test_privacy_violation_detection(self):
        """Test detection of privacy violations."""
        decision = AgentDecision(
            agent_id="test-agent-003",
            decision_type=DecisionType.DATA_ACCESS,
            action="access_personal_data",
            context={
                "personal_data": True,
                "consent": False,
                "target": "medical_records"
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.PRIVACY_VIOLATION, result.violations)
        self.assertGreater(len(result.recommendations), 0)
    
    def test_fairness_check(self):
        """Test fairness validation."""
        decision = AgentDecision(
            agent_id="test-agent-004",
            decision_type=DecisionType.RESOURCE_ALLOCATION,
            action="allocate_resources",
            context={
                "selection_criteria": "prefer_users_of_specific_race",
                "priority": "exclusive"
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.FAIRNESS_BREACH, result.violations)
    
    def test_transparency_requirement(self):
        """Test transparency requirements."""
        decision = AgentDecision(
            agent_id="test-agent-005",
            decision_type=DecisionType.USER_INTERACTION,
            action="respond_to_user",
            context={
                "disclosed_ai": False,
                # Missing explanation
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.TRANSPARENCY_ISSUE, result.violations)
    
    def test_resource_limit_enforcement(self):
        """Test resource limit enforcement."""
        decision = AgentDecision(
            agent_id="test-agent-006",
            decision_type=DecisionType.AGENT_CREATION,
            action="create_large_team",
            context={
                "team_size": 20,  # Exceeds limit of 10
                "purpose": "massive_parallel_processing"
            },
            resources_required={
                "cpu_percent": 95,  # Exceeds limit of 80
                "memory_mb": 8192   # Exceeds limit of 4096
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.RESOURCE_ABUSE, result.violations)
        self.assertGreater(result.risk_score, 0.5)
    
    def test_validation_history(self):
        """Test that validation history is maintained."""
        # Create and validate multiple decisions
        decisions = [
            AgentDecision(
                agent_id=f"test-agent-{i:03d}",
                decision_type=DecisionType.TASK_EXECUTION,
                action=f"action_{i}",
                context={"explanation": f"Test action {i}"}
            )
            for i in range(5)
        ]
        
        for decision in decisions:
            self.loop.run_until_complete(
                self.engine.validate_decision(decision)
            )
        
        # Check history
        history = self.loop.run_until_complete(
            self.engine.get_validation_history(limit=10)
        )
        
        self.assertEqual(len(history), 5)
        
        # Check filtered history
        filtered_history = self.loop.run_until_complete(
            self.engine.get_validation_history(agent_id="test-agent-001")
        )
        
        self.assertEqual(len(filtered_history), 1)
    
    def test_violation_summary(self):
        """Test violation summary tracking."""
        # Create decisions that will trigger violations
        harmful_decision = AgentDecision(
            agent_id="test-agent-harm",
            decision_type=DecisionType.TASK_EXECUTION,
            action="destroy_data",
            context={}
        )
        
        privacy_decision = AgentDecision(
            agent_id="test-agent-privacy",
            decision_type=DecisionType.DATA_ACCESS,
            action="access_private_data",
            context={"personal_data": True, "consent": False}
        )
        
        self.loop.run_until_complete(
            self.engine.validate_decision(harmful_decision)
        )
        self.loop.run_until_complete(
            self.engine.validate_decision(privacy_decision)
        )
        
        summary = self.loop.run_until_complete(
            self.engine.get_violation_summary()
        )
        
        self.assertIn(EthicalViolationType.HARM_PREVENTION.value, summary)
        self.assertIn(EthicalViolationType.PRIVACY_VIOLATION.value, summary)
        self.assertGreater(summary[EthicalViolationType.HARM_PREVENTION.value], 0)
    
    def test_constraint_update(self):
        """Test dynamic constraint updates."""
        new_constraints = {
            "harm_prevention": {
                "enabled": True,
                "priority": "critical",
                "rules": ["prevent_all_harm"]
            },
            "privacy_protection": {
                "enabled": True,
                "priority": "critical",
                "rules": ["maximum_privacy"]
            },
            "fairness": {
                "enabled": True,
                "priority": "high",
                "rules": ["absolute_fairness"]
            },
            "transparency": {
                "enabled": True,
                "priority": "high",
                "rules": ["full_transparency"]
            },
            "resource_limits": {
                "max_cpu_percent": 50,  # More restrictive
                "max_memory_mb": 2048    # More restrictive
            }
        }
        
        self.loop.run_until_complete(
            self.engine.update_constraints(new_constraints)
        )
        
        # Test with previously acceptable resource usage
        decision = AgentDecision(
            agent_id="test-agent-resource",
            decision_type=DecisionType.TASK_EXECUTION,
            action="process_data",
            context={"explanation": "Processing data"},
            resources_required={
                "cpu_percent": 60,  # Now exceeds new limit of 50
                "memory_mb": 3000   # Now exceeds new limit of 2048
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertFalse(result.approved)
        self.assertIn(EthicalViolationType.RESOURCE_ABUSE, result.violations)
    
    def test_emergency_shutdown(self):
        """Test emergency shutdown functionality."""
        shutdown_result = self.loop.run_until_complete(
            self.engine.emergency_shutdown("Critical ethical violation detected")
        )
        
        self.assertIsNotNone(shutdown_result)
        self.assertIn("timestamp", shutdown_result)
        self.assertIn("reason", shutdown_result)
        self.assertEqual(shutdown_result["event"], "emergency_shutdown")
    
    def test_complex_decision_validation(self):
        """Test validation of complex decisions with multiple factors."""
        decision = AgentDecision(
            agent_id="test-agent-complex",
            decision_type=DecisionType.USER_INTERACTION,
            action="personalized_recommendation",
            context={
                "explanation": "Providing personalized recommendations based on user behavior",
                "personal_data": True,
                "consent": True,
                "disclosed_ai": True,
                "encryption": True,
                "selection_criteria": "user_preferences_only"
            },
            resources_required={
                "cpu_percent": 40,
                "memory_mb": 2048
            }
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        self.assertTrue(result.approved)
        self.assertEqual(len(result.violations), 0)
        self.assertLess(result.risk_score, 0.3)
    
    def test_validation_result_serialization(self):
        """Test that validation results can be serialized."""
        decision = AgentDecision(
            agent_id="test-agent-serial",
            decision_type=DecisionType.TASK_EXECUTION,
            action="test_action",
            context={"test": "data"}
        )
        
        result = self.loop.run_until_complete(
            self.engine.validate_decision(decision)
        )
        
        result_dict = result.to_dict()
        
        self.assertIn("validation_id", result_dict)
        self.assertIn("approved", result_dict)
        self.assertIn("reasoning", result_dict)
        self.assertIn("violations", result_dict)
        self.assertIn("risk_score", result_dict)
        self.assertIn("recommendations", result_dict)
        self.assertIn("timestamp", result_dict)
    
    def test_decision_serialization(self):
        """Test that decisions can be serialized."""
        decision = AgentDecision(
            agent_id="test-agent-serial",
            decision_type=DecisionType.TASK_EXECUTION,
            action="test_action",
            context={"test": "data"},
            resources_required={"cpu_percent": 10}
        )
        
        decision_dict = decision.to_dict()
        
        self.assertIn("decision_id", decision_dict)
        self.assertIn("agent_id", decision_dict)
        self.assertIn("decision_type", decision_dict)
        self.assertIn("action", decision_dict)
        self.assertIn("context", decision_dict)
        self.assertIn("resources_required", decision_dict)
        self.assertIn("timestamp", decision_dict)


class TestEthicsEngineIntegration(unittest.TestCase):
    """Integration tests for Ethics Engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = EthicsEngine()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_multiple_agent_coordination(self):
        """Test ethics validation for multiple coordinating agents."""
        team_decisions = []
        
        # Simulate a team of agents making related decisions
        for i in range(5):
            decision = AgentDecision(
                agent_id=f"team-agent-{i:03d}",
                decision_type=DecisionType.TASK_EXECUTION,
                action=f"collaborative_task_part_{i}",
                context={
                    "explanation": f"Executing part {i} of collaborative task",
                    "team_id": "team-001",
                    "coordination_required": True
                },
                resources_required={
                    "cpu_percent": 15,  # Total would be 75% for team
                    "memory_mb": 800    # Total would be 4000MB for team
                }
            )
            team_decisions.append(decision)
        
        # Validate all decisions
        results = []
        for decision in team_decisions:
            result = self.loop.run_until_complete(
                self.engine.validate_decision(decision)
            )
            results.append(result)
        
        # All individual decisions should be approved
        for result in results:
            self.assertTrue(result.approved)
        
        # Check team resource usage doesn't exceed limits
        total_cpu = sum(d.resources_required.get("cpu_percent", 0) for d in team_decisions)
        total_memory = sum(d.resources_required.get("memory_mb", 0) for d in team_decisions)
        
        self.assertLessEqual(total_cpu, 80)  # Team total within limit
        self.assertLessEqual(total_memory, 4096)  # Team total within limit
    
    def test_cascading_decision_validation(self):
        """Test validation of decisions that depend on each other."""
        # Parent decision
        parent_decision = AgentDecision(
            agent_id="parent-agent",
            decision_type=DecisionType.AGENT_CREATION,
            action="spawn_child_agents",
            context={
                "explanation": "Creating child agents for distributed processing",
                "team_size": 3
            }
        )
        
        parent_result = self.loop.run_until_complete(
            self.engine.validate_decision(parent_decision)
        )
        
        self.assertTrue(parent_result.approved)
        
        # Child decisions (only if parent approved)
        if parent_result.approved:
            child_decisions = []
            for i in range(3):
                child_decision = AgentDecision(
                    agent_id=f"child-agent-{i:03d}",
                    decision_type=DecisionType.TASK_EXECUTION,
                    action="process_subset",
                    context={
                        "explanation": f"Processing data subset {i}",
                        "parent_agent": "parent-agent"
                    },
                    resources_required={
                        "cpu_percent": 20,
                        "memory_mb": 1024
                    }
                )
                child_decisions.append(child_decision)
            
            # Validate child decisions
            for decision in child_decisions:
                result = self.loop.run_until_complete(
                    self.engine.validate_decision(decision)
                )
                self.assertTrue(result.approved)


if __name__ == "__main__":
    unittest.main()