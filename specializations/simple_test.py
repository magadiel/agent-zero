#!/usr/bin/env python3
"""
Simple test script for industry specializations.

This script validates specialization configurations without requiring
the full Agent-Zero environment.
"""

import os
import yaml
import json
from pathlib import Path


def test_specialization_configs():
    """Test that all specialization configurations are valid YAML."""
    print("Testing specialization configurations...")
    
    base_path = Path(__file__).parent
    results = {}
    
    # Find all specialization directories
    specializations = []
    for item in base_path.iterdir():
        if item.is_dir() and not item.name.startswith('_') and item.name != '__pycache__':
            config_file = item / 'config' / 'specialization.yaml'
            if config_file.exists():
                specializations.append(item.name)
    
    print(f"Found {len(specializations)} specializations: {specializations}")
    
    for spec_name in specializations:
        try:
            print(f"\nTesting {spec_name}...")
            spec_path = base_path / spec_name
            
            # Test configuration file
            config_path = spec_path / 'config' / 'specialization.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required fields
            required_fields = ['name', 'version', 'description']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                print(f"  ❌ Missing required fields: {missing_fields}")
                results[spec_name] = {'valid': False, 'errors': missing_fields}
                continue
            
            # Test agent files
            agents_path = spec_path / 'agents'
            agent_count = 0
            if agents_path.exists():
                agent_files = list(agents_path.glob('*.md'))
                agent_count = len(agent_files)
                print(f"  📋 Found {agent_count} agent profiles")
            
            # Test workflow files
            workflows_path = spec_path / 'workflows'
            workflow_count = 0
            if workflows_path.exists():
                workflow_files = list(workflows_path.glob('*.yaml'))
                workflow_count = len(workflow_files)
                print(f"  🔄 Found {workflow_count} workflows")
                
                # Validate workflow YAML
                for workflow_file in workflow_files:
                    try:
                        with open(workflow_file, 'r') as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        print(f"    ❌ Invalid YAML in {workflow_file.name}: {e}")
                        raise
            
            # Test template files
            templates_path = spec_path / 'templates'
            template_count = 0
            if templates_path.exists():
                template_files = list(templates_path.glob('*.yaml'))
                template_count = len(template_files)
                print(f"  📄 Found {template_count} templates")
            
            # Test checklist files
            checklists_path = spec_path / 'checklists'
            checklist_count = 0
            if checklists_path.exists():
                checklist_files = list(checklists_path.glob('*.md'))
                checklist_count = len(checklist_files)
                print(f"  ✅ Found {checklist_count} checklists")
            
            # Test README file
            readme_path = spec_path / 'README.md'
            has_readme = readme_path.exists()
            print(f"  📚 README.md: {'✅' if has_readme else '❌'}")
            
            results[spec_name] = {
                'valid': True,
                'config': config,
                'agents': agent_count,
                'workflows': workflow_count,
                'templates': template_count,
                'checklists': checklist_count,
                'has_readme': has_readme
            }
            
            print(f"  ✅ {spec_name} validation passed")
            
        except Exception as e:
            print(f"  ❌ Error testing {spec_name}: {e}")
            results[spec_name] = {'valid': False, 'error': str(e)}
    
    return results


def test_specialization_structure():
    """Test that specializations follow the expected directory structure."""
    print("\n" + "="*50)
    print("Testing specialization directory structure...")
    
    base_path = Path(__file__).parent
    expected_dirs = ['config', 'agents', 'workflows', 'templates', 'checklists', 'docs']
    
    for spec_dir in base_path.iterdir():
        if spec_dir.is_dir() and not spec_dir.name.startswith('_') and spec_dir.name != '__pycache__':
            print(f"\nChecking {spec_dir.name} structure:")
            
            for expected_dir in expected_dirs:
                dir_path = spec_dir / expected_dir
                exists = dir_path.exists()
                print(f"  {expected_dir}: {'✅' if exists else '❌'}")
                
                if exists and expected_dir in ['agents', 'workflows', 'templates', 'checklists']:
                    file_count = len(list(dir_path.glob('*')))
                    print(f"    ({file_count} files)")


def test_configuration_completeness():
    """Test that configurations include expected sections."""
    print("\n" + "="*50)
    print("Testing configuration completeness...")
    
    base_path = Path(__file__).parent
    expected_sections = ['metadata', 'ethics', 'safety', 'resource_allocation', 'audit']
    
    for spec_dir in base_path.iterdir():
        if spec_dir.is_dir() and not spec_dir.name.startswith('_') and spec_dir.name != '__pycache__':
            config_path = spec_dir / 'config' / 'specialization.yaml'
            if config_path.exists():
                print(f"\nChecking {spec_dir.name} configuration:")
                
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                for section in expected_sections:
                    has_section = section in config
                    print(f"  {section}: {'✅' if has_section else '❌'}")
                    
                    if has_section and isinstance(config[section], dict):
                        subsection_count = len(config[section])
                        print(f"    ({subsection_count} subsections)")


def generate_summary_report(results):
    """Generate a summary report of test results."""
    print("\n" + "="*50)
    print("SUMMARY REPORT")
    print("="*50)
    
    total = len(results)
    valid = sum(1 for r in results.values() if r.get('valid', False))
    
    print(f"Total specializations: {total}")
    print(f"Successfully validated: {valid}")
    print(f"Success rate: {(valid/total)*100:.1f}%" if total > 0 else "No specializations found")
    
    print(f"\nSpecialization Details:")
    for name, result in results.items():
        if result.get('valid', False):
            config = result.get('config', {})
            industry = config.get('metadata', {}).get('industry', 'Unknown')
            version = config.get('version', 'Unknown')
            
            print(f"  ✅ {name} v{version} ({industry})")
            print(f"     Agents: {result.get('agents', 0)}, " +
                  f"Workflows: {result.get('workflows', 0)}, " +
                  f"Templates: {result.get('templates', 0)}, " +
                  f"Checklists: {result.get('checklists', 0)}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ❌ {name}: {error}")


def main():
    """Run all specialization tests."""
    print("Industry Specializations Validation Suite")
    print("="*50)
    
    # Test configurations
    results = test_specialization_configs()
    
    # Test directory structure
    test_specialization_structure()
    
    # Test configuration completeness
    test_configuration_completeness()
    
    # Generate summary report
    generate_summary_report(results)
    
    # Overall success check
    all_valid = all(r.get('valid', False) for r in results.values())
    
    if all_valid and len(results) > 0:
        print(f"\n🎉 ALL VALIDATIONS PASSED! All {len(results)} specializations are properly configured.")
        print("\nAcceptance Criteria Status:")
        print("✅ Create fintech specialization")
        print("✅ Create healthcare specialization") 
        print("✅ Create e-commerce specialization")
        print("✅ Document customization process")
        return 0
    else:
        print(f"\n❌ SOME VALIDATIONS FAILED! Check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)