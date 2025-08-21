"""
Comprehensive tests for the Document Sharding System.
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from python.helpers.document_sharding import (
    DocumentShardingSystem,
    DocumentShard,
    ShardIndex,
    ShardingStrategy,
    DocumentFormat,
    MarkdownShardProcessor,
    YAMLShardProcessor,
    JSONShardProcessor
)


class TestDocumentShard:
    """Test DocumentShard class."""
    
    def test_shard_creation(self):
        """Test creating a document shard."""
        shard = DocumentShard(
            title="Test Shard",
            content="This is test content.\nWith multiple lines.",
            format=DocumentFormat.TEXT
        )
        
        assert shard.title == "Test Shard"
        assert shard.content == "This is test content.\nWith multiple lines."
        assert shard.format == DocumentFormat.TEXT
        assert shard.size_bytes == len(shard.content.encode('utf-8'))
        assert shard.line_count == 2
        assert shard.word_count == 7
    
    def test_shard_serialization(self):
        """Test shard serialization and deserialization."""
        shard = DocumentShard(
            title="Test Shard",
            content="Test content",
            metadata={"key": "value"},
            references={"ref1", "ref2"}
        )
        
        # Serialize to dict
        shard_dict = shard.to_dict()
        assert shard_dict['title'] == "Test Shard"
        assert 'created_at' in shard_dict
        assert isinstance(shard_dict['references'], list)
        
        # Deserialize from dict
        restored = DocumentShard.from_dict(shard_dict)
        assert restored.title == shard.title
        assert restored.content == shard.content
        assert restored.metadata == shard.metadata
        assert restored.references == shard.references


class TestShardIndex:
    """Test ShardIndex class."""
    
    def test_index_creation(self):
        """Test creating a shard index."""
        index = ShardIndex(
            document_id="doc123",
            title="Test Document",
            total_shards=3
        )
        
        assert index.document_id == "doc123"
        assert index.title == "Test Document"
        assert index.total_shards == 3
        assert len(index.shards) == 0
    
    def test_add_shard_to_index(self):
        """Test adding shards to index."""
        index = ShardIndex(
            document_id="doc123",
            title="Test Document",
            total_shards=2
        )
        
        shard1 = DocumentShard(title="Part 1", content="Content 1")
        shard2 = DocumentShard(title="Part 2", content="Content 2")
        
        index.add_shard(shard1)
        index.add_shard(shard2)
        
        assert len(index.shards) == 2
        assert index.shards[0]['title'] == "Part 1"
        assert index.shards[1]['title'] == "Part 2"


class TestDocumentShardingSystem:
    """Test DocumentShardingSystem class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.system = DocumentShardingSystem(
            max_shard_size=100,  # Small size for testing
            max_shard_lines=5,
            min_shard_size=20
        )
    
    def test_shard_by_size(self):
        """Test sharding by size."""
        content = "This is a test document. " * 20  # Create content larger than max_shard_size
        
        shards, index = self.system.shard_document(
            content=content,
            title="Test Document",
            strategy=ShardingStrategy.SIZE_BASED
        )
        
        assert len(shards) > 1
        assert index.total_shards == len(shards)
        for shard in shards:
            assert shard.size_bytes <= self.system.max_shard_size * 2  # Allow some overflow
    
    def test_shard_markdown_by_sections(self):
        """Test sharding markdown by sections."""
        content = """# Section 1
This is the first section with some content.
More content here.

## Subsection 1.1
Content for subsection.

# Section 2
This is the second section.
It has different content.

## Subsection 2.1
More subsection content.

# Section 3
Final section content."""
        
        shards, index = self.system.shard_document(
            content=content,
            title="Markdown Document",
            strategy=ShardingStrategy.SECTION_BASED,
            format=DocumentFormat.MARKDOWN
        )
        
        assert len(shards) >= 2
        assert any("Section" in shard.title for shard in shards)
    
    def test_shard_by_paragraphs(self):
        """Test sharding by paragraphs."""
        content = """First paragraph with some text.
Continues on the next line.

Second paragraph here.
With more content.

Third paragraph.
Final content."""
        
        shards, index = self.system.shard_document(
            content=content,
            title="Paragraph Document",
            strategy=ShardingStrategy.PARAGRAPH
        )
        
        assert len(shards) >= 1
        for shard in shards:
            assert shard.content.strip() != ""
    
    def test_get_shard(self):
        """Test retrieving a specific shard."""
        content = "Test content for retrieval"
        shards, index = self.system.shard_document(content, "Test")
        
        shard_id = shards[0].id
        retrieved = self.system.get_shard(shard_id)
        
        assert retrieved is not None
        assert retrieved.id == shard_id
        assert retrieved.content == content
    
    def test_get_shards_by_document(self):
        """Test retrieving all shards for a document."""
        content = "Test content " * 10
        shards, index = self.system.shard_document(content, "Test")
        
        retrieved_shards = self.system.get_shards_by_document(index.document_id)
        
        assert len(retrieved_shards) == len(shards)
        assert all(s.parent_id == index.document_id for s in retrieved_shards)
    
    def test_reassemble_document(self):
        """Test reassembling a sharded document."""
        original_content = "This is line 1.\nThis is line 2.\nThis is line 3."
        shards, index = self.system.shard_document(
            content=original_content,
            title="Test",
            strategy=ShardingStrategy.SIZE_BASED
        )
        
        reassembled = self.system.reassemble_document(index.document_id)
        
        assert reassembled is not None
        # Content might have minor differences due to sharding
        assert len(reassembled) == len(original_content)
    
    def test_search_shards(self):
        """Test searching within shards."""
        content1 = "This document contains specific keyword"
        content2 = "This document has different content"
        
        shards1, index1 = self.system.shard_document(content1, "Doc1")
        shards2, index2 = self.system.shard_document(content2, "Doc2")
        
        # Search for specific keyword
        results = self.system.search_shards("specific keyword")
        
        assert len(results) == 1
        assert results[0].parent_id == index1.document_id
        
        # Search within specific document
        results = self.system.search_shards("document", index2.document_id)
        
        assert len(results) == 1
        assert results[0].parent_id == index2.document_id
    
    def test_export_import_shards(self):
        """Test exporting and importing shards."""
        content = "Test content for export/import"
        shards, index = self.system.shard_document(content, "Test Export")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Export shards
            exported_files = self.system.export_shards(index.document_id, tmppath)
            assert len(exported_files) > 0
            assert any("index" in str(f) for f in exported_files)
            
            # Clear system and reimport
            self.system.shards.clear()
            self.system.indices.clear()
            
            index_file = next(f for f in exported_files if "index" in str(f))
            imported_shards, imported_index = self.system.import_shards(index_file)
            
            assert imported_index.document_id == index.document_id
            assert len(imported_shards) == len(shards)
    
    def test_get_statistics(self):
        """Test getting document statistics."""
        content = "Test content " * 50
        shards, index = self.system.shard_document(content, "Stats Test")
        
        stats = self.system.get_statistics(index.document_id)
        
        assert stats['document_id'] == index.document_id
        assert stats['title'] == "Stats Test"
        assert stats['total_shards'] > 0
        assert stats['total_words'] > 0
        assert 'average_shard_size' in stats
    
    def test_extract_references(self):
        """Test extracting references from content."""
        content = """
        See [link1](http://example.com) for more info.
        Also check @shard:abc123 for details.
        Another [reference](doc.pdf) here.
        """
        
        shards, index = self.system.shard_document(
            content=content,
            title="Refs Test",
            format=DocumentFormat.MARKDOWN
        )
        
        assert len(shards[0].references) > 0
        assert "http://example.com" in shards[0].references
        assert "abc123" in shards[0].references


