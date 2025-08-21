"""
Team Communication Tool for Agent-Zero

This tool provides team communication capabilities for Agent-Zero agents,
enabling them to participate in team-based workflows with broadcast messaging,
voting, status reporting, and synchronization.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle

# Import team protocol
try:
    from python.helpers.team_protocol import (
        TeamProtocol, VoteOption, MessageType,
        create_team_protocol, TeamMessage
    )
    TEAM_PROTOCOL_AVAILABLE = True
except ImportError:
    TEAM_PROTOCOL_AVAILABLE = False
    TeamProtocol = None

# Import team orchestrator for team information
try:
    from coordination.team_orchestrator import TeamOrchestrator, Team
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    TeamOrchestrator = None
    Team = None


class TeamCommunication(Tool):
    """
    Tool for team communication in Agent-Zero.
    
    This tool enables agents to:
    - Broadcast messages to their team
    - Participate in team voting
    - Report their status
    - Synchronize with team members
    - Query team information
    """
    
    def __init__(self, agent_context=None):
        """Initialize the team communication tool."""
        super().__init__(agent_context)
        self.team_protocol: Optional[TeamProtocol] = None
        self.team_orchestrator: Optional[TeamOrchestrator] = None
        self.current_team_id: Optional[str] = None
        self.printer = PrintStyle(color="blue", italic=True)
        
    async def json_schema(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return the JSON schema for the tool.
        """
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "broadcast",
                        "vote_request",
                        "submit_vote",
                        "report_status",
                        "get_team_status",
                        "create_barrier",
                        "wait_at_barrier",
                        "acquire_lock",
                        "release_lock",
                        "set_event",
                        "wait_for_event",
                        "join_team",
                        "leave_team",
                        "get_team_info",
                        "get_metrics"
                    ],
                    "description": "The communication action to perform"
                },
                "message": {
                    "type": "string",
                    "description": "Message content for broadcast or proposal for voting"
                },
                "team_id": {
                    "type": "string",
                    "description": "Team identifier"
                },
                "vote_id": {
                    "type": "string",
                    "description": "Vote identifier for submit_vote action"
                },
                "vote": {
                    "type": "string",
                    "enum": ["yes", "no", "abstain", "veto"],
                    "description": "Vote option"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Reasoning for vote"
                },
                "status": {
                    "type": "string",
                    "enum": ["idle", "working", "blocked", "error"],
                    "description": "Agent status"
                },
                "current_task": {
                    "type": "string",
                    "description": "Current task being worked on"
                },
                "progress": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Progress percentage (0.0 to 1.0)"
                },
                "blockers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of blockers"
                },
                "threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Voting threshold (0.0 to 1.0)"
                },
                "deadline_minutes": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Minutes until vote deadline"
                },
                "allow_veto": {
                    "type": "boolean",
                    "description": "Whether veto is allowed in voting"
                },
                "anonymous": {
                    "type": "boolean",
                    "description": "Whether voting is anonymous"
                },
                "barrier_id": {
                    "type": "string",
                    "description": "Barrier identifier for synchronization"
                },
                "lock_id": {
                    "type": "string",
                    "description": "Lock identifier for mutual exclusion"
                },
                "event_id": {
                    "type": "string",
                    "description": "Event identifier for signaling"
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Timeout in seconds for synchronization operations"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the message"
                }
            },
            "required": ["action"],
            "additionalProperties": False
        }
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute a team communication action.
        
        Args:
            **kwargs: Action parameters
            
        Returns:
            Response with action results
        """
        if not TEAM_PROTOCOL_AVAILABLE:
            return Response(
                success=False,
                message="Team protocol not available. Please ensure dependencies are installed.",
                data={}
            )
        
        action = kwargs.get("action")
        
        if not action:
            return Response(
                success=False,
                message="Action is required",
                data={}
            )
        
        try:
            # Initialize team protocol if needed
            if action not in ["join_team", "get_team_info"] and not self.team_protocol:
                await self._initialize_protocol(kwargs.get("team_id"))
            
            # Route to appropriate handler
            if action == "broadcast":
                return await self._broadcast(kwargs)
            elif action == "vote_request":
                return await self._request_vote(kwargs)
            elif action == "submit_vote":
                return await self._submit_vote(kwargs)
            elif action == "report_status":
                return await self._report_status(kwargs)
            elif action == "get_team_status":
                return await self._get_team_status(kwargs)
            elif action == "create_barrier":
                return await self._create_barrier(kwargs)
            elif action == "wait_at_barrier":
                return await self._wait_at_barrier(kwargs)
            elif action == "acquire_lock":
                return await self._acquire_lock(kwargs)
            elif action == "release_lock":
                return await self._release_lock(kwargs)
            elif action == "set_event":
                return await self._set_event(kwargs)
            elif action == "wait_for_event":
                return await self._wait_for_event(kwargs)
            elif action == "join_team":
                return await self._join_team(kwargs)
            elif action == "leave_team":
                return await self._leave_team(kwargs)
            elif action == "get_team_info":
                return await self._get_team_info(kwargs)
            elif action == "get_metrics":
                return await self._get_metrics(kwargs)
            else:
                return Response(
                    success=False,
                    message=f"Unknown action: {action}",
                    data={}
                )
                
        except Exception as e:
            return Response(
                success=False,
                message=f"Error executing team communication: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _initialize_protocol(self, team_id: Optional[str] = None):
        """Initialize team protocol with team information."""
        if not team_id and not self.current_team_id:
            raise ValueError("Team ID is required")
        
        team_id = team_id or self.current_team_id
        agent_id = getattr(self.agent_context, 'agent_id', None) if self.agent_context else None
        
        self.team_protocol = TeamProtocol(team_id, agent_id)
        self.current_team_id = team_id
        
        # Try to get team members from orchestrator
        if ORCHESTRATOR_AVAILABLE and self.team_orchestrator:
            team = self.team_orchestrator.teams.get(team_id)
            if team:
                for member_id, member in team.members.items():
                    if member_id != agent_id:  # Don't add self
                        # Get member URL from metadata or use default
                        member_url = member.metadata.get('a2a_url', f"http://agent-{member_id}:80/a2a")
                        await self.team_protocol.add_team_member(member_id, member_url)
    
    async def _broadcast(self, kwargs: Dict[str, Any]) -> Response:
        """Broadcast a message to the team."""
        message = kwargs.get("message")
        if not message:
            return Response(
                success=False,
                message="Message is required for broadcast",
                data={}
            )
        
        metadata = kwargs.get("metadata", {})
        
        self.printer.print(f"Broadcasting to team: {message}")
        result = await self.team_protocol.broadcast_to_team(message, metadata)
        
        return Response(
            success=True,
            message=f"Broadcast sent to {result['recipients']} team members",
            data=result
        )
    
    async def _request_vote(self, kwargs: Dict[str, Any]) -> Response:
        """Request a vote from the team."""
        proposal = kwargs.get("message")
        if not proposal:
            return Response(
                success=False,
                message="Proposal message is required for vote request",
                data={}
            )
        
        threshold = kwargs.get("threshold", 0.5)
        deadline_minutes = kwargs.get("deadline_minutes", 5)
        allow_veto = kwargs.get("allow_veto", False)
        anonymous = kwargs.get("anonymous", False)
        
        self.printer.print(f"Requesting team vote: {proposal}")
        vote_id = await self.team_protocol.request_team_vote(
            proposal=proposal,
            threshold=threshold,
            deadline_minutes=deadline_minutes,
            allow_veto=allow_veto,
            anonymous=anonymous
        )
        
        return Response(
            success=True,
            message=f"Vote request sent. Vote ID: {vote_id}",
            data={"vote_id": vote_id, "deadline_minutes": deadline_minutes}
        )
    
    async def _submit_vote(self, kwargs: Dict[str, Any]) -> Response:
        """Submit a vote."""
        vote_id = kwargs.get("vote_id")
        vote_str = kwargs.get("vote")
        
        if not vote_id or not vote_str:
            return Response(
                success=False,
                message="vote_id and vote are required",
                data={}
            )
        
        vote = VoteOption[vote_str.upper()]
        reasoning = kwargs.get("reasoning")
        
        success = await self.team_protocol.submit_vote(vote_id, vote, reasoning)
        
        if success:
            self.printer.print(f"Vote submitted: {vote_str}")
            return Response(
                success=True,
                message=f"Vote submitted successfully",
                data={"vote_id": vote_id, "vote": vote_str}
            )
        else:
            return Response(
                success=False,
                message="Failed to submit vote (may be expired or invalid)",
                data={}
            )
    
    async def _report_status(self, kwargs: Dict[str, Any]) -> Response:
        """Report agent status to the team."""
        status = kwargs.get("status", "idle")
        current_task = kwargs.get("current_task")
        progress = kwargs.get("progress", 0.0)
        blockers = kwargs.get("blockers", [])
        
        self.printer.print(f"Reporting status: {status} ({progress*100:.1f}%)")
        
        success = await self.team_protocol.report_status(
            status=status,
            current_task=current_task,
            progress=progress,
            blockers=blockers
        )
        
        return Response(
            success=success,
            message="Status reported to team",
            data={
                "status": status,
                "progress": progress,
                "blockers": blockers
            }
        )
    
    async def _get_team_status(self, kwargs: Dict[str, Any]) -> Response:
        """Get aggregated team status."""
        team_status = await self.team_protocol.get_team_status()
        
        # Format status for display
        status_summary = f"Team Status ({team_status['reporting_members']}/{team_status['total_members']} reporting)\n"
        
        if 'average_progress' in team_status:
            status_summary += f"Average Progress: {team_status['average_progress']*100:.1f}%\n"
        
        if 'status_distribution' in team_status:
            status_summary += "Status Distribution:\n"
            for status, count in team_status['status_distribution'].items():
                status_summary += f"  - {status}: {count}\n"
        
        if 'all_blockers' in team_status and team_status['all_blockers']:
            status_summary += f"Blockers: {', '.join(team_status['all_blockers'])}\n"
        
        return Response(
            success=True,
            message=status_summary,
            data=team_status
        )
    
    async def _create_barrier(self, kwargs: Dict[str, Any]) -> Response:
        """Create a synchronization barrier."""
        barrier_id = kwargs.get("barrier_id")
        if not barrier_id:
            return Response(
                success=False,
                message="barrier_id is required",
                data={}
            )
        
        success = await self.team_protocol.create_barrier(barrier_id)
        
        return Response(
            success=success,
            message=f"Barrier '{barrier_id}' created",
            data={"barrier_id": barrier_id}
        )
    
    async def _wait_at_barrier(self, kwargs: Dict[str, Any]) -> Response:
        """Wait at a synchronization barrier."""
        barrier_id = kwargs.get("barrier_id")
        if not barrier_id:
            return Response(
                success=False,
                message="barrier_id is required",
                data={}
            )
        
        timeout = kwargs.get("timeout")
        
        self.printer.print(f"Waiting at barrier: {barrier_id}")
        success = await self.team_protocol.wait_at_barrier(barrier_id, timeout)
        
        if success:
            return Response(
                success=True,
                message=f"Barrier '{barrier_id}' passed",
                data={"barrier_id": barrier_id}
            )
        else:
            return Response(
                success=False,
                message=f"Barrier '{barrier_id}' timeout",
                data={"barrier_id": barrier_id}
            )
    
    async def _acquire_lock(self, kwargs: Dict[str, Any]) -> Response:
        """Acquire a distributed lock."""
        lock_id = kwargs.get("lock_id")
        if not lock_id:
            return Response(
                success=False,
                message="lock_id is required",
                data={}
            )
        
        timeout = kwargs.get("timeout")
        
        self.printer.print(f"Acquiring lock: {lock_id}")
        success = await self.team_protocol.acquire_lock(lock_id, timeout)
        
        if success:
            return Response(
                success=True,
                message=f"Lock '{lock_id}' acquired",
                data={"lock_id": lock_id}
            )
        else:
            return Response(
                success=False,
                message=f"Failed to acquire lock '{lock_id}'",
                data={"lock_id": lock_id}
            )
    
    async def _release_lock(self, kwargs: Dict[str, Any]) -> Response:
        """Release a distributed lock."""
        lock_id = kwargs.get("lock_id")
        if not lock_id:
            return Response(
                success=False,
                message="lock_id is required",
                data={}
            )
        
        success = await self.team_protocol.release_lock(lock_id)
        
        if success:
            return Response(
                success=True,
                message=f"Lock '{lock_id}' released",
                data={"lock_id": lock_id}
            )
        else:
            return Response(
                success=False,
                message=f"Failed to release lock '{lock_id}' (not owner)",
                data={"lock_id": lock_id}
            )
    
    async def _set_event(self, kwargs: Dict[str, Any]) -> Response:
        """Set an event flag."""
        event_id = kwargs.get("event_id")
        if not event_id:
            return Response(
                success=False,
                message="event_id is required",
                data={}
            )
        
        success = await self.team_protocol.set_event(event_id)
        
        return Response(
            success=True,
            message=f"Event '{event_id}' set",
            data={"event_id": event_id}
        )
    
    async def _wait_for_event(self, kwargs: Dict[str, Any]) -> Response:
        """Wait for an event to be set."""
        event_id = kwargs.get("event_id")
        if not event_id:
            return Response(
                success=False,
                message="event_id is required",
                data={}
            )
        
        timeout = kwargs.get("timeout")
        
        self.printer.print(f"Waiting for event: {event_id}")
        success = await self.team_protocol.wait_for_event(event_id, timeout)
        
        if success:
            return Response(
                success=True,
                message=f"Event '{event_id}' triggered",
                data={"event_id": event_id}
            )
        else:
            return Response(
                success=False,
                message=f"Event '{event_id}' timeout",
                data={"event_id": event_id}
            )
    
    async def _join_team(self, kwargs: Dict[str, Any]) -> Response:
        """Join a team."""
        team_id = kwargs.get("team_id")
        if not team_id:
            return Response(
                success=False,
                message="team_id is required",
                data={}
            )
        
        await self._initialize_protocol(team_id)
        
        self.printer.print(f"Joined team: {team_id}")
        return Response(
            success=True,
            message=f"Joined team '{team_id}'",
            data={"team_id": team_id}
        )
    
    async def _leave_team(self, kwargs: Dict[str, Any]) -> Response:
        """Leave the current team."""
        if not self.team_protocol:
            return Response(
                success=False,
                message="Not currently in a team",
                data={}
            )
        
        team_id = self.current_team_id
        self.team_protocol = None
        self.current_team_id = None
        
        self.printer.print(f"Left team: {team_id}")
        return Response(
            success=True,
            message=f"Left team '{team_id}'",
            data={"team_id": team_id}
        )
    
    async def _get_team_info(self, kwargs: Dict[str, Any]) -> Response:
        """Get information about a team."""
        team_id = kwargs.get("team_id", self.current_team_id)
        
        if not team_id:
            return Response(
                success=False,
                message="team_id is required",
                data={}
            )
        
        if ORCHESTRATOR_AVAILABLE and self.team_orchestrator:
            team = self.team_orchestrator.teams.get(team_id)
            if team:
                team_info = team.to_dict()
                
                info_summary = f"Team: {team.name}\n"
                info_summary += f"Type: {team.team_type.value}\n"
                info_summary += f"Status: {team.status.value}\n"
                info_summary += f"Mission: {team.mission}\n"
                info_summary += f"Members: {team.get_member_count()}\n"
                
                return Response(
                    success=True,
                    message=info_summary,
                    data=team_info
                )
        
        # Fallback if orchestrator not available
        return Response(
            success=True,
            message=f"Team ID: {team_id}",
            data={"team_id": team_id}
        )
    
    async def _get_metrics(self, kwargs: Dict[str, Any]) -> Response:
        """Get communication metrics."""
        if not self.team_protocol:
            return Response(
                success=False,
                message="Not currently in a team",
                data={}
            )
        
        metrics = self.team_protocol.get_communication_metrics()
        
        metrics_summary = f"Communication Metrics:\n"
        metrics_summary += f"Total Messages: {metrics['total_messages']}\n"
        metrics_summary += f"Team Size: {metrics['team_size']}\n"
        
        if 'avg_latency_ms' in metrics:
            metrics_summary += f"Avg Latency: {metrics['avg_latency_ms']:.2f}ms\n"
        
        if 'avg_response_time_s' in metrics:
            metrics_summary += f"Avg Response Time: {metrics['avg_response_time_s']:.2f}s\n"
        
        return Response(
            success=True,
            message=metrics_summary,
            data=metrics
        )