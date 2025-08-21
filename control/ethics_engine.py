"""
Ethics Engine Core Module
Provides ethical validation and decision-making framework for AI agents.
"""

import asyncio
import logging
import json
import hashlib
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
import os

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class EthicalViolationType(Enum):
    """Types of ethical violations that can occur."""
    HARM_PREVENTION = "harm_prevention"
    PRIVACY_VIOLATION = "privacy_violation"
    FAIRNESS_BREACH = "fairness_breach"
    TRANSPARENCY_ISSUE = "transparency_issue"
    RESOURCE_ABUSE = "resource_abuse"
    MANIPULATION = "manipulation"
    MISINFORMATION = "misinformation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class DecisionType(Enum):
    """Types of decisions that require ethical validation."""
    DATA_ACCESS = "data_access"
    RESOURCE_ALLOCATION = "resource_allocation"
    USER_INTERACTION = "user_interaction"
    AGENT_CREATION = "agent_creation"
    TASK_EXECUTION = "task_execution"
    SYSTEM_MODIFICATION = "system_modification"
    EXTERNAL_COMMUNICATION = "external_communication"
    LEARNING_UPDATE = "learning_update"


class ValidationResult:
    """Represents the result of an ethical validation."""
    
    def __init__(self, approved: bool, reasoning: str, 
                 violations: List[EthicalViolationType] = None,
                 risk_score: float = 0.0,
                 recommendations: List[str] = None):
        self.approved = approved
        self.reasoning = reasoning
        self.violations = violations or []
        self.risk_score = risk_score
        self.recommendations = recommendations or []
        self.timestamp = datetime.utcnow()
        self.validation_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate a unique validation ID."""
        content = f"{self.timestamp}{self.approved}{self.reasoning}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "validation_id": self.validation_id,
            "approved": self.approved,
            "reasoning": self.reasoning,
            "violations": [v.value for v in self.violations],
            "risk_score": self.risk_score,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat()
        }


class AgentDecision:
    """Represents a decision made by an agent that requires validation."""
    
    def __init__(self, agent_id: str, decision_type: DecisionType, 
                 action: str, context: Dict[str, Any],
                 resources_required: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.decision_type = decision_type
        self.action = action
        self.context = context
        self.resources_required = resources_required or {}
        self.timestamp = datetime.utcnow()
        self.decision_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate a unique decision ID."""
        content = f"{self.agent_id}{self.decision_type.value}{self.action}{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "decision_type": self.decision_type.value,
            "action": self.action,
            "context": self.context,
            "resources_required": self.resources_required,
            "timestamp": self.timestamp.isoformat()
        }


