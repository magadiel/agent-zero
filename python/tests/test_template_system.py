"""
Unit tests for the BMAD Template System
"""

import unittest
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import yaml
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.template_system import (
    Template, TemplateSection, TemplateParser, Document,
    DocumentVersion, AccessLevel, InteractionType,
    InteractiveElicitation, RoleBasedAccessControl,
    VersionControl, TemplateSystem, TemplateSystemTool
)


class TestTemplateSection(unittest.TestCase):
    """Test TemplateSection class"""
    
    def test_section_creation(self):
        """Test creating a template section"""
        section = TemplateSection(
            id="test_section",
            title="Test Section",
            description="Test description",
            content="Test content",
            required=True
        )
        
        self.assertEqual(section.id, "test_section")
        self.assertEqual(section.title, "Test Section")
        self.assertEqual(section.description, "Test description")
        self.assertEqual(section.content, "Test content")
        self.assertTrue(section.required)
        
    def test_section_with_access_roles(self):
        """Test section with access roles"""
        section = TemplateSection(
            id="test",
            title="Test",
            description="Test",
            access_roles={
                "owner": AccessLevel.OWNER,
                "editor": AccessLevel.EDITOR,
                "viewer": AccessLevel.VIEWER
            }
        )
        
        self.assertEqual(section.access_roles["owner"], AccessLevel.OWNER)
        self.assertEqual(section.access_roles["editor"], AccessLevel.EDITOR)
        self.assertEqual(section.access_roles["viewer"], AccessLevel.VIEWER)
        
    def test_section_with_interaction(self):
        """Test section with interaction settings"""
        section = TemplateSection(
            id="test",
            title="Test",
            description="Test",
            interaction=InteractionType.TEXT_INPUT,
            interaction_prompt="Enter text:",
            interaction_options=["Option 1", "Option 2"]
        )
        
        self.assertEqual(section.interaction, InteractionType.TEXT_INPUT)
        self.assertEqual(section.interaction_prompt, "Enter text:")
        self.assertEqual(len(section.interaction_options), 2)


class TestTemplate(unittest.TestCase):
    """Test Template class"""
    
    def test_template_creation(self):
        """Test creating a template"""
        template = Template("test_template", "Test Template", "Test description")
        
        self.assertEqual(template.id, "test_template")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.description, "Test description")
        self.assertEqual(len(template.sections), 0)
        
    def test_add_section(self):
        """Test adding sections to template"""
        template = Template("test", "Test", "Test")
        section = TemplateSection("section1", "Section 1", "Description")
        
        template.add_section(section)
        
        self.assertEqual(len(template.sections), 1)
        self.assertIn("section1", template.sections)
        self.assertIn("section1", template.required_sections)
        
    def test_remove_section(self):
        """Test removing sections from template"""
        template = Template("test", "Test", "Test")
        section = TemplateSection("section1", "Section 1", "Description")
        
        template.add_section(section)
        template.remove_section("section1")
        
        self.assertEqual(len(template.sections), 0)
        self.assertNotIn("section1", template.sections)
        self.assertNotIn("section1", template.required_sections)
        
    def test_get_section(self):
        """Test getting section by ID"""
        template = Template("test", "Test", "Test")
        section = TemplateSection("section1", "Section 1", "Description")
        
        template.add_section(section)
        retrieved = template.get_section("section1")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "section1")
        
    def test_template_to_dict(self):
        """Test converting template to dictionary"""
        template = Template("test", "Test", "Test")
        section = TemplateSection("section1", "Section 1", "Description")
        template.add_section(section)
        
        result = template.to_dict()
        
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("sections", result)
        self.assertEqual(len(result["sections"]), 1)


class TestTemplateParser(unittest.TestCase):
    """Test TemplateParser class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_parse_yaml(self):
        """Test parsing template from YAML"""
        yaml_content = """
id: test_template
name: Test Template
description: Test description
sections:
  section1:
    title: Section 1
    description: Description 1
    required: true
    content: Default content
  section2:
    title: Section 2
    description: Description 2
    required: false
