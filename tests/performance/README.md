# Performance Testing Suite

## Overview

The Performance Testing Suite provides comprehensive benchmarking and load testing capabilities for the Agile AI Company framework. It validates that the system meets critical performance targets and can handle production-level loads.

## Test Categories

### 1. Performance Benchmarks (`benchmark.py`)

Tests key system metrics against defined targets:

- **Agent Spawn Time**: Target < 500ms
- **Communication Latency**: Target < 100ms  
- **Decision Validation**: Target < 50ms
- **Resource Allocation**: Target < 100ms
- **Concurrent Team Operations**: Validates parallelism
- **Workflow Execution**: Measures end-to-end performance
- **Memory Usage**: Tracks resource consumption

### 2. Load Tests (`load_tests.py`)

Validates system behavior under stress:

- **Agent Spawn Load**: Tests rapid agent creation
- **Concurrent Teams**: Tests multiple team operations
- **Workflow Execution Load**: Tests workflow throughput
- **Decision Validation Stress**: Tests ethics engine under load
- **Resource Limits**: Tests behavior at resource boundaries
- **Sustained Load**: Tests stability over time

## Usage

### Quick Validation

Run quick performance validation (reduced test scope):

```bash
python tests/performance/run_performance_tests.py --quick
```

### Full Test Suite

Run comprehensive performance tests:

```bash
python tests/performance/run_performance_tests.py
```

### Benchmark Tests Only

```bash
python tests/performance/run_performance_tests.py --benchmark-only
```

### Load Tests Only

```bash
python tests/performance/run_performance_tests.py --load-only
```

### Quiet Mode

Reduce output verbosity:

```bash
python tests/performance/run_performance_tests.py --quiet
```

## Test Results

### Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Agent Spawn Time | < 500ms | Time to create and initialize an agent |
| Communication Latency | < 100ms | Inter-agent message passing time |
| Decision Validation | < 50ms | Ethics engine decision processing |
| Resource Allocation | < 100ms | Time to allocate team resources |
| Success Rate | > 95% | Percentage of successful operations |

### Output Files

Tests generate the following reports:

- `performance_report_YYYYMMDD_HHMMSS.json` - Detailed benchmark results
- `load_test_report_YYYYMMDD_HHMMSS.json` - Load test statistics

### Report Structure

```json
{
  "timestamp": "2025-08-21T10:30:00",
  "summary": {
    "total_tests": 7,
    "passed": 7,
    "failed": 0,
    "pass_rate": 100.0
  },
  "results": [
    {
      "test_name": "Agent Spawn Time",
      "metric": "average_spawn_time",
      "value": 245.3,
      "unit": "ms",
      "target": 500,
      "passed": true,
      "samples": [...],
      "metadata": {...}
    }
  ]
}
```

## Interpreting Results

### Success Indicators

- ✓ All critical performance targets met
- ✓ Success rate > 95% for all operations
- ✓ Stable resource usage under sustained load
- ✓ P99 latency within acceptable bounds

### Warning Signs

- ⚠ P95/P99 latency spikes
- ⚠ Memory usage growth over time
- ⚠ Success rate between 90-95%
- ⚠ Resource exhaustion under expected load

### Failure Conditions

- ✗ Critical performance targets not met
- ✗ Success rate < 90%
- ✗ System crashes or hangs
- ✗ Memory leaks detected

## Performance Optimization Tips

### If Agent Spawn Time is High

1. Review agent initialization code
2. Optimize profile loading
3. Consider lazy loading of dependencies
4. Use agent pooling for reuse

### If Communication Latency is High

1. Check network configuration
2. Optimize message serialization
3. Consider batching messages
4. Review async implementation

### If Decision Validation is Slow

1. Optimize ethics engine rules
2. Cache frequent decisions
3. Parallelize validation where possible
4. Review constraint complexity

### If Load Tests Fail

1. Increase resource limits
2. Optimize concurrent operations
3. Implement better queuing
4. Add circuit breakers

## Advanced Usage

### Custom Performance Tests

Create custom benchmarks by extending the base classes:

```python
from tests.performance import PerformanceBenchmark

class CustomBenchmark(PerformanceBenchmark):
    async def test_custom_metric(self):
        # Your test implementation
        result = BenchmarkResult(
            test_name="Custom Test",
            metric="custom_metric",
            value=123.4,
            unit="ms",
            target=200
        )
        self.results.append(result)
        return result
```

### Integration with CI/CD

Add to your CI pipeline:

```yaml
- name: Run Performance Tests
  run: |
    python tests/performance/run_performance_tests.py --quick
    if [ $? -ne 0 ]; then
      echo "Performance tests failed"
      exit 1
    fi
```

## Troubleshooting

### Import Errors

If components are not found:
1. Ensure all dependencies are installed
2. Check PYTHONPATH includes project root
3. Verify component implementations exist

### Resource Errors

If tests fail due to resources:
1. Check system has sufficient memory
2. Ensure no other processes are consuming resources
3. Consider running with `--quick` flag

### Timeout Errors

If tests timeout:
1. Increase timeout values in test configuration
2. Check for deadlocks in async code
3. Review system resource availability

## Contributing

When adding new performance tests:

1. Define clear performance targets
2. Include multiple samples for statistical validity
3. Add metadata for debugging
4. Document expected values
5. Update this README

## Contact

For issues or questions about performance testing, please refer to the main project documentation or create an issue in the project repository.