"""
Learning Synthesizer for Cross-Team Learning Aggregation

This module implements a comprehensive learning synthesis system that:
- Collects learnings from multiple teams
- Identifies patterns and insights
- Updates organizational knowledge base
- Distributes learnings across teams
- Generates learning reports
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
import re
from pathlib import Path


class LearningType(Enum):
    """Types of learnings that can be captured"""
    TECHNICAL = "technical"
    PROCESS = "process"
    BEHAVIORAL = "behavioral"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    FAILURE = "failure"
    SUCCESS = "success"
    IMPROVEMENT = "improvement"
    INNOVATION = "innovation"


class LearningPriority(Enum):
    """Priority levels for learnings"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatternType(Enum):
    """Types of patterns that can be identified"""
    RECURRING_ISSUE = "recurring_issue"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    OPTIMIZATION = "optimization"
    INNOVATION_OPPORTUNITY = "innovation_opportunity"
    RISK_FACTOR = "risk_factor"
    SUCCESS_FACTOR = "success_factor"


@dataclass
class Learning:
    """Represents a single learning item"""
    id: str
    team_id: str
    type: LearningType
    priority: LearningPriority
    title: str
    description: str
    context: Dict[str, Any]
    tags: List[str]
    source: str  # Where the learning came from (sprint, incident, experiment, etc.)
    timestamp: datetime
    impact_score: float = 0.0  # 0-1 score of impact
    confidence: float = 0.8  # 0-1 confidence level
    validated: bool = False
    applied_count: int = 0  # Number of times this learning has been applied
    related_learnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert learning to dictionary"""
        result = asdict(self)
        result['type'] = self.type.value
        result['priority'] = self.priority.value
        result['timestamp'] = self.timestamp.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Learning':
        """Create learning from dictionary"""
        data = data.copy()
        data['type'] = LearningType(data['type'])
        data['priority'] = LearningPriority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class Pattern:
    """Represents a pattern identified across learnings"""
    id: str
    type: PatternType
    name: str
    description: str
    supporting_learnings: List[str]  # IDs of learnings that support this pattern
    frequency: int  # How often this pattern appears
    teams_affected: Set[str]
    first_observed: datetime
    last_observed: datetime
    confidence: float  # 0-1 confidence in the pattern
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        result = asdict(self)
        result['type'] = self.type.value
        result['teams_affected'] = list(self.teams_affected)
        result['first_observed'] = self.first_observed.isoformat()
        result['last_observed'] = self.last_observed.isoformat()
        return result


@dataclass
class KnowledgeUpdate:
    """Represents an update to the knowledge base"""
    id: str
    category: str
    content: str
    source_learnings: List[str]
    timestamp: datetime
    version: int
    previous_version_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningReport:
    """Comprehensive learning report"""
    id: str
    period_start: datetime
    period_end: datetime
    total_learnings: int
    learnings_by_type: Dict[str, int]
    learnings_by_priority: Dict[str, int]
    learnings_by_team: Dict[str, int]
    patterns_identified: List[Pattern]
    top_insights: List[str]
    recommendations: List[str]
    knowledge_updates: List[KnowledgeUpdate]
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningSynthesizer:
    """
    Main learning synthesis system for cross-team learning aggregation
    """

    def __init__(self, knowledge_base_path: str = "./knowledge_base"):
        """
        Initialize the learning synthesizer
        
        Args:
            knowledge_base_path: Path to the knowledge base directory
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)
        
        self.learnings: Dict[str, Learning] = {}
        self.patterns: Dict[str, Pattern] = {}
        self.knowledge_updates: List[KnowledgeUpdate] = []
        self.team_learnings: Dict[str, List[str]] = defaultdict(list)
        
        # Pattern detection thresholds
        self.min_pattern_frequency = 3
        self.pattern_confidence_threshold = 0.7
        
        # Learning validation
        self.validation_queue: List[str] = []
        
        # Metrics
        self.metrics = {
            'total_learnings': 0,
            'patterns_identified': 0,
            'knowledge_updates': 0,
            'learnings_distributed': 0
        }
        
        self._lock = asyncio.Lock()
        self._load_existing_knowledge()

    def _load_existing_knowledge(self):
        """Load existing knowledge from the knowledge base"""
        try:
            # Load learnings
            learnings_file = self.knowledge_base_path / "learnings.json"
            if learnings_file.exists():
                with open(learnings_file, 'r') as f:
                    data = json.load(f)
                    for learning_data in data:
                        learning = Learning.from_dict(learning_data)
                        self.learnings[learning.id] = learning
                        self.team_learnings[learning.team_id].append(learning.id)
            
            # Load patterns
            patterns_file = self.knowledge_base_path / "patterns.json"
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                    for pattern_data in data:
                        pattern_data['type'] = PatternType(pattern_data['type'])
                        pattern_data['teams_affected'] = set(pattern_data['teams_affected'])
                        pattern_data['first_observed'] = datetime.fromisoformat(pattern_data['first_observed'])
                        pattern_data['last_observed'] = datetime.fromisoformat(pattern_data['last_observed'])
                        pattern = Pattern(**pattern_data)
                        self.patterns[pattern.id] = pattern
        except Exception as e:
            print(f"Error loading existing knowledge: {e}")

    async def collect_learning(self, learning: Learning) -> str:
        """
        Collect a new learning from a team
        
        Args:
            learning: The learning to collect
            
        Returns:
            Learning ID
        """
        async with self._lock:
            # Generate ID if not provided
            if not learning.id:
                learning.id = self._generate_learning_id(learning)
            
            # Store learning
            self.learnings[learning.id] = learning
            self.team_learnings[learning.team_id].append(learning.id)
            
            # Update metrics
            self.metrics['total_learnings'] += 1
            
            # Queue for validation if high priority
            if learning.priority in [LearningPriority.HIGH, LearningPriority.CRITICAL]:
                self.validation_queue.append(learning.id)
            
            # Check for patterns
            await self._check_for_patterns(learning)
            
            # Save to persistent storage
            await self._save_learnings()
            
            return learning.id

    async def collect_bulk_learnings(self, learnings: List[Learning]) -> List[str]:
        """
        Collect multiple learnings at once
        
        Args:
            learnings: List of learnings to collect
            
        Returns:
            List of learning IDs
        """
        ids = []
        for learning in learnings:
            learning_id = await self.collect_learning(learning)
            ids.append(learning_id)
        return ids

    async def identify_patterns(self) -> List[Pattern]:
        """
        Analyze all learnings to identify patterns
        
        Returns:
            List of identified patterns
        """
        async with self._lock:
            new_patterns = []
            
            # Group learnings by various dimensions
            by_type = self._group_learnings_by_type()
            by_tags = self._group_learnings_by_tags()
            by_context = self._group_learnings_by_context()
            
            # Identify recurring issues
            recurring_issues = await self._identify_recurring_issues(by_tags)
            new_patterns.extend(recurring_issues)
            
            # Identify best practices
            best_practices = await self._identify_best_practices(by_type)
            new_patterns.extend(best_practices)
            
            # Identify anti-patterns
            anti_patterns = await self._identify_anti_patterns()
            new_patterns.extend(anti_patterns)
            
            # Identify optimization opportunities
            optimizations = await self._identify_optimizations(by_context)
            new_patterns.extend(optimizations)
            
            # Store new patterns
            for pattern in new_patterns:
                if pattern.id not in self.patterns:
                    self.patterns[pattern.id] = pattern
                    self.metrics['patterns_identified'] += 1
            
            # Save patterns
            await self._save_patterns()
            
            return new_patterns

    async def _check_for_patterns(self, learning: Learning):
        """Check if a new learning contributes to existing patterns"""
        for pattern in self.patterns.values():
            # Check if learning relates to this pattern
            similarity = self._calculate_similarity(learning, pattern)
            if similarity > 0.7:
                pattern.supporting_learnings.append(learning.id)
                pattern.frequency += 1
                pattern.teams_affected.add(learning.team_id)
                pattern.last_observed = learning.timestamp
                pattern.confidence = min(1.0, pattern.confidence + 0.05)

    def _calculate_similarity(self, learning: Learning, pattern: Pattern) -> float:
        """Calculate similarity between a learning and a pattern"""
        score = 0.0
        
        # Check tag overlap
        learning_tags = set(learning.tags)
        pattern_tags = set()
        for learning_id in pattern.supporting_learnings[:5]:  # Check first 5 learnings
            if learning_id in self.learnings:
                pattern_tags.update(self.learnings[learning_id].tags)
        
        if learning_tags and pattern_tags:
            overlap = len(learning_tags & pattern_tags)
            score += overlap / len(learning_tags | pattern_tags) * 0.4
        
        # Check type similarity
        pattern_types = Counter()
        for learning_id in pattern.supporting_learnings:
            if learning_id in self.learnings:
                pattern_types[self.learnings[learning_id].type] += 1
        
        if pattern_types and learning.type in pattern_types:
            score += 0.3
        
        # Check description similarity (simple keyword matching)
        learning_words = set(learning.description.lower().split())
        pattern_words = set(pattern.description.lower().split())
        if learning_words and pattern_words:
            overlap = len(learning_words & pattern_words)
            score += min(0.3, overlap * 0.05)
        
        return score

    async def _identify_recurring_issues(self, by_tags: Dict[str, List[Learning]]) -> List[Pattern]:
        """Identify recurring issues from tagged learnings"""
        patterns = []
        
        for tag, learnings in by_tags.items():
            # Filter for failure/issue related learnings
            issue_learnings = [l for l in learnings if l.type in [LearningType.FAILURE, LearningType.IMPROVEMENT]]
            
            if len(issue_learnings) >= self.min_pattern_frequency:
                pattern = Pattern(
                    id=f"pattern_recurring_{tag}_{datetime.now().timestamp()}",
                    type=PatternType.RECURRING_ISSUE,
                    name=f"Recurring issue: {tag}",
                    description=f"Multiple teams experiencing issues related to {tag}",
                    supporting_learnings=[l.id for l in issue_learnings],
                    frequency=len(issue_learnings),
                    teams_affected=set(l.team_id for l in issue_learnings),
                    first_observed=min(l.timestamp for l in issue_learnings),
                    last_observed=max(l.timestamp for l in issue_learnings),
                    confidence=min(1.0, len(issue_learnings) / 10),
                    recommendations=[
                        f"Investigate root cause of {tag} issues",
                        f"Create standard solution for {tag}",
                        f"Share mitigation strategies across teams"
                    ]
                )
                patterns.append(pattern)
        
        return patterns

    async def _identify_best_practices(self, by_type: Dict[LearningType, List[Learning]]) -> List[Pattern]:
        """Identify best practices from successful learnings"""
        patterns = []
        
        success_learnings = by_type.get(LearningType.SUCCESS, [])
        
        # Group by similar contexts
        context_groups = defaultdict(list)
        for learning in success_learnings:
            context_key = self._get_context_key(learning.context)
            context_groups[context_key].append(learning)
        
        for context_key, learnings in context_groups.items():
            if len(learnings) >= self.min_pattern_frequency:
                pattern = Pattern(
                    id=f"pattern_best_practice_{context_key}_{datetime.now().timestamp()}",
                    type=PatternType.BEST_PRACTICE,
                    name=f"Best practice in {context_key}",
                    description=f"Successful approach identified across multiple teams",
                    supporting_learnings=[l.id for l in learnings],
                    frequency=len(learnings),
                    teams_affected=set(l.team_id for l in learnings),
                    first_observed=min(l.timestamp for l in learnings),
                    last_observed=max(l.timestamp for l in learnings),
                    confidence=min(1.0, len(learnings) / 5),
                    recommendations=[
                        f"Document this best practice",
                        f"Train other teams on this approach",
                        f"Create templates based on this practice"
                    ]
                )
                patterns.append(pattern)
        
        return patterns

    async def _identify_anti_patterns(self) -> List[Pattern]:
        """Identify anti-patterns from failure learnings"""
        patterns = []
        
        failure_learnings = [l for l in self.learnings.values() if l.type == LearningType.FAILURE]
        
        # Group by similar descriptions
        description_groups = defaultdict(list)
        for learning in failure_learnings:
            key_words = self._extract_key_words(learning.description)
            for word in key_words:
                description_groups[word].append(learning)
        
        for keyword, learnings in description_groups.items():
            if len(learnings) >= self.min_pattern_frequency:
                pattern = Pattern(
                    id=f"pattern_anti_{keyword}_{datetime.now().timestamp()}",
                    type=PatternType.ANTI_PATTERN,
                    name=f"Anti-pattern: {keyword}",
                    description=f"Recurring failure pattern related to {keyword}",
                    supporting_learnings=[l.id for l in learnings],
                    frequency=len(learnings),
                    teams_affected=set(l.team_id for l in learnings),
                    first_observed=min(l.timestamp for l in learnings),
                    last_observed=max(l.timestamp for l in learnings),
                    confidence=min(1.0, len(learnings) / 7),
                    recommendations=[
                        f"Avoid approaches involving {keyword}",
                        f"Create guidelines to prevent this pattern",
                        f"Review existing processes for this anti-pattern"
                    ]
                )
                patterns.append(pattern)
        
        return patterns

    async def _identify_optimizations(self, by_context: Dict[str, List[Learning]]) -> List[Pattern]:
        """Identify optimization opportunities"""
        patterns = []
        
        for context, learnings in by_context.items():
            improvement_learnings = [l for l in learnings if l.type == LearningType.IMPROVEMENT]
            
            if len(improvement_learnings) >= 2:  # Lower threshold for optimizations
                pattern = Pattern(
                    id=f"pattern_optimization_{context}_{datetime.now().timestamp()}",
                    type=PatternType.OPTIMIZATION,
                    name=f"Optimization opportunity: {context}",
                    description=f"Multiple improvements identified in {context}",
                    supporting_learnings=[l.id for l in improvement_learnings],
                    frequency=len(improvement_learnings),
                    teams_affected=set(l.team_id for l in improvement_learnings),
                    first_observed=min(l.timestamp for l in improvement_learnings),
                    last_observed=max(l.timestamp for l in improvement_learnings),
                    confidence=min(1.0, len(improvement_learnings) / 4),
                    recommendations=[
                        f"Consolidate improvements in {context}",
                        f"Create optimization project for {context}",
                        f"Share optimization strategies across teams"
                    ]
                )
                patterns.append(pattern)
        
        return patterns

    async def update_knowledge_base(self, learnings_to_apply: List[str]) -> List[KnowledgeUpdate]:
        """
        Update the organizational knowledge base with validated learnings
        
        Args:
            learnings_to_apply: List of learning IDs to apply to knowledge base
            
        Returns:
            List of knowledge updates made
        """
        updates = []
        
        async with self._lock:
            for learning_id in learnings_to_apply:
                if learning_id not in self.learnings:
                    continue
                
                learning = self.learnings[learning_id]
                
                # Only apply validated or high-confidence learnings
                if not learning.validated and learning.confidence < 0.8:
                    continue
                
                # Create knowledge update
                category = self._determine_knowledge_category(learning)
                content = self._format_knowledge_content(learning)
                
                update = KnowledgeUpdate(
                    id=f"knowledge_{category}_{datetime.now().timestamp()}",
                    category=category,
                    content=content,
                    source_learnings=[learning_id],
                    timestamp=datetime.now(),
                    version=self._get_next_version(category)
                )
                
                # Save to knowledge base
                await self._save_knowledge_update(update)
                
                updates.append(update)
                self.knowledge_updates.append(update)
                self.metrics['knowledge_updates'] += 1
                
                # Mark learning as applied
                learning.applied_count += 1
        
        return updates

    def _determine_knowledge_category(self, learning: Learning) -> str:
        """Determine the knowledge category for a learning"""
        if learning.type == LearningType.TECHNICAL:
            return "technical_practices"
        elif learning.type == LearningType.PROCESS:
            return "process_improvements"
        elif learning.type in [LearningType.SUCCESS, LearningType.FAILURE]:
            return "case_studies"
        elif learning.type == LearningType.STRATEGIC:
            return "strategic_insights"
        else:
            return "general_knowledge"

    def _format_knowledge_content(self, learning: Learning) -> str:
        """Format learning content for knowledge base"""
        content = f"# {learning.title}\n\n"
        content += f"**Type**: {learning.type.value}\n"
        content += f"**Priority**: {learning.priority.value}\n"
        content += f"**Source**: {learning.source}\n"
        content += f"**Team**: {learning.team_id}\n\n"
        content += f"## Description\n{learning.description}\n\n"
        
        if learning.context:
            content += f"## Context\n"
            for key, value in learning.context.items():
                content += f"- **{key}**: {value}\n"
            content += "\n"
        
        if learning.tags:
            content += f"## Tags\n{', '.join(learning.tags)}\n\n"
        
        content += f"---\n*Captured: {learning.timestamp.isoformat()}*\n"
        content += f"*Confidence: {learning.confidence:.2f}*\n"
        content += f"*Impact Score: {learning.impact_score:.2f}*\n"
        
        return content

    async def _save_knowledge_update(self, update: KnowledgeUpdate):
        """Save a knowledge update to the knowledge base"""
        category_dir = self.knowledge_base_path / update.category
        category_dir.mkdir(exist_ok=True)
        
        filename = f"{update.id}.md"
        filepath = category_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(update.content)
        
        # Also save metadata
        metadata_file = category_dir / f"{update.id}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'id': update.id,
                'category': update.category,
                'source_learnings': update.source_learnings,
                'timestamp': update.timestamp.isoformat(),
                'version': update.version,
                'previous_version_id': update.previous_version_id,
                'metadata': update.metadata
            }, f, indent=2)

    async def distribute_learnings(self, team_ids: List[str], learning_ids: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Distribute relevant learnings to specified teams
        
        Args:
            team_ids: List of team IDs to distribute to
            learning_ids: Specific learnings to distribute (if None, distribute relevant ones)
            
        Returns:
            Dictionary mapping team_id to list of distributed learning IDs
        """
        distribution = defaultdict(list)
        
        async with self._lock:
            if learning_ids is None:
                # Select relevant learnings for each team
                learning_ids = await self._select_relevant_learnings(team_ids)
            
            for team_id in team_ids:
                relevant_learnings = []
                
                for learning_id in learning_ids:
                    if learning_id not in self.learnings:
                        continue
                    
                    learning = self.learnings[learning_id]
                    
                    # Don't distribute team's own learnings back to them
                    if learning.team_id == team_id:
                        continue
                    
                    # Check relevance
                    if self._is_relevant_for_team(learning, team_id):
                        relevant_learnings.append(learning_id)
                        self.metrics['learnings_distributed'] += 1
                
                distribution[team_id] = relevant_learnings
        
        return distribution

    async def _select_relevant_learnings(self, team_ids: List[str]) -> List[str]:
        """Select relevant learnings for distribution"""
        # Select high-priority and recent learnings
        relevant = []
        
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for learning in self.learnings.values():
            if learning.timestamp > cutoff_date and learning.priority in [LearningPriority.HIGH, LearningPriority.CRITICAL]:
                relevant.append(learning.id)
        
        # Also include learnings from identified patterns
        for pattern in self.patterns.values():
            if pattern.confidence > self.pattern_confidence_threshold:
                relevant.extend(pattern.supporting_learnings[:2])  # Top 2 from each pattern
        
        return list(set(relevant))  # Remove duplicates

    def _is_relevant_for_team(self, learning: Learning, team_id: str) -> bool:
        """Check if a learning is relevant for a specific team"""
        # For now, distribute all high-priority learnings
        # In practice, this would check team profiles, current work, etc.
        return learning.priority in [LearningPriority.HIGH, LearningPriority.CRITICAL]

    async def generate_insights_report(self, 
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None,
                                      team_ids: Optional[List[str]] = None) -> LearningReport:
        """
        Generate a comprehensive learning insights report
        
        Args:
            start_date: Start of reporting period (default: 30 days ago)
            end_date: End of reporting period (default: now)
            team_ids: Specific teams to include (default: all teams)
            
        Returns:
            Comprehensive learning report
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        async with self._lock:
            # Filter learnings by date and team
            filtered_learnings = []
            for learning in self.learnings.values():
                if start_date <= learning.timestamp <= end_date:
                    if team_ids is None or learning.team_id in team_ids:
                        filtered_learnings.append(learning)
            
            # Calculate statistics
            learnings_by_type = Counter(l.type.value for l in filtered_learnings)
            learnings_by_priority = Counter(l.priority.value for l in filtered_learnings)
            learnings_by_team = Counter(l.team_id for l in filtered_learnings)
            
            # Get relevant patterns
            relevant_patterns = []
            for pattern in self.patterns.values():
                if start_date <= pattern.last_observed <= end_date:
                    if team_ids is None or any(team in team_ids for team in pattern.teams_affected):
                        relevant_patterns.append(pattern)
            
            # Generate top insights
            top_insights = self._generate_top_insights(filtered_learnings, relevant_patterns)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(filtered_learnings, relevant_patterns)
            
            # Get knowledge updates in period
            period_updates = [u for u in self.knowledge_updates
                            if start_date <= u.timestamp <= end_date]
            
            report = LearningReport(
                id=f"report_{start_date.date()}_{end_date.date()}",
                period_start=start_date,
                period_end=end_date,
                total_learnings=len(filtered_learnings),
                learnings_by_type=dict(learnings_by_type),
                learnings_by_priority=dict(learnings_by_priority),
                learnings_by_team=dict(learnings_by_team),
                patterns_identified=relevant_patterns,
                top_insights=top_insights,
                recommendations=recommendations,
                knowledge_updates=period_updates,
                metadata={
                    'generated_at': datetime.now().isoformat(),
                    'team_filter': team_ids,
                    'total_patterns': len(relevant_patterns)
                }
            )
            
            return report

    def _generate_top_insights(self, learnings: List[Learning], patterns: List[Pattern]) -> List[str]:
        """Generate top insights from learnings and patterns"""
        insights = []
        
        # Most common learning type
        if learnings:
            type_counts = Counter(l.type for l in learnings)
            most_common_type = type_counts.most_common(1)[0]
            insights.append(f"Most common learning type: {most_common_type[0].value} ({most_common_type[1]} occurrences)")
        
        # High-impact learnings
        high_impact = [l for l in learnings if l.impact_score > 0.8]
        if high_impact:
            insights.append(f"{len(high_impact)} high-impact learnings identified")
        
        # Critical patterns
        critical_patterns = [p for p in patterns if p.confidence > 0.9]
        if critical_patterns:
            insights.append(f"{len(critical_patterns)} critical patterns detected with high confidence")
        
        # Teams with most learnings
        if learnings:
            team_counts = Counter(l.team_id for l in learnings)
            top_team = team_counts.most_common(1)[0]
            insights.append(f"Team {top_team[0]} generated the most learnings ({top_team[1]})")
        
        # Recurring issues
        recurring = [p for p in patterns if p.type == PatternType.RECURRING_ISSUE]
        if recurring:
            insights.append(f"{len(recurring)} recurring issues identified across teams")
        
        return insights

    def _generate_recommendations(self, learnings: List[Learning], patterns: List[Pattern]) -> List[str]:
        """Generate recommendations based on learnings and patterns"""
        recommendations = []
        
        # Recommendations from patterns
        for pattern in patterns[:3]:  # Top 3 patterns
            recommendations.extend(pattern.recommendations)
        
        # High-priority unvalidated learnings
        unvalidated = [l for l in learnings if not l.validated and l.priority == LearningPriority.CRITICAL]
        if unvalidated:
            recommendations.append(f"Validate {len(unvalidated)} critical learnings")
        
        # Teams with many failures
        failure_counts = Counter(l.team_id for l in learnings if l.type == LearningType.FAILURE)
        if failure_counts:
            top_failure_team = failure_counts.most_common(1)[0]
            if top_failure_team[1] > 5:
                recommendations.append(f"Provide additional support to team {top_failure_team[0]}")
        
        # Knowledge gaps
        type_counts = Counter(l.type for l in learnings)
        if LearningType.TECHNICAL not in type_counts or type_counts[LearningType.TECHNICAL] < 3:
            recommendations.append("Increase focus on capturing technical learnings")
        
        return list(set(recommendations))[:10]  # Top 10 unique recommendations

    def _group_learnings_by_type(self) -> Dict[LearningType, List[Learning]]:
        """Group learnings by type"""
        groups = defaultdict(list)
        for learning in self.learnings.values():
            groups[learning.type].append(learning)
        return dict(groups)

    def _group_learnings_by_tags(self) -> Dict[str, List[Learning]]:
        """Group learnings by tags"""
        groups = defaultdict(list)
        for learning in self.learnings.values():
            for tag in learning.tags:
                groups[tag].append(learning)
        return dict(groups)

    def _group_learnings_by_context(self) -> Dict[str, List[Learning]]:
        """Group learnings by context keys"""
        groups = defaultdict(list)
        for learning in self.learnings.values():
            context_key = self._get_context_key(learning.context)
            groups[context_key].append(learning)
        return dict(groups)

    def _get_context_key(self, context: Dict[str, Any]) -> str:
        """Generate a key from context for grouping"""
        if not context:
            return "unknown"
        
        # Use the first key-value pair as the context key
        # In practice, this would be more sophisticated
        key_parts = []
        for k, v in list(context.items())[:2]:
            key_parts.append(f"{k}_{v}")
        
        return "_".join(key_parts) if key_parts else "unknown"

    def _extract_key_words(self, text: str) -> List[str]:
        """Extract key words from text for pattern matching"""
        # Simple keyword extraction - in practice, use NLP
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return keywords[:5]  # Top 5 keywords

    def _generate_learning_id(self, learning: Learning) -> str:
        """Generate a unique ID for a learning"""
        content = f"{learning.team_id}_{learning.title}_{learning.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _get_next_version(self, category: str) -> int:
        """Get the next version number for a knowledge category"""
        category_dir = self.knowledge_base_path / category
        if not category_dir.exists():
            return 1
        
        # Find highest version
        max_version = 0
        for file in category_dir.glob("*_metadata.json"):
            with open(file, 'r') as f:
                metadata = json.load(f)
                max_version = max(max_version, metadata.get('version', 0))
        
        return max_version + 1

    async def _save_learnings(self):
        """Save learnings to persistent storage"""
        learnings_file = self.knowledge_base_path / "learnings.json"
        learnings_data = [learning.to_dict() for learning in self.learnings.values()]
        
        with open(learnings_file, 'w') as f:
            json.dump(learnings_data, f, indent=2)

    async def _save_patterns(self):
        """Save patterns to persistent storage"""
        patterns_file = self.knowledge_base_path / "patterns.json"
        patterns_data = [pattern.to_dict() for pattern in self.patterns.values()]
        
        with open(patterns_file, 'w') as f:
            json.dump(patterns_data, f, indent=2)

    async def validate_learning(self, learning_id: str, validated: bool, validator_id: str) -> bool:
        """
        Validate or reject a learning
        
        Args:
            learning_id: ID of learning to validate
            validated: Whether the learning is validated
            validator_id: ID of the validator (team or agent)
            
        Returns:
            Success status
        """
        async with self._lock:
            if learning_id not in self.learnings:
                return False
            
            learning = self.learnings[learning_id]
            learning.validated = validated
            learning.metadata['validator'] = validator_id
            learning.metadata['validation_time'] = datetime.now().isoformat()
            
            if learning_id in self.validation_queue:
                self.validation_queue.remove(learning_id)
            
            await self._save_learnings()
            return True

    def export_report(self, report: LearningReport, format: str = 'markdown') -> str:
        """
        Export a learning report in various formats
        
        Args:
            report: The report to export
            format: Export format ('markdown', 'json', 'html')
            
        Returns:
            Formatted report string
        """
        if format == 'json':
            return self._export_report_json(report)
        elif format == 'html':
            return self._export_report_html(report)
        else:  # markdown
            return self._export_report_markdown(report)

    def _export_report_markdown(self, report: LearningReport) -> str:
        """Export report as markdown"""
        md = f"# Learning Synthesis Report\n\n"
        md += f"**Report ID**: {report.id}\n"
        md += f"**Period**: {report.period_start.date()} to {report.period_end.date()}\n\n"
        
        md += f"## Summary\n"
        md += f"- **Total Learnings**: {report.total_learnings}\n"
        md += f"- **Patterns Identified**: {len(report.patterns_identified)}\n"
        md += f"- **Knowledge Updates**: {len(report.knowledge_updates)}\n\n"
        
        md += f"## Learnings by Type\n"
        for type_name, count in report.learnings_by_type.items():
            md += f"- {type_name}: {count}\n"
        md += "\n"
        
        md += f"## Learnings by Priority\n"
        for priority, count in report.learnings_by_priority.items():
            md += f"- {priority}: {count}\n"
        md += "\n"
        
        md += f"## Learnings by Team\n"
        for team, count in report.learnings_by_team.items():
            md += f"- {team}: {count}\n"
        md += "\n"
        
        md += f"## Top Insights\n"
        for insight in report.top_insights:
            md += f"- {insight}\n"
        md += "\n"
        
        md += f"## Patterns Identified\n"
        for pattern in report.patterns_identified[:5]:  # Top 5 patterns
            md += f"### {pattern.name}\n"
            md += f"- **Type**: {pattern.type.value}\n"
            md += f"- **Confidence**: {pattern.confidence:.2f}\n"
            md += f"- **Frequency**: {pattern.frequency}\n"
            md += f"- **Teams Affected**: {len(pattern.teams_affected)}\n\n"
        
        md += f"## Recommendations\n"
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"
        md += "\n"
        
        md += f"---\n*Generated: {datetime.now().isoformat()}*\n"
        
        return md

    def _export_report_json(self, report: LearningReport) -> str:
        """Export report as JSON"""
        data = {
            'id': report.id,
            'period_start': report.period_start.isoformat(),
            'period_end': report.period_end.isoformat(),
            'total_learnings': report.total_learnings,
            'learnings_by_type': report.learnings_by_type,
            'learnings_by_priority': report.learnings_by_priority,
            'learnings_by_team': report.learnings_by_team,
            'patterns_identified': [p.to_dict() for p in report.patterns_identified],
            'top_insights': report.top_insights,
            'recommendations': report.recommendations,
            'knowledge_updates': [
                {
                    'id': u.id,
                    'category': u.category,
                    'timestamp': u.timestamp.isoformat(),
                    'version': u.version
                } for u in report.knowledge_updates
            ],
            'metadata': report.metadata
        }
        return json.dumps(data, indent=2)

    def _export_report_html(self, report: LearningReport) -> str:
        """Export report as HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Learning Synthesis Report - {report.id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 1px solid #ccc; }}
                h3 {{ color: #888; }}
                .summary {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border: 1px solid #ddd; }}
                ul {{ list-style-type: none; padding-left: 0; }}
                li {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>Learning Synthesis Report</h1>
            <div class="summary">
                <p><strong>Report ID:</strong> {report.id}</p>
                <p><strong>Period:</strong> {report.period_start.date()} to {report.period_end.date()}</p>
                <div class="metric">
                    <strong>Total Learnings:</strong> {report.total_learnings}
                </div>
                <div class="metric">
                    <strong>Patterns:</strong> {len(report.patterns_identified)}
                </div>
                <div class="metric">
                    <strong>Knowledge Updates:</strong> {len(report.knowledge_updates)}
                </div>
            </div>
        """
        
        # Add more HTML content...
        html += """
        </body>
        </html>
        """
        
        return html

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            **self.metrics,
            'total_patterns': len(self.patterns),
            'pending_validations': len(self.validation_queue),
            'teams_with_learnings': len(self.team_learnings)
        }


