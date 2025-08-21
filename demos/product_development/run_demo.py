#!/usr/bin/env python3
"""
Product Development Demo Runner
Demonstrates full agile product development cycle with AI agents
"""

import os
import sys
import json
import yaml
import asyncio
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Import framework components
from coordination.workflow_engine import WorkflowEngine
from coordination.team_orchestrator import TeamOrchestrator
from coordination.document_manager import DocumentManager
from agile.sprint_manager import SprintManager
from agile.product_backlog import ProductBacklog
from metrics.performance_monitor import PerformanceMonitor
from control.ethics_engine import EthicsEngine
from control.safety_monitor import SafetyMonitor

class ProductDevelopmentDemo:
    """Orchestrates the product development demonstration"""
    
    def __init__(self, config_path: str = "scenario.yaml", interactive: bool = False):
        """Initialize demo with configuration"""
        self.config = self._load_config(config_path)
        self.interactive = interactive
        self.outputs_dir = Path("outputs")
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.workflow_engine = None
        self.team_orchestrator = None
        self.document_manager = None
        self.sprint_manager = None
        self.performance_monitor = None
        self.ethics_engine = None
        self.safety_monitor = None
        
        # Demo state
        self.start_time = None
        self.end_time = None
        self.metrics = {}
        self.artifacts = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load demo configuration from YAML"""
        config_file = Path(config_path)
        if not config_file.exists():
            config_file = Path(__file__).parent / config_path
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    async def setup(self):
        """Initialize all demo components"""
        print("🚀 Setting up Product Development Demo...")
        
        # Initialize control layer
        self.ethics_engine = EthicsEngine()
        self.safety_monitor = SafetyMonitor()
        await self.safety_monitor.start_monitoring()
        
        # Initialize coordination layer
        self.workflow_engine = WorkflowEngine()
        self.team_orchestrator = TeamOrchestrator()
        self.document_manager = DocumentManager()
        
        # Initialize agile components
        self.product_backlog = ProductBacklog()
        self.sprint_manager = SprintManager(
            sprint_duration=timedelta(days=self.config['sprint']['duration_days'])
        )
        
        # Initialize monitoring
        self.performance_monitor = PerformanceMonitor()
        self.performance_monitor.start_monitoring()
        
        print("✅ Setup complete")
        
    async def run_phase_1_product_definition(self):
        """Phase 1: Product Definition"""
        print("\n" + "="*60)
        print("📋 PHASE 1: PRODUCT DEFINITION")
        print("="*60)
        
        if self.interactive:
            input("\nPress Enter to start Product Definition phase...")
        
        # Create PRD
        print("\n1. Product Manager creating PRD...")
        prd_content = await self._create_prd()
        self.artifacts['PRD'] = prd_content
        
        # Save PRD
        prd_path = self.outputs_dir / "PRD.md"
        with open(prd_path, 'w') as f:
            f.write(prd_content)
        print(f"   ✅ PRD saved to {prd_path}")
        
        # Create Architecture
        print("\n2. Architect reviewing PRD and creating system architecture...")
        architecture = await self._create_architecture(prd_content)
        self.artifacts['architecture'] = architecture
        
        # Save Architecture
        arch_path = self.outputs_dir / "architecture.md"
        with open(arch_path, 'w') as f:
            f.write(architecture)
        print(f"   ✅ Architecture saved to {arch_path}")
        
        # Form Team
        print("\n3. Forming development team based on requirements...")
        team = await self._form_team()
        self.artifacts['team'] = team
        print(f"   ✅ Team formed with {len(team['members'])} members")
        
        if self.interactive:
            print("\n📊 Phase 1 Summary:")
            print(f"   - PRD created with {len(self.config['product']['features'])} features")
            print(f"   - Architecture designed with microservices approach")
            print(f"   - Team of {len(team['members'])} specialists formed")
            input("\nPress Enter to continue to Sprint Planning...")
    
    async def run_phase_2_sprint_planning(self):
        """Phase 2: Sprint Planning"""
        print("\n" + "="*60)
        print("📅 PHASE 2: SPRINT PLANNING")
        print("="*60)
        
        if self.interactive:
            input("\nPress Enter to start Sprint Planning phase...")
        
        # Create backlog
        print("\n1. Product Manager creating and prioritizing backlog...")
        backlog = await self._create_backlog()
        self.artifacts['backlog'] = backlog
        
        # Sprint planning
        print("\n2. Scrum Master facilitating sprint planning...")
        sprint_backlog = await self._plan_sprint(backlog)
        self.artifacts['sprint_backlog'] = sprint_backlog
        
        # Save sprint backlog
        backlog_path = self.outputs_dir / "sprint_backlog.md"
        with open(backlog_path, 'w') as f:
            f.write(self._format_sprint_backlog(sprint_backlog))
        print(f"   ✅ Sprint backlog saved to {backlog_path}")
        
        # Team commitment
        print("\n3. Team committing to sprint goals...")
        commitment = await self._get_team_commitment(sprint_backlog)
        self.artifacts['commitment'] = commitment
        print(f"   ✅ Team committed to {commitment['story_points']} story points")
        
        if self.interactive:
            print("\n📊 Phase 2 Summary:")
            print(f"   - Backlog created with {len(backlog)} stories")
            print(f"   - Sprint planned with {len(sprint_backlog)} stories")
            print(f"   - Team capacity: {commitment['capacity']} hours")
            print(f"   - Committed points: {commitment['story_points']}")
            input("\nPress Enter to continue to Development Sprint...")
    
    async def run_phase_3_development_sprint(self):
        """Phase 3: Development Sprint"""
        print("\n" + "="*60)
        print("💻 PHASE 3: DEVELOPMENT SPRINT")
        print("="*60)
        
        if self.interactive:
            input("\nPress Enter to start Development Sprint phase...")
        
        # Daily standups
        print("\n1. Running daily standups...")
        standups = []
        for day in range(1, 6):  # 5 days for demo
            print(f"\n   Day {day} Standup:")
            standup = await self._run_standup(day)
            standups.append(standup)
            print(f"      - Progress: {standup['progress']}%")
            print(f"      - Blockers: {len(standup['blockers'])}")
            
            if self.interactive and day == 3:
                input("\n   Press Enter to continue sprint execution...")
        
        self.artifacts['standups'] = standups
        
        # Development work
        print("\n2. Developers implementing user stories...")
        implementations = await self._implement_stories()
        self.artifacts['implementations'] = implementations
        
        # Save implementations
        impl_dir = self.outputs_dir / "implementations"
        impl_dir.mkdir(exist_ok=True)
        for story_id, impl in implementations.items():
            impl_path = impl_dir / f"{story_id}.md"
            with open(impl_path, 'w') as f:
                f.write(impl)
        print(f"   ✅ {len(implementations)} stories implemented")
        
        # Testing
        print("\n3. QA Engineer testing implementations...")
        test_results = await self._run_tests(implementations)
        self.artifacts['test_results'] = test_results
        
        # Save test results
        test_dir = self.outputs_dir / "test_results"
        test_dir.mkdir(exist_ok=True)
        for story_id, result in test_results.items():
            test_path = test_dir / f"{story_id}_test.json"
            with open(test_path, 'w') as f:
                json.dump(result, f, indent=2)
        print(f"   ✅ {len(test_results)} stories tested")
        print(f"   ✅ Pass rate: {self._calculate_pass_rate(test_results)}%")
        
        # Code review
        print("\n4. Architect reviewing code...")
        reviews = await self._review_code(implementations)
        self.artifacts['code_reviews'] = reviews
        print(f"   ✅ Code quality score: {self._calculate_quality_score(reviews)}%")
        
        if self.interactive:
            print("\n📊 Phase 3 Summary:")
            print(f"   - Stories completed: {len(implementations)}")
            print(f"   - Test pass rate: {self._calculate_pass_rate(test_results)}%")
            print(f"   - Code quality: {self._calculate_quality_score(reviews)}%")
            print(f"   - Sprint velocity: {self._calculate_velocity(implementations)} points")
            input("\nPress Enter to continue to Sprint Review & Retrospective...")
    
    async def run_phase_4_review_retrospective(self):
        """Phase 4: Sprint Review & Retrospective"""
        print("\n" + "="*60)
        print("🔍 PHASE 4: SPRINT REVIEW & RETROSPECTIVE")
        print("="*60)
        
        if self.interactive:
            input("\nPress Enter to start Sprint Review & Retrospective phase...")
        
        # Sprint review
        print("\n1. Conducting sprint review...")
        review = await self._conduct_review()
        self.artifacts['sprint_review'] = review
        
        # Save sprint review
        review_path = self.outputs_dir / "sprint_review.md"
        with open(review_path, 'w') as f:
            f.write(self._format_review(review))
        print(f"   ✅ Sprint review saved to {review_path}")
        
        # Retrospective
        print("\n2. Facilitating retrospective...")
        retrospective = await self._conduct_retrospective()
        self.artifacts['retrospective'] = retrospective
        
        # Save retrospective
        retro_path = self.outputs_dir / "retrospective.md"
        with open(retro_path, 'w') as f:
            f.write(self._format_retrospective(retrospective))
        print(f"   ✅ Retrospective saved to {retro_path}")
        
        # Metrics analysis
        print("\n3. Analyzing sprint metrics...")
        metrics = await self._analyze_metrics()
        self.artifacts['metrics'] = metrics
        
        # Save metrics
        metrics_path = self.outputs_dir / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"   ✅ Metrics saved to {metrics_path}")
        
        if self.interactive:
            print("\n📊 Phase 4 Summary:")
            print(f"   - Sprint goal achieved: {review['goal_achieved']}")
            print(f"   - Velocity: {metrics['velocity']} points")
            print(f"   - Quality score: {metrics['quality']}%")
            print(f"   - Team satisfaction: {retrospective['satisfaction']}/5")
            print(f"   - Action items: {len(retrospective['action_items'])}")
    
    async def _create_prd(self) -> str:
        """Simulate PRD creation by PM agent"""
        # In real implementation, this would call the PM agent
        # For demo, we'll generate a formatted PRD
        with open("inputs/requirements.md", 'r') as f:
            requirements = f.read()
        
        prd = f"""# Product Requirements Document
