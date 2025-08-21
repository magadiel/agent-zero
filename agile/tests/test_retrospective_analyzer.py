"""
Unit tests for the Retrospective Analyzer system
"""

import unittest
from datetime import datetime, timedelta
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agile.retrospective_analyzer import (
    RetrospectiveAnalyzer,
    FeedbackCategory,
    FeedbackItem,
    ActionItem,
    ActionItemStatus,
    ActionItemPriority,
    Sentiment,
    SentimentAnalyzer,
    PatternDetector,
    ImprovementPattern,
    RetrospectiveReport
)


class TestFeedbackItem(unittest.TestCase):
    """Test FeedbackItem class"""
    
    def test_feedback_creation(self):
        """Test creating feedback item"""
        feedback = FeedbackItem(
            agent_id="agent-1",
            category=FeedbackCategory.WENT_WELL,
            content="Great sprint!",
            sentiment=Sentiment.POSITIVE,
            tags=["sprint", "success"]
        )
        
        self.assertEqual(feedback.agent_id, "agent-1")
        self.assertEqual(feedback.category, FeedbackCategory.WENT_WELL)
        self.assertEqual(feedback.content, "Great sprint!")
        self.assertEqual(feedback.sentiment, Sentiment.POSITIVE)
        self.assertEqual(feedback.tags, ["sprint", "success"])
    
    def test_feedback_to_dict(self):
        """Test converting feedback to dictionary"""
        feedback = FeedbackItem(
            agent_id="agent-1",
            category=FeedbackCategory.IDEAS,
            content="Automate testing"
        )
        
        data = feedback.to_dict()
        self.assertIn('agent_id', data)
        self.assertIn('category', data)
        self.assertIn('content', data)
        self.assertIn('timestamp', data)


class TestActionItem(unittest.TestCase):
    """Test ActionItem class"""
    
    def test_action_item_creation(self):
        """Test creating action item"""
        due_date = datetime.now() + timedelta(days=7)
        action = ActionItem(
            id="AI-001",
            title="Improve testing",
            description="Add more unit tests",
            assigned_to="agent-2",
            priority=ActionItemPriority.HIGH,
            due_date=due_date
        )
        
        self.assertEqual(action.id, "AI-001")
        self.assertEqual(action.title, "Improve testing")
        self.assertEqual(action.assigned_to, "agent-2")
        self.assertEqual(action.priority, ActionItemPriority.HIGH)
        self.assertEqual(action.status, ActionItemStatus.PENDING)
    
    def test_update_status(self):
        """Test updating action item status"""
        action = ActionItem(
            id="AI-001",
            title="Test action",
            description="Test description"
        )
        
        # Update to in progress
        action.update_status(ActionItemStatus.IN_PROGRESS)
        self.assertEqual(action.status, ActionItemStatus.IN_PROGRESS)
        self.assertIsNone(action.completed_at)
        
        # Update to completed
        action.update_status(ActionItemStatus.COMPLETED)
        self.assertEqual(action.status, ActionItemStatus.COMPLETED)
        self.assertIsNotNone(action.completed_at)
    
    def test_action_to_dict(self):
        """Test converting action item to dictionary"""
        action = ActionItem(
            id="AI-001",
            title="Test action",
            description="Test description",
            priority=ActionItemPriority.MEDIUM
        )
        
        data = action.to_dict()
        self.assertEqual(data['id'], "AI-001")
        self.assertEqual(data['title'], "Test action")
        self.assertEqual(data['priority'], "medium")
        self.assertEqual(data['status'], "pending")


class TestSentimentAnalyzer(unittest.TestCase):
    """Test SentimentAnalyzer class"""
    
    def setUp(self):
        self.analyzer = SentimentAnalyzer()
    
    def test_positive_sentiment(self):
        """Test detecting positive sentiment"""
        text = "This was great! Excellent work by the team."
        sentiment = self.analyzer.analyze(text)
        self.assertIn(sentiment, [Sentiment.POSITIVE, Sentiment.VERY_POSITIVE])
    
    def test_negative_sentiment(self):
        """Test detecting negative sentiment"""
        text = "This was terrible. Many problems and issues."
        sentiment = self.analyzer.analyze(text)
        self.assertIn(sentiment, [Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE])
    
    def test_neutral_sentiment(self):
        """Test detecting neutral sentiment"""
        text = "The sprint was okay. Some things worked, some didn't."
        sentiment = self.analyzer.analyze(text)
        self.assertEqual(sentiment, Sentiment.NEUTRAL)
    
    def test_intensifiers(self):
        """Test sentiment with intensifiers"""
        text = "This was very very good!"
        sentiment = self.analyzer.analyze(text)
        self.assertIn(sentiment, [Sentiment.POSITIVE, Sentiment.VERY_POSITIVE])


