"""
Test suite for Agile Metrics module
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import unittest
from datetime import datetime, timedelta
from metrics.agile_metrics import (
    AgileMetrics, MetricType, TrendDirection, 
    MetricValue, MetricSummary, TeamMetrics
)


class TestAgileMetrics(unittest.TestCase):
    """Test cases for AgileMetrics class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.metrics = AgileMetrics()
        self._setup_test_data()
        
    def _setup_test_data(self):
        """Set up test data for metrics"""
        # Add sprint data
        self.metrics.add_sprint_data('sprint-1', {
            'team_id': 'team-alpha',
            'start_date': (datetime.now() - timedelta(days=14)).isoformat(),
            'end_date': (datetime.now() - timedelta(days=1)).isoformat(),
            'committed_points': 50,
            'completed_points': 45
        })
        
        self.metrics.add_sprint_data('sprint-2', {
            'team_id': 'team-alpha',
            'start_date': datetime.now().isoformat(),
            'end_date': (datetime.now() + timedelta(days=13)).isoformat(),
            'committed_points': 48,
            'completed_points': 48
        })
        
        # Add story data
        for i in range(5):
            self.metrics.add_story_data(f'story-{i}', {
                'team_id': 'team-alpha',
                'sprint_id': 'sprint-1',
                'points': 10,
                'created_date': (datetime.now() - timedelta(days=20)).isoformat(),
                'start_date': (datetime.now() - timedelta(days=10)).isoformat(),
                'end_date': (datetime.now() - timedelta(days=5 - i)).isoformat(),
                'defect_count': 0 if i < 3 else 1,
                'required_rework': i == 4
            })
    
    def test_record_metric(self):
        """Test recording a metric value"""
        self.metrics.record_metric(
            MetricType.VELOCITY,
            45.0,
            team_id='team-alpha',
            sprint_id='sprint-1'
        )
        
        key = 'team-alpha_velocity'
        self.assertIn(key, self.metrics.metrics_data)
        self.assertEqual(len(self.metrics.metrics_data[key]), 1)
        self.assertEqual(self.metrics.metrics_data[key][0].value, 45.0)
    
    def test_calculate_velocity(self):
        """Test velocity calculation"""
        velocity = self.metrics.calculate_velocity('team-alpha', ['sprint-1', 'sprint-2'])
        self.assertEqual(velocity, 46.5)  # (45 + 48) / 2
    
    def test_calculate_cycle_time(self):
        """Test cycle time calculation"""
        story_ids = ['story-0', 'story-1', 'story-2']
        cycle_time = self.metrics.calculate_cycle_time(story_ids)
        self.assertGreater(cycle_time, 0)
    
    def test_calculate_lead_time(self):
        """Test lead time calculation"""
        story_ids = ['story-0', 'story-1', 'story-2']
        lead_time = self.metrics.calculate_lead_time(story_ids)
        self.assertGreater(lead_time, 0)
        self.assertGreater(lead_time, self.metrics.calculate_cycle_time(story_ids))
    
    def test_calculate_throughput(self):
        """Test throughput calculation"""
        start_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now()
        throughput = self.metrics.calculate_throughput('team-alpha', start_date, end_date)
        self.assertGreater(throughput, 0)
    
    def test_calculate_defect_rate(self):
        """Test defect rate calculation"""
        defect_rate = self.metrics.calculate_defect_rate('team-alpha', ['sprint-1'])
        self.assertEqual(defect_rate, 0.4)  # 2 defects / 5 stories
    
    def test_calculate_rework_rate(self):
        """Test rework rate calculation"""
        rework_rate = self.metrics.calculate_rework_rate('team-alpha', ['sprint-1'])
        self.assertEqual(rework_rate, 20.0)  # 1 rework / 5 stories * 100
    
    def test_calculate_commitment_reliability(self):
        """Test commitment reliability calculation"""
        reliability = self.metrics.calculate_commitment_reliability('team-alpha', ['sprint-1', 'sprint-2'])
        self.assertAlmostEqual(reliability, 94.9, places=1)  # (45 + 48) / (50 + 48) * 100 ≈ 94.9
    
    def test_calculate_trend(self):
        """Test trend calculation"""
        # Test improving trend
        values = [10, 12, 15, 18, 20]
        trend = self.metrics.calculate_trend(values)
        self.assertEqual(trend, TrendDirection.IMPROVING)
        
        # Test declining trend
        values = [20, 18, 15, 12, 10]
        trend = self.metrics.calculate_trend(values)
        self.assertEqual(trend, TrendDirection.DECLINING)
        
        # Test stable trend
        values = [15, 14, 15, 16, 15]
        trend = self.metrics.calculate_trend(values)
        self.assertEqual(trend, TrendDirection.STABLE)
        
        # Test insufficient data
        values = [10, 12]
        trend = self.metrics.calculate_trend(values)
        self.assertEqual(trend, TrendDirection.INSUFFICIENT_DATA)
    
    def test_get_metric_summary(self):
        """Test getting metric summary"""
        # Record some metrics
        for i in range(5):
            self.metrics.record_metric(
                MetricType.VELOCITY,
                40 + i * 2,
                team_id='team-alpha'
            )
        
        summary = self.metrics.get_metric_summary(MetricType.VELOCITY, 'team-alpha')
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary.metric_type, MetricType.VELOCITY)
        self.assertEqual(summary.current_value, 48)  # Last value
        self.assertEqual(summary.average, 44)  # Average of 40,42,44,46,48
        self.assertEqual(summary.median, 44)
        self.assertGreater(summary.std_dev, 0)
        self.assertEqual(summary.min_value, 40)
        self.assertEqual(summary.max_value, 48)
    
    def test_get_team_metrics(self):
        """Test getting comprehensive team metrics"""
        # Record various metrics
        self.metrics.calculate_velocity('team-alpha', ['sprint-1', 'sprint-2'])
        self.metrics.calculate_cycle_time(['story-0', 'story-1'])
        self.metrics.calculate_defect_rate('team-alpha', ['sprint-1'])
        
        team_metrics = self.metrics.get_team_metrics('team-alpha')
        
        self.assertIsNotNone(team_metrics)
        self.assertEqual(team_metrics.team_id, 'team-alpha')
        self.assertIsNotNone(team_metrics.velocity)
        self.assertIsNotNone(team_metrics.defect_rate)
        self.assertGreater(team_metrics.overall_health_score, 0)
    
    def test_calculate_burndown(self):
        """Test burndown calculation"""
        burndown = self.metrics.calculate_burndown('sprint-1')
        
        self.assertIsInstance(burndown, list)
        if burndown:
            self.assertIsInstance(burndown[0], tuple)
            self.assertIsInstance(burndown[0][0], datetime)
            self.assertIsInstance(burndown[0][1], (int, float))
    
    def test_calculate_burnup(self):
        """Test burnup calculation"""
        burnup, total_scope = self.metrics.calculate_burnup('sprint-1')
        
        self.assertIsInstance(burnup, list)
        self.assertIsInstance(total_scope, (int, float))
        if burnup:
            self.assertIsInstance(burnup[0], tuple)
            self.assertIsInstance(burnup[0][0], datetime)
            self.assertIsInstance(burnup[0][1], (int, float))
    
    def test_export_json(self):
        """Test JSON export"""
        self.metrics.calculate_velocity('team-alpha', ['sprint-1'])
        json_export = self.metrics.export_metrics('team-alpha', 'json')
        
        self.assertIsInstance(json_export, str)
        self.assertIn('team_id', json_export)
        self.assertIn('team-alpha', json_export)
    
    def test_export_csv(self):
        """Test CSV export"""
        self.metrics.record_metric(MetricType.VELOCITY, 45.0, team_id='team-alpha')
        csv_export = self.metrics.export_metrics('team-alpha', 'csv')
        
        self.assertIsInstance(csv_export, str)
        self.assertIn('Metric,Team,Value,Timestamp,Sprint,Metadata', csv_export)
        self.assertIn('velocity', csv_export)
    
    def test_export_markdown(self):
        """Test Markdown export"""
        self.metrics.calculate_velocity('team-alpha', ['sprint-1'])
        md_export = self.metrics.export_metrics('team-alpha', 'markdown')
        
        self.assertIsInstance(md_export, str)
        self.assertIn('# Agile Metrics Report', md_export)
        self.assertIn('team-alpha', md_export)
    
    def test_health_score_calculation(self):
        """Test health score calculation"""
        team_metrics = TeamMetrics(team_id='team-alpha')
        
        # Create mock metric summaries
        from unittest.mock import MagicMock
        
        # Good velocity trend
        team_metrics.velocity = MagicMock()
        team_metrics.velocity.trend = TrendDirection.IMPROVING
        team_metrics.velocity.current_value = 50
        
        # Good cycle time
        team_metrics.cycle_time = MagicMock()
        team_metrics.cycle_time.current_value = 40  # 40 hours is good
        
        # Low defect rate
        team_metrics.defect_rate = MagicMock()
        team_metrics.defect_rate.current_value = 0.1  # 0.1 defects per story
        
        # High commitment reliability
        team_metrics.commitment_reliability = MagicMock()
        team_metrics.commitment_reliability.current_value = 95
        
        health_score = self.metrics._calculate_health_score(team_metrics)
        self.assertGreater(health_score, 80)  # Should be a high score


class TestMetricTypes(unittest.TestCase):
    """Test metric type enums and data classes"""
    
    def test_metric_type_enum(self):
        """Test MetricType enum"""
        self.assertEqual(MetricType.VELOCITY.value, 'velocity')
        self.assertEqual(MetricType.CYCLE_TIME.value, 'cycle_time')
        self.assertEqual(MetricType.DEFECT_RATE.value, 'defect_rate')
    
    def test_trend_direction_enum(self):
        """Test TrendDirection enum"""
        self.assertEqual(TrendDirection.IMPROVING.value, 'improving')
        self.assertEqual(TrendDirection.DECLINING.value, 'declining')
        self.assertEqual(TrendDirection.STABLE.value, 'stable')
    
    def test_metric_value_dataclass(self):
        """Test MetricValue dataclass"""
        metric = MetricValue(
            metric_type=MetricType.VELOCITY,
            value=45.0,
            timestamp=datetime.now(),
            sprint_id='sprint-1',
            team_id='team-alpha',
            metadata={'test': 'data'}
        )
        
        self.assertEqual(metric.metric_type, MetricType.VELOCITY)
        self.assertEqual(metric.value, 45.0)
        self.assertEqual(metric.sprint_id, 'sprint-1')
        self.assertEqual(metric.team_id, 'team-alpha')
        self.assertEqual(metric.metadata['test'], 'data')


if __name__ == '__main__':
    unittest.main()