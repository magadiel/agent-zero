"""
Workflow Monitoring API for Agent-Zero

This module provides REST API endpoints for the workflow monitoring system,
enabling integration with the web dashboard and external monitoring tools.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
import os
from pathlib import Path

# Import monitoring components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from coordination.workflow_monitor import (
    WorkflowMonitor,
    MonitoringConfig,
    AlertSeverity,
    Alert,
    WorkflowMonitorIntegration
)
from coordination.workflow_engine import WorkflowEngine
from coordination.workflow_parser import WorkflowParser

# Create FastAPI app
app = FastAPI(
    title="Workflow Monitoring API",
    description="Real-time monitoring and management of Agent-Zero workflows",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
monitor: Optional[WorkflowMonitor] = None
engine: Optional[WorkflowEngine] = None
integration: Optional[WorkflowMonitorIntegration] = None
websocket_manager = None


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: dict):
        message_text = json.dumps(message)
        # Use list() to avoid modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_text)
            except:
                # Remove dead connections
                self.disconnect(connection)


@app.on_event("startup")
async def startup_event():
    """Initialize the monitoring system on startup"""
    global monitor, engine, integration, websocket_manager
    
    # Create monitoring configuration
    config = MonitoringConfig(
        websocket_enabled=False,  # We handle WebSocket separately
        max_step_duration_seconds=300,
        max_workflow_duration_seconds=3600
    )
    
    # Initialize components
    monitor = WorkflowMonitor(config)
    engine = WorkflowEngine()
    integration = WorkflowMonitorIntegration(monitor, engine)
    websocket_manager = WebSocketManager()
    
    # Add alert handler to broadcast to WebSocket clients
    def broadcast_alert(alert: Alert):
        asyncio.create_task(websocket_manager.broadcast({
            "type": "alert",
            "data": {
                "id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "workflow_id": alert.workflow_id,
                "timestamp": alert.timestamp.isoformat()
            }
        }))
    
    monitor.add_alert_handler(broadcast_alert)
    
    # Start monitoring
    await monitor.start()
    
    print("Workflow Monitoring API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global monitor
    if monitor:
        await monitor.stop()


# REST API Endpoints

@app.get("/")
async def root():
    """Root endpoint - serve the dashboard"""
    dashboard_path = Path(__file__).parent.parent.parent / "webui" / "components" / "workflow_dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Workflow Monitoring API", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "monitor_running": monitor is not None and monitor._running
    }


@app.get("/api/workflow/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    return monitor.get_dashboard_data()


@app.get("/api/workflow/{execution_id}/status")
async def get_workflow_status(execution_id: str):
    """Get status of a specific workflow execution"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    status = monitor.get_execution_status(execution_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    
    return status


@app.get("/api/workflow/{execution_id}/metrics")
async def get_workflow_metrics(execution_id: str):
    """Get metrics for a specific workflow execution"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    metrics = monitor.get_execution_metrics(execution_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    
    return {
        "workflow_id": metrics.workflow_id,
        "total_steps": metrics.total_steps,
        "completed_steps": metrics.completed_steps,
        "failed_steps": metrics.failed_steps,
        "skipped_steps": metrics.skipped_steps,
        "duration_seconds": metrics.duration_seconds,
        "average_step_duration": metrics.average_step_duration,
        "error_rate": metrics.error_rate,
        "success_rate": metrics.success_rate,
        "agent_utilization": metrics.agent_utilization
    }


@app.get("/api/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    workflow_id: Optional[str] = None,
    limit: int = 100
):
    """Get alerts with optional filtering"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    # Convert severity string to enum if provided
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    alerts = monitor.get_alerts(severity_enum, workflow_id, limit)
    
    return [
        {
            "id": alert.id,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "workflow_id": alert.workflow_id,
            "step_id": alert.step_id,
            "agent_id": alert.agent_id,
            "timestamp": alert.timestamp.isoformat(),
            "acknowledged": alert.acknowledged,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        }
        for alert in alerts
    ]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "api_user"):
    """Acknowledge an alert"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    monitor.acknowledge_alert(alert_id, acknowledged_by)
    
    # Broadcast update to WebSocket clients
    await websocket_manager.broadcast({
        "type": "alert_acknowledged",
        "data": {
            "alert_id": alert_id,
            "acknowledged_by": acknowledged_by
        }
    })
    
    return {"status": "acknowledged", "alert_id": alert_id}


@app.post("/api/workflow/execute")
async def execute_workflow(workflow_definition: dict, initial_context: Optional[dict] = None):
    """Execute a workflow with monitoring"""
    if not integration:
        raise HTTPException(status_code=503, detail="Integration not initialized")
    
    try:
        # Parse workflow definition
        parser = WorkflowParser()
        workflow = parser.parse(workflow_definition)
        
        # Execute with monitoring
        execution = await integration.execute_monitored_workflow(workflow, initial_context)
        
        # Broadcast to WebSocket clients
        await websocket_manager.broadcast({
            "type": "workflow_started",
            "data": {
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id
            }
        })
        
        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "state": execution.state.value
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/workflow/{execution_id}")
async def stop_workflow(execution_id: str):
    """Stop tracking a workflow execution"""
    if not monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    monitor.untrack_execution(execution_id)
    
    # Broadcast to WebSocket clients
    await websocket_manager.broadcast({
        "type": "workflow_stopped",
        "data": {
            "execution_id": execution_id
        }
    })
    
    return {"status": "stopped", "execution_id": execution_id}


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial dashboard data
        initial_data = monitor.get_dashboard_data() if monitor else {}
        await websocket.send_text(json.dumps({
            "type": "initial",
            "data": initial_data
        }))
        
        # Keep connection alive and handle messages
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Handle client requests
            try:
                message = json.loads(data)
                if message.get("type") == "refresh":
                    dashboard_data = monitor.get_dashboard_data() if monitor else {}
                    await websocket.send_text(json.dumps({
                        "type": "update",
                        "data": dashboard_data
                    }))
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# Serve static files (if needed)
@app.get("/dashboard")
async def serve_dashboard():
    """Serve the workflow dashboard HTML"""
    dashboard_path = Path(__file__).parent.parent.parent / "webui" / "components" / "workflow_dashboard.html"
    if dashboard_path.exists():
        with open(dashboard_path, 'r') as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")


# Integration with Agent-Zero tools
class WorkflowMonitoringTool:
    """
    Agent-Zero tool for workflow monitoring
    
    This tool allows agents to interact with the monitoring system
    """
    
    def __init__(self, monitor: WorkflowMonitor):
        self.monitor = monitor
    
    async def get_workflow_status(self, execution_id: str) -> dict:
        """Get the status of a workflow execution"""
        status = self.monitor.get_execution_status(execution_id)
        if not status:
            raise ValueError(f"Workflow execution {execution_id} not found")
        return status
    
    async def get_alerts(self, severity: Optional[str] = None) -> List[dict]:
        """Get current alerts"""
        severity_enum = AlertSeverity(severity) if severity else None
        alerts = self.monitor.get_alerts(severity_enum)
        return [
            {
                "id": a.id,
                "severity": a.severity.value,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp.isoformat()
            }
            for a in alerts
        ]
    
    async def acknowledge_alert(self, alert_id: str) -> dict:
        """Acknowledge an alert"""
        self.monitor.acknowledge_alert(alert_id, "agent")
        return {"status": "acknowledged", "alert_id": alert_id}


# Main entry point for testing
if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )