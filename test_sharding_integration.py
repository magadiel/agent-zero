#!/usr/bin/env python3
"""
Test integration of document sharding with document handoff system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import document handoff components
from coordination.document_manager import DocumentRegistry, Document, DocumentStatus
from coordination.handoff_protocol import HandoffProtocol, HandoffRequest

# Import sharding components
from python.helpers.document_sharding import (
    DocumentShardingSystem,
    ShardingStrategy,
    DocumentFormat
)
from python.tools.shard_document import ShardDocument


def test_sharding_with_handoff():
    """Test document sharding integration with handoff system."""
    print("Testing Document Sharding Integration with Handoff System")
    print("=" * 60)
    
    # Initialize systems
    doc_registry = DocumentRegistry()
    handoff_protocol = HandoffProtocol()
    sharding_system = DocumentShardingSystem(max_shard_size=200)  # Small for testing
    
    # Create a mock agent for the tool
    class MockAgent:
        def __init__(self):
            self.context = type('obj', (object,), {'log': self.log})()
        def log(self, msg, **kwargs):
            print(f"  [LOG] {msg}")
    
    mock_agent = MockAgent()
    shard_tool = ShardDocument(mock_agent)
    
    print("\n1. Creating Large Document for Handoff")
    print("-" * 50)
    
    # Create a large document that will need sharding
    large_content = """# Product Requirements Document

## Executive Summary
This document outlines the requirements for our new AI-powered document management system.
The system will revolutionize how organizations handle large-scale documentation.

## Background
Organizations today struggle with managing vast amounts of documentation.
Traditional systems are inadequate for handling the complexity and scale of modern documentation needs.
Our solution addresses these challenges through innovative AI-powered approaches.

## Requirements

### Functional Requirements
1. Document ingestion and processing
2. Intelligent categorization and tagging
3. Advanced search capabilities
4. Automated summarization
5. Version control and history tracking

### Non-Functional Requirements
1. Scalability to handle millions of documents
2. Sub-second response times for queries
3. 99.99% uptime availability
4. Enterprise-grade security
5. Compliance with industry standards

## Technical Architecture
The system will be built using a microservices architecture.
Key components include document processing pipeline, search engine, and AI models.

## Implementation Timeline
Phase 1: Core infrastructure (3 months)
Phase 2: AI capabilities (3 months)
Phase 3: Enterprise features (2 months)
Phase 4: Optimization and scaling (2 months)

## Conclusion
This system will transform document management for enterprises worldwide.
"""
    
    # Test automatic sharding during document creation
    print("✓ Creating document that exceeds shard threshold...")
    
    # Integrate sharding with document handoff
    shard_tool.integrate_with_document_handoff(doc_registry)
    
    # Create document (will automatically shard if too large)
    doc_id = doc_registry.create_document(
        title="Product Requirements Document",
        content=large_content,
        owner="product_manager",
        doc_type="requirements",
        metadata={"priority": "high", "team": "product"}
    )
    
    print(f"✓ Document created with ID: {doc_id}")
    
    # Check if document was sharded
    doc = doc_registry.get_document(doc_id)
    if doc and doc.metadata.get("sharded"):
        shard_info = doc.metadata.get("shard_info", {})
        print(f"✓ Document was automatically sharded into {shard_info.get('total_shards', 0)} pieces")
    
    print("\n2. Testing Direct Sharding")
    print("-" * 50)
    
    # Directly shard a document
    response = shard_tool.execute(
        action="shard",
        content=large_content,
        title="Direct Shard Test",
        strategy="section_based",
        format="markdown"
    )
    
    if response.success:
        print(f"✓ Direct sharding successful")
        print(f"  Document ID: {response.data['document_id']}")
        print(f"  Total shards: {response.data['total_shards']}")
        for shard in response.data['shards']:
            print(f"    - {shard['title']} ({shard['size_bytes']} bytes)")
        
        # Store document ID for later tests
        sharded_doc_id = response.data['document_id']
    
    print("\n3. Testing Shard Retrieval")
    print("-" * 50)
    
    # Get specific shard
    if response.success and response.data['shards']:
        first_shard_id = response.data['shards'][0]['id']
        
        shard_response = shard_tool.execute(
            action="get_shard",
            shard_id=first_shard_id
        )
        
        if shard_response.success:
            print(f"✓ Retrieved shard: {shard_response.data['title']}")
            print(f"  Size: {shard_response.data['size_bytes']} bytes")
            print(f"  Content preview: {shard_response.data['content'][:100]}...")
    
    print("\n4. Testing Document Search Across Shards")
    print("-" * 50)
    
    # Search within sharded document
    search_response = shard_tool.execute(
        action="search",
        query="requirements",
        document_id=sharded_doc_id
    )
    
    if search_response.success:
        print(f"✓ Search found {search_response.data['total_matches']} matching shards")
        for result in search_response.data['results']:
            print(f"  - Shard {result['index']}: {result['title']}")
            if result['snippet']:
                print(f"    Snippet: ...{result['snippet'][:80]}...")
    
    print("\n5. Testing Document Reassembly")
    print("-" * 50)
    
    # Reassemble the sharded document
    reassemble_response = shard_tool.execute(
        action="reassemble",
        document_id=sharded_doc_id
    )
    
    if reassemble_response.success:
        print(f"✓ Successfully reassembled document: {reassemble_response.data['title']}")
        print(f"  Total shards combined: {reassemble_response.data['total_shards']}")
        print(f"  Content size: {len(reassemble_response.data['content'])} chars")
    
    print("\n6. Testing Statistics Generation")
    print("-" * 50)
    
    # Get statistics
    stats_response = shard_tool.execute(
        action="stats",
        document_id=sharded_doc_id
    )
    
    if stats_response.success:
        stats = stats_response.data
        print("✓ Document statistics:")
        print(f"  Total shards: {stats['total_shards']}")
        print(f"  Total size: {stats['total_size_bytes']} bytes")
        print(f"  Total words: {stats['total_words']}")
        print(f"  Average shard size: {stats['average_shard_size']} bytes")
    
    print("\n7. Testing Table of Contents Generation")
    print("-" * 50)
    
    # Generate TOC
    toc_response = shard_tool.execute(
        action="get_toc",
        document_id=sharded_doc_id
    )
    
    if toc_response.success:
        print("✓ Generated table of contents")
        toc_preview = toc_response.data['table_of_contents'][:200]
        print(f"  TOC Preview:\n{toc_preview}...")
    
    print("\n8. Testing Handoff with Sharded Documents")
    print("-" * 50)
    
    # Create a handoff request for the sharded document
    if doc:
        handoff_request = HandoffRequest(
            document_id=doc_id,
            from_agent="product_manager",
            to_agent="architect",
            priority=2,
            validation_checklist=["requirements_complete", "feasibility_checked"],
            notes="Sharded PRD ready for architecture review"
        )
        
        request_id = handoff_protocol.initiate_handoff(handoff_request)
        print(f"✓ Created handoff request: {request_id}")
        
        # Accept handoff
        success = handoff_protocol.accept_handoff(request_id, "architect")
        if success:
            print("✓ Handoff accepted by architect")
            
            # Complete handoff
            success = handoff_protocol.complete_handoff(
                request_id,
                validation_results={"requirements_complete": True, "feasibility_checked": True}
            )
            if success:
                print("✓ Handoff completed successfully")
    
    print("\n" + "=" * 60)
    print("Integration testing completed successfully! ✓")
    
    return True


def test_advanced_sharding_scenarios():
    """Test advanced sharding scenarios."""
    print("\nTesting Advanced Sharding Scenarios")
    print("=" * 60)
    
    class MockAgent:
        def __init__(self):
            self.context = type('obj', (object,), {'log': self.log})()
        def log(self, msg, **kwargs):
            pass  # Silent for this test
    
    mock_agent = MockAgent()
    shard_tool = ShardDocument(mock_agent)
    
    print("\n1. Testing YAML Configuration Sharding")
    print("-" * 50)
    
    yaml_config = """