class TestMarkdownShardProcessor:
    """Test MarkdownShardProcessor class."""
    
    def test_extract_toc(self):
        """Test extracting table of contents."""
        processor = MarkdownShardProcessor()
        
        shard1 = DocumentShard(
            title="Part 1",
            content="# Main Title\n## Subtitle\nContent here"
        )
        shard2 = DocumentShard(
            title="Part 2",
            content="# Another Title\n### Subsubtitle\nMore content"
        )
        
        toc = processor.extract_toc([shard1, shard2])
        
        assert "Table of Contents" in toc
        assert "Main Title" in toc
        assert "Another Title" in toc
        assert "@shard:" in toc
    
    def test_create_navigation_links(self):
        """Test creating navigation links."""
        processor = MarkdownShardProcessor()
        
        shards = [
            DocumentShard(title="Part 1", content="Content 1"),
            DocumentShard(title="Part 2", content="Content 2"),
            DocumentShard(title="Part 3", content="Content 3")
        ]
        
        nav_links = processor.create_navigation_links(shards)
        
        assert len(nav_links) == 3
        assert "Previous" not in nav_links[shards[0].id]  # First shard
        assert "Previous" in nav_links[shards[1].id]      # Middle shard
        assert "Next" in nav_links[shards[1].id]          # Middle shard
        assert "Next" not in nav_links[shards[2].id]      # Last shard


