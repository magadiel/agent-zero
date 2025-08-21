"""
Story Management System for Agile AI Company

This module provides comprehensive user story lifecycle management including
templates, state transitions, acceptance criteria tracking, and DoD validation.
"""

import json
import uuid
import os
from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging
import yaml

# Import from existing modules
from agile.product_backlog import Story, StoryStatus, StoryType, Priority, AcceptanceCriteria

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StoryTransition(Enum):
    """Valid story state transitions"""
    CREATE = "create"  # None -> DRAFT
    REFINE = "refine"  # DRAFT -> READY
    PLAN = "plan"  # READY -> IN_SPRINT
    START = "start"  # IN_SPRINT -> IN_PROGRESS
    REVIEW = "review"  # IN_PROGRESS -> IN_REVIEW
    COMPLETE = "complete"  # IN_REVIEW -> DONE
    ACCEPT = "accept"  # DONE -> ACCEPTED
    REJECT = "reject"  # IN_REVIEW -> IN_PROGRESS
    BLOCK = "block"  # Any -> BLOCKED
    UNBLOCK = "unblock"  # BLOCKED -> Previous state
    CANCEL = "cancel"  # Any -> CANCELLED


@dataclass
class StoryTemplate:
    """Template for creating stories with predefined structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    type: StoryType = StoryType.USER_STORY
    
    # Template fields
    title_template: str = ""
    description_template: str = ""
    
    # User story format templates
    as_a_template: str = ""
    i_want_template: str = ""
    so_that_template: str = ""
    
    # Default values
    default_priority: Priority = Priority.MEDIUM
    default_points: Optional[int] = None
    default_business_value: int = 0
    
    # Predefined criteria
    acceptance_criteria_templates: List[str] = field(default_factory=list)
    definition_of_done_items: List[str] = field(default_factory=list)
    
    # Tags and labels
    default_tags: List[str] = field(default_factory=list)
    default_labels: Dict[str, str] = field(default_factory=dict)
    
    # Variables to be filled
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    
    def create_story(self, variables: Dict[str, Any]) -> Story:
        """Create a story from this template"""
        # Validate required variables
        missing = set(self.required_variables) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Format template strings
        def format_template(template: str) -> str:
            try:
                return template.format(**variables)
            except KeyError as e:
                logger.warning(f"Variable {e} not found in template")
                return template
        
        # Create story
        story = Story(
            title=format_template(self.title_template),
            description=format_template(self.description_template),
            type=self.type,
            priority=self.default_priority,
            story_points=self.default_points,
            business_value=self.default_business_value,
            as_a=format_template(self.as_a_template),
            i_want=format_template(self.i_want_template),
            so_that=format_template(self.so_that_template),
            tags=self.default_tags.copy(),
            labels=self.default_labels.copy(),
            definition_of_done=self.definition_of_done_items.copy()
        )
        
        # Add acceptance criteria
        for ac_template in self.acceptance_criteria_templates:
            story.acceptance_criteria.append(
                AcceptanceCriteria(
                    description=format_template(ac_template),
                    is_met=False
                )
            )
        
        return story


@dataclass
class DoDChecklist:
    """Definition of Done checklist for stories"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default DoD"
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_item(self, description: str, category: str = "general", 
                 is_automated: bool = False, validation_script: Optional[str] = None):
        """Add an item to the DoD checklist"""
        self.items.append({
            'id': str(uuid.uuid4()),
            'description': description,
            'category': category,
            'is_automated': is_automated,
            'validation_script': validation_script,
            'is_checked': False,
            'checked_at': None,
            'checked_by': None,
            'notes': ""
        })
    
    def validate(self, story: Story) -> Tuple[bool, List[str]]:
        """Validate a story against the DoD checklist"""
        failures = []
        
        for item in self.items:
            if item['is_automated'] and item['validation_script']:
                # Execute validation script (in production, this would be sandboxed)
                try:
                    # For now, we'll simulate validation
                    item['is_checked'] = True
                except Exception as e:
                    item['is_checked'] = False
                    failures.append(f"{item['description']}: {str(e)}")
            
            if not item['is_checked']:
                failures.append(item['description'])
        
        return len(failures) == 0, failures


