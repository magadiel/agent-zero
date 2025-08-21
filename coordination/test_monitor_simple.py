"""
Simple test for Workflow Monitor without pytest
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from coordination.workflow_monitor import (
    WorkflowMonitor,
    MonitoringConfig,
    AlertSeverity,
    WorkflowMetrics
)
from coordination.workflow_engine import (
    WorkflowExecution,
    StepExecution,
    StepState,
    WorkflowState
)


async def test_workflow_monitor():
    """Test basic workflow monitor functionality"""
    print("Testing Workflow Monitor...")
    
    # Create configuration
    config = MonitoringConfig(
        max_step_duration_seconds=60,
        max_workflow_duration_seconds=300,
        websocket_enabled=False
    )
    
    # Create monitor
    monitor = WorkflowMonitor(config)
    
    # Start monitor
    await monitor.start()
    print("✓ Monitor started successfully")
    
    # Create a test execution
    execution = WorkflowExecution(
        workflow_id="test-workflow",
        execution_id="exec-001",
        state=WorkflowState.RUNNING,
        started_at=datetime.now(timezone.utc)
    )
    
    # Add steps
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
    
    # Track execution
    monitor.track_execution(execution)
    print("✓ Execution tracked successfully")
    
    # Test getting status
    status = monitor.get_execution_status(execution.execution_id)
    assert status is not None, "Failed to get execution status"
    assert status["execution_id"] == "exec-001", "Wrong execution ID"
    assert status["state"] == "running", "Wrong state"
    assert status["current_step"] == "step2", "Wrong current step"
    print(f"✓ Execution status: {status['state']}, Progress: {status['progress']:.1f}%")
    
    # Test getting metrics
    metrics = monitor.get_execution_metrics(execution.execution_id)
    assert metrics is not None, "Failed to get metrics"
    assert metrics.total_steps == 3, "Wrong total steps"
    assert metrics.completed_steps == 1, "Wrong completed steps"
    print(f"✓ Metrics: {metrics.completed_steps}/{metrics.total_steps} steps completed")
    
    # Test alerts
    alerts = monitor.get_alerts()
    assert len(alerts) > 0, "No alerts generated"
    print(f"✓ Generated {len(alerts)} alert(s)")
    
    # Test dashboard data
    dashboard = monitor.get_dashboard_data()
    assert dashboard["summary"]["active_workflows"] == 1, "Wrong active workflow count"
    assert len(dashboard["active_workflows"]) == 1, "Wrong active workflows list"
    print(f"✓ Dashboard data generated with {dashboard['summary']['active_workflows']} active workflow(s)")
    
    # Test alert generation
    monitor._generate_alert(
        AlertSeverity.WARNING,
        "Test Alert",
        "This is a test alert",
        workflow_id=execution.execution_id
    )
    
    alerts = monitor.get_alerts(severity=AlertSeverity.WARNING)
    assert len(alerts) > 0, "Warning alert not found"
    print(f"✓ Alert system working: {alerts[0].title}")
    
    # Test acknowledgment
    alert_id = alerts[0].id
    monitor.acknowledge_alert(alert_id, "test_user")
    
    alerts = monitor.get_alerts()
    acknowledged = [a for a in alerts if a.id == alert_id][0]
    assert acknowledged.acknowledged, "Alert not acknowledged"
    print(f"✓ Alert acknowledged by {acknowledged.acknowledged_by}")
    
    # Complete the workflow
    execution.state = WorkflowState.COMPLETED
    execution.completed_at = datetime.now(timezone.utc)
    for step in execution.step_executions.values():
        if step.state != StepState.COMPLETED:
            step.state = StepState.COMPLETED
            step.completed_at = datetime.now(timezone.utc)
    
    # Wait for monitoring loop to process
    await asyncio.sleep(2)
    
    # Check completion stats
    status = monitor.get_execution_status(execution.execution_id)
    assert status["state"] == "completed", "Workflow not marked as completed"
    print(f"✓ Workflow completed successfully")
    
    # Stop monitor
    await monitor.stop()
    print("✓ Monitor stopped successfully")
    
    print("\n✅ All tests passed!")
    return True


async def test_alert_filtering():
    """Test alert filtering functionality"""
    print("\nTesting Alert Filtering...")
    
    config = MonitoringConfig(websocket_enabled=False)
    monitor = WorkflowMonitor(config)
    await monitor.start()
    
    # Generate alerts of different types
    monitor._generate_alert(AlertSeverity.INFO, "Info 1", "Test", workflow_id="wf1")
    monitor._generate_alert(AlertSeverity.WARNING, "Warning 1", "Test", workflow_id="wf1")
    monitor._generate_alert(AlertSeverity.ERROR, "Error 1", "Test", workflow_id="wf2")
    monitor._generate_alert(AlertSeverity.CRITICAL, "Critical 1", "Test", workflow_id="wf2")
    
    # Test severity filtering
    info_alerts = monitor.get_alerts(severity=AlertSeverity.INFO)
    assert len(info_alerts) == 1, f"Expected 1 info alert, got {len(info_alerts)}"
    print(f"✓ Severity filtering: Found {len(info_alerts)} INFO alert(s)")
    
    # Test workflow filtering
    wf1_alerts = monitor.get_alerts(workflow_id="wf1")
    assert len(wf1_alerts) == 2, f"Expected 2 alerts for wf1, got {len(wf1_alerts)}"
    print(f"✓ Workflow filtering: Found {len(wf1_alerts)} alert(s) for wf1")
    
    # Test limit
    limited = monitor.get_alerts(limit=2)
    assert len(limited) == 2, f"Expected 2 alerts with limit, got {len(limited)}"
    print(f"✓ Limit filtering: Limited to {len(limited)} alert(s)")
    
    await monitor.stop()
    print("✅ Alert filtering tests passed!")
    return True


async def test_progress_calculation():
    """Test progress calculation"""
    print("\nTesting Progress Calculation...")
    
    config = MonitoringConfig(websocket_enabled=False)
    monitor = WorkflowMonitor(config)
    
    execution = WorkflowExecution(
        workflow_id="test",
        execution_id="exec-002"
    )
    
    # Add 4 steps in different states
    execution.step_executions["s1"] = StepExecution("s1", state=StepState.COMPLETED)
    execution.step_executions["s2"] = StepExecution("s2", state=StepState.COMPLETED)
    execution.step_executions["s3"] = StepExecution("s3", state=StepState.RUNNING)
    execution.step_executions["s4"] = StepExecution("s4", state=StepState.PENDING)
    
    progress = monitor._calculate_progress(execution)
    expected = 50.0  # 2 out of 4 completed
    assert abs(progress - expected) < 0.01, f"Expected {expected}% progress, got {progress}%"
    print(f"✓ Progress calculation: {progress:.1f}% (2/4 steps completed)")
    
    # Complete one more step
    execution.step_executions["s3"].state = StepState.COMPLETED
    progress = monitor._calculate_progress(execution)
    expected = 75.0  # 3 out of 4 completed
    assert abs(progress - expected) < 0.01, f"Expected {expected}% progress, got {progress}%"
    print(f"✓ Updated progress: {progress:.1f}% (3/4 steps completed)")
    
    print("✅ Progress calculation tests passed!")
    return True


async def main():
    """Run all tests"""
    print("=" * 50)
    print("WORKFLOW MONITOR TEST SUITE")
    print("=" * 50)
    
    try:
        # Run tests
        await test_workflow_monitor()
        await test_alert_filtering()
        await test_progress_calculation()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    exit(0 if success else 1)