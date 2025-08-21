"""
Comprehensive Test Suite for Sprint Manager System

Tests all functionality of the sprint management and product backlog systems.
"""

import unittest
import sys
import os
from datetime import date, datetime, timedelta
import json
import tempfile

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agile.product_backlog import (
    ProductBacklog, Story, StoryStatus, StoryType, 
    Priority, AcceptanceCriteria
)
from agile.sprint_manager import (
    SprintManager, Sprint, SprintStatus, SprintGoal,
    DailyProgress, SprintRetrospective
)


class TestProductBacklog(unittest.TestCase):
    """Test suite for ProductBacklog functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backlog = ProductBacklog()
        
        # Create test stories
        self.story1 = Story(
            title="User Login",
            description="Implement user login functionality",
            as_a="user",
            i_want="to log in",
            so_that="I can access my account",
            story_points=5,
            business_value=80,
            priority=Priority.HIGH,
            status=StoryStatus.READY
        )
        
        self.story2 = Story(
            title="Password Reset",
            description="Allow users to reset password",
            story_points=3,
            business_value=60,
            priority=Priority.MEDIUM,
            status=StoryStatus.DRAFT
        )
        
        self.epic = Story(
            title="Authentication System",
            description="Complete auth system",
            type=StoryType.EPIC,
            priority=Priority.HIGH,
            business_value=100
        )
    
    def test_add_story(self):
        """Test adding stories to backlog"""
        story_id = self.backlog.add_story(self.story1)
        self.assertIsNotNone(story_id)
        self.assertEqual(len(self.backlog.stories), 1)
        
        # Test adding epic
        epic_id = self.backlog.add_story(self.epic)
        self.assertIsNotNone(epic_id)
        self.assertEqual(len(self.backlog.epics), 1)
    
    def test_story_prioritization(self):
        """Test story prioritization based on WSJF"""
        # Add stories with different priorities and values
        self.backlog.add_story(self.story1)  # High priority, high value
        self.backlog.add_story(self.story2)  # Medium priority, medium value
        
        prioritized = self.backlog.get_prioritized_stories()
        
        # Story1 should be first (higher priority and value)
        self.assertEqual(prioritized[0].title, "User Login")
    
    def test_story_ready_check(self):
        """Test Definition of Ready validation"""
        # Story1 has all required fields
        self.story1.acceptance_criteria.append(
            AcceptanceCriteria(description="User can log in with email")
        )
        self.assertTrue(self.story1.is_ready())
        
        # Story2 is missing acceptance criteria and is DRAFT
        self.assertFalse(self.story2.is_ready())
    
    def test_story_done_check(self):
        """Test Definition of Done validation"""
        self.story1.acceptance_criteria.append(
            AcceptanceCriteria(description="Test criterion", is_met=False)
        )
        self.assertFalse(self.story1.is_done())
        
        # Meet all criteria and set status
        for ac in self.story1.acceptance_criteria:
            ac.verify("tester")
        self.story1.status = StoryStatus.DONE
        self.assertTrue(self.story1.is_done())
    
    def test_update_story(self):
        """Test updating story properties"""
        story_id = self.backlog.add_story(self.story1)
        
        updates = {
            'story_points': 8,
            'priority': Priority.CRITICAL,
            'status': StoryStatus.IN_PROGRESS
        }
        
        self.assertTrue(self.backlog.update_story(story_id, updates))
        
        story = self.backlog.get_story(story_id)
        self.assertEqual(story.story_points, 8)
        self.assertEqual(story.priority, Priority.CRITICAL)
        self.assertEqual(story.status, StoryStatus.IN_PROGRESS)
    
    def test_epic_progress(self):
        """Test epic progress calculation"""
        epic_id = self.backlog.add_story(self.epic)
        
        # Add stories to epic
        self.story1.epic_id = epic_id
        self.story2.epic_id = epic_id
        self.backlog.add_story(self.story1)
        self.backlog.add_story(self.story2)
        
        # Complete one story
        self.story1.status = StoryStatus.DONE
        
        progress = self.backlog.calculate_epic_progress(epic_id)
        
        self.assertEqual(progress['total'], 2)
        self.assertEqual(progress['completed'], 1)
        self.assertEqual(progress['progress'], 50.0)
        self.assertEqual(progress['points_completed'], 5)
        self.assertEqual(progress['points_total'], 8)
    
    def test_grooming_candidates(self):
        """Test identification of stories needing grooming"""
        # Story2 needs grooming (no acceptance criteria)
        self.backlog.add_story(self.story2)
        
        candidates = self.backlog.grooming_candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Password Reset")
    
    def test_backlog_statistics(self):
        """Test backlog statistics generation"""
        self.backlog.add_story(self.story1)
        self.backlog.add_story(self.story2)
        self.backlog.add_story(self.epic)
        
        stats = self.backlog.get_statistics()
        
        self.assertEqual(stats['total_stories'], 2)
        self.assertEqual(stats['total_epics'], 1)
        self.assertEqual(stats['total_points'], 8)
        self.assertEqual(stats['estimated_stories'], 2)
        self.assertEqual(stats['estimation_coverage'], 100.0)
    
    def test_export_import_json(self):
        """Test JSON export and import"""
        self.backlog.add_story(self.story1)
        self.backlog.add_story(self.epic)
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        self.backlog.export_to_json(temp_file)
        
        # Create new backlog and import
        new_backlog = ProductBacklog()
        new_backlog.import_from_json(temp_file)
        
        self.assertEqual(len(new_backlog.stories), 1)
        self.assertEqual(len(new_backlog.epics), 1)
        
        # Clean up
        os.unlink(temp_file)


class TestSprintManager(unittest.TestCase):
    """Test suite for SprintManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backlog = ProductBacklog()
        self.sprint_manager = SprintManager(self.backlog)
        
        # Create test stories
        self.stories = []
        for i in range(5):
            story = Story(
                title=f"Story {i+1}",
                description=f"Test story {i+1}",
                story_points=(i % 3) + 1,  # 1-3 points
                business_value=50,
                priority=Priority.HIGH,
                status=StoryStatus.READY
            )
            story.acceptance_criteria.append(
                AcceptanceCriteria(description="Test criterion")
            )
            self.backlog.add_story(story)
            self.stories.append(story)
    
    def test_create_sprint(self):
        """Test sprint creation"""
        sprint = self.sprint_manager.create_sprint(
            name="Sprint 1",
            goal="Test sprint creation",
            team_id="team-alpha",
            duration_days=14
        )
        
        self.assertIsNotNone(sprint)
        self.assertEqual(sprint.name, "Sprint 1")
        self.assertEqual(sprint.status, SprintStatus.PLANNING)
        self.assertEqual(sprint.duration_days, 14)
        self.assertIn(sprint.id, self.sprint_manager.sprints)
    
    def test_sprint_capacity_calculation(self):
        """Test sprint capacity calculation"""
        sprint = self.sprint_manager.create_sprint(
            name="Sprint 1",
            goal="Test capacity",
            team_id="team-alpha"
        )
        
        capacity = sprint.calculate_capacity(team_size=5, days_off=2)
        
        # Should calculate based on working days and focus factor
        self.assertGreater(capacity, 0)
        self.assertEqual(sprint.capacity_hours, capacity)
    
    def test_plan_sprint(self):
        """Test sprint planning with stories"""
        sprint = self.sprint_manager.create_sprint(
            name="Sprint 1",
            goal="Test planning",
            team_id="team-alpha"
        )
        
        story_ids = [s.id for s in self.stories[:3]]
        result = self.sprint_manager.plan_sprint(
            sprint.id,
            story_ids,
            team_size=5
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['stories_added'], 3)
        self.assertGreater(result['total_points'], 0)
        
        # Check stories are in sprint
        sprint = self.sprint_manager.sprints[sprint.id]
        self.assertEqual(len(sprint.story_ids), 3)
    
    def test_start_sprint(self):
        """Test starting a sprint"""
        sprint = self.sprint_manager.create_sprint(
            name="Sprint 1",
            goal="Test start",
            team_id="team-alpha"
        )
        
        # Plan sprint first
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        
        # Start sprint
        success = self.sprint_manager.start_sprint(sprint.id)
        self.assertTrue(success)
        
        sprint = self.sprint_manager.sprints[sprint.id]
        self.assertEqual(sprint.status, SprintStatus.ACTIVE)
        self.assertIsNotNone(sprint.started_at)
        self.assertEqual(self.sprint_manager.active_sprint, sprint)
    
    def test_cannot_start_multiple_sprints(self):
        """Test that only one sprint can be active"""
        sprint1 = self.sprint_manager.create_sprint("Sprint 1", "Goal 1", "team-alpha")
        sprint2 = self.sprint_manager.create_sprint("Sprint 2", "Goal 2", "team-alpha")
        
        # Start first sprint
        self.sprint_manager.start_sprint(sprint1.id)
        
        # Try to start second sprint
        success = self.sprint_manager.start_sprint(sprint2.id)
        self.assertFalse(success)
    
    def test_complete_story_in_sprint(self):
        """Test completing a story in active sprint"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Plan and start sprint
        story_ids = [self.stories[0].id]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        # Complete story
        success = self.sprint_manager.complete_story(self.stories[0].id)
        self.assertTrue(success)
        
        story = self.backlog.get_story(self.stories[0].id)
        self.assertEqual(story.status, StoryStatus.DONE)
        self.assertIsNotNone(story.completed_at)
        
        sprint = self.sprint_manager.active_sprint
        self.assertEqual(sprint.completed_points, story.story_points)
    
    def test_add_remove_story_from_sprint(self):
        """Test adding and removing stories from active sprint"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Start with 2 stories
        story_ids = [self.stories[0].id, self.stories[1].id]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        # Add a story
        success = self.sprint_manager.add_story_to_sprint(sprint.id, self.stories[2].id)
        self.assertTrue(success)
        self.assertIn(self.stories[2].id, sprint.story_ids)
        
        # Remove a story
        success = self.sprint_manager.remove_story_from_sprint(sprint.id, self.stories[1].id)
        self.assertTrue(success)
        self.assertNotIn(self.stories[1].id, sprint.story_ids)
    
    def test_daily_standup(self):
        """Test daily standup report generation"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Plan and start sprint
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        # Complete one story
        self.sprint_manager.complete_story(self.stories[0].id)
        
        # Get standup report
        standup = self.sprint_manager.daily_standup()
        
        self.assertEqual(standup['sprint_name'], "Sprint 1")
        self.assertGreater(standup['points_completed'], 0)
        self.assertIn('on_track', standup)
        self.assertIn('burndown_status', standup)
    
    def test_end_sprint(self):
        """Test ending a sprint"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Plan and start sprint
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        # Complete some stories
        self.sprint_manager.complete_story(self.stories[0].id)
        
        # End sprint
        result = self.sprint_manager.end_sprint(sprint.id)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['sprint_name'], "Sprint 1")
        self.assertGreater(result['velocity'], 0)
        self.assertIsNone(self.sprint_manager.active_sprint)
        
        sprint = self.sprint_manager.sprints[sprint.id]
        self.assertEqual(sprint.status, SprintStatus.REVIEW)
    
    def test_sprint_retrospective(self):
        """Test conducting sprint retrospective"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Complete sprint cycle
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        self.sprint_manager.end_sprint(sprint.id)
        
        # Conduct retrospective
        success = self.sprint_manager.conduct_retrospective(
            sprint.id,
            what_went_well=["Good collaboration", "Met sprint goal"],
            what_went_wrong=["Too many meetings"],
            action_items=[
                {'description': "Reduce meetings", 'owner': "Scrum Master"}
            ],
            team_happiness=7.5
        )
        
        self.assertTrue(success)
        
        sprint = self.sprint_manager.sprints[sprint.id]
        self.assertEqual(sprint.status, SprintStatus.CLOSED)
        self.assertIsNotNone(sprint.retrospective)
        self.assertEqual(sprint.retrospective.team_happiness, 7.5)
    
    def test_velocity_metrics(self):
        """Test velocity metrics calculation"""
        # Simulate multiple sprints
        velocities = [20, 22, 18, 25, 21]
        for v in velocities:
            self.sprint_manager.velocity_history.append(v)
        
        metrics = self.sprint_manager.get_velocity_metrics()
        
        self.assertEqual(metrics['average_velocity'], 21.2)
        self.assertEqual(metrics['min_velocity'], 18)
        self.assertEqual(metrics['max_velocity'], 25)
        self.assertIn(metrics['trend'], ['increasing', 'decreasing', 'stable'])
        self.assertGreater(metrics['predictability'], 0)
    
    def test_sprint_capacity_recommendation(self):
        """Test sprint capacity recommendations"""
        # Add velocity history
        self.sprint_manager.velocity_history = [20, 22, 21]
        
        recommendation = self.sprint_manager.recommend_sprint_capacity(team_size=5)
        
        self.assertIn('recommended_points', recommendation)
        self.assertIn('confidence', recommendation)
        self.assertEqual(recommendation['based_on_sprints'], 3)
    
    def test_sprint_burndown(self):
        """Test burndown chart generation"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Plan sprint
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        
        # Generate ideal burndown
        sprint = self.sprint_manager.sprints[sprint.id]
        ideal = sprint.generate_burndown_ideal()
        
        self.assertGreater(len(ideal), 0)
        self.assertEqual(ideal[0], sprint.committed_points)
        self.assertEqual(ideal[-1], 0)
        
        # Get burndown data
        burndown_data = sprint.get_burndown_chart_data()
        self.assertIn('ideal', burndown_data)
        self.assertIn('actual', burndown_data)
        self.assertIn('dates', burndown_data)
    
    def test_sprint_on_track_check(self):
        """Test sprint on-track validation"""
        sprint = self.sprint_manager.create_sprint(
            "Sprint 1", "Goal", "team-alpha",
            start_date=date.today() - timedelta(days=5)
        )
        
        # Plan and start sprint
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        sprint = self.sprint_manager.sprints[sprint.id]
        sprint.generate_burndown_ideal()
        
        # Initially should be on track
        self.assertTrue(sprint.is_on_track())
        
        # Update progress
        sprint.update_daily_progress(self.backlog)
        
        # Still should be on track if no major deviation
        on_track = sprint.is_on_track()
        self.assertIsInstance(on_track, bool)
    
    def test_sprint_report_generation(self):
        """Test comprehensive sprint report"""
        sprint = self.sprint_manager.create_sprint("Sprint 1", "Goal", "team-alpha")
        
        # Plan and start sprint
        story_ids = [s.id for s in self.stories[:3]]
        self.sprint_manager.plan_sprint(sprint.id, story_ids, team_size=5)
        self.sprint_manager.start_sprint(sprint.id)
        
        # Get report
        report = self.sprint_manager.get_sprint_report(sprint.id)
        
        self.assertIn('sprint', report)
        self.assertIn('points', report)
        self.assertIn('stories', report)
        self.assertIn('metrics', report)
        self.assertIn('burndown', report)
        
        self.assertEqual(report['sprint']['name'], "Sprint 1")
        self.assertGreater(report['points']['committed'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete sprint workflow"""
    
    def test_complete_sprint_workflow(self):
        """Test complete sprint workflow from planning to retrospective"""
        # Setup
        backlog = ProductBacklog()
        sprint_manager = SprintManager(backlog)
        
        # Create epic and stories
        epic = Story(
            title="E-commerce Platform",
            type=StoryType.EPIC,
            priority=Priority.HIGH,
            business_value=1000
        )
        epic_id = backlog.add_story(epic)
        
        # Create stories for epic
        stories = []
        for i in range(8):
            story = Story(
                title=f"Feature {i+1}",
                description=f"Implement feature {i+1}",
                epic_id=epic_id,
                story_points=(i % 4) + 2,  # 2-5 points
                business_value=100,
                priority=Priority.HIGH if i < 4 else Priority.MEDIUM,
                status=StoryStatus.READY
            )
            story.acceptance_criteria.append(
                AcceptanceCriteria(description=f"Criterion for feature {i+1}")
            )
            backlog.add_story(story)
            stories.append(story)
        
        # Sprint 1: Planning
        sprint1 = sprint_manager.create_sprint(
            name="Sprint 1",
            goal="Launch MVP features",
            team_id="team-alpha"
        )
        
        # Select high-priority stories
        story_ids = [s.id for s in stories[:4]]
        plan_result = sprint_manager.plan_sprint(sprint1.id, story_ids, team_size=4)
        self.assertTrue(plan_result['success'])
        
        # Start sprint
        self.assertTrue(sprint_manager.start_sprint(sprint1.id))
        
        # Simulate sprint progress
        for i in range(3):
            sprint_manager.complete_story(stories[i].id)
        
        # Daily standup
        standup = sprint_manager.daily_standup()
        self.assertGreater(standup['points_completed'], 0)
        
        # End sprint
        end_result = sprint_manager.end_sprint(sprint1.id)
        self.assertTrue(end_result['success'])
        
        # Retrospective
        sprint_manager.conduct_retrospective(
            sprint1.id,
            what_went_well=["Good teamwork"],
            what_went_wrong=["Underestimated complexity"],
            action_items=[],
            team_happiness=7.0
        )
        
        # Check velocity history
        self.assertEqual(len(sprint_manager.velocity_history), 1)
        
        # Sprint 2: Use velocity for planning
        sprint2 = sprint_manager.create_sprint(
            name="Sprint 2",
            goal="Complete remaining features",
            team_id="team-alpha"
        )
        
        # Get capacity recommendation
        capacity = sprint_manager.recommend_sprint_capacity(team_size=4)
        self.assertGreater(capacity['recommended_points'], 0)
        
        # Check epic progress
        progress = backlog.calculate_epic_progress(epic_id)
        self.assertGreater(progress['completed'], 0)
        self.assertLess(progress['progress'], 100)
    
    def test_backlog_persistence(self):
        """Test saving and loading backlog data"""
        backlog = ProductBacklog()
        
        # Add stories
        for i in range(3):
            story = Story(
                title=f"Story {i+1}",
                story_points=i+1,
                priority=Priority.HIGH,
                status=StoryStatus.READY
            )
            backlog.add_story(story)
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        backlog.export_to_json(temp_file)
        
        # Load in new backlog
        new_backlog = ProductBacklog()
        new_backlog.import_from_json(temp_file)
        
        # Verify data integrity
        self.assertEqual(len(new_backlog.stories), 3)
        
        # Clean up
        os.unlink(temp_file)


def run_tests():
    """Run all test suites"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestProductBacklog))
    suite.addTests(loader.loadTestsFromTestCase(TestSprintManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)