# Standalone test
if __name__ == "__main__":
    async def test_learning_synthesizer():
        """Test the learning synthesizer"""
        synthesizer = LearningSynthesizer()
        
        # Create sample learnings
        learning1 = Learning(
            id="",
            team_id="team_alpha",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Database optimization technique",
            description="Using connection pooling reduced query latency by 40%",
            context={"area": "backend", "technology": "postgresql"},
            tags=["database", "performance", "optimization"],
            source="sprint_retrospective",
            timestamp=datetime.now(),
            impact_score=0.8
        )
        
        learning2 = Learning(
            id="",
            team_id="team_beta",
            type=LearningType.FAILURE,
            priority=LearningPriority.CRITICAL,
            title="Memory leak in worker process",
            description="Unclosed connections caused memory leak in background workers",
            context={"area": "backend", "component": "worker"},
            tags=["memory", "bug", "performance"],
            source="incident",
            timestamp=datetime.now() - timedelta(days=5),
            impact_score=0.9
        )
        
        learning3 = Learning(
            id="",
            team_id="team_gamma",
            type=LearningType.SUCCESS,
            priority=LearningPriority.MEDIUM,
            title="Agile adoption success",
            description="Daily standups improved team communication and reduced blockers",
            context={"area": "process", "methodology": "scrum"},
            tags=["agile", "communication", "process"],
            source="team_survey",
            timestamp=datetime.now() - timedelta(days=10),
            impact_score=0.7
        )
        
        # Collect learnings
        print("Collecting learnings...")
        ids = await synthesizer.collect_bulk_learnings([learning1, learning2, learning3])
        print(f"Collected {len(ids)} learnings: {ids}")
        
        # Identify patterns
        print("\nIdentifying patterns...")
        patterns = await synthesizer.identify_patterns()
        print(f"Identified {len(patterns)} patterns")
        for pattern in patterns:
            print(f"  - {pattern.name} (Type: {pattern.type.value}, Confidence: {pattern.confidence:.2f})")
        
        # Update knowledge base
        print("\nUpdating knowledge base...")
        updates = await synthesizer.update_knowledge_base(ids[:2])
        print(f"Created {len(updates)} knowledge updates")
        
        # Distribute learnings
        print("\nDistributing learnings...")
        distribution = await synthesizer.distribute_learnings(["team_delta", "team_epsilon"])
        for team, learnings in distribution.items():
            print(f"  Team {team}: {len(learnings)} learnings")
        
        # Generate report
        print("\nGenerating insights report...")
        report = await synthesizer.generate_insights_report()
        print(f"Report Summary:")
        print(f"  Total learnings: {report.total_learnings}")
        print(f"  Patterns identified: {len(report.patterns_identified)}")
        print(f"  Top insights: {len(report.top_insights)}")
        print(f"  Recommendations: {len(report.recommendations)}")
        
        # Export report
        print("\nExporting report as markdown...")
        markdown_report = synthesizer.export_report(report, 'markdown')
        print(markdown_report[:500] + "...")
        
        # Get metrics
        print("\nCurrent metrics:")
        metrics = synthesizer.get_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Learning synthesizer test completed successfully!")
    
    # Run the test
    asyncio.run(test_learning_synthesizer())