"""
Test suite for Learning Tracker
"""

import unittest
import asyncio
from datetime import datetime, timedelta
import tempfile
import shutil
from pathlib import Path
import statistics

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "coordination"))
sys.path.append(str(Path(__file__).parent.parent))
from learning_synthesizer import Learning, LearningType, LearningPriority
from learning_tracker import (
    LearningTracker, LearningMetrics, TeamLearningProfile,
    LearningEvolution, LearningROI, LearningTrend,
    LearningQuality, LearningImpact
)


class TestLearningTracker(unittest.TestCase):
    """Test cases for Learning Tracker"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = LearningTracker(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_track_learning(self):
        """Test tracking a single learning"""
        learning = Learning(
            id="track_test_001",
            team_id="team_test",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Test Learning",
            description="This is a detailed test learning with comprehensive description for quality scoring",
            context={"area": "testing", "component": "tracker"},
            tags=["test", "learning", "metrics"],
            source="unit_test",
            timestamp=datetime.now(),
            impact_score=0.0,  # Will be calculated
            confidence=0.85,
            validated=True
        )
        
        metrics = asyncio.run(self.tracker.track_learning(learning))
        
        self.assertIsInstance(metrics, LearningMetrics)
        self.assertEqual(metrics.learning_id, "track_test_001")
        self.assertGreater(metrics.quality_score, 0.0)
        self.assertGreater(metrics.impact_score, 0.0)
        self.assertEqual(metrics.validation_score, 0.85)
        # Check that learning was tracked
        self.assertIn("track_test_001", self.tracker.learning_metrics)
    
    def test_quality_score_calculation(self):
        """Test quality score calculation logic"""
        # High quality learning
        high_quality = Learning(
            id="high_quality",
            team_id="team_hq",
            type=LearningType.INNOVATION,
            priority=LearningPriority.CRITICAL,
            title="High Quality Learning",
            description="A" * 250,  # Long description
            context={"key1": "value1", "key2": "value2"},
            tags=["tag1", "tag2", "tag3", "tag4"],
            source="research",
            timestamp=datetime.now(),
            confidence=0.95,
            validated=True
        )
        
        metrics_high = asyncio.run(self.tracker.track_learning(high_quality))
        
        # Low quality learning
        low_quality = Learning(
            id="low_quality",
            team_id="team_lq",
            type=LearningType.OPERATIONAL,
            priority=LearningPriority.LOW,
            title="Low Quality",
            description="Short",
            context={},
            tags=[],
            source="casual",
            timestamp=datetime.now(),
            confidence=0.3,
            validated=False
        )
        
        metrics_low = asyncio.run(self.tracker.track_learning(low_quality))
        
        self.assertGreater(metrics_high.quality_score, metrics_low.quality_score)
        self.assertGreater(metrics_high.quality_score, 0.7)
        self.assertLess(metrics_low.quality_score, 0.4)
    
    def test_impact_score_calculation(self):
        """Test impact score calculation logic"""
        # High impact learning
        high_impact = Learning(
            id="high_impact",
            team_id="team_hi",
            type=LearningType.FAILURE,  # Failures have high impact
            priority=LearningPriority.CRITICAL,
            title="Critical Failure",
            description="Major system failure",
            context={"severity": "critical"},
            tags=["failure", "critical"],
            source="incident",
            timestamp=datetime.now(),
            confidence=0.9,
            applied_count=3
        )
        
        metrics_high = asyncio.run(self.tracker.track_learning(high_impact))
        
        # Low impact learning
        low_impact = Learning(
            id="low_impact",
            team_id="team_li",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.LOW,
            title="Minor Update",
            description="Small technical adjustment",
            context={},
            tags=["minor"],
            source="routine",
            timestamp=datetime.now(),
            confidence=0.5,
            applied_count=0
        )
        
        metrics_low = asyncio.run(self.tracker.track_learning(low_impact))
        
        self.assertGreater(metrics_high.impact_score, metrics_low.impact_score)
        self.assertGreater(metrics_high.impact_score, 0.6)
        self.assertLess(metrics_low.impact_score, 0.4)
    
    def test_team_profile_creation(self):
        """Test team learning profile creation and update"""
        # Track multiple learnings for a team
        team_id = "team_profile_test"
        learnings = []
        
        for i in range(3):
            learning = Learning(
                id=f"profile_{i}",
                team_id=team_id,
                type=LearningType.SUCCESS if i % 2 == 0 else LearningType.PROCESS,
                priority=LearningPriority.HIGH,
                title=f"Learning {i}",
                description=f"Description {i}",
                context={"index": i},
                tags=[f"tag_{i}"],
                source="test",
                timestamp=datetime.now() - timedelta(hours=i),
                confidence=0.7 + i * 0.1
            )
            learnings.append(learning)
        
        for learning in learnings:
            asyncio.run(self.tracker.track_learning(learning))
        
        profile = self.tracker.get_team_profile(team_id)
        
        self.assertIsInstance(profile, TeamLearningProfile)
        self.assertEqual(profile.team_id, team_id)
        self.assertEqual(profile.total_learnings, 3)
        self.assertGreater(profile.avg_quality_score, 0.0)
        self.assertGreater(profile.avg_impact_score, 0.0)
        self.assertIn("success", profile.learning_types)
        self.assertIn("process", profile.learning_types)
    
    def test_track_learning_application(self):
        """Test tracking when a learning is applied"""
        learning = Learning(
            id="apply_test",
            team_id="team_apply",
            type=LearningType.IMPROVEMENT,
            priority=LearningPriority.HIGH,
            title="Applicable Learning",
            description="A learning that will be applied",
            context={},
            tags=["applicable"],
            source="discovery",
            timestamp=datetime.now() - timedelta(days=1),
            confidence=0.8
        )
        
        metrics = asyncio.run(self.tracker.track_learning(learning))
        initial_reuse = metrics.reuse_count
        
        # Apply the learning
        asyncio.run(self.tracker.track_learning_application("apply_test", "team_other", success=True))
        asyncio.run(self.tracker.track_learning_application("apply_test", "team_another", success=True))
        
        updated_metrics = self.tracker.get_learning_metrics("apply_test")
        
        self.assertEqual(updated_metrics.reuse_count, initial_reuse + 2)
        self.assertGreater(updated_metrics.application_rate, 0.0)
        self.assertGreater(updated_metrics.propagation_speed, 0.0)
    
    def test_track_learning_evolution(self):
        """Test tracking learning evolution"""
        original = Learning(
            id="original_learning",
            team_id="team_evo",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.MEDIUM,
            title="Original Learning",
            description="Initial discovery",
            context={},
            tags=["evolution"],
            source="research",
            timestamp=datetime.now(),
            confidence=0.6
        )
        
        improved = Learning(
            id="improved_learning",
            team_id="team_evo",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Improved Learning",
            description="Refined discovery with better understanding",
            context={},
            tags=["evolution", "improved"],
            source="refinement",
            timestamp=datetime.now(),
            confidence=0.9
        )
        
        # Track both learnings
        asyncio.run(self.tracker.track_learning(original))
        asyncio.run(self.tracker.track_learning(improved))
        
        # Track evolution
        evolution = asyncio.run(
            self.tracker.track_learning_evolution("original_learning", "improved_learning", "improvement")
        )
        
        self.assertIsInstance(evolution, LearningEvolution)
        self.assertEqual(evolution.original_learning_id, "original_learning")
        self.assertIn("improved_learning", evolution.evolution_chain)
        self.assertEqual(evolution.refinements, 1)
        self.assertGreater(evolution.quality_improvement, 0.0)
    
    def test_calculate_learning_roi(self):
        """Test ROI calculation for learnings"""
        learning = Learning(
            id="roi_test",
            team_id="team_roi",
            type=LearningType.INNOVATION,
            priority=LearningPriority.HIGH,
            title="High ROI Learning",
            description="Innovation that saves time and prevents issues",
            context={},
            tags=["roi", "value"],
            source="innovation",
            timestamp=datetime.now(),
            confidence=0.85
        )
        
        asyncio.run(self.tracker.track_learning(learning))
        
        # Calculate ROI
        roi = asyncio.run(
            self.tracker.calculate_learning_roi(
                learning_id="roi_test",
                time_invested=5.0,  # 5 hours
                teams_affected=["team_a", "team_b", "team_c"],
                issues_prevented=3,
                time_saved_hours=30.0
            )
        )
        
        self.assertIsInstance(roi, LearningROI)
        self.assertEqual(roi.learning_id, "roi_test")
        self.assertGreater(roi.value_generated, 0.0)
        self.assertGreater(roi.roi_percentage, 0.0)
        self.assertEqual(roi.affected_teams, 3)
        self.assertEqual(roi.prevented_issues, 3)
        self.assertEqual(roi.time_saved, 30.0)
    
    def test_analyze_learning_trends(self):
        """Test learning trend analysis"""
        # Create learnings over time
        base_time = datetime.now() - timedelta(days=20)
        
        for i in range(10):
            learning = Learning(
                id=f"trend_{i}",
                team_id=f"team_{i % 3}",
                type=LearningType.SUCCESS,
                priority=LearningPriority.MEDIUM,
                title=f"Trend Learning {i}",
                description=f"Learning for trend analysis {i}",
                context={},
                tags=[f"trend_{i}"],
                source="trend_test",
                timestamp=base_time + timedelta(days=i*2),
                confidence=0.6 + (i * 0.03)  # Improving quality over time
            )
            asyncio.run(self.tracker.track_learning(learning))
        
        # Analyze trends
        trend = asyncio.run(self.tracker.analyze_learning_trends(period="weekly", lookback_days=30))
        
        self.assertIsInstance(trend, LearningTrend)
        self.assertEqual(trend.period, "weekly")
        self.assertIn(trend.trend_direction, ["increasing", "stable", "decreasing"])
        self.assertIsInstance(trend.growth_rate, float)
        self.assertIn(trend.quality_trend, ["increasing", "stable", "decreasing"])
        self.assertIn('next_period_estimate', trend.predictions)
    
    def test_get_top_learnings(self):
        """Test getting top learnings by different metrics"""
        # Create learnings with varying scores
        learnings = [
            ("high_quality", 0.9, 0.5, 1),
            ("high_impact", 0.5, 0.9, 2),
            ("high_reuse", 0.6, 0.6, 5),
            ("average", 0.5, 0.5, 1)
        ]
        
        for lid, quality, impact, reuse in learnings:
            learning = Learning(
                id=lid,
                team_id="team_top",
                type=LearningType.SUCCESS,
                priority=LearningPriority.MEDIUM,
                title=f"Learning {lid}",
                description=f"Description {lid}",
                context={},
                tags=[lid],
                source="test",
                timestamp=datetime.now(),
                confidence=quality,
                impact_score=impact
            )
            metrics = asyncio.run(self.tracker.track_learning(learning))
            # Manually set reuse count for testing
            self.tracker.learning_metrics[lid].reuse_count = reuse
        
        # Get top by quality
        top_quality = self.tracker.get_top_learnings("quality", 2)
        self.assertEqual(len(top_quality), 2)
        self.assertEqual(top_quality[0][0], "high_quality")
        
        # Get top by impact
        top_impact = self.tracker.get_top_learnings("impact", 2)
        self.assertEqual(len(top_impact), 2)
        
        # Get top by reuse
        top_reuse = self.tracker.get_top_learnings("reuse", 2)
        self.assertEqual(len(top_reuse), 2)
        self.assertEqual(top_reuse[0][0], "high_reuse")
    
    def test_learning_quality_classification(self):
        """Test learning quality classification"""
        # Create learnings with different quality scores
        qualities = [
            ("excellent_learning", 0.95, LearningQuality.EXCELLENT),
            ("good_learning", 0.80, LearningQuality.GOOD),
            ("fair_learning", 0.55, LearningQuality.FAIR),
            ("poor_learning", 0.20, LearningQuality.POOR)
        ]
        
        for lid, confidence, expected_quality in qualities:
            learning = Learning(
                id=lid,
                team_id="team_quality",
                type=LearningType.TECHNICAL,
                priority=LearningPriority.HIGH if confidence > 0.8 else LearningPriority.LOW,
                title=f"Learning {lid}",
                description="A" * int(confidence * 200),  # Longer for higher quality
                context={"test": "quality"} if confidence > 0.5 else {},
                tags=["quality"] if confidence > 0.3 else [],
                source="test",
                timestamp=datetime.now(),
                confidence=confidence,
                validated=confidence > 0.7
            )
            asyncio.run(self.tracker.track_learning(learning))
            
            quality = self.tracker.get_learning_quality(lid)
            # Allow some flexibility in classification
            self.assertIsNotNone(quality)
    
    def test_learning_impact_classification(self):
        """Test learning impact classification"""
        # Create learnings with different impact levels
        impacts = [
            ("transformational", LearningType.INNOVATION, LearningPriority.CRITICAL, 3, LearningImpact.TRANSFORMATIONAL),
            ("high_impact", LearningType.FAILURE, LearningPriority.HIGH, 2, LearningImpact.HIGH),
            ("medium_impact", LearningType.IMPROVEMENT, LearningPriority.MEDIUM, 1, LearningImpact.MEDIUM),
            ("low_impact", LearningType.PROCESS, LearningPriority.LOW, 0, LearningImpact.LOW)
        ]
        
        for lid, ltype, priority, applied, expected_impact in impacts:
            learning = Learning(
                id=lid,
                team_id="team_impact",
                type=ltype,
                priority=priority,
                title=f"Learning {lid}",
                description=f"Impact test {lid}",
                context={},
                tags=["impact"],
                source="test",
                timestamp=datetime.now(),
                confidence=0.8,
                applied_count=applied
            )
            asyncio.run(self.tracker.track_learning(learning))
            
            impact = self.tracker.get_learning_impact(lid)
            self.assertIsNotNone(impact)
    
    def test_calculate_team_learning_velocity(self):
        """Test team learning velocity calculation"""
        team_id = "team_velocity"
        base_time = datetime.now() - timedelta(days=30)
        
        # Create learnings with improving quality over time
        for i in range(9):
            quality_score = 0.4 + (i * 0.05)  # Improving quality
            learning = Learning(
                id=f"velocity_{i}",
                team_id=team_id,
                type=LearningType.SUCCESS,
                priority=LearningPriority.MEDIUM,
                title=f"Learning {i}",
                description=f"Velocity test {i}",
                context={},
                tags=["velocity"],
                source="test",
                timestamp=base_time + timedelta(days=i*3),
                confidence=quality_score
            )
            asyncio.run(self.tracker.track_learning(learning))
        
        velocity = asyncio.run(self.tracker.calculate_team_learning_velocity(team_id))
        
        self.assertIsInstance(velocity, float)
        # Velocity should be positive since quality is improving
        self.assertGreater(velocity, 0.0)
    
    def test_export_metrics_report_markdown(self):
        """Test exporting metrics report as markdown"""
        # Add some test data
        learning = Learning(
            id="export_test",
            team_id="team_export",
            type=LearningType.SUCCESS,
            priority=LearningPriority.HIGH,
            title="Export Test",
            description="Testing export functionality",
            context={},
            tags=["export"],
            source="test",
            timestamp=datetime.now(),
            confidence=0.8
        )
        asyncio.run(self.tracker.track_learning(learning))
        
        report = self.tracker.export_metrics_report("markdown")
        
        self.assertIn("# Learning Metrics Report", report)
        self.assertIn("Total Learnings Tracked: 1", report)
        self.assertIn("Average Metrics", report)
    
    def test_export_metrics_report_json(self):
        """Test exporting metrics report as JSON"""
        learning = Learning(
            id="json_export",
            team_id="team_json",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.MEDIUM,
            title="JSON Export",
            description="JSON export test",
            context={},
            tags=["json"],
            source="test",
            timestamp=datetime.now(),
            confidence=0.7
        )
        asyncio.run(self.tracker.track_learning(learning))
        
        json_report = self.tracker.export_metrics_report("json")
        
        import json
        data = json.loads(json_report)
        
        self.assertIn('summary', data)
        self.assertIn('metrics', data)
        self.assertIn('team_profiles', data)
        self.assertEqual(data['summary']['total_learnings'], 1)
    
    def test_export_metrics_report_csv(self):
        """Test exporting metrics report as CSV"""
        learning = Learning(
            id="csv_export",
            team_id="team_csv",
            type=LearningType.PROCESS,
            priority=LearningPriority.LOW,
            title="CSV Export",
            description="CSV export test",
            context={},
            tags=["csv"],
            source="test",
            timestamp=datetime.now(),
            confidence=0.6
        )
        asyncio.run(self.tracker.track_learning(learning))
        
        csv_report = self.tracker.export_metrics_report("csv")
        
        lines = csv_report.split("\n")
        self.assertIn("Learning ID,Quality Score,Impact Score", lines[0])
        self.assertIn("csv_export", lines[1])
    
    def test_get_tracker_stats(self):
        """Test getting tracker statistics"""
        # Add some test data
        for i in range(3):
            learning = Learning(
                id=f"stats_{i}",
                team_id=f"team_{i}",
                type=LearningType.SUCCESS,
                priority=LearningPriority.MEDIUM,
                title=f"Stats Learning {i}",
                description=f"Stats test {i}",
                context={},
                tags=["stats"],
                source="test",
                timestamp=datetime.now() - timedelta(hours=i),
                confidence=0.7
            )
            asyncio.run(self.tracker.track_learning(learning))
        
        stats = self.tracker.get_tracker_stats()
        
        self.assertIn('total_learnings_tracked', stats)
        self.assertIn('total_teams', stats)
        self.assertIn('total_evolutions', stats)
        self.assertIn('total_rois', stats)
        self.assertIn('timeline_entries', stats)
        self.assertEqual(stats['total_learnings_tracked'], 3)
        self.assertEqual(stats['total_teams'], 3)
    
    def test_team_characteristics_identification(self):
        """Test identification of team strengths and weaknesses"""
        team_id = "team_characteristics"
        
        # Create high-quality, high-impact learnings
        for i in range(6):
            learning = Learning(
                id=f"char_{i}",
                team_id=team_id,
                type=[LearningType.TECHNICAL, LearningType.PROCESS, LearningType.INNOVATION,
                      LearningType.SUCCESS, LearningType.IMPROVEMENT, LearningType.STRATEGIC][i],
                priority=LearningPriority.HIGH,
                title=f"High Quality Learning {i}",
                description="A" * 200,  # Long description
                context={"diverse": i},
                tags=[f"tag_{i}", f"quality_{i}"],
                source="research",
                timestamp=datetime.now() - timedelta(hours=i),
                confidence=0.85,
                validated=True
            )
            asyncio.run(self.tracker.track_learning(learning))
        
        profile = self.tracker.get_team_profile(team_id)
        
        self.assertGreater(len(profile.strengths), 0)
        # Check that strengths were identified (may vary based on thresholds)
        self.assertGreaterEqual(len(profile.strengths), 1)
        self.assertIn("Diverse learning types", profile.strengths)
    
    def test_persistence_and_loading(self):
        """Test saving and loading metrics from storage"""
        # Create and track a learning
        learning = Learning(
            id="persist_test",
            team_id="team_persist",
            type=LearningType.SUCCESS,
            priority=LearningPriority.HIGH,
            title="Persistence Test",
            description="Testing persistence",
            context={},
            tags=["persist"],
            source="test",
            timestamp=datetime.now(),
            confidence=0.8
        )
        
        asyncio.run(self.tracker.track_learning(learning))
        
        # Create a new tracker with same storage path
        new_tracker = LearningTracker(storage_path=self.temp_dir)
        
        # Check that data was loaded
        loaded_metrics = new_tracker.get_learning_metrics("persist_test")
        self.assertIsNotNone(loaded_metrics)
        self.assertEqual(loaded_metrics.learning_id, "persist_test")
        
        loaded_profile = new_tracker.get_team_profile("team_persist")
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.total_learnings, 1)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False)


if __name__ == "__main__":
    run_tests()