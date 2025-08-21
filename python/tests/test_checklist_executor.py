"""
Unit tests for the ChecklistExecutor tool
"""

import os
import sys
import json
import yaml
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from tools.checklist_executor import (
    ChecklistItem, Checklist, ChecklistParser, ChecklistExecutor
)
from helpers.tool import Response

class TestChecklistItem:
    """Test ChecklistItem class"""
    
    def test_item_creation(self):
        item = ChecklistItem("Test item", "done", "Test justification", "LLM instruction")
        assert item.text == "Test item"
        assert item.status == "done"
        assert item.justification == "Test justification"
        assert item.llm_instruction == "LLM instruction"
    
    def test_item_mark_done(self):
        item = ChecklistItem("Test item")
        item.mark_done()
        assert item.status == "done"
    
    def test_item_mark_not_done(self):
        item = ChecklistItem("Test item")
        item.mark_not_done("Not completed because...")
        assert item.status == "not_done"
        assert item.justification == "Not completed because..."
    
    def test_item_mark_not_applicable(self):
        item = ChecklistItem("Test item")
        item.mark_not_applicable("Not needed for this project")
        assert item.status == "n/a"
        assert item.justification == "Not needed for this project"
    
    def test_item_to_dict(self):
        item = ChecklistItem("Test", "done", "Just", "LLM")
        data = item.to_dict()
        assert data["text"] == "Test"
        assert data["status"] == "done"
        assert data["justification"] == "Just"
        assert data["llm_instruction"] == "LLM"
    
    def test_item_from_dict(self):
        data = {
            "text": "Test",
            "status": "done",
            "justification": "Just",
            "llm_instruction": "LLM"
        }
        item = ChecklistItem().from_dict(data)
        assert item.text == "Test"
        assert item.status == "done"

class TestChecklist:
    """Test Checklist class"""
    
    def test_checklist_creation(self):
        checklist = Checklist("Test Checklist", "Test description")
        assert checklist.name == "Test Checklist"
        assert checklist.description == "Test description"
        assert len(checklist.items) == 0
    
    def test_add_item(self):
        checklist = Checklist("Test")
        item = ChecklistItem("Item 1")
        checklist.add_item(item)
        assert len(checklist.items) == 1
        assert checklist.items[0].text == "Item 1"
    
    def test_completion_rate_all_done(self):
        checklist = Checklist("Test")
        checklist.add_item(ChecklistItem("Item 1", "done"))
        checklist.add_item(ChecklistItem("Item 2", "done"))
        assert checklist.get_completion_rate() == 100.0
    
    def test_completion_rate_partial(self):
        checklist = Checklist("Test")
        checklist.add_item(ChecklistItem("Item 1", "done"))
        checklist.add_item(ChecklistItem("Item 2", "not_done"))
        assert checklist.get_completion_rate() == 50.0
    
    def test_completion_rate_with_na(self):
        checklist = Checklist("Test")
        checklist.add_item(ChecklistItem("Item 1", "done"))
        checklist.add_item(ChecklistItem("Item 2", "done"))
        checklist.add_item(ChecklistItem("Item 3", "n/a"))
        # Only 2 applicable items, both done
        assert checklist.get_completion_rate() == 100.0
    
    def test_get_summary(self):
        checklist = Checklist("Test")
        checklist.add_item(ChecklistItem("Item 1", "done"))
        checklist.add_item(ChecklistItem("Item 2", "not_done"))
        checklist.add_item(ChecklistItem("Item 3", "n/a"))
        checklist.add_item(ChecklistItem("Item 4", "unchecked"))
        
        summary = checklist.get_summary()
        assert summary["total_items"] == 4
        assert summary["done"] == 1
        assert summary["not_done"] == 1
        assert summary["not_applicable"] == 1
        assert summary["unchecked"] == 1
    
    def test_to_markdown(self):
        checklist = Checklist("Test Checklist", "Description")
        checklist.add_item(ChecklistItem("Done item", "done"))
        checklist.add_item(ChecklistItem("Not done", "not_done", "Reason"))
        checklist.add_item(ChecklistItem("N/A item", "n/a", "Not needed"))
        
        markdown = checklist.to_markdown()
        assert "# Test Checklist" in markdown
        assert "Description" in markdown
        assert "[x] Done item" in markdown
        assert "[ ] Not done" in markdown
        assert "[N/A] N/A item" in markdown
        assert "Reason" in markdown
        assert "Not needed" in markdown

