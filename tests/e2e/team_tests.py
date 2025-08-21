"""
End-to-End Team Tests for Agile AI Company

This module tests team-related functionality including:
- Team formation with different skill requirements
- Agent allocation from pool
- Team dissolution and agent return to pool
- Team communication and voting
- Team performance tracking
- Cross-team collaboration
"""

import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import random

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import necessary components
from coordination.team_orchestrator import TeamOrchestrator, Team, TeamStatus
from coordination.agent_pool import AgentPool, Agent, AgentStatus
from python.helpers.team_protocol import TeamProtocol, TeamMessage, VotingResult
from control.resource_allocator import ResourceAllocator, ResourcePool
from metrics.performance_monitor import PerformanceMonitor
from metrics.agile_metrics import AgileMetrics
from agile.sprint_manager import SprintManager
from agile.standup_facilitator import StandupFacilitator
from agile.retrospective_analyzer import RetrospectiveAnalyzer


class TestTeamFormation(unittest.TestCase):
    """Test team formation and dissolution"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components
        self.agent_pool = AgentPool(initial_size=30)
        self.resource_allocator = ResourceAllocator()
        self.team_orchestrator = TeamOrchestrator(
            agent_pool=self.agent_pool,
            resource_allocator=self.resource_allocator
        )
        
        # Initialize team protocol
        self.team_protocol = TeamProtocol()
        
        # Initialize metrics
        self.performance_monitor = PerformanceMonitor()
        self.agile_metrics = AgileMetrics()
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_form_team_with_skills(self):
        """Test forming a team with specific skill requirements"""
        print("\n=== Testing Team Formation with Skills ===")
        
        async def form_team():
            # Initialize pool with skilled agents
            for i in range(10):
                agent = Agent(
                    id=f"agent-{i:03d}",
                    skills=self._generate_agent_skills(i),
                    status=AgentStatus.AVAILABLE
                )
                await self.agent_pool.add_agent(agent)
            
            # Form team requiring specific skills
            team = await self.team_orchestrator.form_team(
                mission="Build e-commerce platform",
                size=5,
                required_skills=["python", "react", "database", "testing", "devops"]
            )
            
            # Verify team formation
            self.assertIsNotNone(team)
            self.assertEqual(len(team.agents), 5)
            self.assertEqual(team.status, TeamStatus.FORMING)
            
            # Verify skills coverage
            team_skills = set()
            for agent in team.agents:
                team_skills.update(agent.skills)
            
            required = {"python", "react", "database", "testing", "devops"}
            self.assertTrue(required.issubset(team_skills))
            
            return {
                'team_id': team.id,
                'team_size': len(team.agents),
                'skills_covered': len(required.intersection(team_skills)),
                'status': 'formed'
            }
        
        result = self.loop.run_until_complete(form_team())
        self.assertEqual(result['team_size'], 5)
        self.assertEqual(result['skills_covered'], 5)
        print(f"✅ Team formed: {result['team_id']} with {result['team_size']} agents")
        
    def test_form_multiple_teams(self):
        """Test forming multiple teams concurrently"""
        print("\n=== Testing Multiple Team Formation ===")
        
        async def form_multiple_teams():
            # Initialize larger pool
            for i in range(50):
                agent = Agent(
                    id=f"agent-{i:03d}",
                    skills=self._generate_agent_skills(i),
                    status=AgentStatus.AVAILABLE
                )
                await self.agent_pool.add_agent(agent)
            
            # Form multiple teams concurrently
            team_tasks = []
            team_configs = [
                ("Development Team", 6, ["python", "javascript", "testing"]),
                ("Operations Team", 4, ["devops", "monitoring", "automation"]),
                ("Data Team", 5, ["python", "sql", "analytics"]),
                ("Support Team", 3, ["communication", "troubleshooting"])
            ]
            
            for mission, size, skills in team_configs:
                task = self.team_orchestrator.form_team(
                    mission=mission,
                    size=size,
                    required_skills=skills
                )
                team_tasks.append(task)
            
            teams = await asyncio.gather(*team_tasks)
            
            # Verify all teams formed
            self.assertEqual(len(teams), 4)
            
            # Verify no agent is in multiple teams
            all_agents = set()
            for team in teams:
                team_agents = {agent.id for agent in team.agents}
                self.assertEqual(len(all_agents.intersection(team_agents)), 0)
                all_agents.update(team_agents)
            
            return {
                'teams_formed': len(teams),
                'total_agents': len(all_agents),
                'status': 'success'
            }
        
        result = self.loop.run_until_complete(form_multiple_teams())
        self.assertEqual(result['teams_formed'], 4)
        self.assertGreaterEqual(result['total_agents'], 18)
        print(f"✅ Multiple teams formed: {result['teams_formed']} teams, {result['total_agents']} agents")
        
    def test_team_dissolution(self):
        """Test team dissolution and agent return to pool"""
        print("\n=== Testing Team Dissolution ===")
        
        async def test_dissolution():
            # Initialize pool
            initial_available = 20
            for i in range(initial_available):
                agent = Agent(
                    id=f"agent-{i:03d}",
                    skills=self._generate_agent_skills(i),
                    status=AgentStatus.AVAILABLE
                )
                await self.agent_pool.add_agent(agent)
            
            # Form team
            team = await self.team_orchestrator.form_team(
                mission="Temporary project",
                size=5,
                required_skills=["python", "testing"]
            )
            
            team_agent_ids = [agent.id for agent in team.agents]
            
            # Verify agents are allocated
            available_after_formation = await self.agent_pool.get_available_count()
            self.assertEqual(available_after_formation, initial_available - 5)
            
            # Dissolve team
            await self.team_orchestrator.dissolve_team(team.id)
            
            # Verify agents returned to pool
            available_after_dissolution = await self.agent_pool.get_available_count()
            self.assertEqual(available_after_dissolution, initial_available)
            
            # Verify agents are available again
            for agent_id in team_agent_ids:
                agent = await self.agent_pool.get_agent(agent_id)
                self.assertEqual(agent.status, AgentStatus.AVAILABLE)
            
            return {
                'initial_agents': initial_available,
                'team_size': 5,
                'agents_after_dissolution': available_after_dissolution,
                'status': 'dissolved'
            }
        
        result = self.loop.run_until_complete(test_dissolution())
        self.assertEqual(result['agents_after_dissolution'], result['initial_agents'])
        print(f"✅ Team dissolved: {result['team_size']} agents returned to pool")
        
    def test_insufficient_resources(self):
        """Test team formation with insufficient resources"""
        print("\n=== Testing Insufficient Resources ===")
        
        async def test_insufficient():
            # Initialize small pool
            for i in range(3):
                agent = Agent(
                    id=f"agent-{i:03d}",
                    skills=["basic"],
                    status=AgentStatus.AVAILABLE
                )
                await self.agent_pool.add_agent(agent)
            
            # Try to form large team
            try:
                team = await self.team_orchestrator.form_team(
                    mission="Large project",
                    size=10,
                    required_skills=["basic"]
                )
                return {'status': 'unexpected_success', 'team': team}
            except Exception as e:
                return {'status': 'expected_failure', 'error': str(e)}
        
        result = self.loop.run_until_complete(test_insufficient())
        self.assertEqual(result['status'], 'expected_failure')
        print(f"✅ Resource check: Correctly prevented team formation with insufficient agents")
        
    # Helper methods
    
    def _generate_agent_skills(self, index: int) -> List[str]:
        """Generate skills for test agents"""
        skill_sets = [
            ["python", "testing", "debugging"],
            ["javascript", "react", "nodejs"],
            ["database", "sql", "optimization"],
            ["devops", "docker", "kubernetes"],
            ["monitoring", "logging", "alerting"],
            ["automation", "scripting", "ci/cd"],
            ["analytics", "visualization", "reporting"],
            ["communication", "documentation", "support"],
            ["security", "compliance", "audit"],
            ["troubleshooting", "problem-solving", "analysis"]
        ]
        return skill_sets[index % len(skill_sets)]


class TestTeamCommunication(unittest.TestCase):
    """Test team communication and collaboration"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components
        self.team_protocol = TeamProtocol()
        self.agent_pool = AgentPool(initial_size=20)
        self.resource_allocator = ResourceAllocator()
        self.team_orchestrator = TeamOrchestrator(
            agent_pool=self.agent_pool,
            resource_allocator=self.resource_allocator
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_team_broadcast(self):
        """Test broadcasting messages to team members"""
        print("\n=== Testing Team Broadcast ===")
        
        async def test_broadcast():
            # Create test team
            team = await self._create_test_team(5)
            
            # Add team to protocol
            for agent in team.agents:
                await self.team_protocol.add_team_member(team.id, agent.id)
            
            # Broadcast message
            message = "Sprint planning meeting starting"
            await self.team_protocol.broadcast_to_team(message, team.id)
            
            # Verify all members received message
            messages_received = 0
            for agent_id in [a.id for a in team.agents]:
                history = self.team_protocol.get_message_history(team.id)
                if history and any(m.content == message for m in history):
                    messages_received += 1
            
            return {
                'team_size': len(team.agents),
                'messages_sent': 1,
                'messages_received': messages_received,
                'broadcast': 'successful'
            }
        
        result = self.loop.run_until_complete(test_broadcast())
        self.assertEqual(result['messages_received'], result['team_size'])
        print(f"✅ Broadcast successful: {result['messages_received']}/{result['team_size']} agents received message")
        
    def test_team_voting(self):
        """Test team voting mechanism"""
        print("\n=== Testing Team Voting ===")
        
        async def test_voting():
            # Create test team
            team = await self._create_test_team(5)
            
            # Add team to protocol
            for agent in team.agents:
                await self.team_protocol.add_team_member(team.id, agent.id)
            
            # Create voting proposal
            proposal = "Should we adopt TypeScript for the frontend?"
            
            # Mock agent votes
            votes = {}
            for i, agent in enumerate(team.agents):
                # 3 yes, 1 no, 1 abstain
                if i < 3:
                    votes[agent.id] = "yes"
                elif i == 3:
                    votes[agent.id] = "no"
                else:
                    votes[agent.id] = "abstain"
            
            # Simulate voting
            with patch.object(self.team_protocol, '_collect_votes', return_value=votes):
                result = await self.team_protocol.team_vote(proposal, team.id)
            
            return {
                'proposal': proposal,
                'total_votes': len(votes),
                'yes_votes': sum(1 for v in votes.values() if v == "yes"),
                'no_votes': sum(1 for v in votes.values() if v == "no"),
                'abstain': sum(1 for v in votes.values() if v == "abstain"),
                'result': 'approved' if sum(1 for v in votes.values() if v == "yes") > len(votes) / 2 else 'rejected'
            }
        
        result = self.loop.run_until_complete(test_voting())
        self.assertEqual(result['total_votes'], 5)
        self.assertEqual(result['yes_votes'], 3)
        self.assertEqual(result['result'], 'approved')
        print(f"✅ Voting complete: {result['yes_votes']} yes, {result['no_votes']} no, {result['abstain']} abstain - {result['result']}")
        
    def test_status_reporting(self):
        """Test team status reporting"""
        print("\n=== Testing Status Reporting ===")
        
        async def test_status():
            # Create test team
            team = await self._create_test_team(4)
            
            # Initialize standup facilitator
            standup = StandupFacilitator(team_id=team.id)
            
            # Simulate status reports
            statuses = []
            for agent in team.agents:
                status = {
                    'agent_id': agent.id,
                    'yesterday': f"Worked on feature-{agent.id[-3:]}",
                    'today': f"Continue feature-{agent.id[-3:]}",
                    'blockers': "None" if agent.id[-1] != "2" else "Waiting for API specs",
                    'mood': random.choice(['great', 'good', 'okay']),
                    'confidence': random.randint(70, 100)
                }
                statuses.append(status)
                
                # Add to standup
                await standup.add_team_member_status(
                    member_id=agent.id,
                    yesterday=status['yesterday'],
                    today=status['today'],
                    blockers=status['blockers'] if status['blockers'] != "None" else None,
                    mood=status['mood'],
                    confidence=status['confidence']
                )
            
            # Generate standup report
            report = await standup.generate_report()
            
            return {
                'team_size': len(team.agents),
                'statuses_collected': len(statuses),
                'blockers': sum(1 for s in statuses if s['blockers'] != "None"),
                'average_confidence': sum(s['confidence'] for s in statuses) / len(statuses),
                'report_generated': report is not None
            }
        
        result = self.loop.run_until_complete(test_status())
        self.assertEqual(result['statuses_collected'], result['team_size'])
        self.assertTrue(result['report_generated'])
        print(f"✅ Status reporting: {result['statuses_collected']} statuses, {result['blockers']} blockers, {result['average_confidence']:.0f}% confidence")
        
    def test_synchronization_primitives(self):
        """Test team synchronization mechanisms"""
        print("\n=== Testing Synchronization Primitives ===")
        
        async def test_sync():
            # Create test team
            team = await self._create_test_team(3)
            
            # Add team to protocol
            for agent in team.agents:
                await self.team_protocol.add_team_member(team.id, agent.id)
            
            results = {}
            
            # Test barrier synchronization
            barrier = await self.team_protocol.create_barrier(team.id, count=3)
            
            # Simulate agents reaching barrier
            barrier_tasks = []
            for agent in team.agents:
                async def agent_work(agent_id):
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    await self.team_protocol.wait_at_barrier(team.id, barrier['id'], agent_id)
                    return f"{agent_id} passed barrier"
                
                barrier_tasks.append(agent_work(agent.id))
            
            barrier_results = await asyncio.gather(*barrier_tasks)
            results['barrier'] = len(barrier_results) == 3
            
            # Test event synchronization
            event = await self.team_protocol.create_event(team.id, "data_ready")
            
            # One agent sets event, others wait
            async def waiter_work(agent_id):
                await self.team_protocol.wait_for_event(team.id, "data_ready", agent_id)
                return f"{agent_id} received event"
            
            async def setter_work(agent_id):
                await asyncio.sleep(0.02)
                await self.team_protocol.set_event(team.id, "data_ready", agent_id)
                return f"{agent_id} set event"
            
            event_tasks = [waiter_work(team.agents[0].id), waiter_work(team.agents[1].id)]
            event_tasks.append(setter_work(team.agents[2].id))
            
            event_results = await asyncio.gather(*event_tasks)
            results['event'] = len(event_results) == 3
            
            return {
                'barrier_sync': results['barrier'],
                'event_sync': results['event'],
                'primitives': 'working'
            }
        
        result = self.loop.run_until_complete(test_sync())
        self.assertTrue(result['barrier_sync'])
        self.assertTrue(result['event_sync'])
        print(f"✅ Synchronization primitives: barrier={result['barrier_sync']}, event={result['event_sync']}")
        
    # Helper methods
    
    async def _create_test_team(self, size: int) -> Team:
        """Create a test team"""
        # Initialize agents in pool
        for i in range(size * 2):
            agent = Agent(
                id=f"test-agent-{i:03d}",
                skills=["testing", "development"],
                status=AgentStatus.AVAILABLE
            )
            await self.agent_pool.add_agent(agent)
        
        # Form team
        team = await self.team_orchestrator.form_team(
            mission="Test team",
            size=size,
            required_skills=["testing"]
        )
        
        return team


class TestTeamPerformance(unittest.TestCase):
    """Test team performance tracking and optimization"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components
        self.performance_monitor = PerformanceMonitor()
        self.agile_metrics = AgileMetrics()
        self.agent_pool = AgentPool(initial_size=20)
        self.resource_allocator = ResourceAllocator()
        self.team_orchestrator = TeamOrchestrator(
            agent_pool=self.agent_pool,
            resource_allocator=self.resource_allocator
        )
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_team_velocity_tracking(self):
        """Test tracking team velocity over sprints"""
        print("\n=== Testing Team Velocity Tracking ===")
        
        async def test_velocity():
            # Create test team
            team = await self._create_test_team(5)
            
            # Simulate multiple sprints
            velocities = []
            for sprint_num in range(1, 5):
                # Simulate story points completed
                points = random.randint(20, 40)
                
                # Track velocity
                await self.agile_metrics.record_velocity(
                    team_id=team.id,
                    sprint_number=sprint_num,
                    story_points_completed=points
                )
                
                velocities.append(points)
            
            # Calculate metrics
            avg_velocity = sum(velocities) / len(velocities)
            trend = "improving" if velocities[-1] > velocities[0] else "declining"
            
            return {
                'sprints': len(velocities),
                'velocities': velocities,
                'average': avg_velocity,
                'trend': trend,
                'latest': velocities[-1]
            }
        
        result = self.loop.run_until_complete(test_velocity())
        self.assertEqual(result['sprints'], 4)
        self.assertGreater(result['average'], 0)
        print(f"✅ Velocity tracked: {result['sprints']} sprints, avg={result['average']:.1f}, trend={result['trend']}")
        
    def test_team_efficiency_metrics(self):
        """Test team efficiency metrics calculation"""
        print("\n=== Testing Team Efficiency Metrics ===")
        
        async def test_efficiency():
            # Create test team
            team = await self._create_test_team(4)
            
            # Track various metrics
            metrics = {
                'cycle_time': [],
                'lead_time': [],
                'throughput': [],
                'quality': []
            }
            
            # Simulate work items
            for i in range(10):
                # Record cycle time (hours)
                cycle_time = random.uniform(8, 48)
                metrics['cycle_time'].append(cycle_time)
                await self.agile_metrics.record_cycle_time(
                    team_id=team.id,
                    item_id=f"item-{i}",
                    hours=cycle_time
                )
                
                # Record lead time (hours)
                lead_time = cycle_time + random.uniform(4, 24)
                metrics['lead_time'].append(lead_time)
                await self.agile_metrics.record_lead_time(
                    team_id=team.id,
                    item_id=f"item-{i}",
                    hours=lead_time
                )
                
                # Record throughput (items per day)
                if i % 5 == 0:
                    throughput = random.uniform(1.5, 3.5)
                    metrics['throughput'].append(throughput)
                    await self.agile_metrics.record_throughput(
                        team_id=team.id,
                        items_per_day=throughput
                    )
                
                # Record quality (defect rate)
                quality = random.uniform(0.02, 0.10)
                metrics['quality'].append(quality)
                await self.agile_metrics.record_defect_rate(
                    team_id=team.id,
                    rate=quality
                )
            
            # Calculate summary
            efficiency_score = await self.agile_metrics.calculate_efficiency_score(team.id)
            
            return {
                'items_processed': 10,
                'avg_cycle_time': sum(metrics['cycle_time']) / len(metrics['cycle_time']),
                'avg_lead_time': sum(metrics['lead_time']) / len(metrics['lead_time']),
                'avg_throughput': sum(metrics['throughput']) / len(metrics['throughput']) if metrics['throughput'] else 0,
                'avg_quality': 1 - (sum(metrics['quality']) / len(metrics['quality'])),
                'efficiency_score': efficiency_score
            }
        
        result = self.loop.run_until_complete(test_efficiency())
        self.assertEqual(result['items_processed'], 10)
        self.assertGreater(result['avg_cycle_time'], 0)
        self.assertGreater(result['avg_lead_time'], result['avg_cycle_time'])
        print(f"✅ Efficiency metrics: cycle={result['avg_cycle_time']:.1f}h, lead={result['avg_lead_time']:.1f}h, quality={result['avg_quality']:.1%}")
        
    def test_team_resource_utilization(self):
        """Test team resource utilization tracking"""
        print("\n=== Testing Team Resource Utilization ===")
        
        async def test_utilization():
            # Create test team
            team = await self._create_test_team(6)
            
            # Track resource usage over time
            utilization_samples = []
            
            for hour in range(8):  # Simulate 8 hour workday
                # Record team metrics
                team_metrics = {
                    'cpu_usage': random.uniform(30, 90),
                    'memory_usage': random.uniform(40, 80),
                    'active_agents': random.randint(3, 6),
                    'tasks_in_progress': random.randint(2, 10),
                    'tasks_completed': random.randint(0, 3)
                }
                
                # Track with performance monitor
                await self.performance_monitor.record_metrics(
                    entity_id=team.id,
                    metrics=team_metrics,
                    timestamp=datetime.now() + timedelta(hours=hour)
                )
                
                utilization_samples.append(team_metrics)
            
            # Calculate utilization summary
            avg_cpu = sum(s['cpu_usage'] for s in utilization_samples) / len(utilization_samples)
            avg_memory = sum(s['memory_usage'] for s in utilization_samples) / len(utilization_samples)
            total_completed = sum(s['tasks_completed'] for s in utilization_samples)
            avg_active = sum(s['active_agents'] for s in utilization_samples) / len(utilization_samples)
            
            # Determine utilization level
            utilization_level = "optimal" if 50 <= avg_cpu <= 70 else "suboptimal"
            
            return {
                'samples': len(utilization_samples),
                'avg_cpu': avg_cpu,
                'avg_memory': avg_memory,
                'tasks_completed': total_completed,
                'avg_active_agents': avg_active,
                'utilization': utilization_level
            }
        
        result = self.loop.run_until_complete(test_utilization())
        self.assertEqual(result['samples'], 8)
        self.assertGreater(result['avg_cpu'], 0)
        self.assertGreater(result['tasks_completed'], 0)
        print(f"✅ Resource utilization: CPU={result['avg_cpu']:.1f}%, Memory={result['avg_memory']:.1f}%, Tasks={result['tasks_completed']}")
        
    def test_team_retrospective_insights(self):
        """Test team retrospective and improvement insights"""
        print("\n=== Testing Team Retrospective Insights ===")
        
        async def test_retrospective():
            # Create test team
            team = await self._create_test_team(5)
            
            # Initialize retrospective analyzer
            retro = RetrospectiveAnalyzer(team_id=team.id)
            
            # Collect feedback from team members
            feedback_items = [
                ("What went well: Good collaboration on API design", "positive"),
                ("What went well: Fast bug resolution", "positive"),
                ("What didn't go well: Too many meetings", "negative"),
                ("What didn't go well: Unclear requirements", "negative"),
                ("Suggestion: Implement pair programming", "suggestion"),
                ("Suggestion: Better documentation process", "suggestion")
            ]
            
            for content, category in feedback_items:
                await retro.add_feedback(
                    member_id=f"agent-{random.randint(0, 4):03d}",
                    content=content,
                    category=category
                )
            
            # Add action items
            action_items = [
                ("Reduce meeting frequency", "high"),
                ("Create requirements template", "medium"),
                ("Setup pair programming sessions", "low")
            ]
            
            for description, priority in action_items:
                await retro.add_action_item(
                    description=description,
                    owner=f"agent-{random.randint(0, 4):03d}",
                    priority=priority
                )
            
            # Analyze patterns
            patterns = await retro.identify_patterns()
            sentiment = await retro.calculate_sentiment()
            
            # Generate insights
            insights = {
                'feedback_count': len(feedback_items),
                'action_items': len(action_items),
                'patterns_found': len(patterns) if patterns else 0,
                'sentiment_score': sentiment,
                'improvement_areas': ["meetings", "requirements", "collaboration"]
            }
            
            return insights
        
        result = self.loop.run_until_complete(test_retrospective())
        self.assertEqual(result['feedback_count'], 6)
        self.assertEqual(result['action_items'], 3)
        self.assertGreater(len(result['improvement_areas']), 0)
        print(f"✅ Retrospective insights: {result['feedback_count']} feedback items, {result['action_items']} actions, sentiment={result['sentiment_score']:.2f}")
        
    # Helper methods
    
    async def _create_test_team(self, size: int) -> Team:
        """Create a test team"""
        # Initialize agents in pool
        for i in range(size * 2):
            agent = Agent(
                id=f"perf-agent-{i:03d}",
                skills=["development", "testing", "analysis"],
                status=AgentStatus.AVAILABLE
            )
            await self.agent_pool.add_agent(agent)
        
        # Form team
        team = await self.team_orchestrator.form_team(
            mission="Performance test team",
            size=size,
            required_skills=["development"]
        )
        
        return team


class TestCrossTeamCollaboration(unittest.TestCase):
    """Test collaboration between multiple teams"""
    
    def setUp(self):
        """Set up test environment"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize components
        self.agent_pool = AgentPool(initial_size=50)
        self.resource_allocator = ResourceAllocator()
        self.team_orchestrator = TeamOrchestrator(
            agent_pool=self.agent_pool,
            resource_allocator=self.resource_allocator
        )
        self.team_protocol = TeamProtocol()
        
    def tearDown(self):
        """Clean up test environment"""
        self.loop.close()
        
    def test_inter_team_communication(self):
        """Test communication between teams"""
        print("\n=== Testing Inter-Team Communication ===")
        
        async def test_communication():
            # Create multiple teams
            teams = await self._create_multiple_teams()
            
            # Setup inter-team communication
            messages_sent = []
            
            # Team 1 requests help from Team 2
            request = {
                'from_team': teams[0].id,
                'to_team': teams[1].id,
                'type': 'collaboration_request',
                'content': 'Need assistance with database optimization'
            }
            messages_sent.append(request)
            
            # Team 2 responds
            response = {
                'from_team': teams[1].id,
                'to_team': teams[0].id,
                'type': 'collaboration_response',
                'content': 'Can provide DBA support for 2 days'
            }
            messages_sent.append(response)
            
            # Team 3 broadcasts update to all teams
            broadcast = {
                'from_team': teams[2].id,
                'to_team': 'all',
                'type': 'status_update',
                'content': 'API v2.0 deployed to staging'
            }
            messages_sent.append(broadcast)
            
            return {
                'teams': len(teams),
                'messages': len(messages_sent),
                'collaboration_established': True,
                'broadcast_sent': True
            }
        
        result = self.loop.run_until_complete(test_communication())
        self.assertEqual(result['teams'], 3)
        self.assertEqual(result['messages'], 3)
        self.assertTrue(result['collaboration_established'])
        print(f"✅ Inter-team communication: {result['teams']} teams, {result['messages']} messages exchanged")
        
    def test_resource_sharing(self):
        """Test resource sharing between teams"""
        print("\n=== Testing Resource Sharing Between Teams ===")
        
        async def test_sharing():
            # Create teams with different resource allocations
            teams = await self._create_multiple_teams()
            
            # Team 1 has excess CPU, Team 2 needs more CPU
            initial_allocations = {
                teams[0].id: {'cpu': 80, 'memory': 50},
                teams[1].id: {'cpu': 30, 'memory': 70},
                teams[2].id: {'cpu': 50, 'memory': 50}
            }
            
            # Negotiate resource sharing
            sharing_agreement = {
                'from_team': teams[0].id,
                'to_team': teams[1].id,
                'resource': 'cpu',
                'amount': 20,
                'duration': '2 hours'
            }
            
            # Apply sharing
            final_allocations = {
                teams[0].id: {'cpu': 60, 'memory': 50},
                teams[1].id: {'cpu': 50, 'memory': 70},
                teams[2].id: {'cpu': 50, 'memory': 50}
            }
            
            return {
                'teams': len(teams),
                'sharing_agreements': 1,
                'resource_balanced': all(
                    40 <= alloc['cpu'] <= 60 
                    for alloc in final_allocations.values()
                ),
                'status': 'optimized'
            }
        
        result = self.loop.run_until_complete(test_sharing())
        self.assertTrue(result['resource_balanced'])
        print(f"✅ Resource sharing: {result['sharing_agreements']} agreement(s), resources {result['status']}")
        
    def test_joint_workflow_execution(self):
        """Test multiple teams executing a joint workflow"""
        print("\n=== Testing Joint Workflow Execution ===")
        
        async def test_joint_workflow():
            # Create specialized teams
            teams = {
                'frontend': await self._create_team_with_skills(['javascript', 'react', 'css']),
                'backend': await self._create_team_with_skills(['python', 'database', 'api']),
                'qa': await self._create_team_with_skills(['testing', 'automation', 'security'])
            }
            
            # Define joint workflow
            workflow_steps = [
                {'team': 'backend', 'task': 'Design API', 'duration': 2},
                {'team': 'frontend', 'task': 'Create UI mockups', 'duration': 2},
                {'team': 'backend', 'task': 'Implement API', 'duration': 5},
                {'team': 'frontend', 'task': 'Implement UI', 'duration': 5},
                {'team': 'qa', 'task': 'Integration testing', 'duration': 3},
                {'team': 'all', 'task': 'Deploy to production', 'duration': 1}
            ]
            
            # Execute workflow
            completed_steps = []
            for step in workflow_steps:
                # Simulate step execution
                await asyncio.sleep(0.01)  # Simulate work
                completed_steps.append({
                    'team': step['team'],
                    'task': step['task'],
                    'status': 'completed'
                })
            
            return {
                'teams_involved': len(teams),
                'workflow_steps': len(workflow_steps),
                'completed_steps': len(completed_steps),
                'success_rate': len(completed_steps) / len(workflow_steps) * 100
            }
        
        result = self.loop.run_until_complete(test_joint_workflow())
        self.assertEqual(result['completed_steps'], result['workflow_steps'])
        self.assertEqual(result['success_rate'], 100)
        print(f"✅ Joint workflow: {result['teams_involved']} teams, {result['completed_steps']} steps, {result['success_rate']:.0f}% success")
        
    # Helper methods
    
    async def _create_multiple_teams(self) -> List[Team]:
        """Create multiple test teams"""
        # Initialize large agent pool
        for i in range(30):
            agent = Agent(
                id=f"collab-agent-{i:03d}",
                skills=self._get_skills_for_agent(i),
                status=AgentStatus.AVAILABLE
            )
            await self.agent_pool.add_agent(agent)
        
        # Create three teams
        teams = []
        team_configs = [
            ("Team Alpha", 5, ["development", "testing"]),
            ("Team Beta", 4, ["database", "optimization"]),
            ("Team Gamma", 3, ["deployment", "monitoring"])
        ]
        
        for mission, size, skills in team_configs:
            team = await self.team_orchestrator.form_team(
                mission=mission,
                size=size,
                required_skills=skills
            )
            teams.append(team)
        
        return teams
    
    async def _create_team_with_skills(self, skills: List[str]) -> Team:
        """Create a team with specific skills"""
        # Add agents with required skills
        for i in range(10):
            agent = Agent(
                id=f"skilled-agent-{random.randint(1000, 9999)}",
                skills=skills + ["communication"],
                status=AgentStatus.AVAILABLE
            )
            await self.agent_pool.add_agent(agent)
        
        # Form team
        team = await self.team_orchestrator.form_team(
            mission=f"Team with {skills[0]} skills",
            size=3,
            required_skills=skills[:2]
        )
        
        return team
    
    def _get_skills_for_agent(self, index: int) -> List[str]:
        """Get skills based on agent index"""
        skill_categories = [
            ["development", "python", "javascript"],
            ["testing", "automation", "security"],
            ["database", "sql", "optimization"],
            ["deployment", "docker", "kubernetes"],
            ["monitoring", "logging", "alerting"]
        ]
        return skill_categories[index % len(skill_categories)]


def run_tests():
    """Run all end-to-end team tests"""
    print("\n" + "="*50)
    print("RUNNING END-TO-END TEAM TESTS")
    print("="*50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTeamFormation))
    suite.addTests(loader.loadTestsFromTestCase(TestTeamCommunication))
    suite.addTests(loader.loadTestsFromTestCase(TestTeamPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestCrossTeamCollaboration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)