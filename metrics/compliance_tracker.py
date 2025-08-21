"""
Compliance Tracker System

Monitors and tracks compliance with ethical, safety, resource, and operational policies.
Provides comprehensive violation tracking, threshold monitoring, and compliance reporting.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
import statistics


class ViolationType(Enum):
    """Types of compliance violations"""
    ETHICAL = "ethical"
    SAFETY = "safety"
    RESOURCE = "resource"
    OPERATIONAL = "operational"
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    REGULATORY = "regulatory"


class ViolationSeverity(Enum):
    """Severity levels for violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationStatus(Enum):
    """Status of a violation"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    WAIVED = "waived"


class ComplianceStatus(Enum):
    """Overall compliance status"""
    COMPLIANT = "compliant"
    MINOR_ISSUES = "minor_issues"
    MAJOR_ISSUES = "major_issues"
    NON_COMPLIANT = "non_compliant"
    CRITICAL = "critical"


@dataclass
class Violation:
    """Represents a compliance violation"""
    id: str
    type: ViolationType
    severity: ViolationSeverity
    status: ViolationStatus
    agent_id: str
    team_id: Optional[str]
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    detected_by: str  # System component that detected the violation
    threshold_violated: Optional[Dict[str, Any]] = None
    impact_assessment: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    waiver_reason: Optional[str] = None
    waived_by: Optional[str] = None
    related_violations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary"""
        data = asdict(self)
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class ComplianceThreshold:
    """Defines a compliance threshold"""
    name: str
    category: ViolationType
    metric: str
    operator: str  # >, <, >=, <=, ==, !=
    value: float
    severity: ViolationSeverity
    description: str
    enabled: bool = True
    grace_period: Optional[int] = None  # seconds
    auto_escalate: bool = False
    escalation_time: Optional[int] = None  # seconds


@dataclass
class ComplianceMetrics:
    """Compliance metrics for tracking"""
    total_violations: int = 0
    open_violations: int = 0
    resolved_violations: int = 0
    waived_violations: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    violations_by_severity: Dict[str, int] = field(default_factory=dict)
    mean_resolution_time: Optional[float] = None  # seconds
    compliance_score: float = 100.0  # 0-100
    compliance_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    last_violation: Optional[datetime] = None
    trends: Dict[str, Any] = field(default_factory=dict)


