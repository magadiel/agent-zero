"""
Autonomy Module for Agent-Zero

This module provides advanced capabilities for self-organizing AI teams,
including performance self-assessment, reorganization proposals, voting
mechanisms, and autonomous change execution.
"""

from .self_organization import (
    SelfOrganizingTeam,
    ReorganizationProposal,
    PerformanceAssessment,
    VotingResult
)

from .team_evolution import (
    TeamEvolutionManager,
    EvolutionStrategy,
    TeamMemberReallocation,
    SkillBasedReorganization
)

__all__ = [
    'SelfOrganizingTeam',
    'ReorganizationProposal',
    'PerformanceAssessment',
    'VotingResult',
    'TeamEvolutionManager',
    'EvolutionStrategy',
    'TeamMemberReallocation',
    'SkillBasedReorganization'
]

__version__ = '1.0.0'