"""
Unit tests for Control Layer API
"""

import sys
import os
import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app, create_access_token
from ethics_engine import DecisionType
from safety_monitor import ThreatType, InterventionType
from audit_logger import EventType, EventSeverity


# Test client
client = TestClient(app)


# Helper function to get auth headers
def get_auth_headers():
    """Get authentication headers for testing"""
    access_token = create_access_token(data={"sub": "admin"})
    return {"Authorization": f"Bearer {access_token}"}


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "documentation" in data
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded"]


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login"""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "secret"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_failure(self):
        """Test failed login with wrong credentials"""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 401
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        response = client.post(
            "/ethics/validate",
            json={
                "agent_id": "test-agent",
                "decision_type": "data_processing",
                "decision_data": {}
            }
        )
        assert response.status_code == 403  # Forbidden without auth


class TestEthicsEndpoints:
    """Test ethics validation endpoints"""
    
    def test_validate_decision_approved(self):
        """Test ethics validation for approved decision"""
        headers = get_auth_headers()
        response = client.post(
            "/ethics/validate",
            headers=headers,
            json={
                "agent_id": "test-agent",
                "decision_type": "data_processing",
                "decision_data": {
                    "action": "process_public_data",
                    "data_type": "public",
                    "purpose": "analytics"
                },
                "context": {}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "approved" in data
        assert "risk_score" in data
    
    def test_validate_decision_rejected(self):
        """Test ethics validation for rejected decision"""
        headers = get_auth_headers()
        response = client.post(
            "/ethics/validate",
            headers=headers,
            json={
                "agent_id": "test-agent",
                "decision_type": "data_processing",
                "decision_data": {
                    "action": "process_private_data",
                    "data_type": "private",
                    "consent": False
                },
                "context": {}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "approved" in data
        assert "reasons" in data
    
    def test_validate_decision_invalid_type(self):
        """Test ethics validation with invalid decision type"""
        headers = get_auth_headers()
        response = client.post(
            "/ethics/validate",
            headers=headers,
            json={
                "agent_id": "test-agent",
                "decision_type": "invalid_type",
                "decision_data": {},
                "context": {}
            }
        )
        assert response.status_code == 422  # Validation error


class TestSafetyEndpoints:
    """Test safety monitoring endpoints"""
    
    def test_safety_check(self):
        """Test safety check endpoint"""
        headers = get_auth_headers()
        response = client.post(
            "/safety/check",
            headers=headers,
            json={
                "agent_id": "test-agent",
                "metrics": {
                    "cpu_usage": 45.0,
                    "memory_usage": 60.0,
                    "response_time": 150.0
                },
                "check_type": "standard"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert "status" in data
        assert "violations" in data
        assert "timestamp" in data
    
    def test_emergency_stop(self):
        """Test emergency stop endpoint"""
        headers = get_auth_headers()
        response = client.post(
            "/safety/emergency-stop/test-agent",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert "stopped" in data


class TestResourceEndpoints:
    """Test resource allocation endpoints"""
    
    def test_allocate_resources(self):
        """Test resource allocation"""
        headers = get_auth_headers()
        response = client.post(
            "/resources/allocate",
            headers=headers,
            json={
                "team_id": "team-1",
                "resource_type": "compute",
                "amount": 2.0,
                "priority": 3,
                "duration": 3600
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "team-1"
        assert "allocated" in data
        assert data["resource_type"] == "compute"
    
    def test_release_resources(self):
        """Test resource release"""
        headers = get_auth_headers()
        
        # First allocate resources
        client.post(
            "/resources/allocate",
            headers=headers,
            json={
                "team_id": "team-2",
                "resource_type": "memory",
                "amount": 4.0,
                "priority": 3,
                "duration": 3600
            }
        )
        
        # Then release them
        response = client.delete(
            "/resources/release/team-2",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "team-2"
        assert "released" in data
    
    def test_get_resource_usage(self):
        """Test getting resource usage"""
        headers = get_auth_headers()
        
        # First allocate resources
        client.post(
            "/resources/allocate",
            headers=headers,
            json={
                "team_id": "team-3",
                "resource_type": "storage",
                "amount": 100.0,
                "priority": 2,
                "duration": 7200
            }
        )
        
        # Get usage
        response = client.get(
            "/resources/usage/team-3",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "storage" in data
    
    def test_get_available_resources(self):
        """Test getting available resources"""
        headers = get_auth_headers()
        response = client.get(
            "/resources/available",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should have at least default pool
        assert len(data) > 0


class TestAuditEndpoints:
    """Test audit logging endpoints"""
    
    def test_query_audit_logs(self):
        """Test querying audit logs"""
        headers = get_auth_headers()
        response = client.get(
            "/audit/logs",
            headers=headers,
            params={
                "limit": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)
    
    def test_query_audit_logs_with_filters(self):
        """Test querying audit logs with filters"""
        headers = get_auth_headers()
        response = client.get(
            "/audit/logs",
            headers=headers,
            params={
                "agent_id": "test-agent",
                "event_type": "ethics",
                "severity": "info",
                "limit": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "logs" in data
    
    def test_get_audit_stats(self):
        """Test getting audit statistics"""
        headers = get_auth_headers()
        response = client.get(
            "/audit/stats",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
    
    def test_export_audit_logs(self):
        """Test exporting audit logs"""
        headers = get_auth_headers()
        response = client.post(
            "/audit/export",
            headers=headers,
            params={
                "format": "json"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "filepath" in data
        assert data["format"] == "json"


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_endpoint(self):
        """Test accessing invalid endpoint"""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404
    
    def test_invalid_json_payload(self):
        """Test sending invalid JSON"""
        headers = get_auth_headers()
        response = client.post(
            "/ethics/validate",
            headers=headers,
            content="invalid json",
            headers_extra={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self):
        """Test missing required fields"""
        headers = get_auth_headers()
        response = client.post(
            "/ethics/validate",
            headers=headers,
            json={
                "agent_id": "test-agent"
                # Missing decision_type and decision_data
            }
        )
        assert response.status_code == 422


class TestConcurrency:
    """Test concurrent API requests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_allocations(self):
        """Test concurrent resource allocations"""
        headers = get_auth_headers()
        
        async def allocate_resources(team_id: str):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/resources/allocate",
                    headers=headers,
                    json={
                        "team_id": team_id,
                        "resource_type": "compute",
                        "amount": 1.0,
                        "priority": 3,
                        "duration": 3600
                    }
                )
                return response.status_code == 200
        
        # Create multiple concurrent allocation requests
        tasks = [allocate_resources(f"team-concurrent-{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Most should succeed (depends on available resources)
        assert sum(results) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_validations(self):
        """Test concurrent ethics validations"""
        headers = get_auth_headers()
        
        async def validate_decision(agent_id: str):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/ethics/validate",
                    headers=headers,
                    json={
                        "agent_id": agent_id,
                        "decision_type": "data_processing",
                        "decision_data": {"action": "process"},
                        "context": {}
                    }
                )
                return response.status_code == 200
        
        # Create multiple concurrent validation requests
        tasks = [validate_decision(f"agent-concurrent-{i}") for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)


class TestIntegration:
    """Integration tests across multiple endpoints"""
    
    def test_complete_workflow(self):
        """Test complete workflow: allocate, monitor, validate, release"""
        headers = get_auth_headers()
        team_id = "integration-team"
        
        # 1. Allocate resources
        response = client.post(
            "/resources/allocate",
            headers=headers,
            json={
                "team_id": team_id,
                "resource_type": "compute",
                "amount": 4.0,
                "priority": 2,
                "duration": 3600
            }
        )
        assert response.status_code == 200
        
        # 2. Perform safety check
        response = client.post(
            "/safety/check",
            headers=headers,
            json={
                "agent_id": f"{team_id}-agent",
                "metrics": {
                    "cpu_usage": 75.0,
                    "memory_usage": 80.0,
                    "response_time": 200.0
                },
                "check_type": "standard"
            }
        )
        assert response.status_code == 200
        
        # 3. Validate a decision
        response = client.post(
            "/ethics/validate",
            headers=headers,
            json={
                "agent_id": f"{team_id}-agent",
                "decision_type": "resource_allocation",
                "decision_data": {
                    "action": "scale_up",
                    "reason": "increased_load"
                },
                "context": {"team_id": team_id}
            }
        )
        assert response.status_code == 200
        
        # 4. Query audit logs for this team
        response = client.get(
            "/audit/logs",
            headers=headers,
            params={
                "agent_id": f"{team_id}-agent",
                "limit": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        
        # 5. Release resources
        response = client.delete(
            f"/resources/release/{team_id}",
            headers=headers
        )
        assert response.status_code == 200


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])