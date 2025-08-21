#!/usr/bin/env python3
"""
Product Development Demo Validator
Validates that demo outputs meet acceptance criteria
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class DemoValidator:
    """Validates product development demo outputs"""
    
    def __init__(self):
        self.outputs_dir = Path("outputs")
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔍 Validating Product Development Demo Outputs...")
        print("="*60)
        
        # Check outputs directory exists
        if not self.outputs_dir.exists():
            print("❌ Outputs directory not found. Please run the demo first.")
            return False
        
        # Run validation checks
        self.validate_required_files()
        self.validate_prd()
        self.validate_architecture()
        self.validate_sprint_backlog()
        self.validate_implementations()
        self.validate_test_results()
        self.validate_reviews()
        self.validate_metrics()
        
        # Print results
        self.print_results()
        
        return len(self.results['failed']) == 0
    
    def validate_required_files(self):
        """Check that all required files exist"""
        required_files = [
            "PRD.md",
            "architecture.md",
            "sprint_backlog.md",
            "sprint_review.md",
            "retrospective.md",
            "metrics.json",
            "final_report.md"
        ]
        
        print("\n📁 Checking Required Files...")
        for file in required_files:
            file_path = self.outputs_dir / file
            if file_path.exists():
                self.results['passed'].append(f"File exists: {file}")
                print(f"   ✅ {file}")
            else:
                self.results['failed'].append(f"Missing file: {file}")
                print(f"   ❌ {file} - NOT FOUND")
    
    def validate_prd(self):
        """Validate PRD content and structure"""
        print("\n📋 Validating PRD...")
        prd_path = self.outputs_dir / "PRD.md"
        
        if not prd_path.exists():
            self.results['failed'].append("PRD.md not found")
            return
        
        with open(prd_path, 'r') as f:
            content = f.read()
        
        # Check required sections
        required_sections = [
            "Executive Summary",
            "Problem Statement",
            "Target Users",
            "Core Features",
            "Technical Requirements",
            "Success Metrics"
        ]
        
        for section in required_sections:
            if section in content:
                self.results['passed'].append(f"PRD contains section: {section}")
                print(f"   ✅ Section: {section}")
            else:
                self.results['failed'].append(f"PRD missing section: {section}")
                print(f"   ❌ Missing: {section}")
        
        # Check approval status
        if "Status**: APPROVED" in content:
            self.results['passed'].append("PRD is approved")
            print(f"   ✅ PRD Status: APPROVED")
        else:
            self.results['failed'].append("PRD not approved")
            print(f"   ❌ PRD Status: NOT APPROVED")
    
    def validate_architecture(self):
        """Validate architecture document"""
        print("\n🏗️ Validating Architecture...")
        arch_path = self.outputs_dir / "architecture.md"
        
        if not arch_path.exists():
            self.results['failed'].append("architecture.md not found")
            return
        
        with open(arch_path, 'r') as f:
            content = f.read()
        
        # Check required components
        required_components = [
            "Frontend Layer",
            "API Gateway",
            "Microservices",
            "Data Layer",
            "Security Architecture"
        ]
        
        for component in required_components:
            if component in content:
                self.results['passed'].append(f"Architecture includes: {component}")
                print(f"   ✅ Component: {component}")
            else:
                self.results['failed'].append(f"Architecture missing: {component}")
                print(f"   ❌ Missing: {component}")
    
    def validate_sprint_backlog(self):
        """Validate sprint backlog"""
        print("\n📅 Validating Sprint Backlog...")
        backlog_path = self.outputs_dir / "sprint_backlog.md"
        
        if not backlog_path.exists():
            self.results['failed'].append("sprint_backlog.md not found")
            return
        
        with open(backlog_path, 'r') as f:
            content = f.read()
        
        # Check for user stories
        story_count = content.count("TASK-")
        if story_count > 0:
            self.results['passed'].append(f"Sprint backlog contains {story_count} stories")
            print(f"   ✅ Stories: {story_count}")
        else:
            self.results['failed'].append("Sprint backlog has no stories")
            print(f"   ❌ No stories found")
        
        # Check for story points
        if "Total Story Points:" in content:
            self.results['passed'].append("Sprint backlog shows total points")
            print(f"   ✅ Story points calculated")
        else:
            self.results['warnings'].append("Sprint backlog missing total points")
            print(f"   ⚠️ Total points not shown")
    
    def validate_implementations(self):
        """Validate story implementations"""
        print("\n💻 Validating Implementations...")
        impl_dir = self.outputs_dir / "implementations"
        
        if not impl_dir.exists():
            self.results['failed'].append("implementations directory not found")
            print(f"   ❌ Implementations directory not found")
            return
        
        impl_files = list(impl_dir.glob("*.md"))
        if len(impl_files) > 0:
            self.results['passed'].append(f"Found {len(impl_files)} implementations")
            print(f"   ✅ Implementations: {len(impl_files)}")
            
            # Check implementation content
            for impl_file in impl_files[:1]:  # Check first file as sample
                with open(impl_file, 'r') as f:
                    content = f.read()
                
                if "Implementation Details" in content and "Testing" in content:
                    self.results['passed'].append("Implementation has required sections")
                    print(f"   ✅ Implementation structure valid")
                else:
                    self.results['warnings'].append("Implementation missing sections")
                    print(f"   ⚠️ Implementation structure incomplete")
        else:
            self.results['failed'].append("No implementations found")
            print(f"   ❌ No implementation files")
    
    def validate_test_results(self):
        """Validate test results"""
        print("\n🧪 Validating Test Results...")
        test_dir = self.outputs_dir / "test_results"
        
        if not test_dir.exists():
            self.results['failed'].append("test_results directory not found")
            print(f"   ❌ Test results directory not found")
            return
        
        test_files = list(test_dir.glob("*.json"))
        if len(test_files) > 0:
            self.results['passed'].append(f"Found {len(test_files)} test results")
            print(f"   ✅ Test results: {len(test_files)}")
            
            # Check test content
            total_passed = 0
            total_tests = 0
            
            for test_file in test_files:
                with open(test_file, 'r') as f:
                    data = json.load(f)
                
                if 'test_cases' in data:
                    for test_type in data['test_cases'].values():
                        total_tests += test_type.get('total', 0)
                        total_passed += test_type.get('passed', 0)
            
            if total_tests > 0:
                pass_rate = (total_passed / total_tests) * 100
                self.results['passed'].append(f"Test pass rate: {pass_rate:.1f}%")
                print(f"   ✅ Pass rate: {pass_rate:.1f}%")
                
                if pass_rate < 80:
                    self.results['warnings'].append(f"Low test pass rate: {pass_rate:.1f}%")
                    print(f"   ⚠️ Pass rate below 80%")
        else:
            self.results['failed'].append("No test results found")
            print(f"   ❌ No test result files")
    
    def validate_reviews(self):
        """Validate sprint review and retrospective"""
        print("\n🔍 Validating Reviews...")
        
        # Check sprint review
        review_path = self.outputs_dir / "sprint_review.md"
        if review_path.exists():
            with open(review_path, 'r') as f:
                content = f.read()
            
            if "Sprint Summary" in content and "Feature Demonstrations" in content:
                self.results['passed'].append("Sprint review complete")
                print(f"   ✅ Sprint review valid")
            else:
                self.results['warnings'].append("Sprint review incomplete")
                print(f"   ⚠️ Sprint review missing sections")
        else:
            self.results['failed'].append("Sprint review not found")
            print(f"   ❌ Sprint review missing")
        
        # Check retrospective
        retro_path = self.outputs_dir / "retrospective.md"
        if retro_path.exists():
            with open(retro_path, 'r') as f:
                content = f.read()
            
            if "What Went Well" in content and "Action Items" in content:
                self.results['passed'].append("Retrospective complete")
                print(f"   ✅ Retrospective valid")
            else:
                self.results['warnings'].append("Retrospective incomplete")
                print(f"   ⚠️ Retrospective missing sections")
        else:
            self.results['failed'].append("Retrospective not found")
            print(f"   ❌ Retrospective missing")
    
    def validate_metrics(self):
        """Validate metrics file"""
        print("\n📊 Validating Metrics...")
        metrics_path = self.outputs_dir / "metrics.json"
        
        if not metrics_path.exists():
            self.results['failed'].append("metrics.json not found")
            print(f"   ❌ Metrics file not found")
            return
        
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        # Check required metrics
        required_metrics = [
            'velocity',
            'quality',
            'test_coverage',
            'test_pass_rate',
            'cycle_time_days'
        ]
        
        for metric in required_metrics:
            if metric in metrics:
                value = metrics[metric]
                self.results['passed'].append(f"Metric {metric}: {value}")
                print(f"   ✅ {metric}: {value}")
            else:
                self.results['failed'].append(f"Missing metric: {metric}")
                print(f"   ❌ Missing: {metric}")
        
        # Check metric values
        if metrics.get('velocity', 0) > 0:
            self.results['passed'].append("Positive velocity achieved")
        else:
            self.results['warnings'].append("Zero velocity")
        
        if metrics.get('quality', 0) >= 80:
            self.results['passed'].append("Quality score acceptable")
        else:
            self.results['warnings'].append("Low quality score")
    
    def print_results(self):
        """Print validation results summary"""
        print("\n" + "="*60)
        print("📊 VALIDATION RESULTS")
        print("="*60)
        
        total_checks = len(self.results['passed']) + len(self.results['failed']) + len(self.results['warnings'])
        
        print(f"\n✅ Passed: {len(self.results['passed'])}/{total_checks}")
        print(f"❌ Failed: {len(self.results['failed'])}/{total_checks}")
        print(f"⚠️ Warnings: {len(self.results['warnings'])}/{total_checks}")
        
        if self.results['failed']:
            print("\n❌ Failed Checks:")
            for failure in self.results['failed']:
                print(f"   - {failure}")
        
        if self.results['warnings']:
            print("\n⚠️ Warnings:")
            for warning in self.results['warnings']:
                print(f"   - {warning}")
        
        print("\n" + "="*60)
        if len(self.results['failed']) == 0:
            print("✅ VALIDATION PASSED - Demo outputs meet all requirements!")
        else:
            print("❌ VALIDATION FAILED - Please review failed checks above")
        print("="*60)

def main():
    """Main entry point"""
    validator = DemoValidator()
    
    try:
        success = validator.validate_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()