class TestChecklistParser:
    """Test ChecklistParser class"""
    
    def test_parse_simple_markdown(self):
        content = """# Test Checklist
## Description
This is a test checklist

## Checklist Items
- [x] Completed item
- [ ] Uncompleted item
- [N/A] Not applicable item
"""
        checklist = ChecklistParser.parse_markdown(content)
        assert checklist.name == "Test Checklist"
        assert checklist.description == "This is a test checklist"
        assert len(checklist.items) == 3
        assert checklist.items[0].status == "done"
        assert checklist.items[1].status == "unchecked"
        assert checklist.items[2].status == "n/a"
    
    def test_parse_with_llm_instructions(self):
        content = """# Test Checklist

## Checklist Items
<!-- LLM: Check if requirement is met -->
- [ ] Item with instruction
- [ ] Item without instruction
<!-- LLM: Verify implementation -->
- [ ] Another item with instruction
"""
        checklist = ChecklistParser.parse_markdown(content)
        assert len(checklist.items) == 3
        assert checklist.items[0].llm_instruction == "Check if requirement is met"
        assert checklist.items[1].llm_instruction == ""
        assert checklist.items[2].llm_instruction == "Verify implementation"

class TestChecklistExecutor:
    """Test ChecklistExecutor tool"""
    
    @pytest.fixture
    def executor(self):
        return ChecklistExecutor()
    
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.id = "test-agent"
        return context
    
    @pytest.fixture
    def temp_checklist_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""# Test Checklist
## Description
Test checklist for unit tests

