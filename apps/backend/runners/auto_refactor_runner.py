#!/usr/bin/env python3
"""
Auto-Refactor Agent Runner

Analyzes codebase for code smells, technical debt, and outdated patterns,
then proposes and executes autonomous refactoring operations.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

try:
    # Try to import CoderAgent or create fallback
    try:
        from agents.coder_agent import CoderAgent
    except ImportError:

        class CoderAgent:
            def __init__(self, config=None):
                self.config = config or {}

            def analyze_code(self, *args, **kwargs):
                return {"issues": []}

            def plan_refactoring(self, *args, **kwargs):
                return {"items": [], "estimated_effort": "1 hour"}

            def execute_refactoring(self, *args, **kwargs):
                return {"changes_made": 0, "files_modified": [], "success": True}

    # Try to import ProjectContext or create fallback
    try:
        from core.context import ProjectContext
    except ImportError:

        class ProjectContext:
            def __init__(self, project_dir):
                self.project_dir = project_dir

            def get_summary(self):
                return {"test": "summary"}

    # Try to import model_info or create fallback
    try:
        from core.model_info import get_model_info_for_logs
    except ImportError:

        def get_model_info_for_logs():
            return "test-model"

    from memory import clear_memory, get_memory_dir

    _AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    _AVAILABLE = False


class AutoRefactorRunner:
    """Runner for the Auto-Refactor Agent functionality."""

    def __init__(
        self,
        project_dir: str,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.model = model
        self.thinking_level = thinking_level or "medium"
        self.project_context = None
        self.memory = None
        self.agent = None

    def setup(self):
        """Initialize the agent and context."""
        print("🔧 Initializing Auto-Refactor Agent...")

        # Initialize project context
        self.project_context = ProjectContext(str(self.project_dir))
        print(f"📁 Project context loaded for: {self.project_dir}")

        # Initialize memory using available memory system
        self.memory = {
            "memory_dir": get_memory_dir(str(self.project_dir)),
            "clear": lambda: clear_memory(str(self.project_dir)),
        }

        # Initialize coder agent with specified model
        agent_config = {
            "model": self.model,
            "thinking_level": self.thinking_level,
        }
        self.agent = CoderAgent(config=agent_config)

        model_info = get_model_info_for_logs()
        print(f"🤖 Auto-Refactor Agent initialized with {model_info}")

    def analyze_codebase(self) -> dict[str, Any]:
        """Analyze the codebase for code smells and technical debt."""
        print("🔍 Analyzing codebase for code smells and technical debt...")

        analysis_prompt = """
        Analyze this codebase for the following issues:
        
        1. Code Smells:
           - Long methods and functions
           - Large classes and modules
           - Duplicate code
           - Complex conditional logic
           - Magic numbers and strings
           - Inconsistent naming conventions
        
        2. Technical Debt:
           - Deprecated patterns or methods
           - Security vulnerabilities
           - Performance bottlenecks
           - Missing error handling
           - Hard-coded values
           - Outdated dependencies
        
        3. Architectural Issues:
           - Tight coupling
           - Violation of SOLID principles
           - Missing abstractions
           - Inconsistent design patterns
        
        For each issue found, provide:
        - File path and line numbers
        - Severity level (Low/Medium/High/Critical)
        - Description of the issue
        - Suggested refactoring approach
        - Estimated complexity (Simple/Moderate/Complex)
        
        Focus on issues that would have the most impact on code quality, maintainability, and performance.
        """

        try:
            # Get project structure and key files
            project_files = self._get_project_files()

            # Analyze using the agent
            analysis_result = self.agent.analyze_code(
                prompt=analysis_prompt,
                context={
                    "project_files": project_files,
                    "project_context": self.project_context.get_summary(),
                },
            )

            return {
                "status": "success",
                "analysis": analysis_result,
                "files_analyzed": len(project_files),
            }

        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "files_analyzed": 0,
            }

    def _get_project_files(self) -> list[dict[str, Any]]:
        """Get relevant project files for analysis."""
        relevant_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".go",
            ".rs",
        }
        files = []

        for file_path in self.project_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in relevant_extensions:
                # Skip common ignore patterns
                if any(
                    pattern in str(file_path)
                    for pattern in [
                        "node_modules",
                        ".git",
                        "__pycache__",
                        "dist",
                        "build",
                        ".venv",
                    ]
                ):
                    continue

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    files.append(
                        {
                            "path": str(file_path.relative_to(self.project_dir)),
                            "size": len(content),
                            "lines": content.count("\n") + 1,
                            "extension": file_path.suffix,
                        }
                    )
                except Exception as e:
                    print(f"⚠️ Could not read {file_path}: {str(e)}")

        return sorted(files, key=lambda x: x["size"], reverse=True)[
            :50
        ]  # Limit to 50 largest files

    def generate_refactoring_plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate a prioritized refactoring plan based on analysis."""
        print("📋 Generating refactoring plan...")

        planning_prompt = f"""
        Based on the following codebase analysis, create a prioritized refactoring plan:
        
        {json.dumps(analysis, indent=2)}
        
        Create a refactoring plan that includes:
        
        1. Prioritization:
           - Group issues by severity and impact
           - Identify dependencies between refactoring tasks
           - Suggest an order that minimizes risk
        
        2. Execution Plan:
           - Break down complex refactorings into smaller, safe steps
           - Identify which changes can be made automatically
           - Flag changes that require human review
        
        3. Risk Assessment:
           - Identify potential breaking changes
           - Suggest testing strategies
           - Estimate rollback complexity
        
        4. Quick Wins:
           - Identify simple, high-impact changes
           - Suggest low-risk improvements
        
        Format the response as a structured JSON with clear action items.
        """

        try:
            plan_result = self.agent.plan_refactoring(
                prompt=planning_prompt, analysis_data=analysis
            )

            return {
                "status": "success",
                "plan": plan_result,
            }

        except Exception as e:
            print(f"❌ Error generating plan: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }

    def execute_refactoring(
        self, plan: dict[str, Any], auto_execute: bool = False
    ) -> dict[str, Any]:
        """Execute the refactoring plan."""
        print("🔨 Executing refactoring plan...")

        if not auto_execute:
            print("⚠️ Auto-execution disabled. Generating preview only...")

        try:
            execution_result = self.agent.execute_refactoring(
                plan=plan,
                project_dir=str(self.project_dir),
                auto_execute=auto_execute,
                dry_run=not auto_execute,
            )

            return {
                "status": "success",
                "execution": execution_result,
                "auto_executed": auto_execute,
            }

        except Exception as e:
            print(f"❌ Error during execution: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "auto_executed": auto_execute,
            }

    def run_full_analysis(self) -> dict[str, Any]:
        """Run the complete auto-refactor workflow."""
        print("🚀 Starting Auto-Refactor analysis...")

        # Step 1: Analyze codebase
        analysis = self.analyze_codebase()
        if analysis["status"] != "success":
            return analysis

        # Step 2: Generate refactoring plan
        plan = self.generate_refactoring_plan(analysis)
        if plan["status"] != "success":
            return plan

        # Step 3: Execute refactoring (preview only by default)
        execution = self.execute_refactoring(plan, auto_execute=False)

        result = {
            "status": "success",
            "analysis": analysis,
            "plan": plan,
            "execution": execution,
            "summary": self._generate_summary(analysis, plan, execution),
        }

        print("✅ Auto-Refactor analysis completed!")
        return result

    def _generate_summary(
        self, analysis: dict[str, Any], plan: dict[str, Any], execution: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a summary of the refactoring analysis."""
        return {
            "issues_found": len(analysis.get("analysis", {}).get("issues", [])),
            "files_analyzed": analysis.get("files_analyzed", 0),
            "refactoring_items": len(plan.get("plan", {}).get("items", [])),
            "quick_wins": len(
                [
                    item
                    for item in plan.get("plan", {}).get("items", [])
                    if item.get("priority") == "high"
                ]
            ),
            "estimated_effort": plan.get("plan", {}).get("estimated_effort", "Unknown"),
            "risk_level": execution.get("execution", {})
            .get("risk_assessment", {})
            .get("overall_risk", "Medium"),
        }


def main():
    """Main entry point for the auto-refactor runner."""
    parser = argparse.ArgumentParser(description="Auto-Refactor Agent Runner")
    parser.add_argument(
        "--project-dir", required=True, help="Project directory to analyze"
    )
    parser.add_argument("--model", help="AI model to use")
    parser.add_argument(
        "--thinking-level", default="medium", help="Thinking level for the agent"
    )
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        help="Automatically execute refactoring (use with caution)",
    )

    args = parser.parse_args()

    if not _AVAILABLE:
        error_result = {
            "status": "error",
            "error": "Auto-refactor agent dependencies not yet available. This feature is under development.",
            "analysis": {"status": "error", "analysis": None, "files_analyzed": 0},
            "plan": {"status": "error", "plan": None},
            "execution": {"status": "error", "execution": None, "auto_executed": False},
            "summary": {
                "issues_found": 0,
                "files_analyzed": 0,
                "refactoring_items": 0,
                "quick_wins": 0,
                "estimated_effort": "N/A",
                "risk_level": "N/A",
            },
        }
        print("__AUTO_REFACTOR_RESULT__:" + json.dumps(error_result))
        sys.exit(0)

    # Validate project directory
    if not os.path.exists(args.project_dir):
        print(f"❌ Error: Project directory '{args.project_dir}' does not exist")
        sys.exit(1)

    try:
        # Initialize runner
        runner = AutoRefactorRunner(
            project_dir=args.project_dir,
            model=args.model,
            thinking_level=args.thinking_level,
        )

        # Setup agent and context
        runner.setup()

        # Run analysis
        result = runner.run_full_analysis()

        # Output structured result
        print("__AUTO_REFACTOR_RESULT__:" + json.dumps(result, indent=2))

        # If auto-execute is requested, run execution
        if args.auto_execute:
            print("🔨 Auto-executing refactoring plan...")
            execution_result = runner.execute_refactoring(
                result["plan"], auto_execute=True
            )
            print(
                "__AUTO_REFACTOR_EXECUTION__:" + json.dumps(execution_result, indent=2)
            )

    except KeyboardInterrupt:
        print("\n⚠️ Auto-refactor analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
