"""
Sprint Retrospective Analyzer for Agile AI Company

This module provides comprehensive retrospective analysis including feedback collection,
sentiment analysis, pattern detection, improvement identification, and action item tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
import json
import statistics
from collections import defaultdict, Counter
import re


class FeedbackCategory(Enum):
    """Categories for retrospective feedback"""
    WENT_WELL = "went_well"
    WENT_WRONG = "went_wrong"
    IDEAS = "ideas"
    KUDOS = "kudos"
    ACTION_ITEMS = "action_items"


class Sentiment(Enum):
    """Sentiment analysis results"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class ActionItemStatus(Enum):
    """Status of action items"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class ActionItemPriority(Enum):
    """Priority levels for action items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class FeedbackItem:
    """Individual feedback item from a team member"""
    agent_id: str
    category: FeedbackCategory
    content: str
    sentiment: Optional[Sentiment] = None
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'category': self.category.value,
            'content': self.content,
            'sentiment': self.sentiment.value if self.sentiment else None,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ActionItem:
    """Action item from retrospective"""
    id: str
    title: str
    description: str
    assigned_to: Optional[str] = None
    created_by: str = ""
    priority: ActionItemPriority = ActionItemPriority.MEDIUM
    status: ActionItemStatus = ActionItemStatus.PENDING
    due_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    related_feedback: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'assigned_to': self.assigned_to,
            'created_by': self.created_by,
            'priority': self.priority.value,
            'status': self.status.value,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tags': self.tags,
            'related_feedback': self.related_feedback
        }
    
    def update_status(self, new_status: ActionItemStatus):
        """Update action item status"""
        self.status = new_status
        self.updated_at = datetime.now()
        if new_status == ActionItemStatus.COMPLETED:
            self.completed_at = datetime.now()


@dataclass
class ImprovementPattern:
    """Pattern detected across multiple retrospectives"""
    pattern_type: str
    description: str
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    affected_areas: List[str]
    suggested_actions: List[str]
    confidence: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'pattern_type': self.pattern_type,
            'description': self.description,
            'occurrences': self.occurrences,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'affected_areas': self.affected_areas,
            'suggested_actions': self.suggested_actions,
            'confidence': self.confidence
        }


