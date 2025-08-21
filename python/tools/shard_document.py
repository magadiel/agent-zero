"""
Document Sharding Tool for Agent-Zero.

This tool provides document sharding capabilities to agents,
enabling them to handle large documents by splitting them into manageable pieces.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from python.helpers.document_sharding import (
    DocumentShardingSystem,
    ShardingStrategy,
    DocumentFormat,
    MarkdownShardProcessor,
    YAMLShardProcessor,
    JSONShardProcessor
)
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


class ShardDocument(Tool):
    """
    Tool for sharding large documents into smaller, manageable pieces.
    
    This tool integrates with the document handoff system to enable
    efficient processing of large documents by splitting them into shards
    while maintaining relationships and navigation.
    """
    
    def __init__(self, agent):
        """Initialize the document sharding tool."""
        super().__init__(
            name="shard_document",
            description="""Shard large documents into smaller pieces.
            
            This tool splits large documents into manageable shards while:
            - Maintaining document structure and relationships
            - Creating navigation indices
            - Preserving cross-references
            - Enabling efficient retrieval
            
            Parameters:
            - action: The action to perform (shard, get_shard, reassemble, search, export, import, stats)
            - content: Document content to shard (for 'shard' action)
            - title: Document title
            - strategy: Sharding strategy (section_based, size_based, paragraph, semantic)
            - format: Document format (markdown, yaml, json, text)
            - document_id: ID of the document (for retrieval actions)
            - shard_id: ID of a specific shard (for 'get_shard' action)
            - query: Search query (for 'search' action)
            - output_dir: Output directory (for 'export' action)
            - index_file: Index file path (for 'import' action)
            - max_size: Maximum shard size in characters (default: 50000)
            - max_lines: Maximum lines per shard (default: 1000)
            """,
            agent=agent,
            parameters={
                "action": {
                    "type": "string",
                    "required": True,
                    "enum": ["shard", "get_shard", "reassemble", "search", "export", "import", "stats", "get_toc"]
                },
                "content": {"type": "string", "required": False},
                "title": {"type": "string", "required": False},
                "strategy": {
                    "type": "string",
                    "required": False,
                    "enum": ["section_based", "size_based", "paragraph", "semantic"]
                },
                "format": {
                    "type": "string",
                    "required": False,
                    "enum": ["markdown", "yaml", "json", "text"]
                },
                "document_id": {"type": "string", "required": False},
                "shard_id": {"type": "string", "required": False},
                "query": {"type": "string", "required": False},
                "output_dir": {"type": "string", "required": False},
                "index_file": {"type": "string", "required": False},
                "max_size": {"type": "integer", "required": False},
                "max_lines": {"type": "integer", "required": False},
                "metadata": {"type": "object", "required": False}
            }
        )
        
        # Initialize sharding system
        self.sharding_system = DocumentShardingSystem()
        
        # Store for document management integration
        self.document_registry = {}
    
    def execute(self, **kwargs) -> Response:
        """Execute the document sharding tool."""
        action = kwargs.get('action')
        
        try:
            if action == 'shard':
                return self._shard_document(**kwargs)
            elif action == 'get_shard':
                return self._get_shard(**kwargs)
            elif action == 'reassemble':
                return self._reassemble_document(**kwargs)
            elif action == 'search':
                return self._search_shards(**kwargs)
            elif action == 'export':
                return self._export_shards(**kwargs)
            elif action == 'import':
                return self._import_shards(**kwargs)
            elif action == 'stats':
                return self._get_statistics(**kwargs)
            elif action == 'get_toc':
                return self._get_table_of_contents(**kwargs)
            else:
                return Response(
                    success=False,
                    message=f"Unknown action: {action}",
                    data={}
                )
        except Exception as e:
            return Response(
                success=False,
                message=f"Error executing document sharding: {str(e)}",
                data={}
            )
    
    def _shard_document(self, **kwargs) -> Response:
        """Shard a document into smaller pieces."""
        content = kwargs.get('content')
        if not content:
            return Response(
                success=False,
                message="No content provided to shard",
                data={}
            )
        
        title = kwargs.get('title', 'Untitled Document')
        strategy = kwargs.get('strategy', 'section_based')
        format_str = kwargs.get('format', 'markdown')
        metadata = kwargs.get('metadata', {})
        
        # Configure sharding system
        if kwargs.get('max_size'):
            self.sharding_system.max_shard_size = kwargs['max_size']
        if kwargs.get('max_lines'):
            self.sharding_system.max_shard_lines = kwargs['max_lines']
        
        # Map string values to enums
        try:
            strategy_enum = ShardingStrategy[strategy.upper()]
            format_enum = DocumentFormat[format_str.upper()]
        except KeyError as e:
            return Response(
                success=False,
                message=f"Invalid parameter: {str(e)}",
                data={}
            )
        
        # Special handling for structured formats
        if format_enum == DocumentFormat.YAML:
            processor = YAMLShardProcessor()
            shard_contents = processor.shard_by_keys(content, self.sharding_system.max_shard_size)
            shards = []
            document_id = str(self.sharding_system.__hash__())
            
            for i, (shard_title, shard_content) in enumerate(shard_contents):
                from python.helpers.document_sharding import DocumentShard
                shard = DocumentShard(
                    parent_id=document_id,
                    index=i,
                    title=shard_title or f"{title} - Part {i+1}",
                    content=shard_content,
                    format=format_enum,
                    metadata=metadata
                )
                shards.append(shard)
                self.sharding_system.shards[shard.id] = shard
            
            # Create index manually
            from python.helpers.document_sharding import ShardIndex
            index = ShardIndex(
                document_id=document_id,
                title=title,
                total_shards=len(shards),
                format=format_enum,
                metadata=metadata
            )
            for shard in shards:
                index.add_shard(shard)
            
            self.sharding_system.indices[document_id] = index
            
        elif format_enum == DocumentFormat.JSON:
            processor = JSONShardProcessor()
            shard_contents = processor.shard_by_keys(content, self.sharding_system.max_shard_size)
            shards = []
            document_id = str(self.sharding_system.__hash__())
            
            for i, (shard_title, shard_content) in enumerate(shard_contents):
                from python.helpers.document_sharding import DocumentShard
                shard = DocumentShard(
                    parent_id=document_id,
                    index=i,
                    title=shard_title or f"{title} - Part {i+1}",
                    content=shard_content,
                    format=format_enum,
                    metadata=metadata
                )
                shards.append(shard)
                self.sharding_system.shards[shard.id] = shard
            
            # Create index manually
            from python.helpers.document_sharding import ShardIndex
            index = ShardIndex(
                document_id=document_id,
                title=title,
                total_shards=len(shards),
                format=format_enum,
                metadata=metadata
            )
            for shard in shards:
                index.add_shard(shard)
            
            self.sharding_system.indices[document_id] = index
            
        else:
            # Use standard sharding
            shards, index = self.sharding_system.shard_document(
                content=content,
                title=title,
                strategy=strategy_enum,
                format=format_enum,
                metadata=metadata
            )
        
        # Store in registry for integration
        self.document_registry[index.document_id] = {
            'title': title,
            'shards': len(shards),
            'format': format_enum.value
        }
        
        # Create response
        shard_info = []
        for shard in shards:
            shard_info.append({
                'id': shard.id,
                'index': shard.index,
                'title': shard.title,
                'size_bytes': shard.size_bytes,
                'line_count': shard.line_count,
                'word_count': shard.word_count
            })
        
        response_data = {
            'document_id': index.document_id,
            'title': title,
            'total_shards': len(shards),
            'shards': shard_info,
            'format': format_enum.value,
            'strategy': strategy_enum.value
        }
        
        # Add navigation for markdown
        if format_enum == DocumentFormat.MARKDOWN:
            processor = MarkdownShardProcessor()
            nav_links = processor.create_navigation_links(shards)
            response_data['navigation'] = nav_links
        
        PrintStyle().print(f"Successfully sharded document '{title}' into {len(shards)} pieces")
        
        return Response(
            success=True,
            message=f"Document sharded into {len(shards)} pieces",
            data=response_data
        )
    
    def _get_shard(self, **kwargs) -> Response:
        """Get a specific shard by ID."""
        shard_id = kwargs.get('shard_id')
        if not shard_id:
            return Response(
                success=False,
                message="No shard_id provided",
                data={}
            )
        
        shard = self.sharding_system.get_shard(shard_id)
        if not shard:
            return Response(
                success=False,
                message=f"Shard not found: {shard_id}",
                data={}
            )
        
        return Response(
            success=True,
            message=f"Retrieved shard: {shard.title}",
            data={
                'id': shard.id,
                'title': shard.title,
                'content': shard.content,
                'index': shard.index,
                'parent_id': shard.parent_id,
                'size_bytes': shard.size_bytes,
                'references': list(shard.references)
            }
        )
    
    def _reassemble_document(self, **kwargs) -> Response:
        """Reassemble a sharded document."""
        document_id = kwargs.get('document_id')
        if not document_id:
            return Response(
                success=False,
                message="No document_id provided",
                data={}
            )
        
        content = self.sharding_system.reassemble_document(document_id)
        if content is None:
            return Response(
                success=False,
                message=f"Document not found: {document_id}",
                data={}
            )
        
        index = self.sharding_system.get_index(document_id)
        
        return Response(
            success=True,
            message=f"Reassembled document: {index.title}",
            data={
                'document_id': document_id,
                'title': index.title,
                'content': content,
                'total_shards': index.total_shards
            }
        )
    
    def _search_shards(self, **kwargs) -> Response:
        """Search for shards containing a query."""
        query = kwargs.get('query')
        if not query:
            return Response(
                success=False,
                message="No search query provided",
                data={}
            )
        
        document_id = kwargs.get('document_id')  # Optional filter
        
        results = self.sharding_system.search_shards(query, document_id)
        
        shard_results = []
        for shard in results:
            # Extract snippet around the match
            content_lower = shard.content.lower()
            query_lower = query.lower()
            pos = content_lower.find(query_lower)
            
            snippet = ""
            if pos != -1:
                start = max(0, pos - 100)
                end = min(len(shard.content), pos + len(query) + 100)
                snippet = shard.content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(shard.content):
                    snippet = snippet + "..."
            
            shard_results.append({
                'shard_id': shard.id,
                'document_id': shard.parent_id,
                'title': shard.title,
                'snippet': snippet,
                'index': shard.index
            })
        
        return Response(
            success=True,
            message=f"Found {len(results)} shards matching '{query}'",
            data={
                'query': query,
                'results': shard_results,
                'total_matches': len(results)
            }
        )
    
    def _export_shards(self, **kwargs) -> Response:
        """Export shards to files."""
        document_id = kwargs.get('document_id')
        if not document_id:
            return Response(
                success=False,
                message="No document_id provided",
                data={}
            )
        
        output_dir = kwargs.get('output_dir', './exported_shards')
        output_path = Path(output_dir)
        
        try:
            exported_files = self.sharding_system.export_shards(document_id, output_path)
            
            if not exported_files:
                return Response(
                    success=False,
                    message=f"No shards found for document: {document_id}",
                    data={}
                )
            
            return Response(
                success=True,
                message=f"Exported {len(exported_files)} files",
                data={
                    'document_id': document_id,
                    'output_dir': str(output_path),
                    'files': [str(f) for f in exported_files],
                    'total_files': len(exported_files)
                }
            )
        except Exception as e:
            return Response(
                success=False,
                message=f"Export failed: {str(e)}",
                data={}
            )
    
    def _import_shards(self, **kwargs) -> Response:
        """Import shards from files."""
        index_file = kwargs.get('index_file')
        if not index_file:
            return Response(
                success=False,
                message="No index_file provided",
                data={}
            )
        
        index_path = Path(index_file)
        if not index_path.exists():
            return Response(
                success=False,
                message=f"Index file not found: {index_file}",
                data={}
            )
        
        try:
            shards, index = self.sharding_system.import_shards(index_path)
            
            # Update registry
            self.document_registry[index.document_id] = {
                'title': index.title,
                'shards': len(shards),
                'format': index.format.value
            }
            
            return Response(
                success=True,
                message=f"Imported document '{index.title}' with {len(shards)} shards",
                data={
                    'document_id': index.document_id,
                    'title': index.title,
                    'total_shards': len(shards),
                    'format': index.format.value
                }
            )
        except Exception as e:
            return Response(
                success=False,
                message=f"Import failed: {str(e)}",
                data={}
            )
    
    def _get_statistics(self, **kwargs) -> Response:
        """Get statistics for a sharded document."""
        document_id = kwargs.get('document_id')
        if not document_id:
            return Response(
                success=False,
                message="No document_id provided",
                data={}
            )
        
        stats = self.sharding_system.get_statistics(document_id)
        
        if not stats:
            return Response(
                success=False,
                message=f"Document not found: {document_id}",
                data={}
            )
        
        return Response(
            success=True,
            message=f"Statistics for document: {stats['title']}",
            data=stats
        )
    
    def _get_table_of_contents(self, **kwargs) -> Response:
        """Get table of contents for a sharded document."""
        document_id = kwargs.get('document_id')
        if not document_id:
            return Response(
                success=False,
                message="No document_id provided",
                data={}
            )
        
        index = self.sharding_system.get_index(document_id)
        if not index:
            return Response(
                success=False,
                message=f"Document not found: {document_id}",
                data={}
            )
        
        shards = self.sharding_system.get_shards_by_document(document_id)
        
        if index.format == DocumentFormat.MARKDOWN:
            processor = MarkdownShardProcessor()
            toc = processor.extract_toc(shards)
            
            return Response(
                success=True,
                message=f"Generated table of contents for: {index.title}",
                data={
                    'document_id': document_id,
                    'title': index.title,
                    'table_of_contents': toc,
                    'format': 'markdown'
                }
            )
        else:
            # Simple TOC for non-markdown documents
            toc_lines = [f"# {index.title} - Table of Contents\n"]
            for shard in shards:
                toc_lines.append(f"{shard.index + 1}. {shard.title} (ID: {shard.id})")
            
            return Response(
                success=True,
                message=f"Generated table of contents for: {index.title}",
                data={
                    'document_id': document_id,
                    'title': index.title,
                    'table_of_contents': '\n'.join(toc_lines),
                    'format': 'text'
                }
            )
    
    def integrate_with_document_handoff(self, document_manager):
        """
        Integrate with the document handoff system.
        
        This allows automatic sharding of large documents during handoff.
        """
        # Hook into document creation
        original_create = document_manager.create_document
        
        def create_with_sharding(title, content, owner, doc_type='general', metadata=None):
            # Check if document is large enough to require sharding
            if len(content) > self.sharding_system.max_shard_size:
                # Shard the document
                response = self._shard_document(
                    content=content,
                    title=title,
                    metadata=metadata
                )
                
                if response.success:
                    # Store sharding info in metadata
                    if metadata is None:
                        metadata = {}
                    metadata['sharded'] = True
                    metadata['shard_info'] = response.data
                    
                    # Create a summary document with shard references
                    summary_content = f"# {title}\n\n"
                    summary_content += f"This document has been sharded into {response.data['total_shards']} pieces.\n\n"
                    summary_content += "## Shards\n"
                    for shard in response.data['shards']:
                        summary_content += f"- [{shard['title']}](@shard:{shard['id']})\n"
                    
                    # Create the document with summary
                    return original_create(title, summary_content, owner, doc_type, metadata)
            
            # Normal document creation for small documents
            return original_create(title, content, owner, doc_type, metadata)
        
        document_manager.create_document = create_with_sharding
        
        PrintStyle().print("Document sharding integrated with handoff system")


# Register the tool
def get_tool_class():
    """Return the tool class for Agent-Zero."""
    return ShardDocument