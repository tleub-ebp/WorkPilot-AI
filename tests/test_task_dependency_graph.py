"""Tests for Feature 9.2 — Task Dependency Graph.

40 tests covering:
- TaskNode: 3
- DependencyEdge: 2
- CriticalPath: 2
- GraphAnalysis: 2
- Task CRUD: 5
- Dependency management: 6
- Cycle detection: 3
- Topological sort: 3
- Critical path: 3
- Blocked/ready tasks: 3
- Root/leaf tasks: 2
- Parallelizable groups: 2
- Reactflow export: 2
- Mermaid export: 1
- Stats: 1
"""

import pytest

from apps.backend.scheduling.task_dependency_graph import (
    CriticalPath,
    DependencyEdge,
    GraphAnalysis,
    TaskDependencyGraph,
    TaskNode,
    TaskNodeStatus,
)

# ---------------------------------------------------------------------------
# TaskNode tests (3)
# ---------------------------------------------------------------------------

class TestTaskNode:
    def test_creation(self):
        n = TaskNode(task_id="t1", title="Login page", status="pending")
        assert n.task_id == "t1"
        assert n.title == "Login page"
        assert not n.is_completed

    def test_is_completed(self):
        n = TaskNode(status="completed")
        assert n.is_completed
        n2 = TaskNode(status="cancelled")
        assert n2.is_completed

    def test_to_dict(self):
        n = TaskNode(task_id="t1", title="Test", tags=["ui"])
        d = n.to_dict()
        assert d["task_id"] == "t1"
        assert "ui" in d["tags"]


# ---------------------------------------------------------------------------
# DependencyEdge tests (2)
# ---------------------------------------------------------------------------

class TestDependencyEdge:
    def test_creation(self):
        e = DependencyEdge(source_id="t2", target_id="t1")
        assert e.source_id == "t2"
        assert e.target_id == "t1"
        assert e.edge_id  # auto-generated

    def test_to_dict(self):
        e = DependencyEdge(source_id="a", target_id="b", label="blocks")
        d = e.to_dict()
        assert d["label"] == "blocks"


# ---------------------------------------------------------------------------
# CriticalPath tests (2)
# ---------------------------------------------------------------------------

class TestCriticalPath:
    def test_defaults(self):
        cp = CriticalPath()
        assert cp.path == []
        assert cp.total_estimated_hours == 0.0

    def test_to_dict(self):
        cp = CriticalPath(path=["t1", "t2"], total_estimated_hours=10.0)
        d = cp.to_dict()
        assert len(d["path"]) == 2


# ---------------------------------------------------------------------------
# GraphAnalysis tests (2)
# ---------------------------------------------------------------------------

class TestGraphAnalysis:
    def test_defaults(self):
        ga = GraphAnalysis()
        assert ga.total_tasks == 0
        assert not ga.has_cycles

    def test_to_dict(self):
        ga = GraphAnalysis(total_tasks=5, total_edges=3)
        d = ga.to_dict()
        assert d["total_tasks"] == 5


# ---------------------------------------------------------------------------
# Task CRUD (5)
# ---------------------------------------------------------------------------

