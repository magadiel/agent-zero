"""
Metrics Dashboard Module
Real-time metrics visualization and reporting for agile AI teams.
Part of the Agile AI Company framework.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import our metrics modules
from .agile_metrics import AgileMetrics, MetricType, TrendDirection, TeamMetrics
from .velocity_tracker import VelocityTracker, VelocityTrend, VelocityPrediction

class DashboardView(Enum):
    """Available dashboard views"""
    EXECUTIVE = "executive"          # High-level overview
    TEAM_PERFORMANCE = "team_performance"  # Detailed team metrics
    VELOCITY = "velocity"            # Velocity tracking and predictions
    QUALITY = "quality"              # Quality metrics
    SPRINT = "sprint"               # Current sprint status
    COMPARATIVE = "comparative"     # Team comparisons
    HISTORICAL = "historical"       # Historical trends

@dataclass
class DashboardWidget:
    """Individual dashboard widget"""
    widget_id: str
    title: str
    type: str  # "chart", "metric", "table", "progress"
    data: Any
    last_updated: datetime
    refresh_interval: int  # seconds

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    view: DashboardView
    team_ids: List[str]
    period_days: int
    auto_refresh: bool
    refresh_interval: int  # seconds
    widgets: List[str]  # Widget IDs to display

class MetricsDashboard:
    """
    Comprehensive metrics dashboard for agile AI teams.
    Provides real-time visualization and reporting capabilities.
    """
    
    def __init__(self, agile_metrics: AgileMetrics, velocity_tracker: VelocityTracker):
        self.agile_metrics = agile_metrics
        self.velocity_tracker = velocity_tracker
        self.widgets: Dict[str, DashboardWidget] = {}
        self.configs: Dict[str, DashboardConfig] = {}
        self._initialize_default_widgets()
        
    def _initialize_default_widgets(self):
        """Initialize default dashboard widgets"""
        # Executive widgets
        self.register_widget("health_score", "Team Health Score", "metric", 60)
        self.register_widget("velocity_trend", "Velocity Trend", "chart", 300)
        self.register_widget("sprint_progress", "Sprint Progress", "progress", 60)
        self.register_widget("quality_metrics", "Quality Metrics", "table", 300)
        
        # Team performance widgets
        self.register_widget("team_velocity", "Team Velocity", "chart", 300)
        self.register_widget("cycle_time", "Cycle Time", "chart", 300)
        self.register_widget("throughput", "Throughput", "metric", 300)
        self.register_widget("commitment_reliability", "Commitment Reliability", "metric", 300)
        
        # Quality widgets
        self.register_widget("defect_rate", "Defect Rate", "chart", 600)
        self.register_widget("rework_rate", "Rework Rate", "chart", 600)
        self.register_widget("code_quality", "Code Quality", "metric", 600)
        
        # Comparative widgets
        self.register_widget("team_comparison", "Team Comparison", "table", 300)
        self.register_widget("velocity_comparison", "Velocity Comparison", "chart", 300)
        
    def register_widget(self, widget_id: str, title: str, widget_type: str, 
                       refresh_interval: int):
        """Register a new dashboard widget"""
        self.widgets[widget_id] = DashboardWidget(
            widget_id=widget_id,
            title=title,
            type=widget_type,
            data=None,
            last_updated=datetime.now(),
            refresh_interval=refresh_interval
        )
    
    def create_dashboard(self, view: DashboardView, team_ids: List[str],
                        period_days: int = 30) -> Dict[str, Any]:
        """Create a dashboard view with specified configuration"""
        dashboard = {
            'view': view.value,
            'team_ids': team_ids,
            'period': f"Last {period_days} days",
            'generated_at': datetime.now().isoformat(),
            'widgets': {}
        }
        
        if view == DashboardView.EXECUTIVE:
            dashboard['widgets'] = self._create_executive_dashboard(team_ids, period_days)
        elif view == DashboardView.TEAM_PERFORMANCE:
            dashboard['widgets'] = self._create_team_performance_dashboard(team_ids, period_days)
        elif view == DashboardView.VELOCITY:
            dashboard['widgets'] = self._create_velocity_dashboard(team_ids, period_days)
        elif view == DashboardView.QUALITY:
            dashboard['widgets'] = self._create_quality_dashboard(team_ids, period_days)
        elif view == DashboardView.SPRINT:
            dashboard['widgets'] = self._create_sprint_dashboard(team_ids)
        elif view == DashboardView.COMPARATIVE:
            dashboard['widgets'] = self._create_comparative_dashboard(team_ids, period_days)
        elif view == DashboardView.HISTORICAL:
            dashboard['widgets'] = self._create_historical_dashboard(team_ids, period_days)
            
        return dashboard
    
    def _create_executive_dashboard(self, team_ids: List[str], period_days: int) -> Dict:
        """Create executive summary dashboard"""
        widgets = {}
        
        # Overall health scores
        health_scores = {}
        for team_id in team_ids:
            team_metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            health_scores[team_id] = {
                'score': team_metrics.overall_health_score,
                'trend': self._get_health_trend(team_id)
            }
        
        widgets['health_scores'] = {
            'title': 'Team Health Scores',
            'type': 'metric_group',
            'data': health_scores
        }
        
        # Aggregate velocity
        total_velocity = 0
        for team_id in team_ids:
            velocity = self.velocity_tracker.calculate_average_velocity(team_id, 3)
            total_velocity += velocity
            
        widgets['total_velocity'] = {
            'title': 'Organization Velocity',
            'type': 'metric',
            'data': {
                'value': total_velocity,
                'unit': 'points/sprint',
                'change': self._calculate_velocity_change(team_ids)
            }
        }
        
        # Quality overview
        avg_defect_rate = 0
        avg_rework_rate = 0
        count = 0
        
        for team_id in team_ids:
            team_metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            if team_metrics.defect_rate:
                avg_defect_rate += team_metrics.defect_rate.current_value
                count += 1
            if team_metrics.rework_rate:
                avg_rework_rate += team_metrics.rework_rate.current_value
                
        if count > 0:
            avg_defect_rate /= count
            avg_rework_rate /= count
            
        widgets['quality_overview'] = {
            'title': 'Quality Metrics',
            'type': 'metrics',
            'data': {
                'defect_rate': f"{avg_defect_rate:.2f} per story",
                'rework_rate': f"{avg_rework_rate:.1f}%"
            }
        }
        
        # Key insights
        insights = self._generate_executive_insights(team_ids, period_days)
        widgets['insights'] = {
            'title': 'Key Insights',
            'type': 'list',
            'data': insights
        }
        
        return widgets
    
    def _create_team_performance_dashboard(self, team_ids: List[str], 
                                          period_days: int) -> Dict:
        """Create detailed team performance dashboard"""
        widgets = {}
        
        for team_id in team_ids:
            team_metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            
            # Velocity chart
            velocity_data = self._get_velocity_chart_data(team_id, period_days)
            widgets[f'{team_id}_velocity'] = {
                'title': f'{team_id} Velocity',
                'type': 'line_chart',
                'data': velocity_data
            }
            
            # Cycle time distribution
            if team_metrics.cycle_time:
                widgets[f'{team_id}_cycle_time'] = {
                    'title': f'{team_id} Cycle Time',
                    'type': 'histogram',
                    'data': {
                        'current': team_metrics.cycle_time.current_value,
                        'average': team_metrics.cycle_time.average,
                        'trend': team_metrics.cycle_time.trend.value
                    }
                }
            
            # Throughput
            if team_metrics.throughput:
                widgets[f'{team_id}_throughput'] = {
                    'title': f'{team_id} Throughput',
                    'type': 'metric',
                    'data': {
                        'value': team_metrics.throughput.current_value,
                        'unit': 'stories/day',
                        'change': team_metrics.throughput.change_percentage
                    }
                }
            
            # Commitment reliability
            if team_metrics.commitment_reliability:
                widgets[f'{team_id}_commitment'] = {
                    'title': f'{team_id} Commitment Reliability',
                    'type': 'gauge',
                    'data': {
                        'value': team_metrics.commitment_reliability.current_value,
                        'target': 90,
                        'status': self._get_reliability_status(
                            team_metrics.commitment_reliability.current_value
                        )
                    }
                }
        
        return widgets
    
    def _create_velocity_dashboard(self, team_ids: List[str], period_days: int) -> Dict:
        """Create velocity-focused dashboard"""
        widgets = {}
        
        for team_id in team_ids:
            # Velocity trend
            trend = self.velocity_tracker.get_velocity_trend(team_id)
            widgets[f'{team_id}_trend'] = {
                'title': f'{team_id} Velocity Trend',
                'type': 'trend',
                'data': {
                    'direction': trend.trend_direction,
                    'strength': trend.trend_strength,
                    'average': trend.average_velocity,
                    'stability': trend.stability_score,
                    'maturity': trend.maturity_level
                }
            }
            
            # Velocity prediction
            prediction = self.velocity_tracker.predict_velocity(team_id)
            widgets[f'{team_id}_prediction'] = {
                'title': f'{team_id} Velocity Prediction',
                'type': 'prediction',
                'data': {
                    'predicted': prediction.predicted_velocity,
                    'confidence': prediction.confidence.value,
                    'range': [prediction.lower_bound, prediction.upper_bound],
                    'recommendation': prediction.recommendation
                }
            }
            
            # Commitment analysis
            analysis = self.velocity_tracker.analyze_commitment_vs_completion(team_id)
            if analysis:
                widgets[f'{team_id}_commitment_analysis'] = {
                    'title': f'{team_id} Commitment Analysis',
                    'type': 'comparison',
                    'data': analysis
                }
            
            # Rolling average
            rolling_avg = self.velocity_tracker.calculate_rolling_average(team_id, 3)
            if rolling_avg:
                widgets[f'{team_id}_rolling_avg'] = {
                    'title': f'{team_id} Rolling Average (3 sprints)',
                    'type': 'line_chart',
                    'data': {
                        'values': rolling_avg,
                        'current': rolling_avg[-1] if rolling_avg else 0
                    }
                }
        
        return widgets
    
    def _create_quality_dashboard(self, team_ids: List[str], period_days: int) -> Dict:
        """Create quality-focused dashboard"""
        widgets = {}
        
        for team_id in team_ids:
            team_metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            
            # Defect rate trend
            if team_metrics.defect_rate:
                widgets[f'{team_id}_defect_rate'] = {
                    'title': f'{team_id} Defect Rate',
                    'type': 'area_chart',
                    'data': {
                        'current': team_metrics.defect_rate.current_value,
                        'average': team_metrics.defect_rate.average,
                        'trend': team_metrics.defect_rate.trend.value,
                        'target': 0.1  # Target: < 0.1 defects per story
                    }
                }
            
            # Rework rate
            if team_metrics.rework_rate:
                widgets[f'{team_id}_rework_rate'] = {
                    'title': f'{team_id} Rework Rate',
                    'type': 'bar_chart',
                    'data': {
                        'current': team_metrics.rework_rate.current_value,
                        'average': team_metrics.rework_rate.average,
                        'acceptable_threshold': 10  # 10% rework rate threshold
                    }
                }
            
            # Quality score calculation
            quality_score = self._calculate_quality_score(team_metrics)
            widgets[f'{team_id}_quality_score'] = {
                'title': f'{team_id} Quality Score',
                'type': 'score',
                'data': {
                    'score': quality_score,
                    'grade': self._get_quality_grade(quality_score),
                    'components': {
                        'defects': team_metrics.defect_rate.current_value if team_metrics.defect_rate else 0,
                        'rework': team_metrics.rework_rate.current_value if team_metrics.rework_rate else 0
                    }
                }
            }
        
        return widgets
    
    def _create_sprint_dashboard(self, team_ids: List[str]) -> Dict:
        """Create current sprint status dashboard"""
        widgets = {}
        
        # This would integrate with sprint manager
        # For now, we'll create a placeholder structure
        for team_id in team_ids:
            widgets[f'{team_id}_sprint_progress'] = {
                'title': f'{team_id} Sprint Progress',
                'type': 'burndown',
                'data': {
                    'day': 5,
                    'total_days': 10,
                    'completed_points': 25,
                    'remaining_points': 35,
                    'ideal_remaining': 30,
                    'status': 'at_risk' if 35 > 30 else 'on_track'
                }
            }
            
            widgets[f'{team_id}_sprint_health'] = {
                'title': f'{team_id} Sprint Health',
                'type': 'indicators',
                'data': {
                    'velocity_on_track': True,
                    'blockers': 2,
                    'at_risk_stories': 1,
                    'team_morale': 'good'
                }
            }
        
        return widgets
    
    def _create_comparative_dashboard(self, team_ids: List[str], period_days: int) -> Dict:
        """Create team comparison dashboard"""
        widgets = {}
        
        # Collect metrics for all teams
        team_data = []
        for team_id in team_ids:
            metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            trend = self.velocity_tracker.get_velocity_trend(team_id)
            
            team_data.append({
                'team_id': team_id,
                'health_score': metrics.overall_health_score,
                'velocity': trend.average_velocity,
                'stability': trend.stability_score,
                'maturity': trend.maturity_level,
                'defect_rate': metrics.defect_rate.current_value if metrics.defect_rate else 0,
                'cycle_time': metrics.cycle_time.current_value if metrics.cycle_time else 0
            })
        
        # Comparison table
        widgets['team_comparison_table'] = {
            'title': 'Team Comparison',
            'type': 'table',
            'data': {
                'headers': ['Team', 'Health', 'Velocity', 'Stability', 'Maturity', 'Defects', 'Cycle Time'],
                'rows': team_data
            }
        }
        
        # Velocity comparison chart
        widgets['velocity_comparison'] = {
            'title': 'Velocity Comparison',
            'type': 'bar_chart',
            'data': {
                'teams': [t['team_id'] for t in team_data],
                'velocities': [t['velocity'] for t in team_data]
            }
        }
        
        # Health score comparison
        widgets['health_comparison'] = {
            'title': 'Team Health Comparison',
            'type': 'radar_chart',
            'data': {
                'teams': [t['team_id'] for t in team_data],
                'scores': [t['health_score'] for t in team_data]
            }
        }
        
        # Rankings
        rankings = self._calculate_team_rankings(team_data)
        widgets['team_rankings'] = {
            'title': 'Team Rankings',
            'type': 'leaderboard',
            'data': rankings
        }
        
        return widgets
    
    def _create_historical_dashboard(self, team_ids: List[str], period_days: int) -> Dict:
        """Create historical trends dashboard"""
        widgets = {}
        
        for team_id in team_ids:
            # Historical velocity
            velocities = []
            if team_id in self.velocity_tracker.sprint_velocities:
                for v in self.velocity_tracker.sprint_velocities[team_id]:
                    velocities.append({
                        'sprint': v.sprint_number,
                        'completed': v.completed_points,
                        'committed': v.committed_points
                    })
            
            widgets[f'{team_id}_historical_velocity'] = {
                'title': f'{team_id} Historical Velocity',
                'type': 'line_chart',
                'data': velocities
            }
            
            # Metric trends over time
            metrics_history = self._get_metrics_history(team_id, period_days)
            widgets[f'{team_id}_metrics_history'] = {
                'title': f'{team_id} Metrics History',
                'type': 'multi_line_chart',
                'data': metrics_history
            }
        
        return widgets
    
    def _get_health_trend(self, team_id: str) -> str:
        """Get health score trend for a team"""
        # This would look at historical health scores
        # For now, return based on current metrics
        metrics = self.agile_metrics.get_team_metrics(team_id, 30)
        
        improving_count = 0
        declining_count = 0
        
        for metric in [metrics.velocity, metrics.cycle_time, metrics.defect_rate]:
            if metric and metric.trend == TrendDirection.IMPROVING:
                improving_count += 1
            elif metric and metric.trend == TrendDirection.DECLINING:
                declining_count += 1
                
        if improving_count > declining_count:
            return "improving"
        elif declining_count > improving_count:
            return "declining"
        else:
            return "stable"
    
    def _calculate_velocity_change(self, team_ids: List[str]) -> float:
        """Calculate overall velocity change percentage"""
        total_current = 0
        total_previous = 0
        
        for team_id in team_ids:
            current = self.velocity_tracker.calculate_average_velocity(team_id, 3)
            previous = self.velocity_tracker.calculate_average_velocity(team_id, 6)
            
            if current and previous:
                total_current += current
                total_previous += previous
                
        if total_previous > 0:
            return ((total_current - total_previous) / total_previous) * 100
        return 0
    
    def _generate_executive_insights(self, team_ids: List[str], period_days: int) -> List[str]:
        """Generate executive-level insights"""
        insights = []
        
        # Check for teams with declining velocity
        for team_id in team_ids:
            trend = self.velocity_tracker.get_velocity_trend(team_id)
            if trend.trend_direction == "decreasing":
                insights.append(f"⚠️ {team_id} velocity declining - investigate impediments")
                
        # Check for quality issues
        for team_id in team_ids:
            metrics = self.agile_metrics.get_team_metrics(team_id, period_days)
            if metrics.defect_rate and metrics.defect_rate.current_value > 0.5:
                insights.append(f"🔴 {team_id} high defect rate ({metrics.defect_rate.current_value:.1f}/story)")
                
        # Check for overcommitment
        for team_id in team_ids:
            analysis = self.velocity_tracker.analyze_commitment_vs_completion(team_id)
            if analysis and analysis.get('overcommitment_rate', 0) > 30:
                insights.append(f"📊 {team_id} frequently overcommitting ({analysis['overcommitment_rate']:.0f}%)")
                
        # Positive insights
        for team_id in team_ids:
            trend = self.velocity_tracker.get_velocity_trend(team_id)
            if trend.maturity_level == "optimizing":
                insights.append(f"✅ {team_id} reached optimization maturity level")
                
        if not insights:
            insights.append("✅ All teams operating within normal parameters")
            
        return insights[:5]  # Return top 5 insights
    
    def _get_velocity_chart_data(self, team_id: str, period_days: int) -> Dict:
        """Get velocity chart data for a team"""
        data = {
            'labels': [],
            'committed': [],
            'completed': [],
            'average': []
        }
        
        if team_id in self.velocity_tracker.sprint_velocities:
            velocities = self.velocity_tracker.sprint_velocities[team_id]
            avg = self.velocity_tracker.calculate_average_velocity(team_id)
            
            for v in velocities[-10:]:  # Last 10 sprints
                data['labels'].append(f"Sprint {v.sprint_number}")
                data['committed'].append(v.committed_points)
                data['completed'].append(v.completed_points)
                data['average'].append(avg)
                
        return data
    
    def _get_reliability_status(self, reliability: float) -> str:
        """Get status based on commitment reliability"""
        if reliability >= 90:
            return "excellent"
        elif reliability >= 80:
            return "good"
        elif reliability >= 70:
            return "fair"
        else:
            return "needs_improvement"
    
    def _calculate_quality_score(self, metrics: TeamMetrics) -> float:
        """Calculate overall quality score"""
        score = 100.0
        
        if metrics.defect_rate:
            # Deduct points for defects (max 40 points)
            score -= min(40, metrics.defect_rate.current_value * 40)
            
        if metrics.rework_rate:
            # Deduct points for rework (max 30 points)
            score -= min(30, metrics.rework_rate.current_value * 0.3)
            
        return max(0, score)
    
    def _get_quality_grade(self, score: float) -> str:
        """Get quality grade based on score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _calculate_team_rankings(self, team_data: List[Dict]) -> List[Dict]:
        """Calculate team rankings based on multiple factors"""
        rankings = []
        
        # Score each team
        for team in team_data:
            score = (
                team['health_score'] * 0.3 +
                team['stability'] * 0.2 +
                min(100, team['velocity'] / 2) * 0.3 +  # Normalize velocity
                (100 - min(100, team['defect_rate'] * 100)) * 0.2  # Inverse defect rate
            )
            
            rankings.append({
                'rank': 0,
                'team_id': team['team_id'],
                'score': score,
                'health': team['health_score'],
                'velocity': team['velocity'],
                'quality': 100 - min(100, team['defect_rate'] * 100)
            })
        
        # Sort and assign ranks
        rankings.sort(key=lambda x: x['score'], reverse=True)
        for i, ranking in enumerate(rankings):
            ranking['rank'] = i + 1
            
        return rankings
    
    def _get_metrics_history(self, team_id: str, period_days: int) -> Dict:
        """Get historical metrics data"""
        # This would pull from historical data
        # For now, return sample structure
        return {
            'dates': [],
            'velocity': [],
            'cycle_time': [],
            'defect_rate': [],
            'throughput': []
        }
    
    def export_dashboard(self, dashboard: Dict, format: str = 'json') -> str:
        """Export dashboard in specified format"""
        if format == 'json':
            return json.dumps(dashboard, indent=2, default=str)
        elif format == 'html':
            return self._export_html(dashboard)
        elif format == 'markdown':
            return self._export_markdown(dashboard)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_html(self, dashboard: Dict) -> str:
        """Export dashboard as HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Agile Metrics Dashboard - {dashboard['view']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .widget {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
                .metric {{ font-size: 24px; font-weight: bold; }}
                .label {{ color: #666; }}
            </style>
        </head>
        <body>
            <h1>Agile Metrics Dashboard</h1>
            <p>View: {dashboard['view']} | Teams: {', '.join(dashboard['team_ids'])} | {dashboard['period']}</p>
            <hr>
        """
        
        for widget_id, widget in dashboard['widgets'].items():
            html += f"""
            <div class="widget">
                <h3>{widget['title']}</h3>
                <div class="content">
                    {self._render_widget_html(widget)}
                </div>
            </div>
            """
            
        html += """
        </body>
        </html>
        """
        return html
    
    def _render_widget_html(self, widget: Dict) -> str:
        """Render widget content as HTML"""
        if widget['type'] == 'metric':
            data = widget['data']
            return f"""
                <div class="metric">{data.get('value', 'N/A')}</div>
                <div class="label">{data.get('unit', '')}</div>
            """
        elif widget['type'] == 'table':
            # Render as HTML table
            return "<pre>" + json.dumps(widget['data'], indent=2) + "</pre>"
        else:
            # Generic rendering
            return f"<pre>{json.dumps(widget['data'], indent=2, default=str)}</pre>"
    
    def _export_markdown(self, dashboard: Dict) -> str:
        """Export dashboard as Markdown"""
        lines = [
            f"# Agile Metrics Dashboard",
            f"**View**: {dashboard['view']}",
            f"**Teams**: {', '.join(dashboard['team_ids'])}",
            f"**Period**: {dashboard['period']}",
            f"**Generated**: {dashboard['generated_at']}",
            "",
            "---",
            ""
        ]
        
        for widget_id, widget in dashboard['widgets'].items():
            lines.append(f"## {widget['title']}")
            lines.append(self._render_widget_markdown(widget))
            lines.append("")
            
        return '\n'.join(lines)
    
    def _render_widget_markdown(self, widget: Dict) -> str:
        """Render widget content as Markdown"""
        if widget['type'] == 'metric':
            data = widget['data']
            return f"**{data.get('value', 'N/A')}** {data.get('unit', '')}"
        elif widget['type'] == 'list':
            return '\n'.join([f"- {item}" for item in widget['data']])
        elif widget['type'] == 'table' and 'headers' in widget['data']:
            # Render as Markdown table
            lines = []
            headers = widget['data']['headers']
            lines.append('| ' + ' | '.join(headers) + ' |')
            lines.append('|' + '---|' * len(headers))
            
            for row in widget['data'].get('rows', []):
                if isinstance(row, dict):
                    row_values = [str(row.get(h.lower().replace(' ', '_'), '')) for h in headers]
                else:
                    row_values = [str(v) for v in row]
                lines.append('| ' + ' | '.join(row_values) + ' |')
                
            return '\n'.join(lines)
        else:
            # Generic rendering
            return f"```json\n{json.dumps(widget['data'], indent=2, default=str)}\n```"