"""
Velocity Tracker Module
Tracks and predicts team velocity for sprint planning and capacity management.
Part of the Agile AI Company framework.
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import math

class PredictionConfidence(Enum):
    """Confidence levels for velocity predictions"""
    HIGH = "high"           # > 80% confidence
    MEDIUM = "medium"       # 60-80% confidence
    LOW = "low"            # 40-60% confidence
    VERY_LOW = "very_low"  # < 40% confidence

class CapacityFactor(Enum):
    """Factors affecting team capacity"""
    HOLIDAYS = "holidays"
    TEAM_SIZE_CHANGE = "team_size_change"
    NEW_TEAM_MEMBERS = "new_team_members"
    TECHNICAL_DEBT = "technical_debt"
    LEARNING_CURVE = "learning_curve"
    EXTERNAL_DEPENDENCIES = "external_dependencies"

@dataclass
class SprintVelocity:
    """Velocity data for a single sprint"""
    sprint_id: str
    sprint_number: int
    team_id: str
    committed_points: float
    completed_points: float
    start_date: datetime
    end_date: datetime
    team_size: int
    working_days: int
    capacity_factors: List[CapacityFactor] = field(default_factory=list)
    notes: str = ""

@dataclass
class VelocityPrediction:
    """Predicted velocity for future sprints"""
    team_id: str
    predicted_velocity: float
    confidence: PredictionConfidence
    confidence_percentage: float
    lower_bound: float
    upper_bound: float
    factors_considered: List[str] = field(default_factory=list)
    recommendation: str = ""

@dataclass
class CapacityPlan:
    """Capacity planning for upcoming sprints"""
    team_id: str
    sprint_id: str
    available_capacity: float
    recommended_commitment: float
    buffer_percentage: float
    risk_factors: List[str] = field(default_factory=list)
    adjustments: Dict[str, float] = field(default_factory=dict)

@dataclass
class VelocityTrend:
    """Velocity trend analysis"""
    team_id: str
    trend_direction: str  # "increasing", "stable", "decreasing"
    trend_strength: float  # 0-1 scale
    average_velocity: float
    velocity_variance: float
    stability_score: float  # 0-100 scale
    maturity_level: str  # "forming", "stabilizing", "mature", "optimizing"

class VelocityTracker:
    """
    Advanced velocity tracking and prediction system for agile teams.
    Provides historical analysis, predictions, and capacity planning.
    """
    
    def __init__(self):
        self.sprint_velocities: Dict[str, List[SprintVelocity]] = {}
        self.team_capacity: Dict[str, Dict] = {}
        self.historical_accuracy: Dict[str, List[float]] = {}
        
    def record_sprint_velocity(self, sprint_velocity: SprintVelocity) -> None:
        """Record velocity data for a completed sprint"""
        team_id = sprint_velocity.team_id
        
        if team_id not in self.sprint_velocities:
            self.sprint_velocities[team_id] = []
            
        self.sprint_velocities[team_id].append(sprint_velocity)
        
        # Sort by sprint number
        self.sprint_velocities[team_id].sort(key=lambda x: x.sprint_number)
        
        # Update historical accuracy if we had a prediction
        self._update_prediction_accuracy(sprint_velocity)
    
    def calculate_average_velocity(self, team_id: str, 
                                  last_n_sprints: Optional[int] = None) -> float:
        """Calculate average velocity over specified sprints"""
        if team_id not in self.sprint_velocities:
            return 0.0
            
        velocities = self.sprint_velocities[team_id]
        
        if last_n_sprints:
            velocities = velocities[-last_n_sprints:]
            
        if not velocities:
            return 0.0
            
        completed_points = [v.completed_points for v in velocities]
        return statistics.mean(completed_points)
    
    def calculate_rolling_average(self, team_id: str, window_size: int = 3) -> List[float]:
        """Calculate rolling average velocity"""
        if team_id not in self.sprint_velocities:
            return []
            
        velocities = self.sprint_velocities[team_id]
        if len(velocities) < window_size:
            return []
            
        rolling_avg = []
        for i in range(window_size - 1, len(velocities)):
            window = velocities[i - window_size + 1:i + 1]
            avg = statistics.mean([v.completed_points for v in window])
            rolling_avg.append(avg)
            
        return rolling_avg
    
    def predict_velocity(self, team_id: str, 
                        future_sprint_count: int = 1,
                        consider_factors: bool = True) -> VelocityPrediction:
        """
        Predict future velocity using advanced statistical methods.
        Uses weighted moving average with trend analysis.
        """
        if team_id not in self.sprint_velocities:
            return VelocityPrediction(
                team_id=team_id,
                predicted_velocity=0,
                confidence=PredictionConfidence.VERY_LOW,
                confidence_percentage=0,
                lower_bound=0,
                upper_bound=0,
                recommendation="Insufficient data for prediction"
            )
            
        velocities = self.sprint_velocities[team_id]
        
        if len(velocities) < 2:
            # Not enough data for prediction
            last_velocity = velocities[-1].completed_points if velocities else 0
            return VelocityPrediction(
                team_id=team_id,
                predicted_velocity=last_velocity,
                confidence=PredictionConfidence.VERY_LOW,
                confidence_percentage=25,
                lower_bound=last_velocity * 0.5,
                upper_bound=last_velocity * 1.5,
                recommendation="Need at least 2 sprints for accurate prediction"
            )
            
        # Calculate weighted moving average (recent sprints have more weight)
        weights = self._calculate_weights(len(velocities))
        completed_points = [v.completed_points for v in velocities]
        weighted_avg = sum(w * v for w, v in zip(weights, completed_points))
        
        # Calculate trend
        trend = self._calculate_trend(completed_points)
        
        # Apply trend to prediction
        predicted_velocity = weighted_avg + (trend * future_sprint_count)
        
        # Consider capacity factors if enabled
        if consider_factors:
            adjustments = self._calculate_capacity_adjustments(team_id)
            predicted_velocity *= adjustments
            
        # Calculate confidence and bounds
        std_dev = statistics.stdev(completed_points) if len(completed_points) > 1 else 0
        confidence, confidence_pct = self._calculate_confidence(velocities, std_dev)
        
        # Calculate prediction bounds (using confidence intervals)
        margin = 1.96 * std_dev / math.sqrt(len(velocities))  # 95% confidence interval
        lower_bound = max(0, predicted_velocity - margin)
        upper_bound = predicted_velocity + margin
        
        # Generate recommendation
        recommendation = self._generate_velocity_recommendation(
            predicted_velocity, confidence, trend, velocities
        )
        
        return VelocityPrediction(
            team_id=team_id,
            predicted_velocity=round(predicted_velocity, 1),
            confidence=confidence,
            confidence_percentage=confidence_pct,
            lower_bound=round(lower_bound, 1),
            upper_bound=round(upper_bound, 1),
            factors_considered=["weighted_average", "trend_analysis", "capacity_factors"],
            recommendation=recommendation
        )
    
    def _calculate_weights(self, n: int) -> List[float]:
        """Calculate exponentially decaying weights for weighted average"""
        alpha = 0.3  # Decay factor
        weights = []
        
        for i in range(n):
            weight = (1 - alpha) ** (n - i - 1)
            weights.append(weight)
            
        # Normalize weights to sum to 1
        total = sum(weights)
        return [w / total for w in weights]
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend using linear regression"""
        n = len(values)
        if n < 2:
            return 0
            
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
            
        return numerator / denominator
    
    def _calculate_confidence(self, velocities: List[SprintVelocity], 
                            std_dev: float) -> Tuple[PredictionConfidence, float]:
        """Calculate prediction confidence based on historical data"""
        n = len(velocities)
        
        # Factors affecting confidence
        data_points_score = min(100, n * 10)  # More data = higher confidence
        
        # Stability score (lower variance = higher confidence)
        if velocities:
            mean_velocity = statistics.mean([v.completed_points for v in velocities])
            cv = (std_dev / mean_velocity * 100) if mean_velocity > 0 else 100  # Coefficient of variation
            stability_score = max(0, 100 - cv)
        else:
            stability_score = 0
            
        # Recent accuracy score (if we have historical predictions)
        team_id = velocities[0].team_id if velocities else ""
        accuracy_score = self._get_prediction_accuracy_score(team_id)
        
        # Combined confidence score
        confidence_pct = (data_points_score * 0.3 + 
                         stability_score * 0.5 + 
                         accuracy_score * 0.2)
        
        if confidence_pct > 80:
            return PredictionConfidence.HIGH, confidence_pct
        elif confidence_pct > 60:
            return PredictionConfidence.MEDIUM, confidence_pct
        elif confidence_pct > 40:
            return PredictionConfidence.LOW, confidence_pct
        else:
            return PredictionConfidence.VERY_LOW, confidence_pct
    
    def _calculate_capacity_adjustments(self, team_id: str) -> float:
        """Calculate capacity adjustment factors"""
        if team_id not in self.team_capacity:
            return 1.0
            
        capacity = self.team_capacity[team_id]
        adjustment = 1.0
        
        # Adjust for team size changes
        if 'team_size_change' in capacity:
            adjustment *= capacity['team_size_change']
            
        # Adjust for holidays
        if 'holiday_impact' in capacity:
            adjustment *= (1 - capacity['holiday_impact'])
            
        # Adjust for new team members (learning curve)
        if 'new_members_ratio' in capacity:
            learning_factor = 1 - (capacity['new_members_ratio'] * 0.3)  # 30% reduction per new member
            adjustment *= learning_factor
            
        return adjustment
    
    def _generate_velocity_recommendation(self, predicted: float, 
                                         confidence: PredictionConfidence,
                                         trend: float,
                                         velocities: List[SprintVelocity]) -> str:
        """Generate actionable recommendation based on velocity analysis"""
        recommendations = []
        
        if confidence == PredictionConfidence.HIGH:
            recommendations.append(f"High confidence prediction: commit to {predicted:.0f} points")
        elif confidence == PredictionConfidence.MEDIUM:
            recommendations.append(f"Moderate confidence: consider {predicted * 0.9:.0f}-{predicted:.0f} points")
        else:
            recommendations.append(f"Low confidence: be conservative, consider {predicted * 0.7:.0f}-{predicted * 0.85:.0f} points")
            
        if trend > 0.5:
            recommendations.append("Velocity trending up - team is improving")
        elif trend < -0.5:
            recommendations.append("Velocity trending down - investigate impediments")
            
        # Check for high variance
        if velocities and len(velocities) > 2:
            points = [v.completed_points for v in velocities]
            cv = statistics.stdev(points) / statistics.mean(points) if statistics.mean(points) > 0 else 0
            if cv > 0.3:  # 30% coefficient of variation
                recommendations.append("High variance detected - focus on consistency")
                
        return ". ".join(recommendations)
    
    def analyze_commitment_vs_completion(self, team_id: str) -> Dict[str, float]:
        """Analyze team's commitment accuracy"""
        if team_id not in self.sprint_velocities:
            return {}
            
        velocities = self.sprint_velocities[team_id]
        if not velocities:
            return {}
            
        committed = [v.committed_points for v in velocities]
        completed = [v.completed_points for v in velocities]
        
        analysis = {
            'average_committed': statistics.mean(committed),
            'average_completed': statistics.mean(completed),
            'completion_rate': statistics.mean([c/cm * 100 for c, cm in zip(completed, committed) if cm > 0]),
            'overcommitment_rate': sum(1 for i in range(len(velocities)) if committed[i] > completed[i]) / len(velocities) * 100
        }
        
        return analysis
    
    def get_velocity_trend(self, team_id: str) -> VelocityTrend:
        """Analyze velocity trend and team maturity"""
        if team_id not in self.sprint_velocities:
            return VelocityTrend(
                team_id=team_id,
                trend_direction="unknown",
                trend_strength=0,
                average_velocity=0,
                velocity_variance=0,
                stability_score=0,
                maturity_level="forming"
            )
            
        velocities = self.sprint_velocities[team_id]
        completed_points = [v.completed_points for v in velocities]
        
        # Calculate trend
        trend = self._calculate_trend(completed_points)
        
        # Determine trend direction and strength
        if abs(trend) < 0.5:
            trend_direction = "stable"
        elif trend > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"
            
        trend_strength = min(1.0, abs(trend) / 5)  # Normalize to 0-1
        
        # Calculate statistics
        avg_velocity = statistics.mean(completed_points)
        variance = statistics.variance(completed_points) if len(completed_points) > 1 else 0
        
        # Calculate stability score (lower variance = higher stability)
        cv = math.sqrt(variance) / avg_velocity if avg_velocity > 0 else 1
        stability_score = max(0, min(100, 100 * (1 - cv)))
        
        # Determine maturity level
        maturity_level = self._determine_maturity_level(
            len(velocities), stability_score, trend_direction
        )
        
        return VelocityTrend(
            team_id=team_id,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            average_velocity=avg_velocity,
            velocity_variance=variance,
            stability_score=stability_score,
            maturity_level=maturity_level
        )
    
    def _determine_maturity_level(self, sprint_count: int, 
                                 stability_score: float,
                                 trend_direction: str) -> str:
        """Determine team maturity level based on velocity patterns"""
        if sprint_count < 3:
            return "forming"
        elif sprint_count < 6:
            return "stabilizing"
        elif stability_score > 70 and trend_direction in ["stable", "increasing"]:
            if sprint_count > 12:
                return "optimizing"
            return "mature"
        elif stability_score > 50:
            return "stabilizing"
        else:
            return "forming"
    
    def plan_sprint_capacity(self, team_id: str, sprint_id: str,
                           working_days: int,
                           team_size: int,
                           risk_factors: Optional[List[str]] = None) -> CapacityPlan:
        """Create capacity plan for upcoming sprint"""
        prediction = self.predict_velocity(team_id)
        
        # Calculate available capacity
        if team_id in self.sprint_velocities and self.sprint_velocities[team_id]:
            recent_velocities = self.sprint_velocities[team_id][-3:]
            avg_velocity_per_day_per_person = statistics.mean([
                v.completed_points / (v.working_days * v.team_size)
                for v in recent_velocities
                if v.working_days > 0 and v.team_size > 0
            ])
            available_capacity = avg_velocity_per_day_per_person * working_days * team_size
        else:
            # Default capacity for new teams (conservative estimate)
            available_capacity = working_days * team_size * 1.5  # 1.5 points per person per day
            
        # Determine buffer based on confidence and risk
        if prediction.confidence == PredictionConfidence.HIGH:
            buffer_percentage = 10
        elif prediction.confidence == PredictionConfidence.MEDIUM:
            buffer_percentage = 20
        else:
            buffer_percentage = 30
            
        # Adjust for risk factors
        if risk_factors:
            buffer_percentage += len(risk_factors) * 5
            
        # Calculate recommended commitment
        recommended_commitment = available_capacity * (1 - buffer_percentage / 100)
        
        # Apply any specific adjustments
        adjustments = {}
        if risk_factors and 'new_team_members' in risk_factors:
            adjustments['new_member_adjustment'] = -0.2
            recommended_commitment *= 0.8
            
        return CapacityPlan(
            team_id=team_id,
            sprint_id=sprint_id,
            available_capacity=round(available_capacity, 1),
            recommended_commitment=round(recommended_commitment, 1),
            buffer_percentage=buffer_percentage,
            risk_factors=risk_factors or [],
            adjustments=adjustments
        )
    
    def _update_prediction_accuracy(self, actual: SprintVelocity) -> None:
        """Update historical prediction accuracy"""
        # This would compare actual vs predicted if we stored predictions
        # For now, we'll track completion vs commitment as a proxy
        team_id = actual.team_id
        
        if team_id not in self.historical_accuracy:
            self.historical_accuracy[team_id] = []
            
        if actual.committed_points > 0:
            accuracy = actual.completed_points / actual.committed_points
            self.historical_accuracy[team_id].append(accuracy)
            
            # Keep only last 10 predictions
            if len(self.historical_accuracy[team_id]) > 10:
                self.historical_accuracy[team_id] = self.historical_accuracy[team_id][-10:]
    
    def _get_prediction_accuracy_score(self, team_id: str) -> float:
        """Get historical prediction accuracy score"""
        if team_id not in self.historical_accuracy or not self.historical_accuracy[team_id]:
            return 50  # Default neutral score
            
        accuracies = self.historical_accuracy[team_id]
        
        # Calculate how close predictions were to actual (1.0 = perfect)
        avg_accuracy = statistics.mean(accuracies)
        
        # Convert to 0-100 score (0.8-1.2 range maps to 100-0)
        if 0.8 <= avg_accuracy <= 1.2:
            score = 100 * (1 - abs(1 - avg_accuracy) / 0.2)
        else:
            score = 0
            
        return score
    
    def export_velocity_data(self, team_id: str, format: str = 'json') -> str:
        """Export velocity data in specified format"""
        if format == 'json':
            return self._export_json(team_id)
        elif format == 'csv':
            return self._export_csv(team_id)
        elif format == 'markdown':
            return self._export_markdown(team_id)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, team_id: str) -> str:
        """Export velocity data as JSON"""
        data = {
            'team_id': team_id,
            'velocities': [],
            'prediction': None,
            'trend': None,
            'commitment_analysis': {}
        }
        
        if team_id in self.sprint_velocities:
            data['velocities'] = [asdict(v) for v in self.sprint_velocities[team_id]]
            
        prediction = self.predict_velocity(team_id)
        data['prediction'] = asdict(prediction)
        
        trend = self.get_velocity_trend(team_id)
        data['trend'] = asdict(trend)
        
        data['commitment_analysis'] = self.analyze_commitment_vs_completion(team_id)
        
        return json.dumps(data, indent=2, default=str)
    
    def _export_csv(self, team_id: str) -> str:
        """Export velocity data as CSV"""
        lines = ['Sprint,Sprint_Number,Committed,Completed,Start_Date,End_Date,Team_Size,Working_Days']
        
        if team_id in self.sprint_velocities:
            for v in self.sprint_velocities[team_id]:
                line = f"{v.sprint_id},{v.sprint_number},{v.committed_points},{v.completed_points},"
                line += f"{v.start_date.isoformat()},{v.end_date.isoformat()},"
                line += f"{v.team_size},{v.working_days}"
                lines.append(line)
                
        return '\n'.join(lines)
    
    def _export_markdown(self, team_id: str) -> str:
        """Export velocity report as Markdown"""
        lines = [f"# Velocity Report - Team {team_id}", ""]
        
        # Trend analysis
        trend = self.get_velocity_trend(team_id)
        lines.append("## Velocity Trend")
        lines.append(f"- **Direction**: {trend.trend_direction}")
        lines.append(f"- **Average Velocity**: {trend.average_velocity:.1f} points")
        lines.append(f"- **Stability Score**: {trend.stability_score:.1f}/100")
        lines.append(f"- **Team Maturity**: {trend.maturity_level}")
        lines.append("")
        
        # Prediction
        prediction = self.predict_velocity(team_id)
        lines.append("## Velocity Prediction")
        lines.append(f"- **Predicted**: {prediction.predicted_velocity:.1f} points")
        lines.append(f"- **Confidence**: {prediction.confidence.value} ({prediction.confidence_percentage:.1f}%)")
        lines.append(f"- **Range**: {prediction.lower_bound:.1f} - {prediction.upper_bound:.1f}")
        lines.append(f"- **Recommendation**: {prediction.recommendation}")
        lines.append("")
        
        # Commitment analysis
        analysis = self.analyze_commitment_vs_completion(team_id)
        if analysis:
            lines.append("## Commitment Analysis")
            lines.append(f"- **Average Committed**: {analysis.get('average_committed', 0):.1f} points")
            lines.append(f"- **Average Completed**: {analysis.get('average_completed', 0):.1f} points")
            lines.append(f"- **Completion Rate**: {analysis.get('completion_rate', 0):.1f}%")
            lines.append(f"- **Overcommitment Rate**: {analysis.get('overcommitment_rate', 0):.1f}%")
            lines.append("")
            
        # Historical data
        if team_id in self.sprint_velocities:
            lines.append("## Sprint History")
            lines.append("| Sprint | Committed | Completed | Completion % |")
            lines.append("|--------|-----------|-----------|--------------|")
            
            for v in self.sprint_velocities[team_id][-10:]:  # Last 10 sprints
                completion_pct = (v.completed_points / v.committed_points * 100) if v.committed_points > 0 else 0
                lines.append(f"| Sprint {v.sprint_number} | {v.committed_points:.0f} | {v.completed_points:.0f} | {completion_pct:.1f}% |")
                
        return '\n'.join(lines)