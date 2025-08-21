"""
Inter-Team Collaboration Protocol

This module implements collaboration mechanisms between different agent teams,
enabling resource sharing, knowledge transfer, and coordinated task execution.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from uuid import uuid4
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollaborationType(Enum):
    """Types of collaboration between teams."""
    RESOURCE_SHARING = "resource_sharing"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"
    JOINT_TASK = "joint_task"
    CONSULTATION = "consultation"
    DELEGATION = "delegation"
    PEER_REVIEW = "peer_review"
    EMERGENCY_SUPPORT = "emergency_support"


class CollaborationStatus(Enum):
    """Status of a collaboration request."""
    PENDING = "pending"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Priority(Enum):
    """Priority levels for collaboration requests."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    BACKGROUND = 1


@dataclass
class CollaborationRequest:
    """Represents a collaboration request between teams."""
    id: str = field(default_factory=lambda: str(uuid4()))
    requesting_team: str = ""
    target_teams: List[str] = field(default_factory=list)
    type: CollaborationType = CollaborationType.JOINT_TASK
    priority: Priority = Priority.MEDIUM
    task_description: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    status: CollaborationStatus = CollaborationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['type'] = self.type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        if self.deadline:
            data['deadline'] = self.deadline.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


@dataclass
class CollaborationResponse:
    """Response to a collaboration request."""
    id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    responding_team: str = ""
    decision: str = ""  # accept, reject, negotiate
    conditions: Dict[str, Any] = field(default_factory=dict)
    available_resources: Dict[str, Any] = field(default_factory=dict)
    estimated_completion: Optional[datetime] = None
    counter_proposal: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if self.estimated_completion:
            data['estimated_completion'] = self.estimated_completion.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class CollaborationAgreement:
    """Finalized agreement between teams for collaboration."""
    id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    participating_teams: List[str] = field(default_factory=list)
    type: CollaborationType = CollaborationType.JOINT_TASK
    terms: Dict[str, Any] = field(default_factory=dict)
    resource_allocation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timeline: Dict[str, datetime] = field(default_factory=dict)
    deliverables: List[Dict[str, Any]] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    status: CollaborationStatus = CollaborationStatus.ACCEPTED
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['type'] = self.type.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        # Convert timeline datetimes
        data['timeline'] = {k: v.isoformat() for k, v in self.timeline.items()}
        return data


