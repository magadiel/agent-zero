"""
Resource Tracker - Detailed resource usage monitoring for Agent-Zero

This module provides comprehensive resource tracking for agents and teams,
monitoring CPU, memory, network, and disk usage with efficiency calculations
and bottleneck detection.
"""

import time
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources tracked"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    THREADS = "threads"
    FILE_HANDLES = "file_handles"
    GPU = "gpu"  # For future GPU support


class BottleneckType(Enum):
    """Types of resource bottlenecks"""
    CPU_BOUND = "cpu_bound"
    MEMORY_BOUND = "memory_bound"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    THREAD_BOUND = "thread_bound"
    NO_BOTTLENECK = "no_bottleneck"


@dataclass
class ResourceUsage:
    """Resource usage snapshot for an agent or team"""
    entity_id: str
    entity_type: str  # "agent" or "team"
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    thread_count: int
    file_handle_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceEfficiency:
    """Resource efficiency metrics"""
    entity_id: str
    period_start: datetime
    period_end: datetime
    cpu_efficiency: float  # Useful work / CPU consumed
    memory_efficiency: float  # Active memory / Allocated memory
    io_efficiency: float  # Useful I/O / Total I/O
    overall_efficiency: float  # Weighted average
    tasks_completed: int
    resources_consumed: Dict[str, float]
    efficiency_score: float  # 0-100 score


@dataclass
class ResourceBottleneck:
    """Detected resource bottleneck"""
    entity_id: str
    bottleneck_type: BottleneckType
    severity: float  # 0-1 scale
    duration_seconds: float
    timestamp: datetime
    metrics: Dict[str, float]
    recommendations: List[str]


@dataclass
class ResourceTrend:
    """Resource usage trend analysis"""
    entity_id: str
    resource_type: ResourceType
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_rate: float  # Rate of change per hour
    current_value: float
    predicted_value_1h: float
    predicted_value_24h: float
    confidence: float  # 0-1 confidence in prediction