class TestTaskCRUD:
    def test_add_task(self):
        g = TaskDependencyGraph()
        node = g.add_task("t1", "Task 1")
        assert node.task_id == "t1"
        assert g.get_task("t1").title == "Task 1"

    def test_add_duplicate_raises(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Task 1")
        with pytest.raises(ValueError, match="already exists"):
            g.add_task("t1", "Duplicate")

    def test_update_task(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Task 1", status="pending")
        updated = g.update_task("t1", status="in_progress", priority=1)
        assert updated.status == "in_progress"
        assert updated.priority == 1

    def test_remove_task(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Task 1")
        g.add_task("t2", "Task 2")
        g.add_dependency("t2", "t1")
        g.remove_task("t1")
        assert len(g.list_tasks()) == 1
        assert len(g.get_edges()) == 0

    def test_list_tasks_filter(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="completed")
        g.add_task("t2", "B", status="pending")
        g.add_task("t3", "C", status="completed")
        assert len(g.list_tasks(status="completed")) == 2


# ---------------------------------------------------------------------------
# Dependency management (6)
# ---------------------------------------------------------------------------

class TestDependencyManagement:
    def test_add_dependency(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        edge = g.add_dependency("t2", "t1")
        assert edge.source_id == "t2"
        assert edge.target_id == "t1"

    def test_get_dependencies(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_dependency("t2", "t1")
        deps = g.get_dependencies("t2")
        assert "t1" in deps

    def test_get_dependents(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_dependency("t2", "t1")
        dependents = g.get_dependents("t1")
        assert "t2" in dependents

    def test_remove_dependency(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_dependency("t2", "t1")
        g.remove_dependency("t2", "t1")
        assert len(g.get_dependencies("t2")) == 0
        assert len(g.get_edges()) == 0

    def test_self_dependency_raises(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        with pytest.raises(ValueError, match="cannot depend on itself"):
            g.add_dependency("t1", "t1")

    def test_unknown_task_raises(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        with pytest.raises(KeyError):
            g.add_dependency("t2", "t1")


# ---------------------------------------------------------------------------
# Cycle detection (3)
# ---------------------------------------------------------------------------

class TestCycleDetection:
    def test_cycle_prevented(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_dependency("t2", "t1")
        with pytest.raises(ValueError, match="cycle"):
            g.add_dependency("t1", "t2")

    def test_no_cycle_in_dag(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_task("t3", "C")
        g.add_dependency("t2", "t1")
        g.add_dependency("t3", "t2")
        cycles = g.detect_cycles()
        assert len(cycles) == 0

    def test_three_node_cycle_prevented(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_task("t3", "C")
        g.add_dependency("t2", "t1")
        g.add_dependency("t3", "t2")
        with pytest.raises(ValueError, match="cycle"):
            g.add_dependency("t1", "t3")


# ---------------------------------------------------------------------------
# Topological sort (3)
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_basic_sort(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_task("t3", "C")
        g.add_dependency("t2", "t1")
        g.add_dependency("t3", "t2")
        order = g.topological_sort()
        assert order.index("t1") < order.index("t2")
        assert order.index("t2") < order.index("t3")

    def test_independent_tasks(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        order = g.topological_sort()
        assert set(order) == {"t1", "t2"}

    def test_empty_graph(self):
        g = TaskDependencyGraph()
        assert g.topological_sort() == []


# ---------------------------------------------------------------------------
# Critical path (3)
# ---------------------------------------------------------------------------

class TestCriticalPath:
    def test_critical_path_simple(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Design", estimated_hours=2.0)
        g.add_task("t2", "Implement", estimated_hours=8.0)
        g.add_task("t3", "Test", estimated_hours=3.0)
        g.add_dependency("t2", "t1")
        g.add_dependency("t3", "t2")
        cp = g.get_critical_path()
        assert len(cp.path) >= 2
        assert cp.total_estimated_hours > 0

    def test_critical_path_bottleneck(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Quick", estimated_hours=1.0)
        g.add_task("t2", "Heavy", estimated_hours=20.0)
        g.add_dependency("t2", "t1")
        cp = g.get_critical_path()
        assert cp.bottleneck_task_id == "t2"

    def test_empty_graph_critical_path(self):
        g = TaskDependencyGraph()
        cp = g.get_critical_path()
        assert cp.path == []


# ---------------------------------------------------------------------------
# Blocked/ready tasks (3)
# ---------------------------------------------------------------------------

class TestBlockedReady:
    def test_blocked_tasks(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="pending")
        g.add_task("t2", "B", status="pending")
        g.add_dependency("t2", "t1")
        blocked = g.get_blocked_tasks()
        assert "t2" in blocked

    def test_ready_tasks(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="completed")
        g.add_task("t2", "B", status="pending")
        g.add_dependency("t2", "t1")
        ready = g.get_ready_tasks()
        assert "t2" in ready

    def test_task_unblocked_when_dep_completed(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="pending")
        g.add_task("t2", "B", status="pending")
        g.add_dependency("t2", "t1")
        assert "t2" in g.get_blocked_tasks()
        g.update_task("t1", status="completed")
        assert "t2" not in g.get_blocked_tasks()
        assert "t2" in g.get_ready_tasks()


# ---------------------------------------------------------------------------
# Root/leaf tasks (2)
# ---------------------------------------------------------------------------

class TestRootLeaf:
    def test_root_tasks(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Root")
        g.add_task("t2", "Child")
        g.add_dependency("t2", "t1")
        roots = g.get_root_tasks()
        assert "t1" in roots
        assert "t2" not in roots

    def test_leaf_tasks(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Root")
        g.add_task("t2", "Leaf")
        g.add_dependency("t2", "t1")
        leaves = g.get_leaf_tasks()
        assert "t2" in leaves
        assert "t1" not in leaves


# ---------------------------------------------------------------------------
# Parallelizable groups (2)
# ---------------------------------------------------------------------------

class TestParallelizableGroups:
    def test_groups(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A")
        g.add_task("t2", "B")
        g.add_task("t3", "C")
        g.add_dependency("t3", "t1")
        g.add_dependency("t3", "t2")
        groups = g.get_parallelizable_groups()
        # t1 and t2 should be in the same group (level 0), t3 in level 1
        assert len(groups) == 2
        assert set(groups[0]) == {"t1", "t2"}
        assert groups[1] == ["t3"]

    def test_empty_graph_groups(self):
        g = TaskDependencyGraph()
        assert g.get_parallelizable_groups() == []


# ---------------------------------------------------------------------------
# Reactflow export (2)
# ---------------------------------------------------------------------------

class TestReactflowExport:
    def test_export_structure(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="completed")
        g.add_task("t2", "B", status="in_progress")
        g.add_dependency("t2", "t1")
        export = g.export_reactflow()
        assert "nodes" in export
        assert "edges" in export
        assert len(export["nodes"]) == 2
        assert len(export["edges"]) == 1

    def test_export_node_data(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Login", status="completed", tags=["ui"])
        export = g.export_reactflow()
        node = export["nodes"][0]
        assert node["data"]["label"] == "Login"
        assert node["data"]["status"] == "completed"
        assert "position" in node


# ---------------------------------------------------------------------------
# Mermaid export (1)
# ---------------------------------------------------------------------------

class TestMermaidExport:
    def test_mermaid_output(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "Design")
        g.add_task("t2", "Code")
        g.add_dependency("t2", "t1")
        mermaid = g.export_mermaid()
        assert "graph TD" in mermaid
        assert "Design" in mermaid
        assert "Code" in mermaid


# ---------------------------------------------------------------------------
# Stats (1)
# ---------------------------------------------------------------------------

class TestStats:
    def test_get_stats(self):
        g = TaskDependencyGraph()
        g.add_task("t1", "A", status="completed")
        g.add_task("t2", "B", status="pending")
        g.add_dependency("t2", "t1")
        stats = g.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["total_edges"] == 1
        assert stats["ready_count"] == 1
