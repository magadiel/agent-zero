"""
Organizational Learning System for Continuous Improvement

This module implements comprehensive organizational learning that:
- Aggregates learnings from all teams and agents
- Identifies organizational patterns and insights
- Updates global knowledge base
- Distributes learnings across the organization
- Triggers behavior and workflow evolution
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
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from existing systems
from coordination.learning_synthesizer import (
    Learning, LearningType, LearningPriority, 
    Pattern, PatternType, LearningSynthesizer
)


class LearningSource(Enum):
    """Sources of organizational learning"""
    TEAM = "team"
    AGENT = "agent"
    WORKFLOW = "workflow"
    RETROSPECTIVE = "retrospective"
    INCIDENT = "incident"
    EXPERIMENT = "experiment"
    CUSTOMER_FEEDBACK = "customer_feedback"
    PERFORMANCE_METRICS = "performance_metrics"


class LearningImpact(Enum):
    """Impact levels of learnings"""
    INDIVIDUAL = "individual"
    TEAM = "team"
    DEPARTMENT = "department"
    ORGANIZATION = "organization"


class EvolutionTrigger(Enum):
    """Types of evolution that can be triggered"""
    BEHAVIOR_UPDATE = "behavior_update"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    TEMPLATE_IMPROVEMENT = "template_improvement"
    PROCESS_CHANGE = "process_change"
    TOOL_ENHANCEMENT = "tool_enhancement"
    SKILL_DEVELOPMENT = "skill_development"


@dataclass
class LearningContext:
    """Extended context for organizational learning"""
    source: LearningSource
    impact_level: LearningImpact
    affected_entities: List[str]  # IDs of affected agents/teams/workflows
    performance_before: Dict[str, float]
    performance_after: Dict[str, float]
    cost_benefit: float  # ROI of applying this learning
    risk_assessment: str
    implementation_effort: str  # low, medium, high
    success_criteria: List[str]
    failure_modes: List[str]


@dataclass
class LearningEvolution:
    """Represents an evolution triggered by learning"""
    id: str
    learning_ids: List[str]
    trigger_type: EvolutionTrigger
    target_entities: List[str]
    changes: Dict[str, Any]
    expected_impact: Dict[str, float]
    rollback_plan: Dict[str, Any]
    status: str  # pending, in_progress, completed, rolled_back
    timestamp: datetime
    validation_results: Optional[Dict[str, Any]] = None


@dataclass
class KnowledgeUpdate:
    """Represents an update to the organizational knowledge base"""
    id: str
    category: str
    subcategory: str
    title: str
    content: str
    source_learnings: List[str]
    confidence: float
    version: int
    timestamp: datetime
    tags: List[str]
    references: List[str]
    applicability: Dict[str, bool]  # Which teams/agents this applies to


class OrganizationalLearning:
    """
    Main class for organizational learning management
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize organizational learning system"""
        self.config = self._load_config(config_path)
        self.synthesizer = LearningSynthesizer()
        
        # Storage
        self.learnings: Dict[str, Learning] = {}
        self.evolutions: Dict[str, LearningEvolution] = {}
        self.knowledge_updates: Dict[str, KnowledgeUpdate] = {}
        self.learning_contexts: Dict[str, LearningContext] = {}
        
        # Metrics
        self.learning_metrics = {
            'total_learnings': 0,
            'applied_learnings': 0,
            'successful_evolutions': 0,
            'failed_evolutions': 0,
            'knowledge_updates': 0,
            'avg_impact_score': 0.0,
            'learning_velocity': 0.0
        }
        
        # Thresholds for triggering actions
        self.thresholds = {
            'evolution_confidence': 0.7,
            'knowledge_update_confidence': 0.8,
            'pattern_significance': 0.6,
            'rollback_threshold': 0.3
        }
        
        # Learning history for trend analysis
        self.learning_history: List[Tuple[datetime, str, float]] = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'learning_retention_days': 90,
            'max_learnings_per_source': 1000,
            'evolution_batch_size': 10,
            'knowledge_update_frequency': 'daily',
            'distribution_strategy': 'broadcast',
            'validation_required': True
        }
    
    async def aggregate_learnings(self, 
                                 sources: Optional[List[LearningSource]] = None,
                                 time_window: Optional[timedelta] = None) -> List[Learning]:
        """
        Aggregate learnings from multiple sources
        """
        aggregated = []
        
        # Define sources to aggregate from
        if sources is None:
            sources = list(LearningSource)
        
        # Define time window
        if time_window is None:
            time_window = timedelta(days=7)
        
        cutoff_time = datetime.now() - time_window
        
        for source in sources:
            # Collect learnings from each source
            source_learnings = await self._collect_from_source(source, cutoff_time)
            
            # Process and validate learnings
            for learning_data in source_learnings:
                learning = await self._process_learning(learning_data, source)
                if learning and self._validate_learning(learning):
                    self.learnings[learning.id] = learning
                    aggregated.append(learning)
        
        # Update metrics
        self.learning_metrics['total_learnings'] = len(self.learnings)
        self.learning_metrics['learning_velocity'] = len(aggregated) / time_window.days
        
        # Identify patterns across aggregated learnings
        patterns = await self._identify_patterns(aggregated)
        
        # Trigger synthesis for cross-team patterns
        if patterns:
            await self.synthesizer.synthesize_patterns(patterns)
        
        return aggregated
    
    async def _collect_from_source(self, 
                                  source: LearningSource,
                                  cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from a specific source"""
        learnings = []
        
        if source == LearningSource.TEAM:
            # Collect from team retrospectives and reports
            learnings = await self._collect_team_learnings(cutoff_time)
        elif source == LearningSource.AGENT:
            # Collect from individual agent experiences
            learnings = await self._collect_agent_learnings(cutoff_time)
        elif source == LearningSource.WORKFLOW:
            # Collect from workflow executions
            learnings = await self._collect_workflow_learnings(cutoff_time)
        elif source == LearningSource.RETROSPECTIVE:
            # Collect from sprint retrospectives
            learnings = await self._collect_retrospective_learnings(cutoff_time)
        elif source == LearningSource.INCIDENT:
            # Collect from incident reports
            learnings = await self._collect_incident_learnings(cutoff_time)
        elif source == LearningSource.EXPERIMENT:
            # Collect from experiments and A/B tests
            learnings = await self._collect_experiment_learnings(cutoff_time)
        elif source == LearningSource.CUSTOMER_FEEDBACK:
            # Collect from customer feedback
            learnings = await self._collect_customer_learnings(cutoff_time)
        elif source == LearningSource.PERFORMANCE_METRICS:
            # Collect from performance metrics analysis
            learnings = await self._collect_metric_learnings(cutoff_time)
        
        return learnings
    
    async def _collect_team_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from team sources"""
        # This would integrate with team orchestrator
        # For now, return sample data
        return []
    
    async def _collect_agent_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from agent sources"""
        # This would integrate with agent memory systems
        return []
    
    async def _collect_workflow_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from workflow executions"""
        # This would integrate with workflow engine
        return []
    
    async def _collect_retrospective_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from retrospectives"""
        # This would integrate with retrospective analyzer
        return []
    
    async def _collect_incident_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from incidents"""
        return []
    
    async def _collect_experiment_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from experiments"""
        return []
    
    async def _collect_customer_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from customer feedback"""
        return []
    
    async def _collect_metric_learnings(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect learnings from performance metrics"""
        return []
    
    async def _process_learning(self, 
                               learning_data: Dict[str, Any],
                               source: LearningSource) -> Optional[Learning]:
        """Process raw learning data into Learning object"""
        try:
            # Generate unique ID
            learning_id = hashlib.md5(
                f"{source.value}_{datetime.now().isoformat()}_{json.dumps(learning_data)}".encode()
            ).hexdigest()[:12]
            
            # Create Learning object
            learning = Learning(
                id=learning_id,
                team_id=learning_data.get('team_id', 'unknown'),
                type=LearningType(learning_data.get('type', 'improvement')),
                priority=LearningPriority(learning_data.get('priority', 'medium')),
                title=learning_data.get('title', 'Untitled Learning'),
                description=learning_data.get('description', ''),
                context=learning_data.get('context', {}),
                tags=learning_data.get('tags', []),
                source=source.value,
                timestamp=datetime.now(),
                impact_score=learning_data.get('impact_score', 0.5),
                confidence=learning_data.get('confidence', 0.7)
            )
            
            # Create extended context
            context = LearningContext(
                source=source,
                impact_level=LearningImpact(learning_data.get('impact_level', 'team')),
                affected_entities=learning_data.get('affected_entities', []),
                performance_before=learning_data.get('performance_before', {}),
                performance_after=learning_data.get('performance_after', {}),
                cost_benefit=learning_data.get('cost_benefit', 0.0),
                risk_assessment=learning_data.get('risk_assessment', 'low'),
                implementation_effort=learning_data.get('implementation_effort', 'medium'),
                success_criteria=learning_data.get('success_criteria', []),
                failure_modes=learning_data.get('failure_modes', [])
            )
            
            self.learning_contexts[learning_id] = context
            
            return learning
            
        except Exception as e:
            print(f"Error processing learning: {e}")
            return None
    
    def _validate_learning(self, learning: Learning) -> bool:
        """Validate learning before acceptance"""
        # Check required fields
        if not learning.title or not learning.description:
            return False
        
        # Check confidence threshold
        if learning.confidence < 0.3:
            return False
        
        # Check for duplicates
        for existing in self.learnings.values():
            if self._is_duplicate(learning, existing):
                return False
        
        return True
    
    def _is_duplicate(self, learning1: Learning, learning2: Learning) -> bool:
        """Check if two learnings are duplicates"""
        # Simple similarity check - could be enhanced with NLP
        if learning1.title == learning2.title:
            return True
        
        # Check tag overlap
        tag_overlap = set(learning1.tags) & set(learning2.tags)
        if len(tag_overlap) > len(learning1.tags) * 0.8:
            return True
        
        return False
    
    async def _identify_patterns(self, learnings: List[Learning]) -> List[Pattern]:
        """Identify patterns across learnings"""
        patterns = []
        
        # Group learnings by type
        by_type = defaultdict(list)
        for learning in learnings:
            by_type[learning.type].append(learning)
        
        # Look for recurring themes
        for learning_type, group in by_type.items():
            if len(group) >= 3:  # Minimum for pattern
                pattern = await self._extract_pattern(group)
                if pattern:
                    patterns.append(pattern)
        
        # Look for anti-patterns
        failures = [l for l in learnings if l.type == LearningType.FAILURE]
        if len(failures) >= 2:
            anti_pattern = await self._extract_anti_pattern(failures)
            if anti_pattern:
                patterns.append(anti_pattern)
        
        return patterns
    
    async def _extract_pattern(self, learnings: List[Learning]) -> Optional[Pattern]:
        """Extract pattern from group of learnings"""
        # Analyze commonalities
        common_tags = Counter()
        for learning in learnings:
            common_tags.update(learning.tags)
        
        most_common = common_tags.most_common(3)
        if not most_common:
            return None
        
        # Create pattern
        pattern_id = hashlib.md5(
            f"pattern_{datetime.now().isoformat()}_{most_common}".encode()
        ).hexdigest()[:12]
        
        pattern = Pattern(
            id=pattern_id,
            type=PatternType.BEST_PRACTICE,
            name=f"Pattern: {most_common[0][0]}",
            description=f"Recurring pattern identified across {len(learnings)} learnings",
            learning_ids=[l.id for l in learnings],
            frequency=len(learnings),
            confidence=sum(l.confidence for l in learnings) / len(learnings),
            first_seen=min(l.timestamp for l in learnings),
            last_seen=max(l.timestamp for l in learnings),
            tags=[tag for tag, _ in most_common],
            recommendations=[]
        )
        
        return pattern
    
    async def _extract_anti_pattern(self, failures: List[Learning]) -> Optional[Pattern]:
        """Extract anti-pattern from failures"""
        if not failures:
            return None
        
        pattern_id = hashlib.md5(
            f"antipattern_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        pattern = Pattern(
            id=pattern_id,
            type=PatternType.ANTI_PATTERN,
            name="Recurring Failure Pattern",
            description=f"Anti-pattern identified from {len(failures)} failures",
            learning_ids=[f.id for f in failures],
            frequency=len(failures),
            confidence=0.9,
            first_seen=min(f.timestamp for f in failures),
            last_seen=max(f.timestamp for f in failures),
            tags=['failure', 'anti-pattern'],
            recommendations=["Avoid this pattern", "Implement preventive measures"]
        )
        
        return pattern
    
    async def update_behaviors(self, learnings: List[Learning]) -> List[LearningEvolution]:
        """
        Update agent behaviors based on learnings
        """
        evolutions = []
        
        # Group learnings by impact
        high_impact = [l for l in learnings if l.impact_score > 0.7]
        
        for learning in high_impact:
            context = self.learning_contexts.get(learning.id)
            if not context:
                continue
            
            # Determine evolution type
            evolution_type = self._determine_evolution_type(learning, context)
            
            if evolution_type:
                evolution = await self._create_evolution(
                    learning,
                    context,
                    evolution_type
                )
                
                if evolution:
                    self.evolutions[evolution.id] = evolution
                    evolutions.append(evolution)
                    
                    # Apply evolution
                    success = await self._apply_evolution(evolution)
                    
                    if success:
                        self.learning_metrics['successful_evolutions'] += 1
                    else:
                        self.learning_metrics['failed_evolutions'] += 1
        
        return evolutions
    
    def _determine_evolution_type(self, 
                                 learning: Learning,
                                 context: LearningContext) -> Optional[EvolutionTrigger]:
        """Determine what type of evolution to trigger"""
        if learning.type == LearningType.BEHAVIORAL:
            return EvolutionTrigger.BEHAVIOR_UPDATE
        elif learning.type == LearningType.PROCESS:
            return EvolutionTrigger.WORKFLOW_OPTIMIZATION
        elif learning.type == LearningType.TECHNICAL:
            return EvolutionTrigger.TOOL_ENHANCEMENT
        elif learning.type == LearningType.IMPROVEMENT:
            if 'template' in learning.tags:
                return EvolutionTrigger.TEMPLATE_IMPROVEMENT
            elif 'workflow' in learning.tags:
                return EvolutionTrigger.WORKFLOW_OPTIMIZATION
            else:
                return EvolutionTrigger.PROCESS_CHANGE
        
        return None
    
    async def _create_evolution(self,
                               learning: Learning,
                               context: LearningContext,
                               evolution_type: EvolutionTrigger) -> Optional[LearningEvolution]:
        """Create an evolution based on learning"""
        evolution_id = hashlib.md5(
            f"evolution_{learning.id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Determine changes based on evolution type
        changes = {}
        if evolution_type == EvolutionTrigger.BEHAVIOR_UPDATE:
            changes = {
                'behavior_modifications': self._generate_behavior_changes(learning),
                'agent_profiles': context.affected_entities
            }
        elif evolution_type == EvolutionTrigger.WORKFLOW_OPTIMIZATION:
            changes = {
                'workflow_updates': self._generate_workflow_changes(learning),
                'affected_workflows': context.affected_entities
            }
        elif evolution_type == EvolutionTrigger.TEMPLATE_IMPROVEMENT:
            changes = {
                'template_updates': self._generate_template_changes(learning),
                'affected_templates': context.affected_entities
            }
        
        evolution = LearningEvolution(
            id=evolution_id,
            learning_ids=[learning.id],
            trigger_type=evolution_type,
            target_entities=context.affected_entities,
            changes=changes,
            expected_impact={
                'performance': context.cost_benefit,
                'efficiency': learning.impact_score
            },
            rollback_plan=self._create_rollback_plan(changes),
            status='pending',
            timestamp=datetime.now()
        )
        
        return evolution
    
    def _generate_behavior_changes(self, learning: Learning) -> Dict[str, Any]:
        """Generate behavior modifications from learning"""
        return {
            'new_principles': [],
            'modified_responses': [],
            'enhanced_capabilities': [],
            'removed_behaviors': []
        }
    
    def _generate_workflow_changes(self, learning: Learning) -> Dict[str, Any]:
        """Generate workflow modifications from learning"""
        return {
            'optimized_steps': [],
            'removed_steps': [],
            'parallel_opportunities': [],
            'new_validations': []
        }
    
    def _generate_template_changes(self, learning: Learning) -> Dict[str, Any]:
        """Generate template modifications from learning"""
        return {
            'new_sections': [],
            'modified_sections': [],
            'removed_sections': [],
            'validation_rules': []
        }
    
    def _create_rollback_plan(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Create rollback plan for changes"""
        return {
            'backup_created': True,
            'rollback_steps': [],
            'validation_checks': [],
            'notification_list': []
        }
    
    async def _apply_evolution(self, evolution: LearningEvolution) -> bool:
        """Apply evolution to target entities"""
        try:
            evolution.status = 'in_progress'
            
            # Apply changes based on evolution type
            if evolution.trigger_type == EvolutionTrigger.BEHAVIOR_UPDATE:
                success = await self._apply_behavior_updates(evolution)
            elif evolution.trigger_type == EvolutionTrigger.WORKFLOW_OPTIMIZATION:
                success = await self._apply_workflow_updates(evolution)
            elif evolution.trigger_type == EvolutionTrigger.TEMPLATE_IMPROVEMENT:
                success = await self._apply_template_updates(evolution)
            else:
                success = await self._apply_generic_updates(evolution)
            
            if success:
                evolution.status = 'completed'
                
                # Mark related learnings as applied
                for learning_id in evolution.learning_ids:
                    if learning_id in self.learnings:
                        self.learnings[learning_id].applied_count += 1
                        self.learning_metrics['applied_learnings'] += 1
            else:
                evolution.status = 'failed'
                # Could trigger rollback here
            
            return success
            
        except Exception as e:
            print(f"Error applying evolution: {e}")
            evolution.status = 'failed'
            return False
    
    async def _apply_behavior_updates(self, evolution: LearningEvolution) -> bool:
        """Apply behavior updates to agents"""
        # This would integrate with behavior evolution system
        return True
    
    async def _apply_workflow_updates(self, evolution: LearningEvolution) -> bool:
        """Apply workflow optimizations"""
        # This would integrate with workflow engine
        return True
    
    async def _apply_template_updates(self, evolution: LearningEvolution) -> bool:
        """Apply template improvements"""
        # This would integrate with template system
        return True
    
    async def _apply_generic_updates(self, evolution: LearningEvolution) -> bool:
        """Apply generic updates"""
        return True
    
    async def evolve_workflows(self, patterns: List[Pattern]) -> List[Dict[str, Any]]:
        """
        Evolve workflows based on identified patterns
        """
        workflow_updates = []
        
        for pattern in patterns:
            if pattern.type in [PatternType.OPTIMIZATION, PatternType.BEST_PRACTICE]:
                # Generate workflow optimization
                update = await self._generate_workflow_optimization(pattern)
                if update:
                    workflow_updates.append(update)
            
            elif pattern.type == PatternType.ANTI_PATTERN:
                # Generate workflow correction
                correction = await self._generate_workflow_correction(pattern)
                if correction:
                    workflow_updates.append(correction)
        
        # Apply updates
        for update in workflow_updates:
            await self._apply_workflow_evolution(update)
        
        return workflow_updates
    
    async def _generate_workflow_optimization(self, pattern: Pattern) -> Optional[Dict[str, Any]]:
        """Generate workflow optimization from pattern"""
        return {
            'workflow_id': 'workflow_001',
            'optimization_type': 'parallel_execution',
            'changes': {
                'steps_to_parallelize': [],
                'estimated_time_saving': '30%'
            },
            'pattern_id': pattern.id
        }
    
    async def _generate_workflow_correction(self, pattern: Pattern) -> Optional[Dict[str, Any]]:
        """Generate workflow correction from anti-pattern"""
        return {
            'workflow_id': 'workflow_002',
            'correction_type': 'remove_bottleneck',
            'changes': {
                'bottleneck_step': 'step_5',
                'corrective_action': 'add_validation'
            },
            'pattern_id': pattern.id
        }
    
    async def _apply_workflow_evolution(self, update: Dict[str, Any]) -> bool:
        """Apply workflow evolution"""
        # This would integrate with workflow engine
        return True
    
    async def improve_templates(self, learnings: List[Learning]) -> List[Dict[str, Any]]:
        """
        Improve templates based on learnings
        """
        template_improvements = []
        
        # Filter learnings related to templates
        template_learnings = [l for l in learnings if 'template' in l.tags]
        
        for learning in template_learnings:
            improvement = await self._generate_template_improvement(learning)
            if improvement:
                template_improvements.append(improvement)
                
                # Apply improvement
                await self._apply_template_improvement(improvement)
        
        return template_improvements
    
    async def _generate_template_improvement(self, learning: Learning) -> Optional[Dict[str, Any]]:
        """Generate template improvement from learning"""
        return {
            'template_id': 'template_001',
            'improvement_type': 'add_section',
            'changes': {
                'new_section': {
                    'name': 'Risk Assessment',
                    'required': True,
                    'fields': []
                }
            },
            'learning_id': learning.id
        }
    
    async def _apply_template_improvement(self, improvement: Dict[str, Any]) -> bool:
        """Apply template improvement"""
        # This would integrate with template system
        return True
    
    async def update_knowledge_base(self, 
                                   learnings: List[Learning],
                                   patterns: List[Pattern]) -> List[KnowledgeUpdate]:
        """
        Update organizational knowledge base
        """
        knowledge_updates = []
        
        # Group learnings by category
        by_category = defaultdict(list)
        for learning in learnings:
            category = self._determine_category(learning)
            by_category[category].append(learning)
        
        # Create knowledge updates
        for category, category_learnings in by_category.items():
            if len(category_learnings) >= 2:  # Minimum for knowledge update
                update = await self._create_knowledge_update(
                    category,
                    category_learnings,
                    patterns
                )
                
                if update:
                    self.knowledge_updates[update.id] = update
                    knowledge_updates.append(update)
                    self.learning_metrics['knowledge_updates'] += 1
        
        # Distribute updates
        await self._distribute_knowledge_updates(knowledge_updates)
        
        return knowledge_updates
    
    def _determine_category(self, learning: Learning) -> str:
        """Determine knowledge category for learning"""
        if learning.type == LearningType.TECHNICAL:
            return 'technical'
        elif learning.type == LearningType.PROCESS:
            return 'process'
        elif learning.type == LearningType.BEHAVIORAL:
            return 'behavioral'
        else:
            return 'general'
    
    async def _create_knowledge_update(self,
                                      category: str,
                                      learnings: List[Learning],
                                      patterns: List[Pattern]) -> Optional[KnowledgeUpdate]:
        """Create knowledge update from learnings"""
        update_id = hashlib.md5(
            f"knowledge_{category}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Synthesize content from learnings
        content = await self._synthesize_knowledge_content(learnings)
        
        # Determine applicability
        applicability = {}
        for learning in learnings:
            context = self.learning_contexts.get(learning.id)
            if context:
                for entity in context.affected_entities:
                    applicability[entity] = True
        
        update = KnowledgeUpdate(
            id=update_id,
            category=category,
            subcategory=self._determine_subcategory(learnings),
            title=f"{category.title()} Knowledge Update",
            content=content,
            source_learnings=[l.id for l in learnings],
            confidence=sum(l.confidence for l in learnings) / len(learnings),
            version=1,
            timestamp=datetime.now(),
            tags=list(set(tag for l in learnings for tag in l.tags)),
            references=[],
            applicability=applicability
        )
        
        return update
    
    def _determine_subcategory(self, learnings: List[Learning]) -> str:
        """Determine subcategory from learnings"""
        # Simple implementation - could be enhanced
        if learnings:
            return learnings[0].type.value
        return 'general'
    
    async def _synthesize_knowledge_content(self, learnings: List[Learning]) -> str:
        """Synthesize knowledge content from multiple learnings"""
        content = "## Synthesized Knowledge\n\n"
        
        # Add key insights
        content += "### Key Insights\n"
        for learning in learnings[:5]:  # Top 5
            content += f"- {learning.title}: {learning.description}\n"
        
        # Add recommendations
        content += "\n### Recommendations\n"
        content += "Based on the aggregated learnings, we recommend:\n"
        content += "1. Apply these insights to similar scenarios\n"
        content += "2. Share with relevant teams\n"
        content += "3. Monitor for effectiveness\n"
        
        return content
    
    async def _distribute_knowledge_updates(self, updates: List[KnowledgeUpdate]) -> None:
        """Distribute knowledge updates across organization"""
        for update in updates:
            # Determine distribution list based on applicability
            recipients = list(update.applicability.keys())
            
            # Send updates (this would integrate with communication system)
            for recipient in recipients:
                await self._send_knowledge_update(recipient, update)
    
    async def _send_knowledge_update(self, recipient: str, update: KnowledgeUpdate) -> None:
        """Send knowledge update to recipient"""
        # This would integrate with team communication system
        pass
    
    def generate_learning_report(self) -> str:
        """Generate comprehensive learning report"""
        report = "# Organizational Learning Report\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n\n"
        
        # Executive Summary
        report += "## Executive Summary\n"
        report += f"- Total Learnings: {self.learning_metrics['total_learnings']}\n"
        report += f"- Applied Learnings: {self.learning_metrics['applied_learnings']}\n"
        report += f"- Successful Evolutions: {self.learning_metrics['successful_evolutions']}\n"
        report += f"- Knowledge Updates: {self.learning_metrics['knowledge_updates']}\n"
        report += f"- Learning Velocity: {self.learning_metrics['learning_velocity']:.2f} per day\n\n"
        
        # Top Learnings
        report += "## Top Impact Learnings\n"
        top_learnings = sorted(
            self.learnings.values(),
            key=lambda l: l.impact_score,
            reverse=True
        )[:10]
        
        for i, learning in enumerate(top_learnings, 1):
            report += f"{i}. **{learning.title}**\n"
            report += f"   - Type: {learning.type.value}\n"
            report += f"   - Impact: {learning.impact_score:.2f}\n"
            report += f"   - Applied: {learning.applied_count} times\n\n"
        
        # Evolution Summary
        report += "## Evolution Summary\n"
        by_trigger = defaultdict(list)
        for evolution in self.evolutions.values():
            by_trigger[evolution.trigger_type].append(evolution)
        
        for trigger_type, evolutions in by_trigger.items():
            report += f"\n### {trigger_type.value}\n"
            report += f"- Total: {len(evolutions)}\n"
            completed = len([e for e in evolutions if e.status == 'completed'])
            report += f"- Completed: {completed}\n"
            report += f"- Success Rate: {(completed/len(evolutions)*100):.1f}%\n"
        
        # Knowledge Base Updates
        report += "\n## Knowledge Base Updates\n"
        for update in list(self.knowledge_updates.values())[:5]:
            report += f"- **{update.title}** (v{update.version})\n"
            report += f"  - Category: {update.category}/{update.subcategory}\n"
            report += f"  - Confidence: {update.confidence:.2f}\n"
            report += f"  - Tags: {', '.join(update.tags[:5])}\n\n"
        
        return report
    
    def save_state(self, filepath: str) -> None:
        """Save organizational learning state"""
        state = {
            'learnings': {k: v.to_dict() for k, v in self.learnings.items()},
            'evolutions': {k: asdict(v) for k, v in self.evolutions.items()},
            'knowledge_updates': {k: asdict(v) for k, v in self.knowledge_updates.items()},
            'metrics': self.learning_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self, filepath: str) -> None:
        """Load organizational learning state"""
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Restore learnings
        for learning_id, learning_data in state.get('learnings', {}).items():
            self.learnings[learning_id] = Learning.from_dict(learning_data)
        
        # Restore metrics
        self.learning_metrics.update(state.get('metrics', {}))


# Example usage
async def main():
    """Example of using organizational learning system"""
    org_learning = OrganizationalLearning()
    
    # Aggregate learnings from past week
    learnings = await org_learning.aggregate_learnings(
        time_window=timedelta(days=7)
    )
    
    print(f"Aggregated {len(learnings)} learnings")
    
    # Update behaviors based on learnings
    evolutions = await org_learning.update_behaviors(learnings)
    print(f"Created {len(evolutions)} behavior evolutions")
    
    # Update knowledge base
    patterns = []  # Would come from pattern identification
    knowledge_updates = await org_learning.update_knowledge_base(learnings, patterns)
    print(f"Created {len(knowledge_updates)} knowledge updates")
    
    # Generate report
    report = org_learning.generate_learning_report()
    print("\n" + report)
    
    # Save state
    org_learning.save_state('learning_state.json')


if __name__ == "__main__":
    asyncio.run(main())