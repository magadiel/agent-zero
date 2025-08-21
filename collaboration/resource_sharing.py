"""
Resource Sharing System

This module implements resource sharing mechanisms between agent teams,
enabling dynamic allocation, borrowing/lending, and optimization of resources.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import uuid4
import heapq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be shared."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    AGENTS = "agents"
    KNOWLEDGE = "knowledge"
    TOOLS = "tools"
    TIME = "time"


class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    PRIORITY_BASED = "priority_based"
    FAIR_SHARE = "fair_share"
    WEIGHTED = "weighted"
    DEMAND_BASED = "demand_based"
    AUCTION = "auction"
    COOPERATIVE = "cooperative"


class SharingMode(Enum):
    """Modes of resource sharing."""
    EXCLUSIVE = "exclusive"  # Resource used by one team only
    SHARED = "shared"  # Resource can be used by multiple teams
    TIME_SLICED = "time_sliced"  # Resource alternates between teams
    POOLED = "pooled"  # Resources combined into common pool


@dataclass
class Resource:
    """Represents a shareable resource."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: ResourceType = ResourceType.CPU
    capacity: float = 0.0
    available: float = 0.0
    owner_team: str = ""
    sharing_mode: SharingMode = SharingMode.EXCLUSIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['type'] = self.type.value
        data['sharing_mode'] = self.sharing_mode.value
        return data


@dataclass
class ResourceRequest:
    """Request for resources from a team."""
    id: str = field(default_factory=lambda: str(uuid4()))
    requesting_team: str = ""
    resource_type: ResourceType = ResourceType.CPU
    amount: float = 0.0
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    priority: int = 1  # 1-10, higher is more important
    purpose: str = ""
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        """For priority queue comparison."""
        return self.priority > other.priority  # Higher priority first


@dataclass
class ResourceAllocation:
    """Represents an allocation of resources to a team."""
    id: str = field(default_factory=lambda: str(uuid4()))
    resource_id: str = ""
    allocated_to: str = ""
    amount: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    actual_usage: float = 0.0
    status: str = "active"  # active, completed, cancelled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


