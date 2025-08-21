"""
Document Handoff Protocol for Agile AI Company
Manages document transfers between agents with validation and state tracking.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json
from pathlib import Path
import pickle

try:
    from .document_manager import (
        Document, DocumentRegistry, DocumentStatus, 
        AccessLevel, get_document_registry
    )
except ImportError:
    from document_manager import (
        Document, DocumentRegistry, DocumentStatus, 
        AccessLevel, get_document_registry
    )


class HandoffStatus(Enum):
    """Status of a document handoff"""
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HandoffPriority(Enum):
    """Priority levels for handoffs"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class HandoffRequest:
    """A request to hand off a document"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    from_agent: str = ""
    to_agent: str = ""
    workflow_id: Optional[str] = None
    team_id: Optional[str] = None
    priority: HandoffPriority = HandoffPriority.MEDIUM
    
    # Handoff metadata
    reason: str = ""
    instructions: str = ""
    expected_action: str = ""
    deadline: Optional[datetime] = None
    
    # State tracking
    status: HandoffStatus = HandoffStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Response data
    response: Optional[str] = None
    result_document_id: Optional[str] = None
    
    # Validation requirements
    requires_validation: bool = True
    validation_checklist: Optional[str] = None
    validation_result: Optional[Dict] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data['created_at'] = self.created_at.isoformat()
        if self.delivered_at:
            data['delivered_at'] = self.delivered_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.deadline:
            data['deadline'] = self.deadline.isoformat()
        # Convert enums to values
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        # Convert ISO strings back to datetime
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'delivered_at' in data and data['delivered_at']:
            data['delivered_at'] = datetime.fromisoformat(data['delivered_at'])
        if 'completed_at' in data and data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        if 'deadline' in data and data['deadline']:
            data['deadline'] = datetime.fromisoformat(data['deadline'])
        # Convert values back to enums
        if 'status' in data:
            data['status'] = HandoffStatus(data['status'])
        if 'priority' in data:
            data['priority'] = HandoffPriority(data['priority'])
        return cls(**data)


@dataclass
class HandoffNotification:
    """Notification about a handoff event"""
    handoff_id: str
    event_type: str  # 'new', 'accepted', 'rejected', 'completed', 'failed'
    agent_id: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class HandoffProtocol:
    """Manages document handoffs between agents"""
    
    def __init__(self, storage_path: str = "./storage/handoffs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Get document registry
        self.document_registry = get_document_registry()
        
        # Handoff tracking
        self.active_handoffs: Dict[str, HandoffRequest] = {}
        self.agent_queues: Dict[str, List[str]] = {}  # agent_id -> [handoff_ids]
        self.workflow_handoffs: Dict[str, List[str]] = {}  # workflow_id -> [handoff_ids]
        self.completed_handoffs: Dict[str, HandoffRequest] = {}
        
        # Notification system
        self.notification_handlers: Dict[str, List[Callable]] = {}
        self.notifications: List[HandoffNotification] = []
        
        # Validation callbacks
        self.validation_handlers: Dict[str, Callable] = {}
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        # Load existing handoffs
        self._load_handoffs()
    
    def _load_handoffs(self):
        """Load handoffs from disk"""
        handoffs_file = self.storage_path / "handoffs.pkl"
        if handoffs_file.exists():
            try:
                with open(handoffs_file, 'rb') as f:
                    data = pickle.load(f)
                    
                    # Reconstruct handoffs
                    for handoff_id, handoff_data in data.get('active_handoffs', {}).items():
                        self.active_handoffs[handoff_id] = HandoffRequest.from_dict(handoff_data)
                    
                    for handoff_id, handoff_data in data.get('completed_handoffs', {}).items():
                        self.completed_handoffs[handoff_id] = HandoffRequest.from_dict(handoff_data)
                    
                    self.agent_queues = data.get('agent_queues', {})
                    self.workflow_handoffs = data.get('workflow_handoffs', {})
            except Exception as e:
                print(f"Error loading handoffs: {e}")
    
    def _save_handoffs(self):
        """Save handoffs to disk"""
        handoffs_file = self.storage_path / "handoffs.pkl"
        data = {
            'active_handoffs': {
                h_id: h.to_dict() for h_id, h in self.active_handoffs.items()
            },
            'completed_handoffs': {
                h_id: h.to_dict() for h_id, h in self.completed_handoffs.items()
            },
            'agent_queues': self.agent_queues,
            'workflow_handoffs': self.workflow_handoffs
        }
        with open(handoffs_file, 'wb') as f:
            pickle.dump(data, f)
    
    async def create_handoff(
        self,
        document_id: str,
        from_agent: str,
        to_agent: str,
        reason: str,
        instructions: str = "",
        expected_action: str = "",
        priority: HandoffPriority = HandoffPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        workflow_id: Optional[str] = None,
        team_id: Optional[str] = None,
        requires_validation: bool = True,
        validation_checklist: Optional[str] = None
    ) -> HandoffRequest:
        """Create a new handoff request"""
        async with self.lock:
            # Verify document exists
            document = await self.document_registry.get_document(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Verify from_agent has access
            has_access = await self.document_registry.check_access(
                document_id, from_agent, AccessLevel.READ
            )
            if not has_access:
                raise PermissionError(f"Agent {from_agent} does not have access to document {document_id}")
            
            # Create handoff request
            handoff = HandoffRequest(
                document_id=document_id,
                from_agent=from_agent,
                to_agent=to_agent,
                reason=reason,
                instructions=instructions,
                expected_action=expected_action,
                priority=priority,
                deadline=deadline,
                workflow_id=workflow_id,
                team_id=team_id,
                requires_validation=requires_validation,
                validation_checklist=validation_checklist
            )
            
            # Store handoff
            self.active_handoffs[handoff.id] = handoff
            
            # Add to agent queue
            if to_agent not in self.agent_queues:
                self.agent_queues[to_agent] = []
            self.agent_queues[to_agent].append(handoff.id)
            
            # Track by workflow
            if workflow_id:
                if workflow_id not in self.workflow_handoffs:
                    self.workflow_handoffs[workflow_id] = []
                self.workflow_handoffs[workflow_id].append(handoff.id)
            
            # Grant access to receiving agent
            await self.document_registry.grant_access(
                document_id, to_agent, AccessLevel.READ, from_agent
            )
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff.id,
                event_type='new',
                agent_id=to_agent,
                message=f"New document handoff from {from_agent}: {reason}",
                metadata={'document_id': document_id, 'priority': priority.value}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return handoff
    
    async def deliver_handoff(self, handoff_id: str) -> bool:
        """Mark handoff as delivered to agent"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            handoff.status = HandoffStatus.DELIVERED
            handoff.delivered_at = datetime.now(timezone.utc)
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='delivered',
                agent_id=handoff.to_agent,
                message=f"Handoff delivered to {handoff.to_agent}"
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True
    
    async def accept_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        response: Optional[str] = None
    ) -> bool:
        """Accept a handoff"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            
            # Verify it's the correct agent
            if handoff.to_agent != agent_id:
                return False
            
            handoff.status = HandoffStatus.ACCEPTED
            handoff.response = response
            
            # Grant write access if expected action requires it
            if handoff.expected_action in ['edit', 'update', 'modify', 'complete']:
                await self.document_registry.grant_access(
                    handoff.document_id, agent_id, AccessLevel.WRITE, handoff.from_agent
                )
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='accepted',
                agent_id=agent_id,
                message=f"Handoff accepted by {agent_id}",
                metadata={'response': response}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True
    
    async def reject_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        reason: str
    ) -> bool:
        """Reject a handoff"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            
            # Verify it's the correct agent
            if handoff.to_agent != agent_id:
                return False
            
            handoff.status = HandoffStatus.REJECTED
            handoff.response = reason
            handoff.completed_at = datetime.now(timezone.utc)
            
            # Move to completed
            self.completed_handoffs[handoff_id] = handoff
            del self.active_handoffs[handoff_id]
            
            # Remove from agent queue
            if agent_id in self.agent_queues:
                self.agent_queues[agent_id] = [
                    h_id for h_id in self.agent_queues[agent_id]
                    if h_id != handoff_id
                ]
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='rejected',
                agent_id=agent_id,
                message=f"Handoff rejected by {agent_id}: {reason}",
                metadata={'reason': reason}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True
    
    async def complete_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        result_document_id: Optional[str] = None,
        validation_result: Optional[Dict] = None
    ) -> bool:
        """Complete a handoff"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            
            # Verify it's the correct agent
            if handoff.to_agent != agent_id:
                return False
            
            # Perform validation if required
            if handoff.requires_validation and handoff.validation_checklist:
                if handoff.validation_checklist in self.validation_handlers:
                    validation_result = await self.validation_handlers[handoff.validation_checklist](
                        handoff, result_document_id
                    )
                    
                    if validation_result and not validation_result.get('passed', False):
                        handoff.status = HandoffStatus.FAILED
                        handoff.validation_result = validation_result
                        
                        # Send notification
                        await self._notify(HandoffNotification(
                            handoff_id=handoff_id,
                            event_type='failed',
                            agent_id=agent_id,
                            message=f"Handoff failed validation: {validation_result.get('reason', 'Unknown')}",
                            metadata={'validation_result': validation_result}
                        ))
                        
                        # Save to disk
                        self._save_handoffs()
                        return False
            
            # Mark as completed
            handoff.status = HandoffStatus.ACCEPTED
            handoff.completed_at = datetime.now(timezone.utc)
            handoff.result_document_id = result_document_id
            handoff.validation_result = validation_result
            
            # Move to completed
            self.completed_handoffs[handoff_id] = handoff
            del self.active_handoffs[handoff_id]
            
            # Remove from agent queue
            if agent_id in self.agent_queues:
                self.agent_queues[agent_id] = [
                    h_id for h_id in self.agent_queues[agent_id]
                    if h_id != handoff_id
                ]
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='completed',
                agent_id=agent_id,
                message=f"Handoff completed by {agent_id}",
                metadata={'result_document_id': result_document_id}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True
    
    async def get_agent_queue(
        self,
        agent_id: str,
        include_completed: bool = False
    ) -> List[HandoffRequest]:
        """Get all handoffs for an agent"""
        async with self.lock:
            handoffs = []
            
            # Get active handoffs
            if agent_id in self.agent_queues:
                for handoff_id in self.agent_queues[agent_id]:
                    if handoff_id in self.active_handoffs:
                        handoffs.append(self.active_handoffs[handoff_id])
            
            # Include completed if requested
            if include_completed:
                for handoff in self.completed_handoffs.values():
                    if handoff.to_agent == agent_id or handoff.from_agent == agent_id:
                        handoffs.append(handoff)
            
            # Sort by priority and created time
            handoffs.sort(key=lambda h: (-h.priority.value, h.created_at))
            
            return handoffs
    
    async def get_workflow_handoffs(
        self,
        workflow_id: str,
        include_completed: bool = False
    ) -> List[HandoffRequest]:
        """Get all handoffs for a workflow"""
        async with self.lock:
            handoffs = []
            
            if workflow_id in self.workflow_handoffs:
                for handoff_id in self.workflow_handoffs[workflow_id]:
                    if handoff_id in self.active_handoffs:
                        handoffs.append(self.active_handoffs[handoff_id])
                    elif include_completed and handoff_id in self.completed_handoffs:
                        handoffs.append(self.completed_handoffs[handoff_id])
            
            return handoffs
    
    async def cancel_handoff(
        self,
        handoff_id: str,
        canceller_id: str,
        reason: str
    ) -> bool:
        """Cancel a handoff"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            
            # Only from_agent or system can cancel
            if handoff.from_agent != canceller_id and canceller_id != "system":
                return False
            
            handoff.status = HandoffStatus.CANCELLED
            handoff.response = reason
            handoff.completed_at = datetime.now(timezone.utc)
            
            # Move to completed
            self.completed_handoffs[handoff_id] = handoff
            del self.active_handoffs[handoff_id]
            
            # Remove from agent queue
            if handoff.to_agent in self.agent_queues:
                self.agent_queues[handoff.to_agent] = [
                    h_id for h_id in self.agent_queues[handoff.to_agent]
                    if h_id != handoff_id
                ]
            
            # Send notification
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='cancelled',
                agent_id=handoff.to_agent,
                message=f"Handoff cancelled by {canceller_id}: {reason}",
                metadata={'reason': reason}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True
    
    async def check_deadlines(self) -> List[HandoffRequest]:
        """Check for handoffs past deadline"""
        async with self.lock:
            overdue = []
            now = datetime.now(timezone.utc)
            
            for handoff in self.active_handoffs.values():
                if handoff.deadline and handoff.deadline < now:
                    overdue.append(handoff)
            
            return overdue
    
    def register_notification_handler(
        self,
        agent_id: str,
        handler: Callable[[HandoffNotification], None]
    ):
        """Register a notification handler for an agent"""
        if agent_id not in self.notification_handlers:
            self.notification_handlers[agent_id] = []
        self.notification_handlers[agent_id].append(handler)
    
    def register_validation_handler(
        self,
        checklist_name: str,
        handler: Callable[[HandoffRequest, Optional[str]], Dict]
    ):
        """Register a validation handler for a checklist"""
        self.validation_handlers[checklist_name] = handler
    
    async def _notify(self, notification: HandoffNotification):
        """Send notification to registered handlers"""
        # Store notification
        self.notifications.append(notification)
        
        # Call registered handlers
        if notification.agent_id in self.notification_handlers:
            for handler in self.notification_handlers[notification.agent_id]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(notification)
                    else:
                        handler(notification)
                except Exception as e:
                    print(f"Error in notification handler: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get handoff statistics"""
        async with self.lock:
            stats = {
                'active_handoffs': len(self.active_handoffs),
                'completed_handoffs': len(self.completed_handoffs),
                'agents_with_queues': len(self.agent_queues),
                'workflows_with_handoffs': len(self.workflow_handoffs),
                'handoffs_by_status': {},
                'handoffs_by_priority': {},
                'average_completion_time': None
            }
            
            # Count by status
            for status in HandoffStatus:
                count = 0
                for handoff in self.active_handoffs.values():
                    if handoff.status == status:
                        count += 1
                for handoff in self.completed_handoffs.values():
                    if handoff.status == status:
                        count += 1
                stats['handoffs_by_status'][status.value] = count
            
            # Count by priority
            for priority in HandoffPriority:
                count = sum(
                    1 for h in self.active_handoffs.values()
                    if h.priority == priority
                )
                stats['handoffs_by_priority'][priority.value] = count
            
            # Calculate average completion time
            completion_times = []
            for handoff in self.completed_handoffs.values():
                if handoff.completed_at:
                    duration = (handoff.completed_at - handoff.created_at).total_seconds()
                    completion_times.append(duration)
            
            if completion_times:
                stats['average_completion_time'] = sum(completion_times) / len(completion_times)
            
            return stats
    
    async def create_batch_handoff(
        self,
        document_ids: List[str],
        from_agent: str,
        to_agents: List[str],
        reason: str,
        **kwargs
    ) -> List[HandoffRequest]:
        """Create multiple handoffs at once"""
        handoffs = []
        
        for doc_id in document_ids:
            for to_agent in to_agents:
                handoff = await self.create_handoff(
                    document_id=doc_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    reason=reason,
                    **kwargs
                )
                handoffs.append(handoff)
        
        return handoffs
    
    async def transfer_ownership(
        self,
        handoff_id: str,
        new_agent: str
    ) -> bool:
        """Transfer a handoff to a different agent"""
        async with self.lock:
            if handoff_id not in self.active_handoffs:
                return False
            
            handoff = self.active_handoffs[handoff_id]
            old_agent = handoff.to_agent
            
            # Update handoff
            handoff.to_agent = new_agent
            
            # Update agent queues
            if old_agent in self.agent_queues:
                self.agent_queues[old_agent] = [
                    h_id for h_id in self.agent_queues[old_agent]
                    if h_id != handoff_id
                ]
            
            if new_agent not in self.agent_queues:
                self.agent_queues[new_agent] = []
            self.agent_queues[new_agent].append(handoff_id)
            
            # Update document access
            await self.document_registry.revoke_access(
                handoff.document_id, old_agent, handoff.from_agent
            )
            await self.document_registry.grant_access(
                handoff.document_id, new_agent, AccessLevel.READ, handoff.from_agent
            )
            
            # Send notifications
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='transferred',
                agent_id=old_agent,
                message=f"Handoff transferred from {old_agent} to {new_agent}",
                metadata={'new_agent': new_agent}
            ))
            
            await self._notify(HandoffNotification(
                handoff_id=handoff_id,
                event_type='new',
                agent_id=new_agent,
                message=f"Handoff transferred to you from {old_agent}",
                metadata={'old_agent': old_agent}
            ))
            
            # Save to disk
            self._save_handoffs()
            
            return True


# Singleton instance
_protocol_instance: Optional[HandoffProtocol] = None


def get_handoff_protocol(storage_path: str = "./storage/handoffs") -> HandoffProtocol:
    """Get or create the handoff protocol singleton"""
    global _protocol_instance
    if _protocol_instance is None:
        _protocol_instance = HandoffProtocol(storage_path)
    return _protocol_instance