## TaskFlow AI - Intelligent Task Management System

Generated: {datetime.now().isoformat()}
Author: Product Manager Agent

{requirements}

## Approval Status
- **Status**: APPROVED
- **Approved By**: Product Owner
- **Date**: {datetime.now().isoformat()}
- **Quality Score**: 92/100
"""
        return prd
    
    async def _create_architecture(self, prd: str) -> str:
        """Simulate architecture creation by Architect agent"""
        architecture = f"""# System Architecture Document
## TaskFlow AI - Technical Architecture

Generated: {datetime.now().isoformat()}
Author: System Architect Agent

## Overview
Based on the PRD analysis, TaskFlow AI will be built using a microservices architecture with the following key components.

## Architecture Principles
- **Scalability**: Horizontal scaling for all services
- **Resilience**: Circuit breakers and fallback mechanisms
- **Security**: Zero-trust architecture with end-to-end encryption
- **Performance**: Sub-200ms response times

## System Components

### 1. Frontend Layer
- **Technology**: React 18 with TypeScript
- **State Management**: Redux Toolkit
- **UI Framework**: Material-UI v5
- **Real-time**: WebSocket connections

### 2. API Gateway
- **Technology**: Kong Gateway
- **Features**: Rate limiting, authentication, routing
- **Protocol**: REST and GraphQL

