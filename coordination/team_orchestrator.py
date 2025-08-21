"""
Team Orchestrator for Managing Agent Teams

This module provides comprehensive team management capabilities:
- Dynamic team formation based on requirements
- Team lifecycle management (forming, active, performing, dissolving)
- Role assignment within teams
- Resource allocation and limits
- Performance tracking and optimization
- Integration with workflow engine and control layer
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

# Import internal components
import sys
sys.path.append('/home/magadiel/Desktop/agent-zero')
from coordination.agent_pool import AgentPool, AllocationRequest, PooledAgent, AgentSkill
# Optional import for workflow engine
try:
    from coordination.workflow_engine import WorkflowEngine
except ImportError:
    WorkflowEngine = None
# Optional import for control layer
try:
    from control.resource_allocator import ResourceAllocator
except ImportError:
    ResourceAllocator = None

logger = logging.getLogger(__name__)


class TeamStatus(Enum):
    """Team lifecycle states"""
    FORMING = "forming"          # Team being assembled
    STORMING = "storming"        # Team establishing working patterns
    NORMING = "norming"          # Team developing cohesion
    PERFORMING = "performing"    # Team at peak performance
    ADJOURNING = "adjourning"   # Team dissolving
    DISSOLVED = "dissolved"      # Team dissolved


class TeamType(Enum):
    """Types of teams based on structure and purpose"""
    CROSS_FUNCTIONAL = "cross_functional"  # 5-7 specialized agents
    SELF_MANAGING = "self_managing"        # 3-5 autonomous agents
    FLOW_TO_WORK = "flow_to_work"         # 10-20 agents in pool
    SQUAD = "squad"                        # Agile squad structure
    TASK_FORCE = "task_force"             # Temporary for specific goal


class TeamRole(Enum):
    """Roles within a team"""
    LEADER = "leader"
    MEMBER = "member"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    REVIEWER = "reviewer"


@dataclass
class TeamMember:
    """Represents an agent's role in a team"""
    agent: PooledAgent
    role: TeamRole
    joined_at: datetime = field(default_factory=datetime.now)
    tasks_completed: int = 0
    performance_score: float = 1.0
    specialization: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Team:
    """Represents an agent team with members and mission"""
    team_id: str
    name: str
    team_type: TeamType
    mission: str
    status: TeamStatus
    members: Dict[str, TeamMember]  # agent_id -> TeamMember
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    dissolved_at: Optional[datetime] = None
    
    # Performance metrics
    velocity: float = 0.0
    quality_score: float = 1.0
    efficiency_score: float = 1.0
    collaboration_score: float = 1.0
    
    # Resource allocation
    resource_limits: Dict[str, float] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    # Workflow and tasks
    current_workflow: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    active_tasks: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert team to dictionary for serialization"""
        return {
            'team_id': self.team_id,
            'name': self.name,
            'team_type': self.team_type.value,
            'mission': self.mission,
            'status': self.status.value,
            'members': {
                agent_id: {
                    'agent_id': member.agent.agent_id,
                    'role': member.role.value,
                    'joined_at': member.joined_at.isoformat(),
                    'tasks_completed': member.tasks_completed,
                    'performance_score': member.performance_score
                }
                for agent_id, member in self.members.items()
            },
            'created_at': self.created_at.isoformat(),
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'dissolved_at': self.dissolved_at.isoformat() if self.dissolved_at else None,
            'velocity': self.velocity,
            'quality_score': self.quality_score,
            'efficiency_score': self.efficiency_score,
            'collaboration_score': self.collaboration_score,
            'resource_limits': self.resource_limits,
            'resource_usage': self.resource_usage,
            'current_workflow': self.current_workflow,
            'completed_tasks': self.completed_tasks,
            'active_tasks': self.active_tasks
        }
    
    def get_member_count(self) -> int:
        """Get number of active members"""
        return len(self.members)
    
    def get_skills(self) -> Set[AgentSkill]:
        """Get all skills available in the team"""
        skills = set()
        for member in self.members.values():
            skills.update(member.agent.skills)
        return skills
    
    def get_leader(self) -> Optional[TeamMember]:
        """Get the team leader if one exists"""
        for member in self.members.values():
            if member.role == TeamRole.LEADER:
                return member
        return None


@dataclass
class TeamFormationRequest:
    """Request to form a new team"""
    request_id: str
    team_name: str
    team_type: TeamType
    mission: str
    required_skills: Set[AgentSkill]
    team_size: int
    duration: Optional[timedelta] = None
    workflow_id: Optional[str] = None
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TeamOrchestrator:
    """
    Orchestrates team formation, management, and dissolution.
    
    Features:
    - Dynamic team formation based on requirements
    - Team lifecycle management
    - Role assignment and leadership
    - Resource allocation with limits
    - Performance tracking and optimization
    - Integration with workflow engine
    """
    
    def __init__(self,
                 agent_pool: Optional[AgentPool] = None,
                 workflow_engine: Optional[WorkflowEngine] = None,
                 resource_allocator: Optional[ResourceAllocator] = None,
                 config_path: Optional[Path] = None):
        """
        Initialize the team orchestrator.
        
        Args:
            agent_pool: Agent pool for allocation
            workflow_engine: Workflow engine for task assignment
            resource_allocator: Control layer resource allocator
            config_path: Path to configuration file
        """
        self.agent_pool = agent_pool or AgentPool()
        self.workflow_engine = workflow_engine
        self.resource_allocator = resource_allocator if resource_allocator is not None else (ResourceAllocator() if ResourceAllocator else None)
        self.teams: Dict[str, Team] = {}
        self.config_path = config_path or Path("coordination/config/team_orchestrator.yaml")
        self._lock = asyncio.Lock()
        self._team_monitors: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.config = {
            'max_teams': 20,
            'min_team_size': 3,
            'max_team_size': 20,
            'default_team_sizes': {
                TeamType.CROSS_FUNCTIONAL: 7,
                TeamType.SELF_MANAGING: 4,
                TeamType.FLOW_TO_WORK: 15,
                TeamType.SQUAD: 8,
                TeamType.TASK_FORCE: 5
            },
            'performance_check_interval': 300,  # seconds
            'auto_dissolve_idle_time': 3600,   # seconds
            'leader_assignment_threshold': 5    # Min size for leader
        }
        
        logger.info("TeamOrchestrator initialized")
    
    async def initialize(self):
        """Initialize the team orchestrator"""
        # Initialize agent pool if not already done
        if not self.agent_pool._initialized:
            await self.agent_pool.initialize()
        
        logger.info("TeamOrchestrator initialized")
    
    async def form_team(self, request: TeamFormationRequest) -> Team:
        """
        Form a new team based on requirements.
        
        Args:
            request: Team formation request
            
        Returns:
            Formed team
            
        Raises:
            TeamFormationError: If team cannot be formed
        """
        async with self._lock:
            logger.info(f"Forming team '{request.team_name}' for mission: {request.mission}")
            
            # Validate request
            self._validate_formation_request(request)
            
            # Check resource availability
            if self.resource_allocator:
                resources_approved = await self._request_team_resources(request)
                if not resources_approved:
                    raise TeamFormationError("Insufficient resources for team formation")
            
            # Create team
            team_id = f"team_{uuid.uuid4().hex[:8]}"
            team = Team(
                team_id=team_id,
                name=request.team_name,
                team_type=request.team_type,
                mission=request.mission,
                status=TeamStatus.FORMING,
                members={},
                resource_limits=request.resource_requirements,
                current_workflow=request.workflow_id,
                metadata=request.metadata
            )
            
            # Request agents from pool
            allocation_request = AllocationRequest(
                request_id=request.request_id,
                team_id=team_id,
                required_count=request.team_size,
                required_skills=request.required_skills,
                priority=8
            )
            
            try:
                allocated_agents = await self.agent_pool.allocate_agents(allocation_request)
            except Exception as e:
                raise TeamFormationError(f"Failed to allocate agents: {e}")
            
            # Assign agents to team with roles
            await self._assign_team_members(team, allocated_agents)
            
            # Update team status
            team.status = TeamStatus.STORMING
            team.activated_at = datetime.now()
            
            # Store team
            self.teams[team_id] = team
            
            # Start team monitor
            self._team_monitors[team_id] = asyncio.create_task(
                self._monitor_team(team_id)
            )
            
            # Assign workflow if specified
            if request.workflow_id and self.workflow_engine:
                await self._assign_workflow_to_team(team, request.workflow_id)
            
            logger.info(f"Team '{team.name}' formed with {len(team.members)} members")
            return team
    
    def _validate_formation_request(self, request: TeamFormationRequest):
        """Validate team formation request"""
        if request.team_size < self.config['min_team_size']:
            raise ValueError(f"Team size {request.team_size} below minimum {self.config['min_team_size']}")
        
        if request.team_size > self.config['max_team_size']:
            raise ValueError(f"Team size {request.team_size} above maximum {self.config['max_team_size']}")
        
        if len(self.teams) >= self.config['max_teams']:
            raise TeamFormationError(f"Maximum number of teams ({self.config['max_teams']}) reached")
    
    async def _request_team_resources(self, request: TeamFormationRequest) -> bool:
        """Request resources for team from control layer"""
        if not self.resource_allocator:
            return True  # No resource allocator, assume resources available
            
        try:
            # Calculate total resources needed
            base_resources = {
                'cpu_cores': request.team_size * 2,
                'memory_gb': request.team_size * 4,
                'storage_gb': 100,
                'network_bandwidth_mbps': 100
            }
            
            # Merge with requested resources
            total_resources = {**base_resources, **request.resource_requirements}
            
            # Request allocation
            allocation = self.resource_allocator.request_resources(
                request.team_name,
                total_resources,
                priority=7
            )
            
            return allocation is not None
            
        except Exception as e:
            logger.error(f"Error requesting team resources: {e}")
            return True  # On error, assume resources available
    
    async def _assign_team_members(self, team: Team, agents: List[PooledAgent]):
        """Assign agents to team with appropriate roles"""
        # Sort agents by performance for role assignment
        agents.sort(key=lambda a: a.performance_score, reverse=True)
        
        # Assign leader if team is large enough
        if len(agents) >= self.config['leader_assignment_threshold']:
            leader = agents[0]
            team.members[leader.agent_id] = TeamMember(
                agent=leader,
                role=TeamRole.LEADER,
                specialization=self._get_specialization(leader)
            )
            remaining_agents = agents[1:]
        else:
            remaining_agents = agents
        
        # Assign other roles
        for i, agent in enumerate(remaining_agents):
            role = self._determine_role(agent, i, len(remaining_agents))
            team.members[agent.agent_id] = TeamMember(
                agent=agent,
                role=role,
                specialization=self._get_specialization(agent)
            )
    
    def _determine_role(self, agent: PooledAgent, index: int, total: int) -> TeamRole:
        """Determine appropriate role for agent"""
        # Assign roles based on skills and position
        if AgentSkill.ARCHITECTURE in agent.skills:
            return TeamRole.SPECIALIST
        elif AgentSkill.TESTING in agent.skills and index < total // 3:
            return TeamRole.REVIEWER
        elif index == 0:
            return TeamRole.COORDINATOR
        else:
            return TeamRole.MEMBER
    
    def _get_specialization(self, agent: PooledAgent) -> str:
        """Get agent's primary specialization"""
        # Prioritized list of specializations
        specializations = [
            (AgentSkill.ARCHITECTURE, "architecture"),
            (AgentSkill.SECURITY, "security"),
            (AgentSkill.DATA_ANALYSIS, "data"),
            (AgentSkill.PRODUCT_MANAGEMENT, "product"),
            (AgentSkill.TESTING, "quality"),
            (AgentSkill.DEVELOPMENT, "development"),
            (AgentSkill.DEVOPS, "operations")
        ]
        
        for skill, spec in specializations:
            if skill in agent.skills:
                return spec
        
        return "general"
    
    async def dissolve_team(self, team_id: str, reason: str = "Mission completed"):
        """
        Dissolve a team and release resources.
        
        Args:
            team_id: Team to dissolve
            reason: Reason for dissolution
        """
        async with self._lock:
            if team_id not in self.teams:
                raise ValueError(f"Team {team_id} not found")
            
            team = self.teams[team_id]
            logger.info(f"Dissolving team '{team.name}': {reason}")
            
            # Update status
            team.status = TeamStatus.ADJOURNING
            
            # Stop monitoring
            if team_id in self._team_monitors:
                self._team_monitors[team_id].cancel()
                del self._team_monitors[team_id]
            
            # Release agents back to pool
            agent_ids = list(team.members.keys())
            await self.agent_pool.release_agents(team_id, agent_ids)
            
            # Release resources
            if self.resource_allocator:
                try:
                    self.resource_allocator.release_allocation(team_id)
                except:
                    pass  # Ignore errors on release
            
            # Final status update
            team.status = TeamStatus.DISSOLVED
            team.dissolved_at = datetime.now()
            team.metadata['dissolution_reason'] = reason
            
            # Archive team (keep for historical data)
            await self._archive_team(team)
            
            # Remove from active teams
            del self.teams[team_id]
            
            logger.info(f"Team '{team.name}' dissolved successfully")
    
    async def _archive_team(self, team: Team):
        """Archive team data for historical analysis"""
        archive_path = self.config_path.parent / "archive" / f"{team.team_id}.json"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(archive_path, 'w') as f:
            json.dump(team.to_dict(), f, indent=2)
    
    async def update_team_status(self, team_id: str, new_status: TeamStatus):
        """Update team's lifecycle status"""
        async with self._lock:
            if team_id not in self.teams:
                raise ValueError(f"Team {team_id} not found")
            
            team = self.teams[team_id]
            old_status = team.status
            team.status = new_status
            
            logger.info(f"Team '{team.name}' status changed from {old_status.value} to {new_status.value}")
            
            # Trigger status-specific actions
            if new_status == TeamStatus.PERFORMING:
                await self._on_team_performing(team)
            elif new_status == TeamStatus.ADJOURNING:
                asyncio.create_task(self.dissolve_team(team_id))
    
    async def _on_team_performing(self, team: Team):
        """Actions when team reaches performing status"""
        # Could trigger notifications, unlock features, etc.
        team.metadata['reached_performing_at'] = datetime.now().isoformat()
    
    async def assign_task_to_team(self, team_id: str, task_id: str):
        """Assign a task to a team"""
        async with self._lock:
            if team_id not in self.teams:
                raise ValueError(f"Team {team_id} not found")
            
            team = self.teams[team_id]
            team.active_tasks.append(task_id)
            
            logger.info(f"Task {task_id} assigned to team '{team.name}'")
    
    async def complete_team_task(self, team_id: str, task_id: str, performance_metrics: Dict[str, float]):
        """Mark a team task as completed and update metrics"""
        async with self._lock:
            if team_id not in self.teams:
                raise ValueError(f"Team {team_id} not found")
            
            team = self.teams[team_id]
            
            if task_id in team.active_tasks:
                team.active_tasks.remove(task_id)
                team.completed_tasks.append(task_id)
                
                # Update team metrics
                if 'quality' in performance_metrics:
                    team.quality_score = (team.quality_score + performance_metrics['quality']) / 2
                if 'efficiency' in performance_metrics:
                    team.efficiency_score = (team.efficiency_score + performance_metrics['efficiency']) / 2
                
                # Update velocity (simple calculation)
                team.velocity = len(team.completed_tasks) / max(1, 
                    (datetime.now() - team.created_at).total_seconds() / 3600)
                
                logger.info(f"Team '{team.name}' completed task {task_id}")
    
    async def _assign_workflow_to_team(self, team: Team, workflow_id: str):
        """Assign a workflow to a team"""
        if self.workflow_engine:
            # This would integrate with the workflow engine
            team.current_workflow = workflow_id
            team.metadata['workflow_assigned_at'] = datetime.now().isoformat()
            logger.info(f"Workflow {workflow_id} assigned to team '{team.name}'")
    
    async def _monitor_team(self, team_id: str):
        """Monitor team performance and health"""
        while team_id in self.teams:
            try:
                await asyncio.sleep(self.config['performance_check_interval'])
                
                async with self._lock:
                    if team_id not in self.teams:
                        break
                    
                    team = self.teams[team_id]
                    
                    # Check team health
                    await self._check_team_health(team)
                    
                    # Update team status based on performance
                    await self._update_team_lifecycle(team)
                    
                    # Check for idle dissolution
                    await self._check_idle_dissolution(team)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring team {team_id}: {e}")
    
    async def _check_team_health(self, team: Team):
        """Check and update team health metrics"""
        # Calculate collaboration score based on task completion
        if team.completed_tasks:
            completion_rate = len(team.completed_tasks) / (len(team.completed_tasks) + len(team.active_tasks))
            team.collaboration_score = min(1.0, completion_rate * 1.2)
        
        # Check resource usage
        if team.resource_limits:
            usage_ratio = sum(team.resource_usage.values()) / sum(team.resource_limits.values())
            if usage_ratio > 0.9:
                logger.warning(f"Team '{team.name}' approaching resource limits")
    
    async def _update_team_lifecycle(self, team: Team):
        """Update team lifecycle status based on performance"""
        if team.status == TeamStatus.STORMING and team.completed_tasks:
            # Progress to norming after completing first tasks
            team.status = TeamStatus.NORMING
            
        elif team.status == TeamStatus.NORMING:
            # Progress to performing if metrics are good
            if (team.quality_score > 0.7 and 
                team.efficiency_score > 0.7 and 
                team.collaboration_score > 0.7):
                team.status = TeamStatus.PERFORMING
    
    async def _check_idle_dissolution(self, team: Team):
        """Check if team should be dissolved due to inactivity"""
        if not team.active_tasks and not team.current_workflow:
            idle_time = (datetime.now() - team.created_at).total_seconds()
            if idle_time > self.config['auto_dissolve_idle_time']:
                await self.dissolve_team(team.team_id, "Idle timeout")
    
    async def get_team_recommendations(self, team_id: str) -> Dict[str, Any]:
        """Get recommendations for team improvement"""
        async with self._lock:
            if team_id not in self.teams:
                raise ValueError(f"Team {team_id} not found")
            
            team = self.teams[team_id]
            recommendations = []
            
            # Check team size
            if len(team.members) < self.config['min_team_size']:
                recommendations.append({
                    'type': 'scaling',
                    'action': 'add_members',
                    'reason': 'Team below minimum size'
                })
            
            # Check performance
            if team.quality_score < 0.5:
                recommendations.append({
                    'type': 'quality',
                    'action': 'quality_training',
                    'reason': 'Low quality score'
                })
            
            # Check skills
            team_skills = team.get_skills()
            if AgentSkill.TESTING not in team_skills:
                recommendations.append({
                    'type': 'skills',
                    'action': 'add_qa_member',
                    'reason': 'No testing capability'
                })
            
            return {
                'team_id': team_id,
                'team_name': team.name,
                'recommendations': recommendations,
                'current_metrics': {
                    'velocity': team.velocity,
                    'quality': team.quality_score,
                    'efficiency': team.efficiency_score,
                    'collaboration': team.collaboration_score
                }
            }
    
    def get_all_teams(self) -> List[Dict[str, Any]]:
        """Get summary of all active teams"""
        return [
            {
                'team_id': team.team_id,
                'name': team.name,
                'type': team.team_type.value,
                'status': team.status.value,
                'member_count': len(team.members),
                'active_tasks': len(team.active_tasks),
                'completed_tasks': len(team.completed_tasks),
                'velocity': team.velocity
            }
            for team in self.teams.values()
        ]
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down TeamOrchestrator...")
        
        # Cancel all monitors
        for monitor in self._team_monitors.values():
            monitor.cancel()
        
        # Dissolve all teams
        team_ids = list(self.teams.keys())
        for team_id in team_ids:
            await self.dissolve_team(team_id, "System shutdown")
        
        # Shutdown agent pool
        await self.agent_pool.shutdown()
        
        logger.info("TeamOrchestrator shutdown complete")


