"""
Test suite for Team Communication Protocol and Tool
"""

import asyncio
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python.helpers.team_protocol import (
    TeamProtocol, TeamMessage, MessageType, VoteOption,
    VoteRequest, VoteResponse, StatusReport,
    create_team_protocol, broadcast_message, conduct_team_vote
)
from python.tools.team_communication import TeamCommunication


class TestTeamProtocol:
    """Test cases for TeamProtocol class"""
    
    @pytest.fixture
    def team_protocol(self):
        """Create a team protocol instance for testing"""
        return TeamProtocol(team_id="test-team-001", agent_id="agent-001")
    
    def test_initialization(self):
        """Test protocol initialization"""
        protocol = TeamProtocol("team-001", "agent-001")
        assert protocol.team_id == "team-001"
        assert protocol.agent_id == "agent-001"
        assert len(protocol.team_members) == 0
        assert len(protocol.message_history) == 0
    
    def test_team_message_creation(self):
        """Test TeamMessage creation and serialization"""
        message = TeamMessage(
            message_type=MessageType.BROADCAST,
            sender_id="agent-001",
            team_id="team-001",
            content="Test message",
            metadata={"key": "value"}
        )
        
        assert message.message_type == MessageType.BROADCAST
        assert message.sender_id == "agent-001"
        assert message.content == "Test message"
        
        # Test serialization
        msg_dict = message.to_dict()
        assert msg_dict['message_type'] == "broadcast"
        assert msg_dict['content'] == "Test message"
        assert 'timestamp' in msg_dict
    
    def test_vote_request_creation(self):
        """Test VoteRequest creation"""
        vote_request = VoteRequest(
            proposal="Should we proceed with deployment?",
            options=[VoteOption.YES, VoteOption.NO],
            threshold=0.75,
            allow_veto=True
        )
        
        assert vote_request.proposal == "Should we proceed with deployment?"
        assert VoteOption.YES in vote_request.options
        assert vote_request.threshold == 0.75
        assert vote_request.allow_veto is True
    
    def test_status_report_creation(self):
        """Test StatusReport creation"""
        report = StatusReport(
            agent_id="agent-001",
            team_id="team-001",
            status="working",
            current_task="Implementing feature X",
            progress=0.75,
            blockers=["Waiting for API access"]
        )
        
        assert report.status == "working"
        assert report.progress == 0.75
        assert "Waiting for API access" in report.blockers
    
    @pytest.mark.asyncio
    async def test_broadcast_without_members(self, team_protocol):
        """Test broadcasting when no team members are connected"""
        result = await team_protocol.broadcast_to_team("Test broadcast")
        
        assert result['recipients'] == 0
        assert len(team_protocol.message_history) == 1
        assert team_protocol.message_history[0].content == "Test broadcast"
    
    @pytest.mark.asyncio
    async def test_vote_request_creation_and_tracking(self, team_protocol):
        """Test creating and tracking vote requests"""
        vote_id = await team_protocol.request_team_vote(
            proposal="Approve new feature",
            threshold=0.6,
            deadline_minutes=10
        )
        
        assert vote_id in team_protocol.active_votes
        vote_request = team_protocol.active_votes[vote_id]
        assert vote_request.proposal == "Approve new feature"
        assert vote_request.threshold == 0.6
    
    @pytest.mark.asyncio
    async def test_submit_vote(self, team_protocol):
        """Test vote submission"""
        # Create a vote
        vote_id = await team_protocol.request_team_vote(
            proposal="Test proposal",
            threshold=0.5
        )
        
        # Submit a vote
        success = await team_protocol.submit_vote(
            vote_id=vote_id,
            vote=VoteOption.YES,
            reasoning="I agree with the proposal"
        )
        
        assert success is True
        assert len(team_protocol.vote_responses[vote_id]) == 1
        assert team_protocol.vote_responses[vote_id][0].vote == VoteOption.YES
    
    @pytest.mark.asyncio
    async def test_vote_tallying(self, team_protocol):
        """Test vote tallying and outcome determination"""
        # Create a vote
        vote_id = await team_protocol.request_team_vote(
            proposal="Test proposal",
            threshold=0.5
        )
        
        # Submit votes
        await team_protocol.submit_vote(vote_id, VoteOption.YES, "Agree")
        
        # Tally votes
        results = await team_protocol.tally_votes(vote_id)
        
        assert results['vote_id'] == vote_id
        assert results['total_votes'] == 1
        assert results['vote_counts']['yes'] == 1
        # With only 1 vote out of 1 member, it should pass
        assert results['outcome'] == 'PASSED'
    
    @pytest.mark.asyncio
    async def test_status_reporting(self, team_protocol):
        """Test status reporting"""
        success = await team_protocol.report_status(
            status="working",
            current_task="Testing",
            progress=0.5,
            blockers=["Need review"]
        )
        
        assert success is True
        assert team_protocol.agent_id in team_protocol.status_reports
        report = team_protocol.status_reports[team_protocol.agent_id]
        assert report.status == "working"
        assert report.progress == 0.5
    
    @pytest.mark.asyncio
    async def test_get_team_status(self, team_protocol):
        """Test aggregated team status"""
        # Report status
        await team_protocol.report_status(
            status="working",
            current_task="Task 1",
            progress=0.75
        )
        
        # Get team status
        team_status = await team_protocol.get_team_status()
        
        assert team_status['team_id'] == "test-team-001"
        assert team_status['total_members'] == 1  # Just self
        assert team_status['reporting_members'] == 1
        assert 'average_progress' in team_status
        assert team_status['average_progress'] == 0.75
    
    @pytest.mark.asyncio
    async def test_synchronization_barrier(self, team_protocol):
        """Test synchronization barrier creation"""
        success = await team_protocol.create_barrier("test-barrier", expected_count=2)
        
        assert success is True
        assert "test-barrier" in team_protocol.barriers
    
    @pytest.mark.asyncio
    async def test_lock_acquisition_and_release(self, team_protocol):
        """Test distributed lock mechanism"""
        # Acquire lock
        acquired = await team_protocol.acquire_lock("test-lock", timeout=1)
        assert acquired is True
        assert team_protocol.locks["test-lock"] == team_protocol.agent_id
        
        # Release lock
        released = await team_protocol.release_lock("test-lock")
        assert released is True
        assert team_protocol.locks["test-lock"] is None
    
    @pytest.mark.asyncio
    async def test_event_signaling(self, team_protocol):
        """Test event signaling mechanism"""
        # Set event
        success = await team_protocol.set_event("test-event")
        assert success is True
        assert team_protocol.events["test-event"] is True
        
        # Clear event
        success = await team_protocol.clear_event("test-event")
        assert success is True
        assert team_protocol.events["test-event"] is False
    
    def test_message_handler_registration(self, team_protocol):
        """Test registering message handlers"""
        handler = Mock()
        team_protocol.register_handler(MessageType.BROADCAST, handler)
        
        assert handler in team_protocol.message_handlers[MessageType.BROADCAST]
    
    @pytest.mark.asyncio
    async def test_process_incoming_message(self, team_protocol):
        """Test processing incoming messages"""
        handler = AsyncMock()
        team_protocol.register_handler(MessageType.BROADCAST, handler)
        
        message_data = {
            'message_id': 'msg-001',
            'message_type': 'broadcast',
            'sender_id': 'agent-002',
            'team_id': 'test-team-001',
            'content': 'Test message',
            'metadata': {},
            'timestamp': datetime.now().isoformat()
        }
        
        await team_protocol.process_incoming_message(message_data)
        
        assert len(team_protocol.message_history) == 1
        handler.assert_called_once()
    
    def test_get_communication_metrics(self, team_protocol):
        """Test communication metrics generation"""
        # Add some messages to history
        for i in range(5):
            team_protocol.message_history.append(
                TeamMessage(
                    message_type=MessageType.BROADCAST,
                    sender_id=f"agent-{i}",
                    team_id="test-team-001",
                    content=f"Message {i}"
                )
            )
        
        metrics = team_protocol.get_communication_metrics()
        
        assert metrics['total_messages'] == 5
        assert metrics['team_size'] == 1
        assert metrics['message_types']['broadcast'] == 5
    
    def test_clear_history(self, team_protocol):
        """Test clearing message history"""
        # Add messages
        for i in range(10):
            team_protocol.message_history.append(
                TeamMessage(
                    message_type=MessageType.BROADCAST,
                    sender_id="agent-001",
                    team_id="test-team-001",
                    content=f"Message {i}",
                    timestamp=datetime.now() - timedelta(hours=i)
                )
            )
        
        # Clear all
        team_protocol.clear_history()
        assert len(team_protocol.message_history) == 0
        
        # Add messages again
        for i in range(10):
            team_protocol.message_history.append(
                TeamMessage(
                    message_type=MessageType.BROADCAST,
                    sender_id="agent-001",
                    team_id="test-team-001",
                    content=f"Message {i}",
                    timestamp=datetime.now() - timedelta(hours=i)
                )
            )
        
        # Clear older than 5 hours
        team_protocol.clear_history(older_than=timedelta(hours=5))
        assert len(team_protocol.message_history) == 5


