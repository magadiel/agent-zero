"""
Agile Metrics Module
Implements comprehensive agile performance metrics for AI teams.
Part of the Agile AI Company framework.
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

class MetricType(Enum):
    """Types of agile metrics"""
    VELOCITY = "velocity"
    CYCLE_TIME = "cycle_time"
    LEAD_TIME = "lead_time"
    THROUGHPUT = "throughput"
    BURNDOWN = "burndown"
    BURNUP = "burnup"
    DEFECT_RATE = "defect_rate"
    REWORK_RATE = "rework_rate"
    COMMITMENT_RELIABILITY = "commitment_reliability"
    TEAM_HAPPINESS = "team_happiness"
    CODE_QUALITY = "code_quality"
    TECHNICAL_DEBT = "technical_debt"

class TrendDirection(Enum):
    """Trend direction for metrics"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"

@dataclass
class MetricValue:
    """Represents a single metric value"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    sprint_id: Optional[str] = None
    team_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    metric_type: MetricType
    current_value: float
    average: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    trend: TrendDirection
    change_percentage: float
    sample_size: int
    period_start: datetime
    period_end: datetime

@dataclass
class TeamMetrics:
    """Comprehensive metrics for a team"""
    team_id: str
    velocity: Optional[MetricSummary] = None
    cycle_time: Optional[MetricSummary] = None
    lead_time: Optional[MetricSummary] = None
    throughput: Optional[MetricSummary] = None
    defect_rate: Optional[MetricSummary] = None
    rework_rate: Optional[MetricSummary] = None
    commitment_reliability: Optional[MetricSummary] = None
    team_happiness: Optional[MetricSummary] = None
    overall_health_score: float = 0.0

class AgileMetrics:
    """
    Comprehensive agile metrics calculator for AI teams.
    Tracks velocity, cycle time, throughput, and quality metrics.
    """
    
    def __init__(self):
        self.metrics_data: Dict[str, List[MetricValue]] = defaultdict(list)
        self.sprint_data: Dict[str, Dict] = {}
        self.story_data: Dict[str, Dict] = {}
        self.team_data: Dict[str, Dict] = {}
        
    def record_metric(self, metric_type: MetricType, value: float, 
                     timestamp: Optional[datetime] = None,
                     sprint_id: Optional[str] = None,
                     team_id: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> None:
        """Record a metric value"""
        if timestamp is None:
            timestamp = datetime.now()
            
        metric = MetricValue(
            metric_type=metric_type,
            value=value,
            timestamp=timestamp,
            sprint_id=sprint_id,
            team_id=team_id,
            metadata=metadata or {}
        )
        
        key = f"{team_id or 'global'}_{metric_type.value}"
        self.metrics_data[key].append(metric)
        
    def calculate_velocity(self, team_id: str, sprint_ids: List[str]) -> float:
        """
        Calculate team velocity across sprints.
        Velocity = Story Points Completed / Sprint
        """
        if not sprint_ids:
            return 0.0
            
        total_points = 0
        valid_sprints = 0
        
        for sprint_id in sprint_ids:
            if sprint_id in self.sprint_data:
                sprint = self.sprint_data[sprint_id]
                if sprint.get('completed_points'):
                    total_points += sprint['completed_points']
                    valid_sprints += 1
                    
        if valid_sprints == 0:
            return 0.0
            
        velocity = total_points / valid_sprints
        self.record_metric(
            MetricType.VELOCITY,
            velocity,
            team_id=team_id,
            metadata={'sprint_count': valid_sprints}
        )
        return velocity
    
    def calculate_cycle_time(self, story_ids: List[str]) -> float:
        """
        Calculate average cycle time for stories.
        Cycle Time = Time from In Progress to Done
        """
        if not story_ids:
            return 0.0
            
        cycle_times = []
        
        for story_id in story_ids:
            if story_id in self.story_data:
                story = self.story_data[story_id]
                if story.get('start_date') and story.get('end_date'):
                    start = datetime.fromisoformat(story['start_date'])
                    end = datetime.fromisoformat(story['end_date'])
                    cycle_time = (end - start).total_seconds() / 3600  # Hours
                    cycle_times.append(cycle_time)
                    
        if not cycle_times:
            return 0.0
            
        avg_cycle_time = statistics.mean(cycle_times)
        self.record_metric(
            MetricType.CYCLE_TIME,
            avg_cycle_time,
            metadata={'story_count': len(cycle_times)}
        )
        return avg_cycle_time
    
    def calculate_lead_time(self, story_ids: List[str]) -> float:
        """
        Calculate average lead time for stories.
        Lead Time = Time from Creation to Done
        """
        if not story_ids:
            return 0.0
            
        lead_times = []
        
        for story_id in story_ids:
            if story_id in self.story_data:
                story = self.story_data[story_id]
                if story.get('created_date') and story.get('end_date'):
                    created = datetime.fromisoformat(story['created_date'])
                    end = datetime.fromisoformat(story['end_date'])
                    lead_time = (end - created).total_seconds() / 3600  # Hours
                    lead_times.append(lead_time)
                    
        if not lead_times:
            return 0.0
            
        avg_lead_time = statistics.mean(lead_times)
        self.record_metric(
            MetricType.LEAD_TIME,
            avg_lead_time,
            metadata={'story_count': len(lead_times)}
        )
        return avg_lead_time
    
    def calculate_throughput(self, team_id: str, start_date: datetime, 
                           end_date: datetime) -> float:
        """
        Calculate throughput (stories completed per day).
        """
        completed_stories = 0
        
        for story_id, story in self.story_data.items():
            if story.get('team_id') == team_id and story.get('end_date'):
                end = datetime.fromisoformat(story['end_date'])
                if start_date <= end <= end_date:
                    completed_stories += 1
                    
        days = (end_date - start_date).days or 1
        throughput = completed_stories / days
        
        self.record_metric(
            MetricType.THROUGHPUT,
            throughput,
            team_id=team_id,
            metadata={'period_days': days, 'stories_completed': completed_stories}
        )
        return throughput
    
    def calculate_burndown(self, sprint_id: str) -> List[Tuple[datetime, float]]:
        """
        Calculate burndown chart data for a sprint.
        Returns list of (date, remaining_points) tuples.
        """
        if sprint_id not in self.sprint_data:
            return []
            
        sprint = self.sprint_data[sprint_id]
        start_date = datetime.fromisoformat(sprint['start_date'])
        end_date = datetime.fromisoformat(sprint['end_date'])
        total_points = sprint.get('committed_points', 0)
        
        # Calculate daily burn
        burndown_data = []
        current_date = start_date
        remaining_points = total_points
        
        while current_date <= end_date:
            # Calculate points completed by this date
            completed_today = 0
            for story_id, story in self.story_data.items():
                if story.get('sprint_id') == sprint_id and story.get('end_date'):
                    story_end = datetime.fromisoformat(story['end_date'])
                    if story_end.date() == current_date.date():
                        completed_today += story.get('points', 0)
                        
            remaining_points -= completed_today
            burndown_data.append((current_date, remaining_points))
            current_date += timedelta(days=1)
            
        return burndown_data
    
    def calculate_burnup(self, sprint_id: str) -> Tuple[List[Tuple[datetime, float]], float]:
        """
        Calculate burnup chart data for a sprint.
        Returns (list of (date, completed_points) tuples, total_scope).
        """
        if sprint_id not in self.sprint_data:
            return [], 0
            
        sprint = self.sprint_data[sprint_id]
        start_date = datetime.fromisoformat(sprint['start_date'])
        end_date = datetime.fromisoformat(sprint['end_date'])
        total_scope = sprint.get('committed_points', 0)
        
        # Calculate daily completion
        burnup_data = []
        current_date = start_date
        completed_points = 0
        
        while current_date <= end_date:
            # Calculate points completed by this date
            for story_id, story in self.story_data.items():
                if story.get('sprint_id') == sprint_id and story.get('end_date'):
                    story_end = datetime.fromisoformat(story['end_date'])
                    if story_end.date() <= current_date.date():
                        completed_points += story.get('points', 0)
                        
            burnup_data.append((current_date, completed_points))
            current_date += timedelta(days=1)
            
        return burnup_data, total_scope
    
    def calculate_defect_rate(self, team_id: str, sprint_ids: List[str]) -> float:
        """
        Calculate defect rate (defects per story).
        """
        total_stories = 0
        total_defects = 0
        
        for sprint_id in sprint_ids:
            for story_id, story in self.story_data.items():
                if story.get('team_id') == team_id and story.get('sprint_id') == sprint_id:
                    total_stories += 1
                    total_defects += story.get('defect_count', 0)
                    
        if total_stories == 0:
            return 0.0
            
        defect_rate = total_defects / total_stories
        self.record_metric(
            MetricType.DEFECT_RATE,
            defect_rate,
            team_id=team_id,
            metadata={'total_stories': total_stories, 'total_defects': total_defects}
        )
        return defect_rate
    
    def calculate_rework_rate(self, team_id: str, sprint_ids: List[str]) -> float:
        """
        Calculate rework rate (percentage of stories requiring rework).
        """
        total_stories = 0
        rework_stories = 0
        
        for sprint_id in sprint_ids:
            for story_id, story in self.story_data.items():
                if story.get('team_id') == team_id and story.get('sprint_id') == sprint_id:
                    total_stories += 1
                    if story.get('required_rework', False):
                        rework_stories += 1
                        
        if total_stories == 0:
            return 0.0
            
        rework_rate = (rework_stories / total_stories) * 100
        self.record_metric(
            MetricType.REWORK_RATE,
            rework_rate,
            team_id=team_id,
            metadata={'total_stories': total_stories, 'rework_stories': rework_stories}
        )
        return rework_rate
    
    def calculate_commitment_reliability(self, team_id: str, sprint_ids: List[str]) -> float:
        """
        Calculate commitment reliability (percentage of committed points delivered).
        """
        total_committed = 0
        total_delivered = 0
        
        for sprint_id in sprint_ids:
            if sprint_id in self.sprint_data:
                sprint = self.sprint_data[sprint_id]
                if sprint.get('team_id') == team_id:
                    total_committed += sprint.get('committed_points', 0)
                    total_delivered += sprint.get('completed_points', 0)
                    
        if total_committed == 0:
            return 100.0
            
        reliability = (total_delivered / total_committed) * 100
        self.record_metric(
            MetricType.COMMITMENT_RELIABILITY,
            reliability,
            team_id=team_id,
            metadata={'total_committed': total_committed, 'total_delivered': total_delivered}
        )
        return reliability
    
    def calculate_trend(self, values: List[float], min_samples: int = 3) -> TrendDirection:
        """Calculate trend direction from a series of values"""
        if len(values) < min_samples:
            return TrendDirection.INSUFFICIENT_DATA
            
        # Calculate linear regression slope
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return TrendDirection.STABLE
            
        slope = numerator / denominator
        
        # Determine trend based on slope and variance
        variance = statistics.variance(values) if n > 1 else 0
        relative_slope = abs(slope) / (y_mean if y_mean != 0 else 1)
        
        if relative_slope < 0.05:  # Less than 5% change
            return TrendDirection.STABLE
        elif slope > 0:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.DECLINING
    
    def get_metric_summary(self, metric_type: MetricType, team_id: Optional[str] = None,
                          period_days: int = 90) -> Optional[MetricSummary]:
        """Get summary statistics for a metric"""
        key = f"{team_id or 'global'}_{metric_type.value}"
        if key not in self.metrics_data:
            return None
            
        # Filter by period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        values = [
            m.value for m in self.metrics_data[key]
            if start_date <= m.timestamp <= end_date
        ]
        
        if not values:
            return None
            
        # Calculate statistics
        current_value = values[-1]
        average = statistics.mean(values)
        median = statistics.median(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        min_value = min(values)
        max_value = max(values)
        
        # Calculate trend
        trend = self.calculate_trend(values)
        
        # Calculate change percentage
        if len(values) > 1:
            change_percentage = ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
        else:
            change_percentage = 0
            
        return MetricSummary(
            metric_type=metric_type,
            current_value=current_value,
            average=average,
            median=median,
            std_dev=std_dev,
            min_value=min_value,
            max_value=max_value,
            trend=trend,
            change_percentage=change_percentage,
            sample_size=len(values),
            period_start=start_date,
            period_end=end_date
        )
    
    def get_team_metrics(self, team_id: str, period_days: int = 90) -> TeamMetrics:
        """Get comprehensive metrics for a team"""
        metrics = TeamMetrics(team_id=team_id)
        
        # Collect all metric summaries
        metrics.velocity = self.get_metric_summary(MetricType.VELOCITY, team_id, period_days)
        metrics.cycle_time = self.get_metric_summary(MetricType.CYCLE_TIME, team_id, period_days)
        metrics.lead_time = self.get_metric_summary(MetricType.LEAD_TIME, team_id, period_days)
        metrics.throughput = self.get_metric_summary(MetricType.THROUGHPUT, team_id, period_days)
        metrics.defect_rate = self.get_metric_summary(MetricType.DEFECT_RATE, team_id, period_days)
        metrics.rework_rate = self.get_metric_summary(MetricType.REWORK_RATE, team_id, period_days)
        metrics.commitment_reliability = self.get_metric_summary(MetricType.COMMITMENT_RELIABILITY, team_id, period_days)
        metrics.team_happiness = self.get_metric_summary(MetricType.TEAM_HAPPINESS, team_id, period_days)
        
        # Calculate overall health score
        metrics.overall_health_score = self._calculate_health_score(metrics)
        
        return metrics
    
    def _calculate_health_score(self, metrics: TeamMetrics) -> float:
        """Calculate overall team health score (0-100)"""
        scores = []
        
        # Velocity trend (higher is better)
        if metrics.velocity and metrics.velocity.trend != TrendDirection.INSUFFICIENT_DATA:
            if metrics.velocity.trend == TrendDirection.IMPROVING:
                scores.append(100)
            elif metrics.velocity.trend == TrendDirection.STABLE:
                scores.append(75)
            else:
                scores.append(50)
                
        # Cycle time (lower is better)
        if metrics.cycle_time and metrics.cycle_time.current_value > 0:
            # Normalize to 0-100 scale (assuming 40 hours is good, 200 hours is bad)
            normalized = max(0, min(100, 100 - (metrics.cycle_time.current_value - 40) / 1.6))
            scores.append(normalized)
            
        # Defect rate (lower is better)
        if metrics.defect_rate:
            # Normalize to 0-100 scale (0 defects = 100, 1+ defects per story = 0)
            normalized = max(0, min(100, 100 * (1 - metrics.defect_rate.current_value)))
            scores.append(normalized)
            
        # Commitment reliability (higher is better)
        if metrics.commitment_reliability:
            scores.append(metrics.commitment_reliability.current_value)
            
        # Team happiness (higher is better)
        if metrics.team_happiness:
            scores.append(metrics.team_happiness.current_value)
            
        if not scores:
            return 50.0  # Default neutral score
            
        return statistics.mean(scores)
    
    def add_sprint_data(self, sprint_id: str, data: Dict) -> None:
        """Add sprint data for metrics calculation"""
        self.sprint_data[sprint_id] = data
        
    def add_story_data(self, story_id: str, data: Dict) -> None:
        """Add story data for metrics calculation"""
        self.story_data[story_id] = data
        
    def add_team_data(self, team_id: str, data: Dict) -> None:
        """Add team data for metrics calculation"""
        self.team_data[team_id] = data
    
    def export_metrics(self, team_id: Optional[str] = None, 
                      format: str = 'json') -> str:
        """Export metrics in specified format"""
        if format == 'json':
            return self._export_json(team_id)
        elif format == 'csv':
            return self._export_csv(team_id)
        elif format == 'markdown':
            return self._export_markdown(team_id)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, team_id: Optional[str] = None) -> str:
        """Export metrics as JSON"""
        data = {}
        
        if team_id:
            team_metrics = self.get_team_metrics(team_id)
            data = {
                'team_id': team_id,
                'metrics': {
                    'velocity': asdict(team_metrics.velocity) if team_metrics.velocity else None,
                    'cycle_time': asdict(team_metrics.cycle_time) if team_metrics.cycle_time else None,
                    'lead_time': asdict(team_metrics.lead_time) if team_metrics.lead_time else None,
                    'throughput': asdict(team_metrics.throughput) if team_metrics.throughput else None,
                    'defect_rate': asdict(team_metrics.defect_rate) if team_metrics.defect_rate else None,
                    'rework_rate': asdict(team_metrics.rework_rate) if team_metrics.rework_rate else None,
                    'commitment_reliability': asdict(team_metrics.commitment_reliability) if team_metrics.commitment_reliability else None,
                    'team_happiness': asdict(team_metrics.team_happiness) if team_metrics.team_happiness else None,
                },
                'overall_health_score': team_metrics.overall_health_score
            }
        else:
            # Export all metrics
            for key, values in self.metrics_data.items():
                data[key] = [asdict(v) for v in values]
                
        return json.dumps(data, indent=2, default=str)
    
    def _export_csv(self, team_id: Optional[str] = None) -> str:
        """Export metrics as CSV"""
        lines = ['Metric,Team,Value,Timestamp,Sprint,Metadata']
        
        for key, values in self.metrics_data.items():
            if team_id and not key.startswith(team_id):
                continue
                
            for metric in values:
                line = f"{metric.metric_type.value},{metric.team_id or 'global'},"
                line += f"{metric.value},{metric.timestamp.isoformat()},"
                line += f"{metric.sprint_id or ''},\"{json.dumps(metric.metadata)}\""
                lines.append(line)
                
        return '\n'.join(lines)
    
    def _export_markdown(self, team_id: Optional[str] = None) -> str:
        """Export metrics as Markdown report"""
        lines = ['# Agile Metrics Report', '']
        
        if team_id:
            metrics = self.get_team_metrics(team_id)
            lines.append(f"## Team: {team_id}")
            lines.append(f"**Overall Health Score**: {metrics.overall_health_score:.1f}/100")
            lines.append('')
            
            # Add individual metrics
            for metric_name, metric_summary in [
                ('Velocity', metrics.velocity),
                ('Cycle Time', metrics.cycle_time),
                ('Lead Time', metrics.lead_time),
                ('Throughput', metrics.throughput),
                ('Defect Rate', metrics.defect_rate),
                ('Rework Rate', metrics.rework_rate),
                ('Commitment Reliability', metrics.commitment_reliability),
                ('Team Happiness', metrics.team_happiness)
            ]:
                if metric_summary:
                    lines.append(f"### {metric_name}")
                    lines.append(f"- **Current**: {metric_summary.current_value:.2f}")
                    lines.append(f"- **Average**: {metric_summary.average:.2f}")
                    lines.append(f"- **Trend**: {metric_summary.trend.value}")
                    lines.append(f"- **Change**: {metric_summary.change_percentage:+.1f}%")
                    lines.append('')
        else:
            lines.append("## All Teams Summary")
            # List all teams
            teams = set()
            for key in self.metrics_data.keys():
                team = key.split('_')[0]
                if team != 'global':
                    teams.add(team)
                    
            for team in sorted(teams):
                team_metrics = self.get_team_metrics(team)
                lines.append(f"- **{team}**: Health Score {team_metrics.overall_health_score:.1f}/100")
                
        return '\n'.join(lines)