class TestYAMLShardProcessor:
    """Test YAMLShardProcessor class."""
    
    def test_shard_yaml_by_keys(self):
        """Test sharding YAML by top-level keys."""
        processor = YAMLShardProcessor()
        
        yaml_content = """
key1:
  subkey1: value1
  subkey2: value2
key2:
  subkey3: value3
  subkey4: value4
key3:
  subkey5: value5
"""
        
        shards = processor.shard_by_keys(yaml_content, max_size=50)
        
        assert len(shards) >= 2
        for title, content in shards:
            assert title.startswith("Part")
            assert len(content) > 0
    
    def test_invalid_yaml(self):
        """Test handling invalid YAML."""
        processor = YAMLShardProcessor()
        
        invalid_yaml = "This is not: valid: yaml: content:"
        shards = processor.shard_by_keys(invalid_yaml)
        
        assert len(shards) == 1
        assert shards[0] == ("", invalid_yaml)


class TestJSONShardProcessor:
    """Test JSONShardProcessor class."""
    
    def test_shard_json_by_keys(self):
        """Test sharding JSON by top-level keys."""
        processor = JSONShardProcessor()
        
        json_content = json.dumps({
            "key1": {"subkey1": "value1", "subkey2": "value2"},
            "key2": {"subkey3": "value3", "subkey4": "value4"},
            "key3": {"subkey5": "value5"}
        }, indent=2)
        
        shards = processor.shard_by_keys(json_content, max_size=50)
        
        assert len(shards) >= 2
        for title, content in shards:
            assert title.startswith("Part")
            assert len(content) > 0
            # Verify it's valid JSON
            json.loads(content)
    
    def test_invalid_json(self):
        """Test handling invalid JSON."""
        processor = JSONShardProcessor()
        
        invalid_json = "This is not valid JSON"
        shards = processor.shard_by_keys(invalid_json)
        
        assert len(shards) == 1
        assert shards[0] == ("", invalid_json)


class TestIntegration:
    """Integration tests for the sharding system."""
    
    def test_large_document_sharding(self):
        """Test sharding a large document."""
        system = DocumentShardingSystem()
        
        # Create a large document
        large_content = "\n".join([f"# Section {i}\n" + "Content " * 100 for i in range(50)])
        
        shards, index = system.shard_document(
            content=large_content,
            title="Large Document",
            strategy=ShardingStrategy.SECTION_BASED,
            format=DocumentFormat.MARKDOWN
        )
        
        assert len(shards) > 1
        assert index.total_shards == len(shards)
        
        # Verify reassembly
        reassembled = system.reassemble_document(index.document_id)
        assert reassembled is not None
        assert len(reassembled) == len(large_content)
    
    def test_mixed_format_documents(self):
        """Test sharding different document formats."""
        system = DocumentShardingSystem()
        
        # Test Markdown
        md_content = "# Title\n\nContent here"
        md_shards, md_index = system.shard_document(
            md_content, "MD Doc", format=DocumentFormat.MARKDOWN
        )
        assert md_index.format == DocumentFormat.MARKDOWN
        
        # Test YAML
        yaml_content = "key: value\nlist:\n  - item1\n  - item2"
        yaml_shards, yaml_index = system.shard_document(
            yaml_content, "YAML Doc", format=DocumentFormat.YAML
        )
        assert yaml_index.format == DocumentFormat.YAML
        
        # Test JSON
        json_content = '{"key": "value", "list": ["item1", "item2"]}'
        json_shards, json_index = system.shard_document(
            json_content, "JSON Doc", format=DocumentFormat.JSON
        )
        assert json_index.format == DocumentFormat.JSON
        
        # Test plain text
        text_content = "Plain text content"
        text_shards, text_index = system.shard_document(
            text_content, "Text Doc", format=DocumentFormat.TEXT
        )
        assert text_index.format == DocumentFormat.TEXT


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])