class TeamFormationError(Exception):
    """Raised when team formation fails"""
    pass


# Example usage and testing
if __name__ == "__main__":
    async def test_team_orchestrator():
        """Test the team orchestrator functionality"""
        # Initialize components
        agent_pool = AgentPool(pool_size=20)
        orchestrator = TeamOrchestrator(agent_pool=agent_pool)
        
        await orchestrator.initialize()
        
        # Create team formation request
        request = TeamFormationRequest(
            request_id="req_001",
            team_name="Customer Success Squad",
            team_type=TeamType.CROSS_FUNCTIONAL,
            mission="Improve customer satisfaction and retention",
            required_skills={
                AgentSkill.CUSTOMER_SERVICE,
                AgentSkill.DATA_ANALYSIS,
                AgentSkill.GENERAL
            },
            team_size=7,
            duration=timedelta(days=30)
        )
        
        # Form team
        try:
            team = await orchestrator.form_team(request)
            print(f"Formed team '{team.name}' with {len(team.members)} members:")
            for member_id, member in team.members.items():
                print(f"  - {member.agent.agent_id}: {member.role.value} ({member.specialization})")
        except TeamFormationError as e:
            print(f"Team formation failed: {e}")
            return
        
        # Simulate task completion
        await orchestrator.assign_task_to_team(team.team_id, "task_001")
        await asyncio.sleep(1)
        await orchestrator.complete_team_task(
            team.team_id, 
            "task_001",
            {'quality': 0.85, 'efficiency': 0.9}
        )
        
        # Get recommendations
        recommendations = await orchestrator.get_team_recommendations(team.team_id)
        print(f"\nTeam Recommendations: {json.dumps(recommendations, indent=2)}")
        
        # Get all teams
        all_teams = orchestrator.get_all_teams()
        print(f"\nAll Teams: {json.dumps(all_teams, indent=2)}")
        
        # Dissolve team
        await orchestrator.dissolve_team(team.team_id, "Test completed")
        
        await orchestrator.shutdown()
    
    # Run test
    asyncio.run(test_team_orchestrator())