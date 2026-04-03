"""Tests for Feature 8.4 — Migration de framework assistée.

40 tests covering:
- DetectedDependency: 2 tests (creation, to_dict)
- BreakingChange: 2 tests (creation, to_dict)
- MigrationStep: 3 tests (creation, to_dict, defaults)
- MigrationPlan: 3 tests (creation, progress, to_dict)
- StackAnalyzer: 4 tests (analyze_from_data, languages, frameworks, dependencies)
- Plan creation: 6 tests (react upgrade, express upgrade, js→ts, custom steps, unknown migration, framework switch)
- Plan management: 4 tests (get_plan, list_plans, update_step_status, list_by_status)
- Execution: 6 tests (execute success, dry_run, rollback, not found, step tracking, status update)
- Test generation: 3 tests (basic, breaking changes, empty plan)
- Results & Stats: 4 tests (get_results, get_results_by_id, stats, empty stats)
- Edge cases: 3 tests (multiple plans, plan progress, concurrent migrations)
"""

import json

import pytest

from apps.backend.agents.migration_agent import (
    BreakingChange,
    BreakingChangeType,
    DetectedDependency,
    MigrationAgent,
    MigrationPlan,
    MigrationResult,
    MigrationStatus,
    MigrationStep,
    MigrationType,
    StackAnalysis,
    StackAnalyzer,
    StepRisk,
)

# ---------------------------------------------------------------------------
# DetectedDependency tests
# ---------------------------------------------------------------------------

class TestDetectedDependency:
    def test_create(self):
        dep = DetectedDependency(name="react", current_version="^18.2.0", ecosystem="npm")
        assert dep.name == "react"
        assert dep.current_version == "^18.2.0"
        assert dep.dep_type == "production"

    def test_to_dict(self):
        dep = DetectedDependency(name="express", current_version="^4.18.0", dep_type="production")
        d = dep.to_dict()
        assert d["name"] == "express"
        assert d["dep_type"] == "production"


# ---------------------------------------------------------------------------
# BreakingChange tests
# ---------------------------------------------------------------------------

class TestBreakingChange:
    def test_create(self):
        bc = BreakingChange(
            change_id="bc-001",
            change_type="api_removed",
            description="ReactDOM.render removed",
            old_api="ReactDOM.render",
            new_api="createRoot",
            auto_fixable=True,
        )
        assert bc.change_id == "bc-001"
        assert bc.auto_fixable is True

    def test_to_dict(self):
        bc = BreakingChange(
            change_id="bc-001",
            change_type="api_removed",
            description="Test change",
        )
        d = bc.to_dict()
        assert d["change_id"] == "bc-001"
        assert isinstance(d["affected_files"], list)


# ---------------------------------------------------------------------------
# MigrationStep tests
# ---------------------------------------------------------------------------

class TestMigrationStep:
    def test_create(self):
        step = MigrationStep(
            step_id="step-001",
            order=1,
            title="Update dependencies",
            description="Update react to v19",
            step_type="dependency_update",
        )
        assert step.step_id == "step-001"
        assert step.order == 1
        assert step.status == "planned"

    def test_to_dict(self):
        step = MigrationStep(
            step_id="step-001", order=1,
            title="Test", description="Test step",
        )
        d = step.to_dict()
        assert d["step_id"] == "step-001"

    def test_defaults(self):
        step = MigrationStep(
            step_id="step-001", order=1,
            title="Test", description="desc",
        )
        assert step.risk == "low"
        assert step.step_type == "code_change"
        assert step.estimated_minutes == 5.0


# ---------------------------------------------------------------------------
# MigrationPlan tests
# ---------------------------------------------------------------------------

