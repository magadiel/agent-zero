"""
Self-Organization System for Autonomous AI Teams

This module implements the core self-organization capabilities that allow teams
to autonomously assess their performance, propose reorganizations, vote on changes,
and execute approved modifications to their structure.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from uuid import uuid4
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReorganizationType(Enum):
    """Types of reorganization that can be proposed"""
    MEMBER_SWAP = "member_swap"          # Swap members between teams
    ROLE_CHANGE = "role_change"          # Change member roles
    TEAM_MERGE = "team_merge"            # Merge two teams
    TEAM_SPLIT = "team_split"            # Split a team
    SIZE_ADJUSTMENT = "size_adjustment"   # Add/remove members
    SKILL_REBALANCE = "skill_rebalance"  # Rebalance skills
    LEADERSHIP_CHANGE = "leadership_change"  # Change team leader
    STRUCTURE_CHANGE = "structure_change"    # Change team structure


class VoteType(Enum):
    """Types of votes that can be cast"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    VETO = "veto"  # Leader/critical member can veto


class PerformanceMetric(Enum):
    """Performance metrics for assessment"""
    VELOCITY = "velocity"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"
    INNOVATION = "innovation"
    RELIABILITY = "reliability"
    ADAPTABILITY = "adaptability"
    COMMUNICATION = "communication"


@dataclass
class TeamMember:
    """Represents a team member"""
    id: str
    name: str
    role: str
    skills: List[str]
    performance_history: List[float] = field(default_factory=list)
    current_workload: float = 0.0
    voting_weight: float = 1.0  # Can be adjusted based on seniority/expertise
    can_veto: bool = False  # Leaders or critical members can veto
    
    def get_average_performance(self) -> float:
        """Calculate average performance score"""
        if not self.performance_history:
            return 0.5  # Default neutral score
        return statistics.mean(self.performance_history[-10:])  # Last 10 assessments


@dataclass
class PerformanceAssessment:
    """Results of a team performance self-assessment"""
    team_id: str
    timestamp: datetime
    metrics: Dict[PerformanceMetric, float]
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    member_assessments: Dict[str, float]  # Individual member scores
    
    def needs_reorganization(self, threshold: float = 0.6) -> bool:
        """Determine if reorganization is needed"""
        return self.overall_score < threshold
    
    def get_critical_issues(self) -> List[str]:
        """Identify critical performance issues"""
        issues = []
        for metric, score in self.metrics.items():
            if score < 0.4:  # Critical threshold
                issues.append(f"Critical {metric.value} issue (score: {score:.2f})")
        return issues


@dataclass
class ReorganizationProposal:
    """A proposal for team reorganization"""
    id: str
    team_id: str
    proposed_by: str
    timestamp: datetime
    reorganization_type: ReorganizationType
    description: str
    rationale: str
    expected_benefits: List[str]
    potential_risks: List[str]
    changes: Dict[str, Any]  # Specific changes to implement
    urgency: str  # "low", "medium", "high", "critical"
    votes: Dict[str, VoteType] = field(default_factory=dict)
    status: str = "pending"  # pending, approved, rejected, executed
    
    def add_vote(self, member_id: str, vote: VoteType):
        """Add a vote to the proposal"""
        self.votes[member_id] = vote
    
    def has_veto(self) -> bool:
        """Check if proposal has been vetoed"""
        return VoteType.VETO in self.votes.values()


@dataclass
class VotingResult:
    """Result of a voting process"""
    proposal_id: str
    total_votes: int
    approve_votes: int
    reject_votes: int
    abstain_votes: int
    veto_votes: int
    weighted_approval: float  # Considering voting weights
    passed: bool
    veto_used: bool
    summary: str