"""
        yaml_file = Path(self.temp_dir) / "test.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)
            
        template = TemplateParser.parse_yaml(yaml_file)
        
        self.assertEqual(template.id, "test_template")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(len(template.sections), 2)
        self.assertIn("section1", template.sections)
        self.assertIn("section2", template.sections)
        
    def test_parse_json(self):
        """Test parsing template from JSON"""
        json_content = {
            "id": "test_template",
            "name": "Test Template",
            "description": "Test description",
            "sections": {
                "section1": {
                    "title": "Section 1",
                    "description": "Description 1",
                    "required": True
                }
            }
        }
        
        json_file = Path(self.temp_dir) / "test.json"
        with open(json_file, 'w') as f:
            json.dump(json_content, f)
            
        template = TemplateParser.parse_json(json_file)
        
        self.assertEqual(template.id, "test_template")
        self.assertEqual(len(template.sections), 1)
        
    def test_parse_section_with_interaction(self):
        """Test parsing section with interaction settings"""
        data = {
            "title": "Test Section",
            "description": "Test",
            "interaction": {
                "type": "text_input",
                "prompt": "Enter text:",
                "options": ["Option 1", "Option 2"]
            }
        }
        
        section = TemplateParser._parse_section("test", data)
        
        self.assertEqual(section.interaction, InteractionType.TEXT_INPUT)
        self.assertEqual(section.interaction_prompt, "Enter text:")
        self.assertEqual(len(section.interaction_options), 2)
        
    def test_parse_section_with_children(self):
        """Test parsing section with child sections"""
        data = {
            "title": "Parent Section",
            "description": "Parent",
            "children": {
                "child1": {
                    "title": "Child 1",
                    "description": "Child section 1"
                },
                "child2": {
                    "title": "Child 2",
                    "description": "Child section 2"
                }
            }
        }
        
        section = TemplateParser._parse_section("parent", data)
        
        self.assertEqual(len(section.children), 2)
        self.assertEqual(section.children[0].title, "Child 1")
        self.assertEqual(section.children[1].title, "Child 2")


class TestRoleBasedAccessControl(unittest.TestCase):
    """Test RoleBasedAccessControl class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.rbac = RoleBasedAccessControl()
        
    def test_set_user_roles(self):
        """Test setting user roles"""
        self.rbac.set_user_roles("user1", ["editor", "viewer"])
        
        roles = self.rbac.get_user_roles("user1")
        self.assertEqual(len(roles), 2)
        self.assertIn("editor", roles)
        self.assertIn("viewer", roles)
        
    def test_add_user_role(self):
        """Test adding a role to user"""
        self.rbac.add_user_role("user1", "editor")
        self.rbac.add_user_role("user1", "viewer")
        
        roles = self.rbac.get_user_roles("user1")
        self.assertEqual(len(roles), 2)
        
    def test_remove_user_role(self):
        """Test removing a role from user"""
        self.rbac.set_user_roles("user1", ["editor", "viewer"])
        self.rbac.remove_user_role("user1", "editor")
        
        roles = self.rbac.get_user_roles("user1")
        self.assertEqual(len(roles), 1)
        self.assertIn("viewer", roles)
        
    def test_can_access_owner(self):
        """Test owner access"""
        section = TemplateSection(
            "test", "Test", "Test",
            access_roles={"editor": AccessLevel.EDITOR}
        )
        
        self.rbac.set_user_roles("user1", ["owner"])
        
        # Owner has access to everything
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.OWNER))
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.EDITOR))
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.VIEWER))
        
    def test_can_access_editor(self):
        """Test editor access"""
        section = TemplateSection(
            "test", "Test", "Test",
            access_roles={"editor": AccessLevel.EDITOR}
        )
        
        self.rbac.set_user_roles("user1", ["editor"])
        
        self.assertFalse(self.rbac.can_access("user1", section, AccessLevel.OWNER))
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.EDITOR))
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.VIEWER))
        
    def test_can_access_viewer(self):
        """Test viewer access"""
        section = TemplateSection(
            "test", "Test", "Test",
            access_roles={"viewer": AccessLevel.VIEWER}
        )
        
        self.rbac.set_user_roles("user1", ["viewer"])
        
        self.assertFalse(self.rbac.can_access("user1", section, AccessLevel.OWNER))
        self.assertFalse(self.rbac.can_access("user1", section, AccessLevel.EDITOR))
        self.assertTrue(self.rbac.can_access("user1", section, AccessLevel.VIEWER))