class ResourceTracker:
    """
    Comprehensive resource tracking system for Agent-Zero
    
    Monitors resource usage per agent and team, calculates efficiency,
    detects bottlenecks, and provides trend analysis.
    """
    
    def __init__(self,
                 sampling_interval_seconds: int = 10,
                 history_retention_hours: int = 24,
                 bottleneck_threshold: float = 0.8):
        """
        Initialize the resource tracker
        
        Args:
            sampling_interval_seconds: How often to sample resources
            history_retention_hours: How long to retain historical data
            bottleneck_threshold: Threshold for bottleneck detection (0-1)
        """
        self.sampling_interval_seconds = sampling_interval_seconds
        self.history_retention_hours = history_retention_hours
        self.bottleneck_threshold = bottleneck_threshold
        
        # Resource usage tracking
        self.agent_resources: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self.team_resources: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        
        # Process tracking for agents
        self.agent_processes: Dict[str, psutil.Process] = {}
        self.agent_to_team: Dict[str, str] = {}
        
        # Efficiency tracking
        self.efficiency_history: deque = deque(maxlen=1000)
        self.task_counts: Dict[str, int] = defaultdict(int)
        
        # Bottleneck detection
        self.active_bottlenecks: Dict[str, ResourceBottleneck] = {}
        self.bottleneck_history: deque = deque(maxlen=1000)
        
        # Trend analysis
        self.trend_window_size = 100  # Number of samples for trend analysis
        
        # Resource limits (integration with control layer)
        self.resource_limits: Dict[str, Dict[str, float]] = {}
        
        # Monitoring control
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # System baseline metrics
        self.system_baseline = self._establish_baseline()
        
        logger.info("Resource Tracker initialized")
    
    def _establish_baseline(self) -> Dict[str, float]:
        """Establish system baseline metrics"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
                "disk_total_mb": psutil.disk_usage('/').total / (1024 * 1024),
                "baseline_cpu_percent": psutil.cpu_percent(interval=1),
                "baseline_memory_percent": psutil.virtual_memory().percent
            }
        except Exception as e:
            logger.error(f"Error establishing baseline: {e}")
            return {}
    
    def register_agent(self, 
                      agent_id: str, 
                      process_id: Optional[int] = None,
                      team_id: Optional[str] = None):
        """
        Register an agent for resource tracking
        
        Args:
            agent_id: Unique agent identifier
            process_id: Optional process ID for detailed tracking
            team_id: Optional team the agent belongs to
        """
        with self._lock:
            if process_id:
                try:
                    self.agent_processes[agent_id] = psutil.Process(process_id)
                except psutil.NoSuchProcess:
                    logger.warning(f"Process {process_id} not found for agent {agent_id}")
            
            if team_id:
                self.agent_to_team[agent_id] = team_id
            
            logger.info(f"Registered agent {agent_id} for resource tracking")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from resource tracking"""
        with self._lock:
            self.agent_processes.pop(agent_id, None)
            self.agent_to_team.pop(agent_id, None)
            logger.info(f"Unregistered agent {agent_id}")
    
    def start_monitoring(self):
        """Start the resource monitoring background thread"""
        with self._lock:
            if not self._monitoring:
                self._monitoring = True
                self._monitor_thread = threading.Thread(
                    target=self._monitoring_loop,
                    daemon=True
                )
                self._monitor_thread.start()
                logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop the resource monitoring background thread"""
        with self._lock:
            if self._monitoring:
                self._monitoring = False
                if self._monitor_thread:
                    self._monitor_thread.join(timeout=5)
                logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                # Sample resources for all agents
                self._sample_agent_resources()
                
                # Aggregate team resources
                self._aggregate_team_resources()
                
                # Detect bottlenecks
                self._detect_bottlenecks()
                
                # Update trends
                self._update_trends()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep until next interval
                time.sleep(self.sampling_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sampling_interval_seconds)
    
    def _sample_agent_resources(self):
        """Sample resource usage for all registered agents"""
        timestamp = datetime.now()
        
        for agent_id, process in list(self.agent_processes.items()):
            try:
                # Get process resource usage
                with process.oneshot():
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    io_counters = process.io_counters() if hasattr(process, 'io_counters') else None
                    
                    # Get network usage (if available)
                    connections = process.connections()
                    
                    usage = ResourceUsage(
                        entity_id=agent_id,
                        entity_type="agent",
                        timestamp=timestamp,
                        cpu_percent=cpu_percent,
                        memory_mb=memory_info.rss / (1024 * 1024),
                        memory_percent=(memory_info.rss / psutil.virtual_memory().total) * 100,
                        disk_read_mb=io_counters.read_bytes / (1024 * 1024) if io_counters else 0,
                        disk_write_mb=io_counters.write_bytes / (1024 * 1024) if io_counters else 0,
                        network_sent_mb=0,  # Would need more sophisticated tracking
                        network_recv_mb=0,
                        thread_count=process.num_threads(),
                        file_handle_count=len(process.open_files()) if hasattr(process, 'open_files') else 0
                    )
                    
                    with self._lock:
                        self.agent_resources[agent_id].append(usage)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Error sampling resources for agent {agent_id}: {e}")
                # Remove dead process
                with self._lock:
                    self.agent_processes.pop(agent_id, None)
    
    def _aggregate_team_resources(self):
        """Aggregate resource usage by team"""
        timestamp = datetime.now()
        team_aggregates: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        team_agent_counts: Dict[str, int] = defaultdict(int)
        
        with self._lock:
            for agent_id, team_id in self.agent_to_team.items():
                if agent_id in self.agent_resources and self.agent_resources[agent_id]:
                    latest = self.agent_resources[agent_id][-1]
                    
                    team_aggregates[team_id]["cpu_percent"] += latest.cpu_percent
                    team_aggregates[team_id]["memory_mb"] += latest.memory_mb
                    team_aggregates[team_id]["disk_read_mb"] += latest.disk_read_mb
                    team_aggregates[team_id]["disk_write_mb"] += latest.disk_write_mb
                    team_aggregates[team_id]["thread_count"] += latest.thread_count
                    team_aggregates[team_id]["file_handle_count"] += latest.file_handle_count
                    team_agent_counts[team_id] += 1
        
        # Create team resource usage records
        for team_id, resources in team_aggregates.items():
            if team_agent_counts[team_id] > 0:
                usage = ResourceUsage(
                    entity_id=team_id,
                    entity_type="team",
                    timestamp=timestamp,
                    cpu_percent=resources["cpu_percent"],
                    memory_mb=resources["memory_mb"],
                    memory_percent=(resources["memory_mb"] / self.system_baseline.get("memory_total_mb", 1)) * 100,
                    disk_read_mb=resources["disk_read_mb"],
                    disk_write_mb=resources["disk_write_mb"],
                    network_sent_mb=0,  # Aggregated separately if needed
                    network_recv_mb=0,
                    thread_count=int(resources["thread_count"]),
                    file_handle_count=int(resources["file_handle_count"]),
                    metadata={"agent_count": team_agent_counts[team_id]}
                )
                
                with self._lock:
                    self.team_resources[team_id].append(usage)
    
    def record_task_completion(self, agent_id: str, task_success: bool = True):
        """
        Record task completion for efficiency calculations
        
        Args:
            agent_id: Agent that completed the task
            task_success: Whether the task was successful
        """
        with self._lock:
            if task_success:
                self.task_counts[agent_id] += 1
    
    def calculate_efficiency(self, 
                           entity_id: str,
                           period_minutes: int = 60) -> Optional[ResourceEfficiency]:
        """
        Calculate resource efficiency for an entity
        
        Args:
            entity_id: Agent or team ID
            period_minutes: Period to calculate efficiency over
            
        Returns:
            ResourceEfficiency object or None
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=period_minutes)
        
        # Get resource usage for the period
        with self._lock:
            if entity_id in self.agent_resources:
                resources = [r for r in self.agent_resources[entity_id]
                           if start_time <= r.timestamp <= end_time]
                entity_type = "agent"
            elif entity_id in self.team_resources:
                resources = [r for r in self.team_resources[entity_id]
                           if start_time <= r.timestamp <= end_time]
                entity_type = "team"
            else:
                return None
        
        if not resources:
            return None
        
        # Calculate average resource consumption
        avg_cpu = statistics.mean([r.cpu_percent for r in resources])
        avg_memory = statistics.mean([r.memory_mb for r in resources])
        total_io = sum([r.disk_read_mb + r.disk_write_mb for r in resources])
        
        # Get task count for the period
        tasks_completed = self.task_counts.get(entity_id, 0)
        
        # Calculate efficiency metrics
        # CPU efficiency: ratio of productive CPU time to total CPU time
        cpu_efficiency = min(1.0, tasks_completed / max(1, avg_cpu))
        
        # Memory efficiency: inverse of memory growth rate
        memory_values = [r.memory_mb for r in resources]
        memory_growth = (memory_values[-1] - memory_values[0]) / max(1, memory_values[0])
        memory_efficiency = max(0, 1 - abs(memory_growth))
        
        # I/O efficiency: tasks per MB of I/O
        io_efficiency = min(1.0, tasks_completed / max(1, total_io))
        
        # Overall efficiency score
        overall_efficiency = (cpu_efficiency * 0.4 + 
                            memory_efficiency * 0.3 + 
                            io_efficiency * 0.3)
        
        efficiency = ResourceEfficiency(
            entity_id=entity_id,
            period_start=start_time,
            period_end=end_time,
            cpu_efficiency=cpu_efficiency,
            memory_efficiency=memory_efficiency,
            io_efficiency=io_efficiency,
            overall_efficiency=overall_efficiency,
            tasks_completed=tasks_completed,
            resources_consumed={
                "cpu_hours": avg_cpu * period_minutes / 60 / 100,
                "memory_mb_hours": avg_memory * period_minutes / 60,
                "io_mb": total_io
            },
            efficiency_score=overall_efficiency * 100
        )
        
        with self._lock:
            self.efficiency_history.append(efficiency)
        
        return efficiency
    
    def _detect_bottlenecks(self):
        """Detect resource bottlenecks for all entities"""
        timestamp = datetime.now()
        
        # Check each agent
        for agent_id in list(self.agent_resources.keys()):
            bottleneck = self._check_entity_bottleneck(agent_id, "agent")
            if bottleneck:
                with self._lock:
                    self.active_bottlenecks[agent_id] = bottleneck
                    self.bottleneck_history.append(bottleneck)
            elif agent_id in self.active_bottlenecks:
                # Bottleneck resolved
                with self._lock:
                    del self.active_bottlenecks[agent_id]
        
        # Check each team
        for team_id in list(self.team_resources.keys()):
            bottleneck = self._check_entity_bottleneck(team_id, "team")
            if bottleneck:
                with self._lock:
                    self.active_bottlenecks[team_id] = bottleneck
                    self.bottleneck_history.append(bottleneck)
            elif team_id in self.active_bottlenecks:
                # Bottleneck resolved
                with self._lock:
                    del self.active_bottlenecks[team_id]
    
    def _check_entity_bottleneck(self, 
                                entity_id: str, 
                                entity_type: str) -> Optional[ResourceBottleneck]:
        """Check if an entity has a resource bottleneck"""
        # Get recent resource usage
        with self._lock:
            if entity_type == "agent":
                resources = list(self.agent_resources.get(entity_id, []))[-10:]
            else:
                resources = list(self.team_resources.get(entity_id, []))[-10:]
        
        if len(resources) < 5:
            return None
        
        # Calculate average metrics
        avg_cpu = statistics.mean([r.cpu_percent for r in resources])
        avg_memory = statistics.mean([r.memory_percent for r in resources])
        avg_io = statistics.mean([r.disk_read_mb + r.disk_write_mb for r in resources])
        avg_threads = statistics.mean([r.thread_count for r in resources])
        
        # Determine bottleneck type
        bottleneck_type = BottleneckType.NO_BOTTLENECK
        severity = 0.0
        recommendations = []
        
        # Check CPU bottleneck
        if avg_cpu > self.bottleneck_threshold * 100:
            bottleneck_type = BottleneckType.CPU_BOUND
            severity = avg_cpu / 100
            recommendations.append("Consider distributing CPU-intensive tasks")
            recommendations.append("Optimize algorithms for better CPU efficiency")
        
        # Check memory bottleneck
        elif avg_memory > self.bottleneck_threshold * 100:
            bottleneck_type = BottleneckType.MEMORY_BOUND
            severity = avg_memory / 100
            recommendations.append("Implement memory pooling or caching")
            recommendations.append("Review memory allocation patterns")
        
        # Check I/O bottleneck
        elif avg_io > 100:  # More than 100 MB/s sustained
            bottleneck_type = BottleneckType.IO_BOUND
            severity = min(1.0, avg_io / 200)
            recommendations.append("Consider batching I/O operations")
            recommendations.append("Implement asynchronous I/O where possible")
        
        # Check thread bottleneck
        elif avg_threads > 100:
            bottleneck_type = BottleneckType.THREAD_BOUND
            severity = min(1.0, avg_threads / 200)
            recommendations.append("Review thread creation patterns")
            recommendations.append("Consider using thread pools")
        
        if bottleneck_type == BottleneckType.NO_BOTTLENECK:
            return None
        
        duration = (resources[-1].timestamp - resources[0].timestamp).total_seconds()
        
        return ResourceBottleneck(
            entity_id=entity_id,
            bottleneck_type=bottleneck_type,
            severity=severity,
            duration_seconds=duration,
            timestamp=datetime.now(),
            metrics={
                "avg_cpu": avg_cpu,
                "avg_memory": avg_memory,
                "avg_io": avg_io,
                "avg_threads": avg_threads
            },
            recommendations=recommendations
        )
    
    def _update_trends(self):
        """Update resource usage trends for all entities"""
        # Update trends for agents
        for agent_id in list(self.agent_resources.keys()):
            self._calculate_entity_trends(agent_id, "agent")
        
        # Update trends for teams
        for team_id in list(self.team_resources.keys()):
            self._calculate_entity_trends(team_id, "team")
    
    def _calculate_entity_trends(self, entity_id: str, entity_type: str) -> List[ResourceTrend]:
        """Calculate resource trends for an entity"""
        trends = []
        
        with self._lock:
            if entity_type == "agent":
                resources = list(self.agent_resources.get(entity_id, []))[-self.trend_window_size:]
            else:
                resources = list(self.team_resources.get(entity_id, []))[-self.trend_window_size:]
        
        if len(resources) < 10:
            return trends
        
        # Calculate trends for each resource type
        for resource_type, attr_name in [
            (ResourceType.CPU, "cpu_percent"),
            (ResourceType.MEMORY, "memory_mb"),
            (ResourceType.DISK, "disk_read_mb")
        ]:
            values = [getattr(r, attr_name) for r in resources]
            timestamps = [(r.timestamp - resources[0].timestamp).total_seconds() / 3600 
                         for r in resources]
            
            # Simple linear regression for trend
            if len(values) > 1:
                n = len(values)
                sum_x = sum(timestamps)
                sum_y = sum(values)
                sum_xx = sum(x * x for x in timestamps)
                sum_xy = sum(x * y for x, y in zip(timestamps, values))
                
                # Calculate slope (rate of change per hour)
                denominator = (n * sum_xx - sum_x * sum_x)
                if denominator != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / denominator
                else:
                    slope = 0
                
                # Current value
                current_value = values[-1]
                
                # Predictions
                predicted_1h = current_value + slope * 1
                predicted_24h = current_value + slope * 24
                
                # Determine trend direction
                if abs(slope) < 0.01:
                    direction = "stable"
                elif slope > 0:
                    direction = "increasing"
                else:
                    direction = "decreasing"
                
                # Calculate confidence based on variance
                variance = statistics.variance(values) if len(values) > 1 else 0
                confidence = max(0, 1 - variance / (max(values) - min(values) + 1))
                
                trend = ResourceTrend(
                    entity_id=entity_id,
                    resource_type=resource_type,
                    trend_direction=direction,
                    trend_rate=slope,
                    current_value=current_value,
                    predicted_value_1h=max(0, predicted_1h),
                    predicted_value_24h=max(0, predicted_24h),
                    confidence=confidence
                )
                
                trends.append(trend)
        
        return trends
    
    def get_resource_usage(self, 
                          entity_id: str,
                          duration_minutes: Optional[int] = None) -> List[ResourceUsage]:
        """
        Get resource usage history for an entity
        
        Args:
            entity_id: Agent or team ID
            duration_minutes: How far back to look (None for all)
            
        Returns:
            List of ResourceUsage objects
        """
        with self._lock:
            if entity_id in self.agent_resources:
                resources = list(self.agent_resources[entity_id])
            elif entity_id in self.team_resources:
                resources = list(self.team_resources[entity_id])
            else:
                return []
        
        if duration_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
            resources = [r for r in resources if r.timestamp >= cutoff_time]
        
        return resources
    
    def get_resource_summary(self, entity_id: str) -> Dict[str, Any]:
        """
        Get resource usage summary for an entity
        
        Args:
            entity_id: Agent or team ID
            
        Returns:
            Dictionary with resource summary
        """
        # Get recent usage
        recent_usage = self.get_resource_usage(entity_id, duration_minutes=60)
        
        if not recent_usage:
            return {"entity_id": entity_id, "error": "No resource data available"}
        
        # Calculate statistics
        cpu_values = [r.cpu_percent for r in recent_usage]
        memory_values = [r.memory_mb for r in recent_usage]
        
        # Get current bottleneck
        current_bottleneck = self.active_bottlenecks.get(entity_id)
        
        # Get efficiency
        efficiency = self.calculate_efficiency(entity_id, period_minutes=60)
        
        # Get trends
        trends = self._calculate_entity_trends(
            entity_id, 
            "agent" if entity_id in self.agent_resources else "team"
        )
        
        return {
            "entity_id": entity_id,
            "entity_type": recent_usage[0].entity_type if recent_usage else "unknown",
            "current_usage": {
                "cpu_percent": recent_usage[-1].cpu_percent if recent_usage else 0,
                "memory_mb": recent_usage[-1].memory_mb if recent_usage else 0,
                "thread_count": recent_usage[-1].thread_count if recent_usage else 0
            },
            "statistics": {
                "avg_cpu": statistics.mean(cpu_values) if cpu_values else 0,
                "max_cpu": max(cpu_values) if cpu_values else 0,
                "avg_memory": statistics.mean(memory_values) if memory_values else 0,
                "max_memory": max(memory_values) if memory_values else 0
            },
            "efficiency": {
                "score": efficiency.efficiency_score if efficiency else 0,
                "tasks_completed": efficiency.tasks_completed if efficiency else 0
            } if efficiency else None,
            "bottleneck": {
                "type": current_bottleneck.bottleneck_type.value,
                "severity": current_bottleneck.severity,
                "recommendations": current_bottleneck.recommendations
            } if current_bottleneck else None,
            "trends": [
                {
                    "resource": t.resource_type.value,
                    "direction": t.trend_direction,
                    "rate": t.trend_rate,
                    "predicted_1h": t.predicted_value_1h
                }
                for t in trends
            ] if trends else []
        }
    
    def get_system_resource_overview(self) -> Dict[str, Any]:
        """
        Get system-wide resource overview
        
        Returns:
            Dictionary with system resource information
        """
        # Get current system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Count active entities
        active_agents = len(self.agent_resources)
        active_teams = len(self.team_resources)
        
        # Get bottlenecks
        bottlenecks = list(self.active_bottlenecks.values())
        
        # Calculate total resource usage by tracked entities
        total_tracked_cpu = 0
        total_tracked_memory = 0
        
        for resources in self.agent_resources.values():
            if resources:
                total_tracked_cpu += resources[-1].cpu_percent
                total_tracked_memory += resources[-1].memory_mb
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            },
            "tracked_entities": {
                "active_agents": active_agents,
                "active_teams": active_teams,
                "total_cpu_percent": total_tracked_cpu,
                "total_memory_mb": total_tracked_memory
            },
            "bottlenecks": [
                {
                    "entity_id": b.entity_id,
                    "type": b.bottleneck_type.value,
                    "severity": b.severity
                }
                for b in bottlenecks
            ],
            "baseline": self.system_baseline
        }
    
    def set_resource_limit(self, entity_id: str, limits: Dict[str, float]):
        """
        Set resource limits for an entity
        
        Args:
            entity_id: Agent or team ID
            limits: Dictionary of resource limits
        """
        with self._lock:
            self.resource_limits[entity_id] = limits
        logger.info(f"Set resource limits for {entity_id}: {limits}")
    
    def check_resource_limits(self, entity_id: str) -> Dict[str, bool]:
        """
        Check if an entity is within resource limits
        
        Args:
            entity_id: Agent or team ID
            
        Returns:
            Dictionary indicating which limits are exceeded
        """
        if entity_id not in self.resource_limits:
            return {}
        
        limits = self.resource_limits[entity_id]
        recent_usage = self.get_resource_usage(entity_id, duration_minutes=5)
        
        if not recent_usage:
            return {}
        
        latest = recent_usage[-1]
        
        return {
            "cpu_exceeded": latest.cpu_percent > limits.get("cpu_percent", float('inf')),
            "memory_exceeded": latest.memory_mb > limits.get("memory_mb", float('inf')),
            "threads_exceeded": latest.thread_count > limits.get("thread_count", float('inf'))
        }
    
    def _cleanup_old_data(self):
        """Clean up old resource data beyond retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.history_retention_hours)
        
        with self._lock:
            # Clean up agent resources
            for agent_id in list(self.agent_resources.keys()):
                self.agent_resources[agent_id] = deque(
                    [r for r in self.agent_resources[agent_id]
                     if r.timestamp >= cutoff_time],
                    maxlen=10000
                )
            
            # Clean up team resources
            for team_id in list(self.team_resources.keys()):
                self.team_resources[team_id] = deque(
                    [r for r in self.team_resources[team_id]
                     if r.timestamp >= cutoff_time],
                    maxlen=10000
                )
            
            # Clean up efficiency history
            self.efficiency_history = deque(
                [e for e in self.efficiency_history
                 if e.period_end >= cutoff_time],
                maxlen=1000
            )
    
    def export_resource_data(self, 
                            entity_id: Optional[str] = None,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Export resource data for analysis
        
        Args:
            entity_id: Optional specific entity to export
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary with exported data
        """
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        export_data = {
            "export_time": datetime.now().isoformat(),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "entities": {}
        }
        
        # Determine which entities to export
        if entity_id:
            entities = [entity_id]
        else:
            entities = list(self.agent_resources.keys()) + list(self.team_resources.keys())
        
        for eid in entities:
            usage = self.get_resource_usage(eid)
            filtered_usage = [
                {
                    "timestamp": u.timestamp.isoformat(),
                    "cpu_percent": u.cpu_percent,
                    "memory_mb": u.memory_mb,
                    "thread_count": u.thread_count
                }
                for u in usage
                if start_time <= u.timestamp <= end_time
            ]
            
            if filtered_usage:
                export_data["entities"][eid] = {
                    "type": filtered_usage[0].get("entity_type", "unknown"),
                    "usage": filtered_usage,
                    "summary": self.get_resource_summary(eid)
                }
        
        return export_data


