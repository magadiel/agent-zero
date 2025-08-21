"""
Test suite for the autonomy module
"""

import asyncio
import unittest
from datetime import datetime, timedelta
from autonomy.self_organization import (
    SelfOrganizingTeam,
    TeamMember,
    PerformanceAssessment,
    ReorganizationProposal,
    ReorganizationType,
    VoteType,
    PerformanceMetric,
    create_sample_team
)
from autonomy.team_evolution import (
    TeamEvolutionManager,
    TeamProfile,
    SkillRequirement,
    EvolutionStrategy,
    AllocationStrategy,
    TeamStructure
)


class TestSelfOrganization(unittest.TestCase):
    """Test cases for self-organizing teams"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.team = create_sample_team()
    
    def test_team_creation(self):
        """Test team creation"""
        self.assertEqual(self.team.team_id, "team-001")
        self.assertEqual(self.team.name, "Alpha Team")
        self.assertEqual(len(self.team.members), 5)
    
    def test_member_performance(self):
        """Test member performance calculation"""
        member = self.team.members["m1"]
        avg_performance = member.get_average_performance()
        self.assertAlmostEqual(avg_performance, 0.85, places=2)
    
    async def test_performance_assessment(self):
        """Test performance assessment"""
        assessment = await self.team.assess_performance()
        
        self.assertIsInstance(assessment, PerformanceAssessment)
        self.assertTrue(0 <= assessment.overall_score <= 1)
        self.assertEqual(len(assessment.metrics), len(PerformanceMetric))
        self.assertIsInstance(assessment.strengths, list)
        self.assertIsInstance(assessment.weaknesses, list)
        self.assertIsInstance(assessment.recommendations, list)
    
    async def test_reorganization_proposal(self):
        """Test reorganization proposal generation"""
        # Create a low-performing assessment
        assessment = PerformanceAssessment(
            team_id=self.team.team_id,
            timestamp=datetime.now(),
            metrics={m: 0.4 for m in PerformanceMetric},
            overall_score=0.4,
            strengths=[],
            weaknesses=["Low performance"],
            recommendations=["Reorganize"],
            member_assessments={}
        )
        
        proposal = await self.team.generate_reorganization_proposal(assessment)
        
        self.assertIsNotNone(proposal)
        self.assertIsInstance(proposal, ReorganizationProposal)
        self.assertIn(proposal.reorganization_type, ReorganizationType)
        self.assertEqual(proposal.status, "pending")
    
    async def test_voting_process(self):
        """Test voting on proposals"""
        # Create a proposal
        assessment = PerformanceAssessment(
            team_id=self.team.team_id,
            timestamp=datetime.now(),
            metrics={m: 0.4 for m in PerformanceMetric},
            overall_score=0.4,
            strengths=[],
            weaknesses=["Low performance"],
            recommendations=["Reorganize"],
            member_assessments={}
        )
        
        proposal = await self.team.generate_reorganization_proposal(assessment)
        if proposal:
            result = await self.team.vote_on_proposal(proposal.id)
            
            self.assertIsNotNone(result)
            self.assertEqual(result.proposal_id, proposal.id)
            self.assertGreaterEqual(result.total_votes, 0)
            self.assertIn(proposal.status, ["approved", "rejected"])
    
    async def test_reorganization_execution(self):
        """Test reorganization execution"""
        # Create and approve a proposal
        assessment = PerformanceAssessment(
            team_id=self.team.team_id,
            timestamp=datetime.now(),
            metrics={m: 0.4 for m in PerformanceMetric},
            overall_score=0.4,
            strengths=[],
            weaknesses=["Low performance"],
            recommendations=["Reorganize"],
            member_assessments={}
        )
        
        proposal = await self.team.generate_reorganization_proposal(assessment)
        if proposal:
            # Force approval for testing
            proposal.status = "approved"
            
            success = await self.team.execute_reorganization(proposal.id)
            
            if proposal.reorganization_type in [
                ReorganizationType.ROLE_CHANGE,
                ReorganizationType.SIZE_ADJUSTMENT
            ]:
                self.assertTrue(success)
                self.assertEqual(proposal.status, "executed")
    
    def test_reorganization_history(self):
        """Test reorganization history tracking"""
        history = self.team.get_reorganization_history()
        self.assertIsInstance(history, list)
        
        # After executing reorganizations, history should be populated
        for item in history:
            self.assertIn("id", item)
            self.assertIn("timestamp", item)
            self.assertIn("type", item)
            self.assertIn("status", item)
    
    def test_current_status(self):
        """Test current team status"""
        status = self.team.get_current_status()
        
        self.assertEqual(status["team_id"], self.team.team_id)
        self.assertEqual(status["name"], self.team.name)
        self.assertEqual(status["member_count"], len(self.team.members))
        self.assertIsInstance(status["members"], list)


class TestTeamEvolution(unittest.TestCase):
    """Test cases for team evolution manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = TeamEvolutionManager()
        
        # Create sample teams
        self.team1 = TeamProfile(
            team_id="test-team-1",
            current_skills={
                "python": ["m1", "m2"],
                "testing": ["m3"]
            },
            required_skills=[
                SkillRequirement("python", 3, "high", 2),
                SkillRequirement("devops", 2, "critical", 1)
            ],
            performance_metrics={"overall": 0.7},
            structure=TeamStructure.FLAT,
            size=3,
            optimal_size=5,
            culture_fit=0.8
        )
        
        self.team2 = TeamProfile(
            team_id="test-team-2",
            current_skills={
                "java": ["m4", "m5"],
                "devops": ["m6"]
            },
            required_skills=[
                SkillRequirement("java", 3, "high", 2),
                SkillRequirement("testing", 2, "medium", 1)
            ],
            performance_metrics={"overall": 0.6},
            structure=TeamStructure.HIERARCHICAL,
            size=3,
            optimal_size=4,
            culture_fit=0.7
        )
    
    def test_team_registration(self):
        """Test team registration"""
        self.manager.register_team(self.team1)
        self.assertIn(self.team1.team_id, self.manager.teams)
        
        self.manager.register_team(self.team2)
        self.assertEqual(len(self.manager.teams), 2)
    
    def test_member_registration(self):
        """Test member registration"""
        self.manager.register_member("m1", {
            "name": "Member1",
            "skills": ["python", "testing"],
            "performance": 0.8
        })
        
        self.assertIn("m1", self.manager.member_pool)
        self.assertIn("m1", self.manager.skill_database.get("python", set()))
        self.assertIn("m1", self.manager.skill_database.get("testing", set()))
    
    def test_skill_gap_analysis(self):
        """Test skill gap analysis"""
        gaps = self.team1.skill_gap_analysis()
        
        self.assertIsInstance(gaps, dict)
        # Team1 needs devops skill
        self.assertIn("devops", gaps)
        self.assertEqual(gaps["devops"], 1)
    
    def test_skill_coverage_score(self):
        """Test skill coverage score calculation"""
        score = self.team1.skill_coverage_score()
        
        self.assertTrue(0 <= score <= 1)
        # Team1 has partial coverage
        self.assertGreater(score, 0)
        self.assertLess(score, 1)
    
    async def test_evolution_strategies(self):
        """Test different evolution strategies"""
        self.manager.register_team(self.team1)
        self.manager.register_team(self.team2)
        
        # Test each strategy
        strategies = [
            EvolutionStrategy.GENETIC,
            EvolutionStrategy.GRADIENT,
            EvolutionStrategy.ADAPTIVE
        ]
        
        for strategy in strategies:
            plan = await self.manager.evolve_teams(strategy, iterations=2)
            
            self.assertIsNotNone(plan)
            self.assertEqual(plan.strategy, strategy)
            self.assertIsInstance(plan.phases, list)
            self.assertIsInstance(plan.expected_outcome, dict)
            self.assertIsInstance(plan.risk_assessment, dict)
    
    async def test_member_reallocation(self):
        """Test member reallocation strategies"""
        self.manager.register_team(self.team1)
        self.manager.register_team(self.team2)
        
        # Register members
        for i in range(1, 7):
            self.manager.register_member(f"m{i}", {
                "name": f"Member{i}",
                "skills": ["python", "java"][i % 2:],
                "performance": 0.7
            })
        
        # Test different allocation strategies
        strategies = [
            AllocationStrategy.SKILL_BASED,
            AllocationStrategy.BALANCED,
            AllocationStrategy.PERFORMANCE_BASED
        ]
        
        for strategy in strategies:
            reallocations = await self.manager.reallocate_members(strategy)
            
            self.assertIsInstance(reallocations, list)
            for realloc in reallocations:
                self.assertIsNotNone(realloc.member_id)
                self.assertIsNotNone(realloc.from_team)
                self.assertIsNotNone(realloc.to_team)
                self.assertIsNotNone(realloc.reason)
    
    async def test_skill_reorganization(self):
        """Test skill-based reorganization"""
        self.manager.register_team(self.team1)
        self.manager.register_team(self.team2)
        
        reorganization = await self.manager.reorganize_by_skills(target_coverage=0.8)
        
        self.assertIsNotNone(reorganization)
        self.assertIsInstance(reorganization.skill_mappings, dict)
        self.assertIsInstance(reorganization.member_movements, list)
        self.assertTrue(0 <= reorganization.expected_coverage_improvement <= 1)
        self.assertIsInstance(reorganization.implementation_steps, list)
        self.assertGreater(len(reorganization.implementation_steps), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for autonomy module"""
    
    async def test_full_self_organization_cycle(self):
        """Test complete self-organization cycle"""
        # Create team
        team = create_sample_team()
        
        # Assess performance
        assessment = await team.assess_performance()
        self.assertIsNotNone(assessment)
        
        # Generate proposal if needed
        if assessment.needs_reorganization():
            proposal = await team.generate_reorganization_proposal(assessment)
            self.assertIsNotNone(proposal)
            
            # Vote on proposal
            voting_result = await team.vote_on_proposal(proposal.id)
            self.assertIsNotNone(voting_result)
            
            # Execute if approved
            if voting_result.passed:
                success = await team.execute_reorganization(proposal.id)
                self.assertIsInstance(success, bool)
        
        # Check final status
        status = team.get_current_status()
        self.assertIsNotNone(status)
    
    async def test_evolution_and_reallocation(self):
        """Test evolution followed by reallocation"""
        manager = TeamEvolutionManager()
        
        # Register teams
        for i in range(3):
            team = TeamProfile(
                team_id=f"team-{i}",
                current_skills={f"skill{i}": [f"m{i}"]},
                required_skills=[SkillRequirement(f"skill{i}", 2, "high", 1)],
                performance_metrics={"overall": 0.5 + i * 0.1},
                structure=TeamStructure.ADAPTIVE,
                size=1,
                optimal_size=3,
                culture_fit=0.7
            )
            manager.register_team(team)
        
        # Evolve teams
        evolution_plan = await manager.evolve_teams(EvolutionStrategy.ADAPTIVE, iterations=3)
        self.assertIsNotNone(evolution_plan)
        
        # Reallocate members
        reallocations = await manager.reallocate_members(AllocationStrategy.DYNAMIC)
        self.assertIsInstance(reallocations, list)
        
        # Reorganize by skills
        reorganization = await manager.reorganize_by_skills(target_coverage=0.7)
        self.assertIsNotNone(reorganization)


def run_async_test(test_func):
    """Helper to run async test functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_func())
    finally:
        loop.close()


if __name__ == "__main__":
    # Configure for testing
    import random
    import statistics
    random.seed(42)
    statistics.random = random.random
    statistics.choice = random.choice
    statistics.sample = random.sample
    
    # Run tests
    unittest.main()