### 3. Microservices

#### Task Service
- **Responsibility**: Task CRUD operations
- **Technology**: Node.js with Express
- **Database**: PostgreSQL
- **Cache**: Redis

#### AI Service
- **Responsibility**: ML models and predictions
- **Technology**: Python with FastAPI
- **ML Framework**: TensorFlow 2.x
- **Model Storage**: S3

#### Notification Service
- **Responsibility**: Reminders and alerts
- **Technology**: Node.js
- **Queue**: RabbitMQ
- **Channels**: Email, Push, SMS

#### Integration Service
- **Responsibility**: Third-party integrations
- **Technology**: Node.js
- **Adapters**: Calendar, Project Management tools

### 4. Data Layer
- **Primary DB**: PostgreSQL 14
- **Cache**: Redis 7
- **Search**: Elasticsearch 8
- **Message Queue**: RabbitMQ

### 5. Infrastructure
- **Platform**: AWS
- **Container**: Docker with Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

## Security Architecture
- JWT-based authentication
- OAuth 2.0 for integrations
- TLS 1.3 for all communications
- Encryption at rest using AES-256

## Quality Attributes
- **Availability**: 99.9% uptime
- **Performance**: p99 latency < 200ms
- **Scalability**: Support 10,000 concurrent users
- **Security**: SOC 2 compliant

