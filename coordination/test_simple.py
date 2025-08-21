#!/usr/bin/env python3
"""
Simple test to verify document manager and handoff protocol work
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from document_manager import (
    DocumentRegistry, DocumentType, DocumentStatus, AccessLevel
)
from handoff_protocol import (
    HandoffProtocol, HandoffPriority, HandoffStatus
)


async def test_document_manager():
    """Test basic document manager functionality"""
    print("Testing Document Manager...")
    
    # Create registry
    registry = DocumentRegistry(storage_path="./test_storage/documents")
    
    # Create a document
    doc = await registry.create_document(
        content="Test content",
        title="Test Document",
        doc_type=DocumentType.PRD,
        created_by="agent1",
        workflow_id="workflow1",
        team_id="team1"
    )
    
    print(f"✓ Created document: {doc.metadata.id}")
    assert doc.metadata.title == "Test Document"
    assert doc.metadata.type == DocumentType.PRD
    assert doc.content == "Test content"
    
    # Get document
    retrieved = await registry.get_document(doc.metadata.id)
    assert retrieved is not None
    assert retrieved.metadata.id == doc.metadata.id
    print(f"✓ Retrieved document: {retrieved.metadata.title}")
    
    # Update document
    updated = await registry.update_document(
        doc_id=doc.metadata.id,
        content="Updated content",
        modified_by="agent2",
        create_version=True
    )
    assert updated is not None
    assert updated.metadata.version == 2
    assert updated.content == "Updated content"
    print(f"✓ Updated document to version {updated.metadata.version}")
    
    # Search documents
    results = await registry.search_documents(doc_type=DocumentType.PRD)
    assert len(results) >= 1
    print(f"✓ Found {len(results)} PRD documents")
    
    # Check access
    has_access = await registry.check_access(
        doc.metadata.id,
        "agent1",
        AccessLevel.ADMIN
    )
    assert has_access is True
    print("✓ Access control working")
    
    # Get statistics
    stats = await registry.get_statistics()
    print(f"✓ Statistics: {stats['total_documents']} total documents")
    
    print("Document Manager tests passed!\n")
    return registry, doc


async def test_handoff_protocol(registry, doc):
    """Test basic handoff protocol functionality"""
    print("Testing Handoff Protocol...")
    
    # Create protocol - it will use the same document registry singleton
    protocol = HandoffProtocol(storage_path="./test_storage/handoffs")
    # Set the document registry to use the same instance
    protocol.document_registry = registry
    
    # Create handoff
    handoff = await protocol.create_handoff(
        document_id=doc.metadata.id,
        from_agent="agent1",
        to_agent="agent2",
        reason="Please review this PRD",
        instructions="Check for completeness",
        expected_action="review",
        priority=HandoffPriority.HIGH,
        workflow_id="workflow1"
    )
    
    print(f"✓ Created handoff: {handoff.id}")
    assert handoff.document_id == doc.metadata.id
    assert handoff.from_agent == "agent1"
    assert handoff.to_agent == "agent2"
    assert handoff.priority == HandoffPriority.HIGH
    
    # Get agent queue
    queue = await protocol.get_agent_queue("agent2")
    assert len(queue) >= 1
    print(f"✓ Agent2 has {len(queue)} handoffs in queue")
    
    # Accept handoff
    accepted = await protocol.accept_handoff(
        handoff.id,
        "agent2",
        "I'll review this now"
    )
    assert accepted is True
    print("✓ Handoff accepted")
    
    # Complete handoff
    completed = await protocol.complete_handoff(
        handoff.id,
        "agent2"
    )
    assert completed is True
    print("✓ Handoff completed")
    
    # Get statistics
    stats = await protocol.get_statistics()
    print(f"✓ Statistics: {stats['completed_handoffs']} completed handoffs")
    
    print("Handoff Protocol tests passed!\n")


async def test_integration():
    """Test integration between document manager and handoff protocol"""
    print("Testing Integration...")
    
    # Test document creation and handoff
    registry, doc = await test_document_manager()
    await test_handoff_protocol(registry, doc)
    
    print("All tests passed successfully! ✓")


def cleanup():
    """Clean up test storage"""
    import shutil
    test_dir = Path("./test_storage")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("Cleaned up test storage")


if __name__ == "__main__":
    try:
        # Run tests
        asyncio.run(test_integration())
    finally:
        # Clean up
        cleanup()
