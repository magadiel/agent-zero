"""
Team Communication Protocol for Agent-Zero

This module extends the A2A (Agent-to-Agent) protocol to support team-based communication,
including broadcast messaging, voting mechanisms, status reporting, and synchronization primitives.
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import A2A client for base communication
try:
    from python.helpers.fasta2a_client import AgentConnection
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
    AgentConnection = None

# Import team orchestrator for team management
try:
    from coordination.team_orchestrator import Team, TeamOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    Team = None
    TeamOrchestrator = None

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of team messages"""
    BROADCAST = "broadcast"
    VOTE_REQUEST = "vote_request"
    VOTE_RESPONSE = "vote_response"
    STATUS_REPORT = "status_report"
    SYNC_BARRIER = "sync_barrier"
    SYNC_RELEASE = "sync_release"
    TASK_ASSIGNMENT = "task_assignment"
    KNOWLEDGE_SHARE = "knowledge_share"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"


class VoteOption(Enum):
    """Voting options for team decisions"""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"
    VETO = "veto"


class SyncPrimitive(Enum):
    """Synchronization primitive types"""
    BARRIER = "barrier"         # All agents must reach before continuing
    LOCK = "lock"               # Mutex for exclusive access
    SEMAPHORE = "semaphore"     # Limited concurrent access
    EVENT = "event"             # Signal-based synchronization
    COUNTDOWN_LATCH = "countdown_latch"  # Wait for N agents


