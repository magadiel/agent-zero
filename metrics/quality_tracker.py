"""
Quality Gate System for Agile AI Company
Implements formal quality assessment with gate decisions, issue tracking, and reporting
"""

import asyncio
import json
import yaml
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Quality gate status outcomes"""
    PASS = "PASS"  # All criteria met
    CONCERNS = "CONCERNS"  # Minor issues but acceptable
    FAIL = "FAIL"  # Critical issues, must be fixed
    WAIVED = "WAIVED"  # Issues acknowledged but waived with justification
    PENDING = "PENDING"  # Assessment not yet complete
    BLOCKED = "BLOCKED"  # Cannot assess due to dependencies


class IssueSeverity(Enum):
    """Issue severity classification"""
    LOW = "LOW"  # Minor issue, cosmetic or nice-to-have
    MEDIUM = "MEDIUM"  # Should be fixed but not blocking
    HIGH = "HIGH"  # Must be fixed soon, impacts functionality
    CRITICAL = "CRITICAL"  # Blocker, must be fixed immediately


class IssueCategory(Enum):
    """Categories of quality issues"""
    FUNCTIONAL = "FUNCTIONAL"  # Feature doesn't work as expected
    PERFORMANCE = "PERFORMANCE"  # Performance degradation
    SECURITY = "SECURITY"  # Security vulnerability
    USABILITY = "USABILITY"  # User experience issues
    DOCUMENTATION = "DOCUMENTATION"  # Missing or incorrect documentation
    TESTING = "TESTING"  # Insufficient test coverage
    ARCHITECTURE = "ARCHITECTURE"  # Design or architecture concerns
    COMPLIANCE = "COMPLIANCE"  # Regulatory or policy compliance
    TECHNICAL_DEBT = "TECHNICAL_DEBT"  # Code quality issues
    ACCESSIBILITY = "ACCESSIBILITY"  # Accessibility concerns


@dataclass
class QualityIssue:
    """Represents a quality issue found during gate assessment"""
    id: str
    title: str
    description: str
    severity: IssueSeverity
    category: IssueCategory
    finding: str  # What was found
    expected: str  # What was expected
    impact: str  # Impact if not fixed
    suggested_action: str  # Recommended fix
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    waived: bool = False
    waiver_reason: Optional[str] = None
    waived_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        data['detected_at'] = self.detected_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data
    
    def resolve(self, resolution: str):
        """Mark issue as resolved"""
        self.resolved_at = datetime.now()
        self.resolution = resolution
    
    def waive(self, reason: str, waived_by: str):
        """Waive the issue with justification"""
        self.waived = True
        self.waiver_reason = reason
        self.waived_by = waived_by
        

@dataclass
class QualityMetrics:
    """Metrics collected during quality assessment"""
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    skipped_checks: int = 0
    coverage_percentage: float = 0.0
    complexity_score: float = 0.0
    maintainability_index: float = 0.0
    security_score: float = 0.0
    performance_score: float = 0.0
    documentation_completeness: float = 0.0
    test_coverage: float = 0.0
    code_duplication: float = 0.0
    technical_debt_hours: float = 0.0
    compliance_score: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall quality score (0-100)"""
        weights = {
            'coverage': 0.15,
            'maintainability': 0.15,
            'security': 0.20,
            'performance': 0.15,
            'documentation': 0.10,
            'test': 0.15,
            'compliance': 0.10
        }
        
        score = (
            weights['coverage'] * self.coverage_percentage +
            weights['maintainability'] * self.maintainability_index +
            weights['security'] * self.security_score +
            weights['performance'] * self.performance_score +
            weights['documentation'] * self.documentation_completeness +
            weights['test'] * self.test_coverage +
            weights['compliance'] * self.compliance_score
        )
        
        return min(100.0, max(0.0, score))


