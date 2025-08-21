"""
Quality Gate Tool for Agent-Zero
Integrates quality gate system with Agent-Zero's tool framework
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from metrics.quality_tracker import (
    QualityGate, QualityTracker, GateReport, GateStatus,
    QualityIssue, IssueSeverity, IssueCategory, QualityMetrics,
    create_story_gate, create_release_gate, create_sprint_gate
)

# Try to import checklist if available
try:
    from python.helpers.checklist_core import ChecklistResult
except ImportError:
    ChecklistResult = None


class QualityGateTool(Tool):
    """
    Tool for executing quality gate assessments in Agent-Zero
    
    This tool allows agents to:
    - Execute quality gates on various targets (stories, epics, releases)
    - Create and track quality issues
    - Generate quality reports
    - Make gate decisions (PASS/FAIL/CONCERNS/WAIVED)
    - Track quality metrics over time
    """
    
    def __init__(self):
        super().__init__(
            name="quality_gate",
            description="Execute quality gate assessments and track quality metrics",
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["assess", "create_issue", "waive", "get_report", "get_trends", "list_gates"],
                    "description": "The quality gate action to perform"
                },
                "gate_name": {
                    "type": "string",
                    "description": "Name of the quality gate to execute",
                    "required": False
                },
                "target_type": {
                    "type": "string",
                    "enum": ["story", "epic", "sprint", "release", "code", "custom"],
                    "description": "Type of target being assessed",
                    "required": False
                },
                "target_id": {
                    "type": "string",
                    "description": "ID of the target being assessed",
                    "required": False
                },
                "target_name": {
                    "type": "string",
                    "description": "Name/description of the target",
                    "required": False
                },
                "checklist_path": {
                    "type": "string",
                    "description": "Path to checklist results file",
                    "required": False
                },
                "criteria": {
                    "type": "object",
                    "description": "Custom assessment criteria",
                    "required": False
                },
                "issue": {
                    "type": "object",
                    "description": "Issue details for create_issue action",
                    "required": False
                },
                "waiver_reason": {
                    "type": "string",
                    "description": "Reason for waiving a gate or issue",
                    "required": False
                },
                "report_id": {
                    "type": "string",
                    "description": "ID of report to retrieve",
                    "required": False
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days for trend analysis",
                    "required": False,
                    "default": 7
                }
            }
        )
        
        # Initialize tracker
        self.tracker = QualityTracker()
        self._register_default_gates()
        
    def _register_default_gates(self):
        """Register default quality gates"""
        self.tracker.register_gate(create_story_gate())
        self.tracker.register_gate(create_release_gate())
        self.tracker.register_gate(create_sprint_gate())
        
        # Create additional gates
        self._create_code_gate()
        self._create_epic_gate()
        self._create_architecture_gate()
    
    def _create_code_gate(self):
        """Create quality gate for code reviews"""
        gate = QualityGate("Code Quality Gate", "code")
        gate.set_thresholds({
            'min_coverage': 80.0,
            'min_test_coverage': 75.0,
            'max_critical_issues': 0,
            'max_high_issues': 3,
            'min_security_score': 85.0,
            'min_performance_score': 80.0,
            'min_overall_score': 80.0
        })
        
        # Add code-specific criteria
        async def has_tests(target, metrics):
            metrics.test_coverage = getattr(target, 'test_coverage', 75.0)
            return metrics.test_coverage >= 70.0
        
        async def no_console_logs(target, metrics):
            # Check for console.log statements
            if hasattr(target, 'code'):
                return 'console.log' not in target.code
            return True
        
        async def follows_conventions(target, metrics):
            metrics.maintainability_index = getattr(target, 'maintainability', 80.0)
            return metrics.maintainability_index >= 70.0
        
        gate.add_criteria("Has Adequate Tests", has_tests)
        gate.add_criteria("No Debug Statements", no_console_logs)
        gate.add_criteria("Follows Conventions", follows_conventions)
        
        self.tracker.register_gate(gate)
    
    def _create_epic_gate(self):
        """Create quality gate for epics"""
        gate = QualityGate("Epic Quality Gate", "epic")
        gate.set_thresholds({
            'min_coverage': 85.0,
            'min_test_coverage': 80.0,
            'max_critical_issues': 0,
            'max_high_issues': 5,
            'min_security_score': 80.0,
            'min_performance_score': 75.0,
            'min_overall_score': 80.0
        })
        
        async def has_stories(target, metrics):
            return hasattr(target, 'stories') and len(target.stories) > 0
        
        async def has_acceptance_criteria(target, metrics):
            return hasattr(target, 'acceptance_criteria') and len(target.acceptance_criteria) >= 3
        
        gate.add_criteria("Has Stories Defined", has_stories)
        gate.add_criteria("Has Acceptance Criteria", has_acceptance_criteria)
        
        self.tracker.register_gate(gate)
    
    def _create_architecture_gate(self):
        """Create quality gate for architecture reviews"""
        gate = QualityGate("Architecture Quality Gate", "architecture")
        gate.set_thresholds({
            'min_coverage': 90.0,
            'min_test_coverage': 85.0,
            'max_critical_issues': 0,
            'max_high_issues': 2,
            'min_security_score': 90.0,
            'min_performance_score': 85.0,
            'min_overall_score': 85.0
        })
        
        async def has_diagrams(target, metrics):
            return hasattr(target, 'diagrams') and len(target.diagrams) > 0
        
        async def security_reviewed(target, metrics):
            metrics.security_score = 85.0  # Default if not set
            return hasattr(target, 'security_review') and target.security_review
        
        async def scalability_addressed(target, metrics):
            return hasattr(target, 'scalability_plan') and target.scalability_plan
        
        gate.add_criteria("Has Architecture Diagrams", has_diagrams)
        gate.add_criteria("Security Reviewed", security_reviewed)
        gate.add_criteria("Scalability Addressed", scalability_addressed)
        
        self.tracker.register_gate(gate)
    
    async def execute(self, **kwargs) -> Response:
        """Execute the quality gate tool"""
        action = kwargs.get('action', 'assess')
        
        try:
            if action == "assess":
                return await self._assess_quality(kwargs)
            elif action == "create_issue":
                return await self._create_issue(kwargs)
            elif action == "waive":
                return await self._waive_gate(kwargs)
            elif action == "get_report":
                return await self._get_report(kwargs)
            elif action == "get_trends":
                return await self._get_trends(kwargs)
            elif action == "list_gates":
                return await self._list_gates()
            else:
                return Response(
                    success=False,
                    message=f"Unknown action: {action}",
                    data={}
                )
        except Exception as e:
            return Response(
                success=False,
                message=f"Error executing quality gate: {str(e)}",
                data={}
            )
    
    async def _assess_quality(self, kwargs: Dict) -> Response:
        """Perform quality assessment"""
        gate_name = kwargs.get('gate_name')
        target_type = kwargs.get('target_type', 'custom')
        target_id = kwargs.get('target_id', 'unknown')
        target_name = kwargs.get('target_name', 'Unnamed Target')
        checklist_path = kwargs.get('checklist_path')
        criteria = kwargs.get('criteria', {})
        
        # Determine gate name if not provided
        if not gate_name:
            gate_map = {
                'story': 'Story Quality Gate',
                'epic': 'Epic Quality Gate',
                'sprint': 'Sprint Quality Gate',
                'release': 'Release Quality Gate',
                'code': 'Code Quality Gate',
                'architecture': 'Architecture Quality Gate'
            }
            gate_name = gate_map.get(target_type, 'Story Quality Gate')
        
        # Load checklist results if provided
        checklist_results = None
        if checklist_path and os.path.exists(checklist_path):
            with open(checklist_path, 'r') as f:
                checklist_results = json.load(f)
        
        # Create target object
        class Target:
            def __init__(self):
                self.id = target_id
                self.name = target_name
                self.type = target_type
                # Add criteria as attributes
                for key, value in criteria.items():
                    setattr(self, key, value)
        
        target = Target()
        
        # Execute gate assessment
        report = await self.tracker.execute_gate(
            gate_name,
            target,
            self.agent.context.agent_name if hasattr(self, 'agent') else 'agent',
            checklist_results=checklist_results
        )
        
        # Determine appropriate message based on status
        status_messages = {
            GateStatus.PASS: "✅ Quality gate PASSED! All criteria met.",
            GateStatus.CONCERNS: "⚠️ Quality gate passed with CONCERNS. Review recommendations.",
            GateStatus.FAIL: "❌ Quality gate FAILED. Critical issues must be addressed.",
            GateStatus.WAIVED: "⚠️ Quality gate WAIVED. Proceeding with acknowledged risks.",
            GateStatus.PENDING: "⏳ Quality gate assessment PENDING.",
            GateStatus.BLOCKED: "🚫 Quality gate BLOCKED by dependencies."
        }
        
        message = status_messages.get(report.status, "Quality gate assessment completed.")
        
        # Save report
        report_path = f"./storage/quality/{report.gate_id}.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report.to_markdown())
        
        return Response(
            success=report.status in [GateStatus.PASS, GateStatus.CONCERNS, GateStatus.WAIVED],
            message=message,
            data={
                "report_id": report.gate_id,
                "status": report.status.value,
                "status_reason": report.status_reason,
                "overall_score": report.metrics.calculate_overall_score(),
                "issues_count": len(report.issues),
                "critical_issues": len([i for i in report.issues if i.severity == IssueSeverity.CRITICAL]),
                "high_issues": len([i for i in report.issues if i.severity == IssueSeverity.HIGH]),
                "recommendations": report.recommendations,
                "report_path": report_path,
                "passed_criteria": len(report.passed_criteria),
                "failed_criteria": len(report.failed_criteria),
                "markdown_report": report.to_markdown()
            }
        )
    
    async def _create_issue(self, kwargs: Dict) -> Response:
        """Create a quality issue"""
        issue_data = kwargs.get('issue', {})
        
        # Validate required fields
        required = ['title', 'description', 'severity', 'category']
        missing = [f for f in required if f not in issue_data]
        if missing:
            return Response(
                success=False,
                message=f"Missing required issue fields: {', '.join(missing)}",
                data={}
            )
        
        # Create issue
        issue = QualityIssue(
            id=f"QI-{len(self.tracker.reports):04d}",
            title=issue_data['title'],
            description=issue_data['description'],
            severity=IssueSeverity[issue_data['severity'].upper()],
            category=IssueCategory[issue_data['category'].upper()],
            finding=issue_data.get('finding', 'Issue detected'),
            expected=issue_data.get('expected', 'Expected behavior'),
            impact=issue_data.get('impact', 'May impact quality'),
            suggested_action=issue_data.get('suggested_action', 'Review and address'),
            tags=issue_data.get('tags', [])
        )
        
        return Response(
            success=True,
            message=f"Quality issue {issue.id} created",
            data={
                "issue_id": issue.id,
                "issue": issue.to_dict()
            }
        )
    
    async def _waive_gate(self, kwargs: Dict) -> Response:
        """Waive a quality gate or issue"""
        report_id = kwargs.get('report_id')
        waiver_reason = kwargs.get('waiver_reason', 'Waived by user')
        
        if not report_id:
            return Response(
                success=False,
                message="report_id is required for waiving",
                data={}
            )
        
        # Find report
        report = None
        for r in self.tracker.reports:
            if r.gate_id == report_id:
                report = r
                break
        
        if not report:
            return Response(
                success=False,
                message=f"Report {report_id} not found",
                data={}
            )
        
        # Create waived version
        waived_report = self.tracker.gates[report.gate_name].create_waiver(
            report,
            waiver_reason,
            self.agent.context.agent_name if hasattr(self, 'agent') else 'agent'
        )
        
        # Save updated report
        self.tracker._save_report(waived_report)
        
        return Response(
            success=True,
            message=f"Quality gate {report_id} waived",
            data={
                "report_id": report_id,
                "new_status": waived_report.status.value,
                "waiver_reason": waiver_reason
            }
        )
    
    async def _get_report(self, kwargs: Dict) -> Response:
        """Get a specific quality report"""
        report_id = kwargs.get('report_id')
        
        if not report_id:
            # Return latest report
            if not self.tracker.reports:
                return Response(
                    success=False,
                    message="No quality reports available",
                    data={}
                )
            report = self.tracker.reports[-1]
        else:
            # Find specific report
            report = None
            for r in self.tracker.reports:
                if r.gate_id == report_id:
                    report = r
                    break
            
            if not report:
                return Response(
                    success=False,
                    message=f"Report {report_id} not found",
                    data={}
                )
        
        return Response(
            success=True,
            message=f"Retrieved report {report.gate_id}",
            data={
                "report": report.to_dict(),
                "markdown": report.to_markdown()
            }
        )
    
    async def _get_trends(self, kwargs: Dict) -> Response:
        """Get quality trends"""
        days = kwargs.get('days', 7)
        
        trends = self.tracker.get_quality_trends(days)
        summary = self.tracker.generate_summary_report(days)
        
        return Response(
            success=True,
            message=f"Quality trends for last {days} days",
            data={
                "trends": trends,
                "summary": summary
            }
        )
    
    async def _list_gates(self) -> Response:
        """List available quality gates"""
        gates = []
        for name, gate in self.tracker.gates.items():
            gates.append({
                "name": name,
                "type": gate.gate_type,
                "thresholds": gate.thresholds,
                "criteria_count": len(gate.criteria)
            })
        
        return Response(
            success=True,
            message=f"Found {len(gates)} quality gates",
            data={"gates": gates}
        )


# Integration with Agent-Zero's ChecklistExecutor if available
class QualityGateChecklistIntegration:
    """
    Integrates quality gates with checklist results
    """
    
    @staticmethod
    async def assess_checklist_quality(checklist_result: Dict, 
                                      target_type: str = "story") -> GateReport:
        """
        Assess quality based on checklist results
        
        Args:
            checklist_result: Result from ChecklistExecutor
            target_type: Type of target being assessed
            
        Returns:
            Quality gate report
        """
        tool = QualityGateTool()
        
        # Determine gate based on checklist type
        checklist_name = checklist_result.get('checklist_name', '')
        if 'story' in checklist_name.lower():
            gate_name = 'Story Quality Gate'
        elif 'architecture' in checklist_name.lower():
            gate_name = 'Architecture Quality Gate'
        elif 'release' in checklist_name.lower():
            gate_name = 'Release Quality Gate'
        else:
            gate_name = 'Story Quality Gate'  # Default
        
        # Execute assessment
        response = await tool._assess_quality({
            'gate_name': gate_name,
            'target_type': target_type,
            'target_id': checklist_result.get('target_id', 'unknown'),
            'target_name': checklist_result.get('target_name', 'Checklist Target'),
            'checklist_results': checklist_result
        })
        
        return response


# Standalone test function
async def test_quality_gate_tool():
    """Test the quality gate tool"""
    print(PrintStyle.HEADER + "Testing Quality Gate Tool" + PrintStyle.ENDC)
    
    tool = QualityGateTool()
    
    # Test 1: List available gates
    print("\n" + PrintStyle.BOLD + "Test 1: List Gates" + PrintStyle.ENDC)
    result = await tool.execute(action="list_gates")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Gates: {json.dumps(result.data['gates'], indent=2)}")
    
    # Test 2: Assess a story
    print("\n" + PrintStyle.BOLD + "Test 2: Assess Story" + PrintStyle.ENDC)
    result = await tool.execute(
        action="assess",
        target_type="story",
        target_id="STORY-001",
        target_name="Implement login feature",
        criteria={
            "description": "As a user, I want to log in to access my account",
            "acceptance_criteria": ["Username/password validation", "Session management", "Error handling"],
            "story_points": 5,
            "test_coverage": 85.0,
            "maintainability": 82.0
        }
    )
    print(f"Success: {result.success}")
    print(f"Status: {result.data.get('status')}")
    print(f"Score: {result.data.get('overall_score'):.1f}")
    print(f"Issues: {result.data.get('issues_count')}")
    
    # Test 3: Create an issue
    print("\n" + PrintStyle.BOLD + "Test 3: Create Issue" + PrintStyle.ENDC)
    result = await tool.execute(
        action="create_issue",
        issue={
            "title": "Missing unit tests",
            "description": "Several critical functions lack unit test coverage",
            "severity": "HIGH",
            "category": "TESTING",
            "finding": "Only 60% test coverage",
            "expected": "Minimum 80% test coverage",
            "impact": "Potential bugs in production",
            "suggested_action": "Add unit tests for uncovered functions"
        }
    )
    print(f"Success: {result.success}")
    print(f"Issue ID: {result.data.get('issue_id')}")
    
    # Test 4: Get trends
    print("\n" + PrintStyle.BOLD + "Test 4: Get Trends" + PrintStyle.ENDC)
    result = await tool.execute(action="get_trends", days=30)
    print(f"Success: {result.success}")
    print(f"Trends: {json.dumps(result.data.get('trends', {}), indent=2)}")
    
    print("\n" + PrintStyle.SUCCESS + "All tests completed!" + PrintStyle.ENDC)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_quality_gate_tool())