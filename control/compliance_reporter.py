"""
Compliance Reporter System

Generates comprehensive compliance reports in multiple formats.
Integrates with the compliance tracker to provide detailed insights and recommendations.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics.compliance_tracker import (
    ComplianceTracker, ComplianceMetrics, Violation,
    ViolationType, ViolationSeverity, ViolationStatus, ComplianceStatus
)


class ReportFormat(Enum):
    """Supported report formats"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    EXECUTIVE = "executive"  # Executive summary format


class ReportPeriod(Enum):
    """Standard reporting periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class ComplianceReporter:
    """
    Generates comprehensive compliance reports
    """
    
    def __init__(self, compliance_tracker: Optional[ComplianceTracker] = None):
        """
        Initialize compliance reporter
        
        Args:
            compliance_tracker: Reference to compliance tracker
        """
        self.tracker = compliance_tracker or ComplianceTracker()
        self.report_cache: Dict[str, Tuple[str, datetime]] = {}
        self.cache_ttl = 300  # 5 minutes
    
    def generate_report(self,
                       format: ReportFormat = ReportFormat.MARKDOWN,
                       period: ReportPeriod = ReportPeriod.WEEKLY,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       team_id: Optional[str] = None,
                       include_recommendations: bool = True) -> str:
        """
        Generate a compliance report
        
        Args:
            format: Report format
            period: Reporting period
            start_date: Custom start date
            end_date: Custom end date
            team_id: Filter by team
            include_recommendations: Include recommendations
            
        Returns:
            Generated report
        """
        # Determine date range
        if period != ReportPeriod.CUSTOM:
            end_date = datetime.now()
            if period == ReportPeriod.DAILY:
                start_date = end_date - timedelta(days=1)
            elif period == ReportPeriod.WEEKLY:
                start_date = end_date - timedelta(weeks=1)
            elif period == ReportPeriod.MONTHLY:
                start_date = end_date - timedelta(days=30)
            elif period == ReportPeriod.QUARTERLY:
                start_date = end_date - timedelta(days=90)
        
        # Check cache
        cache_key = f"{format.value}_{period.value}_{team_id}_{start_date}_{end_date}"
        if cache_key in self.report_cache:
            cached_report, cached_time = self.report_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_report
        
        # Generate report based on format
        if format == ReportFormat.MARKDOWN:
            report = self._generate_markdown_report(
                start_date, end_date, team_id, include_recommendations
            )
        elif format == ReportFormat.JSON:
            report = self._generate_json_report(
                start_date, end_date, team_id
            )
        elif format == ReportFormat.HTML:
            report = self._generate_html_report(
                start_date, end_date, team_id, include_recommendations
            )
        elif format == ReportFormat.EXECUTIVE:
            report = self._generate_executive_report(
                start_date, end_date, team_id
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Cache report
        self.report_cache[cache_key] = (report, datetime.now())
        
        return report
    
    def _generate_markdown_report(self,
                                 start_date: Optional[datetime],
                                 end_date: Optional[datetime],
                                 team_id: Optional[str],
                                 include_recommendations: bool) -> str:
        """Generate markdown format report"""
        # Get data
        metrics = self.tracker.calculate_metrics(since=start_date, team_id=team_id)
        violations = self.tracker.get_violations(
            since=start_date, team_id=team_id, limit=1000
        )
        
        # Build report
        report = f"""# Compliance Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Period**: {start_date.strftime('%Y-%m-%d') if start_date else 'All Time'} to {end_date.strftime('%Y-%m-%d') if end_date else 'Present'}
"""
        
        if team_id:
            report += f"**Team**: {team_id}\n"
        
        report += f"""
## Executive Summary

- **Compliance Status**: {self._format_status(metrics.compliance_status)}
- **Compliance Score**: {metrics.compliance_score:.1f}/100
- **Total Violations**: {metrics.total_violations}
- **Open Issues**: {metrics.open_violations}
- **Resolution Rate**: {self._calculate_resolution_rate(metrics):.1f}%

## Violation Analysis

