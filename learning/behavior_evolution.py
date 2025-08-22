"""
Behavior Evolution System for Agent Adaptation

This module implements behavior evolution capabilities that:
- Track agent behavior performance
- Identify successful behavior patterns
- Evolve agent behaviors based on learnings
- Update workflow patterns
- Improve templates from experience
"""

import asyncio
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, Counter
import yaml
from pathlib import Path
import random
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BehaviorType(Enum):
    """Types of agent behaviors"""
    DECISION_MAKING = "decision_making"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    COLLABORATION = "collaboration"
    LEARNING = "learning"
    TASK_EXECUTION = "task_execution"
    ERROR_HANDLING = "error_handling"
    RESOURCE_MANAGEMENT = "resource_management"


class EvolutionStrategy(Enum):
    """Strategies for behavior evolution"""
    REINFORCEMENT = "reinforcement"  # Strengthen successful behaviors
    MUTATION = "mutation"  # Random small changes
    CROSSOVER = "crossover"  # Combine successful behaviors
    PRUNING = "pruning"  # Remove unsuccessful behaviors
    ADAPTATION = "adaptation"  # Adjust to environment
    INNOVATION = "innovation"  # Create new behaviors


class PerformanceMetric(Enum):
    """Metrics for measuring behavior performance"""
    SUCCESS_RATE = "success_rate"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    SPEED = "speed"
    RESOURCE_USAGE = "resource_usage"
    COLLABORATION_SCORE = "collaboration_score"
    INNOVATION_INDEX = "innovation_index"
    ERROR_RATE = "error_rate"


@dataclass
class Behavior:
    """Represents an agent behavior"""
    id: str
    agent_id: str
    type: BehaviorType
    name: str
    description: str
    parameters: Dict[str, Any]
    performance_metrics: Dict[str, float]
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    version: int = 1
    parent_behavior_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Default for new behaviors
        return self.success_count / total
    
    @property
    def fitness_score(self) -> float:
        """Calculate overall fitness score"""
        weights = {
            'success_rate': 0.4,
            'efficiency': 0.3,
            'quality': 0.2,
            'usage': 0.1
        }
        
        score = 0.0
        score += weights['success_rate'] * self.success_rate
        score += weights['efficiency'] * self.performance_metrics.get('efficiency', 0.5)
        score += weights['quality'] * self.performance_metrics.get('quality', 0.5)
        
        # Normalize usage (sigmoid function)
        usage_score = 1 / (1 + pow(2.71828, -0.01 * self.usage_count))
        score += weights['usage'] * usage_score
        
        return min(1.0, max(0.0, score))