class TestVersionControl(unittest.TestCase):
    """Test VersionControl class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.vc = VersionControl()
        self.document = Document(
            id="doc1",
            template_id="template1",
            title="Test Document",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner="user1"
        )
        
    def test_create_version(self):
        """Test creating a version"""
        changes = {"action": "update", "field": "content"}
        version = self.vc.create_version(self.document, "user1", changes, "Test update")
        
        self.assertIsNotNone(version)
        self.assertEqual(version.author, "user1")
        self.assertEqual(version.comment, "Test update")
        self.assertIn("action", version.changes)
        
    def test_get_version(self):
        """Test getting a specific version"""
        changes = {"action": "update"}
        version1 = self.vc.create_version(self.document, "user1", changes, "V1")
        
        retrieved = self.vc.get_version("doc1", version1.version_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.version_id, version1.version_id)
        
    def test_get_versions(self):
        """Test getting all versions"""
        self.vc.create_version(self.document, "user1", {"action": "v1"}, "V1")
        self.vc.create_version(self.document, "user2", {"action": "v2"}, "V2")
        
        versions = self.vc.get_versions("doc1")
        
        self.assertEqual(len(versions), 2)
        
    def test_version_hash(self):
        """Test version hash calculation"""
        version = self.vc.create_version(
            self.document, "user1", 
            {"action": "update"}, "Test"
        )
        
        self.assertIsNotNone(version.hash)
        self.assertEqual(len(version.hash), 64)  # SHA256 hash length
        
    def test_rollback(self):
        """Test rollback to previous version"""
        v1 = self.vc.create_version(self.document, "user1", {"action": "v1"}, "V1")
        v2 = self.vc.create_version(self.document, "user2", {"action": "v2"}, "V2")
        
        success = self.vc.rollback(self.document, v1.version_id)
        
        self.assertTrue(success)
        versions = self.vc.get_versions("doc1")
        self.assertEqual(len(versions), 3)  # Original 2 + rollback version


class TestTemplateSystem(unittest.TestCase):
    """Test TemplateSystem class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.template_system = TemplateSystem(Path(self.temp_dir))
        
        # Create a test template file
        self.test_template = {
            "id": "test_template",
            "name": "Test Template",
            "description": "Test",
            "sections": {
                "section1": {
                    "title": "Section 1",
                    "description": "Test section",
                    "required": True,
                    "content": "Default content"
                }
            }
        }
        
        template_file = Path(self.temp_dir) / "test.yaml"
        with open(template_file, 'w') as f:
            yaml.dump(self.test_template, f)
            
    def test_load_template(self):
        """Test loading a template"""
        template_file = Path(self.temp_dir) / "test.yaml"
        template = self.template_system.load_template(template_file)
        
        self.assertIsNotNone(template)
        self.assertEqual(template.id, "test_template")
        self.assertIn("test_template", self.template_system.templates)
        
    def test_load_all_templates(self):
        """Test loading all templates from directory"""
        # Create another template
        template2 = {
            "id": "template2",
            "name": "Template 2",
            "description": "Test",
            "sections": {}
        }
        
        template_file2 = Path(self.temp_dir) / "template2.yaml"
        with open(template_file2, 'w') as f:
            yaml.dump(template2, f)
            
        self.template_system.load_all_templates()
        
        self.assertEqual(len(self.template_system.templates), 2)
        self.assertIn("test_template", self.template_system.templates)
        self.assertIn("template2", self.template_system.templates)
        
    async def test_create_document(self):
        """Test creating a document from template"""
        template_file = Path(self.temp_dir) / "test.yaml"
        self.template_system.load_template(template_file)
        
        document = await self.template_system.create_document(
            "test_template", "user1", "My Document"
        )
        
        self.assertIsNotNone(document)
        self.assertEqual(document.template_id, "test_template")
        self.assertEqual(document.owner, "user1")
        self.assertEqual(document.title, "My Document")
        self.assertIn("section1", document.sections)
        
    def test_update_section(self):
        """Test updating a document section"""
        # First create a document
        template_file = Path(self.temp_dir) / "test.yaml"
        self.template_system.load_template(template_file)
        
        loop = asyncio.new_event_loop()
        document = loop.run_until_complete(
            self.template_system.create_document("test_template", "user1")
        )
        
        # Set up access control
        self.template_system.access_control.set_user_roles("user1", ["owner"])
        
        # Update section
        success = self.template_system.update_section(
            document.id, "section1", "New content", "user1"
        )
        
        self.assertTrue(success)
        self.assertEqual(document.sections["section1"].content, "New content")
        
    def test_add_editor(self):
        """Test adding an editor to document"""
        template_file = Path(self.temp_dir) / "test.yaml"
        self.template_system.load_template(template_file)
        
        loop = asyncio.new_event_loop()
        document = loop.run_until_complete(
            self.template_system.create_document("test_template", "user1")
        )
        
        success = self.template_system.add_editor(document.id, "user2", "user1")
        
        self.assertTrue(success)
        self.assertIn("user2", document.editors)
        
    def test_export_document_markdown(self):
        """Test exporting document to Markdown"""
        template_file = Path(self.temp_dir) / "test.yaml"
        self.template_system.load_template(template_file)
        
        loop = asyncio.new_event_loop()
        document = loop.run_until_complete(
            self.template_system.create_document("test_template", "user1", "Test Doc")
        )
        
        markdown = self.template_system.export_document(document.id, "markdown")
        
        self.assertIn("# Test Doc", markdown)
        self.assertIn("## Section 1", markdown)
        self.assertIn("Default content", markdown)
        
    def test_export_document_json(self):
        """Test exporting document to JSON"""
        template_file = Path(self.temp_dir) / "test.yaml"
        self.template_system.load_template(template_file)
        
        loop = asyncio.new_event_loop()
        document = loop.run_until_complete(
            self.template_system.create_document("test_template", "user1")
        )
        
        json_str = self.template_system.export_document(document.id, "json")
        json_data = json.loads(json_str)
        
        self.assertIn("id", json_data)
        self.assertIn("template_id", json_data)
        self.assertIn("sections", json_data)