class EthicsEngine:
    """
    Core ethics validation system for AI agent decisions.
    Ensures all agent actions comply with ethical constraints.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Ethics Engine with configuration.
        
        Args:
            config_path: Path to ethical constraints configuration file
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            "config", 
            "ethical_constraints.yaml"
        )
        self.constraints = self._load_constraints()
        self.validation_history = []
        self.violation_count = {}
        self.audit_logger = self._setup_audit_logger()
        
        logger.info(f"Ethics Engine initialized with config: {self.config_path}")
    
    def _load_constraints(self) -> Dict[str, Any]:
        """Load ethical constraints from configuration file."""
        try:
            # Check if config file exists
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found at {self.config_path}, using defaults")
                return self._get_default_constraints()
            
            with open(self.config_path, 'r') as f:
                constraints = yaml.safe_load(f)
                logger.info(f"Loaded {len(constraints)} constraint categories")
                return constraints
        except Exception as e:
            logger.error(f"Error loading constraints: {e}")
            return self._get_default_constraints()
    
    def _get_default_constraints(self) -> Dict[str, Any]:
        """Return default ethical constraints if config file is not available."""
        return {
            "harm_prevention": {
                "enabled": True,
                "priority": "critical",
                "rules": [
                    "prevent_physical_harm",
                    "prevent_psychological_harm",
                    "prevent_financial_harm",
                    "prevent_reputational_harm"
                ]
            },
            "privacy_protection": {
                "enabled": True,
                "priority": "high",
                "rules": [
                    "protect_personal_data",
                    "require_consent_for_data_use",
                    "minimize_data_collection",
                    "ensure_data_security"
                ]
            },
            "fairness": {
                "enabled": True,
                "priority": "high",
                "rules": [
                    "prevent_discrimination",
                    "ensure_equal_treatment",
                    "avoid_bias_amplification",
                    "promote_inclusivity"
                ]
            },
            "transparency": {
                "enabled": True,
                "priority": "medium",
                "rules": [
                    "explain_decisions",
                    "disclose_ai_nature",
                    "provide_audit_trail",
                    "enable_human_oversight"
                ]
            },
            "resource_limits": {
                "enabled": True,
                "priority": "medium",
                "max_cpu_percent": 80,
                "max_memory_mb": 4096,
                "max_api_calls_per_minute": 100,
                "max_agents_per_team": 10
            }
        }
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Set up a separate logger for audit trail."""
        audit_logger = logging.getLogger('ethics_audit')
        audit_logger.setLevel(logging.INFO)
        
        # Create audit log directory if it doesn't exist
        audit_dir = os.path.join(os.path.dirname(__file__), "audit_logs")
        os.makedirs(audit_dir, exist_ok=True)
        
        # Add file handler for audit logs
        audit_file = os.path.join(
            audit_dir, 
            f"ethics_audit_{datetime.now().strftime('%Y%m%d')}.log"
        )
        handler = logging.FileHandler(audit_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        audit_logger.addHandler(handler)
        
        return audit_logger
    
    async def validate_decision(self, decision: AgentDecision) -> ValidationResult:
        """
        Validate an agent's decision against ethical constraints.
        
        Args:
            decision: The decision to validate
            
        Returns:
            ValidationResult indicating approval status and reasoning
        """
        logger.info(f"Validating decision {decision.decision_id} from agent {decision.agent_id}")
        
        violations = []
        risk_score = 0.0
        recommendations = []
        
        # Check harm prevention
        harm_check = await self._check_harm_prevention(decision)
        if not harm_check[0]:
            violations.append(EthicalViolationType.HARM_PREVENTION)
            risk_score += harm_check[1]
            recommendations.extend(harm_check[2])
        
        # Check privacy protection
        privacy_check = await self._check_privacy_protection(decision)
        if not privacy_check[0]:
            violations.append(EthicalViolationType.PRIVACY_VIOLATION)
            risk_score += privacy_check[1]
            recommendations.extend(privacy_check[2])
        
        # Check fairness
        fairness_check = await self._check_fairness(decision)
        if not fairness_check[0]:
            violations.append(EthicalViolationType.FAIRNESS_BREACH)
            risk_score += fairness_check[1]
            recommendations.extend(fairness_check[2])
        
        # Check transparency
        transparency_check = await self._check_transparency(decision)
        if not transparency_check[0]:
            violations.append(EthicalViolationType.TRANSPARENCY_ISSUE)
            risk_score += transparency_check[1]
            recommendations.extend(transparency_check[2])
        
        # Check resource limits
        resource_check = await self._check_resource_limits(decision)
        if not resource_check[0]:
            violations.append(EthicalViolationType.RESOURCE_ABUSE)
            risk_score += resource_check[1]
            recommendations.extend(resource_check[2])
        
        # Determine approval based on violations and risk
        approved = len(violations) == 0 or risk_score < 0.3
        
        # Generate reasoning
        if approved:
            reasoning = f"Decision approved. Risk score: {risk_score:.2f}"
        else:
            reasoning = f"Decision rejected due to ethical violations: {', '.join([v.value for v in violations])}"
        
        # Create validation result
        result = ValidationResult(
            approved=approved,
            reasoning=reasoning,
            violations=violations,
            risk_score=risk_score,
            recommendations=recommendations
        )
        
        # Log the validation
        await self._log_validation(decision, result)
        
        # Store in history
        self.validation_history.append((decision, result))
        
        # Update violation count
        for violation in violations:
            self.violation_count[violation.value] = self.violation_count.get(violation.value, 0) + 1
        
        return result
    
    async def _check_harm_prevention(self, decision: AgentDecision) -> Tuple[bool, float, List[str]]:
        """Check if decision could cause harm."""
        passed = True
        risk = 0.0
        recommendations = []
        
        # Check for potentially harmful keywords in action
        harmful_keywords = ['delete', 'destroy', 'attack', 'harm', 'damage', 'kill', 'hurt']
        action_lower = decision.action.lower()
        
        for keyword in harmful_keywords:
            if keyword in action_lower:
                passed = False
                risk += 0.3
                recommendations.append(f"Reconsider action containing '{keyword}'")
        
        # Check context for harm indicators
        if 'target' in decision.context:
            target = decision.context.get('target', '')
            if any(term in str(target).lower() for term in ['user', 'human', 'person', 'individual']):
                if not passed:
                    risk += 0.2
                    recommendations.append("Action may affect human users - require additional review")
        
        return passed, risk, recommendations
    
    async def _check_privacy_protection(self, decision: AgentDecision) -> Tuple[bool, float, List[str]]:
        """Check if decision respects privacy."""
        passed = True
        risk = 0.0
        recommendations = []
        
        # Check for data access decisions
        if decision.decision_type == DecisionType.DATA_ACCESS:
            if 'personal_data' in decision.context and decision.context['personal_data']:
                if 'consent' not in decision.context or not decision.context['consent']:
                    passed = False
                    risk += 0.4
                    recommendations.append("Obtain user consent before accessing personal data")
        
        # Check for sensitive data patterns
        sensitive_patterns = ['password', 'ssn', 'credit_card', 'medical', 'biometric']
        context_str = json.dumps(decision.context).lower()
        
        for pattern in sensitive_patterns:
            if pattern in context_str:
                if 'encryption' not in decision.context:
                    passed = False
                    risk += 0.3
                    recommendations.append(f"Ensure encryption when handling {pattern} data")
        
        return passed, risk, recommendations
    
    async def _check_fairness(self, decision: AgentDecision) -> Tuple[bool, float, List[str]]:
        """Check if decision is fair and unbiased."""
        passed = True
        risk = 0.0
        recommendations = []
        
        # Check for discriminatory patterns
        if 'selection_criteria' in decision.context:
            criteria = decision.context['selection_criteria']
            protected_attributes = ['race', 'gender', 'age', 'religion', 'nationality', 'disability']
            
            for attr in protected_attributes:
                if attr in str(criteria).lower():
                    passed = False
                    risk += 0.5
                    recommendations.append(f"Remove {attr} from selection criteria to ensure fairness")
        
        # Check resource allocation fairness
        if decision.decision_type == DecisionType.RESOURCE_ALLOCATION:
            if 'priority' in decision.context:
                if decision.context['priority'] == 'exclusive':
                    risk += 0.2
                    recommendations.append("Consider more equitable resource distribution")
        
        return passed, risk, recommendations
    
    async def _check_transparency(self, decision: AgentDecision) -> Tuple[bool, float, List[str]]:
        """Check if decision is transparent and explainable."""
        passed = True
        risk = 0.0
        recommendations = []
        
        # Check if decision has explanation
        if 'explanation' not in decision.context or not decision.context.get('explanation'):
            passed = False
            risk += 0.2
            recommendations.append("Provide clear explanation for the decision")
        
        # Check if decision affects users
        if decision.decision_type == DecisionType.USER_INTERACTION:
            if 'disclosed_ai' not in decision.context or not decision.context['disclosed_ai']:
                passed = False
                risk += 0.2
                recommendations.append("Disclose AI nature to users")
        
        return passed, risk, recommendations
    
    async def _check_resource_limits(self, decision: AgentDecision) -> Tuple[bool, float, List[str]]:
        """Check if decision respects resource limits."""
        passed = True
        risk = 0.0
        recommendations = []
        
        limits = self.constraints.get('resource_limits', {})
        
        # Check CPU usage
        if 'cpu_percent' in decision.resources_required:
            max_cpu = limits.get('max_cpu_percent', 80)
            if decision.resources_required['cpu_percent'] > max_cpu:
                passed = False
                risk += 0.3
                recommendations.append(f"Reduce CPU usage to below {max_cpu}%")
        
        # Check memory usage
        if 'memory_mb' in decision.resources_required:
            max_memory = limits.get('max_memory_mb', 4096)
            if decision.resources_required['memory_mb'] > max_memory:
                passed = False
                risk += 0.3
                recommendations.append(f"Reduce memory usage to below {max_memory}MB")
        
        # Check agent creation limits
        if decision.decision_type == DecisionType.AGENT_CREATION:
            if 'team_size' in decision.context:
                max_agents = limits.get('max_agents_per_team', 10)
                if decision.context['team_size'] > max_agents:
                    passed = False
                    risk += 0.2
                    recommendations.append(f"Limit team size to {max_agents} agents")
        
        return passed, risk, recommendations
    
    async def _log_validation(self, decision: AgentDecision, result: ValidationResult):
        """Log validation to audit trail."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision.to_dict(),
            "result": result.to_dict()
        }
        
        # Log to audit logger
        self.audit_logger.info(json.dumps(log_entry))
        
        # Also log summary to main logger
        logger.info(
            f"Validation {result.validation_id}: "
            f"{'APPROVED' if result.approved else 'REJECTED'} - "
            f"Agent: {decision.agent_id}, "
            f"Type: {decision.decision_type.value}, "
            f"Risk: {result.risk_score:.2f}"
        )
    
    async def get_violation_summary(self) -> Dict[str, int]:
        """Get summary of all violations detected."""
        return dict(self.violation_count)
    
    async def get_validation_history(self, agent_id: str = None, 
                                    limit: int = 100) -> List[Tuple[AgentDecision, ValidationResult]]:
        """
        Get validation history, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of (decision, result) tuples
        """
        history = self.validation_history
        
        if agent_id:
            history = [(d, r) for d, r in history if d.agent_id == agent_id]
        
        return history[-limit:]
    
    async def update_constraints(self, new_constraints: Dict[str, Any]):
        """
        Update ethical constraints dynamically.
        
        Args:
            new_constraints: New constraint configuration
        """
        # Validate new constraints
        required_keys = ['harm_prevention', 'privacy_protection', 'fairness', 'transparency']
        for key in required_keys:
            if key not in new_constraints:
                raise ValueError(f"Missing required constraint category: {key}")
        
        # Update constraints
        self.constraints.update(new_constraints)
        
        # Save to config file
        with open(self.config_path, 'w') as f:
            yaml.dump(self.constraints, f, default_flow_style=False)
        
        logger.info("Ethical constraints updated successfully")
        self.audit_logger.info(f"Constraints updated: {json.dumps(new_constraints)}")
    
    async def emergency_shutdown(self, reason: str):
        """
        Initiate emergency shutdown of all agent activities.
        
        Args:
            reason: Reason for emergency shutdown
        """
        logger.critical(f"EMERGENCY SHUTDOWN INITIATED: {reason}")
        self.audit_logger.critical(f"Emergency shutdown: {reason}")
        
        # This would integrate with the safety monitor to halt all agents
        # For now, we'll just log the event
        shutdown_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "emergency_shutdown",
            "reason": reason,
            "violation_summary": await self.get_violation_summary()
        }
        
        self.audit_logger.critical(json.dumps(shutdown_event))
        
        # In a real implementation, this would trigger actual shutdown procedures
        return shutdown_event


# Example usage and testing
async def test_ethics_engine():
    """Test the Ethics Engine with sample decisions."""
    
    # Initialize engine
    engine = EthicsEngine()
    
    # Test case 1: Acceptable decision
    decision1 = AgentDecision(
        agent_id="agent-001",
        decision_type=DecisionType.TASK_EXECUTION,
        action="analyze_user_feedback",
        context={
            "explanation": "Analyzing aggregated user feedback to improve service",
            "personal_data": False,
            "purpose": "service_improvement"
        },
        resources_required={"cpu_percent": 20, "memory_mb": 512}
    )
    
    result1 = await engine.validate_decision(decision1)
    print(f"Decision 1: {result1.approved} - {result1.reasoning}")
    
    # Test case 2: Privacy violation
    decision2 = AgentDecision(
        agent_id="agent-002",
        decision_type=DecisionType.DATA_ACCESS,
        action="access_user_private_data",
        context={
            "personal_data": True,
            "consent": False,
            "target": "user_medical_records"
        }
    )
    
    result2 = await engine.validate_decision(decision2)
    print(f"Decision 2: {result2.approved} - {result2.reasoning}")
    
    # Test case 3: Resource limit violation
    decision3 = AgentDecision(
        agent_id="agent-003",
        decision_type=DecisionType.AGENT_CREATION,
        action="spawn_analysis_team",
        context={
            "team_size": 15,
            "purpose": "large_scale_analysis"
        },
        resources_required={"cpu_percent": 90, "memory_mb": 8192}
    )
    
    result3 = await engine.validate_decision(decision3)
    print(f"Decision 3: {result3.approved} - {result3.reasoning}")
    
    # Get violation summary
    summary = await engine.get_violation_summary()
    print(f"\nViolation Summary: {summary}")


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_ethics_engine())