#!/usr/bin/env python3
"""
Container Communication Test Suite
Tests inter-container communication for the Agile AI multi-container system
"""

import requests
import time
import json
import subprocess
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    PASS = "✓"
    FAIL = "✗"
    INFO = "ℹ"
    WARN = "⚠"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    details: str = ""

class ContainerCommunicationTester:
    def __init__(self):
        self.results: List[TestResult] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_command(self, command: str) -> Tuple[int, str, str]:
        """Execute a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def add_result(self, result: TestResult):
        """Add a test result and update counters"""
        self.results.append(result)
        self.total_tests += 1
        
        if result.status == TestStatus.PASS:
            self.passed_tests += 1
            print(f"\033[92m{result.status.value}\033[0m {result.message}")
        elif result.status == TestStatus.FAIL:
            self.failed_tests += 1
            print(f"\033[91m{result.status.value}\033[0m {result.message}")
            if result.details:
                print(f"  Details: {result.details}")
        else:
            print(f"\033[93m{result.status.value}\033[0m {result.message}")
    
    def test_container_running(self, container_name: str) -> bool:
        """Test if a container is running"""
        code, stdout, stderr = self.run_command(
            f"docker ps --filter name={container_name} --format '{{{{.Names}}}}'"
        )
        
        is_running = container_name in stdout
        
        self.add_result(TestResult(
            name=f"Container {container_name}",
            status=TestStatus.PASS if is_running else TestStatus.FAIL,
            message=f"Container {container_name} {'is running' if is_running else 'is not running'}",
            details=stderr if stderr else ""
        ))
        
        return is_running
    
    def test_http_endpoint(self, url: str, expected_status: int = 200, 
                          description: str = None) -> bool:
        """Test HTTP endpoint accessibility"""
        description = description or f"HTTP endpoint {url}"
        
        try:
            response = requests.get(url, timeout=5)
            success = response.status_code == expected_status
            
            self.add_result(TestResult(
                name=description,
                status=TestStatus.PASS if success else TestStatus.FAIL,
                message=f"{description} - Status: {response.status_code}",
                details=f"Expected: {expected_status}, Got: {response.status_code}"
            ))
            
            return success
            
        except requests.exceptions.RequestException as e:
            self.add_result(TestResult(
                name=description,
                status=TestStatus.FAIL,
                message=f"{description} - Connection failed",
                details=str(e)
            ))
            return False
    
    def test_container_to_container(self, from_container: str, to_container: str, 
                                   to_port: int, path: str = "/health") -> bool:
        """Test communication between two containers"""
        command = f"docker exec {from_container} curl -s -f http://{to_container}:{to_port}{path}"
        code, stdout, stderr = self.run_command(command)
        
        success = code == 0
        
        self.add_result(TestResult(
            name=f"{from_container} → {to_container}",
            status=TestStatus.PASS if success else TestStatus.FAIL,
            message=f"Communication {from_container} → {to_container}:{to_port}",
            details=stderr if stderr else ""
        ))
        
        return success
    
    def test_redis_connectivity(self) -> bool:
        """Test Redis connectivity"""
        command = "docker exec agile-ai-redis redis-cli ping"
        code, stdout, stderr = self.run_command(command)
        
        success = "PONG" in stdout
        
        self.add_result(TestResult(
            name="Redis connectivity",
            status=TestStatus.PASS if success else TestStatus.FAIL,
            message="Redis connectivity test",
            details=f"Response: {stdout.strip()}" if stdout else stderr
        ))
        
        return success
    
    def test_postgres_connectivity(self) -> bool:
        """Test PostgreSQL connectivity"""
        command = "docker exec agile-ai-postgres pg_isready"
        code, stdout, stderr = self.run_command(command)
        
        success = "accepting connections" in stdout
        
        self.add_result(TestResult(
            name="PostgreSQL connectivity",
            status=TestStatus.PASS if success else TestStatus.FAIL,
            message="PostgreSQL connectivity test",
            details=f"Response: {stdout.strip()}" if stdout else stderr
        ))
        
        return success
    
    def test_network_membership(self, container: str, network: str, 
                               should_have: bool = True) -> bool:
        """Test if container is in the correct network"""
        command = f"docker inspect {container} --format='{{{{json .NetworkSettings.Networks}}}}'"
        code, stdout, stderr = self.run_command(command)
        
        if code != 0:
            self.add_result(TestResult(
                name=f"Network {network} for {container}",
                status=TestStatus.FAIL,
                message=f"Failed to inspect container {container}",
                details=stderr
            ))
            return False
        
        try:
            networks = json.loads(stdout)
            has_network = network in networks
            success = has_network == should_have
            
            self.add_result(TestResult(
                name=f"Network {network} for {container}",
                status=TestStatus.PASS if success else TestStatus.FAIL,
                message=f"{container} {'has' if has_network else 'does not have'} access to {network}",
                details=f"Expected: {should_have}, Got: {has_network}"
            ))
            
            return success
            
        except json.JSONDecodeError:
            self.add_result(TestResult(
                name=f"Network {network} for {container}",
                status=TestStatus.FAIL,
                message=f"Failed to parse network info for {container}",
                details=stdout
            ))
            return False
    
    def test_volume_exists(self, volume_name: str) -> bool:
        """Test if a volume exists"""
        command = f"docker volume ls --format '{{{{.Name}}}}' | grep -q {volume_name}"
        code, stdout, stderr = self.run_command(command)
        
        exists = code == 0
        
        self.add_result(TestResult(
            name=f"Volume {volume_name}",
            status=TestStatus.PASS if exists else TestStatus.FAIL,
            message=f"Volume {volume_name} {'exists' if exists else 'does not exist'}",
            details=stderr if stderr else ""
        ))
        
        return exists
    
    def run_all_tests(self):
        """Run all communication tests"""
        print("\n" + "="*60)
        print("Container Communication Test Suite")
        print("="*60 + "\n")
        
        # Test 1: Check if containers are running
        print("\n--- Testing Container Status ---")
        containers = [
            "agile-ai-control",
            "agile-ai-coordinator",
            "team-customer-agent-1",
            "team-customer-agent-2",
            "team-customer-agent-3",
            "team-operations-agent-1",
            "agile-ai-redis",
            "agile-ai-postgres"
        ]
        
        for container in containers:
            self.test_container_running(container)
        
        # Test 2: Check API endpoints
        print("\n--- Testing API Endpoints ---")
        endpoints = [
            ("http://localhost:8000/health", 200, "Control Layer API"),
            ("http://localhost:8001/health", 200, "Coordinator WebUI"),
            ("http://localhost:6379", 200, "Redis Port"),
        ]
        
        for url, status, desc in endpoints:
            self.test_http_endpoint(url, status, desc)
        
        # Test 3: Container-to-container communication
        print("\n--- Testing Inter-Container Communication ---")
        communications = [
            ("agile-ai-coordinator", "control-layer", 8000),
            ("team-customer-agent-1", "coordinator", 8002),
            ("team-operations-agent-1", "coordinator", 8002),
        ]
        
        for from_c, to_c, port in communications:
            self.test_container_to_container(from_c, to_c, port)
        
        # Test 4: Database connectivity
        print("\n--- Testing Database Connectivity ---")
        self.test_redis_connectivity()
        self.test_postgres_connectivity()
        
        # Test 5: Network isolation
        print("\n--- Testing Network Isolation ---")
        network_tests = [
            ("agile-ai-control", "control-network", True),
            ("agile-ai-control", "coordination-network", True),
            ("agile-ai-coordinator", "coordination-network", True),
            ("agile-ai-coordinator", "execution-network", True),
            ("team-customer-agent-1", "execution-network", True),
        ]
        
        for container, network, should_have in network_tests:
            self.test_network_membership(container, network, should_have)
        
        # Test 6: Volume persistence
        print("\n--- Testing Volume Persistence ---")
        volumes = [
            "control-storage",
            "coordinator-storage",
            "redis-data",
            "postgres-data",
            "shared-data"
        ]
        
        for volume in volumes:
            self.test_volume_exists(volume)
        
        # Print summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"\033[92mPassed:\033[0m {self.passed_tests}")
        print(f"\033[91mFailed:\033[0m {self.failed_tests}")
        print(f"Total:  {self.total_tests}")
        
        if self.failed_tests == 0:
            print("\n\033[92m✓ All tests passed successfully!\033[0m")
            return 0
        else:
            print(f"\n\033[91m✗ {self.failed_tests} test(s) failed.\033[0m")
            return 1

def main():
    """Main entry point"""
    tester = ContainerCommunicationTester()
    
    # Check if Docker is running
    code, stdout, stderr = tester.run_command("docker info")
    if code != 0:
        print("\033[91mError: Docker is not running or not accessible\033[0m")
        print(f"Details: {stderr}")
        return 1
    
    # Run all tests
    exit_code = tester.run_all_tests()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())