class StoryStateError(Exception):
    """Exception raised for invalid story state transitions"""
    pass


class StoryManager:
    """Manages story lifecycle, templates, and validation"""
    
    def __init__(self):
        self.stories: Dict[str, Story] = {}
        self.templates: Dict[str, StoryTemplate] = {}
        self.dod_checklists: Dict[str, DoDChecklist] = {}
        self.state_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize default DoD checklist
        self._initialize_default_dod()
        
        # Initialize default templates
        self._initialize_default_templates()
        
        # Track blocked stories
        self.blocked_stories: Dict[str, str] = {}  # story_id -> previous_state
    
    def _initialize_default_dod(self):
        """Create default Definition of Done checklist"""
        dod = DoDChecklist(name="Default DoD")
        
        # Development items
        dod.add_item("Code is written and compiles without errors", "development")
        dod.add_item("Code follows team coding standards", "development")
        dod.add_item("Unit tests are written and pass", "development", is_automated=True)
        dod.add_item("Integration tests pass", "development", is_automated=True)
        
        # Review items
        dod.add_item("Code has been peer reviewed", "review")
        dod.add_item("Code review comments have been addressed", "review")
        
        # Documentation items
        dod.add_item("Code is properly documented", "documentation")
        dod.add_item("User documentation is updated", "documentation")
        dod.add_item("API documentation is updated", "documentation")
        
        # Testing items
        dod.add_item("Acceptance criteria are met", "testing")
        dod.add_item("Story has been tested in staging environment", "testing")
        dod.add_item("No critical bugs remain open", "testing")
        
        # Deployment items
        dod.add_item("Code is merged to main branch", "deployment")
        dod.add_item("Deployment scripts are updated", "deployment")
        dod.add_item("Monitoring is configured", "deployment")
        
        self.dod_checklists['default'] = dod
    
    def _initialize_default_templates(self):
        """Create default story templates"""
        # User Story template
        user_story = StoryTemplate(
            name="User Story",
            description="Standard user story template",
            type=StoryType.USER_STORY,
            title_template="{feature_name} for {user_type}",
            description_template="Enable {user_type} to {action} in order to {benefit}",
            as_a_template="{user_type}",
            i_want_template="to {action}",
            so_that_template="I can {benefit}",
            acceptance_criteria_templates=[
                "Given {context}, when {action}, then {outcome}",
                "The {feature_name} should be accessible from {location}",
                "Performance should not degrade by more than {threshold}%"
            ],
            required_variables=['feature_name', 'user_type', 'action', 'benefit'],
            optional_variables=['context', 'outcome', 'location', 'threshold'],
            default_tags=['user-story']
        )
        self.templates['user_story'] = user_story
        
        # Bug template
        bug = StoryTemplate(
            name="Bug Report",
            description="Template for bug reports",
            type=StoryType.BUG,
            title_template="[BUG] {summary}",
            description_template="Steps to reproduce:\n{steps}\n\nExpected: {expected}\nActual: {actual}",
            acceptance_criteria_templates=[
                "Bug can no longer be reproduced",
                "Root cause has been identified and fixed",
                "Regression test has been added"
            ],
            required_variables=['summary', 'steps', 'expected', 'actual'],
            default_priority=Priority.HIGH,
            default_tags=['bug', 'defect']
        )
        self.templates['bug'] = bug
        
        # Technical Debt template
        tech_debt = StoryTemplate(
            name="Technical Debt",
            description="Template for technical debt items",
            type=StoryType.TECHNICAL_STORY,
            title_template="[TECH DEBT] {component} - {issue}",
            description_template="Refactor {component} to address {issue}.\nImpact: {impact}\nProposed solution: {solution}",
            acceptance_criteria_templates=[
                "Code quality metrics improve by {metric_improvement}",
                "No functionality is broken",
                "Performance is maintained or improved"
            ],
            required_variables=['component', 'issue', 'impact', 'solution'],
            optional_variables=['metric_improvement'],
            default_tags=['technical-debt', 'refactoring']
        )
        self.templates['tech_debt'] = tech_debt
        
        # Research Spike template
        spike = StoryTemplate(
            name="Research Spike",
            description="Template for research and investigation tasks",
            type=StoryType.SPIKE,
            title_template="[SPIKE] Research {topic}",
            description_template="Investigate {topic} to determine {goal}.\nTimeboxed to {timebox} hours.",
            acceptance_criteria_templates=[
                "Research findings are documented",
                "Recommendations are provided",
                "Next steps are identified"
            ],
            required_variables=['topic', 'goal', 'timebox'],
            default_tags=['spike', 'research']
        )
        self.templates['spike'] = spike
    
    def create_story_from_template(self, template_name: str, variables: Dict[str, Any]) -> Story:
        """Create a story from a template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        story = template.create_story(variables)
        
        # Add to manager
        self.stories[story.id] = story
        
        # Initialize state history
        self._record_state_change(story.id, None, StoryStatus.DRAFT, "Created from template")
        
        logger.info(f"Created story '{story.title}' from template '{template_name}'")
        return story
    
    def create_story(self, title: str, description: str, **kwargs) -> Story:
        """Create a story directly without template"""
        story = Story(
            title=title,
            description=description,
            **kwargs
        )
        
        self.stories[story.id] = story
        self._record_state_change(story.id, None, story.status, "Created directly")
        
        logger.info(f"Created story '{story.title}'")
        return story
    
    def update_story_state(self, story_id: str, transition: StoryTransition, 
                          notes: str = "", actor: str = "system") -> Story:
        """Update story state with validation"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        story = self.stories[story_id]
        old_status = story.status
        
        # Handle state transitions
        if transition == StoryTransition.CREATE:
            if story.status != StoryStatus.DRAFT:
                raise StoryStateError(f"Cannot create story in {story.status} state")
        
        elif transition == StoryTransition.REFINE:
            if story.status != StoryStatus.DRAFT:
                raise StoryStateError(f"Cannot refine story in {story.status} state")
            # Check readiness requirements (without checking status)
            if not (story.title and story.description and 
                   story.story_points is not None and 
                   len(story.acceptance_criteria) > 0):
                raise StoryStateError("Story does not meet Definition of Ready")
            story.status = StoryStatus.READY
        
        elif transition == StoryTransition.PLAN:
            if story.status != StoryStatus.READY:
                raise StoryStateError(f"Cannot plan story in {story.status} state")
            story.status = StoryStatus.IN_SPRINT
        
        elif transition == StoryTransition.START:
            if story.status != StoryStatus.IN_SPRINT:
                raise StoryStateError(f"Cannot start story in {story.status} state")
            story.status = StoryStatus.IN_PROGRESS
        
        elif transition == StoryTransition.REVIEW:
            if story.status != StoryStatus.IN_PROGRESS:
                raise StoryStateError(f"Cannot review story in {story.status} state")
            story.status = StoryStatus.IN_REVIEW
        
        elif transition == StoryTransition.COMPLETE:
            if story.status != StoryStatus.IN_REVIEW:
                raise StoryStateError(f"Cannot complete story in {story.status} state")
            
            # Validate DoD
            is_valid, failures = self.validate_dod(story_id)
            if not is_valid:
                raise StoryStateError(f"Story does not meet DoD: {', '.join(failures)}")
            
            story.status = StoryStatus.DONE
            story.completed_at = datetime.now()
        
        elif transition == StoryTransition.ACCEPT:
            if story.status != StoryStatus.DONE:
                raise StoryStateError(f"Cannot accept story in {story.status} state")
            story.status = StoryStatus.ACCEPTED
        
        elif transition == StoryTransition.REJECT:
            if story.status != StoryStatus.IN_REVIEW:
                raise StoryStateError(f"Cannot reject story in {story.status} state")
            story.status = StoryStatus.IN_PROGRESS
        
        elif transition == StoryTransition.BLOCK:
            if story.status == StoryStatus.BLOCKED:
                raise StoryStateError("Story is already blocked")
            self.blocked_stories[story_id] = story.status.value
            story.status = StoryStatus.BLOCKED
        
        elif transition == StoryTransition.UNBLOCK:
            if story.status != StoryStatus.BLOCKED:
                raise StoryStateError("Story is not blocked")
            if story_id in self.blocked_stories:
                previous_status = self.blocked_stories.pop(story_id)
                story.status = StoryStatus(previous_status)
            else:
                story.status = StoryStatus.IN_PROGRESS
        
        elif transition == StoryTransition.CANCEL:
            story.status = StoryStatus.CANCELLED
        
        else:
            raise ValueError(f"Unknown transition: {transition}")
        
        # Update timestamp
        story.updated_at = datetime.now()
        
        # Record state change
        self._record_state_change(story_id, old_status, story.status, notes, actor)
        
        logger.info(f"Story '{story.title}' transitioned from {old_status} to {story.status}")
        return story
    
    def _record_state_change(self, story_id: str, old_status: Optional[StoryStatus], 
                           new_status: StoryStatus, notes: str = "", actor: str = "system"):
        """Record story state change history"""
        if story_id not in self.state_history:
            self.state_history[story_id] = []
        
        self.state_history[story_id].append({
            'timestamp': datetime.now().isoformat(),
            'old_status': old_status.value if old_status else None,
            'new_status': new_status.value,
            'notes': notes,
            'actor': actor
        })
    
    def update_acceptance_criteria(self, story_id: str, criteria_index: int, 
                                  is_met: bool, verified_by: str = ""):
        """Update acceptance criteria status"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        story = self.stories[story_id]
        if criteria_index >= len(story.acceptance_criteria):
            raise ValueError(f"Invalid criteria index: {criteria_index}")
        
        criteria = story.acceptance_criteria[criteria_index]
        criteria.is_met = is_met
        criteria.verified_by = verified_by
        criteria.verified_at = datetime.now() if is_met else None
        
        story.updated_at = datetime.now()
        
        logger.info(f"Updated acceptance criteria {criteria_index} for story '{story.title}'")
    
    def validate_dod(self, story_id: str, checklist_name: str = 'default') -> Tuple[bool, List[str]]:
        """Validate story against Definition of Done"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        if checklist_name not in self.dod_checklists:
            raise ValueError(f"DoD checklist '{checklist_name}' not found")
        
        story = self.stories[story_id]
        checklist = self.dod_checklists[checklist_name]
        
        # First check if all acceptance criteria are met
        if not story.is_done():
            return False, ["Not all acceptance criteria are met"]
        
        # Then validate against DoD checklist
        return checklist.validate(story)
    
    def get_story_by_id(self, story_id: str) -> Optional[Story]:
        """Get a story by ID"""
        return self.stories.get(story_id)
    
    def get_stories_by_status(self, status: StoryStatus) -> List[Story]:
        """Get all stories with a specific status"""
        return [s for s in self.stories.values() if s.status == status]
    
    def get_stories_by_sprint(self, sprint_id: str) -> List[Story]:
        """Get all stories in a specific sprint"""
        return [s for s in self.stories.values() if s.sprint_id == sprint_id]
    
    def get_blocked_stories(self) -> List[Story]:
        """Get all blocked stories"""
        return self.get_stories_by_status(StoryStatus.BLOCKED)
    
    def get_story_history(self, story_id: str) -> List[Dict[str, Any]]:
        """Get state change history for a story"""
        return self.state_history.get(story_id, [])
    
    def estimate_story(self, story_id: str, points: int, estimated_by: str = ""):
        """Add or update story point estimation"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        story = self.stories[story_id]
        old_points = story.story_points
        story.story_points = points
        story.updated_at = datetime.now()
        
        # Record in history
        self._record_state_change(
            story_id, story.status, story.status,
            f"Points changed from {old_points} to {points}",
            estimated_by or "system"
        )
        
        logger.info(f"Updated story points for '{story.title}' from {old_points} to {points}")
    
    def add_story_comment(self, story_id: str, author: str, text: str):
        """Add a comment to a story"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        story = self.stories[story_id]
        story.add_comment(author, text)
        
        logger.info(f"Added comment to story '{story.title}'")
    
    def link_stories(self, story_id: str, linked_story_id: str, 
                    relationship: str = "blocks"):
        """Create relationship between stories"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        if linked_story_id not in self.stories:
            raise ValueError(f"Story '{linked_story_id}' not found")
        
        story = self.stories[story_id]
        linked_story = self.stories[linked_story_id]
        
        if relationship == "blocks":
            if linked_story_id not in story.blocks:
                story.blocks.append(linked_story_id)
            if story_id not in linked_story.blocked_by:
                linked_story.blocked_by.append(story_id)
        elif relationship == "blocked_by":
            if linked_story_id not in story.blocked_by:
                story.blocked_by.append(linked_story_id)
            if story_id not in linked_story.blocks:
                linked_story.blocks.append(story_id)
        else:
            raise ValueError(f"Unknown relationship: {relationship}")
        
        story.updated_at = datetime.now()
        linked_story.updated_at = datetime.now()
        
        logger.info(f"Linked story '{story.title}' {relationship} '{linked_story.title}'")
    
    def generate_story_report(self, story_id: str) -> Dict[str, Any]:
        """Generate comprehensive report for a story"""
        if story_id not in self.stories:
            raise ValueError(f"Story '{story_id}' not found")
        
        story = self.stories[story_id]
        history = self.get_story_history(story_id)
        
        # Calculate cycle time if completed
        cycle_time = None
        if story.completed_at:
            # Find when story started (moved to IN_PROGRESS)
            for entry in history:
                if entry['new_status'] == StoryStatus.IN_PROGRESS.value:
                    start_time = datetime.fromisoformat(entry['timestamp'])
                    cycle_time = (story.completed_at - start_time).total_seconds() / 3600  # hours
                    break
        
        report = {
            'story': asdict(story),
            'history': history,
            'metrics': {
                'cycle_time_hours': cycle_time,
                'state_changes': len(history),
                'acceptance_criteria_count': len(story.acceptance_criteria),
                'acceptance_criteria_met': sum(1 for ac in story.acceptance_criteria if ac.is_met),
                'is_blocked': story.status == StoryStatus.BLOCKED,
                'blocks_count': len(story.blocks),
                'blocked_by_count': len(story.blocked_by)
            },
            'readiness': {
                'is_ready': story.is_ready(),
                'has_description': bool(story.description),
                'has_points': story.story_points is not None,
                'has_acceptance_criteria': len(story.acceptance_criteria) > 0,
                'has_owner': story.assigned_to is not None
            }
        }
        
        return report
    
    def export_to_json(self, file_path: str):
        """Export all stories and templates to JSON"""
        # Convert stories to dict with enum values as strings
        stories_data = {}
        for sid, story in self.stories.items():
            story_dict = asdict(story)
            # Convert enums to values
            story_dict['status'] = story.status.value
            story_dict['type'] = story.type.value
            story_dict['priority'] = story.priority.value
            stories_data[sid] = story_dict
        
        # Convert templates to dict with enum values as strings
        templates_data = {}
        for tid, template in self.templates.items():
            template_dict = asdict(template)
            template_dict['type'] = template.type.value
            template_dict['default_priority'] = template.default_priority.value
            templates_data[tid] = template_dict
        
        data = {
            'stories': stories_data,
            'templates': templates_data,
            'dod_checklists': {cid: asdict(checklist) for cid, checklist in self.dod_checklists.items()},
            'state_history': self.state_history,
            'blocked_stories': self.blocked_stories,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Exported story data to {file_path}")
    
    def import_from_json(self, file_path: str):
        """Import stories and templates from JSON"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Clear existing data
        self.stories.clear()
        self.templates.clear()
        self.dod_checklists.clear()
        self.state_history.clear()
        self.blocked_stories.clear()
        
        # Import stories
        for sid, story_data in data.get('stories', {}).items():
            # Convert string dates back to datetime objects
            for date_field in ['created_at', 'updated_at', 'completed_at']:
                if story_data.get(date_field):
                    story_data[date_field] = datetime.fromisoformat(story_data[date_field])
            
            # Convert status and priority back to enums
            story_data['status'] = StoryStatus(story_data['status'])
            story_data['type'] = StoryType(story_data['type'])
            story_data['priority'] = Priority(story_data['priority'])
            
            # Recreate acceptance criteria
            acceptance_criteria = []
            for ac_data in story_data.get('acceptance_criteria', []):
                if ac_data.get('verified_at'):
                    ac_data['verified_at'] = datetime.fromisoformat(ac_data['verified_at'])
                acceptance_criteria.append(AcceptanceCriteria(**ac_data))
            story_data['acceptance_criteria'] = acceptance_criteria
            
            self.stories[sid] = Story(**story_data)
        
        # Import templates
        for tid, template_data in data.get('templates', {}).items():
            template_data['type'] = StoryType(template_data['type'])
            template_data['default_priority'] = Priority(template_data['default_priority'])
            self.templates[tid] = StoryTemplate(**template_data)
        
        # Import DoD checklists
        for cid, checklist_data in data.get('dod_checklists', {}).items():
            self.dod_checklists[cid] = DoDChecklist(**checklist_data)
        
        # Import history and blocked stories
        self.state_history = data.get('state_history', {})
        self.blocked_stories = data.get('blocked_stories', {})
        
        logger.info(f"Imported story data from {file_path}")


