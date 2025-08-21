"""
Sprint Management System for Agile AI Company

This module implements comprehensive sprint planning, execution, and tracking
functionality including velocity calculation, burndown charts, and retrospectives.
"""

import json
import uuid
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging
import statistics

from agile.product_backlog import ProductBacklog, Story, StoryStatus, Priority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SprintStatus(Enum):
    """Sprint lifecycle states"""
    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW = "review"
    RETROSPECTIVE = "retrospective"
    CLOSED = "closed"


class SprintGoal(Enum):
    """Types of sprint goals"""
    FEATURE_DELIVERY = "feature_delivery"
    TECHNICAL_DEBT = "technical_debt"
    BUG_FIXING = "bug_fixing"
    RESEARCH = "research"
    MIXED = "mixed"


@dataclass
class DailyProgress:
    """Track daily progress within a sprint"""
    date: date
    stories_completed: int = 0
    points_completed: int = 0
    points_remaining: int = 0
    stories_added: List[str] = field(default_factory=list)
    stories_removed: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class SprintRetrospective:
    """Sprint retrospective data"""
    sprint_id: str
    what_went_well: List[str] = field(default_factory=list)
    what_went_wrong: List[str] = field(default_factory=list)
    action_items: List[Dict[str, str]] = field(default_factory=list)
    team_happiness: Optional[float] = None  # 1-10 scale
    velocity_achieved: int = 0
    commitment_accuracy: float = 0.0  # Percentage of committed points completed
    
    def add_action_item(self, description: str, owner: str, due_date: Optional[date] = None):
        """Add an action item from retrospective"""
        self.action_items.append({
            'id': str(uuid.uuid4()),
            'description': description,
            'owner': owner,
            'due_date': due_date.isoformat() if due_date else None,
            'status': 'pending'
        })


