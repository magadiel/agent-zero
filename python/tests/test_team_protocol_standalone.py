#!/usr/bin/env python3
"""
Standalone test for team protocol (no external dependencies)
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Only import the protocol components
from python.helpers.team_protocol import (
    TeamProtocol, TeamMessage, MessageType, VoteOption,
    VoteRequest, StatusReport, VoteResponse
)


async def test_team_protocol_basic():
    """Test basic team protocol functionality without external dependencies"""
    print("=" * 60)
    print("Testing Team Protocol Core Functionality")
    print("=" * 60)
    
    # 1. Create protocol instance
    print("\n1. Testing Protocol Initialization...")
    protocol = TeamProtocol("test-team-001", "agent-001")
    assert protocol.team_id == "test-team-001"
    assert protocol.agent_id == "agent-001"
    print(f"   ✓ Created protocol for team '{protocol.team_id}' with agent '{protocol.agent_id}'")
    
    # 2. Test message creation
    print("\n2. Testing Message Creation...")
    message = TeamMessage(
        message_type=MessageType.BROADCAST,
        sender_id="agent-001",
        team_id="test-team-001",
        content="Test broadcast message"
    )
    assert message.message_type == MessageType.BROADCAST
    assert message.content == "Test broadcast message"
    msg_dict = message.to_dict()
    assert msg_dict['message_type'] == "broadcast"
    print(f"   ✓ Created broadcast message: '{message.content}'")
    print(f"   ✓ Message serialization works: {msg_dict['message_id'][:8]}...")
    
    # 3. Test vote creation and submission
    print("\n3. Testing Voting System...")
    vote_id = await protocol.request_team_vote(
        proposal="Should we proceed with deployment?",
        threshold=0.5,
        deadline_minutes=5,
        allow_veto=True
    )
    assert vote_id in protocol.active_votes
    print(f"   ✓ Created vote request with ID: {vote_id[:8]}...")
    
    # Submit a vote
    success = await protocol.submit_vote(
        vote_id=vote_id,
        vote=VoteOption.YES,
        reasoning="I agree with the deployment plan"
    )
    assert success == True
    assert len(protocol.vote_responses[vote_id]) == 1
    print(f"   ✓ Submitted vote: YES with reasoning")
    
    # Tally votes
    results = await protocol.tally_votes(vote_id)
    assert results['vote_id'] == vote_id
    assert results['outcome'] in ['PASSED', 'FAILED', 'NO_QUORUM', 'VETOED']
    print(f"   ✓ Vote tally complete: {results['outcome']}")
    print(f"     - Total votes: {results['total_votes']}")
    print(f"     - Vote counts: {results['vote_counts']}")
    
    # 4. Test status reporting
    print("\n4. Testing Status Reporting...")
    success = await protocol.report_status(
        status="working",
        current_task="Testing team communication",
        progress=0.75,
        blockers=["Waiting for code review"],
        metrics={"tasks_completed": 5, "efficiency": 0.85}
    )
    assert success == True
    assert protocol.agent_id in protocol.status_reports
    print(f"   ✓ Reported status: working (75% complete)")
    
    # Get team status
    team_status = await protocol.get_team_status()
    assert team_status['team_id'] == "test-team-001"
    assert team_status['reporting_members'] == 1
    print(f"   ✓ Team status retrieved: {team_status['reporting_members']}/{team_status['total_members']} reporting")
    if 'average_progress' in team_status:
        print(f"     - Average progress: {team_status['average_progress']*100:.1f}%")
    
    # 5. Test synchronization primitives
    print("\n5. Testing Synchronization Primitives...")
    
    # Barrier
    success = await protocol.create_barrier("deployment-barrier", expected_count=1)
    assert success == True
    print(f"   ✓ Created synchronization barrier: 'deployment-barrier'")
    
    # Lock
    acquired = await protocol.acquire_lock("resource-lock", timeout=1)
    assert acquired == True
    assert protocol.locks["resource-lock"] == protocol.agent_id
    print(f"   ✓ Acquired distributed lock: 'resource-lock'")
    
    released = await protocol.release_lock("resource-lock")
    assert released == True
    assert protocol.locks["resource-lock"] == None
    print(f"   ✓ Released distributed lock: 'resource-lock'")
    
    # Event
    success = await protocol.set_event("data-ready")
    assert success == True
    assert protocol.events["data-ready"] == True
    print(f"   ✓ Set event flag: 'data-ready'")
    
    success = await protocol.clear_event("data-ready")
    assert success == True
    assert protocol.events["data-ready"] == False
    print(f"   ✓ Cleared event flag: 'data-ready'")
    
    # 6. Test message history and metrics
    print("\n6. Testing Metrics and History...")
    
    # Add some messages to history
    for i in range(3):
        protocol.message_history.append(
            TeamMessage(
                message_type=MessageType.STATUS_REPORT if i % 2 == 0 else MessageType.BROADCAST,
                sender_id=f"agent-00{i+1}",
                team_id="test-team-001",
                content=f"Message {i+1}"
            )
        )
    
    metrics = protocol.get_communication_metrics()
    assert metrics['total_messages'] >= 3  # At least the ones we just added
    assert metrics['team_size'] == 1  # Just self
    print(f"   ✓ Communication metrics:")
    print(f"     - Total messages: {metrics['total_messages']}")
    print(f"     - Team size: {metrics['team_size']}")
    print(f"     - Message types: {dict(metrics['message_types'])}")
    
    # Clear history
    initial_count = len(protocol.message_history)
    protocol.clear_history()
    assert len(protocol.message_history) == 0
    print(f"   ✓ Cleared message history ({initial_count} messages removed)")
    
    # 7. Test broadcast without team members
    print("\n7. Testing Broadcast (No Team Members)...")
    result = await protocol.broadcast_to_team(
        message="Important announcement",
        metadata={"priority": "high"}
    )
    assert result['recipients'] == 0  # No other members
    assert 'message_id' in result
    print(f"   ✓ Broadcast sent (0 recipients - no team members connected)")
    print(f"     - Message ID: {result['message_id'][:8]}...")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓✓✓")
    print("Team Protocol is working correctly!")
    print("=" * 60)
    
    return True


async def test_vote_scenarios():
    """Test different voting scenarios"""
    print("\n" + "=" * 60)
    print("Testing Voting Scenarios")
    print("=" * 60)
    
    protocol = TeamProtocol("voting-team", "facilitator")
    
    # Scenario 1: Vote with veto
    print("\n1. Testing Veto Scenario...")
    vote_id = await protocol.request_team_vote(
        proposal="Implement risky feature",
        options=[VoteOption.YES, VoteOption.NO, VoteOption.ABSTAIN, VoteOption.VETO],
        threshold=0.5,
        allow_veto=True
    )
    
    # Simulate multiple votes
    await protocol.submit_vote(vote_id, VoteOption.YES, "Good idea")
    
    # Add a veto response manually (simulating another agent)
    protocol.vote_responses[vote_id].append(
        VoteResponse(vote_id=vote_id, agent_id="agent-002", vote=VoteOption.VETO, reasoning="Too risky")
    )
    
    results = await protocol.tally_votes(vote_id)
    assert results['outcome'] == 'VETOED'
    print(f"   ✓ Vote was vetoed as expected")
    
    # Scenario 2: Vote passes with threshold
    print("\n2. Testing Passing Vote...")
    vote_id2 = await protocol.request_team_vote(
        proposal="Regular deployment",
        threshold=0.3,  # Low threshold for testing
        allow_veto=False
    )
    
    await protocol.submit_vote(vote_id2, VoteOption.YES, "Ready to deploy")
    results2 = await protocol.tally_votes(vote_id2)
    assert results2['outcome'] == 'PASSED'  # Should pass with 1 yes vote and low threshold
    print(f"   ✓ Vote passed with threshold met")
    
    print("\nVoting scenarios completed successfully! ✓")
    return True


async def main():
    """Run all tests"""
    try:
        # Run basic tests
        await test_team_protocol_basic()
        
        # Run voting scenarios
        await test_vote_scenarios()
        
        print("\n" + "🎉 " * 20)
        print("All Team Protocol tests completed successfully!")
        print("The implementation is ready for use.")
        print("🎉 " * 20)
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)