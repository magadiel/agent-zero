"""
Tests for Daily Standup Facilitator

This module contains comprehensive tests for the standup facilitator,
including unit tests for all major functionality.
"""

import unittest
import asyncio
from datetime import datetime, timedelta
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from standup_facilitator import (
    StandupFacilitator,
    TeamMemberStatus,
    Blocker,
    BlockerSeverity,
    StandupReport,
    StandupItemType
)


class TestTeamMemberStatus(unittest.TestCase):
    """Test TeamMemberStatus dataclass"""
    
    def test_create_status(self):
        """Test creating a team member status"""
        status = TeamMemberStatus(
            agent_id="agent_1",
            agent_name="Test Agent",
            timestamp=datetime.now(),
            yesterday_completed=["Task 1", "Task 2"],
            today_planned=["Task 3", "Task 4"],
            blockers=[{"description": "API issue", "severity": "high"}],
            help_needed=["Code review"],
            current_story="STORY-123",
            story_progress=75.0,
            confidence_level=0.8,
            mood="positive"
        )
        
        self.assertEqual(status.agent_id, "agent_1")
        self.assertEqual(status.agent_name, "Test Agent")
        self.assertEqual(len(status.yesterday_completed), 2)
        self.assertEqual(len(status.today_planned), 2)
        self.assertEqual(len(status.blockers), 1)
        self.assertEqual(status.story_progress, 75.0)
        self.assertEqual(status.mood, "positive")
    
    def test_status_to_dict(self):
        """Test converting status to dictionary"""
        status = TeamMemberStatus(
            agent_id="agent_1",
            agent_name="Test Agent",
            timestamp=datetime.now()
        )
        
        status_dict = status.to_dict()
        
        self.assertIn('agent_id', status_dict)
        self.assertIn('timestamp', status_dict)
        self.assertIn('story_progress', status_dict)
        self.assertEqual(status_dict['agent_id'], "agent_1")


class TestBlocker(unittest.TestCase):
    """Test Blocker dataclass"""
    
    def test_create_blocker(self):
        """Test creating a blocker"""
        blocker = Blocker(
            id="blocker_1",
            description="Database connection timeout",
            severity=BlockerSeverity.HIGH,
            affected_agents=["agent_1", "agent_2"],
            affected_stories=["STORY-123"],
            identified_at=datetime.now()
        )
        
        self.assertEqual(blocker.id, "blocker_1")
        self.assertEqual(blocker.severity, BlockerSeverity.HIGH)
        self.assertEqual(len(blocker.affected_agents), 2)
        self.assertFalse(blocker.resolved)
    
    def test_blocker_to_dict(self):
        """Test converting blocker to dictionary"""
        blocker = Blocker(
            id="blocker_1",
            description="Test blocker",
            severity=BlockerSeverity.MEDIUM,
            affected_agents=["agent_1"],
            affected_stories=[],
            identified_at=datetime.now()
        )
        
        blocker_dict = blocker.to_dict()
        
        self.assertEqual(blocker_dict['id'], "blocker_1")
        self.assertEqual(blocker_dict['severity'], "medium")
        self.assertFalse(blocker_dict['resolved'])