class TestTemplateSystemTool(unittest.TestCase):
    """Test TemplateSystemTool for Agent-Zero integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.template_system = TemplateSystem(Path(self.temp_dir))
        self.tool = TemplateSystemTool(self.template_system)
        
        # Create test template
        template_file = Path(self.temp_dir) / "test.yaml"
        with open(template_file, 'w') as f:
            yaml.dump({
                "id": "test",
                "name": "Test",
                "description": "Test",
                "sections": {
                    "s1": {"title": "S1", "description": "Test"}
                }
            }, f)
            
    async def test_execute_load_template(self):
        """Test executing load_template command"""
        template_file = Path(self.temp_dir) / "test.yaml"
        result = await self.tool.execute("load_template", path=str(template_file))
        
        self.assertTrue(result["success"])
        self.assertEqual(result["template_id"], "test")
        
    async def test_execute_create_document(self):
        """Test executing create_document command"""
        template_file = Path(self.temp_dir) / "test.yaml"
        await self.tool.execute("load_template", path=str(template_file))
        
        result = await self.tool.execute(
            "create_document",
            template_id="test",
            owner="agent",
            title="Test Document"
        )
        
        self.assertTrue(result["success"])
        self.assertIn("document_id", result)
        
    async def test_execute_update_section(self):
        """Test executing update_section command"""
        template_file = Path(self.temp_dir) / "test.yaml"
        await self.tool.execute("load_template", path=str(template_file))
        
        doc_result = await self.tool.execute(
            "create_document",
            template_id="test"
        )
        
        self.template_system.access_control.set_user_roles("agent", ["owner"])
        
        result = await self.tool.execute(
            "update_section",
            document_id=doc_result["document_id"],
            section_id="s1",
            content="Updated content",
            user="agent"
        )
        
        self.assertTrue(result["success"])
        
    async def test_execute_export_document(self):
        """Test executing export_document command"""
        template_file = Path(self.temp_dir) / "test.yaml"
        await self.tool.execute("load_template", path=str(template_file))
        
        doc_result = await self.tool.execute(
            "create_document",
            template_id="test"
        )
        
        result = await self.tool.execute(
            "export_document",
            document_id=doc_result["document_id"],
            format="markdown"
        )
        
        self.assertTrue(result["success"])
        self.assertIn("content", result)
        
    async def test_execute_unknown_command(self):
        """Test executing unknown command"""
        result = await self.tool.execute("unknown_command")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestInteractiveElicitation(unittest.TestCase):
    """Test InteractiveElicitation class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.elicitor = InteractiveElicitation()
        
    async def test_elicit_no_interaction(self):
        """Test eliciting section with no interaction"""
        section = TemplateSection(
            "test", "Test", "Test",
            content="Default content",
            interaction=InteractionType.NONE
        )
        
        result = await self.elicitor.elicit_section(section)
        
        self.assertEqual(result, "Default content")


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Run specific async tests
class TestAsyncMethods(unittest.TestCase):
    """Test async methods"""
    
    def test_async_create_document(self):
        """Test async document creation"""
        temp_dir = tempfile.mkdtemp()
        template_system = TemplateSystem(Path(temp_dir))
        
        # Create template
        template_file = Path(temp_dir) / "test.yaml"
        with open(template_file, 'w') as f:
            yaml.dump({
                "id": "test",
                "name": "Test",
                "description": "Test",
                "sections": {}
            }, f)
            
        template_system.load_template(template_file)
        
        document = run_async_test(
            template_system.create_document("test", "user1")
        )
        
        self.assertIsNotNone(document)
        self.assertEqual(document.template_id, "test")
        
    def test_async_tool_execution(self):
        """Test async tool execution"""
        temp_dir = tempfile.mkdtemp()
        template_system = TemplateSystem(Path(temp_dir))
        tool = TemplateSystemTool(template_system)
        
        template_file = Path(temp_dir) / "test.yaml"
        with open(template_file, 'w') as f:
            yaml.dump({
                "id": "test",
                "name": "Test",
                "description": "Test",
                "sections": {}
            }, f)
            
        result = run_async_test(
            tool.execute("load_template", path=str(template_file))
        )
        
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()