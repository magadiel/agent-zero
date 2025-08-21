# Security Testing Suite

## Overview

This directory contains comprehensive security tests for the Agile AI Company Framework, validating the control layer's security mechanisms including ethics enforcement, safety monitoring, resource limits, and audit trail integrity.

## Test Coverage

### 1. Ethics Engine Security Tests (`ethics_tests.py`)
Tests the ethics engine's ability to:
- **Constraint Validation**: Block harmful actions and approve safe ones
- **Decision Approval/Rejection**: Handle high-risk and low-risk decisions appropriately
- **Emergency Shutdown**: Trigger system-wide shutdown on critical violations
- **Risk Assessment**: Accurately score and categorize risks
- **Override Mechanisms**: Validate authorization for safety overrides
- **Audit Trail Security**: Ensure ethical decisions are properly logged
- **Constraint Bypass Prevention**: Prevent manipulation attempts
- **Multi-layer Validation**: Validate complex multi-step operations
- **Rate Limiting**: Prevent abuse through repeated requests
- **Escalation Procedures**: Handle repeated violations appropriately

### 2. Safety Monitor Security Tests (`safety_tests.py`)
Tests the safety monitor's ability to:
- **Threshold Monitoring**: Detect breaches and multi-level escalation
- **Automatic Interventions**: Apply throttling, suspension, and termination
- **Kill Switches**: Emergency and graceful shutdown mechanisms
- **Circuit Breakers**: Fault tolerance and recovery patterns
- **Anomaly Detection**: Identify unusual patterns and behaviors
- **Resource Exhaustion Prevention**: Block resource abuse attempts
- **Threat Detection**: Classify and respond to security threats
- **Intervention Validation**: Ensure interventions are effective
- **Coordinated Response**: Handle multi-agent threat scenarios
- **Recovery Procedures**: Restore normal operations after incidents

### 3. Resource Limit Security Tests (`resource_tests.py`)
Tests resource allocation security:
- **Allocation Limits**: Enforce per-team and cumulative limits
- **Priority Queues**: Respect priority ordering and preemption
- **Emergency Releases**: Quick resource recovery mechanisms
- **Resource Exhaustion**: Prevent denial-of-service attacks
- **Burst Allocation**: Temporary resource increases with limits
- **Resource Pools**: Isolation between different pools
- **Deadlock Prevention**: Avoid resource allocation deadlocks
- **Starvation Prevention**: Ensure fair resource distribution
- **Concurrent Access**: Thread-safe resource allocation
- **Resource Reservation**: Future resource planning

### 4. Audit Trail Security Tests (`audit_tests.py`)
Tests audit trail integrity:
- **Immutability**: Prevent modification of audit entries
- **Cryptographic Signatures**: Validate entry authenticity
- **Hash Chain Integrity**: Ensure continuous chain of entries
- **Retention Policies**: Enforce data retention requirements
- **Tamper Detection**: Identify and alert on tampering attempts
- **Query Integrity**: Ensure query results are authentic
- **Backup Integrity**: Validate backup files
- **Access Control**: Role-based audit log access
- **Forensic Analysis**: Pattern detection and investigation
- **Compliance Validation**: Meet regulatory requirements

## Running the Tests

### Run All Security Tests
```bash
python tests/security/run_security_tests.py
```

### Run with Verbose Output
```bash
python tests/security/run_security_tests.py --verbose
```

### Generate Test Report
```bash
python tests/security/run_security_tests.py --report security_report.json
```

### Validate Acceptance Criteria
```bash
python tests/security/run_security_tests.py --validate
```

### Run Individual Test Suites
```bash
# Ethics Engine Tests
python tests/security/ethics_tests.py

# Safety Monitor Tests
python tests/security/safety_tests.py

# Resource Limit Tests
python tests/security/resource_tests.py

# Audit Trail Tests
python tests/security/audit_tests.py
```

## Test Structure

Each test module contains:
1. **Unit Tests**: Test individual security components
2. **Integration Tests**: Test interaction between components
3. **Security-Specific Tests**: Focus on security vulnerabilities

## Acceptance Criteria Validation

The test suite validates all acceptance criteria for TASK-604:

1. ✅ **Ethics Engine Enforcement**: 10+ tests covering all aspects
2. ✅ **Safety Thresholds**: 10+ tests for monitoring and intervention
3. ✅ **Resource Limits**: 10+ tests for allocation and protection
4. ✅ **Audit Trail Integrity**: 10+ tests for immutability and compliance

## Test Results Interpretation

### Success Indicators
- All tests pass (100% success rate)
- No security vulnerabilities detected
- All acceptance criteria validated
- Integration between components verified

### Failure Investigation
If tests fail:
1. Check the specific test output for details
2. Review the component being tested
3. Verify test environment setup
4. Check for missing dependencies

## Security Best Practices

The tests validate:
- **Defense in Depth**: Multiple layers of security
- **Fail-Safe Defaults**: Deny by default approach
- **Least Privilege**: Minimal necessary permissions
- **Audit Everything**: Comprehensive logging
- **Tamper Evidence**: Detectable modifications
- **Recovery Capability**: Incident response procedures

## Integration with CI/CD

These tests should be run:
- On every commit (basic tests)
- On pull requests (full suite)
- Before releases (comprehensive validation)
- Periodically in production (monitoring)

## Dependencies

Required Python packages:
- unittest (standard library)
- asyncio (standard library)
- sqlite3 (standard library)
- hashlib (standard library)
- hmac (standard library)

Project components:
- `/control/ethics_engine.py`
- `/control/safety_monitor.py`
- `/control/resource_allocator.py`
- `/control/audit_logger.py`

## Maintenance

### Adding New Tests
1. Identify security concern
2. Create test in appropriate module
3. Follow existing test patterns
4. Update this README
5. Verify test passes

### Updating Tests
1. Modify test to reflect new requirements
2. Ensure backward compatibility
3. Update documentation
4. Run full test suite

## Contact

For questions or issues with security tests:
- Review test documentation
- Check component implementation
- Consult security requirements
- Report security vulnerabilities privately