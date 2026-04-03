"""
Tests for architecture/circular_detector.py — cycle detection and bounded context violations.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from architecture.circular_detector import CircularDependencyDetector
from architecture.models import (
    ArchitectureConfig,
    BoundedContextConfig,
    ImportEdge,
    ImportGraph,
    RulesConfig,
)


def _make_graph(edges: list[tuple[str, str]]) -> ImportGraph:
    """Helper to create an ImportGraph from (source, target) tuples."""
    return ImportGraph(
        edges=[
            ImportEdge(source_file=src, target_module=tgt)
            for src, tgt in edges
        ],
        files_analyzed=len(set(src for src, _ in edges)),
    )


def _make_config(
    no_circular=True, bounded_contexts=None, inferred=False
) -> ArchitectureConfig:
    """Helper to create a config."""
    return ArchitectureConfig(
        rules=RulesConfig(no_circular_dependencies=no_circular),
        bounded_contexts=bounded_contexts or [],
        inferred=inferred,
    )


class TestCycleDetection:
    """Tests for detect_cycles()."""

    def test_detects_simple_cycle(self):
        """Should detect A -> B -> A cycle."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        assert len(cycles) >= 1
        # The cycle should contain both a.py and b.py
        cycle_files = set()
        for cycle in cycles:
            cycle_files.update(cycle)
        assert "a.py" in cycle_files
        assert "b.py" in cycle_files

    def test_detects_three_node_cycle(self):
        """Should detect A -> B -> C -> A cycle."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "c.py"),
            ("c.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        assert len(cycles) >= 1
        # At least one cycle should contain all three
        found = False
        for cycle in cycles:
            if set(cycle) == {"a.py", "b.py", "c.py"}:
                found = True
                break
        assert found, f"Expected 3-node cycle, got: {cycles}"

    def test_no_cycle_in_dag(self):
        """Should not detect cycles in a DAG."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "c.py"),
            ("a.py", "c.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        assert len(cycles) == 0

    def test_no_cycle_in_linear_chain(self):
        """Should not detect cycles in a linear chain."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "c.py"),
            ("c.py", "d.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        assert len(cycles) == 0

    def test_no_cycle_in_empty_graph(self):
        """Should handle an empty graph."""
        graph = _make_graph([])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        assert len(cycles) == 0

    def test_self_import_not_counted_as_cycle(self):
        """Self-imports should not be counted as cycles."""
        graph = _make_graph([
            ("a.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        # Self-imports are filtered out in adjacency building
        assert len(cycles) == 0

    def test_deduplicates_cycles(self):
        """Should not report the same cycle with different starting nodes."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        cycles = detector.detect_cycles()

        # Should only have 1 cycle, not 2 (a->b and b->a are the same cycle)
        assert len(cycles) == 1


class TestCycleViolations:
    """Tests for get_cycle_violations()."""

    def test_returns_violations_for_cycles(self):
        """Should return ArchitectureViolation objects for detected cycles."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        violations = detector.get_cycle_violations()

        assert len(violations) >= 1
        assert violations[0].type == "circular_dependency"
        assert violations[0].severity == "error"
        assert "a.py" in violations[0].description
        assert "b.py" in violations[0].description

    def test_skips_when_disabled(self):
        """Should return empty list when circular dependency check is disabled."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config(no_circular=False))
        violations = detector.get_cycle_violations()

        assert len(violations) == 0

    def test_inferred_config_produces_warnings(self):
        """Inferred configs should produce warnings."""
        graph = _make_graph([
            ("a.py", "b.py"),
            ("b.py", "a.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config(inferred=True))
        violations = detector.get_cycle_violations()

        if violations:
            assert all(v.severity == "warning" for v in violations)


class TestBoundedContextViolations:
    """Tests for check_bounded_context_violations()."""

    def test_detects_cross_context_import(self):
        """Should detect imports crossing bounded context boundaries."""
        graph = _make_graph([
            ("auth/login.py", "billing/invoice.py"),
        ])
        config = _make_config(
            bounded_contexts=[
                BoundedContextConfig(
                    name="auth",
                    patterns=["auth/**"],
                    allowed_cross_context_imports=["shared"],
                ),
                BoundedContextConfig(
                    name="billing",
                    patterns=["billing/**"],
                    allowed_cross_context_imports=["shared"],
                ),
            ]
        )

        detector = CircularDependencyDetector(graph, config)
        violations = detector.check_bounded_context_violations()

        assert len(violations) >= 1
        assert violations[0].type == "bounded_context"
        assert "auth" in violations[0].description
        assert "billing" in violations[0].description

    def test_allows_shared_imports(self):
        """Should allow imports from 'shared' context."""
        graph = _make_graph([
            ("auth/login.py", "shared/utils.py"),
        ])
        config = _make_config(
            bounded_contexts=[
                BoundedContextConfig(
                    name="auth",
                    patterns=["auth/**"],
                    allowed_cross_context_imports=["shared"],
                ),
                BoundedContextConfig(
                    name="shared",
                    patterns=["shared/**"],
                    allowed_cross_context_imports=[],
                ),
            ]
        )

        detector = CircularDependencyDetector(graph, config)
        violations = detector.check_bounded_context_violations()

        assert len(violations) == 0

    def test_allows_same_context_imports(self):
        """Should allow imports within the same context."""
        graph = _make_graph([
            ("auth/login.py", "auth/utils.py"),
        ])
        config = _make_config(
            bounded_contexts=[
                BoundedContextConfig(
                    name="auth",
                    patterns=["auth/**"],
                    allowed_cross_context_imports=["shared"],
                ),
            ]
        )

        detector = CircularDependencyDetector(graph, config)
        violations = detector.check_bounded_context_violations()

        assert len(violations) == 0

    def test_no_violations_without_contexts(self):
        """Should return empty list when no bounded contexts configured."""
        graph = _make_graph([
            ("auth/login.py", "billing/invoice.py"),
        ])
        detector = CircularDependencyDetector(graph, _make_config())
        violations = detector.check_bounded_context_violations()

        assert len(violations) == 0