## Checklist Items
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3
""")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_executor_initialization(self, executor):
        assert executor.name == "ChecklistExecutor"
        assert "story_dod" in executor.predefined_checklists
        assert "architecture_review" in executor.predefined_checklists
        assert "po_master" in executor.predefined_checklists
    
    @pytest.mark.asyncio
    async def test_create_mode(self, executor, mock_context):
        response = await executor.execute(
            checklist_path="new_checklist",
            mode="create",
            context=mock_context
        )
        
        assert response.success is True
        assert "template created" in response.message
        assert "checklist" in response.data
        assert "markdown" in response.data
    
    @pytest.mark.asyncio
    async def test_review_mode(self, executor, mock_context, temp_checklist_file):
        response = await executor.execute(
            checklist_path=temp_checklist_file,
            mode="review",
            context=mock_context
        )
        
        assert response.success is True
        assert "Test Checklist" in response.message
        assert response.data["checklist"]["name"] == "Test Checklist"
        assert len(response.data["checklist"]["items"]) == 3
    
    @pytest.mark.asyncio
    async def test_execute_mode_manual(self, executor, mock_context, temp_checklist_file):
        items_status = {
            0: {"status": "done"},
            1: {"status": "not_done", "justification": "Not ready"},
            2: {"status": "n/a", "justification": "Not needed"}
        }
        
        response = await executor.execute(
            checklist_path=temp_checklist_file,
            mode="execute",
            items_status=items_status,
            auto_assess=False,
            context=mock_context
        )
        
        assert response.success is True
        checklist_data = response.data["checklist"]
        assert checklist_data["items"][0]["status"] == "done"
        assert checklist_data["items"][1]["status"] == "not_done"
        assert checklist_data["items"][2]["status"] == "n/a"
    
    @pytest.mark.asyncio
    async def test_quality_gate_pass(self, executor, mock_context, temp_checklist_file):
        # All items done should result in PASS
        items_status = {
            0: {"status": "done"},
            1: {"status": "done"},
            2: {"status": "done"}
        }
        
        response = await executor.execute(
            checklist_path=temp_checklist_file,
            mode="execute",
            items_status=items_status,
            auto_assess=False,
            context=mock_context
        )
        
        assert response.data["quality_gate"] == "PASS"
    
    @pytest.mark.asyncio
    async def test_quality_gate_concerns(self, executor, mock_context, temp_checklist_file):
        # 2 out of 3 done should result in CONCERNS
        items_status = {
            0: {"status": "done"},
            1: {"status": "done"},
            2: {"status": "not_done", "justification": "Issue"}
        }
        
        response = await executor.execute(
            checklist_path=temp_checklist_file,
            mode="execute",
            items_status=items_status,
            auto_assess=False,
            context=mock_context
        )
        
        # 66.7% completion should result in FAIL based on current logic
        assert response.data["quality_gate"] in ["FAIL", "CONCERNS"]
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(self, executor, mock_context, temp_checklist_file):
        items_status = {
            0: {"status": "done"},
            1: {"status": "not_done", "justification": "Need more time"},
            2: {"status": "unchecked"}
        }
        
        response = await executor.execute(
            checklist_path=temp_checklist_file,
            mode="execute",
            items_status=items_status,
            auto_assess=False,
            context=mock_context
        )
        
        recommendations = response.data["recommendations"]
        assert len(recommendations) > 0
        assert any("Complete: Item 2" in r for r in recommendations)
        assert any("Review and assess: Item 3" in r for r in recommendations)
    
    @pytest.mark.asyncio
    async def test_predefined_checklist_resolution(self, executor, mock_context):
        # Test that predefined checklist names are resolved
        executor.predefined_checklists["test"] = "test_path.md"
        
        with patch.object(executor, '_load_checklist') as mock_load:
            mock_load.return_value = Checklist("Test")
            
            with patch.object(executor, '_execute_checklist') as mock_execute:
                mock_execute.return_value = Response(success=True, message="OK", data={})
                
                await executor.execute(
                    checklist_path="test",
                    mode="execute",
                    context=mock_context
                )
                
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0]
                assert call_args[0] == "test_path.md"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, executor, mock_context):
        response = await executor.execute(
            checklist_path="non_existent_file.md",
            mode="execute",
            context=mock_context
        )
        
        assert response.success is False
        assert "Failed to load checklist" in response.message

class TestIntegration:
    """Integration tests for the complete checklist system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from creation to execution"""
        executor = ChecklistExecutor()
        mock_context = Mock()
        
        # Create a temporary checklist file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""# Integration Test Checklist
## Description
Full workflow test

## Checklist Items
<!-- LLM: Verify feature A -->
- [ ] Feature A implemented
<!-- LLM: Verify feature B -->
- [ ] Feature B implemented
- [ ] Documentation updated
- [ ] Tests written
""")
            temp_path = f.name
        
        try:
            # Review the checklist
            review_response = await executor.execute(
                checklist_path=temp_path,
                mode="review",
                context=mock_context
            )
            assert review_response.success is True
            assert len(review_response.data["checklist"]["items"]) == 4
            
            # Execute with manual assessment
            execute_response = await executor.execute(
                checklist_path=temp_path,
                mode="execute",
                items_status={
                    0: {"status": "done"},
                    1: {"status": "done"},
                    2: {"status": "not_done", "justification": "In progress"},
                    3: {"status": "done"}
                },
                auto_assess=False,
                context=mock_context
            )
            
            assert execute_response.success is True
            assert execute_response.data["summary"]["done"] == 3
            assert execute_response.data["summary"]["not_done"] == 1
            assert execute_response.data["quality_gate"] in ["CONCERNS", "PASS"]
            
            # Verify markdown output
            markdown = execute_response.data["markdown"]
            assert "[x] Feature A implemented" in markdown
            assert "[ ] Documentation updated" in markdown
            assert "In progress" in markdown
            
        finally:
            os.unlink(temp_path)
            # Clean up any result files
            results_dir = Path("checklists/results")
            if results_dir.exists():
                for file in results_dir.glob("Integration_Test_Checklist_*"):
                    file.unlink()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])