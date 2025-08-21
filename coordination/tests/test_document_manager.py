"""
Test suite for Document Manager
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

import sys
sys.path.append('..')
from document_manager import (
    DocumentRegistry, Document, DocumentMetadata,
    DocumentType, DocumentStatus, AccessLevel,
    get_document_registry
)


class TestDocumentMetadata:
    """Test DocumentMetadata class"""
    
    def test_metadata_creation(self):
        """Test creating metadata"""
        metadata = DocumentMetadata(
            title="Test Document",
            type=DocumentType.PRD,
            created_by="agent1",
            owner="agent1"
        )
        
        assert metadata.title == "Test Document"
        assert metadata.type == DocumentType.PRD
        assert metadata.status == DocumentStatus.DRAFT
        assert metadata.created_by == "agent1"
        assert metadata.owner == "agent1"
        assert metadata.version == 1
        assert metadata.parent_version is None
        
    def test_metadata_serialization(self):
        """Test metadata to_dict and from_dict"""
        metadata = DocumentMetadata(
            title="Test Doc",
            type=DocumentType.ARCHITECTURE,
            created_by="agent2",
            owner="agent2"
        )
        metadata.editors.add("agent3")
        metadata.viewers.add("agent4")
        
        # Convert to dict
        data = metadata.to_dict()
        assert data['title'] == "Test Doc"
        assert data['type'] == DocumentType.ARCHITECTURE.value
        assert 'agent3' in data['editors']
        assert 'agent4' in data['viewers']
        
        # Convert back from dict
        metadata2 = DocumentMetadata.from_dict(data)
        assert metadata2.title == metadata.title
        assert metadata2.type == metadata.type
        assert metadata2.editors == metadata.editors
        assert metadata2.viewers == metadata.viewers


class TestDocument:
    """Test Document class"""
    
    def test_document_creation(self):
        """Test creating a document"""
        metadata = DocumentMetadata(
            title="Test Content",
            type=DocumentType.STORY,
            created_by="agent1",
            owner="agent1"
        )
        
        content = "This is test content"
        doc = Document(metadata=metadata, content=content)
        
        assert doc.metadata == metadata
        assert doc.content == content
        
    def test_content_hash(self):
        """Test content hash calculation"""
        metadata = DocumentMetadata(title="Hash Test")
        
        # Test string content
        doc1 = Document(metadata=metadata, content="Hello World")
        hash1 = doc1.calculate_hash()
        assert len(hash1) == 64  # SHA256 hex digest length
        
        # Same content should produce same hash
        doc2 = Document(metadata=metadata, content="Hello World")
        hash2 = doc2.calculate_hash()
        assert hash1 == hash2
        
        # Different content should produce different hash
        doc3 = Document(metadata=metadata, content="Different content")
        hash3 = doc3.calculate_hash()
        assert hash1 != hash3
        
        # Test dict content
        doc4 = Document(metadata=metadata, content={"key": "value"})
        hash4 = doc4.calculate_hash()
        assert len(hash4) == 64
        
    def test_update_metadata(self):
        """Test updating document metadata"""
        metadata = DocumentMetadata(title="Update Test")
        doc = Document(metadata=metadata, content="Initial content")
        
        initial_time = doc.metadata.modified_at
        initial_hash = doc.metadata.content_hash
        
        # Update metadata
        doc.update_metadata("modifier1")
        
        assert doc.metadata.modified_by == "modifier1"
        assert doc.metadata.modified_at > initial_time
        assert doc.metadata.content_hash != initial_hash
        assert doc.metadata.content_size == len("Initial content")


@pytest.mark.asyncio
class TestDocumentRegistry:
    """Test DocumentRegistry class"""
    
    @pytest.fixture
    async def registry(self):
        """Create a temporary registry for testing"""
        temp_dir = tempfile.mkdtemp()
        registry = DocumentRegistry(storage_path=temp_dir)
        yield registry
        # Cleanup
        shutil.rmtree(temp_dir)
    
    async def test_create_document(self, registry):
        """Test creating a document"""
        doc = await registry.create_document(
            content="Test content",
            title="Test Document",
            doc_type=DocumentType.PRD,
            created_by="agent1",
            workflow_id="workflow1",
            team_id="team1"
        )
        
        assert doc.metadata.title == "Test Document"
        assert doc.metadata.type == DocumentType.PRD
        assert doc.metadata.created_by == "agent1"
        assert doc.metadata.owner == "agent1"
        assert doc.metadata.workflow_id == "workflow1"
        assert doc.metadata.team_id == "team1"
        assert doc.content == "Test content"
        
        # Verify document is stored
        assert doc.metadata.id in registry.documents
        
        # Verify indices updated
        assert doc.metadata.id in registry.type_index[DocumentType.PRD]
        assert doc.metadata.id in registry.workflow_documents["workflow1"]
        assert doc.metadata.id in registry.team_documents["team1"]
        
    async def test_get_document(self, registry):
        """Test retrieving a document"""
        # Create a document
        created_doc = await registry.create_document(
            content="Retrieve test",
            title="Get Test",
            doc_type=DocumentType.STORY,
            created_by="agent2"
        )
        
        # Retrieve it
        retrieved_doc = await registry.get_document(created_doc.metadata.id)
        
        assert retrieved_doc is not None
        assert retrieved_doc.metadata.id == created_doc.metadata.id
        assert retrieved_doc.content == "Retrieve test"
        
        # Try to retrieve non-existent document
        none_doc = await registry.get_document("non-existent-id")
        assert none_doc is None
        
    async def test_update_document(self, registry):
        """Test updating a document"""
        # Create initial document
        doc = await registry.create_document(
            content="Initial content",
            title="Update Test",
            doc_type=DocumentType.DESIGN,
            created_by="agent3"
        )
        
        initial_id = doc.metadata.id
        
        # Update with new version
        updated_doc = await registry.update_document(
            doc_id=initial_id,
            content="Updated content",
            modified_by="agent4",
            create_version=True
        )
        
        assert updated_doc is not None
        assert updated_doc.metadata.version == 2
        assert updated_doc.metadata.parent_version == initial_id
        assert updated_doc.content == "Updated content"
        assert updated_doc.metadata.modified_by == "agent4"
        
        # Verify version history
        assert initial_id in registry.version_history
        assert len(registry.version_history[initial_id]) == 2
        
        # Update in place (no new version)
        updated_doc2 = await registry.update_document(
            doc_id=initial_id,
            content="In-place update",
            modified_by="agent5",
            create_version=False
        )
        
        assert updated_doc2 is not None
        assert updated_doc2.metadata.id == initial_id
        assert updated_doc2.metadata.version == 1  # Version unchanged
        assert updated_doc2.content == "In-place update"
        
    async def test_delete_document(self, registry):
        """Test deleting (archiving) a document"""
        # Create a document
        doc = await registry.create_document(
            content="To be deleted",
            title="Delete Test",
            doc_type=DocumentType.REPORT,
            created_by="agent6"
        )
        
        doc_id = doc.metadata.id
        
        # Delete it
        result = await registry.delete_document(doc_id)
        assert result is True
        
        # Document should still exist but be archived
        archived_doc = await registry.get_document(doc_id)
        assert archived_doc is not None
        assert archived_doc.metadata.status == DocumentStatus.ARCHIVED
        
        # Try to delete non-existent document
        result2 = await registry.delete_document("non-existent")
        assert result2 is False
        
    async def test_document_versions(self, registry):
        """Test document version management"""
        # Create initial document
        doc = await registry.create_document(
            content="Version 1",
            title="Version Test",
            doc_type=DocumentType.EPIC,
            created_by="agent7"
        )
        
        initial_id = doc.metadata.id
        
        # Create multiple versions
        for i in range(2, 5):
            await registry.update_document(
                doc_id=initial_id,
                content=f"Version {i}",
                modified_by=f"agent{i+6}",
                create_version=True
            )
        
        # Get all versions
        versions = await registry.get_document_versions(initial_id)
        
        assert len(versions) == 4
        assert versions[0].content == "Version 1"
        assert versions[0].metadata.version == 1
        assert versions[-1].metadata.version == 4
        
    async def test_search_documents(self, registry):
        """Test searching for documents"""
        # Create various documents
        await registry.create_document(
            content="PRD content",
            title="PRD 1",
            doc_type=DocumentType.PRD,
            created_by="agent8",
            workflow_id="wf1",
            tags=["important", "phase1"]
        )
        
        await registry.create_document(
            content="Story content",
            title="Story 1",
            doc_type=DocumentType.STORY,
            created_by="agent8",
            team_id="team1",
            tags=["phase1"]
        )
        
        await registry.create_document(
            content="PRD content 2",
            title="PRD 2",
            doc_type=DocumentType.PRD,
            created_by="agent9",
            workflow_id="wf2"
        )
        
        # Search by type
        prds = await registry.search_documents(doc_type=DocumentType.PRD)
        assert len(prds) == 2
        
        # Search by creator
        agent8_docs = await registry.search_documents(created_by="agent8")
        assert len(agent8_docs) == 2
        
        # Search by workflow
        wf1_docs = await registry.search_documents(workflow_id="wf1")
        assert len(wf1_docs) == 1
        
        # Search by tags
        phase1_docs = await registry.search_documents(tags=["phase1"])
        assert len(phase1_docs) == 2
        
        # Combined search
        combined = await registry.search_documents(
            doc_type=DocumentType.PRD,
            created_by="agent8"
        )
        assert len(combined) == 1
        
    async def test_access_control(self, registry):
        """Test document access control"""
        # Create a document
        doc = await registry.create_document(
            content="Private content",
            title="Access Test",
            doc_type=DocumentType.DESIGN,
            created_by="owner1"
        )
        
        doc_id = doc.metadata.id
        
        # Owner should have admin access
        has_admin = await registry.check_access(doc_id, "owner1", AccessLevel.ADMIN)
        assert has_admin is True
        
        # Others should not have access
        no_access = await registry.check_access(doc_id, "other1", AccessLevel.READ)
        assert no_access is False
        
        # Grant read access
        granted = await registry.grant_access(
            doc_id, "reader1", AccessLevel.READ, "owner1"
        )
        assert granted is True
        
        # Verify read access
        has_read = await registry.check_access(doc_id, "reader1", AccessLevel.READ)
        assert has_read is True
        
        # But not write access
        no_write = await registry.check_access(doc_id, "reader1", AccessLevel.WRITE)
        assert no_write is False
        
        # Grant write access
        granted2 = await registry.grant_access(
            doc_id, "editor1", AccessLevel.WRITE, "owner1"
        )
        assert granted2 is True
        
        # Verify write access
        has_write = await registry.check_access(doc_id, "editor1", AccessLevel.WRITE)
        assert has_write is True
        
        # Revoke access
        revoked = await registry.revoke_access(doc_id, "reader1", "owner1")
        assert revoked is True
        
        # Verify access revoked
        no_access2 = await registry.check_access(doc_id, "reader1", AccessLevel.READ)
        assert no_access2 is False
        
        # Non-owner can't grant access
        not_granted = await registry.grant_access(
            doc_id, "other2", AccessLevel.READ, "editor1"
        )
        assert not_granted is False
        
    async def test_dependencies(self, registry):
        """Test document dependencies"""
        # Create documents
        doc1 = await registry.create_document(
            content="Doc 1",
            title="Doc 1",
            doc_type=DocumentType.ARCHITECTURE,
            created_by="agent10"
        )
        
        doc2 = await registry.create_document(
            content="Doc 2",
            title="Doc 2",
            doc_type=DocumentType.DESIGN,
            created_by="agent10"
        )
        
        doc3 = await registry.create_document(
            content="Doc 3",
            title="Doc 3",
            doc_type=DocumentType.STORY,
            created_by="agent10"
        )
        
        # Add dependencies: doc3 depends on doc2, doc2 depends on doc1
        added1 = await registry.add_dependency(doc3.metadata.id, doc2.metadata.id)
        assert added1 is True
        
        added2 = await registry.add_dependency(doc2.metadata.id, doc1.metadata.id)
        assert added2 is True
        
        # Get direct dependencies
        deps = await registry.get_dependencies(doc3.metadata.id, recursive=False)
        assert len(deps) == 1
        assert deps[0].metadata.id == doc2.metadata.id
        
        # Get recursive dependencies
        all_deps = await registry.get_dependencies(doc3.metadata.id, recursive=True)
        assert len(all_deps) == 2
        dep_ids = {d.metadata.id for d in all_deps}
        assert doc1.metadata.id in dep_ids
        assert doc2.metadata.id in dep_ids
        
    async def test_export_document(self, registry):
        """Test document export"""
        # Create a document
        doc = await registry.create_document(
            content="Export test content",
            title="Export Test",
            doc_type=DocumentType.PRD,
            created_by="agent11"
        )
        
        doc_id = doc.metadata.id
        
        # Export as JSON
        json_export = await registry.export_document(doc_id, format="json")
        assert json_export is not None
        data = json.loads(json_export)
        assert data['metadata']['title'] == "Export Test"
        assert data['content'] == "Export test content"
        
        # Export as YAML
        yaml_export = await registry.export_document(doc_id, format="yaml")
        assert yaml_export is not None
        assert "title: Export Test" in yaml_export
        
        # Export as Markdown
        md_export = await registry.export_document(doc_id, format="markdown")
        assert md_export is not None
        assert "title: Export Test" in md_export
        assert "Export test content" in md_export
        
    async def test_statistics(self, registry):
        """Test registry statistics"""
        # Create some documents
        await registry.create_document(
            content="Doc 1", title="Doc 1",
            doc_type=DocumentType.PRD,
            created_by="agent12"
        )
        
        await registry.create_document(
            content="Doc 2", title="Doc 2",
            doc_type=DocumentType.PRD,
            created_by="agent12",
            workflow_id="wf1"
        )
        
        await registry.create_document(
            content="Doc 3", title="Doc 3",
            doc_type=DocumentType.STORY,
            created_by="agent13",
            team_id="team1"
        )
        
        # Get statistics
        stats = await registry.get_statistics()
        
        assert stats['total_documents'] >= 3
        assert stats['documents_by_type'][DocumentType.PRD.value] >= 2
        assert stats['documents_by_type'][DocumentType.STORY.value] >= 1
        assert stats['documents_by_status'][DocumentStatus.DRAFT.value] >= 3
        assert stats['total_workflows'] >= 1
        assert stats['total_teams'] >= 1
        
    async def test_workflow_documents(self, registry):
        """Test getting documents by workflow"""
        # Create documents for workflow
        workflow_id = "test-workflow"
        
        doc1 = await registry.create_document(
            content="WF Doc 1",
            title="WF Doc 1",
            doc_type=DocumentType.PRD,
            created_by="agent14",
            workflow_id=workflow_id
        )
        
        doc2 = await registry.create_document(
            content="WF Doc 2",
            title="WF Doc 2",
            doc_type=DocumentType.ARCHITECTURE,
            created_by="agent14",
            workflow_id=workflow_id
        )
        
        # Get workflow documents
        wf_docs = await registry.get_workflow_documents(workflow_id)
        
        assert len(wf_docs) == 2
        doc_ids = {d.metadata.id for d in wf_docs}
        assert doc1.metadata.id in doc_ids
        assert doc2.metadata.id in doc_ids
        
    async def test_team_documents(self, registry):
        """Test getting documents by team"""
        # Create documents for team
        team_id = "test-team"
        
        doc1 = await registry.create_document(
            content="Team Doc 1",
            title="Team Doc 1",
            doc_type=DocumentType.STORY,
            created_by="agent15",
            team_id=team_id
        )
        
        doc2 = await registry.create_document(
            content="Team Doc 2",
            title="Team Doc 2",
            doc_type=DocumentType.TEST_PLAN,
            created_by="agent15",
            team_id=team_id
        )
        
        # Get team documents
        team_docs = await registry.get_team_documents(team_id)
        
        assert len(team_docs) == 2
        doc_ids = {d.metadata.id for d in team_docs}
        assert doc1.metadata.id in doc_ids
        assert doc2.metadata.id in doc_ids
        
    async def test_persistence(self, registry):
        """Test that data persists across registry instances"""
        temp_dir = registry.storage_path
        
        # Create a document
        doc = await registry.create_document(
            content="Persistence test",
            title="Persist Test",
            doc_type=DocumentType.CHECKLIST,
            created_by="agent16"
        )
        
        doc_id = doc.metadata.id
        
        # Create new registry instance with same storage path
        registry2 = DocumentRegistry(storage_path=str(temp_dir))
        
        # Document should still be there
        loaded_doc = await registry2.get_document(doc_id)
        assert loaded_doc is not None
        assert loaded_doc.metadata.title == "Persist Test"
        assert loaded_doc.content == "Persistence test"
        
        # Verify indices are restored
        assert doc_id in registry2.type_index[DocumentType.CHECKLIST]


def test_singleton():
    """Test singleton pattern"""
    registry1 = get_document_registry("/tmp/test1")
    registry2 = get_document_registry("/tmp/test2")  # Different path ignored
    
    assert registry1 is registry2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])