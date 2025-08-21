"""
Epic Management System for Agile AI Company

This module provides comprehensive epic tracking and management including
templates, progress tracking, story relationships, and report generation.
"""

import json
import uuid
import os
from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
import logging
import yaml
from pathlib import Path

# Import from existing modules
try:
    from agile.story_manager import StoryManager, Story, StoryStatus
    from agile.product_backlog import Priority
except ImportError:
    # Fallback for testing
    from dataclasses import dataclass
    from enum import Enum
    
    class Priority(Enum):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
    
    class StoryStatus(Enum):
        DRAFT = "draft"
        READY = "ready"
        IN_SPRINT = "in_sprint"
        IN_PROGRESS = "in_progress"
        IN_REVIEW = "in_review"
        DONE = "done"
        ACCEPTED = "accepted"
        BLOCKED = "blocked"
        CANCELLED = "cancelled"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EpicStatus(Enum):
    """Epic lifecycle states"""
    DRAFT = "draft"  # Initial planning
    ACTIVE = "active"  # In development
    COMPLETED = "completed"  # All stories done
    CANCELLED = "cancelled"  # Cancelled


class EpicType(Enum):
    """Types of epics"""
    FEATURE = "feature"  # New feature development
    ENHANCEMENT = "enhancement"  # Improvement to existing feature
    TECHNICAL = "technical"  # Technical improvements/debt
    RESEARCH = "research"  # Research and exploration
    INFRASTRUCTURE = "infrastructure"  # Infrastructure changes


