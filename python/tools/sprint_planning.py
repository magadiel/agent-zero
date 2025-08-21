"""
Sprint Planning Tool for Agent-Zero

This tool enables agents to perform sprint planning activities including
backlog grooming, sprint creation, and capacity planning.
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python.tools.tool import Tool, Response
from agile.product_backlog import ProductBacklog, Story, StoryStatus, StoryType, Priority
from agile.sprint_manager import SprintManager, Sprint, SprintStatus


class SprintPlanningTool(Tool):
    """
    Tool for sprint planning activities in agile development.
    Enables agents to manage backlogs, plan sprints, and track velocity.
    """
    
    def __init__(self, agent: Any):
        """Initialize the sprint planning tool"""
        super().__init__(agent)
        self.agent = agent
        
        # Initialize or load backlog and sprint manager
        self.backlog = self._load_or_create_backlog()
        self.sprint_manager = SprintManager(self.backlog)
        self._load_sprints()
    
    def _load_or_create_backlog(self) -> ProductBacklog:
        """Load existing backlog or create new one"""
        backlog_file = os.path.join(self.agent.context.workspace_path, "agile", "backlog.json")
        backlog = ProductBacklog()
        
        if os.path.exists(backlog_file):
            try:
                backlog.import_from_json(backlog_file)
                self.agent.context.log.info(f"Loaded backlog from {backlog_file}")
            except Exception as e:
                self.agent.context.log.error(f"Failed to load backlog: {e}")
        
        return backlog
    
    def _load_sprints(self):
        """Load existing sprints"""
        sprints_file = os.path.join(self.agent.context.workspace_path, "agile", "sprints.json")
        
        if os.path.exists(sprints_file):
            try:
                with open(sprints_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct sprints from data
                    for sprint_data in data.get('sprints', []):
                        sprint = self._sprint_from_dict(sprint_data)
                        self.sprint_manager.sprints[sprint.id] = sprint
                        if sprint.status == SprintStatus.ACTIVE:
                            self.sprint_manager.active_sprint = sprint
                    
                    self.sprint_manager.velocity_history = data.get('velocity_history', [])
                    self.agent.context.log.info(f"Loaded {len(self.sprint_manager.sprints)} sprints")
            except Exception as e:
                self.agent.context.log.error(f"Failed to load sprints: {e}")
    
    def _sprint_from_dict(self, data: Dict[str, Any]) -> Sprint:
        """Reconstruct Sprint object from dictionary"""
        # Convert string dates and enums
        if 'start_date' in data:
            data['start_date'] = date.fromisoformat(data['start_date'])
        if 'end_date' in data:
            data['end_date'] = date.fromisoformat(data['end_date'])
        if 'status' in data:
            data['status'] = SprintStatus(data['status'])
        
        # Handle datetime fields
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'started_at' in data and data['started_at']:
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if 'completed_at' in data and data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        return Sprint(**data)
    
    def _save_backlog(self):
        """Save backlog to file"""
        backlog_file = os.path.join(self.agent.context.workspace_path, "agile", "backlog.json")
        os.makedirs(os.path.dirname(backlog_file), exist_ok=True)
        self.backlog.export_to_json(backlog_file)
    
    def _save_sprints(self):
        """Save sprints to file"""
        sprints_file = os.path.join(self.agent.context.workspace_path, "agile", "sprints.json")
        os.makedirs(os.path.dirname(sprints_file), exist_ok=True)
        
        data = {
            'sprints': [sprint.to_dict() for sprint in self.sprint_manager.sprints.values()],
            'velocity_history': self.sprint_manager.velocity_history,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(sprints_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute sprint planning commands.
        
        Available commands:
        - create_story: Create a new user story
        - list_backlog: List prioritized backlog items
        - groom_backlog: Get stories needing grooming
        - create_sprint: Create a new sprint
        - plan_sprint: Add stories to sprint
        - start_sprint: Start the active sprint
        - daily_standup: Get daily standup report
        - complete_story: Mark story as done
        - end_sprint: End current sprint
        - sprint_metrics: Get velocity metrics
        - sprint_report: Get sprint report
        """
        command = kwargs.get('command', 'list_backlog')
        
        try:
            if command == 'create_story':
                return await self._create_story(kwargs)
            elif command == 'list_backlog':
                return await self._list_backlog(kwargs)
            elif command == 'groom_backlog':
                return await self._groom_backlog(kwargs)
            elif command == 'create_sprint':
                return await self._create_sprint(kwargs)
            elif command == 'plan_sprint':
                return await self._plan_sprint(kwargs)
            elif command == 'start_sprint':
                return await self._start_sprint(kwargs)
            elif command == 'daily_standup':
                return await self._daily_standup()
            elif command == 'complete_story':
                return await self._complete_story(kwargs)
            elif command == 'end_sprint':
                return await self._end_sprint(kwargs)
            elif command == 'sprint_metrics':
                return await self._sprint_metrics()
            elif command == 'sprint_report':
                return await self._sprint_report(kwargs)
            elif command == 'backlog_stats':
                return await self._backlog_stats()
            else:
                return Response(
                    success=False,
                    message=f"Unknown command: {command}",
                    data={'available_commands': [
                        'create_story', 'list_backlog', 'groom_backlog',
                        'create_sprint', 'plan_sprint', 'start_sprint',
                        'daily_standup', 'complete_story', 'end_sprint',
                        'sprint_metrics', 'sprint_report', 'backlog_stats'
                    ]}
                )
        except Exception as e:
            return Response(
                success=False,
                message=f"Error executing sprint planning command: {str(e)}",
                data={'error': str(e)}
            )
    
    async def _create_story(self, kwargs: Dict[str, Any]) -> Response:
        """Create a new story in the backlog"""
        story = Story(
            title=kwargs.get('title', ''),
            description=kwargs.get('description', ''),
            as_a=kwargs.get('as_a', ''),
            i_want=kwargs.get('i_want', ''),
            so_that=kwargs.get('so_that', ''),
            story_points=kwargs.get('points'),
            business_value=kwargs.get('value', 0),
            priority=Priority(kwargs.get('priority', 'medium')),
            type=StoryType(kwargs.get('type', 'user_story')),
            status=StoryStatus.DRAFT,
            created_by=self.agent.agent_name
        )
        
        # Add acceptance criteria if provided
        criteria = kwargs.get('acceptance_criteria', [])
        for criterion in criteria:
            from agile.product_backlog import AcceptanceCriteria
            story.acceptance_criteria.append(
                AcceptanceCriteria(description=criterion)
            )
        
        story_id = self.backlog.add_story(story)
        self._save_backlog()
        
        return Response(
            success=True,
            message=f"Created story: {story.title}",
            data={
                'story_id': story_id,
                'title': story.title,
                'points': story.story_points,
                'priority': story.priority.value
            }
        )
    
    async def _list_backlog(self, kwargs: Dict[str, Any]) -> Response:
        """List prioritized backlog items"""
        limit = kwargs.get('limit', 10)
        stories = self.backlog.get_prioritized_stories(limit=limit)
        
        story_list = []
        for story in stories:
            story_list.append({
                'id': story.id,
                'title': story.title,
                'type': story.type.value,
                'status': story.status.value,
                'priority': story.priority.value,
                'points': story.story_points,
                'value': story.business_value,
                'ready': story.is_ready()
            })
        
        stats = self.backlog.get_statistics()
        
        return Response(
            success=True,
            message=f"Found {len(story_list)} prioritized stories",
            data={
                'stories': story_list,
                'total_stories': stats['total_stories'],
                'ready_stories': stats['ready_stories'],
                'total_points': stats['total_points']
            }
        )
    
    async def _groom_backlog(self, kwargs: Dict[str, Any]) -> Response:
        """Get stories that need grooming"""
        limit = kwargs.get('limit', 10)
        candidates = self.backlog.grooming_candidates(limit=limit)
        
        grooming_list = []
        for story in candidates:
            issues = []
            if story.story_points is None:
                issues.append("needs estimation")
            if not story.acceptance_criteria:
                issues.append("needs acceptance criteria")
            if not story.description:
                issues.append("needs description")
            
            grooming_list.append({
                'id': story.id,
                'title': story.title,
                'issues': issues
            })
        
        return Response(
            success=True,
            message=f"Found {len(grooming_list)} stories needing grooming",
            data={'stories': grooming_list}
        )
    
    async def _create_sprint(self, kwargs: Dict[str, Any]) -> Response:
        """Create a new sprint"""
        sprint = self.sprint_manager.create_sprint(
            name=kwargs.get('name', f"Sprint {len(self.sprint_manager.sprints) + 1}"),
            goal=kwargs.get('goal', ''),
            team_id=kwargs.get('team_id', 'default-team'),
            start_date=date.fromisoformat(kwargs['start_date']) if 'start_date' in kwargs else None,
            duration_days=kwargs.get('duration', 14)
        )
        
        self._save_sprints()
        
        return Response(
            success=True,
            message=f"Created sprint: {sprint.name}",
            data={
                'sprint_id': sprint.id,
                'name': sprint.name,
                'goal': sprint.goal,
                'start_date': sprint.start_date.isoformat(),
                'end_date': sprint.end_date.isoformat()
            }
        )
    
    async def _plan_sprint(self, kwargs: Dict[str, Any]) -> Response:
        """Plan a sprint with stories"""
        sprint_id = kwargs.get('sprint_id')
        story_ids = kwargs.get('story_ids', [])
        team_size = kwargs.get('team_size', 5)
        days_off = kwargs.get('days_off', 0)
        
        if not sprint_id:
            # Use the most recent sprint in planning status
            for sprint in self.sprint_manager.sprints.values():
                if sprint.status == SprintStatus.PLANNING:
                    sprint_id = sprint.id
                    break
        
        if not sprint_id:
            return Response(
                success=False,
                message="No sprint available for planning",
                data={}
            )
        
        # If no story IDs provided, auto-select from backlog
        if not story_ids:
            capacity = self.sprint_manager.recommend_sprint_capacity(team_size)
            recommended_points = capacity['recommended_points']
            
            stories = self.backlog.get_prioritized_stories()
            selected_points = 0
            for story in stories:
                if story.story_points and selected_points + story.story_points <= recommended_points:
                    story_ids.append(story.id)
                    selected_points += story.story_points
        
        result = self.sprint_manager.plan_sprint(sprint_id, story_ids, team_size, days_off)
        
        if result['success']:
            self._save_backlog()
            self._save_sprints()
        
        return Response(
            success=result['success'],
            message=result.get('error', f"Planned sprint with {result.get('stories_added', 0)} stories"),
            data=result
        )
    
    async def _start_sprint(self, kwargs: Dict[str, Any]) -> Response:
        """Start a sprint"""
        sprint_id = kwargs.get('sprint_id')
        
        if not sprint_id:
            # Find sprint in planning status
            for sprint in self.sprint_manager.sprints.values():
                if sprint.status == SprintStatus.PLANNING:
                    sprint_id = sprint.id
                    break
        
        if not sprint_id:
            return Response(
                success=False,
                message="No sprint ready to start",
                data={}
            )
        
        success = self.sprint_manager.start_sprint(sprint_id)
        
        if success:
            self._save_sprints()
            sprint = self.sprint_manager.sprints[sprint_id]
            return Response(
                success=True,
                message=f"Started sprint: {sprint.name}",
                data={
                    'sprint_id': sprint_id,
                    'name': sprint.name,
                    'committed_points': sprint.committed_points,
                    'end_date': sprint.end_date.isoformat()
                }
            )
        else:
            return Response(
                success=False,
                message="Failed to start sprint - check if another sprint is active",
                data={}
            )
    
    async def _daily_standup(self) -> Response:
        """Get daily standup report"""
        standup = self.sprint_manager.daily_standup()
        
        if 'error' in standup:
            return Response(
                success=False,
                message=standup['error'],
                data={}
            )
        
        # Format standup report
        report = f"**Daily Standup - {standup['sprint_name']}**\n\n"
        report += f"Day {standup['day']} - {standup['days_remaining']} days remaining\n\n"
        report += f"**Progress:**\n"
        report += f"- Points completed: {standup['points_completed']}\n"
        report += f"- Points remaining: {standup['points_remaining']}\n"
        report += f"- Status: {standup['burndown_status']}\n\n"
        
        if standup['stories_completed_today']:
            report += f"**Completed Today:**\n"
            for story in standup['stories_completed_today']:
                report += f"- {story}\n"
            report += "\n"
        
        if standup['stories_in_progress']:
            report += f"**In Progress:**\n"
            for story in standup['stories_in_progress']:
                report += f"- {story}\n"
            report += "\n"
        
        if standup['stories_blocked']:
            report += f"**Blocked:**\n"
            for story in standup['stories_blocked']:
                report += f"- {story}\n"
            report += "\n"
        
        return Response(
            success=True,
            message=report,
            data=standup
        )
    
    async def _complete_story(self, kwargs: Dict[str, Any]) -> Response:
        """Mark a story as complete"""
        story_id = kwargs.get('story_id')
        
        if not story_id:
            return Response(
                success=False,
                message="Story ID required",
                data={}
            )
        
        success = self.sprint_manager.complete_story(story_id)
        
        if success:
            self._save_backlog()
            self._save_sprints()
            story = self.backlog.get_story(story_id)
            return Response(
                success=True,
                message=f"Completed story: {story.title}",
                data={
                    'story_id': story_id,
                    'title': story.title,
                    'points': story.story_points
                }
            )
        else:
            return Response(
                success=False,
                message="Failed to complete story - check if it's in active sprint",
                data={}
            )
    
    async def _end_sprint(self, kwargs: Dict[str, Any]) -> Response:
        """End a sprint"""
        sprint_id = kwargs.get('sprint_id')
        
        if not sprint_id and self.sprint_manager.active_sprint:
            sprint_id = self.sprint_manager.active_sprint.id
        
        if not sprint_id:
            return Response(
                success=False,
                message="No active sprint to end",
                data={}
            )
        
        result = self.sprint_manager.end_sprint(sprint_id)
        
        if result['success']:
            self._save_backlog()
            self._save_sprints()
            
            # Format sprint summary
            summary = f"**Sprint Completed: {result['sprint_name']}**\n\n"
            summary += f"- Velocity: {result['velocity']} points\n"
            summary += f"- Completion Rate: {result['completion_rate']:.1f}%\n"
            summary += f"- Completed: {result['completed_points']}/{result['committed_points']} points\n"
            
            if result['incomplete_stories']:
                summary += f"\n**Incomplete stories moved to backlog:**\n"
                for story in result['incomplete_stories']:
                    summary += f"- {story}\n"
            
            return Response(
                success=True,
                message=summary,
                data=result
            )
        else:
            return Response(
                success=False,
                message=result.get('error', 'Failed to end sprint'),
                data={}
            )
    
    async def _sprint_metrics(self) -> Response:
        """Get velocity metrics"""
        metrics = self.sprint_manager.get_velocity_metrics()
        capacity = self.sprint_manager.recommend_sprint_capacity(5)  # Default team size
        
        # Format metrics report
        report = "**Sprint Velocity Metrics**\n\n"
        report += f"- Average Velocity: {metrics['average_velocity']:.1f} points\n"
        report += f"- Min/Max: {metrics['min_velocity']}/{metrics['max_velocity']} points\n"
        report += f"- Trend: {metrics['trend']}\n"
        report += f"- Predictability: {metrics['predictability']:.2%}\n\n"
        report += f"**Recommended Capacity:**\n"
        report += f"- Points: {capacity['recommended_points']}\n"
        report += f"- Confidence: {capacity['confidence']}\n"
        
        return Response(
            success=True,
            message=report,
            data={
                'metrics': metrics,
                'capacity_recommendation': capacity
            }
        )
    
    async def _sprint_report(self, kwargs: Dict[str, Any]) -> Response:
        """Get comprehensive sprint report"""
        sprint_id = kwargs.get('sprint_id')
        
        if not sprint_id and self.sprint_manager.active_sprint:
            sprint_id = self.sprint_manager.active_sprint.id
        
        if not sprint_id:
            # Get most recent sprint
            if self.sprint_manager.sprints:
                sprint_id = list(self.sprint_manager.sprints.keys())[-1]
        
        if not sprint_id:
            return Response(
                success=False,
                message="No sprint available for report",
                data={}
            )
        
        report = self.sprint_manager.get_sprint_report(sprint_id)
        
        if 'error' in report:
            return Response(
                success=False,
                message=report['error'],
                data={}
            )
        
        # Format report
        formatted = f"**Sprint Report: {report['sprint']['name']}**\n\n"
        formatted += f"Status: {report['sprint']['status']}\n"
        formatted += f"Goal: {report['sprint']['goal']}\n"
        formatted += f"Period: {report['sprint']['start_date']} to {report['sprint']['end_date']}\n\n"
        
        formatted += "**Points:**\n"
        formatted += f"- Committed: {report['points']['committed']}\n"
        formatted += f"- Completed: {report['points']['completed']}\n"
        formatted += f"- Remaining: {report['points']['remaining']}\n\n"
        
        formatted += "**Stories:**\n"
        formatted += f"- Total: {report['stories']['total']}\n"
        formatted += f"- Completed: {report['stories']['completed']}\n"
        formatted += f"- In Progress: {report['stories']['in_progress']}\n"
        formatted += f"- Blocked: {report['stories']['blocked']}\n\n"
        
        formatted += "**Metrics:**\n"
        formatted += f"- Velocity: {report['metrics']['velocity'] or 'N/A'}\n"
        formatted += f"- Completion Rate: {report['metrics']['completion_rate']:.1f}%\n"
        formatted += f"- On Track: {'Yes' if report['metrics']['on_track'] else 'No'}\n"
        
        return Response(
            success=True,
            message=formatted,
            data=report
        )
    
    async def _backlog_stats(self) -> Response:
        """Get backlog statistics"""
        stats = self.backlog.get_statistics()
        
        # Format statistics
        report = "**Backlog Statistics**\n\n"
        report += f"- Total Stories: {stats['total_stories']}\n"
        report += f"- Total Epics: {stats['total_epics']}\n"
        report += f"- Ready Stories: {stats['ready_stories']}\n"
        report += f"- Blocked Stories: {stats['blocked_stories']}\n"
        report += f"- Total Points: {stats['total_points']}\n"
        report += f"- Estimation Coverage: {stats['estimation_coverage']:.1f}%\n\n"
        
        if stats['status_distribution']:
            report += "**Status Distribution:**\n"
            for status, count in stats['status_distribution'].items():
                report += f"- {status}: {count}\n"
            report += "\n"
        
        if stats['priority_distribution']:
            report += "**Priority Distribution:**\n"
            for priority, count in stats['priority_distribution'].items():
                report += f"- {priority}: {count}\n"
        
        return Response(
            success=True,
            message=report,
            data=stats
        )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Mock agent for testing
    class MockAgent:
        def __init__(self):
            self.agent_name = "TestAgent"
            self.context = type('obj', (object,), {
                'workspace_path': '/tmp/test_sprint',
                'log': type('obj', (object,), {
                    'info': print,
                    'error': print
                })()
            })()
    
    async def test_sprint_planning():
        agent = MockAgent()
        tool = SprintPlanningTool(agent)
        
        # Create some stories
        for i in range(5):
            result = await tool.execute(
                command='create_story',
                title=f"Test Story {i+1}",
                description=f"Description for story {i+1}",
                points=3,
                value=50,
                priority='high' if i < 2 else 'medium',
                acceptance_criteria=[f"Criterion {j+1}" for j in range(2)]
            )
            print(result.message)
        
        # List backlog
        result = await tool.execute(command='list_backlog')
        print(result.message)
        
        # Create sprint
        result = await tool.execute(
            command='create_sprint',
            name="Test Sprint 1",
            goal="Test sprint planning functionality"
        )
        print(result.message)
        
        # Plan sprint
        result = await tool.execute(
            command='plan_sprint',
            team_size=3
        )
        print(result.message)
        
        # Get metrics
        result = await tool.execute(command='sprint_metrics')
        print(result.message)
    
    # Run test
    asyncio.run(test_sprint_planning())