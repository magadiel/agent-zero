"""
Document Manager for Agile AI Company
Handles document storage, retrieval, versioning, and metadata management.
"""

import json
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path
import pickle
import yaml


class DocumentType(Enum):
    """Types of documents in the system"""
    PRD = "product_requirements_document"
    ARCHITECTURE = "architecture_document"
    STORY = "user_story"
    EPIC = "epic"
    TEST_PLAN = "test_plan"
    DESIGN = "design_document"
    REPORT = "report"
    CHECKLIST = "checklist"
    TEMPLATE = "template"
    WORKFLOW = "workflow"
    MEETING_NOTES = "meeting_notes"
    RETROSPECTIVE = "retrospective"
    OTHER = "other"


class DocumentStatus(Enum):
    """Document lifecycle states"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class AccessLevel(Enum):
    """Access control levels"""
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3


@dataclass
class DocumentMetadata:
    """Metadata for a document"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified_by: str = ""
    modified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    parent_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    workflow_id: Optional[str] = None
    team_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    # Access control
    owner: str = ""
    editors: Set[str] = field(default_factory=set)
    viewers: Set[str] = field(default_factory=set)
    
    # Content metadata
    content_hash: str = ""
    content_size: int = 0
    content_type: str = "text/markdown"
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data['created_at'] = self.created_at.isoformat()
        data['modified_at'] = self.modified_at.isoformat()
        # Convert sets to lists
        data['editors'] = list(self.editors)
        data['viewers'] = list(self.viewers)
        # Convert enums to strings
        data['type'] = self.type.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        # Convert ISO strings back to datetime
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'modified_at' in data:
            data['modified_at'] = datetime.fromisoformat(data['modified_at'])
        # Convert lists back to sets
        if 'editors' in data:
            data['editors'] = set(data['editors'])
        if 'viewers' in data:
            data['viewers'] = set(data['viewers'])
        # Convert strings back to enums
        if 'type' in data:
            data['type'] = DocumentType(data['type'])
        if 'status' in data:
            data['status'] = DocumentStatus(data['status'])
        return cls(**data)


@dataclass
class Document:
    """A document with content and metadata"""
    metadata: DocumentMetadata
    content: Any  # Can be string, dict, list, etc.
    
    def calculate_hash(self) -> str:
        """Calculate content hash"""
        if isinstance(self.content, str):
            content_bytes = self.content.encode('utf-8')
        else:
            content_bytes = json.dumps(self.content, sort_keys=True).encode('utf-8')
        return hashlib.sha256(content_bytes).hexdigest()
    
    def update_metadata(self, modifier: str):
        """Update metadata after modification"""
        self.metadata.modified_by = modifier
        self.metadata.modified_at = datetime.now(timezone.utc)
        self.metadata.content_hash = self.calculate_hash()
        if isinstance(self.content, str):
            self.metadata.content_size = len(self.content)
        else:
            self.metadata.content_size = len(json.dumps(self.content))


