"""
Refactoring Engine
==================

Generates and applies automated refactoring plans.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from core.client import create_client
    from phase_config import get_phase_model, get_phase_thinking_budget
except ImportError:
    def create_client(*args, **kwargs): return None
    def get_phase_model(*args, **kwargs): return "claude-3-5-sonnet-20241022"
    def get_phase_thinking_budget(*args, **kwargs): return "medium"

try:
    from debug import debug, debug_error, debug_section, debug_success
except ImportError:
    def debug(module: str, message: str, **kwargs): pass
    def debug_section(module: str, message: str): pass
    def debug_success(module: str, message: str, **kwargs): pass
    def debug_error(module: str, message: str, **kwargs): pass

from .health_checker import HealthIssue


@dataclass
class RefactoringAction:
    """A single refactoring action."""
    
    type: str  # rename, extract, inline, move, etc.
    description: str
    file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    applied: bool = False
    success: bool = False
    error: Optional[str] = None


@dataclass
class RefactoringPlan:
    """A complete refactoring plan."""
    
    title: str
    description: str
    issues_addressed: list[HealthIssue]
    actions: list[RefactoringAction] = field(default_factory=list)
    estimated_time: str = "unknown"
    risk_level: str = "low"  # low, medium, high
    
    # Execution tracking
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "issues_count": len(self.issues_addressed),
            "actions_count": len(self.actions),
            "estimated_time": self.estimated_time,
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
        }


class RefactoringEngine:
    """Generates and applies refactoring plans."""
    
    def __init__(self, project_dir: str | Path, model: Optional[str] = None):
        self.project_dir = Path(project_dir)
        self.model = model or get_phase_model("refactoring")
    
    async def generate_plan(
        self,
        issues: list[HealthIssue],
        max_actions: int = 10,
    ) -> RefactoringPlan:
        """Generate a refactoring plan from health issues."""
        debug_section("refactoring", "🔧 Generating Refactoring Plan")
        
        # Group issues by file
        by_file: dict[str, list[HealthIssue]] = {}
        for issue in issues:
            if issue.file not in by_file:
                by_file[issue.file] = []
            by_file[issue.file].append(issue)
        
        # Generate actions using LLM
        actions = []
        
        for file_path, file_issues in list(by_file.items())[:max_actions]:
            action = await self._generate_action_for_issues(file_path, file_issues)
            if action:
                actions.append(action)
        
        # Assess risk
        risk_level = self._assess_risk(actions)
        
        plan = RefactoringPlan(
            title=f"Auto-refactoring: {len(actions)} improvements",
            description=f"Addresses {len(issues)} health issues across {len(by_file)} files",
            issues_addressed=issues,
            actions=actions,
            estimated_time=f"{len(actions) * 5} minutes",
            risk_level=risk_level,
        )
        
        debug("self_healing", f"Generated plan with {len(actions)} actions")
        
        return plan
    
    async def _generate_action_for_issues(
        self,
        file_path: str,
        issues: list[HealthIssue],
    ) -> RefactoringAction | None:
        """Generate a refactoring action for specific issues."""
        try:
            # Read file
            full_path = self.project_dir / file_path
            if not full_path.exists():
                return None
            
            content = full_path.read_text(encoding="utf-8")
            
            # Create prompt for LLM
            issues_desc = "\n".join([
                f"- {issue.title}: {issue.description} (line {issue.line})"
                for issue in issues
            ])
            
            prompt = f"""Analyze this code and suggest a refactoring to fix these issues:

File: {file_path}
Issues:
{issues_desc}

Code:
```
{content[:2000]}  # Limit for token budget
```