@dataclass
class RetrospectiveReport:
    """Comprehensive retrospective report"""
    sprint_id: str
    team_id: str
    date: datetime
    participants: List[str]
    feedback_items: List[FeedbackItem]
    action_items: List[ActionItem]
    team_sentiment: Sentiment
    sentiment_scores: Dict[str, float]
    improvement_patterns: List[ImprovementPattern]
    key_themes: List[Tuple[str, int]]  # (theme, count)
    participation_rate: float
    action_item_completion_rate: float
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'sprint_id': self.sprint_id,
            'team_id': self.team_id,
            'date': self.date.isoformat(),
            'participants': self.participants,
            'feedback_items': [item.to_dict() for item in self.feedback_items],
            'action_items': [item.to_dict() for item in self.action_items],
            'team_sentiment': self.team_sentiment.value,
            'sentiment_scores': self.sentiment_scores,
            'improvement_patterns': [p.to_dict() for p in self.improvement_patterns],
            'key_themes': self.key_themes,
            'participation_rate': self.participation_rate,
            'action_item_completion_rate': self.action_item_completion_rate,
            'recommendations': self.recommendations
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = f"# Sprint Retrospective Report\n\n"
        md += f"**Sprint:** {self.sprint_id}\n"
        md += f"**Team:** {self.team_id}\n"
        md += f"**Date:** {self.date.strftime('%Y-%m-%d')}\n"
        md += f"**Participants:** {len(self.participants)} ({', '.join(self.participants)})\n"
        md += f"**Participation Rate:** {self.participation_rate:.1%}\n\n"
        
        # Team Sentiment
        md += f"## Team Sentiment: {self.team_sentiment.value.replace('_', ' ').title()}\n\n"
        md += "### Sentiment Breakdown\n"
        for sentiment, score in self.sentiment_scores.items():
            md += f"- {sentiment}: {score:.1%}\n"
        md += "\n"
        
        # Key Themes
        if self.key_themes:
            md += "## Key Themes\n\n"
            for theme, count in self.key_themes[:5]:
                md += f"- **{theme}** (mentioned {count} times)\n"
            md += "\n"
        
        # What Went Well
        went_well = [f for f in self.feedback_items if f.category == FeedbackCategory.WENT_WELL]
        if went_well:
            md += "## What Went Well 🎉\n\n"
            for item in went_well[:10]:
                md += f"- {item.content} (*{item.agent_id}*)\n"
            md += "\n"
        
        # What Could Be Improved
        went_wrong = [f for f in self.feedback_items if f.category == FeedbackCategory.WENT_WRONG]
        if went_wrong:
            md += "## What Could Be Improved 🔧\n\n"
            for item in went_wrong[:10]:
                md += f"- {item.content} (*{item.agent_id}*)\n"
            md += "\n"
        
        # Ideas
        ideas = [f for f in self.feedback_items if f.category == FeedbackCategory.IDEAS]
        if ideas:
            md += "## Ideas and Suggestions 💡\n\n"
            for item in ideas[:10]:
                md += f"- {item.content} (*{item.agent_id}*)\n"
            md += "\n"
        
        # Kudos
        kudos = [f for f in self.feedback_items if f.category == FeedbackCategory.KUDOS]
        if kudos:
            md += "## Kudos 👏\n\n"
            for item in kudos:
                md += f"- {item.content} (*from {item.agent_id}*)\n"
            md += "\n"
        
        # Action Items
        if self.action_items:
            md += "## Action Items 📋\n\n"
            md += f"**Completion Rate:** {self.action_item_completion_rate:.1%}\n\n"
            
            # Group by priority
            for priority in ActionItemPriority:
                priority_items = [a for a in self.action_items if a.priority == priority]
                if priority_items:
                    md += f"### {priority.value.title()} Priority\n\n"
                    for item in priority_items:
                        status_emoji = "✅" if item.status == ActionItemStatus.COMPLETED else "⏳"
                        md += f"- {status_emoji} **{item.title}**\n"
                        md += f"  - Assigned to: {item.assigned_to or 'Unassigned'}\n"
                        md += f"  - Status: {item.status.value}\n"
                        if item.due_date:
                            md += f"  - Due: {item.due_date.strftime('%Y-%m-%d')}\n"
                        md += "\n"
        
        # Improvement Patterns
        if self.improvement_patterns:
            md += "## Detected Patterns 📊\n\n"
            for pattern in self.improvement_patterns:
                md += f"### {pattern.pattern_type}\n"
                md += f"- **Description:** {pattern.description}\n"
                md += f"- **Occurrences:** {pattern.occurrences}\n"
                md += f"- **Confidence:** {pattern.confidence:.1%}\n"
                md += f"- **Affected Areas:** {', '.join(pattern.affected_areas)}\n"
                md += f"- **Suggested Actions:**\n"
                for action in pattern.suggested_actions:
                    md += f"  - {action}\n"
                md += "\n"
        
        # Recommendations
        if self.recommendations:
            md += "## Recommendations 🎯\n\n"
            for i, rec in enumerate(self.recommendations, 1):
                md += f"{i}. {rec}\n"
            md += "\n"
        
        md += "---\n"
        md += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return md


