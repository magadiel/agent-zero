"""
Test suite for Velocity Tracker module
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import unittest
from datetime import datetime, timedelta
from metrics.velocity_tracker import (
    VelocityTracker, SprintVelocity, VelocityPrediction,
    CapacityPlan, VelocityTrend, PredictionConfidence, CapacityFactor
)


class TestVelocityTracker(unittest.TestCase):
    """Test cases for VelocityTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = VelocityTracker()
        self._setup_test_data()
        
    def _setup_test_data(self):
        """Set up test velocity data"""
        # Add historical sprint velocities for team-alpha
        base_date = datetime.now() - timedelta(days=140)
        
        velocities = [
            (40, 38),  # Sprint 1
            (42, 40),  # Sprint 2
            (45, 44),  # Sprint 3
            (48, 47),  # Sprint 4
            (50, 49),  # Sprint 5 - improving trend
            (52, 51),  # Sprint 6
            (50, 50),  # Sprint 7
        ]
        
        for i, (committed, completed) in enumerate(velocities):
            sprint_velocity = SprintVelocity(
                sprint_id=f'sprint-{i+1}',
                sprint_number=i+1,
                team_id='team-alpha',
                committed_points=committed,
                completed_points=completed,
                start_date=base_date + timedelta(days=i*14),
                end_date=base_date + timedelta(days=(i+1)*14 - 1),
                team_size=5,
                working_days=10,
                capacity_factors=[],
                notes=f"Sprint {i+1} notes"
            )
            self.tracker.record_sprint_velocity(sprint_velocity)
    
    def test_record_sprint_velocity(self):
        """Test recording sprint velocity"""
        sprint_velocity = SprintVelocity(
            sprint_id='test-sprint',
            sprint_number=8,
            team_id='team-beta',
            committed_points=30,
            completed_points=28,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=14),
            team_size=4,
            working_days=10
        )
        
        self.tracker.record_sprint_velocity(sprint_velocity)
        
        self.assertIn('team-beta', self.tracker.sprint_velocities)
        self.assertEqual(len(self.tracker.sprint_velocities['team-beta']), 1)
        self.assertEqual(self.tracker.sprint_velocities['team-beta'][0].sprint_id, 'test-sprint')
    
    def test_calculate_average_velocity(self):
        """Test average velocity calculation"""
        # Test with all sprints
        avg = self.tracker.calculate_average_velocity('team-alpha')
        self.assertAlmostEqual(avg, 45.571, places=2)  # Average of completed points
        
        # Test with last 3 sprints
        avg_last_3 = self.tracker.calculate_average_velocity('team-alpha', 3)
        self.assertAlmostEqual(avg_last_3, 50.0, places=1)  # Average of last 3
        
        # Test with non-existent team
        avg_none = self.tracker.calculate_average_velocity('team-none')
        self.assertEqual(avg_none, 0.0)
    
    def test_calculate_rolling_average(self):
        """Test rolling average calculation"""
        rolling_avg = self.tracker.calculate_rolling_average('team-alpha', 3)
        
        self.assertIsInstance(rolling_avg, list)
        self.assertEqual(len(rolling_avg), 5)  # 7 sprints - 3 window + 1
        
        # Check first rolling average (sprints 1,2,3)
        expected_first = (38 + 40 + 44) / 3
        self.assertAlmostEqual(rolling_avg[0], expected_first, places=1)
    
    def test_predict_velocity(self):
        """Test velocity prediction"""
        prediction = self.tracker.predict_velocity('team-alpha')
        
        self.assertIsInstance(prediction, VelocityPrediction)
        self.assertEqual(prediction.team_id, 'team-alpha')
        self.assertGreater(prediction.predicted_velocity, 0)
        self.assertIn(prediction.confidence, [c for c in PredictionConfidence])
        self.assertGreater(prediction.confidence_percentage, 0)
        self.assertLessEqual(prediction.lower_bound, prediction.predicted_velocity)
        self.assertGreaterEqual(prediction.upper_bound, prediction.predicted_velocity)
        self.assertIsInstance(prediction.recommendation, str)
    
    def test_predict_velocity_insufficient_data(self):
        """Test velocity prediction with insufficient data"""
        # Team with no data
        prediction = self.tracker.predict_velocity('team-none')
        self.assertEqual(prediction.confidence, PredictionConfidence.VERY_LOW)
        self.assertEqual(prediction.predicted_velocity, 0)
        
        # Team with only one sprint
        self.tracker.record_sprint_velocity(SprintVelocity(
            sprint_id='single',
            sprint_number=1,
            team_id='team-single',
            committed_points=20,
            completed_points=18,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=14),
            team_size=3,
            working_days=10
        ))
        
        prediction = self.tracker.predict_velocity('team-single')
        self.assertEqual(prediction.confidence, PredictionConfidence.VERY_LOW)
        self.assertEqual(prediction.predicted_velocity, 18)
    
    def test_analyze_commitment_vs_completion(self):
        """Test commitment vs completion analysis"""
        analysis = self.tracker.analyze_commitment_vs_completion('team-alpha')
        
        self.assertIn('average_committed', analysis)
        self.assertIn('average_completed', analysis)
        self.assertIn('completion_rate', analysis)
        self.assertIn('overcommitment_rate', analysis)
        
        self.assertGreater(analysis['average_committed'], 0)
        self.assertGreater(analysis['average_completed'], 0)
        self.assertGreater(analysis['completion_rate'], 90)  # Team is doing well
        self.assertLess(analysis['overcommitment_rate'], 100)
    
    def test_get_velocity_trend(self):
        """Test velocity trend analysis"""
        trend = self.tracker.get_velocity_trend('team-alpha')
        
        self.assertIsInstance(trend, VelocityTrend)
        self.assertEqual(trend.team_id, 'team-alpha')
        self.assertIn(trend.trend_direction, ['increasing', 'stable', 'decreasing'])
        self.assertGreaterEqual(trend.trend_strength, 0)
        self.assertLessEqual(trend.trend_strength, 1)
        self.assertGreater(trend.average_velocity, 0)
        self.assertGreaterEqual(trend.stability_score, 0)
        self.assertLessEqual(trend.stability_score, 100)
        self.assertIn(trend.maturity_level, ['forming', 'stabilizing', 'mature', 'optimizing'])
    
    def test_plan_sprint_capacity(self):
        """Test sprint capacity planning"""
        capacity_plan = self.tracker.plan_sprint_capacity(
            team_id='team-alpha',
            sprint_id='sprint-8',
            working_days=10,
            team_size=5,
            risk_factors=['new_team_members']
        )
        
        self.assertIsInstance(capacity_plan, CapacityPlan)
        self.assertEqual(capacity_plan.team_id, 'team-alpha')
        self.assertEqual(capacity_plan.sprint_id, 'sprint-8')
        self.assertGreater(capacity_plan.available_capacity, 0)
        self.assertGreater(capacity_plan.recommended_commitment, 0)
        self.assertLess(capacity_plan.recommended_commitment, capacity_plan.available_capacity)
        self.assertGreater(capacity_plan.buffer_percentage, 0)
        self.assertIn('new_team_members', capacity_plan.risk_factors)
        
    def test_capacity_adjustments(self):
        """Test capacity adjustment calculations"""
        # Set team capacity factors
        self.tracker.team_capacity['team-alpha'] = {
            'team_size_change': 0.9,  # 10% reduction
            'holiday_impact': 0.1,     # 10% holidays
            'new_members_ratio': 0.2   # 20% new members
        }
        
        adjustment = self.tracker._calculate_capacity_adjustments('team-alpha')
        
        # Should be less than 1.0 due to negative factors
        self.assertLess(adjustment, 1.0)
        self.assertGreater(adjustment, 0)
    
    def test_maturity_level_determination(self):
        """Test team maturity level determination"""
        # Test forming (few sprints)
        maturity = self.tracker._determine_maturity_level(2, 50, 'stable')
        self.assertEqual(maturity, 'forming')
        
        # Test stabilizing
        maturity = self.tracker._determine_maturity_level(5, 60, 'stable')
        self.assertEqual(maturity, 'stabilizing')
        
        # Test mature
        maturity = self.tracker._determine_maturity_level(8, 75, 'stable')
        self.assertEqual(maturity, 'mature')
        
        # Test optimizing
        maturity = self.tracker._determine_maturity_level(15, 80, 'increasing')
        self.assertEqual(maturity, 'optimizing')
    
    def test_export_json(self):
        """Test JSON export"""
        json_export = self.tracker.export_velocity_data('team-alpha', 'json')
        
        self.assertIsInstance(json_export, str)
        self.assertIn('team_id', json_export)
        self.assertIn('velocities', json_export)
        self.assertIn('prediction', json_export)
        self.assertIn('trend', json_export)
        self.assertIn('commitment_analysis', json_export)
    
    def test_export_csv(self):
        """Test CSV export"""
        csv_export = self.tracker.export_velocity_data('team-alpha', 'csv')
        
        self.assertIsInstance(csv_export, str)
        self.assertIn('Sprint,Sprint_Number,Committed,Completed', csv_export)
        self.assertIn('sprint-1', csv_export)
        
        # Check number of data rows
        lines = csv_export.split('\n')
        self.assertEqual(len(lines), 8)  # Header + 7 sprints
    
    def test_export_markdown(self):
        """Test Markdown export"""
        md_export = self.tracker.export_velocity_data('team-alpha', 'markdown')
        
        self.assertIsInstance(md_export, str)
        self.assertIn('# Velocity Report', md_export)
        self.assertIn('## Velocity Trend', md_export)
        self.assertIn('## Velocity Prediction', md_export)
        self.assertIn('## Commitment Analysis', md_export)
        self.assertIn('## Sprint History', md_export)
    
    def test_prediction_accuracy_tracking(self):
        """Test prediction accuracy tracking"""
        # Record a sprint to update accuracy
        sprint = SprintVelocity(
            sprint_id='sprint-8',
            sprint_number=8,
            team_id='team-alpha',
            committed_points=52,
            completed_points=50,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=14),
            team_size=5,
            working_days=10
        )
        
        self.tracker.record_sprint_velocity(sprint)
        
        # Check that accuracy was tracked
        self.assertIn('team-alpha', self.tracker.historical_accuracy)
        self.assertGreater(len(self.tracker.historical_accuracy['team-alpha']), 0)
        
        # Get accuracy score
        score = self.tracker._get_prediction_accuracy_score('team-alpha')
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_calculate_weights(self):
        """Test weight calculation for weighted average"""
        weights = self.tracker._calculate_weights(5)
        
        self.assertEqual(len(weights), 5)
        self.assertAlmostEqual(sum(weights), 1.0, places=5)
        
        # Recent items should have higher weight
        self.assertGreater(weights[-1], weights[0])
    
    def test_calculate_trend(self):
        """Test trend calculation"""
        # Increasing trend
        trend = self.tracker._calculate_trend([10, 15, 20, 25, 30])
        self.assertGreater(trend, 0)
        
        # Decreasing trend
        trend = self.tracker._calculate_trend([30, 25, 20, 15, 10])
        self.assertLess(trend, 0)
        
        # Stable trend
        trend = self.tracker._calculate_trend([20, 20, 20, 20, 20])
        self.assertAlmostEqual(trend, 0, places=1)