class DocumentRegistry:
    """Central registry for all documents"""
    
    def __init__(self, storage_path: str = "./storage/documents"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory indices
        self.documents: Dict[str, Document] = {}
        self.version_history: Dict[str, List[str]] = {}  # doc_id -> [version_ids]
        self.workflow_documents: Dict[str, Set[str]] = {}  # workflow_id -> doc_ids
        self.team_documents: Dict[str, Set[str]] = {}  # team_id -> doc_ids
        self.type_index: Dict[DocumentType, Set[str]] = {}  # type -> doc_ids
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        # Load existing documents
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk"""
        registry_file = self.storage_path / "registry.pkl"
        if registry_file.exists():
            try:
                with open(registry_file, 'rb') as f:
                    data = pickle.load(f)
                    # Reconstruct documents from saved data
                    for doc_id, doc_data in data.get('documents', {}).items():
                        metadata = DocumentMetadata.from_dict(doc_data['metadata'])
                        document = Document(metadata=metadata, content=doc_data['content'])
                        self.documents[doc_id] = document
                    
                    self.version_history = data.get('version_history', {})
                    self.workflow_documents = {k: set(v) for k, v in data.get('workflow_documents', {}).items()}
                    self.team_documents = {k: set(v) for k, v in data.get('team_documents', {}).items()}
                    
                    # Rebuild type index
                    for doc_id, doc in self.documents.items():
                        doc_type = doc.metadata.type
                        if doc_type not in self.type_index:
                            self.type_index[doc_type] = set()
                        self.type_index[doc_type].add(doc_id)
            except Exception as e:
                print(f"Error loading registry: {e}")
    
    def _save_registry(self):
        """Save registry to disk"""
        registry_file = self.storage_path / "registry.pkl"
        data = {
            'documents': {
                doc_id: {
                    'metadata': doc.metadata.to_dict(),
                    'content': doc.content
                }
                for doc_id, doc in self.documents.items()
            },
            'version_history': self.version_history,
            'workflow_documents': {k: list(v) for k, v in self.workflow_documents.items()},
            'team_documents': {k: list(v) for k, v in self.team_documents.items()}
        }
        with open(registry_file, 'wb') as f:
            pickle.dump(data, f)
    
    async def create_document(
        self,
        content: Any,
        title: str,
        doc_type: DocumentType,
        created_by: str,
        workflow_id: Optional[str] = None,
        team_id: Optional[str] = None,
        **kwargs
    ) -> Document:
        """Create a new document"""
        async with self.lock:
            metadata = DocumentMetadata(
                title=title,
                type=doc_type,
                created_by=created_by,
                owner=created_by,
                workflow_id=workflow_id,
                team_id=team_id,
                **kwargs
            )
            
            document = Document(metadata=metadata, content=content)
            document.update_metadata(created_by)
            
            # Store document
            self.documents[metadata.id] = document
            
            # Update indices
            if doc_type not in self.type_index:
                self.type_index[doc_type] = set()
            self.type_index[doc_type].add(metadata.id)
            
            if workflow_id:
                if workflow_id not in self.workflow_documents:
                    self.workflow_documents[workflow_id] = set()
                self.workflow_documents[workflow_id].add(metadata.id)
            
            if team_id:
                if team_id not in self.team_documents:
                    self.team_documents[team_id] = set()
                self.team_documents[team_id].add(metadata.id)
            
            # Initialize version history
            self.version_history[metadata.id] = [metadata.id]
            
            # Save to disk
            self._save_registry()
            
            return document
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve a document by ID"""
        async with self.lock:
            return self.documents.get(doc_id)
    
    async def update_document(
        self,
        doc_id: str,
        content: Any,
        modified_by: str,
        create_version: bool = True
    ) -> Optional[Document]:
        """Update a document, optionally creating a new version"""
        async with self.lock:
            if doc_id not in self.documents:
                return None
            
            document = self.documents[doc_id]
            
            if create_version:
                # Create new version
                old_metadata = document.metadata
                new_metadata = DocumentMetadata(
                    title=old_metadata.title,
                    type=old_metadata.type,
                    created_by=modified_by,
                    owner=old_metadata.owner,
                    editors=old_metadata.editors.copy(),
                    viewers=old_metadata.viewers.copy(),
                    workflow_id=old_metadata.workflow_id,
                    team_id=old_metadata.team_id,
                    version=old_metadata.version + 1,
                    parent_version=old_metadata.id,
                    tags=old_metadata.tags.copy(),
                    dependencies=old_metadata.dependencies.copy(),
                    properties=old_metadata.properties.copy()
                )
                
                new_document = Document(metadata=new_metadata, content=content)
                new_document.update_metadata(modified_by)
                
                # Store new version
                self.documents[new_metadata.id] = new_document
                
                # Update version history
                if doc_id in self.version_history:
                    self.version_history[doc_id].append(new_metadata.id)
                else:
                    self.version_history[doc_id] = [doc_id, new_metadata.id]
                
                # Update indices for new version
                if new_metadata.type not in self.type_index:
                    self.type_index[new_metadata.type] = set()
                self.type_index[new_metadata.type].add(new_metadata.id)
                
                if new_metadata.workflow_id:
                    if new_metadata.workflow_id not in self.workflow_documents:
                        self.workflow_documents[new_metadata.workflow_id] = set()
                    self.workflow_documents[new_metadata.workflow_id].add(new_metadata.id)
                
                if new_metadata.team_id:
                    if new_metadata.team_id not in self.team_documents:
                        self.team_documents[new_metadata.team_id] = set()
                    self.team_documents[new_metadata.team_id].add(new_metadata.id)
                
                document = new_document
            else:
                # Update in place
                document.content = content
                document.update_metadata(modified_by)
            
            # Save to disk
            self._save_registry()
            
            return document
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document (marks as archived)"""
        async with self.lock:
            if doc_id not in self.documents:
                return False
            
            document = self.documents[doc_id]
            document.metadata.status = DocumentStatus.ARCHIVED
            
            # Save to disk
            self._save_registry()
            
            return True
    
    async def get_document_versions(self, doc_id: str) -> List[Document]:
        """Get all versions of a document"""
        async with self.lock:
            if doc_id not in self.version_history:
                return []
            
            versions = []
            for version_id in self.version_history[doc_id]:
                if version_id in self.documents:
                    versions.append(self.documents[version_id])
            
            return versions
    
    async def search_documents(
        self,
        doc_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        workflow_id: Optional[str] = None,
        team_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> List[Document]:
        """Search for documents matching criteria"""
        async with self.lock:
            results = []
            
            # Start with all documents or filtered by type
            if doc_type and doc_type in self.type_index:
                candidate_ids = self.type_index[doc_type]
            else:
                candidate_ids = set(self.documents.keys())
            
            # Apply filters
            for doc_id in candidate_ids:
                if doc_id not in self.documents:
                    continue
                    
                document = self.documents[doc_id]
                metadata = document.metadata
                
                # Check status
                if status and metadata.status != status:
                    continue
                
                # Check workflow
                if workflow_id and metadata.workflow_id != workflow_id:
                    continue
                
                # Check team
                if team_id and metadata.team_id != team_id:
                    continue
                
                # Check tags
                if tags and not any(tag in metadata.tags for tag in tags):
                    continue
                
                # Check creator
                if created_by and metadata.created_by != created_by:
                    continue
                
                results.append(document)
            
            return results
    
    async def get_workflow_documents(self, workflow_id: str) -> List[Document]:
        """Get all documents for a workflow"""
        async with self.lock:
            if workflow_id not in self.workflow_documents:
                return []
            
            docs = []
            for doc_id in self.workflow_documents[workflow_id]:
                if doc_id in self.documents:
                    docs.append(self.documents[doc_id])
            
            return docs
    
    async def get_team_documents(self, team_id: str) -> List[Document]:
        """Get all documents for a team"""
        async with self.lock:
            if team_id not in self.team_documents:
                return []
            
            docs = []
            for doc_id in self.team_documents[team_id]:
                if doc_id in self.documents:
                    docs.append(self.documents[doc_id])
            
            return docs
    
    async def check_access(
        self,
        doc_id: str,
        user_id: str,
        required_level: AccessLevel
    ) -> bool:
        """Check if user has required access level"""
        async with self.lock:
            if doc_id not in self.documents:
                return False
            
            metadata = self.documents[doc_id].metadata
            
            # Owner has admin access
            if metadata.owner == user_id:
                return True
            
            # Check specific access levels
            if required_level == AccessLevel.READ:
                return user_id in metadata.viewers or user_id in metadata.editors
            elif required_level == AccessLevel.WRITE:
                return user_id in metadata.editors
            elif required_level == AccessLevel.ADMIN:
                return metadata.owner == user_id
            
            return False
    
    async def grant_access(
        self,
        doc_id: str,
        user_id: str,
        access_level: AccessLevel,
        granter_id: str
    ) -> bool:
        """Grant access to a document"""
        async with self.lock:
            if doc_id not in self.documents:
                return False
            
            document = self.documents[doc_id]
            metadata = document.metadata
            
            # Only owner can grant access
            if metadata.owner != granter_id:
                return False
            
            if access_level == AccessLevel.READ:
                metadata.viewers.add(user_id)
            elif access_level == AccessLevel.WRITE:
                metadata.editors.add(user_id)
                metadata.viewers.add(user_id)  # Write implies read
            elif access_level == AccessLevel.ADMIN:
                # Transfer ownership
                metadata.owner = user_id
                metadata.editors.add(user_id)
                metadata.viewers.add(user_id)
            
            # Save to disk
            self._save_registry()
            
            return True
    
    async def revoke_access(
        self,
        doc_id: str,
        user_id: str,
        revoker_id: str
    ) -> bool:
        """Revoke access to a document"""
        async with self.lock:
            if doc_id not in self.documents:
                return False
            
            document = self.documents[doc_id]
            metadata = document.metadata
            
            # Only owner can revoke access
            if metadata.owner != revoker_id:
                return False
            
            # Can't revoke owner's access
            if user_id == metadata.owner:
                return False
            
            metadata.viewers.discard(user_id)
            metadata.editors.discard(user_id)
            
            # Save to disk
            self._save_registry()
            
            return True
    
    async def add_dependency(
        self,
        doc_id: str,
        dependency_id: str
    ) -> bool:
        """Add a dependency between documents"""
        async with self.lock:
            if doc_id not in self.documents or dependency_id not in self.documents:
                return False
            
            document = self.documents[doc_id]
            if dependency_id not in document.metadata.dependencies:
                document.metadata.dependencies.append(dependency_id)
                
                # Save to disk
                self._save_registry()
            
            return True
    
    async def get_dependencies(
        self,
        doc_id: str,
        recursive: bool = False
    ) -> List[Document]:
        """Get document dependencies"""
        async with self.lock:
            if doc_id not in self.documents:
                return []
            
            document = self.documents[doc_id]
            dependency_ids = set(document.metadata.dependencies)
            
            if recursive:
                # Recursively collect all dependencies
                visited = set()
                to_visit = list(dependency_ids)
                
                while to_visit:
                    dep_id = to_visit.pop(0)
                    if dep_id in visited:
                        continue
                    
                    visited.add(dep_id)
                    
                    if dep_id in self.documents:
                        dep_doc = self.documents[dep_id]
                        for sub_dep_id in dep_doc.metadata.dependencies:
                            if sub_dep_id not in visited:
                                to_visit.append(sub_dep_id)
                
                dependency_ids = visited
            
            # Collect documents
            dependencies = []
            for dep_id in dependency_ids:
                if dep_id in self.documents:
                    dependencies.append(self.documents[dep_id])
            
            return dependencies
    
    async def export_document(
        self,
        doc_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """Export document in specified format"""
        async with self.lock:
            if doc_id not in self.documents:
                return None
            
            document = self.documents[doc_id]
            
            if format == "json":
                data = {
                    'metadata': document.metadata.to_dict(),
                    'content': document.content
                }
                return json.dumps(data, indent=2, default=str)
            
            elif format == "yaml":
                data = {
                    'metadata': document.metadata.to_dict(),
                    'content': document.content
                }
                return yaml.dump(data, default_flow_style=False)
            
            elif format == "markdown":
                # Format as markdown with metadata header
                lines = ["---"]
                lines.append(f"title: {document.metadata.title}")
                lines.append(f"type: {document.metadata.type.value}")
                lines.append(f"status: {document.metadata.status.value}")
                lines.append(f"version: {document.metadata.version}")
                lines.append(f"created_by: {document.metadata.created_by}")
                lines.append(f"created_at: {document.metadata.created_at.isoformat()}")
                lines.append("---")
                lines.append("")
                
                if isinstance(document.content, str):
                    lines.append(document.content)
                else:
                    lines.append("```json")
                    lines.append(json.dumps(document.content, indent=2))
                    lines.append("```")
                
                return "\n".join(lines)
            
            return None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        async with self.lock:
            stats = {
                'total_documents': len(self.documents),
                'documents_by_type': {},
                'documents_by_status': {},
                'total_workflows': len(self.workflow_documents),
                'total_teams': len(self.team_documents),
                'total_versions': sum(len(versions) for versions in self.version_history.values())
            }
            
            # Count by type
            for doc_type in DocumentType:
                if doc_type in self.type_index:
                    stats['documents_by_type'][doc_type.value] = len(self.type_index[doc_type])
                else:
                    stats['documents_by_type'][doc_type.value] = 0
            
            # Count by status
            for status in DocumentStatus:
                count = sum(
                    1 for doc in self.documents.values()
                    if doc.metadata.status == status
                )
                stats['documents_by_status'][status.value] = count
            
            return stats


# Singleton instance
_registry_instance: Optional[DocumentRegistry] = None


def get_document_registry(storage_path: str = "./storage/documents") -> DocumentRegistry:
    """Get or create the document registry singleton"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DocumentRegistry(storage_path)
    return _registry_instance