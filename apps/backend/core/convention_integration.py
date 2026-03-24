"""
Convention Integration for AI Agents

This module integrates the convention enforcement engine and learning loop
with existing AI agents to ensure consistent adherence to project standards.
"""

import logging
from pathlib import Path
from typing import Any

from .convention_engine import create_convention_engine
from .learning_loop import create_learning_loop

logger = logging.getLogger(__name__)

# Constants
WORKPILOT_DIR = ".workpilot"


class ConventionAwareAgent:
    """
    Base class for agents that are convention-aware and can enforce
    project standards while learning from successful patterns.
    """

    def __init__(self, project_root: str, agent_type: str):
        self.project_root = Path(project_root)
        self.agent_type = agent_type

        # Initialize convention systems
        self.convention_engine = create_convention_engine(project_root)
        self.learning_loop = create_learning_loop(project_root)

        # Agent state
        self.current_build_id: str | None = None
        self.build_start_time: float | None = None
        self.violations_found: list[dict[str, Any]] = []
        self.patterns_applied: list[str] = []

    def start_build_tracking(self) -> str:
        """Start tracking a new build for learning."""
        import time
        import uuid

        self.current_build_id = str(uuid.uuid4())
        self.build_start_time = time.time()
        self.violations_found = []
        self.patterns_applied = []

        logger.info(f"Started build tracking: {self.current_build_id}")
        return self.current_build_id

    def validate_and_enforce_conventions(self, file_paths: list[str]) -> dict[str, Any]:
        """Validate files against conventions and enforce compliance."""
        validation_results = {}
        total_violations = 0

        for file_path in file_paths:
            violations = self.convention_engine.validate_file(file_path)
            if violations:
                validation_results[file_path] = violations
                total_violations += len(violations)

                # Track violations for learning
                for violation in violations:
                    self.violations_found.append(
                        {
                            "file_path": file_path,
                            "rule_type": violation.rule_type,
                            "severity": violation.severity,
                            "message": violation.message,
                        }
                    )

        logger.info(
            f"Convention validation completed: {total_violations} violations found"
        )

        return {
            "build_id": self.current_build_id,
            "violations_count": total_violations,
            "validation_results": validation_results,
            "files_checked": len(file_paths),
        }

    def apply_convention_fixes(
        self, file_path: str, violations: list
    ) -> dict[str, Any]:
        """Apply automatic fixes for convention violations."""
        fixes_applied = []

        for violation in violations:
            if violation.auto_fixable and violation.suggestion:
                try:
                    # Apply the fix
                    success = self._apply_auto_fix(file_path, violation)
                    if success:
                        fixes_applied.append(
                            {
                                "rule_type": violation.rule_type,
                                "fix_applied": violation.suggestion,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to apply auto-fix for {violation.rule_type}: {e}"
                    )

        return {
            "file_path": file_path,
            "fixes_applied": fixes_applied,
            "total_fixes": len(fixes_applied),
        }

    def _apply_auto_fix(self, file_path: str, violation) -> bool:
        """Apply an automatic fix for a violation."""
        try:
            file_path_obj = Path(file_path)

            if violation.rule_type == "python_file_naming":
                # Rename file to snake_case
                new_name = violation.suggestion.replace("Rename to '", "").replace(
                    "'", ""
                )
                new_path = file_path_obj.parent / new_name
                file_path_obj.rename(new_path)
                return True

            elif violation.rule_type == "typescript_component_naming":
                # Rename component file
                new_name = violation.suggestion.replace("Rename file to '", "").replace(
                    "'", ""
                )
                new_path = file_path_obj.parent / new_name
                file_path_obj.rename(new_path)
                return True

        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")

        return False

    def get_convention_context(self) -> dict[str, Any]:
        """Get convention context for agent decision making."""
        conventions_file = self.project_root / WORKPILOT_DIR / "conventions.md"
        architecture_file = self.project_root / WORKPILOT_DIR / "architecture.md"
        patterns_file = self.project_root / WORKPILOT_DIR / "patterns.md"

        context = {
            "conventions": {},
            "architecture": {},
            "patterns": {},
            "active_rules": [rule.name for rule in self.convention_engine.rules],
        }

        # Load steering file content
        try:
            if conventions_file.exists():
                context["conventions"] = conventions_file.read_text(encoding="utf-8")

            if architecture_file.exists():
                context["architecture"] = architecture_file.read_text(encoding="utf-8")

            if patterns_file.exists():
                context["patterns"] = patterns_file.read_text(encoding="utf-8")

        except Exception as e:
            logger.warning(f"Failed to load convention context: {e}")

        return context

    def record_pattern_usage(self, pattern_name: str, context: dict[str, Any]):
        """Record that a pattern was applied during build."""
        self.patterns_applied.append(
            {
                "pattern_name": pattern_name,
                "context": context,
                "timestamp": self._get_timestamp(),
            }
        )

    def complete_build_tracking(
        self, success: bool, build_data: dict[str, Any] | None = None
    ):
        """Complete build tracking and record for learning."""
        if not self.current_build_id or not self.build_start_time:
            logger.warning("No active build tracking to complete")
            return

        import time

        # Prepare build data for learning loop
        build_record = {
            "build_id": self.current_build_id,
            "success": success,
            "duration": time.time() - self.build_start_time,
            "agent_types": [self.agent_type],
            "files_changed": build_data.get("files_changed", []) if build_data else [],
            "patterns_applied": self.patterns_applied,
            "violations_found": self.violations_found,
            "performance_metrics": build_data.get("performance_metrics", {})
            if build_data
            else {},
            "technologies_used": build_data.get("technologies_used", [])
            if build_data
            else [],
            "context_size": build_data.get("context_size", 0) if build_data else 0,
            "tokens_used": build_data.get("tokens_used", 0) if build_data else 0,
        }

        # Record in learning loop
        self.learning_loop.record_build(build_record)

        # Check for evolution proposals
        pending_evolutions = self.learning_loop.get_pending_evolutions()
        if pending_evolutions:
            logger.info(
                f"Found {len(pending_evolutions)} pending convention evolutions"
            )
            for evolution in pending_evolutions[-3:]:  # Show latest 3
                logger.info(f"Evolution: {evolution.rationale}")

        # Reset tracking state
        self.current_build_id = None
        self.build_start_time = None

        logger.info("Build tracking completed and recorded for learning")

    def get_learning_insights(self) -> dict[str, Any]:
        """Get insights from the learning loop."""
        return self.learning_loop.get_learning_summary()

    def apply_pending_evolutions(self, auto_apply: bool = False) -> dict[str, Any]:
        """Apply pending convention evolutions."""
        pending_evolutions = self.learning_loop.get_pending_evolutions()
        applied_count = 0

        for evolution in pending_evolutions:
            if auto_apply and evolution.confidence_score >= 0.9:
                # High confidence evolutions can be auto-applied
                if self.learning_loop.apply_evolution(evolution.evolution_id):
                    applied_count += 1
                    logger.info(f"Auto-applied evolution: {evolution.evolution_id}")
            else:
                # Log for manual review
                logger.info(f"Evolution pending review: {evolution.rationale}")

        return {
            "total_pending": len(pending_evolutions),
            "auto_applied": applied_count,
            "pending_review": len(pending_evolutions) - applied_count,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()


class ConventionIntegration:
    """
    Integration layer for convention enforcement across the agent system.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.convention_engine = create_convention_engine(project_root)
        self.learning_loop = create_learning_loop(project_root)
        self.agent_registry: dict[str, ConventionAwareAgent] = {}

    def register_agent(self, agent_id: str, agent_type: str) -> ConventionAwareAgent:
        """Register an agent for convention tracking."""
        agent = ConventionAwareAgent(str(self.project_root), agent_type)
        self.agent_registry[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> ConventionAwareAgent | None:
        """Get a registered agent."""
        return self.agent_registry.get(agent_id)

    def validate_project_conventions(
        self, file_paths: list[str] | None = None
    ) -> dict[str, Any]:
        """Validate entire project or specific files against conventions."""
        validation_results = self.convention_engine.validate_project(file_paths)

        total_violations = sum(
            len(violations) for violations in validation_results.values()
        )

        return {
            "files_validated": len(validation_results),
            "total_violations": total_violations,
            "validation_results": validation_results,
            "summary": self._generate_validation_summary(validation_results),
        }

    def _generate_validation_summary(
        self, validation_results: dict[str, list]
    ) -> dict[str, Any]:
        """Generate summary of validation results."""
        rule_violations = {}
        severity_counts = {"error": 0, "warning": 0, "info": 0}

        for file_path, violations in validation_results.items():
            for violation in violations:
                rule_type = violation.rule_type
                severity = violation.severity

                rule_violations[rule_type] = rule_violations.get(rule_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "rule_violations": rule_violations,
            "severity_counts": severity_counts,
            "most_violated_rules": sorted(
                rule_violations.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        return {
            "registered_agents": len(self.agent_registry),
            "active_builds": len(
                [
                    agent
                    for agent in self.agent_registry.values()
                    if agent.current_build_id is not None
                ]
            ),
            "convention_rules": len(self.convention_engine.rules),
            "learning_summary": self.learning_loop.get_learning_summary(),
            "pending_evolutions": len(self.learning_loop.get_pending_evolutions()),
        }


# Global integration instance
_integration_instance: ConventionIntegration | None = None


def get_convention_integration(project_root: str) -> ConventionIntegration:
    """Get or create the global convention integration instance."""
    global _integration_instance

    if (
        _integration_instance is None
        or str(_integration_instance.project_root) != project_root
    ):
        _integration_instance = ConventionIntegration(project_root)

    return _integration_instance


def initialize_convention_system(project_root: str) -> ConventionIntegration:
    """Initialize the convention system for a project."""
    integration = get_convention_integration(project_root)

    # Ensure .workpilot directory exists
    workpilot_dir = Path(project_root) / WORKPILOT_DIR
    workpilot_dir.mkdir(exist_ok=True)

    logger.info(f"Convention system initialized for {project_root}")
    return integration
