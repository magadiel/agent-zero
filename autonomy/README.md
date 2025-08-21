# Autonomy Module for Agent-Zero

## Overview

The Autonomy module provides advanced self-organization capabilities for AI agent teams, enabling them to autonomously assess their performance, propose reorganizations, vote on changes, and execute approved modifications to their structure.

## Key Features

### 1. Self-Organization (`self_organization.py`)

#### Core Capabilities
- **Performance Self-Assessment**: Teams evaluate their own performance across multiple metrics
- **Reorganization Proposals**: Automatic generation of improvement proposals based on assessment
- **Democratic Voting**: Team members vote on proposed changes with weighted voting
- **Autonomous Execution**: Approved changes are executed automatically

#### Reorganization Types
- `MEMBER_SWAP`: Exchange members between teams
- `ROLE_CHANGE`: Reassign member roles
- `TEAM_MERGE`: Combine two teams
- `TEAM_SPLIT`: Divide a large team
- `SIZE_ADJUSTMENT`: Add or remove members
- `SKILL_REBALANCE`: Redistribute skills across team
- `LEADERSHIP_CHANGE`: Change team leadership
- `STRUCTURE_CHANGE`: Modify team structure

#### Performance Metrics
- Velocity
- Quality
- Efficiency
- Collaboration
- Innovation
- Reliability
- Adaptability
- Communication

### 2. Team Evolution (`team_evolution.py`)

#### Evolution Strategies
- **Genetic Algorithm**: Teams evolve through mutation and crossover
- **Gradient Optimization**: Move toward improved performance metrics
- **Reinforcement Learning**: Learn from actions and rewards
- **Swarm Intelligence**: Teams act as particles seeking optimal configurations
- **Hybrid Approach**: Combine multiple strategies
- **Adaptive Strategy**: Dynamically switch between strategies

#### Allocation Strategies
- **Skill-Based**: Match member skills to team requirements
- **Performance-Based**: Balance high and low performers
- **Balanced**: Equal team sizes and capabilities
- **Specialized**: Create focused expert teams
- **Cross-Functional**: Ensure diverse skills in each team
- **Dynamic**: Adapt based on current needs

## Usage Examples

### Creating a Self-Organizing Team

```python
from autonomy.self_organization import SelfOrganizingTeam, TeamMember

# Create team members
members = [
    TeamMember(
        id="m1",
        name="Alice",
        role="leader",
        skills=["python", "architecture"],
        performance_history=[0.8, 0.85, 0.9],
        voting_weight=2.0,
        can_veto=True
    ),
    TeamMember(
        id="m2",
        name="Bob",
        role="developer",
        skills=["javascript", "react"],
        performance_history=[0.7, 0.75, 0.7]
    )
]

# Create self-organizing team
team = SelfOrganizingTeam(
    team_id="team-001",
    name="Alpha Team",
    members=members
)

# Perform self-assessment
assessment = await team.assess_performance()
print(f"Overall score: {assessment.overall_score}")

# Generate reorganization proposal if needed
if assessment.needs_reorganization():
    proposal = await team.generate_reorganization_proposal(assessment)
    
    # Vote on proposal
    voting_result = await team.vote_on_proposal(proposal.id)
    
    # Execute if approved
    if voting_result.passed:
        success = await team.execute_reorganization(proposal.id)
```

### Evolving Teams

```python
from autonomy.team_evolution import TeamEvolutionManager, TeamProfile, EvolutionStrategy

# Create evolution manager
manager = TeamEvolutionManager()

# Register teams
team_profile = TeamProfile(
    team_id="team-alpha",
    current_skills={"python": ["m1", "m2"], "testing": ["m3"]},
    required_skills=[
        SkillRequirement("python", 3, "high", 2),
        SkillRequirement("devops", 2, "critical", 1)
    ],
    performance_metrics={"overall": 0.7},
    structure=TeamStructure.FLAT,
    size=3,
    optimal_size=5,
    culture_fit=0.8
)
manager.register_team(team_profile)

# Evolve teams using adaptive strategy
evolution_plan = await manager.evolve_teams(
    strategy=EvolutionStrategy.ADAPTIVE,
    iterations=10
)

# Reallocate members based on skills
reallocations = await manager.reallocate_members(
    allocation_strategy=AllocationStrategy.SKILL_BASED
)

# Reorganize to improve skill coverage
reorganization = await manager.reorganize_by_skills(target_coverage=0.8)
```

## Integration with Agent-Zero

### 1. Enhance Agent Teams

