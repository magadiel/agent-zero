"""
Control Layer API - Main application entry point
Provides REST API endpoints for ethics validation, safety monitoring,
resource allocation, and audit logging.
"""

import os
import sys
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Security, status, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from jose import JWTError, jwt
import uvicorn

# Add control module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import control components
from ethics_engine import EthicsEngine, DecisionType
from safety_monitor import SafetyMonitor
from resource_allocator import ResourceAllocator
from audit_logger import AuditLogger, AuditEntry, EventType, EventCategory, Severity

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize components
ethics_engine = None
safety_monitor = None
resource_allocator = None
audit_logger = None

# Security
security = HTTPBearer()


# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: Optional[bool] = False


class UserInDB(User):
    hashed_password: str


class AgentDecision(BaseModel):
    """Model for agent decision validation request"""
    agent_id: str = Field(..., description="ID of the agent making the decision")
    decision_type: str = Field(..., description="Type of decision being made")
    decision_data: Dict[str, Any] = Field(..., description="Decision details and parameters")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")
    
    @validator('decision_type')
    def validate_decision_type(cls, v):
        valid_types = [dt.value for dt in DecisionType]
        if v not in valid_types:
            raise ValueError(f"Invalid decision type. Must be one of: {valid_types}")
        return v


class ResourceRequest(BaseModel):
    """Model for resource allocation request"""
    team_id: str = Field(..., description="ID of the team requesting resources")
    resource_type: str = Field(..., description="Type of resource (compute, memory, storage)")
    amount: float = Field(..., gt=0, description="Amount of resource requested")
    priority: int = Field(default=3, ge=1, le=5, description="Priority level (1-5)")
    duration: Optional[int] = Field(default=3600, description="Duration in seconds")


class SafetyCheck(BaseModel):
    """Model for safety check request"""
    agent_id: str = Field(..., description="ID of the agent to monitor")
    metrics: Dict[str, float] = Field(..., description="Current metrics to check")
    check_type: str = Field(default="standard", description="Type of check (standard, deep, emergency)")


class AuditQuery(BaseModel):
    """Model for audit log query"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    agent_id: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    limit: int = Field(default=100, le=1000)


class HealthStatus(BaseModel):
    """Model for health check response"""
    status: str
    timestamp: datetime
    components: Dict[str, str]
    version: str = "1.0.0"


# Authentication functions
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "disabled": False,
    }
}


def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Generate password hash"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def get_user(username: str):
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)


def authenticate_user(username: str, password: str):
    """Authenticate a user"""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources"""
    global ethics_engine, safety_monitor, resource_allocator, audit_logger
    
    # Startup
    print("Initializing Control Layer API...")
    
    # Initialize components
    ethics_engine = EthicsEngine()
    safety_monitor = SafetyMonitor()
    resource_allocator = ResourceAllocator()
    audit_logger = AuditLogger()
    
    # Start monitoring
    asyncio.create_task(safety_monitor.start_monitoring())
    
    # Log startup
    await audit_logger.log_event(
        event_type=EventType.SYSTEM,
        severity=Severity.INFO,
        component="API",
        agent_id="system",
        action="startup",
        details={"message": "Control Layer API started"}
    )
    
    print("Control Layer API initialized successfully")
    
    yield
    
    # Shutdown
    print("Shutting down Control Layer API...")
    
    # Stop monitoring
    safety_monitor.stop_monitoring()
    
    # Log shutdown
    await audit_logger.log_event(
        event_type=EventType.SYSTEM,
        severity=Severity.INFO,
        component="API",
        agent_id="system",
        action="shutdown",
        details={"message": "Control Layer API stopped"}
    )
    
    # Close connections
    audit_logger.close()
    
    print("Control Layer API shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="Agile AI Control Layer API",
    description="Control layer API for ethics validation, safety monitoring, and resource management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Agile AI Control Layer API",
        "version": "1.0.0",
        "documentation": "/docs"
    }


@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    components_status = {}
    
    # Check each component
    try:
        if ethics_engine:
            components_status["ethics_engine"] = "healthy"
    except:
        components_status["ethics_engine"] = "unhealthy"
        
    try:
        if safety_monitor:
            components_status["safety_monitor"] = "healthy"
    except:
        components_status["safety_monitor"] = "unhealthy"
        
    try:
        if resource_allocator:
            components_status["resource_allocator"] = "healthy"
    except:
        components_status["resource_allocator"] = "unhealthy"
        
    try:
        if audit_logger:
            components_status["audit_logger"] = "healthy"
    except:
        components_status["audit_logger"] = "unhealthy"
    
    overall_status = "healthy" if all(s == "healthy" for s in components_status.values()) else "degraded"
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        components=components_status
    )


@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(username: str = Body(...), password: str = Body(...)):
    """Login endpoint to get access token"""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/ethics/validate", tags=["Ethics"])
