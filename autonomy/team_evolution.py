"""
Team Evolution Manager for Autonomous AI Teams

This module implements advanced team evolution strategies including member
reallocation, skill-based reorganization, and adaptive team structures.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from uuid import uuid4
import statistics
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvolutionStrategy(Enum):
    """Evolution strategies for team adaptation"""
    GENETIC = "genetic"                    # Genetic algorithm-inspired evolution
    GRADIENT = "gradient"                  # Gradient-based optimization
    REINFORCEMENT = "reinforcement"        # Reinforcement learning approach
    SWARM = "swarm"                        # Swarm intelligence
    HYBRID = "hybrid"                      # Combination of strategies
    ADAPTIVE = "adaptive"                  # Self-adjusting strategy


class AllocationStrategy(Enum):
    """Strategies for member allocation"""
    SKILL_BASED = "skill_based"           # Match skills to requirements
    PERFORMANCE_BASED = "performance"      # Based on performance metrics
    BALANCED = "balanced"                  # Balance across teams
    SPECIALIZED = "specialized"            # Create specialized teams
    CROSS_FUNCTIONAL = "cross_functional"  # Diverse skill mix
    DYNAMIC = "dynamic"                    # Adapt based on current needs


class TeamStructure(Enum):
    """Types of team structures"""
    HIERARCHICAL = "hierarchical"         # Traditional hierarchy
    FLAT = "flat"                          # Flat structure
    MATRIX = "matrix"                      # Matrix organization
    NETWORK = "network"                    # Network of peers
    HOLACRACY = "holacracy"               # Self-managing circles
    ADAPTIVE = "adaptive"                  # Structure adapts to needs


@dataclass
class SkillRequirement:
    """Represents a skill requirement for a team or project"""
    skill: str
    level: int  # 1-5 (beginner to expert)
    priority: str  # "critical", "high", "medium", "low"
    quantity: int  # Number of members needed with this skill


@dataclass
class TeamProfile:
    """Profile of a team's capabilities and needs"""
    team_id: str
    current_skills: Dict[str, List[str]]  # skill -> list of member IDs
    required_skills: List[SkillRequirement]
    performance_metrics: Dict[str, float]
    structure: TeamStructure
    size: int
    optimal_size: int
    culture_fit: float  # 0-1 score
    
    def skill_gap_analysis(self) -> Dict[str, int]:
        """Analyze gaps between current and required skills"""
        gaps = {}
        for req in self.required_skills:
            current_count = len(self.current_skills.get(req.skill, []))
            gap = req.quantity - current_count
            if gap > 0:
                gaps[req.skill] = gap
        return gaps
    
    def skill_coverage_score(self) -> float:
        """Calculate how well current skills cover requirements"""
        if not self.required_skills:
            return 1.0
        
        total_required = sum(req.quantity for req in self.required_skills)
        total_covered = 0
        
        for req in self.required_skills:
            current_count = len(self.current_skills.get(req.skill, []))
            covered = min(current_count, req.quantity)
            
            # Weight by priority
            weight = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}.get(req.priority, 1.0)
            total_covered += covered * weight
            
        return min(1.0, total_covered / total_required) if total_required > 0 else 0.0


@dataclass
class EvolutionPlan:
    """A plan for team evolution"""
    id: str
    strategy: EvolutionStrategy
    timestamp: datetime
    duration: timedelta
    phases: List[Dict[str, Any]]
    expected_outcome: Dict[str, float]
    risk_assessment: Dict[str, str]
    rollback_plan: Optional[Dict[str, Any]] = None


@dataclass 
class TeamMemberReallocation:
    """Represents a member reallocation between teams"""
    member_id: str
    from_team: str
    to_team: str
    reason: str
    expected_impact: Dict[str, float]
    transition_period: timedelta
    
    
@dataclass
class SkillBasedReorganization:
    """Skill-based team reorganization plan"""
    reorganization_id: str
    timestamp: datetime
    skill_mappings: Dict[str, List[str]]  # skill -> list of team IDs needing it
    member_movements: List[TeamMemberReallocation]
    expected_coverage_improvement: float
    implementation_steps: List[str]