class SelfOrganizingTeam:
    """
    A team capable of self-organization through performance assessment,
    proposal generation, voting, and change execution.
    """
    
    def __init__(self, team_id: str, name: str, members: List[TeamMember]):
        self.team_id = team_id
        self.name = name
        self.members = {m.id: m for m in members}
        self.performance_history: List[PerformanceAssessment] = []
        self.proposals: Dict[str, ReorganizationProposal] = {}
        self.executed_changes: List[ReorganizationProposal] = []
        self.performance_threshold = 0.7  # Trigger reorganization below this
        self.approval_threshold = 0.66  # 2/3 majority for approval
        self.min_votes_required = 0.75  # 75% participation required
        
        # Team configuration
        self.max_size = 12
        self.min_size = 3
        self.ideal_size = 7
        
        # Performance weights for different metrics
        self.metric_weights = {
            PerformanceMetric.VELOCITY: 0.2,
            PerformanceMetric.QUALITY: 0.2,
            PerformanceMetric.EFFICIENCY: 0.15,
            PerformanceMetric.COLLABORATION: 0.15,
            PerformanceMetric.INNOVATION: 0.1,
            PerformanceMetric.RELIABILITY: 0.1,
            PerformanceMetric.ADAPTABILITY: 0.05,
            PerformanceMetric.COMMUNICATION: 0.05
        }
    
    async def assess_performance(self) -> PerformanceAssessment:
        """
        Perform comprehensive self-assessment of team performance.
        This simulates various performance metrics evaluation.
        """
        logger.info(f"Team {self.name} performing self-assessment...")
        
        # Simulate metric evaluation (in real implementation, these would be calculated)
        metrics = {}
        for metric in PerformanceMetric:
            # Simulate score based on team members' performance
            member_scores = [m.get_average_performance() for m in self.members.values()]
            base_score = statistics.mean(member_scores) if member_scores else 0.5
            
            # Add some variation based on metric type
            if metric == PerformanceMetric.VELOCITY:
                score = base_score * (0.9 + 0.2 * (self.ideal_size / len(self.members)))
            elif metric == PerformanceMetric.COLLABORATION:
                score = base_score * (1.1 if len(self.members) <= self.ideal_size else 0.9)
            else:
                score = base_score * (0.8 + 0.4 * statistics.random())  # Add variation
            
            metrics[metric] = min(1.0, max(0.0, score))
        
        # Calculate overall score using weights
        overall_score = sum(
            metrics[m] * self.metric_weights[m] 
            for m in metrics
        )
        
        # Assess individual members
        member_assessments = {
            m_id: m.get_average_performance() 
            for m_id, m in self.members.items()
        }
        
        # Identify strengths and weaknesses
        strengths = [
            f"Strong {m.value}" 
            for m, score in metrics.items() 
            if score > 0.8
        ]
        
        weaknesses = [
            f"Weak {m.value}" 
            for m, score in metrics.items() 
            if score < 0.5
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, member_assessments)
        
        assessment = PerformanceAssessment(
            team_id=self.team_id,
            timestamp=datetime.now(),
            metrics=metrics,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            member_assessments=member_assessments
        )
        
        self.performance_history.append(assessment)
        logger.info(f"Assessment complete. Overall score: {overall_score:.2f}")
        
        return assessment
    
    def _generate_recommendations(self, 
                                 metrics: Dict[PerformanceMetric, float],
                                 member_assessments: Dict[str, float]) -> List[str]:
        """Generate recommendations based on assessment"""
        recommendations = []
        
        # Check team size
        if len(self.members) > self.ideal_size + 2:
            recommendations.append("Consider splitting team - size exceeds ideal")
        elif len(self.members) < self.min_size + 1:
            recommendations.append("Consider merging with another team - size too small")
        
        # Check for underperforming members
        low_performers = [
            m_id for m_id, score in member_assessments.items() 
            if score < 0.4
        ]
        if low_performers:
            recommendations.append(f"Address performance issues with {len(low_performers)} members")
        
        # Check metrics
        if metrics.get(PerformanceMetric.COLLABORATION, 1.0) < 0.5:
            recommendations.append("Improve team collaboration through pair work or mob sessions")
        
        if metrics.get(PerformanceMetric.VELOCITY, 1.0) < 0.5:
            recommendations.append("Review and optimize team processes for better velocity")
        
        if metrics.get(PerformanceMetric.QUALITY, 1.0) < 0.5:
            recommendations.append("Implement additional quality checks and reviews")
        
        return recommendations
    
    async def generate_reorganization_proposal(self, 
                                              assessment: PerformanceAssessment) -> Optional[ReorganizationProposal]:
        """
        Generate a reorganization proposal based on performance assessment.
        Returns None if no reorganization is needed.
        """
        if not assessment.needs_reorganization(self.performance_threshold):
            logger.info(f"Team {self.name} performance acceptable, no reorganization needed")
            return None
        
        logger.info(f"Team {self.name} generating reorganization proposal...")
        
        # Determine reorganization type based on issues
        reorg_type, changes = self._determine_reorganization_strategy(assessment)
        
        # Create proposal
        proposal = ReorganizationProposal(
            id=str(uuid4()),
            team_id=self.team_id,
            proposed_by="self_assessment_system",
            timestamp=datetime.now(),
            reorganization_type=reorg_type,
            description=f"Reorganization to address performance issues (score: {assessment.overall_score:.2f})",
            rationale=f"Performance below threshold. Issues: {', '.join(assessment.get_critical_issues())}",
            expected_benefits=self._calculate_expected_benefits(reorg_type, assessment),
            potential_risks=self._identify_potential_risks(reorg_type),
            changes=changes,
            urgency=self._determine_urgency(assessment.overall_score)
        )
        
        self.proposals[proposal.id] = proposal
        logger.info(f"Generated proposal {proposal.id} of type {reorg_type.value}")
        
        return proposal
    
    def _determine_reorganization_strategy(self, 
                                          assessment: PerformanceAssessment) -> Tuple[ReorganizationType, Dict]:
        """Determine the best reorganization strategy"""
        changes = {}
        
        # Check for size issues
        if len(self.members) > self.ideal_size + 2:
            return ReorganizationType.TEAM_SPLIT, {
                "split_size": self.ideal_size,
                "criteria": "performance_based"
            }
        
        if len(self.members) < self.min_size + 1:
            return ReorganizationType.SIZE_ADJUSTMENT, {
                "action": "add_members",
                "target_size": self.ideal_size
            }
        
        # Check for collaboration issues
        if assessment.metrics.get(PerformanceMetric.COLLABORATION, 1.0) < 0.4:
            # Find members with poor collaboration
            low_collaborators = [
                m_id for m_id, score in assessment.member_assessments.items()
                if score < 0.4
            ]
            if low_collaborators:
                return ReorganizationType.MEMBER_SWAP, {
                    "swap_members": low_collaborators[:2] if len(low_collaborators) > 1 else low_collaborators
                }
        
        # Check for skill imbalance
        skill_coverage = self._analyze_skill_coverage()
        if skill_coverage < 0.6:
            return ReorganizationType.SKILL_REBALANCE, {
                "needed_skills": self._identify_missing_skills(),
                "redundant_skills": self._identify_redundant_skills()
            }
        
        # Default to role change if no specific issue
        return ReorganizationType.ROLE_CHANGE, {
            "proposed_changes": self._propose_role_changes(assessment)
        }
    
    def _analyze_skill_coverage(self) -> float:
        """Analyze how well team skills are distributed"""
        all_skills = set()
        for member in self.members.values():
            all_skills.update(member.skills)
        
        if not all_skills:
            return 0.0
        
        # Count how many members have each skill
        skill_counts = {skill: 0 for skill in all_skills}
        for member in self.members.values():
            for skill in member.skills:
                skill_counts[skill] += 1
        
        # Good coverage means 2-3 members per skill
        ideal_coverage = sum(
            1 for count in skill_counts.values() 
            if 2 <= count <= 3
        )
        
        return ideal_coverage / len(all_skills) if all_skills else 0.0
    
    def _identify_missing_skills(self) -> List[str]:
        """Identify skills that are missing or underrepresented"""
        # In real implementation, this would check against required skills
        return ["testing", "documentation", "deployment"]  # Simulated
    
    def _identify_redundant_skills(self) -> List[str]:
        """Identify skills that are overrepresented"""
        skill_counts = {}
        for member in self.members.values():
            for skill in member.skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        return [
            skill for skill, count in skill_counts.items() 
            if count > len(self.members) * 0.6
        ]
    
    def _propose_role_changes(self, assessment: PerformanceAssessment) -> Dict[str, str]:
        """Propose role changes based on performance"""
        changes = {}
        
        # Find best and worst performers
        sorted_members = sorted(
            assessment.member_assessments.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        if sorted_members:
            # Promote best performer
            best_id = sorted_members[0][0]
            if self.members[best_id].role != "leader":
                changes[best_id] = "leader"
            
            # Reassign worst performer if significantly underperforming
            if len(sorted_members) > 1:
                worst_id = sorted_members[-1][0]
                if sorted_members[-1][1] < 0.3:
                    changes[worst_id] = "trainee"
        
        return changes
    
    def _calculate_expected_benefits(self, 
                                    reorg_type: ReorganizationType,
                                    assessment: PerformanceAssessment) -> List[str]:
        """Calculate expected benefits of reorganization"""
        benefits = []
        
        if reorg_type == ReorganizationType.TEAM_SPLIT:
            benefits.append("Improved communication with smaller team size")
            benefits.append("Faster decision making")
            benefits.append("Better focus on specific objectives")
        
        elif reorg_type == ReorganizationType.SKILL_REBALANCE:
            benefits.append("Better skill coverage across team")
            benefits.append("Reduced bottlenecks")
            benefits.append("Improved knowledge sharing")
        
        elif reorg_type == ReorganizationType.MEMBER_SWAP:
            benefits.append("Fresh perspectives from new members")
            benefits.append("Better team dynamics")
            benefits.append("Improved collaboration")
        
        elif reorg_type == ReorganizationType.ROLE_CHANGE:
            benefits.append("Better alignment of roles with skills")
            benefits.append("Improved motivation")
            benefits.append("Career development opportunities")
        
        # Add performance improvement estimate
        expected_improvement = (1.0 - assessment.overall_score) * 0.5  # Conservative estimate
        benefits.append(f"Expected performance improvement: {expected_improvement:.1%}")
        
        return benefits
    
    def _identify_potential_risks(self, reorg_type: ReorganizationType) -> List[str]:
        """Identify potential risks of reorganization"""
        risks = []
        
        if reorg_type in [ReorganizationType.TEAM_SPLIT, ReorganizationType.TEAM_MERGE]:
            risks.append("Temporary productivity decrease during transition")
            risks.append("Loss of team cohesion")
            risks.append("Communication overhead during reorganization")
        
        if reorg_type == ReorganizationType.MEMBER_SWAP:
            risks.append("Knowledge transfer challenges")
            risks.append("Team dynamics disruption")
            risks.append("Onboarding overhead")
        
        if reorg_type == ReorganizationType.LEADERSHIP_CHANGE:
            risks.append("Resistance to new leadership")
            risks.append("Strategic direction changes")
            risks.append("Morale impact")
        
        risks.append("Implementation complexity")
        risks.append("Temporary performance dip")
        
        return risks
    
    def _determine_urgency(self, overall_score: float) -> str:
        """Determine urgency based on performance score"""
        if overall_score < 0.3:
            return "critical"
        elif overall_score < 0.5:
            return "high"
        elif overall_score < 0.6:
            return "medium"
        else:
            return "low"
    
    async def vote_on_proposal(self, 
                              proposal_id: str,
                              voting_period: timedelta = timedelta(hours=24)) -> VotingResult:
        """
        Conduct voting on a reorganization proposal.
        Simulates async voting by team members.
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        logger.info(f"Starting voting on proposal {proposal_id}")
        
        # Simulate voting by each member
        for member_id, member in self.members.items():
            vote = await self._simulate_member_vote(member, proposal)
            proposal.add_vote(member_id, vote)
            
            # Check for veto
            if vote == VoteType.VETO and member.can_veto:
                logger.warning(f"Proposal {proposal_id} vetoed by {member.name}")
                break
        
        # Calculate results
        result = self._calculate_voting_result(proposal)
        
        # Update proposal status
        if result.veto_used:
            proposal.status = "rejected"
        elif result.passed:
            proposal.status = "approved"
        else:
            proposal.status = "rejected"
        
        logger.info(f"Voting complete. Result: {proposal.status}")
        
        return result
    
    async def _simulate_member_vote(self, 
                                   member: TeamMember,
                                   proposal: ReorganizationProposal) -> VoteType:
        """Simulate how a member would vote (in real implementation, this would be actual voting)"""
        await asyncio.sleep(0.1)  # Simulate thinking time
        
        # Factors affecting vote
        performance = member.get_average_performance()
        affects_member = member.id in str(proposal.changes)
        
        # High performers tend to be conservative
        if performance > 0.8:
            if affects_member:
                return VoteType.REJECT if member.can_veto else VoteType.ABSTAIN
            else:
                return VoteType.ABSTAIN
        
        # Low performers more open to change
        if performance < 0.5:
            return VoteType.APPROVE
        
        # Urgent proposals get more approvals
        if proposal.urgency in ["critical", "high"]:
            return VoteType.APPROVE
        
        # Default based on expected benefits vs risks
        if len(proposal.expected_benefits) > len(proposal.potential_risks):
            return VoteType.APPROVE
        else:
            return VoteType.ABSTAIN
    
    def _calculate_voting_result(self, proposal: ReorganizationProposal) -> VotingResult:
        """Calculate the voting result"""
        total_votes = len(proposal.votes)
        approve_votes = sum(1 for v in proposal.votes.values() if v == VoteType.APPROVE)
        reject_votes = sum(1 for v in proposal.votes.values() if v == VoteType.REJECT)
        abstain_votes = sum(1 for v in proposal.votes.values() if v == VoteType.ABSTAIN)
        veto_votes = sum(1 for v in proposal.votes.values() if v == VoteType.VETO)
        
        # Calculate weighted approval
        weighted_approval = 0.0
        total_weight = 0.0
        for member_id, vote in proposal.votes.items():
            member = self.members[member_id]
            if vote == VoteType.APPROVE:
                weighted_approval += member.voting_weight
            total_weight += member.voting_weight
        
        if total_weight > 0:
            weighted_approval = weighted_approval / total_weight
        
        # Check if proposal passes
        veto_used = veto_votes > 0
        participation_rate = total_votes / len(self.members) if self.members else 0
        
        passed = (
            not veto_used and
            participation_rate >= self.min_votes_required and
            weighted_approval >= self.approval_threshold
        )
        
        summary = f"Votes: {approve_votes} approve, {reject_votes} reject, {abstain_votes} abstain"
        if veto_used:
            summary += f", {veto_votes} VETO"
        
        return VotingResult(
            proposal_id=proposal.id,
            total_votes=total_votes,
            approve_votes=approve_votes,
            reject_votes=reject_votes,
            abstain_votes=abstain_votes,
            veto_votes=veto_votes,
            weighted_approval=weighted_approval,
            passed=passed,
            veto_used=veto_used,
            summary=summary
        )
    
    async def execute_reorganization(self, proposal_id: str) -> bool:
        """
        Execute an approved reorganization proposal.
        Returns True if successful.
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != "approved":
            logger.error(f"Cannot execute proposal {proposal_id} - status: {proposal.status}")
            return False
        
        logger.info(f"Executing reorganization proposal {proposal_id}")
        
        try:
            # Execute based on reorganization type
            if proposal.reorganization_type == ReorganizationType.ROLE_CHANGE:
                await self._execute_role_changes(proposal.changes)
            
            elif proposal.reorganization_type == ReorganizationType.MEMBER_SWAP:
                await self._execute_member_swap(proposal.changes)
            
            elif proposal.reorganization_type == ReorganizationType.SIZE_ADJUSTMENT:
                await self._execute_size_adjustment(proposal.changes)
            
            elif proposal.reorganization_type == ReorganizationType.SKILL_REBALANCE:
                await self._execute_skill_rebalance(proposal.changes)
            
            elif proposal.reorganization_type == ReorganizationType.LEADERSHIP_CHANGE:
                await self._execute_leadership_change(proposal.changes)
            
            else:
                logger.warning(f"Reorganization type {proposal.reorganization_type} not implemented")
                return False
            
            # Mark as executed
            proposal.status = "executed"
            self.executed_changes.append(proposal)
            
            logger.info(f"Successfully executed reorganization {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute reorganization: {e}")
            proposal.status = "failed"
            return False
    
    async def _execute_role_changes(self, changes: Dict[str, Any]):
        """Execute role changes"""
        role_changes = changes.get("proposed_changes", {})
        for member_id, new_role in role_changes.items():
            if member_id in self.members:
                old_role = self.members[member_id].role
                self.members[member_id].role = new_role
                
                # Update voting weight based on new role
                if new_role == "leader":
                    self.members[member_id].voting_weight = 2.0
                    self.members[member_id].can_veto = True
                elif new_role == "trainee":
                    self.members[member_id].voting_weight = 0.5
                    self.members[member_id].can_veto = False
                else:
                    self.members[member_id].voting_weight = 1.0
                    self.members[member_id].can_veto = False
                
                logger.info(f"Changed {member_id} role from {old_role} to {new_role}")
    
    async def _execute_member_swap(self, changes: Dict[str, Any]):
        """Execute member swap (simulated)"""
        swap_members = changes.get("swap_members", [])
        for member_id in swap_members:
            if member_id in self.members:
                # In real implementation, this would coordinate with other teams
                logger.info(f"Member {member_id} marked for swap")
                # Reset their performance history
                self.members[member_id].performance_history = []
    
    async def _execute_size_adjustment(self, changes: Dict[str, Any]):
        """Execute team size adjustment"""
        action = changes.get("action")
        target_size = changes.get("target_size", self.ideal_size)
        
        if action == "add_members":
            # In real implementation, request members from pool
            members_needed = target_size - len(self.members)
            logger.info(f"Requesting {members_needed} new members")
        
        elif action == "remove_members":
            # Identify members to remove based on performance
            members_to_remove = len(self.members) - target_size
            sorted_members = sorted(
                self.members.values(),
                key=lambda m: m.get_average_performance()
            )
            for member in sorted_members[:members_to_remove]:
                logger.info(f"Removing member {member.id} from team")
                del self.members[member.id]
    
    async def _execute_skill_rebalance(self, changes: Dict[str, Any]):
        """Execute skill rebalancing"""
        needed_skills = changes.get("needed_skills", [])
        redundant_skills = changes.get("redundant_skills", [])
        
        logger.info(f"Rebalancing skills - Need: {needed_skills}, Redundant: {redundant_skills}")
        
        # In real implementation, this would:
        # 1. Request members with needed skills
        # 2. Offer members with redundant skills to other teams
        # 3. Arrange training for existing members
    
    async def _execute_leadership_change(self, changes: Dict[str, Any]):
        """Execute leadership change"""
        new_leader_id = changes.get("new_leader")
        
        # Remove current leader privileges
        for member in self.members.values():
            if member.role == "leader":
                member.role = "member"
                member.voting_weight = 1.0
                member.can_veto = False
        
        # Assign new leader
        if new_leader_id and new_leader_id in self.members:
            self.members[new_leader_id].role = "leader"
            self.members[new_leader_id].voting_weight = 2.0
            self.members[new_leader_id].can_veto = True
            logger.info(f"New leader assigned: {new_leader_id}")
    
    def get_reorganization_history(self) -> List[Dict]:
        """Get history of executed reorganizations"""
        return [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "type": p.reorganization_type.value,
                "description": p.description,
                "status": p.status
            }
            for p in self.executed_changes
        ]
    
    def get_current_status(self) -> Dict:
        """Get current team status"""
        latest_assessment = self.performance_history[-1] if self.performance_history else None
        
        return {
            "team_id": self.team_id,
            "name": self.name,
            "member_count": len(self.members),
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "performance": m.get_average_performance()
                }
                for m in self.members.values()
            ],
            "latest_performance": latest_assessment.overall_score if latest_assessment else None,
            "pending_proposals": len([p for p in self.proposals.values() if p.status == "pending"]),
            "executed_changes": len(self.executed_changes)
        }


