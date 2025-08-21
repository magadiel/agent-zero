"""
Performance Testing Suite for Agile AI Company Framework

This package provides comprehensive performance and load testing capabilities
for validating system performance, scalability, and resource limits.

Modules:
- benchmark: Performance benchmarks for key metrics
- load_tests: Load and stress testing under high concurrency

Author: Agile AI Framework Team
Date: 2025-08-21
Version: 1.0.0
"""

from .benchmark import PerformanceBenchmark, BenchmarkResult
from .load_tests import LoadTestRunner, LoadTestResult

__all__ = [
    'PerformanceBenchmark',
    'BenchmarkResult',
    'LoadTestRunner',
    'LoadTestResult'
]

__version__ = '1.0.0'