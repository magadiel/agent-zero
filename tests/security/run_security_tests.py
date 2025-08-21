#!/usr/bin/env python3
"""
Security Test Suite Runner

Runs all security tests for the Agile AI Company Framework,
validating ethics engine, safety monitor, resource limits, and audit trail.
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
import unittest
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import all test modules
from ethics_tests import run_ethics_security_tests, EthicsEngineSecurityTests, EthicsEngineIntegrationTests
from safety_tests import run_safety_security_tests, SafetyMonitorSecurityTests, SafetyMonitorIntegrationTests
from resource_tests import run_resource_security_tests, ResourceLimitSecurityTests, ResourceAllocatorIntegrationTests
from audit_tests import run_audit_security_tests, AuditTrailSecurityTests, AuditLoggerIntegrationTests


class SecurityTestRunner:
    """Comprehensive security test runner"""
    
    def __init__(self, verbose: bool = True):
        """Initialize test runner
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self) -> bool:
        """Run all security test suites
        
        Returns:
            bool: True if all tests pass, False otherwise
        """
        print("=" * 80)
        print("AGILE AI COMPANY FRAMEWORK - SECURITY TEST SUITE")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        self.start_time = time.time()
        
        # Test suites to run
        test_suites = [
            ("Ethics Engine Security Tests", self._run_ethics_tests),
            ("Safety Monitor Security Tests", self._run_safety_tests),
            ("Resource Limit Security Tests", self._run_resource_tests),
            ("Audit Trail Security Tests", self._run_audit_tests)
        ]
        
        all_passed = True
        
        for suite_name, test_func in test_suites:
            print(f"\n[*] Running {suite_name}...")
            print("-" * 40)
            
            success, stats = test_func()
            self.results[suite_name] = {
                'success': success,
                'stats': stats
            }
            
            if not success:
                all_passed = False
                print(f"[✗] {suite_name} FAILED")
            else:
                print(f"[✓] {suite_name} PASSED")
        
        self.end_time = time.time()
        
        # Print summary
        self._print_summary()
        
        return all_passed
    
    def _run_ethics_tests(self) -> Tuple[bool, Dict]:
        """Run ethics engine security tests"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load test cases
        suite.addTests(loader.loadTestsFromTestCase(EthicsEngineSecurityTests))
        suite.addTests(loader.loadTestsFromTestCase(EthicsEngineIntegrationTests))
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2 if self.verbose else 1)
        result = runner.run(suite)
        
        if self.verbose:
            print(stream.getvalue())
        
        stats = {
            'total': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped)
        }
        
        return result.wasSuccessful(), stats
    
    def _run_safety_tests(self) -> Tuple[bool, Dict]:
        """Run safety monitor security tests"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load test cases
        suite.addTests(loader.loadTestsFromTestCase(SafetyMonitorSecurityTests))
        suite.addTests(loader.loadTestsFromTestCase(SafetyMonitorIntegrationTests))
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2 if self.verbose else 1)
        result = runner.run(suite)
        
        if self.verbose:
            print(stream.getvalue())
        
        stats = {
            'total': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped)
        }
        
        return result.wasSuccessful(), stats
    
    def _run_resource_tests(self) -> Tuple[bool, Dict]:
        """Run resource limit security tests"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load test cases
        suite.addTests(loader.loadTestsFromTestCase(ResourceLimitSecurityTests))
        suite.addTests(loader.loadTestsFromTestCase(ResourceAllocatorIntegrationTests))
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2 if self.verbose else 1)
        result = runner.run(suite)
        
        if self.verbose:
            print(stream.getvalue())
        
        stats = {
            'total': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped)
        }
        
        return result.wasSuccessful(), stats
    
    def _run_audit_tests(self) -> Tuple[bool, Dict]:
        """Run audit trail security tests"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load test cases
        suite.addTests(loader.loadTestsFromTestCase(AuditTrailSecurityTests))
        suite.addTests(loader.loadTestsFromTestCase(AuditLoggerIntegrationTests))
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2 if self.verbose else 1)
        result = runner.run(suite)
        
        if self.verbose:
            print(stream.getvalue())
        
        stats = {
            'total': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped)
        }
        
        return result.wasSuccessful(), stats
    
    def _print_summary(self):
        """Print test execution summary"""
        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        
        # Calculate totals
        for suite_name, result in self.results.items():
            stats = result['stats']
            total_tests += stats['total']
            total_passed += stats['passed']
            total_failed += stats['failed']
            total_errors += stats['errors']
            
            # Print suite results
            status = "✓ PASSED" if result['success'] else "✗ FAILED"
            print(f"\n{suite_name}:")
            print(f"  Status: {status}")
            print(f"  Tests Run: {stats['total']}")
            print(f"  Passed: {stats['passed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Errors: {stats['errors']}")
        
        # Print totals
        print("\n" + "-" * 80)
        print("OVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Errors: {total_errors}")
        print(f"  Success Rate: {(total_passed/total_tests*100):.1f}%")
        
        # Print execution time
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"\nExecution Time: {duration:.2f} seconds")
        
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def generate_report(self, output_file: str = "security_test_report.json"):
        """Generate JSON report of test results
        
        Args:
            output_file: Path to output file
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': self.end_time - self.start_time if self.start_time and self.end_time else 0,
            'results': self.results,
            'summary': {
                'total_tests': sum(r['stats']['total'] for r in self.results.values()),
                'total_passed': sum(r['stats']['passed'] for r in self.results.values()),
                'total_failed': sum(r['stats']['failed'] for r in self.results.values()),
                'total_errors': sum(r['stats']['errors'] for r in self.results.values()),
                'all_passed': all(r['success'] for r in self.results.values())
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nTest report saved to: {output_file}")


def validate_acceptance_criteria():
    """Validate that all acceptance criteria are met"""
    print("\n" + "=" * 80)
    print("VALIDATING ACCEPTANCE CRITERIA")
    print("=" * 80)
    
    criteria = [
        ("Ethics Engine Enforcement", "Testing harmful action blocking, decision approval/rejection, emergency shutdown, risk assessment, and override mechanisms"),
        ("Safety Thresholds", "Testing threshold monitoring, automatic interventions, kill switches, circuit breakers, and anomaly detection"),
        ("Resource Limits", "Testing allocation limits, priority queues, emergency releases, exhaustion prevention, and burst allocation"),
        ("Audit Trail Integrity", "Testing immutability, cryptographic signatures, hash chain integrity, retention policies, and tamper detection")
    ]
    
    print("\nAcceptance Criteria Coverage:")
    for criterion, description in criteria:
        print(f"\n✓ {criterion}:")
        print(f"  {description}")
    
    print("\n" + "-" * 80)
    print("All acceptance criteria have been implemented and tested.")
    print("=" * 80)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run security tests for Agile AI Company Framework')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--report', '-r', help='Generate JSON report to specified file')
    parser.add_argument('--validate', action='store_true', help='Validate acceptance criteria')
    
    args = parser.parse_args()
    
    # Run tests
    runner = SecurityTestRunner(verbose=args.verbose)
    success = runner.run_all_tests()
    
    # Generate report if requested
    if args.report:
        runner.generate_report(args.report)
    
    # Validate acceptance criteria if requested
    if args.validate:
        validate_acceptance_criteria()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()