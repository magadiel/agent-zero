"""
Unit tests for the Quality Tracker system
"""

import unittest
import asyncio
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from metrics.quality_tracker import (
    QualityGate, QualityTracker, GateStatus, IssueSeverity, IssueCategory,
    QualityIssue, QualityMetrics, GateReport,
    create_story_gate, create_release_gate, create_sprint_gate
)


class TestQualityIssue(unittest.TestCase):
    """Test QualityIssue class"""
    
    def test_issue_creation(self):
        """Test creating a quality issue"""
        issue = QualityIssue(
            id="QI-001",
            title="Test Issue",
            description="Test description",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.FUNCTIONAL,
            finding="Found this",
            expected="Expected that",
            impact="High impact",
            suggested_action="Fix it"
        )
        
        self.assertEqual(issue.id, "QI-001")
        self.assertEqual(issue.severity, IssueSeverity.HIGH)
        self.assertFalse(issue.waived)
        self.assertIsNone(issue.resolved_at)
    
    def test_issue_resolution(self):
        """Test resolving an issue"""
        issue = QualityIssue(
            id="QI-002",
            title="Test Issue",
            description="Test",
            severity=IssueSeverity.MEDIUM,
            category=IssueCategory.TESTING,
            finding="Found",
            expected="Expected",
            impact="Impact",
            suggested_action="Action"
        )
        
        issue.resolve("Fixed the issue")
        self.assertIsNotNone(issue.resolved_at)
        self.assertEqual(issue.resolution, "Fixed the issue")
    
    def test_issue_waiver(self):
        """Test waiving an issue"""
        issue = QualityIssue(
            id="QI-003",
            title="Test Issue",
            description="Test",
            severity=IssueSeverity.LOW,
            category=IssueCategory.DOCUMENTATION,
            finding="Found",
            expected="Expected",
            impact="Impact",
            suggested_action="Action"
        )
        
        issue.waive("Acceptable risk", "manager")
        self.assertTrue(issue.waived)
        self.assertEqual(issue.waiver_reason, "Acceptable risk")
        self.assertEqual(issue.waived_by, "manager")
    
    def test_issue_serialization(self):
        """Test issue serialization to dict"""
        issue = QualityIssue(
            id="QI-004",
            title="Test Issue",
            description="Test",
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.SECURITY,
            finding="Security vulnerability",
            expected="Secure code",
            impact="Data breach risk",
            suggested_action="Patch immediately",
            tags=["security", "critical"]
        )
        
        data = issue.to_dict()
        self.assertEqual(data['id'], "QI-004")
        self.assertEqual(data['severity'], "CRITICAL")
        self.assertEqual(data['category'], "SECURITY")
        self.assertIn("security", data['tags'])


class TestQualityMetrics(unittest.TestCase):
    """Test QualityMetrics class"""
    
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        metrics = QualityMetrics()
        self.assertEqual(metrics.total_checks, 0)
        self.assertEqual(metrics.coverage_percentage, 0.0)
        self.assertEqual(metrics.calculate_overall_score(), 0.0)
    
    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        metrics = QualityMetrics(
            coverage_percentage=85.0,
            maintainability_index=75.0,
            security_score=90.0,
            performance_score=80.0,
            documentation_completeness=70.0,
            test_coverage=85.0,
            compliance_score=95.0
        )
        
        score = metrics.calculate_overall_score()
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_custom_metrics(self):
        """Test custom metrics"""
        metrics = QualityMetrics()
        metrics.custom_metrics['custom_score'] = 85.5
        metrics.custom_metrics['another_metric'] = 92.0
        
        self.assertEqual(metrics.custom_metrics['custom_score'], 85.5)
        self.assertEqual(len(metrics.custom_metrics), 2)


