"""
Sprint Retrospective Tool for Agent-Zero

This tool enables agents to facilitate sprint retrospectives, collect feedback,
identify improvements, track action items, and generate reports.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Add agile module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from python.helpers.tool import Tool, Response
from agile.retrospective_analyzer import (
    RetrospectiveAnalyzer,
    FeedbackCategory,
    ActionItemPriority,
    ActionItemStatus,
    FeedbackItem,
    ActionItem
)


class Retrospective(Tool):
    """
    Tool for facilitating sprint retrospectives and collecting team feedback.
    
    This tool provides commands for:
    - Facilitating retrospective ceremonies
    - Collecting feedback from team members
    - Creating and tracking action items
    - Generating retrospective reports
    - Analyzing historical trends
    """
    
    def __init__(self, agent):
        super().__init__(agent)
        self.analyzer = RetrospectiveAnalyzer()
        self.current_retrospective = {
            'sprint_id': None,
            'team_id': None,
            'feedback_items': [],
            'participants': set()
        }
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute retrospective commands.
        
        Supported commands:
        - start_retrospective: Begin a new retrospective session
        - collect_feedback: Collect feedback from team member
        - create_action_item: Create new action item
        - update_action_item: Update action item status
        - generate_report: Generate retrospective report
        - get_trends: Analyze historical trends
        - list_action_items: List pending action items
        """
        command = kwargs.get('command', 'generate_report')
        
        try:
            if command == 'start_retrospective':
                return await self._start_retrospective(kwargs)
            elif command == 'collect_feedback':
                return await self._collect_feedback(kwargs)
            elif command == 'create_action_item':
                return await self._create_action_item(kwargs)
            elif command == 'update_action_item':
                return await self._update_action_item(kwargs)
            elif command == 'generate_report':
                return await self._generate_report(kwargs)
            elif command == 'get_trends':
                return await self._get_trends(kwargs)
            elif command == 'list_action_items':
                return await self._list_action_items(kwargs)
            elif command == 'facilitate':
                return await self._facilitate_retrospective(kwargs)
            else:
                return Response(
                    success=False,
                    message=f"Unknown command: {command}",
                    data={"available_commands": [
                        "start_retrospective", "collect_feedback", "create_action_item",
                        "update_action_item", "generate_report", "get_trends",
                        "list_action_items", "facilitate"
                    ]}
                )
        except Exception as e:
            return Response(
                success=False,
                message=f"Error executing retrospective command: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _start_retrospective(self, kwargs: Dict[str, Any]) -> Response:
        """Start a new retrospective session"""
        sprint_id = kwargs.get('sprint_id')
        team_id = kwargs.get('team_id')
        
        if not sprint_id or not team_id:
            return Response(
                success=False,
                message="Sprint ID and Team ID are required",
                data={}
            )
        
        self.current_retrospective = {
            'sprint_id': sprint_id,
            'team_id': team_id,
            'feedback_items': [],
            'participants': set(),
            'started_at': datetime.now()
        }
        
        return Response(
            success=True,
            message=f"Started retrospective for sprint {sprint_id}",
            data={
                'sprint_id': sprint_id,
                'team_id': team_id,
                'status': 'active',
                'started_at': self.current_retrospective['started_at'].isoformat()
            }
        )
    
    async def _collect_feedback(self, kwargs: Dict[str, Any]) -> Response:
        """Collect feedback from a team member"""
        agent_id = kwargs.get('agent_id', self.agent.get_agent_id())
        category = kwargs.get('category', 'went_well')
        content = kwargs.get('content')
        tags = kwargs.get('tags', [])
        
        if not content:
            return Response(
                success=False,
                message="Feedback content is required",
                data={}
            )
        
        # Map category string to enum
        category_map = {
            'went_well': FeedbackCategory.WENT_WELL,
            'went_wrong': FeedbackCategory.WENT_WRONG,
            'ideas': FeedbackCategory.IDEAS,
            'kudos': FeedbackCategory.KUDOS,
            'action_items': FeedbackCategory.ACTION_ITEMS
        }
        
        feedback_category = category_map.get(category, FeedbackCategory.WENT_WELL)
        
        # Collect feedback
        feedback = self.analyzer.collect_feedback(
            agent_id=agent_id,
            category=feedback_category,
            content=content,
            tags=tags
        )
        
        # Add to current retrospective
        self.current_retrospective['feedback_items'].append(feedback)
        self.current_retrospective['participants'].add(agent_id)
        
        return Response(
            success=True,
            message=f"Feedback collected from {agent_id}",
            data={
                'feedback_id': len(self.current_retrospective['feedback_items']),
                'agent_id': agent_id,
                'category': category,
                'sentiment': feedback.sentiment.value if feedback.sentiment else None
            }
        )
    
    async def _create_action_item(self, kwargs: Dict[str, Any]) -> Response:
        """Create a new action item"""
        title = kwargs.get('title')
        description = kwargs.get('description')
        assigned_to = kwargs.get('assigned_to')
        priority = kwargs.get('priority', 'medium')
        due_days = kwargs.get('due_days', 14)
        tags = kwargs.get('tags', [])
        
        if not title or not description:
            return Response(
                success=False,
                message="Title and description are required",
                data={}
            )
        
        # Map priority string to enum
        priority_map = {
            'critical': ActionItemPriority.CRITICAL,
            'high': ActionItemPriority.HIGH,
            'medium': ActionItemPriority.MEDIUM,
            'low': ActionItemPriority.LOW
        }
        
        action_priority = priority_map.get(priority, ActionItemPriority.MEDIUM)
        due_date = datetime.now() + timedelta(days=due_days)
        
        # Create action item
        action_item = self.analyzer.create_action_item(
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=action_priority,
            due_date=due_date,
            tags=tags
        )
        
        return Response(
            success=True,
            message=f"Created action item: {action_item.id}",
            data={
                'action_id': action_item.id,
                'title': title,
                'assigned_to': assigned_to or 'Unassigned',
                'priority': priority,
                'due_date': due_date.strftime('%Y-%m-%d')
            }
        )
    
    async def _update_action_item(self, kwargs: Dict[str, Any]) -> Response:
        """Update action item status"""
        action_id = kwargs.get('action_id')
        status = kwargs.get('status')
        
        if not action_id or not status:
            return Response(
                success=False,
                message="Action ID and status are required",
                data={}
            )
        
        # Map status string to enum
        status_map = {
            'pending': ActionItemStatus.PENDING,
            'in_progress': ActionItemStatus.IN_PROGRESS,
            'completed': ActionItemStatus.COMPLETED,
            'cancelled': ActionItemStatus.CANCELLED,
            'deferred': ActionItemStatus.DEFERRED
        }
        
        action_status = status_map.get(status)
        if not action_status:
            return Response(
                success=False,
                message=f"Invalid status: {status}",
                data={"valid_statuses": list(status_map.keys())}
            )
        
        # Update status
        success = self.analyzer.update_action_item_status(action_id, action_status)
        
        if success:
            return Response(
                success=True,
                message=f"Updated action item {action_id} to {status}",
                data={'action_id': action_id, 'new_status': status}
            )
        else:
            return Response(
                success=False,
                message=f"Action item {action_id} not found",
                data={}
            )
    
    async def _generate_report(self, kwargs: Dict[str, Any]) -> Response:
        """Generate retrospective report"""
        sprint_id = kwargs.get('sprint_id') or self.current_retrospective.get('sprint_id')
        team_id = kwargs.get('team_id') or self.current_retrospective.get('team_id')
        total_team_size = kwargs.get('team_size', 5)
        format_type = kwargs.get('format', 'markdown')
        
        if not sprint_id or not team_id:
            return Response(
                success=False,
                message="Sprint ID and Team ID are required",
                data={}
            )
        
        # Get feedback items
        feedback_items = self.current_retrospective.get('feedback_items', [])
        if not feedback_items:
            feedback_items = [f for f in self.analyzer.feedback_history 
                            if hasattr(f, 'sprint_id') and f.sprint_id == sprint_id]
        
        participants = list(self.current_retrospective.get('participants', set()))
        
        # Generate report
        report = self.analyzer.analyze_retrospective(
            sprint_id=sprint_id,
            team_id=team_id,
            feedback_items=feedback_items,
            participants=participants,
            total_team_size=total_team_size
        )
        
        # Format output
        if format_type == 'json':
            output = self.analyzer.export_to_json(report)
        else:
            output = report.to_markdown()
        
        # Save report
        report_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'retrospectives')
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"retrospective_{sprint_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if format_type == 'json':
            filename += '.json'
        else:
            filename += '.md'
        
        filepath = os.path.join(report_dir, filename)
        with open(filepath, 'w') as f:
            f.write(output)
        
        return Response(
            success=True,
            message=f"Generated retrospective report for sprint {sprint_id}",
            data={
                'sprint_id': sprint_id,
                'team_id': team_id,
                'participants': len(participants),
                'feedback_count': len(feedback_items),
                'action_items': len(report.action_items),
                'team_sentiment': report.team_sentiment.value,
                'filepath': filepath,
                'report': output if len(output) < 5000 else output[:5000] + '...'
            }
        )
    
    async def _get_trends(self, kwargs: Dict[str, Any]) -> Response:
        """Get historical trends"""
        team_id = kwargs.get('team_id')
        lookback_sprints = kwargs.get('lookback_sprints', 5)
        
        if not team_id:
            return Response(
                success=False,
                message="Team ID is required",
                data={}
            )
        
        trends = self.analyzer.get_historical_trends(team_id, lookback_sprints)
        
        if not trends:
            return Response(
                success=True,
                message=f"No historical data found for team {team_id}",
                data={}
            )
        
        return Response(
            success=True,
            message=f"Historical trends for team {team_id}",
            data=trends
        )
    
    async def _list_action_items(self, kwargs: Dict[str, Any]) -> Response:
        """List pending action items"""
        assigned_to = kwargs.get('assigned_to')
        
        items = self.analyzer.get_pending_action_items(assigned_to)
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'title': item.title,
                'assigned_to': item.assigned_to or 'Unassigned',
                'priority': item.priority.value,
                'status': item.status.value,
                'due_date': item.due_date.strftime('%Y-%m-%d') if item.due_date else None
            })
        
        return Response(
            success=True,
            message=f"Found {len(items)} pending action items",
            data={'action_items': items_data}
        )
    
    async def _facilitate_retrospective(self, kwargs: Dict[str, Any]) -> Response:
        """Facilitate a complete retrospective ceremony"""
        sprint_id = kwargs.get('sprint_id')
        team_id = kwargs.get('team_id')
        team_members = kwargs.get('team_members', [])
        
        if not sprint_id or not team_id or not team_members:
            return Response(
                success=False,
                message="Sprint ID, Team ID, and team members are required",
                data={}
            )
        
        # Start retrospective
        await self._start_retrospective({
            'sprint_id': sprint_id,
            'team_id': team_id
        })
        
        # Simulate collecting feedback from each team member
        categories = ['went_well', 'went_wrong', 'ideas']
        sample_feedback = {
            'went_well': [
                "Good collaboration on complex features",
                "Sprint goals were clear and achievable",
                "Daily standups were effective"
            ],
            'went_wrong': [
                "Some stories were underestimated",
                "Testing bottleneck towards end of sprint",
                "Documentation needs improvement"
            ],
            'ideas': [
                "Automate more testing processes",
                "Add code review checklist",
                "Schedule knowledge sharing sessions"
            ]
        }
        
        feedback_count = 0
        for member in team_members:
            for category in categories:
                # Get sample feedback for this category
                feedback_options = sample_feedback[category]
                content = feedback_options[feedback_count % len(feedback_options)]
                
                await self._collect_feedback({
                    'agent_id': member,
                    'category': category,
                    'content': f"{content} (from {member})",
                    'tags': [category, 'retrospective']
                })
                feedback_count += 1
        
        # Create some action items based on feedback
        action_items_created = []
        
        # Create action item for testing
        action1 = await self._create_action_item({
            'title': "Improve test automation coverage",
            'description': "Increase automated test coverage to reduce testing bottleneck",
            'assigned_to': team_members[0] if team_members else None,
            'priority': 'high',
            'due_days': 14,
            'tags': ['testing', 'automation']
        })
        action_items_created.append(action1.data)
        
        # Create action item for documentation
        action2 = await self._create_action_item({
            'title': "Update technical documentation",
            'description': "Improve documentation for new features and APIs",
            'assigned_to': team_members[1] if len(team_members) > 1 else None,
            'priority': 'medium',
            'due_days': 7,
            'tags': ['documentation']
        })
        action_items_created.append(action2.data)
        
        # Generate report
        report = await self._generate_report({
            'sprint_id': sprint_id,
            'team_id': team_id,
            'team_size': len(team_members),
            'format': 'markdown'
        })
        
        return Response(
            success=True,
            message=f"Facilitated retrospective for sprint {sprint_id}",
            data={
                'sprint_id': sprint_id,
                'team_id': team_id,
                'participants': len(team_members),
                'feedback_collected': feedback_count,
                'action_items_created': len(action_items_created),
                'action_items': action_items_created,
                'report_generated': report.success,
                'report_path': report.data.get('filepath'),
                'team_sentiment': report.data.get('team_sentiment')
            }
        )
    
    def get_agent_id(self) -> str:
        """Get current agent ID"""
        if hasattr(self.agent, 'agent_id'):
            return self.agent.agent_id
        elif hasattr(self.agent, 'id'):
            return self.agent.id
        else:
            return 'agent-' + str(id(self.agent))[-6:]


# Example usage
if __name__ == "__main__":
    import asyncio
    
    class MockAgent:
        def __init__(self):
            self.agent_id = "test-agent"
    
    async def test_retrospective():
        agent = MockAgent()
        tool = Retrospective(agent)
        
        # Facilitate a complete retrospective
        result = await tool.execute(
            command='facilitate',
            sprint_id='sprint-001',
            team_id='team-alpha',
            team_members=['agent-1', 'agent-2', 'agent-3']
        )
        
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        print(f"Data: {json.dumps(result.data, indent=2)}")
    
    asyncio.run(test_retrospective())