@dataclass
class Sprint:
    """Represents a sprint with planning, execution, and tracking"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    goal: str = ""
    goal_type: SprintGoal = SprintGoal.MIXED
    status: SprintStatus = SprintStatus.PLANNING
    
    # Timing
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=lambda: date.today() + timedelta(days=14))
    duration_days: int = 14
    
    # Team and capacity
    team_id: str = ""
    team_members: List[str] = field(default_factory=list)
    capacity_hours: int = 0
    focus_factor: float = 0.7  # Percentage of time available for sprint work
    
    # Stories and points
    story_ids: List[str] = field(default_factory=list)
    committed_points: int = 0
    completed_points: int = 0
    added_points: int = 0  # Points added after sprint start
    removed_points: int = 0  # Points removed from sprint
    
    # Tracking
    daily_progress: List[DailyProgress] = field(default_factory=list)
    burndown_ideal: List[float] = field(default_factory=list)
    burndown_actual: List[float] = field(default_factory=list)
    
    # Metrics
    velocity: Optional[int] = None
    predictability: Optional[float] = None  # Consistency of velocity
    
    # Meta
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retrospective: Optional[SprintRetrospective] = None
    
    def calculate_capacity(self, team_size: int, days_off: int = 0) -> int:
        """Calculate team capacity for the sprint"""
        working_days = self._get_working_days()
        available_days = working_days - days_off
        hours_per_day = 6  # Assume 6 productive hours per day
        
        self.capacity_hours = int(team_size * available_days * hours_per_day * self.focus_factor)
        return self.capacity_hours
    
    def _get_working_days(self) -> int:
        """Calculate working days in sprint (excluding weekends)"""
        current = self.start_date
        working_days = 0
        
        while current <= self.end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                working_days += 1
            current += timedelta(days=1)
        
        return working_days
    
    def generate_burndown_ideal(self) -> List[float]:
        """Generate ideal burndown line"""
        working_days = self._get_working_days()
        if working_days == 0:
            return []
        
        daily_burn = self.committed_points / working_days
        self.burndown_ideal = [self.committed_points - (daily_burn * i) 
                               for i in range(working_days + 1)]
        return self.burndown_ideal
    
    def update_daily_progress(self, backlog: ProductBacklog):
        """Update daily progress and actual burndown"""
        today = date.today()
        if today < self.start_date or today > self.end_date:
            return
        
        # Calculate remaining points
        remaining_points = 0
        completed_today = 0
        
        for story_id in self.story_ids:
            story = backlog.get_story(story_id)
            if story:
                if story.status not in [StoryStatus.DONE, StoryStatus.ACCEPTED]:
                    remaining_points += story.story_points or 0
                elif story.completed_at and story.completed_at.date() == today:
                    completed_today += story.story_points or 0
        
        # Create or update today's progress
        progress = next((p for p in self.daily_progress if p.date == today), None)
        if not progress:
            progress = DailyProgress(date=today)
            self.daily_progress.append(progress)
        
        progress.points_remaining = remaining_points
        progress.points_completed = completed_today
        
        # Update actual burndown
        day_index = (today - self.start_date).days
        if day_index >= 0:
            while len(self.burndown_actual) <= day_index:
                self.burndown_actual.append(self.committed_points)
            self.burndown_actual[day_index] = remaining_points
    
    def calculate_velocity(self) -> int:
        """Calculate sprint velocity (completed story points)"""
        self.velocity = self.completed_points
        return self.velocity
    
    def get_burndown_chart_data(self) -> Dict[str, Any]:
        """Get data for burndown chart visualization"""
        return {
            'sprint_name': self.name,
            'dates': [str(self.start_date + timedelta(days=i)) 
                     for i in range(self.duration_days + 1)],
            'ideal': self.burndown_ideal,
            'actual': self.burndown_actual,
            'remaining_points': self.burndown_actual[-1] if self.burndown_actual else self.committed_points
        }
    
    def is_on_track(self) -> bool:
        """Check if sprint is on track based on burndown"""
        if not self.burndown_actual or not self.burndown_ideal:
            return True
        
        today_index = min((date.today() - self.start_date).days, 
                         len(self.burndown_ideal) - 1)
        
        if today_index < 0 or today_index >= len(self.burndown_ideal):
            return True
        
        ideal_remaining = self.burndown_ideal[today_index]
        actual_remaining = self.burndown_actual[-1] if self.burndown_actual else self.committed_points
        
        # Allow 10% deviation
        return actual_remaining <= ideal_remaining * 1.1
    
    def get_completion_percentage(self) -> float:
        """Calculate sprint completion percentage"""
        if self.committed_points == 0:
            return 0.0
        return (self.completed_points / self.committed_points) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sprint to dictionary"""
        data = asdict(self)
        # Convert enums and dates
        data['goal_type'] = self.goal_type.value
        data['status'] = self.status.value
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        
        # Convert daily progress dates
        for progress in data.get('daily_progress', []):
            if isinstance(progress.get('date'), date):
                progress['date'] = progress['date'].isoformat()
        
        return data