class TestTeamCommunicationTool:
    """Test cases for TeamCommunication tool"""
    
    @pytest.fixture
    def team_tool(self):
        """Create a team communication tool instance"""
        tool = TeamCommunication()
        tool.team_protocol = Mock(spec=TeamProtocol)
        tool.current_team_id = "test-team-001"
        return tool
    
    @pytest.mark.asyncio
    async def test_json_schema(self):
        """Test JSON schema generation"""
        tool = TeamCommunication()
        schema = await tool.json_schema()
        
        assert schema['type'] == 'object'
        assert 'action' in schema['properties']
        assert 'broadcast' in schema['properties']['action']['enum']
        assert 'vote_request' in schema['properties']['action']['enum']
    
    @pytest.mark.asyncio
    async def test_broadcast_action(self, team_tool):
        """Test broadcast action"""
        team_tool.team_protocol.broadcast_to_team = AsyncMock(
            return_value={'recipients': 3, 'message_id': 'msg-001'}
        )
        
        response = await team_tool.execute(
            action="broadcast",
            message="Test broadcast message"
        )
        
        assert response.success is True
        assert "3 team members" in response.message
        team_tool.team_protocol.broadcast_to_team.assert_called_once_with(
            "Test broadcast message", {}
        )
    
    @pytest.mark.asyncio
    async def test_vote_request_action(self, team_tool):
        """Test vote request action"""
        team_tool.team_protocol.request_team_vote = AsyncMock(
            return_value="vote-001"
        )
        
        response = await team_tool.execute(
            action="vote_request",
            message="Should we deploy?",
            threshold=0.75,
            deadline_minutes=10
        )
        
        assert response.success is True
        assert "vote-001" in response.message
        assert response.data['vote_id'] == "vote-001"
    
    @pytest.mark.asyncio
    async def test_submit_vote_action(self, team_tool):
        """Test submit vote action"""
        team_tool.team_protocol.submit_vote = AsyncMock(return_value=True)
        
        response = await team_tool.execute(
            action="submit_vote",
            vote_id="vote-001",
            vote="yes",
            reasoning="I agree"
        )
        
        assert response.success is True
        assert "submitted successfully" in response.message
    
    @pytest.mark.asyncio
    async def test_report_status_action(self, team_tool):
        """Test report status action"""
        team_tool.team_protocol.report_status = AsyncMock(return_value=True)
        
        response = await team_tool.execute(
            action="report_status",
            status="working",
            current_task="Testing",
            progress=0.5,
            blockers=["Need review"]
        )
        
        assert response.success is True
        assert "Status reported" in response.message
        assert response.data['progress'] == 0.5
    
    @pytest.mark.asyncio
    async def test_get_team_status_action(self, team_tool):
        """Test get team status action"""
        team_tool.team_protocol.get_team_status = AsyncMock(
            return_value={
                'team_id': 'test-team-001',
                'total_members': 5,
                'reporting_members': 4,
                'average_progress': 0.6,
                'status_distribution': {'working': 3, 'idle': 1},
                'all_blockers': []
            }
        )
        
        response = await team_tool.execute(action="get_team_status")
        
        assert response.success is True
        assert "4/5 reporting" in response.message
        assert "60.0%" in response.message
    
    @pytest.mark.asyncio
    async def test_synchronization_actions(self, team_tool):
        """Test synchronization primitive actions"""
        # Test barrier creation
        team_tool.team_protocol.create_barrier = AsyncMock(return_value=True)
        response = await team_tool.execute(
            action="create_barrier",
            barrier_id="test-barrier"
        )
        assert response.success is True
        
        # Test lock acquisition
        team_tool.team_protocol.acquire_lock = AsyncMock(return_value=True)
        response = await team_tool.execute(
            action="acquire_lock",
            lock_id="test-lock"
        )
        assert response.success is True
        
        # Test event setting
        team_tool.team_protocol.set_event = AsyncMock(return_value=True)
        response = await team_tool.execute(
            action="set_event",
            event_id="test-event"
        )
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_join_team_action(self):
        """Test join team action"""
        tool = TeamCommunication()
        
        with patch.object(tool, '_initialize_protocol', new_callable=AsyncMock):
            response = await tool.execute(
                action="join_team",
                team_id="new-team-001"
            )
            
            assert response.success is True
            assert "new-team-001" in response.message
            tool._initialize_protocol.assert_called_once_with("new-team-001")
    
    @pytest.mark.asyncio
    async def test_leave_team_action(self, team_tool):
        """Test leave team action"""
        response = await team_tool.execute(action="leave_team")
        
        assert response.success is True
        assert "test-team-001" in response.message
        assert team_tool.team_protocol is None
        assert team_tool.current_team_id is None
    
    @pytest.mark.asyncio
    async def test_get_metrics_action(self, team_tool):
        """Test get metrics action"""
        team_tool.team_protocol.get_communication_metrics = Mock(
            return_value={
                'total_messages': 100,
                'team_size': 5,
                'avg_latency_ms': 25.5,
                'avg_response_time_s': 2.3
            }
        )
        
        response = await team_tool.execute(action="get_metrics")
        
        assert response.success is True
        assert "100" in response.message
        assert "25.50ms" in response.message
        assert "2.30s" in response.message
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in tool execution"""
        tool = TeamCommunication()
        
        # Test missing action
        response = await tool.execute()
        assert response.success is False
        assert "Action is required" in response.message
        
        # Test unknown action
        response = await tool.execute(action="unknown_action")
        assert response.success is False
        assert "Unknown action" in response.message
        
        # Test missing required parameters
        response = await tool.execute(action="submit_vote")
        assert response.success is False
        assert "vote_id and vote are required" in response.message


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions"""
    with patch('python.helpers.team_protocol.TeamProtocol') as MockProtocol:
        mock_protocol = AsyncMock(spec=TeamProtocol)
        MockProtocol.return_value = mock_protocol
        
        # Test create_team_protocol
        protocol = await create_team_protocol(
            "team-001",
            "agent-001",
            {"agent-002": "http://agent2"}
        )
        
        assert protocol is not None
        mock_protocol.add_team_member.assert_called_once()
        
        # Test broadcast_message
        mock_protocol.broadcast_to_team = AsyncMock(
            return_value={'recipients': 2}
        )
        
        with patch('python.helpers.team_protocol.create_team_protocol', 
                  return_value=mock_protocol):
            result = await broadcast_message(
                "team-001",
                "Test message",
                {"agent-002": "http://agent2"}
            )
            
            assert result['recipients'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])