```python
# In agent.py or team management code
from autonomy.self_organization import SelfOrganizingTeam

class AgentZeroTeam:
    def __init__(self, agents):
        # Convert agents to team members
        members = [self._agent_to_member(agent) for agent in agents]
        
        # Create self-organizing team
        self.self_org_team = SelfOrganizingTeam(
            team_id=self.id,
            name=self.name,
            members=members
        )
    
    async def self_organize(self):
        """Trigger self-organization process"""
        assessment = await self.self_org_team.assess_performance()
        
        if assessment.needs_reorganization():
            proposal = await self.self_org_team.generate_reorganization_proposal(assessment)
            result = await self.self_org_team.vote_on_proposal(proposal.id)
            
            if result.passed:
                await self.self_org_team.execute_reorganization(proposal.id)
```

### 2. Add to Workflow Engine

```python
# In coordination/workflow_engine.py
from autonomy.team_evolution import TeamEvolutionManager

class WorkflowEngine:
    def __init__(self):
        self.evolution_manager = TeamEvolutionManager()
    
    async def optimize_team_allocation(self, workflow):
        """Optimize team allocation for workflow"""
        # Register current teams
        for team in self.get_workflow_teams(workflow):
            team_profile = self._create_team_profile(team)
            self.evolution_manager.register_team(team_profile)
        
        # Evolve and reallocate
        evolution_plan = await self.evolution_manager.evolve_teams()
        reallocations = await self.evolution_manager.reallocate_members()
        
        # Apply reallocations
        for realloc in reallocations:
            await self._apply_reallocation(realloc)
```

### 3. Create Autonomy Tool

```python
# In python/tools/team_autonomy.py
from python.helpers.tool import Tool
from autonomy.self_organization import SelfOrganizingTeam

class TeamAutonomyTool(Tool):
    async def execute(self, **kwargs):
        """Enable team self-organization"""
        team_id = kwargs.get("team_id")
        action = kwargs.get("action", "assess")
        
        team = self.get_team(team_id)
        
        if action == "assess":
            return await team.assess_performance()
        elif action == "reorganize":
            return await team.trigger_reorganization()
        elif action == "evolve":
            return await team.evolve_structure()
```

## Configuration

### Performance Thresholds

```python
team.performance_threshold = 0.7  # Trigger reorganization below this
team.approval_threshold = 0.66    # 2/3 majority for approval
team.min_votes_required = 0.75    # 75% participation required
```

### Evolution Parameters

```python
manager.mutation_rate = 0.1        # Genetic algorithm mutation rate
manager.crossover_rate = 0.7       # Genetic algorithm crossover rate
manager.learning_rate = 0.01       # Gradient descent learning rate
manager.exploration_rate = 0.2     # RL exploration vs exploitation
```

### Team Constraints

```python
team.max_size = 12                 # Maximum team size
team.min_size = 3                  # Minimum team size
team.ideal_size = 7                # Optimal team size
```

## Testing

Run the test suite:

```bash
python -m pytest autonomy/test_autonomy.py -v
```

Or run the standalone test:

```bash
python autonomy/test_autonomy.py
```

## Architecture

### Class Hierarchy

```
SelfOrganizingTeam
├── TeamMember
├── PerformanceAssessment
├── ReorganizationProposal
└── VotingResult

TeamEvolutionManager
├── TeamProfile
├── SkillRequirement
├── EvolutionPlan
├── TeamMemberReallocation
└── SkillBasedReorganization
```

### Data Flow

1. **Assessment Phase**
   - Collect performance metrics
   - Evaluate team and individual performance
   - Identify strengths and weaknesses

2. **Proposal Phase**
   - Analyze assessment results
   - Generate reorganization proposals
   - Calculate expected benefits and risks

3. **Voting Phase**
   - Distribute proposals to team members
   - Collect and weight votes
   - Determine approval/rejection

4. **Execution Phase**
   - Implement approved changes
   - Update team structure
   - Track execution results

5. **Evolution Phase**
   - Apply evolution strategies
   - Optimize team configurations
   - Learn from outcomes

## Best Practices

1. **Regular Assessments**: Schedule periodic self-assessments (e.g., after each sprint)
2. **Gradual Changes**: Implement reorganizations incrementally to minimize disruption
3. **Monitor Impact**: Track metrics before and after reorganizations
4. **Preserve Knowledge**: Ensure knowledge transfer during member reallocations
5. **Respect Constraints**: Honor team size limits and skill requirements
6. **Democratic Process**: Ensure fair voting and consider veto rights carefully
7. **Rollback Plans**: Always have a plan to revert changes if needed

## Future Enhancements

1. **Machine Learning Integration**: Use historical data to predict reorganization success
2. **Multi-Objective Optimization**: Balance multiple competing objectives
3. **Cultural Fit Assessment**: Consider team dynamics and personality compatibility
4. **Continuous Learning**: Update strategies based on reorganization outcomes
5. **Cross-Team Collaboration**: Optimize for inter-team dependencies
6. **Automated Onboarding**: Streamline member transitions between teams

## License

This module is part of the Agent-Zero project and follows the same license terms.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Code follows the existing style
- Documentation is updated
- New features include tests

## Support

For issues or questions, please refer to the main Agent-Zero documentation or create an issue in the project repository.