@dataclass
class GateReport:
    """Quality gate assessment report"""
    gate_id: str
    gate_name: str
    status: GateStatus
    assessed_at: datetime
    assessed_by: str
    target_type: str  # What was assessed (story, epic, release, etc.)
    target_id: str
    target_name: str
    issues: List[QualityIssue]
    metrics: QualityMetrics
    status_reason: str
    recommendations: List[str]
    passed_criteria: List[str]
    failed_criteria: List[str]
    waived_criteria: List[str]
    notes: str = ""
    attachments: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'gate_id': self.gate_id,
            'gate_name': self.gate_name,
            'status': self.status.value,
            'assessed_at': self.assessed_at.isoformat(),
            'assessed_by': self.assessed_by,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'issues': [issue.to_dict() for issue in self.issues],
            'metrics': asdict(self.metrics),
            'status_reason': self.status_reason,
            'recommendations': self.recommendations,
            'passed_criteria': self.passed_criteria,
            'failed_criteria': self.failed_criteria,
            'waived_criteria': self.waived_criteria,
            'notes': self.notes,
            'attachments': self.attachments
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = f"""# Quality Gate Report: {self.gate_name}

## Summary
- **Status**: {self.status.value}
- **Target**: {self.target_type} - {self.target_name} ({self.target_id})
- **Assessed**: {self.assessed_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Assessor**: {self.assessed_by}

## Status Reason
{self.status_reason}

## Metrics
- **Overall Score**: {self.metrics.calculate_overall_score():.1f}/100
- **Checks**: {self.metrics.passed_checks}/{self.metrics.total_checks} passed
- **Coverage**: {self.metrics.coverage_percentage:.1f}%
- **Test Coverage**: {self.metrics.test_coverage:.1f}%
- **Security Score**: {self.metrics.security_score:.1f}/100
- **Performance Score**: {self.metrics.performance_score:.1f}/100
- **Technical Debt**: {self.metrics.technical_debt_hours:.1f} hours

## Criteria Assessment

### ✅ Passed ({len(self.passed_criteria)})
"""
        for criteria in self.passed_criteria:
            md += f"- {criteria}\n"
        
        md += f"\n### ❌ Failed ({len(self.failed_criteria)})\n"
        for criteria in self.failed_criteria:
            md += f"- {criteria}\n"
        
        if self.waived_criteria:
            md += f"\n### ⚠️ Waived ({len(self.waived_criteria)})\n"
            for criteria in self.waived_criteria:
                md += f"- {criteria}\n"
        
        if self.issues:
            md += f"\n## Issues Found ({len(self.issues)})\n\n"
            
            # Group by severity
            critical = [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]
            high = [i for i in self.issues if i.severity == IssueSeverity.HIGH]
            medium = [i for i in self.issues if i.severity == IssueSeverity.MEDIUM]
            low = [i for i in self.issues if i.severity == IssueSeverity.LOW]
            
            for severity_group, label in [(critical, "🔴 Critical"), 
                                         (high, "🟠 High"),
                                         (medium, "🟡 Medium"), 
                                         (low, "🟢 Low")]:
                if severity_group:
                    md += f"\n### {label} Issues\n"
                    for issue in severity_group:
                        status = "✅ Resolved" if issue.resolved_at else ("⚠️ Waived" if issue.waived else "❌ Open")
                        md += f"""
#### {issue.title} ({issue.id}) - {status}
- **Category**: {issue.category.value}
- **Finding**: {issue.finding}
- **Expected**: {issue.expected}
- **Impact**: {issue.impact}
- **Action**: {issue.suggested_action}
"""
                        if issue.waived:
                            md += f"- **Waiver Reason**: {issue.waiver_reason} (by {issue.waived_by})\n"
                        if issue.resolved_at:
                            md += f"- **Resolution**: {issue.resolution}\n"
        
        if self.recommendations:
            md += "\n## Recommendations\n"
            for i, rec in enumerate(self.recommendations, 1):
                md += f"{i}. {rec}\n"
        
        if self.notes:
            md += f"\n## Notes\n{self.notes}\n"
        
        return md


