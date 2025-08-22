"""
Test Suite for Behavior Evolution System

This module tests the behavior evolution functionality including:
- Behavior tracking and performance measurement
- Evolution strategies (mutation, crossover, reinforcement, etc.)
- Workflow pattern optimization
- Template improvement
- Fitness score calculation
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from learning.behavior_evolution import (
    BehaviorEvolution,
    Behavior,
    BehaviorType,
    EvolutionStrategy,
    PerformanceMetric,
    WorkflowPattern,
    TemplateEvolution,
    EvolutionGeneration
)


class TestBehaviorEvolution:
    """Test class for BehaviorEvolution"""
    
    @pytest.fixture
    def evolution_system(self):
        """Create BehaviorEvolution instance for testing"""
        return BehaviorEvolution()
    
    @pytest.fixture
    def sample_behavior(self):
        """Create sample Behavior for testing"""
        return Behavior(
            id='behavior_001',
            agent_id='agent_001',
            type=BehaviorType.PROBLEM_SOLVING,
            name='Test Behavior',
            description='Test behavior for unit tests',
            parameters={'approach': 'analytical', 'depth': 3},
            performance_metrics={'efficiency': 0.8, 'quality': 0.9},
            usage_count=10,
            success_count=8,
            failure_count=2
        )
    
    @pytest.fixture
    def sample_workflow_pattern(self):
        """Create sample WorkflowPattern for testing"""
        return WorkflowPattern(
            id='workflow_001',
            name='Test Workflow',
            description='Test workflow pattern',
            steps=[
                {'name': 'step1', 'duration': 10},
                {'name': 'step2', 'duration': 20},
                {'name': 'step3', 'duration': 15}
            ],
            success_rate=0.8,
            avg_duration=45.0,
            resource_usage={'cpu': 0.3, 'memory': 0.4},
            applicable_scenarios=['test', 'development']
        )
    
    def test_initialization(self, evolution_system):
        """Test BehaviorEvolution initialization"""
        assert evolution_system is not None
        assert evolution_system.behaviors == {}
        assert evolution_system.workflow_patterns == {}
        assert evolution_system.template_evolutions == {}
        assert evolution_system.generations == []
        assert evolution_system.current_generation == 0
        assert 'mutation_rate' in evolution_system.evolution_params
        assert evolution_system.evolution_params['mutation_rate'] == 0.1
    
    def test_load_config_default(self):
        """Test loading default configuration"""
        evolution_system = BehaviorEvolution()
        assert 'evolution_interval' in evolution_system.config
        assert evolution_system.config['evolution_interval'] == 'daily'
        assert evolution_system.config['min_data_points'] == 10
    
    def test_load_config_from_file(self):
        """Test loading configuration from file"""
        config_data = {
            'evolution_interval': 'hourly',
            'min_data_points': 5,
            'fitness_threshold': 0.8
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            evolution_system = BehaviorEvolution(config_path)
            assert evolution_system.config['evolution_interval'] == 'hourly'
            assert evolution_system.config['min_data_points'] == 5
            assert evolution_system.config['fitness_threshold'] == 0.8
        finally:
            os.unlink(config_path)
    
    def test_behavior_properties(self, sample_behavior):
        """Test Behavior class properties"""
        # Test success rate calculation
        assert sample_behavior.success_rate == 0.8  # 8/(8+2)
        
        # Test fitness score calculation
        fitness = sample_behavior.fitness_score
        assert 0.0 <= fitness <= 1.0
        assert fitness > 0.6  # Should be reasonably high given good metrics
        
        # Test behavior with no usage
        new_behavior = Behavior(
            id='new_001',
            agent_id='agent_001',
            type=BehaviorType.COMMUNICATION,
            name='New Behavior',
            description='New behavior',
            parameters={},
            performance_metrics={}
        )
        assert new_behavior.success_rate == 0.5  # Default for new behaviors
    
    @pytest.mark.asyncio
    async def test_track_behavior(self, evolution_system):
        """Test behavior tracking"""
        behavior = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.DECISION_MAKING,
            parameters={'threshold': 0.7, 'method': 'weighted'},
            outcome='success',
            metrics={'efficiency': 0.8, 'accuracy': 0.9}
        )
        
        assert behavior is not None
        assert behavior.agent_id == 'agent_001'
        assert behavior.type == BehaviorType.DECISION_MAKING
        assert behavior.usage_count == 1
        assert behavior.success_count == 1
        assert behavior.failure_count == 0
        assert behavior.performance_metrics['efficiency'] == 0.8
        assert behavior.performance_metrics['accuracy'] == 0.9
        assert behavior.id in evolution_system.behaviors
        assert behavior.id in evolution_system.performance_history
        
        # Track same behavior again
        behavior2 = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.DECISION_MAKING,
            parameters={'threshold': 0.7, 'method': 'weighted'},
            outcome='failure',
            metrics={'efficiency': 0.6, 'accuracy': 0.7}
        )
        
        # Should be same behavior object (same parameters)
        assert behavior2.id == behavior.id
        assert behavior2.usage_count == 2
        assert behavior2.success_count == 1
        assert behavior2.failure_count == 1
        
        # Performance metrics should be updated (moving average)
        assert behavior2.performance_metrics['efficiency'] < 0.8  # Should decrease
    
    @pytest.mark.asyncio
    async def test_evolve_behaviors_insufficient_data(self, evolution_system):
        """Test evolution with insufficient data"""
        # Add only a few behaviors (less than min_data_points)
        for i in range(5):
            await evolution_system.track_behavior(
                agent_id='agent_001',
                behavior_type=BehaviorType.TASK_EXECUTION,
                parameters={'speed': i},
                outcome='success',
                metrics={'efficiency': 0.7}
            )
        
        evolved = await evolution_system.evolve_behaviors()
        assert len(evolved) == 0  # Not enough data to evolve
    
    @pytest.mark.asyncio
    async def test_evolve_behaviors_mixed_strategy(self, evolution_system):
        """Test mixed evolution strategy"""
        # Add sufficient behaviors
        behaviors = []
        for i in range(15):
            behavior = await evolution_system.track_behavior(
                agent_id='agent_001',
                behavior_type=BehaviorType.COLLABORATION,
                parameters={'aggressiveness': i * 0.1, 'patience': (15 - i) * 0.1},
                outcome='success' if i % 3 != 0 else 'failure',
                metrics={'efficiency': 0.5 + i * 0.03, 'quality': 0.6 + i * 0.02}
            )
            behaviors.append(behavior)
        
        evolved = await evolution_system.evolve_behaviors()
        
        # Should have evolved behaviors
        assert len(evolved) > 0
        
        # Check generation was recorded
        assert evolution_system.current_generation == 1
        assert len(evolution_system.generations) == 1
        
        generation = evolution_system.generations[0]
        assert generation.generation_number == 1
        assert generation.population_size == 15
        assert 0.0 <= generation.avg_fitness <= 1.0
        assert generation.best_fitness >= generation.avg_fitness
        assert generation.avg_fitness >= generation.worst_fitness
    
    @pytest.mark.asyncio
    async def test_reinforcement_strategy(self, evolution_system):
        """Test reinforcement evolution strategy"""
        # Create behavior with high success rate
        high_success_behavior = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.LEARNING,
            parameters={'learning_rate': 0.1, 'exploration': 0.2},
            outcome='success',
            metrics={'efficiency': 0.9, 'quality': 0.8}
        )
        
        # Track multiple successes
        for _ in range(9):
            await evolution_system.track_behavior(
                agent_id='agent_001',
                behavior_type=BehaviorType.LEARNING,
                parameters={'learning_rate': 0.1, 'exploration': 0.2},
                outcome='success',
                metrics={'efficiency': 0.9, 'quality': 0.8}
            )
        
        evolved = await evolution_system._apply_reinforcement([high_success_behavior])
        
        assert len(evolved) == 1
        reinforced = evolved[0]
        
        # Should be a reinforced version
        if reinforced.id != high_success_behavior.id:
            assert reinforced.parent_behavior_id == high_success_behavior.id
            assert reinforced.version == high_success_behavior.version + 1
            assert 'reinforced' in reinforced.name
    
    @pytest.mark.asyncio
    async def test_mutation_strategy(self, evolution_system):
        """Test mutation evolution strategy"""
        original_behavior = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.ERROR_HANDLING,
            parameters={'retry_limit': 3, 'timeout': 30.0, 'escalate': True},
            outcome='success',
            metrics={'reliability': 0.8}
        )
        
        # Set high mutation rate for testing
        evolution_system.evolution_params['mutation_rate'] = 1.0
        
        mutated_population = await evolution_system._apply_mutation([original_behavior])
        
        assert len(mutated_population) == 1
        mutated = mutated_population[0]
        
        # Should be a mutated version
        if mutated.id != original_behavior.id:
            assert mutated.parent_behavior_id == original_behavior.id
            assert 'mut' in mutated.name or mutated.version > original_behavior.version
    
    @pytest.mark.asyncio
    async def test_crossover_strategy(self, evolution_system):
        """Test crossover evolution strategy"""
        # Create two parent behaviors
        parent1 = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.RESOURCE_MANAGEMENT,
            parameters={'cpu_threshold': 0.8, 'memory_threshold': 0.7, 'priority': 'high'},
            outcome='success',
            metrics={'efficiency': 0.9}
        )
        
        parent2 = await evolution_system.track_behavior(
            agent_id='agent_001',
            behavior_type=BehaviorType.RESOURCE_MANAGEMENT,
            parameters={'cpu_threshold': 0.6, 'memory_threshold': 0.9, 'priority': 'medium'},
            outcome='success',
            metrics={'efficiency': 0.8}
        )
        
        # Crossover
        child = await evolution_system._crossover_behaviors(parent1, parent2)
        
        assert child is not None
        assert child.agent_id == parent1.agent_id
        assert child.type == parent1.type
        assert child.parent_behavior_id == parent1.id
        assert child.version > max(parent1.version, parent2.version)
        
        # Parameters should be mix of parents
        assert 'cpu_threshold' in child.parameters
        assert 'memory_threshold' in child.parameters
        assert 'priority' in child.parameters
    
    @pytest.mark.asyncio
    async def test_crossover_different_types(self, evolution_system):
        """Test crossover with different behavior types"""
        parent1 = Behavior(
            id='parent1',
            agent_id='agent_001',
            type=BehaviorType.COMMUNICATION,
            name='Parent 1',
            description='Test',
            parameters={},
            performance_metrics={}
        )
        
        parent2 = Behavior(
            id='parent2',
            agent_id='agent_001',
            type=BehaviorType.DECISION_MAKING,  # Different type
            name='Parent 2',
            description='Test',
            parameters={},
            performance_metrics={}
        )
        
        child = await evolution_system._crossover_behaviors(parent1, parent2)
        assert child is None  # Can't crossover different types
    
    @pytest.mark.asyncio
    async def test_pruning_strategy(self, evolution_system):
        """Test pruning evolution strategy"""
        # Create behaviors with different fitness scores
        good_behavior = Behavior(
            id='good_001',
            agent_id='agent_001',
            type=BehaviorType.TASK_EXECUTION,
            name='Good Behavior',
            description='High performing behavior',
            parameters={},
            performance_metrics={'efficiency': 0.9, 'quality': 0.8},
            usage_count=10,
            success_count=9,
            failure_count=1
        )
        
        poor_behavior = Behavior(
            id='poor_001',
            agent_id='agent_001',
            type=BehaviorType.TASK_EXECUTION,
            name='Poor Behavior',
            description='Low performing behavior',
            parameters={},
            performance_metrics={'efficiency': 0.2, 'quality': 0.3},
            usage_count=10,
            success_count=2,
            failure_count=8
        )
        
        evolution_system.behaviors['good_001'] = good_behavior
        evolution_system.behaviors['poor_001'] = poor_behavior
        
        pruned = await evolution_system._apply_pruning([good_behavior, poor_behavior])
        
        # Only good behavior should remain
        assert len(pruned) == 1
        assert pruned[0].id == 'good_001'
        
        # Poor behavior should be removed from storage
        assert 'poor_001' not in evolution_system.behaviors
    
    @pytest.mark.asyncio
    async def test_innovation_strategy(self, evolution_system):
        """Test innovation creation"""
        innovation = await evolution_system._create_innovation('agent_001')
        
        assert innovation is not None
        assert innovation.agent_id == 'agent_001'
        assert innovation.type in list(BehaviorType)
        assert 'innovation' in innovation.name
        assert 'innovation' in innovation.tags
        assert 'exploration_rate' in innovation.parameters
        assert 'creativity_factor' in innovation.parameters
        assert innovation.id in evolution_system.behaviors
    
    def test_needs_adaptation(self, evolution_system):
        """Test adaptation need detection"""
        behavior = Behavior(
            id='adapt_test',
            agent_id='agent_001',
            type=BehaviorType.LEARNING,
            name='Adaptation Test',
            description='Test',
            parameters={},
            performance_metrics={}
        )
        
        # No history - should not need adaptation
        assert evolution_system._needs_adaptation(behavior) is False
        
        # Add declining performance history
        evolution_system.performance_history['adapt_test'] = [
            (datetime.now() - timedelta(days=5), 0.8),
            (datetime.now() - timedelta(days=4), 0.75),
            (datetime.now() - timedelta(days=3), 0.7),
            (datetime.now() - timedelta(days=2), 0.65),
            (datetime.now() - timedelta(days=1), 0.6)
        ]
        
        # Should need adaptation due to declining trend
        assert evolution_system._needs_adaptation(behavior) is True
        
        # Add improving performance history
        evolution_system.performance_history['adapt_test'] = [
            (datetime.now() - timedelta(days=5), 0.6),
            (datetime.now() - timedelta(days=4), 0.65),
            (datetime.now() - timedelta(days=3), 0.7),
            (datetime.now() - timedelta(days=2), 0.75),
            (datetime.now() - timedelta(days=1), 0.8)
        ]
        
        # Should not need adaptation with improving trend
        assert evolution_system._needs_adaptation(behavior) is False
    
    @pytest.mark.asyncio
    async def test_optimize_workflow(self, evolution_system):
        """Test workflow optimization"""
        performance_data = {
            'success_rate': 0.6,  # Poor performance
            'duration': 60.0,
            'resources': {'cpu': 0.8, 'memory': 0.9}
        }
        
        optimized_pattern = await evolution_system.optimize_workflow(
            'workflow_test',
            performance_data
        )
        
        assert optimized_pattern is not None
        assert optimized_pattern.id == 'workflow_test'
        assert optimized_pattern.success_rate == 0.6
        assert optimized_pattern.avg_duration == 60.0
        assert optimized_pattern.resource_usage['cpu'] == 0.8
        
        # Should be optimized due to poor performance
        assert optimized_pattern.version > 1
        assert optimized_pattern.last_optimized is not None
        assert len(optimized_pattern.optimization_history) > 0
    
    def test_remove_redundant_steps(self, evolution_system):
        """Test redundant step removal"""
        steps = [
            {'name': 'step1', 'action': 'validate'},
            {'name': 'step2', 'action': 'process'},
            {'name': 'step1', 'action': 'validate'},  # Duplicate
            {'name': 'step3', 'action': 'output'}
        ]
        
        unique_steps = evolution_system._remove_redundant_steps(steps)
        
        assert len(unique_steps) == 3  # One duplicate removed
        step_names = [step['name'] for step in unique_steps]
        assert step_names.count('step1') == 1
    
    def test_parallelize_steps(self, evolution_system):
        """Test step parallelization"""
        steps = [
            {'name': 'step1'},
            {'name': 'step2', 'dependencies': ['step1']},
            {'name': 'step3'}
        ]
        
        parallel_steps = evolution_system._parallelize_steps(steps)
        
        assert parallel_steps[0]['parallel'] is True  # No dependencies
        assert parallel_steps[1]['parallel'] is False  # Has dependencies
        assert parallel_steps[2]['parallel'] is True  # No dependencies
    
    def test_reorder_steps(self, evolution_system):
        """Test step reordering"""
        steps = [
            {'name': 'slow_step', 'duration': 30},
            {'name': 'fast_step', 'duration': 5},
            {'name': 'medium_step', 'duration': 15}
        ]
        
        reordered = evolution_system._reorder_steps(steps)
        
        # Should be ordered by duration (fast first)
        assert reordered[0]['name'] == 'fast_step'
        assert reordered[1]['name'] == 'medium_step'
        assert reordered[2]['name'] == 'slow_step'
    
    @pytest.mark.asyncio
    async def test_improve_template(self, evolution_system):
        """Test template improvement"""
        usage_data = {
            'name': 'User Story Template',
            'unused_sections': ['Technical Notes', 'Legacy Info'],
            'custom_fields': ['Priority', 'Risk Level', 'Priority', 'Complexity'],
            'validation_errors': ['Missing acceptance criteria', 'Invalid format']
        }
        
        evolution = await evolution_system.improve_template('template_001', usage_data)
        
        assert evolution is not None
        assert evolution.template_id == 'template_001'
        assert evolution.template_name == 'User Story Template'
        assert 'remove_sections' in evolution.changes
        assert 'add_fields' in evolution.changes
        assert 'fix_validations' in evolution.changes
        assert evolution.expected_improvement > 0
        assert evolution.status in ['applied', 'rejected']
        
        if evolution.status == 'applied':
            assert evolution.actual_improvement is not None
            assert evolution.applied_at is not None
    
    def test_analyze_template_usage(self, evolution_system):
        """Test template usage analysis"""
        usage_data = {
            'unused_sections': ['section1', 'section2'],
            'custom_fields': ['field1', 'field1', 'field2'] * 3,  # field1 appears 9 times
            'validation_errors': ['error1', 'error2']
        }
        
        improvements = evolution_system._analyze_template_usage(usage_data)
        
        assert 'remove_sections' in improvements
        assert improvements['remove_sections'] == ['section1', 'section2']
        
        assert 'add_fields' in improvements
        assert 'field1' in improvements['add_fields']  # Frequent field
        
        assert 'fix_validations' in improvements
        assert improvements['fix_validations'] == ['error1', 'error2']
    
    def test_get_best_behaviors(self, evolution_system):
        """Test getting best behaviors"""
        # Add behaviors with different fitness scores
        behaviors = []
        for i in range(5):
            behavior = Behavior(
                id=f'best_test_{i}',
                agent_id='agent_001',
                type=BehaviorType.COMMUNICATION,
                name=f'Behavior {i}',
                description='Test',
                parameters={},
                performance_metrics={'efficiency': 0.1 + i * 0.2},
                usage_count=10,
                success_count=i * 2 + 1,
                failure_count=10 - (i * 2 + 1)
            )
            behaviors.append(behavior)
            evolution_system.behaviors[behavior.id] = behavior
        
        # Get best behaviors
        best = evolution_system.get_best_behaviors(top_n=3)
        
        assert len(best) == 3
        # Should be ordered by fitness (descending)
        assert best[0].fitness_score >= best[1].fitness_score
        assert best[1].fitness_score >= best[2].fitness_score
        
        # Test filtering by agent
        best_agent = evolution_system.get_best_behaviors(agent_id='agent_001', top_n=3)
        assert len(best_agent) == 3
        assert all(b.agent_id == 'agent_001' for b in best_agent)
        
        # Test filtering by type
        best_type = evolution_system.get_best_behaviors(
            behavior_type=BehaviorType.COMMUNICATION,
            top_n=3
        )
        assert len(best_type) == 3
        assert all(b.type == BehaviorType.COMMUNICATION for b in best_type)
    
    def test_generate_evolution_report(self, evolution_system):
        """Test evolution report generation"""
        # Add test data
        behavior = Behavior(
            id='report_test',
            agent_id='agent_001',
            type=BehaviorType.PROBLEM_SOLVING,
            name='Report Test Behavior',
            description='Test behavior for reporting',
            parameters={},
            performance_metrics={'efficiency': 0.9},
            usage_count=15,
            success_count=13,
            failure_count=2
        )
        evolution_system.behaviors['report_test'] = behavior
        
        # Add generation
        generation = EvolutionGeneration(
            generation_number=1,
            timestamp=datetime.now(),
            population_size=10,
            avg_fitness=0.7,
            best_fitness=0.9,
            worst_fitness=0.5,
            mutations=2,
            crossovers=1,
            innovations=1,
            pruned=1
        )
        evolution_system.generations.append(generation)
        evolution_system.current_generation = 1
        
        # Add workflow pattern
        pattern = WorkflowPattern(
            id='pattern_001',
            name='Test Pattern',
            description='Test',
            steps=[],
            success_rate=0.8,
            avg_duration=30.0,
            resource_usage={},
            applicable_scenarios=[],
            version=2,
            last_optimized=datetime.now()
        )
        evolution_system.workflow_patterns['pattern_001'] = pattern
        
        # Add template evolution
        template_evolution = TemplateEvolution(
            id='template_evo_001',
            template_id='template_001',
            template_name='Test Template',
            changes={},
            reason='Test improvement',
            expected_improvement=0.2,
            actual_improvement=0.25,
            status='applied',
            applied_at=datetime.now()
        )
        evolution_system.template_evolutions['template_evo_001'] = template_evolution
        
        report = evolution_system.generate_evolution_report()
        
        assert '# Behavior Evolution Report' in report
        assert 'Evolution Statistics' in report
        assert 'Current Generation: 1' in report
        assert 'Total Behaviors: 1' in report
        assert 'Generation Progress' in report
        assert 'Top Performing Behaviors' in report
        assert 'Report Test Behavior' in report
        assert 'Workflow Optimizations' in report
        assert 'Test Pattern' in report
        assert 'Template Improvements' in report
        assert 'Test Template' in report
    
    def test_save_and_load_state(self, evolution_system):
        """Test state persistence"""
        # Add test data
        behavior = Behavior(
            id='persist_test',
            agent_id='agent_001',
            type=BehaviorType.LEARNING,
            name='Persistence Test',
            description='Test behavior for persistence',
            parameters={'param1': 'value1'},
            performance_metrics={'metric1': 0.8},
            usage_count=5,
            success_count=4,
            failure_count=1
        )
        evolution_system.behaviors['persist_test'] = behavior
        evolution_system.current_generation = 3
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            evolution_system.save_state(filepath)
            
            # Create new instance and load
            new_evolution = BehaviorEvolution()
            new_evolution.load_state(filepath)
            
            assert 'persist_test' in new_evolution.behaviors
            loaded_behavior = new_evolution.behaviors['persist_test']
            assert loaded_behavior.name == 'Persistence Test'
            assert loaded_behavior.usage_count == 5
            assert loaded_behavior.success_count == 4
            assert loaded_behavior.type == BehaviorType.LEARNING
            assert new_evolution.current_generation == 3
            
        finally:
            os.unlink(filepath)


# Test runner
if __name__ == "__main__":
    # Run simple validation tests
    async def run_tests():
        print("Running Behavior Evolution Tests...")
        
        # Test initialization
        evolution = BehaviorEvolution()
        print("✓ Initialization test passed")
        
        # Test behavior tracking
        behavior = await evolution.track_behavior(
            agent_id='test_agent',
            behavior_type=BehaviorType.PROBLEM_SOLVING,
            parameters={'approach': 'systematic'},
            outcome='success',
            metrics={'efficiency': 0.8}
        )
        assert behavior is not None
        assert behavior.usage_count == 1
        print("✓ Behavior tracking test passed")
        
        # Test behavior properties
        assert 0.0 <= behavior.fitness_score <= 1.0
        assert behavior.success_rate == 1.0  # All successes so far
        print("✓ Behavior properties test passed")
        
        # Test workflow optimization
        pattern = await evolution.optimize_workflow(
            'test_workflow',
            {'success_rate': 0.9, 'duration': 30}
        )
        assert pattern is not None
        print("✓ Workflow optimization test passed")
        
        # Test template improvement
        template_evolution = await evolution.improve_template(
            'test_template',
            {
                'name': 'Test Template',
                'unused_sections': ['old_section'],
                'custom_fields': ['priority'] * 6  # Frequent field
            }
        )
        assert template_evolution is not None
        print("✓ Template improvement test passed")
        
        # Test report generation
        report = evolution.generate_evolution_report()
        assert len(report) > 0
        print("✓ Report generation test passed")
        
        print("All tests passed! ✓")
    
    asyncio.run(run_tests())