## Deployment Strategy
- Blue-green deployments
- Canary releases for new features
- Automated rollback on failure
- Multi-region deployment

## Approval Status
- **Status**: APPROVED
- **Approved By**: Chief Architect
- **Date**: {datetime.now().isoformat()}
- **Quality Score**: 94/100
"""
        return architecture
    
    async def _form_team(self) -> Dict:
        """Simulate team formation"""
        team_config = self.config['teams']['product_development']
        team = {
            'name': team_config['name'],
            'members': [],
            'formed_at': datetime.now().isoformat()
        }
        
        for role_config in team_config['composition']:
            role = role_config['role']
            count = role_config['count']
            for i in range(count):
                member = {
                    'id': f"{role}_{i+1}",
                    'role': role,
                    'profile': role_config['agent_profile'],
                    'status': 'active',
                    'capacity_hours': 6 * self.config['sprint']['duration_days']
                }
                team['members'].append(member)
        
        return team
    
    async def _create_backlog(self) -> List[Dict]:
        """Create product backlog from features"""
        backlog = []
        for i, feature in enumerate(self.config['product']['features']):
            story = {
                'id': f"TASK-{i+1:03d}",
                'title': feature['name'],
                'description': feature['description'],
                'story_points': feature['story_points'],
                'priority': feature['priority'],
                'status': 'backlog',
                'acceptance_criteria': [
                    f"Feature implements {feature['name']}",
                    "Unit tests pass with >80% coverage",
                    "Integration tests pass",
                    "Documentation updated"
                ]
            }
            backlog.append(story)
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        backlog.sort(key=lambda x: priority_order[x['priority']])
        
        return backlog
    
    async def _plan_sprint(self, backlog: List[Dict]) -> List[Dict]:
        """Plan sprint based on capacity"""
        capacity_percentage = self.config['sprint']['capacity_percentage'] / 100
        team_size = self.config['teams']['product_development']['size']
        days = self.config['sprint']['duration_days']
        
        # Calculate capacity in story points (simplified)
        # Assume 1 story point = 4 hours, 6 productive hours per day
        total_hours = team_size * days * 6 * capacity_percentage
        capacity_points = int(total_hours / 4)
        
        sprint_backlog = []
        committed_points = 0
        
        for story in backlog:
            if committed_points + story['story_points'] <= capacity_points:
                story['status'] = 'sprint'
                story['sprint'] = 1
                sprint_backlog.append(story)
                committed_points += story['story_points']
        
        return sprint_backlog
    
    def _format_sprint_backlog(self, sprint_backlog: List[Dict]) -> str:
        """Format sprint backlog as markdown"""
        content = f"""# Sprint Backlog
## Sprint 1

