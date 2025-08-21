"""
BMAD Template System for Agent-Zero
Provides document template management with interactive elicitation,
role-based access control, and version tracking.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import asyncio
from copy import deepcopy


class AccessLevel(Enum):
    """Access levels for template sections"""
    OWNER = "owner"      # Can modify structure and content
    EDITOR = "editor"    # Can modify content only
    VIEWER = "viewer"    # Can only view
    NONE = "none"        # No access


class InteractionType(Enum):
    """Types of user interactions for template sections"""
    TEXT_INPUT = "text_input"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    BOOLEAN = "boolean"
    NUMBER = "number"
    DATE = "date"
    NONE = "none"


@dataclass
class TemplateSection:
    """Represents a section in a template"""
    id: str
    title: str
    description: str
    content: str = ""
    required: bool = True
    access_roles: Dict[str, AccessLevel] = field(default_factory=dict)
    interaction: InteractionType = InteractionType.NONE
    interaction_prompt: Optional[str] = None
    interaction_options: Optional[List[str]] = None
    validation_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['TemplateSection'] = field(default_factory=list)


@dataclass
class DocumentVersion:
    """Represents a version of a document"""
    version_id: str
    timestamp: datetime
    author: str
    changes: Dict[str, Any]
    previous_version: Optional[str] = None
    comment: str = ""
    hash: str = ""


@dataclass
class Document:
    """Represents a document created from a template"""
    id: str
    template_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    owner: str
    editors: List[str] = field(default_factory=list)
    sections: Dict[str, TemplateSection] = field(default_factory=dict)
    versions: List[DocumentVersion] = field(default_factory=list)
    current_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary"""
        def serialize_section(section):
            """Serialize a section, handling enums properly"""
            result = {
                'id': section.id,
                'title': section.title,
                'description': section.description,
                'content': section.content,
                'required': section.required,
                'access_roles': {k: v.value for k, v in section.access_roles.items()},
                'interaction': section.interaction.value,
                'interaction_prompt': section.interaction_prompt,
                'interaction_options': section.interaction_options,
                'validation_rules': section.validation_rules,
                'metadata': section.metadata,
                'children': [serialize_section(child) for child in section.children]
            }
            return result
            
        def serialize_version(version):
            """Serialize a version, handling datetime properly"""
            return {
                'version_id': version.version_id,
                'timestamp': version.timestamp.isoformat() if isinstance(version.timestamp, datetime) else version.timestamp,
                'author': version.author,
                'changes': version.changes,
                'previous_version': version.previous_version,
                'comment': version.comment,
                'hash': version.hash
            }
            
        return {
            'id': self.id,
            'template_id': self.template_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'owner': self.owner,
            'editors': self.editors,
            'sections': {k: serialize_section(v) for k, v in self.sections.items()},
            'versions': [serialize_version(v) for v in self.versions],
            'current_version': self.current_version,
            'metadata': self.metadata
        }


class Template:
    """Represents a document template"""
    
    def __init__(self, template_id: str, name: str, description: str):
        self.id = template_id
        self.name = name
        self.description = description
        self.sections: Dict[str, TemplateSection] = {}
        self.metadata: Dict[str, Any] = {}
        self.validation_rules: List[str] = []
        self.required_sections: List[str] = []
        
    def add_section(self, section: TemplateSection) -> None:
        """Add a section to the template"""
        self.sections[section.id] = section
        if section.required:
            self.required_sections.append(section.id)
            
    def remove_section(self, section_id: str) -> None:
        """Remove a section from the template"""
        if section_id in self.sections:
            del self.sections[section_id]
            if section_id in self.required_sections:
                self.required_sections.remove(section_id)
                
    def get_section(self, section_id: str) -> Optional[TemplateSection]:
        """Get a section by ID"""
        return self.sections.get(section_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sections': {k: asdict(v) for k, v in self.sections.items()},
            'metadata': self.metadata,
            'validation_rules': self.validation_rules,
            'required_sections': self.required_sections
        }