Provide a specific refactoring action in this format:
TYPE: [extract_method|rename|simplify|optimize]
DESCRIPTION: Brief description
LINE_START: Starting line number (if applicable)
LINE_END: Ending line number (if applicable)
OLD_CODE: Original code snippet
NEW_CODE: Refactored code snippet
"""
            
            client = create_agent_client(
                project_dir=Path.cwd(),  # Use current directory as project_dir
                spec_dir=Path.cwd(),     # Use current directory as spec_dir
                model=self.model
            )
            if not client:
                return self._create_simple_action(file_path, issues)
            
            # Get LLM response
            response = await client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            
            # Parse response
            action = self._parse_llm_response(response.content[0].text, file_path)
            
            return action
        
        except Exception as e:
            debug_error(f"Failed to generate action for {file_path}: {e}")
            return self._create_simple_action(file_path, issues)
    
    def _create_simple_action(
        self,
        file_path: str,
        issues: list[HealthIssue],
    ) -> RefactoringAction:
        """Create a simple action without LLM."""
        return RefactoringAction(
            type="manual_review",
            description=f"Review and fix {len(issues)} issues",
            file=file_path,
        )
    
    def _parse_llm_response(self, response: str, file_path: str) -> RefactoringAction:
        """Parse LLM response into a refactoring action."""
        lines = response.split("\n")
        
        action_data = {
            "type": "refactor",
            "description": "Refactoring suggested by AI",
            "file": file_path,
        }
        
        for line in lines:
            if line.startswith("TYPE:"):
                action_data["type"] = line.replace("TYPE:", "").strip()
            elif line.startswith("DESCRIPTION:"):
                action_data["description"] = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("LINE_START:"):
                try:
                    action_data["line_start"] = int(line.replace("LINE_START:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("LINE_END:"):
                try:
                    action_data["line_end"] = int(line.replace("LINE_END:", "").strip())
                except ValueError:
                    pass
        
        return RefactoringAction(**action_data)
    
    def _assess_risk(self, actions: list[RefactoringAction]) -> str:
        """Assess risk level of the refactoring plan."""
        if not actions:
            return "low"
        
        # Count action types
        high_risk_types = ["move", "delete", "rename_public"]
        high_risk_count = sum(
            1 for action in actions
            if any(rt in action.type for rt in high_risk_types)
        )
        
        if high_risk_count > len(actions) * 0.5:
            return "high"
        elif high_risk_count > 0:
            return "medium"
        else:
            return "low"
    
    async def apply_plan(
        self,
        plan: RefactoringPlan,
        create_branch: bool = True,
        branch_name: str | None = None,
    ) -> bool:
        """Apply a refactoring plan."""
        debug_section("refactoring", "🔧 Applying Refactoring Plan")
        
        plan.started_at = datetime.now()
        
        try:
            # Create branch if requested
            if create_branch:
                branch_name = branch_name or f"self-healing/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                await self._create_branch(branch_name)
            
            # Apply each action
            for action in plan.actions:
                success = await self._apply_action(action)
                action.applied = True
                action.success = success
                
                if not success:
                    debug_error(f"Failed to apply action: {action.description}")
            
            # Check if all succeeded
            all_success = all(action.success for action in plan.actions)
            
            plan.completed_at = datetime.now()
            plan.success = all_success
            
            if all_success:
                debug_success(f"Successfully applied {len(plan.actions)} refactoring actions")
            
            return all_success
        
        except Exception as e:
            debug_error(f"Failed to apply refactoring plan: {e}")
            plan.completed_at = datetime.now()
            plan.success = False
            return False
    
    async def _create_branch(self, branch_name: str) -> None:
        """Create a git branch."""
        try:
            # Check if git repo
            git_dir = self.project_dir / ".git"
            if not git_dir.exists():
                debug("self_healing", "Not a git repository, skipping branch creation")
                return
            
            # Create and checkout branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
            
            debug("self_healing", f"Created branch: {branch_name}")
        
        except Exception as e:
            debug_error(f"Failed to create branch: {e}")
    
    async def _apply_action(self, action: RefactoringAction) -> bool:
        """Apply a single refactoring action."""
        try:
            if not action.new_code:
                # Can't apply without new code
                return False
            
            file_path = self.project_dir / action.file
            if not file_path.exists():
                action.error = "File not found"
                return False
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            
            # Replace lines
            if action.line_start and action.line_end:
                start = action.line_start - 1
                end = action.line_end
                
                new_lines = action.new_code.split("\n")
                lines[start:end] = new_lines
                
                # Write back
                new_content = "\n".join(lines)
                file_path.write_text(new_content, encoding="utf-8")
                
                return True
            else:
                # No line numbers, can't apply
                return False
        
        except Exception as e:
            action.error = str(e)
            return False
    
    async def create_pr_for_plan(
        self,
        plan: RefactoringPlan,
        branch_name: str,
    ) -> str | None:
        """Create a PR for a refactoring plan."""
        try:
            # Generate PR description
            description = f"""# 🧬 Self-Healing Refactoring

{plan.description}

## Changes
"""
            
            for action in plan.actions:
                description += f"\n- {action.description} ({action.file})"
            
            description += f"""

## Issues Addressed
{len(plan.issues_addressed)} health issues fixed

## Risk Level
{plan.risk_level}

---
*Generated by Auto-Claude Self-Healing System*
"""
            
            # Create PR using git (would integrate with GitHub/GitLab API)
            debug("self_healing", f"Would create PR with description:\n{description}")
            
            # TODO: Integrate with git provider API
            # For now, just commit
            subprocess.run(
                ["git", "add", "."],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
            
            commit_message = f"🧬 Self-Healing: {plan.title}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
            
            debug_success(f"Committed changes: {commit_message}")
            
            return branch_name
        
        except Exception as e:
            debug_error(f"Failed to create PR: {e}")
            return None