@dataclass
class EpicTemplate:
    """Template for creating epics with predefined structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    type: EpicType = EpicType.FEATURE
    
    # Template fields
    title_template: str = ""
    vision_template: str = ""
    goals_template: List[str] = field(default_factory=list)
    success_criteria_template: List[str] = field(default_factory=list)
    
    # Default values
    default_priority: Priority = Priority.MEDIUM
    default_target_duration_weeks: int = 4
    
    # Story breakdown
    story_templates: List[Dict[str, Any]] = field(default_factory=list)
    
    # Dependencies
    default_dependencies: List[str] = field(default_factory=list)
    
    # Tags and labels
    default_tags: List[str] = field(default_factory=list)
    default_labels: Dict[str, str] = field(default_factory=dict)
    
    # Variables to be filled
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EpicTemplate':
        """Create template from dictionary"""
        # Convert string enums back to enum types
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = EpicType(data['type'])
        if 'default_priority' in data and isinstance(data['default_priority'], str):
            data['default_priority'] = Priority(data['default_priority'])
        return cls(**data)


@dataclass
class Epic:
    """Represents an epic in the agile process"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    vision: str = ""
    goals: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    # Metadata
    type: EpicType = EpicType.FEATURE
    status: EpicStatus = EpicStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    
    # Timeline
    created_date: datetime = field(default_factory=datetime.now)
    start_date: Optional[datetime] = None
    target_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Relationships
    story_ids: Set[str] = field(default_factory=set)
    dependency_ids: Set[str] = field(default_factory=set)  # Other epics this depends on
    blocked_by: Set[str] = field(default_factory=set)  # Epics blocked by this one
    
    # Team
    owner: str = ""
    team: str = ""
    stakeholders: List[str] = field(default_factory=list)
    
    # Progress tracking
    total_stories: int = 0
    completed_stories: int = 0
    total_story_points: int = 0
    completed_story_points: int = 0
    
    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    notes: List[Dict[str, Any]] = field(default_factory=list)  # Timestamped notes
    
    def add_story(self, story_id: str) -> None:
        """Add a story to this epic"""
        self.story_ids.add(story_id)
        self.total_stories = len(self.story_ids)
    
    def remove_story(self, story_id: str) -> None:
        """Remove a story from this epic"""
        self.story_ids.discard(story_id)
        self.total_stories = len(self.story_ids)
    
    def add_dependency(self, epic_id: str) -> None:
        """Add a dependency to another epic"""
        self.dependency_ids.add(epic_id)
    
    def add_note(self, note: str, author: str = "system") -> None:
        """Add a timestamped note"""
        self.notes.append({
            "timestamp": datetime.now().isoformat(),
            "author": author,
            "note": note
        })
    
    def calculate_progress(self) -> float:
        """Calculate progress percentage based on story points"""
        if self.total_story_points == 0:
            return 0.0
        return (self.completed_story_points / self.total_story_points) * 100
    
    def is_complete(self) -> bool:
        """Check if all stories are complete"""
        return self.completed_stories == self.total_stories and self.total_stories > 0
    
    def is_blocked(self) -> bool:
        """Check if epic is blocked by dependencies"""
        return len(self.dependency_ids) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert epic to dictionary"""
        data = asdict(self)
        # Convert sets to lists for JSON serialization
        data['story_ids'] = list(self.story_ids)
        data['dependency_ids'] = list(self.dependency_ids)
        data['blocked_by'] = list(self.blocked_by)
        # Convert enums to strings
        data['type'] = self.type.value
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        # Convert dates to ISO format
        data['created_date'] = self.created_date.isoformat()
        if self.start_date:
            data['start_date'] = self.start_date.isoformat()
        if self.target_completion:
            data['target_completion'] = self.target_completion.isoformat()
        if self.actual_completion:
            data['actual_completion'] = self.actual_completion.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Epic':
        """Create epic from dictionary"""
        # Convert lists back to sets
        if 'story_ids' in data:
            data['story_ids'] = set(data['story_ids'])
        if 'dependency_ids' in data:
            data['dependency_ids'] = set(data['dependency_ids'])
        if 'blocked_by' in data:
            data['blocked_by'] = set(data['blocked_by'])
        # Convert string enums back to enum types
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = EpicType(data['type'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = EpicStatus(data['status'])
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = Priority(data['priority'])
        # Convert ISO strings back to datetime
        if 'created_date' in data and isinstance(data['created_date'], str):
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        if 'start_date' in data and data['start_date']:
            data['start_date'] = datetime.fromisoformat(data['start_date'])
        if 'target_completion' in data and data['target_completion']:
            data['target_completion'] = datetime.fromisoformat(data['target_completion'])
        if 'actual_completion' in data and data['actual_completion']:
            data['actual_completion'] = datetime.fromisoformat(data['actual_completion'])
        return cls(**data)


class EpicManager:
    """Manages epic lifecycle and relationships"""
    
    def __init__(self, story_manager: Optional['StoryManager'] = None):
        """Initialize epic manager"""
        self.epics: Dict[str, Epic] = {}
        self.templates: Dict[str, EpicTemplate] = {}
        self.story_manager = story_manager
        self._load_default_templates()
        logger.info("EpicManager initialized")
    
    def _load_default_templates(self) -> None:
        """Load default epic templates"""
        # Feature epic template
        feature_template = EpicTemplate(
            name="feature_epic",
            description="Template for new feature epics",
            type=EpicType.FEATURE,
            title_template="Epic: {feature_name}",
            vision_template="Deliver {feature_name} to enable {business_value}",
            goals_template=[
                "Implement core {feature_name} functionality",
                "Ensure scalability and performance",
                "Provide comprehensive documentation",
                "Enable monitoring and observability"
            ],
            success_criteria_template=[
                "All user stories completed and accepted",
                "Performance benchmarks met",
                "Documentation reviewed and approved",
                "Zero critical bugs in production"
            ],
            default_priority=Priority.HIGH,
            default_target_duration_weeks=6,
            story_templates=[
                {"type": "research", "title": "Research {feature_name} requirements"},
                {"type": "design", "title": "Design {feature_name} architecture"},
                {"type": "implementation", "title": "Implement {feature_name} core"},
                {"type": "testing", "title": "Test {feature_name} functionality"},
                {"type": "documentation", "title": "Document {feature_name}"}
            ],
            required_variables=["feature_name", "business_value"]
        )
        self.templates["feature_epic"] = feature_template
        
        # Technical debt epic template
        tech_debt_template = EpicTemplate(
            name="tech_debt_epic",
            description="Template for technical debt epics",
            type=EpicType.TECHNICAL,
            title_template="Tech Debt: {debt_area}",
            vision_template="Improve {debt_area} to reduce maintenance burden and improve reliability",
            goals_template=[
                "Refactor {debt_area} codebase",
                "Improve test coverage to 80%+",
                "Update documentation",
                "Eliminate deprecated dependencies"
            ],
            success_criteria_template=[
                "Code quality metrics improved by 30%",
                "Test coverage above 80%",
                "All deprecated dependencies removed",
                "Performance improved by 20%"
            ],
            default_priority=Priority.MEDIUM,
            default_target_duration_weeks=4,
            required_variables=["debt_area"]
        )
        self.templates["tech_debt_epic"] = tech_debt_template
        
        # Research epic template
        research_template = EpicTemplate(
            name="research_epic",
            description="Template for research and exploration epics",
            type=EpicType.RESEARCH,
            title_template="Research: {research_topic}",
            vision_template="Explore {research_topic} to inform strategic decisions",
            goals_template=[
                "Conduct thorough analysis of {research_topic}",
                "Create proof of concept implementations",
                "Document findings and recommendations",
                "Present results to stakeholders"
            ],
            success_criteria_template=[
                "Research report completed and reviewed",
                "POC demonstrates feasibility",
                "Recommendations approved by stakeholders",
                "Knowledge transferred to team"
            ],
            default_priority=Priority.LOW,
            default_target_duration_weeks=2,
            required_variables=["research_topic"]
        )
        self.templates["research_epic"] = research_template
    
    def create_epic(self, 
                   title: str,
                   vision: str,
                   type: EpicType = EpicType.FEATURE,
                   priority: Priority = Priority.MEDIUM,
                   **kwargs) -> Epic:
        """Create a new epic"""
        epic = Epic(
            title=title,
            vision=vision,
            type=type,
            priority=priority,
            **kwargs
        )
        
        self.epics[epic.id] = epic
        epic.add_note(f"Epic created: {title}")
        logger.info(f"Created epic: {epic.id} - {title}")
        
        return epic
    
    def create_epic_from_template(self,
                                 template_name: str,
                                 variables: Dict[str, Any]) -> Epic:
        """Create an epic from a template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Validate required variables
        missing = set(template.required_variables) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Format template strings
        def format_template(template_str: str) -> str:
            try:
                return template_str.format(**variables)
            except KeyError as e:
                logger.warning(f"Variable {e} not found in template")
                return template_str
        
        # Format lists
        def format_list(template_list: List[str]) -> List[str]:
            return [format_template(item) for item in template_list]
        
        # Create epic
        epic = Epic(
            title=format_template(template.title_template),
            vision=format_template(template.vision_template),
            goals=format_list(template.goals_template),
            success_criteria=format_list(template.success_criteria_template),
            type=template.type,
            priority=template.default_priority,
            tags=template.default_tags.copy(),
            labels=template.default_labels.copy()
        )
        
        # Add to registry
        self.epics[epic.id] = epic
        epic.add_note(f"Epic created from template: {template_name}")
        
        # Create associated stories if story manager is available
        if self.story_manager and template.story_templates:
            for story_template in template.story_templates:
                try:
                    story_title = format_template(story_template.get('title', ''))
                    # Create story through story manager
                    story = self.story_manager.create_story(
                        title=story_title,
                        type=story_template.get('type', 'user_story'),
                        epic_id=epic.id
                    )
                    epic.add_story(story.id)
                except Exception as e:
                    logger.warning(f"Failed to create story from template: {e}")
        
        logger.info(f"Created epic from template: {epic.id} - {epic.title}")
        return epic
    
    def get_epic(self, epic_id: str) -> Optional[Epic]:
        """Get epic by ID"""
        return self.epics.get(epic_id)
    
    def update_epic_status(self, epic_id: str, status: EpicStatus) -> bool:
        """Update epic status"""
        epic = self.get_epic(epic_id)
        if not epic:
            logger.warning(f"Epic not found: {epic_id}")
            return False
        
        old_status = epic.status
        epic.status = status
        
        # Update dates based on status
        if status == EpicStatus.ACTIVE and not epic.start_date:
            epic.start_date = datetime.now()
        elif status == EpicStatus.COMPLETED:
            epic.actual_completion = datetime.now()
        
        epic.add_note(f"Status changed from {old_status.value} to {status.value}")
        logger.info(f"Epic {epic_id} status updated: {old_status.value} -> {status.value}")
        
        return True
    
    def add_story_to_epic(self, epic_id: str, story_id: str) -> bool:
        """Add a story to an epic"""
        epic = self.get_epic(epic_id)
        if not epic:
            logger.warning(f"Epic not found: {epic_id}")
            return False
        
        epic.add_story(story_id)
        epic.add_note(f"Story added: {story_id}")
        
        # Update progress if story manager is available
        if self.story_manager:
            self.update_epic_progress(epic_id)
        
        logger.info(f"Story {story_id} added to epic {epic_id}")
        return True
    
    def remove_story_from_epic(self, epic_id: str, story_id: str) -> bool:
        """Remove a story from an epic"""
        epic = self.get_epic(epic_id)
        if not epic:
            logger.warning(f"Epic not found: {epic_id}")
            return False
        
        epic.remove_story(story_id)
        epic.add_note(f"Story removed: {story_id}")
        
        # Update progress if story manager is available
        if self.story_manager:
            self.update_epic_progress(epic_id)
        
        logger.info(f"Story {story_id} removed from epic {epic_id}")
        return True
    
    def add_epic_dependency(self, epic_id: str, dependency_id: str) -> bool:
        """Add a dependency between epics"""
        epic = self.get_epic(epic_id)
        dependency = self.get_epic(dependency_id)
        
        if not epic or not dependency:
            logger.warning(f"Epic not found: {epic_id} or {dependency_id}")
            return False
        
        # Check for circular dependencies
        if self._would_create_circular_dependency(epic_id, dependency_id):
            logger.error(f"Adding dependency would create circular reference")
            return False
        
        epic.add_dependency(dependency_id)
        dependency.blocked_by.add(epic_id)
        
        epic.add_note(f"Dependency added: {dependency_id}")
        logger.info(f"Epic {epic_id} now depends on {dependency_id}")
        
        return True
    
    def _would_create_circular_dependency(self, epic_id: str, dependency_id: str) -> bool:
        """Check if adding a dependency would create a circular reference"""
        visited = set()
        
        def has_path(from_id: str, to_id: str) -> bool:
            if from_id == to_id:
                return True
            if from_id in visited:
                return False
            
            visited.add(from_id)
            epic = self.get_epic(from_id)
            if not epic:
                return False
            
            for dep_id in epic.dependency_ids:
                if has_path(dep_id, to_id):
                    return True
            
            return False
        
        # Check if dependency already has a path to epic
        return has_path(dependency_id, epic_id)
    
    def update_epic_progress(self, epic_id: str) -> None:
        """Update epic progress based on story completion"""
        epic = self.get_epic(epic_id)
        if not epic or not self.story_manager:
            return
        
        total_stories = 0
        completed_stories = 0
        total_points = 0
        completed_points = 0
        
        for story_id in epic.story_ids:
            story = self.story_manager.get_story(story_id)
            if story:
                total_stories += 1
                total_points += story.story_points or 0
                
                if story.status in [StoryStatus.DONE, StoryStatus.ACCEPTED]:
                    completed_stories += 1
                    completed_points += story.story_points or 0
        
        epic.total_stories = total_stories
        epic.completed_stories = completed_stories
        epic.total_story_points = total_points
        epic.completed_story_points = completed_points
        
        # Auto-complete epic if all stories are done
        if epic.is_complete() and epic.status == EpicStatus.ACTIVE:
            self.update_epic_status(epic_id, EpicStatus.COMPLETED)
        
        logger.info(f"Updated progress for epic {epic_id}: "
                   f"{completed_stories}/{total_stories} stories, "
                   f"{completed_points}/{total_points} points")
    
    def get_epic_progress_report(self, epic_id: str) -> Dict[str, Any]:
        """Generate a progress report for an epic"""
        epic = self.get_epic(epic_id)
        if not epic:
            return {}
        
        report = {
            "epic_id": epic.id,
            "title": epic.title,
            "status": epic.status.value,
            "progress_percentage": epic.calculate_progress(),
            "stories": {
                "total": epic.total_stories,
                "completed": epic.completed_stories,
                "remaining": epic.total_stories - epic.completed_stories
            },
            "story_points": {
                "total": epic.total_story_points,
                "completed": epic.completed_story_points,
                "remaining": epic.total_story_points - epic.completed_story_points
            },
            "timeline": {
                "created": epic.created_date.isoformat(),
                "started": epic.start_date.isoformat() if epic.start_date else None,
                "target": epic.target_completion.isoformat() if epic.target_completion else None,
                "actual": epic.actual_completion.isoformat() if epic.actual_completion else None
            },
            "dependencies": {
                "depends_on": list(epic.dependency_ids),
                "blocks": list(epic.blocked_by),
                "is_blocked": epic.is_blocked()
            }
        }
        
        # Add story details if story manager is available
        if self.story_manager:
            story_details = []
            for story_id in epic.story_ids:
                story = self.story_manager.get_story(story_id)
                if story:
                    story_details.append({
                        "id": story.id,
                        "title": story.title,
                        "status": story.status.value,
                        "points": story.story_points
                    })
            report["story_details"] = story_details
        
        return report
    
    def get_epics_by_status(self, status: EpicStatus) -> List[Epic]:
        """Get all epics with a specific status"""
        return [epic for epic in self.epics.values() if epic.status == status]
    
    def get_active_epics(self) -> List[Epic]:
        """Get all active epics"""
        return self.get_epics_by_status(EpicStatus.ACTIVE)
    
    def get_blocked_epics(self) -> List[Epic]:
        """Get all blocked epics"""
        return [epic for epic in self.epics.values() if epic.is_blocked()]
    
    def generate_epic_report(self, epic_id: str, format: str = "markdown") -> str:
        """Generate a comprehensive report for an epic"""
        epic = self.get_epic(epic_id)
        if not epic:
            return "Epic not found"
        
        progress_report = self.get_epic_progress_report(epic_id)
        
        if format == "markdown":
            return self._generate_markdown_report(epic, progress_report)
        elif format == "json":
            return json.dumps(progress_report, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown_report(self, epic: Epic, progress: Dict[str, Any]) -> str:
        """Generate markdown report for an epic"""
        lines = []
        
        # Header
        lines.append(f"# Epic Report: {epic.title}")
        lines.append(f"**ID**: {epic.id}")
        lines.append(f"**Status**: {epic.status.value.upper()}")
        lines.append(f"**Type**: {epic.type.value}")
        lines.append(f"**Priority**: {epic.priority.value.upper()}")
        lines.append("")
        
        # Vision and Goals
        lines.append("## Vision")
        lines.append(epic.vision)
        lines.append("")
        
        if epic.goals:
            lines.append("## Goals")
            for goal in epic.goals:
                lines.append(f"- {goal}")
            lines.append("")
        
        # Success Criteria
        if epic.success_criteria:
            lines.append("## Success Criteria")
            for criterion in epic.success_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.append("")
        
        # Progress
        lines.append("## Progress")
        lines.append(f"**Overall**: {progress['progress_percentage']:.1f}%")
        lines.append(f"**Stories**: {progress['stories']['completed']}/{progress['stories']['total']} completed")
        lines.append(f"**Story Points**: {progress['story_points']['completed']}/{progress['story_points']['total']} completed")
        lines.append("")
        
        # Timeline
        lines.append("## Timeline")
        lines.append(f"- **Created**: {progress['timeline']['created']}")
        if progress['timeline']['started']:
            lines.append(f"- **Started**: {progress['timeline']['started']}")
        if progress['timeline']['target']:
            lines.append(f"- **Target Completion**: {progress['timeline']['target']}")
        if progress['timeline']['actual']:
            lines.append(f"- **Actual Completion**: {progress['timeline']['actual']}")
        lines.append("")
        
        # Dependencies
        if progress['dependencies']['depends_on'] or progress['dependencies']['blocks']:
            lines.append("## Dependencies")
            if progress['dependencies']['depends_on']:
                lines.append("### Depends On")
                for dep_id in progress['dependencies']['depends_on']:
                    dep_epic = self.get_epic(dep_id)
                    if dep_epic:
                        lines.append(f"- {dep_epic.title} ({dep_epic.status.value})")
            if progress['dependencies']['blocks']:
                lines.append("### Blocks")
                for blocked_id in progress['dependencies']['blocks']:
                    blocked_epic = self.get_epic(blocked_id)
                    if blocked_epic:
                        lines.append(f"- {blocked_epic.title} ({blocked_epic.status.value})")
            lines.append("")
        
        # Story Details
        if 'story_details' in progress and progress['story_details']:
            lines.append("## Stories")
            for story in progress['story_details']:
                status_icon = "✅" if story['status'] in ['done', 'accepted'] else "⏳"
                points_str = f" ({story['points']} pts)" if story['points'] else ""
                lines.append(f"- {status_icon} {story['title']}{points_str} - {story['status'].upper()}")
            lines.append("")
        
        # Team
        if epic.owner or epic.team or epic.stakeholders:
            lines.append("## Team")
            if epic.owner:
                lines.append(f"**Owner**: {epic.owner}")
            if epic.team:
                lines.append(f"**Team**: {epic.team}")
            if epic.stakeholders:
                lines.append(f"**Stakeholders**: {', '.join(epic.stakeholders)}")
            lines.append("")
        
        # Notes
        if epic.notes:
            lines.append("## Notes")
            for note in epic.notes[-5:]:  # Last 5 notes
                lines.append(f"- [{note['timestamp']}] {note['author']}: {note['note']}")
            lines.append("")
        
        # Tags and Labels
        if epic.tags or epic.labels:
            lines.append("## Metadata")
            if epic.tags:
                lines.append(f"**Tags**: {', '.join(epic.tags)}")
            if epic.labels:
                lines.append("**Labels**:")
                for key, value in epic.labels.items():
                    lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def export_epics(self, file_path: str) -> None:
        """Export all epics to JSON file"""
        data = {
            "epics": [epic.to_dict() for epic in self.epics.values()],
            "templates": [template.to_dict() for template in self.templates.values()],
            "export_date": datetime.now().isoformat()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(self.epics)} epics to {file_path}")
    
    def import_epics(self, file_path: str) -> None:
        """Import epics from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Import templates
        if 'templates' in data:
            for template_data in data['templates']:
                template = EpicTemplate.from_dict(template_data)
                self.templates[template.name] = template
        
        # Import epics
        if 'epics' in data:
            for epic_data in data['epics']:
                epic = Epic.from_dict(epic_data)
                self.epics[epic.id] = epic
        
        logger.info(f"Imported {len(self.epics)} epics from {file_path}")
    
    def get_roadmap(self) -> List[Dict[str, Any]]:
        """Generate a roadmap view of all epics"""
        roadmap = []
        
        for epic in sorted(self.epics.values(), 
                          key=lambda e: (e.priority.value, e.created_date)):
            roadmap_item = {
                "id": epic.id,
                "title": epic.title,
                "type": epic.type.value,
                "status": epic.status.value,
                "priority": epic.priority.value,
                "progress": epic.calculate_progress(),
                "start_date": epic.start_date.isoformat() if epic.start_date else None,
                "target_completion": epic.target_completion.isoformat() if epic.target_completion else None,
                "dependencies": list(epic.dependency_ids),
                "is_blocked": epic.is_blocked()
            }
            roadmap.append(roadmap_item)
        
        return roadmap


# Example usage
if __name__ == "__main__":
    # Create epic manager
    manager = EpicManager()
    
    # Create epic from template
    epic = manager.create_epic_from_template(
        "feature_epic",
        {
            "feature_name": "User Authentication",
            "business_value": "secure user access and personalization"
        }
    )
    
    print(f"Created epic: {epic.title}")
    
    # Update progress
    epic.total_stories = 5
    epic.completed_stories = 2
    epic.total_story_points = 21
    epic.completed_story_points = 8
    
    # Generate report
    report = manager.generate_epic_report(epic.id, format="markdown")
    print("\n" + report)
    
    # Export
    manager.export_epics("epics_backup.json")