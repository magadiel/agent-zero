"""
Test suite for Emergent Behavior Management System

This script tests the integration of EmergenceMonitor and BehaviorClassifier
to ensure all acceptance criteria are met.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import the modules
from emergence_monitor import (
    EmergenceMonitor, BehaviorEvent, BehaviorPattern,
    MetricType, PatternDetection
)
from behavior_classifier import (
    BehaviorClassifier, BehaviorCategory, InterventionType,
    process_detected_patterns
)


class EmergenceTester:
    """Test harness for emergent behavior management"""
    
    def __init__(self):
        self.monitor = EmergenceMonitor()
        self.classifier = BehaviorClassifier()
        self.test_results = {
            "pattern_detection": False,
            "behavior_classification": False,
            "positive_guidance": False,
            "negative_suppression": False,
            "all_criteria_met": False
        }
        
    async def run_all_tests(self):
        """Run all acceptance criteria tests"""
        print("=" * 60)
        print("EMERGENT BEHAVIOR MANAGEMENT SYSTEM TEST")
        print("=" * 60)
        
        # Start systems
        monitor_task = asyncio.create_task(self.monitor.start_monitoring())
        classifier_task = asyncio.create_task(self.classifier.start_classification())
        
        # Give systems time to initialize
        await asyncio.sleep(1)
        
        # Run tests
        print("\n1. Testing Pattern Detection...")
        await self.test_pattern_detection()
        
        print("\n2. Testing Behavior Classification...")
        await self.test_behavior_classification()
        
        print("\n3. Testing Positive Behavior Guidance...")
        await self.test_positive_guidance()
        
        print("\n4. Testing Negative Pattern Suppression...")
        await self.test_negative_suppression()
        
        # Stop systems
        await self.monitor.stop_monitoring()
        await self.classifier.stop_classification()
        monitor_task.cancel()
        classifier_task.cancel()
        
        # Check if all criteria are met
        self.test_results["all_criteria_met"] = all(
            self.test_results[k] for k in self.test_results if k != "all_criteria_met"
        )
        
        # Print results
        self.print_test_results()
        
        return self.test_results["all_criteria_met"]
        
    async def test_pattern_detection(self):
        """Test Acceptance Criteria 1: Detect behavior patterns"""
        print("  - Generating behavior events...")
        
        # Generate collaboration increase pattern
        agents = ["agent_1", "agent_2", "agent_3"]
        for _ in range(50):
            event = BehaviorEvent(
                agent_id=random.choice(agents),
                team_id="team_alpha",
                event_type="collaboration",
                event_data={
                    "receiver": random.choice(agents),
                    "collaboration_score": 0.8 + random.random() * 0.2
                }
            )
            self.monitor.record_event(event)
            
        # Generate resource optimization pattern
        for _ in range(30):
            event = BehaviorEvent(
                agent_id=random.choice(agents),
                team_id="team_alpha",
                event_type="resource_usage",
                event_data={
                    "utilization": 0.3 + random.random() * 0.2  # Low utilization
                }
            )
            self.monitor.record_event(event)
            
        # Wait for pattern detection
        await asyncio.sleep(12)
        
        # Check if patterns were detected
        patterns_detected = len(self.monitor.detected_patterns) > 0
        
        if patterns_detected:
            print(f"  ✓ Detected {len(self.monitor.detected_patterns)} patterns")
            for pattern in self.monitor.detected_patterns:
                print(f"    - {pattern.pattern_type.value} (confidence: {pattern.confidence:.2f})")
            self.test_results["pattern_detection"] = True
        else:
            print("  ✗ No patterns detected")
            
    async def test_behavior_classification(self):
        """Test Acceptance Criteria 2: Classify behaviors"""
        print("  - Classifying detected patterns...")
        
        classifications_made = []
        
        # Convert patterns to behavior data and classify
        for pattern in self.monitor.detected_patterns:
            behavior_data = {
                "behavior_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type.value,
                "confidence": pattern.confidence,
                "affected_agents": pattern.affected_agents,
                "affected_teams": pattern.affected_teams
            }
            
            classification = self.classifier.classify_behavior(behavior_data)
            classifications_made.append(classification)
            
        if classifications_made:
            print(f"  ✓ Made {len(classifications_made)} classifications")
            
            # Count categories
            categories = {}
            for c in classifications_made:
                cat = c.category.value
                categories[cat] = categories.get(cat, 0) + 1
                
            for cat, count in categories.items():
                print(f"    - {cat}: {count}")
                
            self.test_results["behavior_classification"] = True
        else:
            print("  ✗ No classifications made")
            
    async def test_positive_guidance(self):
        """Test Acceptance Criteria 3: Guide positive emergence"""
        print("  - Testing positive behavior reinforcement...")
        
        # Create a positive behavior
        positive_behavior = {
            "behavior_id": "test_positive",
            "pattern_type": "innovation_burst",
            "confidence": 0.9,
            "affected_agents": ["agent_a", "agent_b"],
            "affected_teams": ["team_innovation"]
        }
        
        # Classify and create intervention
        classification = self.classifier.classify_behavior(positive_behavior)
        intervention = await self.classifier.create_intervention(
            classification, positive_behavior
        )
        
        if intervention and intervention.intervention_type in [
            InterventionType.REINFORCEMENT, InterventionType.REWARD
        ]:
            print(f"  ✓ Created {intervention.intervention_type.value} intervention")
            print(f"    - Target agents: {intervention.target_agents}")
            print(f"    - Parameters: {intervention.parameters}")
            self.test_results["positive_guidance"] = True
        else:
            print("  ✗ Failed to create positive reinforcement")
            
    async def test_negative_suppression(self):
        """Test Acceptance Criteria 4: Suppress negative patterns"""
        print("  - Testing negative behavior suppression...")
        
        # Create negative behaviors with different severities
        negative_behaviors = [
            {
                "behavior_id": "test_negative_1",
                "pattern_type": "resource_competition",
                "confidence": 0.8,
                "affected_agents": ["agent_x", "agent_y"],
                "affected_teams": ["team_conflict"]
            },
            {
                "behavior_id": "test_negative_2",
                "pattern_type": "conflict_pattern",
                "confidence": 0.75,
                "affected_agents": ["agent_m", "agent_n"],
                "affected_teams": ["team_problem"]
            }
        ]
        
        interventions_created = []
        
        for behavior in negative_behaviors:
            classification = self.classifier.classify_behavior(behavior)
            intervention = await self.classifier.create_intervention(
                classification, behavior
            )
            if intervention:
                interventions_created.append(intervention)
                
        if interventions_created:
            print(f"  ✓ Created {len(interventions_created)} suppression interventions")
            for intervention in interventions_created:
                print(f"    - Type: {intervention.intervention_type.value}")
                print(f"      Targets: {intervention.target_agents}")
                print(f"      Duration: {intervention.duration}")
                
            self.test_results["negative_suppression"] = True
        else:
            print("  ✗ Failed to create suppression interventions")
            
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        criteria = [
            ("Pattern Detection", "pattern_detection"),
            ("Behavior Classification", "behavior_classification"),
            ("Positive Guidance", "positive_guidance"),
            ("Negative Suppression", "negative_suppression")
        ]
        
        for name, key in criteria:
            status = "✓ PASS" if self.test_results[key] else "✗ FAIL"
            print(f"{name:.<40} {status}")
            
        print("-" * 60)
        overall = "✓ ALL TESTS PASSED" if self.test_results["all_criteria_met"] else "✗ TESTS FAILED"
        print(f"Overall Result: {overall}")
        
        # Print system statistics
        print("\n" + "=" * 60)
        print("SYSTEM STATISTICS")
        print("=" * 60)
        
        # Monitor statistics
        monitor_summary = self.monitor.get_summary()
        print("\nEmergence Monitor:")
        print(f"  - Total events: {monitor_summary['total_events']}")
        print(f"  - Patterns detected: {monitor_summary['detected_patterns']}")
        print(f"  - Active patterns: {monitor_summary['active_patterns']}")
        print(f"  - Anomalies detected: {monitor_summary['detected_anomalies']}")
        print(f"  - Emergent behaviors: {monitor_summary['emergent_behaviors']}")
        
        # Classifier statistics
        classifier_stats = self.classifier.get_intervention_statistics()
        print("\nBehavior Classifier:")
        print(f"  - Classifications made: {sum(classifier_stats['classification_distribution'].values())}")
        print(f"  - Active interventions: {classifier_stats['active_interventions']}")
        print(f"  - Completed interventions: {classifier_stats['completed_interventions']}")
        
        print("\nClassification Distribution:")
        for category, count in classifier_stats['classification_distribution'].items():
            if count > 0:
                print(f"    - {category}: {count}")
                
        if classifier_stats['intervention_types']:
            print("\nIntervention Types Used:")
            for itype, count in classifier_stats['intervention_types'].items():
                print(f"    - {itype}: {count}")


async def integration_test():
    """Full integration test of emergence monitor and behavior classifier"""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: EMERGENT BEHAVIOR MANAGEMENT")
    print("=" * 60)
    
    # Initialize systems
    monitor = EmergenceMonitor(window_size=500, anomaly_threshold=2.5)
    classifier = BehaviorClassifier()
    
    # Start systems
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    classifier_task = asyncio.create_task(classifier.start_classification())
    
    print("\n1. Simulating complex team behaviors...")
    
    # Simulate a complex scenario
    agents = [f"agent_{i}" for i in range(15)]
    teams = [f"team_{chr(65+i)}" for i in range(4)]
    
    # Phase 1: Normal collaboration
    print("  Phase 1: Normal collaboration")
    for _ in range(100):
        event = BehaviorEvent(
            agent_id=random.choice(agents),
            team_id=random.choice(teams),
            event_type=random.choice(["communication", "collaboration", "task_assignment"]),
            event_data={
                "receiver": random.choice(agents),
                "alignment_score": 0.7 + random.random() * 0.3
            }
        )
        monitor.record_event(event)
        await asyncio.sleep(0.01)
        
    # Phase 2: Emerging conflict
    print("  Phase 2: Emerging conflict")
    conflict_agents = agents[:5]
    for _ in range(50):
        event = BehaviorEvent(
            agent_id=random.choice(conflict_agents),
            team_id=teams[0],
            event_type="decision",
            event_data={
                "alignment_score": random.random() * 0.3,  # Low alignment
                "conflict": True
            }
        )
        monitor.record_event(event)
        await asyncio.sleep(0.01)
        
    # Phase 3: Innovation burst
    print("  Phase 3: Innovation burst")
    innovation_agents = agents[10:]
    for _ in range(30):
        event = BehaviorEvent(
            agent_id=random.choice(innovation_agents),
            team_id=teams[2],
            event_type="innovation",
            event_data={
                "innovation_type": "process_improvement",
                "impact": 0.8 + random.random() * 0.2
            }
        )
        monitor.record_event(event)
        await asyncio.sleep(0.01)
        
    # Wait for processing
    print("\n2. Waiting for pattern detection and classification...")
    await asyncio.sleep(15)
    
    # Process detected patterns
    print("\n3. Processing detected patterns...")
    patterns_for_classification = []
    for pattern in monitor.detected_patterns:
        pattern_data = {
            "pattern_id": pattern.pattern_id,
            "pattern_type": pattern.pattern_type.value,
            "confidence": pattern.confidence,
            "affected_agents": pattern.affected_agents,
            "affected_teams": pattern.affected_teams,
            "evidence": pattern.evidence
        }
        patterns_for_classification.append(pattern_data)
        
    await process_detected_patterns(classifier, patterns_for_classification)
    
    # Wait for interventions
    await asyncio.sleep(5)
    
    # Print results
    print("\n4. Integration Test Results:")
    print("-" * 60)
    
    monitor_summary = monitor.get_summary()
    print(f"Patterns Detected: {monitor_summary['detected_patterns']}")
    print(f"Anomalies Detected: {monitor_summary['detected_anomalies']}")
    print(f"Emergent Behaviors: {monitor_summary['emergent_behaviors']}")
    
    classifier_stats = classifier.get_intervention_statistics()
    print(f"Classifications Made: {sum(classifier_stats['classification_distribution'].values())}")
    print(f"Interventions Created: {classifier_stats['completed_interventions'] + classifier_stats['active_interventions']}")
    
    # Get recommendations
    recommendations = classifier.get_recommendations()
    if recommendations:
        print("\n5. System Recommendations:")
        for rec in recommendations:
            print(f"  - {rec['recommendation']}")
            
    # Stop systems
    await monitor.stop_monitoring()
    await classifier.stop_classification()
    monitor_task.cancel()
    classifier_task.cancel()
    
    # Export data
    print("\n6. Exporting data for analysis...")
    
    monitor_data = monitor.export_data()
    with open("integration_monitor_data.json", "w") as f:
        json.dump(monitor_data, f, indent=2, default=str)
        
    classifier_data = classifier.export_data()
    with open("integration_classifier_data.json", "w") as f:
        json.dump(classifier_data, f, indent=2, default=str)
        
    print("  ✓ Data exported to JSON files")
    
    return monitor, classifier


async def main():
    """Main test execution"""
    # Run acceptance criteria tests
    print("\n" + "=" * 80)
    print("TASK-702: EMERGENT BEHAVIOR MANAGEMENT - ACCEPTANCE TESTS")
    print("=" * 80)
    
    tester = EmergenceTester()
    all_passed = await tester.run_all_tests()
    
    # Run integration test
    print("\n\n")
    await integration_test()
    
    # Final result
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ TASK-702 ACCEPTANCE CRITERIA: ALL MET")
        print("  - ✓ Detect behavior patterns")
        print("  - ✓ Classify behaviors")
        print("  - ✓ Guide positive emergence")
        print("  - ✓ Suppress negative patterns")
    else:
        print("✗ TASK-702 ACCEPTANCE CRITERIA: NOT ALL MET")
        
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    # Run all tests
    result = asyncio.run(main())
    
    # Exit with appropriate code
    exit(0 if result else 1)