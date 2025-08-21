"""
Document Sharding System for BMAD-style document handling.

This module provides functionality to split large documents into manageable shards,
maintain relationships between shards, and enable efficient retrieval.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import yaml


class ShardingStrategy(Enum):
    """Document sharding strategies."""
    SECTION_BASED = "section_based"      # Split by markdown headers
    SIZE_BASED = "size_based"            # Split by character/line count
    SEMANTIC = "semantic"                # Split by semantic boundaries
    PARAGRAPH = "paragraph"              # Split by paragraphs
    CUSTOM = "custom"                    # Custom splitting logic


class DocumentFormat(Enum):
    """Supported document formats."""
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    TEXT = "text"


@dataclass
class DocumentShard:
    """Represents a single document shard."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str = ""
    index: int = 0
    title: str = ""
    content: str = ""
    format: DocumentFormat = DocumentFormat.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    references: Set[str] = field(default_factory=set)  # IDs of referenced shards
    created_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    line_count: int = 0
    word_count: int = 0
    
    def __post_init__(self):
        """Calculate size metrics after initialization."""
        self.size_bytes = len(self.content.encode('utf-8'))
        self.line_count = len(self.content.splitlines())
        self.word_count = len(self.content.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert shard to dictionary."""
        data = asdict(self)
        data['format'] = self.format.value
        data['created_at'] = self.created_at.isoformat()
        data['references'] = list(self.references)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentShard':
        """Create shard from dictionary."""
        data = data.copy()
        data['format'] = DocumentFormat(data.get('format', 'text'))
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['references'] = set(data.get('references', []))
        return cls(**data)


@dataclass
class ShardIndex:
    """Index for navigating document shards."""
    document_id: str
    title: str
    total_shards: int
    shards: List[Dict[str, Any]] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    format: DocumentFormat = DocumentFormat.TEXT
    
    def add_shard(self, shard: DocumentShard):
        """Add a shard to the index."""
        self.shards.append({
            'id': shard.id,
            'index': shard.index,
            'title': shard.title,
            'size_bytes': shard.size_bytes,
            'line_count': shard.line_count,
            'word_count': shard.word_count
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert index to dictionary."""
        return {
            'document_id': self.document_id,
            'title': self.title,
            'total_shards': self.total_shards,
            'shards': self.shards,
            'relationships': self.relationships,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'format': self.format.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShardIndex':
        """Create index from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['format'] = DocumentFormat(data.get('format', 'text'))
        return cls(**data)


class DocumentShardingSystem:
    """System for sharding and managing large documents."""
    
    def __init__(self, 
                 max_shard_size: int = 50000,  # Max characters per shard
                 max_shard_lines: int = 1000,   # Max lines per shard
                 min_shard_size: int = 1000):   # Min characters per shard
        """
        Initialize the document sharding system.
        
        Args:
            max_shard_size: Maximum size in characters for a shard
            max_shard_lines: Maximum number of lines for a shard
            min_shard_size: Minimum size in characters for a shard
        """
        self.max_shard_size = max_shard_size
        self.max_shard_lines = max_shard_lines
        self.min_shard_size = min_shard_size
        self.shards: Dict[str, DocumentShard] = {}
        self.indices: Dict[str, ShardIndex] = {}
    
    def shard_document(self,
                      content: str,
                      title: str = "Untitled Document",
                      strategy: ShardingStrategy = ShardingStrategy.SECTION_BASED,
                      format: DocumentFormat = DocumentFormat.MARKDOWN,
                      metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[DocumentShard], ShardIndex]:
        """
        Shard a document into smaller pieces.
        
        Args:
            content: The document content to shard
            title: Document title
            strategy: Sharding strategy to use
            format: Document format
            metadata: Optional metadata for the document
            
        Returns:
            Tuple of (list of shards, shard index)
        """
        document_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        # Detect format if not specified
        if format == DocumentFormat.MARKDOWN and not self._is_markdown(content):
            format = DocumentFormat.TEXT
        
        # Apply sharding strategy
        if strategy == ShardingStrategy.SECTION_BASED and format == DocumentFormat.MARKDOWN:
            shard_contents = self._shard_by_sections(content)
        elif strategy == ShardingStrategy.SIZE_BASED:
            shard_contents = self._shard_by_size(content)
        elif strategy == ShardingStrategy.PARAGRAPH:
            shard_contents = self._shard_by_paragraphs(content)
        elif strategy == ShardingStrategy.SEMANTIC:
            shard_contents = self._shard_by_semantic_boundaries(content)
        else:
            shard_contents = self._shard_by_size(content)
        
        # Create shards
        shards = []
        for i, (shard_title, shard_content) in enumerate(shard_contents):
            shard = DocumentShard(
                parent_id=document_id,
                index=i,
                title=shard_title or f"{title} - Part {i+1}",
                content=shard_content,
                format=format,
                metadata={**metadata, 'original_title': title}
            )
            
            # Extract references
            shard.references = self._extract_references(shard_content)
            
            shards.append(shard)
            self.shards[shard.id] = shard
        
        # Create index
        index = ShardIndex(
            document_id=document_id,
            title=title,
            total_shards=len(shards),
            format=format,
            metadata=metadata
        )
        
        for shard in shards:
            index.add_shard(shard)
        
        # Build relationships
        index.relationships = self._build_relationships(shards)
        
        self.indices[document_id] = index
        
        return shards, index
    
    def _is_markdown(self, content: str) -> bool:
        """Check if content appears to be markdown."""
        markdown_patterns = [
            r'^#{1,6}\s',  # Headers
            r'\[.*\]\(.*\)',  # Links
            r'^\*{1,2}.*\*{1,2}',  # Bold/italic
            r'^[-*+]\s',  # Lists
            r'^```',  # Code blocks
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    
    def _shard_by_sections(self, content: str) -> List[Tuple[str, str]]:
        """Shard markdown document by sections (headers)."""
        lines = content.splitlines()
        shards = []
        current_shard = []
        current_title = ""
        current_size = 0
        
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        
        for line in lines:
            match = header_pattern.match(line)
            
            # Check if we should start a new shard
            if match and current_size > self.min_shard_size:
                if current_shard:
                    shards.append((current_title, '\n'.join(current_shard)))
                current_shard = [line]
                current_title = match.group(2)
                current_size = len(line)
            else:
                current_shard.append(line)
                current_size += len(line)
                
                if not current_title and match:
                    current_title = match.group(2)
                
                # Check if shard is too large
                if current_size > self.max_shard_size or len(current_shard) > self.max_shard_lines:
                    shards.append((current_title, '\n'.join(current_shard)))
                    current_shard = []
                    current_title = ""
                    current_size = 0
        
        # Add remaining content
        if current_shard:
            shards.append((current_title, '\n'.join(current_shard)))
        
        return shards if shards else [("", content)]
    
    def _shard_by_size(self, content: str) -> List[Tuple[str, str]]:
        """Shard document by size limits."""
        lines = content.splitlines()
        shards = []
        current_shard = []
        current_size = 0
        shard_num = 1
        
        for line in lines:
            current_shard.append(line)
            current_size += len(line)
            
            if current_size > self.max_shard_size or len(current_shard) > self.max_shard_lines:
                shards.append((f"Part {shard_num}", '\n'.join(current_shard)))
                current_shard = []
                current_size = 0
                shard_num += 1
        
        if current_shard:
            shards.append((f"Part {shard_num}", '\n'.join(current_shard)))
        
        return shards if shards else [("", content)]
    
    def _shard_by_paragraphs(self, content: str) -> List[Tuple[str, str]]:
        """Shard document by paragraphs."""
        paragraphs = re.split(r'\n\s*\n', content)
        shards = []
        current_shard = []
        current_size = 0
        shard_num = 1
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > self.max_shard_size and current_shard:
                shards.append((f"Part {shard_num}", '\n\n'.join(current_shard)))
                current_shard = [para]
                current_size = para_size
                shard_num += 1
            else:
                current_shard.append(para)
                current_size += para_size
        
        if current_shard:
            shards.append((f"Part {shard_num}", '\n\n'.join(current_shard)))
        
        return shards if shards else [("", content)]
    
    def _shard_by_semantic_boundaries(self, content: str) -> List[Tuple[str, str]]:
        """Shard document by semantic boundaries (sentences and paragraphs)."""
        # Simple semantic sharding based on sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        shards = []
        current_shard = []
        current_size = 0
        shard_num = 1
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_shard_size and current_shard:
                shards.append((f"Part {shard_num}", ' '.join(current_shard)))
                current_shard = [sentence]
                current_size = sentence_size
                shard_num += 1
            else:
                current_shard.append(sentence)
                current_size += sentence_size
        
        if current_shard:
            shards.append((f"Part {shard_num}", ' '.join(current_shard)))
        
        return shards if shards else [("", content)]
    
    def _extract_references(self, content: str) -> Set[str]:
        """Extract references to other documents or sections."""
        references = set()
        
        # Extract markdown links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        for match in link_pattern.finditer(content):
            references.add(match.group(2))
        
        # Extract references to other shards (format: @shard:id)
        shard_ref_pattern = re.compile(r'@shard:([a-f0-9-]+)')
        for match in shard_ref_pattern.finditer(content):
            references.add(match.group(1))
        
        return references
    
    def _build_relationships(self, shards: List[DocumentShard]) -> Dict[str, List[str]]:
        """Build relationships between shards."""
        relationships = {}
        
        for i, shard in enumerate(shards):
            shard_relations = []
            
            # Previous/next relationships
            if i > 0:
                shard_relations.append(shards[i-1].id)
            if i < len(shards) - 1:
                shard_relations.append(shards[i+1].id)
            
            # Reference relationships
            for ref in shard.references:
                if ref in self.shards:
                    shard_relations.append(ref)
            
            if shard_relations:
                relationships[shard.id] = shard_relations
        
        return relationships
    
    def get_shard(self, shard_id: str) -> Optional[DocumentShard]:
        """Retrieve a specific shard by ID."""
        return self.shards.get(shard_id)
    
    def get_shards_by_document(self, document_id: str) -> List[DocumentShard]:
        """Get all shards for a document."""
        shards = []
        for shard in self.shards.values():
            if shard.parent_id == document_id:
                shards.append(shard)
        return sorted(shards, key=lambda s: s.index)
    
    def get_index(self, document_id: str) -> Optional[ShardIndex]:
        """Get the index for a document."""
        return self.indices.get(document_id)
    
    def reassemble_document(self, document_id: str) -> Optional[str]:
        """Reassemble a sharded document."""
        shards = self.get_shards_by_document(document_id)
        if not shards:
            return None
        
        return '\n'.join(shard.content for shard in shards)
    
    def search_shards(self, query: str, document_id: Optional[str] = None) -> List[DocumentShard]:
        """Search for shards containing the query string."""
        results = []
        query_lower = query.lower()
        
        for shard in self.shards.values():
            if document_id and shard.parent_id != document_id:
                continue
            
            if query_lower in shard.content.lower() or query_lower in shard.title.lower():
                results.append(shard)
        
        return results
    
    def export_shards(self, document_id: str, output_dir: Path) -> List[Path]:
        """Export shards to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        index = self.get_index(document_id)
        if not index:
            return []
        
        exported_files = []
        
        # Export index
        index_file = output_dir / f"{document_id}_index.json"
        with open(index_file, 'w') as f:
            json.dump(index.to_dict(), f, indent=2)
        exported_files.append(index_file)
        
        # Export shards
        shards = self.get_shards_by_document(document_id)
        for shard in shards:
            shard_file = output_dir / f"{document_id}_shard_{shard.index:03d}.json"
            with open(shard_file, 'w') as f:
                json.dump(shard.to_dict(), f, indent=2)
            exported_files.append(shard_file)
        
        return exported_files
    
    def import_shards(self, index_file: Path) -> Tuple[List[DocumentShard], ShardIndex]:
        """Import shards from files."""
        index_file = Path(index_file)
        
        # Load index
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        index = ShardIndex.from_dict(index_data)
        
        # Load shards
        shards = []
        shard_dir = index_file.parent
        
        for shard_info in index.shards:
            shard_file = shard_dir / f"{index.document_id}_shard_{shard_info['index']:03d}.json"
            if shard_file.exists():
                with open(shard_file, 'r') as f:
                    shard_data = json.load(f)
                shard = DocumentShard.from_dict(shard_data)
                shards.append(shard)
                self.shards[shard.id] = shard
        
        self.indices[index.document_id] = index
        
        return shards, index
    
    def get_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get statistics for a sharded document."""
        index = self.get_index(document_id)
        if not index:
            return {}
        
        shards = self.get_shards_by_document(document_id)
        
        total_size = sum(s.size_bytes for s in shards)
        total_lines = sum(s.line_count for s in shards)
        total_words = sum(s.word_count for s in shards)
        
        return {
            'document_id': document_id,
            'title': index.title,
            'total_shards': len(shards),
            'total_size_bytes': total_size,
            'total_lines': total_lines,
            'total_words': total_words,
            'average_shard_size': total_size // len(shards) if shards else 0,
            'average_lines_per_shard': total_lines // len(shards) if shards else 0,
            'average_words_per_shard': total_words // len(shards) if shards else 0,
            'format': index.format.value,
            'created_at': index.created_at.isoformat()
        }


class MarkdownShardProcessor:
    """Specialized processor for markdown documents."""
    
    @staticmethod
    def extract_toc(shards: List[DocumentShard]) -> str:
        """Extract table of contents from shards."""
        toc_lines = ["# Table of Contents\n"]
        
        for shard in shards:
            # Extract headers from shard
            header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
            for match in header_pattern.finditer(shard.content):
                level = len(match.group(1))
                title = match.group(2)
                indent = "  " * (level - 1)
                toc_lines.append(f"{indent}- [{title}](@shard:{shard.id})")
        
        return '\n'.join(toc_lines)
    
    @staticmethod
    def create_navigation_links(shards: List[DocumentShard]) -> Dict[str, str]:
        """Create navigation links for each shard."""
        nav_links = {}
        
        for i, shard in enumerate(shards):
            links = []
            
            if i > 0:
                links.append(f"[← Previous](@shard:{shards[i-1].id})")
            
            links.append(f"[Index](@index)")
            
            if i < len(shards) - 1:
                links.append(f"[Next →](@shard:{shards[i+1].id})")
            
            nav_links[shard.id] = " | ".join(links)
        
        return nav_links


class YAMLShardProcessor:
    """Specialized processor for YAML documents."""
    
    @staticmethod
    def shard_by_keys(content: str, max_size: int = 50000) -> List[Tuple[str, str]]:
        """Shard YAML document by top-level keys."""
        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return [("", content)]
            
            shards = []
            current_shard = {}
            current_size = 0
            shard_num = 1
            
            for key, value in data.items():
                item_yaml = yaml.dump({key: value}, default_flow_style=False)
                item_size = len(item_yaml)
                
                if current_size + item_size > max_size and current_shard:
                    shard_yaml = yaml.dump(current_shard, default_flow_style=False)
                    shards.append((f"Part {shard_num}", shard_yaml))
                    current_shard = {key: value}
                    current_size = item_size
                    shard_num += 1
                else:
                    current_shard[key] = value
                    current_size += item_size
            
            if current_shard:
                shard_yaml = yaml.dump(current_shard, default_flow_style=False)
                shards.append((f"Part {shard_num}", shard_yaml))
            
            return shards
            
        except yaml.YAMLError:
            return [("", content)]


class JSONShardProcessor:
    """Specialized processor for JSON documents."""
    
    @staticmethod
    def shard_by_keys(content: str, max_size: int = 50000) -> List[Tuple[str, str]]:
        """Shard JSON document by top-level keys."""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return [("", content)]
            
            shards = []
            current_shard = {}
            current_size = 0
            shard_num = 1
            
            for key, value in data.items():
                item_json = json.dumps({key: value}, indent=2)
                item_size = len(item_json)
                
                if current_size + item_size > max_size and current_shard:
                    shard_json = json.dumps(current_shard, indent=2)
                    shards.append((f"Part {shard_num}", shard_json))
                    current_shard = {key: value}
                    current_size = item_size
                    shard_num += 1
                else:
                    current_shard[key] = value
                    current_size += item_size
            
            if current_shard:
                shard_json = json.dumps(current_shard, indent=2)
                shards.append((f"Part {shard_num}", shard_json))
            
            return shards
            
        except json.JSONDecodeError:
            return [("", content)]