"""
Workflow Monitoring System for Agent-Zero

This module provides real-time monitoring, tracking, and alerting capabilities
for workflow executions. It integrates with the workflow engine to track state
changes, agent progress, and performance metrics.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
import weakref

# Try to import websockets for real-time updates
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("Warning: websockets package not available. Real-time updates disabled.")

from coordination.workflow_engine import (
    WorkflowEngine,
    WorkflowExecution,
    StepExecution,
    StepState,
    WorkflowState
)
from coordination.workflow_parser import WorkflowDefinition


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics tracked"""
    WORKFLOW_DURATION = "workflow_duration"
    STEP_DURATION = "step_duration"
    AGENT_UTILIZATION = "agent_utilization"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    QUEUE_DEPTH = "queue_depth"


@dataclass
class Alert:
    """Represents a monitoring alert"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """A single metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowMetrics:
    """Aggregated metrics for a workflow"""
    workflow_id: str
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    duration_seconds: Optional[float] = None
    average_step_duration: Optional[float] = None
    error_rate: float = 0.0
    success_rate: float = 0.0
    agent_utilization: Dict[str, float] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring system"""
    # Alert thresholds
    max_step_duration_seconds: float = 300  # 5 minutes
    max_workflow_duration_seconds: float = 3600  # 1 hour
    max_retry_count: int = 3
    max_error_rate: float = 0.1  # 10%
    min_success_rate: float = 0.9  # 90%
    
    # Monitoring intervals
    metric_collection_interval: float = 10.0  # seconds
    health_check_interval: float = 30.0  # seconds
    
    # Data retention
    max_alerts: int = 1000
    max_metrics_per_type: int = 10000
    metric_retention_hours: int = 24
    
    # WebSocket configuration
    websocket_host: str = "localhost"
    websocket_port: int = 8765
    websocket_enabled: bool = WEBSOCKET_AVAILABLE


class WorkflowMonitor:
    """
    Main monitoring system for workflow executions
    
    Provides:
    - Real-time state tracking
    - Performance metrics collection
    - Alert generation and management
    - WebSocket server for real-time updates
    - Dashboard data API
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        Initialize the workflow monitor
        
        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        
        # Tracked executions (weak references to avoid memory leaks)
        self._executions: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        
        # Metrics storage
        self._metrics: Dict[MetricType, deque] = defaultdict(
            lambda: deque(maxlen=self.config.max_metrics_per_type)
        )
        
        # Alert storage
        self._alerts: deque = deque(maxlen=self.config.max_alerts)
        self._alert_handlers: List[Callable[[Alert], None]] = []
        
        # WebSocket connections
        self._websocket_clients: Set[WebSocketServerProtocol] = set()
        self._websocket_server = None
        self._websocket_task = None
        
        # Background tasks
        self._monitoring_task = None
        self._cleanup_task = None
        self._running = False
        
        # Statistics
        self._stats = {
            "workflows_tracked": 0,
            "workflows_completed": 0,
            "workflows_failed": 0,
            "total_steps_executed": 0,
            "total_alerts_generated": 0
        }
    
    async def start(self):
        """Start the monitoring system"""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Start WebSocket server if enabled
        if self.config.websocket_enabled:
            self._websocket_task = asyncio.create_task(self._start_websocket_server())
    
    async def stop(self):
        """Stop the monitoring system"""
        self._running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Stop WebSocket server
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()
        
        # Close all WebSocket connections
        for client in list(self._websocket_clients):
            await client.close()
    
    def track_execution(self, execution: WorkflowExecution):
        """
        Start tracking a workflow execution
        
        Args:
            execution: The workflow execution to track
        """
        self._executions[execution.execution_id] = execution
        self._stats["workflows_tracked"] += 1
        
        # Generate initial tracking alert
        self._generate_alert(
            AlertSeverity.INFO,
            "Workflow Started",
            f"Started tracking workflow {execution.workflow_id}",
            workflow_id=execution.execution_id
        )
    
    def untrack_execution(self, execution_id: str):
        """
        Stop tracking a workflow execution
        
        Args:
            execution_id: ID of the execution to stop tracking
        """
        if execution_id in self._executions:
            del self._executions[execution_id]
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """
        Add a custom alert handler
        
        Args:
            handler: Function to call when an alert is generated
        """
        self._alert_handlers.append(handler)
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a workflow execution
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Status dictionary or None if not found
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return None
        
        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "state": execution.state.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "progress": self._calculate_progress(execution),
            "current_step": self._get_current_step(execution),
            "step_states": {
                step_id: step.state.value 
                for step_id, step in execution.step_executions.items()
            },
            "error": execution.error
        }
    
    def get_execution_metrics(self, execution_id: str) -> Optional[WorkflowMetrics]:
        """
        Get metrics for a workflow execution
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Metrics object or None if not found
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return None
        
        return self._calculate_metrics(execution)
    
    def get_alerts(
        self, 
        severity: Optional[AlertSeverity] = None,
        workflow_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get alerts with optional filtering
        
        Args:
            severity: Filter by severity
            workflow_id: Filter by workflow
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        alerts = list(self._alerts)
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if workflow_id:
            alerts = [a for a in alerts if a.workflow_id == workflow_id]
        
        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """
        Acknowledge an alert
        
        Args:
            alert_id: ID of the alert to acknowledge
            acknowledged_by: Who is acknowledging the alert
        """
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                break
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data
        
        Returns:
            Dictionary with dashboard information
        """
        active_executions = list(self._executions.values())
        
        return {
            "summary": {
                "active_workflows": len(active_executions),
                "total_workflows": self._stats["workflows_tracked"],
                "completed_workflows": self._stats["workflows_completed"],
                "failed_workflows": self._stats["workflows_failed"],
                "total_steps": self._stats["total_steps_executed"],
                "total_alerts": self._stats["total_alerts_generated"]
            },
            "active_workflows": [
                {
                    "execution_id": e.execution_id,
                    "workflow_id": e.workflow_id,
                    "state": e.state.value,
                    "progress": self._calculate_progress(e),
                    "duration": self._calculate_duration(e),
                    "current_step": self._get_current_step(e)
                }
                for e in active_executions
            ],
            "recent_alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                    "acknowledged": a.acknowledged
                }
                for a in list(self._alerts)[:10]
            ],
            "metrics": self._get_aggregated_metrics(),
            "agent_utilization": self._calculate_agent_utilization()
        }
    
    # Private methods
    
    def _generate_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        **kwargs
    ):
        """Generate a new alert"""
        alert = Alert(
            id=f"alert_{int(time.time() * 1000)}_{self._stats['total_alerts_generated']}",
            severity=severity,
            title=title,
            message=message,
            **kwargs
        )
        
        self._alerts.append(alert)
        self._stats["total_alerts_generated"] += 1
        
        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")
        
        # Send to WebSocket clients
        asyncio.create_task(self._broadcast_alert(alert))
    
    def _calculate_progress(self, execution: WorkflowExecution) -> float:
        """Calculate workflow progress percentage"""
        if not execution.step_executions:
            return 0.0
        
        completed = sum(
            1 for step in execution.step_executions.values()
            if step.state in [StepState.COMPLETED, StepState.SKIPPED]
        )
        total = len(execution.step_executions)
        
        return (completed / total) * 100 if total > 0 else 0.0
    
    def _get_current_step(self, execution: WorkflowExecution) -> Optional[str]:
        """Get the currently executing step"""
        for step_id, step in execution.step_executions.items():
            if step.state == StepState.RUNNING:
                return step_id
        return None
    
    def _calculate_duration(self, execution: WorkflowExecution) -> Optional[float]:
        """Calculate workflow duration in seconds"""
        if not execution.started_at:
            return None
        
        end_time = execution.completed_at or datetime.now(timezone.utc)
        return (end_time - execution.started_at).total_seconds()
    
    def _calculate_metrics(self, execution: WorkflowExecution) -> WorkflowMetrics:
        """Calculate metrics for a workflow execution"""
        metrics = WorkflowMetrics(workflow_id=execution.execution_id)
        
        step_durations = []
        for step in execution.step_executions.values():
            metrics.total_steps += 1
            
            if step.state == StepState.COMPLETED:
                metrics.completed_steps += 1
                if step.started_at and step.completed_at:
                    duration = (step.completed_at - step.started_at).total_seconds()
                    step_durations.append(duration)
            elif step.state == StepState.FAILED:
                metrics.failed_steps += 1
            elif step.state == StepState.SKIPPED:
                metrics.skipped_steps += 1
            
            # Track agent utilization
            if step.agent_id:
                if step.agent_id not in metrics.agent_utilization:
                    metrics.agent_utilization[step.agent_id] = 0
                metrics.agent_utilization[step.agent_id] += 1
        
        # Calculate rates
        if metrics.total_steps > 0:
            metrics.error_rate = metrics.failed_steps / metrics.total_steps
            metrics.success_rate = metrics.completed_steps / metrics.total_steps
        
        # Calculate durations
        metrics.duration_seconds = self._calculate_duration(execution)
        if step_durations:
            metrics.average_step_duration = sum(step_durations) / len(step_durations)
        
        return metrics
    
    def _calculate_agent_utilization(self) -> Dict[str, float]:
        """Calculate current agent utilization across all workflows"""
        agent_tasks = defaultdict(int)
        total_agents = defaultdict(int)
        
        for execution in self._executions.values():
            for step in execution.step_executions.values():
                if step.agent_id:
                    total_agents[step.agent_id] = 1
                    if step.state == StepState.RUNNING:
                        agent_tasks[step.agent_id] += 1
        
        utilization = {}
        for agent_id in total_agents:
            utilization[agent_id] = agent_tasks.get(agent_id, 0)
        
        return utilization
    
    def _get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all workflows"""
        recent_window = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        aggregated = {
            "average_workflow_duration": 0.0,
            "average_step_duration": 0.0,
            "overall_success_rate": 0.0,
            "overall_error_rate": 0.0,
            "workflows_per_minute": 0.0
        }
        
        # Calculate from recent metrics
        durations = []
        success_count = 0
        error_count = 0
        total_count = 0
        
        for metric_points in self._metrics.values():
            for point in metric_points:
                if point.timestamp < recent_window:
                    continue
                
                if point.metric_type == MetricType.WORKFLOW_DURATION:
                    durations.append(point.value)
                elif point.metric_type == MetricType.SUCCESS_RATE:
                    success_count += 1
                    total_count += 1
                elif point.metric_type == MetricType.ERROR_RATE:
                    error_count += 1
                    total_count += 1
        
        if durations:
            aggregated["average_workflow_duration"] = sum(durations) / len(durations)
        
        if total_count > 0:
            aggregated["overall_success_rate"] = success_count / total_count
            aggregated["overall_error_rate"] = error_count / total_count
        
        # Calculate throughput
        completed_recent = sum(
            1 for e in self._executions.values()
            if e.completed_at and e.completed_at >= recent_window
        )
        aggregated["workflows_per_minute"] = completed_recent / 5.0
        
        return aggregated
    
    async def _monitoring_loop(self):
        """Background task for monitoring executions"""
        while self._running:
            try:
                # Check all tracked executions
                for execution in list(self._executions.values()):
                    await self._check_execution(execution)
                
                # Collect metrics
                self._collect_metrics()
                
                # Sleep before next iteration
                await asyncio.sleep(self.config.metric_collection_interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
    
    async def _check_execution(self, execution: WorkflowExecution):
        """Check a single execution for issues"""
        
        # Check workflow duration
        duration = self._calculate_duration(execution)
        if duration and duration > self.config.max_workflow_duration_seconds:
            self._generate_alert(
                AlertSeverity.WARNING,
                "Long Running Workflow",
                f"Workflow {execution.workflow_id} has been running for {duration:.1f} seconds",
                workflow_id=execution.execution_id
            )
        
        # Check step durations and retries
        for step_id, step in execution.step_executions.items():
            if step.state == StepState.RUNNING and step.started_at:
                step_duration = (datetime.now(timezone.utc) - step.started_at).total_seconds()
                if step_duration > self.config.max_step_duration_seconds:
                    self._generate_alert(
                        AlertSeverity.WARNING,
                        "Long Running Step",
                        f"Step {step_id} has been running for {step_duration:.1f} seconds",
                        workflow_id=execution.execution_id,
                        step_id=step_id
                    )
            
            if step.retry_count >= self.config.max_retry_count:
                self._generate_alert(
                    AlertSeverity.ERROR,
                    "Max Retries Exceeded",
                    f"Step {step_id} has been retried {step.retry_count} times",
                    workflow_id=execution.execution_id,
                    step_id=step_id
                )
        
        # Check error rates
        metrics = self._calculate_metrics(execution)
        if metrics.error_rate > self.config.max_error_rate:
            self._generate_alert(
                AlertSeverity.ERROR,
                "High Error Rate",
                f"Workflow has {metrics.error_rate:.1%} error rate",
                workflow_id=execution.execution_id
            )
        
        # Update stats on completion
        if execution.state == WorkflowState.COMPLETED:
            self._stats["workflows_completed"] += 1
            self._record_metric(MetricType.SUCCESS_RATE, 1.0, {"workflow_id": execution.workflow_id})
        elif execution.state == WorkflowState.FAILED:
            self._stats["workflows_failed"] += 1
            self._record_metric(MetricType.ERROR_RATE, 1.0, {"workflow_id": execution.workflow_id})
            self._generate_alert(
                AlertSeverity.ERROR,
                "Workflow Failed",
                f"Workflow {execution.workflow_id} failed: {execution.error}",
                workflow_id=execution.execution_id
            )
    
    def _collect_metrics(self):
        """Collect metrics from all executions"""
        for execution in self._executions.values():
            metrics = self._calculate_metrics(execution)
            
            # Record workflow metrics
            if metrics.duration_seconds:
                self._record_metric(
                    MetricType.WORKFLOW_DURATION,
                    metrics.duration_seconds,
                    {"workflow_id": execution.workflow_id}
                )
            
            if metrics.average_step_duration:
                self._record_metric(
                    MetricType.STEP_DURATION,
                    metrics.average_step_duration,
                    {"workflow_id": execution.workflow_id}
                )
            
            # Record agent utilization
            for agent_id, utilization in metrics.agent_utilization.items():
                self._record_metric(
                    MetricType.AGENT_UTILIZATION,
                    utilization,
                    {"agent_id": agent_id, "workflow_id": execution.workflow_id}
                )
            
            # Update step execution stats
            self._stats["total_steps_executed"] = sum(
                len(e.step_executions) for e in self._executions.values()
            )
    
    def _record_metric(self, metric_type: MetricType, value: float, labels: Dict[str, str]):
        """Record a metric data point"""
        point = MetricPoint(
            metric_type=metric_type,
            value=value,
            labels=labels
        )
        self._metrics[metric_type].append(point)
    
    async def _cleanup_loop(self):
        """Background task for cleaning up old data"""
        while self._running:
            try:
                # Clean up old metrics
                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    hours=self.config.metric_retention_hours
                )
                
                for metric_type in self._metrics:
                    # Remove old metrics
                    while self._metrics[metric_type]:
                        if self._metrics[metric_type][0].timestamp < cutoff_time:
                            self._metrics[metric_type].popleft()
                        else:
                            break
                
                # Sleep for an hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
    
    async def _start_websocket_server(self):
        """Start the WebSocket server for real-time updates"""
        if not WEBSOCKET_AVAILABLE:
            return
        
        try:
            async def handler(websocket, path):
                # Add client to set
                self._websocket_clients.add(websocket)
                try:
                    # Send initial data
                    await websocket.send(json.dumps({
                        "type": "initial",
                        "data": self.get_dashboard_data()
                    }))
                    
                    # Keep connection alive
                    await websocket.wait_closed()
                finally:
                    # Remove client from set
                    self._websocket_clients.discard(websocket)
            
            self._websocket_server = await websockets.serve(
                handler,
                self.config.websocket_host,
                self.config.websocket_port
            )
            
            print(f"WebSocket server started on ws://{self.config.websocket_host}:{self.config.websocket_port}")
            
        except Exception as e:
            print(f"Failed to start WebSocket server: {e}")
    
    async def _broadcast_update(self, update_type: str, data: Any):
        """Broadcast an update to all WebSocket clients"""
        if not self._websocket_clients:
            return
        
        message = json.dumps({
            "type": update_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Send to all connected clients
        disconnected = set()
        for client in self._websocket_clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self._websocket_clients -= disconnected
    
    async def _broadcast_alert(self, alert: Alert):
        """Broadcast an alert to WebSocket clients"""
        await self._broadcast_update("alert", {
            "id": alert.id,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "workflow_id": alert.workflow_id,
            "timestamp": alert.timestamp.isoformat()
        })


class WorkflowMonitorIntegration:
    """
    Integration helper for connecting WorkflowMonitor with WorkflowEngine
    """
    
    def __init__(self, monitor: WorkflowMonitor, engine: WorkflowEngine):
        """
        Initialize the integration
        
        Args:
            monitor: The workflow monitor instance
            engine: The workflow engine instance
        """
        self.monitor = monitor
        self.engine = engine
        
        # Register callbacks with the engine
        self._register_callbacks()
    
    def _register_callbacks(self):
        """Register monitoring callbacks with the workflow engine"""
        # Note: This would require modifying WorkflowEngine to support callbacks
        # For now, we'll use a polling approach in the monitor
        pass
    
    async def execute_monitored_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow with monitoring
        
        Args:
            workflow: The workflow definition
            initial_context: Initial context for the workflow
            
        Returns:
            The workflow execution result
        """
        # Start monitoring
        execution = await self.engine.execute_workflow(workflow, initial_context)
        self.monitor.track_execution(execution)
        
        return execution


# Example usage
if __name__ == "__main__":
    async def main():
        # Create monitor
        config = MonitoringConfig(
            websocket_enabled=True,
            max_step_duration_seconds=60
        )
        monitor = WorkflowMonitor(config)
        
        # Add a custom alert handler
        def print_alert(alert: Alert):
            print(f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        
        monitor.add_alert_handler(print_alert)
        
        # Start monitoring
        await monitor.start()
        
        print("Workflow Monitor started. Dashboard data:")
        print(json.dumps(monitor.get_dashboard_data(), indent=2, default=str))
        
        # Keep running
        try:
            await asyncio.sleep(3600)
        finally:
            await monitor.stop()
    
    asyncio.run(main())