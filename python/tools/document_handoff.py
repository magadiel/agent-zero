"""
Document Handoff Tool for Agent-Zero
Enables agents to manage document creation, updates, and handoffs within workflows.
"""

import asyncio
from typing import Any, Optional, Dict, List
from pathlib import Path
import sys
import json

# Add coordination directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "coordination"))

from coordination.document_manager import (
    DocumentRegistry, Document, DocumentMetadata,
    DocumentType, DocumentStatus, AccessLevel,
    get_document_registry
)
from coordination.handoff_protocol import (
    HandoffProtocol, HandoffRequest, HandoffNotification,
    HandoffStatus, HandoffPriority, get_handoff_protocol
)

from python.helpers import files
from python.helpers.tool import Tool, Response


class DocumentHandoffTool(Tool):
    """
    Tool for managing documents and handoffs between agents.
    
    This tool provides comprehensive document management capabilities including:
    - Creating and updating documents
    - Managing document versions
    - Handling document handoffs between agents
    - Access control and permissions
    - Workflow document tracking
    """
    
    def __init__(self, agent: Any):
        super().__init__(
            name="document_handoff",
            description="Manage documents and handoffs between agents",
            agent=agent
        )
        
        # Initialize registries
        storage_base = Path("./storage")
        self.document_registry = get_document_registry(str(storage_base / "documents"))
        self.handoff_protocol = get_handoff_protocol(str(storage_base / "handoffs"))
        
        # Register notification handler for this agent
        if hasattr(agent, 'id'):
            self.agent_id = agent.id
        else:
            self.agent_id = "agent_" + str(id(agent))
            
        self.handoff_protocol.register_notification_handler(
            self.agent_id,
            self._handle_notification
        )
        
        self.notifications = []
    
    async def execute(self, **kwargs) -> Response:
        """
        Execute document handoff operations.
        
        Operations:
        - create_document: Create a new document
        - update_document: Update an existing document
        - get_document: Retrieve a document
        - search_documents: Search for documents
        - create_handoff: Create a document handoff
        - accept_handoff: Accept a handoff
        - reject_handoff: Reject a handoff
        - complete_handoff: Complete a handoff
        - get_my_handoffs: Get agent's handoff queue
        - get_workflow_documents: Get documents for a workflow
        - check_access: Check document access permissions
        - grant_access: Grant access to a document
        - add_dependency: Add document dependency
        """
        operation = kwargs.get('operation', '').lower()
        
        try:
            if operation == 'create_document':
                return await self._create_document(**kwargs)
            elif operation == 'update_document':
                return await self._update_document(**kwargs)
            elif operation == 'get_document':
                return await self._get_document(**kwargs)
            elif operation == 'search_documents':
                return await self._search_documents(**kwargs)
            elif operation == 'create_handoff':
                return await self._create_handoff(**kwargs)
            elif operation == 'accept_handoff':
                return await self._accept_handoff(**kwargs)
            elif operation == 'reject_handoff':
                return await self._reject_handoff(**kwargs)
            elif operation == 'complete_handoff':
                return await self._complete_handoff(**kwargs)
            elif operation == 'get_my_handoffs':
                return await self._get_my_handoffs(**kwargs)
            elif operation == 'get_workflow_documents':
                return await self._get_workflow_documents(**kwargs)
            elif operation == 'check_access':
                return await self._check_access(**kwargs)
            elif operation == 'grant_access':
                return await self._grant_access(**kwargs)
            elif operation == 'add_dependency':
                return await self._add_dependency(**kwargs)
            elif operation == 'get_notifications':
                return await self._get_notifications()
            elif operation == 'get_statistics':
                return await self._get_statistics()
            else:
                return Response(
                    message=f"Unknown operation: {operation}",
                    success=False,
                    data={
                        "available_operations": [
                            "create_document", "update_document", "get_document",
                            "search_documents", "create_handoff", "accept_handoff",
                            "reject_handoff", "complete_handoff", "get_my_handoffs",
                            "get_workflow_documents", "check_access", "grant_access",
                            "add_dependency", "get_notifications", "get_statistics"
                        ]
                    }
                )
        except Exception as e:
            return Response(
                message=f"Error executing {operation}: {str(e)}",
                success=False,
                data={"error": str(e)}
            )
    
    async def _create_document(self, **kwargs) -> Response:
        """Create a new document"""
        content = kwargs.get('content', '')
        title = kwargs.get('title', 'Untitled')
        doc_type = kwargs.get('doc_type', 'OTHER')
        workflow_id = kwargs.get('workflow_id')
        team_id = kwargs.get('team_id')
        tags = kwargs.get('tags', [])
        
        # Convert string doc_type to enum
        try:
            doc_type_enum = DocumentType[doc_type.upper()]
        except KeyError:
            doc_type_enum = DocumentType.OTHER
        
        # Create document
        document = await self.document_registry.create_document(
            content=content,
            title=title,
            doc_type=doc_type_enum,
            created_by=self.agent_id,
            workflow_id=workflow_id,
            team_id=team_id,
            tags=tags
        )
        
        return Response(
            message=f"Document created: {document.metadata.title}",
            success=True,
            data={
                "document_id": document.metadata.id,
                "title": document.metadata.title,
                "type": document.metadata.type.value,
                "status": document.metadata.status.value,
                "created_at": document.metadata.created_at.isoformat()
            }
        )
    
    async def _update_document(self, **kwargs) -> Response:
        """Update an existing document"""
        doc_id = kwargs.get('document_id')
        content = kwargs.get('content')
        create_version = kwargs.get('create_version', True)
        
        if not doc_id or content is None:
            return Response(
                message="document_id and content are required",
                success=False
            )
        
        # Update document
        document = await self.document_registry.update_document(
            doc_id=doc_id,
            content=content,
            modified_by=self.agent_id,
            create_version=create_version
        )
        
        if document:
            return Response(
                message=f"Document updated: {document.metadata.title}",
                success=True,
                data={
                    "document_id": document.metadata.id,
                    "title": document.metadata.title,
                    "version": document.metadata.version,
                    "modified_at": document.metadata.modified_at.isoformat()
                }
            )
        else:
            return Response(
                message=f"Document {doc_id} not found",
                success=False
            )
    
    async def _get_document(self, **kwargs) -> Response:
        """Retrieve a document"""
        doc_id = kwargs.get('document_id')
        export_format = kwargs.get('format', 'json')
        
        if not doc_id:
            return Response(
                message="document_id is required",
                success=False
            )
        
        # Check access
        has_access = await self.document_registry.check_access(
            doc_id, self.agent_id, AccessLevel.READ
        )
        
        if not has_access:
            # Check if document exists
            document = await self.document_registry.get_document(doc_id)
            if document and document.metadata.owner != self.agent_id:
                return Response(
                    message=f"Access denied to document {doc_id}",
                    success=False
                )
        
        # Get document
        document = await self.document_registry.get_document(doc_id)
        
        if document:
            # Export in requested format
            exported = await self.document_registry.export_document(
                doc_id, format=export_format
            )
            
            return Response(
                message=f"Document retrieved: {document.metadata.title}",
                success=True,
                data={
                    "document_id": document.metadata.id,
                    "title": document.metadata.title,
                    "type": document.metadata.type.value,
                    "status": document.metadata.status.value,
                    "version": document.metadata.version,
                    "content": document.content if export_format == 'raw' else exported,
                    "metadata": document.metadata.to_dict()
                }
            )
        else:
            return Response(
                message=f"Document {doc_id} not found",
                success=False
            )
    
    async def _search_documents(self, **kwargs) -> Response:
        """Search for documents"""
        doc_type = kwargs.get('doc_type')
        status = kwargs.get('status')
        workflow_id = kwargs.get('workflow_id')
        team_id = kwargs.get('team_id')
        tags = kwargs.get('tags')
        created_by = kwargs.get('created_by')
        
        # Convert string types to enums
        if doc_type:
            try:
                doc_type = DocumentType[doc_type.upper()]
            except KeyError:
                doc_type = None
        
        if status:
            try:
                status = DocumentStatus[status.upper()]
            except KeyError:
                status = None
        
        # Search documents
        documents = await self.document_registry.search_documents(
            doc_type=doc_type,
            status=status,
            workflow_id=workflow_id,
            team_id=team_id,
            tags=tags,
            created_by=created_by
        )
        
        # Filter by access permissions
        accessible_docs = []
        for doc in documents:
            if doc.metadata.owner == self.agent_id:
                accessible_docs.append(doc)
            elif await self.document_registry.check_access(
                doc.metadata.id, self.agent_id, AccessLevel.READ
            ):
                accessible_docs.append(doc)
        
        return Response(
            message=f"Found {len(accessible_docs)} documents",
            success=True,
            data={
                "documents": [
                    {
                        "document_id": doc.metadata.id,
                        "title": doc.metadata.title,
                        "type": doc.metadata.type.value,
                        "status": doc.metadata.status.value,
                        "created_by": doc.metadata.created_by,
                        "created_at": doc.metadata.created_at.isoformat()
                    }
                    for doc in accessible_docs
                ]
            }
        )
    
    async def _create_handoff(self, **kwargs) -> Response:
        """Create a document handoff"""
        document_id = kwargs.get('document_id')
        to_agent = kwargs.get('to_agent')
        reason = kwargs.get('reason', 'Please review')
        instructions = kwargs.get('instructions', '')
        expected_action = kwargs.get('expected_action', 'review')
        priority = kwargs.get('priority', 'MEDIUM')
        workflow_id = kwargs.get('workflow_id')
        team_id = kwargs.get('team_id')
        requires_validation = kwargs.get('requires_validation', True)
        validation_checklist = kwargs.get('validation_checklist')
        
        if not document_id or not to_agent:
            return Response(
                message="document_id and to_agent are required",
                success=False
            )
        
        # Convert priority to enum
        try:
            priority_enum = HandoffPriority[priority.upper()]
        except KeyError:
            priority_enum = HandoffPriority.MEDIUM
        
        # Create handoff
        try:
            handoff = await self.handoff_protocol.create_handoff(
                document_id=document_id,
                from_agent=self.agent_id,
                to_agent=to_agent,
                reason=reason,
                instructions=instructions,
                expected_action=expected_action,
                priority=priority_enum,
                workflow_id=workflow_id,
                team_id=team_id,
                requires_validation=requires_validation,
                validation_checklist=validation_checklist
            )
            
            return Response(
                message=f"Handoff created to {to_agent}",
                success=True,
                data={
                    "handoff_id": handoff.id,
                    "document_id": handoff.document_id,
                    "to_agent": handoff.to_agent,
                    "status": handoff.status.value,
                    "priority": handoff.priority.value,
                    "created_at": handoff.created_at.isoformat()
                }
            )
        except (ValueError, PermissionError) as e:
            return Response(
                message=str(e),
                success=False
            )
    
    async def _accept_handoff(self, **kwargs) -> Response:
        """Accept a handoff"""
        handoff_id = kwargs.get('handoff_id')
        response = kwargs.get('response', '')
        
        if not handoff_id:
            return Response(
                message="handoff_id is required",
                success=False
            )
        
        # Accept handoff
        accepted = await self.handoff_protocol.accept_handoff(
            handoff_id=handoff_id,
            agent_id=self.agent_id,
            response=response
        )
        
        if accepted:
            return Response(
                message="Handoff accepted",
                success=True,
                data={"handoff_id": handoff_id}
            )
        else:
            return Response(
                message="Failed to accept handoff",
                success=False
            )
    
    async def _reject_handoff(self, **kwargs) -> Response:
        """Reject a handoff"""
        handoff_id = kwargs.get('handoff_id')
        reason = kwargs.get('reason', 'Unable to process')
        
        if not handoff_id:
            return Response(
                message="handoff_id is required",
                success=False
            )
        
        # Reject handoff
        rejected = await self.handoff_protocol.reject_handoff(
            handoff_id=handoff_id,
            agent_id=self.agent_id,
            reason=reason
        )
        
        if rejected:
            return Response(
                message="Handoff rejected",
                success=True,
                data={"handoff_id": handoff_id}
            )
        else:
            return Response(
                message="Failed to reject handoff",
                success=False
            )
    
    async def _complete_handoff(self, **kwargs) -> Response:
        """Complete a handoff"""
        handoff_id = kwargs.get('handoff_id')
        result_document_id = kwargs.get('result_document_id')
        validation_result = kwargs.get('validation_result')
        
        if not handoff_id:
            return Response(
                message="handoff_id is required",
                success=False
            )
        
        # Complete handoff
        completed = await self.handoff_protocol.complete_handoff(
            handoff_id=handoff_id,
            agent_id=self.agent_id,
            result_document_id=result_document_id,
            validation_result=validation_result
        )
        
        if completed:
            return Response(
                message="Handoff completed",
                success=True,
                data={
                    "handoff_id": handoff_id,
                    "result_document_id": result_document_id
                }
            )
        else:
            return Response(
                message="Failed to complete handoff",
                success=False
            )
    
    async def _get_my_handoffs(self, **kwargs) -> Response:
        """Get agent's handoff queue"""
        include_completed = kwargs.get('include_completed', False)
        
        # Get handoffs
        handoffs = await self.handoff_protocol.get_agent_queue(
            agent_id=self.agent_id,
            include_completed=include_completed
        )
        
        return Response(
            message=f"Found {len(handoffs)} handoffs",
            success=True,
            data={
                "handoffs": [
                    {
                        "handoff_id": h.id,
                        "document_id": h.document_id,
                        "from_agent": h.from_agent,
                        "to_agent": h.to_agent,
                        "reason": h.reason,
                        "status": h.status.value,
                        "priority": h.priority.value,
                        "created_at": h.created_at.isoformat(),
                        "deadline": h.deadline.isoformat() if h.deadline else None
                    }
                    for h in handoffs
                ]
            }
        )
    
    async def _get_workflow_documents(self, **kwargs) -> Response:
        """Get documents for a workflow"""
        workflow_id = kwargs.get('workflow_id')
        
        if not workflow_id:
            return Response(
                message="workflow_id is required",
                success=False
            )
        
        # Get documents
        documents = await self.document_registry.get_workflow_documents(workflow_id)
        
        # Filter by access permissions
        accessible_docs = []
        for doc in documents:
            if doc.metadata.owner == self.agent_id:
                accessible_docs.append(doc)
            elif await self.document_registry.check_access(
                doc.metadata.id, self.agent_id, AccessLevel.READ
            ):
                accessible_docs.append(doc)
        
        return Response(
            message=f"Found {len(accessible_docs)} workflow documents",
            success=True,
            data={
                "workflow_id": workflow_id,
                "documents": [
                    {
                        "document_id": doc.metadata.id,
                        "title": doc.metadata.title,
                        "type": doc.metadata.type.value,
                        "status": doc.metadata.status.value,
                        "version": doc.metadata.version
                    }
                    for doc in accessible_docs
                ]
            }
        )
    
    async def _check_access(self, **kwargs) -> Response:
        """Check document access permissions"""
        document_id = kwargs.get('document_id')
        access_level = kwargs.get('access_level', 'READ')
        
        if not document_id:
            return Response(
                message="document_id is required",
                success=False
            )
        
        # Convert access level to enum
        try:
            access_enum = AccessLevel[access_level.upper()]
        except KeyError:
            access_enum = AccessLevel.READ
        
        # Check access
        has_access = await self.document_registry.check_access(
            doc_id=document_id,
            user_id=self.agent_id,
            required_level=access_enum
        )
        
        return Response(
            message=f"Access check for document {document_id}",
            success=True,
            data={
                "document_id": document_id,
                "access_level": access_level,
                "has_access": has_access
            }
        )
    
    async def _grant_access(self, **kwargs) -> Response:
        """Grant access to a document"""
        document_id = kwargs.get('document_id')
        user_id = kwargs.get('user_id')
        access_level = kwargs.get('access_level', 'READ')
        
        if not document_id or not user_id:
            return Response(
                message="document_id and user_id are required",
                success=False
            )
        
        # Convert access level to enum
        try:
            access_enum = AccessLevel[access_level.upper()]
        except KeyError:
            access_enum = AccessLevel.READ
        
        # Grant access
        granted = await self.document_registry.grant_access(
            doc_id=document_id,
            user_id=user_id,
            access_level=access_enum,
            granter_id=self.agent_id
        )
        
        if granted:
            return Response(
                message=f"Access granted to {user_id}",
                success=True,
                data={
                    "document_id": document_id,
                    "user_id": user_id,
                    "access_level": access_level
                }
            )
        else:
            return Response(
                message="Failed to grant access (not owner)",
                success=False
            )
    
    async def _add_dependency(self, **kwargs) -> Response:
        """Add document dependency"""
        document_id = kwargs.get('document_id')
        dependency_id = kwargs.get('dependency_id')
        
        if not document_id or not dependency_id:
            return Response(
                message="document_id and dependency_id are required",
                success=False
            )
        
        # Add dependency
        added = await self.document_registry.add_dependency(
            doc_id=document_id,
            dependency_id=dependency_id
        )
        
        if added:
            return Response(
                message=f"Dependency added",
                success=True,
                data={
                    "document_id": document_id,
                    "dependency_id": dependency_id
                }
            )
        else:
            return Response(
                message="Failed to add dependency",
                success=False
            )
    
    async def _get_notifications(self) -> Response:
        """Get recent notifications"""
        return Response(
            message=f"Found {len(self.notifications)} notifications",
            success=True,
            data={
                "notifications": [
                    {
                        "handoff_id": n.handoff_id,
                        "event_type": n.event_type,
                        "message": n.message,
                        "timestamp": n.timestamp.isoformat(),
                        "metadata": n.metadata
                    }
                    for n in self.notifications[-10:]  # Last 10 notifications
                ]
            }
        )
    
    async def _get_statistics(self) -> Response:
        """Get document and handoff statistics"""
        doc_stats = await self.document_registry.get_statistics()
        handoff_stats = await self.handoff_protocol.get_statistics()
        
        return Response(
            message="Statistics retrieved",
            success=True,
            data={
                "documents": doc_stats,
                "handoffs": handoff_stats
            }
        )
    
    def _handle_notification(self, notification: HandoffNotification):
        """Handle incoming handoff notifications"""
        self.notifications.append(notification)
        
        # Log notification if agent has context
        if hasattr(self.agent, 'context'):
            self.agent.context.log.log(
                type="info",
                heading=f"Handoff Notification: {notification.event_type}",
                content=notification.message
            )