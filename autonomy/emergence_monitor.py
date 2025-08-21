"""
Emergent Behavior Monitoring System

This module monitors and tracks emergent behaviors in autonomous AI teams,
detecting patterns, anomalies, and collective behaviors that arise from
individual agent interactions.
"""

import asyncio
import json
import logging
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Deque
from uuid import uuid4
import math
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BehaviorPattern(Enum):
    """Types of behavior patterns that can emerge"""
    COLLABORATION_INCREASE = "collaboration_increase"
    COLLABORATION_DECREASE = "collaboration_decrease"
    SPECIALIZATION_EMERGENCE = "specialization_emergence"
    GENERALIZATION_TREND = "generalization_trend"
    COMMUNICATION_CLUSTERING = "communication_clustering"
    DECISION_CONVERGENCE = "decision_convergence"
    DECISION_DIVERGENCE = "decision_divergence"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    RESOURCE_COMPETITION = "resource_competition"
    KNOWLEDGE_SHARING = "knowledge_sharing"
    KNOWLEDGE_HOARDING = "knowledge_hoarding"
    TASK_PREFERENCE_SHIFT = "task_preference_shift"
    INNOVATION_BURST = "innovation_burst"
    ROUTINE_FORMATION = "routine_formation"
    CONFLICT_PATTERN = "conflict_pattern"
    CONSENSUS_BUILDING = "consensus_building"


class MetricType(Enum):
    """Types of metrics to track"""
    COMMUNICATION_FREQUENCY = "communication_frequency"
    DECISION_ALIGNMENT = "decision_alignment"
    TASK_DISTRIBUTION = "task_distribution"
    RESOURCE_UTILIZATION = "resource_utilization"
    KNOWLEDGE_FLOW = "knowledge_flow"
    TEAM_COHESION = "team_cohesion"
    INNOVATION_RATE = "innovation_rate"
    CONFLICT_FREQUENCY = "conflict_frequency"
    PERFORMANCE_VARIANCE = "performance_variance"
    ADAPTATION_SPEED = "adaptation_speed"


class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    STATISTICAL = "statistical"      # Statistical outliers
    STRUCTURAL = "structural"        # Structural changes in interaction patterns
    TEMPORAL = "temporal"           # Time-based anomalies
    BEHAVIORAL = "behavioral"       # Behavioral deviations
    PERFORMANCE = "performance"     # Performance anomalies


@dataclass
class BehaviorEvent:
    """Represents a single behavior event"""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: str = ""
    team_id: str = ""
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternDetection:
    """Represents a detected pattern"""
    pattern_id: str = field(default_factory=lambda: str(uuid4()))
    pattern_type: BehaviorPattern = BehaviorPattern.COLLABORATION_INCREASE
    confidence: float = 0.0
    detected_at: datetime = field(default_factory=datetime.now)
    affected_agents: List[str] = field(default_factory=list)
    affected_teams: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    duration: Optional[timedelta] = None
    frequency: int = 0
    impact_score: float = 0.0


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    anomaly_id: str = field(default_factory=lambda: str(uuid4()))
    anomaly_type: AnomalyType = AnomalyType.STATISTICAL
    severity: float = 0.0  # 0.0 to 1.0
    detected_at: datetime = field(default_factory=datetime.now)
    metric_type: Optional[MetricType] = None
    expected_value: Any = None
    actual_value: Any = None
    deviation: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergentBehavior:
    """Represents an emergent behavior"""
    behavior_id: str = field(default_factory=lambda: str(uuid4()))
    behavior_type: str = ""
    emergence_time: datetime = field(default_factory=datetime.now)
    stability: float = 0.0  # How stable the behavior is (0.0 to 1.0)
    persistence: timedelta = timedelta()
    participating_agents: Set[str] = field(default_factory=set)
    characteristics: Dict[str, Any] = field(default_factory=dict)
    predictions: List[Dict[str, Any]] = field(default_factory=list)


