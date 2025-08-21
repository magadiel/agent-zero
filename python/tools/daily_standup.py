"""
Daily Standup Tool for Agent-Zero

This tool integrates the standup facilitator with Agent-Zero's tool system,
enabling agents to conduct and participate in daily standup ceremonies.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agile'))

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from agile.standup_facilitator import (
    StandupFacilitator, 
    TeamMemberStatus, 
    BlockerSeverity,
    StandupReport
)

# Try to import sprint manager if available
try:
    from agile.sprint_manager import SprintManager
except ImportError:
    SprintManager = None


class DailyStandup(Tool):
    """
    Tool for conducting daily standup ceremonies with AI agent teams.
    
    This tool allows agents to:
    - Facilitate daily standups
    - Report their status (yesterday, today, blockers)
    - Identify and track blockers
    - Generate standup reports
    - Analyze team trends
    """
    
    def __init__(self, agent, name="daily_standup", args={}, message=""):
        super().__init__(agent, name, args, message)
        self.facilitators: Dict[str, StandupFacilitator] = {}
    
    async def execute(self, **kwargs):
        """
        Execute standup-related operations
        
        Supported operations:
        - conduct: Conduct a full standup ceremony
        - report_status: Report individual agent status
        - get_blockers: Get current blockers
        - get_report: Get latest standup report
        - get_trends: Get blocker and participation trends
        - export: Export standup history
        """
        operation = kwargs.get('operation', 'conduct')
        team_id = kwargs.get('team_id', 'default_team')
        
        # Get or create facilitator for team
        if team_id not in self.facilitators:
            sprint_manager = await self._get_sprint_manager(team_id)
            self.facilitators[team_id] = StandupFacilitator(team_id, sprint_manager)
        
        facilitator = self.facilitators[team_id]
        
        try:
            if operation == 'conduct':
                return await self._conduct_standup(facilitator, **kwargs)
            elif operation == 'report_status':
                return await self._report_status(**kwargs)
            elif operation == 'get_blockers':
                return self._get_blockers(facilitator)
            elif operation == 'get_report':
                return self._get_latest_report(facilitator, **kwargs)
            elif operation == 'get_trends':
                return self._get_trends(facilitator, **kwargs)
            elif operation == 'export':
                return self._export_history(facilitator, **kwargs)
            else:
                return Response(
                    message=f"Unknown operation: {operation}",
                    data={
                        'error': f"Unknown operation: {operation}",
                        'supported_operations': [
                            'conduct', 'report_status', 'get_blockers', 
                            'get_report', 'get_trends', 'export'
                        ]
                    },
                    break_loop=False
                )
        except Exception as e:
            return Response(
                message=f"Error in daily standup: {str(e)}",
                data={'error': str(e)},
                break_loop=False
            )
    
    async def _conduct_standup(self, facilitator: StandupFacilitator, **kwargs) -> Response:
        """
        Conduct a full standup ceremony
        
        Args:
            facilitator: The standup facilitator
            **kwargs: Additional arguments including team_members
        
        Returns:
            Response with standup report
        """
        team_members = kwargs.get('team_members', [])
        
        if not team_members:
            # Try to get team members from context
            team_members = await self._get_team_members(facilitator.team_id)
        
        if not team_members:
            return Response(
                message="No team members found for standup",
                data={'error': 'No team members available'},
                break_loop=False
            )
        
        # Create status collection function
        async def collect_status(member):
            # If member is a dict with status info
            if isinstance(member, dict) and 'status' in member:
                return await self._create_status_from_dict(member)
            
            # Try to get status from agent
            if hasattr(member, 'report_standup_status'):
                return await member.report_standup_status()
            
            # Use default status
            return await self._create_default_status(member)
        
        # Conduct standup
        report = await facilitator.conduct_standup(team_members, collect_status)
        
        # Format response
        message = self._format_standup_summary(report)
        
        return Response(
            message=message,
            data={
                'standup_id': report.standup_id,
                'team_id': report.team_id,
                'date': report.date.isoformat(),
                'participants': report.participants,
                'blockers_count': len(report.blockers),
                'team_mood': report.team_mood,
                'sprint_progress': report.sprint_progress,
                'risks': report.risks_identified,
                'action_items': report.action_items,
                'full_report': report.to_dict()
            },
            break_loop=False
        )
    
    async def _report_status(self, **kwargs) -> Response:
        """
        Report individual agent status
        
        Args:
            **kwargs: Status information
        
        Returns:
            Response with confirmation
        """
        agent_id = kwargs.get('agent_id', self.agent.config.chat_id if self.agent else 'unknown')
        agent_name = kwargs.get('agent_name', self.agent.name if self.agent else 'Unknown Agent')
        
        status = TeamMemberStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            timestamp=datetime.now(),
            yesterday_completed=kwargs.get('yesterday', []),
            today_planned=kwargs.get('today', []),
            blockers=[{'description': b, 'severity': 'medium'} 
                     for b in kwargs.get('blockers', [])],
            help_needed=kwargs.get('help_needed', []),
            current_story=kwargs.get('current_story'),
            story_progress=kwargs.get('story_progress', 0.0),
            confidence_level=kwargs.get('confidence', 1.0),
            mood=kwargs.get('mood', 'neutral')
        )
        
        # Store status for later use in standup
        # This would typically be stored in a shared location
        
        return Response(
            message=f"Status reported for {agent_name}",
            data={
                'agent_id': agent_id,
                'status': status.to_dict()
            },
            break_loop=False
        )
    
    def _get_blockers(self, facilitator: StandupFacilitator) -> Response:
        """
        Get current active blockers
        
        Args:
            facilitator: The standup facilitator
        
        Returns:
            Response with blocker information
        """
        blockers = list(facilitator.active_blockers.values())
        
        if not blockers:
            return Response(
                message="No active blockers",
                data={'blockers': []},
                break_loop=False
            )
        
        critical = [b for b in blockers if b.severity == BlockerSeverity.CRITICAL]
        high = [b for b in blockers if b.severity == BlockerSeverity.HIGH]
        
        message_lines = [f"Active blockers: {len(blockers)}"]
        if critical:
            message_lines.append(f"- Critical: {len(critical)}")
        if high:
            message_lines.append(f"- High Priority: {len(high)}")
        
        return Response(
            message='\n'.join(message_lines),
            data={
                'total_blockers': len(blockers),
                'critical': len(critical),
                'high': len(high),
                'blockers': [b.to_dict() for b in blockers]
            },
            break_loop=False
        )
    
    def _get_latest_report(self, facilitator: StandupFacilitator, **kwargs) -> Response:
        """
        Get the latest standup report
        
        Args:
            facilitator: The standup facilitator
            **kwargs: Additional arguments including format
        
        Returns:
            Response with latest report
        """
        if not facilitator.standup_history:
            return Response(
                message="No standup reports available",
                data={'error': 'No standups conducted yet'},
                break_loop=False
            )
        
        report = facilitator.standup_history[-1]
        format = kwargs.get('format', 'summary')
        
        if format == 'markdown':
            return Response(
                message=report.to_markdown(),
                data={'report_id': report.standup_id},
                break_loop=False
            )
        elif format == 'full':
            return Response(
                message=f"Standup report {report.standup_id}",
                data=report.to_dict(),
                break_loop=False
            )
        else:  # summary
            message = self._format_standup_summary(report)
            return Response(
                message=message,
                data={
                    'report_id': report.standup_id,
                    'date': report.date.isoformat(),
                    'participants': len(report.participants),
                    'blockers': len(report.blockers),
                    'team_mood': report.team_mood
                },
                break_loop=False
            )
    
    def _get_trends(self, facilitator: StandupFacilitator, **kwargs) -> Response:
        """
        Get standup trends and metrics
        
        Args:
            facilitator: The standup facilitator
            **kwargs: Additional arguments including days
        
        Returns:
            Response with trend analysis
        """
        days = kwargs.get('days', 7)
        
        blocker_trends = facilitator.get_blocker_trends(days)
        participation_metrics = facilitator.get_participation_metrics()
        
        message_lines = [
            f"Standup metrics for last {days} days:",
            f"- Total standups: {participation_metrics['total_standups']}",
            f"- Average participation: {participation_metrics['average_participation']:.1f}%",
            f"- Average duration: {participation_metrics['average_duration']:.1f} minutes",
            f"- Total blockers: {blocker_trends['total_blockers']}",
            f"- Resolution rate: {blocker_trends['resolution_rate']*100:.1f}%"
        ]
        
        return Response(
            message='\n'.join(message_lines),
            data={
                'blocker_trends': blocker_trends,
                'participation_metrics': participation_metrics
            },
            break_loop=False
        )
    
    def _export_history(self, facilitator: StandupFacilitator, **kwargs) -> Response:
        """
        Export standup history
        
        Args:
            facilitator: The standup facilitator
            **kwargs: Additional arguments including format and file_path
        
        Returns:
            Response with export confirmation
        """
        format = kwargs.get('format', 'json')
        file_path = kwargs.get('file_path')
        
        exported_data = facilitator.export_history(format)
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(exported_data)
                
                return Response(
                    message=f"Standup history exported to {file_path}",
                    data={'file_path': file_path, 'format': format},
                    break_loop=False
                )
            except Exception as e:
                return Response(
                    message=f"Failed to export: {str(e)}",
                    data={'error': str(e)},
                    break_loop=False
                )
        else:
            return Response(
                message=f"Standup history ({format} format)",
                data={'exported_data': exported_data, 'format': format},
                break_loop=False
            )
    
    async def _get_sprint_manager(self, team_id: str) -> Optional[Any]:
        """
        Get sprint manager for the team if available
        
        Args:
            team_id: Team ID
        
        Returns:
            Sprint manager instance or None
        """
        if SprintManager:
            # Try to get existing sprint manager
            # This would typically be retrieved from a shared context
            return None
        return None
    
    async def _get_team_members(self, team_id: str) -> List[Any]:
        """
        Get team members for standup
        
        Args:
            team_id: Team ID
        
        Returns:
            List of team members
        """
        # This would typically retrieve team members from the team orchestrator
        # For now, return empty list
        return []
    
    async def _create_status_from_dict(self, member_dict: Dict[str, Any]) -> TeamMemberStatus:
        """
        Create TeamMemberStatus from dictionary
        
        Args:
            member_dict: Dictionary with member status information
        
        Returns:
            TeamMemberStatus instance
        """
        status_info = member_dict.get('status', {})
        
        return TeamMemberStatus(
            agent_id=member_dict.get('id', 'unknown'),
            agent_name=member_dict.get('name', 'Unknown'),
            timestamp=datetime.now(),
            yesterday_completed=status_info.get('yesterday', []),
            today_planned=status_info.get('today', []),
            blockers=[{'description': b, 'severity': 'medium'} 
                     for b in status_info.get('blockers', [])],
            help_needed=status_info.get('help_needed', []),
            current_story=status_info.get('current_story'),
            story_progress=status_info.get('story_progress', 0.0),
            confidence_level=status_info.get('confidence', 1.0),
            mood=status_info.get('mood', 'neutral')
        )
    
    async def _create_default_status(self, member: Any) -> TeamMemberStatus:
        """
        Create default status for a team member
        
        Args:
            member: Team member
        
        Returns:
            Default TeamMemberStatus
        """
        agent_id = getattr(member, 'id', str(member))
        agent_name = getattr(member, 'name', f"Agent {agent_id}")
        
        return TeamMemberStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            timestamp=datetime.now(),
            yesterday_completed=["Worked on assigned tasks"],
            today_planned=["Continue with current work"],
            blockers=[],
            help_needed=[],
            current_story=None,
            story_progress=0.0,
            confidence_level=1.0,
            mood="neutral"
        )
    
    def _format_standup_summary(self, report: StandupReport) -> str:
        """
        Format a summary of the standup report
        
        Args:
            report: StandupReport instance
        
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"Daily Standup completed for team {report.team_id}")
        lines.append(f"Date: {report.date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Participants: {len(report.participants)}/{len(report.member_statuses)}")
        lines.append(f"Team mood: {report.team_mood}")
        lines.append(f"Sprint progress: {report.sprint_progress:.1f}%")
        
        if report.blockers:
            critical = [b for b in report.blockers if b.severity == BlockerSeverity.CRITICAL]
            high = [b for b in report.blockers if b.severity == BlockerSeverity.HIGH]
            
            lines.append(f"\nBlockers identified: {len(report.blockers)}")
            if critical:
                lines.append(f"  - Critical: {len(critical)}")
            if high:
                lines.append(f"  - High Priority: {len(high)}")
        
        if report.risks_identified:
            lines.append(f"\nRisks identified: {len(report.risks_identified)}")
            for risk in report.risks_identified[:3]:  # Show first 3 risks
                lines.append(f"  - {risk}")
        
        if report.action_items:
            lines.append(f"\nAction items: {len(report.action_items)}")
        
        return '\n'.join(lines)


# Tool registration
tool = DailyStandup