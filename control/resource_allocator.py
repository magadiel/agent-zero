"""
Resource Allocator Module
Manages fair distribution of computational resources across agent teams.
"""

import asyncio
import logging
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
import heapq
import threading
import time

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ResourceType(Enum):
    """Types of resources that can be allocated."""
    CPU_CORES = "cpu_cores"
    MEMORY_GB = "memory_gb"
    GPU_COUNT = "gpu_count"
    DISK_GB = "disk_gb"
    NETWORK_MBPS = "network_mbps"
    API_CALLS = "api_calls"
    AGENT_SLOTS = "agent_slots"


class PriorityLevel(Enum):
    """Priority levels for resource allocation requests."""
    CRITICAL = 1  # Lowest number = highest priority
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class AllocationStatus(Enum):
    """Status of a resource allocation request."""
    PENDING = "pending"
    ALLOCATED = "allocated"
    PARTIAL = "partial"
    DENIED = "denied"
    EXPIRED = "expired"
    RELEASED = "released"


@dataclass
class ResourcePool:
    """Represents a pool of available resources."""
    total: Dict[ResourceType, float] = field(default_factory=dict)
    available: Dict[ResourceType, float] = field(default_factory=dict)
    reserved: Dict[ResourceType, float] = field(default_factory=dict)
    
    def initialize(self, config: Dict[str, Any]):
        """Initialize resource pool from configuration."""
        for resource_str, value in config.items():
            try:
                resource_type = ResourceType(resource_str)
                self.total[resource_type] = float(value)
                self.available[resource_type] = float(value)
                self.reserved[resource_type] = 0.0
            except (ValueError, KeyError):
                logger.warning(f"Unknown resource type in config: {resource_str}")


