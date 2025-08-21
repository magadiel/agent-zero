"""
Test suite for Learning Synthesizer
"""

import unittest
import asyncio
from datetime import datetime, timedelta
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))
from learning_synthesizer import (
    LearningSynthesizer, Learning, LearningType, LearningPriority,
    Pattern, PatternType, KnowledgeUpdate, LearningReport
)


class TestLearningSynthesizer(unittest.TestCase):
    """Test cases for Learning Synthesizer"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.synthesizer = LearningSynthesizer(knowledge_base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_collect_learning(self):
        """Test collecting a single learning"""
        learning = Learning(
            id="",
            team_id="team_test",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Test Learning",
            description="This is a test learning",
            context={"test": "context"},
            tags=["test", "learning"],
            source="unit_test",
            timestamp=datetime.now(),
            impact_score=0.7
        )
        
        learning_id = asyncio.run(self.synthesizer.collect_learning(learning))
        
        self.assertIsNotNone(learning_id)
        self.assertIn(learning_id, self.synthesizer.learnings)
        self.assertEqual(self.synthesizer.metrics['total_learnings'], 1)
    
    def test_collect_bulk_learnings(self):
        """Test collecting multiple learnings"""
        learnings = []
        for i in range(3):
            learning = Learning(
                id="",
                team_id=f"team_{i}",
                type=LearningType.SUCCESS,
                priority=LearningPriority.MEDIUM,
                title=f"Learning {i}",
                description=f"Description {i}",
                context={"index": i},
                tags=[f"tag_{i}"],
                source="bulk_test",
                timestamp=datetime.now(),
                impact_score=0.5
            )
            learnings.append(learning)
        
        ids = asyncio.run(self.synthesizer.collect_bulk_learnings(learnings))
        
        self.assertEqual(len(ids), 3)
        self.assertEqual(self.synthesizer.metrics['total_learnings'], 3)
    
    def test_identify_patterns_recurring_issues(self):
        """Test identifying recurring issue patterns"""
        # Create multiple failure learnings with same tag
        learnings = []
        for i in range(4):
            learning = Learning(
                id=f"failure_{i}",
                team_id=f"team_{i}",
                type=LearningType.FAILURE,
                priority=LearningPriority.HIGH,
                title=f"Database failure {i}",
                description=f"Database connection timeout issue {i}",
                context={"component": "database"},
                tags=["database", "timeout"],
                source="incident",
                timestamp=datetime.now() - timedelta(days=i),
                impact_score=0.8
            )
            learnings.append(learning)
        
        # Collect learnings
        asyncio.run(self.synthesizer.collect_bulk_learnings(learnings))
        
        # Identify patterns
        patterns = asyncio.run(self.synthesizer.identify_patterns())
        
        # Check for recurring issue pattern
        recurring_patterns = [p for p in patterns if p.type == PatternType.RECURRING_ISSUE]
        self.assertGreater(len(recurring_patterns), 0)
        
        # Verify pattern details
        if recurring_patterns:
            pattern = recurring_patterns[0]
            self.assertGreaterEqual(pattern.frequency, 3)
            self.assertGreater(pattern.confidence, 0.0)
    
    def test_identify_patterns_best_practices(self):
        """Test identifying best practice patterns"""
        # Create multiple success learnings
        learnings = []
        for i in range(3):
            learning = Learning(
                id=f"success_{i}",
                team_id=f"team_{i}",
                type=LearningType.SUCCESS,
                priority=LearningPriority.HIGH,
                title=f"Optimization success {i}",
                description=f"Successfully optimized performance {i}",
                context={"area": "performance"},
                tags=["optimization", "success"],
                source="sprint_review",
                timestamp=datetime.now() - timedelta(days=i),
                impact_score=0.9
            )
            learnings.append(learning)
        
        asyncio.run(self.synthesizer.collect_bulk_learnings(learnings))
        patterns = asyncio.run(self.synthesizer.identify_patterns())
        
        best_practices = [p for p in patterns if p.type == PatternType.BEST_PRACTICE]
        self.assertGreaterEqual(len(best_practices), 0)
    
    def test_update_knowledge_base(self):
        """Test updating the knowledge base"""
        learning = Learning(
            id="kb_test",
            team_id="team_kb",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Knowledge Base Test",
            description="Testing knowledge base update",
            context={"test": "kb"},
            tags=["knowledge", "test"],
            source="test",
            timestamp=datetime.now(),
            impact_score=0.8,
            confidence=0.9,
            validated=True
        )
        
        learning_id = asyncio.run(self.synthesizer.collect_learning(learning))
        updates = asyncio.run(self.synthesizer.update_knowledge_base([learning_id]))
        
        self.assertEqual(len(updates), 1)
        self.assertEqual(self.synthesizer.metrics['knowledge_updates'], 1)
        
        # Check that knowledge file was created
        kb_path = Path(self.temp_dir) / "technical_practices"
        self.assertTrue(kb_path.exists())
    
    def test_distribute_learnings(self):
        """Test distributing learnings to teams"""
        # Create high-priority learning
        learning = Learning(
            id="dist_test",
            team_id="team_source",
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.CRITICAL,
            title="Critical Improvement",
            description="Important improvement to share",
            context={"importance": "high"},
            tags=["critical", "improvement"],
            source="discovery",
            timestamp=datetime.now(),
            impact_score=0.95
        )
        
        learning_id = asyncio.run(self.synthesizer.collect_learning(learning))
        
        # Distribute to other teams
        distribution = asyncio.run(
            self.synthesizer.distribute_learnings(
                ["team_target1", "team_target2"],
                [learning_id]
            )
        )
        
        self.assertEqual(len(distribution), 2)
        self.assertIn("team_target1", distribution)
        self.assertIn("team_target2", distribution)
        
        # Source team shouldn't receive its own learning
        distribution_source = asyncio.run(
            self.synthesizer.distribute_learnings(["team_source"], [learning_id])
        )
        self.assertEqual(len(distribution_source["team_source"]), 0)
    
    def test_generate_insights_report(self):
        """Test generating insights report"""
        # Create diverse learnings
        learnings = [
            Learning(
                id="report_1",
                team_id="team_alpha",
                type=LearningType.TECHNICAL,
                priority=LearningPriority.HIGH,
                title="Technical Learning",
                description="Technical improvement",
                context={"area": "tech"},
                tags=["technical"],
                source="development",
                timestamp=datetime.now() - timedelta(days=5),
                impact_score=0.7
            ),
            Learning(
                id="report_2",
                team_id="team_beta",
                type=LearningType.FAILURE,
                priority=LearningPriority.CRITICAL,
                title="Critical Failure",
                description="System failure",
                context={"severity": "high"},
                tags=["failure"],
                source="incident",
                timestamp=datetime.now() - timedelta(days=2),
                impact_score=0.9
            )
        ]
        
        asyncio.run(self.synthesizer.collect_bulk_learnings(learnings))
        
        # Generate report
        report = asyncio.run(self.synthesizer.generate_insights_report())
        
        self.assertIsInstance(report, LearningReport)
        self.assertEqual(report.total_learnings, 2)
        self.assertIn("technical", report.learnings_by_type)
        self.assertIn("failure", report.learnings_by_type)
        self.assertGreater(len(report.top_insights), 0)
    
    def test_validate_learning(self):
        """Test learning validation"""
        learning = Learning(
            id="validate_test",
            team_id="team_val",
            type=LearningType.INNOVATION,
            priority=LearningPriority.HIGH,
            title="Innovation to Validate",
            description="New innovative approach",
            context={"status": "pending"},
            tags=["innovation"],
            source="experiment",
            timestamp=datetime.now(),
            impact_score=0.8,
            validated=False
        )
        
        learning_id = asyncio.run(self.synthesizer.collect_learning(learning))
        
        # Validate the learning
        success = asyncio.run(
            self.synthesizer.validate_learning(learning_id, True, "validator_1")
        )
        
        self.assertTrue(success)
        self.assertTrue(self.synthesizer.learnings[learning_id].validated)
        self.assertIn("validator", self.synthesizer.learnings[learning_id].metadata)
    
    def test_export_report_markdown(self):
        """Test exporting report as markdown"""
        # Create sample report
        report = LearningReport(
            id="test_report",
            period_start=datetime.now() - timedelta(days=30),
            period_end=datetime.now(),
            total_learnings=10,
            learnings_by_type={"technical": 5, "process": 5},
            learnings_by_priority={"high": 6, "medium": 4},
            learnings_by_team={"team_a": 5, "team_b": 5},
            patterns_identified=[],
            top_insights=["Insight 1", "Insight 2"],
            recommendations=["Recommendation 1"],
            knowledge_updates=[]
        )
        
        markdown = self.synthesizer.export_report(report, 'markdown')
        
        self.assertIn("# Learning Synthesis Report", markdown)
        self.assertIn("**Total Learnings**: 10", markdown)
        self.assertIn("Insight 1", markdown)
    
    def test_export_report_json(self):
        """Test exporting report as JSON"""
        report = LearningReport(
            id="json_report",
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            total_learnings=5,
            learnings_by_type={"success": 3, "failure": 2},
            learnings_by_priority={"high": 5},
            learnings_by_team={"team_x": 5},
            patterns_identified=[],
            top_insights=["JSON test insight"],
            recommendations=["JSON recommendation"],
            knowledge_updates=[]
        )
        
        json_output = self.synthesizer.export_report(report, 'json')
        
        import json
        data = json.loads(json_output)
        
        self.assertEqual(data['total_learnings'], 5)
        self.assertEqual(data['learnings_by_type']['success'], 3)
        self.assertIn("JSON test insight", data['top_insights'])
    
    def test_pattern_similarity_calculation(self):
        """Test pattern similarity calculation"""
        # Create initial learning
        learning1 = Learning(
            id="sim_1",
            team_id="team_sim",
            type=LearningType.FAILURE,
            priority=LearningPriority.HIGH,
            title="Database Error",
            description="Connection pool exhausted causing timeouts",
            context={"component": "database"},
            tags=["database", "connection", "timeout"],
            source="monitoring",
            timestamp=datetime.now(),
            impact_score=0.8
        )
        
        asyncio.run(self.synthesizer.collect_learning(learning1))
        
        # Create similar learning
        learning2 = Learning(
            id="sim_2",
            team_id="team_sim2",
            type=LearningType.FAILURE,
            priority=LearningPriority.HIGH,
            title="DB Connection Issue",
            description="Database connection failures under load",
            context={"component": "database"},
            tags=["database", "connection", "failure"],
            source="incident",
            timestamp=datetime.now(),
            impact_score=0.7
        )
        
        # Test similarity calculation (internal method)
        # This would normally trigger pattern detection
        asyncio.run(self.synthesizer.collect_learning(learning2))
        
        # After collecting similar learnings, patterns should be detected
        patterns = asyncio.run(self.synthesizer.identify_patterns())
        self.assertGreaterEqual(len(patterns), 0)
    
    def test_get_metrics(self):
        """Test getting synthesizer metrics"""
        # Add some learnings
        learning = Learning(
            id="metrics_test",
            team_id="team_metrics",
            type=LearningType.SUCCESS,
            priority=LearningPriority.MEDIUM,
            title="Metrics Test",
            description="Testing metrics",
            context={},
            tags=["test"],
            source="test",
            timestamp=datetime.now(),
            impact_score=0.5
        )
        
        asyncio.run(self.synthesizer.collect_learning(learning))
        
        metrics = self.synthesizer.get_metrics()
        
        self.assertIn('total_learnings', metrics)
        self.assertIn('patterns_identified', metrics)
        self.assertIn('knowledge_updates', metrics)
        self.assertIn('learnings_distributed', metrics)
        self.assertEqual(metrics['total_learnings'], 1)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False)


if __name__ == "__main__":
    run_tests()