class TestQualityGate(unittest.TestCase):
    """Test QualityGate class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.gate = QualityGate("Test Gate", "test")
    
    def test_gate_creation(self):
        """Test gate creation"""
        self.assertEqual(self.gate.gate_name, "Test Gate")
        self.assertEqual(self.gate.gate_type, "test")
        self.assertIn('min_coverage', self.gate.thresholds)
    
    def test_threshold_setting(self):
        """Test setting thresholds"""
        self.gate.set_thresholds({
            'min_coverage': 90.0,
            'max_critical_issues': 1
        })
        
        self.assertEqual(self.gate.thresholds['min_coverage'], 90.0)
        self.assertEqual(self.gate.thresholds['max_critical_issues'], 1)
    
    def test_criteria_addition(self):
        """Test adding criteria"""
        async def test_criteria(target, metrics):
            return True
        
        self.gate.add_criteria("Test Criteria", test_criteria, required=True)
        self.assertIn("Test Criteria", self.gate.criteria)
        self.assertTrue(self.gate.criteria["Test Criteria"]['required'])
    
    async def test_assessment_pass(self):
        """Test assessment that passes"""
        class MockTarget:
            id = "test-001"
            name = "Test Target"
        
        report = await self.gate.assess(
            MockTarget(),
            "tester"
        )
        
        self.assertIsInstance(report, GateReport)
        self.assertEqual(report.gate_name, "Test Gate")
        self.assertEqual(report.assessed_by, "tester")
    
    async def test_assessment_with_issues(self):
        """Test assessment with issues"""
        class MockTarget:
            id = "test-002"
            name = "Test Target with Issues"
        
        # Add custom check that creates issues
        async def create_issues(target, metrics, issues):
            issue = QualityIssue(
                id="QI-TEST",
                title="Critical Issue",
                description="Test critical issue",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                finding="Security hole",
                expected="Secure",
                impact="High",
                suggested_action="Fix now"
            )
            return [issue]
        
        report = await self.gate.assess(
            MockTarget(),
            "tester",
            custom_checks=[create_issues]
        )
        
        self.assertEqual(len(report.issues), 1)
        self.assertEqual(report.issues[0].severity, IssueSeverity.CRITICAL)
        # Critical issue should cause failure
        self.assertIn(report.status, [GateStatus.FAIL, GateStatus.CONCERNS])
    
    def test_waiver_creation(self):
        """Test creating a waiver"""
        report = GateReport(
            gate_id="QG-001",
            gate_name="Test Gate",
            status=GateStatus.FAIL,
            assessed_at=datetime.now(),
            assessed_by="tester",
            target_type="test",
            target_id="001",
            target_name="Test",
            issues=[],
            metrics=QualityMetrics(),
            status_reason="Failed",
            recommendations=[],
            passed_criteria=[],
            failed_criteria=["criteria1"],
            waived_criteria=[]
        )
        
        waived = self.gate.create_waiver(report, "Known issue", "manager")
        self.assertEqual(waived.status, GateStatus.WAIVED)
        self.assertIn("WAIVED", waived.status_reason)


class TestGateReport(unittest.TestCase):
    """Test GateReport class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.report = GateReport(
            gate_id="QG-TEST",
            gate_name="Test Gate",
            status=GateStatus.PASS,
            assessed_at=datetime.now(),
            assessed_by="tester",
            target_type="story",
            target_id="STORY-001",
            target_name="Test Story",
            issues=[],
            metrics=QualityMetrics(
                total_checks=10,
                passed_checks=9,
                failed_checks=1,
                coverage_percentage=85.0,
                test_coverage=80.0,
                security_score=90.0,
                performance_score=85.0
            ),
            status_reason="All criteria met",
            recommendations=["Keep up the good work"],
            passed_criteria=["criteria1", "criteria2"],
            failed_criteria=[],
            waived_criteria=[]
        )
    
    def test_report_serialization(self):
        """Test report serialization"""
        data = self.report.to_dict()
        self.assertEqual(data['gate_id'], "QG-TEST")
        self.assertEqual(data['status'], "PASS")
        self.assertEqual(len(data['passed_criteria']), 2)
    
    def test_markdown_generation(self):
        """Test markdown report generation"""
        markdown = self.report.to_markdown()
        self.assertIn("# Quality Gate Report", markdown)
        self.assertIn("Test Gate", markdown)
        self.assertIn("PASS", markdown)
        self.assertIn("criteria1", markdown)
    
    def test_report_with_issues(self):
        """Test report with issues"""
        issue = QualityIssue(
            id="QI-001",
            title="Test Issue",
            description="Description",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.TESTING,
            finding="Found",
            expected="Expected",
            impact="Impact",
            suggested_action="Action"
        )
        
        self.report.issues.append(issue)
        markdown = self.report.to_markdown()
        self.assertIn("Issues Found", markdown)
        self.assertIn("Test Issue", markdown)
        self.assertIn("High Issues", markdown)  # Check for "High Issues" instead of just "HIGH"