class InterTeamProtocol:
    """
    Manages collaboration protocols between different agent teams.
    """
    
    def __init__(self):
        """Initialize the inter-team protocol manager."""
        self.requests: Dict[str, CollaborationRequest] = {}
        self.responses: Dict[str, List[CollaborationResponse]] = {}
        self.agreements: Dict[str, CollaborationAgreement] = {}
        self.team_capabilities: Dict[str, Dict[str, Any]] = {}
        self.team_availability: Dict[str, Dict[str, Any]] = {}
        self.collaboration_history: List[Dict[str, Any]] = []
        self.negotiation_rules: Dict[str, Any] = self._default_negotiation_rules()
        self.conflict_resolution_strategies: List[Callable] = []
        self.metrics: Dict[str, Any] = {
            'total_requests': 0,
            'successful_collaborations': 0,
            'failed_collaborations': 0,
            'average_negotiation_time': 0,
            'resource_utilization': {},
            'knowledge_transfers': 0,
            'by_type': {t.value: 0 for t in CollaborationType},
            'by_priority': {p.name: 0 for p in Priority}
        }
        self._lock = asyncio.Lock()
        
    def _default_negotiation_rules(self) -> Dict[str, Any]:
        """Define default negotiation rules."""
        return {
            'max_negotiation_rounds': 3,
            'timeout_minutes': 30,
            'priority_weight': {
                Priority.CRITICAL: 1.0,
                Priority.HIGH: 0.8,
                Priority.MEDIUM: 0.5,
                Priority.LOW: 0.3,
                Priority.BACKGROUND: 0.1
            },
            'auto_accept_threshold': 0.8,
            'auto_reject_threshold': 0.2,
            'resource_buffer': 0.2  # Keep 20% resources as buffer
        }
    
    async def register_team(self, team_id: str, capabilities: Dict[str, Any],
                           availability: Dict[str, Any]) -> None:
        """
        Register a team with its capabilities and availability.
        
        Args:
            team_id: Team identifier
            capabilities: Team's capabilities and skills
            availability: Team's resource availability
        """
        async with self._lock:
            self.team_capabilities[team_id] = capabilities
            self.team_availability[team_id] = availability
            logger.info(f"Registered team {team_id} with capabilities: {list(capabilities.keys())}")
    
    async def request_collaboration(self, request: CollaborationRequest) -> str:
        """
        Submit a collaboration request to other teams.
        
        Args:
            request: Collaboration request details
            
        Returns:
            Request ID for tracking
        """
        async with self._lock:
            # Update metrics
            self.metrics['total_requests'] += 1
            self.metrics['by_type'][request.type.value] += 1
            self.metrics['by_priority'][request.priority.name] += 1
            
            # Store request
            self.requests[request.id] = request
            self.responses[request.id] = []
            
            # Find suitable teams based on requirements
            if not request.target_teams:
                request.target_teams = await self._find_suitable_teams(request)
            
            # Notify target teams (in real implementation, this would be async messaging)
            for team_id in request.target_teams:
                await self._notify_team(team_id, request)
            
            logger.info(f"Collaboration request {request.id} submitted to teams: {request.target_teams}")
            return request.id
    
    async def _find_suitable_teams(self, request: CollaborationRequest) -> List[str]:
        """Find teams suitable for the collaboration request."""
        suitable_teams = []
        
        for team_id, capabilities in self.team_capabilities.items():
            if team_id == request.requesting_team:
                continue
                
            # Check if team has required capabilities
            if request.requirements:
                required_skills = request.requirements.get('skills', [])
                team_skills = capabilities.get('skills', [])
                
                if all(skill in team_skills for skill in required_skills):
                    # Check availability
                    availability = self.team_availability.get(team_id, {})
                    if availability.get('accepting_requests', True):
                        suitable_teams.append(team_id)
        
        return suitable_teams
    
    async def _notify_team(self, team_id: str, request: CollaborationRequest) -> None:
        """Notify a team about a collaboration request."""
        # In real implementation, this would send an actual notification
        logger.debug(f"Notifying team {team_id} about request {request.id}")
    
    async def respond_to_request(self, response: CollaborationResponse) -> None:
        """
        Process a team's response to a collaboration request.
        
        Args:
            response: Team's response to the request
        """
        async with self._lock:
            if response.request_id not in self.requests:
                raise ValueError(f"Unknown request ID: {response.request_id}")
            
            self.responses[response.request_id].append(response)
            request = self.requests[response.request_id]
            
            # Check if all teams have responded
            if len(self.responses[response.request_id]) == len(request.target_teams):
                await self._process_responses(request)
    
    async def _process_responses(self, request: CollaborationRequest) -> None:
        """Process all responses and negotiate agreement."""
        responses = self.responses[request.id]
        accepting_teams = []
        negotiating_teams = []
        
        for response in responses:
            if response.decision == "accept":
                accepting_teams.append(response.responding_team)
            elif response.decision == "negotiate":
                negotiating_teams.append(response)
        
        if accepting_teams:
            # Create agreement with accepting teams
            agreement = await self._create_agreement(request, accepting_teams, responses)
            self.agreements[agreement.id] = agreement
            request.status = CollaborationStatus.ACCEPTED
            logger.info(f"Collaboration agreement {agreement.id} created for request {request.id}")
        elif negotiating_teams:
            # Enter negotiation phase
            request.status = CollaborationStatus.NEGOTIATING
            await self._negotiate(request, negotiating_teams)
        else:
            # All teams rejected
            request.status = CollaborationStatus.REJECTED
            self.metrics['failed_collaborations'] += 1
            logger.warning(f"Collaboration request {request.id} rejected by all teams")
    
    async def _create_agreement(self, request: CollaborationRequest,
                               teams: List[str],
                               responses: List[CollaborationResponse]) -> CollaborationAgreement:
        """Create a collaboration agreement."""
        # Aggregate resources and conditions from responses
        resource_allocation = {}
        terms = {}
        
        for response in responses:
            if response.responding_team in teams:
                resource_allocation[response.responding_team] = response.available_resources
                if response.conditions:
                    terms[response.responding_team] = response.conditions
        
        agreement = CollaborationAgreement(
            request_id=request.id,
            participating_teams=teams + [request.requesting_team],
            type=request.type,
            terms=terms,
            resource_allocation=resource_allocation,
            timeline={
                'start': datetime.now(),
                'end': request.deadline or datetime.now() + timedelta(days=7)
            },
            deliverables=request.requirements.get('deliverables', []),
            success_criteria=request.requirements.get('success_criteria', [])
        )
        
        return agreement
    
    async def _negotiate(self, request: CollaborationRequest,
                        negotiating_teams: List[CollaborationResponse]) -> None:
        """Handle negotiation between teams."""
        negotiation_rounds = 0
        max_rounds = self.negotiation_rules['max_negotiation_rounds']
        
        # Check if this is the first negotiation round
        if negotiation_rounds == 0 and not any(t.counter_proposal for t in negotiating_teams):
            # Just entered negotiation, no counter proposals yet
            return
        
        while negotiation_rounds < max_rounds:
            # Aggregate counter proposals
            counter_proposals = [t.counter_proposal for t in negotiating_teams if t.counter_proposal]
            
            if counter_proposals:
                # Find common ground
                agreed_terms = await self._find_common_ground(request, counter_proposals)
                
                if agreed_terms:
                    # Create modified agreement
                    teams = [t.responding_team for t in negotiating_teams]
                    agreement = CollaborationAgreement(
                        request_id=request.id,
                        participating_teams=teams + [request.requesting_team],
                        type=request.type,
                        terms=agreed_terms,
                        timeline={
                            'start': datetime.now(),
                            'end': request.deadline or datetime.now() + timedelta(days=7)
                        }
                    )
                    self.agreements[agreement.id] = agreement
                    request.status = CollaborationStatus.ACCEPTED
                    logger.info(f"Negotiated agreement {agreement.id} for request {request.id}")
                    return
            
            negotiation_rounds += 1
        
        # Negotiation failed
        request.status = CollaborationStatus.FAILED
        self.metrics['failed_collaborations'] += 1
        logger.warning(f"Negotiation failed for request {request.id}")
    
    async def _find_common_ground(self, request: CollaborationRequest,
                                 counter_proposals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find common ground between counter proposals."""
        # Simple implementation: find intersection of acceptable terms
        if not counter_proposals:
            return None
        
        common_terms = counter_proposals[0].copy()
        
        for proposal in counter_proposals[1:]:
            for key in list(common_terms.keys()):
                if key in proposal:
                    # Keep only if values are compatible
                    if common_terms[key] != proposal[key]:
                        # Try to find middle ground for numeric values
                        if isinstance(common_terms[key], (int, float)) and \
                           isinstance(proposal[key], (int, float)):
                            common_terms[key] = (common_terms[key] + proposal[key]) / 2
                        else:
                            del common_terms[key]
                else:
                    del common_terms[key]
        
        return common_terms if common_terms else None
    
    async def execute_collaboration(self, agreement_id: str) -> Dict[str, Any]:
        """
        Execute a collaboration agreement.
        
        Args:
            agreement_id: Agreement identifier
            
        Returns:
            Execution results
        """
        async with self._lock:
            if agreement_id not in self.agreements:
                raise ValueError(f"Unknown agreement ID: {agreement_id}")
            
            agreement = self.agreements[agreement_id]
            agreement.status = CollaborationStatus.IN_PROGRESS
            
            # Simulate collaboration execution
            results = {
                'agreement_id': agreement_id,
                'participating_teams': agreement.participating_teams,
                'start_time': datetime.now(),
                'tasks_completed': [],
                'resources_used': {},
                'knowledge_shared': []
            }
            
            try:
                # Execute based on collaboration type
                if agreement.type == CollaborationType.RESOURCE_SHARING:
                    results['resources_shared'] = await self._execute_resource_sharing(agreement)
                elif agreement.type == CollaborationType.KNOWLEDGE_TRANSFER:
                    results['knowledge_transferred'] = await self._execute_knowledge_transfer(agreement)
                elif agreement.type == CollaborationType.JOINT_TASK:
                    results['task_results'] = await self._execute_joint_task(agreement)
                elif agreement.type == CollaborationType.CONSULTATION:
                    results['consultation_results'] = await self._execute_consultation(agreement)
                elif agreement.type == CollaborationType.DELEGATION:
                    results['delegation_results'] = await self._execute_delegation(agreement)
                elif agreement.type == CollaborationType.PEER_REVIEW:
                    results['review_results'] = await self._execute_peer_review(agreement)
                elif agreement.type == CollaborationType.EMERGENCY_SUPPORT:
                    results['support_results'] = await self._execute_emergency_support(agreement)
                
                # Mark as completed
                agreement.status = CollaborationStatus.COMPLETED
                agreement.completed_at = datetime.now()
                results['end_time'] = agreement.completed_at
                results['status'] = 'success'
                
                # Update metrics
                self.metrics['successful_collaborations'] += 1
                
                # Add to history
                self.collaboration_history.append({
                    'agreement_id': agreement_id,
                    'type': agreement.type.value,
                    'teams': agreement.participating_teams,
                    'completed_at': agreement.completed_at.isoformat(),
                    'success': True
                })
                
                logger.info(f"Collaboration {agreement_id} completed successfully")
                
            except Exception as e:
                agreement.status = CollaborationStatus.FAILED
                results['status'] = 'failed'
                results['error'] = str(e)
                self.metrics['failed_collaborations'] += 1
                logger.error(f"Collaboration {agreement_id} failed: {e}")
            
            return results
    
    async def _execute_resource_sharing(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute resource sharing collaboration."""
        shared_resources = {}
        for team, resources in agreement.resource_allocation.items():
            shared_resources[team] = {
                'cpu': resources.get('cpu', 0),
                'memory': resources.get('memory', 0),
                'agents': resources.get('agents', [])
            }
        return shared_resources
    
    async def _execute_knowledge_transfer(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute knowledge transfer collaboration."""
        self.metrics['knowledge_transfers'] += 1
        return {
            'documents_shared': agreement.terms.get('documents', []),
            'learnings_shared': agreement.terms.get('learnings', []),
            'best_practices': agreement.terms.get('best_practices', [])
        }
    
    async def _execute_joint_task(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute joint task collaboration."""
        return {
            'task_id': str(uuid4()),
            'subtasks_assigned': {team: [] for team in agreement.participating_teams},
            'coordination_points': agreement.terms.get('coordination_points', []),
            'deliverables': agreement.deliverables
        }
    
    async def _execute_consultation(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute consultation collaboration."""
        return {
            'consultation_id': str(uuid4()),
            'expert_team': agreement.participating_teams[1],
            'recommendations': [],
            'analysis': {}
        }
    
    async def _execute_delegation(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute delegation collaboration."""
        return {
            'delegation_id': str(uuid4()),
            'delegated_to': agreement.participating_teams[1],
            'task_accepted': True,
            'estimated_completion': agreement.timeline.get('end')
        }
    
    async def _execute_peer_review(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute peer review collaboration."""
        return {
            'review_id': str(uuid4()),
            'reviewer_teams': agreement.participating_teams[1:],
            'review_criteria': agreement.success_criteria,
            'feedback': []
        }
    
    async def _execute_emergency_support(self, agreement: CollaborationAgreement) -> Dict[str, Any]:
        """Execute emergency support collaboration."""
        return {
            'support_id': str(uuid4()),
            'supporting_teams': agreement.participating_teams[1:],
            'resources_provided': agreement.resource_allocation,
            'response_time': (datetime.now() - agreement.created_at).total_seconds()
        }
    
    async def resolve_conflict(self, team1: str, team2: str, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve conflicts between teams.
        
        Args:
            team1: First team in conflict
            team2: Second team in conflict
            conflict: Conflict details
            
        Returns:
            Resolution details
        """
        resolution = {
            'conflict_id': str(uuid4()),
            'teams': [team1, team2],
            'conflict_type': conflict.get('type', 'resource'),
            'resolution_strategy': None,
            'outcome': None,
            'timestamp': datetime.now()
        }
        
        # Try different resolution strategies
        for strategy in self.conflict_resolution_strategies:
            try:
                outcome = await strategy(team1, team2, conflict)
                if outcome:
                    resolution['resolution_strategy'] = strategy.__name__
                    resolution['outcome'] = outcome
                    logger.info(f"Conflict resolved between {team1} and {team2} using {strategy.__name__}")
                    break
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
        
        if not resolution['outcome']:
            # Default resolution: priority-based
            resolution['resolution_strategy'] = 'priority_based'
            resolution['outcome'] = await self._priority_based_resolution(team1, team2, conflict)
        
        return resolution
    
    async def _priority_based_resolution(self, team1: str, team2: str, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict based on priority."""
        # Simple priority-based resolution
        team1_priority = conflict.get('team1_priority', Priority.MEDIUM)
        team2_priority = conflict.get('team2_priority', Priority.MEDIUM)
        
        if team1_priority.value > team2_priority.value:
            winner = team1
        elif team2_priority.value > team1_priority.value:
            winner = team2
        else:
            # Equal priority, use timestamp
            winner = team1 if conflict.get('team1_timestamp', 0) < conflict.get('team2_timestamp', 0) else team2
        
        return {
            'winner': winner,
            'allocation': conflict.get('resource'),
            'reason': 'priority_based'
        }
    
    def get_collaboration_metrics(self) -> Dict[str, Any]:
        """Get collaboration metrics and statistics."""
        if self.metrics['total_requests'] > 0:
            success_rate = self.metrics['successful_collaborations'] / self.metrics['total_requests']
        else:
            success_rate = 0
        
        return {
            **self.metrics,
            'success_rate': success_rate,
            'active_agreements': len([a for a in self.agreements.values() 
                                     if a.status == CollaborationStatus.IN_PROGRESS]),
            'pending_requests': len([r for r in self.requests.values() 
                                   if r.status == CollaborationStatus.PENDING]),
            'total_teams': len(self.team_capabilities)
        }
    
    def get_team_collaboration_history(self, team_id: str) -> List[Dict[str, Any]]:
        """Get collaboration history for a specific team."""
        team_history = []
        
        for record in self.collaboration_history:
            if team_id in record.get('teams', []):
                team_history.append(record)
        
        return team_history
    
    async def optimize_collaboration_patterns(self) -> Dict[str, Any]:
        """Analyze and optimize collaboration patterns."""
        patterns = {
            'frequent_collaborators': {},
            'successful_patterns': [],
            'bottlenecks': [],
            'recommendations': []
        }
        
        # Analyze collaboration history
        team_pairs = {}
        for record in self.collaboration_history:
            teams = tuple(sorted(record['teams'][:2]))  # Consider pairs
            if teams not in team_pairs:
                team_pairs[teams] = {'count': 0, 'success': 0}
            team_pairs[teams]['count'] += 1
            if record.get('success'):
                team_pairs[teams]['success'] += 1
        
        # Find frequent collaborators
        patterns['frequent_collaborators'] = {
            str(teams): data for teams, data in team_pairs.items()
            if data['count'] > 3
        }
        
        # Identify successful patterns
        for teams, data in team_pairs.items():
            if data['count'] > 0:
                success_rate = data['success'] / data['count']
                if success_rate > 0.8:
                    patterns['successful_patterns'].append({
                        'teams': teams,
                        'success_rate': success_rate,
                        'collaborations': data['count']
                    })
        
        # Generate recommendations
        if patterns['successful_patterns']:
            patterns['recommendations'].append(
                "Encourage collaboration between teams with high success rates"
            )
        
        if self.metrics['failed_collaborations'] > self.metrics['successful_collaborations'] * 0.2:
            patterns['recommendations'].append(
                "Review and update negotiation rules to reduce failed collaborations"
            )
        
        return patterns