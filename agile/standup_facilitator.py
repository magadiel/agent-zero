"""
Daily Standup Facilitator for Agile AI Teams

This module provides automated daily standup ceremonies for AI agent teams,
including status collection, blocker identification, and progress tracking.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StandupItemType(Enum):
    """Types of standup items"""
    YESTERDAY = "yesterday"
    TODAY = "today"
    BLOCKERS = "blockers"
    HELP_NEEDED = "help_needed"


class BlockerSeverity(Enum):
    """Severity levels for blockers"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TeamMemberStatus:
    """Status report from a team member"""
    agent_id: str
    agent_name: str
    timestamp: datetime
    yesterday_completed: List[str] = field(default_factory=list)
    today_planned: List[str] = field(default_factory=list)
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    help_needed: List[str] = field(default_factory=list)
    current_story: Optional[str] = None
    story_progress: float = 0.0  # 0-100 percentage
    confidence_level: float = 1.0  # 0-1 confidence in meeting today's goals
    mood: str = "neutral"  # positive, neutral, concerned, frustrated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'timestamp': self.timestamp.isoformat(),
            'yesterday_completed': self.yesterday_completed,
            'today_planned': self.today_planned,
            'blockers': self.blockers,
            'help_needed': self.help_needed,
            'current_story': self.current_story,
            'story_progress': self.story_progress,
            'confidence_level': self.confidence_level,
            'mood': self.mood
        }


@dataclass
class Blocker:
    """Represents a blocker identified during standup"""
    id: str
    description: str
    severity: BlockerSeverity
    affected_agents: List[str]
    affected_stories: List[str]
    identified_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'description': self.description,
            'severity': self.severity.value,
            'affected_agents': self.affected_agents,
            'affected_stories': self.affected_stories,
            'identified_at': self.identified_at.isoformat(),
            'resolved': self.resolved,
            'resolution': self.resolution,
            'assigned_to': self.assigned_to
        }