Generated: {datetime.now().isoformat()}
Total Story Points: {sum(s['story_points'] for s in sprint_backlog)}

## Committed User Stories

"""
        for story in sprint_backlog:
            content += f"""### {story['id']}: {story['title']}
**Points**: {story['story_points']}
**Priority**: {story['priority']}
**Description**: {story['description']}

**Acceptance Criteria**:
"""
            for criterion in story['acceptance_criteria']:
                content += f"- {criterion}\n"
            content += "\n---\n\n"
        
        return content
    
    async def _get_team_commitment(self, sprint_backlog: List[Dict]) -> Dict:
        """Get team commitment for sprint"""
        story_points = sum(s['story_points'] for s in sprint_backlog)
        team_size = self.config['teams']['product_development']['size']
        days = self.config['sprint']['duration_days']
        capacity_percentage = self.config['sprint']['capacity_percentage'] / 100
        
        commitment = {
            'sprint': 1,
            'story_points': story_points,
            'stories': len(sprint_backlog),
            'capacity': team_size * days * 6 * capacity_percentage,
            'confidence': 85,  # Team confidence percentage
            'risks': [
                "New AI service integration complexity",
                "Potential dependency on external calendar APIs"
            ]
        }
        
        return commitment
    
    async def _run_standup(self, day: int) -> Dict:
        """Simulate daily standup"""
        progress = min(day * 20, 100)  # 20% progress per day
        
        standup = {
            'day': day,
            'date': (datetime.now() + timedelta(days=day)).isoformat(),
            'progress': progress,
            'updates': [],
            'blockers': []
        }
        
        # Simulate team member updates
        for member in self.artifacts.get('team', {}).get('members', []):
            update = {
                'member': member['id'],
                'yesterday': f"Worked on assigned tasks",
                'today': f"Continue implementation",
                'blockers': []
            }
            
            # Add some blockers on day 2
            if day == 2 and member['role'] == 'developer':
                blocker = "Waiting for API documentation"
                update['blockers'].append(blocker)
                standup['blockers'].append({
                    'member': member['id'],
                    'blocker': blocker,
                    'severity': 'medium'
                })
            
            standup['updates'].append(update)
        
        return standup
    
    async def _implement_stories(self) -> Dict[str, str]:
        """Simulate story implementation"""
        implementations = {}
        
        for story in self.artifacts.get('sprint_backlog', []):
            impl = f"""# Implementation: {story['title']}
## Story ID: {story['id']}

### Implementation Details
- **Developer**: developer_1
- **Start Date**: {datetime.now().isoformat()}
- **Completion Date**: {(datetime.now() + timedelta(days=3)).isoformat()}

### Code Changes
- Created new service module for {story['title']}
- Implemented core business logic
- Added unit tests (coverage: 87%)
- Updated API endpoints
- Added database migrations

### Testing
- Unit tests: ✅ Passed (15/15)
- Integration tests: ✅ Passed (8/8)
- Performance tests: ✅ Passed (meets <200ms requirement)

### Documentation
- API documentation updated
- README updated with new features
- Added usage examples