class RetrospectiveAnalyzer:
    """Main retrospective analysis system"""
    
    def __init__(self):
        self.feedback_history: List[FeedbackItem] = []
        self.action_items: Dict[str, ActionItem] = {}
        self.retrospective_history: List[RetrospectiveReport] = []
        self.pattern_detector = PatternDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.action_item_counter = 0
    
    def collect_feedback(self, agent_id: str, category: FeedbackCategory, 
                         content: str, tags: Optional[List[str]] = None) -> FeedbackItem:
        """Collect feedback from a team member"""
        sentiment = self.sentiment_analyzer.analyze(content)
        feedback = FeedbackItem(
            agent_id=agent_id,
            category=category,
            content=content,
            sentiment=sentiment,
            tags=tags or []
        )
        self.feedback_history.append(feedback)
        return feedback
    
    def create_action_item(self, title: str, description: str, 
                          assigned_to: Optional[str] = None,
                          priority: ActionItemPriority = ActionItemPriority.MEDIUM,
                          due_date: Optional[datetime] = None,
                          tags: Optional[List[str]] = None) -> ActionItem:
        """Create a new action item"""
        self.action_item_counter += 1
        action_id = f"AI-{self.action_item_counter:04d}"
        
        action_item = ActionItem(
            id=action_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
            due_date=due_date,
            tags=tags or []
        )
        
        self.action_items[action_id] = action_item
        return action_item
    
    def update_action_item_status(self, action_id: str, 
                                  new_status: ActionItemStatus) -> bool:
        """Update the status of an action item"""
        if action_id in self.action_items:
            self.action_items[action_id].update_status(new_status)
            return True
        return False
    
    def get_pending_action_items(self, assigned_to: Optional[str] = None) -> List[ActionItem]:
        """Get pending action items, optionally filtered by assignee"""
        items = [
            item for item in self.action_items.values()
            if item.status in [ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS]
        ]
        
        if assigned_to:
            items = [item for item in items if item.assigned_to == assigned_to]
        
        return sorted(items, key=lambda x: (x.priority.value, x.due_date or datetime.max))
    
    def analyze_retrospective(self, sprint_id: str, team_id: str,
                            feedback_items: List[FeedbackItem],
                            participants: List[str],
                            total_team_size: int) -> RetrospectiveReport:
        """Analyze retrospective and generate comprehensive report"""
        
        # Calculate team sentiment
        sentiments = [f.sentiment for f in feedback_items if f.sentiment]
        team_sentiment = self._calculate_overall_sentiment(sentiments)
        sentiment_scores = self._calculate_sentiment_distribution(sentiments)
        
        # Extract key themes
        key_themes = self._extract_themes(feedback_items)
        
        # Detect improvement patterns
        patterns = self.pattern_detector.detect_patterns(
            feedback_items, 
            self.feedback_history
        )
        
        # Calculate metrics
        participation_rate = len(participants) / total_team_size if total_team_size > 0 else 0
        
        completed_items = [
            item for item in self.action_items.values()
            if item.status == ActionItemStatus.COMPLETED
        ]
        total_items = len(self.action_items)
        completion_rate = len(completed_items) / total_items if total_items > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            feedback_items,
            patterns,
            team_sentiment,
            completion_rate
        )
        
        # Create report
        report = RetrospectiveReport(
            sprint_id=sprint_id,
            team_id=team_id,
            date=datetime.now(),
            participants=participants,
            feedback_items=feedback_items,
            action_items=list(self.action_items.values()),
            team_sentiment=team_sentiment,
            sentiment_scores=sentiment_scores,
            improvement_patterns=patterns,
            key_themes=key_themes,
            participation_rate=participation_rate,
            action_item_completion_rate=completion_rate,
            recommendations=recommendations
        )
        
        self.retrospective_history.append(report)
        return report
    
    def _calculate_overall_sentiment(self, sentiments: List[Sentiment]) -> Sentiment:
        """Calculate overall team sentiment"""
        if not sentiments:
            return Sentiment.NEUTRAL
        
        # Map sentiments to scores
        sentiment_scores = {
            Sentiment.VERY_POSITIVE: 2,
            Sentiment.POSITIVE: 1,
            Sentiment.NEUTRAL: 0,
            Sentiment.NEGATIVE: -1,
            Sentiment.VERY_NEGATIVE: -2
        }
        
        scores = [sentiment_scores[s] for s in sentiments]
        avg_score = statistics.mean(scores)
        
        # Map back to sentiment
        if avg_score >= 1.5:
            return Sentiment.VERY_POSITIVE
        elif avg_score >= 0.5:
            return Sentiment.POSITIVE
        elif avg_score >= -0.5:
            return Sentiment.NEUTRAL
        elif avg_score >= -1.5:
            return Sentiment.NEGATIVE
        else:
            return Sentiment.VERY_NEGATIVE
    
    def _calculate_sentiment_distribution(self, sentiments: List[Sentiment]) -> Dict[str, float]:
        """Calculate sentiment distribution"""
        if not sentiments:
            return {}
        
        counter = Counter(sentiments)
        total = len(sentiments)
        
        return {
            sentiment.value: count / total
            for sentiment, count in counter.items()
        }
    
    def _extract_themes(self, feedback_items: List[FeedbackItem]) -> List[Tuple[str, int]]:
        """Extract key themes from feedback"""
        # Combine all feedback content
        all_text = " ".join([f.content for f in feedback_items])
        
        # Simple theme extraction based on common keywords
        # In production, this would use more sophisticated NLP
        theme_keywords = {
            'communication': ['communication', 'communicate', 'discuss', 'meeting', 'sync'],
            'process': ['process', 'workflow', 'procedure', 'method', 'approach'],
            'quality': ['quality', 'bug', 'defect', 'testing', 'review'],
            'performance': ['performance', 'speed', 'slow', 'fast', 'efficient'],
            'collaboration': ['collaboration', 'teamwork', 'together', 'coordinate'],
            'planning': ['planning', 'plan', 'estimation', 'sprint', 'backlog'],
            'documentation': ['documentation', 'document', 'readme', 'comment'],
            'automation': ['automation', 'automate', 'manual', 'script'],
            'learning': ['learning', 'training', 'knowledge', 'skill'],
            'tools': ['tool', 'software', 'system', 'platform']
        }
        
        theme_counts = {}
        lower_text = all_text.lower()
        
        for theme, keywords in theme_keywords.items():
            count = sum(lower_text.count(keyword) for keyword in keywords)
            if count > 0:
                theme_counts[theme] = count
        
        # Sort by count
        return sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
    
    def _generate_recommendations(self, feedback_items: List[FeedbackItem],
                                 patterns: List[ImprovementPattern],
                                 team_sentiment: Sentiment,
                                 completion_rate: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Sentiment-based recommendations
        if team_sentiment in [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE]:
            recommendations.append(
                "Team morale appears low. Consider a team-building session or addressing specific concerns raised."
            )
        
        # Completion rate recommendations
        if completion_rate < 0.5:
            recommendations.append(
                "Action item completion rate is below 50%. Review action item assignments and priorities."
            )
        
        # Pattern-based recommendations
        for pattern in patterns[:3]:  # Top 3 patterns
            if pattern.suggested_actions:
                recommendations.append(pattern.suggested_actions[0])
        
        # Category-specific recommendations
        went_wrong = [f for f in feedback_items if f.category == FeedbackCategory.WENT_WRONG]
        if len(went_wrong) > len(feedback_items) * 0.5:
            recommendations.append(
                "High volume of issues reported. Consider a focused problem-solving session."
            )
        
        ideas = [f for f in feedback_items if f.category == FeedbackCategory.IDEAS]
        if len(ideas) > 5:
            recommendations.append(
                "Many improvement ideas suggested. Schedule an innovation workshop to explore them."
            )
        
        return recommendations
    
    def get_historical_trends(self, team_id: str, 
                            lookback_sprints: int = 5) -> Dict[str, Any]:
        """Analyze historical trends across retrospectives"""
        team_retros = [
            r for r in self.retrospective_history 
            if r.team_id == team_id
        ][-lookback_sprints:]
        
        if not team_retros:
            return {}
        
        trends = {
            'sentiment_trend': [r.team_sentiment.value for r in team_retros],
            'participation_trend': [r.participation_rate for r in team_retros],
            'completion_trend': [r.action_item_completion_rate for r in team_retros],
            'action_items_trend': [len(r.action_items) for r in team_retros],
            'recurring_themes': self._find_recurring_themes(team_retros)
        }
        
        return trends
    
    def _find_recurring_themes(self, reports: List[RetrospectiveReport]) -> List[str]:
        """Find themes that appear across multiple retrospectives"""
        theme_counter = Counter()
        
        for report in reports:
            for theme, _ in report.key_themes[:3]:  # Top 3 themes per retro
                theme_counter[theme] += 1
        
        # Return themes that appear in at least half the retrospectives
        min_occurrences = len(reports) / 2
        return [
            theme for theme, count in theme_counter.items()
            if count >= min_occurrences
        ]
    
    def export_to_json(self, report: RetrospectiveReport) -> str:
        """Export report to JSON"""
        return json.dumps(report.to_dict(), indent=2)
    
    def load_from_json(self, json_str: str) -> RetrospectiveReport:
        """Load report from JSON"""
        data = json.loads(json_str)
        
        # Reconstruct objects from dictionaries
        feedback_items = [
            FeedbackItem(
                agent_id=f['agent_id'],
                category=FeedbackCategory(f['category']),
                content=f['content'],
                sentiment=Sentiment(f['sentiment']) if f['sentiment'] else None,
                tags=f['tags'],
                timestamp=datetime.fromisoformat(f['timestamp'])
            )
            for f in data['feedback_items']
        ]
        
        action_items = [
            ActionItem(
                id=a['id'],
                title=a['title'],
                description=a['description'],
                assigned_to=a['assigned_to'],
                created_by=a['created_by'],
                priority=ActionItemPriority(a['priority']),
                status=ActionItemStatus(a['status']),
                due_date=datetime.fromisoformat(a['due_date']) if a['due_date'] else None,
                created_at=datetime.fromisoformat(a['created_at']),
                updated_at=datetime.fromisoformat(a['updated_at']),
                completed_at=datetime.fromisoformat(a['completed_at']) if a['completed_at'] else None,
                tags=a['tags'],
                related_feedback=a['related_feedback']
            )
            for a in data['action_items']
        ]
        
        patterns = [
            ImprovementPattern(
                pattern_type=p['pattern_type'],
                description=p['description'],
                occurrences=p['occurrences'],
                first_seen=datetime.fromisoformat(p['first_seen']),
                last_seen=datetime.fromisoformat(p['last_seen']),
                affected_areas=p['affected_areas'],
                suggested_actions=p['suggested_actions'],
                confidence=p['confidence']
            )
            for p in data['improvement_patterns']
        ]
        
        return RetrospectiveReport(
            sprint_id=data['sprint_id'],
            team_id=data['team_id'],
            date=datetime.fromisoformat(data['date']),
            participants=data['participants'],
            feedback_items=feedback_items,
            action_items=action_items,
            team_sentiment=Sentiment(data['team_sentiment']),
            sentiment_scores=data['sentiment_scores'],
            improvement_patterns=patterns,
            key_themes=[(t[0], t[1]) for t in data['key_themes']],
            participation_rate=data['participation_rate'],
            action_item_completion_rate=data['action_item_completion_rate'],
            recommendations=data['recommendations']
        )


class SentimentAnalyzer:
    """Simple sentiment analyzer for feedback"""
    
    def __init__(self):
        # Simple keyword-based sentiment analysis
        # In production, this would use a proper NLP model
        self.positive_words = {
            'good', 'great', 'excellent', 'awesome', 'fantastic', 'perfect',
            'happy', 'pleased', 'satisfied', 'successful', 'effective',
            'improved', 'better', 'best', 'love', 'amazing', 'wonderful'
        }
        
        self.negative_words = {
            'bad', 'poor', 'terrible', 'awful', 'horrible', 'worst',
            'unhappy', 'disappointed', 'frustrated', 'failed', 'ineffective',
            'problem', 'issue', 'difficult', 'hard', 'slow', 'blocked'
        }
        
        self.intensifiers = {
            'very', 'extremely', 'really', 'totally', 'absolutely', 'completely'
        }
    
    def analyze(self, text: str) -> Sentiment:
        """Analyze sentiment of text"""
        lower_text = text.lower()
        words = re.findall(r'\b\w+\b', lower_text)
        
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        intensifier_count = sum(1 for word in words if word in self.intensifiers)
        
        # Apply intensifiers
        if intensifier_count > 0:
            positive_count *= (1 + intensifier_count * 0.5)
            negative_count *= (1 + intensifier_count * 0.5)
        
        # Calculate sentiment score
        if positive_count > negative_count * 1.5:
            return Sentiment.VERY_POSITIVE if positive_count > 3 else Sentiment.POSITIVE
        elif negative_count > positive_count * 1.5:
            return Sentiment.VERY_NEGATIVE if negative_count > 3 else Sentiment.NEGATIVE
        else:
            return Sentiment.NEUTRAL


class PatternDetector:
    """Detect patterns in retrospective feedback"""
    
    def detect_patterns(self, current_feedback: List[FeedbackItem],
                        historical_feedback: List[FeedbackItem]) -> List[ImprovementPattern]:
        """Detect improvement patterns from feedback"""
        patterns = []
        
        # Combine current and historical feedback
        all_feedback = historical_feedback + current_feedback
        
        # Group feedback by category and extract common issues
        category_groups = defaultdict(list)
        for item in all_feedback:
            category_groups[item.category].append(item)
        
        # Analyze "went wrong" items for recurring issues
        if FeedbackCategory.WENT_WRONG in category_groups:
            wrong_items = category_groups[FeedbackCategory.WENT_WRONG]
            
            # Simple pattern detection based on keyword frequency
            issue_keywords = self._extract_issue_keywords(wrong_items)
            
            for keyword, occurrences in issue_keywords.items():
                if occurrences >= 3:  # Pattern threshold
                    pattern = ImprovementPattern(
                        pattern_type=f"Recurring {keyword} Issues",
                        description=f"Multiple team members reported issues related to {keyword}",
                        occurrences=occurrences,
                        first_seen=min(item.timestamp for item in wrong_items if keyword in item.content.lower()),
                        last_seen=max(item.timestamp for item in wrong_items if keyword in item.content.lower()),
                        affected_areas=[keyword],
                        suggested_actions=[
                            f"Conduct focused session on improving {keyword}",
                            f"Create action items to address {keyword} concerns"
                        ],
                        confidence=min(0.9, occurrences / 10)  # Confidence based on frequency
                    )
                    patterns.append(pattern)
        
        # Analyze sentiment patterns
        sentiment_pattern = self._detect_sentiment_pattern(all_feedback)
        if sentiment_pattern:
            patterns.append(sentiment_pattern)
        
        return patterns
    
    def _extract_issue_keywords(self, feedback_items: List[FeedbackItem]) -> Dict[str, int]:
        """Extract common keywords from feedback"""
        keyword_counts = Counter()
        
        # Common issue categories
        issue_categories = {
            'communication': ['communication', 'meeting', 'sync', 'discussion'],
            'testing': ['test', 'testing', 'qa', 'quality'],
            'deployment': ['deploy', 'deployment', 'release', 'production'],
            'documentation': ['document', 'documentation', 'readme'],
            'performance': ['slow', 'performance', 'speed', 'latency'],
            'planning': ['planning', 'estimation', 'sprint', 'story']
        }
        
        for item in feedback_items:
            lower_content = item.content.lower()
            for category, keywords in issue_categories.items():
                if any(keyword in lower_content for keyword in keywords):
                    keyword_counts[category] += 1
        
        return dict(keyword_counts)
    
    def _detect_sentiment_pattern(self, feedback_items: List[FeedbackItem]) -> Optional[ImprovementPattern]:
        """Detect patterns in team sentiment"""
        sentiments = [f.sentiment for f in feedback_items if f.sentiment]
        
        if not sentiments:
            return None
        
        negative_count = sum(1 for s in sentiments if s in [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE])
        negative_ratio = negative_count / len(sentiments)
        
        if negative_ratio > 0.4:  # 40% negative sentiment threshold
            return ImprovementPattern(
                pattern_type="Declining Team Morale",
                description="High percentage of negative sentiment in feedback",
                occurrences=negative_count,
                first_seen=min(f.timestamp for f in feedback_items if f.sentiment in [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE]),
                last_seen=max(f.timestamp for f in feedback_items if f.sentiment in [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE]),
                affected_areas=["team_morale", "motivation"],
                suggested_actions=[
                    "Schedule team morale session",
                    "Address root causes of dissatisfaction",
                    "Implement team recognition program"
                ],
                confidence=min(0.95, negative_ratio * 2)
            )
        
        return None


if __name__ == "__main__":
    # Example usage
    analyzer = RetrospectiveAnalyzer()
    
    # Collect feedback
    feedback1 = analyzer.collect_feedback(
        "agent-1",
        FeedbackCategory.WENT_WELL,
        "Great collaboration on the API implementation. Team communication was excellent.",
        ["collaboration", "api"]
    )
    
    feedback2 = analyzer.collect_feedback(
        "agent-2",
        FeedbackCategory.WENT_WRONG,
        "Testing was slow and we found bugs late in the sprint.",
        ["testing", "quality"]
    )
    
    feedback3 = analyzer.collect_feedback(
        "agent-3",
        FeedbackCategory.IDEAS,
        "We should automate more of our testing process to catch bugs earlier.",
        ["automation", "testing"]
    )
    
    feedback4 = analyzer.collect_feedback(
        "agent-1",
        FeedbackCategory.KUDOS,
        "Thanks to agent-2 for helping with the difficult deployment issue!",
        ["recognition"]
    )
    
    # Create action items
    action1 = analyzer.create_action_item(
        "Automate integration tests",
        "Set up automated integration testing in CI/CD pipeline",
        assigned_to="agent-3",
        priority=ActionItemPriority.HIGH,
        due_date=datetime.now() + timedelta(days=14)
    )
    
    # Analyze retrospective
    report = analyzer.analyze_retrospective(
        sprint_id="sprint-001",
        team_id="team-alpha",
        feedback_items=[feedback1, feedback2, feedback3, feedback4],
        participants=["agent-1", "agent-2", "agent-3"],
        total_team_size=5
    )
    
    # Generate reports
    print(report.to_markdown())
    print("\n" + "="*50 + "\n")
    print("JSON Export:")
    print(analyzer.export_to_json(report))