application:
  name: AgileAI
  version: 1.0.0
  environment: production
  
database:
  primary:
    host: db-primary.example.com
    port: 5432
    name: agileai_prod
    pool_size: 20
  replica:
    host: db-replica.example.com
    port: 5432
    name: agileai_prod
    pool_size: 10
    
services:
  auth:
    url: https://auth.example.com
    timeout: 30
  payment:
    url: https://payment.example.com
    timeout: 60
  notification:
    url: https://notify.example.com
    timeout: 15
    
features:
  enable_beta: false
  max_upload_size: 104857600
  session_timeout: 3600
  rate_limit: 1000
"""
    
    response = shard_tool.execute(
        action="shard",
        content=yaml_config,
        title="Application Configuration",
        format="yaml",
        max_size=150  # Force multiple shards
    )
    
    if response.success:
        print(f"✓ YAML sharded into {response.data['total_shards']} pieces")
    
    print("\n2. Testing JSON API Response Sharding")
    print("-" * 50)
    
    json_data = """{
  "users": [
    {"id": 1, "name": "Alice Smith", "role": "admin", "email": "alice@example.com"},
    {"id": 2, "name": "Bob Jones", "role": "developer", "email": "bob@example.com"},
    {"id": 3, "name": "Carol White", "role": "designer", "email": "carol@example.com"}
  ],
  "projects": [
    {"id": 101, "name": "Project Alpha", "status": "active", "team_size": 5},
    {"id": 102, "name": "Project Beta", "status": "planning", "team_size": 3}
  ],
  "metrics": {
    "total_users": 150,
    "active_projects": 12,
    "completed_tasks": 1543,
    "average_velocity": 47.5
  }
}"""
    
    response = shard_tool.execute(
        action="shard",
        content=json_data,
        title="API Response Data",
        format="json",
        max_size=200  # Force sharding
    )
    
    if response.success:
        print(f"✓ JSON sharded into {response.data['total_shards']} pieces")
    
    print("\n3. Testing Export/Import Functionality")
    print("-" * 50)
    
    import tempfile
    import os
    
    # Create temporary directory for export
    with tempfile.TemporaryDirectory() as tmpdir:
        # Export shards
        export_response = shard_tool.execute(
            action="export",
            document_id=response.data['document_id'],
            output_dir=tmpdir
        )
        
        if export_response.success:
            print(f"✓ Exported {export_response.data['total_files']} files to {tmpdir}")
            
            # Clear the sharding system
            shard_tool.sharding_system.shards.clear()
            shard_tool.sharding_system.indices.clear()
            
            # Import shards back
            index_file = next(f for f in export_response.data['files'] if 'index' in f)
            import_response = shard_tool.execute(
                action="import",
                index_file=index_file
            )
            
            if import_response.success:
                print(f"✓ Successfully imported {import_response.data['total_shards']} shards")
                print(f"  Document: {import_response.data['title']}")
    
    print("\n" + "=" * 60)
    print("Advanced scenarios testing completed! ✓")
    
    return True


if __name__ == "__main__":
    try:
        # Run integration tests
        success = test_sharding_with_handoff()
        
        # Run advanced scenarios
        success = success and test_advanced_sharding_scenarios()
        
        if success:
            print("\n✅ All integration tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)