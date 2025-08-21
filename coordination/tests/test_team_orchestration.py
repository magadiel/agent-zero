"""
Comprehensive tests for Team Orchestration System

Tests both AgentPool and TeamOrchestrator functionality including:
- Agent allocation and release
- Team formation and dissolution
- Resource management
- Performance tracking
- Error handling
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import timedelta
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from coordination.agent_pool import (
    AgentPool, AgentStatus, AgentSkill, PooledAgent,
    AllocationRequest, InsufficientAgentsError
)
from coordination.team_orchestrator import (
    TeamOrchestrator, Team, TeamStatus, TeamType,
    TeamFormationRequest, TeamFormationError
)


class TestAgentPool:
    """Test suite for AgentPool"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Test agent pool initialization"""
        pool = AgentPool(pool_size=10)
        await pool.initialize()
        
        assert len(pool.agents) == 10
        assert pool._initialized is True
        
        # Check agent properties
        for agent in pool.agents.values():
            assert agent.status == AgentStatus.AVAILABLE
            assert len(agent.skills) > 0
            assert AgentSkill.GENERAL in agent.skills
    
    @pytest.mark.asyncio
    async def test_agent_allocation(self):
        """Test allocating agents from pool"""
        pool = AgentPool(pool_size=10)
        await pool.initialize()
        
        # Create allocation request
        request = AllocationRequest(
            request_id="test_001",
            team_id="team_test",
            required_count=3,
            required_skills={AgentSkill.GENERAL},
            priority=5
        )
        
        # Allocate agents
        agents = await pool.allocate_agents(request)
        
        assert len(agents) == 3
        for agent in agents:
            assert agent.status == AgentStatus.ALLOCATED
            assert agent.allocated_to == "team_test"
    
    @pytest.mark.asyncio
    async def test_agent_release(self):
        """Test releasing agents back to pool"""
        pool = AgentPool(pool_size=5)
        await pool.initialize()
        
        # Allocate agents
        request = AllocationRequest(
            request_id="test_002",
            team_id="team_test",
            required_count=3,
            required_skills={AgentSkill.GENERAL}
        )
        agents = await pool.allocate_agents(request)
        
        # Release agents
        await pool.release_agents("team_test")
        
        # Check all agents are available again
        for agent in agents:
            assert agent.status == AgentStatus.AVAILABLE
            assert agent.allocated_to is None
    
    @pytest.mark.asyncio
    async def test_insufficient_agents(self):
        """Test handling insufficient agents"""
        pool = AgentPool(pool_size=3)
        await pool.initialize()
        
        # Request more agents than available
        request = AllocationRequest(
            request_id="test_003",
            team_id="team_test",
            required_count=5,
            required_skills={AgentSkill.GENERAL}
        )
        
        with pytest.raises(InsufficientAgentsError):
            await pool.allocate_agents(request)
        
        # Check request was queued
        assert len(pool.allocation_queue) == 1
    
    @pytest.mark.asyncio
    async def test_skill_based_allocation(self):
        """Test allocating agents based on skills"""
        pool = AgentPool(pool_size=20)
        await pool.initialize()
        
        # Request specific skills
        request = AllocationRequest(
            request_id="test_004",
            team_id="team_dev",
            required_count=2,
            required_skills={AgentSkill.DEVELOPMENT, AgentSkill.GENERAL},
            optional_skills={AgentSkill.TESTING}
        )
        
        agents = await pool.allocate_agents(request)
        
        # Verify allocated agents have required skills
        for agent in agents:
            assert AgentSkill.DEVELOPMENT in agent.skills
            assert AgentSkill.GENERAL in agent.skills
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self):
        """Test agent performance tracking"""
        pool = AgentPool(pool_size=5)
        await pool.initialize()
        
        agent_id = list(pool.agents.keys())[0]
        
        # Update performance
        await pool.update_agent_performance(agent_id, -0.5)
        
        agent = pool.agents[agent_id]
        assert agent.performance_score == 0.5
        
        # Further decrease should trigger maintenance
        await pool.update_agent_performance(agent_id, -0.3)
        assert agent.status == AgentStatus.MAINTENANCE
    
    @pytest.mark.asyncio
    async def test_pool_status(self):
        """Test getting pool status"""
        pool = AgentPool(pool_size=10)
        await pool.initialize()
        
        status = pool.get_pool_status()
        
        assert status['total_agents'] == 10
        assert status['status_distribution'][AgentStatus.AVAILABLE.value] == 10
        assert 'skill_distribution' in status
        assert 'average_performance' in status


