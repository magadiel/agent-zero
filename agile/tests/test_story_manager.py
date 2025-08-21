"""
Unit tests for Story Management System
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agile.story_manager import (
    StoryManager, StoryTemplate, DoDChecklist, StoryTransition,
    StoryStateError, create_user_story, create_bug_report,
    create_tech_debt, create_spike
)
from agile.product_backlog import (
    Story, StoryStatus, StoryType, Priority, AcceptanceCriteria
)


class TestStoryManager(unittest.TestCase):
    """Test cases for StoryManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = StoryManager()
    
    def test_create_story_directly(self):
        """Test direct story creation"""
        story = self.manager.create_story(
            title="Test Story",
            description="Test Description",
            type=StoryType.USER_STORY,
            priority=Priority.HIGH
        )
        
        self.assertIsNotNone(story)
        self.assertEqual(story.title, "Test Story")
        self.assertEqual(story.description, "Test Description")
        self.assertEqual(story.type, StoryType.USER_STORY)
        self.assertEqual(story.priority, Priority.HIGH)
        self.assertEqual(story.status, StoryStatus.DRAFT)
        self.assertIn(story.id, self.manager.stories)
    
    def test_create_story_from_template(self):
        """Test story creation from template"""
        story = create_user_story(
            self.manager,
            feature_name="Login",
            user_type="customer",
            action="sign in",
            benefit="access my account"
        )
        
        self.assertIsNotNone(story)
        self.assertEqual(story.title, "Login for customer")
        self.assertEqual(story.as_a, "customer")
        self.assertEqual(story.i_want, "to sign in")
        self.assertEqual(story.so_that, "I can access my account")
        self.assertTrue(len(story.acceptance_criteria) > 0)
    
    def test_story_state_transitions(self):
        """Test valid story state transitions"""
        story = self.manager.create_story("Test Story", "Description")
        
        # Add requirements for READY state
        story.story_points = 5
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Test criteria", is_met=False)
        )
        
        # DRAFT -> READY
        self.manager.update_story_state(story.id, StoryTransition.REFINE)
        self.assertEqual(story.status, StoryStatus.READY)
        
        # READY -> IN_SPRINT
        self.manager.update_story_state(story.id, StoryTransition.PLAN)
        self.assertEqual(story.status, StoryStatus.IN_SPRINT)
        
        # IN_SPRINT -> IN_PROGRESS
        self.manager.update_story_state(story.id, StoryTransition.START)
        self.assertEqual(story.status, StoryStatus.IN_PROGRESS)
        
        # IN_PROGRESS -> IN_REVIEW
        self.manager.update_story_state(story.id, StoryTransition.REVIEW)
        self.assertEqual(story.status, StoryStatus.IN_REVIEW)
    
    def test_invalid_state_transition(self):
        """Test invalid story state transition raises error"""
        story = self.manager.create_story("Test Story", "Description")
        
        # Try to start a story that's not in sprint
        with self.assertRaises(StoryStateError):
            self.manager.update_story_state(story.id, StoryTransition.START)
    
    def test_story_blocking(self):
        """Test story blocking and unblocking"""
        story = self.manager.create_story("Test Story", "Description")
        story.story_points = 5
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Test", is_met=False)
        )
        
        # Move to IN_PROGRESS
        self.manager.update_story_state(story.id, StoryTransition.REFINE)
        self.manager.update_story_state(story.id, StoryTransition.PLAN)
        self.manager.update_story_state(story.id, StoryTransition.START)
        self.assertEqual(story.status, StoryStatus.IN_PROGRESS)
        
        # Block the story
        self.manager.update_story_state(story.id, StoryTransition.BLOCK)
        self.assertEqual(story.status, StoryStatus.BLOCKED)
        self.assertIn(story.id, self.manager.blocked_stories)
        
        # Unblock the story
        self.manager.update_story_state(story.id, StoryTransition.UNBLOCK)
        self.assertEqual(story.status, StoryStatus.IN_PROGRESS)
        self.assertNotIn(story.id, self.manager.blocked_stories)
    
    def test_acceptance_criteria_update(self):
        """Test updating acceptance criteria"""
        story = self.manager.create_story("Test Story", "Description")
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Criteria 1", is_met=False)
        )
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Criteria 2", is_met=False)
        )
        
        # Update first criteria
        self.manager.update_acceptance_criteria(story.id, 0, True, "tester")
        self.assertTrue(story.acceptance_criteria[0].is_met)
        self.assertEqual(story.acceptance_criteria[0].verified_by, "tester")
        self.assertIsNotNone(story.acceptance_criteria[0].verified_at)
        
        # Second criteria should remain unchanged
        self.assertFalse(story.acceptance_criteria[1].is_met)
    
    def test_dod_validation(self):
        """Test Definition of Done validation"""
        story = self.manager.create_story("Test Story", "Description")
        story.story_points = 5
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Test criteria", is_met=False)
        )
        
        # Should fail if acceptance criteria not met
        is_valid, failures = self.manager.validate_dod(story.id)
        self.assertFalse(is_valid)
        self.assertIn("Not all acceptance criteria are met", failures)
        
        # Mark acceptance criteria as met
        story.acceptance_criteria[0].is_met = True
        story.status = StoryStatus.DONE
        
        # Should still have DoD checklist items to validate
        is_valid, failures = self.manager.validate_dod(story.id)
        self.assertFalse(is_valid)  # DoD checklist items not checked
        self.assertTrue(len(failures) > 0)
    
    def test_story_estimation(self):
        """Test story point estimation"""
        story = self.manager.create_story("Test Story", "Description")
        
        self.assertIsNone(story.story_points)
        
        self.manager.estimate_story(story.id, 8, "estimator")
        self.assertEqual(story.story_points, 8)
        
        # Check history
        history = self.manager.get_story_history(story.id)
        self.assertTrue(any("Points changed" in h['notes'] for h in history))
    
    def test_story_linking(self):
        """Test linking stories"""
        story1 = self.manager.create_story("Story 1", "Description 1")
        story2 = self.manager.create_story("Story 2", "Description 2")
        
        # Create blocking relationship
        self.manager.link_stories(story1.id, story2.id, "blocks")
        
        self.assertIn(story2.id, story1.blocks)
        self.assertIn(story1.id, story2.blocked_by)
    
    def test_story_comments(self):
        """Test adding comments to stories"""
        story = self.manager.create_story("Test Story", "Description")
        
        self.manager.add_story_comment(story.id, "author1", "First comment")
        self.manager.add_story_comment(story.id, "author2", "Second comment")
        
        self.assertEqual(len(story.comments), 2)
        self.assertEqual(story.comments[0]['author'], "author1")
        self.assertEqual(story.comments[0]['text'], "First comment")
    
    def test_get_stories_by_status(self):
        """Test filtering stories by status"""
        # Create stories in different states
        story1 = self.manager.create_story("Story 1", "Desc 1")
        story2 = self.manager.create_story("Story 2", "Desc 2")
        story3 = self.manager.create_story("Story 3", "Desc 3")
        
        # Set up story2 for READY state
        story2.story_points = 5
        story2.acceptance_criteria.append(
            AcceptanceCriteria(description="Test", is_met=False)
        )
        self.manager.update_story_state(story2.id, StoryTransition.REFINE)
        
        # Get stories by status
        draft_stories = self.manager.get_stories_by_status(StoryStatus.DRAFT)
        ready_stories = self.manager.get_stories_by_status(StoryStatus.READY)
        
        self.assertEqual(len(draft_stories), 2)
        self.assertEqual(len(ready_stories), 1)
        self.assertIn(story2, ready_stories)
    
    def test_story_report_generation(self):
        """Test generating story report"""
        story = self.manager.create_story("Test Story", "Description")
        story.story_points = 5
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Criteria 1", is_met=True)
        )
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Criteria 2", is_met=False)
        )
        
        report = self.manager.generate_story_report(story.id)
        
        self.assertIn('story', report)
        self.assertIn('history', report)
        self.assertIn('metrics', report)
        self.assertIn('readiness', report)
        
        # Check metrics
        metrics = report['metrics']
        self.assertEqual(metrics['acceptance_criteria_count'], 2)
        self.assertEqual(metrics['acceptance_criteria_met'], 1)
        self.assertFalse(metrics['is_blocked'])
        
        # Check readiness
        readiness = report['readiness']
        self.assertTrue(readiness['has_description'])
        self.assertTrue(readiness['has_points'])
        self.assertTrue(readiness['has_acceptance_criteria'])
    
    def test_template_variable_validation(self):
        """Test template variable validation"""
        template = self.manager.templates['user_story']
        
        # Missing required variables should raise error
        with self.assertRaises(ValueError) as context:
            template.create_story({'feature_name': 'Login'})  # Missing other required vars
        
        self.assertIn("Missing required variables", str(context.exception))
    
    def test_export_import_json(self):
        """Test exporting and importing data"""
        # Create some test data
        story1 = self.manager.create_story("Story 1", "Description 1")
        story2 = create_user_story(
            self.manager,
            feature_name="Feature",
            user_type="user",
            action="action",
            benefit="benefit"
        )
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.manager.export_to_json(temp_file)
            
            # Create new manager and import
            new_manager = StoryManager()
            new_manager.import_from_json(temp_file)
            
            # Verify data was imported correctly
            self.assertEqual(len(new_manager.stories), 2)
            self.assertIn(story1.id, new_manager.stories)
            self.assertIn(story2.id, new_manager.stories)
            
            # Check that story details match
            imported_story1 = new_manager.get_story_by_id(story1.id)
            self.assertEqual(imported_story1.title, story1.title)
            self.assertEqual(imported_story1.description, story1.description)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_bug_template(self):
        """Test bug report template"""
        story = create_bug_report(
            self.manager,
            summary="Login button not working",
            steps="1. Go to login page\n2. Click login button",
            expected="Should navigate to dashboard",
            actual="Nothing happens"
        )
        
        self.assertEqual(story.type, StoryType.BUG)
        self.assertEqual(story.priority, Priority.HIGH)
        self.assertIn("[BUG]", story.title)
        self.assertIn("bug", story.tags)
    
    def test_tech_debt_template(self):
        """Test technical debt template"""
        story = create_tech_debt(
            self.manager,
            component="Database layer",
            issue="Inefficient queries",
            impact="Slow page load times",
            solution="Optimize queries and add indexes"
        )
        
        self.assertEqual(story.type, StoryType.TECHNICAL_STORY)
        self.assertIn("[TECH DEBT]", story.title)
        self.assertIn("technical-debt", story.tags)
    
    def test_spike_template(self):
        """Test research spike template"""
        story = create_spike(
            self.manager,
            topic="New authentication method",
            goal="feasibility and implementation approach",
            timebox=16
        )
        
        self.assertEqual(story.type, StoryType.SPIKE)
        self.assertIn("[SPIKE]", story.title)
        self.assertIn("spike", story.tags)
        self.assertIn("16", story.description)
    
    def test_dod_checklist_items(self):
        """Test DoD checklist items"""
        checklist = self.manager.dod_checklists['default']
        
        # Should have items in various categories
        categories = set(item['category'] for item in checklist.items)
        self.assertIn('development', categories)
        self.assertIn('review', categories)
        self.assertIn('documentation', categories)
        self.assertIn('testing', categories)
        self.assertIn('deployment', categories)
        
        # Should have some automated items
        automated_items = [item for item in checklist.items if item['is_automated']]
        self.assertTrue(len(automated_items) > 0)
    
    def test_state_history_tracking(self):
        """Test state change history tracking"""
        story = self.manager.create_story("Test Story", "Description")
        story.story_points = 5
        story.acceptance_criteria.append(
            AcceptanceCriteria(description="Test", is_met=False)
        )
        
        # Make several state transitions
        self.manager.update_story_state(story.id, StoryTransition.REFINE, "Ready for sprint")
        self.manager.update_story_state(story.id, StoryTransition.PLAN, "Added to sprint")
        self.manager.update_story_state(story.id, StoryTransition.START, "Development started")
        
        history = self.manager.get_story_history(story.id)
        
        # Should have 4 entries (creation + 3 transitions)
        self.assertEqual(len(history), 4)
        
        # Check transition notes
        self.assertEqual(history[1]['notes'], "Ready for sprint")
        self.assertEqual(history[2]['notes'], "Added to sprint")
        self.assertEqual(history[3]['notes'], "Development started")
        
        # Check state values
        self.assertEqual(history[1]['new_status'], StoryStatus.READY.value)
        self.assertEqual(history[2]['new_status'], StoryStatus.IN_SPRINT.value)
        self.assertEqual(history[3]['new_status'], StoryStatus.IN_PROGRESS.value)


if __name__ == '__main__':
    unittest.main()