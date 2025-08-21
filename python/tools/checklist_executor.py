"""
Checklist Executor Tool for BMAD Quality Verification
Implements self-assessment checklists with justification requirements
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from python.helpers.checklist_core import ChecklistItem, Checklist, ChecklistParser
from agent import AgentContext

class ChecklistExecutor(Tool):
    """
    Tool for executing BMAD quality verification checklists.
    Supports self-assessment, justification requirements, and quality gates.
    """
    
    def __init__(self):
        super().__init__(
            name="ChecklistExecutor",
            description="Execute quality verification checklists with self-assessment",
            args={
                "checklist_path": "Path to the checklist file or name of predefined checklist",
                "mode": "execution mode: 'execute' (perform assessment), 'review' (review existing), 'create' (create new)",
                "items_status": "Optional: Dict mapping item indices to status and justification",
                "auto_assess": "Optional: Whether to automatically assess items based on context (default: True)",
                "context": "Optional: Additional context for assessment"
            },
            response_format={
                "checklist": "The executed/reviewed checklist",
                "summary": "Summary of checklist results",
                "quality_gate": "Quality gate decision: PASS, CONCERNS, FAIL, or WAIVED",
                "recommendations": "List of recommendations based on results"
            }
        )
        
        # Predefined checklist paths
        self.predefined_checklists = {
            "story_dod": "checklists/story_dod.md",
            "architecture_review": "checklists/architecture_review.md",
            "po_master": "checklists/po_master.md"
        }
    
    async def execute(self, checklist_path: str, mode: str = "execute", 
                     items_status: Optional[Dict[int, Dict[str, str]]] = None,
                     auto_assess: bool = True, assessment_context: str = "", 
                     context: AgentContext = None) -> Response:
        """Execute the checklist tool"""
        
        PrintStyle.print_info(f"Executing checklist: {checklist_path} in {mode} mode")
        
        try:
            # Resolve checklist path
            if checklist_path in self.predefined_checklists:
                checklist_file = self.predefined_checklists[checklist_path]
            else:
                checklist_file = checklist_path
            
            # Handle different modes
            if mode == "create":
                return await self._create_checklist(checklist_file, context)
            elif mode == "review":
                return await self._review_checklist(checklist_file, context)
            else:  # execute mode
                return await self._execute_checklist(
                    checklist_file, items_status, auto_assess, assessment_context, context
                )
                
        except Exception as e:
            return Response(
                success=False,
                message=f"Checklist execution failed: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _execute_checklist(self, checklist_file: str, 
                                items_status: Optional[Dict[int, Dict[str, str]]], 
                                auto_assess: bool, assessment_context: str,
                                agent_context: AgentContext) -> Response:
        """Execute checklist with assessment"""
        
        # Load checklist
        checklist = await self._load_checklist(checklist_file)
        if not checklist:
            return Response(
                success=False,
                message=f"Failed to load checklist: {checklist_file}",
                data={}
            )
        
        # Apply manual status updates if provided
        if items_status:
            for idx, status_info in items_status.items():
                if 0 <= idx < len(checklist.items):
                    item = checklist.items[idx]
                    status = status_info.get("status", "unchecked")
                    justification = status_info.get("justification", "")
                    
                    if status == "done":
                        item.mark_done()
                    elif status == "not_done":
                        item.mark_not_done(justification)
                    elif status == "n/a":
                        item.mark_not_applicable(justification)
        
        # Auto-assess if requested
        if auto_assess and agent_context:
            await self._auto_assess_items(checklist, assessment_context, agent_context)
        
        # Determine quality gate
        quality_gate = checklist.determine_quality_gate()
        
        # Generate recommendations
        recommendations = checklist.generate_recommendations()
        
        # Update metadata
        checklist.metadata["updated_at"] = datetime.now().isoformat()
        checklist.metadata["executed_at"] = datetime.now().isoformat()
        checklist.metadata["quality_gate"] = quality_gate
        
        # Save results
        await self._save_results(checklist, checklist_file)
        
        return Response(
            success=True,
            message=f"Checklist executed successfully: {checklist.name}",
            data={
                "checklist": checklist.to_dict(),
                "summary": checklist.get_summary(),
                "quality_gate": quality_gate,
                "recommendations": recommendations,
                "markdown": checklist.to_markdown()
            }
        )
    
    async def _create_checklist(self, checklist_file: str, 
                               agent_context: AgentContext) -> Response:
        """Create a new checklist"""
        
        # This would typically involve interaction with the user
        # For now, return a template
        template = Checklist(
            name="New Checklist",
            description="Add description here",
            items=[
                ChecklistItem("Sample item 1", llm_instruction="Check if requirement 1 is met"),
                ChecklistItem("Sample item 2", llm_instruction="Verify implementation of feature 2"),
                ChecklistItem("Sample item 3", llm_instruction="Validate test coverage")
            ]
        )
        
        return Response(
            success=True,
            message="Checklist template created",
            data={
                "checklist": template.to_dict(),
                "markdown": template.to_markdown()
            }
        )
    
    async def _review_checklist(self, checklist_file: str, 
                               agent_context: AgentContext) -> Response:
        """Review an existing checklist"""
        
        checklist = await self._load_checklist(checklist_file)
        if not checklist:
            return Response(
                success=False,
                message=f"Failed to load checklist: {checklist_file}",
                data={}
            )
        
        return Response(
            success=True,
            message=f"Checklist loaded: {checklist.name}",
            data={
                "checklist": checklist.to_dict(),
                "summary": checklist.get_summary(),
                "markdown": checklist.to_markdown()
            }
        )
    
    async def _load_checklist(self, checklist_file: str) -> Optional[Checklist]:
        """Load a checklist from file"""
        
        # Try to load from different locations
        possible_paths = [
            checklist_file,
            Path("checklists") / checklist_file,
            Path("checklists") / f"{checklist_file}.md",
            Path("checklists") / f"{checklist_file}.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                    
                if str(path).endswith('.md'):
                    return ChecklistParser.parse_markdown(content)
                elif str(path).endswith('.yaml') or str(path).endswith('.yml'):
                    data = yaml.safe_load(content)
                    return Checklist().from_dict(data)
                elif str(path).endswith('.json'):
                    data = json.loads(content)
                    return Checklist().from_dict(data)
        
        return None
    
    async def _auto_assess_items(self, checklist: Checklist, 
                                assessment_context: str,
                                agent_context: AgentContext):
        """Automatically assess checklist items using AI"""
        
        if not agent_context:
            return
        
        # Prepare assessment prompt
        prompt = f"""
        You are performing a self-assessment on the following checklist: {checklist.name}
        
        Context: {assessment_context}
        
        For each item, honestly assess whether it is:
        - Done (fully completed)
        - Not Done (not completed, provide justification)
        - N/A (not applicable, provide justification)
        
        Be thorough and honest in your assessment. If something is not done, explain why.
        
        Checklist items to assess:
        """
        
        for i, item in enumerate(checklist.items):
            prompt += f"\n{i+1}. {item.text}"
            if item.llm_instruction:
                prompt += f"\n   (Instruction: {item.llm_instruction})"
        
        # Get AI assessment (this would use the agent's LLM)
        # For now, we'll mark items based on simple heuristics
        # In production, this would call the agent's LLM
        
        for item in checklist.items:
            # Simple heuristic for demonstration
            if "optional" in item.text.lower():
                item.mark_not_applicable("Optional item not required for this context")
            elif "test" in item.text.lower() and "test" not in assessment_context.lower():
                item.mark_not_done("Tests not yet implemented")
            else:
                item.mark_done()
    
    async def _save_results(self, checklist: Checklist, original_file: str):
        """Save checklist results"""
        
        # Create results directory
        results_dir = Path("checklists/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(original_file).stem
        
        # Save as JSON for data
        json_file = results_dir / f"{base_name}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(checklist.to_dict(), f, indent=2)
        
        # Save as Markdown for readability
        md_file = results_dir / f"{base_name}_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write(checklist.to_markdown())
        
        PrintStyle.print_info(f"Results saved to: {json_file} and {md_file}")