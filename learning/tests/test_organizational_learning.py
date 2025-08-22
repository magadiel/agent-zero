"""
Test Suite for Organizational Learning System

This module tests the organizational learning functionality including:
- Learning aggregation from multiple sources
- Behavior updates based on learnings
- Workflow evolution from patterns
- Template improvements
- Knowledge base updates
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

from learning.organizational_learning import (
    OrganizationalLearning,
    LearningSource,
    LearningImpact,
    EvolutionTrigger,
    LearningContext,
    LearningEvolution,
    KnowledgeUpdate
)
from coordination.learning_synthesizer import Learning, LearningType, LearningPriority


class TestOrganizationalLearning:
    """Test class for OrganizationalLearning"""
    
    @pytest.fixture
    def org_learning(self):
        """Create OrganizationalLearning instance for testing"""
        return OrganizationalLearning()
    
    @pytest.fixture
    def sample_learning_data(self):
        """Create sample learning data for testing"""
        return {
            'team_id': 'team_001',
            'type': 'improvement',
            'priority': 'high',
            'title': 'Improved Error Handling',
            'description': 'Better error handling reduces failures',
            'context': {'domain': 'error_handling'},
            'tags': ['error', 'improvement', 'reliability'],
            'impact_score': 0.8,
            'confidence': 0.9,
            'impact_level': 'team',
            'affected_entities': ['agent_001', 'agent_002'],
            'performance_before': {'success_rate': 0.7},
            'performance_after': {'success_rate': 0.9},
            'cost_benefit': 0.3,
            'risk_assessment': 'low'
        }
    
    @pytest.fixture
    def sample_learning(self):
        """Create sample Learning object"""
        return Learning(
            id='learning_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Test Learning',
            description='Test learning for unit tests',
            context={'test': True},
            tags=['test', 'improvement'],
            source='test',
            timestamp=datetime.now(),
            impact_score=0.8,
            confidence=0.9
        )
    
    def test_initialization(self, org_learning):
        """Test OrganizationalLearning initialization"""
        assert org_learning is not None
        assert org_learning.learnings == {}
        assert org_learning.evolutions == {}
        assert org_learning.knowledge_updates == {}
        assert org_learning.learning_contexts == {}
        assert 'total_learnings' in org_learning.learning_metrics
        assert 'evolution_confidence' in org_learning.thresholds
    
    def test_load_config_default(self):
        """Test loading default configuration"""
        org_learning = OrganizationalLearning()
        assert 'learning_retention_days' in org_learning.config
        assert org_learning.config['learning_retention_days'] == 90
        assert org_learning.config['max_learnings_per_source'] == 1000
    
    def test_load_config_from_file(self):
        """Test loading configuration from file"""
        config_data = {
            'learning_retention_days': 60,
            'max_learnings_per_source': 500
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            org_learning = OrganizationalLearning(config_path)
            assert org_learning.config['learning_retention_days'] == 60
            assert org_learning.config['max_learnings_per_source'] == 500
        finally:
            os.unlink(config_path)
    
    @pytest.mark.asyncio
    async def test_process_learning(self, org_learning, sample_learning_data):
        """Test processing raw learning data"""
        learning = await org_learning._process_learning(
            sample_learning_data,
            LearningSource.TEAM
        )
        
        assert learning is not None
        assert learning.title == 'Improved Error Handling'
        assert learning.type == LearningType.IMPROVEMENT
        assert learning.priority == LearningPriority.HIGH
        assert learning.source == 'team'
        assert learning.impact_score == 0.8
        assert learning.confidence == 0.9
        
        # Check context was created
        assert learning.id in org_learning.learning_contexts
        context = org_learning.learning_contexts[learning.id]
        assert context.source == LearningSource.TEAM
        assert context.impact_level == LearningImpact.TEAM
        assert context.cost_benefit == 0.3
    
    def test_validate_learning(self, org_learning, sample_learning):
        """Test learning validation"""
        # Valid learning
        assert org_learning._validate_learning(sample_learning) is True
        
        # Invalid learning - no title
        invalid_learning = Learning(
            id='invalid_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='',  # Empty title
            description='Test learning',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now()
        )
        assert org_learning._validate_learning(invalid_learning) is False
        
        # Invalid learning - low confidence
        low_confidence = Learning(
            id='low_conf_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Low Confidence Learning',
            description='Test learning',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now(),
            confidence=0.2  # Below threshold
        )
        assert org_learning._validate_learning(low_confidence) is False
    
    def test_is_duplicate(self, org_learning):
        """Test duplicate detection"""
        learning1 = Learning(
            id='dup_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Duplicate Test',
            description='Test learning',
            context={},
            tags=['tag1', 'tag2'],
            source='test',
            timestamp=datetime.now()
        )
        
        # Same title
        learning2 = Learning(
            id='dup_002',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Duplicate Test',  # Same title
            description='Different description',
            context={},
            tags=['tag3'],
            source='test',
            timestamp=datetime.now()
        )
        
        assert org_learning._is_duplicate(learning1, learning2) is True
        
        # Similar tags
        learning3 = Learning(
            id='dup_003',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Different Title',
            description='Test learning',
            context={},
            tags=['tag1', 'tag2', 'tag3'],  # 2/3 overlap
            source='test',
            timestamp=datetime.now()
        )
        
        assert org_learning._is_duplicate(learning1, learning3) is True
        
        # Different learning
        learning4 = Learning(
            id='unique_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Unique Learning',
            description='Test learning',
            context={},
            tags=['different'],
            source='test',
            timestamp=datetime.now()
        )
        
        assert org_learning._is_duplicate(learning1, learning4) is False
    
    @pytest.mark.asyncio
    async def test_identify_patterns(self, org_learning):
        """Test pattern identification"""
        # Create learnings with common tags
        learnings = []
        for i in range(5):
            learning = Learning(
                id=f'pattern_test_{i}',
                team_id='team_001',
                type=LearningType.IMPROVEMENT,
                priority=LearningPriority.HIGH,
                title=f'Pattern Learning {i}',
                description='Test learning for pattern',
                context={},
                tags=['performance', 'optimization'],
                source='test',
                timestamp=datetime.now(),
                confidence=0.8
            )
            learnings.append(learning)
        
        patterns = await org_learning._identify_patterns(learnings)
        
        assert len(patterns) >= 1
        pattern = patterns[0]
        assert pattern.type.value in ['best_practice', 'anti_pattern']
        assert pattern.frequency == 5
        assert 'performance' in pattern.tags or 'optimization' in pattern.tags
    
    @pytest.mark.asyncio
    async def test_determine_evolution_type(self, org_learning):
        """Test evolution type determination"""
        context = LearningContext(
            source=LearningSource.TEAM,
            impact_level=LearningImpact.TEAM,
            affected_entities=['agent_001'],
            performance_before={},
            performance_after={},
            cost_benefit=0.2,
            risk_assessment='low',
            implementation_effort='medium',
            success_criteria=[],
            failure_modes=[]
        )
        
        # Behavioral learning
        behavioral_learning = Learning(
            id='behavioral_001',
            team_id='team_001',
            type=LearningType.BEHAVIORAL,
            priority=LearningPriority.HIGH,
            title='Behavioral Learning',
            description='Test',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now()
        )
        
        evolution_type = org_learning._determine_evolution_type(behavioral_learning, context)
        assert evolution_type == EvolutionTrigger.BEHAVIOR_UPDATE
        
        # Process learning
        process_learning = Learning(
            id='process_001',
            team_id='team_001',
            type=LearningType.PROCESS,
            priority=LearningPriority.HIGH,
            title='Process Learning',
            description='Test',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now()
        )
        
        evolution_type = org_learning._determine_evolution_type(process_learning, context)
        assert evolution_type == EvolutionTrigger.WORKFLOW_OPTIMIZATION
        
        # Template improvement
        template_learning = Learning(
            id='template_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Template Learning',
            description='Test',
            context={},
            tags=['template'],
            source='test',
            timestamp=datetime.now()
        )
        
        evolution_type = org_learning._determine_evolution_type(template_learning, context)
        assert evolution_type == EvolutionTrigger.TEMPLATE_IMPROVEMENT
    
    @pytest.mark.asyncio
    async def test_create_evolution(self, org_learning, sample_learning):
        """Test creating evolution from learning"""
        context = LearningContext(
            source=LearningSource.TEAM,
            impact_level=LearningImpact.TEAM,
            affected_entities=['agent_001', 'agent_002'],
            performance_before={'success_rate': 0.7},
            performance_after={'success_rate': 0.9},
            cost_benefit=0.3,
            risk_assessment='low',
            implementation_effort='medium',
            success_criteria=['improve success rate'],
            failure_modes=['parameter misconfiguration']
        )
        
        org_learning.learning_contexts[sample_learning.id] = context
        
        evolution = await org_learning._create_evolution(
            sample_learning,
            context,
            EvolutionTrigger.BEHAVIOR_UPDATE
        )
        
        assert evolution is not None
        assert evolution.trigger_type == EvolutionTrigger.BEHAVIOR_UPDATE
        assert evolution.target_entities == ['agent_001', 'agent_002']
        assert sample_learning.id in evolution.learning_ids
        assert evolution.status == 'pending'
        assert 'performance' in evolution.expected_impact
        assert 'rollback_steps' in evolution.rollback_plan
    
    @pytest.mark.asyncio
    async def test_update_behaviors(self, org_learning):
        """Test behavior update process"""
        # Create high-impact learning
        learning = Learning(
            id='high_impact_001',
            team_id='team_001',
            type=LearningType.BEHAVIORAL,
            priority=LearningPriority.HIGH,
            title='High Impact Learning',
            description='Learning with high impact',
            context={},
            tags=['behavior'],
            source='test',
            timestamp=datetime.now(),
            impact_score=0.8,  # High impact
            confidence=0.9
        )
        
        context = LearningContext(
            source=LearningSource.TEAM,
            impact_level=LearningImpact.TEAM,
            affected_entities=['agent_001'],
            performance_before={},
            performance_after={},
            cost_benefit=0.4,
            risk_assessment='low',
            implementation_effort='medium',
            success_criteria=[],
            failure_modes=[]
        )
        
        org_learning.learning_contexts[learning.id] = context
        
        # Mock the evolution application
        with patch.object(org_learning, '_apply_evolution', return_value=True):
            evolutions = await org_learning.update_behaviors([learning])
        
        assert len(evolutions) == 1
        evolution = evolutions[0]
        assert evolution.trigger_type == EvolutionTrigger.BEHAVIOR_UPDATE
        assert evolution.id in org_learning.evolutions
        assert org_learning.learning_metrics['successful_evolutions'] == 1
    
    def test_determine_category(self, org_learning):
        """Test learning categorization"""
        technical_learning = Learning(
            id='tech_001',
            team_id='team_001',
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title='Technical Learning',
            description='Test',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now()
        )
        
        assert org_learning._determine_category(technical_learning) == 'technical'
        
        process_learning = Learning(
            id='process_001',
            team_id='team_001',
            type=LearningType.PROCESS,
            priority=LearningPriority.HIGH,
            title='Process Learning',
            description='Test',
            context={},
            tags=[],
            source='test',
            timestamp=datetime.now()
        )
        
        assert org_learning._determine_category(process_learning) == 'process'
    
    @pytest.mark.asyncio
    async def test_create_knowledge_update(self, org_learning):
        """Test knowledge update creation"""
        learnings = []
        for i in range(3):
            learning = Learning(
                id=f'knowledge_test_{i}',
                team_id='team_001',
                type=LearningType.TECHNICAL,
                priority=LearningPriority.HIGH,
                title=f'Knowledge Learning {i}',
                description='Learning for knowledge base',
                context={},
                tags=['knowledge', 'technical'],
                source='test',
                timestamp=datetime.now(),
                confidence=0.8
            )
            learnings.append(learning)
            
            # Create context
            context = LearningContext(
                source=LearningSource.TEAM,
                impact_level=LearningImpact.TEAM,
                affected_entities=[f'entity_{i}'],
                performance_before={},
                performance_after={},
                cost_benefit=0.2,
                risk_assessment='low',
                implementation_effort='medium',
                success_criteria=[],
                failure_modes=[]
            )
            org_learning.learning_contexts[learning.id] = context
        
        patterns = []  # Empty patterns for test
        
        update = await org_learning._create_knowledge_update(
            'technical',
            learnings,
            patterns
        )
        
        assert update is not None
        assert update.category == 'technical'
        assert update.confidence == 0.8  # Average of learnings
        assert len(update.source_learnings) == 3
        assert 'knowledge' in update.tags
        assert 'technical' in update.tags
        assert 'entity_0' in update.applicability
        assert update.applicability['entity_0'] is True
    
    @pytest.mark.asyncio
    async def test_synthesize_knowledge_content(self, org_learning):
        """Test knowledge content synthesis"""
        learnings = []
        for i in range(3):
            learning = Learning(
                id=f'synthesis_test_{i}',
                team_id='team_001',
                type=LearningType.IMPROVEMENT,
                priority=LearningPriority.HIGH,
                title=f'Synthesis Learning {i}',
                description=f'Description for learning {i}',
                context={},
                tags=[],
                source='test',
                timestamp=datetime.now()
            )
            learnings.append(learning)
        
        content = await org_learning._synthesize_knowledge_content(learnings)
        
        assert '## Synthesized Knowledge' in content
        assert '### Key Insights' in content
        assert '### Recommendations' in content
        assert 'Synthesis Learning 0' in content
        assert 'Description for learning 0' in content
    
    def test_generate_learning_report(self, org_learning):
        """Test learning report generation"""
        # Add some test data
        sample_learning = Learning(
            id='report_test_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Report Test Learning',
            description='Learning for report test',
            context={},
            tags=['test', 'report'],
            source='test',
            timestamp=datetime.now(),
            impact_score=0.9,
            applied_count=3
        )
        
        org_learning.learnings['report_test_001'] = sample_learning
        org_learning.learning_metrics['total_learnings'] = 1
        org_learning.learning_metrics['applied_learnings'] = 3
        
        evolution = LearningEvolution(
            id='evolution_001',
            learning_ids=['report_test_001'],
            trigger_type=EvolutionTrigger.BEHAVIOR_UPDATE,
            target_entities=['agent_001'],
            changes={},
            expected_impact={},
            rollback_plan={},
            status='completed',
            timestamp=datetime.now()
        )
        
        org_learning.evolutions['evolution_001'] = evolution
        org_learning.learning_metrics['successful_evolutions'] = 1
        
        report = org_learning.generate_learning_report()
        
        assert '# Organizational Learning Report' in report
        assert 'Executive Summary' in report
        assert 'Total Learnings: 1' in report
        assert 'Applied Learnings: 3' in report
        assert 'Successful Evolutions: 1' in report
        assert 'Top Impact Learnings' in report
        assert 'Report Test Learning' in report
        assert 'Evolution Summary' in report
        assert 'behavior_update' in report
    
    def test_save_and_load_state(self, org_learning):
        """Test state persistence"""
        # Add test data
        sample_learning = Learning(
            id='persistence_001',
            team_id='team_001',
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title='Persistence Test',
            description='Test learning for persistence',
            context={},
            tags=['persistence'],
            source='test',
            timestamp=datetime.now(),
            impact_score=0.7
        )
        
        org_learning.learnings['persistence_001'] = sample_learning
        org_learning.learning_metrics['total_learnings'] = 1
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            org_learning.save_state(filepath)
            
            # Create new instance and load
            new_org_learning = OrganizationalLearning()
            new_org_learning.load_state(filepath)
            
            assert 'persistence_001' in new_org_learning.learnings
            loaded_learning = new_org_learning.learnings['persistence_001']
            assert loaded_learning.title == 'Persistence Test'
            assert loaded_learning.impact_score == 0.7
            assert new_org_learning.learning_metrics['total_learnings'] == 1
            
        finally:
            os.unlink(filepath)
    
    @pytest.mark.asyncio
    async def test_aggregate_learnings_integration(self, org_learning):
        """Test learning aggregation with mocked sources"""
        # Mock collection methods
        mock_team_learnings = [
            {
                'team_id': 'team_001',
                'type': 'improvement',
                'priority': 'high',
                'title': 'Team Learning 1',
                'description': 'Learning from team',
                'tags': ['team'],
                'impact_score': 0.8
            }
        ]
        
        with patch.object(org_learning, '_collect_team_learnings', return_value=mock_team_learnings):
            learnings = await org_learning.aggregate_learnings(
                sources=[LearningSource.TEAM],
                time_window=timedelta(days=1)
            )
        
        assert len(learnings) == 1
        learning = learnings[0]
        assert learning.title == 'Team Learning 1'
        assert learning.source == 'team'
        assert org_learning.learning_metrics['total_learnings'] == 1
        assert org_learning.learning_metrics['learning_velocity'] == 1.0  # 1 learning per day


# Test runner
if __name__ == "__main__":
    # Run simple validation tests
    async def run_tests():
        print("Running Organizational Learning Tests...")
        
        # Test initialization
        org_learning = OrganizationalLearning()
        print("✓ Initialization test passed")
        
        # Test learning processing
        sample_data = {
            'team_id': 'team_001',
            'type': 'improvement',
            'priority': 'high',
            'title': 'Test Learning',
            'description': 'Test description',
            'tags': ['test'],
            'impact_score': 0.8,
            'impact_level': 'team',
            'affected_entities': ['agent_001']
        }
        
        learning = await org_learning._process_learning(sample_data, LearningSource.TEAM)
        assert learning is not None
        print("✓ Learning processing test passed")
        
        # Test validation
        assert org_learning._validate_learning(learning) is True
        print("✓ Learning validation test passed")
        
        # Test report generation
        org_learning.learnings[learning.id] = learning
        report = org_learning.generate_learning_report()
        assert len(report) > 0
        print("✓ Report generation test passed")
        
        print("All tests passed! ✓")
    
    asyncio.run(run_tests())