class TestStandupReport(unittest.TestCase):
    """Test StandupReport dataclass"""
    
    def test_create_report(self):
        """Test creating a standup report"""
        status = TeamMemberStatus(
            agent_id="agent_1",
            agent_name="Test Agent",
            timestamp=datetime.now()
        )
        
        blocker = Blocker(
            id="blocker_1",
            description="Test blocker",
            severity=BlockerSeverity.HIGH,
            affected_agents=["agent_1"],
            affected_stories=["STORY-123"],
            identified_at=datetime.now()
        )
        
        report = StandupReport(
            standup_id="standup_1",
            team_id="team_alpha",
            sprint_id="sprint_1",
            date=datetime.now(),
            duration_minutes=5.5,
            participants=["agent_1"],
            member_statuses=[status],
            blockers=[blocker],
            team_mood="positive",
            sprint_progress=45.0,
            risks_identified=["Risk 1"],
            help_requests=[],
            action_items=[]
        )
        
        self.assertEqual(report.standup_id, "standup_1")
        self.assertEqual(report.team_id, "team_alpha")
        self.assertEqual(len(report.member_statuses), 1)
        self.assertEqual(len(report.blockers), 1)
        self.assertEqual(report.sprint_progress, 45.0)
    
    def test_report_to_markdown(self):
        """Test generating markdown report"""
        status = TeamMemberStatus(
            agent_id="agent_1",
            agent_name="Test Agent",
            timestamp=datetime.now(),
            yesterday_completed=["Completed feature X"],
            today_planned=["Work on feature Y"],
            current_story="STORY-123",
            story_progress=50.0,
            mood="positive"
        )
        
        report = StandupReport(
            standup_id="standup_1",
            team_id="team_alpha",
            sprint_id="sprint_1",
            date=datetime.now(),
            duration_minutes=5.0,
            participants=["agent_1"],
            member_statuses=[status],
            blockers=[],
            team_mood="positive",
            sprint_progress=45.0,
            risks_identified=[],
            help_requests=[],
            action_items=[]
        )
        
        markdown = report.to_markdown()
        
        self.assertIn("Daily Standup Report", markdown)
        self.assertIn("team_alpha", markdown)
        self.assertIn("Test Agent", markdown)
        self.assertIn("STORY-123", markdown)
        self.assertIn("Completed feature X", markdown)


