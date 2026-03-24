"""
Migration Orchestrator: Coordinates the migration pipeline.
"""

import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyzer import StackAnalyzer
from .llm_transformer import LLMTransformer
from .models import (
    MigrationContext,
    MigrationState,
    RollbackCheckpoint,
    StackInfo,
    ValidationReport,
)
from .planner import MigrationPlanner
from .transformer import TransformationEngine


class MigrationOrchestrator:
    """Main orchestrator for the migration pipeline."""

    def __init__(self, project_dir: str, enable_llm: bool = True):
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / ".auto-claude" / "migration"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.context: MigrationContext | None = None
        self.checkpoints: dict[str, RollbackCheckpoint] = {}
        self.enable_llm = enable_llm
        self.llm_transformer = (
            LLMTransformer(str(self.project_dir)) if enable_llm else None
        )

    def start_migration(
        self, target_framework: str, target_language: str
    ) -> MigrationContext:
        """Start a new migration process."""
        # Analyze source stack
        analyzer = StackAnalyzer(str(self.project_dir))
        source_stack = analyzer.detect_stack()

        # Create target stack
        target_stack = StackInfo(
            framework=target_framework,
            language=target_language,
            version="latest",
        )

        # Validate migration is supported
        migration_key = (source_stack.framework, target_stack.framework)
        from .config import SUPPORTED_MIGRATIONS

        if migration_key not in SUPPORTED_MIGRATIONS:
            raise ValueError(
                f"Migration from {source_stack.framework} to {target_stack.framework} "
                "is not supported"
            )

        # Create migration context
        self.context = MigrationContext(
            migration_id=str(uuid.uuid4()),
            source_stack=source_stack,
            target_stack=target_stack,
            project_dir=str(self.project_dir),
            state=MigrationState.PLANNING,
            started_at=datetime.now(),
        )

        # Generate migration plan
        planner = MigrationPlanner(source_stack, target_stack)
        self.context.plan = planner.create_plan()

        # Save initial state
        self._save_context()

        return self.context

    def resume_migration(self, migration_id: str) -> MigrationContext:
        """Resume a paused or interrupted migration."""
        state_file = self.state_dir / f"{migration_id}.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Migration {migration_id} not found")

        # Load context
        with open(state_file) as f:
            data = json.load(f)

        self.context = self._deserialize_context(data)
        return self.context

    def pause_migration(self) -> None:
        """Pause the current migration."""
        if not self.context:
            raise ValueError("No active migration")

        self.context.state = MigrationState.PAUSED
        self.context.paused_at = datetime.now()
        self._save_context()

    def plan_phase(self) -> dict[str, Any]:
        """Execute planning phase."""
        if not self.context:
            raise ValueError("No active migration")

        self.context.state = MigrationState.PLANNING
        self.context.current_phase = "planning"

        # Run analyzer to assess complexity
        analyzer = StackAnalyzer(str(self.project_dir))
        complexity = analyzer.assess_migration_complexity(
            self.context.source_stack,
            self.context.target_stack,
        )

        # Save checkpoint
        self._create_checkpoint("planning")

        return {
            "status": "planned",
            "plan": self.context.plan.to_dict() if self.context.plan else None,
            "complexity": complexity,
        }

    def analyze_phase(self) -> dict[str, Any]:
        """Execute analysis phase."""
        if not self.context:
            raise ValueError("No active migration")

        self.context.state = MigrationState.ANALYZING
        self.context.current_phase = "analysis"

        # Save checkpoint
        self._create_checkpoint("analysis")

        return {
            "status": "analyzed",
            "source_stack": self.context.source_stack.to_dict(),
            "target_stack": self.context.target_stack.to_dict(),
            "affected_files": self._count_affected_files(),
        }

    def transform_phase(self) -> dict[str, Any]:
        """Execute transformation phase."""
        if not self.context or not self.context.plan:
            raise ValueError("No active migration or plan")

        self.context.state = MigrationState.TRANSFORMING
        self.context.current_phase = "transformation"

        results = {
            "status": "in_progress",
            "phases_completed": 0,
            "total_phases": len(self.context.plan.phases),
            "transformations": [],
        }

        # Initialize transformation engine
        transformer = TransformationEngine(
            str(self.project_dir),
            self.context.source_stack.framework,
            self.context.target_stack.framework,
        )

        # Execute transformations
        print(
            f"Starting transformation from {self.context.source_stack.framework} to {self.context.target_stack.framework}..."
        )
        transformation_results = transformer.transform_code()

        # Enhance with LLM if enabled
        if self.enable_llm and self.llm_transformer and transformation_results:
            print(
                f"Enhancing {len(transformation_results)} transformations with LLM..."
            )
            import asyncio

            # Determine prompt template
            prompt_template = f"{self.context.source_stack.framework}_to_{self.context.target_stack.framework}.md"

            # Run async enhancement
            enhanced_results = asyncio.run(
                self.llm_transformer.enhance_transformations_batch(
                    transformation_results,
                    self.context.source_stack.framework,
                    self.context.target_stack.framework,
                    prompt_template,
                )
            )
            transformation_results = enhanced_results

        # Store results
        self.context.transformations = transformation_results
        results["transformations"] = [
            {
                "file": t.file_path,
                "type": t.transformation_type,
                "confidence": t.confidence,
                "changes": t.changes_count,
                "llm_enhanced": getattr(t, "llm_enhanced", False),
            }
            for t in transformation_results
        ]

        # Execute each transformation phase
        for phase in self.context.plan.phases:
            if phase.id in ["analysis", "planning", "backup"]:
                continue  # Skip non-transformation phases

            phase.status = "in_progress"
            phase.started_at = datetime.now()

            phase.status = "completed"
            phase.completed_at = datetime.now()
            results["phases_completed"] += 1

            # Save checkpoint after each phase
            self._create_checkpoint(phase.id)

        self.context.state = MigrationState.VALIDATING
        self._save_context()

        return results

    def validate_phase(self) -> ValidationReport:
        """Execute validation phase."""
        if not self.context:
            raise ValueError("No active migration")

        self.context.state = MigrationState.VALIDATING
        self.context.current_phase = "validation"

        report = ValidationReport(passed=True)

        # Run tests
        test_result = self._run_tests()
        report.passed = test_result["success"]
        report.total_tests = test_result.get("total", 0)
        report.passed_tests = test_result.get("passed", 0)
        report.failed_tests = test_result.get("failed", 0)

        # Check build
        build_result = self._check_build()
        if not build_result["success"]:
            report.passed = False
            report.errors.append("Build failed")

        # Check linting
        lint_result = self._check_lint()
        if not lint_result["success"]:
            report.warnings.append("Linting issues detected")

        self.context.test_results = {
            "tests": test_result,
            "build": build_result,
            "lint": lint_result,
        }

        if report.passed:
            self.context.state = MigrationState.COMPLETE
        else:
            self.context.state = MigrationState.FAILED

        self._save_context()
        return report

    def rollback_migration(self, to_checkpoint: str | None = None) -> dict[str, Any]:
        """Rollback the migration to a previous state."""
        if not self.context:
            raise ValueError("No active migration")

        if not self.context.checkpoints:
            return {"status": "error", "message": "No checkpoints available"}

        # Get checkpoint to rollback to
        if to_checkpoint:
            if to_checkpoint not in self.context.checkpoints:
                return {
                    "status": "error",
                    "message": f"Checkpoint {to_checkpoint} not found",
                }
            checkpoint_commit = self.context.checkpoints[to_checkpoint]
        else:
            # Rollback to the first checkpoint (before transformation started)
            checkpoint_commit = self.context.checkpoints.get("planning")
            if not checkpoint_commit:
                checkpoint_commit = list(self.context.checkpoints.values())[0]

        # Execute git rollback
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", checkpoint_commit],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Git rollback failed: {result.stderr}",
                }
        except Exception as e:
            return {"status": "error", "message": f"Rollback failed: {str(e)}"}

        self.context.state = MigrationState.ROLLED_BACK
        self.context.rollback_available = False
        self._save_context()

        return {
            "status": "rolled_back",
            "checkpoint": to_checkpoint or "initial",
            "commit": checkpoint_commit,
        }

    def get_status(self) -> dict[str, Any]:
        """Get current migration status."""
        if not self.context:
            return {"status": "no_migration"}

        return {
            "migration_id": self.context.migration_id,
            "state": self.context.state.value,
            "source_stack": self.context.source_stack.to_dict(),
            "target_stack": self.context.target_stack.to_dict(),
            "started_at": self.context.started_at.isoformat()
            if self.context.started_at
            else None,
            "current_phase": self.context.current_phase,
            "plan": self.context.plan.to_dict() if self.context.plan else None,
            "checkpoints": list(self.context.checkpoints.keys()),
        }

    # Private helper methods

    def _create_checkpoint(self, phase_id: str) -> str:
        """Create a git checkpoint and save state."""
        try:
            # Create git commit for checkpoint
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.project_dir,
                capture_output=True,
                timeout=30,
            )

            result = subprocess.run(
                ["git", "commit", "-m", f"Migration checkpoint: {phase_id}"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Extract commit hash
                commit_hash = result.stdout.strip().split(" ")[-2]

                # Save to context
                if self.context:
                    self.context.checkpoints[phase_id] = commit_hash

                return commit_hash
        except Exception as e:
            print(f"Warning: Could not create git checkpoint: {e}")

        return ""

    def _count_affected_files(self) -> int:
        """Count affected files in the migration."""
        if not self.context or not self.context.plan:
            return 0

        affected_files = set()
        for phase in self.context.plan.phases:
            for step in phase.steps:
                affected_files.update(step.files_affected)

        return len(affected_files)

    def _run_tests(self) -> dict[str, Any]:
        """Run test suite and return results."""
        try:
            # Try to detect test command
            test_commands = [
                "npm test",
                "pytest",
                "python -m pytest",
                "python -m unittest discover",
                "yarn test",
                "pnpm test",
            ]

            for cmd in test_commands:
                result = subprocess.run(
                    cmd.split(),
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                    }
        except Exception as e:
            print(f"Test execution error: {e}")

        return {"success": False, "error": "No test command found"}

    def _check_build(self) -> dict[str, Any]:
        """Check if project builds successfully."""
        try:
            build_commands = [
                "npm run build",
                "yarn build",
                "pnpm build",
                "python setup.py build",
                "gradle build",
                "mvn clean build",
            ]

            for cmd in build_commands:
                result = subprocess.run(
                    cmd.split(),
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode == 0:
                    return {"success": True}
        except Exception as e:
            print(f"Build check error: {e}")

        return {"success": False, "error": "Build failed or no build command found"}

    def _check_lint(self) -> dict[str, Any]:
        """Check linting."""
        try:
            lint_commands = [
                "npm run lint",
                "eslint .",
                "pylint .",
                "flake8 .",
            ]

            for cmd in lint_commands:
                result = subprocess.run(
                    cmd.split(),
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    return {"success": True}
        except Exception as e:
            print(f"Lint check error: {e}")

        return {"success": False}

    def _save_context(self) -> None:
        """Save migration context to file."""
        if not self.context:
            return

        state_file = self.state_dir / f"{self.context.migration_id}.json"
        with open(state_file, "w") as f:
            json.dump(self.context.to_dict(), f, indent=2)

    def _deserialize_context(self, data: dict) -> MigrationContext:
        """Deserialize migration context from dict."""
        # Simplified deserialization - full implementation in models.py
        return MigrationContext.load_from_file("")  # Placeholder
