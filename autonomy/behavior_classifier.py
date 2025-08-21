"""
Behavior Classification and Intervention System

This module classifies detected behaviors as positive, neutral, or negative,
and implements intervention strategies to guide positive emergence and
suppress negative patterns.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from uuid import uuid4
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BehaviorCategory(Enum):
    """Categories for behavior classification"""
    POSITIVE = "positive"          # Beneficial behaviors to encourage
    NEUTRAL = "neutral"            # Normal operational behaviors
    NEGATIVE = "negative"          # Harmful behaviors to suppress
    UNKNOWN = "unknown"           # Unclassified behaviors


class InterventionType(Enum):
    """Types of interventions available"""
    REINFORCEMENT = "reinforcement"      # Positive reinforcement
    GUIDANCE = "guidance"                # Gentle guidance
    CORRECTION = "correction"            # Corrective action
    SUPPRESSION = "suppression"          # Active suppression
    ISOLATION = "isolation"              # Isolate problematic behavior
    REWARD = "reward"                    # Reward good behavior
    PENALTY = "penalty"                  # Penalize bad behavior
    EDUCATION = "education"              # Educational intervention
    RESTRUCTURING = "restructuring"      # Team restructuring
    MONITORING = "monitoring"            # Enhanced monitoring only


class BehaviorSeverity(Enum):
    """Severity levels for behaviors"""
    CRITICAL = "critical"    # Requires immediate intervention
    HIGH = "high"           # Requires prompt intervention
    MEDIUM = "medium"       # Should be addressed
    LOW = "low"            # Monitor and track
    MINIMAL = "minimal"     # No action needed


@dataclass
class BehaviorClassification:
    """Classification result for a behavior"""
    classification_id: str = field(default_factory=lambda: str(uuid4()))
    behavior_id: str = ""
    category: BehaviorCategory = BehaviorCategory.UNKNOWN
    confidence: float = 0.0
    severity: BehaviorSeverity = BehaviorSeverity.MINIMAL
    classified_at: datetime = field(default_factory=datetime.now)
    reasoning: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_interventions: List[InterventionType] = field(default_factory=list)


@dataclass
class Intervention:
    """Represents an intervention action"""
    intervention_id: str = field(default_factory=lambda: str(uuid4()))
    intervention_type: InterventionType = InterventionType.MONITORING
    target_behavior_id: str = ""
    target_agents: List[str] = field(default_factory=list)
    target_teams: List[str] = field(default_factory=list)
    initiated_at: datetime = field(default_factory=datetime.now)
    duration: Optional[timedelta] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, active, completed, failed
    effectiveness: Optional[float] = None
    outcomes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorRule:
    """Rule for classifying behaviors"""
    rule_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    category: BehaviorCategory = BehaviorCategory.UNKNOWN
    severity: BehaviorSeverity = BehaviorSeverity.MINIMAL
    interventions: List[InterventionType] = field(default_factory=list)
    priority: int = 0  # Higher priority rules are evaluated first


class BehaviorClassifier:
    """Classifies and manages interventions for emergent behaviors"""
    
    def __init__(self):
        """Initialize the behavior classifier"""
        # Classification rules
        self.rules: List[BehaviorRule] = self._initialize_rules()
        
        # ML model placeholders (would be actual models in production)
        self.ml_models: Dict[str, Any] = {}
        
        # Classification history
        self.classifications: List[BehaviorClassification] = []
        
        # Active interventions
        self.active_interventions: Dict[str, Intervention] = {}
        self.intervention_history: List[Intervention] = []
        
        # Effectiveness tracking
        self.intervention_effectiveness: Dict[str, List[float]] = {
            intervention_type: [] for intervention_type in InterventionType
        }
        
        # Callbacks for interventions
        self.intervention_callbacks: Dict[InterventionType, Callable] = {}
        
        self.running = False
        
    def _initialize_rules(self) -> List[BehaviorRule]:
        """Initialize behavior classification rules"""
        rules = [
            # Positive behaviors
            BehaviorRule(
                name="collaboration_increase",
                description="Increasing collaboration between agents",
                conditions={"pattern_type": "collaboration_increase", "confidence_min": 0.7},
                category=BehaviorCategory.POSITIVE,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.REINFORCEMENT, InterventionType.REWARD],
                priority=10
            ),
            BehaviorRule(
                name="innovation_burst",
                description="Burst of innovative solutions",
                conditions={"pattern_type": "innovation_burst", "confidence_min": 0.6},
                category=BehaviorCategory.POSITIVE,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.REINFORCEMENT, InterventionType.REWARD],
                priority=10
            ),
            BehaviorRule(
                name="resource_optimization",
                description="Efficient resource utilization",
                conditions={"pattern_type": "resource_optimization", "confidence_min": 0.7},
                category=BehaviorCategory.POSITIVE,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.REINFORCEMENT],
                priority=10
            ),
            BehaviorRule(
                name="knowledge_sharing",
                description="Active knowledge sharing between agents",
                conditions={"pattern_type": "knowledge_sharing", "confidence_min": 0.6},
                category=BehaviorCategory.POSITIVE,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.REINFORCEMENT, InterventionType.REWARD],
                priority=10
            ),
            BehaviorRule(
                name="consensus_building",
                description="Building consensus in decision making",
                conditions={"pattern_type": "consensus_building", "confidence_min": 0.7},
                category=BehaviorCategory.POSITIVE,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.REINFORCEMENT],
                priority=10
            ),
            
            # Negative behaviors
            BehaviorRule(
                name="collaboration_decrease",
                description="Decreasing collaboration between agents",
                conditions={"pattern_type": "collaboration_decrease", "confidence_min": 0.7},
                category=BehaviorCategory.NEGATIVE,
                severity=BehaviorSeverity.MEDIUM,
                interventions=[InterventionType.GUIDANCE, InterventionType.EDUCATION],
                priority=20
            ),
            BehaviorRule(
                name="resource_competition",
                description="Unhealthy competition for resources",
                conditions={"pattern_type": "resource_competition", "confidence_min": 0.7},
                category=BehaviorCategory.NEGATIVE,
                severity=BehaviorSeverity.HIGH,
                interventions=[InterventionType.CORRECTION, InterventionType.RESTRUCTURING],
                priority=25
            ),
            BehaviorRule(
                name="knowledge_hoarding",
                description="Agents hoarding knowledge",
                conditions={"pattern_type": "knowledge_hoarding", "confidence_min": 0.6},
                category=BehaviorCategory.NEGATIVE,
                severity=BehaviorSeverity.MEDIUM,
                interventions=[InterventionType.CORRECTION, InterventionType.EDUCATION],
                priority=20
            ),
            BehaviorRule(
                name="conflict_pattern",
                description="Recurring conflicts between agents",
                conditions={"pattern_type": "conflict_pattern", "confidence_min": 0.6},
                category=BehaviorCategory.NEGATIVE,
                severity=BehaviorSeverity.HIGH,
                interventions=[InterventionType.CORRECTION, InterventionType.RESTRUCTURING],
                priority=25
            ),
            BehaviorRule(
                name="decision_divergence",
                description="Increasing divergence in decision making",
                conditions={"pattern_type": "decision_divergence", "confidence_min": 0.7},
                category=BehaviorCategory.NEGATIVE,
                severity=BehaviorSeverity.MEDIUM,
                interventions=[InterventionType.GUIDANCE, InterventionType.EDUCATION],
                priority=20
            ),
            
            # Neutral behaviors
            BehaviorRule(
                name="routine_formation",
                description="Formation of routine procedures",
                conditions={"pattern_type": "routine_formation", "confidence_min": 0.5},
                category=BehaviorCategory.NEUTRAL,
                severity=BehaviorSeverity.MINIMAL,
                interventions=[InterventionType.MONITORING],
                priority=5
            ),
            BehaviorRule(
                name="specialization_emergence",
                description="Agents developing specializations",
                conditions={"pattern_type": "specialization_emergence", "confidence_min": 0.6},
                category=BehaviorCategory.NEUTRAL,
                severity=BehaviorSeverity.LOW,
                interventions=[InterventionType.MONITORING, InterventionType.GUIDANCE],
                priority=5
            ),
            BehaviorRule(
                name="communication_clustering",
                description="Formation of communication clusters",
                conditions={"pattern_type": "communication_clustering", "confidence_min": 0.6},
                category=BehaviorCategory.NEUTRAL,
                severity=BehaviorSeverity.LOW,
                interventions=[InterventionType.MONITORING],
                priority=5
            ),
        ]
        
        # Sort rules by priority (higher priority first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules
        
    async def start_classification(self):
        """Start the classification system"""
        self.running = True
        logger.info("Behavior classifier started")
        
        # Start background tasks
        await asyncio.gather(
            self._intervention_monitor_loop(),
            self._effectiveness_evaluation_loop()
        )
        
    async def stop_classification(self):
        """Stop the classification system"""
        self.running = False
        logger.info("Behavior classifier stopped")
        
    def classify_behavior(self, behavior_data: Dict[str, Any]) -> BehaviorClassification:
        """
        Classify a behavior based on rules and ML models
        
        Args:
            behavior_data: Data about the behavior to classify
            
        Returns:
            BehaviorClassification object
        """
        # First try rule-based classification
        classification = self._rule_based_classification(behavior_data)
        
        # If no rule matches or confidence is low, try ML classification
        if classification.category == BehaviorCategory.UNKNOWN or classification.confidence < 0.5:
            ml_classification = self._ml_based_classification(behavior_data)
            if ml_classification.confidence > classification.confidence:
                classification = ml_classification
                
        # Store classification
        self.classifications.append(classification)
        
        # Log classification
        logger.info(f"Classified behavior as {classification.category.value} "
                   f"with confidence {classification.confidence:.2f}")
        
        return classification
        
    def _rule_based_classification(self, behavior_data: Dict[str, Any]) -> BehaviorClassification:
        """Apply rule-based classification"""
        for rule in self.rules:
            if self._evaluate_rule(rule, behavior_data):
                return BehaviorClassification(
                    behavior_id=behavior_data.get("behavior_id", ""),
                    category=rule.category,
                    confidence=behavior_data.get("confidence", 0.8),
                    severity=rule.severity,
                    reasoning=f"Matched rule: {rule.name} - {rule.description}",
                    evidence={"rule": rule.name, "conditions": rule.conditions},
                    recommended_interventions=rule.interventions
                )
                
        # No rule matched
        return BehaviorClassification(
            behavior_id=behavior_data.get("behavior_id", ""),
            category=BehaviorCategory.UNKNOWN,
            confidence=0.0,
            reasoning="No matching rules found"
        )
        
    def _evaluate_rule(self, rule: BehaviorRule, behavior_data: Dict[str, Any]) -> bool:
        """Evaluate if a rule matches the behavior data"""
        for key, value in rule.conditions.items():
            if key == "pattern_type":
                if behavior_data.get("pattern_type") != value:
                    return False
            elif key == "confidence_min":
                if behavior_data.get("confidence", 0) < value:
                    return False
            elif key in behavior_data:
                if behavior_data[key] != value:
                    return False
            else:
                return False
        return True
        
    def _ml_based_classification(self, behavior_data: Dict[str, Any]) -> BehaviorClassification:
        """Apply ML-based classification (placeholder for actual ML implementation)"""
        # In production, this would use trained ML models
        # For now, return a basic classification based on simple heuristics
        
        pattern_type = behavior_data.get("pattern_type", "")
        confidence = behavior_data.get("confidence", 0.5)
        
        # Simple heuristic classification
        if "collaboration" in pattern_type or "knowledge_sharing" in pattern_type:
            category = BehaviorCategory.POSITIVE
        elif "conflict" in pattern_type or "competition" in pattern_type:
            category = BehaviorCategory.NEGATIVE
        else:
            category = BehaviorCategory.NEUTRAL
            
        return BehaviorClassification(
            behavior_id=behavior_data.get("behavior_id", ""),
            category=category,
            confidence=confidence * 0.7,  # Lower confidence for ML classification
            severity=BehaviorSeverity.LOW,
            reasoning="ML-based classification (heuristic)",
            evidence={"method": "ml_heuristic", "pattern": pattern_type}
        )
        
    async def create_intervention(self, 
                                 classification: BehaviorClassification,
                                 behavior_data: Dict[str, Any]) -> Optional[Intervention]:
        """
        Create and initiate an intervention based on classification
        
        Args:
            classification: The behavior classification
            behavior_data: Additional data about the behavior
            
        Returns:
            Intervention object if created, None otherwise
        """
        # Skip intervention for positive behaviors with minimal severity
        if (classification.category == BehaviorCategory.POSITIVE and 
            classification.severity == BehaviorSeverity.MINIMAL):
            # Only reinforcement for positive behaviors
            if InterventionType.REINFORCEMENT in classification.recommended_interventions:
                return await self._create_reinforcement_intervention(
                    classification, behavior_data
                )
            return None
            
        # Skip intervention for neutral behaviors unless severity is high
        if (classification.category == BehaviorCategory.NEUTRAL and
            classification.severity in [BehaviorSeverity.MINIMAL, BehaviorSeverity.LOW]):
            return None
            
        # Create intervention for negative behaviors
        if classification.category == BehaviorCategory.NEGATIVE:
            return await self._create_corrective_intervention(
                classification, behavior_data
            )
            
        return None
        
    async def _create_reinforcement_intervention(self,
                                                classification: BehaviorClassification,
                                                behavior_data: Dict[str, Any]) -> Intervention:
        """Create reinforcement intervention for positive behavior"""
        intervention = Intervention(
            intervention_type=InterventionType.REINFORCEMENT,
            target_behavior_id=classification.behavior_id,
            target_agents=behavior_data.get("affected_agents", []),
            target_teams=behavior_data.get("affected_teams", []),
            duration=timedelta(hours=1),
            parameters={
                "reinforcement_strength": 0.8,
                "method": "positive_feedback",
                "rewards": ["resource_priority", "autonomy_increase"]
            },
            status="active"
        )
        
        # Store and execute intervention
        self.active_interventions[intervention.intervention_id] = intervention
        await self._execute_intervention(intervention)
        
        logger.info(f"Created reinforcement intervention for positive behavior: "
                   f"{classification.behavior_id}")
        
        return intervention
        
    async def _create_corrective_intervention(self,
                                             classification: BehaviorClassification,
                                             behavior_data: Dict[str, Any]) -> Intervention:
        """Create corrective intervention for negative behavior"""
        # Select intervention type based on severity
        if classification.severity == BehaviorSeverity.CRITICAL:
            intervention_type = InterventionType.SUPPRESSION
            duration = timedelta(minutes=30)
        elif classification.severity == BehaviorSeverity.HIGH:
            intervention_type = InterventionType.CORRECTION
            duration = timedelta(hours=1)
        else:
            intervention_type = InterventionType.GUIDANCE
            duration = timedelta(hours=2)
            
        intervention = Intervention(
            intervention_type=intervention_type,
            target_behavior_id=classification.behavior_id,
            target_agents=behavior_data.get("affected_agents", []),
            target_teams=behavior_data.get("affected_teams", []),
            duration=duration,
            parameters={
                "severity": classification.severity.value,
                "method": "gradual_correction",
                "constraints": self._get_intervention_constraints(classification)
            },
            status="active"
        )
        
        # Store and execute intervention
        self.active_interventions[intervention.intervention_id] = intervention
        await self._execute_intervention(intervention)
        
        logger.warning(f"Created {intervention_type.value} intervention for negative behavior: "
                      f"{classification.behavior_id}")
        
        return intervention
        
    def _get_intervention_constraints(self, classification: BehaviorClassification) -> Dict:
        """Get constraints for intervention based on classification"""
        constraints = {
            "max_impact": 0.5,  # Maximum impact on agent autonomy
            "gradual": True,    # Apply gradually
            "reversible": True  # Can be reversed if ineffective
        }
        
        if classification.severity == BehaviorSeverity.CRITICAL:
            constraints["max_impact"] = 0.9
            constraints["gradual"] = False
            
        elif classification.severity == BehaviorSeverity.HIGH:
            constraints["max_impact"] = 0.7
            
        return constraints
        
    async def _execute_intervention(self, intervention: Intervention):
        """Execute an intervention"""
        # Check for registered callback
        if intervention.intervention_type in self.intervention_callbacks:
            callback = self.intervention_callbacks[intervention.intervention_type]
            try:
                await callback(intervention)
                logger.info(f"Executed intervention {intervention.intervention_id} "
                          f"via callback")
            except Exception as e:
                logger.error(f"Error executing intervention callback: {e}")
                intervention.status = "failed"
                return
                
        # Default intervention actions
        if intervention.intervention_type == InterventionType.REINFORCEMENT:
            await self._execute_reinforcement(intervention)
        elif intervention.intervention_type == InterventionType.GUIDANCE:
            await self._execute_guidance(intervention)
        elif intervention.intervention_type == InterventionType.CORRECTION:
            await self._execute_correction(intervention)
        elif intervention.intervention_type == InterventionType.SUPPRESSION:
            await self._execute_suppression(intervention)
        elif intervention.intervention_type == InterventionType.ISOLATION:
            await self._execute_isolation(intervention)
        elif intervention.intervention_type == InterventionType.REWARD:
            await self._execute_reward(intervention)
        elif intervention.intervention_type == InterventionType.PENALTY:
            await self._execute_penalty(intervention)
        elif intervention.intervention_type == InterventionType.EDUCATION:
            await self._execute_education(intervention)
        elif intervention.intervention_type == InterventionType.RESTRUCTURING:
            await self._execute_restructuring(intervention)
        else:
            # MONITORING type - no active intervention needed
            logger.info(f"Monitoring behavior: {intervention.target_behavior_id}")
            
    async def _execute_reinforcement(self, intervention: Intervention):
        """Execute reinforcement intervention"""
        logger.info(f"Reinforcing positive behavior for agents: {intervention.target_agents}")
        
        # Simulate reinforcement actions
        intervention.outcomes = {
            "feedback_sent": True,
            "rewards_allocated": intervention.parameters.get("rewards", []),
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_guidance(self, intervention: Intervention):
        """Execute guidance intervention"""
        logger.info(f"Providing guidance to agents: {intervention.target_agents}")
        
        # Simulate guidance actions
        intervention.outcomes = {
            "guidance_type": "suggestion",
            "guidance_content": "Consider alternative collaboration patterns",
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_correction(self, intervention: Intervention):
        """Execute correction intervention"""
        logger.warning(f"Applying correction to agents: {intervention.target_agents}")
        
        # Simulate correction actions
        intervention.outcomes = {
            "correction_applied": True,
            "constraints_added": intervention.parameters.get("constraints", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_suppression(self, intervention: Intervention):
        """Execute suppression intervention"""
        logger.warning(f"Suppressing behavior for agents: {intervention.target_agents}")
        
        # Simulate suppression actions
        intervention.outcomes = {
            "suppression_active": True,
            "suppression_level": intervention.parameters.get("severity", "medium"),
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_isolation(self, intervention: Intervention):
        """Execute isolation intervention"""
        logger.warning(f"Isolating agents: {intervention.target_agents}")
        
        # Simulate isolation actions
        intervention.outcomes = {
            "isolation_active": True,
            "communication_restricted": True,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_reward(self, intervention: Intervention):
        """Execute reward intervention"""
        logger.info(f"Rewarding agents: {intervention.target_agents}")
        
        # Simulate reward actions
        intervention.outcomes = {
            "rewards_given": intervention.parameters.get("rewards", ["recognition"]),
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_penalty(self, intervention: Intervention):
        """Execute penalty intervention"""
        logger.warning(f"Applying penalty to agents: {intervention.target_agents}")
        
        # Simulate penalty actions
        intervention.outcomes = {
            "penalty_applied": True,
            "penalty_type": "resource_limitation",
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_education(self, intervention: Intervention):
        """Execute education intervention"""
        logger.info(f"Providing education to agents: {intervention.target_agents}")
        
        # Simulate education actions
        intervention.outcomes = {
            "education_provided": True,
            "topics": ["collaboration_best_practices", "conflict_resolution"],
            "timestamp": datetime.now().isoformat()
        }
        
    async def _execute_restructuring(self, intervention: Intervention):
        """Execute restructuring intervention"""
        logger.warning(f"Restructuring teams: {intervention.target_teams}")
        
        # Simulate restructuring actions
        intervention.outcomes = {
            "restructuring_initiated": True,
            "restructuring_type": "role_reassignment",
            "timestamp": datetime.now().isoformat()
        }
        
    async def _intervention_monitor_loop(self):
        """Monitor active interventions"""
        while self.running:
            try:
                current_time = datetime.now()
                completed_interventions = []
                
                for intervention_id, intervention in self.active_interventions.items():
                    # Check if intervention duration has elapsed
                    if intervention.duration:
                        elapsed = current_time - intervention.initiated_at
                        if elapsed >= intervention.duration:
                            intervention.status = "completed"
                            completed_interventions.append(intervention_id)
                            logger.info(f"Intervention {intervention_id} completed")
                            
                # Move completed interventions to history
                for intervention_id in completed_interventions:
                    intervention = self.active_interventions.pop(intervention_id)
                    self.intervention_history.append(intervention)
                    
            except Exception as e:
                logger.error(f"Error in intervention monitoring: {e}")
                
            await asyncio.sleep(30)  # Check every 30 seconds
            
    async def _effectiveness_evaluation_loop(self):
        """Evaluate intervention effectiveness"""
        while self.running:
            try:
                # Evaluate completed interventions
                for intervention in self.intervention_history[-10:]:  # Last 10 interventions
                    if intervention.effectiveness is None:
                        effectiveness = await self._evaluate_intervention_effectiveness(
                            intervention
                        )
                        intervention.effectiveness = effectiveness
                        
                        # Track effectiveness by type
                        self.intervention_effectiveness[
                            intervention.intervention_type
                        ].append(effectiveness)
                        
                        logger.info(f"Intervention {intervention.intervention_id} "
                                  f"effectiveness: {effectiveness:.2f}")
                        
            except Exception as e:
                logger.error(f"Error in effectiveness evaluation: {e}")
                
            await asyncio.sleep(60)  # Evaluate every minute
            
    async def _evaluate_intervention_effectiveness(self, 
                                                  intervention: Intervention) -> float:
        """
        Evaluate the effectiveness of an intervention
        
        Args:
            intervention: The intervention to evaluate
            
        Returns:
            Effectiveness score (0.0 to 1.0)
        """
        # In production, this would analyze actual behavior changes
        # For now, simulate effectiveness based on intervention type
        
        base_effectiveness = {
            InterventionType.REINFORCEMENT: 0.8,
            InterventionType.GUIDANCE: 0.7,
            InterventionType.CORRECTION: 0.6,
            InterventionType.SUPPRESSION: 0.5,
            InterventionType.ISOLATION: 0.4,
            InterventionType.REWARD: 0.85,
            InterventionType.PENALTY: 0.45,
            InterventionType.EDUCATION: 0.75,
            InterventionType.RESTRUCTURING: 0.65,
            InterventionType.MONITORING: 0.3
        }
        
        effectiveness = base_effectiveness.get(intervention.intervention_type, 0.5)
        
        # Adjust based on intervention outcomes
        if intervention.outcomes:
            if "failed" in str(intervention.outcomes).lower():
                effectiveness *= 0.5
            elif "success" in str(intervention.outcomes).lower():
                effectiveness = min(effectiveness * 1.2, 1.0)
                
        return effectiveness
        
    def register_intervention_callback(self, 
                                      intervention_type: InterventionType,
                                      callback: Callable):
        """
        Register a callback for a specific intervention type
        
        Args:
            intervention_type: The type of intervention
            callback: Async function to call when intervention is executed
        """
        self.intervention_callbacks[intervention_type] = callback
        logger.info(f"Registered callback for {intervention_type.value}")
        
    def get_intervention_statistics(self) -> Dict[str, Any]:
        """Get statistics about interventions"""
        stats = {
            "active_interventions": len(self.active_interventions),
            "completed_interventions": len(self.intervention_history),
            "intervention_types": {},
            "average_effectiveness": {},
            "classification_distribution": {
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "unknown": 0
            }
        }
        
        # Count intervention types
        for intervention in self.intervention_history:
            intervention_type = intervention.intervention_type.value
            stats["intervention_types"][intervention_type] = \
                stats["intervention_types"].get(intervention_type, 0) + 1
                
        # Calculate average effectiveness
        for intervention_type, scores in self.intervention_effectiveness.items():
            if scores:
                stats["average_effectiveness"][intervention_type.value] = \
                    statistics.mean(scores)
                    
        # Count classifications
        for classification in self.classifications:
            category = classification.category.value
            stats["classification_distribution"][category] += 1
            
        return stats
        
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations based on classification and intervention history"""
        recommendations = []
        
        # Analyze intervention effectiveness
        for intervention_type, scores in self.intervention_effectiveness.items():
            if scores and len(scores) >= 5:
                avg_effectiveness = statistics.mean(scores)
                
                if avg_effectiveness < 0.4:
                    recommendations.append({
                        "type": "intervention_improvement",
                        "intervention": intervention_type.value,
                        "current_effectiveness": avg_effectiveness,
                        "recommendation": f"Consider alternative to {intervention_type.value} "
                                        f"interventions due to low effectiveness"
                    })
                elif avg_effectiveness > 0.8:
                    recommendations.append({
                        "type": "intervention_success",
                        "intervention": intervention_type.value,
                        "current_effectiveness": avg_effectiveness,
                        "recommendation": f"Continue using {intervention_type.value} "
                                        f"interventions due to high effectiveness"
                    })
                    
        # Analyze classification patterns
        if len(self.classifications) > 20:
            recent_negative = sum(1 for c in self.classifications[-20:]
                                if c.category == BehaviorCategory.NEGATIVE)
            if recent_negative > 10:
                recommendations.append({
                    "type": "behavior_alert",
                    "severity": "high",
                    "recommendation": "High rate of negative behaviors detected. "
                                    "Consider system-wide review and adjustment."
                })
                
        return recommendations
        
    def export_data(self) -> Dict[str, Any]:
        """Export classifier data for analysis"""
        return {
            "classifications": [asdict(c) for c in self.classifications[-100:]],
            "active_interventions": {
                k: asdict(v) for k, v in self.active_interventions.items()
            },
            "intervention_history": [asdict(i) for i in self.intervention_history[-50:]],
            "statistics": self.get_intervention_statistics(),
            "recommendations": self.get_recommendations(),
            "rules": [
                {
                    "name": r.name,
                    "category": r.category.value,
                    "severity": r.severity.value,
                    "priority": r.priority
                }
                for r in self.rules
            ]
        }