class TestTeamOrchestrator:
    """Test suite for TeamOrchestrator"""
    
    @pytest.mark.asyncio
    async def test_team_formation(self):
        """Test forming a new team"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Create formation request
        request = TeamFormationRequest(
            request_id="form_001",
            team_name="Development Team",
            team_type=TeamType.CROSS_FUNCTIONAL,
            mission="Build new features",
            required_skills={AgentSkill.DEVELOPMENT, AgentSkill.TESTING},
            team_size=5
        )
        
        # Form team
        team = await orchestrator.form_team(request)
        
        assert team.name == "Development Team"
        assert team.team_type == TeamType.CROSS_FUNCTIONAL
        assert len(team.members) == 5
        assert team.status == TeamStatus.STORMING
    
    @pytest.mark.asyncio
    async def test_team_dissolution(self):
        """Test dissolving a team"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form a team
        request = TeamFormationRequest(
            request_id="form_002",
            team_name="Temp Team",
            team_type=TeamType.TASK_FORCE,
            mission="Quick task",
            required_skills={AgentSkill.GENERAL},
            team_size=3
        )
        team = await orchestrator.form_team(request)
        team_id = team.team_id
        
        # Dissolve team
        await orchestrator.dissolve_team(team_id, "Test completed")
        
        # Verify team is dissolved
        assert team_id not in orchestrator.teams
        assert team.status == TeamStatus.DISSOLVED
        
        # Verify agents were released
        pool_status = pool.get_pool_status()
        assert pool_status['status_distribution'][AgentStatus.AVAILABLE.value] >= 3
    
    @pytest.mark.asyncio
    async def test_team_lifecycle(self):
        """Test team lifecycle progression"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form team
        request = TeamFormationRequest(
            request_id="form_003",
            team_name="Lifecycle Team",
            team_type=TeamType.SQUAD,
            mission="Test lifecycle",
            required_skills={AgentSkill.GENERAL},
            team_size=8
        )
        team = await orchestrator.form_team(request)
        
        # Progress through lifecycle
        assert team.status == TeamStatus.STORMING
        
        await orchestrator.update_team_status(team.team_id, TeamStatus.NORMING)
        assert team.status == TeamStatus.NORMING
        
        await orchestrator.update_team_status(team.team_id, TeamStatus.PERFORMING)
        assert team.status == TeamStatus.PERFORMING
        
        # Clean up
        await orchestrator.dissolve_team(team.team_id)
    
    @pytest.mark.asyncio
    async def test_task_assignment(self):
        """Test assigning tasks to teams"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form team
        request = TeamFormationRequest(
            request_id="form_004",
            team_name="Task Team",
            team_type=TeamType.SELF_MANAGING,
            mission="Complete tasks",
            required_skills={AgentSkill.GENERAL},
            team_size=4
        )
        team = await orchestrator.form_team(request)
        
        # Assign tasks
        await orchestrator.assign_task_to_team(team.team_id, "task_001")
        await orchestrator.assign_task_to_team(team.team_id, "task_002")
        
        assert len(team.active_tasks) == 2
        
        # Complete a task
        await orchestrator.complete_team_task(
            team.team_id,
            "task_001",
            {'quality': 0.9, 'efficiency': 0.85}
        )
        
        assert len(team.active_tasks) == 1
        assert len(team.completed_tasks) == 1
        assert team.quality_score > 0.9
        
        # Clean up
        await orchestrator.dissolve_team(team.team_id)
    
    @pytest.mark.asyncio
    async def test_team_recommendations(self):
        """Test getting team improvement recommendations"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form small team
        request = TeamFormationRequest(
            request_id="form_005",
            team_name="Small Team",
            team_type=TeamType.SELF_MANAGING,
            mission="Test recommendations",
            required_skills={AgentSkill.GENERAL},
            team_size=3
        )
        team = await orchestrator.form_team(request)
        
        # Set low quality score
        team.quality_score = 0.4
        
        # Get recommendations
        recommendations = await orchestrator.get_team_recommendations(team.team_id)
        
        assert 'recommendations' in recommendations
        assert len(recommendations['recommendations']) > 0
        
        # Should recommend quality improvement
        quality_recs = [r for r in recommendations['recommendations'] 
                        if r['type'] == 'quality']
        assert len(quality_recs) > 0
        
        # Clean up
        await orchestrator.dissolve_team(team.team_id)
    
    @pytest.mark.asyncio
    async def test_multiple_teams(self):
        """Test managing multiple teams simultaneously"""
        pool = AgentPool(pool_size=30)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        teams = []
        
        # Form multiple teams
        for i in range(3):
            request = TeamFormationRequest(
                request_id=f"form_{i:03d}",
                team_name=f"Team {i}",
                team_type=TeamType.CROSS_FUNCTIONAL,
                mission=f"Mission {i}",
                required_skills={AgentSkill.GENERAL},
                team_size=5
            )
            team = await orchestrator.form_team(request)
            teams.append(team)
        
        # Verify all teams exist
        all_teams = orchestrator.get_all_teams()
        assert len(all_teams) == 3
        
        # Clean up
        for team in teams:
            await orchestrator.dissolve_team(team.team_id)
    
    @pytest.mark.asyncio
    async def test_team_skills(self):
        """Test team skill aggregation"""
        pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Request team with specific skills
        request = TeamFormationRequest(
            request_id="form_skills",
            team_name="Skilled Team",
            team_type=TeamType.CROSS_FUNCTIONAL,
            mission="Diverse skills test",
            required_skills={
                AgentSkill.DEVELOPMENT,
                AgentSkill.TESTING,
                AgentSkill.ARCHITECTURE
            },
            team_size=7
        )
        
        team = await orchestrator.form_team(request)
        team_skills = team.get_skills()
        
        # Verify required skills are present
        assert AgentSkill.DEVELOPMENT in team_skills
        assert AgentSkill.TESTING in team_skills
        assert AgentSkill.ARCHITECTURE in team_skills
        
        # Clean up
        await orchestrator.dissolve_team(team.team_id)
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in team orchestration"""
        pool = AgentPool(pool_size=5)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Try to form team larger than pool
        request = TeamFormationRequest(
            request_id="form_error",
            team_name="Too Large",
            team_type=TeamType.FLOW_TO_WORK,
            mission="Test error",
            required_skills={AgentSkill.GENERAL},
            team_size=10
        )
        
        with pytest.raises(TeamFormationError):
            await orchestrator.form_team(request)
        
        # Try to dissolve non-existent team
        with pytest.raises(ValueError):
            await orchestrator.dissolve_team("non_existent_team")


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow from team formation to dissolution"""
        pool = AgentPool(pool_size=25)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form a development team
        dev_request = TeamFormationRequest(
            request_id="workflow_001",
            team_name="Product Development",
            team_type=TeamType.SQUAD,
            mission="Build product features",
            required_skills={
                AgentSkill.DEVELOPMENT,
                AgentSkill.TESTING,
                AgentSkill.PRODUCT_MANAGEMENT
            },
            team_size=8,
            duration=timedelta(days=30)
        )
        
        dev_team = await orchestrator.form_team(dev_request)
        
        # Simulate sprint work
        tasks = ["story_001", "story_002", "story_003", "bug_001", "bug_002"]
        
        for task in tasks:
            await orchestrator.assign_task_to_team(dev_team.team_id, task)
        
        # Complete tasks with varying performance
        for i, task in enumerate(tasks):
            quality = 0.7 + (i * 0.05)
            efficiency = 0.8 + (i * 0.03)
            
            await orchestrator.complete_team_task(
                dev_team.team_id,
                task,
                {'quality': quality, 'efficiency': efficiency}
            )
        
        # Check team metrics
        assert dev_team.completed_tasks == tasks
        assert dev_team.velocity > 0
        assert dev_team.quality_score > 0.7
        assert dev_team.efficiency_score > 0.8
        
        # Get team status
        all_teams = orchestrator.get_all_teams()
        dev_team_status = next(t for t in all_teams if t['team_id'] == dev_team.team_id)
        assert dev_team_status['completed_tasks'] == 5
        
        # Dissolve team
        await orchestrator.dissolve_team(dev_team.team_id, "Sprint completed")
        
        # Verify cleanup
        assert dev_team.team_id not in orchestrator.teams
        pool_status = pool.get_pool_status()
        assert pool_status['status_distribution'][AgentStatus.AVAILABLE.value] >= 8
    
    @pytest.mark.asyncio
    async def test_resource_contention(self):
        """Test handling resource contention between teams"""
        pool = AgentPool(pool_size=10)
        orchestrator = TeamOrchestrator(agent_pool=pool)
        await orchestrator.initialize()
        
        # Form first team using most agents
        request1 = TeamFormationRequest(
            request_id="contention_001",
            team_name="Team A",
            team_type=TeamType.CROSS_FUNCTIONAL,
            mission="Primary mission",
            required_skills={AgentSkill.GENERAL},
            team_size=7
        )
        team_a = await orchestrator.form_team(request1)
        
        # Try to form second team
        request2 = TeamFormationRequest(
            request_id="contention_002",
            team_name="Team B",
            team_type=TeamType.SELF_MANAGING,
            mission="Secondary mission",
            required_skills={AgentSkill.GENERAL},
            team_size=3
        )
        team_b = await orchestrator.form_team(request2)
        
        # Both teams should be formed
        assert len(team_a.members) == 7
        assert len(team_b.members) == 3
        
        # Try to form third team - should fail
        request3 = TeamFormationRequest(
            request_id="contention_003",
            team_name="Team C",
            team_type=TeamType.SELF_MANAGING,
            mission="Tertiary mission",
            required_skills={AgentSkill.GENERAL},
            team_size=3
        )
        
        with pytest.raises(TeamFormationError):
            await orchestrator.form_team(request3)
        
        # Clean up
        await orchestrator.dissolve_team(team_a.team_id)
        await orchestrator.dissolve_team(team_b.team_id)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])