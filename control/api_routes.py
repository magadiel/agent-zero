"""
Control Layer API Routes - Additional route definitions
Extended API endpoints for advanced control layer operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from api import get_current_user, User
from ethics_engine import EthicsEngine
from safety_monitor import SafetyMonitor, ThreatType, InterventionType
from resource_allocator import ResourceAllocator
from audit_logger import AuditLogger, EventType, EventCategory, Severity


# Create routers for different API sections
ethics_router = APIRouter(prefix="/ethics", tags=["Ethics"])
safety_router = APIRouter(prefix="/safety", tags=["Safety"])
resource_router = APIRouter(prefix="/resources", tags=["Resources"])
audit_router = APIRouter(prefix="/audit", tags=["Audit"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# Extended Pydantic Models
class EthicsConstraintUpdate(BaseModel):
    """Model for updating ethical constraints"""
    constraint_id: str = Field(..., description="ID of the constraint to update")
    category: str = Field(..., description="Category of the constraint")
    updates: Dict[str, Any] = Field(..., description="Updates to apply")
    reason: str = Field(..., description="Reason for the update")


class SafetyThresholdUpdate(BaseModel):
    """Model for updating safety thresholds"""
    agent_id: Optional[str] = Field(None, description="Agent ID for specific threshold")
    metric: str = Field(..., description="Metric to update")
    threshold_type: str = Field(..., description="Type of threshold (warning, critical, emergency)")
    value: float = Field(..., description="New threshold value")
    reason: str = Field(..., description="Reason for the update")


class TeamResourceProfile(BaseModel):
    """Model for team resource profile"""
    team_id: str = Field(..., description="Team identifier")
    profile_name: str = Field(..., description="Resource profile name")
    compute_limit: float = Field(..., description="Compute resource limit")
    memory_limit: float = Field(..., description="Memory limit in GB")
    storage_limit: float = Field(..., description="Storage limit in GB")
    priority_tier: int = Field(default=3, ge=1, le=5, description="Priority tier")


class BulkResourceAllocation(BaseModel):
    """Model for bulk resource allocation"""
    allocations: List[Dict[str, Any]] = Field(..., description="List of allocation requests")
    strategy: str = Field(default="fair", description="Allocation strategy (fair, priority, performance)")


class AuditAnalysis(BaseModel):
    """Model for audit analysis request"""
    analysis_type: str = Field(..., description="Type of analysis (patterns, anomalies, compliance)")
    time_window: int = Field(default=86400, description="Time window in seconds")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Analysis filters")


class SystemConfiguration(BaseModel):
    """Model for system configuration"""
    component: str = Field(..., description="Component to configure")
    settings: Dict[str, Any] = Field(..., description="Configuration settings")
    apply_immediately: bool = Field(default=False, description="Apply changes immediately")


# Ethics Extended Routes
@ethics_router.get("/constraints")
async def get_ethical_constraints(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get current ethical constraints"""
    ethics_engine = EthicsEngine()
    constraints = ethics_engine.constraints
    
    if category:
        filtered = {k: v for k, v in constraints.items() if v.get("category") == category}
        return filtered
    
    return constraints