class TestQualityTracker(unittest.TestCase):
    """Test QualityTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = QualityTracker(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_tracker_initialization(self):
        """Test tracker initialization"""
        self.assertEqual(len(self.tracker.reports), 0)
        self.assertEqual(len(self.tracker.gates), 0)
    
    def test_gate_registration(self):
        """Test registering gates"""
        gate = QualityGate("Test Gate", "test")
        self.tracker.register_gate(gate)
        self.assertIn("Test Gate", self.tracker.gates)
    
    async def test_gate_execution(self):
        """Test executing a gate"""
        gate = create_story_gate()
        self.tracker.register_gate(gate)
        
        class MockStory:
            id = "STORY-123"
            name = "Test Story"
            description = "A long description that meets the minimum length requirement for testing purposes"
            acceptance_criteria = ["AC1", "AC2", "AC3"]
            story_points = 5
        
        report = await self.tracker.execute_gate(
            "Story Quality Gate",
            MockStory(),
            "tester"
        )
        
        self.assertIsInstance(report, GateReport)
        self.assertEqual(len(self.tracker.reports), 1)
        
        # Check that report was saved
        report_file = Path(self.temp_dir) / f"{report.gate_id}.json"
        self.assertTrue(report_file.exists())
    
    def test_report_retrieval(self):
        """Test retrieving reports"""
        # Create some mock reports
        for i in range(3):
            report = GateReport(
                gate_id=f"QG-{i:03d}",
                gate_name="Test Gate",
                status=GateStatus.PASS if i % 2 == 0 else GateStatus.FAIL,
                assessed_at=datetime.now(),
                assessed_by="tester",
                target_type="story",
                target_id=f"STORY-{i:03d}",
                target_name=f"Story {i}",
                issues=[],
                metrics=QualityMetrics(),
                status_reason="Test",
                recommendations=[],
                passed_criteria=[],
                failed_criteria=[],
                waived_criteria=[]
            )
            self.tracker.reports.append(report)
        
        # Test retrieval by target
        reports = self.tracker.get_reports_by_target("STORY-001")
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].target_id, "STORY-001")
        
        # Test retrieval by status
        passed = self.tracker.get_reports_by_status(GateStatus.PASS)
        self.assertEqual(len(passed), 2)
    
    def test_quality_trends(self):
        """Test quality trends calculation"""
        # Add some reports
        for i in range(5):
            report = GateReport(
                gate_id=f"QG-{i:03d}",
                gate_name="Test Gate",
                status=GateStatus.PASS if i < 3 else GateStatus.FAIL,
                assessed_at=datetime.now() - timedelta(days=i),
                assessed_by="tester",
                target_type="story",
                target_id=f"STORY-{i:03d}",
                target_name=f"Story {i}",
                issues=[],
                metrics=QualityMetrics(
                    coverage_percentage=80 + i,
                    test_coverage=75 + i,
                    security_score=85 + i,
                    performance_score=80 + i
                ),
                status_reason="Test",
                recommendations=[],
                passed_criteria=[],
                failed_criteria=[],
                waived_criteria=[]
            )
            self.tracker.reports.append(report)
        
        trends = self.tracker.get_quality_trends(30)
        self.assertEqual(trends['total_assessments'], 5)
        self.assertEqual(trends['pass_rate'], 60.0)  # 3 out of 5
        self.assertEqual(trends['fail_rate'], 40.0)  # 2 out of 5
    
    def test_summary_report(self):
        """Test summary report generation"""
        # Add a report
        report = GateReport(
            gate_id="QG-001",
            gate_name="Test Gate",
            status=GateStatus.PASS,
            assessed_at=datetime.now(),
            assessed_by="tester",
            target_type="story",
            target_id="STORY-001",
            target_name="Test Story",
            issues=[],
            metrics=QualityMetrics(),
            status_reason="All good",
            recommendations=[],
            passed_criteria=["criteria1"],
            failed_criteria=[],
            waived_criteria=[]
        )
        self.tracker.reports.append(report)
        
        summary = self.tracker.generate_summary_report(7)
        self.assertIn("Quality Summary Report", summary)
        self.assertIn("**Total Assessments**: 1", summary)  # Check for the actual format with asterisks


class TestPredefinedGates(unittest.TestCase):
    """Test predefined gate creators"""
    
    async def test_story_gate(self):
        """Test story quality gate"""
        gate = create_story_gate()
        self.assertEqual(gate.gate_name, "Story Quality Gate")
        self.assertEqual(gate.gate_type, "story")
        self.assertEqual(gate.thresholds['min_coverage'], 85.0)
        
        # Test with valid story
        class ValidStory:
            id = "STORY-001"
            name = "Valid Story"
            description = "This is a valid story with a sufficiently long description for testing"
            acceptance_criteria = ["AC1", "AC2"]
            story_points = 3
        
        report = await gate.assess(ValidStory(), "tester")
        self.assertIn("Has Acceptance Criteria", report.passed_criteria)
        self.assertIn("Has Story Points", report.passed_criteria)
    
    def test_release_gate(self):
        """Test release quality gate"""
        gate = create_release_gate()
        self.assertEqual(gate.gate_name, "Release Quality Gate")
        self.assertEqual(gate.gate_type, "release")
        self.assertEqual(gate.thresholds['min_coverage'], 90.0)
        self.assertEqual(gate.thresholds['max_high_issues'], 0)
    
    def test_sprint_gate(self):
        """Test sprint quality gate"""
        gate = create_sprint_gate()
        self.assertEqual(gate.gate_name, "Sprint Quality Gate")
        self.assertEqual(gate.gate_type, "sprint")
        self.assertEqual(gate.thresholds['min_test_coverage'], 75.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the quality system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = QualityTracker(storage_path=self.temp_dir)
        self.tracker.register_gate(create_story_gate())
        self.tracker.register_gate(create_sprint_gate())
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    async def test_full_workflow(self):
        """Test a complete quality assessment workflow"""
        # Create a story
        class Story:
            id = "STORY-999"
            name = "Complete Story"
            description = "As a user, I want to have a complete story with all required fields properly filled out"
            acceptance_criteria = [
                "All fields are present",
                "Validation passes",
                "Quality gate passes"
            ]
            story_points = 8
        
        # Assess the story
        report = await self.tracker.execute_gate(
            "Story Quality Gate",
            Story(),
            "qa_engineer"
        )
        
        self.assertEqual(report.status, GateStatus.PASS)
        
        # Get trends
        trends = self.tracker.get_quality_trends(30)
        self.assertEqual(trends['total_assessments'], 1)
        self.assertEqual(trends['pass_rate'], 100.0)
        
        # Generate summary
        summary = self.tracker.generate_summary_report(7)
        self.assertIn("Pass Rate: 100.0%", summary)


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == "__main__":
    # Run all tests
    unittest.main()