class EmergenceMonitor:
    """Monitors and tracks emergent behaviors in AI teams"""
    
    def __init__(self, 
                 window_size: int = 1000,
                 anomaly_threshold: float = 3.0,
                 pattern_min_confidence: float = 0.7):
        """
        Initialize the emergence monitor
        
        Args:
            window_size: Size of the sliding window for analysis
            anomaly_threshold: Z-score threshold for anomaly detection
            pattern_min_confidence: Minimum confidence for pattern detection
        """
        self.window_size = window_size
        self.anomaly_threshold = anomaly_threshold
        self.pattern_min_confidence = pattern_min_confidence
        
        # Event storage
        self.events: Deque[BehaviorEvent] = deque(maxlen=window_size * 2)
        self.event_index: Dict[str, List[BehaviorEvent]] = defaultdict(list)
        
        # Metrics tracking
        self.metrics: Dict[MetricType, Deque[float]] = {
            metric: deque(maxlen=window_size) for metric in MetricType
        }
        self.metric_baselines: Dict[MetricType, Dict[str, float]] = {}
        
        # Pattern and anomaly storage
        self.detected_patterns: List[PatternDetection] = []
        self.detected_anomalies: List[Anomaly] = []
        self.emergent_behaviors: List[EmergentBehavior] = []
        
        # Agent and team tracking
        self.agent_behaviors: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'interactions': [],
            'decisions': [],
            'tasks': [],
            'performance': []
        })
        self.team_dynamics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'cohesion': 0.0,
            'communication_matrix': {},
            'decision_alignment': 0.0,
            'performance_trend': []
        })
        
        # Pattern detection cache
        self.pattern_cache: Dict[str, List[Any]] = defaultdict(list)
        self.running = False
        
    async def start_monitoring(self):
        """Start the monitoring process"""
        self.running = True
        logger.info("Emergence monitor started")
        
        # Start background tasks
        await asyncio.gather(
            self._analyze_patterns_loop(),
            self._detect_anomalies_loop(),
            self._track_emergence_loop(),
            self._cleanup_loop()
        )
        
    async def stop_monitoring(self):
        """Stop the monitoring process"""
        self.running = False
        logger.info("Emergence monitor stopped")
        
    def record_event(self, event: BehaviorEvent):
        """
        Record a behavior event
        
        Args:
            event: The behavior event to record
        """
        self.events.append(event)
        self.event_index[event.agent_id].append(event)
        
        # Update metrics based on event
        self._update_metrics(event)
        
        logger.debug(f"Recorded event: {event.event_type} from {event.agent_id}")
        
    def _update_metrics(self, event: BehaviorEvent):
        """Update metrics based on event"""
        # Update communication frequency
        if event.event_type == "communication":
            current_freq = len([e for e in list(self.events)[-100:] 
                               if e.event_type == "communication"])
            self.metrics[MetricType.COMMUNICATION_FREQUENCY].append(current_freq)
            
        # Update decision alignment
        elif event.event_type == "decision":
            alignment = event.event_data.get("alignment_score", 0.5)
            self.metrics[MetricType.DECISION_ALIGNMENT].append(alignment)
            
        # Update resource utilization
        elif event.event_type == "resource_usage":
            utilization = event.event_data.get("utilization", 0.0)
            self.metrics[MetricType.RESOURCE_UTILIZATION].append(utilization)
            
        # Update innovation rate
        elif event.event_type == "innovation":
            recent_innovations = len([e for e in list(self.events)[-500:] 
                                     if e.event_type == "innovation"])
            rate = recent_innovations / 500.0
            self.metrics[MetricType.INNOVATION_RATE].append(rate)
            
    async def _analyze_patterns_loop(self):
        """Background task to analyze patterns"""
        while self.running:
            try:
                patterns = await self._detect_patterns()
                for pattern in patterns:
                    if pattern.confidence >= self.pattern_min_confidence:
                        self.detected_patterns.append(pattern)
                        logger.info(f"Detected pattern: {pattern.pattern_type.value} "
                                  f"with confidence {pattern.confidence:.2f}")
                        
                        # Trigger intervention if needed
                        await self._evaluate_pattern_intervention(pattern)
                        
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
                
            await asyncio.sleep(10)  # Analyze every 10 seconds
            
    async def _detect_patterns(self) -> List[PatternDetection]:
        """Detect patterns in behavior"""
        patterns = []
        
        # Check for collaboration changes
        collab_pattern = await self._detect_collaboration_pattern()
        if collab_pattern:
            patterns.append(collab_pattern)
            
        # Check for specialization emergence
        spec_pattern = await self._detect_specialization_pattern()
        if spec_pattern:
            patterns.append(spec_pattern)
            
        # Check for communication clustering
        comm_pattern = await self._detect_communication_clustering()
        if comm_pattern:
            patterns.append(comm_pattern)
            
        # Check for decision convergence/divergence
        decision_pattern = await self._detect_decision_pattern()
        if decision_pattern:
            patterns.append(decision_pattern)
            
        # Check for resource patterns
        resource_pattern = await self._detect_resource_pattern()
        if resource_pattern:
            patterns.append(resource_pattern)
            
        # Check for innovation patterns
        innovation_pattern = await self._detect_innovation_pattern()
        if innovation_pattern:
            patterns.append(innovation_pattern)
            
        return patterns
        
    async def _detect_collaboration_pattern(self) -> Optional[PatternDetection]:
        """Detect collaboration patterns"""
        if len(self.events) < 100:
            return None
            
        recent_events = list(self.events)[-500:]
        collab_events = [e for e in recent_events 
                        if e.event_type in ["collaboration", "teamwork", "cooperation"]]
        
        if len(collab_events) < 10:
            return None
            
        # Calculate collaboration trend
        time_windows = 5
        window_size = len(collab_events) // time_windows
        trends = []
        
        for i in range(time_windows):
            start = i * window_size
            end = (i + 1) * window_size
            window_events = collab_events[start:end]
            trends.append(len(window_events))
            
        # Detect trend direction
        if HAS_NUMPY:
            correlation = np.corrcoef(range(len(trends)), trends)[0, 1]
        else:
            # Simple correlation without numpy
            x = list(range(len(trends)))
            n = len(trends)
            x_mean = sum(x) / n
            y_mean = sum(trends) / n
            
            numerator = sum((x[i] - x_mean) * (trends[i] - y_mean) for i in range(n))
            denominator = math.sqrt(sum((x[i] - x_mean)**2 for i in range(n)) * 
                                   sum((trends[i] - y_mean)**2 for i in range(n)))
            
            correlation = numerator / denominator if denominator != 0 else 0
        
        if abs(correlation) > 0.7:
            pattern_type = (BehaviorPattern.COLLABORATION_INCREASE 
                           if correlation > 0 
                           else BehaviorPattern.COLLABORATION_DECREASE)
                           
            affected_agents = list(set(e.agent_id for e in collab_events))
            affected_teams = list(set(e.team_id for e in collab_events))
            
            return PatternDetection(
                pattern_type=pattern_type,
                confidence=abs(correlation),
                affected_agents=affected_agents,
                affected_teams=affected_teams,
                evidence=[{"trend": trends, "correlation": correlation}],
                frequency=len(collab_events),
                impact_score=abs(correlation) * len(affected_agents) / 100
            )
            
        return None
        
    async def _detect_specialization_pattern(self) -> Optional[PatternDetection]:
        """Detect specialization emergence"""
        # Analyze task distribution per agent
        agent_tasks = defaultdict(lambda: defaultdict(int))
        
        for event in list(self.events)[-1000:]:
            if event.event_type == "task_assignment":
                task_type = event.event_data.get("task_type", "unknown")
                agent_tasks[event.agent_id][task_type] += 1
                
        # Calculate specialization scores
        specialization_scores = {}
        for agent_id, tasks in agent_tasks.items():
            if sum(tasks.values()) > 10:
                # Calculate entropy as measure of specialization
                total = sum(tasks.values())
                probs = [count/total for count in tasks.values()]
                entropy = -sum(p * math.log(p) if p > 0 else 0 for p in probs)
                specialization_scores[agent_id] = 1 - (entropy / math.log(len(tasks)))
                
        # Detect emerging specialization
        if specialization_scores:
            avg_specialization = statistics.mean(specialization_scores.values())
            if avg_specialization > 0.6:
                return PatternDetection(
                    pattern_type=BehaviorPattern.SPECIALIZATION_EMERGENCE,
                    confidence=avg_specialization,
                    affected_agents=list(specialization_scores.keys()),
                    evidence=[{"specialization_scores": specialization_scores}],
                    impact_score=avg_specialization * len(specialization_scores)
                )
                
        return None
        
    async def _detect_communication_clustering(self) -> Optional[PatternDetection]:
        """Detect communication clustering patterns"""
        comm_matrix = defaultdict(lambda: defaultdict(int))
        
        for event in list(self.events)[-500:]:
            if event.event_type == "communication":
                sender = event.agent_id
                receiver = event.event_data.get("receiver", "")
                if receiver:
                    comm_matrix[sender][receiver] += 1
                    
        # Detect clusters using simple threshold
        clusters = []
        processed = set()
        
        for sender, receivers in comm_matrix.items():
            if sender not in processed:
                cluster = {sender}
                for receiver, count in receivers.items():
                    if count > 5:  # Threshold for cluster membership
                        cluster.add(receiver)
                        
                if len(cluster) > 2:
                    clusters.append(cluster)
                    processed.update(cluster)
                    
        if clusters:
            return PatternDetection(
                pattern_type=BehaviorPattern.COMMUNICATION_CLUSTERING,
                confidence=0.8 if len(clusters) > 1 else 0.6,
                affected_agents=list(set.union(*clusters)),
                evidence=[{"clusters": [list(c) for c in clusters]}],
                impact_score=len(clusters) * 0.3
            )
            
        return None
        
    async def _detect_decision_pattern(self) -> Optional[PatternDetection]:
        """Detect decision convergence or divergence"""
        decision_alignments = []
        
        for event in list(self.events)[-200:]:
            if event.event_type == "decision":
                alignment = event.event_data.get("alignment_score", 0.5)
                decision_alignments.append(alignment)
                
        if len(decision_alignments) > 20:
            # Calculate trend
            recent = statistics.mean(decision_alignments[-10:])
            older = statistics.mean(decision_alignments[:10])
            change = recent - older
            
            if abs(change) > 0.2:
                pattern_type = (BehaviorPattern.DECISION_CONVERGENCE 
                               if change > 0 
                               else BehaviorPattern.DECISION_DIVERGENCE)
                               
                return PatternDetection(
                    pattern_type=pattern_type,
                    confidence=min(abs(change) * 2, 1.0),
                    evidence=[{"alignment_trend": decision_alignments,
                             "change": change}],
                    impact_score=abs(change) * 2
                )
                
        return None
        
    async def _detect_resource_pattern(self) -> Optional[PatternDetection]:
        """Detect resource utilization patterns"""
        if MetricType.RESOURCE_UTILIZATION not in self.metrics:
            return None
            
        utilization = list(self.metrics[MetricType.RESOURCE_UTILIZATION])
        if len(utilization) < 50:
            return None
            
        # Check for optimization or competition
        recent_avg = statistics.mean(utilization[-20:]) if utilization[-20:] else 0
        older_avg = statistics.mean(utilization[:20]) if utilization[:20] else 0
        variance = statistics.variance(utilization) if len(utilization) > 1 else 0
        
        if recent_avg < older_avg - 0.1 and variance < 0.1:
            # Resource optimization detected
            return PatternDetection(
                pattern_type=BehaviorPattern.RESOURCE_OPTIMIZATION,
                confidence=0.8,
                evidence=[{"recent_avg": recent_avg, "older_avg": older_avg,
                         "variance": variance}],
                impact_score=0.7
            )
        elif variance > 0.3:
            # Resource competition detected
            return PatternDetection(
                pattern_type=BehaviorPattern.RESOURCE_COMPETITION,
                confidence=min(variance * 2, 1.0),
                evidence=[{"variance": variance}],
                impact_score=variance * 1.5
            )
            
        return None
        
    async def _detect_innovation_pattern(self) -> Optional[PatternDetection]:
        """Detect innovation patterns"""
        innovation_events = [e for e in list(self.events)[-1000:]
                           if e.event_type == "innovation"]
                           
        if len(innovation_events) < 5:
            return None
            
        # Calculate innovation rate over time
        time_buckets = defaultdict(int)
        for event in innovation_events:
            bucket = event.timestamp.replace(minute=0, second=0, microsecond=0)
            time_buckets[bucket] += 1
            
        if len(time_buckets) > 3:
            rates = list(time_buckets.values())
            avg_rate = statistics.mean(rates)
            recent_rate = rates[-1] if rates else 0
            
            if recent_rate > avg_rate * 2:
                return PatternDetection(
                    pattern_type=BehaviorPattern.INNOVATION_BURST,
                    confidence=min(recent_rate / (avg_rate + 0.1), 1.0),
                    evidence=[{"rates": rates, "recent": recent_rate,
                             "average": avg_rate}],
                    impact_score=0.9
                )
                
        return None
        
    async def _detect_anomalies_loop(self):
        """Background task to detect anomalies"""
        while self.running:
            try:
                anomalies = await self._detect_anomalies()
                for anomaly in anomalies:
                    self.detected_anomalies.append(anomaly)
                    logger.warning(f"Detected anomaly: {anomaly.anomaly_type.value} "
                                 f"with severity {anomaly.severity:.2f}")
                    
                    # Trigger alerts for high severity
                    if anomaly.severity > 0.8:
                        await self._alert_anomaly(anomaly)
                        
            except Exception as e:
                logger.error(f"Error in anomaly detection: {e}")
                
            await asyncio.sleep(5)  # Check every 5 seconds
            
    async def _detect_anomalies(self) -> List[Anomaly]:
        """Detect anomalies in metrics"""
        anomalies = []
        
        for metric_type, values in self.metrics.items():
            if len(values) < 20:
                continue
                
            # Statistical anomaly detection (Z-score)
            values_list = list(values)
            mean = statistics.mean(values_list)
            stdev = statistics.stdev(values_list) if len(values_list) > 1 else 0
            
            if stdev > 0:
                recent_value = values_list[-1] if values_list else 0
                z_score = abs((recent_value - mean) / stdev)
                
                if z_score > self.anomaly_threshold:
                    anomaly = Anomaly(
                        anomaly_type=AnomalyType.STATISTICAL,
                        severity=min(z_score / 5.0, 1.0),
                        metric_type=metric_type,
                        expected_value=mean,
                        actual_value=recent_value,
                        deviation=z_score,
                        context={"z_score": z_score, "threshold": self.anomaly_threshold}
                    )
                    anomalies.append(anomaly)
                    
        # Detect structural anomalies
        structural_anomaly = await self._detect_structural_anomaly()
        if structural_anomaly:
            anomalies.append(structural_anomaly)
            
        # Detect temporal anomalies
        temporal_anomaly = await self._detect_temporal_anomaly()
        if temporal_anomaly:
            anomalies.append(temporal_anomaly)
            
        return anomalies
        
    async def _detect_structural_anomaly(self) -> Optional[Anomaly]:
        """Detect structural anomalies in interaction patterns"""
        # Analyze communication structure changes
        recent_structure = self._calculate_communication_structure(
            list(self.events)[-200:]
        )
        older_structure = self._calculate_communication_structure(
            list(self.events)[-400:-200]
        )
        
        if recent_structure and older_structure:
            # Compare structures
            structure_change = self._compare_structures(recent_structure, older_structure)
            
            if structure_change > 0.5:
                return Anomaly(
                    anomaly_type=AnomalyType.STRUCTURAL,
                    severity=min(structure_change, 1.0),
                    context={
                        "recent_structure": recent_structure,
                        "older_structure": older_structure,
                        "change_magnitude": structure_change
                    }
                )
                
        return None
        
    def _calculate_communication_structure(self, events: List[BehaviorEvent]) -> Dict:
        """Calculate communication structure from events"""
        structure = {
            "nodes": set(),
            "edges": defaultdict(int),
            "density": 0.0
        }
        
        for event in events:
            if event.event_type == "communication":
                sender = event.agent_id
                receiver = event.event_data.get("receiver", "")
                if receiver:
                    structure["nodes"].add(sender)
                    structure["nodes"].add(receiver)
                    structure["edges"][(sender, receiver)] += 1
                    
        # Calculate density
        if len(structure["nodes"]) > 1:
            max_edges = len(structure["nodes"]) * (len(structure["nodes"]) - 1)
            structure["density"] = len(structure["edges"]) / max_edges
            
        return structure
        
    def _compare_structures(self, struct1: Dict, struct2: Dict) -> float:
        """Compare two communication structures"""
        # Simple comparison based on node and edge differences
        node_diff = len(struct1["nodes"].symmetric_difference(struct2["nodes"]))
        edge_diff = len(set(struct1["edges"].keys()).symmetric_difference(
            set(struct2["edges"].keys())))
        density_diff = abs(struct1["density"] - struct2["density"])
        
        # Normalize and combine differences
        total_diff = (node_diff / 10.0 + edge_diff / 20.0 + density_diff) / 3
        return min(total_diff, 1.0)
        
    async def _detect_temporal_anomaly(self) -> Optional[Anomaly]:
        """Detect temporal anomalies in event patterns"""
        # Check for unusual timing patterns
        event_times = [e.timestamp for e in list(self.events)[-100:]]
        if len(event_times) < 10:
            return None
            
        # Calculate inter-event times
        inter_times = []
        for i in range(1, len(event_times)):
            delta = (event_times[i] - event_times[i-1]).total_seconds()
            inter_times.append(delta)
            
        if inter_times:
            mean_time = statistics.mean(inter_times)
            stdev_time = statistics.stdev(inter_times) if len(inter_times) > 1 else 0
            
            # Check for temporal anomalies
            if stdev_time > mean_time * 2:
                return Anomaly(
                    anomaly_type=AnomalyType.TEMPORAL,
                    severity=min(stdev_time / (mean_time + 1), 1.0),
                    context={
                        "mean_inter_time": mean_time,
                        "stdev_inter_time": stdev_time,
                        "coefficient_variation": stdev_time / (mean_time + 0.01)
                    }
                )
                
        return None
        
    async def _track_emergence_loop(self):
        """Background task to track emergent behaviors"""
        while self.running:
            try:
                # Identify emergent behaviors from patterns
                await self._identify_emergent_behaviors()
                
                # Update existing emergent behaviors
                await self._update_emergent_behaviors()
                
                # Predict future behaviors
                await self._predict_behaviors()
                
            except Exception as e:
                logger.error(f"Error in emergence tracking: {e}")
                
            await asyncio.sleep(30)  # Track every 30 seconds
            
    async def _identify_emergent_behaviors(self):
        """Identify new emergent behaviors from patterns"""
        # Group related patterns
        pattern_groups = defaultdict(list)
        for pattern in self.detected_patterns[-50:]:  # Recent patterns
            pattern_groups[pattern.pattern_type.value[:10]].append(pattern)
            
        # Check for emergent behaviors
        for group_key, patterns in pattern_groups.items():
            if len(patterns) >= 3:  # Multiple related patterns
                # Check if this represents a new emergent behavior
                behavior = EmergentBehavior(
                    behavior_type=f"emergent_{group_key}",
                    stability=self._calculate_stability(patterns),
                    persistence=datetime.now() - patterns[0].detected_at,
                    participating_agents=set().union(
                        *[set(p.affected_agents) for p in patterns]
                    ),
                    characteristics={
                        "patterns": [p.pattern_type.value for p in patterns],
                        "average_confidence": statistics.mean([p.confidence for p in patterns])
                    }
                )
                
                # Check if this is a new behavior
                if not self._is_duplicate_behavior(behavior):
                    self.emergent_behaviors.append(behavior)
                    logger.info(f"Identified emergent behavior: {behavior.behavior_type}")
                    
    def _calculate_stability(self, patterns: List[PatternDetection]) -> float:
        """Calculate stability of emergent behavior"""
        if len(patterns) < 2:
            return 0.0
            
        # Check consistency over time
        time_deltas = []
        for i in range(1, len(patterns)):
            delta = (patterns[i].detected_at - patterns[i-1].detected_at).total_seconds()
            time_deltas.append(delta)
            
        if time_deltas:
            # Lower variance means higher stability
            variance = statistics.variance(time_deltas) if len(time_deltas) > 1 else 0
            stability = 1.0 / (1.0 + variance / 1000.0)
            return min(stability, 1.0)
            
        return 0.5
        
    def _is_duplicate_behavior(self, behavior: EmergentBehavior) -> bool:
        """Check if behavior already exists"""
        for existing in self.emergent_behaviors:
            if (existing.behavior_type == behavior.behavior_type and
                len(existing.participating_agents.intersection(
                    behavior.participating_agents)) > len(behavior.participating_agents) * 0.5):
                return True
        return False
        
    async def _update_emergent_behaviors(self):
        """Update existing emergent behaviors"""
        current_time = datetime.now()
        
        for behavior in self.emergent_behaviors:
            # Update persistence
            behavior.persistence = current_time - behavior.emergence_time
            
            # Update stability based on recent patterns
            recent_patterns = [p for p in self.detected_patterns
                             if current_time - p.detected_at < timedelta(minutes=10)]
            relevant_patterns = [p for p in recent_patterns
                               if any(agent in p.affected_agents 
                                     for agent in behavior.participating_agents)]
            
            if relevant_patterns:
                behavior.stability = self._calculate_stability(relevant_patterns)
                
    async def _predict_behaviors(self):
        """Predict future behaviors based on current patterns"""
        for behavior in self.emergent_behaviors:
            if behavior.stability > 0.7:
                # High stability suggests persistence
                prediction = {
                    "behavior_type": behavior.behavior_type,
                    "prediction": "persist",
                    "confidence": behavior.stability,
                    "time_horizon": "next_hour"
                }
                behavior.predictions.append(prediction)
                
            elif behavior.stability < 0.3:
                # Low stability suggests dissolution
                prediction = {
                    "behavior_type": behavior.behavior_type,
                    "prediction": "dissolve",
                    "confidence": 1.0 - behavior.stability,
                    "time_horizon": "next_30_minutes"
                }
                behavior.predictions.append(prediction)
                
    async def _cleanup_loop(self):
        """Background task to cleanup old data"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Remove old patterns
                self.detected_patterns = [
                    p for p in self.detected_patterns
                    if current_time - p.detected_at < timedelta(hours=24)
                ]
                
                # Remove old anomalies
                self.detected_anomalies = [
                    a for a in self.detected_anomalies
                    if current_time - a.detected_at < timedelta(hours=12)
                ]
                
                # Remove dissolved emergent behaviors
                self.emergent_behaviors = [
                    b for b in self.emergent_behaviors
                    if b.stability > 0.1 or current_time - b.emergence_time < timedelta(hours=1)
                ]
                
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
                
            await asyncio.sleep(3600)  # Cleanup every hour
            
    async def _evaluate_pattern_intervention(self, pattern: PatternDetection):
        """Evaluate if intervention is needed for a pattern"""
        # This would connect to the behavior classifier for intervention decisions
        pass
        
    async def _alert_anomaly(self, anomaly: Anomaly):
        """Send alert for high-severity anomaly"""
        logger.critical(f"HIGH SEVERITY ANOMALY: {anomaly.anomaly_type.value}")
        logger.critical(f"Details: {anomaly.context}")
        # In production, this would send alerts to monitoring systems
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current monitoring state"""
        return {
            "total_events": len(self.events),
            "detected_patterns": len(self.detected_patterns),
            "active_patterns": len([p for p in self.detected_patterns
                                   if (datetime.now() - p.detected_at).total_seconds() < 3600]),
            "detected_anomalies": len(self.detected_anomalies),
            "recent_anomalies": len([a for a in self.detected_anomalies
                                    if (datetime.now() - a.detected_at).total_seconds() < 1800]),
            "emergent_behaviors": len(self.emergent_behaviors),
            "stable_behaviors": len([b for b in self.emergent_behaviors if b.stability > 0.7]),
            "metrics": {
                metric.value: {
                    "current": values[-1] if values else None,
                    "mean": statistics.mean(values) if values else None,
                    "std": statistics.stdev(values) if len(values) > 1 else None
                }
                for metric, values in self.metrics.items()
                if values
            }
        }
        
    def export_data(self) -> Dict[str, Any]:
        """Export monitoring data for analysis"""
        # Convert events with proper serialization
        events_data = []
        for e in list(self.events)[-1000:]:
            event_dict = asdict(e)
            # Convert datetime to string
            event_dict['timestamp'] = event_dict['timestamp'].isoformat() if isinstance(event_dict['timestamp'], datetime) else str(event_dict['timestamp'])
            events_data.append(event_dict)
            
        # Convert patterns
        patterns_data = []
        for p in self.detected_patterns:
            pattern_dict = asdict(p)
            pattern_dict['detected_at'] = pattern_dict['detected_at'].isoformat() if isinstance(pattern_dict['detected_at'], datetime) else str(pattern_dict['detected_at'])
            pattern_dict['pattern_type'] = str(pattern_dict['pattern_type'])
            if pattern_dict.get('duration'):
                pattern_dict['duration'] = str(pattern_dict['duration'])
            patterns_data.append(pattern_dict)
            
        # Convert anomalies
        anomalies_data = []
        for a in self.detected_anomalies:
            anomaly_dict = asdict(a)
            anomaly_dict['detected_at'] = anomaly_dict['detected_at'].isoformat() if isinstance(anomaly_dict['detected_at'], datetime) else str(anomaly_dict['detected_at'])
            anomaly_dict['anomaly_type'] = str(anomaly_dict['anomaly_type'])
            if anomaly_dict.get('metric_type'):
                anomaly_dict['metric_type'] = str(anomaly_dict['metric_type'])
            # Convert defaultdict in context
            if 'context' in anomaly_dict and isinstance(anomaly_dict['context'], dict):
                for key, value in anomaly_dict['context'].items():
                    if hasattr(value, '__dict__'):
                        # Convert complex objects to dict
                        if 'edges' in value:
                            # Convert defaultdict to regular dict with string keys
                            value['edges'] = {str(k): v for k, v in dict(value['edges']).items()}
                        if 'nodes' in value:
                            value['nodes'] = list(value['nodes'])
            anomalies_data.append(anomaly_dict)
            
        return {
            "events": events_data,
            "patterns": patterns_data,
            "anomalies": anomalies_data,
            "emergent_behaviors": [
                {
                    "behavior_id": b.behavior_id,
                    "behavior_type": b.behavior_type,
                    "emergence_time": b.emergence_time.isoformat(),
                    "stability": b.stability,
                    "persistence": b.persistence.total_seconds(),
                    "participating_agents": list(b.participating_agents),
                    "characteristics": b.characteristics,
                    "predictions": b.predictions
                }
                for b in self.emergent_behaviors
            ],
            "summary": self.get_summary()
        }


