"""
End-to-End Testing Suite for Agile AI Company Framework

This module contains comprehensive end-to-end tests for the multi-agent
AI company implementation built on Agent-Zero.
"""

from .workflow_tests import TestWorkflowE2E, TestWorkflowIntegration
from .team_tests import TestTeamFormation, TestTeamCommunication, TestTeamPerformance, TestCrossTeamCollaboration

__all__ = [
    'TestWorkflowE2E',
    'TestWorkflowIntegration', 
    'TestTeamFormation',
    'TestTeamCommunication',
    'TestTeamPerformance',
    'TestCrossTeamCollaboration'
]


def test_suite():
    """Create and return the complete test suite"""
    import unittest
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add workflow tests
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowIntegration))
    
    # Add team tests
    suite.addTests(loader.loadTestsFromTestCase(TestTeamFormation))
    suite.addTests(loader.loadTestsFromTestCase(TestTeamCommunication))
    suite.addTests(loader.loadTestsFromTestCase(TestTeamPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestCrossTeamCollaboration))
    
    return suite