class TestMigrationPlan:
    def test_create(self):
        plan = MigrationPlan(
            plan_id="mig-0001",
            migration_type="version_upgrade",
            source_framework="react",
            source_version="18.2",
            target_framework="react",
            target_version="19.0",
        )
        assert plan.plan_id == "mig-0001"
        assert plan.status == "draft"

    def test_progress(self):
        plan = MigrationPlan(
            plan_id="mig-0001",
            migration_type="version_upgrade",
            source_framework="react",
            source_version="18",
            target_framework="react",
            target_version="19",
            steps=[
                MigrationStep(step_id="s1", order=1, title="A", description="A", status="completed"),
                MigrationStep(step_id="s2", order=2, title="B", description="B", status="planned"),
            ],
        )
        assert plan.progress_pct == 50.0
        assert plan.completed_steps == 1

    def test_to_dict(self):
        plan = MigrationPlan(
            plan_id="mig-0001",
            migration_type="version_upgrade",
            source_framework="react",
            source_version="18",
            target_framework="react",
            target_version="19",
        )
        d = plan.to_dict()
        assert d["plan_id"] == "mig-0001"
        assert "progress_pct" in d
        assert "completed_steps" in d


# ---------------------------------------------------------------------------
# StackAnalyzer tests
# ---------------------------------------------------------------------------

class TestStackAnalyzer:
    def test_analyze_from_data(self):
        analyzer = StackAnalyzer(".")
        analysis = analyzer.analyze_from_data(
            languages=["typescript", "python"],
            frameworks=["react", "express"],
        )
        assert "typescript" in analysis.detected_languages
        assert "react" in analysis.detected_frameworks

    def test_languages(self):
        analyzer = StackAnalyzer(".")
        analysis = analyzer.analyze_from_data(languages=["python", "javascript"])
        assert len(analysis.detected_languages) == 2

    def test_frameworks(self):
        analyzer = StackAnalyzer(".")
        analysis = analyzer.analyze_from_data(frameworks=["django", "vue"])
        assert "django" in analysis.detected_frameworks

    def test_dependencies(self):
        analyzer = StackAnalyzer(".")
        analysis = analyzer.analyze_from_data(
            dependencies=[
                {"name": "react", "current_version": "^18.2.0"},
                {"name": "express", "current_version": "^4.18.0"},
            ]
        )
        assert len(analysis.dependencies) == 2
        assert analysis.dependencies[0].name == "react"


# ---------------------------------------------------------------------------
# Plan creation tests
# ---------------------------------------------------------------------------

