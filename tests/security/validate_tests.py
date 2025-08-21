#!/usr/bin/env python3
"""
Security Test Validation Script

Validates that all security test files exist and contain the required test coverage
for TASK-604 acceptance criteria.
"""

import os
import sys
import re
from typing import Dict, List, Tuple


def check_file_exists(filepath: str) -> bool:
    """Check if a file exists"""
    return os.path.exists(filepath)


def count_test_methods(filepath: str) -> int:
    """Count test methods in a test file"""
    if not os.path.exists(filepath):
        return 0
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Count methods that start with 'def test_'
    test_methods = re.findall(r'def test_\w+\(self', content)
    return len(test_methods)


def analyze_test_coverage(filepath: str) -> Dict[str, bool]:
    """Analyze what the test file covers"""
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    coverage = {}
    
    # Check for specific test patterns
    patterns = {
        'constraint_validation': r'test.*constraint.*validation',
        'decision_approval': r'test.*decision.*approval|rejection',
        'emergency_shutdown': r'test.*emergency.*shutdown',
        'risk_assessment': r'test.*risk.*assessment',
        'override_mechanisms': r'test.*override.*mechanism',
        'threshold_monitoring': r'test.*threshold.*monitor',
        'automatic_interventions': r'test.*automatic.*intervention',
        'kill_switches': r'test.*kill.*switch',
        'circuit_breakers': r'test.*circuit.*breaker',
        'anomaly_detection': r'test.*anomaly.*detection',
        'allocation_limits': r'test.*allocation.*limit',
        'priority_queues': r'test.*priority.*queue',
        'emergency_releases': r'test.*emergency.*release',
        'resource_exhaustion': r'test.*resource.*exhaustion',
        'burst_allocation': r'test.*burst.*allocation',
        'immutability': r'test.*immutability|immutable',
        'cryptographic_signatures': r'test.*cryptographic.*signature',
        'hash_chain': r'test.*hash.*chain',
        'retention_policies': r'test.*retention.*polic',
        'tamper_detection': r'test.*tamper.*detection'
    }
    
    for name, pattern in patterns.items():
        coverage[name] = bool(re.search(pattern, content, re.IGNORECASE))
    
    return coverage


def main():
    """Main validation function"""
    print("=" * 80)
    print("SECURITY TEST VALIDATION - TASK-604")
    print("=" * 80)
    
    # Define test files and their requirements
    test_files = {
        'ethics_tests.py': {
            'path': 'tests/security/ethics_tests.py',
            'min_tests': 10,
            'required_coverage': [
                'constraint_validation',
                'decision_approval',
                'emergency_shutdown',
                'risk_assessment',
                'override_mechanisms'
            ]
        },
        'safety_tests.py': {
            'path': 'tests/security/safety_tests.py',
            'min_tests': 10,
            'required_coverage': [
                'threshold_monitoring',
                'automatic_interventions',
                'kill_switches',
                'circuit_breakers',
                'anomaly_detection'
            ]
        },
        'resource_tests.py': {
            'path': 'tests/security/resource_tests.py',
            'min_tests': 10,
            'required_coverage': [
                'allocation_limits',
                'priority_queues',
                'emergency_releases',
                'resource_exhaustion',
                'burst_allocation'
            ]
        },
        'audit_tests.py': {
            'path': 'tests/security/audit_tests.py',
            'min_tests': 10,
            'required_coverage': [
                'immutability',
                'cryptographic_signatures',
                'hash_chain',
                'retention_policies',
                'tamper_detection'
            ]
        }
    }
    
    # Additional files to check
    additional_files = [
        'tests/security/__init__.py',
        'tests/security/run_security_tests.py',
        'tests/security/README.md'
    ]
    
    all_valid = True
    
    # Check each test file
    print("\n[1] CHECKING TEST FILES")
    print("-" * 40)
    
    for name, requirements in test_files.items():
        filepath = requirements['path']
        exists = check_file_exists(filepath)
        
        if exists:
            test_count = count_test_methods(filepath)
            coverage = analyze_test_coverage(filepath)
            
            print(f"\n✓ {name}")
            print(f"  Location: {filepath}")
            print(f"  Test Methods: {test_count} (required: {requirements['min_tests']})")
            
            # Check coverage
            print(f"  Coverage:")
            for req in requirements['required_coverage']:
                if coverage.get(req, False):
                    print(f"    ✓ {req}")
                else:
                    print(f"    ✗ {req} (MISSING)")
                    all_valid = False
            
            if test_count < requirements['min_tests']:
                print(f"  ⚠ WARNING: Insufficient test methods")
                all_valid = False
        else:
            print(f"\n✗ {name} - FILE NOT FOUND")
            all_valid = False
    
    # Check additional files
    print("\n[2] CHECKING ADDITIONAL FILES")
    print("-" * 40)
    
    for filepath in additional_files:
        if check_file_exists(filepath):
            print(f"✓ {filepath}")
        else:
            print(f"✗ {filepath} - NOT FOUND")
            all_valid = False
    
    # Check acceptance criteria
    print("\n[3] ACCEPTANCE CRITERIA VALIDATION")
    print("-" * 40)
    
    criteria = [
        ("Ethics Engine Enforcement", "ethics_tests.py"),
        ("Safety Thresholds", "safety_tests.py"),
        ("Resource Limits", "resource_tests.py"),
        ("Audit Trail Integrity", "audit_tests.py")
    ]
    
    print("\nAcceptance Criteria Coverage:")
    for criterion, test_file in criteria:
        filepath = f"tests/security/{test_file}"
        if check_file_exists(filepath):
            test_count = count_test_methods(filepath)
            if test_count >= 10:
                print(f"✓ {criterion}: {test_count} tests implemented")
            else:
                print(f"⚠ {criterion}: Only {test_count} tests (10 required)")
        else:
            print(f"✗ {criterion}: Test file missing")
    
    # Final summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if all_valid:
        print("\n✓ ALL VALIDATION CHECKS PASSED")
        print("  - All test files present")
        print("  - All acceptance criteria covered")
        print("  - Minimum test requirements met")
        print("\nTASK-604 Security Testing is COMPLETE")
    else:
        print("\n✗ VALIDATION FAILED")
        print("  Some test coverage is missing or incomplete")
        print("  Review the output above for details")
    
    print("=" * 80)
    
    return 0 if all_valid else 1


if __name__ == '__main__':
    sys.exit(main())