@dataclass
class TeamMessage:
    """Structured team message"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.BROADCAST
    sender_id: str = ""
    team_id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'team_id': self.team_id,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'requires_response': self.requires_response,
            'response_deadline': self.response_deadline.isoformat() if self.response_deadline else None
        }


@dataclass
class VoteRequest:
    """Vote request for team decisions"""
    vote_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposal: str = ""
    options: List[VoteOption] = field(default_factory=list)
    threshold: float = 0.5  # Percentage needed to pass
    deadline: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    allow_veto: bool = False
    anonymous: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoteResponse:
    """Individual vote response"""
    vote_id: str
    agent_id: str
    vote: VoteOption
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class StatusReport:
    """Agent status report"""
    agent_id: str
    team_id: str
    status: str  # "idle", "working", "blocked", "error"
    current_task: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    blockers: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class TeamProtocol:
    """
    Team communication protocol implementation.
    Extends A2A protocol with team-specific communication patterns.
    """
    
    def __init__(self, team_id: str, agent_id: Optional[str] = None):
        """
        Initialize team protocol.
        
        Args:
            team_id: ID of the team
            agent_id: ID of the current agent (optional)
        """
        self.team_id = team_id
        self.agent_id = agent_id or str(uuid.uuid4())
        self.team_members: Dict[str, AgentConnection] = {}
        self.message_history: List[TeamMessage] = []
        self.active_votes: Dict[str, VoteRequest] = {}
        self.vote_responses: Dict[str, List[VoteResponse]] = defaultdict(list)
        self.status_reports: Dict[str, StatusReport] = {}
        
        # Synchronization primitives
        self.barriers: Dict[str, Set[str]] = defaultdict(set)
        self.locks: Dict[str, Optional[str]] = defaultdict(lambda: None)
        self.semaphores: Dict[str, int] = defaultdict(lambda: 1)
        self.events: Dict[str, bool] = defaultdict(bool)
        self.latches: Dict[str, int] = defaultdict(int)
        
        # Callbacks for message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        
        # Performance tracking
        self.message_latencies: List[float] = []
        self.response_times: Dict[str, float] = {}
        
        logger.info(f"TeamProtocol initialized for team {team_id}, agent {agent_id}")
    
    async def add_team_member(self, agent_id: str, agent_url: str, token: Optional[str] = None):
        """
        Add a team member connection.
        
        Args:
            agent_id: ID of the agent
            agent_url: URL of the agent's A2A endpoint
            token: Optional authentication token
        """
        if not A2A_AVAILABLE:
            raise RuntimeError("A2A client not available for team communication")
        
        try:
            connection = AgentConnection(agent_url, token=token)
            await connection.get_agent_card()
            self.team_members[agent_id] = connection
            logger.info(f"Added team member {agent_id} at {agent_url}")
        except Exception as e:
            logger.error(f"Failed to add team member {agent_id}: {e}")
            raise
    
    async def remove_team_member(self, agent_id: str):
        """Remove a team member."""
        if agent_id in self.team_members:
            del self.team_members[agent_id]
            logger.info(f"Removed team member {agent_id}")
    
    async def broadcast_to_team(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Broadcast a message to all team members.
        
        Args:
            message: Message content
            metadata: Optional metadata
            
        Returns:
            Dictionary with broadcast results
        """
        team_message = TeamMessage(
            message_type=MessageType.BROADCAST,
            sender_id=self.agent_id,
            team_id=self.team_id,
            content=message,
            metadata=metadata or {}
        )
        
        self.message_history.append(team_message)
        
        results = {}
        tasks = []
        
        for member_id, connection in self.team_members.items():
            if member_id != self.agent_id:  # Don't send to self
                task = self._send_to_member(member_id, connection, team_message)
                tasks.append(task)
        
        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for i, (member_id, _) in enumerate(self.team_members.items()):
                if member_id != self.agent_id:
                    results[member_id] = responses[i] if i < len(responses) else None
        
        logger.info(f"Broadcast sent to {len(results)} team members")
        return {
            'message_id': team_message.message_id,
            'recipients': len(results),
            'responses': results
        }
    
    async def _send_to_member(self, member_id: str, connection: AgentConnection, 
                             message: TeamMessage) -> Tuple[str, Any]:
        """Send message to a specific team member."""
        try:
            response = await connection.send_message(
                message=json.dumps(message.to_dict()),
                metadata={'team_protocol': True, 'message_type': message.message_type.value}
            )
            return member_id, response
        except Exception as e:
            logger.error(f"Failed to send to {member_id}: {e}")
            return member_id, {'error': str(e)}
    
    async def request_team_vote(self, proposal: str, options: Optional[List[VoteOption]] = None,
                                threshold: float = 0.5, deadline_minutes: int = 5,
                                allow_veto: bool = False, anonymous: bool = False) -> str:
        """
        Request a vote from the team.
        
        Args:
            proposal: The proposal to vote on
            options: Vote options (defaults to YES/NO/ABSTAIN)
            threshold: Percentage needed to pass (0.0 to 1.0)
            deadline_minutes: Minutes until vote closes
            allow_veto: Whether veto is allowed
            anonymous: Whether voting is anonymous
            
        Returns:
            Vote ID for tracking
        """
        if options is None:
            options = [VoteOption.YES, VoteOption.NO, VoteOption.ABSTAIN]
            if allow_veto:
                options.append(VoteOption.VETO)
        
        vote_request = VoteRequest(
            proposal=proposal,
            options=options,
            threshold=threshold,
            deadline=datetime.now() + timedelta(minutes=deadline_minutes),
            allow_veto=allow_veto,
            anonymous=anonymous
        )
        
        self.active_votes[vote_request.vote_id] = vote_request
        
        # Send vote request to all members
        vote_message = TeamMessage(
            message_type=MessageType.VOTE_REQUEST,
            sender_id=self.agent_id,
            team_id=self.team_id,
            content=proposal,
            metadata={
                'vote_id': vote_request.vote_id,
                'options': [opt.value for opt in options],
                'threshold': threshold,
                'deadline': vote_request.deadline.isoformat(),
                'allow_veto': allow_veto,
                'anonymous': anonymous
            },
            requires_response=True,
            response_deadline=vote_request.deadline
        )
        
        await self.broadcast_to_team(json.dumps(vote_message.to_dict()))
        logger.info(f"Vote request {vote_request.vote_id} sent for: {proposal}")
        
        return vote_request.vote_id
    
    async def submit_vote(self, vote_id: str, vote: VoteOption, 
                         reasoning: Optional[str] = None) -> bool:
        """
        Submit a vote response.
        
        Args:
            vote_id: ID of the vote
            vote: Vote option
            reasoning: Optional reasoning for the vote
            
        Returns:
            Whether vote was successfully submitted
        """
        if vote_id not in self.active_votes:
            logger.warning(f"Vote {vote_id} not found")
            return False
        
        vote_request = self.active_votes[vote_id]
        if datetime.now() > vote_request.deadline:
            logger.warning(f"Vote {vote_id} has expired")
            return False
        
        vote_response = VoteResponse(
            vote_id=vote_id,
            agent_id=self.agent_id,
            vote=vote,
            reasoning=reasoning
        )
        
        self.vote_responses[vote_id].append(vote_response)
        logger.info(f"Vote submitted for {vote_id}: {vote.value}")
        
        return True
    
    async def tally_votes(self, vote_id: str) -> Dict[str, Any]:
        """
        Tally votes and determine outcome.
        
        Args:
            vote_id: ID of the vote
            
        Returns:
            Vote results including outcome
        """
        if vote_id not in self.active_votes:
            return {'error': 'Vote not found'}
        
        vote_request = self.active_votes[vote_id]
        responses = self.vote_responses[vote_id]
        
        # Count votes
        vote_counts = defaultdict(int)
        for response in responses:
            vote_counts[response.vote] += 1
        
        total_votes = len(responses)
        total_members = len(self.team_members) + 1  # Include self
        
        # Check for veto
        if vote_request.allow_veto and vote_counts.get(VoteOption.VETO, 0) > 0:
            outcome = 'VETOED'
        # Check if threshold met
        elif total_votes > 0:
            yes_votes = vote_counts.get(VoteOption.YES, 0)
            if yes_votes / total_members >= vote_request.threshold:
                outcome = 'PASSED'
            else:
                outcome = 'FAILED'
        else:
            outcome = 'NO_QUORUM'
        
        results = {
            'vote_id': vote_id,
            'proposal': vote_request.proposal,
            'outcome': outcome,
            'vote_counts': {opt.value: vote_counts.get(opt, 0) for opt in vote_request.options},
            'total_votes': total_votes,
            'total_members': total_members,
            'participation_rate': total_votes / total_members if total_members > 0 else 0,
            'threshold': vote_request.threshold,
            'deadline': vote_request.deadline.isoformat()
        }
        
        # Include reasoning if not anonymous
        if not vote_request.anonymous:
            results['reasoning'] = [
                {'agent_id': r.agent_id, 'vote': r.vote.value, 'reasoning': r.reasoning}
                for r in responses
            ]
        
        logger.info(f"Vote {vote_id} outcome: {outcome}")
        return results
    
    async def report_status(self, status: str, current_task: Optional[str] = None,
                           progress: float = 0.0, blockers: Optional[List[str]] = None,
                           metrics: Optional[Dict[str, float]] = None) -> bool:
        """
        Report agent status to the team.
        
        Args:
            status: Current status ("idle", "working", "blocked", "error")
            current_task: Current task being worked on
            progress: Progress percentage (0.0 to 1.0)
            blockers: List of blockers
            metrics: Performance metrics
            
        Returns:
            Whether status was reported successfully
        """
        status_report = StatusReport(
            agent_id=self.agent_id,
            team_id=self.team_id,
            status=status,
            current_task=current_task,
            progress=progress,
            blockers=blockers or [],
            metrics=metrics or {}
        )
        
        self.status_reports[self.agent_id] = status_report
        
        # Broadcast status to team
        status_message = TeamMessage(
            message_type=MessageType.STATUS_REPORT,
            sender_id=self.agent_id,
            team_id=self.team_id,
            content=f"Status: {status}",
            metadata={
                'status': status,
                'current_task': current_task,
                'progress': progress,
                'blockers': blockers or [],
                'metrics': metrics or {}
            }
        )
        
        await self.broadcast_to_team(json.dumps(status_message.to_dict()))
        logger.info(f"Status reported: {status} ({progress*100:.1f}% complete)")
        
        return True
    
    async def get_team_status(self) -> Dict[str, Any]:
        """
        Get aggregated team status.
        
        Returns:
            Team status summary
        """
        team_status = {
            'team_id': self.team_id,
            'total_members': len(self.team_members) + 1,
            'reporting_members': len(self.status_reports),
            'timestamp': datetime.now().isoformat(),
            'members': {}
        }
        
        # Add individual member statuses
        for agent_id, report in self.status_reports.items():
            team_status['members'][agent_id] = {
                'status': report.status,
                'current_task': report.current_task,
                'progress': report.progress,
                'blockers': report.blockers,
                'last_update': report.timestamp.isoformat()
            }
        
        # Calculate aggregate metrics
        if self.status_reports:
            avg_progress = sum(r.progress for r in self.status_reports.values()) / len(self.status_reports)
            team_status['average_progress'] = avg_progress
            
            status_counts = defaultdict(int)
            for report in self.status_reports.values():
                status_counts[report.status] += 1
            team_status['status_distribution'] = dict(status_counts)
            
            all_blockers = []
            for report in self.status_reports.values():
                all_blockers.extend(report.blockers)
            team_status['all_blockers'] = list(set(all_blockers))
        
        return team_status
    
    # Synchronization Primitives
    
    async def create_barrier(self, barrier_id: str, expected_count: Optional[int] = None) -> bool:
        """
        Create a synchronization barrier.
        
        Args:
            barrier_id: Unique barrier identifier
            expected_count: Number of agents to wait for (defaults to team size)
            
        Returns:
            Whether barrier was created
        """
        if expected_count is None:
            expected_count = len(self.team_members) + 1
        
        self.barriers[barrier_id] = set()
        
        # Notify team about barrier
        barrier_message = TeamMessage(
            message_type=MessageType.SYNC_BARRIER,
            sender_id=self.agent_id,
            team_id=self.team_id,
            content=f"Barrier created: {barrier_id}",
            metadata={
                'barrier_id': barrier_id,
                'expected_count': expected_count,
                'action': 'create'
            }
        )
        
        await self.broadcast_to_team(json.dumps(barrier_message.to_dict()))
        logger.info(f"Barrier {barrier_id} created, expecting {expected_count} agents")
        
        return True
    
    async def wait_at_barrier(self, barrier_id: str, timeout: Optional[int] = None) -> bool:
        """
        Wait at a synchronization barrier.
        
        Args:
            barrier_id: Barrier identifier
            timeout: Optional timeout in seconds
            
        Returns:
            Whether all agents reached the barrier
        """
        self.barriers[barrier_id].add(self.agent_id)
        
        # Notify arrival at barrier
        arrival_message = TeamMessage(
            message_type=MessageType.SYNC_BARRIER,
            sender_id=self.agent_id,
            team_id=self.team_id,
            content=f"Arrived at barrier: {barrier_id}",
            metadata={
                'barrier_id': barrier_id,
                'action': 'arrive',
                'waiting_count': len(self.barriers[barrier_id])
            }
        )
        
        await self.broadcast_to_team(json.dumps(arrival_message.to_dict()))
        
        # Wait for all agents
        expected_count = len(self.team_members) + 1
        start_time = datetime.now()
        
        while len(self.barriers[barrier_id]) < expected_count:
            if timeout and (datetime.now() - start_time).seconds > timeout:
                logger.warning(f"Barrier {barrier_id} timeout")
                return False
            await asyncio.sleep(0.5)
        
        # All agents reached barrier
        if self.agent_id == min(self.barriers[barrier_id]):  # First agent releases
            release_message = TeamMessage(
                message_type=MessageType.SYNC_RELEASE,
                sender_id=self.agent_id,
                team_id=self.team_id,
                content=f"Barrier released: {barrier_id}",
                metadata={'barrier_id': barrier_id}
            )
            await self.broadcast_to_team(json.dumps(release_message.to_dict()))
        
        logger.info(f"Barrier {barrier_id} passed")
        return True
    
    async def acquire_lock(self, lock_id: str, timeout: Optional[int] = None) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_id: Lock identifier
            timeout: Optional timeout in seconds
            
        Returns:
            Whether lock was acquired
        """
        start_time = datetime.now()
        
        while self.locks[lock_id] is not None:
            if timeout and (datetime.now() - start_time).seconds > timeout:
                logger.warning(f"Lock {lock_id} acquisition timeout")
                return False
            await asyncio.sleep(0.1)
        
        self.locks[lock_id] = self.agent_id
        logger.info(f"Lock {lock_id} acquired")
        return True
    
    async def release_lock(self, lock_id: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_id: Lock identifier
            
        Returns:
            Whether lock was released
        """
        if self.locks[lock_id] == self.agent_id:
            self.locks[lock_id] = None
            logger.info(f"Lock {lock_id} released")
            return True
        return False
    
    async def acquire_semaphore(self, semaphore_id: str, permits: int = 1,
                               timeout: Optional[int] = None) -> bool:
        """
        Acquire semaphore permits.
        
        Args:
            semaphore_id: Semaphore identifier  
            permits: Number of permits to acquire
            timeout: Optional timeout in seconds
            
        Returns:
            Whether permits were acquired
        """
        start_time = datetime.now()
        
        while self.semaphores[semaphore_id] < permits:
            if timeout and (datetime.now() - start_time).seconds > timeout:
                logger.warning(f"Semaphore {semaphore_id} acquisition timeout")
                return False
            await asyncio.sleep(0.1)
        
        self.semaphores[semaphore_id] -= permits
        logger.info(f"Semaphore {semaphore_id} acquired {permits} permits")
        return True
    
    async def release_semaphore(self, semaphore_id: str, permits: int = 1) -> bool:
        """
        Release semaphore permits.
        
        Args:
            semaphore_id: Semaphore identifier
            permits: Number of permits to release
            
        Returns:
            Whether permits were released
        """
        self.semaphores[semaphore_id] += permits
        logger.info(f"Semaphore {semaphore_id} released {permits} permits")
        return True
    
    async def set_event(self, event_id: str) -> bool:
        """
        Set an event flag.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Whether event was set
        """
        self.events[event_id] = True
        logger.info(f"Event {event_id} set")
        return True
    
    async def wait_for_event(self, event_id: str, timeout: Optional[int] = None) -> bool:
        """
        Wait for an event to be set.
        
        Args:
            event_id: Event identifier
            timeout: Optional timeout in seconds
            
        Returns:
            Whether event was set
        """
        start_time = datetime.now()
        
        while not self.events[event_id]:
            if timeout and (datetime.now() - start_time).seconds > timeout:
                logger.warning(f"Event {event_id} wait timeout")
                return False
            await asyncio.sleep(0.1)
        
        logger.info(f"Event {event_id} triggered")
        return True
    
    async def clear_event(self, event_id: str) -> bool:
        """
        Clear an event flag.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Whether event was cleared
        """
        self.events[event_id] = False
        logger.info(f"Event {event_id} cleared")
        return True
    
    # Message Handling
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """
        Register a message handler.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type].append(handler)
        logger.info(f"Registered handler for {message_type.value}")
    
    async def process_incoming_message(self, message_data: Dict[str, Any]):
        """
        Process an incoming team message.
        
        Args:
            message_data: Message data dictionary
        """
        try:
            message_type = MessageType(message_data.get('message_type'))
            team_message = TeamMessage(
                message_id=message_data.get('message_id'),
                message_type=message_type,
                sender_id=message_data.get('sender_id'),
                team_id=message_data.get('team_id'),
                content=message_data.get('content'),
                metadata=message_data.get('metadata', {}),
                timestamp=datetime.fromisoformat(message_data.get('timestamp'))
            )
            
            self.message_history.append(team_message)
            
            # Call registered handlers
            for handler in self.message_handlers[message_type]:
                await handler(team_message)
            
            logger.debug(f"Processed {message_type.value} message from {team_message.sender_id}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    # Performance Metrics
    
    def get_communication_metrics(self) -> Dict[str, Any]:
        """
        Get team communication performance metrics.
        
        Returns:
            Communication metrics
        """
        metrics = {
            'total_messages': len(self.message_history),
            'active_votes': len(self.active_votes),
            'team_size': len(self.team_members) + 1,
            'message_types': defaultdict(int)
        }
        
        # Count message types
        for msg in self.message_history:
            metrics['message_types'][msg.message_type.value] += 1
        
        # Calculate average latency
        if self.message_latencies:
            metrics['avg_latency_ms'] = sum(self.message_latencies) / len(self.message_latencies)
            metrics['max_latency_ms'] = max(self.message_latencies)
            metrics['min_latency_ms'] = min(self.message_latencies)
        
        # Response times
        if self.response_times:
            metrics['avg_response_time_s'] = sum(self.response_times.values()) / len(self.response_times)
        
        return metrics
    
    def clear_history(self, older_than: Optional[timedelta] = None):
        """
        Clear message history.
        
        Args:
            older_than: Only clear messages older than this duration
        """
        if older_than:
            cutoff = datetime.now() - older_than
            self.message_history = [
                msg for msg in self.message_history
                if msg.timestamp > cutoff
            ]
        else:
            self.message_history.clear()
        
        logger.info(f"Cleared message history, {len(self.message_history)} messages remaining")


# Convenience functions for standalone usage

async def create_team_protocol(team_id: str, agent_id: Optional[str] = None,
                              team_members: Optional[Dict[str, str]] = None) -> TeamProtocol:
    """
    Create and initialize a team protocol instance.
    
    Args:
        team_id: Team identifier
        agent_id: Current agent identifier
        team_members: Dictionary of agent_id -> agent_url
        
    Returns:
        Initialized TeamProtocol instance
    """
    protocol = TeamProtocol(team_id, agent_id)
    
    if team_members:
        for member_id, member_url in team_members.items():
            await protocol.add_team_member(member_id, member_url)
    
    return protocol


async def broadcast_message(team_id: str, message: str, 
                           team_members: Dict[str, str]) -> Dict[str, Any]:
    """
    Broadcast a message to a team (convenience function).
    
    Args:
        team_id: Team identifier
        message: Message to broadcast
        team_members: Dictionary of agent_id -> agent_url
        
    Returns:
        Broadcast results
    """
    protocol = await create_team_protocol(team_id, team_members=team_members)
    return await protocol.broadcast_to_team(message)


async def conduct_team_vote(team_id: str, proposal: str,
                           team_members: Dict[str, str],
                           threshold: float = 0.5) -> Dict[str, Any]:
    """
    Conduct a team vote (convenience function).
    
    Args:
        team_id: Team identifier
        proposal: Proposal to vote on
        team_members: Dictionary of agent_id -> agent_url
        threshold: Voting threshold
        
    Returns:
        Vote results
    """
    protocol = await create_team_protocol(team_id, team_members=team_members)
    vote_id = await protocol.request_team_vote(proposal, threshold=threshold)
    
    # Wait for voting deadline
    await asyncio.sleep(5 * 60)  # Default 5 minutes
    
    return await protocol.tally_votes(vote_id)