@dataclass
class StandupReport:
    """Complete standup report"""
    standup_id: str
    team_id: str
    sprint_id: Optional[str]
    date: datetime
    duration_minutes: float
    participants: List[str]
    member_statuses: List[TeamMemberStatus]
    blockers: List[Blocker]
    team_mood: str
    sprint_progress: float
    risks_identified: List[str]
    help_requests: List[Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'standup_id': self.standup_id,
            'team_id': self.team_id,
            'sprint_id': self.sprint_id,
            'date': self.date.isoformat(),
            'duration_minutes': self.duration_minutes,
            'participants': self.participants,
            'member_statuses': [s.to_dict() for s in self.member_statuses],
            'blockers': [b.to_dict() for b in self.blockers],
            'team_mood': self.team_mood,
            'sprint_progress': self.sprint_progress,
            'risks_identified': self.risks_identified,
            'help_requests': self.help_requests,
            'action_items': self.action_items
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = []
        lines.append(f"# Daily Standup Report - {self.date.strftime('%Y-%m-%d')}")
        lines.append(f"\n**Team ID**: {self.team_id}")
        lines.append(f"**Sprint**: {self.sprint_id or 'No active sprint'}")
        lines.append(f"**Duration**: {self.duration_minutes:.1f} minutes")
        lines.append(f"**Participants**: {len(self.participants)}/{len(self.member_statuses)} present")
        lines.append(f"**Sprint Progress**: {self.sprint_progress:.1f}%")
        lines.append(f"**Team Mood**: {self.team_mood}")
        
        # Team member updates
        lines.append("\n## Team Member Updates")
        for status in self.member_statuses:
            lines.append(f"\n### {status.agent_name}")
            lines.append(f"**Current Story**: {status.current_story or 'None'}")
            lines.append(f"**Story Progress**: {status.story_progress:.0f}%")
            lines.append(f"**Confidence**: {status.confidence_level*100:.0f}%")
            lines.append(f"**Mood**: {status.mood}")
            
            if status.yesterday_completed:
                lines.append("\n**Yesterday Completed**:")
                for item in status.yesterday_completed:
                    lines.append(f"- ✅ {item}")
            
            if status.today_planned:
                lines.append("\n**Today Planned**:")
                for item in status.today_planned:
                    lines.append(f"- 🎯 {item}")
            
            if status.blockers:
                lines.append("\n**Blockers**:")
                for blocker in status.blockers:
                    severity_emoji = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(blocker.get('severity', 'medium'), '⚪')
                    lines.append(f"- {severity_emoji} {blocker['description']}")
            
            if status.help_needed:
                lines.append("\n**Help Needed**:")
                for help_item in status.help_needed:
                    lines.append(f"- 🤝 {help_item}")
        
        # Blockers summary
        if self.blockers:
            lines.append("\n## Blockers Summary")
            critical_blockers = [b for b in self.blockers if b.severity == BlockerSeverity.CRITICAL]
            high_blockers = [b for b in self.blockers if b.severity == BlockerSeverity.HIGH]
            
            if critical_blockers:
                lines.append("\n### 🔴 Critical Blockers")
                for blocker in critical_blockers:
                    lines.append(f"- {blocker.description}")
                    lines.append(f"  - Affects: {', '.join(blocker.affected_agents)}")
                    if blocker.assigned_to:
                        lines.append(f"  - Assigned to: {blocker.assigned_to}")
            
            if high_blockers:
                lines.append("\n### 🟠 High Priority Blockers")
                for blocker in high_blockers:
                    lines.append(f"- {blocker.description}")
                    lines.append(f"  - Affects: {', '.join(blocker.affected_agents)}")
        
        # Risks
        if self.risks_identified:
            lines.append("\n## Risks Identified")
            for risk in self.risks_identified:
                lines.append(f"- ⚠️ {risk}")
        
        # Action items
        if self.action_items:
            lines.append("\n## Action Items")
            for item in self.action_items:
                owner = item.get('owner', 'Unassigned')
                lines.append(f"- [ ] {item['description']} (@{owner})")
        
        # Help requests
        if self.help_requests:
            lines.append("\n## Help Requests")
            for request in self.help_requests:
                lines.append(f"- 🤝 **{request['from']}**: {request['description']}")
        
        return '\n'.join(lines)


class StandupFacilitator:
    """Facilitates daily standup ceremonies for AI agent teams"""
    
    def __init__(self, team_id: str, sprint_manager=None):
        """
        Initialize standup facilitator
        
        Args:
            team_id: ID of the team
            sprint_manager: Optional sprint manager for sprint data
        """
        self.team_id = team_id
        self.sprint_manager = sprint_manager
        self.standup_history: List[StandupReport] = []
        self.active_blockers: Dict[str, Blocker] = {}
        self.standup_counter = 0
    
    async def conduct_standup(self, 
                             team_members: List[Any],
                             collect_status_func=None) -> StandupReport:
        """
        Conduct a daily standup ceremony
        
        Args:
            team_members: List of team member agents
            collect_status_func: Optional async function to collect status from agent
        
        Returns:
            StandupReport with complete standup information
        """
        start_time = datetime.now()
        self.standup_counter += 1
        standup_id = f"standup_{self.team_id}_{self.standup_counter}"
        
        logger.info(f"Starting daily standup {standup_id} for team {self.team_id}")
        
        # Collect status from all team members
        member_statuses = []
        participants = []
        
        for member in team_members:
            try:
                if collect_status_func:
                    status = await collect_status_func(member)
                else:
                    status = await self._default_collect_status(member)
                
                if status:
                    member_statuses.append(status)
                    participants.append(status.agent_id)
                    logger.info(f"Collected status from {status.agent_name}")
            except Exception as e:
                logger.error(f"Failed to collect status from {member}: {e}")
        
        # Analyze blockers
        blockers = self._analyze_blockers(member_statuses)
        
        # Calculate team mood
        team_mood = self._calculate_team_mood(member_statuses)
        
        # Calculate sprint progress
        sprint_progress = await self._calculate_sprint_progress()
        
        # Identify risks
        risks = self._identify_risks(member_statuses, blockers)
        
        # Collect help requests
        help_requests = self._collect_help_requests(member_statuses)
        
        # Generate action items
        action_items = self._generate_action_items(blockers, help_requests)
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds() / 60
        
        # Get sprint ID
        sprint_id = None
        if self.sprint_manager and hasattr(self.sprint_manager, 'current_sprint'):
            sprint_id = getattr(self.sprint_manager.current_sprint, 'id', None)
        
        # Create report
        report = StandupReport(
            standup_id=standup_id,
            team_id=self.team_id,
            sprint_id=sprint_id,
            date=start_time,
            duration_minutes=duration,
            participants=participants,
            member_statuses=member_statuses,
            blockers=blockers,
            team_mood=team_mood,
            sprint_progress=sprint_progress,
            risks_identified=risks,
            help_requests=help_requests,
            action_items=action_items
        )
        
        # Store report
        self.standup_history.append(report)
        
        # Update active blockers
        for blocker in blockers:
            if not blocker.resolved:
                self.active_blockers[blocker.id] = blocker
        
        logger.info(f"Completed standup {standup_id} in {duration:.1f} minutes")
        
        return report
    
    async def _default_collect_status(self, member: Any) -> TeamMemberStatus:
        """
        Default status collection from a team member
        
        Args:
            member: Team member agent
        
        Returns:
            TeamMemberStatus
        """
        # This is a default implementation
        # In practice, this would interface with the actual agent
        agent_id = getattr(member, 'id', str(member))
        agent_name = getattr(member, 'name', f"Agent {agent_id}")
        
        return TeamMemberStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            timestamp=datetime.now(),
            yesterday_completed=["Completed assigned tasks"],
            today_planned=["Continue with current story"],
            blockers=[],
            help_needed=[],
            current_story="STORY-001",
            story_progress=50.0,
            confidence_level=0.8,
            mood="neutral"
        )
    
    def _analyze_blockers(self, statuses: List[TeamMemberStatus]) -> List[Blocker]:
        """
        Analyze and consolidate blockers from all team members
        
        Args:
            statuses: List of team member statuses
        
        Returns:
            List of consolidated blockers
        """
        blockers = []
        blocker_map = {}
        
        for status in statuses:
            for blocker_dict in status.blockers:
                desc = blocker_dict.get('description', '')
                severity = blocker_dict.get('severity', 'medium')
                
                # Check if similar blocker already exists
                blocker_key = f"{desc[:30]}_{severity}"
                
                if blocker_key in blocker_map:
                    # Add agent to existing blocker
                    blocker_map[blocker_key].affected_agents.append(status.agent_id)
                    if status.current_story:
                        blocker_map[blocker_key].affected_stories.append(status.current_story)
                else:
                    # Create new blocker
                    blocker = Blocker(
                        id=f"blocker_{len(blockers) + 1}",
                        description=desc,
                        severity=BlockerSeverity[severity.upper()],
                        affected_agents=[status.agent_id],
                        affected_stories=[status.current_story] if status.current_story else [],
                        identified_at=datetime.now()
                    )
                    blocker_map[blocker_key] = blocker
                    blockers.append(blocker)
        
        # Sort by severity
        severity_order = {
            BlockerSeverity.CRITICAL: 0,
            BlockerSeverity.HIGH: 1,
            BlockerSeverity.MEDIUM: 2,
            BlockerSeverity.LOW: 3
        }
        blockers.sort(key=lambda b: severity_order[b.severity])
        
        return blockers
    
    def _calculate_team_mood(self, statuses: List[TeamMemberStatus]) -> str:
        """
        Calculate overall team mood
        
        Args:
            statuses: List of team member statuses
        
        Returns:
            Team mood string
        """
        if not statuses:
            return "unknown"
        
        mood_scores = {
            'positive': 1.0,
            'neutral': 0.0,
            'concerned': -0.5,
            'frustrated': -1.0
        }
        
        total_score = sum(mood_scores.get(s.mood, 0) for s in statuses)
        avg_score = total_score / len(statuses)
        
        if avg_score > 0.5:
            return "positive"
        elif avg_score > -0.25:
            return "neutral"
        elif avg_score > -0.75:
            return "concerned"
        else:
            return "frustrated"
    
    async def _calculate_sprint_progress(self) -> float:
        """
        Calculate sprint progress
        
        Returns:
            Sprint progress percentage
        """
        if self.sprint_manager:
            try:
                # Try to get sprint progress from sprint manager
                if hasattr(self.sprint_manager, 'get_sprint_progress'):
                    return await self.sprint_manager.get_sprint_progress()
                elif hasattr(self.sprint_manager, 'calculate_progress'):
                    return self.sprint_manager.calculate_progress()
            except:
                pass
        
        # Default calculation based on standup history
        if self.standup_history:
            # Estimate based on story progress from team members
            last_standup = self.standup_history[-1]
            if last_standup.member_statuses:
                total_progress = sum(s.story_progress for s in last_standup.member_statuses)
                return total_progress / len(last_standup.member_statuses)
        
        return 0.0
    
    def _identify_risks(self, 
                       statuses: List[TeamMemberStatus], 
                       blockers: List[Blocker]) -> List[str]:
        """
        Identify risks based on status and blockers
        
        Args:
            statuses: List of team member statuses
            blockers: List of blockers
        
        Returns:
            List of identified risks
        """
        risks = []
        
        # Check for critical blockers
        critical_blockers = [b for b in blockers if b.severity == BlockerSeverity.CRITICAL]
        if critical_blockers:
            risks.append(f"{len(critical_blockers)} critical blockers may impact sprint goal")
        
        # Check for low confidence
        low_confidence = [s for s in statuses if s.confidence_level < 0.5]
        if len(low_confidence) > len(statuses) / 3:
            risks.append("Multiple team members have low confidence in meeting goals")
        
        # Check for team mood
        frustrated_count = len([s for s in statuses if s.mood == "frustrated"])
        if frustrated_count > len(statuses) / 2:
            risks.append("Team morale is low - may impact productivity")
        
        # Check for multiple agents blocked on same story
        story_blockers = {}
        for blocker in blockers:
            for story in blocker.affected_stories:
                story_blockers[story] = story_blockers.get(story, 0) + 1
        
        for story, count in story_blockers.items():
            if count >= 2:
                risks.append(f"Story {story} has multiple blockers")
        
        # Check for agents without current stories
        idle_agents = [s for s in statuses if not s.current_story]
        if idle_agents:
            risks.append(f"{len(idle_agents)} team members without assigned stories")
        
        return risks
    
    def _collect_help_requests(self, statuses: List[TeamMemberStatus]) -> List[Dict[str, Any]]:
        """
        Collect and organize help requests
        
        Args:
            statuses: List of team member statuses
        
        Returns:
            List of help requests
        """
        help_requests = []
        
        for status in statuses:
            for help_item in status.help_needed:
                help_requests.append({
                    'from': status.agent_name,
                    'agent_id': status.agent_id,
                    'description': help_item,
                    'story': status.current_story,
                    'timestamp': status.timestamp.isoformat()
                })
        
        return help_requests
    
    def _generate_action_items(self, 
                              blockers: List[Blocker], 
                              help_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate action items from blockers and help requests
        
        Args:
            blockers: List of blockers
            help_requests: List of help requests
        
        Returns:
            List of action items
        """
        action_items = []
        
        # Critical blockers need immediate action
        for blocker in blockers:
            if blocker.severity in [BlockerSeverity.CRITICAL, BlockerSeverity.HIGH]:
                action_items.append({
                    'description': f"Resolve blocker: {blocker.description}",
                    'priority': 'high',
                    'owner': blocker.assigned_to or 'Scrum Master',
                    'due': 'today',
                    'related_to': f"blocker_{blocker.id}"
                })
        
        # Help requests become action items
        for request in help_requests:
            action_items.append({
                'description': f"Help {request['from']}: {request['description']}",
                'priority': 'medium',
                'owner': 'Team',
                'due': 'today',
                'related_to': f"help_request_{request['agent_id']}"
            })
        
        return action_items
    
    def get_blocker_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze blocker trends over time
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with blocker trend analysis
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_standups = [s for s in self.standup_history if s.date >= cutoff_date]
        
        if not recent_standups:
            return {
                'total_blockers': 0,
                'resolved_blockers': 0,
                'average_blockers_per_day': 0,
                'most_common_blockers': [],
                'resolution_rate': 0
            }
        
        total_blockers = sum(len(s.blockers) for s in recent_standups)
        resolved = len([b for b in self.active_blockers.values() if b.resolved])
        
        # Find most common blocker patterns
        blocker_descriptions = []
        for standup in recent_standups:
            for blocker in standup.blockers:
                blocker_descriptions.append(blocker.description[:50])
        
        from collections import Counter
        common_blockers = Counter(blocker_descriptions).most_common(3)
        
        return {
            'total_blockers': total_blockers,
            'resolved_blockers': resolved,
            'average_blockers_per_day': total_blockers / len(recent_standups),
            'most_common_blockers': [{'description': desc, 'count': count} 
                                    for desc, count in common_blockers],
            'resolution_rate': resolved / total_blockers if total_blockers > 0 else 0
        }
    
    def get_participation_metrics(self) -> Dict[str, Any]:
        """
        Get standup participation metrics
        
        Returns:
            Dictionary with participation metrics
        """
        if not self.standup_history:
            return {
                'total_standups': 0,
                'average_participation': 0,
                'average_duration': 0,
                'trend': 'no_data'
            }
        
        total_standups = len(self.standup_history)
        total_participants = sum(len(s.participants) for s in self.standup_history)
        total_team_size = sum(len(s.member_statuses) for s in self.standup_history)
        avg_participation = (total_participants / total_team_size * 100) if total_team_size > 0 else 0
        avg_duration = sum(s.duration_minutes for s in self.standup_history) / total_standups
        
        # Calculate trend
        if len(self.standup_history) >= 2:
            recent_participation = len(self.standup_history[-1].participants) / len(self.standup_history[-1].member_statuses)
            previous_participation = len(self.standup_history[-2].participants) / len(self.standup_history[-2].member_statuses)
            trend = 'improving' if recent_participation > previous_participation else 'declining'
        else:
            trend = 'stable'
        
        return {
            'total_standups': total_standups,
            'average_participation': avg_participation,
            'average_duration': avg_duration,
            'trend': trend
        }
    
    def export_history(self, format: str = 'json') -> str:
        """
        Export standup history
        
        Args:
            format: Export format ('json' or 'markdown')
        
        Returns:
            Exported data as string
        """
        if format == 'json':
            data = {
                'team_id': self.team_id,
                'standup_count': self.standup_counter,
                'history': [report.to_dict() for report in self.standup_history],
                'active_blockers': {k: v.to_dict() for k, v in self.active_blockers.items()}
            }
            return json.dumps(data, indent=2)
        
        elif format == 'markdown':
            lines = [f"# Standup History for Team {self.team_id}"]
            lines.append(f"\nTotal Standups: {self.standup_counter}")
            
            for report in self.standup_history[-5:]:  # Last 5 standups
                lines.append(f"\n---\n")
                lines.append(report.to_markdown())
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")


# Example usage
if __name__ == "__main__":
    async def main():
        # Create facilitator
        facilitator = StandupFacilitator("team_alpha")
        
        # Mock team members
        team_members = [
            {'id': 'agent_1', 'name': 'PM Agent'},
            {'id': 'agent_2', 'name': 'Dev Agent 1'},
            {'id': 'agent_3', 'name': 'Dev Agent 2'},
            {'id': 'agent_4', 'name': 'QA Agent'}
        ]
        
        # Mock status collection function
        async def mock_collect_status(member):
            return TeamMemberStatus(
                agent_id=member['id'],
                agent_name=member['name'],
                timestamp=datetime.now(),
                yesterday_completed=["Implemented feature X", "Fixed bug Y"],
                today_planned=["Complete feature Z", "Code review"],
                blockers=[
                    {'description': 'API endpoint not available', 'severity': 'high'}
                ] if member['id'] == 'agent_2' else [],
                help_needed=["Need clarification on requirements"] if member['id'] == 'agent_3' else [],
                current_story="STORY-123",
                story_progress=65.0,
                confidence_level=0.75,
                mood="positive"
            )
        
        # Conduct standup
        report = await facilitator.conduct_standup(team_members, mock_collect_status)
        
        # Print report
        print(report.to_markdown())
        
        # Get metrics
        print("\n## Blocker Trends")
        print(json.dumps(facilitator.get_blocker_trends(), indent=2))
        
        print("\n## Participation Metrics")
        print(json.dumps(facilitator.get_participation_metrics(), indent=2))
    
    asyncio.run(main())