class TestStandupFacilitator(unittest.TestCase):
    """Test StandupFacilitator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.facilitator = StandupFacilitator("test_team")
    
    def test_facilitator_initialization(self):
        """Test facilitator initialization"""
        self.assertEqual(self.facilitator.team_id, "test_team")
        self.assertEqual(self.facilitator.standup_counter, 0)
        self.assertEqual(len(self.facilitator.standup_history), 0)
        self.assertEqual(len(self.facilitator.active_blockers), 0)
    
    async def _conduct_test_standup(self):
        """Helper to conduct a test standup"""
        team_members = [
            {'id': 'agent_1', 'name': 'Agent One'},
            {'id': 'agent_2', 'name': 'Agent Two'}
        ]
        
        async def mock_collect_status(member):
            blockers = []
            if member['id'] == 'agent_2':
                blockers = [{'description': 'Test blocker', 'severity': 'high'}]
            
            return TeamMemberStatus(
                agent_id=member['id'],
                agent_name=member['name'],
                timestamp=datetime.now(),
                yesterday_completed=["Task completed"],
                today_planned=["Task planned"],
                blockers=blockers,
                current_story="STORY-001",
                story_progress=50.0,
                mood="positive"
            )
        
        return await self.facilitator.conduct_standup(team_members, mock_collect_status)
    
    def test_conduct_standup(self):
        """Test conducting a standup"""
        async def run_test():
            report = await self._conduct_test_standup()
            
            self.assertIsNotNone(report)
            self.assertEqual(report.team_id, "test_team")
            self.assertEqual(len(report.participants), 2)
            self.assertEqual(len(report.member_statuses), 2)
            self.assertGreater(report.duration_minutes, 0)
            
            # Check standup was added to history
            self.assertEqual(len(self.facilitator.standup_history), 1)
            self.assertEqual(self.facilitator.standup_counter, 1)
        
        asyncio.run(run_test())
    
    def test_blocker_analysis(self):
        """Test blocker analysis"""
        statuses = [
            TeamMemberStatus(
                agent_id="agent_1",
                agent_name="Agent One",
                timestamp=datetime.now(),
                blockers=[
                    {'description': 'API timeout', 'severity': 'high'},
                    {'description': 'Missing docs', 'severity': 'low'}
                ]
            ),
            TeamMemberStatus(
                agent_id="agent_2",
                agent_name="Agent Two",
                timestamp=datetime.now(),
                blockers=[
                    {'description': 'API timeout', 'severity': 'high'}  # Same blocker
                ]
            )
        ]
        
        blockers = self.facilitator._analyze_blockers(statuses)
        
        # Should consolidate similar blockers
        self.assertEqual(len(blockers), 2)  # API timeout (consolidated) + Missing docs
        
        # Check severity sorting (high should come first)
        high_severity_blockers = [b for b in blockers if b.severity == BlockerSeverity.HIGH]
        self.assertGreater(len(high_severity_blockers), 0)
    
    def test_team_mood_calculation(self):
        """Test team mood calculation"""
        statuses = [
            TeamMemberStatus(
                agent_id="agent_1",
                agent_name="Agent One",
                timestamp=datetime.now(),
                mood="positive"
            ),
            TeamMemberStatus(
                agent_id="agent_2",
                agent_name="Agent Two",
                timestamp=datetime.now(),
                mood="neutral"
            ),
            TeamMemberStatus(
                agent_id="agent_3",
                agent_name="Agent Three",
                timestamp=datetime.now(),
                mood="positive"
            )
        ]
        
        mood = self.facilitator._calculate_team_mood(statuses)
        self.assertEqual(mood, "positive")  # 2 positive, 1 neutral should be positive overall
        
        # Test with negative moods
        statuses[0].mood = "frustrated"
        statuses[1].mood = "frustrated"
        mood = self.facilitator._calculate_team_mood(statuses)
        self.assertIn(mood, ["concerned", "frustrated"])
    
    def test_risk_identification(self):
        """Test risk identification"""
        # Create statuses with low confidence
        statuses = [
            TeamMemberStatus(
                agent_id=f"agent_{i}",
                agent_name=f"Agent {i}",
                timestamp=datetime.now(),
                confidence_level=0.3,
                mood="frustrated" if i < 2 else "neutral"
            )
            for i in range(3)
        ]
        
        # Create critical blocker
        blocker = Blocker(
            id="blocker_1",
            description="Critical issue",
            severity=BlockerSeverity.CRITICAL,
            affected_agents=["agent_1"],
            affected_stories=["STORY-001"],
            identified_at=datetime.now()
        )
        
        risks = self.facilitator._identify_risks(statuses, [blocker])
        
        # Should identify multiple risks
        self.assertGreater(len(risks), 0)
        
        # Check for specific risks
        risk_descriptions = ' '.join(risks).lower()
        self.assertIn("critical", risk_descriptions)  # Critical blocker risk
        self.assertIn("confidence", risk_descriptions)  # Low confidence risk
    
    def test_help_request_collection(self):
        """Test help request collection"""
        statuses = [
            TeamMemberStatus(
                agent_id="agent_1",
                agent_name="Agent One",
                timestamp=datetime.now(),
                help_needed=["Code review", "Architecture guidance"],
                current_story="STORY-123"
            ),
            TeamMemberStatus(
                agent_id="agent_2",
                agent_name="Agent Two",
                timestamp=datetime.now(),
                help_needed=["Testing help"]
            )
        ]
        
        help_requests = self.facilitator._collect_help_requests(statuses)
        
        self.assertEqual(len(help_requests), 3)  # Total help items
        self.assertEqual(help_requests[0]['from'], "Agent One")
        self.assertEqual(help_requests[0]['story'], "STORY-123")
    
    def test_action_item_generation(self):
        """Test action item generation"""
        blocker = Blocker(
            id="blocker_1",
            description="Database issue",
            severity=BlockerSeverity.CRITICAL,
            affected_agents=["agent_1"],
            affected_stories=["STORY-001"],
            identified_at=datetime.now()
        )
        
        help_request = {
            'from': 'Agent One',
            'agent_id': 'agent_1',
            'description': 'Need code review'
        }
        
        action_items = self.facilitator._generate_action_items([blocker], [help_request])
        
        self.assertEqual(len(action_items), 2)  # One for blocker, one for help
        
        # Check blocker action item
        blocker_action = next(a for a in action_items if 'blocker' in a['related_to'])
        self.assertEqual(blocker_action['priority'], 'high')
        self.assertIn('Database issue', blocker_action['description'])
        
        # Check help action item
        help_action = next(a for a in action_items if 'help_request' in a['related_to'])
        self.assertEqual(help_action['priority'], 'medium')
        self.assertIn('code review', help_action['description'])
    
    def test_blocker_trends(self):
        """Test blocker trend analysis"""
        async def run_test():
            # Conduct multiple standups
            for _ in range(3):
                await self._conduct_test_standup()
            
            trends = self.facilitator.get_blocker_trends(days=7)
            
            self.assertIn('total_blockers', trends)
            self.assertIn('average_blockers_per_day', trends)
            self.assertIn('resolution_rate', trends)
            self.assertGreater(trends['total_blockers'], 0)
        
        asyncio.run(run_test())
    
    def test_participation_metrics(self):
        """Test participation metrics calculation"""
        async def run_test():
            # Conduct a standup
            await self._conduct_test_standup()
            
            metrics = self.facilitator.get_participation_metrics()
            
            self.assertEqual(metrics['total_standups'], 1)
            self.assertGreater(metrics['average_participation'], 0)
            self.assertGreater(metrics['average_duration'], 0)
            self.assertIn(metrics['trend'], ['stable', 'improving', 'declining'])
        
        asyncio.run(run_test())
    
    def test_export_json(self):
        """Test exporting history as JSON"""
        async def run_test():
            # Conduct a standup
            await self._conduct_test_standup()
            
            json_export = self.facilitator.export_history(format='json')
            
            # Parse JSON to verify structure
            data = json.loads(json_export)
            
            self.assertEqual(data['team_id'], 'test_team')
            self.assertEqual(data['standup_count'], 1)
            self.assertEqual(len(data['history']), 1)
            self.assertIn('active_blockers', data)
        
        asyncio.run(run_test())
    
    def test_export_markdown(self):
        """Test exporting history as Markdown"""
        async def run_test():
            # Conduct a standup
            await self._conduct_test_standup()
            
            markdown_export = self.facilitator.export_history(format='markdown')
            
            self.assertIn("# Standup History", markdown_export)
            self.assertIn("test_team", markdown_export)
            self.assertIn("Total Standups: 1", markdown_export)
        
        asyncio.run(run_test())
    
    def test_sprint_progress_calculation(self):
        """Test sprint progress calculation"""
        async def run_test():
            # Without sprint manager, should use standup data
            team_members = [
                {'id': 'agent_1', 'name': 'Agent One'},
                {'id': 'agent_2', 'name': 'Agent Two'}
            ]
            
            async def mock_collect_status(member):
                return TeamMemberStatus(
                    agent_id=member['id'],
                    agent_name=member['name'],
                    timestamp=datetime.now(),
                    story_progress=75.0 if member['id'] == 'agent_1' else 50.0
                )
            
            await self.facilitator.conduct_standup(team_members, mock_collect_status)
            
            progress = await self.facilitator._calculate_sprint_progress()
            
            # Should be average of story progress
            self.assertAlmostEqual(progress, 62.5, places=1)
        
        asyncio.run(run_test())


class TestIntegration(unittest.TestCase):
    """Integration tests for standup facilitator"""
    
    def test_multiple_standups(self):
        """Test conducting multiple standups over time"""
        async def run_test():
            facilitator = StandupFacilitator("integration_team")
            
            team_members = [
                {'id': f'agent_{i}', 'name': f'Agent {i}'}
                for i in range(4)
            ]
            
            # Conduct 5 standups
            for day in range(5):
                async def mock_collect_status(member):
                    # Simulate varying conditions
                    progress = 20 * (day + 1)  # Increasing progress
                    mood = "positive" if day < 3 else "concerned"
                    blockers = []
                    
                    if day == 2 and member['id'] == 'agent_1':
                        blockers = [{'description': 'Integration issue', 'severity': 'high'}]
                    
                    return TeamMemberStatus(
                        agent_id=member['id'],
                        agent_name=member['name'],
                        timestamp=datetime.now(),
                        yesterday_completed=[f"Day {day} tasks"],
                        today_planned=[f"Day {day+1} tasks"],
                        blockers=blockers,
                        current_story=f"STORY-{day+1}",
                        story_progress=progress,
                        mood=mood
                    )
                
                report = await facilitator.conduct_standup(team_members, mock_collect_status)
                
                # Verify report
                self.assertEqual(len(report.participants), 4)
                self.assertLessEqual(report.sprint_progress, 100.0)
            
            # Check history
            self.assertEqual(len(facilitator.standup_history), 5)
            
            # Check trends
            trends = facilitator.get_blocker_trends()
            self.assertGreaterEqual(trends['total_blockers'], 1)
            
            # Check metrics
            metrics = facilitator.get_participation_metrics()
            self.assertEqual(metrics['total_standups'], 5)
            self.assertEqual(metrics['average_participation'], 100.0)
        
        asyncio.run(run_test())


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTeamMemberStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestBlocker))
    suite.addTests(loader.loadTestsFromTestCase(TestStandupReport))
    suite.addTests(loader.loadTestsFromTestCase(TestStandupFacilitator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)