@dataclass
class WorkflowPattern:
    """Represents a workflow pattern"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    success_rate: float
    avg_duration: float
    resource_usage: Dict[str, float]
    applicable_scenarios: List[str]
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_optimized: Optional[datetime] = None
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplateEvolution:
    """Represents an evolution of a template"""
    id: str
    template_id: str
    template_name: str
    changes: Dict[str, Any]
    reason: str
    expected_improvement: float
    actual_improvement: Optional[float] = None
    status: str = "proposed"  # proposed, testing, applied, rejected
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None


@dataclass
class EvolutionGeneration:
    """Represents a generation in the evolution process"""
    generation_number: int
    timestamp: datetime
    population_size: int
    avg_fitness: float
    best_fitness: float
    worst_fitness: float
    mutations: int
    crossovers: int
    innovations: int
    pruned: int


class BehaviorEvolution:
    """
    Main class for behavior evolution management
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize behavior evolution system"""
        self.config = self._load_config(config_path)
        
        # Storage
        self.behaviors: Dict[str, Behavior] = {}
        self.workflow_patterns: Dict[str, WorkflowPattern] = {}
        self.template_evolutions: Dict[str, TemplateEvolution] = {}
        self.generations: List[EvolutionGeneration] = []
        
        # Evolution parameters
        self.evolution_params = {
            'mutation_rate': 0.1,
            'crossover_rate': 0.3,
            'innovation_rate': 0.05,
            'pruning_threshold': 0.3,
            'elite_percentage': 0.2,
            'population_size': 100
        }
        
        # Performance tracking
        self.performance_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Current generation
        self.current_generation = 0
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'evolution_interval': 'daily',
            'min_data_points': 10,
            'fitness_threshold': 0.7,
            'max_generations': 1000,
            'convergence_threshold': 0.01
        }
    
    async def track_behavior(self,
                            agent_id: str,
                            behavior_type: BehaviorType,
                            parameters: Dict[str, Any],
                            outcome: str,
                            metrics: Dict[str, float]) -> Behavior:
        """
        Track agent behavior and its performance
        """
        # Generate behavior ID
        behavior_key = f"{agent_id}_{behavior_type.value}_{json.dumps(parameters, sort_keys=True)}"
        behavior_id = hashlib.md5(behavior_key.encode()).hexdigest()[:12]
        
        # Get or create behavior
        if behavior_id in self.behaviors:
            behavior = self.behaviors[behavior_id]
        else:
            behavior = Behavior(
                id=behavior_id,
                agent_id=agent_id,
                type=behavior_type,
                name=f"{behavior_type.value}_{behavior_id[:6]}",
                description=f"Behavior pattern for {behavior_type.value}",
                parameters=parameters,
                performance_metrics={}
            )
            self.behaviors[behavior_id] = behavior
        
        # Update behavior statistics
        behavior.usage_count += 1
        behavior.last_used = datetime.now()
        
        if outcome == 'success':
            behavior.success_count += 1
        else:
            behavior.failure_count += 1
        
        # Update performance metrics
        for metric_name, value in metrics.items():
            if metric_name in behavior.performance_metrics:
                # Moving average
                old_value = behavior.performance_metrics[metric_name]
                behavior.performance_metrics[metric_name] = 0.7 * old_value + 0.3 * value
            else:
                behavior.performance_metrics[metric_name] = value
        
        # Track performance history
        self.performance_history[behavior_id].append(
            (datetime.now(), behavior.fitness_score)
        )
        
        return behavior
    
    async def evolve_behaviors(self,
                              agent_id: Optional[str] = None,
                              strategy: Optional[EvolutionStrategy] = None) -> List[Behavior]:
        """
        Evolve behaviors for an agent or all agents
        """
        # Select behaviors to evolve
        if agent_id:
            population = [b for b in self.behaviors.values() if b.agent_id == agent_id]
        else:
            population = list(self.behaviors.values())
        
        if len(population) < self.config['min_data_points']:
            return []  # Not enough data to evolve
        
        # Start new generation
        self.current_generation += 1
        generation_start = datetime.now()
        
        # Apply evolution strategy
        if strategy is None:
            # Use mixed strategy
            evolved = await self._apply_mixed_evolution(population)
        elif strategy == EvolutionStrategy.REINFORCEMENT:
            evolved = await self._apply_reinforcement(population)
        elif strategy == EvolutionStrategy.MUTATION:
            evolved = await self._apply_mutation(population)
        elif strategy == EvolutionStrategy.CROSSOVER:
            evolved = await self._apply_crossover(population)
        elif strategy == EvolutionStrategy.PRUNING:
            evolved = await self._apply_pruning(population)
        elif strategy == EvolutionStrategy.ADAPTATION:
            evolved = await self._apply_adaptation(population)
        elif strategy == EvolutionStrategy.INNOVATION:
            evolved = await self._apply_innovation(population)
        else:
            evolved = []
        
        # Record generation statistics
        if population:
            fitness_scores = [b.fitness_score for b in population]
            generation = EvolutionGeneration(
                generation_number=self.current_generation,
                timestamp=generation_start,
                population_size=len(population),
                avg_fitness=sum(fitness_scores) / len(fitness_scores),
                best_fitness=max(fitness_scores),
                worst_fitness=min(fitness_scores),
                mutations=sum(1 for b in evolved if b.parent_behavior_id),
                crossovers=0,  # Track in crossover method
                innovations=sum(1 for b in evolved if not b.parent_behavior_id),
                pruned=len(population) - len(evolved)
            )
            self.generations.append(generation)
        
        return evolved
    
    async def _apply_mixed_evolution(self, population: List[Behavior]) -> List[Behavior]:
        """Apply mixed evolution strategies"""
        evolved = []
        
        # Sort by fitness
        population.sort(key=lambda b: b.fitness_score, reverse=True)
        
        # Keep elite
        elite_count = int(len(population) * self.evolution_params['elite_percentage'])
        evolved.extend(population[:elite_count])
        
        # Apply different strategies to rest
        remaining = population[elite_count:]
        
        # Mutate some
        mutation_count = int(len(remaining) * self.evolution_params['mutation_rate'])
        for behavior in random.sample(remaining, min(mutation_count, len(remaining))):
            mutated = await self._mutate_behavior(behavior)
            if mutated:
                evolved.append(mutated)
        
        # Crossover some
        crossover_count = int(len(remaining) * self.evolution_params['crossover_rate'])
        for _ in range(crossover_count // 2):
            if len(remaining) >= 2:
                parent1, parent2 = random.sample(remaining, 2)
                child = await self._crossover_behaviors(parent1, parent2)
                if child:
                    evolved.append(child)
        
        # Innovate occasionally
        if random.random() < self.evolution_params['innovation_rate']:
            innovation = await self._create_innovation(population[0].agent_id if population else None)
            if innovation:
                evolved.append(innovation)
        
        # Prune poor performers
        evolved = [b for b in evolved if b.fitness_score > self.evolution_params['pruning_threshold']]
        
        return evolved
    
    async def _apply_reinforcement(self, population: List[Behavior]) -> List[Behavior]:
        """Reinforce successful behaviors"""
        reinforced = []
        
        for behavior in population:
            if behavior.success_rate > 0.7:
                # Strengthen parameters
                reinforced_behavior = await self._reinforce_behavior(behavior)
                reinforced.append(reinforced_behavior)
            else:
                reinforced.append(behavior)
        
        return reinforced
    
    async def _reinforce_behavior(self, behavior: Behavior) -> Behavior:
        """Reinforce a successful behavior"""
        # Create reinforced version
        reinforced = Behavior(
            id=hashlib.md5(f"{behavior.id}_reinforced_{datetime.now()}".encode()).hexdigest()[:12],
            agent_id=behavior.agent_id,
            type=behavior.type,
            name=f"{behavior.name}_reinforced",
            description=f"Reinforced version of {behavior.description}",
            parameters=behavior.parameters.copy(),
            performance_metrics=behavior.performance_metrics.copy(),
            parent_behavior_id=behavior.id,
            version=behavior.version + 1
        )
        
        # Strengthen successful parameters
        for param, value in reinforced.parameters.items():
            if isinstance(value, (int, float)):
                # Increase numeric parameters slightly
                reinforced.parameters[param] = value * 1.1
        
        self.behaviors[reinforced.id] = reinforced
        return reinforced
    
    async def _apply_mutation(self, population: List[Behavior]) -> List[Behavior]:
        """Apply random mutations to behaviors"""
        mutated_population = []
        
        for behavior in population:
            if random.random() < self.evolution_params['mutation_rate']:
                mutated = await self._mutate_behavior(behavior)
                if mutated:
                    mutated_population.append(mutated)
            else:
                mutated_population.append(behavior)
        
        return mutated_population
    
    async def _mutate_behavior(self, behavior: Behavior) -> Optional[Behavior]:
        """Mutate a behavior"""
        mutated = Behavior(
            id=hashlib.md5(f"{behavior.id}_mutated_{datetime.now()}".encode()).hexdigest()[:12],
            agent_id=behavior.agent_id,
            type=behavior.type,
            name=f"{behavior.name}_mut",
            description=f"Mutated version of {behavior.description}",
            parameters=behavior.parameters.copy(),
            performance_metrics={},
            parent_behavior_id=behavior.id,
            version=behavior.version + 1
        )
        
        # Mutate parameters
        for param, value in mutated.parameters.items():
            if isinstance(value, bool):
                # Flip boolean with small probability
                if random.random() < 0.1:
                    mutated.parameters[param] = not value
            elif isinstance(value, (int, float)):
                # Add gaussian noise
                noise = random.gauss(0, 0.1)
                mutated.parameters[param] = value * (1 + noise)
            elif isinstance(value, str):
                # Occasionally change string parameters
                if random.random() < 0.05:
                    mutated.parameters[param] = f"{value}_variant"
        
        self.behaviors[mutated.id] = mutated
        return mutated
    
    async def _apply_crossover(self, population: List[Behavior]) -> List[Behavior]:
        """Apply crossover between successful behaviors"""
        crossed_population = list(population)
        
        # Select parents based on fitness
        parents = sorted(population, key=lambda b: b.fitness_score, reverse=True)
        
        crossover_count = int(len(parents) * self.evolution_params['crossover_rate'])
        for _ in range(crossover_count):
            if len(parents) >= 2:
                parent1, parent2 = random.sample(parents[:len(parents)//2], 2)
                child = await self._crossover_behaviors(parent1, parent2)
                if child:
                    crossed_population.append(child)
        
        return crossed_population
    
    async def _crossover_behaviors(self, parent1: Behavior, parent2: Behavior) -> Optional[Behavior]:
        """Create child behavior from two parents"""
        if parent1.type != parent2.type:
            return None  # Can only crossover same type
        
        child_id = hashlib.md5(
            f"{parent1.id}_{parent2.id}_child_{datetime.now()}".encode()
        ).hexdigest()[:12]
        
        # Mix parameters
        child_params = {}
        all_params = set(parent1.parameters.keys()) | set(parent2.parameters.keys())
        
        for param in all_params:
            if param in parent1.parameters and param in parent2.parameters:
                # Take from better parent or average
                if random.random() < 0.5:
                    child_params[param] = parent1.parameters[param]
                else:
                    child_params[param] = parent2.parameters[param]
            elif param in parent1.parameters:
                child_params[param] = parent1.parameters[param]
            else:
                child_params[param] = parent2.parameters[param]
        
        child = Behavior(
            id=child_id,
            agent_id=parent1.agent_id,
            type=parent1.type,
            name=f"child_{child_id[:6]}",
            description=f"Crossover of {parent1.name} and {parent2.name}",
            parameters=child_params,
            performance_metrics={},
            parent_behavior_id=parent1.id,
            version=max(parent1.version, parent2.version) + 1
        )
        
        self.behaviors[child.id] = child
        return child
    
    async def _apply_pruning(self, population: List[Behavior]) -> List[Behavior]:
        """Remove poor performing behaviors"""
        threshold = self.evolution_params['pruning_threshold']
        pruned = [b for b in population if b.fitness_score > threshold]
        
        # Remove from storage
        for behavior in population:
            if behavior.fitness_score <= threshold:
                if behavior.id in self.behaviors:
                    del self.behaviors[behavior.id]
        
        return pruned
    
    async def _apply_adaptation(self, population: List[Behavior]) -> List[Behavior]:
        """Adapt behaviors to environment changes"""
        adapted = []
        
        for behavior in population:
            # Check if behavior needs adaptation
            if self._needs_adaptation(behavior):
                adapted_behavior = await self._adapt_behavior(behavior)
                adapted.append(adapted_behavior)
            else:
                adapted.append(behavior)
        
        return adapted
    
    def _needs_adaptation(self, behavior: Behavior) -> bool:
        """Check if behavior needs adaptation"""
        # Check performance trend
        if behavior.id not in self.performance_history:
            return False
        
        history = self.performance_history[behavior.id]
        if len(history) < 5:
            return False
        
        # Check if performance is declining
        recent = [score for _, score in history[-5:]]
        trend = (recent[-1] - recent[0]) / max(recent[0], 0.01)
        
        return trend < -0.1  # 10% decline
    
    async def _adapt_behavior(self, behavior: Behavior) -> Behavior:
        """Adapt behavior to current environment"""
        adapted = Behavior(
            id=hashlib.md5(f"{behavior.id}_adapted_{datetime.now()}".encode()).hexdigest()[:12],
            agent_id=behavior.agent_id,
            type=behavior.type,
            name=f"{behavior.name}_adapted",
            description=f"Adapted version of {behavior.description}",
            parameters=behavior.parameters.copy(),
            performance_metrics={},
            parent_behavior_id=behavior.id,
            version=behavior.version + 1
        )
        
        # Adjust parameters based on performance metrics
        if 'efficiency' in behavior.performance_metrics:
            if behavior.performance_metrics['efficiency'] < 0.5:
                # Optimize for efficiency
                for param in adapted.parameters:
                    if 'threshold' in param.lower():
                        adapted.parameters[param] *= 0.9  # Lower thresholds
        
        self.behaviors[adapted.id] = adapted
        return adapted
    
    async def _apply_innovation(self, population: List[Behavior]) -> List[Behavior]:
        """Create innovative new behaviors"""
        innovations = list(population)
        
        # Create innovations based on successful behaviors
        top_performers = sorted(population, key=lambda b: b.fitness_score, reverse=True)[:5]
        
        for performer in top_performers:
            if random.random() < self.evolution_params['innovation_rate']:
                innovation = await self._create_innovation(performer.agent_id)
                if innovation:
                    innovations.append(innovation)
        
        return innovations
    
    async def _create_innovation(self, agent_id: Optional[str]) -> Optional[Behavior]:
        """Create an innovative new behavior"""
        if not agent_id:
            return None
        
        # Random behavior type
        behavior_type = random.choice(list(BehaviorType))
        
        innovation = Behavior(
            id=hashlib.md5(f"innovation_{agent_id}_{datetime.now()}".encode()).hexdigest()[:12],
            agent_id=agent_id,
            type=behavior_type,
            name=f"innovation_{behavior_type.value}",
            description="Innovative behavior pattern",
            parameters={
                'exploration_rate': random.random(),
                'risk_tolerance': random.random(),
                'creativity_factor': random.random(),
                'adaptation_speed': random.random()
            },
            performance_metrics={},
            tags=['innovation']
        )
        
        self.behaviors[innovation.id] = innovation
        return innovation
    
    async def optimize_workflow(self, 
                               workflow_id: str,
                               performance_data: Dict[str, Any]) -> Optional[WorkflowPattern]:
        """
        Optimize a workflow based on performance data
        """
        # Get or create workflow pattern
        if workflow_id in self.workflow_patterns:
            pattern = self.workflow_patterns[workflow_id]
        else:
            pattern = WorkflowPattern(
                id=workflow_id,
                name=f"Workflow {workflow_id}",
                description="Workflow pattern",
                steps=[],
                success_rate=0.5,
                avg_duration=0.0,
                resource_usage={},
                applicable_scenarios=[]
            )
            self.workflow_patterns[workflow_id] = pattern
        
        # Update performance metrics
        pattern.success_rate = performance_data.get('success_rate', pattern.success_rate)
        pattern.avg_duration = performance_data.get('duration', pattern.avg_duration)
        pattern.resource_usage = performance_data.get('resources', pattern.resource_usage)
        
        # Optimize if performance is poor
        if pattern.success_rate < 0.7:
            optimized = await self._optimize_workflow_pattern(pattern)
            if optimized:
                pattern = optimized
                pattern.last_optimized = datetime.now()
                pattern.version += 1
                
                # Record optimization
                pattern.optimization_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'Low success rate',
                    'changes': 'Workflow optimization applied',
                    'expected_improvement': 0.1
                })
        
        return pattern
    
    async def _optimize_workflow_pattern(self, pattern: WorkflowPattern) -> Optional[WorkflowPattern]:
        """Apply optimizations to workflow pattern"""
        optimized = WorkflowPattern(
            id=pattern.id,
            name=pattern.name,
            description=pattern.description,
            steps=pattern.steps.copy(),
            success_rate=pattern.success_rate,
            avg_duration=pattern.avg_duration,
            resource_usage=pattern.resource_usage.copy(),
            applicable_scenarios=pattern.applicable_scenarios.copy(),
            version=pattern.version + 1,
            optimization_history=pattern.optimization_history.copy()
        )
        
        # Apply optimizations
        # 1. Remove redundant steps
        optimized.steps = self._remove_redundant_steps(optimized.steps)
        
        # 2. Parallelize independent steps
        optimized.steps = self._parallelize_steps(optimized.steps)
        
        # 3. Reorder for efficiency
        optimized.steps = self._reorder_steps(optimized.steps)
        
        self.workflow_patterns[pattern.id] = optimized
        return optimized
    
    def _remove_redundant_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove redundant workflow steps"""
        unique_steps = []
        seen = set()
        
        for step in steps:
            step_key = json.dumps(step, sort_keys=True)
            if step_key not in seen:
                seen.add(step_key)
                unique_steps.append(step)
        
        return unique_steps
    
    def _parallelize_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify and mark steps that can run in parallel"""
        # Simple implementation - mark independent steps
        for i, step in enumerate(steps):
            if 'dependencies' not in step:
                step['parallel'] = True
            else:
                step['parallel'] = False
        
        return steps
    
    def _reorder_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reorder steps for efficiency"""
        # Sort by estimated duration (quick steps first)
        return sorted(steps, key=lambda s: s.get('duration', 0))
    
    async def improve_template(self,
                              template_id: str,
                              usage_data: Dict[str, Any]) -> Optional[TemplateEvolution]:
        """
        Improve a template based on usage data
        """
        # Analyze usage patterns
        improvements = self._analyze_template_usage(usage_data)
        
        if not improvements:
            return None
        
        # Create evolution
        evolution = TemplateEvolution(
            id=hashlib.md5(f"{template_id}_{datetime.now()}".encode()).hexdigest()[:12],
            template_id=template_id,
            template_name=usage_data.get('name', 'Unknown Template'),
            changes=improvements,
            reason=self._determine_improvement_reason(improvements),
            expected_improvement=self._estimate_improvement(improvements)
        )
        
        self.template_evolutions[evolution.id] = evolution
        
        # Test evolution
        test_result = await self._test_template_evolution(evolution)
        
        if test_result > evolution.expected_improvement:
            evolution.status = 'applied'
            evolution.actual_improvement = test_result
            evolution.applied_at = datetime.now()
        else:
            evolution.status = 'rejected'
        
        return evolution
    
    def _analyze_template_usage(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze template usage and identify improvements"""
        improvements = {}
        
        # Check for unused sections
        if 'unused_sections' in usage_data:
            improvements['remove_sections'] = usage_data['unused_sections']
        
        # Check for frequently added custom fields
        if 'custom_fields' in usage_data:
            field_frequency = Counter(usage_data['custom_fields'])
            common_fields = [f for f, count in field_frequency.items() if count > 5]
            if common_fields:
                improvements['add_fields'] = common_fields
        
        # Check for validation issues
        if 'validation_errors' in usage_data:
            improvements['fix_validations'] = usage_data['validation_errors']
        
        return improvements
    
    def _determine_improvement_reason(self, improvements: Dict[str, Any]) -> str:
        """Determine reason for template improvement"""
        reasons = []
        
        if 'remove_sections' in improvements:
            reasons.append("Remove unused sections")
        if 'add_fields' in improvements:
            reasons.append("Add frequently used custom fields")
        if 'fix_validations' in improvements:
            reasons.append("Fix validation issues")
        
        return "; ".join(reasons) if reasons else "General optimization"
    
    def _estimate_improvement(self, improvements: Dict[str, Any]) -> float:
        """Estimate expected improvement from changes"""
        score = 0.0
        
        # Each type of improvement contributes to score
        if 'remove_sections' in improvements:
            score += 0.1 * len(improvements['remove_sections'])
        if 'add_fields' in improvements:
            score += 0.15 * len(improvements['add_fields'])
        if 'fix_validations' in improvements:
            score += 0.2 * len(improvements['fix_validations'])
        
        return min(1.0, score)
    
    async def _test_template_evolution(self, evolution: TemplateEvolution) -> float:
        """Test template evolution effectiveness"""
        # Simulate testing - in reality would test with actual usage
        base_score = random.random() * 0.3  # Random base improvement
        
        # Add score based on change types
        if 'remove_sections' in evolution.changes:
            base_score += 0.1
        if 'add_fields' in evolution.changes:
            base_score += 0.15
        if 'fix_validations' in evolution.changes:
            base_score += 0.2
        
        return min(1.0, base_score)
    
    def get_best_behaviors(self, 
                          agent_id: Optional[str] = None,
                          behavior_type: Optional[BehaviorType] = None,
                          top_n: int = 10) -> List[Behavior]:
        """
        Get best performing behaviors
        """
        # Filter behaviors
        behaviors = list(self.behaviors.values())
        
        if agent_id:
            behaviors = [b for b in behaviors if b.agent_id == agent_id]
        
        if behavior_type:
            behaviors = [b for b in behaviors if b.type == behavior_type]
        
        # Sort by fitness
        behaviors.sort(key=lambda b: b.fitness_score, reverse=True)
        
        return behaviors[:top_n]
    
    def generate_evolution_report(self) -> str:
        """Generate behavior evolution report"""
        report = "# Behavior Evolution Report\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n\n"
        
        # Evolution Statistics
        report += "## Evolution Statistics\n"
        report += f"- Current Generation: {self.current_generation}\n"
        report += f"- Total Behaviors: {len(self.behaviors)}\n"
        report += f"- Workflow Patterns: {len(self.workflow_patterns)}\n"
        report += f"- Template Evolutions: {len(self.template_evolutions)}\n\n"
        
        # Generation Progress
        if self.generations:
            report += "## Generation Progress\n"
            report += "| Gen | Population | Avg Fitness | Best | Worst |\n"
            report += "|-----|------------|-------------|------|-------|\n"
            
            for gen in self.generations[-10:]:  # Last 10 generations
                report += f"| {gen.generation_number} | {gen.population_size} | "
                report += f"{gen.avg_fitness:.3f} | {gen.best_fitness:.3f} | "
                report += f"{gen.worst_fitness:.3f} |\n"
            report += "\n"
        
        # Top Behaviors
        report += "## Top Performing Behaviors\n"
        top_behaviors = self.get_best_behaviors(top_n=5)
        
        for i, behavior in enumerate(top_behaviors, 1):
            report += f"{i}. **{behavior.name}**\n"
            report += f"   - Type: {behavior.type.value}\n"
            report += f"   - Fitness: {behavior.fitness_score:.3f}\n"
            report += f"   - Success Rate: {behavior.success_rate:.3f}\n"
            report += f"   - Usage: {behavior.usage_count}\n\n"
        
        # Workflow Optimizations
        if self.workflow_patterns:
            report += "## Workflow Optimizations\n"
            for pattern in list(self.workflow_patterns.values())[:5]:
                report += f"- **{pattern.name}** (v{pattern.version})\n"
                report += f"  - Success Rate: {pattern.success_rate:.3f}\n"
                report += f"  - Avg Duration: {pattern.avg_duration:.1f}s\n"
                if pattern.last_optimized:
                    report += f"  - Last Optimized: {pattern.last_optimized.isoformat()}\n"
                report += "\n"
        
        # Template Improvements
        if self.template_evolutions:
            report += "## Template Improvements\n"
            applied = [e for e in self.template_evolutions.values() if e.status == 'applied']
            
            for evolution in applied[:5]:
                report += f"- **{evolution.template_name}**\n"
                report += f"  - Reason: {evolution.reason}\n"
                report += f"  - Expected: {evolution.expected_improvement:.2f}\n"
                if evolution.actual_improvement:
                    report += f"  - Actual: {evolution.actual_improvement:.2f}\n"
                report += "\n"
        
        return report
    
    def save_state(self, filepath: str) -> None:
        """Save evolution state"""
        state = {
            'behaviors': {k: asdict(v) for k, v in self.behaviors.items()},
            'workflow_patterns': {k: asdict(v) for k, v in self.workflow_patterns.items()},
            'template_evolutions': {k: asdict(v) for k, v in self.template_evolutions.items()},
            'generations': [asdict(g) for g in self.generations],
            'current_generation': self.current_generation,
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert enums to strings
        for behavior_data in state['behaviors'].values():
            behavior_data['type'] = behavior_data['type'].value if isinstance(behavior_data['type'], Enum) else behavior_data['type']
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self, filepath: str) -> None:
        """Load evolution state"""
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Restore behaviors
        for behavior_id, behavior_data in state.get('behaviors', {}).items():
            behavior_data['type'] = BehaviorType(behavior_data['type'])
            behavior_data['created_at'] = datetime.fromisoformat(behavior_data['created_at'])
            if behavior_data.get('last_used'):
                behavior_data['last_used'] = datetime.fromisoformat(behavior_data['last_used'])
            self.behaviors[behavior_id] = Behavior(**behavior_data)
        
        self.current_generation = state.get('current_generation', 0)


# Example usage
async def main():
    """Example of using behavior evolution system"""
    evolution = BehaviorEvolution()
    
    # Track some behaviors
    behavior1 = await evolution.track_behavior(
        agent_id="agent_001",
        behavior_type=BehaviorType.PROBLEM_SOLVING,
        parameters={'approach': 'analytical', 'depth': 3},
        outcome='success',
        metrics={'efficiency': 0.8, 'quality': 0.9}
    )
    
    print(f"Tracked behavior: {behavior1.name} (fitness: {behavior1.fitness_score:.3f})")
    
    # Evolve behaviors
    evolved = await evolution.evolve_behaviors(strategy=EvolutionStrategy.MUTATION)
    print(f"Evolved {len(evolved)} behaviors")
    
    # Optimize workflow
    workflow = await evolution.optimize_workflow(
        workflow_id="workflow_001",
        performance_data={'success_rate': 0.65, 'duration': 120}
    )
    if workflow:
        print(f"Optimized workflow: {workflow.name} (v{workflow.version})")
    
    # Improve template
    template_evolution = await evolution.improve_template(
        template_id="template_001",
        usage_data={
            'name': 'User Story Template',
            'unused_sections': ['Technical Notes'],
            'custom_fields': ['Priority', 'Priority', 'Risk Level']
        }
    )
    if template_evolution:
        print(f"Template improvement: {template_evolution.reason}")
    
    # Generate report
    report = evolution.generate_evolution_report()
    print("\n" + report)
    
    # Save state
    evolution.save_state('evolution_state.json')


if __name__ == "__main__":
    asyncio.run(main())