@dataclass
class ResourcePool:
    """Pool of shared resources."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    resources: Dict[str, Resource] = field(default_factory=dict)
    participating_teams: List[str] = field(default_factory=list)
    allocation_strategy: AllocationStrategy = AllocationStrategy.FAIR_SHARE
    total_capacity: Dict[ResourceType, float] = field(default_factory=dict)
    available_capacity: Dict[ResourceType, float] = field(default_factory=dict)


class ResourceSharingManager:
    """
    Manages resource sharing between agent teams.
    """
    
    def __init__(self):
        """Initialize the resource sharing manager."""
        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.pools: Dict[str, ResourcePool] = {}
        self.team_resources: Dict[str, List[str]] = {}  # team_id -> resource_ids
        self.pending_requests: List[ResourceRequest] = []
        self.request_queue = asyncio.PriorityQueue()
        self.allocation_history: List[ResourceAllocation] = []
        self.sharing_agreements: Dict[str, Dict[str, Any]] = {}
        self.resource_metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._allocation_task = None
        
    async def start(self):
        """Start the resource allocation background task."""
        if not self._allocation_task:
            self._allocation_task = asyncio.create_task(self._allocation_loop())
            logger.info("Resource sharing manager started")
    
    async def stop(self):
        """Stop the resource allocation background task."""
        if self._allocation_task:
            self._allocation_task.cancel()
            try:
                await self._allocation_task
            except asyncio.CancelledError:
                pass
            self._allocation_task = None
            logger.info("Resource sharing manager stopped")
    
    async def _allocation_loop(self):
        """Background task for processing resource allocation requests."""
        while True:
            try:
                # Process pending requests every second
                await asyncio.sleep(1)
                await self._process_pending_requests()
                await self._cleanup_expired_allocations()
                await self._optimize_allocations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in allocation loop: {e}")
    
    async def register_resource(self, resource: Resource, team_id: str) -> str:
        """
        Register a resource owned by a team.
        
        Args:
            resource: Resource to register
            team_id: Team that owns the resource
            
        Returns:
            Resource ID
        """
        async with self._lock:
            resource.owner_team = team_id
            self.resources[resource.id] = resource
            
            if team_id not in self.team_resources:
                self.team_resources[team_id] = []
            self.team_resources[team_id].append(resource.id)
            
            # Initialize metrics for this resource
            self.resource_metrics[resource.id] = {
                'total_allocations': 0,
                'total_usage': 0.0,
                'utilization_rate': 0.0,
                'sharing_count': 0,
                'last_updated': datetime.now()
            }
            
            logger.info(f"Registered resource {resource.id} ({resource.type.value}) for team {team_id}")
            return resource.id
    
    async def create_resource_pool(self, name: str, teams: List[str],
                                  strategy: AllocationStrategy = AllocationStrategy.FAIR_SHARE) -> str:
        """
        Create a resource pool for sharing between teams.
        
        Args:
            name: Pool name
            teams: Participating teams
            strategy: Allocation strategy
            
        Returns:
            Pool ID
        """
        async with self._lock:
            pool = ResourcePool(
                name=name,
                participating_teams=teams,
                allocation_strategy=strategy
            )
            
            # Add team resources to pool
            for team_id in teams:
                if team_id in self.team_resources:
                    for resource_id in self.team_resources[team_id]:
                        resource = self.resources[resource_id]
                        pool.resources[resource_id] = resource
                        
                        # Update pool capacity
                        if resource.type not in pool.total_capacity:
                            pool.total_capacity[resource.type] = 0
                            pool.available_capacity[resource.type] = 0
                        pool.total_capacity[resource.type] += resource.capacity
                        pool.available_capacity[resource.type] += resource.available
            
            self.pools[pool.id] = pool
            logger.info(f"Created resource pool '{name}' with {len(teams)} teams")
            return pool.id
    
    async def request_resource(self, request: ResourceRequest) -> Optional[str]:
        """
        Request resources for a team.
        
        Args:
            request: Resource request details
            
        Returns:
            Request ID if queued, None if rejected
        """
        async with self._lock:
            # Validate request
            if request.amount <= 0:
                logger.warning(f"Invalid resource amount requested: {request.amount}")
                return None
            
            # Check if resources are available
            available = await self._check_availability(request)
            
            if available:
                # Try immediate allocation
                allocation = await self._allocate_resource(request)
                if allocation:
                    return allocation.id
            
            # Queue the request
            await self.request_queue.put((request.priority, request))
            self.pending_requests.append(request)
            logger.info(f"Queued resource request {request.id} from {request.requesting_team}")
            return request.id
    
    async def _check_availability(self, request: ResourceRequest) -> bool:
        """Check if requested resources are available."""
        total_available = 0.0
        
        for resource in self.resources.values():
            if resource.type == request.resource_type:
                total_available += resource.available
        
        return total_available >= request.amount
    
    async def _allocate_resource(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Allocate resources to fulfill a request."""
        # Find suitable resources
        suitable_resources = []
        
        for resource_id, resource in self.resources.items():
            if resource.type == request.resource_type and resource.available > 0:
                suitable_resources.append((resource.available, resource_id, resource))
        
        if not suitable_resources:
            return None
        
        # Sort by available capacity (descending)
        suitable_resources.sort(reverse=True)
        
        # Allocate from available resources
        remaining = request.amount
        allocations = []
        
        for available, resource_id, resource in suitable_resources:
            if remaining <= 0:
                break
                
            allocation_amount = min(available, remaining)
            
            # Create allocation
            allocation = ResourceAllocation(
                resource_id=resource_id,
                allocated_to=request.requesting_team,
                amount=allocation_amount,
                start_time=datetime.now(),
                end_time=datetime.now() + request.duration if request.duration else None
            )
            
            # Update resource availability
            resource.available -= allocation_amount
            remaining -= allocation_amount
            
            allocations.append(allocation)
            self.allocations[allocation.id] = allocation
            
            # Update metrics
            self.resource_metrics[resource_id]['total_allocations'] += 1
            self.resource_metrics[resource_id]['sharing_count'] += 1
            
            logger.debug(f"Allocated {allocation_amount} of {resource.type.value} to {request.requesting_team}")
        
        if remaining > 0:
            # Couldn't fulfill entire request, rollback
            for allocation in allocations:
                resource = self.resources[allocation.resource_id]
                resource.available += allocation.amount
                del self.allocations[allocation.id]
            return None
        
        # Return primary allocation
        return allocations[0] if allocations else None
    
    async def release_resource(self, allocation_id: str, actual_usage: Optional[float] = None) -> bool:
        """
        Release allocated resources.
        
        Args:
            allocation_id: Allocation to release
            actual_usage: Actual amount used (for metrics)
            
        Returns:
            Success status
        """
        async with self._lock:
            if allocation_id not in self.allocations:
                logger.warning(f"Unknown allocation ID: {allocation_id}")
                return False
            
            allocation = self.allocations[allocation_id]
            resource = self.resources.get(allocation.resource_id)
            
            if not resource:
                logger.error(f"Resource {allocation.resource_id} not found")
                return False
            
            # Update resource availability
            resource.available += allocation.amount
            
            # Update allocation
            allocation.status = "completed"
            allocation.end_time = datetime.now()
            if actual_usage is not None:
                allocation.actual_usage = actual_usage
            
            # Update metrics
            self.resource_metrics[resource.id]['total_usage'] += allocation.actual_usage or allocation.amount
            
            # Move to history
            self.allocation_history.append(allocation)
            del self.allocations[allocation_id]
            
            logger.info(f"Released {allocation.amount} of resource {resource.id}")
            return True
    
    async def borrow_resource(self, borrower_team: str, lender_team: str,
                            resource_type: ResourceType, amount: float,
                            duration: timedelta) -> Optional[str]:
        """
        Borrow resources from another team.
        
        Args:
            borrower_team: Team borrowing resources
            lender_team: Team lending resources
            resource_type: Type of resource to borrow
            amount: Amount to borrow
            duration: Borrowing duration
            
        Returns:
            Borrowing agreement ID if successful
        """
        async with self._lock:
            # Find lender's resources
            lender_resources = []
            if lender_team in self.team_resources:
                for resource_id in self.team_resources[lender_team]:
                    resource = self.resources[resource_id]
                    if resource.type == resource_type and resource.available >= amount:
                        lender_resources.append(resource)
            
            if not lender_resources:
                logger.warning(f"Team {lender_team} has insufficient {resource_type.value} to lend")
                return None
            
            # Create borrowing agreement
            agreement_id = str(uuid4())
            resource = lender_resources[0]
            
            # Create allocation
            allocation = ResourceAllocation(
                resource_id=resource.id,
                allocated_to=borrower_team,
                amount=amount,
                start_time=datetime.now(),
                end_time=datetime.now() + duration
            )
            
            # Update resource
            resource.available -= amount
            self.allocations[allocation.id] = allocation
            
            # Store agreement
            self.sharing_agreements[agreement_id] = {
                'id': agreement_id,
                'borrower': borrower_team,
                'lender': lender_team,
                'resource_type': resource_type.value,
                'amount': amount,
                'allocation_id': allocation.id,
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + duration).isoformat(),
                'status': 'active'
            }
            
            logger.info(f"Team {borrower_team} borrowed {amount} {resource_type.value} from {lender_team}")
            return agreement_id
    
    async def return_borrowed_resource(self, agreement_id: str) -> bool:
        """
        Return borrowed resources.
        
        Args:
            agreement_id: Borrowing agreement ID
            
        Returns:
            Success status
        """
        async with self._lock:
            if agreement_id not in self.sharing_agreements:
                logger.warning(f"Unknown agreement ID: {agreement_id}")
                return False
            
            agreement = self.sharing_agreements[agreement_id]
            allocation_id = agreement['allocation_id']
            
            # Release the allocation
            success = await self.release_resource(allocation_id)
            
            if success:
                agreement['status'] = 'completed'
                agreement['returned_at'] = datetime.now().isoformat()
                logger.info(f"Borrowed resources returned for agreement {agreement_id}")
            
            return success
    
    async def _process_pending_requests(self):
        """Process pending resource requests."""
        if self.request_queue.empty():
            return
        
        processed = []
        
        while not self.request_queue.empty():
            try:
                priority, request = await self.request_queue.get_nowait()
                
                # Try to allocate
                allocation = await self._allocate_resource(request)
                
                if allocation:
                    processed.append(request)
                    logger.debug(f"Processed request {request.id}")
                else:
                    # Re-queue if not expired
                    if request.deadline and datetime.now() < request.deadline:
                        await self.request_queue.put((priority, request))
                    else:
                        logger.warning(f"Request {request.id} expired")
                        
            except asyncio.QueueEmpty:
                break
        
        # Remove processed requests from pending list
        for request in processed:
            if request in self.pending_requests:
                self.pending_requests.remove(request)
    
    async def _cleanup_expired_allocations(self):
        """Clean up expired allocations."""
        expired = []
        
        for allocation_id, allocation in self.allocations.items():
            if allocation.end_time and datetime.now() > allocation.end_time:
                expired.append(allocation_id)
        
        for allocation_id in expired:
            await self.release_resource(allocation_id)
            logger.debug(f"Cleaned up expired allocation {allocation_id}")
    
    async def _optimize_allocations(self):
        """Optimize resource allocations for better utilization."""
        # Calculate utilization rates
        for resource_id, resource in self.resources.items():
            metrics = self.resource_metrics[resource_id]
            
            if resource.capacity > 0:
                utilization = (resource.capacity - resource.available) / resource.capacity
                metrics['utilization_rate'] = utilization
                metrics['last_updated'] = datetime.now()
        
        # Find underutilized resources
        underutilized = []
        for resource_id, metrics in self.resource_metrics.items():
            if metrics['utilization_rate'] < 0.3:  # Less than 30% utilized
                underutilized.append(resource_id)
        
        # TODO: Implement rebalancing logic
        if underutilized:
            logger.debug(f"Found {len(underutilized)} underutilized resources")
    
    async def negotiate_sharing(self, team1: str, team2: str,
                              resource_type: ResourceType,
                              proposed_split: Tuple[float, float]) -> Dict[str, Any]:
        """
        Negotiate resource sharing between teams.
        
        Args:
            team1: First team
            team2: Second team
            resource_type: Type of resource to share
            proposed_split: Proposed split (team1_share, team2_share)
            
        Returns:
            Negotiation result
        """
        result = {
            'teams': [team1, team2],
            'resource_type': resource_type.value,
            'proposed_split': proposed_split,
            'agreed_split': None,
            'status': 'negotiating'
        }
        
        # Find total available resources from both teams
        team1_resources = 0.0
        team2_resources = 0.0
        
        for resource_id in self.team_resources.get(team1, []):
            resource = self.resources[resource_id]
            if resource.type == resource_type:
                team1_resources += resource.available
        
        for resource_id in self.team_resources.get(team2, []):
            resource = self.resources[resource_id]
            if resource.type == resource_type:
                team2_resources += resource.available
        
        total_resources = team1_resources + team2_resources
        
        if total_resources == 0:
            result['status'] = 'failed'
            result['reason'] = 'No resources available'
            return result
        
        # Calculate fair share based on current holdings
        fair_share = (
            team1_resources / total_resources,
            team2_resources / total_resources
        )
        
        # Check if proposed split is acceptable
        if abs(proposed_split[0] - fair_share[0]) < 0.1:  # Within 10% of fair share
            result['agreed_split'] = proposed_split
            result['status'] = 'agreed'
        else:
            # Counter with fair share
            result['agreed_split'] = fair_share
            result['status'] = 'counter_proposed'
        
        logger.info(f"Negotiated sharing between {team1} and {team2}: {result['status']}")
        return result
    
    def get_resource_utilization(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get resource utilization statistics.
        
        Args:
            team_id: Optional team ID for team-specific stats
            
        Returns:
            Utilization statistics
        """
        stats = {
            'total_resources': len(self.resources),
            'total_allocations': len(self.allocations),
            'by_type': {},
            'overall_utilization': 0.0
        }
        
        # Calculate utilization by type
        for resource_type in ResourceType:
            type_capacity = 0.0
            type_used = 0.0
            
            for resource in self.resources.values():
                if team_id and resource.owner_team != team_id:
                    continue
                    
                if resource.type == resource_type:
                    type_capacity += resource.capacity
                    type_used += resource.capacity - resource.available
            
            if type_capacity > 0:
                utilization = type_used / type_capacity
                stats['by_type'][resource_type.value] = {
                    'capacity': type_capacity,
                    'used': type_used,
                    'available': type_capacity - type_used,
                    'utilization': utilization
                }
        
        # Calculate overall utilization
        total_capacity = sum(r.capacity for r in self.resources.values())
        total_used = sum(r.capacity - r.available for r in self.resources.values())
        
        if total_capacity > 0:
            stats['overall_utilization'] = total_used / total_capacity
        
        return stats
    
    def get_sharing_metrics(self) -> Dict[str, Any]:
        """Get resource sharing metrics."""
        metrics = {
            'total_pools': len(self.pools),
            'active_agreements': len([a for a in self.sharing_agreements.values() 
                                    if a['status'] == 'active']),
            'pending_requests': len(self.pending_requests),
            'total_allocations': len(self.allocation_history) + len(self.allocations),
            'sharing_efficiency': 0.0,
            'top_borrowers': [],
            'top_lenders': []
        }
        
        # Calculate sharing patterns
        borrower_counts = {}
        lender_counts = {}
        
        for agreement in self.sharing_agreements.values():
            borrower = agreement['borrower']
            lender = agreement['lender']
            
            borrower_counts[borrower] = borrower_counts.get(borrower, 0) + 1
            lender_counts[lender] = lender_counts.get(lender, 0) + 1
        
        # Top borrowers and lenders
        if borrower_counts:
            metrics['top_borrowers'] = sorted(
                borrower_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        if lender_counts:
            metrics['top_lenders'] = sorted(
                lender_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        # Calculate sharing efficiency
        total_shared = len(self.sharing_agreements)
        total_resources = len(self.resources)
        
        if total_resources > 0:
            metrics['sharing_efficiency'] = total_shared / total_resources
        
        return metrics
    
    async def predict_resource_needs(self, team_id: str, 
                                    horizon: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Predict future resource needs for a team.
        
        Args:
            team_id: Team to predict for
            horizon: Time horizon for prediction
            
        Returns:
            Predicted resource needs
        """
        predictions = {
            'team_id': team_id,
            'horizon': horizon.total_seconds() / 3600,  # hours
            'predicted_needs': {},
            'confidence': 0.0
        }
        
        # Analyze historical allocations
        team_history = [
            a for a in self.allocation_history
            if a.allocated_to == team_id
        ]
        
        if not team_history:
            predictions['confidence'] = 0.0
            return predictions
        
        # Calculate average usage by resource type
        usage_by_type = {}
        
        for allocation in team_history:
            resource = self.resources.get(allocation.resource_id)
            if resource:
                if resource.type not in usage_by_type:
                    usage_by_type[resource.type] = []
                usage_by_type[resource.type].append(
                    allocation.actual_usage or allocation.amount
                )
        
        # Calculate predictions
        for resource_type, usages in usage_by_type.items():
            avg_usage = sum(usages) / len(usages)
            max_usage = max(usages)
            
            predictions['predicted_needs'][resource_type.value] = {
                'average': avg_usage,
                'peak': max_usage,
                'recommended': avg_usage * 1.2  # 20% buffer
            }
        
        # Calculate confidence based on data points
        total_points = sum(len(usages) for usages in usage_by_type.values())
        predictions['confidence'] = min(total_points / 10, 1.0)  # Max confidence at 10+ points
        
        return predictions