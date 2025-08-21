"""
Audit Logger Module for Agile AI Control Layer

This module provides an immutable, cryptographically verifiable audit trail
for all agent decisions, actions, and system events. It ensures compliance,
accountability, and traceability throughout the AI system.

Features:
- Append-only logging with cryptographic signatures
- Hash chain for tamper detection
- Configurable retention policies
- Query interface for audit retrieval
- Integration with Ethics Engine, Safety Monitor, and Resource Allocator
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from queue import Queue, Empty
import hmac
import base64

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class EventType(Enum):
    """Types of events that can be logged"""
    DECISION = "DECISION"
    ACTION = "ACTION"
    INTERVENTION = "INTERVENTION"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class EventCategory(Enum):
    """Categories for classifying events"""
    ETHICS = "ETHICS"
    SAFETY = "SAFETY"
    RESOURCE = "RESOURCE"
    WORKFLOW = "WORKFLOW"
    TEAM = "TEAM"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"


class Severity(Enum):
    """Severity levels for events"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ActorType(Enum):
    """Types of actors that can generate events"""
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    HUMAN = "HUMAN"
    TEAM = "TEAM"


class DecisionResult(Enum):
    """Possible results of a decision"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    DEFERRED = "DEFERRED"


class ComplianceStatus(Enum):
    """Compliance status of an event"""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    WAIVED = "WAIVED"
    PENDING = "PENDING"


class RetentionPolicy(Enum):
    """Retention policies for audit records"""
    PERMANENT = "PERMANENT"  # Never delete
    LONG_TERM = "LONG_TERM"  # 7 years
    STANDARD = "STANDARD"    # 1 year
    SHORT_TERM = "SHORT_TERM"  # 90 days


@dataclass
class AuditEntry:
    """Data structure for an audit log entry"""
    # Core fields
    timestamp: datetime
    event_type: EventType
    event_category: EventCategory
    severity: Severity
    
    # Actor information
    actor_type: ActorType
    actor_id: str
    actor_role: Optional[str] = None
    team_id: Optional[str] = None
    
    # Event details
    event_id: str = None
    event_description: str = ""
    event_data: Optional[Dict[str, Any]] = None
    
    # Decision tracking
    decision_id: Optional[str] = None
    decision_type: Optional[str] = None
    decision_result: Optional[DecisionResult] = None
    decision_reasoning: Optional[str] = None
    
    # Resource tracking
    resource_type: Optional[str] = None
    resource_amount: Optional[float] = None
    resource_limit: Optional[float] = None
    
    # Compliance and ethics
    ethical_assessment: Optional[Dict[str, Any]] = None
    compliance_status: Optional[ComplianceStatus] = None
    compliance_details: Optional[str] = None
    
    # Cryptographic fields
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    signature: Optional[str] = None
    
    # Retention
    retention_policy: RetentionPolicy = RetentionPolicy.STANDARD
    retention_until: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize computed fields"""
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        
        if self.retention_until is None:
            self.retention_until = self._calculate_retention_date()
    
    def _calculate_retention_date(self) -> datetime:
        """Calculate retention date based on policy"""
        retention_days = {
            RetentionPolicy.PERMANENT: 36500,  # 100 years
            RetentionPolicy.LONG_TERM: 2555,   # 7 years
            RetentionPolicy.STANDARD: 365,     # 1 year
            RetentionPolicy.SHORT_TERM: 90     # 90 days
        }
        days = retention_days.get(self.retention_policy, 365)
        return datetime.now(timezone.utc) + timedelta(days=days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for storage"""
        data = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    data[key] = value.value
                elif isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = value
        return data
    
    def calculate_hash(self, previous_hash: str = "") -> str:
        """Calculate SHA-512 hash of the entry"""
        # Create a deterministic string representation
        hash_data = {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'event_category': self.event_category.value,
            'severity': self.severity.value,
            'actor_type': self.actor_type.value,
            'actor_id': self.actor_id,
            'event_id': self.event_id,
            'event_description': self.event_description,
            'previous_hash': previous_hash
        }
        
        # Add optional fields if present
        if self.decision_id:
            hash_data['decision_id'] = self.decision_id
        if self.decision_result:
            hash_data['decision_result'] = self.decision_result.value
        
        # Create hash
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha512(hash_string.encode()).hexdigest()
    
    def sign(self, secret_key: str) -> str:
        """Create HMAC signature for the entry"""
        message = f"{self.event_id}:{self.current_hash}:{self.timestamp.isoformat()}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha512
        ).digest()
        return base64.b64encode(signature).decode()


class AuditLogger:
    """
    Main audit logger class that manages the audit trail
    """
    
    def __init__(self, db_path: str = None, secret_key: str = None):
        """
        Initialize the audit logger
        
        Args:
            db_path: Path to SQLite database (uses in-memory if None)
            secret_key: Secret key for signing entries
        """
        self.db_path = db_path or ":memory:"
        self.secret_key = secret_key or os.environ.get('AUDIT_SECRET_KEY', 'default-secret-key')
        self.connection = None
        self.write_queue = Queue(maxsize=1000)
        self.write_thread = None
        self.running = False
        self.lock = threading.Lock()
        self.last_hash = ""
        
        # Initialize database
        self._init_database()
        
        # Start background writer thread
        self._start_writer_thread()
        
        # Log initialization
        self.log_event(
            event_type=EventType.INFO,
            event_category=EventCategory.SYSTEM,
            severity=Severity.INFO,
            actor_type=ActorType.SYSTEM,
            actor_id="AUDIT_LOGGER",
            event_description="Audit logger initialized"
        )
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        
        # Create main audit table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_category TEXT NOT NULL,
                severity TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_role TEXT,
                team_id TEXT,
                event_id TEXT UNIQUE NOT NULL,
                event_description TEXT NOT NULL,
                event_data TEXT,
                decision_id TEXT,
                decision_type TEXT,
                decision_result TEXT,
                decision_reasoning TEXT,
                resource_type TEXT,
                resource_amount REAL,
                resource_limit REAL,
                ethical_assessment TEXT,
                compliance_status TEXT,
                compliance_details TEXT,
                previous_hash TEXT,
                current_hash TEXT NOT NULL,
                signature TEXT,
                retention_policy TEXT DEFAULT 'STANDARD',
                retention_until TEXT,
                archived INTEGER DEFAULT 0,
                archive_location TEXT
            )
        """)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_event_category ON audit_log(event_category)",
            "CREATE INDEX IF NOT EXISTS idx_severity ON audit_log(severity)",
            "CREATE INDEX IF NOT EXISTS idx_actor_id ON audit_log(actor_id)",
            "CREATE INDEX IF NOT EXISTS idx_team_id ON audit_log(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_event_id ON audit_log(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_decision_id ON audit_log(decision_id)",
            "CREATE INDEX IF NOT EXISTS idx_archived ON audit_log(archived)"
        ]
        
        for index in indexes:
            self.connection.execute(index)
        
        # Create metadata table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create query log table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                queried_by TEXT NOT NULL,
                query_type TEXT NOT NULL,
                query_parameters TEXT,
                result_count INTEGER
            )
        """)
        
        self.connection.commit()
        
        # Get last hash if exists
        cursor = self.connection.execute(
            "SELECT current_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            self.last_hash = row['current_hash']
    
    def _start_writer_thread(self):
        """Start background thread for writing audit entries"""
        self.running = True
        self.write_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.write_thread.start()
    
    def _writer_loop(self):
        """Background loop for writing queued entries to database"""
        while self.running:
            try:
                # Get entry from queue with timeout
                entry = self.write_queue.get(timeout=1.0)
                
                # Only write if it's an actual AuditEntry
                if isinstance(entry, AuditEntry):
                    self._write_entry(entry)
                
                # Mark task as done
                self.write_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in writer loop: {e}")
    
    def _write_entry(self, entry: AuditEntry):
        """Write an entry to the database"""
        with self.lock:
            # Calculate hash
            entry.previous_hash = self.last_hash
            entry.current_hash = entry.calculate_hash(self.last_hash)
            
            # Sign the entry
            entry.signature = entry.sign(self.secret_key)
            
            # Convert to dict for storage
            data = entry.to_dict()
            
            # Prepare SQL
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            sql = f"INSERT INTO audit_log ({columns}) VALUES ({placeholders})"
            
            # Execute insert
            self.connection.execute(sql, list(data.values()))
            self.connection.commit()
            
            # Update last hash
            self.last_hash = entry.current_hash
            
            # Update metadata
            self.connection.execute(
                "INSERT OR REPLACE INTO audit_metadata (key, value) VALUES (?, ?)",
                ('last_entry_timestamp', entry.timestamp.isoformat())
            )
            self.connection.commit()
    
    def log_event(
        self,
        event_type: EventType,
        event_category: EventCategory,
        severity: Severity,
        actor_type: ActorType,
        actor_id: str,
        event_description: str,
        **kwargs
    ) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            event_category: Category of event
            severity: Severity level
            actor_type: Type of actor
            actor_id: ID of the actor
            event_description: Description of the event
            **kwargs: Additional optional fields
        
        Returns:
            Event ID of the logged entry
        """
        # Create audit entry
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            event_description=event_description,
            **kwargs
        )
        
        # Add to write queue
        self.write_queue.put(entry)
        
        # Also write to file for redundancy
        self._write_to_file(entry)
        
        return entry.event_id
    
    def _write_to_file(self, entry: AuditEntry):
        """Write entry to file as backup"""
        try:
            # Create audit logs directory if it doesn't exist
            log_dir = Path(__file__).parent / 'audit_logs'
            log_dir.mkdir(exist_ok=True)
            
            # Create filename based on date
            date_str = entry.timestamp.strftime('%Y%m%d')
            filename = log_dir / f'audit_{date_str}.log'
            
            # Write entry as JSON
            with open(filename, 'a') as f:
                json_entry = {
                    'timestamp': entry.timestamp.isoformat(),
                    'event_id': entry.event_id,
                    'event_type': entry.event_type.value,
                    'event_category': entry.event_category.value,
                    'severity': entry.severity.value,
                    'actor_id': entry.actor_id,
                    'description': entry.event_description,
                    'hash': entry.current_hash
                }
                f.write(json.dumps(json_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to audit file: {e}")
    
    def log_decision(
        self,
        actor_id: str,
        decision_type: str,
        decision_result: DecisionResult,
        reasoning: str,
        **kwargs
    ) -> str:
        """
        Log a decision event
        
        Args:
            actor_id: ID of the decision maker
            decision_type: Type of decision
            decision_result: Result of the decision
            reasoning: Reasoning for the decision
            **kwargs: Additional fields
        
        Returns:
            Event ID
        """
        decision_id = str(uuid.uuid4())
        
        return self.log_event(
            event_type=EventType.DECISION,
            event_category=kwargs.get('event_category', EventCategory.SYSTEM),
            severity=kwargs.get('severity', Severity.INFO),
            actor_type=kwargs.get('actor_type', ActorType.AGENT),
            actor_id=actor_id,
            event_description=f"Decision made: {decision_type}",
            decision_id=decision_id,
            decision_type=decision_type,
            decision_result=decision_result,
            decision_reasoning=reasoning,
            **{k: v for k, v in kwargs.items() if k not in ['event_category', 'severity', 'actor_type']}
        )
    
    def log_resource_usage(
        self,
        actor_id: str,
        resource_type: str,
        amount: float,
        limit: float,
        **kwargs
    ) -> str:
        """
        Log resource usage
        
        Args:
            actor_id: ID of the resource consumer
            resource_type: Type of resource
            amount: Amount used
            limit: Resource limit
            **kwargs: Additional fields
        
        Returns:
            Event ID
        """
        # Determine severity based on usage percentage
        usage_percent = (amount / limit) * 100 if limit > 0 else 0
        if usage_percent >= 90:
            severity = Severity.HIGH
        elif usage_percent >= 75:
            severity = Severity.MEDIUM
        else:
            severity = Severity.INFO
        
        return self.log_event(
            event_type=EventType.ACTION,
            event_category=EventCategory.RESOURCE,
            severity=severity,
            actor_type=kwargs.get('actor_type', ActorType.AGENT),
            actor_id=actor_id,
            event_description=f"Resource usage: {resource_type} ({amount:.2f}/{limit:.2f})",
            resource_type=resource_type,
            resource_amount=amount,
            resource_limit=limit,
            **{k: v for k, v in kwargs.items() if k not in ['actor_type']}
        )
    
    def log_ethical_assessment(
        self,
        actor_id: str,
        assessment: Dict[str, Any],
        compliance_status: ComplianceStatus,
        **kwargs
    ) -> str:
        """
        Log an ethical assessment
        
        Args:
            actor_id: ID of the assessed actor
            assessment: Ethical assessment details
            compliance_status: Compliance status
            **kwargs: Additional fields
        
        Returns:
            Event ID
        """
        # Determine severity based on compliance
        severity_map = {
            ComplianceStatus.COMPLIANT: Severity.INFO,
            ComplianceStatus.PENDING: Severity.LOW,
            ComplianceStatus.WAIVED: Severity.MEDIUM,
            ComplianceStatus.NON_COMPLIANT: Severity.HIGH
        }
        severity = severity_map.get(compliance_status, Severity.INFO)
        
        return self.log_event(
            event_type=EventType.DECISION,
            event_category=EventCategory.ETHICS,
            severity=severity,
            actor_type=kwargs.get('actor_type', ActorType.SYSTEM),
            actor_id=actor_id,
            event_description=f"Ethical assessment: {compliance_status.value}",
            ethical_assessment=assessment,
            compliance_status=compliance_status,
            compliance_details=kwargs.get('compliance_details', ''),
            **{k: v for k, v in kwargs.items() if k not in ['actor_type', 'compliance_details']}
        )
    
    def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        event_category: Optional[EventCategory] = None,
        severity: Optional[Severity] = None,
        actor_id: Optional[str] = None,
        team_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        queried_by: str = "SYSTEM"
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters
        
        Args:
            start_time: Start time for query
            end_time: End time for query
            event_type: Filter by event type
            event_category: Filter by category
            severity: Filter by severity
            actor_id: Filter by actor ID
            team_id: Filter by team ID
            limit: Maximum results
            offset: Result offset
            queried_by: Who is querying
        
        Returns:
            List of matching audit entries
        """
        # Build query
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if event_category:
            query += " AND event_category = ?"
            params.append(event_category.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)
        
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        cursor = self.connection.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Log the query
        self.connection.execute(
            """INSERT INTO audit_query_log 
               (queried_by, query_type, query_parameters, result_count)
               VALUES (?, ?, ?, ?)""",
            (queried_by, 'SELECT', json.dumps({
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'event_type': event_type.value if event_type else None,
                'limit': limit,
                'offset': offset
            }), len(results))
        )
        self.connection.commit()
        
        return results
    
    def verify_integrity(self, start_id: int = 1, end_id: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the audit log hash chain
        
        Args:
            start_id: Starting record ID
            end_id: Ending record ID (None for latest)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Get records
        if end_id:
            query = "SELECT * FROM audit_log WHERE id >= ? AND id <= ? ORDER BY id"
            params = [start_id, end_id]
        else:
            query = "SELECT * FROM audit_log WHERE id >= ? ORDER BY id"
            params = [start_id]
        
        cursor = self.connection.execute(query, params)
        records = cursor.fetchall()
        
        if not records:
            return True, []
        
        # Verify hash chain
        previous_hash = ""
        for i, record in enumerate(records):
            # Check previous hash matches
            if i > 0 and record['previous_hash'] != previous_hash:
                errors.append(
                    f"Hash chain broken at record {record['id']}: "
                    f"expected previous_hash={previous_hash}, "
                    f"got {record['previous_hash']}"
                )
            
            # Verify signature if present
            if record['signature']:
                expected_signature = self._calculate_signature(
                    record['event_id'],
                    record['current_hash'],
                    record['timestamp']
                )
                if record['signature'] != expected_signature:
                    errors.append(
                        f"Invalid signature at record {record['id']}"
                    )
            
            previous_hash = record['current_hash']
        
        return len(errors) == 0, errors
    
    def _calculate_signature(self, event_id: str, hash_value: str, timestamp: str) -> str:
        """Calculate expected signature for verification"""
        message = f"{event_id}:{hash_value}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha512
        ).digest()
        return base64.b64encode(signature).decode()
    
    def apply_retention_policies(self) -> int:
        """
        Apply retention policies to archive or delete old records
        
        Returns:
            Number of records affected
        """
        affected = 0
        
        # Define retention periods (in days)
        retention_periods = {
            'PERMANENT': 36500,  # 100 years
            'LONG_TERM': 2555,   # 7 years
            'STANDARD': 365,     # 1 year
            'SHORT_TERM': 90     # 90 days
        }
        
        for policy, days in retention_periods.items():
            if policy == 'PERMANENT':
                continue  # Skip permanent records
            
            # Archive old records
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            cursor = self.connection.execute(
                """UPDATE audit_log 
                   SET archived = 1, 
                       archive_location = 'archive_' || strftime('%Y%m', 'now')
                   WHERE retention_policy = ? 
                   AND timestamp < ? 
                   AND archived = 0""",
                (policy, cutoff_date.isoformat())
            )
            
            affected += cursor.rowcount
        
        self.connection.commit()
        
        # Log retention application
        self.log_event(
            event_type=EventType.ACTION,
            event_category=EventCategory.SYSTEM,
            severity=Severity.INFO,
            actor_type=ActorType.SYSTEM,
            actor_id="RETENTION_MANAGER",
            event_description=f"Applied retention policies, {affected} records archived"
        )
        
        return affected
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics
        
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Total records
        cursor = self.connection.execute("SELECT COUNT(*) as count FROM audit_log")
        stats['total_records'] = cursor.fetchone()['count']
        
        # Records by type
        cursor = self.connection.execute(
            """SELECT event_type, COUNT(*) as count 
               FROM audit_log 
               GROUP BY event_type"""
        )
        stats['by_type'] = {row['event_type']: row['count'] for row in cursor.fetchall()}
        
        # Records by category
        cursor = self.connection.execute(
            """SELECT event_category, COUNT(*) as count 
               FROM audit_log 
               GROUP BY event_category"""
        )
        stats['by_category'] = {row['event_category']: row['count'] for row in cursor.fetchall()}
        
        # Records by severity
        cursor = self.connection.execute(
            """SELECT severity, COUNT(*) as count 
               FROM audit_log 
               GROUP BY severity"""
        )
        stats['by_severity'] = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        # Active vs archived
        cursor = self.connection.execute(
            """SELECT archived, COUNT(*) as count 
               FROM audit_log 
               GROUP BY archived"""
        )
        archive_stats = {row['archived']: row['count'] for row in cursor.fetchall()}
        stats['active_records'] = archive_stats.get(0, 0)
        stats['archived_records'] = archive_stats.get(1, 0)
        
        # Recent activity (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        cursor = self.connection.execute(
            "SELECT COUNT(*) as count FROM audit_log WHERE timestamp >= ?",
            (yesterday.isoformat(),)
        )
        stats['last_24_hours'] = cursor.fetchone()['count']
        
        return stats
    
    def export_logs(
        self,
        output_file: str,
        format: str = 'json',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Export audit logs to file
        
        Args:
            output_file: Output file path
            format: Export format (json, csv)
            start_time: Start time filter
            end_time: End time filter
        
        Returns:
            Number of records exported
        """
        # Query logs
        logs = self.query_logs(
            start_time=start_time,
            end_time=end_time,
            limit=1000000  # Large limit for export
        )
        
        # Export based on format
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(logs, f, indent=2, default=str)
        
        elif format == 'csv':
            import csv
            if logs:
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)
        
        # Log the export
        self.log_event(
            event_type=EventType.ACTION,
            event_category=EventCategory.SYSTEM,
            severity=Severity.INFO,
            actor_type=ActorType.SYSTEM,
            actor_id="EXPORT_MANAGER",
            event_description=f"Exported {len(logs)} records to {output_file}"
        )
        
        return len(logs)
    
    def close(self):
        """Close the audit logger and clean up resources"""
        # Stop writer thread
        self.running = False
        if self.write_thread:
            self.write_thread.join(timeout=5)
        
        # Flush any remaining entries
        while not self.write_queue.empty():
            try:
                entry = self.write_queue.get_nowait()
                # Only write if it's an actual AuditEntry
                if isinstance(entry, AuditEntry):
                    self._write_entry(entry)
            except Empty:
                break
        
        # Close database connection
        if self.connection:
            self.connection.close()
        
        logger.info("Audit logger closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience functions for integration with other modules

def create_audit_logger(db_path: str = None) -> AuditLogger:
    """
    Factory function to create an audit logger instance
    
    Args:
        db_path: Database path (None for in-memory)
    
    Returns:
        AuditLogger instance
    """
    # Use environment variable if available
    if db_path is None:
        db_path = os.environ.get('AUDIT_DB_PATH', 'control/storage/audit.db')
    
    # Ensure directory exists
    if db_path != ':memory:':
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    return AuditLogger(db_path=db_path)


# Integration helpers for other control layer components

class EthicsAuditMixin:
    """Mixin for Ethics Engine integration"""
    
    def audit_ethical_decision(
        self,
        audit_logger: AuditLogger,
        decision: Dict[str, Any],
        assessment: Dict[str, Any],
        result: DecisionResult
    ):
        """Log an ethical decision to audit trail"""
        return audit_logger.log_ethical_assessment(
            actor_id=decision.get('agent_id', 'UNKNOWN'),
            assessment=assessment,
            compliance_status=ComplianceStatus.COMPLIANT if result == DecisionResult.APPROVED else ComplianceStatus.NON_COMPLIANT,
            decision_result=result,
            actor_type=ActorType.AGENT,
            team_id=decision.get('team_id')
        )


class SafetyAuditMixin:
    """Mixin for Safety Monitor integration"""
    
    def audit_safety_intervention(
        self,
        audit_logger: AuditLogger,
        agent_id: str,
        intervention_type: str,
        reason: str,
        severity: Severity = Severity.HIGH
    ):
        """Log a safety intervention to audit trail"""
        return audit_logger.log_event(
            event_type=EventType.INTERVENTION,
            event_category=EventCategory.SAFETY,
            severity=severity,
            actor_type=ActorType.SYSTEM,
            actor_id="SAFETY_MONITOR",
            event_description=f"Safety intervention: {intervention_type}",
            event_data={
                'target_agent': agent_id,
                'intervention_type': intervention_type,
                'reason': reason
            }
        )


class ResourceAuditMixin:
    """Mixin for Resource Allocator integration"""
    
    def audit_resource_allocation(
        self,
        audit_logger: AuditLogger,
        team_id: str,
        resource_type: str,
        amount: float,
        limit: float
    ):
        """Log resource allocation to audit trail"""
        return audit_logger.log_resource_usage(
            actor_id=team_id,
            resource_type=resource_type,
            amount=amount,
            limit=limit,
            actor_type=ActorType.TEAM
        )


if __name__ == "__main__":
    # Example usage and testing
    logger_instance = create_audit_logger()
    
    # Log various events
    logger_instance.log_event(
        event_type=EventType.INFO,
        event_category=EventCategory.SYSTEM,
        severity=Severity.INFO,
        actor_type=ActorType.SYSTEM,
        actor_id="TEST",
        event_description="Test audit logger"
    )
    
    # Log a decision
    logger_instance.log_decision(
        actor_id="AGENT-001",
        decision_type="TASK_ALLOCATION",
        decision_result=DecisionResult.APPROVED,
        reasoning="Resources available and task priority high"
    )
    
    # Query logs
    recent_logs = logger_instance.query_logs(limit=10)
    print(f"Found {len(recent_logs)} recent audit entries")
    
    # Verify integrity
    is_valid, errors = logger_instance.verify_integrity()
    print(f"Audit log integrity: {'Valid' if is_valid else 'Invalid'}")
    
    # Get statistics
    stats = logger_instance.get_statistics()
    print(f"Audit statistics: {stats}")
    
    # Clean up
    logger_instance.close()