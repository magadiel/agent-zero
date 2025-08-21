"""
Product Backlog Management System for Agile AI Company

This module implements a comprehensive product backlog management system
that supports story management, prioritization, estimation, and tracking.
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import heapq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StoryStatus(Enum):
    """Story lifecycle states"""
    DRAFT = "draft"
    READY = "ready"
    IN_SPRINT = "in_sprint"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


class StoryType(Enum):
    """Types of backlog items"""
    USER_STORY = "user_story"
    TECHNICAL_STORY = "technical_story"
    BUG = "bug"
    SPIKE = "spike"
    TASK = "task"
    EPIC = "epic"


class Priority(Enum):
    """Priority levels for backlog items"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    TRIVIAL = 5


@dataclass
class AcceptanceCriteria:
    """Acceptance criteria for a story"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    is_met: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    
    def verify(self, verified_by: str):
        """Mark criteria as verified"""
        self.is_met = True
        self.verified_by = verified_by
        self.verified_at = datetime.now()
        return True


@dataclass
class Story:
    """Represents a backlog item (story, task, bug, etc.)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    type: StoryType = StoryType.USER_STORY
    status: StoryStatus = StoryStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    story_points: Optional[int] = None
    business_value: int = 0
    
    # User story format
    as_a: str = ""
    i_want: str = ""
    so_that: str = ""
    
    # Relationships
    epic_id: Optional[str] = None
    parent_story_id: Optional[str] = None
    blocked_by: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    
    # Team assignment
    assigned_to: Optional[str] = None
    team_id: Optional[str] = None
    sprint_id: Optional[str] = None
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Acceptance
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    definition_of_done: List[str] = field(default_factory=list)
    
    # Tags and labels
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Comments and attachments
    comments: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    
    def get_user_story_format(self) -> str:
        """Get story in user story format"""
        if self.as_a and self.i_want and self.so_that:
            return f"As a {self.as_a}, I want {self.i_want}, so that {self.so_that}"
        return self.title
    
    def calculate_priority_score(self) -> float:
        """Calculate weighted priority score for ranking"""
        # WSJF (Weighted Shortest Job First) calculation
        if self.story_points and self.story_points > 0:
            # Higher business value and lower effort = higher priority
            urgency_weight = 6 - self.priority.value  # Invert priority (1=5, 5=1)
            return (self.business_value * urgency_weight) / self.story_points
        return self.business_value * (6 - self.priority.value)
    
    def is_ready(self) -> bool:
        """Check if story meets Definition of Ready"""
        checks = [
            bool(self.title),
            bool(self.description),
            self.story_points is not None,
            len(self.acceptance_criteria) > 0,
            self.status in [StoryStatus.READY, StoryStatus.IN_SPRINT]
        ]
        return all(checks)
    
    def is_done(self) -> bool:
        """Check if story meets Definition of Done"""
        # All acceptance criteria must be met
        if not all(ac.is_met for ac in self.acceptance_criteria):
            return False
        # Status must be done or accepted
        return self.status in [StoryStatus.DONE, StoryStatus.ACCEPTED]
    
    def add_comment(self, author: str, text: str):
        """Add a comment to the story"""
        self.comments.append({
            'id': str(uuid.uuid4()),
            'author': author,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def update_status(self, new_status: StoryStatus):
        """Update story status with tracking"""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == StoryStatus.DONE:
            self.completed_at = datetime.now()
        
        logger.info(f"Story {self.id} status changed: {old_status.value} -> {new_status.value}")
        return old_status, new_status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert story to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['type'] = self.type.value
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        # Convert datetime objects
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class ProductBacklog:
    """Manages the product backlog with prioritization and filtering"""
    
    def __init__(self):
        self.stories: Dict[str, Story] = {}
        self.epics: Dict[str, Story] = {}
        self.priority_queue: List[Tuple[float, str]] = []
        self.sprint_capacity_history: List[int] = []
        
    def add_story(self, story: Story) -> str:
        """Add a story to the backlog"""
        if story.type == StoryType.EPIC:
            self.epics[story.id] = story
        else:
            self.stories[story.id] = story
            # Add to priority queue
            priority_score = -story.calculate_priority_score()  # Negative for max heap
            heapq.heappush(self.priority_queue, (priority_score, story.id))
        
        logger.info(f"Added {story.type.value} to backlog: {story.id}")
        return story.id
    
    def update_story(self, story_id: str, updates: Dict[str, Any]) -> bool:
        """Update a story with new values"""
        if story_id in self.stories:
            story = self.stories[story_id]
            for key, value in updates.items():
                if hasattr(story, key):
                    # Handle enum conversions
                    if key == 'status' and isinstance(value, str):
                        value = StoryStatus(value)
                    elif key == 'priority' and isinstance(value, str):
                        value = Priority(value)
                    elif key == 'type' and isinstance(value, str):
                        value = StoryType(value)
                    
                    setattr(story, key, value)
            
            story.updated_at = datetime.now()
            # Rebuild priority queue if priority-related fields changed
            if any(k in updates for k in ['priority', 'business_value', 'story_points']):
                self._rebuild_priority_queue()
            
            logger.info(f"Updated story {story_id}")
            return True
        return False
    
    def _rebuild_priority_queue(self):
        """Rebuild the priority queue after updates"""
        self.priority_queue = []
        for story_id, story in self.stories.items():
            if story.status not in [StoryStatus.DONE, StoryStatus.ACCEPTED, StoryStatus.CANCELLED]:
                priority_score = -story.calculate_priority_score()
                heapq.heappush(self.priority_queue, (priority_score, story_id))
    
    def get_story(self, story_id: str) -> Optional[Story]:
        """Get a story by ID"""
        return self.stories.get(story_id) or self.epics.get(story_id)
    
    def remove_story(self, story_id: str) -> bool:
        """Remove a story from the backlog"""
        if story_id in self.stories:
            del self.stories[story_id]
            self._rebuild_priority_queue()
            logger.info(f"Removed story {story_id}")
            return True
        elif story_id in self.epics:
            del self.epics[story_id]
            logger.info(f"Removed epic {story_id}")
            return True
        return False
    
    def get_prioritized_stories(self, 
                              limit: Optional[int] = None,
                              exclude_statuses: Optional[List[StoryStatus]] = None) -> List[Story]:
        """Get stories in priority order"""
        exclude_statuses = exclude_statuses or [
            StoryStatus.DONE, 
            StoryStatus.ACCEPTED, 
            StoryStatus.CANCELLED,
            StoryStatus.IN_SPRINT,
            StoryStatus.IN_PROGRESS
        ]
        
        # Create a copy of the queue to iterate without modifying
        temp_queue = list(self.priority_queue)
        heapq.heapify(temp_queue)
        
        prioritized = []
        while temp_queue and (limit is None or len(prioritized) < limit):
            _, story_id = heapq.heappop(temp_queue)
            story = self.stories.get(story_id)
            if story and story.status not in exclude_statuses:
                prioritized.append(story)
        
        return prioritized
    
    def get_stories_by_status(self, status: StoryStatus) -> List[Story]:
        """Get all stories with a specific status"""
        return [s for s in self.stories.values() if s.status == status]
    
    def get_stories_by_epic(self, epic_id: str) -> List[Story]:
        """Get all stories belonging to an epic"""
        return [s for s in self.stories.values() if s.epic_id == epic_id]
    
    def get_ready_stories(self) -> List[Story]:
        """Get stories that meet Definition of Ready"""
        return [s for s in self.stories.values() if s.is_ready()]
    
    def get_blocked_stories(self) -> List[Story]:
        """Get stories that are blocked"""
        return [s for s in self.stories.values() if s.blocked_by]
    
    def calculate_epic_progress(self, epic_id: str) -> Dict[str, Any]:
        """Calculate progress for an epic"""
        stories = self.get_stories_by_epic(epic_id)
        if not stories:
            return {'progress': 0, 'completed': 0, 'total': 0, 'points_completed': 0, 'points_total': 0}
        
        completed = sum(1 for s in stories if s.status in [StoryStatus.DONE, StoryStatus.ACCEPTED])
        total = len(stories)
        
        points_completed = sum(
            s.story_points or 0 for s in stories 
            if s.status in [StoryStatus.DONE, StoryStatus.ACCEPTED]
        )
        points_total = sum(s.story_points or 0 for s in stories)
        
        progress = (completed / total * 100) if total > 0 else 0
        
        return {
            'progress': progress,
            'completed': completed,
            'total': total,
            'points_completed': points_completed,
            'points_total': points_total,
            'stories': stories
        }
    
    def estimate_completion(self, story_points: int, velocity: Optional[float] = None) -> int:
        """Estimate sprints needed to complete given story points"""
        if not velocity:
            # Use historical average if available
            if self.sprint_capacity_history:
                velocity = sum(self.sprint_capacity_history) / len(self.sprint_capacity_history)
            else:
                velocity = 20  # Default velocity assumption
        
        if velocity <= 0:
            return 0
        
        import math
        return math.ceil(story_points / velocity)
    
    def grooming_candidates(self, limit: int = 10) -> List[Story]:
        """Get stories that need grooming (estimation, refinement)"""
        candidates = []
        for story in self.stories.values():
            if story.status == StoryStatus.DRAFT and (
                story.story_points is None or
                not story.acceptance_criteria or
                not story.description
            ):
                candidates.append(story)
                if len(candidates) >= limit:
                    break
        return candidates
    
    def export_to_json(self, file_path: str):
        """Export backlog to JSON file"""
        data = {
            'stories': [s.to_dict() for s in self.stories.values()],
            'epics': [e.to_dict() for e in self.epics.values()],
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_stories': len(self.stories),
                'total_epics': len(self.epics)
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported backlog to {file_path}")
    
    def import_from_json(self, file_path: str):
        """Import backlog from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Clear existing data
        self.stories.clear()
        self.epics.clear()
        self.priority_queue.clear()
        
        # Import stories
        for story_data in data.get('stories', []):
            story = self._story_from_dict(story_data)
            self.add_story(story)
        
        # Import epics
        for epic_data in data.get('epics', []):
            epic = self._story_from_dict(epic_data)
            self.add_story(epic)
        
        logger.info(f"Imported backlog from {file_path}")
    
    def _story_from_dict(self, data: Dict[str, Any]) -> Story:
        """Create a Story object from dictionary"""
        # Convert string enums back to enum objects
        if 'type' in data:
            data['type'] = StoryType(data['type'])
        if 'status' in data:
            data['status'] = StoryStatus(data['status'])
        if 'priority' in data:
            data['priority'] = Priority(data['priority'])
        
        # Convert ISO strings back to datetime
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'completed_at' in data and data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        # Handle acceptance criteria
        if 'acceptance_criteria' in data:
            data['acceptance_criteria'] = [
                AcceptanceCriteria(**ac) if isinstance(ac, dict) else ac
                for ac in data['acceptance_criteria']
            ]
        
        return Story(**data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get backlog statistics"""
        total_stories = len(self.stories)
        total_epics = len(self.epics)
        
        status_counts = {}
        type_counts = {}
        priority_counts = {}
        
        total_points = 0
        estimated_stories = 0
        
        for story in self.stories.values():
            # Status distribution
            status_counts[story.status.value] = status_counts.get(story.status.value, 0) + 1
            
            # Type distribution
            type_counts[story.type.value] = type_counts.get(story.type.value, 0) + 1
            
            # Priority distribution
            priority_counts[story.priority.value] = priority_counts.get(story.priority.value, 0) + 1
            
            # Points calculation
            if story.story_points:
                total_points += story.story_points
                estimated_stories += 1
        
        ready_stories = len(self.get_ready_stories())
        blocked_stories = len(self.get_blocked_stories())
        
        return {
            'total_stories': total_stories,
            'total_epics': total_epics,
            'ready_stories': ready_stories,
            'blocked_stories': blocked_stories,
            'total_points': total_points,
            'estimated_stories': estimated_stories,
            'estimation_coverage': (estimated_stories / total_stories * 100) if total_stories > 0 else 0,
            'status_distribution': status_counts,
            'type_distribution': type_counts,
            'priority_distribution': priority_counts
        }


# Example usage and testing
if __name__ == "__main__":
    # Create backlog
    backlog = ProductBacklog()
    
    # Create an epic
    epic = Story(
        title="User Authentication System",
        description="Implement complete authentication and authorization",
        type=StoryType.EPIC,
        priority=Priority.HIGH,
        business_value=100
    )
    epic_id = backlog.add_story(epic)
    
    # Create user stories
    story1 = Story(
        title="User Registration",
        description="Allow users to register with email",
        as_a="new user",
        i_want="to register with my email",
        so_that="I can access the platform",
        type=StoryType.USER_STORY,
        priority=Priority.HIGH,
        story_points=5,
        business_value=80,
        epic_id=epic_id,
        status=StoryStatus.READY
    )
    story1.acceptance_criteria.append(
        AcceptanceCriteria(description="Email validation works")
    )
    story1.acceptance_criteria.append(
        AcceptanceCriteria(description="Password meets security requirements")
    )
    
    story2 = Story(
        title="Login Functionality",
        description="Users can log in with credentials",
        as_a="registered user",
        i_want="to log in",
        so_that="I can access my account",
        type=StoryType.USER_STORY,
        priority=Priority.HIGH,
        story_points=3,
        business_value=90,
        epic_id=epic_id,
        status=StoryStatus.READY
    )
    
    story3 = Story(
        title="Fix Login Bug",
        description="Login fails for users with special characters",
        type=StoryType.BUG,
        priority=Priority.CRITICAL,
        story_points=2,
        business_value=70,
        status=StoryStatus.READY
    )
    
    # Add stories to backlog
    backlog.add_story(story1)
    backlog.add_story(story2)
    backlog.add_story(story3)
    
    # Get prioritized stories
    print("\nPrioritized Backlog:")
    for story in backlog.get_prioritized_stories(limit=5):
        print(f"  - [{story.priority.value}] {story.title} (Points: {story.story_points}, Value: {story.business_value})")
    
    # Get epic progress
    progress = backlog.calculate_epic_progress(epic_id)
    print(f"\nEpic Progress: {progress['progress']:.1f}% ({progress['completed']}/{progress['total']} stories)")
    
    # Get statistics
    stats = backlog.get_statistics()
    print(f"\nBacklog Statistics:")
    print(f"  Total Stories: {stats['total_stories']}")
    print(f"  Ready Stories: {stats['ready_stories']}")
    print(f"  Total Points: {stats['total_points']}")
    print(f"  Estimation Coverage: {stats['estimation_coverage']:.1f}%")