class TestPlanCreation:
    def test_react_upgrade(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18.2", "19.0")
        assert plan.source_framework == "react"
        assert plan.target_version == "19.0"
        assert len(plan.steps) > 0
        assert len(plan.breaking_changes) > 0

    def test_express_upgrade(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("express", "4.18", "5.0")
        assert plan.source_framework == "express"
        assert len(plan.breaking_changes) >= 1

    def test_js_to_typescript(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan(
            "javascript", "es5", "typescript",
            target_framework="typescript",
            migration_type="language_migration",
        )
        assert plan.migration_type == "language_migration"
        assert plan.target_framework == "typescript"
        assert len(plan.breaking_changes) >= 1

    def test_custom_steps(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan(
            "react", "18", "19",
            custom_steps=[
                {"title": "Update SSR config", "description": "Update server rendering", "risk": "high"},
            ]
        )
        titles = [s.title for s in plan.steps]
        assert any("SSR" in t for t in titles)

    def test_unknown_migration(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("unknown_fw", "1.0", "2.0")
        assert plan.plan_id is not None
        assert len(plan.breaking_changes) == 0
        # Still has backup and test steps
        assert len(plan.steps) >= 2

    def test_framework_switch(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan(
            "express", "4", "1",
            target_framework="fastify",
            migration_type="framework_switch",
        )
        assert plan.target_framework == "fastify"
        assert plan.migration_type == "framework_switch"


# ---------------------------------------------------------------------------
# Plan management tests
# ---------------------------------------------------------------------------

class TestPlanManagement:
    def test_get_plan(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        retrieved = agent.get_plan(plan.plan_id)
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id

    def test_list_plans(self):
        agent = MigrationAgent()
        agent.create_migration_plan("react", "18", "19")
        agent.create_migration_plan("express", "4", "5")
        plans = agent.list_plans()
        assert len(plans) == 2

    def test_update_step_status(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        step = plan.steps[0]
        updated = agent.update_step_status(plan.plan_id, step.step_id, "completed")
        assert updated is not None
        assert updated.status == "completed"

    def test_list_plans_by_status(self):
        agent = MigrationAgent()
        agent.create_migration_plan("react", "18", "19")
        p2 = agent.create_migration_plan("express", "4", "5")
        p2.status = "completed"
        drafts = agent.list_plans(status="draft")
        assert len(drafts) == 1


# ---------------------------------------------------------------------------
# Execution tests
# ---------------------------------------------------------------------------

class TestExecution:
    def test_execute_success(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        result = agent.execute_migration(plan.plan_id)
        assert result.success is True
        assert result.steps_completed == len(plan.steps)
        assert result.steps_failed == 0

    def test_dry_run(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        result = agent.execute_migration(plan.plan_id, dry_run=True)
        assert result.success is True
        assert result.steps_completed == len(plan.steps)

    def test_rollback(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        agent.execute_migration(plan.plan_id)
        result = agent.rollback_migration(plan.plan_id)
        assert result.rollback_performed is True
        assert plan.status == "rolled_back"

    def test_plan_not_found(self):
        agent = MigrationAgent()
        result = agent.execute_migration("nonexistent")
        assert result.success is False
        assert len(result.errors) > 0

    def test_step_tracking(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        agent.execute_migration(plan.plan_id)
        for step in plan.steps:
            assert step.status == "completed"

    def test_plan_status_update(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        assert plan.status == "draft"
        agent.execute_migration(plan.plan_id)
        assert plan.status == "completed"


# ---------------------------------------------------------------------------
# Test generation tests
# ---------------------------------------------------------------------------

class TestTestGeneration:
    def test_generates_test_code(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        result = agent.execute_migration(plan.plan_id)
        assert result.test_code is not None
        assert "def test_" in result.test_code
        assert result.tests_generated > 0

    def test_includes_breaking_changes(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        result = agent.execute_migration(plan.plan_id)
        assert "breaking_change" in result.test_code.lower() or "migration" in result.test_code.lower()

    def test_empty_plan(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("unknown_fw", "1.0", "2.0")
        result = agent.execute_migration(plan.plan_id)
        assert result.test_code is not None


# ---------------------------------------------------------------------------
# Results & Stats tests
# ---------------------------------------------------------------------------

class TestResultsAndStats:
    def test_get_results(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        agent.execute_migration(plan.plan_id)
        results = agent.get_results()
        assert len(results) == 1

    def test_get_results_by_id(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        agent.execute_migration(plan.plan_id)
        results = agent.get_results(plan.plan_id)
        assert len(results) == 1
        assert results[0].plan_id == plan.plan_id

    def test_stats(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        agent.execute_migration(plan.plan_id)
        stats = agent.get_stats()
        assert stats["total_plans"] == 1
        assert stats["successful_migrations"] == 1

    def test_stats_empty(self):
        agent = MigrationAgent()
        stats = agent.get_stats()
        assert stats["total_plans"] == 0
        assert stats["total_migrations_executed"] == 0


# ---------------------------------------------------------------------------
# Edge cases tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_multiple_plans(self):
        agent = MigrationAgent()
        p1 = agent.create_migration_plan("react", "18", "19")
        p2 = agent.create_migration_plan("express", "4", "5")
        p3 = agent.create_migration_plan("javascript", "es5", "typescript", target_framework="typescript")
        assert len(agent.list_plans()) == 3
        assert p1.plan_id != p2.plan_id != p3.plan_id

    def test_plan_progress_tracking(self):
        agent = MigrationAgent()
        plan = agent.create_migration_plan("react", "18", "19")
        assert plan.progress_pct == 0.0
        agent.execute_migration(plan.plan_id)
        assert plan.progress_pct == 100.0

    def test_concurrent_migrations(self):
        agent = MigrationAgent()
        p1 = agent.create_migration_plan("react", "18", "19")
        p2 = agent.create_migration_plan("express", "4", "5")
        r1 = agent.execute_migration(p1.plan_id)
        r2 = agent.execute_migration(p2.plan_id)
        assert r1.success is True
        assert r2.success is True
        stats = agent.get_stats()
        assert stats["successful_migrations"] == 2