class TestVelocityDataClasses(unittest.TestCase):
    """Test velocity-related data classes"""
    
    def test_sprint_velocity_dataclass(self):
        """Test SprintVelocity dataclass"""
        sprint = SprintVelocity(
            sprint_id='test-sprint',
            sprint_number=1,
            team_id='team-test',
            committed_points=30,
            completed_points=28,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=14),
            team_size=5,
            working_days=10,
            capacity_factors=[CapacityFactor.HOLIDAYS],
            notes="Test sprint"
        )
        
        self.assertEqual(sprint.sprint_id, 'test-sprint')
        self.assertEqual(sprint.committed_points, 30)
        self.assertEqual(sprint.completed_points, 28)
        self.assertEqual(len(sprint.capacity_factors), 1)
        self.assertEqual(sprint.capacity_factors[0], CapacityFactor.HOLIDAYS)
    
    def test_prediction_confidence_enum(self):
        """Test PredictionConfidence enum"""
        self.assertEqual(PredictionConfidence.HIGH.value, 'high')
        self.assertEqual(PredictionConfidence.MEDIUM.value, 'medium')
        self.assertEqual(PredictionConfidence.LOW.value, 'low')
        self.assertEqual(PredictionConfidence.VERY_LOW.value, 'very_low')
    
    def test_capacity_factor_enum(self):
        """Test CapacityFactor enum"""
        self.assertEqual(CapacityFactor.HOLIDAYS.value, 'holidays')
        self.assertEqual(CapacityFactor.TEAM_SIZE_CHANGE.value, 'team_size_change')
        self.assertEqual(CapacityFactor.TECHNICAL_DEBT.value, 'technical_debt')


if __name__ == '__main__':
    unittest.main()