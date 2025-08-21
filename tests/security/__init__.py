"""
Security Testing Suite for Agile AI Company Framework

This module provides comprehensive security testing for:
- Ethics engine enforcement
- Safety threshold monitoring
- Resource limit validation
- Audit trail integrity
"""

from .ethics_tests import EthicsEngineSecurityTests
from .safety_tests import SafetyMonitorSecurityTests
from .resource_tests import ResourceLimitSecurityTests
from .audit_tests import AuditTrailSecurityTests

__all__ = [
    'EthicsEngineSecurityTests',
    'SafetyMonitorSecurityTests',
    'ResourceLimitSecurityTests',
    'AuditTrailSecurityTests'
]

# Version
__version__ = '1.0.0'