class QualityGate:
    """Quality gate implementation for assessing work items"""
    
    def __init__(self, gate_name: str, gate_type: str = "standard"):
        self.gate_name = gate_name
        self.gate_type = gate_type
        self.criteria: Dict[str, Any] = {}
        self.thresholds: Dict[str, float] = {
            'min_coverage': 80.0,
            'min_test_coverage': 70.0,
            'max_critical_issues': 0,
            'max_high_issues': 3,
            'min_security_score': 75.0,
            'min_performance_score': 70.0,
            'min_overall_score': 75.0
        }
        self.issue_counter = 0
        
    def set_thresholds(self, thresholds: Dict[str, float]):
        """Update quality thresholds"""
        self.thresholds.update(thresholds)
    
    def add_criteria(self, name: str, check_function: callable, required: bool = True):
        """Add assessment criteria"""
        self.criteria[name] = {
            'check': check_function,
            'required': required
        }
    
    def _generate_issue_id(self) -> str:
        """Generate unique issue ID"""
        self.issue_counter += 1
        return f"QI-{datetime.now().strftime('%Y%m%d')}-{self.issue_counter:04d}"
    
    async def assess(self, 
                     target: Any,
                     assessor: str,
                     checklist_results: Optional[Dict] = None,
                     custom_checks: Optional[List[callable]] = None) -> GateReport:
        """
        Perform quality gate assessment
        
        Args:
            target: The item to assess (story, epic, code, etc.)
            assessor: Who is performing the assessment
            checklist_results: Results from checklist execution
            custom_checks: Additional custom check functions
            
        Returns:
            GateReport with assessment results
        """
        issues = []
        passed_criteria = []
        failed_criteria = []
        waived_criteria = []
        recommendations = []
        
        # Initialize metrics
        metrics = QualityMetrics()
        
        # Process checklist results if provided
        if checklist_results:
            metrics.total_checks = checklist_results.get('total_items', 0)
            metrics.passed_checks = checklist_results.get('checked_items', 0)
            metrics.failed_checks = checklist_results.get('unchecked_items', 0)
            metrics.skipped_checks = checklist_results.get('na_items', 0)
            
            if metrics.total_checks > 0:
                metrics.coverage_percentage = (metrics.passed_checks / metrics.total_checks) * 100
            
            # Create issues from failed checklist items
            for item in checklist_results.get('items', []):
                if item['status'] == 'unchecked' and not item.get('waived'):
                    issue = QualityIssue(
                        id=self._generate_issue_id(),
                        title=f"Checklist: {item['text'][:50]}",
                        description=item['text'],
                        severity=IssueSeverity.MEDIUM,
                        category=IssueCategory.COMPLIANCE,
                        finding=f"Checklist item not satisfied",
                        expected="Item should be checked or justified",
                        impact="Quality criteria not met",
                        suggested_action=item.get('justification', 'Address the checklist item')
                    )
                    issues.append(issue)
        
        # Run standard criteria checks
        for criteria_name, criteria_info in self.criteria.items():
            try:
                result = await criteria_info['check'](target, metrics)
                if result:
                    passed_criteria.append(criteria_name)
                else:
                    if criteria_info['required']:
                        failed_criteria.append(criteria_name)
                    else:
                        waived_criteria.append(criteria_name)
            except Exception as e:
                logger.error(f"Error checking criteria {criteria_name}: {e}")
                failed_criteria.append(f"{criteria_name} (error)")
        
        # Run custom checks if provided
        if custom_checks:
            for check in custom_checks:
                try:
                    check_result = await check(target, metrics, issues)
                    if check_result:
                        if isinstance(check_result, QualityIssue):
                            issues.append(check_result)
                        elif isinstance(check_result, list):
                            issues.extend(check_result)
                except Exception as e:
                    logger.error(f"Error in custom check: {e}")
        
        # Apply threshold checks
        critical_issues = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == IssueSeverity.HIGH])
        
        # Calculate some default metrics if not set
        if metrics.security_score == 0:
            security_issues = len([i for i in issues if i.category == IssueCategory.SECURITY])
            metrics.security_score = max(0, 100 - (security_issues * 20))
        
        if metrics.performance_score == 0:
            perf_issues = len([i for i in issues if i.category == IssueCategory.PERFORMANCE])
            metrics.performance_score = max(0, 100 - (perf_issues * 15))
        
        # Determine gate status
        status = GateStatus.PASS
        status_reason = "All quality criteria met"
        
        if critical_issues > self.thresholds['max_critical_issues']:
            status = GateStatus.FAIL
            status_reason = f"Found {critical_issues} critical issues (max allowed: {self.thresholds['max_critical_issues']})"
            recommendations.append(f"Fix all {critical_issues} critical issues before proceeding")
        elif high_issues > self.thresholds['max_high_issues']:
            status = GateStatus.CONCERNS
            status_reason = f"Found {high_issues} high severity issues (max allowed: {self.thresholds['max_high_issues']})"
            recommendations.append(f"Address the {high_issues} high severity issues")
        elif metrics.coverage_percentage < self.thresholds['min_coverage']:
            status = GateStatus.CONCERNS
            status_reason = f"Coverage {metrics.coverage_percentage:.1f}% below threshold {self.thresholds['min_coverage']}%"
            recommendations.append(f"Improve coverage to at least {self.thresholds['min_coverage']}%")
        elif metrics.security_score < self.thresholds['min_security_score']:
            status = GateStatus.CONCERNS
            status_reason = f"Security score {metrics.security_score:.1f} below threshold {self.thresholds['min_security_score']}"
            recommendations.append("Address security vulnerabilities")
        elif failed_criteria:
            status = GateStatus.FAIL if len(failed_criteria) > 3 else GateStatus.CONCERNS
            status_reason = f"Failed {len(failed_criteria)} required criteria"
            recommendations.append("Address all failed criteria")
        
        # Add general recommendations based on metrics
        overall_score = metrics.calculate_overall_score()
        if overall_score < self.thresholds['min_overall_score']:
            recommendations.append(f"Improve overall quality score from {overall_score:.1f} to at least {self.thresholds['min_overall_score']}")
        
        if metrics.technical_debt_hours > 40:
            recommendations.append(f"Consider addressing {metrics.technical_debt_hours:.1f} hours of technical debt")
        
        if metrics.test_coverage < self.thresholds['min_test_coverage']:
            recommendations.append(f"Increase test coverage from {metrics.test_coverage:.1f}% to at least {self.thresholds['min_test_coverage']}%")
        
        # Create report
        report = GateReport(
            gate_id=f"QG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            gate_name=self.gate_name,
            status=status,
            assessed_at=datetime.now(),
            assessed_by=assessor,
            target_type=type(target).__name__ if hasattr(target, '__class__') else 'Unknown',
            target_id=getattr(target, 'id', 'unknown'),
            target_name=getattr(target, 'name', str(target)[:100]),
            issues=issues,
            metrics=metrics,
            status_reason=status_reason,
            recommendations=recommendations,
            passed_criteria=passed_criteria,
            failed_criteria=failed_criteria,
            waived_criteria=waived_criteria
        )
        
        return report
    
    def create_waiver(self, report: GateReport, waiver_reason: str, waived_by: str) -> GateReport:
        """Create a waived version of a failed gate report"""
        report.status = GateStatus.WAIVED
        report.status_reason = f"WAIVED: {waiver_reason}"
        report.notes = f"Original status: {report.status.value}\nWaived by: {waived_by}\nReason: {waiver_reason}\n{report.notes}"
        return report


