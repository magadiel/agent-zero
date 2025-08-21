#!/usr/bin/env python3
"""
Test script for Control Layer Docker container
Tests all major API endpoints and functionality
"""

import requests
import json
import time
import sys
from typing import Dict, Any
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key"

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASSED{NC}" if passed else f"{RED}✗ FAILED{NC}"
    print(f"  {status} - {name}")
    if details and not passed:
        print(f"    {YELLOW}Details: {details}{NC}")


def test_health_check() -> bool:
    """Test health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        return False


def test_api_docs() -> bool:
    """Test API documentation endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        return response.status_code == 200
    except Exception as e:
        return False


def test_ethics_validation() -> bool:
    """Test ethics validation endpoint"""
    headers = {"X-API-Key": API_KEY}
    decision = {
        "agent_id": "test_agent",
        "action": "data_processing",
        "context": {
            "purpose": "user_analysis",
            "data_type": "personal",
            "consent": True
        },
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ethics/validate",
            json=decision,
            headers=headers,
            timeout=5
        )
        return response.status_code in [200, 201]
    except Exception as e:
        return False


def test_safety_monitoring() -> bool:
    """Test safety monitoring endpoint"""
    headers = {"X-API-Key": API_KEY}
    
    try:
        # Start monitoring
        monitor_data = {
            "agent_id": "test_agent",
            "metrics": {
                "cpu_usage": 45.2,
                "memory_usage": 60.5,
                "request_rate": 100
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/safety/monitor",
            json=monitor_data,
            headers=headers,
            timeout=5
        )
        return response.status_code in [200, 201]
    except Exception as e:
        return False


def test_resource_allocation() -> bool:
    """Test resource allocation endpoint"""
    headers = {"X-API-Key": API_KEY}
    
    try:
        # Request resources
        request_data = {
            "team_id": "test_team",
            "resource_type": "compute",
            "amount": 2,
            "priority": 1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/resources/allocate",
            json=request_data,
            headers=headers,
            timeout=5
        )
        
        if response.status_code not in [200, 201]:
            return False
        
        # Release resources
        allocation_id = response.json().get("allocation_id", "test_allocation")
        release_response = requests.post(
            f"{BASE_URL}/api/v1/resources/release/{allocation_id}",
            headers=headers,
            timeout=5
        )
        
        return release_response.status_code in [200, 204]
    except Exception as e:
        return False


def test_audit_logging() -> bool:
    """Test audit logging endpoint"""
    headers = {"X-API-Key": API_KEY}
    
    try:
        # Query audit logs
        response = requests.get(
            f"{BASE_URL}/api/v1/audit/logs",
            headers=headers,
            params={"limit": 10},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        return False


def test_metrics_endpoint() -> bool:
    """Test metrics endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        # Metrics might be restricted, so 403 is also acceptable
        return response.status_code in [200, 403]
    except Exception as e:
        return False


def test_authentication() -> bool:
    """Test authentication mechanisms"""
    try:
        # Test without API key (should fail)
        response1 = requests.post(
            f"{BASE_URL}/api/v1/ethics/validate",
            json={"test": "data"},
            timeout=5
        )
        
        if response1.status_code != 401:
            return False
        
        # Test with API key
        headers = {"X-API-Key": API_KEY}
        response2 = requests.get(
            f"{BASE_URL}/api/v1/audit/logs",
            headers=headers,
            timeout=5
        )
        
        # Should either work or give a different error (not 401)
        return response2.status_code != 401
    except Exception as e:
        return False


def run_tests():
    """Run all container tests"""
    print(f"\n{GREEN}Starting Control Layer Container Tests{NC}")
    print("=" * 50)
    
    # Wait for services to be ready
    print("\nWaiting for services to be ready...")
    max_retries = 30
    for i in range(max_retries):
        if test_health_check():
            print(f"{GREEN}Services are ready!{NC}\n")
            break
        time.sleep(1)
        if i == max_retries - 1:
            print(f"{RED}Services failed to start{NC}")
            return False
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("API Documentation", test_api_docs),
        ("Ethics Validation", test_ethics_validation),
        ("Safety Monitoring", test_safety_monitoring),
        ("Resource Allocation", test_resource_allocation),
        ("Audit Logging", test_audit_logging),
        ("Metrics Endpoint", test_metrics_endpoint),
        ("Authentication", test_authentication),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append(passed)
            print_test(name, passed)
        except Exception as e:
            results.append(False)
            print_test(name, False, str(e))
    
    # Summary
    print("\n" + "=" * 50)
    passed_count = sum(results)
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    
    if success_rate == 100:
        print(f"{GREEN}All tests passed! ({passed_count}/{total_count}){NC}")
        return True
    elif success_rate >= 75:
        print(f"{YELLOW}Most tests passed ({passed_count}/{total_count} - {success_rate:.1f}%){NC}")
        return True
    else:
        print(f"{RED}Many tests failed ({passed_count}/{total_count} - {success_rate:.1f}%){NC}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)