### Code Review Status
- **Reviewer**: architect_1
- **Status**: Approved
- **Comments**: Clean implementation, follows architecture guidelines
"""
            implementations[story['id']] = impl
        
        return implementations
    
    async def _run_tests(self, implementations: Dict[str, str]) -> Dict[str, Dict]:
        """Simulate testing"""
        test_results = {}
        
        for story_id in implementations:
            test_results[story_id] = {
                'story_id': story_id,
                'tester': 'qa_engineer_1',
                'test_date': datetime.now().isoformat(),
                'test_cases': {
                    'unit_tests': {'total': 15, 'passed': 15, 'failed': 0},
                    'integration_tests': {'total': 8, 'passed': 8, 'failed': 0},
                    'ui_tests': {'total': 5, 'passed': 5, 'failed': 0},
                    'performance_tests': {'total': 3, 'passed': 3, 'failed': 0}
                },
                'defects': [],
                'status': 'PASSED',
                'coverage': 87
            }
            
            # Add a minor defect to one story for realism
            if story_id == 'TASK-003':
                test_results[story_id]['defects'].append({
                    'id': 'BUG-001',
                    'severity': 'low',
                    'description': 'Minor UI alignment issue on mobile',
                    'status': 'fixed'
                })
        
        return test_results
    
    def _calculate_pass_rate(self, test_results: Dict[str, Dict]) -> float:
        """Calculate overall test pass rate"""
        total_tests = 0
        passed_tests = 0
        
        for result in test_results.values():
            for test_type in result['test_cases'].values():
                total_tests += test_type['total']
                passed_tests += test_type['passed']
        
        return round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
    
    async def _review_code(self, implementations: Dict[str, str]) -> Dict[str, Dict]:
        """Simulate code review"""
        reviews = {}
        
        for story_id in implementations:
            reviews[story_id] = {
                'story_id': story_id,
                'reviewer': 'architect_1',
                'review_date': datetime.now().isoformat(),
                'quality_score': 92,
                'issues': [],
                'suggestions': [
                    "Consider adding more error handling",
                    "Could optimize database queries"
                ],
                'status': 'APPROVED'
            }
        
        return reviews
    
    def _calculate_quality_score(self, reviews: Dict[str, Dict]) -> float:
        """Calculate average quality score"""
        scores = [r['quality_score'] for r in reviews.values()]
        return round(sum(scores) / len(scores), 1) if scores else 0
    
    def _calculate_velocity(self, implementations: Dict[str, str]) -> int:
        """Calculate sprint velocity"""
        completed_points = 0
        for story in self.artifacts.get('sprint_backlog', []):
            if story['id'] in implementations:
                completed_points += story['story_points']
        return completed_points
    
    async def _conduct_review(self) -> Dict:
        """Conduct sprint review"""
        implementations = self.artifacts.get('implementations', {})
        sprint_backlog = self.artifacts.get('sprint_backlog', [])
        
        completed = len(implementations)
        total = len(sprint_backlog)
        
        review = {
            'sprint': 1,
            'date': datetime.now().isoformat(),
            'stories_completed': completed,
            'stories_total': total,
            'completion_rate': round((completed / total) * 100, 1) if total > 0 else 0,
            'velocity': self._calculate_velocity(implementations),
            'goal_achieved': completed == total,
            'demonstrations': [
                {
                    'feature': 'Intelligent Task Prioritization',
                    'status': 'Working',
                    'feedback': 'Stakeholders impressed with AI accuracy'
                },
                {
                    'feature': 'Automated Task Breakdown',
                    'status': 'Working',
                    'feedback': 'Useful for complex project planning'
                }
            ],
            'stakeholder_feedback': [
                "Great progress on core features",
                "UI needs some polish",
                "Performance exceeds expectations"
            ],
            'next_sprint_recommendations': [
                "Focus on UI improvements",
                "Add more integration tests",
                "Begin work on smart scheduling"
            ]
        }
        
        return review
    
    def _format_review(self, review: Dict) -> str:
        """Format sprint review as markdown"""
        content = f"""# Sprint Review
## Sprint {review['sprint']}

**Date**: {review['date']}
**Facilitator**: Scrum Master

## Sprint Summary
- **Stories Completed**: {review['stories_completed']}/{review['stories_total']}
- **Completion Rate**: {review['completion_rate']}%
- **Velocity**: {review['velocity']} story points
- **Sprint Goal Achieved**: {'✅ Yes' if review['goal_achieved'] else '❌ No'}

## Feature Demonstrations

"""
        for demo in review['demonstrations']:
            content += f"""### {demo['feature']}
- **Status**: {demo['status']}
- **Feedback**: {demo['feedback']}