### By Severity
"""
        
        # Severity breakdown
        for severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH, 
                        ViolationSeverity.MEDIUM, ViolationSeverity.LOW]:
            count = metrics.violations_by_severity.get(severity.value, 0)
            percentage = (count / metrics.total_violations * 100) if metrics.total_violations > 0 else 0
            emoji = self._get_severity_emoji(severity)
            report += f"- {emoji} **{severity.value.title()}**: {count} ({percentage:.1f}%)\n"
        
        report += "\n### By Category\n"
        
        # Category breakdown
        for vtype, count in sorted(metrics.violations_by_type.items(), 
                                  key=lambda x: x[1], reverse=True):
            percentage = (count / metrics.total_violations * 100) if metrics.total_violations > 0 else 0
            report += f"- **{vtype.title()}**: {count} ({percentage:.1f}%)\n"
        
        # Recent violations
        report += "\n## Recent Violations\n\n"
        
        recent_violations = sorted(violations, key=lambda v: v.timestamp, reverse=True)[:10]
        
        if recent_violations:
            report += "| Time | Severity | Type | Agent | Description | Status |\n"
            report += "|------|----------|------|-------|-------------|--------|\n"
            
            for violation in recent_violations:
                time_str = violation.timestamp.strftime('%m-%d %H:%M')
                severity_emoji = self._get_severity_emoji(violation.severity)
                status_emoji = self._get_status_emoji(violation.status)
                description = violation.description[:50] + "..." if len(violation.description) > 50 else violation.description
                
                report += f"| {time_str} | {severity_emoji} {violation.severity.value} | "
                report += f"{violation.type.value} | {violation.agent_id} | "
                report += f"{description} | {status_emoji} {violation.status.value} |\n"
        else:
            report += "*No violations in this period*\n"
        
        # Performance metrics
        report += "\n## Performance Metrics\n\n"
        
        if metrics.mean_resolution_time:
            hours = metrics.mean_resolution_time / 3600
            report += f"- **Mean Resolution Time**: {hours:.1f} hours\n"
        
        resolution_rate = self._calculate_resolution_rate(metrics)
        report += f"- **Resolution Rate**: {resolution_rate:.1f}%\n"
        
        if metrics.trends:
            report += "\n### Trends\n\n"
            
            for period in [7, 30, 90]:
                key = f'violation_rate_{period}d'
                if key in metrics.trends:
                    rate = metrics.trends[key]
                    trend = self._calculate_trend(metrics.trends, period)
                    report += f"- **{period}-day rate**: {rate:.2f} violations/day {trend}\n"
        
        # Top violators
        report += "\n## Top Violators\n\n"
        agent_violations = self._get_top_violators(violations, 5)
        
        if agent_violations:
            report += "| Agent | Violations | Critical | High | Medium | Low |\n"
            report += "|-------|------------|----------|------|--------|-----|\n"
            
            for agent_id, stats in agent_violations:
                report += f"| {agent_id} | {stats['total']} | "
                report += f"{stats['critical']} | {stats['high']} | "
                report += f"{stats['medium']} | {stats['low']} |\n"
        else:
            report += "*No violations to report*\n"
        
        # Recommendations
        if include_recommendations:
            recommendations = self._generate_recommendations(metrics, violations)
            if recommendations:
                report += "\n## Recommendations\n\n"
                for i, recommendation in enumerate(recommendations, 1):
                    report += f"{i}. {recommendation}\n"
        
        # Compliance attestation
        report += "\n## Compliance Attestation\n\n"
        if metrics.compliance_status == ComplianceStatus.COMPLIANT:
            report += "✅ **The system is operating within compliance parameters.**\n"
        elif metrics.compliance_status == ComplianceStatus.MINOR_ISSUES:
            report += "⚠️ **The system has minor compliance issues that should be addressed.**\n"
        elif metrics.compliance_status == ComplianceStatus.MAJOR_ISSUES:
            report += "⚠️ **The system has major compliance issues requiring immediate attention.**\n"
        elif metrics.compliance_status == ComplianceStatus.NON_COMPLIANT:
            report += "❌ **The system is non-compliant and requires urgent remediation.**\n"
        else:  # CRITICAL
            report += "🚨 **CRITICAL: The system has critical compliance violations requiring immediate action.**\n"
        
        return report
    
    def _generate_json_report(self,
                            start_date: Optional[datetime],
                            end_date: Optional[datetime],
                            team_id: Optional[str]) -> str:
        """Generate JSON format report"""
        metrics = self.tracker.calculate_metrics(since=start_date, team_id=team_id)
        violations = self.tracker.get_violations(
            since=start_date, team_id=team_id, limit=1000
        )
        
        report_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                },
                'team_id': team_id
            },
            'summary': {
                'compliance_status': metrics.compliance_status.value,
                'compliance_score': metrics.compliance_score,
                'total_violations': metrics.total_violations,
                'open_violations': metrics.open_violations,
                'resolved_violations': metrics.resolved_violations,
                'waived_violations': metrics.waived_violations,
                'resolution_rate': self._calculate_resolution_rate(metrics),
                'mean_resolution_time_hours': metrics.mean_resolution_time / 3600 if metrics.mean_resolution_time else None
            },
            'breakdown': {
                'by_severity': metrics.violations_by_severity,
                'by_type': metrics.violations_by_type
            },
            'trends': metrics.trends,
            'violations': [v.to_dict() for v in violations[:100]],  # Limit to 100
            'top_violators': dict(self._get_top_violators(violations, 10)),
            'recommendations': self._generate_recommendations(metrics, violations)
        }
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _generate_html_report(self,
                            start_date: Optional[datetime],
                            end_date: Optional[datetime],
                            team_id: Optional[str],
                            include_recommendations: bool) -> str:
        """Generate HTML format report"""
        # Get markdown report first
        markdown_report = self._generate_markdown_report(
            start_date, end_date, team_id, include_recommendations
        )
        
        # Convert to HTML (basic conversion)
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 30px;
        }}
        h1 {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric {{
            display: inline-block;
            padding: 10px 20px;
            margin: 10px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .status-compliant {{
            color: #27ae60;
        }}
        .status-issues {{
            color: #f39c12;
        }}
        .status-noncompliant {{
            color: #e74c3c;
        }}
        .recommendation {{
            background: #ecf0f1;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #3498db;
        }}
        ul {{
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        li {{
            margin: 10px 0;
        }}
        strong {{
            color: #2c3e50;
        }}
        code {{
            background: #ecf0f1;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
"""
        
        # Convert markdown to HTML (simple conversion)
        import re
        
        # Convert headers
        html_content = markdown_report
        html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        
        # Convert bold
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        
        # Convert lists
        html_content = re.sub(r'^- (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
        
        # Convert tables (basic)
        lines = html_content.split('\n')
        in_table = False
        new_lines = []
        
        for line in lines:
            if '|' in line and '---' in line:
                # Skip separator line
                continue
            elif '|' in line:
                if not in_table:
                    new_lines.append('<table>')
                    in_table = True
                    # Header row
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    new_lines.append('<tr>')
                    for cell in cells:
                        new_lines.append(f'<th>{cell}</th>')
                    new_lines.append('</tr>')
                else:
                    # Data row
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    new_lines.append('<tr>')
                    for cell in cells:
                        new_lines.append(f'<td>{cell}</td>')
                    new_lines.append('</tr>')
            else:
                if in_table:
                    new_lines.append('</table>')
                    in_table = False
                new_lines.append(line)
        
        if in_table:
            new_lines.append('</table>')
        
        html_content = '\n'.join(new_lines)
        
        html += html_content
        html += """
</body>
</html>
"""
        
        return html
    
    def _generate_executive_report(self,
                                  start_date: Optional[datetime],
                                  end_date: Optional[datetime],
                                  team_id: Optional[str]) -> str:
        """Generate executive summary report"""
        metrics = self.tracker.calculate_metrics(since=start_date, team_id=team_id)
        violations = self.tracker.get_violations(
            since=start_date, team_id=team_id, limit=100
        )
        
        report = f"""# Executive Compliance Summary

**Date**: {datetime.now().strftime('%Y-%m-%d')}

## Status: {self._format_status(metrics.compliance_status)}

### Key Metrics
- **Compliance Score**: {metrics.compliance_score:.0f}%
- **Open Issues**: {metrics.open_violations}
- **Resolution Rate**: {self._calculate_resolution_rate(metrics):.0f}%

### Critical Issues
"""
        
        # Get critical violations
        critical_violations = [v for v in violations 
                              if v.severity == ViolationSeverity.CRITICAL 
                              and v.status != ViolationStatus.RESOLVED]
        
        if critical_violations:
            for v in critical_violations[:3]:
                report += f"- {v.description} (Agent: {v.agent_id})\n"
        else:
            report += "- No critical issues\n"
        
        # Risk assessment
        risk_level = self._assess_risk_level(metrics)
        report += f"\n### Risk Assessment: {risk_level}\n"
        
        # Top recommendations
        recommendations = self._generate_recommendations(metrics, violations)[:3]
        if recommendations:
            report += "\n### Priority Actions\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"
        
        # Trend
        report += "\n### 30-Day Trend: "
        if metrics.trends and 'violation_rate_30d' in metrics.trends:
            current_rate = metrics.trends['violation_rate_30d']
            if 'violation_rate_7d' in metrics.trends:
                recent_rate = metrics.trends['violation_rate_7d']
                if recent_rate < current_rate:
                    report += "📈 Improving\n"
                elif recent_rate > current_rate * 1.2:
                    report += "📉 Deteriorating\n"
                else:
                    report += "➡️ Stable\n"
            else:
                report += "➡️ Stable\n"
        else:
            report += "No trend data available\n"
        
        return report
    
    def _format_status(self, status: ComplianceStatus) -> str:
        """Format compliance status with emoji"""
        status_map = {
            ComplianceStatus.COMPLIANT: "✅ Compliant",
            ComplianceStatus.MINOR_ISSUES: "⚠️ Minor Issues",
            ComplianceStatus.MAJOR_ISSUES: "⚠️ Major Issues",
            ComplianceStatus.NON_COMPLIANT: "❌ Non-Compliant",
            ComplianceStatus.CRITICAL: "🚨 Critical"
        }
        return status_map.get(status, status.value)
    
    def _get_severity_emoji(self, severity: ViolationSeverity) -> str:
        """Get emoji for severity level"""
        emoji_map = {
            ViolationSeverity.LOW: "🟢",
            ViolationSeverity.MEDIUM: "🟡",
            ViolationSeverity.HIGH: "🟠",
            ViolationSeverity.CRITICAL: "🔴"
        }
        return emoji_map.get(severity, "⚪")
    
    def _get_status_emoji(self, status: ViolationStatus) -> str:
        """Get emoji for violation status"""
        emoji_map = {
            ViolationStatus.OPEN: "📂",
            ViolationStatus.INVESTIGATING: "🔍",
            ViolationStatus.MITIGATING: "🔧",
            ViolationStatus.RESOLVED: "✅",
            ViolationStatus.ESCALATED: "⬆️",
            ViolationStatus.WAIVED: "📝"
        }
        return emoji_map.get(status, "❓")
    
    def _calculate_resolution_rate(self, metrics: ComplianceMetrics) -> float:
        """Calculate resolution rate percentage"""
        total_closed = metrics.resolved_violations + metrics.waived_violations
        total_processed = total_closed + metrics.open_violations
        
        if total_processed == 0:
            return 100.0
        
        return (total_closed / total_processed) * 100
    
    def _calculate_trend(self, trends: Dict[str, Any], period: int) -> str:
        """Calculate trend indicator"""
        current_key = f'violation_rate_{period}d'
        
        if current_key not in trends:
            return ""
        
        current_rate = trends[current_key]
        
        # Compare with longer period
        if period == 7 and 'violation_rate_30d' in trends:
            baseline = trends['violation_rate_30d']
        elif period == 30 and 'violation_rate_90d' in trends:
            baseline = trends['violation_rate_90d']
        else:
            return ""
        
        if current_rate < baseline * 0.8:
            return "📈"  # Improving
        elif current_rate > baseline * 1.2:
            return "📉"  # Worsening
        else:
            return "➡️"  # Stable
    
    def _get_top_violators(self, violations: List[Violation], 
                          limit: int = 5) -> List[Tuple[str, Dict[str, int]]]:
        """Get agents with most violations"""
        agent_stats = {}
        
        for violation in violations:
            if violation.agent_id not in agent_stats:
                agent_stats[violation.agent_id] = {
                    'total': 0,
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }
            
            agent_stats[violation.agent_id]['total'] += 1
            agent_stats[violation.agent_id][violation.severity.value] += 1
        
        # Sort by total violations
        sorted_agents = sorted(agent_stats.items(), 
                             key=lambda x: x[1]['total'], 
                             reverse=True)
        
        return sorted_agents[:limit]
    
    def _generate_recommendations(self, metrics: ComplianceMetrics, 
                                 violations: List[Violation]) -> List[str]:
        """Generate recommendations based on compliance data"""
        recommendations = []
        
        # Critical violations
        critical_count = metrics.violations_by_severity.get('critical', 0)
        if critical_count > 0:
            recommendations.append(
                f"🚨 Address {critical_count} critical violation(s) immediately"
            )
        
        # High violation rate
        if metrics.trends and 'violation_rate_7d' in metrics.trends:
            rate = metrics.trends['violation_rate_7d']
            if rate > 5:
                recommendations.append(
                    f"⚠️ Reduce violation rate (currently {rate:.1f}/day)"
                )
        
        # Slow resolution
        if metrics.mean_resolution_time and metrics.mean_resolution_time > 7200:  # > 2 hours
            hours = metrics.mean_resolution_time / 3600
            recommendations.append(
                f"⏱️ Improve resolution time (currently {hours:.1f} hours)"
            )
        
        # Open violations backlog
        if metrics.open_violations > 20:
            recommendations.append(
                f"📊 Clear backlog of {metrics.open_violations} open violations"
            )
        
        # Ethical violations
        ethical_count = metrics.violations_by_type.get('ethical', 0)
        if ethical_count > 0:
            recommendations.append(
                f"🛡️ Review and strengthen ethical controls ({ethical_count} violations)"
            )
        
        # Safety violations
        safety_count = metrics.violations_by_type.get('safety', 0)
        if safety_count > 5:
            recommendations.append(
                f"🔒 Enhance safety monitoring ({safety_count} violations)"
            )
        
        # Resource violations
        resource_count = metrics.violations_by_type.get('resource', 0)
        if resource_count > 10:
            recommendations.append(
                f"💾 Optimize resource usage ({resource_count} violations)"
            )
        
        # Performance issues
        performance_count = metrics.violations_by_type.get('performance', 0)
        if performance_count > 10:
            recommendations.append(
                f"⚡ Address performance bottlenecks ({performance_count} violations)"
            )
        
        # Quality issues
        quality_count = metrics.violations_by_type.get('quality', 0)
        if quality_count > 5:
            recommendations.append(
                f"✨ Improve code quality standards ({quality_count} violations)"
            )
        
        # Compliance score
        if metrics.compliance_score < 80:
            recommendations.append(
                f"📈 Implement compliance improvement plan (score: {metrics.compliance_score:.0f}/100)"
            )
        
        # Top violators
        top_violators = self._get_top_violators(violations, 3)
        if top_violators and top_violators[0][1]['total'] > 10:
            agent_id = top_violators[0][0]
            count = top_violators[0][1]['total']
            recommendations.append(
                f"👤 Provide additional training for agent '{agent_id}' ({count} violations)"
            )
        
        return recommendations
    
    def _assess_risk_level(self, metrics: ComplianceMetrics) -> str:
        """Assess overall risk level"""
        if metrics.compliance_status == ComplianceStatus.CRITICAL:
            return "🔴 CRITICAL"
        elif metrics.compliance_status == ComplianceStatus.NON_COMPLIANT:
            return "🟠 HIGH"
        elif metrics.compliance_status == ComplianceStatus.MAJOR_ISSUES:
            return "🟡 MEDIUM"
        elif metrics.compliance_status == ComplianceStatus.MINOR_ISSUES:
            return "🟢 LOW"
        else:
            return "🟢 MINIMAL"
    
    def schedule_report(self,
                       format: ReportFormat,
                       period: ReportPeriod,
                       recipients: List[str],
                       output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Schedule automated report generation
        
        Args:
            format: Report format
            period: Reporting period
            recipients: List of recipients (email/webhook)
            output_path: Optional output file path
            
        Returns:
            Schedule configuration
        """
        schedule_config = {
            'format': format.value,
            'period': period.value,
            'recipients': recipients,
            'output_path': output_path,
            'created_at': datetime.now().isoformat(),
            'next_run': self._calculate_next_run(period),
            'enabled': True
        }
        
        # Save schedule configuration
        config_path = Path('storage/report_schedules.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        schedules = []
        if config_path.exists():
            with open(config_path, 'r') as f:
                schedules = json.load(f)
        
        schedules.append(schedule_config)
        
        with open(config_path, 'w') as f:
            json.dump(schedules, f, indent=2)
        
        return schedule_config
    
    def _calculate_next_run(self, period: ReportPeriod) -> str:
        """Calculate next report run time"""
        now = datetime.now()
        
        if period == ReportPeriod.DAILY:
            next_run = now + timedelta(days=1)
            next_run = next_run.replace(hour=0, minute=0, second=0)
        elif period == ReportPeriod.WEEKLY:
            days_ahead = 7 - now.weekday()  # Monday is 0
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=0, minute=0, second=0)
        elif period == ReportPeriod.MONTHLY:
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_run = now.replace(month=now.month + 1, day=1)
            next_run = next_run.replace(hour=0, minute=0, second=0)
        elif period == ReportPeriod.QUARTERLY:
            quarter_month = ((now.month - 1) // 3 + 1) * 3 + 1
            if quarter_month > 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_run = now.replace(month=quarter_month, day=1)
            next_run = next_run.replace(hour=0, minute=0, second=0)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run.isoformat()
    
    def export_report(self, 
                     report: str,
                     output_path: str,
                     format: ReportFormat):
        """
        Export report to file
        
        Args:
            report: Report content
            output_path: Output file path
            format: Report format
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add appropriate extension
        if format == ReportFormat.MARKDOWN:
            if not output_path.suffix:
                output_path = output_path.with_suffix('.md')
        elif format == ReportFormat.JSON:
            if not output_path.suffix:
                output_path = output_path.with_suffix('.json')
        elif format == ReportFormat.HTML:
            if not output_path.suffix:
                output_path = output_path.with_suffix('.html')
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        print(f"Report exported to: {output_path}")


if __name__ == "__main__":
    # Test compliance reporter
    from compliance_tracker import ComplianceTracker, ViolationType, ViolationSeverity
    
    # Create tracker with test data
    tracker = ComplianceTracker()
    
    # Add some test violations
    tracker.record_violation(
        type=ViolationType.ETHICAL,
        severity=ViolationSeverity.HIGH,
        agent_id='test_agent_1',
        description='Attempted to access restricted user data',
        details={'resource': '/user/private', 'action': 'read'},
        detected_by='access_control'
    )
    
    tracker.record_violation(
        type=ViolationType.SAFETY,
        severity=ViolationSeverity.CRITICAL,
        agent_id='test_agent_2',
        description='CPU usage exceeded critical threshold',
        details={'cpu_percent': 98.5, 'duration': 120},
        detected_by='safety_monitor'
    )
    
    tracker.record_violation(
        type=ViolationType.PERFORMANCE,
        severity=ViolationSeverity.MEDIUM,
        agent_id='test_agent_1',
        description='Response time exceeded threshold',
        details={'response_time_ms': 8500, 'endpoint': '/api/process'},
        detected_by='performance_monitor'
    )
    
    # Create reporter
    reporter = ComplianceReporter(tracker)
    
    # Generate reports in different formats
    print("Generating Markdown report...")
    markdown_report = reporter.generate_report(
        format=ReportFormat.MARKDOWN,
        period=ReportPeriod.WEEKLY
    )
    print(markdown_report)
    
    print("\n" + "="*50 + "\n")
    print("Generating Executive report...")
    executive_report = reporter.generate_report(
        format=ReportFormat.EXECUTIVE,
        period=ReportPeriod.WEEKLY
    )
    print(executive_report)
    
    print("\n" + "="*50 + "\n")
    print("Generating JSON report...")
    json_report = reporter.generate_report(
        format=ReportFormat.JSON,
        period=ReportPeriod.WEEKLY
    )
    print(json_report[:500] + "...")  # Print first 500 chars
    
    # Export report
    reporter.export_report(
        markdown_report,
        'reports/compliance_weekly.md',
        ReportFormat.MARKDOWN
    )
    
    print("\nCompliance reporter test completed!")