class TestPatternDetector(unittest.TestCase):
    """Test PatternDetector class"""
    
    def setUp(self):
        self.detector = PatternDetector()
    
    def test_detect_recurring_issues(self):
        """Test detecting recurring issue patterns"""
        feedback = [
            FeedbackItem("agent-1", FeedbackCategory.WENT_WRONG, "Testing was slow"),
            FeedbackItem("agent-2", FeedbackCategory.WENT_WRONG, "Testing issues again"),
            FeedbackItem("agent-3", FeedbackCategory.WENT_WRONG, "Problems with testing")
        ]
        
        patterns = self.detector.detect_patterns(feedback, [])
        
        # Should detect testing pattern
        self.assertTrue(any('testing' in p.pattern_type.lower() for p in patterns))
    
    def test_detect_sentiment_pattern(self):
        """Test detecting sentiment patterns"""
        feedback = [
            FeedbackItem("agent-1", FeedbackCategory.WENT_WRONG, "Bad sprint", sentiment=Sentiment.NEGATIVE),
            FeedbackItem("agent-2", FeedbackCategory.WENT_WRONG, "Terrible experience", sentiment=Sentiment.VERY_NEGATIVE),
            FeedbackItem("agent-3", FeedbackCategory.WENT_WRONG, "Not good", sentiment=Sentiment.NEGATIVE),
            FeedbackItem("agent-4", FeedbackCategory.WENT_WELL, "Some good parts", sentiment=Sentiment.POSITIVE)
        ]
        
        patterns = self.detector.detect_patterns(feedback, [])
        
        # Should detect morale pattern
        morale_patterns = [p for p in patterns if 'morale' in p.pattern_type.lower()]
        self.assertTrue(len(morale_patterns) > 0)