class TeamEvolutionManager:
    """
    Manages the evolution of teams through various strategies including
    genetic algorithms, reinforcement learning, and adaptive structures.
    """
    
    def __init__(self):
        self.teams: Dict[str, TeamProfile] = {}
        self.evolution_history: List[EvolutionPlan] = []
        self.member_pool: Dict[str, Dict[str, Any]] = {}  # member_id -> member info
        self.skill_database: Dict[str, Set[str]] = {}  # skill -> set of member IDs
        self.evolution_metrics: Dict[str, List[float]] = {}
        
        # Evolution parameters
        self.mutation_rate = 0.1
        self.crossover_rate = 0.7
        self.selection_pressure = 0.3
        self.learning_rate = 0.01
        self.exploration_rate = 0.2
        
        # Constraints
        self.max_team_size = 12
        self.min_team_size = 3
        self.max_reallocation_per_cycle = 0.3  # Max 30% of members can move
        
    def register_team(self, team_profile: TeamProfile):
        """Register a team for evolution management"""
        self.teams[team_profile.team_id] = team_profile
        logger.info(f"Registered team {team_profile.team_id} for evolution management")
        
        # Update skill database
        for skill, members in team_profile.current_skills.items():
            if skill not in self.skill_database:
                self.skill_database[skill] = set()
            self.skill_database[skill].update(members)
    
    def register_member(self, member_id: str, member_info: Dict[str, Any]):
        """Register a member in the pool"""
        self.member_pool[member_id] = member_info
        
        # Update skill database
        for skill in member_info.get("skills", []):
            if skill not in self.skill_database:
                self.skill_database[skill] = set()
            self.skill_database[skill].add(member_id)
    
    async def evolve_teams(self, 
                          strategy: EvolutionStrategy = EvolutionStrategy.ADAPTIVE,
                          iterations: int = 10) -> EvolutionPlan:
        """
        Evolve teams using the specified strategy.
        Returns an evolution plan.
        """
        logger.info(f"Starting team evolution with strategy: {strategy.value}")
        
        # Choose evolution method based on strategy
        if strategy == EvolutionStrategy.GENETIC:
            plan = await self._genetic_evolution(iterations)
        elif strategy == EvolutionStrategy.GRADIENT:
            plan = await self._gradient_evolution(iterations)
        elif strategy == EvolutionStrategy.REINFORCEMENT:
            plan = await self._reinforcement_evolution(iterations)
        elif strategy == EvolutionStrategy.SWARM:
            plan = await self._swarm_evolution(iterations)
        elif strategy == EvolutionStrategy.HYBRID:
            plan = await self._hybrid_evolution(iterations)
        else:  # ADAPTIVE
            plan = await self._adaptive_evolution(iterations)
        
        self.evolution_history.append(plan)
        logger.info(f"Evolution plan {plan.id} created")
        
        return plan
    
    async def _genetic_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Evolve teams using genetic algorithm principles.
        Teams are treated as organisms that can mutate and crossover.
        """
        phases = []
        population = self._create_initial_population()
        
        for generation in range(iterations):
            # Evaluate fitness
            fitness_scores = await self._evaluate_population_fitness(population)
            
            # Selection
            selected = self._tournament_selection(population, fitness_scores)
            
            # Crossover
            offspring = await self._crossover_teams(selected)
            
            # Mutation
            mutated = await self._mutate_teams(offspring)
            
            # Replace weakest teams
            population = self._replace_weakest(population, mutated, fitness_scores)
            
            phases.append({
                "generation": generation,
                "best_fitness": max(fitness_scores.values()),
                "average_fitness": statistics.mean(fitness_scores.values()),
                "mutations": len(mutated),
                "crossovers": len(offspring)
            })
        
        # Create evolution plan from best solution
        best_team_config = max(population, key=lambda x: fitness_scores.get(x['id'], 0))
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.GENETIC,
            timestamp=datetime.now(),
            duration=timedelta(days=30),
            phases=phases,
            expected_outcome={"fitness_improvement": 0.3, "skill_coverage": 0.85},
            risk_assessment={"disruption": "medium", "adaptation_time": "2-3 weeks"}
        )
    
    async def _gradient_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Evolve teams using gradient-based optimization.
        Move in the direction of improving performance metrics.
        """
        phases = []
        current_state = self._get_current_state()
        
        for iteration in range(iterations):
            # Calculate gradient
            gradient = await self._calculate_performance_gradient(current_state)
            
            # Take step in gradient direction
            next_state = self._gradient_step(current_state, gradient)
            
            # Evaluate improvement
            improvement = await self._evaluate_state_improvement(current_state, next_state)
            
            phases.append({
                "iteration": iteration,
                "gradient_magnitude": self._calculate_magnitude(gradient),
                "improvement": improvement,
                "learning_rate": self.learning_rate
            })
            
            # Adaptive learning rate
            if improvement > 0:
                self.learning_rate *= 1.1  # Increase if improving
            else:
                self.learning_rate *= 0.5  # Decrease if not improving
            
            current_state = next_state
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.GRADIENT,
            timestamp=datetime.now(),
            duration=timedelta(days=14),
            phases=phases,
            expected_outcome={"performance_gain": 0.25, "convergence": 0.9},
            risk_assessment={"local_optima": "low", "overfitting": "medium"}
        )
    
    async def _reinforcement_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Evolve teams using reinforcement learning principles.
        Learn from actions and their rewards.
        """
        phases = []
        q_table = {}  # State-action value table
        
        for episode in range(iterations):
            state = self._get_current_state_encoded()
            episode_reward = 0
            actions_taken = []
            
            # Episode loop
            for step in range(10):  # Max steps per episode
                # Choose action (epsilon-greedy)
                if statistics.random() < self.exploration_rate:
                    action = self._random_action()
                else:
                    action = self._best_action(q_table, state)
                
                # Take action
                next_state, reward = await self._take_evolution_action(state, action)
                
                # Update Q-value
                self._update_q_value(q_table, state, action, reward, next_state)
                
                episode_reward += reward
                actions_taken.append(action)
                state = next_state
            
            # Decay exploration rate
            self.exploration_rate *= 0.95
            
            phases.append({
                "episode": episode,
                "total_reward": episode_reward,
                "actions": len(actions_taken),
                "exploration_rate": self.exploration_rate,
                "q_table_size": len(q_table)
            })
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.REINFORCEMENT,
            timestamp=datetime.now(),
            duration=timedelta(days=21),
            phases=phases,
            expected_outcome={"learned_policy": 0.8, "reward_maximization": 0.7},
            risk_assessment={"exploration_cost": "high", "convergence_time": "long"}
        )
    
    async def _swarm_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Evolve teams using swarm intelligence.
        Teams act as particles in a swarm, moving towards optimal configurations.
        """
        phases = []
        particles = self._initialize_swarm()
        global_best = None
        global_best_fitness = float('-inf')
        
        for iteration in range(iterations):
            # Evaluate each particle
            for particle in particles:
                fitness = await self._evaluate_particle_fitness(particle)
                
                # Update personal best
                if fitness > particle.get('best_fitness', float('-inf')):
                    particle['best_fitness'] = fitness
                    particle['best_position'] = particle['position'].copy()
                
                # Update global best
                if fitness > global_best_fitness:
                    global_best_fitness = fitness
                    global_best = particle['position'].copy()
            
            # Update velocities and positions
            for particle in particles:
                self._update_particle_velocity(particle, global_best)
                self._update_particle_position(particle)
            
            phases.append({
                "iteration": iteration,
                "global_best_fitness": global_best_fitness,
                "average_fitness": statistics.mean([p.get('best_fitness', 0) for p in particles]),
                "convergence": self._calculate_swarm_convergence(particles)
            })
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.SWARM,
            timestamp=datetime.now(),
            duration=timedelta(days=10),
            phases=phases,
            expected_outcome={"optimization": 0.85, "convergence": 0.95},
            risk_assessment={"premature_convergence": "medium", "diversity_loss": "low"}
        )
    
    async def _hybrid_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Combine multiple evolution strategies for robust optimization.
        """
        phases = []
        
        # Phase 1: Genetic exploration (40% of iterations)
        genetic_iterations = int(iterations * 0.4)
        genetic_phases = []
        for i in range(genetic_iterations):
            phase_result = await self._genetic_evolution_step()
            genetic_phases.append(phase_result)
        
        # Phase 2: Swarm refinement (30% of iterations)
        swarm_iterations = int(iterations * 0.3)
        swarm_phases = []
        for i in range(swarm_iterations):
            phase_result = await self._swarm_evolution_step()
            swarm_phases.append(phase_result)
        
        # Phase 3: Gradient fine-tuning (30% of iterations)
        gradient_iterations = iterations - genetic_iterations - swarm_iterations
        gradient_phases = []
        for i in range(gradient_iterations):
            phase_result = await self._gradient_evolution_step()
            gradient_phases.append(phase_result)
        
        phases = [
            {"phase": "genetic", "results": genetic_phases},
            {"phase": "swarm", "results": swarm_phases},
            {"phase": "gradient", "results": gradient_phases}
        ]
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.HYBRID,
            timestamp=datetime.now(),
            duration=timedelta(days=45),
            phases=phases,
            expected_outcome={"robustness": 0.9, "global_optimization": 0.8},
            risk_assessment={"complexity": "high", "coordination": "challenging"}
        )
    
    async def _adaptive_evolution(self, iterations: int) -> EvolutionPlan:
        """
        Adaptively choose and switch between strategies based on performance.
        """
        phases = []
        strategy_performance = {s: 0.5 for s in EvolutionStrategy if s != EvolutionStrategy.ADAPTIVE}
        current_strategy = EvolutionStrategy.GENETIC
        
        for iteration in range(iterations):
            # Execute current strategy for one step
            if current_strategy == EvolutionStrategy.GENETIC:
                result = await self._genetic_evolution_step()
            elif current_strategy == EvolutionStrategy.GRADIENT:
                result = await self._gradient_evolution_step()
            elif current_strategy == EvolutionStrategy.SWARM:
                result = await self._swarm_evolution_step()
            else:
                result = await self._reinforcement_evolution_step()
            
            # Update strategy performance
            performance = result.get('performance', 0.5)
            strategy_performance[current_strategy] = (
                0.9 * strategy_performance[current_strategy] + 0.1 * performance
            )
            
            # Adaptively choose next strategy
            if iteration % 5 == 0:  # Re-evaluate every 5 iterations
                current_strategy = max(strategy_performance, key=strategy_performance.get)
            
            phases.append({
                "iteration": iteration,
                "strategy": current_strategy.value,
                "performance": performance,
                "strategy_scores": strategy_performance.copy()
            })
        
        return EvolutionPlan(
            id=str(uuid4()),
            strategy=EvolutionStrategy.ADAPTIVE,
            timestamp=datetime.now(),
            duration=timedelta(days=30),
            phases=phases,
            expected_outcome={"adaptability": 0.95, "overall_performance": 0.85},
            risk_assessment={"strategy_switching_cost": "medium", "learning_time": "moderate"}
        )
    
    async def reallocate_members(self, 
                                allocation_strategy: AllocationStrategy = AllocationStrategy.BALANCED) -> List[TeamMemberReallocation]:
        """
        Reallocate members between teams based on the specified strategy.
        """
        logger.info(f"Starting member reallocation with strategy: {allocation_strategy.value}")
        
        if allocation_strategy == AllocationStrategy.SKILL_BASED:
            reallocations = await self._skill_based_reallocation()
        elif allocation_strategy == AllocationStrategy.PERFORMANCE_BASED:
            reallocations = await self._performance_based_reallocation()
        elif allocation_strategy == AllocationStrategy.BALANCED:
            reallocations = await self._balanced_reallocation()
        elif allocation_strategy == AllocationStrategy.SPECIALIZED:
            reallocations = await self._specialized_reallocation()
        elif allocation_strategy == AllocationStrategy.CROSS_FUNCTIONAL:
            reallocations = await self._cross_functional_reallocation()
        else:  # DYNAMIC
            reallocations = await self._dynamic_reallocation()
        
        logger.info(f"Generated {len(reallocations)} reallocations")
        return reallocations
    
    async def _skill_based_reallocation(self) -> List[TeamMemberReallocation]:
        """Reallocate members to match skill requirements"""
        reallocations = []
        
        # Identify skill gaps for each team
        for team_id, team_profile in self.teams.items():
            gaps = team_profile.skill_gap_analysis()
            
            for skill, gap_count in gaps.items():
                # Find members with this skill in other teams
                members_with_skill = self.skill_database.get(skill, set())
                
                for member_id in members_with_skill:
                    if gap_count <= 0:
                        break
                    
                    # Find current team of member
                    current_team = self._find_member_team(member_id)
                    if current_team and current_team != team_id:
                        # Check if current team can spare this member
                        if self._can_spare_member(current_team, member_id, skill):
                            reallocation = TeamMemberReallocation(
                                member_id=member_id,
                                from_team=current_team,
                                to_team=team_id,
                                reason=f"Skill gap: {skill}",
                                expected_impact={"skill_coverage": 0.1, "team_performance": 0.05},
                                transition_period=timedelta(days=7)
                            )
                            reallocations.append(reallocation)
                            gap_count -= 1
        
        return reallocations
    
    async def _performance_based_reallocation(self) -> List[TeamMemberReallocation]:
        """Reallocate based on performance metrics"""
        reallocations = []
        
        # Identify high and low performing teams
        team_performances = {
            tid: team.performance_metrics.get('overall', 0.5) 
            for tid, team in self.teams.items()
        }
        
        sorted_teams = sorted(team_performances.items(), key=lambda x: x[1])
        low_performers = sorted_teams[:len(sorted_teams)//3]
        high_performers = sorted_teams[-len(sorted_teams)//3:]
        
        # Move strong members to struggling teams
        for low_team_id, _ in low_performers:
            for high_team_id, _ in high_performers:
                # Find a strong member to transfer
                strong_member = self._find_transferable_member(high_team_id, "high_performance")
                if strong_member:
                    reallocation = TeamMemberReallocation(
                        member_id=strong_member,
                        from_team=high_team_id,
                        to_team=low_team_id,
                        reason="Performance balancing",
                        expected_impact={"team_balance": 0.15, "mentoring": 0.1},
                        transition_period=timedelta(days=14)
                    )
                    reallocations.append(reallocation)
        
        return reallocations
    
    async def _balanced_reallocation(self) -> List[TeamMemberReallocation]:
        """Create balanced teams with similar sizes and capabilities"""
        reallocations = []
        
        # Calculate average team size
        total_members = sum(team.size for team in self.teams.values())
        avg_size = total_members / len(self.teams) if self.teams else 0
        
        for team_id, team_profile in self.teams.items():
            size_diff = team_profile.size - avg_size
            
            if size_diff > 1:  # Team is too large
                # Find members to move out
                excess_count = int(size_diff)
                for _ in range(min(excess_count, 2)):  # Move max 2 at a time
                    member = self._find_transferable_member(team_id, "excess")
                    if member:
                        # Find smallest team
                        target_team = min(self.teams.items(), key=lambda x: x[1].size)[0]
                        if target_team != team_id:
                            reallocation = TeamMemberReallocation(
                                member_id=member,
                                from_team=team_id,
                                to_team=target_team,
                                reason="Size balancing",
                                expected_impact={"balance": 0.1, "efficiency": 0.05},
                                transition_period=timedelta(days=7)
                            )
                            reallocations.append(reallocation)
        
        return reallocations
    
    async def _specialized_reallocation(self) -> List[TeamMemberReallocation]:
        """Create specialized teams focused on specific skills"""
        reallocations = []
        
        # Define specializations
        specializations = {
            "frontend": ["javascript", "react", "css", "html"],
            "backend": ["python", "java", "database", "api"],
            "devops": ["docker", "kubernetes", "ci/cd", "monitoring"],
            "data": ["ml", "analytics", "statistics", "visualization"]
        }
        
        # Assign teams to specializations
        team_specialization = {}
        for i, (team_id, _) in enumerate(self.teams.items()):
            spec_name = list(specializations.keys())[i % len(specializations)]
            team_specialization[team_id] = spec_name
        
        # Reallocate members to match specializations
        for team_id, spec_name in team_specialization.items():
            required_skills = specializations[spec_name]
            
            for skill in required_skills:
                if skill not in self.teams[team_id].current_skills:
                    # Find member with this skill
                    members_with_skill = self.skill_database.get(skill, set())
                    for member_id in members_with_skill:
                        current_team = self._find_member_team(member_id)
                        if current_team and current_team != team_id:
                            reallocation = TeamMemberReallocation(
                                member_id=member_id,
                                from_team=current_team,
                                to_team=team_id,
                                reason=f"Specialization: {spec_name}",
                                expected_impact={"specialization": 0.2, "expertise": 0.15},
                                transition_period=timedelta(days=10)
                            )
                            reallocations.append(reallocation)
                            break
        
        return reallocations
    
    async def _cross_functional_reallocation(self) -> List[TeamMemberReallocation]:
        """Ensure each team has diverse skills"""
        reallocations = []
        
        # Define essential skills each team should have
        essential_skills = ["development", "testing", "design", "communication"]
        
        for team_id, team_profile in self.teams.items():
            missing_skills = []
            for skill in essential_skills:
                if skill not in team_profile.current_skills:
                    missing_skills.append(skill)
            
            # Find members to fill missing skills
            for skill in missing_skills:
                members_with_skill = self.skill_database.get(skill, set())
                for member_id in members_with_skill:
                    current_team = self._find_member_team(member_id)
                    if current_team and current_team != team_id:
                        # Check if current team has redundancy
                        if self._has_skill_redundancy(current_team, skill):
                            reallocation = TeamMemberReallocation(
                                member_id=member_id,
                                from_team=current_team,
                                to_team=team_id,
                                reason=f"Cross-functional: {skill}",
                                expected_impact={"diversity": 0.15, "collaboration": 0.1},
                                transition_period=timedelta(days=7)
                            )
                            reallocations.append(reallocation)
                            break
        
        return reallocations
    
    async def _dynamic_reallocation(self) -> List[TeamMemberReallocation]:
        """Dynamically adjust based on current needs and metrics"""
        reallocations = []
        
        # Analyze current state
        skill_coverage_scores = {
            tid: team.skill_coverage_score() 
            for tid, team in self.teams.items()
        }
        
        performance_scores = {
            tid: team.performance_metrics.get('overall', 0.5)
            for tid, team in self.teams.items()
        }
        
        # Combine scores to identify needs
        combined_scores = {
            tid: 0.5 * skill_coverage_scores[tid] + 0.5 * performance_scores[tid]
            for tid in self.teams
        }
        
        # Sort teams by need
        sorted_teams = sorted(combined_scores.items(), key=lambda x: x[1])
        
        # Reallocate from strong to weak teams
        for i in range(len(sorted_teams) // 2):
            weak_team = sorted_teams[i][0]
            strong_team = sorted_teams[-(i+1)][0]
            
            # Identify what weak team needs
            weak_profile = self.teams[weak_team]
            gaps = weak_profile.skill_gap_analysis()
            
            if gaps:
                # Find member from strong team with needed skill
                needed_skill = list(gaps.keys())[0]
                member = self._find_member_with_skill(strong_team, needed_skill)
                
                if member:
                    reallocation = TeamMemberReallocation(
                        member_id=member,
                        from_team=strong_team,
                        to_team=weak_team,
                        reason=f"Dynamic adjustment: {needed_skill}",
                        expected_impact={"overall_balance": 0.2, "adaptation": 0.15},
                        transition_period=timedelta(days=5)
                    )
                    reallocations.append(reallocation)
        
        return reallocations
    
    async def reorganize_by_skills(self, 
                                  target_coverage: float = 0.8) -> SkillBasedReorganization:
        """
        Reorganize teams to achieve target skill coverage.
        """
        logger.info(f"Starting skill-based reorganization with target coverage: {target_coverage}")
        
        # Analyze current skill distribution
        skill_mappings = self._analyze_skill_distribution()
        
        # Calculate movements needed
        movements = []
        
        for team_id, team_profile in self.teams.items():
            current_coverage = team_profile.skill_coverage_score()
            
            if current_coverage < target_coverage:
                # Team needs skills
                gaps = team_profile.skill_gap_analysis()
                
                for skill, gap_count in gaps.items():
                    # Find teams with excess of this skill
                    for other_team_id, other_profile in self.teams.items():
                        if other_team_id != team_id:
                            if self._has_skill_redundancy(other_team_id, skill):
                                member = self._find_member_with_skill(other_team_id, skill)
                                if member:
                                    movement = TeamMemberReallocation(
                                        member_id=member,
                                        from_team=other_team_id,
                                        to_team=team_id,
                                        reason=f"Skill reorganization: {skill}",
                                        expected_impact={"skill_coverage": 0.1},
                                        transition_period=timedelta(days=7)
                                    )
                                    movements.append(movement)
                                    gap_count -= 1
                                    if gap_count <= 0:
                                        break
        
        # Calculate expected improvement
        expected_improvement = min(0.3, (target_coverage - 0.5) * 0.5)
        
        reorganization = SkillBasedReorganization(
            reorganization_id=str(uuid4()),
            timestamp=datetime.now(),
            skill_mappings=skill_mappings,
            member_movements=movements,
            expected_coverage_improvement=expected_improvement,
            implementation_steps=self._generate_implementation_steps(movements)
        )
        
        logger.info(f"Skill reorganization plan created with {len(movements)} movements")
        return reorganization
    
    # Helper methods
    
    def _create_initial_population(self) -> List[Dict]:
        """Create initial population for genetic algorithm"""
        return [
            {
                "id": f"config_{i}",
                "team_assignments": self._random_team_assignment(),
                "structure": statistics.choice(list(TeamStructure))
            }
            for i in range(10)
        ]
    
    async def _evaluate_population_fitness(self, population: List[Dict]) -> Dict[str, float]:
        """Evaluate fitness of each configuration in population"""
        fitness_scores = {}
        for config in population:
            # Simulate fitness calculation
            skill_score = statistics.random()
            performance_score = statistics.random()
            balance_score = statistics.random()
            
            fitness = 0.4 * skill_score + 0.4 * performance_score + 0.2 * balance_score
            fitness_scores[config['id']] = fitness
        
        return fitness_scores
    
    def _tournament_selection(self, population: List[Dict], fitness_scores: Dict[str, float]) -> List[Dict]:
        """Select individuals using tournament selection"""
        selected = []
        tournament_size = 3
        
        for _ in range(len(population) // 2):
            tournament = statistics.sample(population, min(tournament_size, len(population)))
            winner = max(tournament, key=lambda x: fitness_scores.get(x['id'], 0))
            selected.append(winner)
        
        return selected
    
    async def _crossover_teams(self, parents: List[Dict]) -> List[Dict]:
        """Create offspring through crossover"""
        offspring = []
        
        for i in range(0, len(parents) - 1, 2):
            if statistics.random() < self.crossover_rate:
                # Perform crossover
                child1 = parents[i].copy()
                child2 = parents[i + 1].copy()
                
                # Swap some team assignments
                crossover_point = len(child1['team_assignments']) // 2
                child1['team_assignments'][:crossover_point], child2['team_assignments'][:crossover_point] = \
                    child2['team_assignments'][:crossover_point], child1['team_assignments'][:crossover_point]
                
                offspring.extend([child1, child2])
            else:
                offspring.extend([parents[i], parents[i + 1]])
        
        return offspring
    
    async def _mutate_teams(self, teams: List[Dict]) -> List[Dict]:
        """Apply mutations to teams"""
        mutated = []
        
        for team_config in teams:
            if statistics.random() < self.mutation_rate:
                # Apply mutation
                mutated_config = team_config.copy()
                # Random change to structure or assignment
                if statistics.random() < 0.5:
                    mutated_config['structure'] = statistics.choice(list(TeamStructure))
                else:
                    # Swap two random members
                    if len(mutated_config['team_assignments']) > 1:
                        i, j = statistics.sample(range(len(mutated_config['team_assignments'])), 2)
                        mutated_config['team_assignments'][i], mutated_config['team_assignments'][j] = \
                            mutated_config['team_assignments'][j], mutated_config['team_assignments'][i]
                
                mutated.append(mutated_config)
            else:
                mutated.append(team_config)
        
        return mutated
    
    def _replace_weakest(self, population: List[Dict], new_individuals: List[Dict], 
                        fitness_scores: Dict[str, float]) -> List[Dict]:
        """Replace weakest individuals with new ones"""
        # Sort by fitness
        sorted_pop = sorted(population, key=lambda x: fitness_scores.get(x['id'], 0), reverse=True)
        
        # Keep best and replace worst
        keep_count = len(population) - len(new_individuals)
        return sorted_pop[:keep_count] + new_individuals
    
    def _find_member_team(self, member_id: str) -> Optional[str]:
        """Find which team a member belongs to"""
        for team_id, team_profile in self.teams.items():
            for skill_members in team_profile.current_skills.values():
                if member_id in skill_members:
                    return team_id
        return None
    
    def _can_spare_member(self, team_id: str, member_id: str, skill: str) -> bool:
        """Check if team can spare a member with given skill"""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        # Check if team has redundancy for this skill
        skill_members = team.current_skills.get(skill, [])
        return len(skill_members) > 1  # Can spare if more than one member has the skill
    
    def _has_skill_redundancy(self, team_id: str, skill: str) -> bool:
        """Check if team has redundancy for a skill"""
        team = self.teams.get(team_id)
        if not team:
            return False
        
        skill_members = team.current_skills.get(skill, [])
        return len(skill_members) > 2  # Redundant if more than 2 members have it
    
    def _find_transferable_member(self, team_id: str, criteria: str) -> Optional[str]:
        """Find a member that can be transferred from team"""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        # Find members (simplified - just return first available)
        for skill_members in team.current_skills.values():
            if skill_members:
                return skill_members[0]
        
        return None
    
    def _find_member_with_skill(self, team_id: str, skill: str) -> Optional[str]:
        """Find a member in team with specific skill"""
        team = self.teams.get(team_id)
        if not team:
            return None
        
        skill_members = team.current_skills.get(skill, [])
        return skill_members[0] if skill_members else None
    
    def _analyze_skill_distribution(self) -> Dict[str, List[str]]:
        """Analyze how skills are distributed across teams"""
        skill_distribution = {}
        
        for skill, members in self.skill_database.items():
            teams_with_skill = []
            for member in members:
                team = self._find_member_team(member)
                if team and team not in teams_with_skill:
                    teams_with_skill.append(team)
            skill_distribution[skill] = teams_with_skill
        
        return skill_distribution
    
    def _generate_implementation_steps(self, movements: List[TeamMemberReallocation]) -> List[str]:
        """Generate implementation steps for reorganization"""
        steps = []
        
        # Group movements by phase
        immediate = [m for m in movements if m.transition_period.days <= 7]
        short_term = [m for m in movements if 7 < m.transition_period.days <= 14]
        long_term = [m for m in movements if m.transition_period.days > 14]
        
        if immediate:
            steps.append(f"Phase 1 (Immediate): Transfer {len(immediate)} members within 7 days")
        if short_term:
            steps.append(f"Phase 2 (Short-term): Transfer {len(short_term)} members within 14 days")
        if long_term:
            steps.append(f"Phase 3 (Long-term): Transfer {len(long_term)} members over 14+ days")
        
        steps.extend([
            "Conduct knowledge transfer sessions",
            "Update team documentation and access",
            "Schedule onboarding meetings",
            "Monitor integration progress",
            "Gather feedback and adjust as needed"
        ])
        
        return steps
    
    def _random_team_assignment(self) -> List[Dict]:
        """Generate random team assignment for genetic algorithm"""
        assignment = []
        for member_id in self.member_pool.keys():
            assignment.append({
                "member": member_id,
                "team": statistics.choice(list(self.teams.keys())) if self.teams else "team_1"
            })
        return assignment
    
    def _get_current_state(self) -> Dict:
        """Get current state of all teams"""
        return {
            "teams": {tid: asdict(team) for tid, team in self.teams.items()},
            "metrics": self.evolution_metrics
        }
    
    def _get_current_state_encoded(self) -> str:
        """Get encoded state for reinforcement learning"""
        # Simple encoding for demo purposes
        state_values = []
        for team in self.teams.values():
            state_values.append(team.skill_coverage_score())
            state_values.append(team.performance_metrics.get('overall', 0.5))
        return "_".join([f"{v:.2f}" for v in state_values])
    
    async def _calculate_performance_gradient(self, state: Dict) -> Dict:
        """Calculate gradient of performance with respect to state"""
        # Simplified gradient calculation
        gradient = {}
        for team_id in state['teams']:
            gradient[team_id] = {
                "skill_gradient": statistics.random() - 0.5,
                "size_gradient": statistics.random() - 0.5,
                "structure_gradient": statistics.random() - 0.5
            }
        return gradient
    
    def _gradient_step(self, current_state: Dict, gradient: Dict) -> Dict:
        """Take a step in gradient direction"""
        # Simplified gradient step
        next_state = current_state.copy()
        # Apply gradients (simplified)
        return next_state
    
    async def _evaluate_state_improvement(self, old_state: Dict, new_state: Dict) -> float:
        """Evaluate improvement between states"""
        # Simplified evaluation
        return statistics.random() - 0.3
    
    def _calculate_magnitude(self, gradient: Dict) -> float:
        """Calculate magnitude of gradient"""
        total = 0
        for team_gradients in gradient.values():
            for value in team_gradients.values():
                total += value ** 2
        return math.sqrt(total)
    
    def _random_action(self) -> str:
        """Generate random action for RL"""
        actions = ["move_member", "change_structure", "merge_teams", "split_team", "no_op"]
        return statistics.choice(actions)
    
    def _best_action(self, q_table: Dict, state: str) -> str:
        """Get best action from Q-table"""
        state_actions = q_table.get(state, {})
        if not state_actions:
            return self._random_action()
        return max(state_actions, key=state_actions.get)
    
    async def _take_evolution_action(self, state: str, action: str) -> Tuple[str, float]:
        """Execute evolution action and return new state and reward"""
        # Simplified action execution
        reward = statistics.random() - 0.5
        next_state = state + "_" + action[:3]  # Simple state transition
        return next_state, reward
    
    def _update_q_value(self, q_table: Dict, state: str, action: str, 
                       reward: float, next_state: str):
        """Update Q-value using Q-learning formula"""
        if state not in q_table:
            q_table[state] = {}
        
        if action not in q_table[state]:
            q_table[state][action] = 0
        
        # Q-learning update
        alpha = 0.1  # Learning rate
        gamma = 0.9  # Discount factor
        
        next_max = max(q_table.get(next_state, {}).values()) if next_state in q_table else 0
        q_table[state][action] = (1 - alpha) * q_table[state][action] + \
                                 alpha * (reward + gamma * next_max)
    
    def _initialize_swarm(self) -> List[Dict]:
        """Initialize particle swarm"""
        particles = []
        for i in range(20):  # 20 particles
            particles.append({
                "id": f"particle_{i}",
                "position": [statistics.random() for _ in range(10)],
                "velocity": [statistics.random() - 0.5 for _ in range(10)],
                "best_position": None,
                "best_fitness": float('-inf')
            })
        return particles
    
    async def _evaluate_particle_fitness(self, particle: Dict) -> float:
        """Evaluate fitness of a particle position"""
        # Simplified fitness based on position
        return sum(particle['position']) / len(particle['position'])
    
    def _update_particle_velocity(self, particle: Dict, global_best: List[float]):
        """Update particle velocity"""
        w = 0.7  # Inertia weight
        c1 = 1.5  # Personal best weight
        c2 = 1.5  # Global best weight
        
        for i in range(len(particle['velocity'])):
            r1 = statistics.random()
            r2 = statistics.random()
            
            personal_component = 0
            if particle['best_position']:
                personal_component = c1 * r1 * (particle['best_position'][i] - particle['position'][i])
            
            global_component = 0
            if global_best:
                global_component = c2 * r2 * (global_best[i] - particle['position'][i])
            
            particle['velocity'][i] = w * particle['velocity'][i] + personal_component + global_component
    
    def _update_particle_position(self, particle: Dict):
        """Update particle position based on velocity"""
        for i in range(len(particle['position'])):
            particle['position'][i] += particle['velocity'][i]
            # Bound position to [0, 1]
            particle['position'][i] = max(0, min(1, particle['position'][i]))
    
    def _calculate_swarm_convergence(self, particles: List[Dict]) -> float:
        """Calculate convergence of swarm"""
        if not particles:
            return 0
        
        # Calculate variance of positions
        positions = [p['position'] for p in particles]
        variances = []
        
        for dim in range(len(positions[0])):
            dim_values = [p[dim] for p in positions]
            if len(dim_values) > 1:
                variances.append(statistics.variance(dim_values))
        
        # Low variance means high convergence
        avg_variance = statistics.mean(variances) if variances else 0
        return 1 - min(1, avg_variance)
    
    async def _genetic_evolution_step(self) -> Dict:
        """Single step of genetic evolution"""
        # Simplified step
        return {"performance": statistics.random(), "type": "genetic"}
    
    async def _gradient_evolution_step(self) -> Dict:
        """Single step of gradient evolution"""
        return {"performance": statistics.random(), "type": "gradient"}
    
    async def _swarm_evolution_step(self) -> Dict:
        """Single step of swarm evolution"""
        return {"performance": statistics.random(), "type": "swarm"}
    
    async def _reinforcement_evolution_step(self) -> Dict:
        """Single step of reinforcement learning evolution"""
        return {"performance": statistics.random(), "type": "reinforcement"}


# Demonstration function
async def demonstrate_evolution():
    """Demonstrate team evolution capabilities"""
    print("=== Team Evolution Manager Demonstration ===\n")
    
    # Create evolution manager
    manager = TeamEvolutionManager()
    
    # Register sample teams
    team1 = TeamProfile(
        team_id="team-alpha",
        current_skills={
            "python": ["m1", "m2"],
            "javascript": ["m3"],
            "testing": ["m4"]
        },
        required_skills=[
            SkillRequirement("python", 3, "high", 2),
            SkillRequirement("devops", 3, "critical", 1),
            SkillRequirement("testing", 2, "medium", 2)
        ],
        performance_metrics={"overall": 0.65, "velocity": 0.7, "quality": 0.6},
        structure=TeamStructure.FLAT,
        size=4,
        optimal_size=6,
        culture_fit=0.75
    )
    
    team2 = TeamProfile(
        team_id="team-beta",
        current_skills={
            "java": ["m5", "m6", "m7"],
            "devops": ["m8", "m9"],
            "database": ["m10"]
        },
        required_skills=[
            SkillRequirement("java", 3, "high", 3),
            SkillRequirement("testing", 3, "critical", 2),
            SkillRequirement("frontend", 2, "medium", 1)
        ],
        performance_metrics={"overall": 0.8, "velocity": 0.85, "quality": 0.75},
        structure=TeamStructure.HIERARCHICAL,
        size=6,
        optimal_size=5,
        culture_fit=0.85
    )
    
    manager.register_team(team1)
    manager.register_team(team2)
    
    # Register members
    for i in range(1, 11):
        manager.register_member(f"m{i}", {
            "name": f"Member{i}",
            "skills": statistics.sample(["python", "java", "javascript", "testing", "devops", "database"], 2),
            "performance": 0.5 + statistics.random() * 0.5
        })
    
    print("1. Registered 2 teams and 10 members\n")
    
    # Evolve teams
    print("2. Evolving teams with adaptive strategy...")
    evolution_plan = await manager.evolve_teams(EvolutionStrategy.ADAPTIVE, iterations=5)
    print(f"   Evolution plan ID: {evolution_plan.id}")
    print(f"   Strategy: {evolution_plan.strategy.value}")
    print(f"   Duration: {evolution_plan.duration.days} days")
    print(f"   Expected outcome: {evolution_plan.expected_outcome}\n")
    
    # Reallocate members
    print("3. Reallocating members with skill-based strategy...")
    reallocations = await manager.reallocate_members(AllocationStrategy.SKILL_BASED)
    print(f"   Generated {len(reallocations)} reallocations:")
    for realloc in reallocations[:3]:  # Show first 3
        print(f"   - Move {realloc.member_id} from {realloc.from_team} to {realloc.to_team}")
        print(f"     Reason: {realloc.reason}")
    print()
    
    # Skill-based reorganization
    print("4. Performing skill-based reorganization...")
    reorganization = await manager.reorganize_by_skills(target_coverage=0.8)
    print(f"   Reorganization ID: {reorganization.reorganization_id}")
    print(f"   Member movements: {len(reorganization.member_movements)}")
    print(f"   Expected improvement: {reorganization.expected_coverage_improvement:.1%}")
    print(f"   Implementation steps:")
    for step in reorganization.implementation_steps[:3]:
        print(f"   - {step}")
    print()
    
    print("=== Demonstration Complete ===")


if __name__ == "__main__":
    # For demonstration purposes
    import random
    random.seed(42)
    statistics.random = random.random
    statistics.choice = random.choice
    statistics.sample = random.sample
    statistics.variance = lambda x: sum((i - sum(x)/len(x))**2 for i in x) / len(x) if x else 0
    
    asyncio.run(demonstrate_evolution())