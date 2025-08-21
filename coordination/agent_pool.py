"""
Agent Pool Management System for Dynamic Agent Allocation

This module provides a comprehensive agent pool management system that handles:
- Dynamic agent allocation based on requirements
- Agent availability and skill tracking  
- Resource-aware allocation with limits
- Agent release and pool management
- Integration with control layer resource allocator
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import random
from pathlib import Path

# Import control layer components
import sys
sys.path.append('/home/magadiel/Desktop/agent-zero')
try:
    from control.resource_allocator import ResourceAllocator
except ImportError:
    ResourceAllocator = None

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent availability status in the pool"""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    TERMINATING = "terminating"


class AgentSkill(Enum):
    """Agent skill categories for matching requirements"""
    PRODUCT_MANAGEMENT = "product_management"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEVOPS = "devops"
    DATA_ANALYSIS = "data_analysis"
    CUSTOMER_SERVICE = "customer_service"
    OPERATIONS = "operations"
    SECURITY = "security"
    UI_UX = "ui_ux"
    SCRUM_MASTER = "scrum_master"
    GENERAL = "general"


@dataclass
class PooledAgent:
    """Represents an agent in the pool with metadata"""
    agent_id: str
    profile: str  # Agent profile type (e.g., "developer", "architect")
    skills: Set[AgentSkill]
    status: AgentStatus
    allocated_to: Optional[str] = None  # Team ID if allocated
    allocated_at: Optional[datetime] = None
    performance_score: float = 1.0  # Performance metric (0.0 to 1.0)
    total_allocations: int = 0
    total_task_completions: int = 0
    last_health_check: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for serialization"""
        return {
            'agent_id': self.agent_id,
            'profile': self.profile,
            'skills': [s.value for s in self.skills],
            'status': self.status.value,
            'allocated_to': self.allocated_to,
            'allocated_at': self.allocated_at.isoformat() if self.allocated_at else None,
            'performance_score': self.performance_score,
            'total_allocations': self.total_allocations,
            'total_task_completions': self.total_task_completions,
            'last_health_check': self.last_health_check.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class AllocationRequest:
    """Request for agent allocation from the pool"""
    request_id: str
    team_id: str
    required_count: int
    required_skills: Set[AgentSkill]
    optional_skills: Set[AgentSkill] = field(default_factory=set)
    preferred_profiles: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher is more important
    timeout: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentPool:
    """
    Manages a pool of agents for dynamic allocation to teams.
    
    Features:
    - Dynamic agent creation and management
    - Skill-based allocation
    - Resource-aware allocation with control layer integration
    - Performance tracking and optimization
    - Health monitoring and recovery
    """
    
    def __init__(self, 
                 pool_size: int = 20,
                 resource_allocator: Optional[ResourceAllocator] = None,
                 config_path: Optional[Path] = None):
        """
        Initialize the agent pool.
        
        Args:
            pool_size: Initial number of agents in the pool
            resource_allocator: Control layer resource allocator
            config_path: Path to pool configuration file
        """
        self.pool_size = pool_size
        self.agents: Dict[str, PooledAgent] = {}
        self.allocation_queue: List[AllocationRequest] = []
        self.resource_allocator = resource_allocator if resource_allocator is not None else (ResourceAllocator() if ResourceAllocator else None)
        self.config_path = config_path or Path("coordination/config/agent_pool.yaml")
        self._lock = asyncio.Lock()
        self._allocation_history: List[Dict[str, Any]] = []
        self._initialized = False
        
        # Pool configuration
        self.config = {
            'max_pool_size': 100,
            'min_pool_size': 5,
            'auto_scale': True,
            'health_check_interval': 60,  # seconds
            'allocation_timeout': 30,  # seconds
            'performance_threshold': 0.3,  # Min performance score
            'skill_distribution': self._default_skill_distribution()
        }
        
        logger.info(f"AgentPool initialized with size {pool_size}")
    
    def _default_skill_distribution(self) -> Dict[str, float]:
        """Default distribution of skills in the pool"""
        return {
            AgentSkill.DEVELOPMENT.value: 0.30,
            AgentSkill.TESTING.value: 0.15,
            AgentSkill.PRODUCT_MANAGEMENT.value: 0.10,
            AgentSkill.ARCHITECTURE.value: 0.10,
            AgentSkill.DEVOPS.value: 0.10,
            AgentSkill.DATA_ANALYSIS.value: 0.05,
            AgentSkill.CUSTOMER_SERVICE.value: 0.05,
            AgentSkill.OPERATIONS.value: 0.05,
            AgentSkill.SECURITY.value: 0.05,
            AgentSkill.UI_UX.value: 0.03,
            AgentSkill.SCRUM_MASTER.value: 0.02
        }
    
    async def initialize(self):
        """Initialize the agent pool with agents"""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing agent pool...")
            
            # Create initial agents based on skill distribution
            for i in range(self.pool_size):
                agent = await self._create_agent(i)
                self.agents[agent.agent_id] = agent
            
            # Start background tasks
            asyncio.create_task(self._health_monitor())
            asyncio.create_task(self._allocation_processor())
            
            self._initialized = True
            logger.info(f"Agent pool initialized with {len(self.agents)} agents")
    
    async def _create_agent(self, index: int) -> PooledAgent:
        """Create a new agent with assigned skills"""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        # Assign profile and skills based on distribution
        profile, skills = self._assign_profile_and_skills(index)
        
        agent = PooledAgent(
            agent_id=agent_id,
            profile=profile,
            skills=skills,
            status=AgentStatus.AVAILABLE,
            metadata={
                'created_at': datetime.now().isoformat(),
                'pool_index': index
            }
        )
        
        logger.debug(f"Created agent {agent_id} with profile {profile} and skills {skills}")
        return agent
    
    def _assign_profile_and_skills(self, index: int) -> Tuple[str, Set[AgentSkill]]:
        """Assign profile and skills to an agent based on distribution"""
        # Determine primary skill based on distribution
        skill_weights = list(self.config['skill_distribution'].values())
        skill_names = list(self.config['skill_distribution'].keys())
        
        # Use weighted random selection
        primary_skill_name = random.choices(skill_names, weights=skill_weights)[0]
        primary_skill = AgentSkill(primary_skill_name)
        
        # Map skill to profile
        skill_to_profile = {
            AgentSkill.PRODUCT_MANAGEMENT: "product_manager",
            AgentSkill.ARCHITECTURE: "architect",
            AgentSkill.DEVELOPMENT: "developer",
            AgentSkill.TESTING: "qa_engineer",
            AgentSkill.DEVOPS: "devops",
            AgentSkill.DATA_ANALYSIS: "data_analyst",
            AgentSkill.CUSTOMER_SERVICE: "customer_service",
            AgentSkill.OPERATIONS: "operations",
            AgentSkill.SECURITY: "security",
            AgentSkill.UI_UX: "designer",
            AgentSkill.SCRUM_MASTER: "scrum_master"
        }
        
        profile = skill_to_profile.get(primary_skill, "general")
        
        # Assign skills (primary + potentially secondary skills)
        skills = {primary_skill}
        
        # Add secondary skills based on profile
        if profile == "developer":
            skills.add(AgentSkill.TESTING)
            if random.random() > 0.5:
                skills.add(AgentSkill.DEVOPS)
        elif profile == "architect":
            skills.add(AgentSkill.DEVELOPMENT)
            skills.add(AgentSkill.SECURITY)
        elif profile == "product_manager":
            skills.add(AgentSkill.DATA_ANALYSIS)
        elif profile == "qa_engineer":
            skills.add(AgentSkill.DEVELOPMENT)
        
        # All agents have general skills
        skills.add(AgentSkill.GENERAL)
        
        return profile, skills
    
    async def allocate_agents(self, request: AllocationRequest) -> List[PooledAgent]:
        """
        Allocate agents from the pool based on requirements.
        
        Args:
            request: Allocation request with requirements
            
        Returns:
            List of allocated agents
            
        Raises:
            InsufficientResourcesError: If not enough agents available
        """
        async with self._lock:
            logger.info(f"Processing allocation request {request.request_id} for team {request.team_id}")
            
            # Check resource availability with control layer
            if self.resource_allocator:
                resources_available = await self._check_resource_availability(
                    request.team_id, 
                    request.required_count
                )
                if not resources_available:
                    raise InsufficientResourcesError(
                        f"Insufficient resources for team {request.team_id}"
                    )
            
            # Find suitable agents
            suitable_agents = await self._find_suitable_agents(request)
            
            if len(suitable_agents) < request.required_count:
                # Try to create more agents if auto-scaling is enabled
                if self.config['auto_scale']:
                    await self._auto_scale(request.required_count - len(suitable_agents))
                    suitable_agents = await self._find_suitable_agents(request)
                
                if len(suitable_agents) < request.required_count:
                    # Add to queue if still not enough agents
                    self.allocation_queue.append(request)
                    raise InsufficientAgentsError(
                        f"Only {len(suitable_agents)} agents available, "
                        f"need {request.required_count}. Request queued."
                    )
            
            # Allocate the agents
            allocated = suitable_agents[:request.required_count]
            for agent in allocated:
                agent.status = AgentStatus.ALLOCATED
                agent.allocated_to = request.team_id
                agent.allocated_at = datetime.now()
                agent.total_allocations += 1
            
            # Track allocation
            self._allocation_history.append({
                'request_id': request.request_id,
                'team_id': request.team_id,
                'allocated_agents': [a.agent_id for a in allocated],
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Allocated {len(allocated)} agents to team {request.team_id}")
            return allocated
    
    async def _find_suitable_agents(self, request: AllocationRequest) -> List[PooledAgent]:
        """Find agents that match the request requirements"""
        suitable = []
        
        for agent in self.agents.values():
            if agent.status != AgentStatus.AVAILABLE:
                continue
            
            # Check performance threshold
            if agent.performance_score < self.config['performance_threshold']:
                continue
            
            # Check required skills
            if request.required_skills and not request.required_skills.issubset(agent.skills):
                continue
            
            # Score agent based on match quality
            score = self._calculate_match_score(agent, request)
            suitable.append((score, agent))
        
        # Sort by score (higher is better) and return agents
        suitable.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in suitable]
    
    def _calculate_match_score(self, agent: PooledAgent, request: AllocationRequest) -> float:
        """Calculate how well an agent matches the request"""
        score = 0.0
        
        # Base score for availability
        score += 1.0
        
        # Score for required skills (already filtered)
        score += len(request.required_skills.intersection(agent.skills)) * 2.0
        
        # Score for optional skills
        score += len(request.optional_skills.intersection(agent.skills)) * 1.0
        
        # Score for preferred profile
        if agent.profile in request.preferred_profiles:
            score += 3.0
        
        # Factor in performance score
        score *= agent.performance_score
        
        # Prefer agents with fewer total allocations (load balancing)
        score -= agent.total_allocations * 0.01
        
        return score
    
    async def release_agents(self, team_id: str, agent_ids: Optional[List[str]] = None):
        """
        Release agents back to the pool.
        
        Args:
            team_id: Team releasing the agents
            agent_ids: Specific agents to release (None = all from team)
        """
        async with self._lock:
            released = []
            
            for agent_id, agent in self.agents.items():
                if agent.allocated_to == team_id:
                    if agent_ids is None or agent_id in agent_ids:
                        agent.status = AgentStatus.AVAILABLE
                        agent.allocated_to = None
                        agent.allocated_at = None
                        released.append(agent_id)
            
            logger.info(f"Released {len(released)} agents from team {team_id}")
            
            # Process queued requests
            await self._process_queue()
    
    async def _process_queue(self):
        """Process queued allocation requests"""
        if not self.allocation_queue:
            return
        
        processed = []
        for request in self.allocation_queue[:]:  # Copy to avoid modification during iteration
            try:
                agents = await self.allocate_agents(request)
                processed.append(request)
                logger.info(f"Processed queued request {request.request_id}")
            except (InsufficientAgentsError, InsufficientResourcesError):
                # Keep in queue
                pass
        
        # Remove processed requests
        for request in processed:
            self.allocation_queue.remove(request)
    
    async def update_agent_performance(self, agent_id: str, performance_delta: float):
        """
        Update agent performance score.
        
        Args:
            agent_id: Agent to update
            performance_delta: Change in performance (-1.0 to 1.0)
        """
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.performance_score = max(0.0, min(1.0, 
                    agent.performance_score + performance_delta))
                
                # Mark for maintenance if performance too low
                if agent.performance_score < self.config['performance_threshold']:
                    if agent.status == AgentStatus.AVAILABLE:
                        agent.status = AgentStatus.MAINTENANCE
                        logger.warning(f"Agent {agent_id} marked for maintenance due to low performance")
    
    async def _health_monitor(self):
        """Background task to monitor agent health"""
        while True:
            try:
                await asyncio.sleep(self.config['health_check_interval'])
                
                async with self._lock:
                    for agent in self.agents.values():
                        # Simulate health check
                        agent.last_health_check = datetime.now()
                        
                        # Recover agents in maintenance if performance improved
                        if (agent.status == AgentStatus.MAINTENANCE and 
                            agent.performance_score >= self.config['performance_threshold']):
                            agent.status = AgentStatus.AVAILABLE
                            logger.info(f"Agent {agent.agent_id} recovered from maintenance")
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    async def _allocation_processor(self):
        """Background task to process allocation queue"""
        while True:
            try:
                await asyncio.sleep(5)  # Check queue every 5 seconds
                await self._process_queue()
            except Exception as e:
                logger.error(f"Error in allocation processor: {e}")
    
    async def _auto_scale(self, needed_count: int):
        """Auto-scale the pool by creating new agents"""
        current_size = len(self.agents)
        max_size = self.config['max_pool_size']
        
        if current_size >= max_size:
            logger.warning(f"Cannot auto-scale: at maximum pool size {max_size}")
            return
        
        new_count = min(needed_count, max_size - current_size)
        logger.info(f"Auto-scaling: creating {new_count} new agents")
        
        for i in range(new_count):
            agent = await self._create_agent(current_size + i)
            self.agents[agent.agent_id] = agent
    
    async def _check_resource_availability(self, team_id: str, agent_count: int) -> bool:
        """Check with control layer if resources are available"""
        try:
            # Each agent needs certain resources
            resources_per_agent = {
                'cpu_cores': 1,
                'memory_gb': 2,
                'agents': 1
            }
            
            total_resources = {
                k: v * agent_count 
                for k, v in resources_per_agent.items()
            }
            
            # Request allocation from control layer
            allocation = await self.resource_allocator.allocate_resources(
                team_id=team_id,
                resources=total_resources,
                priority=5
            )
            
            return allocation is not None
            
        except Exception as e:
            logger.error(f"Error checking resource availability: {e}")
            return True  # Assume available if check fails
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and statistics"""
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = sum(
                1 for a in self.agents.values() 
                if a.status == status
            )
        
        skill_counts = {}
        for skill in AgentSkill:
            skill_counts[skill.value] = sum(
                1 for a in self.agents.values()
                if skill in a.skills
            )
        
        return {
            'total_agents': len(self.agents),
            'status_distribution': status_counts,
            'skill_distribution': skill_counts,
            'queued_requests': len(self.allocation_queue),
            'allocation_history_count': len(self._allocation_history),
            'average_performance': sum(a.performance_score for a in self.agents.values()) / len(self.agents) if self.agents else 0,
            'config': self.config
        }
    
    async def shutdown(self):
        """Gracefully shutdown the agent pool"""
        logger.info("Shutting down agent pool...")
        
        async with self._lock:
            # Mark all agents as terminating
            for agent in self.agents.values():
                agent.status = AgentStatus.TERMINATING
            
            # Save state if needed
            if self.config_path:
                await self._save_state()
        
        logger.info("Agent pool shutdown complete")
    
    async def _save_state(self):
        """Save pool state to disk"""
        state = {
            'agents': [a.to_dict() for a in self.agents.values()],
            'allocation_history': self._allocation_history[-100:],  # Keep last 100
            'config': self.config,
            'timestamp': datetime.now().isoformat()
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path.with_suffix('.json'), 'w') as f:
            json.dump(state, f, indent=2)