async def validate_decision(
    decision: AgentDecision,
    current_user: User = Depends(get_current_user)
):
    """Validate an agent's decision against ethical constraints"""
    try:
        # Convert string to DecisionType enum
        decision_type = DecisionType(decision.decision_type)
        
        # Validate decision
        result = await ethics_engine.validate_decision(
            agent_id=decision.agent_id,
            decision_type=decision_type,
            decision_data=decision.decision_data,
            context=decision.context
        )
        
        # Log the validation
        await audit_logger.log_event(
            event_type=EventType.ETHICS,
            severity=Severity.INFO if result["approved"] else Severity.MEDIUM,
            component="EthicsEngine",
            agent_id=decision.agent_id,
            action="validate_decision",
            details={
                "decision_type": decision.decision_type,
                "approved": result["approved"],
                "risk_score": result.get("risk_score", 0)
            }
        )
        
        return result
        
    except Exception as e:
        await audit_logger.log_event(
            event_type=EventType.ERROR,
            severity=Severity.HIGH,
            component="API",
            agent_id=decision.agent_id,
            action="validate_decision_error",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/safety/check", tags=["Safety"])
async def safety_check(
    check: SafetyCheck,
    current_user: User = Depends(get_current_user)
):
    """Perform safety check on an agent"""
    try:
        # Monitor agent
        await safety_monitor.monitor_agent(
            agent_id=check.agent_id,
            metrics=check.metrics
        )
        
        # Check for violations
        violations = safety_monitor.check_violations(check.agent_id)
        
        # Get agent status
        status = safety_monitor.get_agent_status(check.agent_id)
        
        result = {
            "agent_id": check.agent_id,
            "status": status,
            "violations": violations,
            "timestamp": datetime.utcnow()
        }
        
        # Log if violations found
        if violations:
            await audit_logger.log_event(
                event_type=EventType.SAFETY,
                severity=Severity.MEDIUM,
                component="SafetyMonitor",
                agent_id=check.agent_id,
                action="safety_violation",
                details={"violations": violations}
            )
        
        return result
        
    except Exception as e:
        await audit_logger.log_event(
            event_type=EventType.ERROR,
            severity=Severity.HIGH,
            component="API",
            agent_id=check.agent_id,
            action="safety_check_error",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/safety/emergency-stop/{agent_id}", tags=["Safety"])
async def emergency_stop(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """Trigger emergency stop for an agent"""
    try:
        result = await safety_monitor.emergency_stop(agent_id)
        
        await audit_logger.log_event(
            event_type=EventType.SAFETY,
            severity=Severity.HIGH,
            component="SafetyMonitor",
            agent_id=agent_id,
            action="emergency_stop",
            details={"success": result}
        )
        
        return {"agent_id": agent_id, "stopped": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/resources/allocate", tags=["Resources"])
async def allocate_resources(
    request: ResourceRequest,
    current_user: User = Depends(get_current_user)
):
    """Allocate resources to a team"""
    try:
        # Try to allocate resources
        allocated = await resource_allocator.allocate_resources(
            team_id=request.team_id,
            resource_type=request.resource_type,
            amount=request.amount,
            priority=request.priority,
            duration=request.duration
        )
        
        if allocated:
            await audit_logger.log_event(
                event_type=EventType.RESOURCE,
                severity=Severity.INFO,
                component="ResourceAllocator",
                agent_id=request.team_id,
                action="allocate_resources",
                details={
                    "resource_type": request.resource_type,
                    "amount": request.amount,
                    "allocated": allocated
                }
            )
            
            return {
                "team_id": request.team_id,
                "allocated": allocated,
                "resource_type": request.resource_type,
                "amount": request.amount
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Insufficient resources available"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        await audit_logger.log_event(
            event_type=EventType.ERROR,
            severity=Severity.HIGH,
            component="API",
            agent_id=request.team_id,
            action="allocate_resources_error",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/resources/release/{team_id}", tags=["Resources"])
async def release_resources(
    team_id: str,
    current_user: User = Depends(get_current_user)
):
    """Release resources allocated to a team"""
    try:
        released = await resource_allocator.release_resources(team_id)
        
        await audit_logger.log_event(
            event_type=EventType.RESOURCE,
            severity=Severity.INFO,
            component="ResourceAllocator",
            agent_id=team_id,
            action="release_resources",
            details={"released": released}
        )
        
        return {"team_id": team_id, "released": released}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resources/usage/{team_id}", tags=["Resources"])
async def get_resource_usage(
    team_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get resource usage for a team"""
    try:
        usage = resource_allocator.get_team_usage(team_id)
        if usage:
            return usage
        else:
            raise HTTPException(status_code=404, detail="Team not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resources/available", tags=["Resources"])
async def get_available_resources(
    current_user: User = Depends(get_current_user)
):
    """Get available resources in all pools"""
    try:
        available = resource_allocator.get_available_resources()
        return available
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/logs", tags=["Audit"])
async def query_audit_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    agent_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user)
):
    """Query audit logs"""
    try:
        # Convert strings to enums if provided
        event_type_enum = EventType(event_type) if event_type else None
        severity_enum = Severity(severity) if severity else None
        
        # Query logs
        logs = audit_logger.query_logs(
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            event_type=event_type_enum,
            severity=severity_enum,
            limit=limit
        )
        
        # Convert to dict for JSON response
        return {
            "count": len(logs),
            "logs": [log.__dict__ for log in logs]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/stats", tags=["Audit"])
async def get_audit_stats(
    current_user: User = Depends(get_current_user)
):
    """Get audit log statistics"""
    try:
        stats = audit_logger.get_statistics()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/export", tags=["Audit"])
async def export_audit_logs(
    format: str = Query("json", regex="^(json|csv)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Export audit logs"""
    try:
        filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
        filepath = audit_logger.export_logs(
            filename=filename,
            format=format,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "filename": filename,
            "filepath": filepath,
            "format": format
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    # Log the error
    if audit_logger:
        await audit_logger.log_event(
            event_type=EventType.ERROR,
            severity=Severity.HIGH,
            component="API",
            agent_id="system",
            action="unhandled_exception",
            details={"error": str(exc), "path": request.url.path}
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )