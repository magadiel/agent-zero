"""
Tests for Workflow Monitoring System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from coordination.workflow_monitor import (
    WorkflowMonitor,
    MonitoringConfig,
    Alert,
    AlertSeverity,
    MetricType,
    MetricPoint,
    WorkflowMetrics,
    WorkflowMonitorIntegration
)
from coordination.workflow_engine import (
    WorkflowExecution,
    StepExecution,
    StepState,
    WorkflowState
)
from coordination.workflow_parser import WorkflowDefinition


class TestWorkflowMonitor:
    """Test suite for WorkflowMonitor"""
    
    @pytest.fixture
    def monitor_config(self):
        """Create a test monitoring configuration"""
        return MonitoringConfig(
            max_step_duration_seconds=60,
            max_workflow_duration_seconds=300,
            max_retry_count=2,
            websocket_enabled=False,  # Disable WebSocket for tests
            metric_collection_interval=1.0  # Faster for testing
        )
    
    @pytest.fixture
    async def monitor(self, monitor_config):
        """Create a monitor instance"""
        monitor = WorkflowMonitor(monitor_config)
        await monitor.start()
        yield monitor
        await monitor.stop()
    
    @pytest.fixture
    def mock_execution(self):
        """Create a mock workflow execution"""
        execution = WorkflowExecution(
            workflow_id="test-workflow",
            execution_id="exec-123",
            state=WorkflowState.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        # Add some step executions
        execution.step_executions["step1"] = StepExecution(
            step_id="step1",
            state=StepState.COMPLETED,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=30),
            completed_at=datetime.now(timezone.utc) - timedelta(seconds=20),
            agent_id="agent1"
        )
        
        execution.step_executions["step2"] = StepExecution(
            step_id="step2",
            state=StepState.RUNNING,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=10),
            agent_id="agent2"
        )
        
        execution.step_executions["step3"] = StepExecution(
            step_id="step3",
            state=StepState.PENDING
        )
        
        return execution
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, monitor_config):
        """Test monitor initialization"""
        monitor = WorkflowMonitor(monitor_config)
        
        assert monitor.config == monitor_config
        assert not monitor._running
        assert len(monitor._executions) == 0
        assert len(monitor._alerts) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, monitor_config):
        """Test starting and stopping the monitor"""
        monitor = WorkflowMonitor(monitor_config)
        
        # Start monitor
        await monitor.start()
        assert monitor._running
        assert monitor._monitoring_task is not None
        assert monitor._cleanup_task is not None
        
        # Stop monitor
        await monitor.stop()
        assert not monitor._running
    
    @pytest.mark.asyncio
    async def test_track_execution(self, monitor, mock_execution):
        """Test tracking a workflow execution"""
        # Track execution
        monitor.track_execution(mock_execution)
        
        assert mock_execution.execution_id in monitor._executions
        assert monitor._stats["workflows_tracked"] == 1
        
        # Should generate an info alert
        alerts = monitor.get_alerts()
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.INFO
        assert "Started tracking" in alerts[0].message
    
    @pytest.mark.asyncio
    async def test_untrack_execution(self, monitor, mock_execution):
        """Test untracking a workflow execution"""
        # Track and then untrack
        monitor.track_execution(mock_execution)
        monitor.untrack_execution(mock_execution.execution_id)
        
        assert mock_execution.execution_id not in monitor._executions
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, monitor, mock_execution):
        """Test getting execution status"""
        monitor.track_execution(mock_execution)
        
        status = monitor.get_execution_status(mock_execution.execution_id)
        
        assert status is not None
        assert status["execution_id"] == mock_execution.execution_id
        assert status["workflow_id"] == mock_execution.workflow_id
        assert status["state"] == WorkflowState.RUNNING.value
        assert status["progress"] > 0  # Should have some progress
        assert status["current_step"] == "step2"  # Currently running step
        assert "step1" in status["step_states"]
        assert status["step_states"]["step1"] == StepState.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_get_execution_metrics(self, monitor, mock_execution):
        """Test getting execution metrics"""
        monitor.track_execution(mock_execution)
        
        metrics = monitor.get_execution_metrics(mock_execution.execution_id)
        
        assert metrics is not None
        assert metrics.workflow_id == mock_execution.execution_id
        assert metrics.total_steps == 3
        assert metrics.completed_steps == 1
        assert metrics.failed_steps == 0
        assert metrics.success_rate > 0
        assert "agent1" in metrics.agent_utilization
        assert "agent2" in metrics.agent_utilization
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, monitor, mock_execution):
        """Test alert generation for various conditions"""
        # Modify execution to trigger alerts
        mock_execution.step_executions["step2"].started_at = (
            datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        mock_execution.step_executions["step2"].retry_count = 3
        
        monitor.track_execution(mock_execution)
        
        # Let monitoring loop run
        await asyncio.sleep(2)
        
        alerts = monitor.get_alerts()
        
        # Should have multiple alerts
        assert len(alerts) > 1
        
        # Check for specific alert types
        alert_titles = [a.title for a in alerts]
        assert any("Long Running Step" in title for title in alert_titles)
        assert any("Max Retries" in title for title in alert_titles)
    
    @pytest.mark.asyncio
    async def test_alert_filtering(self, monitor):
        """Test alert filtering"""
        # Generate alerts of different severities
        monitor._generate_alert(AlertSeverity.INFO, "Info Alert", "Test info", workflow_id="wf1")
        monitor._generate_alert(AlertSeverity.WARNING, "Warning Alert", "Test warning", workflow_id="wf1")
        monitor._generate_alert(AlertSeverity.ERROR, "Error Alert", "Test error", workflow_id="wf2")
        monitor._generate_alert(AlertSeverity.CRITICAL, "Critical Alert", "Test critical", workflow_id="wf2")
        
        # Test severity filtering
        info_alerts = monitor.get_alerts(severity=AlertSeverity.INFO)
        assert len(info_alerts) == 1
        assert info_alerts[0].severity == AlertSeverity.INFO
        
        # Test workflow filtering
        wf1_alerts = monitor.get_alerts(workflow_id="wf1")
        assert len(wf1_alerts) == 2
        assert all(a.workflow_id == "wf1" for a in wf1_alerts)
        
        # Test limit
        limited_alerts = monitor.get_alerts(limit=2)
        assert len(limited_alerts) == 2
    
    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, monitor):
        """Test alert acknowledgment"""
        # Generate an alert
        monitor._generate_alert(AlertSeverity.ERROR, "Test Alert", "Test message")
        
        alerts = monitor.get_alerts()
        alert_id = alerts[0].id
        
        # Acknowledge the alert
        monitor.acknowledge_alert(alert_id, "test_user")
        
        # Check acknowledgment
        alerts = monitor.get_alerts()
        assert alerts[0].acknowledged
        assert alerts[0].acknowledged_by == "test_user"
        assert alerts[0].acknowledged_at is not None
    
    @pytest.mark.asyncio
    async def test_dashboard_data(self, monitor, mock_execution):
        """Test dashboard data generation"""
        monitor.track_execution(mock_execution)
        
        dashboard = monitor.get_dashboard_data()
        
        assert "summary" in dashboard
        assert dashboard["summary"]["active_workflows"] == 1
        assert dashboard["summary"]["total_workflows"] == 1
        
        assert "active_workflows" in dashboard
        assert len(dashboard["active_workflows"]) == 1
        assert dashboard["active_workflows"][0]["execution_id"] == mock_execution.execution_id
        
        assert "recent_alerts" in dashboard
        assert "metrics" in dashboard
        assert "agent_utilization" in dashboard
    
    @pytest.mark.asyncio
    async def test_progress_calculation(self, monitor, mock_execution):
        """Test workflow progress calculation"""
        monitor.track_execution(mock_execution)
        
        progress = monitor._calculate_progress(mock_execution)
        
        # 1 completed out of 3 steps = 33.33%
        assert progress == pytest.approx(33.33, rel=0.01)
        
        # Complete another step
        mock_execution.step_executions["step2"].state = StepState.COMPLETED
        progress = monitor._calculate_progress(mock_execution)
        
        # 2 completed out of 3 steps = 66.67%
        assert progress == pytest.approx(66.67, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_duration_calculation(self, monitor, mock_execution):
        """Test duration calculation"""
        mock_execution.started_at = datetime.now(timezone.utc) - timedelta(seconds=100)
        
        duration = monitor._calculate_duration(mock_execution)
        
        assert duration is not None
        assert duration >= 100
        assert duration < 110  # Allow some margin
        
        # Test with completed execution
        mock_execution.completed_at = datetime.now(timezone.utc)
        duration = monitor._calculate_duration(mock_execution)
        
        assert duration >= 100
    
    @pytest.mark.asyncio
    async def test_metric_recording(self, monitor):
        """Test metric recording and retrieval"""
        # Record some metrics
        monitor._record_metric(MetricType.WORKFLOW_DURATION, 120.5, {"workflow_id": "wf1"})
        monitor._record_metric(MetricType.STEP_DURATION, 15.3, {"step_id": "step1"})
        monitor._record_metric(MetricType.AGENT_UTILIZATION, 0.75, {"agent_id": "agent1"})
        
        # Check metrics are stored
        assert len(monitor._metrics[MetricType.WORKFLOW_DURATION]) == 1
        assert monitor._metrics[MetricType.WORKFLOW_DURATION][0].value == 120.5
        
        assert len(monitor._metrics[MetricType.STEP_DURATION]) == 1
        assert monitor._metrics[MetricType.STEP_DURATION][0].value == 15.3
        
        assert len(monitor._metrics[MetricType.AGENT_UTILIZATION]) == 1
        assert monitor._metrics[MetricType.AGENT_UTILIZATION][0].value == 0.75
    
    @pytest.mark.asyncio
    async def test_agent_utilization(self, monitor):
        """Test agent utilization calculation"""
        # Create multiple executions with different agents
        exec1 = WorkflowExecution(
            workflow_id="wf1",
            execution_id="exec1"
        )
        exec1.step_executions["step1"] = StepExecution(
            step_id="step1",
            state=StepState.RUNNING,
            agent_id="agent1"
        )
        
        exec2 = WorkflowExecution(
            workflow_id="wf2",
            execution_id="exec2"
        )
        exec2.step_executions["step2"] = StepExecution(
            step_id="step2",
            state=StepState.RUNNING,
            agent_id="agent1"
        )
        exec2.step_executions["step3"] = StepExecution(
            step_id="step3",
            state=StepState.COMPLETED,
            agent_id="agent2"
        )
        
        monitor.track_execution(exec1)
        monitor.track_execution(exec2)
        
        utilization = monitor._calculate_agent_utilization()
        
        assert utilization["agent1"] == 2  # 2 running tasks
        assert utilization["agent2"] == 0  # No running tasks
    
    @pytest.mark.asyncio
    async def test_alert_handler(self, monitor):
        """Test custom alert handler"""
        received_alerts = []
        
        def custom_handler(alert: Alert):
            received_alerts.append(alert)
        
        monitor.add_alert_handler(custom_handler)
        
        # Generate an alert
        monitor._generate_alert(AlertSeverity.ERROR, "Test", "Test message")
        
        # Handler should have been called
        assert len(received_alerts) == 1
        assert received_alerts[0].title == "Test"
    
    @pytest.mark.asyncio
    async def test_workflow_completion_tracking(self, monitor, mock_execution):
        """Test tracking of workflow completion"""
        monitor.track_execution(mock_execution)
        
        # Complete the workflow
        mock_execution.state = WorkflowState.COMPLETED
        mock_execution.completed_at = datetime.now(timezone.utc)
        
        # Let monitoring loop detect completion
        await asyncio.sleep(2)
        
        assert monitor._stats["workflows_completed"] > 0
        
        # Check for success rate metric
        success_metrics = [
            m for m in monitor._metrics[MetricType.SUCCESS_RATE]
            if m.labels.get("workflow_id") == mock_execution.workflow_id
        ]
        assert len(success_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_workflow_failure_tracking(self, monitor, mock_execution):
        """Test tracking of workflow failures"""
        monitor.track_execution(mock_execution)
        
        # Fail the workflow
        mock_execution.state = WorkflowState.FAILED
        mock_execution.error = "Test error"
        
        # Let monitoring loop detect failure
        await asyncio.sleep(2)
        
        assert monitor._stats["workflows_failed"] > 0
        
        # Should have generated an error alert
        alerts = monitor.get_alerts(severity=AlertSeverity.ERROR)
        assert any("Workflow Failed" in a.title for a in alerts)
    
    @pytest.mark.asyncio
    async def test_high_error_rate_detection(self, monitor, mock_execution):
        """Test detection of high error rates"""
        # Add more failed steps
        mock_execution.step_executions["step2"].state = StepState.FAILED
        mock_execution.step_executions["step3"].state = StepState.FAILED
        
        monitor.track_execution(mock_execution)
        
        # Let monitoring loop detect high error rate
        await asyncio.sleep(2)
        
        alerts = monitor.get_alerts(severity=AlertSeverity.ERROR)
        assert any("High Error Rate" in a.title for a in alerts)
    
    @pytest.mark.asyncio
    async def test_metric_cleanup(self, monitor):
        """Test cleanup of old metrics"""
        # Add old metric
        old_metric = MetricPoint(
            metric_type=MetricType.WORKFLOW_DURATION,
            value=100,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        monitor._metrics[MetricType.WORKFLOW_DURATION].append(old_metric)
        
        # Add recent metric
        recent_metric = MetricPoint(
            metric_type=MetricType.WORKFLOW_DURATION,
            value=200
        )
        monitor._metrics[MetricType.WORKFLOW_DURATION].append(recent_metric)
        
        # Run cleanup (normally runs every hour, but we'll call it directly)
        await monitor._cleanup_loop.__wrapped__(monitor)
        
        # Old metric should be removed
        assert len(monitor._metrics[MetricType.WORKFLOW_DURATION]) == 1
        assert monitor._metrics[MetricType.WORKFLOW_DURATION][0].value == 200


class TestWorkflowMonitorIntegration:
    """Test suite for WorkflowMonitorIntegration"""
    
    @pytest.fixture
    def mock_monitor(self):
        """Create a mock monitor"""
        monitor = MagicMock(spec=WorkflowMonitor)
        monitor.track_execution = MagicMock()
        return monitor
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine"""
        engine = AsyncMock()
        engine.execute_workflow = AsyncMock(return_value=WorkflowExecution(
            workflow_id="test",
            execution_id="exec-123"
        ))
        return engine
    
    @pytest.fixture
    def integration(self, mock_monitor, mock_engine):
        """Create an integration instance"""
        return WorkflowMonitorIntegration(mock_monitor, mock_engine)
    
    @pytest.mark.asyncio
    async def test_execute_monitored_workflow(self, integration, mock_monitor, mock_engine):
        """Test executing a workflow with monitoring"""
        workflow = MagicMock(spec=WorkflowDefinition)
        context = {"test": "context"}
        
        execution = await integration.execute_monitored_workflow(workflow, context)
        
        # Engine should have been called
        mock_engine.execute_workflow.assert_called_once_with(workflow, context)
        
        # Monitor should track the execution
        mock_monitor.track_execution.assert_called_once()
        
        # Should return the execution
        assert execution.execution_id == "exec-123"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])