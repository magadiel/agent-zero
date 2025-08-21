"""
Story Operations Tool for Agent-Zero

This tool provides story management capabilities for AI agents,
enabling them to create, update, and manage user stories throughout
their lifecycle.
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import asdict

# Agent-Zero imports
from python.helpers.tool import Tool, Response
from python.helpers import files

# Import story management components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agile.story_manager import (
    StoryManager, StoryTemplate, DoDChecklist, StoryTransition,
    create_user_story, create_bug_report, create_tech_debt, create_spike
)
from agile.product_backlog import StoryStatus, StoryType, Priority


class StoryOperations(Tool):
    """
    Tool for managing user stories in the agile development process.
    Provides capabilities for story creation, state management, validation, and reporting.
    """
    
    def __init__(self, agent):
        super().__init__(agent)
        self.story_manager = StoryManager()
        
        # Load any existing story data
        self.data_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'stories.json'
        )
        self._load_data()
    
    def _load_data(self):
        """Load existing story data if available"""
        if os.path.exists(self.data_file):
            try:
                self.story_manager.import_from_json(self.data_file)
                self.agent.context.log.log(
                    "STORY_OPERATIONS",
                    f"Loaded {len(self.story_manager.stories)} existing stories"
                )
            except Exception as e:
                self.agent.context.log.log(
                    "STORY_OPERATIONS",
                    f"Could not load existing stories: {e}",
                    error=True
                )
    
    def _save_data(self):
        """Save story data to disk"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            self.story_manager.export_to_json(self.data_file)
            self.agent.context.log.log(
                "STORY_OPERATIONS",
                f"Saved {len(self.story_manager.stories)} stories to disk"
            )
        except Exception as e:
            self.agent.context.log.log(
                "STORY_OPERATIONS",
                f"Could not save stories: {e}",
                error=True
            )
    
    async def execute(self, **kwargs):
        """
        Execute story operations based on the provided action.
        
        Actions:
        - create_story: Create a new story (with or without template)
        - create_from_template: Create story from a specific template
        - update_state: Transition story to a new state
        - update_acceptance_criteria: Mark acceptance criteria as met/unmet
        - validate_dod: Check if story meets Definition of Done
        - estimate: Add or update story points
        - link: Create relationship between stories
        - get_story: Get story details
        - list_stories: List stories by various filters
        - generate_report: Generate comprehensive story report
        - add_comment: Add a comment to a story
        """
        action = kwargs.get('action', 'list_stories')
        
        try:
            if action == 'create_story':
                return await self._create_story(kwargs)
            elif action == 'create_from_template':
                return await self._create_from_template(kwargs)
            elif action == 'update_state':
                return await self._update_state(kwargs)
            elif action == 'update_acceptance_criteria':
                return await self._update_acceptance_criteria(kwargs)
            elif action == 'validate_dod':
                return await self._validate_dod(kwargs)
            elif action == 'estimate':
                return await self._estimate_story(kwargs)
            elif action == 'link':
                return await self._link_stories(kwargs)
            elif action == 'get_story':
                return await self._get_story(kwargs)
            elif action == 'list_stories':
                return await self._list_stories(kwargs)
            elif action == 'generate_report':
                return await self._generate_report(kwargs)
            elif action == 'add_comment':
                return await self._add_comment(kwargs)
            else:
                return Response(
                    message=f"Unknown action: {action}",
                    success=False
                )
        except Exception as e:
            return Response(
                message=f"Error executing story operation: {str(e)}",
                success=False
            )
    
    async def _create_story(self, kwargs: Dict[str, Any]) -> Response:
        """Create a new story"""
        title = kwargs.get('title', '')
        description = kwargs.get('description', '')
        story_type = kwargs.get('type', 'user_story')
        
        if not title:
            return Response(
                message="Story title is required",
                success=False
            )
        
        # Map story type string to enum
        type_map = {
            'user_story': StoryType.USER_STORY,
            'bug': StoryType.BUG,
            'technical_story': StoryType.TECHNICAL_STORY,
            'tech_debt': StoryType.TECHNICAL_STORY,
            'spike': StoryType.SPIKE,
            'task': StoryType.TASK,
            'epic': StoryType.EPIC
        }
        
        story_type_enum = type_map.get(story_type, StoryType.USER_STORY)
        
        # Create story
        story = self.story_manager.create_story(
            title=title,
            description=description,
            type=story_type_enum,
            priority=Priority(kwargs.get('priority', 3)),  # Default MEDIUM
            story_points=kwargs.get('points'),
            business_value=kwargs.get('business_value', 0),
            as_a=kwargs.get('as_a', ''),
            i_want=kwargs.get('i_want', ''),
            so_that=kwargs.get('so_that', ''),
            tags=kwargs.get('tags', []),
            assigned_to=kwargs.get('assigned_to'),
            team_id=kwargs.get('team_id')
        )
        
        # Add acceptance criteria if provided
        acceptance_criteria = kwargs.get('acceptance_criteria', [])
        for criteria in acceptance_criteria:
            from agile.product_backlog import AcceptanceCriteria
            story.acceptance_criteria.append(
                AcceptanceCriteria(description=criteria, is_met=False)
            )
        
        # Save data
        self._save_data()
        
        return Response(
            message=f"Created story: {story.title}",
            success=True,
            data={
                'story_id': story.id,
                'title': story.title,
                'status': story.status.value,
                'type': story.type.value
            }
        )
    
    async def _create_from_template(self, kwargs: Dict[str, Any]) -> Response:
        """Create story from a template"""
        template_type = kwargs.get('template', 'user_story')
        
        if template_type == 'user_story':
            story = create_user_story(
                self.story_manager,
                feature_name=kwargs.get('feature_name', 'New Feature'),
                user_type=kwargs.get('user_type', 'user'),
                action=kwargs.get('action', 'perform action'),
                benefit=kwargs.get('benefit', 'achieve goal'),
                context=kwargs.get('context', 'using the application'),
                outcome=kwargs.get('outcome', 'see expected result'),
                location=kwargs.get('location', 'main menu'),
                threshold=kwargs.get('threshold', '10')
            )
        elif template_type == 'bug':
            story = create_bug_report(
                self.story_manager,
                summary=kwargs.get('summary', 'Bug summary'),
                steps=kwargs.get('steps', '1. Step one\n2. Step two'),
                expected=kwargs.get('expected', 'Expected behavior'),
                actual=kwargs.get('actual', 'Actual behavior')
            )
        elif template_type == 'tech_debt':
            story = create_tech_debt(
                self.story_manager,
                component=kwargs.get('component', 'Component'),
                issue=kwargs.get('issue', 'Technical issue'),
                impact=kwargs.get('impact', 'Performance impact'),
                solution=kwargs.get('solution', 'Proposed solution'),
                metric_improvement=kwargs.get('metric_improvement', '20%')
            )
        elif template_type == 'spike':
            story = create_spike(
                self.story_manager,
                topic=kwargs.get('topic', 'Research topic'),
                goal=kwargs.get('goal', 'Research goal'),
                timebox=kwargs.get('timebox', 8)
            )
        else:
            return Response(
                message=f"Unknown template: {template_type}",
                success=False
            )
        
        # Save data
        self._save_data()
        
        return Response(
            message=f"Created story from template: {story.title}",
            success=True,
            data={
                'story_id': story.id,
                'title': story.title,
                'template': template_type,
                'status': story.status.value
            }
        )
    
    async def _update_state(self, kwargs: Dict[str, Any]) -> Response:
        """Update story state"""
        story_id = kwargs.get('story_id')
        transition = kwargs.get('transition')
        notes = kwargs.get('notes', '')
        actor = kwargs.get('actor', self.agent.name)
        
        if not story_id or not transition:
            return Response(
                message="story_id and transition are required",
                success=False
            )
        
        # Map transition string to enum
        transition_map = {
            'create': StoryTransition.CREATE,
            'refine': StoryTransition.REFINE,
            'plan': StoryTransition.PLAN,
            'start': StoryTransition.START,
            'review': StoryTransition.REVIEW,
            'complete': StoryTransition.COMPLETE,
            'accept': StoryTransition.ACCEPT,
            'reject': StoryTransition.REJECT,
            'block': StoryTransition.BLOCK,
            'unblock': StoryTransition.UNBLOCK,
            'cancel': StoryTransition.CANCEL
        }
        
        transition_enum = transition_map.get(transition)
        if not transition_enum:
            return Response(
                message=f"Invalid transition: {transition}",
                success=False
            )
        
        try:
            story = self.story_manager.update_story_state(
                story_id, transition_enum, notes, actor
            )
            
            # Save data
            self._save_data()
            
            return Response(
                message=f"Story '{story.title}' transitioned to {story.status.value}",
                success=True,
                data={
                    'story_id': story.id,
                    'title': story.title,
                    'new_status': story.status.value,
                    'transition': transition
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to update story state: {str(e)}",
                success=False
            )
    
    async def _update_acceptance_criteria(self, kwargs: Dict[str, Any]) -> Response:
        """Update acceptance criteria status"""
        story_id = kwargs.get('story_id')
        criteria_index = kwargs.get('criteria_index', 0)
        is_met = kwargs.get('is_met', False)
        verified_by = kwargs.get('verified_by', self.agent.name)
        
        if not story_id:
            return Response(
                message="story_id is required",
                success=False
            )
        
        try:
            self.story_manager.update_acceptance_criteria(
                story_id, criteria_index, is_met, verified_by
            )
            
            # Save data
            self._save_data()
            
            story = self.story_manager.get_story_by_id(story_id)
            criteria = story.acceptance_criteria[criteria_index]
            
            return Response(
                message=f"Updated acceptance criteria: {'Met' if is_met else 'Not met'}",
                success=True,
                data={
                    'story_id': story_id,
                    'criteria_index': criteria_index,
                    'description': criteria.description,
                    'is_met': is_met
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to update acceptance criteria: {str(e)}",
                success=False
            )
    
    async def _validate_dod(self, kwargs: Dict[str, Any]) -> Response:
        """Validate story against Definition of Done"""
        story_id = kwargs.get('story_id')
        checklist_name = kwargs.get('checklist', 'default')
        
        if not story_id:
            return Response(
                message="story_id is required",
                success=False
            )
        
        try:
            is_valid, failures = self.story_manager.validate_dod(story_id, checklist_name)
            story = self.story_manager.get_story_by_id(story_id)
            
            return Response(
                message=f"DoD validation {'passed' if is_valid else 'failed'}",
                success=True,
                data={
                    'story_id': story_id,
                    'title': story.title,
                    'is_valid': is_valid,
                    'failures': failures,
                    'checklist': checklist_name
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to validate DoD: {str(e)}",
                success=False
            )
    
    async def _estimate_story(self, kwargs: Dict[str, Any]) -> Response:
        """Add or update story points"""
        story_id = kwargs.get('story_id')
        points = kwargs.get('points')
        estimated_by = kwargs.get('estimated_by', self.agent.name)
        
        if not story_id or points is None:
            return Response(
                message="story_id and points are required",
                success=False
            )
        
        try:
            self.story_manager.estimate_story(story_id, points, estimated_by)
            
            # Save data
            self._save_data()
            
            story = self.story_manager.get_story_by_id(story_id)
            
            return Response(
                message=f"Updated story points to {points}",
                success=True,
                data={
                    'story_id': story_id,
                    'title': story.title,
                    'points': points,
                    'estimated_by': estimated_by
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to estimate story: {str(e)}",
                success=False
            )
    
    async def _link_stories(self, kwargs: Dict[str, Any]) -> Response:
        """Create relationship between stories"""
        story_id = kwargs.get('story_id')
        linked_story_id = kwargs.get('linked_story_id')
        relationship = kwargs.get('relationship', 'blocks')
        
        if not story_id or not linked_story_id:
            return Response(
                message="story_id and linked_story_id are required",
                success=False
            )
        
        try:
            self.story_manager.link_stories(story_id, linked_story_id, relationship)
            
            # Save data
            self._save_data()
            
            story = self.story_manager.get_story_by_id(story_id)
            linked_story = self.story_manager.get_story_by_id(linked_story_id)
            
            return Response(
                message=f"Linked stories: {story.title} {relationship} {linked_story.title}",
                success=True,
                data={
                    'story_id': story_id,
                    'linked_story_id': linked_story_id,
                    'relationship': relationship
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to link stories: {str(e)}",
                success=False
            )
    
    async def _get_story(self, kwargs: Dict[str, Any]) -> Response:
        """Get story details"""
        story_id = kwargs.get('story_id')
        
        if not story_id:
            return Response(
                message="story_id is required",
                success=False
            )
        
        story = self.story_manager.get_story_by_id(story_id)
        if not story:
            return Response(
                message=f"Story not found: {story_id}",
                success=False
            )
        
        return Response(
            message=f"Retrieved story: {story.title}",
            success=True,
            data={
                'story': asdict(story),
                'history': self.story_manager.get_story_history(story_id)
            }
        )
    
    async def _list_stories(self, kwargs: Dict[str, Any]) -> Response:
        """List stories by various filters"""
        filter_by = kwargs.get('filter_by', 'all')
        filter_value = kwargs.get('filter_value')
        
        if filter_by == 'status' and filter_value:
            status_map = {
                'draft': StoryStatus.DRAFT,
                'ready': StoryStatus.READY,
                'in_sprint': StoryStatus.IN_SPRINT,
                'in_progress': StoryStatus.IN_PROGRESS,
                'in_review': StoryStatus.IN_REVIEW,
                'done': StoryStatus.DONE,
                'accepted': StoryStatus.ACCEPTED,
                'blocked': StoryStatus.BLOCKED,
                'cancelled': StoryStatus.CANCELLED
            }
            status = status_map.get(filter_value)
            if status:
                stories = self.story_manager.get_stories_by_status(status)
            else:
                stories = []
        elif filter_by == 'sprint' and filter_value:
            stories = self.story_manager.get_stories_by_sprint(filter_value)
        elif filter_by == 'blocked':
            stories = self.story_manager.get_blocked_stories()
        else:
            stories = list(self.story_manager.stories.values())
        
        # Format stories for response
        story_list = []
        for story in stories:
            story_list.append({
                'id': story.id,
                'title': story.title,
                'type': story.type.value,
                'status': story.status.value,
                'priority': story.priority.value,
                'points': story.story_points,
                'assigned_to': story.assigned_to,
                'sprint_id': story.sprint_id
            })
        
        return Response(
            message=f"Found {len(story_list)} stories",
            success=True,
            data={
                'stories': story_list,
                'filter': {'by': filter_by, 'value': filter_value}
            }
        )
    
    async def _generate_report(self, kwargs: Dict[str, Any]) -> Response:
        """Generate comprehensive story report"""
        story_id = kwargs.get('story_id')
        
        if not story_id:
            return Response(
                message="story_id is required",
                success=False
            )
        
        try:
            report = self.story_manager.generate_story_report(story_id)
            
            # Format report for display
            story = self.story_manager.get_story_by_id(story_id)
            formatted_report = f"""
# Story Report: {story.title}

## Overview
- **ID**: {story.id}
- **Type**: {story.type.value}
- **Status**: {story.status.value}
- **Priority**: {story.priority.value}
- **Points**: {story.story_points or 'Not estimated'}
- **Business Value**: {story.business_value}

## User Story
{story.get_user_story_format()}

## Metrics
- **Cycle Time**: {report['metrics']['cycle_time_hours']:.2f} hours if report['metrics']['cycle_time_hours'] else 'N/A'}
- **State Changes**: {report['metrics']['state_changes']}
- **Acceptance Criteria**: {report['metrics']['acceptance_criteria_met']}/{report['metrics']['acceptance_criteria_count']}
- **Blocked**: {'Yes' if report['metrics']['is_blocked'] else 'No'}
- **Blocks**: {report['metrics']['blocks_count']} stories
- **Blocked By**: {report['metrics']['blocked_by_count']} stories

## Readiness Check
- **Is Ready**: {'✅' if report['readiness']['is_ready'] else '❌'}
- **Has Description**: {'✅' if report['readiness']['has_description'] else '❌'}
- **Has Points**: {'✅' if report['readiness']['has_points'] else '❌'}
- **Has Acceptance Criteria**: {'✅' if report['readiness']['has_acceptance_criteria'] else '❌'}
- **Has Owner**: {'✅' if report['readiness']['has_owner'] else '❌'}
"""
            
            return Response(
                message="Generated story report",
                success=True,
                data={
                    'report': report,
                    'formatted': formatted_report
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to generate report: {str(e)}",
                success=False
            )
    
    async def _add_comment(self, kwargs: Dict[str, Any]) -> Response:
        """Add a comment to a story"""
        story_id = kwargs.get('story_id')
        text = kwargs.get('text', '')
        author = kwargs.get('author', self.agent.name)
        
        if not story_id or not text:
            return Response(
                message="story_id and text are required",
                success=False
            )
        
        try:
            self.story_manager.add_story_comment(story_id, author, text)
            
            # Save data
            self._save_data()
            
            story = self.story_manager.get_story_by_id(story_id)
            
            return Response(
                message=f"Added comment to story: {story.title}",
                success=True,
                data={
                    'story_id': story_id,
                    'title': story.title,
                    'comment': {
                        'author': author,
                        'text': text
                    }
                }
            )
        except Exception as e:
            return Response(
                message=f"Failed to add comment: {str(e)}",
                success=False
            )