"""
        
        content += "## Stakeholder Feedback\n\n"
        for feedback in review['stakeholder_feedback']:
            content += f"- {feedback}\n"
        
        content += "\n## Recommendations for Next Sprint\n\n"
        for rec in review['next_sprint_recommendations']:
            content += f"- {rec}\n"
        
        return content
    
    async def _conduct_retrospective(self) -> Dict:
        """Conduct sprint retrospective"""
        retrospective = {
            'sprint': 1,
            'date': datetime.now().isoformat(),
            'facilitator': 'scrum_master_1',
            'participants': [m['id'] for m in self.artifacts.get('team', {}).get('members', [])],
            'satisfaction': 4.2,  # Out of 5
            'what_went_well': [
                "Good collaboration between developers and QA",
                "All stories completed on time",
                "Effective use of AI for prioritization",
                "Quick blocker resolution"
            ],
            'what_could_improve': [
                "Need better API documentation upfront",
                "More frequent code reviews",
                "Improve estimation accuracy",
                "Better integration test coverage"
            ],
            'action_items': [
                {
                    'id': 'AI-001',
                    'action': 'Create API documentation template',
                    'owner': 'architect_1',
                    'due_date': (datetime.now() + timedelta(days=7)).isoformat()
                },
                {
                    'id': 'AI-002',
                    'action': 'Implement daily code review practice',
                    'owner': 'developer_1',
                    'due_date': (datetime.now() + timedelta(days=3)).isoformat()
                },
                {
                    'id': 'AI-003',
                    'action': 'Add planning poker for estimation',
                    'owner': 'scrum_master_1',
                    'due_date': (datetime.now() + timedelta(days=5)).isoformat()
                }
            ],
            'team_mood': {
                'happy': 3,
                'neutral': 2,
                'concerned': 1
            }
        }
        
        return retrospective
    
    def _format_retrospective(self, retrospective: Dict) -> str:
        """Format retrospective as markdown"""
        content = f"""# Sprint Retrospective
## Sprint {retrospective['sprint']}

**Date**: {retrospective['date']}
**Facilitator**: {retrospective['facilitator']}
**Team Satisfaction**: {retrospective['satisfaction']}/5.0

## What Went Well 🎉

"""
        for item in retrospective['what_went_well']:
            content += f"- {item}\n"
        
        content += "\n## What Could Be Improved 🔧\n\n"
        for item in retrospective['what_could_improve']:
            content += f"- {item}\n"
        
        content += "\n## Action Items 📋\n\n"
        for action in retrospective['action_items']:
            content += f"""### {action['id']}: {action['action']}
- **Owner**: {action['owner']}
- **Due Date**: {action['due_date']}

"""
        
        content += f"""## Team Mood
- 😊 Happy: {retrospective['team_mood']['happy']}
- 😐 Neutral: {retrospective['team_mood']['neutral']}
- 😟 Concerned: {retrospective['team_mood']['concerned']}
"""
        
        return content
    
    async def _analyze_metrics(self) -> Dict:
        """Analyze sprint metrics"""
        test_results = self.artifacts.get('test_results', {})
        reviews = self.artifacts.get('code_reviews', {})
        implementations = self.artifacts.get('implementations', {})
        
        metrics = {
            'sprint': 1,
            'velocity': self._calculate_velocity(implementations),
            'quality': self._calculate_quality_score(reviews),
            'test_coverage': 87,
            'test_pass_rate': self._calculate_pass_rate(test_results),
            'defect_escape_rate': 2,
            'cycle_time_days': 2.5,
            'lead_time_days': 4,
            'team_utilization': 85,
            'story_completion_rate': 100,
            'estimation_accuracy': 92,
            'trends': {
                'velocity_trend': 'increasing',
                'quality_trend': 'stable',
                'team_satisfaction_trend': 'increasing'
            },
            'comparisons': {
                'velocity_vs_average': '+15%',
                'quality_vs_target': '+2%',
                'cycle_time_vs_target': '-0.5 days'
            }
        }
        
        return metrics
    
    async def generate_final_report(self):
        """Generate final demo report"""
        print("\n" + "="*60)
        print("📊 GENERATING FINAL REPORT")
        print("="*60)
        
        report = f"""# Product Development Demo - Final Report