# Integration with EmergenceMonitor
async def process_detected_patterns(classifier: BehaviorClassifier,
                                   patterns: List[Dict[str, Any]]):
    """Process patterns detected by EmergenceMonitor"""
    for pattern in patterns:
        # Prepare behavior data
        behavior_data = {
            "behavior_id": pattern.get("pattern_id", str(uuid4())),
            "pattern_type": pattern.get("pattern_type", "unknown"),
            "confidence": pattern.get("confidence", 0.5),
            "affected_agents": pattern.get("affected_agents", []),
            "affected_teams": pattern.get("affected_teams", []),
            "evidence": pattern.get("evidence", {})
        }
        
        # Classify behavior
        classification = classifier.classify_behavior(behavior_data)
        
        # Create intervention if needed
        if classification.recommended_interventions:
            await classifier.create_intervention(classification, behavior_data)


# Example usage and testing
async def test_behavior_classifier():
    """Test the behavior classifier"""
    classifier = BehaviorClassifier()
    
    # Start classifier
    classifier_task = asyncio.create_task(classifier.start_classification())
    
    # Simulate different behaviors
    test_behaviors = [
        {
            "behavior_id": "test_1",
            "pattern_type": "collaboration_increase",
            "confidence": 0.8,
            "affected_agents": ["agent_1", "agent_2", "agent_3"],
            "affected_teams": ["team_a"]
        },
        {
            "behavior_id": "test_2",
            "pattern_type": "resource_competition",
            "confidence": 0.75,
            "affected_agents": ["agent_4", "agent_5"],
            "affected_teams": ["team_b"]
        },
        {
            "behavior_id": "test_3",
            "pattern_type": "innovation_burst",
            "confidence": 0.9,
            "affected_agents": ["agent_6", "agent_7", "agent_8"],
            "affected_teams": ["team_c"]
        },
        {
            "behavior_id": "test_4",
            "pattern_type": "conflict_pattern",
            "confidence": 0.7,
            "affected_agents": ["agent_9", "agent_10"],
            "affected_teams": ["team_a", "team_b"]
        }
    ]
    
    # Process behaviors
    for behavior_data in test_behaviors:
        classification = classifier.classify_behavior(behavior_data)
        print(f"\nBehavior: {behavior_data['pattern_type']}")
        print(f"Classification: {classification.category.value}")
        print(f"Severity: {classification.severity.value}")
        print(f"Confidence: {classification.confidence:.2f}")
        print(f"Recommended interventions: {[i.value for i in classification.recommended_interventions]}")
        
        # Create intervention
        intervention = await classifier.create_intervention(classification, behavior_data)
        if intervention:
            print(f"Created intervention: {intervention.intervention_type.value}")
            
    # Wait for some processing
    await asyncio.sleep(5)
    
    # Get statistics
    stats = classifier.get_intervention_statistics()
    print("\nIntervention Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Get recommendations
    recommendations = classifier.get_recommendations()
    print("\nRecommendations:")
    for rec in recommendations:
        print(f"- {rec['recommendation']}")
        
    # Stop classifier
    await classifier.stop_classification()
    classifier_task.cancel()
    
    return classifier


if __name__ == "__main__":
    # Run test
    classifier = asyncio.run(test_behavior_classifier())
    
    # Export data
    data = classifier.export_data()
    with open("classifier_data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
        
    print(f"\nProcessed {len(classifier.classifications)} classifications")
    print(f"Created {len(classifier.intervention_history)} interventions")