class SprintManager:
    """Manages sprints including planning, execution, and retrospectives"""
    
    def __init__(self, backlog: ProductBacklog):
        self.backlog = backlog
        self.sprints: Dict[str, Sprint] = {}
        self.active_sprint: Optional[Sprint] = None
        self.velocity_history: List[int] = []
        self.team_capacity: Dict[str, int] = {}  # team_id -> capacity
        
    def create_sprint(self, 
                     name: str,
                     goal: str,
                     team_id: str,
                     start_date: Optional[date] = None,
                     duration_days: int = 14) -> Sprint:
        """Create a new sprint"""
        sprint = Sprint(
            name=name,
            goal=goal,
            team_id=team_id,
            start_date=start_date or date.today(),
            duration_days=duration_days
        )
        sprint.end_date = sprint.start_date + timedelta(days=duration_days - 1)
        
        self.sprints[sprint.id] = sprint
        logger.info(f"Created sprint: {sprint.name} ({sprint.id})")
        return sprint
    
    def plan_sprint(self, 
                   sprint_id: str,
                   story_ids: List[str],
                   team_size: int,
                   days_off: int = 0) -> Dict[str, Any]:
        """Plan a sprint with selected stories"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return {'success': False, 'error': 'Sprint not found'}
        
        if sprint.status != SprintStatus.PLANNING:
            return {'success': False, 'error': 'Sprint is not in planning status'}
        
        # Calculate capacity
        sprint.calculate_capacity(team_size, days_off)
        
        # Add stories to sprint
        total_points = 0
        added_stories = []
        
        for story_id in story_ids:
            story = self.backlog.get_story(story_id)
            if story and story.is_ready():
                story.sprint_id = sprint_id
                story.status = StoryStatus.IN_SPRINT
                sprint.story_ids.append(story_id)
                total_points += story.story_points or 0
                added_stories.append(story.title)
        
        sprint.committed_points = total_points
        
        # Generate ideal burndown
        sprint.generate_burndown_ideal()
        
        # Check capacity vs commitment
        points_per_hour = 0.5  # Rough estimate
        estimated_hours = total_points / points_per_hour
        capacity_utilization = (estimated_hours / sprint.capacity_hours * 100) if sprint.capacity_hours > 0 else 0
        
        return {
            'success': True,
            'sprint_id': sprint_id,
            'stories_added': len(added_stories),
            'total_points': total_points,
            'capacity_hours': sprint.capacity_hours,
            'capacity_utilization': capacity_utilization,
            'recommendation': 'Good load' if 70 <= capacity_utilization <= 90 else 
                            'Under-committed' if capacity_utilization < 70 else 'Over-committed'
        }
    
    def start_sprint(self, sprint_id: str) -> bool:
        """Start a sprint"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return False
        
        if sprint.status != SprintStatus.PLANNING:
            return False
        
        # Check for active sprint
        if self.active_sprint:
            logger.warning(f"Cannot start sprint - {self.active_sprint.name} is already active")
            return False
        
        sprint.status = SprintStatus.ACTIVE
        sprint.started_at = datetime.now()
        self.active_sprint = sprint
        
        # Update story statuses
        for story_id in sprint.story_ids:
            story = self.backlog.get_story(story_id)
            if story:
                story.status = StoryStatus.IN_SPRINT
        
        logger.info(f"Started sprint: {sprint.name}")
        return True
    
    def add_story_to_sprint(self, sprint_id: str, story_id: str) -> bool:
        """Add a story to an active sprint"""
        sprint = self.sprints.get(sprint_id)
        story = self.backlog.get_story(story_id)
        
        if not sprint or not story:
            return False
        
        if sprint.status != SprintStatus.ACTIVE:
            return False
        
        sprint.story_ids.append(story_id)
        sprint.added_points += story.story_points or 0
        story.sprint_id = sprint_id
        story.status = StoryStatus.IN_SPRINT
        
        # Track in daily progress
        today = date.today()
        progress = next((p for p in sprint.daily_progress if p.date == today), None)
        if not progress:
            progress = DailyProgress(date=today)
            sprint.daily_progress.append(progress)
        progress.stories_added.append(story_id)
        
        logger.info(f"Added story {story_id} to sprint {sprint_id}")
        return True
    
    def remove_story_from_sprint(self, sprint_id: str, story_id: str) -> bool:
        """Remove a story from sprint"""
        sprint = self.sprints.get(sprint_id)
        story = self.backlog.get_story(story_id)
        
        if not sprint or not story:
            return False
        
        if story_id not in sprint.story_ids:
            return False
        
        sprint.story_ids.remove(story_id)
        sprint.removed_points += story.story_points or 0
        story.sprint_id = None
        story.status = StoryStatus.READY
        
        # Track in daily progress
        today = date.today()
        progress = next((p for p in sprint.daily_progress if p.date == today), None)
        if not progress:
            progress = DailyProgress(date=today)
            sprint.daily_progress.append(progress)
        progress.stories_removed.append(story_id)
        
        logger.info(f"Removed story {story_id} from sprint {sprint_id}")
        return True
    
    def complete_story(self, story_id: str) -> bool:
        """Mark a story as complete in active sprint"""
        if not self.active_sprint:
            return False
        
        story = self.backlog.get_story(story_id)
        if not story or story_id not in self.active_sprint.story_ids:
            return False
        
        story.status = StoryStatus.DONE
        story.completed_at = datetime.now()
        self.active_sprint.completed_points += story.story_points or 0
        
        # Update daily progress
        self.active_sprint.update_daily_progress(self.backlog)
        
        logger.info(f"Completed story {story_id} in sprint {self.active_sprint.id}")
        return True
    
    def daily_standup(self) -> Dict[str, Any]:
        """Generate daily standup report"""
        if not self.active_sprint:
            return {'error': 'No active sprint'}
        
        sprint = self.active_sprint
        sprint.update_daily_progress(self.backlog)
        
        # Get today's progress
        today = date.today()
        today_progress = next((p for p in sprint.daily_progress if p.date == today), None)
        
        # Calculate metrics
        stories_in_progress = []
        stories_blocked = []
        stories_completed_today = []
        
        for story_id in sprint.story_ids:
            story = self.backlog.get_story(story_id)
            if story:
                if story.status == StoryStatus.IN_PROGRESS:
                    stories_in_progress.append(story.title)
                elif story.blocked_by:
                    stories_blocked.append(story.title)
                elif story.completed_at and story.completed_at.date() == today:
                    stories_completed_today.append(story.title)
        
        days_remaining = (sprint.end_date - today).days
        on_track = sprint.is_on_track()
        
        return {
            'sprint_name': sprint.name,
            'day': (today - sprint.start_date).days + 1,
            'days_remaining': days_remaining,
            'points_remaining': today_progress.points_remaining if today_progress else sprint.committed_points,
            'points_completed': sprint.completed_points,
            'stories_in_progress': stories_in_progress,
            'stories_blocked': stories_blocked,
            'stories_completed_today': stories_completed_today,
            'on_track': on_track,
            'burndown_status': 'On track' if on_track else 'Behind schedule',
            'blockers': today_progress.blockers if today_progress else []
        }
    
    def end_sprint(self, sprint_id: str) -> Dict[str, Any]:
        """End a sprint and move to review"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return {'success': False, 'error': 'Sprint not found'}
        
        if sprint.status != SprintStatus.ACTIVE:
            return {'success': False, 'error': 'Sprint is not active'}
        
        sprint.status = SprintStatus.REVIEW
        sprint.completed_at = datetime.now()
        
        # Calculate final velocity
        sprint.calculate_velocity()
        self.velocity_history.append(sprint.velocity)
        
        # Move incomplete stories back to backlog
        incomplete_stories = []
        for story_id in sprint.story_ids:
            story = self.backlog.get_story(story_id)
            if story and story.status not in [StoryStatus.DONE, StoryStatus.ACCEPTED]:
                story.sprint_id = None
                story.status = StoryStatus.READY
                incomplete_stories.append(story.title)
        
        # Clear active sprint
        if self.active_sprint and self.active_sprint.id == sprint_id:
            self.active_sprint = None
        
        completion_rate = sprint.get_completion_percentage()
        
        return {
            'success': True,
            'sprint_name': sprint.name,
            'velocity': sprint.velocity,
            'committed_points': sprint.committed_points,
            'completed_points': sprint.completed_points,
            'completion_rate': completion_rate,
            'incomplete_stories': incomplete_stories,
            'added_points': sprint.added_points,
            'removed_points': sprint.removed_points
        }
    
    def conduct_retrospective(self, 
                            sprint_id: str,
                            what_went_well: List[str],
                            what_went_wrong: List[str],
                            action_items: List[Dict[str, str]],
                            team_happiness: float) -> bool:
        """Conduct sprint retrospective"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return False
        
        if sprint.status != SprintStatus.REVIEW:
            return False
        
        retro = SprintRetrospective(
            sprint_id=sprint_id,
            what_went_well=what_went_well,
            what_went_wrong=what_went_wrong,
            team_happiness=team_happiness,
            velocity_achieved=sprint.velocity or 0,
            commitment_accuracy=sprint.get_completion_percentage()
        )
        
        for item in action_items:
            retro.add_action_item(
                item.get('description', ''),
                item.get('owner', ''),
                date.fromisoformat(item['due_date']) if 'due_date' in item else None
            )
        
        sprint.retrospective = retro
        sprint.status = SprintStatus.CLOSED
        
        logger.info(f"Completed retrospective for sprint {sprint.name}")
        return True
    
    def get_velocity_metrics(self) -> Dict[str, Any]:
        """Calculate velocity metrics across sprints"""
        if not self.velocity_history:
            return {
                'average_velocity': 0,
                'min_velocity': 0,
                'max_velocity': 0,
                'trend': 'stable',
                'predictability': 0
            }
        
        avg_velocity = statistics.mean(self.velocity_history)
        min_velocity = min(self.velocity_history)
        max_velocity = max(self.velocity_history)
        
        # Calculate trend (last 3 sprints)
        recent = self.velocity_history[-3:] if len(self.velocity_history) >= 3 else self.velocity_history
        if len(recent) >= 2:
            if recent[-1] > recent[0]:
                trend = 'increasing'
            elif recent[-1] < recent[0]:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        # Calculate predictability (coefficient of variation)
        if len(self.velocity_history) >= 3:
            stdev = statistics.stdev(self.velocity_history)
            predictability = 1 - (stdev / avg_velocity) if avg_velocity > 0 else 0
        else:
            predictability = 0
        
        return {
            'average_velocity': avg_velocity,
            'min_velocity': min_velocity,
            'max_velocity': max_velocity,
            'trend': trend,
            'predictability': predictability,
            'history': self.velocity_history
        }
    
    def recommend_sprint_capacity(self, team_size: int) -> Dict[str, Any]:
        """Recommend sprint capacity based on historical velocity"""
        metrics = self.get_velocity_metrics()
        
        if not self.velocity_history:
            # Default recommendation for new teams
            recommended_points = team_size * 8  # 8 points per person
            confidence = 'low'
        else:
            avg_velocity = metrics['average_velocity']
            predictability = metrics['predictability']
            
            if predictability > 0.8:
                recommended_points = int(avg_velocity)
                confidence = 'high'
            elif predictability > 0.6:
                # Use 90% of average for medium predictability
                recommended_points = int(avg_velocity * 0.9)
                confidence = 'medium'
            else:
                # Use 80% of average for low predictability
                recommended_points = int(avg_velocity * 0.8)
                confidence = 'low'
        
        return {
            'recommended_points': recommended_points,
            'confidence': confidence,
            'based_on_sprints': len(self.velocity_history),
            'average_velocity': metrics['average_velocity'],
            'predictability': metrics['predictability']
        }
    
    def export_sprint_data(self, sprint_id: str, file_path: str):
        """Export sprint data to JSON"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return False
        
        # Gather complete sprint data
        sprint_data = sprint.to_dict()
        
        # Add story details
        stories = []
        for story_id in sprint.story_ids:
            story = self.backlog.get_story(story_id)
            if story:
                stories.append(story.to_dict())
        
        sprint_data['stories'] = stories
        
        # Add metrics
        sprint_data['metrics'] = {
            'velocity': sprint.velocity,
            'completion_rate': sprint.get_completion_percentage(),
            'on_track': sprint.is_on_track()
        }
        
        with open(file_path, 'w') as f:
            json.dump(sprint_data, f, indent=2)
        
        logger.info(f"Exported sprint data to {file_path}")
        return True
    
    def get_sprint_report(self, sprint_id: str) -> Dict[str, Any]:
        """Generate comprehensive sprint report"""
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return {'error': 'Sprint not found'}
        
        # Gather story statistics
        story_stats = {
            'total': len(sprint.story_ids),
            'completed': 0,
            'in_progress': 0,
            'blocked': 0,
            'not_started': 0
        }
        
        for story_id in sprint.story_ids:
            story = self.backlog.get_story(story_id)
            if story:
                if story.status in [StoryStatus.DONE, StoryStatus.ACCEPTED]:
                    story_stats['completed'] += 1
                elif story.status == StoryStatus.IN_PROGRESS:
                    story_stats['in_progress'] += 1
                elif story.blocked_by:
                    story_stats['blocked'] += 1
                else:
                    story_stats['not_started'] += 1
        
        return {
            'sprint': {
                'id': sprint.id,
                'name': sprint.name,
                'goal': sprint.goal,
                'status': sprint.status.value,
                'start_date': sprint.start_date.isoformat(),
                'end_date': sprint.end_date.isoformat()
            },
            'points': {
                'committed': sprint.committed_points,
                'completed': sprint.completed_points,
                'added': sprint.added_points,
                'removed': sprint.removed_points,
                'remaining': sprint.committed_points - sprint.completed_points
            },
            'stories': story_stats,
            'metrics': {
                'velocity': sprint.velocity,
                'completion_rate': sprint.get_completion_percentage(),
                'on_track': sprint.is_on_track(),
                'capacity_hours': sprint.capacity_hours
            },
            'burndown': sprint.get_burndown_chart_data()
        }


# Example usage and testing
if __name__ == "__main__":
    # Create backlog and add some stories
    backlog = ProductBacklog()
    
    # Create stories
    stories = []
    for i in range(10):
        story = Story(
            title=f"Story {i+1}",
            description=f"Description for story {i+1}",
            story_points=(i % 4) + 1,  # 1-4 points
            business_value=(i % 3 + 1) * 20,
            status=StoryStatus.READY,
            priority=Priority.HIGH if i < 3 else Priority.MEDIUM
        )
        backlog.add_story(story)
        stories.append(story)
    
    # Create sprint manager
    sprint_manager = SprintManager(backlog)
    
    # Create and plan a sprint
    sprint = sprint_manager.create_sprint(
        name="Sprint 1",
        goal="Deliver core authentication features",
        team_id="team-alpha"
    )
    
    # Plan sprint with first 5 stories
    story_ids = [s.id for s in stories[:5]]
    plan_result = sprint_manager.plan_sprint(
        sprint.id,
        story_ids,
        team_size=5,
        days_off=2
    )
    
    print(f"Sprint Planning Result:")
    print(f"  Stories: {plan_result['stories_added']}")
    print(f"  Points: {plan_result['total_points']}")
    print(f"  Capacity: {plan_result['capacity_hours']} hours")
    print(f"  Utilization: {plan_result['capacity_utilization']:.1f}%")
    print(f"  Recommendation: {plan_result['recommendation']}")
    
    # Start sprint
    sprint_manager.start_sprint(sprint.id)
    
    # Simulate daily progress
    sprint_manager.complete_story(stories[0].id)
    sprint_manager.complete_story(stories[1].id)
    
    # Get daily standup
    standup = sprint_manager.daily_standup()
    print(f"\nDaily Standup:")
    print(f"  Day {standup['day']} of {sprint.name}")
    print(f"  Points completed: {standup['points_completed']}")
    print(f"  Points remaining: {standup['points_remaining']}")
    print(f"  Status: {standup['burndown_status']}")
    
    # Get velocity metrics
    metrics = sprint_manager.get_velocity_metrics()
    print(f"\nVelocity Metrics:")
    print(f"  Average: {metrics['average_velocity']:.1f}")
    print(f"  Trend: {metrics['trend']}")
    print(f"  Predictability: {metrics['predictability']:.2f}")