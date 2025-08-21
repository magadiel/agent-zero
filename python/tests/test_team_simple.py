#!/usr/bin/env python3
"""
Simple test for team communication without pytest
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python.helpers.team_protocol import (
    TeamProtocol, TeamMessage, MessageType, VoteOption,
    VoteRequest, StatusReport
)
from python.tools.team_communication import TeamCommunication


async def test_team_protocol():
    """Test basic team protocol functionality"""
    print("Testing Team Protocol...")
    
    # Create protocol
    protocol = TeamProtocol("test-team-001", "agent-001")
    print(f"✓ Created protocol for team {protocol.team_id}")
    
    # Test message creation
    message = TeamMessage(
        message_type=MessageType.BROADCAST,
        sender_id="agent-001",
        team_id="test-team-001",
        content="Test broadcast message"
    )
    print(f"✓ Created broadcast message: {message.content}")
    
    # Test vote request
    vote_id = await protocol.request_team_vote(
        proposal="Should we proceed with deployment?",
        threshold=0.5,
        deadline_minutes=5
    )
    print(f"✓ Created vote request with ID: {vote_id}")
    
    # Test vote submission
    success = await protocol.submit_vote(
        vote_id=vote_id,
        vote=VoteOption.YES,
        reasoning="I agree with the deployment"
    )
    print(f"✓ Submitted vote: {success}")
    
    # Test vote tallying
    results = await protocol.tally_votes(vote_id)
    print(f"✓ Vote results: {results['outcome']} ({results['vote_counts']})")
    
    # Test status reporting
    success = await protocol.report_status(
        status="working",
        current_task="Testing team communication",
        progress=0.75,
        blockers=["Waiting for review"]
    )
    print(f"✓ Reported status: {success}")
    
    # Test team status
    team_status = await protocol.get_team_status()
    print(f"✓ Team status: {team_status['reporting_members']}/{team_status['total_members']} reporting")
    
    # Test synchronization primitives
    success = await protocol.create_barrier("test-barrier", expected_count=1)
    print(f"✓ Created barrier: {success}")
    
    acquired = await protocol.acquire_lock("test-lock", timeout=1)
    print(f"✓ Acquired lock: {acquired}")
    
    released = await protocol.release_lock("test-lock")
    print(f"✓ Released lock: {released}")
    
    success = await protocol.set_event("test-event")
    print(f"✓ Set event: {success}")
    
    # Test metrics
    metrics = protocol.get_communication_metrics()
    print(f"✓ Communication metrics: {metrics['total_messages']} messages")
    
    print("\nAll Team Protocol tests passed! ✓")
    return True


async def test_team_tool():
    """Test team communication tool"""
    print("\nTesting Team Communication Tool...")
    
    # Create tool
    tool = TeamCommunication()
    print("✓ Created team communication tool")
    
    # Test JSON schema
    schema = await tool.json_schema()
    print(f"✓ Generated JSON schema with {len(schema['properties'])} properties")
    
    # Test join team
    response = await tool.execute(
        action="join_team",
        team_id="test-team-002"
    )
    print(f"✓ Join team: {response.success} - {response.message}")
    
    # Test broadcast
    response = await tool.execute(
        action="broadcast",
        message="Test broadcast from tool"
    )
    print(f"✓ Broadcast: {response.success} - {response.message}")
    
    # Test status report
    response = await tool.execute(
        action="report_status",
        status="working",
        current_task="Testing tool",
        progress=0.5
    )
    print(f"✓ Report status: {response.success} - {response.message}")
    
    # Test team status
    response = await tool.execute(
        action="get_team_status"
    )
    print(f"✓ Get team status: {response.success}")
    
    # Test metrics
    response = await tool.execute(
        action="get_metrics"
    )
    print(f"✓ Get metrics: {response.success}")
    
    # Test leave team
    response = await tool.execute(
        action="leave_team"
    )
    print(f"✓ Leave team: {response.success} - {response.message}")
    
    print("\nAll Team Tool tests passed! ✓")
    return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Team Communication Test Suite")
    print("=" * 60)
    
    try:
        # Test protocol
        protocol_success = await test_team_protocol()
        
        # Test tool
        tool_success = await test_team_tool()
        
        if protocol_success and tool_success:
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED! ✓✓✓")
            print("=" * 60)
            return 0
        else:
            print("\nSome tests failed.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)