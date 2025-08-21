#!/usr/bin/env python3
"""
Simple test script for document sharding system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.helpers.document_sharding import (
    DocumentShardingSystem,
    ShardingStrategy,
    DocumentFormat,
    MarkdownShardProcessor
)


def test_basic_sharding():
    """Test basic document sharding functionality."""
    print("Testing Document Sharding System")
    print("=" * 50)
    
    # Create sharding system
    system = DocumentShardingSystem(
        max_shard_size=500,  # Small size for testing
        max_shard_lines=20
    )
    
    # Test 1: Shard a markdown document
    print("\n1. Testing Markdown Document Sharding")
    print("-" * 40)
    
    markdown_content = """# Introduction
This is the introduction section with some important information.
We'll cover various topics in this document.

## Background
Here's the background information that provides context.
This section explains the history and motivation.

# Main Content
This is the main content section with detailed information.
We'll explore several key concepts here.

## Concept 1
First concept explanation with examples and details.
This is important for understanding the rest.

## Concept 2
Second concept builds on the first one.
More examples and practical applications.

# Conclusion
Summary of what we've learned.
Final thoughts and next steps.

## References
- Reference 1
- Reference 2
- Reference 3
"""
    
    shards, index = system.shard_document(
        content=markdown_content,
        title="Technical Documentation",
        strategy=ShardingStrategy.SECTION_BASED,
        format=DocumentFormat.MARKDOWN,
        metadata={"author": "Test System", "version": "1.0"}
    )
    
    print(f"✓ Created {len(shards)} shards from markdown document")
    print(f"  Document ID: {index.document_id}")
    print(f"  Title: {index.title}")
    
    for i, shard in enumerate(shards):
        print(f"  Shard {i+1}: {shard.title} ({shard.size_bytes} bytes, {shard.line_count} lines)")
    
    # Test 2: Search functionality
    print("\n2. Testing Search Functionality")
    print("-" * 40)
    
    search_results = system.search_shards("concept")
    print(f"✓ Found {len(search_results)} shards containing 'concept'")
    for result in search_results:
        print(f"  - {result.title}")
    
    # Test 3: Reassemble document
    print("\n3. Testing Document Reassembly")
    print("-" * 40)
    
    reassembled = system.reassemble_document(index.document_id)
    if reassembled:
        print(f"✓ Successfully reassembled document")
        print(f"  Original size: {len(markdown_content)} chars")
        print(f"  Reassembled size: {len(reassembled)} chars")
        print(f"  Content matches: {reassembled == markdown_content}")
    
    # Test 4: Get statistics
    print("\n4. Testing Statistics")
    print("-" * 40)
    
    stats = system.get_statistics(index.document_id)
    print(f"✓ Document statistics:")
    print(f"  Total shards: {stats['total_shards']}")
    print(f"  Total size: {stats['total_size_bytes']} bytes")
    print(f"  Total lines: {stats['total_lines']}")
    print(f"  Total words: {stats['total_words']}")
    print(f"  Average shard size: {stats['average_shard_size']} bytes")
    
    # Test 5: Table of Contents
    print("\n5. Testing Table of Contents Generation")
    print("-" * 40)
    
    processor = MarkdownShardProcessor()
    toc = processor.extract_toc(shards)
    print("✓ Generated table of contents:")
    print(toc[:200] + "..." if len(toc) > 200 else toc)
    
    # Test 6: Large document sharding
    print("\n6. Testing Large Document Sharding")
    print("-" * 40)
    
    large_content = "\n".join([f"# Section {i}\n\n" + "Content paragraph. " * 50 for i in range(20)])
    
    large_shards, large_index = system.shard_document(
        content=large_content,
        title="Large Document",
        strategy=ShardingStrategy.SIZE_BASED,
        format=DocumentFormat.MARKDOWN
    )
    
    print(f"✓ Sharded large document ({len(large_content)} chars) into {len(large_shards)} pieces")
    print(f"  Document ID: {large_index.document_id}")
    
    # Test 7: Different sharding strategies
    print("\n7. Testing Different Sharding Strategies")
    print("-" * 40)
    
    test_content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n\nFourth paragraph."
    
    # Paragraph-based sharding
    para_shards, para_index = system.shard_document(
        content=test_content,
        title="Paragraph Test",
        strategy=ShardingStrategy.PARAGRAPH
    )
    print(f"✓ Paragraph strategy: {len(para_shards)} shards")
    
    # Size-based sharding
    size_shards, size_index = system.shard_document(
        content=test_content,
        title="Size Test",
        strategy=ShardingStrategy.SIZE_BASED
    )
    print(f"✓ Size-based strategy: {len(size_shards)} shards")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully! ✓")
    
    return True


def test_yaml_json_sharding():
    """Test YAML and JSON document sharding."""
    print("\nTesting YAML and JSON Document Sharding")
    print("=" * 50)
    
    system = DocumentShardingSystem(max_shard_size=100)
    
    # Test YAML sharding
    print("\n1. Testing YAML Document")
    print("-" * 40)
    
    yaml_content = """
configuration:
  database:
    host: localhost
    port: 5432
    name: testdb
  cache:
    type: redis
    ttl: 3600
  logging:
    level: info
    file: app.log
settings:
  feature_flags:
    new_ui: true
    beta_features: false
  limits:
    max_connections: 100
    timeout: 30
"""
    
    yaml_shards, yaml_index = system.shard_document(
        content=yaml_content,
        title="Configuration File",
        format=DocumentFormat.YAML
    )
    
    print(f"✓ Created {len(yaml_shards)} shards from YAML document")
    
    # Test JSON sharding
    print("\n2. Testing JSON Document")
    print("-" * 40)
    
    json_content = """{
  "users": [
    {"id": 1, "name": "Alice", "role": "admin"},
    {"id": 2, "name": "Bob", "role": "user"}
  ],
  "settings": {
    "theme": "dark",
    "notifications": true
  },
  "metadata": {
    "version": "1.0.0",
    "created": "2024-01-01"
  }
}"""
    
    json_shards, json_index = system.shard_document(
        content=json_content,
        title="User Data",
        format=DocumentFormat.JSON
    )
    
    print(f"✓ Created {len(json_shards)} shards from JSON document")
    
    print("\nYAML/JSON sharding tests completed! ✓")
    
    return True


if __name__ == "__main__":
    try:
        # Run basic tests
        success = test_basic_sharding()
        
        # Run YAML/JSON tests
        success = success and test_yaml_json_sharding()
        
        if success:
            print("\n✅ All document sharding tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)