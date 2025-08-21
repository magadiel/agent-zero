#!/usr/bin/env python3
"""
Basic API functionality test without external dependencies
"""

import sys
import os
import json
import asyncio
from datetime import datetime

# Add control module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from ethics_engine import EthicsEngine, DecisionType
    from safety_monitor import SafetyMonitor
    from resource_allocator import ResourceAllocator
    from audit_logger import AuditLogger, EventType, Severity
    print("✅ All control components imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_components():
    """Test basic functionality of control components"""
    
    print("\n" + "="*50)
    print("Testing Control Layer Components")
    print("="*50)
    
    # Test Ethics Engine
    print("\n1. Testing Ethics Engine...")
    try:
        ethics_engine = EthicsEngine()
        result = await ethics_engine.validate_decision(
            agent_id="test-agent",
            decision_type=DecisionType.DATA_PROCESSING,
            decision_data={
                "action": "process_data",
                "data_type": "public",
                "purpose": "analytics"
            }
        )
        print(f"   - Decision validation: {'✅ Approved' if result['approved'] else '❌ Rejected'}")
        print(f"   - Risk score: {result.get('risk_score', 0):.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Safety Monitor
    print("\n2. Testing Safety Monitor...")
    try:
        safety_monitor = SafetyMonitor()
        await safety_monitor.monitor_agent(
            agent_id="test-agent",
            metrics={
                "cpu_usage": 45.0,
                "memory_usage": 60.0,
                "response_time": 150.0
            }
        )
        status = safety_monitor.get_agent_status("test-agent")
        print(f"   - Agent monitoring: ✅")
        print(f"   - Status: {status.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Resource Allocator
    print("\n3. Testing Resource Allocator...")
    try:
        resource_allocator = ResourceAllocator()
        allocated = await resource_allocator.allocate_resources(
            team_id="test-team",
            resource_type="compute",
            amount=2.0,
            priority=3
        )
        print(f"   - Resource allocation: {'✅ Success' if allocated else '❌ Failed'}")
        if allocated:
            usage = resource_allocator.get_team_usage("test-team")
            print(f"   - Team usage: {usage}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Audit Logger
    print("\n4. Testing Audit Logger...")
    try:
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=EventType.SYSTEM,
            severity=Severity.INFO,
            component="TestScript",
            agent_id="test-agent",
            action="test_event",
            details={"test": True}
        )
        print(f"   - Event logging: ✅")
        
        logs = audit_logger.query_logs(limit=5)
        print(f"   - Query logs: {len(logs)} events found")
        
        stats = audit_logger.get_statistics()
        print(f"   - Total events: {stats.get('total_events', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_api_structure():
    """Test API structure and imports"""
    
    print("\n" + "="*50)
    print("Testing API Structure")
    print("="*50)
    
    # Test API imports
    print("\n5. Testing API module...")
    try:
        import api
        print("   - Main API module: ✅")
        
        # Check for required functions/classes
        required_items = [
            'app', 'Token', 'AgentDecision', 'ResourceRequest',
            'SafetyCheck', 'AuditQuery', 'get_current_user'
        ]
        
        for item in required_items:
            if hasattr(api, item):
                print(f"   - {item}: ✅")
            else:
                print(f"   - {item}: ❌ Missing")
                
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
    
    # Test API routes
    print("\n6. Testing API routes module...")
    try:
        import api_routes
        print("   - API routes module: ✅")
        
        # Check for routers
        routers = ['ethics_router', 'safety_router', 'resource_router', 'audit_router', 'admin_router']
        for router in routers:
            if hasattr(api_routes, router):
                print(f"   - {router}: ✅")
            else:
                print(f"   - {router}: ❌ Missing")
                
    except ImportError as e:
        print(f"   ❌ Import error: {e}")

def main():
    """Main test runner"""
    
    print("\n" + "="*50)
    print("Control Layer API - Basic Functionality Test")
    print("="*50)
    
    # Test component functionality
    print("\nRunning async component tests...")
    asyncio.run(test_components())
    
    # Test API structure
    test_api_structure()
    
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    print("\n✅ Basic functionality tests completed")
    print("Note: Full API testing requires FastAPI test client and pytest")
    print("which are not available in the current environment.")

if __name__ == "__main__":
    main()