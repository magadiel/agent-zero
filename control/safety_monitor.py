"""
Safety Monitor Module
Provides real-time monitoring and safety enforcement for AI agents.
"""

import asyncio
import logging
import json
import yaml
import time

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum
from pathlib import Path
from collections import deque, defaultdict
import os
import hashlib
import threading

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SafetyLevel(Enum):
    """Safety levels for system operation."""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ThreatType(Enum):
    """Types of safety threats."""
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    RUNAWAY_AGENT = "runaway_agent"
    CASCADING_FAILURE = "cascading_failure"
    THRESHOLD_BREACH = "threshold_breach"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_CORRUPTION = "data_corruption"
    INFINITE_LOOP = "infinite_loop"


class InterventionType(Enum):
    """Types of safety interventions."""
    THROTTLE = "throttle"
    PAUSE = "pause"
    TERMINATE = "terminate"
    RESTART = "restart"
    ISOLATE = "isolate"
    RESOURCE_LIMIT = "resource_limit"
    EMERGENCY_STOP = "emergency_stop"


class SafetyMetrics:
    """Container for safety-related metrics."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize safety metrics tracker.
        
        Args:
            window_size: Size of sliding window for metrics
        """
        self.window_size = window_size
        self.cpu_usage = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.response_times = deque(maxlen=window_size)
        self.error_count = 0
        self.warning_count = 0
        self.intervention_count = 0
        self.last_update = time.time()
    
    def update(self, cpu: float, memory: float, response_time: float = None):
        """Update metrics with new values."""
        self.cpu_usage.append(cpu)
        self.memory_usage.append(memory)
        if response_time is not None:
            self.response_times.append(response_time)
        self.last_update = time.time()
    
    def get_averages(self) -> Dict[str, float]:
        """Get average values for all metrics."""
        return {
            "avg_cpu": sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
            "avg_memory": sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "error_rate": self.error_count / self.window_size if self.window_size > 0 else 0
        }
    
    def get_trends(self) -> Dict[str, str]:
        """Analyze trends in metrics."""
        trends = {}
        
        # CPU trend
        if len(self.cpu_usage) >= 10:
            recent = list(self.cpu_usage)[-5:]
            older = list(self.cpu_usage)[-10:-5]
            if sum(recent) / 5 > sum(older) / 5 * 1.2:
                trends["cpu"] = "increasing"
            elif sum(recent) / 5 < sum(older) / 5 * 0.8:
                trends["cpu"] = "decreasing"
            else:
                trends["cpu"] = "stable"
        
        # Memory trend
        if len(self.memory_usage) >= 10:
            recent = list(self.memory_usage)[-5:]
            older = list(self.memory_usage)[-10:-5]
            if sum(recent) / 5 > sum(older) / 5 * 1.2:
                trends["memory"] = "increasing"
            elif sum(recent) / 5 < sum(older) / 5 * 0.8:
                trends["memory"] = "decreasing"
            else:
                trends["memory"] = "stable"
        
        return trends


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.successful_calls = 0
    
    def record_success(self):
        """Record a successful operation."""
        self.successful_calls += 1
        if self.state == "half_open" and self.successful_calls >= 3:
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful recovery")
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.successful_calls = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def can_proceed(self) -> bool:
        """Check if operations can proceed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        return self.state == "half_open"


class AgentMonitor:
    """Monitors individual agent behavior and resource usage."""
    
    def __init__(self, agent_id: str):
        """Initialize agent monitor."""
        self.agent_id = agent_id
        self.metrics = SafetyMetrics()
        self.circuit_breaker = CircuitBreaker()
        self.start_time = time.time()
        self.last_activity = time.time()
        self.action_count = 0
        self.violation_count = 0
        self.suspended = False
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()
        self.action_count += 1
    
    def get_runtime(self) -> float:
        """Get agent runtime in seconds."""
        return time.time() - self.start_time
    
    def get_idle_time(self) -> float:
        """Get time since last activity."""
        return time.time() - self.last_activity


class SafetyMonitor:
    """
    Real-time safety monitoring system for AI agents.
    Monitors resource usage, detects anomalies, and enforces safety thresholds.
    """
    
    def __init__(self, config_path: str = None, ethics_engine=None):
        """
        Initialize the Safety Monitor.
        
        Args:
            config_path: Path to safety thresholds configuration
            ethics_engine: Optional reference to Ethics Engine for coordination
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__),
            "config",
            "safety_thresholds.yaml"
        )
        self.thresholds = self._load_thresholds()
        self.ethics_engine = ethics_engine
        
        # Monitoring state
        self.agent_monitors: Dict[str, AgentMonitor] = {}
        self.global_metrics = SafetyMetrics(window_size=1000)
        self.safety_level = SafetyLevel.NORMAL
        self.active_threats: Set[ThreatType] = set()
        self.intervention_history = deque(maxlen=100)
        
        # Kill switches
        self.emergency_stop_triggered = False
        self.kill_switch_armed = True
        self.shutdown_in_progress = False
        
        # Monitoring thread
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_lock = threading.Lock()
        
        # Audit logger
        self.audit_logger = self._setup_audit_logger()
        
        logger.info(f"Safety Monitor initialized with config: {self.config_path}")
    
    def _load_thresholds(self) -> Dict[str, Any]:
        """Load safety thresholds from configuration."""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found at {self.config_path}, using defaults")
                return self._get_default_thresholds()
            
            with open(self.config_path, 'r') as f:
                thresholds = yaml.safe_load(f)
                logger.info(f"Loaded safety thresholds from {self.config_path}")
                return thresholds
        except Exception as e:
            logger.error(f"Error loading thresholds: {e}")
            return self._get_default_thresholds()
    
    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Return default safety thresholds."""
        return {
            "resource_limits": {
                "cpu_percent": {
                    "warning": 70,
                    "critical": 85,
                    "emergency": 95
                },
                "memory_percent": {
                    "warning": 70,
                    "critical": 85,
                    "emergency": 95
                },
                "disk_io_mbps": {
                    "warning": 80,
                    "critical": 100,
                    "emergency": 120
                }
            },
            "response_times": {
                "warning_ms": 1000,
                "critical_ms": 5000,
                "timeout_ms": 10000
            },
            "error_rates": {
                "warning_percent": 5,
                "critical_percent": 10,
                "emergency_percent": 25
            },
            "agent_limits": {
                "max_runtime_seconds": 3600,
                "max_idle_seconds": 300,
                "max_actions_per_minute": 100,
                "max_concurrent_agents": 50
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout_seconds": 60,
                "half_open_trials": 3
            },
            "kill_switches": {
                "emergency_stop": {
                    "enabled": True,
                    "auto_trigger_on_emergency": True,
                    "cooldown_seconds": 300
                },
                "graceful_shutdown": {
                    "enabled": True,
                    "max_duration_seconds": 60,
                    "save_state": True
                }
            }
        }
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Set up audit logger for safety events."""
        audit_logger = logging.getLogger('safety_audit')
        audit_logger.setLevel(logging.INFO)
        
        # Create audit log directory
        audit_dir = os.path.join(os.path.dirname(__file__), "audit_logs")
        os.makedirs(audit_dir, exist_ok=True)
        
        # Add file handler
        audit_file = os.path.join(
            audit_dir,
            f"safety_audit_{datetime.now().strftime('%Y%m%d')}.log"
        )
        handler = logging.FileHandler(audit_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        audit_logger.addHandler(handler)
        
        return audit_logger
    
    async def start_monitoring(self):
        """Start the monitoring loop."""
        if self.monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Safety monitoring started")
    
    def _monitoring_loop(self):
        """Main monitoring loop (runs in separate thread)."""
        while self.monitoring:
            try:
                # Collect system metrics
                if PSUTIL_AVAILABLE:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory_percent = psutil.virtual_memory().percent
                else:
                    # Fallback: use simulated values for testing
                    import random
                    cpu_percent = 30 + random.random() * 20
                    memory_percent = 40 + random.random() * 20
                
                # Update global metrics
                self.global_metrics.update(cpu_percent, memory_percent)
                
                # Check thresholds
                asyncio.run(self._check_thresholds())
                
                # Check agent health
                asyncio.run(self._check_agent_health())
                
                # Update safety level
                asyncio.run(self._update_safety_level())
                
                # Sleep before next iteration
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Safety monitoring stopped")
    
    async def register_agent(self, agent_id: str) -> bool:
        """
        Register an agent for monitoring.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Success status
        """
        with self.monitor_lock:
            if len(self.agent_monitors) >= self.thresholds["agent_limits"]["max_concurrent_agents"]:
                logger.error(f"Cannot register agent {agent_id}: max concurrent agents reached")
                return False
            
            if agent_id not in self.agent_monitors:
                self.agent_monitors[agent_id] = AgentMonitor(agent_id)
                logger.info(f"Agent {agent_id} registered for monitoring")
                
                # Log to audit
                self.audit_logger.info(json.dumps({
                    "event": "agent_registered",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
                return True
            
            logger.warning(f"Agent {agent_id} already registered")
            return False
    
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent from monitoring."""
        with self.monitor_lock:
            if agent_id in self.agent_monitors:
                del self.agent_monitors[agent_id]
                logger.info(f"Agent {agent_id} unregistered")
                
                # Log to audit
                self.audit_logger.info(json.dumps({
                    "event": "agent_unregistered",
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
    
    async def report_agent_activity(self, agent_id: str, 
                                   cpu: float = None, 
                                   memory: float = None,
                                   response_time: float = None,
                                   error: bool = False):
        """
        Report agent activity and metrics.
        
        Args:
            agent_id: Agent identifier
            cpu: CPU usage percentage
            memory: Memory usage percentage
            response_time: Response time in milliseconds
            error: Whether an error occurred
        """
        with self.monitor_lock:
            if agent_id not in self.agent_monitors:
                await self.register_agent(agent_id)
            
            monitor = self.agent_monitors[agent_id]
            monitor.update_activity()
            
            # Update metrics if provided
            if cpu is not None or memory is not None:
                monitor.metrics.update(
                    cpu or 0,
                    memory or 0,
                    response_time
                )
            
            # Record errors
            if error:
                monitor.metrics.error_count += 1
                monitor.circuit_breaker.record_failure()
            else:
                monitor.circuit_breaker.record_success()
            
            # Check if intervention needed
            await self._check_agent_intervention(agent_id, monitor)
    
    async def _check_thresholds(self):
        """Check system-wide thresholds."""
        metrics = self.global_metrics.get_averages()
        limits = self.thresholds["resource_limits"]
        
        threats = set()
        
        # Check CPU thresholds
        if metrics["avg_cpu"] > limits["cpu_percent"]["emergency"]:
            threats.add(ThreatType.RESOURCE_EXHAUSTION)
            await self._trigger_intervention(
                InterventionType.EMERGENCY_STOP,
                f"CPU usage critical: {metrics['avg_cpu']:.1f}%"
            )
        elif metrics["avg_cpu"] > limits["cpu_percent"]["critical"]:
            threats.add(ThreatType.THRESHOLD_BREACH)
            await self._trigger_intervention(
                InterventionType.THROTTLE,
                f"CPU usage high: {metrics['avg_cpu']:.1f}%"
            )
        
        # Check memory thresholds
        if metrics["avg_memory"] > limits["memory_percent"]["emergency"]:
            threats.add(ThreatType.RESOURCE_EXHAUSTION)
            await self._trigger_intervention(
                InterventionType.EMERGENCY_STOP,
                f"Memory usage critical: {metrics['avg_memory']:.1f}%"
            )
        elif metrics["avg_memory"] > limits["memory_percent"]["critical"]:
            threats.add(ThreatType.THRESHOLD_BREACH)
            await self._trigger_intervention(
                InterventionType.RESOURCE_LIMIT,
                f"Memory usage high: {metrics['avg_memory']:.1f}%"
            )
        
        self.active_threats = threats
    
    async def _check_agent_health(self):
        """Check health of all monitored agents."""
        with self.monitor_lock:
            for agent_id, monitor in list(self.agent_monitors.items()):
                # Check runtime limits
                if monitor.get_runtime() > self.thresholds["agent_limits"]["max_runtime_seconds"]:
                    await self._trigger_agent_intervention(
                        agent_id,
                        InterventionType.TERMINATE,
                        "Agent exceeded maximum runtime"
                    )
                
                # Check idle time
                if monitor.get_idle_time() > self.thresholds["agent_limits"]["max_idle_seconds"]:
                    await self._trigger_agent_intervention(
                        agent_id,
                        InterventionType.TERMINATE,
                        "Agent idle timeout"
                    )
                
                # Check action rate
                if monitor.action_count > 0:
                    runtime_minutes = monitor.get_runtime() / 60
                    if runtime_minutes > 0:
                        actions_per_minute = monitor.action_count / runtime_minutes
                        if actions_per_minute > self.thresholds["agent_limits"]["max_actions_per_minute"]:
                            await self._trigger_agent_intervention(
                                agent_id,
                                InterventionType.THROTTLE,
                                f"Agent action rate too high: {actions_per_minute:.1f}/min"
                            )
    
    async def _check_agent_intervention(self, agent_id: str, monitor: AgentMonitor):
        """Check if agent-specific intervention is needed."""
        if monitor.suspended:
            return
        
        # Check circuit breaker
        if not monitor.circuit_breaker.can_proceed():
            await self._trigger_agent_intervention(
                agent_id,
                InterventionType.PAUSE,
                "Circuit breaker triggered"
            )
        
        # Check error rate
        metrics = monitor.metrics.get_averages()
        error_thresholds = self.thresholds["error_rates"]
        
        if metrics["error_rate"] * 100 > error_thresholds["emergency_percent"]:
            await self._trigger_agent_intervention(
                agent_id,
                InterventionType.TERMINATE,
                f"Error rate critical: {metrics['error_rate']*100:.1f}%"
            )
        elif metrics["error_rate"] * 100 > error_thresholds["critical_percent"]:
            await self._trigger_agent_intervention(
                agent_id,
                InterventionType.RESTART,
                f"Error rate high: {metrics['error_rate']*100:.1f}%"
            )
    
    async def _update_safety_level(self):
        """Update overall safety level based on current conditions."""
        previous_level = self.safety_level
        
        if self.emergency_stop_triggered:
            self.safety_level = SafetyLevel.EMERGENCY
        elif ThreatType.RESOURCE_EXHAUSTION in self.active_threats:
            self.safety_level = SafetyLevel.CRITICAL
        elif ThreatType.THRESHOLD_BREACH in self.active_threats:
            self.safety_level = SafetyLevel.WARNING
        elif ThreatType.ANOMALOUS_BEHAVIOR in self.active_threats:
            self.safety_level = SafetyLevel.CAUTION
        else:
            self.safety_level = SafetyLevel.NORMAL
        
        if self.safety_level != previous_level:
            logger.info(f"Safety level changed: {previous_level.value} -> {self.safety_level.value}")
            
            # Log to audit
            self.audit_logger.info(json.dumps({
                "event": "safety_level_change",
                "previous": previous_level.value,
                "current": self.safety_level.value,
                "threats": [t.value for t in self.active_threats],
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def _trigger_intervention(self, intervention_type: InterventionType, reason: str):
        """Trigger a system-wide intervention."""
        logger.warning(f"Triggering {intervention_type.value}: {reason}")
        
        # Record intervention
        self.intervention_history.append({
            "type": intervention_type.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log to audit
        self.audit_logger.warning(json.dumps({
            "event": "intervention_triggered",
            "type": intervention_type.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Execute intervention
        if intervention_type == InterventionType.EMERGENCY_STOP:
            await self.emergency_stop(reason)
        elif intervention_type == InterventionType.THROTTLE:
            await self.throttle_all_agents()
        elif intervention_type == InterventionType.RESOURCE_LIMIT:
            await self.enforce_resource_limits()
    
    async def _trigger_agent_intervention(self, agent_id: str, 
                                         intervention_type: InterventionType, 
                                         reason: str):
        """Trigger an agent-specific intervention."""
        logger.warning(f"Agent {agent_id} intervention: {intervention_type.value} - {reason}")
        
        # Log to audit
        self.audit_logger.warning(json.dumps({
            "event": "agent_intervention",
            "agent_id": agent_id,
            "type": intervention_type.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Execute intervention
        if intervention_type == InterventionType.TERMINATE:
            await self.terminate_agent(agent_id)
        elif intervention_type == InterventionType.PAUSE:
            await self.pause_agent(agent_id)
        elif intervention_type == InterventionType.RESTART:
            await self.restart_agent(agent_id)
        elif intervention_type == InterventionType.THROTTLE:
            await self.throttle_agent(agent_id)
    
    async def emergency_stop(self, reason: str):
        """
        Trigger emergency stop of all agent activities.
        
        Args:
            reason: Reason for emergency stop
        """
        if not self.kill_switch_armed:
            logger.error("Emergency stop requested but kill switch is disarmed")
            return
        
        logger.critical(f"EMERGENCY STOP INITIATED: {reason}")
        self.emergency_stop_triggered = True
        self.shutdown_in_progress = True
        
        # Log to audit
        self.audit_logger.critical(json.dumps({
            "event": "emergency_stop",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Notify ethics engine if available
        if self.ethics_engine:
            await self.ethics_engine.emergency_shutdown(f"Safety Monitor: {reason}")
        
        # Terminate all agents
        for agent_id in list(self.agent_monitors.keys()):
            await self.terminate_agent(agent_id, force=True)
        
        # Stop monitoring
        await self.stop_monitoring()
        
        logger.critical("Emergency stop completed")
    
    async def graceful_shutdown(self, timeout_seconds: int = 60):
        """
        Perform graceful shutdown of all agents.
        
        Args:
            timeout_seconds: Maximum time for shutdown
        """
        logger.info("Initiating graceful shutdown")
        self.shutdown_in_progress = True
        
        start_time = time.time()
        
        # Phase 1: Stop accepting new agents
        self.kill_switch_armed = False
        
        # Phase 2: Pause all agents
        for agent_id in list(self.agent_monitors.keys()):
            await self.pause_agent(agent_id)
        
        # Phase 3: Save state if configured
        if self.thresholds["kill_switches"]["graceful_shutdown"]["save_state"]:
            await self._save_system_state()
        
        # Phase 4: Terminate agents
        while self.agent_monitors and time.time() - start_time < timeout_seconds:
            for agent_id in list(self.agent_monitors.keys()):
                await self.terminate_agent(agent_id)
            await asyncio.sleep(1)
        
        # Phase 5: Force terminate remaining
        if self.agent_monitors:
            logger.warning("Forcing termination of remaining agents")
            for agent_id in list(self.agent_monitors.keys()):
                await self.terminate_agent(agent_id, force=True)
        
        # Stop monitoring
        await self.stop_monitoring()
        
        logger.info("Graceful shutdown completed")
    
    async def terminate_agent(self, agent_id: str, force: bool = False):
        """Terminate an agent."""
        with self.monitor_lock:
            if agent_id in self.agent_monitors:
                logger.info(f"Terminating agent {agent_id} (force={force})")
                
                # In real implementation, would send termination signal to agent
                # For now, just remove from monitoring
                del self.agent_monitors[agent_id]
    
    async def pause_agent(self, agent_id: str):
        """Pause an agent's operations."""
        with self.monitor_lock:
            if agent_id in self.agent_monitors:
                self.agent_monitors[agent_id].suspended = True
                logger.info(f"Agent {agent_id} paused")
    
    async def resume_agent(self, agent_id: str):
        """Resume an agent's operations."""
        with self.monitor_lock:
            if agent_id in self.agent_monitors:
                self.agent_monitors[agent_id].suspended = False
                logger.info(f"Agent {agent_id} resumed")
    
    async def restart_agent(self, agent_id: str):
        """Restart an agent."""
        logger.info(f"Restarting agent {agent_id}")
        await self.terminate_agent(agent_id)
        # In real implementation, would trigger agent restart
        await self.register_agent(agent_id)
    
    async def throttle_agent(self, agent_id: str):
        """Throttle an agent's resource usage."""
        logger.info(f"Throttling agent {agent_id}")
        # In real implementation, would apply resource limits
    
    async def throttle_all_agents(self):
        """Throttle all agents."""
        for agent_id in self.agent_monitors:
            await self.throttle_agent(agent_id)
    
    async def enforce_resource_limits(self):
        """Enforce resource limits on all agents."""
        logger.info("Enforcing resource limits")
        # In real implementation, would apply system-wide limits
    
    async def _save_system_state(self):
        """Save current system state for recovery."""
        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "safety_level": self.safety_level.value,
            "active_threats": [t.value for t in self.active_threats],
            "agents": {
                agent_id: {
                    "runtime": monitor.get_runtime(),
                    "action_count": monitor.action_count,
                    "suspended": monitor.suspended
                }
                for agent_id, monitor in self.agent_monitors.items()
            }
        }
        
        # Save to file
        state_file = os.path.join(
            os.path.dirname(__file__),
            "state",
            f"safety_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"System state saved to {state_file}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current safety monitor status."""
        return {
            "monitoring": self.monitoring,
            "safety_level": self.safety_level.value,
            "active_threats": [t.value for t in self.active_threats],
            "emergency_stop_triggered": self.emergency_stop_triggered,
            "kill_switch_armed": self.kill_switch_armed,
            "agent_count": len(self.agent_monitors),
            "global_metrics": self.global_metrics.get_averages(),
            "intervention_count": len(self.intervention_history),
            "recent_interventions": list(self.intervention_history)[-5:] if self.intervention_history else []
        }
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        with self.monitor_lock:
            if agent_id not in self.agent_monitors:
                return None
            
            monitor = self.agent_monitors[agent_id]
            return {
                "agent_id": agent_id,
                "runtime": monitor.get_runtime(),
                "idle_time": monitor.get_idle_time(),
                "action_count": monitor.action_count,
                "violation_count": monitor.violation_count,
                "suspended": monitor.suspended,
                "circuit_breaker_state": monitor.circuit_breaker.state,
                "metrics": monitor.metrics.get_averages(),
                "trends": monitor.metrics.get_trends()
            }
    
    async def arm_kill_switch(self):
        """Arm the emergency kill switch."""
        self.kill_switch_armed = True
        logger.info("Kill switch armed")
    
    async def disarm_kill_switch(self):
        """Disarm the emergency kill switch."""
        self.kill_switch_armed = False
        logger.warning("Kill switch disarmed")
    
    async def reset_emergency_stop(self):
        """Reset emergency stop flag after cooldown."""
        if self.emergency_stop_triggered:
            cooldown = self.thresholds["kill_switches"]["emergency_stop"]["cooldown_seconds"]
            logger.info(f"Emergency stop will reset after {cooldown} second cooldown")
            await asyncio.sleep(cooldown)
            self.emergency_stop_triggered = False
            self.shutdown_in_progress = False
            logger.info("Emergency stop reset")


# Example usage and testing
async def test_safety_monitor():
    """Test the Safety Monitor with simulated scenarios."""
    
    # Initialize monitor
    monitor = SafetyMonitor()
    
    # Start monitoring
    await monitor.start_monitoring()
    
    # Register some agents
    await monitor.register_agent("agent-001")
    await monitor.register_agent("agent-002")
    await monitor.register_agent("agent-003")
    
    # Simulate normal activity
    for i in range(5):
        await monitor.report_agent_activity(
            "agent-001",
            cpu=30 + i * 5,
            memory=40 + i * 3,
            response_time=100 + i * 50
        )
        await asyncio.sleep(0.5)
    
    # Simulate high CPU usage
    for i in range(3):
        await monitor.report_agent_activity(
            "agent-002",
            cpu=80 + i * 5,
            memory=60,
            response_time=500
        )
        await asyncio.sleep(0.5)
    
    # Simulate errors
    for i in range(5):
        await monitor.report_agent_activity(
            "agent-003",
            cpu=50,
            memory=50,
            error=True
        )
        await asyncio.sleep(0.2)
    
    # Get status
    status = await monitor.get_status()
    print(f"System Status: {json.dumps(status, indent=2)}")
    
    # Get agent statuses
    for agent_id in ["agent-001", "agent-002", "agent-003"]:
        agent_status = await monitor.get_agent_status(agent_id)
        if agent_status:
            print(f"\nAgent {agent_id} Status:")
            print(json.dumps(agent_status, indent=2))
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Graceful shutdown
    await monitor.graceful_shutdown()
    
    print("\nTest completed")


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_safety_monitor())