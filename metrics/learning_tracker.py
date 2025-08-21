"""
Learning Tracker for Measuring and Monitoring Learning Metrics

This module tracks and measures learning patterns, evolution, and ROI across teams.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
from pathlib import Path

# Import from learning synthesizer
import sys
sys.path.append(str(Path(__file__).parent.parent / "coordination"))
from learning_synthesizer import Learning, LearningType, LearningPriority, Pattern, PatternType


class LearningQuality(Enum):
    """Quality levels for learnings"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class LearningImpact(Enum):
    """Impact levels of learnings"""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TRANSFORMATIONAL = "transformational"


@dataclass
class LearningMetrics:
    """Metrics for a single learning"""
    learning_id: str
    quality_score: float  # 0-1
    impact_score: float  # 0-1
    application_rate: float  # How often applied
    validation_score: float  # Validation confidence
    reuse_count: int  # Times reused
    propagation_speed: float  # How fast it spreads
    retention_rate: float  # How well retained
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamLearningProfile:
    """Learning profile for a team"""
    team_id: str
    total_learnings: int
    learning_frequency: float  # Learnings per day
    avg_quality_score: float
    avg_impact_score: float
    learning_velocity: float  # Rate of learning improvement
    knowledge_retention: float  # How well team retains knowledge
    pattern_recognition: float  # Ability to identify patterns
    application_effectiveness: float  # How well learnings are applied
    learning_types: Dict[str, int]  # Count by type
    strengths: List[str]
    weaknesses: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningEvolution:
    """Tracks how learnings evolve over time"""
    original_learning_id: str
    evolution_chain: List[str]  # Chain of learning IDs
    refinements: int  # Number of refinements
    quality_improvement: float  # Improvement in quality
    impact_amplification: float  # Increase in impact
    time_to_maturity: timedelta  # Time to reach maturity
    current_state: str  # Current evolution state
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningROI:
    """Return on Investment for learnings"""
    learning_id: str
    investment_cost: float  # Time/resources invested
    value_generated: float  # Value created
    roi_percentage: float  # ROI %
    payback_period: timedelta  # Time to positive ROI
    affected_teams: int  # Number of teams benefited
    prevented_issues: int  # Issues prevented
    time_saved: float  # Hours saved
    quality_improvement: float  # Quality metric improvement
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningTrend:
    """Trend analysis for learning patterns"""
    period: str  # e.g., "weekly", "monthly"
    trend_direction: str  # "increasing", "stable", "decreasing"
    growth_rate: float  # Percentage growth
    quality_trend: str  # Quality direction
    impact_trend: str  # Impact direction
    emerging_topics: List[str]
    declining_topics: List[str]
    predictions: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningTracker:
    """
    Tracks and measures learning metrics across the organization
    """

    def __init__(self, storage_path: str = "./learning_metrics"):
        """
        Initialize the learning tracker
        
        Args:
            storage_path: Path to store metrics data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Metrics storage
        self.learning_metrics: Dict[str, LearningMetrics] = {}
        self.team_profiles: Dict[str, TeamLearningProfile] = {}
        self.learning_evolutions: Dict[str, LearningEvolution] = {}
        self.learning_rois: Dict[str, LearningROI] = {}
        
        # Time series data
        self.learning_timeline: deque = deque(maxlen=1000)  # Last 1000 learnings
        self.quality_history: deque = deque(maxlen=100)  # Quality scores over time
        self.impact_history: deque = deque(maxlen=100)  # Impact scores over time
        
        # Tracking windows
        self.tracking_window = timedelta(days=30)  # Default 30-day window
        
        # Thresholds
        self.quality_thresholds = {
            LearningQuality.POOR: 0.25,
            LearningQuality.FAIR: 0.5,
            LearningQuality.GOOD: 0.75,
            LearningQuality.EXCELLENT: 0.9
        }
        
        self.impact_thresholds = {
            LearningImpact.NEGLIGIBLE: 0.2,
            LearningImpact.LOW: 0.4,
            LearningImpact.MEDIUM: 0.6,
            LearningImpact.HIGH: 0.8,
            LearningImpact.TRANSFORMATIONAL: 0.95
        }
        
        self._lock = asyncio.Lock()
        self._load_existing_metrics()

    def _load_existing_metrics(self):
        """Load existing metrics from storage"""
        try:
            # Load learning metrics
            metrics_file = self.storage_path / "learning_metrics.json"
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    for metric_data in data:
                        metric = LearningMetrics(**metric_data)
                        self.learning_metrics[metric.learning_id] = metric
            
            # Load team profiles
            profiles_file = self.storage_path / "team_profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r') as f:
                    data = json.load(f)
                    for profile_data in data:
                        profile = TeamLearningProfile(**profile_data)
                        self.team_profiles[profile.team_id] = profile
        except Exception as e:
            print(f"Error loading existing metrics: {e}")

    async def track_learning(self, learning: Learning) -> LearningMetrics:
        """
        Track metrics for a new learning
        
        Args:
            learning: The learning to track
            
        Returns:
            Learning metrics
        """
        async with self._lock:
            # Calculate quality score
            quality_score = self._calculate_quality_score(learning)
            
            # Use existing impact score or calculate
            impact_score = learning.impact_score if learning.impact_score > 0 else self._calculate_impact_score(learning)
            
            # Create metrics
            metrics = LearningMetrics(
                learning_id=learning.id,
                quality_score=quality_score,
                impact_score=impact_score,
                application_rate=0.0,  # Will be updated as learning is applied
                validation_score=learning.confidence,
                reuse_count=0,
                propagation_speed=0.0,
                retention_rate=1.0,  # Starts at 100%
                metadata={
                    'team_id': learning.team_id,
                    'type': learning.type.value,
                    'priority': learning.priority.value,
                    'timestamp': learning.timestamp.isoformat()
                }
            )
            
            # Store metrics
            self.learning_metrics[learning.id] = metrics
            
            # Update timeline
            self.learning_timeline.append({
                'learning_id': learning.id,
                'timestamp': learning.timestamp,
                'team_id': learning.team_id,
                'quality': quality_score,
                'impact': impact_score
            })
            
            # Update history
            self.quality_history.append(quality_score)
            self.impact_history.append(impact_score)
            
            # Update team profile
            await self._update_team_profile(learning.team_id, metrics)
            
            # Save metrics
            await self._save_metrics()
            
            return metrics

    def _calculate_quality_score(self, learning: Learning) -> float:
        """Calculate quality score for a learning"""
        score = 0.0
        
        # Base score from confidence
        score += learning.confidence * 0.3
        
        # Priority contribution
        priority_scores = {
            LearningPriority.LOW: 0.1,
            LearningPriority.MEDIUM: 0.2,
            LearningPriority.HIGH: 0.3,
            LearningPriority.CRITICAL: 0.4
        }
        score += priority_scores.get(learning.priority, 0.1) * 0.2
        
        # Validation status
        if learning.validated:
            score += 0.2
        
        # Description quality (length as proxy)
        if len(learning.description) > 100:
            score += 0.1
        if len(learning.description) > 200:
            score += 0.1
        
        # Tags and context
        if len(learning.tags) >= 3:
            score += 0.05
        if learning.context:
            score += 0.05
        
        return min(1.0, score)

    def _calculate_impact_score(self, learning: Learning) -> float:
        """Calculate impact score for a learning"""
        score = 0.0
        
        # Type-based impact
        type_impacts = {
            LearningType.FAILURE: 0.3,  # Failures have high impact
            LearningType.SUCCESS: 0.25,
            LearningType.INNOVATION: 0.35,
            LearningType.STRATEGIC: 0.3,
            LearningType.IMPROVEMENT: 0.2,
            LearningType.TECHNICAL: 0.15,
            LearningType.PROCESS: 0.15,
            LearningType.BEHAVIORAL: 0.2,
            LearningType.OPERATIONAL: 0.15
        }
        score += type_impacts.get(learning.type, 0.1)
        
        # Priority impact
        priority_impacts = {
            LearningPriority.LOW: 0.1,
            LearningPriority.MEDIUM: 0.2,
            LearningPriority.HIGH: 0.3,
            LearningPriority.CRITICAL: 0.4
        }
        score += priority_impacts.get(learning.priority, 0.1)
        
        # Applied count impact
        if learning.applied_count > 0:
            score += min(0.3, learning.applied_count * 0.1)
        
        return min(1.0, score)

    async def _update_team_profile(self, team_id: str, metrics: LearningMetrics):
        """Update team learning profile with new metrics"""
        if team_id not in self.team_profiles:
            self.team_profiles[team_id] = TeamLearningProfile(
                team_id=team_id,
                total_learnings=0,
                learning_frequency=0.0,
                avg_quality_score=0.0,
                avg_impact_score=0.0,
                learning_velocity=0.0,
                knowledge_retention=1.0,
                pattern_recognition=0.5,
                application_effectiveness=0.5,
                learning_types={},
                strengths=[],
                weaknesses=[]
            )
        
        profile = self.team_profiles[team_id]
        profile.total_learnings += 1
        
        # Update averages
        profile.avg_quality_score = (profile.avg_quality_score * (profile.total_learnings - 1) + metrics.quality_score) / profile.total_learnings
        profile.avg_impact_score = (profile.avg_impact_score * (profile.total_learnings - 1) + metrics.impact_score) / profile.total_learnings
        
        # Update learning types
        learning_type = metrics.metadata.get('type', 'unknown')
        profile.learning_types[learning_type] = profile.learning_types.get(learning_type, 0) + 1
        
        # Calculate learning frequency (learnings per day)
        team_learnings = [l for l in self.learning_timeline if l.get('team_id') == team_id]
        if len(team_learnings) >= 2:
            time_span = (team_learnings[-1]['timestamp'] - team_learnings[0]['timestamp']).total_seconds() / 86400
            if time_span > 0:
                profile.learning_frequency = len(team_learnings) / time_span
        
        # Identify strengths and weaknesses
        await self._identify_team_characteristics(profile)

    async def _identify_team_characteristics(self, profile: TeamLearningProfile):
        """Identify team strengths and weaknesses"""
        strengths = []
        weaknesses = []
        
        # Quality assessment
        if profile.avg_quality_score > 0.8:
            strengths.append("High quality learnings")
        elif profile.avg_quality_score < 0.4:
            weaknesses.append("Low quality learnings")
        
        # Impact assessment
        if profile.avg_impact_score > 0.7:
            strengths.append("High impact discoveries")
        elif profile.avg_impact_score < 0.3:
            weaknesses.append("Low impact learnings")
        
        # Frequency assessment
        if profile.learning_frequency > 1.0:
            strengths.append("Frequent learning capture")
        elif profile.learning_frequency < 0.2:
            weaknesses.append("Infrequent learning capture")
        
        # Type diversity
        if len(profile.learning_types) >= 5:
            strengths.append("Diverse learning types")
        elif len(profile.learning_types) <= 2:
            weaknesses.append("Limited learning diversity")
        
        profile.strengths = strengths
        profile.weaknesses = weaknesses

    async def track_learning_application(self, learning_id: str, team_id: str, success: bool = True):
        """
        Track when a learning is applied by a team
        
        Args:
            learning_id: ID of the learning applied
            team_id: ID of the team applying it
            success: Whether the application was successful
        """
        async with self._lock:
            if learning_id not in self.learning_metrics:
                return
            
            metrics = self.learning_metrics[learning_id]
            
            # Update application rate
            metrics.reuse_count += 1
            if success:
                metrics.application_rate = min(1.0, metrics.application_rate + 0.1)
            
            # Calculate propagation speed (teams reached per day)
            first_timestamp = datetime.fromisoformat(metrics.metadata['timestamp'])
            days_elapsed = (datetime.now() - first_timestamp).days or 1
            metrics.propagation_speed = metrics.reuse_count / days_elapsed
            
            await self._save_metrics()

    async def track_learning_evolution(self, 
                                     original_id: str,
                                     new_id: str,
                                     refinement_type: str = "improvement") -> LearningEvolution:
        """
        Track how a learning evolves into new learnings
        
        Args:
            original_id: Original learning ID
            new_id: New/evolved learning ID
            refinement_type: Type of refinement
            
        Returns:
            Learning evolution tracking
        """
        async with self._lock:
            if original_id in self.learning_evolutions:
                evolution = self.learning_evolutions[original_id]
                evolution.evolution_chain.append(new_id)
                evolution.refinements += 1
            else:
                evolution = LearningEvolution(
                    original_learning_id=original_id,
                    evolution_chain=[original_id, new_id],
                    refinements=1,
                    quality_improvement=0.0,
                    impact_amplification=0.0,
                    time_to_maturity=timedelta(days=0),
                    current_state=refinement_type,
                    metadata={'last_update': datetime.now().isoformat()}
                )
                self.learning_evolutions[original_id] = evolution
            
            # Calculate improvements if metrics exist
            if original_id in self.learning_metrics and new_id in self.learning_metrics:
                original_metrics = self.learning_metrics[original_id]
                new_metrics = self.learning_metrics[new_id]
                
                evolution.quality_improvement = new_metrics.quality_score - original_metrics.quality_score
                evolution.impact_amplification = new_metrics.impact_score - original_metrics.impact_score
            
            await self._save_evolutions()
            return evolution

    async def calculate_learning_roi(self, 
                                   learning_id: str,
                                   time_invested: float,
                                   teams_affected: List[str],
                                   issues_prevented: int = 0,
                                   time_saved_hours: float = 0.0) -> LearningROI:
        """
        Calculate ROI for a learning
        
        Args:
            learning_id: Learning ID
            time_invested: Hours invested in creating/validating learning
            teams_affected: List of teams that benefited
            issues_prevented: Number of issues prevented
            time_saved_hours: Total hours saved across teams
            
        Returns:
            Learning ROI calculation
        """
        async with self._lock:
            # Calculate value generated (simplified model)
            value_per_team = 100  # Base value per team
            value_per_issue = 500  # Value per prevented issue
            value_per_hour = 50  # Value per hour saved
            
            value_generated = (
                len(teams_affected) * value_per_team +
                issues_prevented * value_per_issue +
                time_saved_hours * value_per_hour
            )
            
            investment_cost = time_invested * 75  # Cost per hour
            
            roi_percentage = ((value_generated - investment_cost) / investment_cost * 100) if investment_cost > 0 else 0
            
            # Calculate payback period
            if value_generated > investment_cost:
                days_to_payback = 30 * (investment_cost / value_generated)  # Rough estimate
                payback_period = timedelta(days=days_to_payback)
            else:
                payback_period = timedelta(days=365)  # Not yet profitable
            
            # Get quality improvement if metrics exist
            quality_improvement = 0.0
            if learning_id in self.learning_metrics:
                metrics = self.learning_metrics[learning_id]
                quality_improvement = metrics.quality_score
            
            roi = LearningROI(
                learning_id=learning_id,
                investment_cost=investment_cost,
                value_generated=value_generated,
                roi_percentage=roi_percentage,
                payback_period=payback_period,
                affected_teams=len(teams_affected),
                prevented_issues=issues_prevented,
                time_saved=time_saved_hours,
                quality_improvement=quality_improvement,
                metadata={
                    'calculated_at': datetime.now().isoformat(),
                    'teams': teams_affected
                }
            )
            
            self.learning_rois[learning_id] = roi
            await self._save_rois()
            
            return roi

    async def analyze_learning_trends(self, 
                                    period: str = "weekly",
                                    lookback_days: int = 30) -> LearningTrend:
        """
        Analyze learning trends over time
        
        Args:
            period: Analysis period ("daily", "weekly", "monthly")
            lookback_days: Days to look back
            
        Returns:
            Learning trend analysis
        """
        async with self._lock:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            
            # Filter recent learnings
            recent_learnings = [l for l in self.learning_timeline 
                              if l['timestamp'] > cutoff_date]
            
            if not recent_learnings:
                return LearningTrend(
                    period=period,
                    trend_direction="stable",
                    growth_rate=0.0,
                    quality_trend="stable",
                    impact_trend="stable",
                    emerging_topics=[],
                    declining_topics=[],
                    predictions={}
                )
            
            # Calculate growth rate
            if period == "weekly":
                period_days = 7
            elif period == "monthly":
                period_days = 30
            else:  # daily
                period_days = 1
            
            periods = lookback_days // period_days
            if periods < 2:
                periods = 2
            
            # Group learnings by period
            period_counts = defaultdict(int)
            period_quality = defaultdict(list)
            period_impact = defaultdict(list)
            
            for learning in recent_learnings:
                days_ago = (datetime.now() - learning['timestamp']).days
                period_idx = days_ago // period_days
                period_counts[period_idx] += 1
                period_quality[period_idx].append(learning['quality'])
                period_impact[period_idx].append(learning['impact'])
            
            # Calculate trends
            counts = [period_counts.get(i, 0) for i in range(periods)]
            growth_rate = 0.0
            if len(counts) >= 2 and counts[-2] > 0:
                growth_rate = ((counts[-1] - counts[-2]) / counts[-2]) * 100
            
            # Determine trend direction
            if growth_rate > 10:
                trend_direction = "increasing"
            elif growth_rate < -10:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            
            # Quality and impact trends
            quality_trend = self._calculate_metric_trend(period_quality)
            impact_trend = self._calculate_metric_trend(period_impact)
            
            # Identify emerging and declining topics (simplified)
            recent_tags = defaultdict(int)
            older_tags = defaultdict(int)
            
            midpoint = cutoff_date + timedelta(days=lookback_days/2)
            
            # This would need actual tag data from learnings
            emerging_topics = []
            declining_topics = []
            
            # Predictions
            predictions = {
                'next_period_estimate': int(counts[-1] * (1 + growth_rate/100)) if counts else 0,
                'quality_forecast': 'improving' if quality_trend == 'increasing' else 'stable',
                'impact_forecast': 'improving' if impact_trend == 'increasing' else 'stable'
            }
            
            trend = LearningTrend(
                period=period,
                trend_direction=trend_direction,
                growth_rate=growth_rate,
                quality_trend=quality_trend,
                impact_trend=impact_trend,
                emerging_topics=emerging_topics,
                declining_topics=declining_topics,
                predictions=predictions,
                metadata={
                    'analysis_date': datetime.now().isoformat(),
                    'lookback_days': lookback_days,
                    'data_points': len(recent_learnings)
                }
            )
            
            return trend

    def _calculate_metric_trend(self, period_metrics: Dict[int, List[float]]) -> str:
        """Calculate trend for a metric over periods"""
        if not period_metrics:
            return "stable"
        
        # Calculate average for each period
        period_avgs = {}
        for period, values in period_metrics.items():
            if values:
                period_avgs[period] = statistics.mean(values)
        
        if len(period_avgs) < 2:
            return "stable"
        
        # Compare recent to older
        sorted_periods = sorted(period_avgs.keys())
        recent_avg = statistics.mean([period_avgs[p] for p in sorted_periods[:len(sorted_periods)//2]])
        older_avg = statistics.mean([period_avgs[p] for p in sorted_periods[len(sorted_periods)//2:]])
        
        change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        if change > 10:
            return "increasing"
        elif change < -10:
            return "decreasing"
        else:
            return "stable"

    def get_team_profile(self, team_id: str) -> Optional[TeamLearningProfile]:
        """Get learning profile for a team"""
        return self.team_profiles.get(team_id)

    def get_all_team_profiles(self) -> Dict[str, TeamLearningProfile]:
        """Get all team learning profiles"""
        return self.team_profiles.copy()

    def get_learning_metrics(self, learning_id: str) -> Optional[LearningMetrics]:
        """Get metrics for a specific learning"""
        return self.learning_metrics.get(learning_id)

    def get_top_learnings(self, 
                         metric: str = "quality",
                         limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get top learnings by a specific metric
        
        Args:
            metric: Metric to sort by ("quality", "impact", "reuse")
            limit: Number of top learnings to return
            
        Returns:
            List of (learning_id, metric_value) tuples
        """
        if metric == "quality":
            sorted_learnings = sorted(
                self.learning_metrics.items(),
                key=lambda x: x[1].quality_score,
                reverse=True
            )
        elif metric == "impact":
            sorted_learnings = sorted(
                self.learning_metrics.items(),
                key=lambda x: x[1].impact_score,
                reverse=True
            )
        elif metric == "reuse":
            sorted_learnings = sorted(
                self.learning_metrics.items(),
                key=lambda x: x[1].reuse_count,
                reverse=True
            )
        else:
            return []
        
        return [(lid, getattr(metrics, f"{metric}_score" if metric != "reuse" else "reuse_count")) 
                for lid, metrics in sorted_learnings[:limit]]

    def get_learning_quality(self, learning_id: str) -> Optional[LearningQuality]:
        """Get quality classification for a learning"""
        if learning_id not in self.learning_metrics:
            return None
        
        score = self.learning_metrics[learning_id].quality_score
        
        for quality, threshold in sorted(self.quality_thresholds.items(), 
                                        key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return quality
        
        return LearningQuality.POOR

    def get_learning_impact(self, learning_id: str) -> Optional[LearningImpact]:
        """Get impact classification for a learning"""
        if learning_id not in self.learning_metrics:
            return None
        
        score = self.learning_metrics[learning_id].impact_score
        
        for impact, threshold in sorted(self.impact_thresholds.items(), 
                                       key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return impact
        
        return LearningImpact.NEGLIGIBLE

    async def calculate_team_learning_velocity(self, team_id: str) -> float:
        """
        Calculate learning velocity (improvement rate) for a team
        
        Args:
            team_id: Team ID
            
        Returns:
            Learning velocity score
        """
        async with self._lock:
            team_learnings = [l for l in self.learning_timeline if l.get('team_id') == team_id]
            
            if len(team_learnings) < 2:
                return 0.0
            
            # Sort by timestamp
            team_learnings.sort(key=lambda x: x['timestamp'])
            
            # Calculate quality improvement over time
            early_quality = statistics.mean([l['quality'] for l in team_learnings[:len(team_learnings)//3]])
            recent_quality = statistics.mean([l['quality'] for l in team_learnings[-len(team_learnings)//3:]])
            
            quality_improvement = recent_quality - early_quality
            
            # Calculate time span in days
            time_span = (team_learnings[-1]['timestamp'] - team_learnings[0]['timestamp']).days or 1
            
            # Velocity is improvement per day
            velocity = quality_improvement / time_span * 100
            
            # Update team profile
            if team_id in self.team_profiles:
                self.team_profiles[team_id].learning_velocity = velocity
            
            return velocity

    async def _save_metrics(self):
        """Save metrics to persistent storage"""
        metrics_file = self.storage_path / "learning_metrics.json"
        metrics_data = [asdict(metrics) for metrics in self.learning_metrics.values()]
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        # Save team profiles
        profiles_file = self.storage_path / "team_profiles.json"
        profiles_data = [asdict(profile) for profile in self.team_profiles.values()]
        
        with open(profiles_file, 'w') as f:
            json.dump(profiles_data, f, indent=2)

    async def _save_evolutions(self):
        """Save learning evolutions to storage"""
        evolutions_file = self.storage_path / "learning_evolutions.json"
        evolutions_data = []
        
        for evolution in self.learning_evolutions.values():
            evo_dict = asdict(evolution)
            evo_dict['time_to_maturity'] = evolution.time_to_maturity.total_seconds()
            evolutions_data.append(evo_dict)
        
        with open(evolutions_file, 'w') as f:
            json.dump(evolutions_data, f, indent=2)

    async def _save_rois(self):
        """Save ROI calculations to storage"""
        rois_file = self.storage_path / "learning_rois.json"
        rois_data = []
        
        for roi in self.learning_rois.values():
            roi_dict = asdict(roi)
            roi_dict['payback_period'] = roi.payback_period.total_seconds()
            rois_data.append(roi_dict)
        
        with open(rois_file, 'w') as f:
            json.dump(rois_data, f, indent=2)

    def export_metrics_report(self, format: str = "markdown") -> str:
        """
        Export metrics report in various formats
        
        Args:
            format: Export format ("markdown", "json", "csv")
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return self._export_json_report()
        elif format == "csv":
            return self._export_csv_report()
        else:  # markdown
            return self._export_markdown_report()

    def _export_markdown_report(self) -> str:
        """Export metrics as markdown report"""
        md = "# Learning Metrics Report\n\n"
        md += f"*Generated: {datetime.now().isoformat()}*\n\n"
        
        # Summary statistics
        md += "## Summary\n"
        md += f"- Total Learnings Tracked: {len(self.learning_metrics)}\n"
        md += f"- Teams with Profiles: {len(self.team_profiles)}\n"
        md += f"- Learning Evolutions: {len(self.learning_evolutions)}\n"
        md += f"- ROI Calculations: {len(self.learning_rois)}\n\n"
        
        # Average metrics
        if self.learning_metrics:
            avg_quality = statistics.mean([m.quality_score for m in self.learning_metrics.values()])
            avg_impact = statistics.mean([m.impact_score for m in self.learning_metrics.values()])
            avg_reuse = statistics.mean([m.reuse_count for m in self.learning_metrics.values()])
            
            md += "## Average Metrics\n"
            md += f"- Average Quality Score: {avg_quality:.2f}\n"
            md += f"- Average Impact Score: {avg_impact:.2f}\n"
            md += f"- Average Reuse Count: {avg_reuse:.1f}\n\n"
        
        # Top learnings
        md += "## Top Quality Learnings\n"
        top_quality = self.get_top_learnings("quality", 5)
        for learning_id, score in top_quality:
            md += f"- {learning_id}: {score:.2f}\n"
        md += "\n"
        
        md += "## Top Impact Learnings\n"
        top_impact = self.get_top_learnings("impact", 5)
        for learning_id, score in top_impact:
            md += f"- {learning_id}: {score:.2f}\n"
        md += "\n"
        
        # Team profiles
        if self.team_profiles:
            md += "## Team Learning Profiles\n"
            for team_id, profile in list(self.team_profiles.items())[:5]:
                md += f"### {team_id}\n"
                md += f"- Total Learnings: {profile.total_learnings}\n"
                md += f"- Learning Frequency: {profile.learning_frequency:.2f} per day\n"
                md += f"- Avg Quality: {profile.avg_quality_score:.2f}\n"
                md += f"- Avg Impact: {profile.avg_impact_score:.2f}\n"
                if profile.strengths:
                    md += f"- Strengths: {', '.join(profile.strengths)}\n"
                if profile.weaknesses:
                    md += f"- Weaknesses: {', '.join(profile.weaknesses)}\n"
                md += "\n"
        
        # ROI highlights
        if self.learning_rois:
            md += "## Top ROI Learnings\n"
            sorted_rois = sorted(self.learning_rois.values(), 
                               key=lambda x: x.roi_percentage, reverse=True)[:5]
            for roi in sorted_rois:
                md += f"- {roi.learning_id}: {roi.roi_percentage:.1f}% ROI\n"
            md += "\n"
        
        return md

    def _export_json_report(self) -> str:
        """Export metrics as JSON"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_learnings': len(self.learning_metrics),
                'total_teams': len(self.team_profiles),
                'total_evolutions': len(self.learning_evolutions),
                'total_rois': len(self.learning_rois)
            },
            'metrics': [asdict(m) for m in list(self.learning_metrics.values())[:100]],
            'team_profiles': [asdict(p) for p in self.team_profiles.values()],
            'top_quality': self.get_top_learnings("quality", 10),
            'top_impact': self.get_top_learnings("impact", 10),
            'top_reuse': self.get_top_learnings("reuse", 10)
        }
        return json.dumps(data, indent=2)

    def _export_csv_report(self) -> str:
        """Export metrics as CSV"""
        csv_lines = []
        csv_lines.append("Learning ID,Quality Score,Impact Score,Reuse Count,Application Rate,Validation Score")
        
        for learning_id, metrics in self.learning_metrics.items():
            csv_lines.append(f"{learning_id},{metrics.quality_score:.2f},{metrics.impact_score:.2f},"
                           f"{metrics.reuse_count},{metrics.application_rate:.2f},{metrics.validation_score:.2f}")
        
        return "\n".join(csv_lines)

    def get_tracker_stats(self) -> Dict[str, Any]:
        """Get current tracker statistics"""
        stats = {
            'total_learnings_tracked': len(self.learning_metrics),
            'total_teams': len(self.team_profiles),
            'total_evolutions': len(self.learning_evolutions),
            'total_rois': len(self.learning_rois),
            'timeline_entries': len(self.learning_timeline)
        }
        
        if self.quality_history:
            stats['avg_recent_quality'] = statistics.mean(list(self.quality_history)[-10:])
        
        if self.impact_history:
            stats['avg_recent_impact'] = statistics.mean(list(self.impact_history)[-10:])
        
        return stats


# Standalone test
if __name__ == "__main__":
    async def test_learning_tracker():
        """Test the learning tracker"""
        tracker = LearningTracker()
        
        # Create sample learning
        learning = Learning(
            id="test_learning_001",
            team_id="team_alpha",
            type=LearningType.TECHNICAL,
            priority=LearningPriority.HIGH,
            title="Optimized database queries",
            description="Implementing query caching reduced database load by 60% and improved response times",
            context={"area": "backend", "component": "database"},
            tags=["performance", "database", "optimization"],
            source="sprint_review",
            timestamp=datetime.now(),
            impact_score=0.8,
            confidence=0.9,
            validated=True
        )
        
        # Track the learning
        print("Tracking learning...")
        metrics = await tracker.track_learning(learning)
        print(f"Quality Score: {metrics.quality_score:.2f}")
        print(f"Impact Score: {metrics.impact_score:.2f}")
        
        # Simulate application
        print("\nSimulating learning application...")
        await tracker.track_learning_application(learning.id, "team_beta", success=True)
        await tracker.track_learning_application(learning.id, "team_gamma", success=True)
        
        # Calculate ROI
        print("\nCalculating ROI...")
        roi = await tracker.calculate_learning_roi(
            learning.id,
            time_invested=4.0,  # 4 hours
            teams_affected=["team_beta", "team_gamma"],
            issues_prevented=2,
            time_saved_hours=20.0
        )
        print(f"ROI: {roi.roi_percentage:.1f}%")
        print(f"Value Generated: ${roi.value_generated:.2f}")
        
        # Get team profile
        print("\nTeam Profile:")
        profile = tracker.get_team_profile("team_alpha")
        if profile:
            print(f"Team: {profile.team_id}")
            print(f"Total Learnings: {profile.total_learnings}")
            print(f"Avg Quality: {profile.avg_quality_score:.2f}")
            print(f"Strengths: {', '.join(profile.strengths) if profile.strengths else 'None yet'}")
        
        # Analyze trends
        print("\nAnalyzing trends...")
        trend = await tracker.analyze_learning_trends(period="weekly", lookback_days=30)
        print(f"Trend Direction: {trend.trend_direction}")
        print(f"Growth Rate: {trend.growth_rate:.1f}%")
        
        # Get top learnings
        print("\nTop Quality Learnings:")
        top_learnings = tracker.get_top_learnings("quality", 3)
        for lid, score in top_learnings:
            print(f"  {lid}: {score:.2f}")
        
        # Export report
        print("\nExporting markdown report...")
        report = tracker.export_metrics_report("markdown")
        print(report[:500] + "...")
        
        # Get tracker stats
        print("\nTracker Statistics:")
        stats = tracker.get_tracker_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Learning tracker test completed successfully!")
    
    # Run the test
    asyncio.run(test_learning_tracker())