class InsufficientAgentsError(Exception):
    """Raised when not enough agents are available"""
    pass


class InsufficientResourcesError(Exception):
    """Raised when not enough resources are available"""
    pass


# Example usage and testing
if __name__ == "__main__":
    async def test_agent_pool():
        """Test the agent pool functionality"""
        pool = AgentPool(pool_size=10)
        await pool.initialize()
        
        # Create allocation request
        request = AllocationRequest(
            request_id="req_001",
            team_id="team_customer_service",
            required_count=3,
            required_skills={AgentSkill.CUSTOMER_SERVICE, AgentSkill.GENERAL},
            optional_skills={AgentSkill.DATA_ANALYSIS},
            priority=8
        )
        
        # Allocate agents
        try:
            agents = await pool.allocate_agents(request)
            print(f"Allocated {len(agents)} agents:")
            for agent in agents:
                print(f"  - {agent.agent_id}: {agent.profile} with skills {agent.skills}")
        except InsufficientAgentsError as e:
            print(f"Allocation failed: {e}")
        
        # Get pool status
        status = pool.get_pool_status()
        print(f"\nPool Status: {json.dumps(status, indent=2)}")
        
        # Release agents
        await asyncio.sleep(2)
        await pool.release_agents("team_customer_service")
        
        # Check status again
        status = pool.get_pool_status()
        print(f"\nPool Status after release: {json.dumps(status, indent=2)}")
        
        await pool.shutdown()
    
    # Run test
    asyncio.run(test_agent_pool())