## Demo Execution Summary
- **Start Time**: {self.start_time}
- **End Time**: {self.end_time}
- **Duration**: {(self.end_time - self.start_time).total_seconds() / 60:.1f} minutes

## Artifacts Generated
- ✅ Product Requirements Document (PRD)
- ✅ System Architecture Document
- ✅ Sprint Backlog
- ✅ {len(self.artifacts.get('implementations', {}))} User Story Implementations
- ✅ Test Results
- ✅ Sprint Review Report
- ✅ Retrospective Report
- ✅ Metrics Analysis

## Key Metrics
- **Sprint Velocity**: {self.artifacts.get('metrics', {}).get('velocity', 0)} story points
- **Quality Score**: {self.artifacts.get('metrics', {}).get('quality', 0)}%
- **Test Pass Rate**: {self.artifacts.get('metrics', {}).get('test_pass_rate', 0)}%
- **Team Satisfaction**: {self.artifacts.get('retrospective', {}).get('satisfaction', 0)}/5.0

## Demo Success Criteria
- ✅ All phases completed successfully
- ✅ Team collaboration demonstrated
- ✅ Quality gates passed
- ✅ Agile ceremonies executed
- ✅ Metrics tracked and analyzed

## Lessons Learned
1. AI agents can effectively collaborate in agile teams
2. Automated quality gates ensure consistent standards
3. Real-time metrics provide valuable insights
4. Retrospectives drive continuous improvement

## Next Steps
1. Review generated artifacts in /outputs directory
2. Analyze metrics for improvement opportunities
3. Customize scenario for your specific needs
4. Deploy in production environment

---
Demo completed successfully! 🎉
"""
        
        # Save final report
        report_path = self.outputs_dir / "final_report.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Final report saved to {report_path}")
        print("\n" + "="*60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        # Print summary
        print("\n📁 Generated Artifacts:")
        for file in sorted(self.outputs_dir.glob("**/*")):
            if file.is_file():
                print(f"   - {file.relative_to(self.outputs_dir)}")
        
        print(f"\n📊 Key Metrics:")
        print(f"   - Velocity: {self.artifacts.get('metrics', {}).get('velocity', 0)} points")
        print(f"   - Quality: {self.artifacts.get('metrics', {}).get('quality', 0)}%")
        print(f"   - Completion: 100%")
        
        if self.interactive:
            print("\n💡 To explore the results:")
            print("   1. Check the outputs/ directory for all artifacts")
            print("   2. Review the final_report.md for summary")
            print("   3. Analyze metrics.json for detailed data")
            print("\nThank you for running the Product Development Demo!")
    
    async def run(self):
        """Run the complete demo"""
        self.start_time = datetime.now()
        
        try:
            # Setup
            await self.setup()
            
            # Run phases
            await self.run_phase_1_product_definition()
            await self.run_phase_2_sprint_planning()
            await self.run_phase_3_development_sprint()
            await self.run_phase_4_review_retrospective()
            
            # Generate report
            self.end_time = datetime.now()
            await self.generate_final_report()
            
        except Exception as e:
            print(f"\n❌ Error during demo execution: {e}")
            raise
        finally:
            # Cleanup
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
            if self.safety_monitor:
                await self.safety_monitor.stop_monitoring()
    
    async def cleanup(self):
        """Cleanup demo resources"""
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        if self.safety_monitor:
            await self.safety_monitor.stop_monitoring()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Product Development Demo')
    parser.add_argument(
        '--config',
        default='scenario.yaml',
        help='Path to scenario configuration file'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode with pauses and explanations'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Run demo
    demo = ProductDevelopmentDemo(
        config_path=args.config,
        interactive=args.interactive
    )
    
    try:
        asyncio.run(demo.run())
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
        asyncio.run(demo.cleanup())
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()