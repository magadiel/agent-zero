"""
Test suite for Handoff Protocol
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.append('..')
from handoff_protocol import (
    HandoffProtocol, HandoffRequest, HandoffNotification,
    HandoffStatus, HandoffPriority, get_handoff_protocol
)
from document_manager import (
    DocumentRegistry, DocumentType, DocumentStatus, AccessLevel
)


@pytest.mark.asyncio
class TestHandoffRequest:
    """Test HandoffRequest class"""
    
    def test_handoff_creation(self):
        """Test creating a handoff request"""
        handoff = HandoffRequest(
            document_id="doc123",
            from_agent="agent1",
            to_agent="agent2",
            reason="Review required",
            priority=HandoffPriority.HIGH
        )
        
        assert handoff.document_id == "doc123"
        assert handoff.from_agent == "agent1"
        assert handoff.to_agent == "agent2"
        assert handoff.reason == "Review required"
        assert handoff.priority == HandoffPriority.HIGH
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.requires_validation is True
        
    def test_handoff_serialization(self):
        """Test handoff to_dict and from_dict"""
        deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        handoff = HandoffRequest(
            document_id="doc456",
            from_agent="agent3",
            to_agent="agent4",
            reason="Update needed",
            deadline=deadline,
            validation_checklist="checklist1"
        )
        
        # Convert to dict
        data = handoff.to_dict()
        assert data['document_id'] == "doc456"
        assert data['status'] == HandoffStatus.PENDING.value
        assert data['priority'] == HandoffPriority.MEDIUM.value
        
        # Convert back from dict
        handoff2 = HandoffRequest.from_dict(data)
        assert handoff2.document_id == handoff.document_id
        assert handoff2.from_agent == handoff.from_agent
        assert handoff2.to_agent == handoff.to_agent
        assert handoff2.status == handoff.status
        assert handoff2.priority == handoff.priority


@pytest.mark.asyncio
class TestHandoffProtocol:
    """Test HandoffProtocol class"""
    
    @pytest.fixture
    async def setup(self):
        """Create temporary protocol and registry for testing"""
        temp_dir = tempfile.mkdtemp()
        doc_path = Path(temp_dir) / "documents"
        handoff_path = Path(temp_dir) / "handoffs"
        
        registry = DocumentRegistry(storage_path=str(doc_path))
        protocol = HandoffProtocol(storage_path=str(handoff_path))
        
        # Create some test documents
        doc1 = await registry.create_document(
            content="Test document 1",
            title="Doc 1",
            doc_type=DocumentType.PRD,
            created_by="owner1"
        )
        
        doc2 = await registry.create_document(
            content="Test document 2",
            title="Doc 2",
            doc_type=DocumentType.STORY,
            created_by="owner2"
        )
        
        yield {
            'protocol': protocol,
            'registry': registry,
            'doc1': doc1,
            'doc2': doc2,
            'temp_dir': temp_dir
        }
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    async def test_create_handoff(self, setup):
        """Test creating a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Please review this PRD",
            instructions="Check for completeness",
            expected_action="review",
            priority=HandoffPriority.HIGH,
            workflow_id="wf1",
            team_id="team1"
        )
        
        assert handoff.document_id == doc1.metadata.id
        assert handoff.from_agent == "owner1"
        assert handoff.to_agent == "reviewer1"
        assert handoff.reason == "Please review this PRD"
        assert handoff.priority == HandoffPriority.HIGH
        assert handoff.status == HandoffStatus.PENDING
        
        # Verify handoff is stored
        assert handoff.id in protocol.active_handoffs
        
        # Verify agent queue updated
        assert "reviewer1" in protocol.agent_queues
        assert handoff.id in protocol.agent_queues["reviewer1"]
        
        # Verify workflow tracking
        assert "wf1" in protocol.workflow_handoffs
        assert handoff.id in protocol.workflow_handoffs["wf1"]
        
    async def test_create_handoff_permission_denied(self, setup):
        """Test creating handoff without access"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Try to create handoff from agent without access
        with pytest.raises(PermissionError):
            await protocol.create_handoff(
                document_id=doc1.metadata.id,
                from_agent="unauthorized",
                to_agent="reviewer1",
                reason="Should fail"
            )
    
    async def test_create_handoff_document_not_found(self, setup):
        """Test creating handoff for non-existent document"""
        protocol = setup['protocol']
        
        with pytest.raises(ValueError):
            await protocol.create_handoff(
                document_id="non-existent",
                from_agent="owner1",
                to_agent="reviewer1",
                reason="Should fail"
            )
    
    async def test_deliver_handoff(self, setup):
        """Test delivering a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Deliver it
        delivered = await protocol.deliver_handoff(handoff.id)
        assert delivered is True
        
        # Check status updated
        updated_handoff = protocol.active_handoffs[handoff.id]
        assert updated_handoff.status == HandoffStatus.DELIVERED
        assert updated_handoff.delivered_at is not None
        
    async def test_accept_handoff(self, setup):
        """Test accepting a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        registry = setup['registry']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            expected_action="edit"
        )
        
        # Accept it
        accepted = await protocol.accept_handoff(
            handoff.id,
            "reviewer1",
            "I'll review this immediately"
        )
        assert accepted is True
        
        # Check status updated
        updated_handoff = protocol.active_handoffs[handoff.id]
        assert updated_handoff.status == HandoffStatus.ACCEPTED
        assert updated_handoff.response == "I'll review this immediately"
        
        # Check write access granted (because expected_action is "edit")
        has_write = await registry.check_access(
            doc1.metadata.id,
            "reviewer1",
            AccessLevel.WRITE
        )
        assert has_write is True
        
    async def test_accept_handoff_wrong_agent(self, setup):
        """Test accepting handoff by wrong agent"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Try to accept with wrong agent
        accepted = await protocol.accept_handoff(
            handoff.id,
            "wrong_agent",
            "Should fail"
        )
        assert accepted is False
        
    async def test_reject_handoff(self, setup):
        """Test rejecting a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Reject it
        rejected = await protocol.reject_handoff(
            handoff.id,
            "reviewer1",
            "Not enough context provided"
        )
        assert rejected is True
        
        # Check handoff moved to completed
        assert handoff.id not in protocol.active_handoffs
        assert handoff.id in protocol.completed_handoffs
        
        completed_handoff = protocol.completed_handoffs[handoff.id]
        assert completed_handoff.status == HandoffStatus.REJECTED
        assert completed_handoff.response == "Not enough context provided"
        assert completed_handoff.completed_at is not None
        
        # Check removed from agent queue
        assert handoff.id not in protocol.agent_queues.get("reviewer1", [])
        
    async def test_complete_handoff(self, setup):
        """Test completing a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        registry = setup['registry']
        
        # Create result document
        result_doc = await registry.create_document(
            content="Reviewed document",
            title="Review Result",
            doc_type=DocumentType.REPORT,
            created_by="reviewer1"
        )
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            requires_validation=False
        )
        
        # Complete it
        completed = await protocol.complete_handoff(
            handoff.id,
            "reviewer1",
            result_document_id=result_doc.metadata.id
        )
        assert completed is True
        
        # Check handoff moved to completed
        assert handoff.id not in protocol.active_handoffs
        assert handoff.id in protocol.completed_handoffs
        
        completed_handoff = protocol.completed_handoffs[handoff.id]
        assert completed_handoff.status == HandoffStatus.ACCEPTED
        assert completed_handoff.result_document_id == result_doc.metadata.id
        assert completed_handoff.completed_at is not None
        
    async def test_complete_handoff_with_validation(self, setup):
        """Test completing handoff with validation"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Register validation handler
        def validation_handler(handoff, result_doc_id):
            return {'passed': True, 'score': 95}
        
        protocol.register_validation_handler("test_checklist", validation_handler)
        
        # Create handoff with validation
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            requires_validation=True,
            validation_checklist="test_checklist"
        )
        
        # Complete it
        completed = await protocol.complete_handoff(
            handoff.id,
            "reviewer1"
        )
        assert completed is True
        
        completed_handoff = protocol.completed_handoffs[handoff.id]
        assert completed_handoff.validation_result['passed'] is True
        assert completed_handoff.validation_result['score'] == 95
        
    async def test_complete_handoff_validation_failed(self, setup):
        """Test completing handoff with failed validation"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Register failing validation handler
        async def validation_handler(handoff, result_doc_id):
            return {'passed': False, 'reason': 'Quality too low'}
        
        protocol.register_validation_handler("strict_checklist", validation_handler)
        
        # Create handoff with validation
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            requires_validation=True,
            validation_checklist="strict_checklist"
        )
        
        # Try to complete it
        completed = await protocol.complete_handoff(
            handoff.id,
            "reviewer1"
        )
        assert completed is False
        
        # Check status is failed
        failed_handoff = protocol.active_handoffs[handoff.id]
        assert failed_handoff.status == HandoffStatus.FAILED
        assert failed_handoff.validation_result['reason'] == 'Quality too low'
        
    async def test_cancel_handoff(self, setup):
        """Test cancelling a handoff"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Cancel it by original agent
        cancelled = await protocol.cancel_handoff(
            handoff.id,
            "owner1",
            "No longer needed"
        )
        assert cancelled is True
        
        # Check handoff moved to completed
        assert handoff.id not in protocol.active_handoffs
        assert handoff.id in protocol.completed_handoffs
        
        completed_handoff = protocol.completed_handoffs[handoff.id]
        assert completed_handoff.status == HandoffStatus.CANCELLED
        assert completed_handoff.response == "No longer needed"
        
    async def test_cancel_handoff_unauthorized(self, setup):
        """Test cancelling handoff by unauthorized agent"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Try to cancel by wrong agent
        cancelled = await protocol.cancel_handoff(
            handoff.id,
            "wrong_agent",
            "Should fail"
        )
        assert cancelled is False
        
        # Handoff should still be active
        assert handoff.id in protocol.active_handoffs
        
    async def test_get_agent_queue(self, setup):
        """Test getting agent's handoff queue"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        doc2 = setup['doc2']
        
        # Create multiple handoffs for same agent
        h1 = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review 1",
            priority=HandoffPriority.LOW
        )
        
        h2 = await protocol.create_handoff(
            document_id=doc2.metadata.id,
            from_agent="owner2",
            to_agent="reviewer1",
            reason="Review 2",
            priority=HandoffPriority.HIGH
        )
        
        # Get agent queue
        queue = await protocol.get_agent_queue("reviewer1")
        
        assert len(queue) == 2
        # Should be sorted by priority (high first)
        assert queue[0].priority == HandoffPriority.HIGH
        assert queue[1].priority == HandoffPriority.LOW
        
    async def test_get_agent_queue_with_completed(self, setup):
        """Test getting agent queue including completed"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create and complete a handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        await protocol.complete_handoff(
            handoff.id,
            "reviewer1"
        )
        
        # Get queue without completed
        queue1 = await protocol.get_agent_queue("reviewer1", include_completed=False)
        assert len(queue1) == 0
        
        # Get queue with completed
        queue2 = await protocol.get_agent_queue("reviewer1", include_completed=True)
        assert len(queue2) == 1
        
    async def test_get_workflow_handoffs(self, setup):
        """Test getting workflow handoffs"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        doc2 = setup['doc2']
        
        workflow_id = "test-workflow"
        
        # Create handoffs for workflow
        h1 = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            workflow_id=workflow_id
        )
        
        h2 = await protocol.create_handoff(
            document_id=doc2.metadata.id,
            from_agent="owner2",
            to_agent="reviewer2",
            reason="Review",
            workflow_id=workflow_id
        )
        
        # Get workflow handoffs
        handoffs = await protocol.get_workflow_handoffs(workflow_id)
        
        assert len(handoffs) == 2
        handoff_ids = {h.id for h in handoffs}
        assert h1.id in handoff_ids
        assert h2.id in handoff_ids
        
    async def test_check_deadlines(self, setup):
        """Test checking for overdue handoffs"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        doc2 = setup['doc2']
        
        # Create handoff with past deadline
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        h1 = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Urgent",
            deadline=past_deadline
        )
        
        # Create handoff with future deadline
        future_deadline = datetime.now(timezone.utc) + timedelta(hours=1)
        h2 = await protocol.create_handoff(
            document_id=doc2.metadata.id,
            from_agent="owner2",
            to_agent="reviewer2",
            reason="Normal",
            deadline=future_deadline
        )
        
        # Check deadlines
        overdue = await protocol.check_deadlines()
        
        assert len(overdue) == 1
        assert overdue[0].id == h1.id
        
    async def test_notifications(self, setup):
        """Test notification system"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        received_notifications = []
        
        # Register notification handler
        def handler(notification: HandoffNotification):
            received_notifications.append(notification)
        
        protocol.register_notification_handler("reviewer1", handler)
        
        # Create handoff (should trigger notification)
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Check notification received
        assert len(received_notifications) == 1
        assert received_notifications[0].event_type == 'new'
        assert received_notifications[0].agent_id == "reviewer1"
        assert received_notifications[0].handoff_id == handoff.id
        
    async def test_batch_handoff(self, setup):
        """Test creating batch handoffs"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        doc2 = setup['doc2']
        
        # Create batch handoffs
        handoffs = await protocol.create_batch_handoff(
            document_ids=[doc1.metadata.id, doc2.metadata.id],
            from_agent="owner1",
            to_agents=["reviewer1", "reviewer2"],
            reason="Batch review"
        )
        
        # Should create 2 docs * 2 agents = 4 handoffs
        assert len(handoffs) == 4
        
        # Verify all combinations created
        combinations = {(h.document_id, h.to_agent) for h in handoffs}
        assert (doc1.metadata.id, "reviewer1") in combinations
        assert (doc1.metadata.id, "reviewer2") in combinations
        assert (doc2.metadata.id, "reviewer1") in combinations
        assert (doc2.metadata.id, "reviewer2") in combinations
        
    async def test_transfer_ownership(self, setup):
        """Test transferring handoff to different agent"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        registry = setup['registry']
        
        # Create handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review"
        )
        
        # Transfer to different agent
        transferred = await protocol.transfer_ownership(
            handoff.id,
            "reviewer2"
        )
        assert transferred is True
        
        # Check handoff updated
        updated_handoff = protocol.active_handoffs[handoff.id]
        assert updated_handoff.to_agent == "reviewer2"
        
        # Check agent queues updated
        assert handoff.id not in protocol.agent_queues.get("reviewer1", [])
        assert handoff.id in protocol.agent_queues["reviewer2"]
        
        # Check document access updated
        has_access1 = await registry.check_access(
            doc1.metadata.id, "reviewer1", AccessLevel.READ
        )
        assert has_access1 is False
        
        has_access2 = await registry.check_access(
            doc1.metadata.id, "reviewer2", AccessLevel.READ
        )
        assert has_access2 is True
        
    async def test_statistics(self, setup):
        """Test getting handoff statistics"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        
        # Create some handoffs
        h1 = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Review",
            priority=HandoffPriority.HIGH
        )
        
        h2 = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer2",
            reason="Review",
            priority=HandoffPriority.LOW
        )
        
        # Complete one
        await protocol.complete_handoff(h1.id, "reviewer1")
        
        # Get statistics
        stats = await protocol.get_statistics()
        
        assert stats['active_handoffs'] == 1
        assert stats['completed_handoffs'] == 1
        assert stats['agents_with_queues'] >= 1
        assert stats['handoffs_by_priority'][HandoffPriority.HIGH.value] == 0  # Completed
        assert stats['handoffs_by_priority'][HandoffPriority.LOW.value] == 1
        assert stats['average_completion_time'] is not None
        
    async def test_persistence(self, setup):
        """Test that handoffs persist across protocol instances"""
        protocol = setup['protocol']
        doc1 = setup['doc1']
        handoff_path = protocol.storage_path
        
        # Create a handoff
        handoff = await protocol.create_handoff(
            document_id=doc1.metadata.id,
            from_agent="owner1",
            to_agent="reviewer1",
            reason="Persistence test"
        )
        
        handoff_id = handoff.id
        
        # Create new protocol instance with same storage path
        protocol2 = HandoffProtocol(storage_path=str(handoff_path))
        
        # Handoff should still be there
        assert handoff_id in protocol2.active_handoffs
        loaded_handoff = protocol2.active_handoffs[handoff_id]
        assert loaded_handoff.reason == "Persistence test"
        
        # Agent queue should be restored
        assert "reviewer1" in protocol2.agent_queues
        assert handoff_id in protocol2.agent_queues["reviewer1"]


def test_singleton():
    """Test singleton pattern"""
    protocol1 = get_handoff_protocol("/tmp/test1")
    protocol2 = get_handoff_protocol("/tmp/test2")  # Different path ignored
    
    assert protocol1 is protocol2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])