# Helper function for creating common story types
def create_user_story(manager: StoryManager, feature_name: str, user_type: str,
                     action: str, benefit: str, **kwargs) -> Story:
    """Helper to create a user story from common parameters"""
    variables = {
        'feature_name': feature_name,
        'user_type': user_type,
        'action': action,
        'benefit': benefit
    }
    variables.update(kwargs)
    
    return manager.create_story_from_template('user_story', variables)


def create_bug_report(manager: StoryManager, summary: str, steps: str,
                     expected: str, actual: str, **kwargs) -> Story:
    """Helper to create a bug report"""
    variables = {
        'summary': summary,
        'steps': steps,
        'expected': expected,
        'actual': actual
    }
    variables.update(kwargs)
    
    return manager.create_story_from_template('bug', variables)


def create_tech_debt(manager: StoryManager, component: str, issue: str,
                    impact: str, solution: str, **kwargs) -> Story:
    """Helper to create a technical debt item"""
    variables = {
        'component': component,
        'issue': issue,
        'impact': impact,
        'solution': solution
    }
    variables.update(kwargs)
    
    return manager.create_story_from_template('tech_debt', variables)


def create_spike(manager: StoryManager, topic: str, goal: str,
                timebox: int, **kwargs) -> Story:
    """Helper to create a research spike"""
    variables = {
        'topic': topic,
        'goal': goal,
        'timebox': timebox
    }
    variables.update(kwargs)
    
    return manager.create_story_from_template('spike', variables)