# Integration with Control Layer Resource Allocator
class ResourceTrackerIntegration:
    """Integration between ResourceTracker and Control Layer ResourceAllocator"""
    
    def __init__(self, resource_tracker: ResourceTracker, resource_allocator: Any):
        """
        Initialize integration
        
        Args:
            resource_tracker: ResourceTracker instance
            resource_allocator: Control layer ResourceAllocator instance
        """
        self.tracker = resource_tracker
        self.allocator = resource_allocator
    
    def sync_resource_limits(self):
        """Sync resource limits from allocator to tracker"""
        # This would pull limits from the control layer
        # and apply them to the tracker
        pass
    
    def report_usage_to_allocator(self):
        """Report current usage back to the allocator"""
        # This would send usage data back to the control layer
        # for allocation decisions
        pass


# Example usage and testing
if __name__ == "__main__":
    # Create resource tracker
    tracker = ResourceTracker(
        sampling_interval_seconds=5,
        history_retention_hours=24,
        bottleneck_threshold=0.8
    )
    
    # Start monitoring
    tracker.start_monitoring()
    
    # Register some mock agents
    import os
    current_pid = os.getpid()
    
    tracker.register_agent("agent_1", current_pid, "team_alpha")
    tracker.register_agent("agent_2", current_pid, "team_alpha")
    
    # Simulate some work and task completions
    for i in range(10):
        time.sleep(2)
        tracker.record_task_completion("agent_1")
        if i % 2 == 0:
            tracker.record_task_completion("agent_2")
    
    # Get resource summaries
    print("\n=== Agent 1 Resource Summary ===")
    print(json.dumps(tracker.get_resource_summary("agent_1"), indent=2))
    
    print("\n=== Team Alpha Resource Summary ===")
    print(json.dumps(tracker.get_resource_summary("team_alpha"), indent=2))
    
    print("\n=== System Resource Overview ===")
    print(json.dumps(tracker.get_system_resource_overview(), indent=2))
    
    # Calculate efficiency
    efficiency = tracker.calculate_efficiency("agent_1", period_minutes=5)
    if efficiency:
        print(f"\n=== Agent 1 Efficiency ===")
        print(f"Overall Score: {efficiency.efficiency_score:.2f}%")
        print(f"Tasks Completed: {efficiency.tasks_completed}")
    
    # Stop monitoring
    tracker.stop_monitoring()