# Helper function to create a sample team
def create_sample_team() -> SelfOrganizingTeam:
    """Create a sample team for testing"""
    members = [
        TeamMember(
            id="m1",
            name="Alice",
            role="leader",
            skills=["python", "architecture", "leadership"],
            performance_history=[0.8, 0.85, 0.9],
            voting_weight=2.0,
            can_veto=True
        ),
        TeamMember(
            id="m2",
            name="Bob",
            role="developer",
            skills=["javascript", "react", "testing"],
            performance_history=[0.7, 0.75, 0.7]
        ),
        TeamMember(
            id="m3",
            name="Charlie",
            role="developer",
            skills=["python", "docker", "ci/cd"],
            performance_history=[0.6, 0.65, 0.7]
        ),
        TeamMember(
            id="m4",
            name="Diana",
            role="qa",
            skills=["testing", "automation", "documentation"],
            performance_history=[0.9, 0.85, 0.88]
        ),
        TeamMember(
            id="m5",
            name="Eve",
            role="developer",
            skills=["java", "spring", "microservices"],
            performance_history=[0.4, 0.45, 0.5]
        )
    ]
    
    return SelfOrganizingTeam(
        team_id="team-001",
        name="Alpha Team",
        members=members
    )


async def main():
    """Demonstration of self-organization capabilities"""
    print("=== Self-Organizing Team Demonstration ===\n")
    
    # Create a sample team
    team = create_sample_team()
    print(f"Created team: {team.name} with {len(team.members)} members\n")
    
    # Perform self-assessment
    print("1. Performing self-assessment...")
    assessment = await team.assess_performance()
    print(f"   Overall score: {assessment.overall_score:.2f}")
    print(f"   Strengths: {assessment.strengths}")
    print(f"   Weaknesses: {assessment.weaknesses}")
    print(f"   Recommendations: {assessment.recommendations}\n")
    
    # Generate reorganization proposal if needed
    print("2. Generating reorganization proposal...")
    proposal = await team.generate_reorganization_proposal(assessment)
    
    if proposal:
        print(f"   Proposal ID: {proposal.id}")
        print(f"   Type: {proposal.reorganization_type.value}")
        print(f"   Description: {proposal.description}")
        print(f"   Expected benefits: {proposal.expected_benefits}")
        print(f"   Potential risks: {proposal.potential_risks}\n")
        
        # Vote on proposal
        print("3. Voting on proposal...")
        voting_result = await team.vote_on_proposal(proposal.id)
        print(f"   {voting_result.summary}")
        print(f"   Weighted approval: {voting_result.weighted_approval:.1%}")
        print(f"   Result: {'PASSED' if voting_result.passed else 'REJECTED'}\n")
        
        # Execute if approved
        if voting_result.passed:
            print("4. Executing reorganization...")
            success = await team.execute_reorganization(proposal.id)
            print(f"   Execution: {'Successful' if success else 'Failed'}\n")
    else:
        print("   No reorganization needed\n")
    
    # Show final status
    print("5. Current team status:")
    status = team.get_current_status()
    print(f"   Team: {status['name']}")
    print(f"   Members: {status['member_count']}")
    print(f"   Latest performance: {status['latest_performance']:.2f}" if status['latest_performance'] else "   No performance data")
    print(f"   Executed changes: {status['executed_changes']}")


if __name__ == "__main__":
    # For demonstration purposes
    import random
    random.seed(42)  # For reproducible results
    statistics.random = random.random  # Use seeded random
    
    asyncio.run(main())