class QualityTracker:
    """Tracks quality metrics and gate results over time"""
    
    def __init__(self, storage_path: str = "./storage/quality"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.reports: List[GateReport] = []
        self.gates: Dict[str, QualityGate] = {}
        
    def register_gate(self, gate: QualityGate):
        """Register a quality gate"""
        self.gates[gate.gate_name] = gate
    
    async def execute_gate(self, 
                           gate_name: str,
                           target: Any,
                           assessor: str,
                           **kwargs) -> GateReport:
        """Execute a registered quality gate"""
        if gate_name not in self.gates:
            raise ValueError(f"Gate '{gate_name}' not registered")
        
        gate = self.gates[gate_name]
        report = await gate.assess(target, assessor, **kwargs)
        
        # Store report
        self.reports.append(report)
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: GateReport):
        """Save report to storage"""
        filename = f"{report.gate_id}.json"
        filepath = self.storage_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        # Also save markdown version
        md_filename = f"{report.gate_id}.md"
        md_filepath = self.storage_path / md_filename
        
        with open(md_filepath, 'w') as f:
            f.write(report.to_markdown())
    
    def get_reports_by_target(self, target_id: str) -> List[GateReport]:
        """Get all reports for a specific target"""
        return [r for r in self.reports if r.target_id == target_id]
    
    def get_reports_by_status(self, status: GateStatus) -> List[GateReport]:
        """Get all reports with a specific status"""
        return [r for r in self.reports if r.status == status]
    
    def get_quality_trends(self, days: int = 30) -> Dict[str, Any]:
        """Calculate quality trends over time"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_reports = [r for r in self.reports if r.assessed_at >= cutoff]
        
        if not recent_reports:
            return {}
        
        trends = {
            'total_assessments': len(recent_reports),
            'pass_rate': len([r for r in recent_reports if r.status == GateStatus.PASS]) / len(recent_reports) * 100,
            'fail_rate': len([r for r in recent_reports if r.status == GateStatus.FAIL]) / len(recent_reports) * 100,
            'average_score': sum(r.metrics.calculate_overall_score() for r in recent_reports) / len(recent_reports),
            'total_issues': sum(len(r.issues) for r in recent_reports),
            'critical_issues': sum(len([i for i in r.issues if i.severity == IssueSeverity.CRITICAL]) for r in recent_reports),
            'resolved_issues': sum(len([i for i in r.issues if i.resolved_at]) for r in recent_reports),
            'waived_issues': sum(len([i for i in r.issues if i.waived]) for r in recent_reports)
        }
        
        return trends
    
    def generate_summary_report(self, days: int = 7) -> str:
        """Generate a summary report of recent quality assessments"""
        trends = self.get_quality_trends(days)
        
        if not trends:
            return "No quality assessments in the specified period"
        
        summary = f"""# Quality Summary Report
        
## Period: Last {days} days