@dataclass
class ResourceRequest:
    """Represents a request for resources."""
    request_id: str
    team_id: str
    resources: Dict[ResourceType, float]
    priority: PriorityLevel
    duration_minutes: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Compare requests for priority queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class ResourceAllocation:
    """Represents an active resource allocation."""
    allocation_id: str
    request: ResourceRequest
    allocated_resources: Dict[ResourceType, float]
    status: AllocationStatus
    allocated_at: datetime
    expires_at: datetime
    actual_usage: Dict[ResourceType, float] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if allocation has expired."""
        return datetime.now() > self.expires_at


class ResourceAllocator:
    """Manages resource allocation for agent teams."""
    
    def __init__(self, config_path: str = None):
        """Initialize the resource allocator."""
        self.config_path = config_path or "config/resource_limits.yaml"
        self.config = self._load_config()
        
        # Initialize resource pools
        self.pools = self._initialize_pools()
        
        # Priority queue for pending requests
        self.pending_requests: List[ResourceRequest] = []
        self.request_lock = threading.Lock()
        
        # Active allocations
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.allocation_lock = threading.Lock()
        
        # Team resource limits
        self.team_limits = self._load_team_limits()
        self.team_usage: Dict[str, Dict[ResourceType, float]] = {}
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Resource Allocator initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = Path(self.config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "resource_pools": {
                "default": {
                    "cpu_cores": 32,
                    "memory_gb": 128,
                    "gpu_count": 4,
                    "disk_gb": 1000,
                    "network_mbps": 1000,
                    "api_calls": 10000,
                    "agent_slots": 50
                }
            },
            "team_limits": {
                "default": {
                    "max_cpu_cores": 8,
                    "max_memory_gb": 32,
                    "max_gpu_count": 1,
                    "max_agent_slots": 10
                }
            },
            "allocation_policies": {
                "max_duration_minutes": 60,
                "auto_release_idle_minutes": 15,
                "oversubscription_ratio": 1.2,
                "priority_boost_critical": 2.0,
                "priority_boost_high": 1.5
            }
        }
    
    def _initialize_pools(self) -> Dict[str, ResourcePool]:
        """Initialize resource pools from configuration."""
        pools = {}
        for pool_name, pool_config in self.config.get("resource_pools", {}).items():
            pool = ResourcePool()
            pool.initialize(pool_config)
            pools[pool_name] = pool
            logger.info(f"Initialized resource pool '{pool_name}' with {len(pool.total)} resource types")
        return pools
    
    def _load_team_limits(self) -> Dict[str, Dict[ResourceType, float]]:
        """Load per-team resource limits."""
        limits = {}
        for team_id, team_config in self.config.get("team_limits", {}).items():
            team_limits = {}
            for resource_str, value in team_config.items():
                if resource_str.startswith("max_"):
                    resource_type_str = resource_str[4:]  # Remove 'max_' prefix
                    try:
                        resource_type = ResourceType(resource_type_str)
                        team_limits[resource_type] = float(value)
                    except ValueError:
                        logger.warning(f"Unknown resource type: {resource_type_str}")
            limits[team_id] = team_limits
        return limits
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        # Start expiration checker
        expiry_thread = threading.Thread(target=self._expiration_checker, daemon=True)
        expiry_thread.start()
        
        # Start allocation processor
        processor_thread = threading.Thread(target=self._allocation_processor, daemon=True)
        processor_thread.start()
    
    def _expiration_checker(self):
        """Background task to check and release expired allocations."""
        while True:
            try:
                expired_ids = []
                with self.allocation_lock:
                    for alloc_id, allocation in self.allocations.items():
                        if allocation.is_expired():
                            expired_ids.append(alloc_id)
                
                for alloc_id in expired_ids:
                    self.release_resources(alloc_id, reason="expired")
                    logger.info(f"Released expired allocation: {alloc_id}")
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in expiration checker: {e}")
                time.sleep(60)
    
    def _allocation_processor(self):
        """Background task to process pending allocation requests."""
        while True:
            try:
                if self.pending_requests:
                    with self.request_lock:
                        # Process highest priority request
                        if self.pending_requests:
                            request = heapq.heappop(self.pending_requests)
                            self._try_allocate(request)
                
                time.sleep(1)  # Process every second
            except Exception as e:
                logger.error(f"Error in allocation processor: {e}")
                time.sleep(5)
    
    async def request_resources(
        self,
        team_id: str,
        resources: Dict[ResourceType, float],
        priority: PriorityLevel = PriorityLevel.NORMAL,
        duration_minutes: int = 30,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, AllocationStatus]:
        """
        Request resources for a team.
        
        Returns:
            Tuple of (request_id, initial_status)
        """
        # Generate request ID
        request_id = f"req_{team_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Validate against team limits
        if not self._validate_team_limits(team_id, resources):
            self._audit_event("resource_request_denied", {
                "request_id": request_id,
                "team_id": team_id,
                "reason": "exceeds_team_limits"
            })
            return request_id, AllocationStatus.DENIED
        
        # Create request
        request = ResourceRequest(
            request_id=request_id,
            team_id=team_id,
            resources=resources,
            priority=priority,
            duration_minutes=min(duration_minutes, self.config.get("allocation_policies", {}).get("max_duration_minutes", 60)),
            metadata=metadata or {}
        )
        
        # Try immediate allocation for critical requests
        if priority == PriorityLevel.CRITICAL:
            status = self._try_allocate(request)
            if status == AllocationStatus.ALLOCATED:
                return request_id, status
        
        # Add to priority queue
        with self.request_lock:
            heapq.heappush(self.pending_requests, request)
        
        self._audit_event("resource_request_queued", {
            "request_id": request_id,
            "team_id": team_id,
            "priority": priority.name
        })
        
        return request_id, AllocationStatus.PENDING
    
    def _validate_team_limits(self, team_id: str, resources: Dict[ResourceType, float]) -> bool:
        """Validate request against team resource limits."""
        # Get team limits (use default if team not found)
        team_limits = self.team_limits.get(team_id, self.team_limits.get("default", {}))
        
        # Get current team usage
        current_usage = self.team_usage.get(team_id, {})
        
        # Check each requested resource
        for resource_type, requested_amount in resources.items():
            limit = team_limits.get(resource_type, float('inf'))
            current = current_usage.get(resource_type, 0)
            
            if current + requested_amount > limit:
                logger.warning(f"Team {team_id} would exceed limit for {resource_type.value}: {current + requested_amount} > {limit}")
                return False
        
        return True
    
    def _try_allocate(self, request: ResourceRequest) -> AllocationStatus:
        """Try to allocate resources for a request."""
        # Find suitable pool
        pool = self._find_suitable_pool(request.resources)
        if not pool:
            return AllocationStatus.DENIED
        
        # Check availability
        can_allocate = True
        for resource_type, amount in request.resources.items():
            available = pool.available.get(resource_type, 0)
            
            # Apply priority boost for critical/high priority
            if request.priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
                boost = self.config.get("allocation_policies", {}).get(
                    f"priority_boost_{request.priority.name.lower()}", 1.0
                )
                available *= boost
            
            if available < amount:
                can_allocate = False
                break
        
        if not can_allocate:
            return AllocationStatus.PENDING
        
        # Perform allocation
        allocated_resources = {}
        for resource_type, amount in request.resources.items():
            pool.available[resource_type] -= amount
            allocated_resources[resource_type] = amount
            
            # Update team usage
            if request.team_id not in self.team_usage:
                self.team_usage[request.team_id] = {}
            self.team_usage[request.team_id][resource_type] = \
                self.team_usage[request.team_id].get(resource_type, 0) + amount
        
        # Create allocation record
        allocation = ResourceAllocation(
            allocation_id=f"alloc_{request.request_id}",
            request=request,
            allocated_resources=allocated_resources,
            status=AllocationStatus.ALLOCATED,
            allocated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=request.duration_minutes)
        )
        
        with self.allocation_lock:
            self.allocations[allocation.allocation_id] = allocation
        
        self._audit_event("resource_allocated", {
            "allocation_id": allocation.allocation_id,
            "team_id": request.team_id,
            "resources": {k.value: v for k, v in allocated_resources.items()}
        })
        
        logger.info(f"Allocated resources for team {request.team_id}: {allocation.allocation_id}")
        return AllocationStatus.ALLOCATED
    
    def _find_suitable_pool(self, resources: Dict[ResourceType, float]) -> Optional[ResourcePool]:
        """Find a suitable pool that can satisfy the resource request."""
        # For now, use the default pool
        # In future, implement more sophisticated pool selection
        return self.pools.get("default")
    
    async def release_resources(self, allocation_id: str, reason: str = "manual") -> bool:
        """
        Release allocated resources back to the pool.
        
        Returns:
            True if successful, False otherwise
        """
        with self.allocation_lock:
            if allocation_id not in self.allocations:
                logger.warning(f"Allocation not found: {allocation_id}")
                return False
            
            allocation = self.allocations[allocation_id]
            pool = self._find_suitable_pool(allocation.allocated_resources)
            
            if pool:
                # Return resources to pool
                for resource_type, amount in allocation.allocated_resources.items():
                    pool.available[resource_type] += amount
                    
                    # Update team usage
                    team_id = allocation.request.team_id
                    if team_id in self.team_usage:
                        self.team_usage[team_id][resource_type] = max(
                            0, self.team_usage[team_id].get(resource_type, 0) - amount
                        )
            
            # Update allocation status
            allocation.status = AllocationStatus.RELEASED
            
            # Remove from active allocations
            del self.allocations[allocation_id]
        
        self._audit_event("resource_released", {
            "allocation_id": allocation_id,
            "team_id": allocation.request.team_id,
            "reason": reason
        })
        
        logger.info(f"Released resources for allocation {allocation_id} (reason: {reason})")
        return True
    
    async def get_allocation_status(self, allocation_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an allocation."""
        with self.allocation_lock:
            if allocation_id in self.allocations:
                allocation = self.allocations[allocation_id]
                return {
                    "allocation_id": allocation_id,
                    "status": allocation.status.value,
                    "team_id": allocation.request.team_id,
                    "allocated_resources": {k.value: v for k, v in allocation.allocated_resources.items()},
                    "allocated_at": allocation.allocated_at.isoformat(),
                    "expires_at": allocation.expires_at.isoformat(),
                    "is_expired": allocation.is_expired()
                }
        return None
    
    async def get_team_usage(self, team_id: str) -> Dict[str, float]:
        """Get current resource usage for a team."""
        usage = self.team_usage.get(team_id, {})
        return {k.value: v for k, v in usage.items()}
    
    async def get_pool_status(self, pool_name: str = "default") -> Dict[str, Any]:
        """Get the status of a resource pool."""
        pool = self.pools.get(pool_name)
        if not pool:
            return {}
        
        return {
            "pool_name": pool_name,
            "resources": {
                resource_type.value: {
                    "total": pool.total.get(resource_type, 0),
                    "available": pool.available.get(resource_type, 0),
                    "used": pool.total.get(resource_type, 0) - pool.available.get(resource_type, 0),
                    "utilization": 1 - (pool.available.get(resource_type, 0) / max(pool.total.get(resource_type, 1), 1))
                }
                for resource_type in pool.total.keys()
            }
        }
    
    async def update_actual_usage(self, allocation_id: str, usage: Dict[ResourceType, float]):
        """Update the actual resource usage for an allocation."""
        with self.allocation_lock:
            if allocation_id in self.allocations:
                self.allocations[allocation_id].actual_usage.update(usage)
                
                # Check for overuse
                allocation = self.allocations[allocation_id]
                for resource_type, used in usage.items():
                    allocated = allocation.allocated_resources.get(resource_type, 0)
                    if used > allocated * 1.1:  # 10% tolerance
                        logger.warning(f"Team {allocation.request.team_id} exceeding allocation for {resource_type.value}: {used} > {allocated}")
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get list of pending resource requests."""
        with self.request_lock:
            return [
                {
                    "request_id": req.request_id,
                    "team_id": req.team_id,
                    "priority": req.priority.name,
                    "resources": {k.value: v for k, v in req.resources.items()},
                    "timestamp": req.timestamp.isoformat()
                }
                for req in self.pending_requests
            ]
    
    def _audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log an audit event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        self.audit_log.append(event)
        
        # Also log to file if audit directory exists
        audit_dir = Path("audit_logs")
        if audit_dir.exists():
            audit_file = audit_dir / f"resource_audit_{datetime.now().strftime('%Y%m%d')}.log"
            with open(audit_file, 'a') as f:
                f.write(json.dumps(event) + "\n")
    
    async def emergency_release_all(self, reason: str = "emergency"):
        """Emergency release of all allocations."""
        logger.warning(f"Emergency release triggered: {reason}")
        
        with self.allocation_lock:
            allocation_ids = list(self.allocations.keys())
        
        # Release all allocations
        release_tasks = []
        for alloc_id in allocation_ids:
            release_tasks.append(self.release_resources(alloc_id, reason=reason))
        
        if release_tasks:
            await asyncio.gather(*release_tasks)
        
        # Clear pending requests
        with self.request_lock:
            self.pending_requests.clear()
        
        self._audit_event("emergency_release", {"reason": reason, "allocations_released": len(allocation_ids)})