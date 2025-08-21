"""
Core checklist functionality without Agent-Zero dependencies
This module provides the basic checklist classes that can be used independently
"""

import re
import json
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

class ChecklistItem:
    """Represents a single checklist item"""
    
    def __init__(self, text: str, status: str = "unchecked", justification: str = "", llm_instruction: str = ""):
        self.text = text
        self.status = status  # "done", "not_done", "n/a", "unchecked"
        self.justification = justification
        self.llm_instruction = llm_instruction  # Hidden instruction for AI execution
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "status": self.status,
            "justification": self.justification,
            "llm_instruction": self.llm_instruction
        }
    
    def from_dict(self, data: Dict[str, Any]):
        self.text = data.get("text", "")
        self.status = data.get("status", "unchecked")
        self.justification = data.get("justification", "")
        self.llm_instruction = data.get("llm_instruction", "")
        return self
    
    def mark_done(self):
        self.status = "done"
        
    def mark_not_done(self, justification: str):
        self.status = "not_done"
        self.justification = justification
        
    def mark_not_applicable(self, justification: str):
        self.status = "n/a"
        self.justification = justification

class Checklist:
    """Represents a complete checklist"""
    
    def __init__(self, name: str, description: str = "", items: List[ChecklistItem] = None):
        self.name = name
        self.description = description
        self.items = items or []
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
    def add_item(self, item: ChecklistItem):
        self.items.append(item)
        
    def get_completion_rate(self) -> float:
        if not self.items:
            return 0.0
        done_count = sum(1 for item in self.items if item.status == "done")
        applicable_count = sum(1 for item in self.items if item.status != "n/a")
        return (done_count / applicable_count * 100) if applicable_count > 0 else 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "total_items": len(self.items),
            "done": sum(1 for item in self.items if item.status == "done"),
            "not_done": sum(1 for item in self.items if item.status == "not_done"),
            "not_applicable": sum(1 for item in self.items if item.status == "n/a"),
            "unchecked": sum(1 for item in self.items if item.status == "unchecked"),
            "completion_rate": self.get_completion_rate(),
            "metadata": self.metadata
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "metadata": self.metadata,
            "summary": self.get_summary()
        }
    
    def from_dict(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.metadata = data.get("metadata", {})
        self.items = [ChecklistItem().from_dict(item_data) for item_data in data.get("items", [])]
        return self
    
    def to_markdown(self) -> str:
        """Export checklist to markdown format"""
        md = f"# {self.name}\n\n"
        if self.description:
            md += f"{self.description}\n\n"
        
        md += "## Checklist Items\n\n"
        for item in self.items:
            checkbox = "[x]" if item.status == "done" else "[ ]" if item.status == "not_done" else "[N/A]" if item.status == "n/a" else "[ ]"
            md += f"- {checkbox} {item.text}\n"
            if item.justification:
                md += f"  - *Justification*: {item.justification}\n"
        
        md += f"\n## Summary\n\n"
        summary = self.get_summary()
        md += f"- **Completion Rate**: {summary['completion_rate']:.1f}%\n"
        md += f"- **Done**: {summary['done']}/{summary['total_items']}\n"
        md += f"- **Not Done**: {summary['not_done']}\n"
        md += f"- **Not Applicable**: {summary['not_applicable']}\n"
        
        return md
    
    def determine_quality_gate(self) -> str:
        """Determine quality gate status based on checklist results"""
        summary = self.get_summary()
        completion_rate = summary["completion_rate"]
        not_done_count = summary["not_done"]
        
        # Quality gate logic
        if completion_rate >= 95:
            return "PASS"
        elif completion_rate >= 80:
            return "CONCERNS"
        elif not_done_count > len(self.items) * 0.3:
            return "FAIL"
        else:
            return "WAIVED"
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on checklist results"""
        recommendations = []
        
        for item in self.items:
            if item.status == "not_done":
                recommendations.append(f"Complete: {item.text}")
                if item.justification:
                    recommendations.append(f"  Reason: {item.justification}")
            elif item.status == "unchecked":
                recommendations.append(f"Review and assess: {item.text}")
        
        summary = self.get_summary()
        if summary["completion_rate"] < 80:
            recommendations.append("Priority: Focus on completing critical items to reach 80% completion")
        
        return recommendations

class ChecklistParser:
    """Parses checklist definitions from markdown files"""
    
    @staticmethod
    def parse_markdown(content: str) -> Checklist:
        """Parse a markdown checklist file"""
        lines = content.split('\n')
        
        # Extract name from title
        name = "Unnamed Checklist"
        description = ""
        items = []
        
        # Parse header
        for i, line in enumerate(lines):
            if line.startswith("# "):
                name = line[2:].strip()
            elif line.startswith("## Description"):
                # Find description in next non-empty lines
                j = i + 1
                desc_lines = []
                while j < len(lines) and not lines[j].startswith("#"):
                    if lines[j].strip():
                        desc_lines.append(lines[j].strip())
                    j += 1
                description = " ".join(desc_lines)
                break
        
        # Parse checklist items
        in_checklist = False
        current_item_text = ""
        current_llm_instruction = ""
        
        for line in lines:
            # Check for checklist section
            if "## Checklist" in line or "## Items" in line:
                in_checklist = True
                continue
                
            if in_checklist:
                # Check for LLM instruction (hidden comment)
                llm_match = re.match(r'<!--\s*LLM:\s*(.*?)\s*-->', line.strip())
                if llm_match:
                    current_llm_instruction = llm_match.group(1)
                    continue
                
                # Parse checklist item
                item_match = re.match(r'^\s*-\s*\[([ xX]|N\/A|n\/a)\]\s*(.+)', line)
                if item_match:
                    status_char = item_match.group(1).lower()
                    item_text = item_match.group(2).strip()
                    
                    # Determine status
                    if status_char == 'x':
                        status = "done"
                    elif status_char in ['n/a', 'n/a']:
                        status = "n/a"
                    else:
                        status = "unchecked"
                    
                    # Create item
                    item = ChecklistItem(
                        text=item_text,
                        status=status,
                        llm_instruction=current_llm_instruction
                    )
                    items.append(item)
                    current_llm_instruction = ""  # Reset for next item
        
        checklist = Checklist(name=name, description=description, items=items)
        return checklist