## Overview
- **Total Assessments**: {trends['total_assessments']}
- **Pass Rate**: {trends['pass_rate']:.1f}%
- **Fail Rate**: {trends['fail_rate']:.1f}%
- **Average Quality Score**: {trends['average_score']:.1f}/100

## Issues
- **Total Issues Found**: {trends['total_issues']}
- **Critical Issues**: {trends['critical_issues']}
- **Resolved Issues**: {trends['resolved_issues']}
- **Waived Issues**: {trends['waived_issues']}

## Recent Failed Assessments
"""
        cutoff = datetime.now() - timedelta(days=days)
        failed = [r for r in self.reports if r.assessed_at >= cutoff and r.status == GateStatus.FAIL]
        
        for report in failed[:5]:  # Show top 5
            summary += f"- {report.target_name}: {report.status_reason}\n"
        
        return summary


# Create predefined gates for common scenarios
def create_story_gate() -> QualityGate:
    """Create a quality gate for user stories"""
    gate = QualityGate("Story Quality Gate", "story")
    
    # Define story-specific thresholds
    gate.set_thresholds({
        'min_coverage': 85.0,
        'min_test_coverage': 80.0,
        'max_critical_issues': 0,
        'max_high_issues': 2,
        'min_security_score': 80.0,
        'min_performance_score': 75.0,
        'min_overall_score': 80.0
    })
    
    # Add story-specific criteria
    async def has_acceptance_criteria(target, metrics):
        return hasattr(target, 'acceptance_criteria') and len(target.acceptance_criteria) > 0
    
    async def has_story_points(target, metrics):
        return hasattr(target, 'story_points') and target.story_points > 0
    
    async def has_description(target, metrics):
        return hasattr(target, 'description') and len(target.description) > 50
    
    gate.add_criteria("Has Acceptance Criteria", has_acceptance_criteria)
    gate.add_criteria("Has Story Points", has_story_points)
    gate.add_criteria("Has Adequate Description", has_description)
    
    return gate


def create_release_gate() -> QualityGate:
    """Create a quality gate for releases"""
    gate = QualityGate("Release Quality Gate", "release")
    
    # Define release-specific thresholds (stricter)
    gate.set_thresholds({
        'min_coverage': 90.0,
        'min_test_coverage': 85.0,
        'max_critical_issues': 0,
        'max_high_issues': 0,
        'min_security_score': 90.0,
        'min_performance_score': 85.0,
        'min_overall_score': 85.0
    })
    
    return gate


def create_sprint_gate() -> QualityGate:
    """Create a quality gate for sprint completion"""
    gate = QualityGate("Sprint Quality Gate", "sprint")
    
    gate.set_thresholds({
        'min_coverage': 80.0,
        'min_test_coverage': 75.0,
        'max_critical_issues': 0,
        'max_high_issues': 5,
        'min_security_score': 75.0,
        'min_performance_score': 70.0,
        'min_overall_score': 75.0
    })
    
    return gate


# Example usage and testing
async def test_quality_gate():
    """Test the quality gate system"""
    
    # Create a tracker
    tracker = QualityTracker()
    
    # Register gates
    tracker.register_gate(create_story_gate())
    tracker.register_gate(create_release_gate())
    tracker.register_gate(create_sprint_gate())
    
    # Create a mock story for testing
    class MockStory:
        def __init__(self):
            self.id = "STORY-123"
            self.name = "Implement user authentication"
            self.description = "As a user, I want to be able to log in securely so that I can access my personal data"
            self.acceptance_criteria = [
                "User can enter username and password",
                "System validates credentials",
                "User receives error message for invalid credentials",
                "User is redirected to dashboard on successful login"
            ]
            self.story_points = 5
    
    story = MockStory()
    
    # Mock checklist results
    checklist_results = {
        'total_items': 10,
        'checked_items': 8,
        'unchecked_items': 2,
        'na_items': 0,
        'items': [
            {'text': 'Code is properly documented', 'status': 'checked'},
            {'text': 'Unit tests are written', 'status': 'unchecked', 'justification': 'Will add in next iteration'},
            {'text': 'Security review completed', 'status': 'unchecked'}
        ]
    }
    
    # Execute gate
    report = await tracker.execute_gate(
        "Story Quality Gate",
        story,
        "qa_engineer_01",
        checklist_results=checklist_results
    )
    
    # Print report
    print(report.to_markdown())
    
    # Get trends
    trends = tracker.get_quality_trends(30)
    print(f"\nQuality Trends: {json.dumps(trends, indent=2)}")
    
    # Generate summary
    summary = tracker.generate_summary_report(7)
    print(f"\n{summary}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_quality_gate())