class ComplianceTracker:
    """
    Tracks compliance violations and monitors thresholds
    """
    
    def __init__(self, 
                 db_path: str = "storage/compliance.db",
                 config_path: Optional[str] = None,
                 ethics_engine: Optional[Any] = None,
                 safety_monitor: Optional[Any] = None,
                 audit_logger: Optional[Any] = None):
        """
        Initialize compliance tracker
        
        Args:
            db_path: Path to compliance database
            config_path: Path to threshold configuration
            ethics_engine: Reference to ethics engine
            safety_monitor: Reference to safety monitor
            audit_logger: Reference to audit logger
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # External components
        self.ethics_engine = ethics_engine
        self.safety_monitor = safety_monitor
        self.audit_logger = audit_logger
        
        # Initialize database
        self._init_database()
        
        # Load thresholds
        self.thresholds: Dict[str, ComplianceThreshold] = {}
        if config_path:
            self._load_thresholds(config_path)
        else:
            self._load_default_thresholds()
        
        # Violation cache
        self._violation_cache: Dict[str, Violation] = {}
        
        # Metrics cache
        self._metrics_cache: Optional[ComplianceMetrics] = None
        self._metrics_cache_time: Optional[datetime] = None
        self._metrics_cache_ttl = 60  # seconds
    
    def _init_database(self):
        """Initialize the compliance database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                team_id TEXT,
                description TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                detected_by TEXT NOT NULL,
                threshold_violated TEXT,
                impact_assessment TEXT,
                resolution TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                waiver_reason TEXT,
                waived_by TEXT,
                related_violations TEXT,
                hash TEXT NOT NULL
            )
        ''')
        
        # Create index for efficient queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_violations_status 
            ON violations(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_violations_timestamp 
            ON violations(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_violations_agent 
            ON violations(agent_id)
        ''')
        
        # Create thresholds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threshold_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                threshold_name TEXT NOT NULL,
                value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                violation_id TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (violation_id) REFERENCES violations(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_default_thresholds(self):
        """Load default compliance thresholds"""
        self.thresholds = {
            # Ethical thresholds
            "harm_prevention": ComplianceThreshold(
                name="harm_prevention",
                category=ViolationType.ETHICAL,
                metric="harm_score",
                operator=">",
                value=0.0,
                severity=ViolationSeverity.CRITICAL,
                description="No harm to users allowed",
                auto_escalate=True,
                escalation_time=0
            ),
            "privacy_violation": ComplianceThreshold(
                name="privacy_violation",
                category=ViolationType.ETHICAL,
                metric="privacy_breaches",
                operator=">",
                value=0.0,
                severity=ViolationSeverity.HIGH,
                description="Privacy breaches not allowed"
            ),
            
            # Safety thresholds
            "cpu_usage": ComplianceThreshold(
                name="cpu_usage",
                category=ViolationType.SAFETY,
                metric="cpu_percent",
                operator=">",
                value=90.0,
                severity=ViolationSeverity.MEDIUM,
                description="CPU usage exceeds safe threshold",
                grace_period=30
            ),
            "memory_usage": ComplianceThreshold(
                name="memory_usage",
                category=ViolationType.SAFETY,
                metric="memory_percent",
                operator=">",
                value=85.0,
                severity=ViolationSeverity.MEDIUM,
                description="Memory usage exceeds safe threshold",
                grace_period=30
            ),
            "error_rate": ComplianceThreshold(
                name="error_rate",
                category=ViolationType.SAFETY,
                metric="error_rate",
                operator=">",
                value=0.05,
                severity=ViolationSeverity.HIGH,
                description="Error rate exceeds 5%"
            ),
            
            # Resource thresholds
            "api_rate_limit": ComplianceThreshold(
                name="api_rate_limit",
                category=ViolationType.RESOURCE,
                metric="api_calls_per_minute",
                operator=">",
                value=1000.0,
                severity=ViolationSeverity.LOW,
                description="API rate limit exceeded"
            ),
            "storage_usage": ComplianceThreshold(
                name="storage_usage",
                category=ViolationType.RESOURCE,
                metric="storage_gb",
                operator=">",
                value=100.0,
                severity=ViolationSeverity.LOW,
                description="Storage limit exceeded"
            ),
            
            # Performance thresholds
            "response_time": ComplianceThreshold(
                name="response_time",
                category=ViolationType.PERFORMANCE,
                metric="response_time_ms",
                operator=">",
                value=5000.0,
                severity=ViolationSeverity.MEDIUM,
                description="Response time exceeds 5 seconds",
                grace_period=60
            ),
            "task_timeout": ComplianceThreshold(
                name="task_timeout",
                category=ViolationType.PERFORMANCE,
                metric="task_duration_seconds",
                operator=">",
                value=3600.0,
                severity=ViolationSeverity.HIGH,
                description="Task exceeds 1 hour timeout"
            ),
            
            # Quality thresholds
            "test_coverage": ComplianceThreshold(
                name="test_coverage",
                category=ViolationType.QUALITY,
                metric="test_coverage_percent",
                operator="<",
                value=80.0,
                severity=ViolationSeverity.LOW,
                description="Test coverage below 80%"
            ),
            "code_quality": ComplianceThreshold(
                name="code_quality",
                category=ViolationType.QUALITY,
                metric="quality_score",
                operator="<",
                value=7.0,
                severity=ViolationSeverity.MEDIUM,
                description="Code quality score below 7.0"
            )
        }
    
    def _load_thresholds(self, config_path: str):
        """Load thresholds from configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            for name, threshold_config in config.get('thresholds', {}).items():
                self.thresholds[name] = ComplianceThreshold(
                    name=name,
                    category=ViolationType(threshold_config['category']),
                    metric=threshold_config['metric'],
                    operator=threshold_config['operator'],
                    value=threshold_config['value'],
                    severity=ViolationSeverity(threshold_config['severity']),
                    description=threshold_config['description'],
                    enabled=threshold_config.get('enabled', True),
                    grace_period=threshold_config.get('grace_period'),
                    auto_escalate=threshold_config.get('auto_escalate', False),
                    escalation_time=threshold_config.get('escalation_time')
                )
        except Exception as e:
            print(f"Error loading thresholds from {config_path}: {e}")
            self._load_default_thresholds()
    
    def check_threshold(self, metric: str, value: float, 
                       agent_id: str, team_id: Optional[str] = None) -> Optional[Violation]:
        """
        Check if a metric violates any thresholds
        
        Args:
            metric: Metric name
            value: Metric value
            agent_id: Agent ID
            team_id: Optional team ID
            
        Returns:
            Violation if threshold violated, None otherwise
        """
        for threshold in self.thresholds.values():
            if not threshold.enabled or threshold.metric != metric:
                continue
            
            violated = False
            if threshold.operator == '>':
                violated = value > threshold.value
            elif threshold.operator == '>=':
                violated = value >= threshold.value
            elif threshold.operator == '<':
                violated = value < threshold.value
            elif threshold.operator == '<=':
                violated = value <= threshold.value
            elif threshold.operator == '==':
                violated = value == threshold.value
            elif threshold.operator == '!=':
                violated = value != threshold.value
            
            if violated:
                # Check grace period
                if threshold.grace_period:
                    # TODO: Implement grace period logic
                    pass
                
                # Create violation
                violation = self.record_violation(
                    type=threshold.category,
                    severity=threshold.severity,
                    agent_id=agent_id,
                    team_id=team_id,
                    description=threshold.description,
                    details={
                        'metric': metric,
                        'value': value,
                        'threshold': threshold.value,
                        'operator': threshold.operator
                    },
                    detected_by='threshold_monitor',
                    threshold_violated=asdict(threshold)
                )
                
                # Auto-escalate if configured
                if threshold.auto_escalate:
                    self.escalate_violation(violation.id, 
                                           reason="Auto-escalation configured")
                
                return violation
        
        return None
    
    def record_violation(self, 
                        type: ViolationType,
                        severity: ViolationSeverity,
                        agent_id: str,
                        description: str,
                        details: Dict[str, Any],
                        detected_by: str,
                        team_id: Optional[str] = None,
                        threshold_violated: Optional[Dict[str, Any]] = None,
                        impact_assessment: Optional[str] = None) -> Violation:
        """
        Record a new compliance violation
        
        Args:
            type: Type of violation
            severity: Severity level
            agent_id: Agent that caused violation
            description: Description of violation
            details: Additional details
            detected_by: Component that detected violation
            team_id: Optional team ID
            threshold_violated: Threshold that was violated
            impact_assessment: Assessment of impact
            
        Returns:
            Created violation
        """
        # Generate violation ID
        timestamp = datetime.now()
        violation_id = hashlib.sha256(
            f"{agent_id}_{type.value}_{timestamp.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create violation
        violation = Violation(
            id=violation_id,
            type=type,
            severity=severity,
            status=ViolationStatus.OPEN,
            agent_id=agent_id,
            team_id=team_id,
            description=description,
            details=details,
            timestamp=timestamp,
            detected_by=detected_by,
            threshold_violated=threshold_violated,
            impact_assessment=impact_assessment
        )
        
        # Store in database
        self._store_violation(violation)
        
        # Cache violation
        self._violation_cache[violation_id] = violation
        
        # Invalidate metrics cache
        self._metrics_cache = None
        
        # Log to audit trail if available
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type='COMPLIANCE_VIOLATION',
                agent_id=agent_id,
                details=violation.to_dict(),
                severity='HIGH' if severity in [ViolationSeverity.HIGH, ViolationSeverity.CRITICAL] else 'MEDIUM'
            )
        
        # Notify safety monitor if critical
        if self.safety_monitor and severity == ViolationSeverity.CRITICAL:
            self.safety_monitor.trigger_alert(
                alert_type='compliance_violation',
                severity='critical',
                details=violation.to_dict()
            )
        
        return violation
    
    def _store_violation(self, violation: Violation):
        """Store violation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Generate hash for integrity
        violation_dict = violation.to_dict()
        violation_hash = hashlib.sha256(
            json.dumps(violation_dict, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        cursor.execute('''
            INSERT INTO violations (
                id, type, severity, status, agent_id, team_id,
                description, details, timestamp, detected_by,
                threshold_violated, impact_assessment, resolution,
                resolved_at, resolved_by, waiver_reason, waived_by,
                related_violations, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation.id, violation.type.value, violation.severity.value,
            violation.status.value, violation.agent_id, violation.team_id,
            violation.description, json.dumps(violation.details),
            violation.timestamp.isoformat(), violation.detected_by,
            json.dumps(violation.threshold_violated, default=str) if violation.threshold_violated else None,
            violation.impact_assessment, violation.resolution,
            violation.resolved_at.isoformat() if violation.resolved_at else None,
            violation.resolved_by, violation.waiver_reason, violation.waived_by,
            json.dumps(violation.related_violations), violation_hash
        ))
        
        conn.commit()
        conn.close()
    
    def update_violation_status(self, violation_id: str, 
                               status: ViolationStatus,
                               resolution: Optional[str] = None,
                               resolved_by: Optional[str] = None,
                               waiver_reason: Optional[str] = None,
                               waived_by: Optional[str] = None):
        """
        Update the status of a violation
        
        Args:
            violation_id: Violation ID
            status: New status
            resolution: Resolution description
            resolved_by: Who resolved it
            waiver_reason: Reason for waiver
            waived_by: Who waived it
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current violation
        cursor.execute('SELECT * FROM violations WHERE id = ?', (violation_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Violation {violation_id} not found")
        
        # Update fields
        update_fields = ['status = ?']
        update_values = [status.value]
        
        if status == ViolationStatus.RESOLVED:
            update_fields.extend(['resolution = ?', 'resolved_at = ?', 'resolved_by = ?'])
            update_values.extend([resolution, datetime.now().isoformat(), resolved_by])
        elif status == ViolationStatus.WAIVED:
            update_fields.extend(['waiver_reason = ?', 'waived_by = ?', 'resolved_at = ?'])
            update_values.extend([waiver_reason, waived_by, datetime.now().isoformat()])
        
        update_values.append(violation_id)
        
        cursor.execute(f'''
            UPDATE violations 
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)
        
        conn.commit()
        conn.close()
        
        # Update cache
        if violation_id in self._violation_cache:
            self._violation_cache[violation_id].status = status
            if resolution:
                self._violation_cache[violation_id].resolution = resolution
            if resolved_by:
                self._violation_cache[violation_id].resolved_by = resolved_by
            if waiver_reason:
                self._violation_cache[violation_id].waiver_reason = waiver_reason
            if waived_by:
                self._violation_cache[violation_id].waived_by = waived_by
            if status in [ViolationStatus.RESOLVED, ViolationStatus.WAIVED]:
                self._violation_cache[violation_id].resolved_at = datetime.now()
        
        # Invalidate metrics cache
        self._metrics_cache = None
        
        # Log to audit trail
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type='VIOLATION_STATUS_UPDATE',
                agent_id=resolved_by or waived_by or 'system',
                details={
                    'violation_id': violation_id,
                    'new_status': status.value,
                    'resolution': resolution,
                    'waiver_reason': waiver_reason
                }
            )
    
    def escalate_violation(self, violation_id: str, reason: str):
        """
        Escalate a violation
        
        Args:
            violation_id: Violation ID
            reason: Reason for escalation
        """
        self.update_violation_status(violation_id, ViolationStatus.ESCALATED)
        
        # Log escalation
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type='VIOLATION_ESCALATED',
                agent_id='system',
                details={
                    'violation_id': violation_id,
                    'reason': reason
                },
                severity='HIGH'
            )
        
        # Notify safety monitor
        if self.safety_monitor:
            violation = self.get_violation(violation_id)
            if violation:
                self.safety_monitor.trigger_alert(
                    alert_type='violation_escalated',
                    severity='high',
                    details=violation.to_dict()
                )
    
    def get_violation(self, violation_id: str) -> Optional[Violation]:
        """
        Get a specific violation
        
        Args:
            violation_id: Violation ID
            
        Returns:
            Violation if found
        """
        # Check cache first
        if violation_id in self._violation_cache:
            return self._violation_cache[violation_id]
        
        # Query database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM violations WHERE id = ?', (violation_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            violation = self._row_to_violation(row)
            self._violation_cache[violation_id] = violation
            return violation
        
        return None
    
    def _row_to_violation(self, row: Tuple) -> Violation:
        """Convert database row to Violation object"""
        return Violation(
            id=row[0],
            type=ViolationType(row[1]),
            severity=ViolationSeverity(row[2]),
            status=ViolationStatus(row[3]),
            agent_id=row[4],
            team_id=row[5],
            description=row[6],
            details=json.loads(row[7]) if row[7] else {},
            timestamp=datetime.fromisoformat(row[8]),
            detected_by=row[9],
            threshold_violated=json.loads(row[10]) if row[10] else None,
            impact_assessment=row[11],
            resolution=row[12],
            resolved_at=datetime.fromisoformat(row[13]) if row[13] else None,
            resolved_by=row[14],
            waiver_reason=row[15],
            waived_by=row[16],
            related_violations=json.loads(row[17]) if row[17] else []
        )
    
    def get_violations(self, 
                       status: Optional[ViolationStatus] = None,
                       type: Optional[ViolationType] = None,
                       severity: Optional[ViolationSeverity] = None,
                       agent_id: Optional[str] = None,
                       team_id: Optional[str] = None,
                       since: Optional[datetime] = None,
                       limit: int = 100) -> List[Violation]:
        """
        Get violations matching criteria
        
        Args:
            status: Filter by status
            type: Filter by type
            severity: Filter by severity
            agent_id: Filter by agent
            team_id: Filter by team
            since: Filter by time
            limit: Maximum results
            
        Returns:
            List of violations
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = 'SELECT * FROM violations WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status.value)
        if type:
            query += ' AND type = ?'
            params.append(type.value)
        if severity:
            query += ' AND severity = ?'
            params.append(severity.value)
        if agent_id:
            query += ' AND agent_id = ?'
            params.append(agent_id)
        if team_id:
            query += ' AND team_id = ?'
            params.append(team_id)
        if since:
            query += ' AND timestamp > ?'
            params.append(since.isoformat())
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        violations = []
        for row in rows:
            violation = self._row_to_violation(row)
            violations.append(violation)
            # Cache violation
            self._violation_cache[violation.id] = violation
        
        return violations
    
    def calculate_metrics(self, 
                         since: Optional[datetime] = None,
                         team_id: Optional[str] = None) -> ComplianceMetrics:
        """
        Calculate compliance metrics
        
        Args:
            since: Calculate metrics since this time
            team_id: Filter by team
            
        Returns:
            Compliance metrics
        """
        # Check cache
        if self._metrics_cache and self._metrics_cache_time:
            if (datetime.now() - self._metrics_cache_time).seconds < self._metrics_cache_ttl:
                return self._metrics_cache
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metrics = ComplianceMetrics()
        
        # Build base query
        base_query = 'FROM violations WHERE 1=1'
        params = []
        
        if since:
            base_query += ' AND timestamp > ?'
            params.append(since.isoformat())
        if team_id:
            base_query += ' AND team_id = ?'
            params.append(team_id)
        
        # Total violations
        cursor.execute(f'SELECT COUNT(*) {base_query}', params)
        metrics.total_violations = cursor.fetchone()[0]
        
        # Open violations
        cursor.execute(f'SELECT COUNT(*) {base_query} AND status IN (?, ?, ?)', 
                      params + ['open', 'investigating', 'mitigating'])
        metrics.open_violations = cursor.fetchone()[0]
        
        # Resolved violations
        cursor.execute(f'SELECT COUNT(*) {base_query} AND status = ?', 
                      params + ['resolved'])
        metrics.resolved_violations = cursor.fetchone()[0]
        
        # Waived violations
        cursor.execute(f'SELECT COUNT(*) {base_query} AND status = ?', 
                      params + ['waived'])
        metrics.waived_violations = cursor.fetchone()[0]
        
        # Violations by type
        cursor.execute(f'SELECT type, COUNT(*) {base_query} GROUP BY type', params)
        for row in cursor.fetchall():
            metrics.violations_by_type[row[0]] = row[1]
        
        # Violations by severity
        cursor.execute(f'SELECT severity, COUNT(*) {base_query} GROUP BY severity', params)
        for row in cursor.fetchall():
            metrics.violations_by_severity[row[0]] = row[1]
        
        # Mean resolution time
        cursor.execute(f'''
            SELECT AVG(julianday(resolved_at) - julianday(timestamp)) * 86400
            {base_query} AND resolved_at IS NOT NULL
        ''', params)
        result = cursor.fetchone()[0]
        if result:
            metrics.mean_resolution_time = result
        
        # Last violation
        cursor.execute(f'SELECT MAX(timestamp) {base_query}', params)
        result = cursor.fetchone()[0]
        if result:
            metrics.last_violation = datetime.fromisoformat(result)
        
        conn.close()
        
        # Calculate compliance score
        metrics.compliance_score = self._calculate_compliance_score(metrics)
        
        # Determine compliance status
        metrics.compliance_status = self._determine_compliance_status(metrics)
        
        # Calculate trends
        metrics.trends = self._calculate_trends(since, team_id)
        
        # Cache metrics
        self._metrics_cache = metrics
        self._metrics_cache_time = datetime.now()
        
        return metrics
    
    def _calculate_compliance_score(self, metrics: ComplianceMetrics) -> float:
        """
        Calculate compliance score (0-100)
        
        Args:
            metrics: Current metrics
            
        Returns:
            Compliance score
        """
        score = 100.0
        
        # Deduct for open violations
        if metrics.open_violations > 0:
            score -= min(metrics.open_violations * 2, 20)
        
        # Deduct for critical/high severity violations
        critical_count = metrics.violations_by_severity.get('critical', 0)
        high_count = metrics.violations_by_severity.get('high', 0)
        
        score -= critical_count * 10
        score -= high_count * 5
        
        # Deduct for ethical violations
        ethical_count = metrics.violations_by_type.get('ethical', 0)
        score -= ethical_count * 15
        
        # Deduct for slow resolution
        if metrics.mean_resolution_time and metrics.mean_resolution_time > 3600:  # > 1 hour
            score -= 5
        
        # Bonus for low violation rate
        if metrics.total_violations == 0:
            score = 100.0
        elif metrics.total_violations < 5:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _determine_compliance_status(self, metrics: ComplianceMetrics) -> ComplianceStatus:
        """
        Determine overall compliance status
        
        Args:
            metrics: Current metrics
            
        Returns:
            Compliance status
        """
        critical_count = metrics.violations_by_severity.get('critical', 0)
        high_count = metrics.violations_by_severity.get('high', 0)
        
        if critical_count > 0:
            return ComplianceStatus.CRITICAL
        elif metrics.open_violations > 10 or high_count > 5:
            return ComplianceStatus.NON_COMPLIANT
        elif metrics.open_violations > 5 or high_count > 2:
            return ComplianceStatus.MAJOR_ISSUES
        elif metrics.open_violations > 0:
            return ComplianceStatus.MINOR_ISSUES
        else:
            return ComplianceStatus.COMPLIANT
    
    def _calculate_trends(self, since: Optional[datetime], 
                         team_id: Optional[str]) -> Dict[str, Any]:
        """
        Calculate compliance trends
        
        Args:
            since: Start time for trends
            team_id: Filter by team
            
        Returns:
            Trend data
        """
        trends = {}
        
        # Calculate violation rate trend (violations per day)
        now = datetime.now()
        periods = [7, 30, 90]  # days
        
        for period in periods:
            start_date = now - timedelta(days=period)
            violations = self.get_violations(since=start_date, team_id=team_id)
            rate = len(violations) / period
            trends[f'violation_rate_{period}d'] = rate
        
        # Calculate resolution time trend
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                DATE(timestamp) as date,
                AVG(julianday(resolved_at) - julianday(timestamp)) * 86400 as avg_resolution
            FROM violations
            WHERE resolved_at IS NOT NULL
        '''
        params = []
        
        if since:
            query += ' AND timestamp > ?'
            params.append(since.isoformat())
        if team_id:
            query += ' AND team_id = ?'
            params.append(team_id)
        
        query += ' GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 30'
        
        cursor.execute(query, params)
        resolution_times = []
        for row in cursor.fetchall():
            if row[1]:
                resolution_times.append(row[1])
        
        conn.close()
        
        if resolution_times:
            trends['resolution_time_trend'] = {
                'mean': statistics.mean(resolution_times),
                'median': statistics.median(resolution_times),
                'improving': resolution_times[0] < resolution_times[-1] if len(resolution_times) > 1 else False
            }
        
        return trends
    
    def generate_summary(self, 
                        since: Optional[datetime] = None,
                        team_id: Optional[str] = None) -> str:
        """
        Generate compliance summary
        
        Args:
            since: Start time for summary
            team_id: Filter by team
            
        Returns:
            Summary text
        """
        metrics = self.calculate_metrics(since, team_id)
        
        summary = f"""
## Compliance Summary

**Status**: {metrics.compliance_status.value.replace('_', ' ').title()}
**Score**: {metrics.compliance_score:.1f}/100

### Violations
- Total: {metrics.total_violations}
- Open: {metrics.open_violations}
- Resolved: {metrics.resolved_violations}
- Waived: {metrics.waived_violations}

### By Severity
"""
        
        for severity in ['critical', 'high', 'medium', 'low']:
            count = metrics.violations_by_severity.get(severity, 0)
            if count > 0:
                summary += f"- {severity.title()}: {count}\n"
        
        summary += "\n### By Type\n"
        for vtype, count in metrics.violations_by_type.items():
            summary += f"- {vtype.title()}: {count}\n"
        
        if metrics.mean_resolution_time:
            hours = metrics.mean_resolution_time / 3600
            summary += f"\n### Resolution\n"
            summary += f"- Mean Resolution Time: {hours:.1f} hours\n"
        
        if metrics.last_violation:
            summary += f"\n### Last Violation\n"
            summary += f"- {metrics.last_violation.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Add trends
        if metrics.trends:
            summary += "\n### Trends\n"
            for period in [7, 30, 90]:
                key = f'violation_rate_{period}d'
                if key in metrics.trends:
                    rate = metrics.trends[key]
                    summary += f"- {period}-day violation rate: {rate:.2f}/day\n"
        
        return summary
    
    def export_violations(self, 
                         format: str = 'json',
                         since: Optional[datetime] = None,
                         team_id: Optional[str] = None) -> str:
        """
        Export violations in specified format
        
        Args:
            format: Export format (json, csv)
            since: Export violations since
            team_id: Filter by team
            
        Returns:
            Exported data
        """
        violations = self.get_violations(since=since, team_id=team_id, limit=10000)
        
        if format == 'json':
            return json.dumps([v.to_dict() for v in violations], indent=2)
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if violations:
                writer = csv.DictWriter(output, fieldnames=violations[0].to_dict().keys())
                writer.writeheader()
                for violation in violations:
                    writer.writerow(violation.to_dict())
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


if __name__ == "__main__":
    # Test compliance tracker
    tracker = ComplianceTracker()
    
    # Test threshold violation
    print("Testing threshold violation...")
    violation = tracker.check_threshold(
        metric='cpu_percent',
        value=95.0,
        agent_id='test_agent',
        team_id='test_team'
    )
    if violation:
        print(f"Created violation: {violation.id}")
    
    # Record manual violation
    print("\nRecording manual violation...")
    violation2 = tracker.record_violation(
        type=ViolationType.ETHICAL,
        severity=ViolationSeverity.HIGH,
        agent_id='test_agent_2',
        description='Attempted to access restricted data',
        details={'resource': '/sensitive/data', 'action': 'read'},
        detected_by='access_control'
    )
    print(f"Created violation: {violation2.id}")
    
    # Calculate metrics
    print("\nCalculating metrics...")
    metrics = tracker.calculate_metrics()
    print(f"Compliance Score: {metrics.compliance_score:.1f}")
    print(f"Compliance Status: {metrics.compliance_status.value}")
    print(f"Open Violations: {metrics.open_violations}")
    
    # Generate summary
    print("\nGenerating summary...")
    summary = tracker.generate_summary()
    print(summary)
    
    # Update violation status
    if violation:
        print(f"\nResolving violation {violation.id}...")
        tracker.update_violation_status(
            violation.id,
            ViolationStatus.RESOLVED,
            resolution="CPU usage normalized after scaling",
            resolved_by="auto_scaler"
        )
    
    print("\nCompliance tracker test completed!")