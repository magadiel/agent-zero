"""
Metrics API for KPI Dashboard
Provides REST and WebSocket endpoints for accessing and streaming metrics data
"""

from fastapi import FastAPI, WebSocket, HTTPException, Query, Path, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import logging
from pathlib import Path as FilePath
import sys

# Add project root to path for imports
project_root = FilePath(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import metrics systems
try:
    from metrics.quality_tracker import QualityTracker, GateStatus
    from metrics.performance_monitor import PerformanceMonitor
    from metrics.agile_metrics import AgileMetrics, MetricType
    from metrics.velocity_tracker import VelocityTracker
    from metrics.dashboard import Dashboard, DashboardView
    from coordination.workflow_monitor import WorkflowMonitor
except ImportError as e:
    logging.warning(f"Some metrics modules not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="KPI Dashboard API",
    description="API for accessing and streaming KPI metrics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances of metrics systems
quality_tracker = None
performance_monitor = None
agile_metrics = None
velocity_tracker = None
workflow_monitor = None
dashboard = None

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

class MetricCategory(str, Enum):
    """Categories of metrics available"""
    VELOCITY = "velocity"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"
    AGILE = "agile"
    WORKFLOW = "workflow"
    TEAM = "team"
    ALL = "all"

class TimeRange(str, Enum):
    """Time ranges for metric queries"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    SPRINT = "sprint"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"

@app.on_event("startup")
async def startup_event():
    """Initialize metrics systems on startup"""
    global quality_tracker, performance_monitor, agile_metrics
    global velocity_tracker, workflow_monitor, dashboard
    
    try:
        quality_tracker = QualityTracker()
        performance_monitor = PerformanceMonitor()
        agile_metrics = AgileMetrics()
        velocity_tracker = VelocityTracker()
        workflow_monitor = WorkflowMonitor()
        dashboard = Dashboard()
        
        # Start background monitoring if available
        if hasattr(performance_monitor, 'start_monitoring'):
            asyncio.create_task(performance_monitor.start_monitoring())
        
        logger.info("Metrics systems initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize metrics systems: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if performance_monitor and hasattr(performance_monitor, 'stop_monitoring'):
        performance_monitor.stop_monitoring()
    
    # Close all WebSocket connections
    for connection in active_connections:
        await connection.close()

# REST API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "title": "KPI Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "metrics": "/metrics/{category}",
            "dashboard": "/dashboard/{view}",
            "teams": "/teams/{team_id}/metrics",
            "velocity": "/velocity/{team_id}",
            "quality": "/quality/gates",
            "performance": "/performance/summary",
            "export": "/export/{format}",
            "ws": "/ws"
        }
    }

@app.get("/metrics/{category}")
async def get_metrics(
    category: MetricCategory,
    time_range: TimeRange = Query(TimeRange.WEEK),
    team_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Get metrics by category"""
    try:
        metrics_data = {}
        
        if category in [MetricCategory.VELOCITY, MetricCategory.ALL]:
            if velocity_tracker:
                velocity_data = velocity_tracker.get_velocity_trend(
                    team_id=team_id or "default",
                    sprints=_get_sprint_count(time_range)
                )
                metrics_data["velocity"] = velocity_data
        
        if category in [MetricCategory.QUALITY, MetricCategory.ALL]:
            if quality_tracker:
                quality_data = quality_tracker.get_summary()
                metrics_data["quality"] = quality_data
        
        if category in [MetricCategory.PERFORMANCE, MetricCategory.ALL]:
            if performance_monitor:
                perf_data = performance_monitor.get_statistics()
                metrics_data["performance"] = perf_data
        
        if category in [MetricCategory.EFFICIENCY, MetricCategory.ALL]:
            if performance_monitor:
                efficiency = performance_monitor.get_efficiency_score()
                metrics_data["efficiency"] = {
                    "score": efficiency,
                    "breakdown": performance_monitor.get_bottlenecks()
                }
        
        if category in [MetricCategory.AGILE, MetricCategory.ALL]:
            if agile_metrics:
                agile_data = {}
                for metric_type in MetricType:
                    agile_data[metric_type.value] = agile_metrics.get_metric(
                        metric_type,
                        team_id or "default"
                    )
                metrics_data["agile"] = agile_data
        
        if category in [MetricCategory.WORKFLOW, MetricCategory.ALL]:
            if workflow_monitor:
                workflow_data = workflow_monitor.get_all_workflows_status()
                metrics_data["workflow"] = workflow_data
        
        if category in [MetricCategory.TEAM, MetricCategory.ALL]:
            team_data = await _get_team_metrics(team_id, time_range)
            metrics_data["team"] = team_data
        
        return {
            "status": "success",
            "category": category,
            "time_range": time_range,
            "team_id": team_id,
            "data": metrics_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/{view}")
async def get_dashboard(
    view: DashboardView,
    team_id: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Get dashboard data for specific view"""
    try:
        if not dashboard:
            raise HTTPException(status_code=503, detail="Dashboard not available")
        
        view_data = dashboard.get_view(view, team_id=team_id)
        
        return {
            "status": "success",
            "view": view,
            "team_id": team_id,
            "data": view_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/teams/{team_id}/metrics")
async def get_team_metrics(
    team_id: str = Path(...),
    include_members: bool = Query(False)
) -> Dict[str, Any]:
    """Get comprehensive metrics for a specific team"""
    try:
        team_metrics = {
            "team_id": team_id,
            "velocity": None,
            "quality": None,
            "efficiency": None,
            "performance": None,
            "health_score": None
        }
        
        # Velocity metrics
        if velocity_tracker:
            team_metrics["velocity"] = {
                "current": velocity_tracker.get_current_velocity(team_id),
                "average": velocity_tracker.get_average_velocity(team_id),
                "trend": velocity_tracker.get_velocity_trend(team_id, sprints=5)
            }
        
        # Quality metrics
        if quality_tracker:
            gates = quality_tracker.get_gates_by_type()
            team_gates = [g for g in gates.get("story", []) 
                         if g.get("metadata", {}).get("team_id") == team_id]
            team_metrics["quality"] = {
                "gates_passed": len([g for g in team_gates if g["status"] == GateStatus.PASS]),
                "gates_failed": len([g for g in team_gates if g["status"] == GateStatus.FAIL]),
                "issues": quality_tracker.get_open_issues()
            }
        
        # Performance metrics
        if performance_monitor:
            team_metrics["performance"] = {
                "response_times": performance_monitor.get_metric_stats("response_time"),
                "task_success_rate": performance_monitor.get_task_success_rate(),
                "resource_usage": performance_monitor.get_current_metrics()
            }
        
        # Efficiency score
        if performance_monitor:
            team_metrics["efficiency"] = performance_monitor.get_efficiency_score()
        
        # Calculate health score
        team_metrics["health_score"] = _calculate_team_health(team_metrics)
        
        # Include member metrics if requested
        if include_members:
            team_metrics["members"] = await _get_team_member_metrics(team_id)
        
        return {
            "status": "success",
            "data": team_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching team metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/velocity/{team_id}")
async def get_velocity_metrics(
    team_id: str = Path(...),
    sprints: int = Query(5, ge=1, le=20)
) -> Dict[str, Any]:
    """Get velocity metrics for a team"""
    try:
        if not velocity_tracker:
            raise HTTPException(status_code=503, detail="Velocity tracker not available")
        
        velocity_data = {
            "current": velocity_tracker.get_current_velocity(team_id),
            "average": velocity_tracker.get_average_velocity(team_id),
            "trend": velocity_tracker.get_velocity_trend(team_id, sprints),
            "prediction": velocity_tracker.predict_velocity(team_id),
            "capacity": velocity_tracker.get_capacity_metrics(team_id)
        }
        
        return {
            "status": "success",
            "team_id": team_id,
            "data": velocity_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching velocity metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quality/gates")
async def get_quality_gates(
    gate_type: Optional[str] = Query(None),
    status: Optional[GateStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """Get quality gate information"""
    try:
        if not quality_tracker:
            raise HTTPException(status_code=503, detail="Quality tracker not available")
        
        gates = quality_tracker.get_gates_by_type()
        
        # Filter by type if specified
        if gate_type:
            gates = {gate_type: gates.get(gate_type, [])}
        
        # Filter by status if specified
        if status:
            for gate_type in gates:
                gates[gate_type] = [g for g in gates[gate_type] 
                                  if g["status"] == status][:limit]
        
        summary = quality_tracker.get_summary()
        
        return {
            "status": "success",
            "data": {
                "gates": gates,
                "summary": summary,
                "open_issues": quality_tracker.get_open_issues()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching quality gates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance/summary")
async def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    try:
        if not performance_monitor:
            raise HTTPException(status_code=503, detail="Performance monitor not available")
        
        summary = {
            "statistics": performance_monitor.get_statistics(),
            "current_metrics": performance_monitor.get_current_metrics(),
            "bottlenecks": performance_monitor.get_bottlenecks(),
            "efficiency_score": performance_monitor.get_efficiency_score(),
            "task_success_rate": performance_monitor.get_task_success_rate(),
            "alerts": performance_monitor.get_active_alerts()
        }
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/{format}")
async def export_metrics(
    format: str = Path(..., regex="^(json|csv|markdown|html)$"),
    category: MetricCategory = Query(MetricCategory.ALL),
    time_range: TimeRange = Query(TimeRange.WEEK)
) -> Union[Dict, str]:
    """Export metrics in specified format"""
    try:
        # Gather all metrics
        metrics = await get_metrics(category, time_range, None, 1000)
        
        if format == "json":
            return metrics
        
        elif format == "csv":
            csv_data = _convert_to_csv(metrics["data"])
            return JSONResponse(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=metrics.csv"}
            )
        
        elif format == "markdown":
            if dashboard:
                md_report = dashboard.export_markdown()
            else:
                md_report = _convert_to_markdown(metrics["data"])
            return JSONResponse(
                content=md_report,
                media_type="text/markdown",
                headers={"Content-Disposition": "attachment; filename=metrics.md"}
            )
        
        elif format == "html":
            if dashboard:
                html_report = dashboard.export_html()
            else:
                html_report = _convert_to_html(metrics["data"])
            return JSONResponse(
                content=html_report,
                media_type="text/html",
                headers={"Content-Disposition": "attachment; filename=metrics.html"}
            )
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metric updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial data
        initial_data = {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(initial_data)
        
        # Start sending periodic updates
        while True:
            try:
                # Wait for client messages or timeout for periodic updates
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=5.0  # Send updates every 5 seconds
                )
                
                # Handle client requests
                if message.get("type") == "subscribe":
                    category = message.get("category", "all")
                    team_id = message.get("team_id")
                    await _send_metric_update(websocket, category, team_id)
                
                elif message.get("type") == "unsubscribe":
                    # Handle unsubscribe logic
                    pass
                
            except asyncio.TimeoutError:
                # Send periodic updates
                await _send_periodic_update(websocket)
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)

# Helper functions

def _get_sprint_count(time_range: TimeRange) -> int:
    """Convert time range to number of sprints"""
    sprint_mapping = {
        TimeRange.HOUR: 1,
        TimeRange.DAY: 1,
        TimeRange.WEEK: 1,
        TimeRange.SPRINT: 1,
        TimeRange.MONTH: 2,
        TimeRange.QUARTER: 6,
        TimeRange.YEAR: 26,
        TimeRange.ALL: 52
    }
    return sprint_mapping.get(time_range, 5)

async def _get_team_metrics(team_id: Optional[str], time_range: TimeRange) -> Dict[str, Any]:
    """Get aggregated team metrics"""
    team_metrics = {}
    
    if agile_metrics:
        team_metrics["velocity"] = agile_metrics.get_metric(
            MetricType.VELOCITY,
            team_id or "all"
        )
        team_metrics["cycle_time"] = agile_metrics.get_metric(
            MetricType.CYCLE_TIME,
            team_id or "all"
        )
        team_metrics["throughput"] = agile_metrics.get_metric(
            MetricType.THROUGHPUT,
            team_id or "all"
        )
    
    return team_metrics

async def _get_team_member_metrics(team_id: str) -> List[Dict[str, Any]]:
    """Get metrics for team members"""
    # Placeholder for team member metrics
    # Would integrate with team management system
    return []

def _calculate_team_health(metrics: Dict[str, Any]) -> float:
    """Calculate overall team health score"""
    score = 0.0
    weights = {
        "velocity": 0.3,
        "quality": 0.3,
        "efficiency": 0.2,
        "performance": 0.2
    }
    
    # Velocity contribution
    if metrics.get("velocity"):
        velocity_data = metrics["velocity"]
        if velocity_data.get("trend"):
            # Positive trend increases score
            score += weights["velocity"] * 0.8
    
    # Quality contribution
    if metrics.get("quality"):
        quality_data = metrics["quality"]
        total_gates = quality_data.get("gates_passed", 0) + quality_data.get("gates_failed", 0)
        if total_gates > 0:
            pass_rate = quality_data.get("gates_passed", 0) / total_gates
            score += weights["quality"] * pass_rate
    
    # Efficiency contribution
    if metrics.get("efficiency"):
        score += weights["efficiency"] * min(metrics["efficiency"], 1.0)
    
    # Performance contribution
    if metrics.get("performance"):
        if metrics["performance"].get("task_success_rate"):
            score += weights["performance"] * metrics["performance"]["task_success_rate"]
    
    return round(score * 100, 2)

async def _send_metric_update(websocket: WebSocket, category: str, team_id: Optional[str]):
    """Send metric update to WebSocket client"""
    try:
        metrics = await get_metrics(
            MetricCategory(category),
            TimeRange.DAY,
            team_id,
            50
        )
        
        update = {
            "type": "metric_update",
            "category": category,
            "team_id": team_id,
            "data": metrics["data"],
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send_json(update)
        
    except Exception as e:
        logger.error(f"Error sending metric update: {e}")

async def _send_periodic_update(websocket: WebSocket):
    """Send periodic update to WebSocket client"""
    try:
        # Send current performance metrics
        if performance_monitor:
            current_metrics = performance_monitor.get_current_metrics()
            update = {
                "type": "periodic_update",
                "data": {
                    "performance": current_metrics,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await websocket.send_json(update)
            
    except Exception as e:
        logger.error(f"Error sending periodic update: {e}")

def _convert_to_csv(data: Dict[str, Any]) -> str:
    """Convert metrics data to CSV format"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["Category", "Metric", "Value", "Timestamp"])
    
    # Write data
    timestamp = datetime.now().isoformat()
    for category, metrics in data.items():
        if isinstance(metrics, dict):
            for metric, value in metrics.items():
                writer.writerow([category, metric, str(value), timestamp])
        else:
            writer.writerow([category, "value", str(metrics), timestamp])
    
    return output.getvalue()

def _convert_to_markdown(data: Dict[str, Any]) -> str:
    """Convert metrics data to Markdown format"""
    lines = ["# KPI Dashboard Report", ""]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    for category, metrics in data.items():
        lines.append(f"## {category.title()}")
        lines.append("")
        
        if isinstance(metrics, dict):
            for metric, value in metrics.items():
                lines.append(f"- **{metric}**: {value}")
        else:
            lines.append(f"- {metrics}")
        
        lines.append("")
    
    return "\n".join(lines)

def _convert_to_html(data: Dict[str, Any]) -> str:
    """Convert metrics data to HTML format"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KPI Dashboard Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            h2 { color: #666; border-bottom: 1px solid #ddd; }
            .metric { margin: 10px 0; }
            .metric-name { font-weight: bold; }
            .timestamp { color: #999; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>KPI Dashboard Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
    """.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    for category, metrics in data.items():
        html += f"<h2>{category.title()}</h2>"
        
        if isinstance(metrics, dict):
            for metric, value in metrics.items():
                html += f'<div class="metric"><span class="metric-name">{metric}:</span> {value}</div>'
        else:
            html += f'<div class="metric">{metrics}</div>'
    
    html += "</body></html>"
    return html

# Run the API if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)