class TestRetrospectiveAnalyzer(unittest.TestCase):
    """Test RetrospectiveAnalyzer class"""
    
    def setUp(self):
        self.analyzer = RetrospectiveAnalyzer()
    
    def test_collect_feedback(self):
        """Test collecting feedback"""
        feedback = self.analyzer.collect_feedback(
            agent_id="agent-1",
            category=FeedbackCategory.WENT_WELL,
            content="Great collaboration",
            tags=["teamwork"]
        )
        
        self.assertEqual(feedback.agent_id, "agent-1")
        self.assertEqual(feedback.category, FeedbackCategory.WENT_WELL)
        self.assertIsNotNone(feedback.sentiment)
        self.assertIn(feedback, self.analyzer.feedback_history)
    
    def test_create_action_item(self):
        """Test creating action items"""
        action = self.analyzer.create_action_item(
            title="Improve testing",
            description="Add more automated tests",
            assigned_to="agent-2",
            priority=ActionItemPriority.HIGH
        )
        
        self.assertIn(action.id, self.analyzer.action_items)
        self.assertEqual(action.title, "Improve testing")
        self.assertEqual(action.priority, ActionItemPriority.HIGH)
    
    def test_update_action_item_status(self):
        """Test updating action item status"""
        action = self.analyzer.create_action_item(
            title="Test action",
            description="Test description"
        )
        
        # Update status
        success = self.analyzer.update_action_item_status(
            action.id, 
            ActionItemStatus.COMPLETED
        )
        
        self.assertTrue(success)
        self.assertEqual(
            self.analyzer.action_items[action.id].status,
            ActionItemStatus.COMPLETED
        )
        
        # Try updating non-existent item
        success = self.analyzer.update_action_item_status(
            "INVALID-ID",
            ActionItemStatus.COMPLETED
        )
        self.assertFalse(success)
    
    def test_get_pending_action_items(self):
        """Test getting pending action items"""
        # Create action items with different statuses
        action1 = self.analyzer.create_action_item(
            title="Pending task",
            description="Description",
            assigned_to="agent-1"
        )
        
        action2 = self.analyzer.create_action_item(
            title="In progress task",
            description="Description",
            assigned_to="agent-1"
        )
        self.analyzer.update_action_item_status(action2.id, ActionItemStatus.IN_PROGRESS)
        
        action3 = self.analyzer.create_action_item(
            title="Completed task",
            description="Description",
            assigned_to="agent-1"
        )
        self.analyzer.update_action_item_status(action3.id, ActionItemStatus.COMPLETED)
        
        # Get pending items
        pending = self.analyzer.get_pending_action_items()
        self.assertEqual(len(pending), 2)  # Only pending and in_progress
        
        # Get pending for specific agent
        agent_pending = self.analyzer.get_pending_action_items("agent-1")
        self.assertEqual(len(agent_pending), 2)
        
        # Get pending for non-existent agent
        no_pending = self.analyzer.get_pending_action_items("agent-999")
        self.assertEqual(len(no_pending), 0)
    
    def test_analyze_retrospective(self):
        """Test analyzing retrospective"""
        # Collect feedback
        feedback_items = []
        for i in range(3):
            feedback = self.analyzer.collect_feedback(
                agent_id=f"agent-{i}",
                category=FeedbackCategory.WENT_WELL if i % 2 == 0 else FeedbackCategory.WENT_WRONG,
                content="Test feedback"
            )
            feedback_items.append(feedback)
        
        # Create action items
        self.analyzer.create_action_item(
            title="Test action",
            description="Description"
        )
        
        # Analyze
        report = self.analyzer.analyze_retrospective(
            sprint_id="sprint-001",
            team_id="team-alpha",
            feedback_items=feedback_items,
            participants=["agent-0", "agent-1", "agent-2"],
            total_team_size=5
        )
        
        self.assertEqual(report.sprint_id, "sprint-001")
        self.assertEqual(report.team_id, "team-alpha")
        self.assertEqual(len(report.feedback_items), 3)
        self.assertEqual(len(report.participants), 3)
        self.assertEqual(report.participation_rate, 0.6)
        self.assertIsNotNone(report.team_sentiment)
    
    def test_report_to_markdown(self):
        """Test generating markdown report"""
        # Create minimal report
        feedback = [
            FeedbackItem("agent-1", FeedbackCategory.WENT_WELL, "Good work")
        ]
        
        report = self.analyzer.analyze_retrospective(
            sprint_id="sprint-001",
            team_id="team-alpha",
            feedback_items=feedback,
            participants=["agent-1"],
            total_team_size=1
        )
        
        markdown = report.to_markdown()
        
        self.assertIn("Sprint Retrospective Report", markdown)
        self.assertIn("sprint-001", markdown)
        self.assertIn("team-alpha", markdown)
        self.assertIn("What Went Well", markdown)
    
    def test_export_import_json(self):
        """Test exporting and importing JSON"""
        # Create report
        feedback = [
            FeedbackItem("agent-1", FeedbackCategory.IDEAS, "Test idea")
        ]
        
        report = self.analyzer.analyze_retrospective(
            sprint_id="sprint-001",
            team_id="team-alpha",
            feedback_items=feedback,
            participants=["agent-1"],
            total_team_size=1
        )
        
        # Export to JSON
        json_str = self.analyzer.export_to_json(report)
        
        # Verify it's valid JSON
        data = json.loads(json_str)
        self.assertEqual(data['sprint_id'], "sprint-001")
        
        # Import from JSON
        loaded_report = self.analyzer.load_from_json(json_str)
        
        self.assertEqual(loaded_report.sprint_id, report.sprint_id)
        self.assertEqual(loaded_report.team_id, report.team_id)
        self.assertEqual(len(loaded_report.feedback_items), len(report.feedback_items))
    
    def test_historical_trends(self):
        """Test getting historical trends"""
        # Create multiple retrospectives
        for i in range(3):
            feedback = [
                FeedbackItem(f"agent-{j}", FeedbackCategory.WENT_WELL, "Good")
                for j in range(3)
            ]
            
            report = self.analyzer.analyze_retrospective(
                sprint_id=f"sprint-{i:03d}",
                team_id="team-alpha",
                feedback_items=feedback,
                participants=[f"agent-{j}" for j in range(3)],
                total_team_size=5
            )
        
        # Get trends
        trends = self.analyzer.get_historical_trends("team-alpha", lookback_sprints=3)
        
        self.assertIn('sentiment_trend', trends)
        self.assertIn('participation_trend', trends)
        self.assertIn('completion_trend', trends)
        self.assertEqual(len(trends['sentiment_trend']), 3)
    
    def test_extract_themes(self):
        """Test extracting themes from feedback"""
        feedback_items = [
            FeedbackItem("agent-1", FeedbackCategory.WENT_WRONG, "Communication issues in meetings"),
            FeedbackItem("agent-2", FeedbackCategory.WENT_WRONG, "Poor communication between teams"),
            FeedbackItem("agent-3", FeedbackCategory.IDEAS, "Improve testing process"),
            FeedbackItem("agent-4", FeedbackCategory.IDEAS, "Better automation tools")
        ]
        
        themes = self.analyzer._extract_themes(feedback_items)
        
        # Should identify communication and testing as themes
        theme_names = [theme[0] for theme in themes]
        self.assertIn('communication', theme_names)
    
    def test_generate_recommendations(self):
        """Test generating recommendations"""
        # Create feedback with negative sentiment
        feedback_items = [
            FeedbackItem("agent-1", FeedbackCategory.WENT_WRONG, "Bad sprint", sentiment=Sentiment.NEGATIVE),
            FeedbackItem("agent-2", FeedbackCategory.WENT_WRONG, "Many issues", sentiment=Sentiment.NEGATIVE)
        ]
        
        recommendations = self.analyzer._generate_recommendations(
            feedback_items=feedback_items,
            patterns=[],
            team_sentiment=Sentiment.NEGATIVE,
            completion_rate=0.3
        )
        
        # Should recommend addressing morale and completion rate
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(any('morale' in r.lower() for r in recommendations))
        self.assertTrue(any('completion rate' in r.lower() for r in recommendations))


class TestImprovementPattern(unittest.TestCase):
    """Test ImprovementPattern class"""
    
    def test_pattern_creation(self):
        """Test creating improvement pattern"""
        pattern = ImprovementPattern(
            pattern_type="Recurring Testing Issues",
            description="Testing problems occur frequently",
            occurrences=5,
            first_seen=datetime.now() - timedelta(days=30),
            last_seen=datetime.now(),
            affected_areas=["testing", "quality"],
            suggested_actions=["Improve test automation"],
            confidence=0.85
        )
        
        self.assertEqual(pattern.pattern_type, "Recurring Testing Issues")
        self.assertEqual(pattern.occurrences, 5)
        self.assertEqual(pattern.confidence, 0.85)
    
    def test_pattern_to_dict(self):
        """Test converting pattern to dictionary"""
        pattern = ImprovementPattern(
            pattern_type="Test Pattern",
            description="Test description",
            occurrences=3,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            affected_areas=["area1"],
            suggested_actions=["action1"],
            confidence=0.75
        )
        
        data = pattern.to_dict()
        self.assertEqual(data['pattern_type'], "Test Pattern")
        self.assertEqual(data['occurrences'], 3)
        self.assertEqual(data['confidence'], 0.75)


class TestRetrospectiveReport(unittest.TestCase):
    """Test RetrospectiveReport class"""
    
    def test_report_creation(self):
        """Test creating retrospective report"""
        feedback = [FeedbackItem("agent-1", FeedbackCategory.WENT_WELL, "Good")]
        actions = [ActionItem("AI-001", "Test", "Description")]
        
        report = RetrospectiveReport(
            sprint_id="sprint-001",
            team_id="team-alpha",
            date=datetime.now(),
            participants=["agent-1"],
            feedback_items=feedback,
            action_items=actions,
            team_sentiment=Sentiment.POSITIVE,
            sentiment_scores={"positive": 1.0},
            improvement_patterns=[],
            key_themes=[("testing", 3)],
            participation_rate=0.8,
            action_item_completion_rate=0.5,
            recommendations=["Test recommendation"]
        )
        
        self.assertEqual(report.sprint_id, "sprint-001")
        self.assertEqual(len(report.feedback_items), 1)
        self.assertEqual(len(report.action_items), 1)
        self.assertEqual(report.participation_rate, 0.8)
    
    def test_report_to_dict(self):
        """Test converting report to dictionary"""
        report = RetrospectiveReport(
            sprint_id="sprint-001",
            team_id="team-alpha",
            date=datetime.now(),
            participants=["agent-1"],
            feedback_items=[],
            action_items=[],
            team_sentiment=Sentiment.NEUTRAL,
            sentiment_scores={},
            improvement_patterns=[],
            key_themes=[],
            participation_rate=1.0,
            action_item_completion_rate=0.0,
            recommendations=[]
        )
        
        data = report.to_dict()
        self.assertEqual(data['sprint_id'], "sprint-001")
        self.assertEqual(data['team_id'], "team-alpha")
        self.assertEqual(data['participation_rate'], 1.0)


if __name__ == '__main__':
    unittest.main()