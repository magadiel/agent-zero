#!/usr/bin/env python3
"""
Performance Test Runner for Agile AI Company Framework

This script runs the performance testing suite and validates that all
performance targets are met.

Author: Agile AI Framework Team
Date: 2025-08-21
Version: 1.0.0
"""

import asyncio
import sys
import os
from pathlib import Path
import argparse
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance import PerformanceBenchmark, LoadTestRunner


async def run_benchmark_tests(verbose: bool = True) -> bool:
    """Run performance benchmark tests"""
    print("\n" + "="*60)
    print("RUNNING PERFORMANCE BENCHMARKS")
    print("="*60 + "\n")
    
    benchmark = PerformanceBenchmark(verbose=verbose)
    
    try:
        # Run all benchmarks
        results = await benchmark.run_all_benchmarks()
        
        # Check critical performance targets
        critical_tests = {
            'Agent Spawn Time': 500,  # < 500ms
            'Communication Latency': 100,  # < 100ms
            'Decision Validation': 50  # < 50ms
        }
        
        all_passed = True
        for test_name, target in critical_tests.items():
            result = next((r for r in results if r and r.test_name == test_name), None)
            if result:
                if result.value > target:
                    print(f"✗ {test_name} failed: {result.value:.2f}ms > {target}ms target")
                    all_passed = False
                else:
                    print(f"✓ {test_name} passed: {result.value:.2f}ms < {target}ms target")
            else:
                print(f"⚠ {test_name} not found in results")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"✗ Benchmark tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_load_tests(quick: bool = True, verbose: bool = True) -> bool:
    """Run load tests"""
    print("\n" + "="*60)
    print("RUNNING LOAD TESTS")
    print("="*60 + "\n")
    
    runner = LoadTestRunner(verbose=verbose)
    
    try:
        # Run load tests
        results = await runner.run_all_tests(quick_mode=quick)
        
        # Check success rates
        if results:
            min_success_rate = 90.0  # Minimum acceptable success rate
            all_passed = True
            
            for result in results:
                if result.success_rate < min_success_rate:
                    print(f"✗ {result.test_name} success rate too low: {result.success_rate:.1f}% < {min_success_rate}%")
                    all_passed = False
                else:
                    print(f"✓ {result.test_name} success rate: {result.success_rate:.1f}%")
            
            return all_passed
        else:
            print("⚠ No load test results generated")
            return False
            
    except Exception as e:
        print(f"✗ Load tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Run performance tests for Agile AI Framework')
    parser.add_argument('--benchmark-only', action='store_true', help='Run only benchmark tests')
    parser.add_argument('--load-only', action='store_true', help='Run only load tests')
    parser.add_argument('--quick', action='store_true', help='Run quick validation tests')
    parser.add_argument('--quiet', action='store_true', help='Reduce output verbosity')
    args = parser.parse_args()
    
    print("="*60)
    print("AGILE AI COMPANY - PERFORMANCE TEST SUITE")
    print("="*60)
    print(f"Test Mode: {'Quick' if args.quick else 'Full'}")
    print(f"Verbosity: {'Quiet' if args.quiet else 'Verbose'}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    verbose = not args.quiet
    all_passed = True
    
    # Run benchmark tests
    if not args.load_only:
        benchmark_passed = await run_benchmark_tests(verbose=verbose)
        all_passed = all_passed and benchmark_passed
    
    # Run load tests
    if not args.benchmark_only:
        load_passed = await run_load_tests(quick=args.quick, verbose=verbose)
        all_passed = all_passed and load_passed
    
    # Final summary
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUITE SUMMARY")
    print("="*60)
    
    if all_passed:
        print("✓ ALL PERFORMANCE TESTS PASSED")
        print("✓ System meets all performance targets")
        return 0
    else:
        print("✗ SOME PERFORMANCE TESTS FAILED")
        print("✗ System does not meet all performance targets")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)