class TemplateParser:
    """Parses template definitions from YAML/JSON files"""
    
    @staticmethod
    def parse_yaml(file_path: Path) -> Template:
        """Parse a template from a YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return TemplateParser._parse_template_data(data)
    
    @staticmethod
    def parse_json(file_path: Path) -> Template:
        """Parse a template from a JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return TemplateParser._parse_template_data(data)
    
    @staticmethod
    def _parse_template_data(data: Dict[str, Any]) -> Template:
        """Parse template data from dictionary"""
        template = Template(
            template_id=data.get('id', 'unnamed'),
            name=data.get('name', 'Unnamed Template'),
            description=data.get('description', '')
        )
        
        # Parse metadata
        template.metadata = data.get('metadata', {})
        template.validation_rules = data.get('validation_rules', [])
        
        # Parse sections
        sections = data.get('sections', {})
        for section_id, section_data in sections.items():
            section = TemplateParser._parse_section(section_id, section_data)
            template.add_section(section)
            
        return template
    
    @staticmethod
    def _parse_section(section_id: str, data: Dict[str, Any]) -> TemplateSection:
        """Parse a section from dictionary"""
        # Parse interaction type
        interaction_str = data.get('interaction', {}).get('type', 'none')
        try:
            interaction = InteractionType(interaction_str)
        except ValueError:
            interaction = InteractionType.NONE
            
        # Parse access roles
        access_roles = {}
        for role, level_str in data.get('access_roles', {}).items():
            try:
                access_roles[role] = AccessLevel(level_str)
            except ValueError:
                access_roles[role] = AccessLevel.VIEWER
                
        section = TemplateSection(
            id=section_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            content=data.get('content', ''),
            required=data.get('required', True),
            access_roles=access_roles,
            interaction=interaction,
            interaction_prompt=data.get('interaction', {}).get('prompt'),
            interaction_options=data.get('interaction', {}).get('options'),
            validation_rules=data.get('validation_rules', []),
            metadata=data.get('metadata', {})
        )
        
        # Parse children recursively
        children = data.get('children', {})
        for child_id, child_data in children.items():
            child = TemplateParser._parse_section(child_id, child_data)
            section.children.append(child)
            
        return section


class InteractiveElicitation:
    """Handles interactive user input for template sections"""
    
    def __init__(self, user_interface=None):
        """Initialize with optional user interface"""
        self.user_interface = user_interface
        
    async def elicit_section(self, section: TemplateSection) -> str:
        """Elicit user input for a section"""
        if section.interaction == InteractionType.NONE:
            return section.content
            
        prompt = section.interaction_prompt or f"Please provide content for {section.title}:"
        
        if section.interaction == InteractionType.TEXT_INPUT:
            return await self._get_text_input(prompt)
        elif section.interaction == InteractionType.CHOICE:
            return await self._get_choice(prompt, section.interaction_options or [])
        elif section.interaction == InteractionType.MULTI_CHOICE:
            return await self._get_multi_choice(prompt, section.interaction_options or [])
        elif section.interaction == InteractionType.BOOLEAN:
            return await self._get_boolean(prompt)
        elif section.interaction == InteractionType.NUMBER:
            return await self._get_number(prompt)
        elif section.interaction == InteractionType.DATE:
            return await self._get_date(prompt)
        else:
            return section.content
            
    async def _get_text_input(self, prompt: str) -> str:
        """Get text input from user"""
        if self.user_interface:
            return await self.user_interface.get_text_input(prompt)
        # Fallback implementation
        return input(f"{prompt} ")
        
    async def _get_choice(self, prompt: str, options: List[str]) -> str:
        """Get single choice from user"""
        if self.user_interface:
            return await self.user_interface.get_choice(prompt, options)
        # Fallback implementation
        print(prompt)
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        while True:
            try:
                choice = int(input("Enter choice number: "))
                if 1 <= choice <= len(options):
                    return options[choice - 1]
            except ValueError:
                pass
            print("Invalid choice. Please try again.")
            
    async def _get_multi_choice(self, prompt: str, options: List[str]) -> str:
        """Get multiple choices from user"""
        if self.user_interface:
            return await self.user_interface.get_multi_choice(prompt, options)
        # Fallback implementation
        print(prompt)
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        choices = input("Enter choice numbers (comma-separated): ")
        selected = []
        for choice_str in choices.split(','):
            try:
                choice = int(choice_str.strip())
                if 1 <= choice <= len(options):
                    selected.append(options[choice - 1])
            except ValueError:
                pass
        return ', '.join(selected)
        
    async def _get_boolean(self, prompt: str) -> str:
        """Get boolean input from user"""
        if self.user_interface:
            return await self.user_interface.get_boolean(prompt)
        # Fallback implementation
        response = input(f"{prompt} (yes/no): ").lower()
        return "true" if response in ['yes', 'y', 'true', '1'] else "false"
        
    async def _get_number(self, prompt: str) -> str:
        """Get number input from user"""
        if self.user_interface:
            return await self.user_interface.get_number(prompt)
        # Fallback implementation
        while True:
            try:
                return str(float(input(f"{prompt} ")))
            except ValueError:
                print("Invalid number. Please try again.")
                
    async def _get_date(self, prompt: str) -> str:
        """Get date input from user"""
        if self.user_interface:
            return await self.user_interface.get_date(prompt)
        # Fallback implementation
        return input(f"{prompt} (YYYY-MM-DD): ")


