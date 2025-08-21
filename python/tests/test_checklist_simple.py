"""
Simple standalone tests for checklist functionality
Tests core checklist logic without dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only the core classes (no Tool dependency)
import importlib.util
spec = importlib.util.spec_from_file_location("checklist_core", "python/tools/checklist_executor.py")
checklist_module = importlib.util.module_from_spec(spec)

# Manually extract the classes we need
exec(open("python/tools/checklist_executor.py").read().split("class ChecklistExecutor")[0])

def test_checklist_item():
    """Test ChecklistItem functionality"""
    print("Testing ChecklistItem...")
    
    # Test creation
    item = ChecklistItem("Test item", "done", "Test justification", "LLM instruction")
    assert item.text == "Test item"
    assert item.status == "done"
    assert item.justification == "Test justification"
    assert item.llm_instruction == "LLM instruction"
    
    # Test mark_done
    item2 = ChecklistItem("Test item 2")
    item2.mark_done()
    assert item2.status == "done"
    
    # Test mark_not_done
    item3 = ChecklistItem("Test item 3")
    item3.mark_not_done("Not ready")
    assert item3.status == "not_done"
    assert item3.justification == "Not ready"
    
    # Test mark_not_applicable
    item4 = ChecklistItem("Test item 4")
    item4.mark_not_applicable("Not needed")
    assert item4.status == "n/a"
    assert item4.justification == "Not needed"
    
    print("✓ ChecklistItem tests passed")

def test_checklist():
    """Test Checklist functionality"""
    print("Testing Checklist...")
    
    # Test creation
    checklist = Checklist("Test Checklist", "Test description")
    assert checklist.name == "Test Checklist"
    assert checklist.description == "Test description"
    assert len(checklist.items) == 0
    
    # Test adding items
    checklist.add_item(ChecklistItem("Item 1", "done"))
    checklist.add_item(ChecklistItem("Item 2", "not_done"))
    checklist.add_item(ChecklistItem("Item 3", "n/a"))
    assert len(checklist.items) == 3
    
    # Test completion rate
    rate = checklist.get_completion_rate()
    assert rate == 50.0  # 1 done out of 2 applicable (n/a doesn't count)
    
    # Test summary
    summary = checklist.get_summary()
    assert summary["total_items"] == 3
    assert summary["done"] == 1
    assert summary["not_done"] == 1
    assert summary["not_applicable"] == 1
    assert summary["completion_rate"] == 50.0
    
    # Test to_markdown
    markdown = checklist.to_markdown()
    assert "# Test Checklist" in markdown
    assert "[x] Item 1" in markdown
    assert "[ ] Item 2" in markdown
    assert "[N/A] Item 3" in markdown
    
    print("✓ Checklist tests passed")

def test_checklist_parser():
    """Test ChecklistParser functionality"""
    print("Testing ChecklistParser...")
    
    # Test basic parsing
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
    assert checklist.items[0].text == "Completed item"
    assert checklist.items[1].status == "unchecked"
    assert checklist.items[2].status == "n/a"
    
    # Test parsing with LLM instructions
    content2 = """# Test Checklist 2

## Checklist Items
<!-- LLM: Check requirement A -->
- [ ] Item with instruction
- [ ] Item without instruction
<!-- LLM: Check requirement B -->
- [ ] Another item with instruction
"""
    
    checklist2 = ChecklistParser.parse_markdown(content2)
    assert len(checklist2.items) == 3
    assert checklist2.items[0].llm_instruction == "Check requirement A"
    assert checklist2.items[1].llm_instruction == ""
    assert checklist2.items[2].llm_instruction == "Check requirement B"
    
    print("✓ ChecklistParser tests passed")

def test_quality_gate_logic():
    """Test quality gate determination logic"""
    print("Testing quality gate logic...")
    
    # Test PASS scenario (>95% completion)
    checklist1 = Checklist("Test")
    for i in range(20):
        checklist1.add_item(ChecklistItem(f"Item {i}", "done"))
    assert checklist1.get_completion_rate() == 100.0
    
    # Test CONCERNS scenario (80-95% completion)
    checklist2 = Checklist("Test")
    for i in range(10):
        status = "done" if i < 9 else "not_done"
        checklist2.add_item(ChecklistItem(f"Item {i}", status))
    assert checklist2.get_completion_rate() == 90.0
    
    # Test FAIL scenario (<80% completion)
    checklist3 = Checklist("Test")
    for i in range(10):
        status = "done" if i < 5 else "not_done"
        checklist3.add_item(ChecklistItem(f"Item {i}", status))
    assert checklist3.get_completion_rate() == 50.0
    
    print("✓ Quality gate logic tests passed")

def test_checklist_serialization():
    """Test checklist serialization and deserialization"""
    print("Testing checklist serialization...")
    
    # Create a checklist
    checklist = Checklist("Test Checklist", "Description")
    checklist.add_item(ChecklistItem("Item 1", "done"))
    checklist.add_item(ChecklistItem("Item 2", "not_done", "Reason"))
    
    # Convert to dict
    data = checklist.to_dict()
    assert data["name"] == "Test Checklist"
    assert len(data["items"]) == 2
    assert data["items"][0]["status"] == "done"
    
    # Create from dict
    checklist2 = Checklist().from_dict(data)
    assert checklist2.name == "Test Checklist"
    assert len(checklist2.items) == 2
    assert checklist2.items[1].justification == "Reason"
    
    print("✓ Serialization tests passed")

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running Checklist System Tests")
    print("=" * 50)
    
    try:
        test_checklist_item()
        test_checklist()
        test_checklist_parser()
        test_quality_gate_logic()
        test_checklist_serialization()
        
        print("=" * 50)
        print("✅ All tests passed successfully!")
        print("=" * 50)
        return True
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)