# Example usage and testing
async def test_emergence_monitor():
    """Test the emergence monitor"""
    monitor = EmergenceMonitor()
    
    # Start monitoring in background
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    # Simulate events
    import random
    
    agents = [f"agent_{i}" for i in range(10)]
    teams = [f"team_{i}" for i in range(3)]
    
    for _ in range(100):
        event = BehaviorEvent(
            agent_id=random.choice(agents),
            team_id=random.choice(teams),
            event_type=random.choice(["communication", "decision", "task_assignment",
                                     "collaboration", "innovation", "resource_usage"]),
            event_data={
                "receiver": random.choice(agents) if random.random() > 0.5 else "",
                "alignment_score": random.random(),
                "task_type": random.choice(["analysis", "implementation", "review"]),
                "utilization": random.random()
            }
        )
        monitor.record_event(event)
        await asyncio.sleep(0.1)
        
    # Get summary
    summary = monitor.get_summary()
    print("Monitor Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    # Stop monitoring
    await monitor.stop_monitoring()
    monitor_task.cancel()
    
    return monitor


if __name__ == "__main__":
    # Run test
    monitor = asyncio.run(test_emergence_monitor())
    
    # Export data
    data = monitor.export_data()
    with open("emergence_data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\nDetected {len(monitor.detected_patterns)} patterns")
    print(f"Detected {len(monitor.detected_anomalies)} anomalies")
    print(f"Identified {len(monitor.emergent_behaviors)} emergent behaviors")