class RoleBasedAccessControl:
    """Manages role-based access to template sections"""
    
    def __init__(self):
        self.user_roles: Dict[str, List[str]] = {}
        
    def set_user_roles(self, user: str, roles: List[str]) -> None:
        """Set roles for a user"""
        self.user_roles[user] = roles
        
    def add_user_role(self, user: str, role: str) -> None:
        """Add a role to a user"""
        if user not in self.user_roles:
            self.user_roles[user] = []
        if role not in self.user_roles[user]:
            self.user_roles[user].append(role)
            
    def remove_user_role(self, user: str, role: str) -> None:
        """Remove a role from a user"""
        if user in self.user_roles and role in self.user_roles[user]:
            self.user_roles[user].remove(role)
            
    def get_user_roles(self, user: str) -> List[str]:
        """Get roles for a user"""
        return self.user_roles.get(user, [])
        
    def can_access(self, user: str, section: TemplateSection, 
                   required_level: AccessLevel = AccessLevel.VIEWER) -> bool:
        """Check if user can access a section with required level"""
        user_roles = self.get_user_roles(user)
        
        # Check if user is owner
        if 'owner' in user_roles:
            return True
            
        # Check each user role against section access roles
        for role in user_roles:
            if role in section.access_roles:
                level = section.access_roles[role]
                if self._compare_access_levels(level, required_level):
                    return True
                    
        return False
        
    def _compare_access_levels(self, user_level: AccessLevel, 
                              required_level: AccessLevel) -> bool:
        """Compare access levels"""
        level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.VIEWER: 1,
            AccessLevel.EDITOR: 2,
            AccessLevel.OWNER: 3
        }
        return level_hierarchy.get(user_level, 0) >= level_hierarchy.get(required_level, 0)


