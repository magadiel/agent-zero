"""
Performance Monitor - Real-time system performance tracking for Agent-Zero

This module provides comprehensive performance monitoring for the Agent-Zero framework,
tracking agent response times, resource usage, task completion rates, and generating
performance alerts when thresholds are exceeded.
"""

import time
import statistics
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import json
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics tracked"""
    RESPONSE_TIME = "response_time"
    TASK_DURATION = "task_duration"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    TASK_SUCCESS_RATE = "task_success_rate"
    TASK_FAILURE_RATE = "task_failure_rate"
    THROUGHPUT = "throughput"
    QUEUE_LENGTH = "queue_length"
    ERROR_RATE = "error_rate"
    AGENT_UTILIZATION = "agent_utilization"


class AlertSeverity(Enum):
    """Severity levels for performance alerts"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Status of tracked tasks"""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    duration_seconds: int = 60  # Time window for evaluation
    consecutive_breaches: int = 3  # Number of consecutive breaches before alert


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert generated when thresholds are breached"""
    alert_id: str
    severity: AlertSeverity
    metric_type: MetricType
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    agent_id: Optional[str] = None
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class TaskPerformance:
    """Task performance tracking data"""
    task_id: str
    agent_id: str
    task_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.STARTED
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System-wide performance metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    active_agents: int
    active_tasks: int
    queue_length: int


class PerformanceMonitor:
    """
    Real-time performance monitoring system for Agent-Zero
    
    Tracks agent response times, resource usage, task completion rates,
    and generates alerts when performance thresholds are exceeded.
    """
    
    def __init__(self, 
                 retention_hours: int = 24,
                 sampling_interval_seconds: int = 5,
                 alert_callback: Optional[callable] = None):
        """
        Initialize the performance monitor
        
        Args:
            retention_hours: How long to retain metrics data
            sampling_interval_seconds: Interval for system metrics sampling
            alert_callback: Optional callback for alert notifications
        """
        self.retention_hours = retention_hours
        self.sampling_interval_seconds = sampling_interval_seconds
        self.alert_callback = alert_callback
        
        # Metrics storage
        self.metrics: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.agent_metrics: Dict[str, Dict[MetricType, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=1000))
        )
        
        # Task tracking
        self.active_tasks: Dict[str, TaskPerformance] = {}
        self.completed_tasks: deque = deque(maxlen=10000)
        
        # Alert management
        self.thresholds: List[PerformanceThreshold] = self._initialize_thresholds()
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.breach_counters: Dict[str, int] = defaultdict(int)
        
        # System metrics
        self.system_metrics_history: deque = deque(maxlen=10000)
        self.last_disk_io = psutil.disk_io_counters()
        self.last_network_io = psutil.net_io_counters()
        
        # Monitoring control
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # Statistics cache
        self._stats_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl_seconds = 10
        
        logger.info("Performance Monitor initialized")
    
    def _initialize_thresholds(self) -> List[PerformanceThreshold]:
        """Initialize default performance thresholds"""
        return [
            # Response time thresholds (milliseconds)
            PerformanceThreshold(
                MetricType.RESPONSE_TIME,
                warning_threshold=1000,  # 1 second
                critical_threshold=5000,  # 5 seconds
                duration_seconds=60
            ),
            # Task duration thresholds (milliseconds)
            PerformanceThreshold(
                MetricType.TASK_DURATION,
                warning_threshold=30000,  # 30 seconds
                critical_threshold=120000,  # 2 minutes
                duration_seconds=300
            ),
            # CPU usage thresholds (percentage)
            PerformanceThreshold(
                MetricType.CPU_USAGE,
                warning_threshold=80,
                critical_threshold=95,
                duration_seconds=60
            ),
            # Memory usage thresholds (percentage)
            PerformanceThreshold(
                MetricType.MEMORY_USAGE,
                warning_threshold=85,
                critical_threshold=95,
                duration_seconds=60
            ),
            # Task failure rate thresholds (percentage)
            PerformanceThreshold(
                MetricType.TASK_FAILURE_RATE,
                warning_threshold=10,
                critical_threshold=25,
                duration_seconds=300
            ),
            # Error rate thresholds (errors per minute)
            PerformanceThreshold(
                MetricType.ERROR_RATE,
                warning_threshold=10,
                critical_threshold=50,
                duration_seconds=60
            ),
        ]
    
    def start_monitoring(self):
        """Start the performance monitoring background thread"""
        with self._lock:
            if not self._monitoring:
                self._monitoring = True
                self._monitor_thread = threading.Thread(
                    target=self._monitoring_loop,
                    daemon=True
                )
                self._monitor_thread.start()
                logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the performance monitoring background thread"""
        with self._lock:
            if self._monitoring:
                self._monitoring = False
                if self._monitor_thread:
                    self._monitor_thread.join(timeout=5)
                logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check thresholds and generate alerts
                self._check_thresholds()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep until next sampling interval
                time.sleep(self.sampling_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sampling_interval_seconds)
    
    def _collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # Get current I/O counters
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            # Calculate I/O rates
            disk_read_mb = (disk_io.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024)
            disk_write_mb = (disk_io.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024)
            network_sent_mb = (network_io.bytes_sent - self.last_network_io.bytes_sent) / (1024 * 1024)
            network_recv_mb = (network_io.bytes_recv - self.last_network_io.bytes_recv) / (1024 * 1024)
            
            # Update last counters
            self.last_disk_io = disk_io
            self.last_network_io = network_io
            
            # Create system metrics snapshot
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=psutil.virtual_memory().percent,
                memory_mb=psutil.virtual_memory().used / (1024 * 1024),
                disk_io_read_mb=max(0, disk_read_mb),
                disk_io_write_mb=max(0, disk_write_mb),
                network_io_sent_mb=max(0, network_sent_mb),
                network_io_recv_mb=max(0, network_recv_mb),
                active_agents=len(self.agent_metrics),
                active_tasks=len(self.active_tasks),
                queue_length=self._get_queue_length()
            )
            
            with self._lock:
                self.system_metrics_history.append(metrics)
                
                # Record as individual metrics
                self.record_metric(MetricType.CPU_USAGE, metrics.cpu_percent)
                self.record_metric(MetricType.MEMORY_USAGE, metrics.memory_percent)
                
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _get_queue_length(self) -> int:
        """Get current task queue length (to be overridden by integration)"""
        # This would be integrated with the actual task queue system
        return 0
    
    def record_metric(self, 
                     metric_type: MetricType, 
                     value: float,
                     agent_id: Optional[str] = None,
                     task_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """
        Record a performance metric
        
        Args:
            metric_type: Type of metric
            value: Metric value
            agent_id: Optional agent identifier
            task_id: Optional task identifier
            metadata: Optional additional metadata
        """
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            agent_id=agent_id,
            task_id=task_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            # Store in global metrics
            self.metrics[metric_type].append(metric)
            
            # Store in agent-specific metrics if applicable
            if agent_id:
                self.agent_metrics[agent_id][metric_type].append(metric)
            
            # Invalidate statistics cache
            self._invalidate_cache(metric_type, agent_id)
    
    def start_task(self, 
                   task_id: str, 
                   agent_id: str, 
                   task_type: str,
                   metadata: Optional[Dict[str, Any]] = None) -> TaskPerformance:
        """
        Start tracking a task's performance
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent executing the task
            task_type: Type of task
            metadata: Optional task metadata
            
        Returns:
            TaskPerformance object
        """
        task = TaskPerformance(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self.active_tasks[task_id] = task
            
        logger.debug(f"Started tracking task {task_id} for agent {agent_id}")
        return task
    
    def end_task(self, 
                 task_id: str, 
                 status: TaskStatus,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        End tracking a task's performance
        
        Args:
            task_id: Task identifier
            status: Final task status
            metadata: Optional additional metadata
        """
        with self._lock:
            if task_id not in self.active_tasks:
                logger.warning(f"Task {task_id} not found in active tasks")
                return
            
            task = self.active_tasks.pop(task_id)
            task.end_time = datetime.now()
            task.status = status
            task.duration_ms = (task.end_time - task.start_time).total_seconds() * 1000
            
            if metadata:
                task.metadata.update(metadata)
            
            # Record task metrics
            self.completed_tasks.append(task)
            self.record_metric(
                MetricType.TASK_DURATION,
                task.duration_ms,
                agent_id=task.agent_id,
                task_id=task_id
            )
            
            # Record response time for the agent
            self.record_metric(
                MetricType.RESPONSE_TIME,
                task.duration_ms,
                agent_id=task.agent_id
            )
            
            logger.debug(f"Completed tracking task {task_id} with status {status}")
    
    def _check_thresholds(self):
        """Check performance thresholds and generate alerts"""
        current_time = datetime.now()
        
        for threshold in self.thresholds:
            # Get recent metrics for this type
            metrics = self._get_recent_metrics(
                threshold.metric_type,
                threshold.duration_seconds
            )
            
            if not metrics:
                continue
            
            # Calculate average value
            avg_value = statistics.mean([m.value for m in metrics])
            
            # Check against thresholds
            alert_generated = False
            
            if avg_value >= threshold.critical_threshold:
                self._generate_alert(
                    severity=AlertSeverity.CRITICAL,
                    metric_type=threshold.metric_type,
                    current_value=avg_value,
                    threshold_value=threshold.critical_threshold
                )
                alert_generated = True
                
            elif avg_value >= threshold.warning_threshold:
                # Check consecutive breaches for warnings
                breach_key = f"{threshold.metric_type}_warning"
                self.breach_counters[breach_key] += 1
                
                if self.breach_counters[breach_key] >= threshold.consecutive_breaches:
                    self._generate_alert(
                        severity=AlertSeverity.WARNING,
                        metric_type=threshold.metric_type,
                        current_value=avg_value,
                        threshold_value=threshold.warning_threshold
                    )
                    alert_generated = True
            else:
                # Reset breach counter if threshold not exceeded
                breach_key = f"{threshold.metric_type}_warning"
                self.breach_counters[breach_key] = 0
            
            if alert_generated:
                # Reset breach counter after alert
                breach_key = f"{threshold.metric_type}_warning"
                self.breach_counters[breach_key] = 0
    
    def _generate_alert(self,
                       severity: AlertSeverity,
                       metric_type: MetricType,
                       current_value: float,
                       threshold_value: float,
                       agent_id: Optional[str] = None):
        """Generate a performance alert"""
        alert_id = f"{metric_type.value}_{severity.value}_{int(time.time())}"
        
        # Check if similar alert already active
        for existing_alert in self.active_alerts.values():
            if (existing_alert.metric_type == metric_type and
                existing_alert.severity == severity and
                not existing_alert.resolved):
                # Don't create duplicate alert
                return
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            severity=severity,
            metric_type=metric_type,
            message=self._format_alert_message(
                severity, metric_type, current_value, threshold_value
            ),
            current_value=current_value,
            threshold_value=threshold_value,
            timestamp=datetime.now(),
            agent_id=agent_id
        )
        
        with self._lock:
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
        
        # Trigger callback if configured
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.warning(f"Performance alert: {alert.message}")
    
    def _format_alert_message(self,
                             severity: AlertSeverity,
                             metric_type: MetricType,
                             current_value: float,
                             threshold_value: float) -> str:
        """Format an alert message"""
        metric_name = metric_type.value.replace('_', ' ').title()
        
        if metric_type in [MetricType.CPU_USAGE, MetricType.MEMORY_USAGE,
                          MetricType.TASK_SUCCESS_RATE, MetricType.TASK_FAILURE_RATE]:
            unit = "%"
        elif metric_type in [MetricType.RESPONSE_TIME, MetricType.TASK_DURATION]:
            unit = "ms"
        else:
            unit = ""
        
        return (f"{severity.value.upper()}: {metric_name} "
                f"({current_value:.2f}{unit}) exceeded threshold "
                f"({threshold_value:.2f}{unit})")
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                logger.info(f"Alert {alert_id} acknowledged")
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts.pop(alert_id)
                alert.resolved = True
                logger.info(f"Alert {alert_id} resolved")
    
    def _get_recent_metrics(self,
                           metric_type: MetricType,
                           duration_seconds: int) -> List[PerformanceMetric]:
        """Get metrics from the recent time window"""
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        
        with self._lock:
            metrics = [m for m in self.metrics[metric_type]
                      if m.timestamp >= cutoff_time]
        
        return metrics
    
    def _cleanup_old_data(self):
        """Clean up old metrics data beyond retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean up metrics
            for metric_type in list(self.metrics.keys()):
                self.metrics[metric_type] = deque(
                    [m for m in self.metrics[metric_type]
                     if m.timestamp >= cutoff_time],
                    maxlen=10000
                )
            
            # Clean up agent metrics
            for agent_id in list(self.agent_metrics.keys()):
                for metric_type in list(self.agent_metrics[agent_id].keys()):
                    self.agent_metrics[agent_id][metric_type] = deque(
                        [m for m in self.agent_metrics[agent_id][metric_type]
                         if m.timestamp >= cutoff_time],
                        maxlen=1000
                    )
            
            # Clean up resolved alerts
            self.active_alerts = {
                aid: alert for aid, alert in self.active_alerts.items()
                if not alert.resolved or alert.timestamp >= cutoff_time
            }
    
    def _invalidate_cache(self, metric_type: MetricType, agent_id: Optional[str] = None):
        """Invalidate statistics cache for a metric type"""
        cache_key = f"{metric_type.value}_{agent_id or 'global'}"
        if cache_key in self._stats_cache:
            del self._stats_cache[cache_key]
    
    def get_statistics(self,
                       metric_type: MetricType,
                       duration_seconds: Optional[int] = None,
                       agent_id: Optional[str] = None) -> Dict[str, float]:
        """
        Get statistics for a specific metric
        
        Args:
            metric_type: Type of metric
            duration_seconds: Time window (None for all data)
            agent_id: Optional agent filter
            
        Returns:
            Dictionary with statistics
        """
        cache_key = f"{metric_type.value}_{agent_id or 'global'}_{duration_seconds}"
        
        # Check cache
        if cache_key in self._stats_cache:
            cached_data, cache_time = self._stats_cache[cache_key]
            if (datetime.now() - cache_time).seconds < self._cache_ttl_seconds:
                return cached_data
        
        # Get metrics
        if duration_seconds:
            metrics = self._get_recent_metrics(metric_type, duration_seconds)
        else:
            with self._lock:
                if agent_id:
                    metrics = list(self.agent_metrics[agent_id][metric_type])
                else:
                    metrics = list(self.metrics[metric_type])
        
        if not metrics:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "std_dev": 0,
                "p95": 0,
                "p99": 0
            }
        
        values = [m.value for m in metrics]
        
        stats = {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
        
        # Cache the results
        self._stats_cache[cache_key] = (stats, datetime.now())
        
        return stats
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[index]
    
    def get_task_statistics(self, 
                           duration_seconds: Optional[int] = None,
                           agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get task completion statistics
        
        Args:
            duration_seconds: Time window (None for all data)
            agent_id: Optional agent filter
            
        Returns:
            Dictionary with task statistics
        """
        if duration_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
            tasks = [t for t in self.completed_tasks 
                    if t.end_time and t.end_time >= cutoff_time]
        else:
            tasks = list(self.completed_tasks)
        
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        
        if not tasks:
            return {
                "total_tasks": 0,
                "success_rate": 0,
                "failure_rate": 0,
                "avg_duration_ms": 0,
                "tasks_by_status": {},
                "tasks_by_type": {}
            }
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]
        
        tasks_by_status = defaultdict(int)
        tasks_by_type = defaultdict(int)
        
        for task in tasks:
            tasks_by_status[task.status.value] += 1
            tasks_by_type[task.task_type] += 1
        
        durations = [t.duration_ms for t in tasks if t.duration_ms is not None]
        
        return {
            "total_tasks": total_tasks,
            "success_rate": (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0,
            "failure_rate": (len(failed_tasks) / total_tasks * 100) if total_tasks > 0 else 0,
            "avg_duration_ms": statistics.mean(durations) if durations else 0,
            "tasks_by_status": dict(tasks_by_status),
            "tasks_by_type": dict(tasks_by_type)
        }
    
    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary with agent performance data
        """
        return {
            "agent_id": agent_id,
            "response_time_stats": self.get_statistics(
                MetricType.RESPONSE_TIME, 
                agent_id=agent_id
            ),
            "task_duration_stats": self.get_statistics(
                MetricType.TASK_DURATION,
                agent_id=agent_id
            ),
            "task_stats": self.get_task_statistics(agent_id=agent_id),
            "active_tasks": [
                task.task_id for task in self.active_tasks.values()
                if task.agent_id == agent_id
            ]
        }
    
    def get_system_performance(self) -> Dict[str, Any]:
        """
        Get current system performance overview
        
        Returns:
            Dictionary with system performance data
        """
        # Get latest system metrics
        latest_metrics = None
        if self.system_metrics_history:
            latest_metrics = self.system_metrics_history[-1]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": {
                "cpu_percent": latest_metrics.cpu_percent if latest_metrics else 0,
                "memory_percent": latest_metrics.memory_percent if latest_metrics else 0,
                "memory_mb": latest_metrics.memory_mb if latest_metrics else 0,
                "active_agents": len(self.agent_metrics),
                "active_tasks": len(self.active_tasks),
                "queue_length": latest_metrics.queue_length if latest_metrics else 0
            } if latest_metrics else {},
            "performance_stats": {
                "response_time": self.get_statistics(MetricType.RESPONSE_TIME, 300),
                "task_duration": self.get_statistics(MetricType.TASK_DURATION, 300),
                "cpu_usage": self.get_statistics(MetricType.CPU_USAGE, 300),
                "memory_usage": self.get_statistics(MetricType.MEMORY_USAGE, 300)
            },
            "task_stats": self.get_task_statistics(300),
            "active_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in self.active_alerts.values()
                if not alert.resolved
            ]
        }
    
    def export_metrics(self, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Export metrics data for analysis
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary with exported metrics
        """
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        # Filter metrics by time range
        filtered_metrics = {}
        for metric_type, metrics in self.metrics.items():
            filtered = [
                {
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "agent_id": m.agent_id,
                    "task_id": m.task_id
                }
                for m in metrics
                if start_time <= m.timestamp <= end_time
            ]
            if filtered:
                filtered_metrics[metric_type.value] = filtered
        
        # Filter tasks by time range
        filtered_tasks = [
            {
                "task_id": t.task_id,
                "agent_id": t.agent_id,
                "task_type": t.task_type,
                "status": t.status.value,
                "start_time": t.start_time.isoformat(),
                "end_time": t.end_time.isoformat() if t.end_time else None,
                "duration_ms": t.duration_ms
            }
            for t in self.completed_tasks
            if t.end_time and start_time <= t.end_time <= end_time
        ]
        
        # Filter system metrics
        filtered_system = [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_mb": m.memory_mb,
                "active_agents": m.active_agents,
                "active_tasks": m.active_tasks
            }
            for m in self.system_metrics_history
            if start_time <= m.timestamp <= end_time
        ]
        
        return {
            "export_time": datetime.now().isoformat(),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "metrics": filtered_metrics,
            "tasks": filtered_tasks,
            "system_metrics": filtered_system
        }
    
    def set_threshold(self, threshold: PerformanceThreshold):
        """Update or add a performance threshold"""
        with self._lock:
            # Remove existing threshold for this metric type if present
            self.thresholds = [
                t for t in self.thresholds 
                if t.metric_type != threshold.metric_type
            ]
            self.thresholds.append(threshold)
            
        logger.info(f"Updated threshold for {threshold.metric_type.value}")
    
    def get_alerts(self, 
                  active_only: bool = True,
                  severity_filter: Optional[AlertSeverity] = None) -> List[PerformanceAlert]:
        """
        Get performance alerts
        
        Args:
            active_only: Only return active (unresolved) alerts
            severity_filter: Filter by severity level
            
        Returns:
            List of alerts
        """
        alerts = list(self.active_alerts.values()) if active_only else list(self.alert_history)
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
        
        if active_only:
            alerts = [a for a in alerts if not a.resolved]
        
        return alerts


# Example usage and testing
if __name__ == "__main__":
    # Create performance monitor
    monitor = PerformanceMonitor(
        retention_hours=24,
        sampling_interval_seconds=5,
        alert_callback=lambda alert: print(f"ALERT: {alert.message}")
    )
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Simulate some tasks
    import random
    
    for i in range(5):
        task_id = f"task_{i}"
        agent_id = f"agent_{i % 2}"
        
        # Start task
        monitor.start_task(task_id, agent_id, "processing")
        
        # Simulate some work
        time.sleep(random.uniform(0.1, 0.5))
        
        # Record some metrics
        monitor.record_metric(
            MetricType.CPU_USAGE,
            random.uniform(30, 90),
            agent_id=agent_id
        )
        
        # End task
        status = TaskStatus.COMPLETED if random.random() > 0.2 else TaskStatus.FAILED
        monitor.end_task(task_id, status)
    
    # Wait for some monitoring cycles
    time.sleep(10)
    
    # Get statistics
    print("\n=== System Performance ===")
    print(json.dumps(monitor.get_system_performance(), indent=2))
    
    print("\n=== Task Statistics ===")
    print(json.dumps(monitor.get_task_statistics(), indent=2))
    
    print("\n=== Response Time Stats ===")
    print(json.dumps(monitor.get_statistics(MetricType.RESPONSE_TIME), indent=2))
    
    # Stop monitoring
    monitor.stop_monitoring()