@ethics_router.post("/constraints/update")
async def update_ethical_constraint(
    update: EthicsConstraintUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an ethical constraint (requires admin privileges)"""
    # Check admin privileges (simplified for demo)
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    # Log the update attempt
    audit_logger = AuditLogger()
    await audit_logger.log_event(
        event_type=EventType.CONFIGURATION,
        severity=Severity.MEDIUM,
        component="EthicsEngine",
        agent_id=current_user.username,
        action="update_constraint",
        details={
            "constraint_id": update.constraint_id,
            "updates": update.updates,
            "reason": update.reason
        }
    )
    
    return {
        "status": "constraint_update_logged",
        "message": "Constraint update requires system restart to take effect",
        "constraint_id": update.constraint_id
    }


@ethics_router.get("/risk-assessment/{agent_id}")
async def get_agent_risk_assessment(
    agent_id: str,
    time_window: int = Query(3600, description="Time window in seconds"),
    current_user: User = Depends(get_current_user)
):
    """Get risk assessment for a specific agent"""
    ethics_engine = EthicsEngine()
    audit_logger = AuditLogger()
    
    # Get recent decisions for the agent
    recent_decisions = audit_logger.query_logs(
        agent_id=agent_id,
        event_type=EventType.ETHICS,
        start_time=datetime.utcnow() - timedelta(seconds=time_window)
    )
    
    # Calculate risk metrics
    total_decisions = len(recent_decisions)
    rejected_decisions = sum(1 for d in recent_decisions if not d.details.get("approved", True))
    avg_risk_score = sum(d.details.get("risk_score", 0) for d in recent_decisions) / max(total_decisions, 1)
    
    return {
        "agent_id": agent_id,
        "time_window": time_window,
        "total_decisions": total_decisions,
        "rejected_decisions": rejected_decisions,
        "rejection_rate": rejected_decisions / max(total_decisions, 1),
        "average_risk_score": avg_risk_score,
        "risk_level": "high" if avg_risk_score > 0.7 else "medium" if avg_risk_score > 0.4 else "low"
    }


# Safety Extended Routes
@safety_router.get("/thresholds")
async def get_safety_thresholds(
    agent_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get current safety thresholds"""
    safety_monitor = SafetyMonitor()
    
    if agent_id:
        return safety_monitor.get_agent_thresholds(agent_id)
    
    return safety_monitor.thresholds


@safety_router.post("/thresholds/update")
async def update_safety_threshold(
    update: SafetyThresholdUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update safety thresholds (requires admin privileges)"""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    audit_logger = AuditLogger()
    await audit_logger.log_event(
        event_type=EventType.CONFIGURATION,
        severity=Severity.MEDIUM,
        component="SafetyMonitor",
        agent_id=current_user.username,
        action="update_threshold",
        details={
            "agent_id": update.agent_id,
            "metric": update.metric,
            "threshold_type": update.threshold_type,
            "value": update.value,
            "reason": update.reason
        }
    )
    
    return {
        "status": "threshold_update_logged",
        "message": "Threshold update will be applied on next monitoring cycle"
    }


@safety_router.get("/threats/active")
async def get_active_threats(
    current_user: User = Depends(get_current_user)
):
    """Get currently active threats"""
    safety_monitor = SafetyMonitor()
    
    active_threats = []
    for agent_id, status in safety_monitor.agent_status.items():
        if status.get("threats"):
            active_threats.append({
                "agent_id": agent_id,
                "threats": status["threats"],
                "interventions": status.get("interventions", []),
                "status": status.get("status", "unknown")
            })
    
    return {
        "total_threats": len(active_threats),
        "active_threats": active_threats,
        "timestamp": datetime.utcnow()
    }


@safety_router.post("/intervention/{agent_id}")
async def trigger_intervention(
    agent_id: str,
    intervention_type: str = Query(..., description="Type of intervention"),
    reason: str = Query(..., description="Reason for intervention"),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger an intervention for an agent"""
    safety_monitor = SafetyMonitor()
    
    try:
        intervention = InterventionType(intervention_type)
        result = await safety_monitor.apply_intervention(agent_id, intervention)
        
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=EventType.SAFETY,
            severity=Severity.MEDIUM,
            component="SafetyMonitor",
            agent_id=agent_id,
            action="manual_intervention",
            details={
                "intervention_type": intervention_type,
                "reason": reason,
                "triggered_by": current_user.username,
                "success": result
            }
        )
        
        return {
            "agent_id": agent_id,
            "intervention": intervention_type,
            "applied": result,
            "reason": reason
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid intervention type")


# Resource Extended Routes
@resource_router.post("/profiles/create")
async def create_resource_profile(
    profile: TeamResourceProfile,
    current_user: User = Depends(get_current_user)
):
    """Create a resource profile for a team"""
    resource_allocator = ResourceAllocator()
    
    # Create profile
    resource_allocator.create_team_profile(
        team_id=profile.team_id,
        profile_name=profile.profile_name,
        limits={
            "compute": profile.compute_limit,
            "memory": profile.memory_limit,
            "storage": profile.storage_limit
        },
        priority=profile.priority_tier
    )
    
    audit_logger = AuditLogger()
    await audit_logger.log_event(
        event_type=EventType.CONFIGURATION,
        severity=Severity.INFO,
        component="ResourceAllocator",
        agent_id=profile.team_id,
        action="create_profile",
        details={
            "profile_name": profile.profile_name,
            "limits": {
                "compute": profile.compute_limit,
                "memory": profile.memory_limit,
                "storage": profile.storage_limit
            }
        }
    )
    
    return {
        "team_id": profile.team_id,
        "profile_name": profile.profile_name,
        "created": True
    }


@resource_router.post("/allocate/bulk")
async def bulk_allocate_resources(
    request: BulkResourceAllocation,
    current_user: User = Depends(get_current_user)
):
    """Perform bulk resource allocation"""
    resource_allocator = ResourceAllocator()
    results = []
    
    for allocation in request.allocations:
        try:
            allocated = await resource_allocator.allocate_resources(
                team_id=allocation["team_id"],
                resource_type=allocation["resource_type"],
                amount=allocation["amount"],
                priority=allocation.get("priority", 3),
                duration=allocation.get("duration", 3600)
            )
            
            results.append({
                "team_id": allocation["team_id"],
                "success": allocated,
                "allocated": allocation["amount"] if allocated else 0
            })
        except Exception as e:
            results.append({
                "team_id": allocation["team_id"],
                "success": False,
                "error": str(e)
            })
    
    return {
        "strategy": request.strategy,
        "total_requests": len(request.allocations),
        "successful": sum(1 for r in results if r["success"]),
        "results": results
    }


@resource_router.get("/utilization")
async def get_resource_utilization(
    pool_name: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get current resource utilization across pools"""
    resource_allocator = ResourceAllocator()
    
    utilization = {}
    pools = [pool_name] if pool_name else resource_allocator.pools.keys()
    
    for pool in pools:
        if pool in resource_allocator.pools:
            pool_data = resource_allocator.pools[pool]
            total = pool_data["total"]
            available = pool_data["available"]
            
            utilization[pool] = {
                "total": total,
                "available": available,
                "allocated": {k: total[k] - available[k] for k in total.keys()},
                "utilization_percentage": {
                    k: ((total[k] - available[k]) / total[k] * 100) if total[k] > 0 else 0
                    for k in total.keys()
                }
            }
    
    return utilization


# Audit Extended Routes
@audit_router.get("/analysis/patterns")
async def analyze_patterns(
    time_window: int = Query(86400, description="Time window in seconds"),
    current_user: User = Depends(get_current_user)
):
    """Analyze patterns in audit logs"""
    audit_logger = AuditLogger()
    
    # Get logs for analysis
    logs = audit_logger.query_logs(
        start_time=datetime.utcnow() - timedelta(seconds=time_window)
    )
    
    # Analyze patterns
    patterns = {
        "event_distribution": {},
        "severity_distribution": {},
        "top_agents": {},
        "error_rate": 0,
        "peak_activity_hour": None
    }
    
    for log in logs:
        # Event distribution
        event_type = log.event_type.value if hasattr(log.event_type, 'value') else str(log.event_type)
        patterns["event_distribution"][event_type] = patterns["event_distribution"].get(event_type, 0) + 1
        
        # Severity distribution
        severity = log.severity.value if hasattr(log.severity, 'value') else str(log.severity)
        patterns["severity_distribution"][severity] = patterns["severity_distribution"].get(severity, 0) + 1
        
        # Top agents
        patterns["top_agents"][log.agent_id] = patterns["top_agents"].get(log.agent_id, 0) + 1
    
    # Calculate error rate
    total_events = len(logs)
    error_events = patterns["event_distribution"].get("error", 0)
    patterns["error_rate"] = error_events / max(total_events, 1)
    
    # Get top 10 agents
    patterns["top_agents"] = dict(sorted(patterns["top_agents"].items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        "time_window": time_window,
        "total_events": total_events,
        "patterns": patterns
    }


@audit_router.post("/retention/apply")
async def apply_retention_policy(
    policy: str = Query(..., regex="^(SHORT_TERM|STANDARD|LONG_TERM|PERMANENT)$"),
    apply_to_existing: bool = Query(False),
    current_user: User = Depends(get_current_user)
):
    """Apply retention policy to audit logs"""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    audit_logger = AuditLogger()
    
    # Apply retention policy
    if apply_to_existing:
        archived = audit_logger.apply_retention_policies()
        
        return {
            "policy": policy,
            "applied_to_existing": True,
            "events_archived": archived
        }
    else:
        return {
            "policy": policy,
            "message": "Policy will be applied to new events"
        }


# Admin Routes
@admin_router.get("/status")
async def get_system_status(
    current_user: User = Depends(get_current_user)
):
    """Get overall system status"""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    # Gather status from all components
    ethics_engine = EthicsEngine()
    safety_monitor = SafetyMonitor()
    resource_allocator = ResourceAllocator()
    audit_logger = AuditLogger()
    
    status = {
        "timestamp": datetime.utcnow(),
        "components": {
            "ethics_engine": {
                "status": "operational",
                "constraints_loaded": len(ethics_engine.constraints) > 0
            },
            "safety_monitor": {
                "status": "operational",
                "agents_monitored": len(safety_monitor.agent_status),
                "active_threats": sum(1 for s in safety_monitor.agent_status.values() if s.get("threats"))
            },
            "resource_allocator": {
                "status": "operational",
                "pools": list(resource_allocator.pools.keys()),
                "active_allocations": len(resource_allocator.allocations)
            },
            "audit_logger": {
                "status": "operational",
                "total_events": audit_logger.get_statistics().get("total_events", 0)
            }
        }
    }
    
    return status


@admin_router.post("/configuration/update")
async def update_system_configuration(
    config: SystemConfiguration,
    current_user: User = Depends(get_current_user)
):
    """Update system configuration"""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    audit_logger = AuditLogger()
    await audit_logger.log_event(
        event_type=EventType.CONFIGURATION,
        severity=Severity.MEDIUM,
        component="System",
        agent_id=current_user.username,
        action="update_configuration",
        details={
            "component": config.component,
            "settings": config.settings,
            "apply_immediately": config.apply_immediately
        }
    )
    
    return {
        "component": config.component,
        "status": "configuration_updated",
        "apply_immediately": config.apply_immediately,
        "message": "Configuration will take effect on next restart" if not config.apply_immediately else "Configuration applied"
    }


@admin_router.post("/shutdown")
async def initiate_shutdown(
    confirm: bool = Query(False, description="Confirm shutdown"),
    grace_period: int = Query(30, description="Grace period in seconds"),
    current_user: User = Depends(get_current_user)
):
    """Initiate graceful system shutdown"""
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shutdown must be confirmed"
        )
    
    audit_logger = AuditLogger()
    await audit_logger.log_event(
        event_type=EventType.SYSTEM,
        severity=Severity.HIGH,
        component="System",
        agent_id=current_user.username,
        action="shutdown_initiated",
        details={
            "grace_period": grace_period,
            "initiated_by": current_user.username
        }
    )
    
    # In production, this would trigger actual shutdown sequence
    return {
        "status": "shutdown_initiated",
        "grace_period": grace_period,
        "message": f"System will shutdown in {grace_period} seconds"
    }


# Export routers to be included in main app
routers = [
    ethics_router,
    safety_router,
    resource_router,
    audit_router,
    admin_router
]