class VersionControl:
    """Manages document versioning"""
    
    def __init__(self):
        self.versions: Dict[str, List[DocumentVersion]] = {}
        
    def create_version(self, document: Document, author: str, 
                      changes: Dict[str, Any], comment: str = "") -> DocumentVersion:
        """Create a new version of a document"""
        version_id = self._generate_version_id(document.id)
        
        # Calculate hash of document state
        doc_hash = self._calculate_hash(document)
        
        version = DocumentVersion(
            version_id=version_id,
            timestamp=datetime.now(),
            author=author,
            changes=changes,
            previous_version=document.current_version if document.current_version else None,
            comment=comment,
            hash=doc_hash
        )
        
        # Store version
        if document.id not in self.versions:
            self.versions[document.id] = []
        self.versions[document.id].append(version)
        
        # Update document
        document.versions.append(version)
        document.current_version = version_id
        document.updated_at = version.timestamp
        
        return version
        
    def get_version(self, document_id: str, version_id: str) -> Optional[DocumentVersion]:
        """Get a specific version of a document"""
        if document_id in self.versions:
            for version in self.versions[document_id]:
                if version.version_id == version_id:
                    return version
        return None
        
    def get_versions(self, document_id: str) -> List[DocumentVersion]:
        """Get all versions of a document"""
        return self.versions.get(document_id, [])
        
    def rollback(self, document: Document, version_id: str) -> bool:
        """Rollback document to a specific version"""
        version = self.get_version(document.id, version_id)
        if not version:
            return False
            
        # Create rollback version
        rollback_changes = {
            'action': 'rollback',
            'to_version': version_id,
            'from_version': document.current_version
        }
        
        self.create_version(
            document, 
            'system', 
            rollback_changes,
            f"Rollback to version {version_id}"
        )
        
        return True
        
    def _generate_version_id(self, document_id: str) -> str:
        """Generate a unique version ID"""
        timestamp = datetime.now().isoformat()
        return f"{document_id}-v-{timestamp}"
        
    def _calculate_hash(self, document: Document) -> str:
        """Calculate hash of document state"""
        # Create a string representation of document content
        content = json.dumps(document.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class TemplateSystem:
    """Main template system orchestrator"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path("templates")
        self.templates: Dict[str, Template] = {}
        self.documents: Dict[str, Document] = {}
        self.parser = TemplateParser()
        self.elicitor = InteractiveElicitation()
        self.access_control = RoleBasedAccessControl()
        self.version_control = VersionControl()
        
    def load_template(self, template_path: Path) -> Template:
        """Load a template from file"""
        if template_path.suffix == '.yaml' or template_path.suffix == '.yml':
            template = self.parser.parse_yaml(template_path)
        elif template_path.suffix == '.json':
            template = self.parser.parse_json(template_path)
        else:
            raise ValueError(f"Unsupported template format: {template_path.suffix}")
            
        self.templates[template.id] = template
        return template
        
    def load_all_templates(self) -> None:
        """Load all templates from template directory"""
        if self.template_dir.exists():
            for template_file in self.template_dir.glob("*.yaml"):
                self.load_template(template_file)
            for template_file in self.template_dir.glob("*.yml"):
                self.load_template(template_file)
            for template_file in self.template_dir.glob("*.json"):
                self.load_template(template_file)
                
    async def create_document(self, template_id: str, owner: str, 
                            title: Optional[str] = None) -> Document:
        """Create a new document from a template"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
            
        template = self.templates[template_id]
        doc_id = self._generate_document_id(template_id)
        
        document = Document(
            id=doc_id,
            template_id=template_id,
            title=title or f"New {template.name}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=owner,
            sections=deepcopy(template.sections)
        )
        
        # Elicit content for interactive sections
        for section_id, section in document.sections.items():
            if section.interaction != InteractionType.NONE:
                content = await self.elicitor.elicit_section(section)
                section.content = content
                
        # Create initial version
        self.version_control.create_version(
            document,
            owner,
            {'action': 'create', 'template': template_id},
            "Initial document creation"
        )
        
        self.documents[doc_id] = document
        return document
        
    def update_section(self, document_id: str, section_id: str, 
                      content: str, user: str) -> bool:
        """Update a section in a document"""
        if document_id not in self.documents:
            return False
            
        document = self.documents[document_id]
        if section_id not in document.sections:
            return False
            
        section = document.sections[section_id]
        
        # Check access control
        if not self.access_control.can_access(user, section, AccessLevel.EDITOR):
            return False
            
        # Update content
        old_content = section.content
        section.content = content
        
        # Create version
        changes = {
            'action': 'update_section',
            'section': section_id,
            'old_content': old_content,
            'new_content': content
        }
        self.version_control.create_version(
            document,
            user,
            changes,
            f"Updated section: {section.title}"
        )
        
        return True
        
    def add_editor(self, document_id: str, editor: str, user: str) -> bool:
        """Add an editor to a document"""
        if document_id not in self.documents:
            return False
            
        document = self.documents[document_id]
        
        # Check if user is owner
        if document.owner != user:
            return False
            
        if editor not in document.editors:
            document.editors.append(editor)
            
            # Create version
            changes = {
                'action': 'add_editor',
                'editor': editor
            }
            self.version_control.create_version(
                document,
                user,
                changes,
                f"Added editor: {editor}"
            )
            
        return True
        
    def export_document(self, document_id: str, format: str = 'markdown') -> str:
        """Export a document to a specific format"""
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found")
            
        document = self.documents[document_id]
        
        if format == 'markdown':
            return self._export_to_markdown(document)
        elif format == 'json':
            return json.dumps(document.to_dict(), indent=2)
        elif format == 'yaml':
            return yaml.dump(document.to_dict(), default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
    def _export_to_markdown(self, document: Document) -> str:
        """Export document to Markdown format"""
        lines = []
        lines.append(f"# {document.title}")
        lines.append(f"\n*Document ID: {document.id}*")
        lines.append(f"*Created: {document.created_at.isoformat()}*")
        lines.append(f"*Updated: {document.updated_at.isoformat()}*")
        lines.append(f"*Owner: {document.owner}*")
        
        if document.editors:
            lines.append(f"*Editors: {', '.join(document.editors)}*")
            
        lines.append("\n---\n")
        
        # Export sections
        for section_id, section in document.sections.items():
            lines.append(f"\n## {section.title}")
            if section.description:
                lines.append(f"\n*{section.description}*\n")
            lines.append(section.content)
            
            # Export children recursively
            if section.children:
                for child in section.children:
                    lines.append(f"\n### {child.title}")
                    if child.description:
                        lines.append(f"\n*{child.description}*\n")
                    lines.append(child.content)
                    
        return '\n'.join(lines)
        
    def _generate_document_id(self, template_id: str) -> str:
        """Generate a unique document ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{template_id}-doc-{timestamp}"


# Integration with Agent-Zero
class TemplateSystemTool:
    """Tool wrapper for Agent-Zero integration"""
    
    def __init__(self, template_system: TemplateSystem):
        self.template_system = template_system
        
    async def execute(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute template system commands"""
        if command == "load_template":
            template_path = Path(kwargs.get('path', ''))
            template = self.template_system.load_template(template_path)
            return {'success': True, 'template_id': template.id}
            
        elif command == "create_document":
            template_id = kwargs.get('template_id', '')
            owner = kwargs.get('owner', 'agent')
            title = kwargs.get('title')
            document = await self.template_system.create_document(
                template_id, owner, title
            )
            return {'success': True, 'document_id': document.id}
            
        elif command == "update_section":
            document_id = kwargs.get('document_id', '')
            section_id = kwargs.get('section_id', '')
            content = kwargs.get('content', '')
            user = kwargs.get('user', 'agent')
            success = self.template_system.update_section(
                document_id, section_id, content, user
            )
            return {'success': success}
            
        elif command == "export_document":
            document_id = kwargs.get('document_id', '')
            format = kwargs.get('format', 'markdown')
            content = self.template_system.export_document(document_id, format)
            return {'success': True, 'content': content}
            
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}