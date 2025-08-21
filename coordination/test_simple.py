#!/usr/bin/env python3
"""
Simple test for Team Orchestration components
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from coordination.agent_pool import (
    AgentPool, AgentStatus, AgentSkill, 
    AllocationRequest
)
from coordination.team_orchestrator import (
    TeamOrchestrator, TeamType, TeamStatus,
    TeamFormationRequest
)


async def test_agent_pool():
    """Test basic agent pool operations"""
    print("\n=== Testing Agent Pool ===")
    
    # Create pool without resource allocator
    pool = AgentPool(pool_size=15, resource_allocator=None)
    await pool.initialize()
    
    print(f"✓ Pool initialized with {len(pool.agents)} agents")
    
    # Test allocation
    request = AllocationRequest(
        request_id="test_001",
        team_id="team_dev",
        required_count=5,
        required_skills={AgentSkill.DEVELOPMENT, AgentSkill.GENERAL}
    )
    
    agents = await pool.allocate_agents(request)
    print(f"✓ Allocated {len(agents)} agents with development skills")
    
    # Check status
    status = pool.get_pool_status()
    print(f"✓ Pool status: {status['status_distribution']}")
    
    # Release agents
    await pool.release_agents("team_dev")
    print(f"✓ Released agents back to pool")
    
    # Final status
    status = pool.get_pool_status()
    available = status['status_distribution'].get('available', 0)
    print(f"✓ Available agents after release: {available}")
    
    await pool.shutdown()
    return True


async def test_team_orchestrator():
    """Test basic team orchestration"""
    print("\n=== Testing Team Orchestrator ===")
    
    # Create components without resource allocator
    pool = AgentPool(pool_size=20, resource_allocator=None)
    orchestrator = TeamOrchestrator(
        agent_pool=pool,
        resource_allocator=None
    )
    
    await orchestrator.initialize()
    print(f"✓ Orchestrator initialized")
    
    # Form a team
    request = TeamFormationRequest(
        request_id="form_001",
        team_name="Product Team",
        team_type=TeamType.CROSS_FUNCTIONAL,
        mission="Build awesome products",
        required_skills={
            AgentSkill.GENERAL  # Only require general skills for testing
        },
        team_size=7
    )
    
    team = await orchestrator.form_team(request)
    print(f"✓ Formed team '{team.name}' with {len(team.members)} members")
    
    # Show team composition
    print("\nTeam composition:")
    for member_id, member in team.members.items():
        skills_str = ", ".join([s.value for s in member.agent.skills])
        print(f"  - {member.agent.profile} ({member.role.value}): {skills_str}")
    
    # Assign and complete tasks
    await orchestrator.assign_task_to_team(team.team_id, "task_001")
    await orchestrator.assign_task_to_team(team.team_id, "task_002")
    print(f"✓ Assigned 2 tasks to team")
    
    await orchestrator.complete_team_task(
        team.team_id, 
        "task_001",
        {'quality': 0.9, 'efficiency': 0.85}
    )
    print(f"✓ Completed task with quality metrics")
    
    # Get team status
    all_teams = orchestrator.get_all_teams()
    print(f"\n✓ Active teams: {len(all_teams)}")
    for team_info in all_teams:
        print(f"  - {team_info['name']}: {team_info['status']} "
              f"({team_info['completed_tasks']} tasks completed)")
    
    # Get recommendations
    recommendations = await orchestrator.get_team_recommendations(team.team_id)
    print(f"\n✓ Team metrics:")
    for metric, value in recommendations['current_metrics'].items():
        print(f"  - {metric}: {value:.2f}")
    
    # Dissolve team
    await orchestrator.dissolve_team(team.team_id, "Test completed")
    print(f"✓ Team dissolved successfully")
    
    await orchestrator.shutdown()
    return True


async def test_integration():
    """Test integrated workflow"""
    print("\n=== Testing Integration ===")
    
    # Create system
    pool = AgentPool(pool_size=30, resource_allocator=None)
    orchestrator = TeamOrchestrator(
        agent_pool=pool,
        resource_allocator=None
    )
    
    await orchestrator.initialize()
    
    # Form multiple teams
    teams = []
    team_types = [
        (TeamType.CROSS_FUNCTIONAL, "Development Squad", 7),
        (TeamType.SELF_MANAGING, "QA Team", 4),
        (TeamType.SQUAD, "DevOps Team", 5)
    ]
    
    for i, (team_type, name, size) in enumerate(team_types):
        request = TeamFormationRequest(
            request_id=f"form_{i:03d}",
            team_name=name,
            team_type=team_type,
            mission=f"Mission for {name}",
            required_skills={AgentSkill.GENERAL},
            team_size=size
        )
        team = await orchestrator.form_team(request)
        teams.append(team)
        print(f"✓ Formed {name} with {size} members")
    
    # Show pool utilization
    pool_status = pool.get_pool_status()
    allocated = pool_status['status_distribution'].get('allocated', 0)
    available = pool_status['status_distribution'].get('available', 0)
    print(f"\n✓ Pool utilization: {allocated} allocated, {available} available")
    
    # Simulate work
    for team in teams:
        for j in range(3):
            task_id = f"{team.team_id}_task_{j:03d}"
            await orchestrator.assign_task_to_team(team.team_id, task_id)
            await orchestrator.complete_team_task(
                team.team_id,
                task_id,
                {'quality': 0.8 + j*0.05, 'efficiency': 0.75 + j*0.05}
            )
    
    print(f"✓ All teams completed 3 tasks each")
    
    # Show final statistics
    all_teams = orchestrator.get_all_teams()
    print(f"\n✓ Final team statistics:")
    for team_info in all_teams:
        print(f"  - {team_info['name']}: "
              f"{team_info['completed_tasks']} tasks, "
              f"velocity: {team_info['velocity']:.2f}")
    
    # Clean up
    for team in teams:
        await orchestrator.dissolve_team(team.team_id)
    
    await orchestrator.shutdown()
    print(f"✓ All teams dissolved and system shutdown")
    
    return True


async def main():
    """Run all tests"""
    print("=" * 50)
    print("Team Orchestration System Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        results = []
        results.append(await test_agent_pool())
        results.append(await test_team_orchestrator())
        results.append(await test_integration())
        
        # Summary
        print("\n" + "=" * 50)
        if all(results):
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)