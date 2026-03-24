"""
Architecture Rules Engine
==========================

Main deterministic analysis orchestrator. Composes ImportAnalyzer and
CircularDependencyDetector into a single validation pipeline.
"""

from __future__ import annotations

import time
from pathlib import Path

from .circular_detector import CircularDependencyDetector
from .config import ArchitectureConfig
from .import_analyzer import ImportAnalyzer
from .models import ArchitectureReport, ArchitectureViolation


class ArchitectureRulesEngine:
    """
    Deterministic architecture validation engine.

    Runs static analysis to detect:
    - Layer boundary violations (imports crossing forbidden layers)
    - Circular dependencies
    - Forbidden import patterns
    - Bounded context violations
    """

    def __init__(self, project_dir: Path, config: ArchitectureConfig):
        self.project_dir = project_dir
        self.config = config

    def validate(self, changed_files: list[str] | None = None) -> ArchitectureReport:
        """
        Run all deterministic architecture validations.

        Args:
            changed_files: If provided, only analyze these files (relative paths).
                          If None, analyze the entire project.

        Returns:
            ArchitectureReport with violations, warnings, and pass/fail status.
        """
        start = time.time()

        # 1. Build import graph
        analyzer = ImportAnalyzer(self.project_dir, self.config)
        graph = analyzer.analyze_imports(changed_files)

        # 2. Run all checks
        all_violations: list[ArchitectureViolation] = []

        # Layer violations
        layer_violations = analyzer.check_layer_violations(graph)
        all_violations.extend(layer_violations)

        # Forbidden import patterns
        forbidden_violations = analyzer.check_forbidden_imports(graph)
        all_violations.extend(forbidden_violations)

        # Circular dependencies
        circular_detector = CircularDependencyDetector(graph, self.config)
        cycle_violations = circular_detector.get_cycle_violations()
        all_violations.extend(cycle_violations)

        # Bounded context violations
        context_violations = circular_detector.check_bounded_context_violations()
        all_violations.extend(context_violations)

        # 3. Separate errors from warnings
        errors = [v for v in all_violations if v.severity == "error"]
        warnings = [v for v in all_violations if v.severity == "warning"]

        # 4. Build report
        duration = time.time() - start
        passed = len(errors) == 0
        config_source = "inferred" if self.config.inferred else "explicit"

        summary = self._build_summary(errors, warnings, graph.files_analyzed, passed)

        return ArchitectureReport(
            violations=errors,
            warnings=warnings,
            passed=passed,
            summary=summary,
            files_analyzed=graph.files_analyzed,
            duration_seconds=round(duration, 3),
            config_source=config_source,
        )

    def _build_summary(
        self,
        errors: list[ArchitectureViolation],
        warnings: list[ArchitectureViolation],
        files_analyzed: int,
        passed: bool,
    ) -> str:
        """Build a human-readable summary of the validation results."""
        if passed and not warnings:
            return (
                f"Architecture validation PASSED. "
                f"Analyzed {files_analyzed} files with no violations."
            )

        parts = []
        if passed:
            parts.append(
                f"Architecture validation PASSED with {len(warnings)} warning(s)."
            )
        else:
            parts.append(
                f"Architecture validation FAILED with {len(errors)} error(s) "
                f"and {len(warnings)} warning(s)."
            )

        parts.append(f"Analyzed {files_analyzed} files.")

        # Group violations by type
        type_counts: dict[str, int] = {}
        for v in errors + warnings:
            type_counts[v.type] = type_counts.get(v.type, 0) + 1

        type_labels = {
            "layer_violation": "layer boundary violation",
            "circular_dependency": "circular dependency",
            "forbidden_import": "forbidden import",
            "bounded_context": "bounded context violation",
        }

        for vtype, count in type_counts.items():
            label = type_labels.get(vtype, vtype)
            parts.append(f"  - {count} {label}(s)")

        return "\n".join(parts)
