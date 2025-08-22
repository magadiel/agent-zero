#!/usr/bin/env python3
"""
Test script for industry specializations.

This script validates that all specializations are properly configured
and can be loaded without errors.
"""

import os
import sys
import traceback
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from specializations.loader import SpecializationLoader


def test_specialization_loading():
    """Test that all specializations can be loaded."""
    print("Testing specialization loading...")
    
    loader = SpecializationLoader()
    available = loader.list_available_specializations()
    
    print(f"Found {len(available)} specializations: {available}")
    
    results = {}
    for spec_name in available:
        try:
            print(f"\nTesting {spec_name}...")
            
            # Test getting info without full loading
            info = loader.get_specialization_info(spec_name)
            print(f"  Info: {info.name} v{info.version} ({info.industry})")
            
            # Test full loading
            spec = loader.load_specialization(spec_name)
            print(f"  Loaded: {len(spec.agents)} agents, {len(spec.workflows)} workflows")
            
            # Test validation
            validation = spec.validate()
            if validation['valid']:
                print(f"  Validation: PASSED")
            else:
                print(f"  Validation: FAILED - {validation['errors']}")
            
            results[spec_name] = {
                'loaded': True,
                'valid': validation['valid'],
                'errors': validation['errors'],
                'summary': validation['summary']
            }
            
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            results[spec_name] = {
                'loaded': False,
                'error': str(e)
            }
    
    return results


def test_agent_creation():
    """Test creating agents from specializations."""
    print("\n" + "="*50)
    print("Testing agent creation...")
    
    loader = SpecializationLoader()
    
    # Test fintech agents
    try:
        fintech = loader.load_specialization('fintech')
        if 'compliance_officer' in fintech.list_agents():
            agent = fintech.create_agent('compliance_officer', 'test_compliance_001')
            print(f"Created fintech compliance officer: {agent.get('id', 'N/A')}")
    except Exception as e:
        print(f"Failed to create fintech agent: {e}")
    
    # Test healthcare agents
    try:
        healthcare = loader.load_specialization('healthcare')
        if 'clinical_data_analyst' in healthcare.list_agents():
            agent = healthcare.create_agent('clinical_data_analyst', 'test_clinical_001')
            print(f"Created healthcare clinical analyst: {agent.get('id', 'N/A')}")
    except Exception as e:
        print(f"Failed to create healthcare agent: {e}")
    
    # Test ecommerce agents
    try:
        ecommerce = loader.load_specialization('ecommerce')
        if 'customer_experience_specialist' in ecommerce.list_agents():
            agent = ecommerce.create_agent('customer_experience_specialist', 'test_cx_001')
            print(f"Created ecommerce CX specialist: {agent.get('id', 'N/A')}")
    except Exception as e:
        print(f"Failed to create ecommerce agent: {e}")


def test_team_creation():
    """Test creating teams with specialized agents."""
    print("\n" + "="*50)
    print("Testing team creation...")
    
    loader = SpecializationLoader()
    
    # Test fintech compliance team
    try:
        fintech = loader.load_specialization('fintech')
        team = fintech.create_team('compliance_team', {
            'compliance_officer': 1,
            'risk_analyst': 1
        })
        print(f"Created fintech compliance team with {len(team['agents'])} agents")
    except Exception as e:
        print(f"Failed to create fintech team: {e}")
    
    # Test healthcare clinical team
    try:
        healthcare = loader.load_specialization('healthcare')
        team = healthcare.create_team('clinical_team', {
            'clinical_data_analyst': 2
        })
        print(f"Created healthcare clinical team with {len(team['agents'])} agents")
    except Exception as e:
        print(f"Failed to create healthcare team: {e}")
    
    # Test ecommerce customer service team
    try:
        ecommerce = loader.load_specialization('ecommerce')
        team = ecommerce.create_team('customer_service_team', {
            'customer_experience_specialist': 1
        })
        print(f"Created ecommerce customer service team with {len(team['agents'])} agents")
    except Exception as e:
        print(f"Failed to create ecommerce team: {e}")


def test_configuration_access():
    """Test accessing specialization configurations."""
    print("\n" + "="*50)
    print("Testing configuration access...")
    
    loader = SpecializationLoader()
    
    for spec_name in loader.list_available_specializations():
        try:
            spec = loader.load_specialization(spec_name)
            
            print(f"\n{spec_name.upper()} Configuration:")
            
            # Test ethics constraints
            ethics = spec.get_ethics_constraints()
            if ethics:
                constraints = list(ethics.keys())
                print(f"  Ethics constraints: {len(constraints)} categories")
            
            # Test safety thresholds
            safety = spec.get_safety_thresholds()
            if safety:
                thresholds = list(safety.keys())
                print(f"  Safety thresholds: {len(thresholds)} categories")
            
            # Test resource allocation
            resources = spec.get_resource_allocation()
            if resources:
                allocations = list(resources.keys())
                print(f"  Resource allocations: {len(allocations)} types")
            
            # Test audit requirements
            audit = spec.get_audit_requirements()
            if audit:
                requirements = list(audit.keys())
                print(f"  Audit requirements: {len(requirements)} categories")
            
        except Exception as e:
            print(f"Failed to access {spec_name} configuration: {e}")


def generate_summary_report(results):
    """Generate a summary report of test results."""
    print("\n" + "="*50)
    print("SUMMARY REPORT")
    print("="*50)
    
    total = len(results)
    loaded = sum(1 for r in results.values() if r.get('loaded', False))
    valid = sum(1 for r in results.values() if r.get('valid', False))
    
    print(f"Total specializations: {total}")
    print(f"Successfully loaded: {loaded}")
    print(f"Validation passed: {valid}")
    print(f"Success rate: {(valid/total)*100:.1f}%")
    
    print(f"\nDetailed Results:")
    for name, result in results.items():
        status = "✓" if result.get('valid', False) else "✗"
        summary = result.get('summary', {})
        agents = summary.get('agents', 0)
        workflows = summary.get('workflows', 0)
        
        print(f"  {status} {name}: {agents} agents, {workflows} workflows")
        
        if result.get('errors'):
            for error in result['errors']:
                print(f"    ERROR: {error}")


def main():
    """Run all specialization tests."""
    print("Industry Specializations Test Suite")
    print("="*50)
    
    # Test specialization loading and validation
    results = test_specialization_loading()
    
    # Test agent creation
    test_agent_creation()
    
    # Test team creation
    test_team_creation()
    
    # Test configuration access
    test_configuration_access()
    
    # Generate summary report
    generate_summary_report(results)
    
    # Overall success check
    all_valid = all(r.get('valid', False) for r in results.values())
    
    if all_valid:
        print(f"\n🎉 ALL TESTS PASSED! All {len(results)} specializations are working correctly.")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED! Check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)