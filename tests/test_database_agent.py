"""
Tests for Database Schema Agent — Zero-downtime migration planner.

Covers: SchemaAnalyzer, MigrationPlanner, LockDetector, BackfillEstimator, RollbackGenerator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from database_agent.backfill_estimator import (
    BackfillEstimator,
    OperationType,
)
from database_agent.lock_detector import LockDetector, LockSeverity
from database_agent.migration_planner import (
    MigrationPhase,
    MigrationPlan,
    MigrationPlanner,
    MigrationStep,
    MigrationType,
)
from database_agent.rollback_generator import RollbackGenerator, RollbackScript
from database_agent.schema_analyzer import (
    ColumnInfo,
    DatabaseEngine,
    SchemaAnalyzer,
    TableInfo,
)

# =========================================================================
# SchemaAnalyzer tests
# =========================================================================


class TestSchemaAnalyzer:
    def test_detect_postgresql(self):
        assert SchemaAnalyzer.detect_engine("postgresql://user:password@localhost/mydb") == DatabaseEngine.POSTGRESQL

    def test_detect_mysql(self):
        assert SchemaAnalyzer.detect_engine("mysql://root:password@localhost/mydb") == DatabaseEngine.MYSQL

    def test_detect_sqlite(self):
        assert SchemaAnalyzer.detect_engine("sqlite:///app.db") == DatabaseEngine.SQLITE
        assert SchemaAnalyzer.detect_engine("data.sqlite3") == DatabaseEngine.SQLITE

    def test_detect_sqlserver(self):
        assert SchemaAnalyzer.detect_engine("mssql://sa:password@localhost") == DatabaseEngine.SQLSERVER

    def test_detect_unknown(self):
        assert SchemaAnalyzer.detect_engine("redis://localhost") == DatabaseEngine.UNKNOWN

    def test_analyze_ddl_simple(self):
        analyzer = SchemaAnalyzer()
        ddl = """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        tables = analyzer.analyze_ddl(ddl)
        assert len(tables) == 1
        t = tables[0]
        assert t.name == "users"
        assert len(t.columns) == 4

    def test_analyze_ddl_column_properties(self):
        analyzer = SchemaAnalyzer()
        ddl = "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price DECIMAL(10,2));"
        tables = analyzer.analyze_ddl(ddl)
        t = tables[0]
        id_col = t.get_column("id")
        assert id_col is not None
        assert id_col.is_primary_key

        name_col = t.get_column("name")
        assert name_col is not None
        assert not name_col.nullable

    def test_analyze_ddl_foreign_key(self):
        analyzer = SchemaAnalyzer()
        ddl = "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id));"
        tables = analyzer.analyze_ddl(ddl)
        t = tables[0]
        fk_col = t.get_column("user_id")
        assert fk_col is not None
        assert fk_col.foreign_key == "users.id"

    def test_analyze_ddl_multiple_tables(self):
        analyzer = SchemaAnalyzer()
        ddl = """
        CREATE TABLE a (id INTEGER PRIMARY KEY);
        CREATE TABLE b (id INTEGER PRIMARY KEY, a_id INTEGER);
        """
        tables = analyzer.analyze_ddl(ddl)
        assert len(tables) == 2

    def test_column_type_checks(self):
        text_col = ColumnInfo(name="n", data_type="VARCHAR(255)")
        assert text_col.is_text_type
        assert not text_col.is_numeric_type

        int_col = ColumnInfo(name="n", data_type="INTEGER")
        assert int_col.is_numeric_type
        assert not int_col.is_text_type

    def test_table_get_primary_keys(self):
        t = TableInfo(name="t", columns=[
            ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
            ColumnInfo(name="name", data_type="TEXT"),
        ])
        pks = t.get_primary_keys()
        assert len(pks) == 1
        assert pks[0].name == "id"

    def test_classify_change_destructive(self):
        analyzer = SchemaAnalyzer()
        t = TableInfo(name="users")
        assert analyzer.classify_change(t, "rename column email to mail") == "destructive"
        assert analyzer.classify_change(t, "drop column legacy_field") == "destructive"

    def test_classify_change_non_destructive(self):
        analyzer = SchemaAnalyzer()
        t = TableInfo(name="users")
        assert analyzer.classify_change(t, "add column email_verified boolean") == "non_destructive"
        assert analyzer.classify_change(t, "create index on email") == "non_destructive"

    def test_max_length_parsing(self):
        analyzer = SchemaAnalyzer()
        ddl = "CREATE TABLE t (name VARCHAR(100));"
        tables = analyzer.analyze_ddl(ddl)
        col = tables[0].get_column("name")
        assert col is not None
        assert col.max_length == 100

    def test_get_column_nonexistent(self):
        t = TableInfo(name="t", columns=[ColumnInfo(name="id", data_type="INT")])
        assert t.get_column("nonexistent") is None


# =========================================================================
# MigrationPlanner tests
# =========================================================================


class TestMigrationPlanner:
    def test_add_nullable_column_single_step(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_column(
            "users", ColumnInfo(name="bio", data_type="TEXT", nullable=True)
        )
        assert plan.migration_type == MigrationType.NON_DESTRUCTIVE
        assert plan.step_count == 1
        assert "ADD COLUMN" in plan.steps[0].sql_up

    def test_add_column_with_default_single_step(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_column(
            "users", ColumnInfo(name="active", data_type="BOOLEAN", nullable=True, default="true")
        )
        assert plan.migration_type == MigrationType.NON_DESTRUCTIVE
        assert "DEFAULT" in plan.steps[0].sql_up

    def test_add_not_null_column_multi_step(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_column(
            "users",
            ColumnInfo(name="email", data_type="VARCHAR(255)", nullable=False),
            estimated_rows=1_000_000,
        )
        assert plan.migration_type == MigrationType.DESTRUCTIVE
        assert plan.step_count >= 3  # expand, migrate, contract

    def test_drop_column_multi_step(self):
        planner = MigrationPlanner()
        plan = planner.plan_drop_column("users", "legacy_field")
        assert plan.is_destructive
        assert plan.step_count >= 3
        assert any("DROP COLUMN" in s.sql_up for s in plan.steps)
        assert len(plan.warnings) > 0  # "data will be lost"

    def test_rename_column_four_steps(self):
        planner = MigrationPlanner()
        plan = planner.plan_rename_column(
            "users", "email", "email_address", data_type="VARCHAR(255)",
            estimated_rows=500_000,
        )
        assert plan.is_destructive
        assert plan.step_count == 4
        phases = [s.phase for s in plan.steps]
        assert MigrationPhase.EXPAND in phases
        assert MigrationPhase.MIGRATE in phases
        assert MigrationPhase.SWITCH in phases
        assert MigrationPhase.CONTRACT in phases

    def test_change_type_multi_step(self):
        planner = MigrationPlanner()
        plan = planner.plan_change_type(
            "orders", "amount", "VARCHAR(50)", "DECIMAL(10,2)",
            estimated_rows=100_000,
        )
        assert plan.is_destructive
        assert plan.step_count == 4
        assert any("CAST" in s.sql_up for s in plan.steps)

    def test_add_index_concurrent(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_index(
            "users", "idx_users_email", ["email"], concurrent=True
        )
        assert plan.migration_type == MigrationType.NON_DESTRUCTIVE
        assert "CONCURRENTLY" in plan.steps[0].sql_up
        assert not plan.steps[0].requires_lock

    def test_add_index_non_concurrent_warns(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_index(
            "users", "idx_users_email", ["email"], concurrent=False
        )
        assert plan.steps[0].requires_lock
        assert len(plan.warnings) > 0

    def test_add_unique_index(self):
        planner = MigrationPlanner()
        plan = planner.plan_add_index(
            "users", "idx_users_email_unique", ["email"], unique=True
        )
        assert "UNIQUE" in plan.steps[0].sql_up

    def test_estimated_total_seconds(self):
        planner = MigrationPlanner()
        plan = planner.plan_rename_column(
            "users", "a", "b", estimated_rows=1_000_000
        )
        assert plan.estimated_total_seconds > 0


# =========================================================================
# LockDetector tests
# =========================================================================


class TestLockDetector:
    def test_detect_non_concurrent_index(self):
        detector = LockDetector()
        warnings = detector.analyze("CREATE INDEX idx_email ON users (email);")
        assert len(warnings) >= 1
        assert warnings[0].severity == LockSeverity.HIGH

    def test_concurrent_index_no_warning(self):
        detector = LockDetector()
        warnings = detector.analyze("CREATE INDEX CONCURRENTLY idx_email ON users (email);")
        assert len(warnings) == 0

    def test_detect_drop_column(self):
        detector = LockDetector()
        warnings = detector.analyze("ALTER TABLE users DROP COLUMN legacy;")
        assert len(warnings) >= 1

    def test_detect_type_change(self):
        detector = LockDetector()
        warnings = detector.analyze("ALTER TABLE orders ALTER COLUMN amount TYPE DECIMAL(10,2);")
        assert any(w.severity == LockSeverity.CRITICAL for w in warnings)

    def test_detect_add_not_null_without_default(self):
        detector = LockDetector()
        warnings = detector.analyze("ALTER TABLE users ADD COLUMN age INTEGER NOT NULL;")
        assert any(w.severity == LockSeverity.HIGH for w in warnings)

    def test_has_critical_locks(self):
        detector = LockDetector()
        assert detector.has_critical_locks("ALTER TABLE t ALTER COLUMN c TYPE INT;")
        assert not detector.has_critical_locks("ALTER TABLE t ADD COLUMN c TEXT;")

    def test_suggest_safe_alternative(self):
        detector = LockDetector()
        alt = detector.suggest_safe_alternative("CREATE INDEX idx ON users (email);")
        assert alt is not None
        assert "CONCURRENTLY" in alt

    def test_no_alternative_for_safe_sql(self):
        detector = LockDetector()
        alt = detector.suggest_safe_alternative("SELECT 1;")
        assert alt is None

    def test_multiple_statements(self):
        detector = LockDetector()
        sql = """
        CREATE INDEX idx1 ON users (email);
        ALTER TABLE orders DROP COLUMN old_field;
        """
        warnings = detector.analyze(sql)
        assert len(warnings) >= 2

    def test_detect_fk_constraint(self):
        detector = LockDetector()
        sql = "ALTER TABLE orders ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id);"
        warnings = detector.analyze(sql)
        assert len(warnings) >= 1
        assert warnings[0].severity == LockSeverity.HIGH

    def test_detect_rename(self):
        detector = LockDetector()
        warnings = detector.analyze("ALTER TABLE users RENAME TO accounts;")
        assert len(warnings) >= 1


# =========================================================================
# BackfillEstimator tests
# =========================================================================


class TestBackfillEstimator:
    def test_simple_update_estimate(self):
        estimator = BackfillEstimator()
        est = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=1_000_000)
        assert est.estimated_seconds == pytest.approx(10.0, rel=0.1)
        assert est.estimated_rows == 1_000_000
        assert est.batch_count > 0

    def test_zero_rows(self):
        estimator = BackfillEstimator()
        est = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=0)
        assert est.estimated_seconds == 0
        assert "instant" in est.human_readable

    def test_human_readable_formatting(self):
        estimator = BackfillEstimator()
        # Small
        est_small = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=500)
        assert "500 rows" in est_small.human_readable

        # Thousands
        est_k = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=50_000)
        assert "K" in est_k.human_readable

        # Millions
        est_m = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=8_000_000)
        assert "M" in est_m.human_readable

    def test_estimated_minutes(self):
        estimator = BackfillEstimator()
        est = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=6_000_000)
        assert est.estimated_minutes == pytest.approx(1.0, rel=0.1)

    def test_index_build_estimate(self):
        estimator = BackfillEstimator()
        est = estimator.estimate_index_build(row_count=10_000_000, concurrent=True)
        assert est.estimated_seconds > 0
        assert est.estimated_lock_ms == 0  # concurrent = no lock

    def test_non_concurrent_index_has_lock(self):
        estimator = BackfillEstimator()
        est = estimator.estimate_index_build(row_count=10_000_000, concurrent=False)
        assert est.estimated_lock_ms > 0

    def test_multi_column_index_slower(self):
        estimator = BackfillEstimator()
        est1 = estimator.estimate_index_build(row_count=1_000_000, column_count=1)
        est3 = estimator.estimate_index_build(row_count=1_000_000, column_count=3)
        assert est3.estimated_seconds > est1.estimated_seconds

    def test_custom_throughput(self):
        estimator = BackfillEstimator()
        est = estimator.estimate(
            OperationType.SIMPLE_UPDATE, row_count=1_000_000,
            custom_throughput=500_000,
        )
        assert est.estimated_seconds == pytest.approx(2.0, rel=0.01)

    def test_cast_update_slower_than_simple(self):
        estimator = BackfillEstimator()
        simple = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=1_000_000)
        cast = estimator.estimate(OperationType.CAST_UPDATE, row_count=1_000_000)
        assert cast.estimated_seconds > simple.estimated_seconds


# =========================================================================
# RollbackGenerator tests
# =========================================================================


class TestRollbackGenerator:
    def _make_plan(self) -> MigrationPlan:
        return MigrationPlan(
            table_name="users",
            change_description="Rename email to email_address",
            migration_type=MigrationType.DESTRUCTIVE,
            steps=[
                MigrationStep(
                    phase=MigrationPhase.EXPAND,
                    description="Add column email_address",
                    sql_up="ALTER TABLE users ADD COLUMN email_address VARCHAR(255);",
                    sql_down="ALTER TABLE users DROP COLUMN email_address;",
                ),
                MigrationStep(
                    phase=MigrationPhase.MIGRATE,
                    description="Backfill data",
                    sql_up="UPDATE users SET email_address = email;",
                    sql_down="UPDATE users SET email = email_address;",
                ),
                MigrationStep(
                    phase=MigrationPhase.CONTRACT,
                    description="Drop old column",
                    sql_up="ALTER TABLE users DROP COLUMN email;",
                    sql_down="ALTER TABLE users ADD COLUMN email VARCHAR(255);",
                    is_reversible=True,
                ),
            ],
        )

    def test_generate_rollback(self):
        gen = RollbackGenerator()
        plan = self._make_plan()
        rollback = gen.generate(plan)
        assert rollback.is_fully_reversible
        assert len(rollback.steps) == 3

    def test_rollback_steps_reversed(self):
        gen = RollbackGenerator()
        plan = self._make_plan()
        rollback = gen.generate(plan)
        # Last plan step should be first in rollback
        assert "Drop old column" in rollback.steps[0]

    def test_rollback_to_sql(self):
        gen = RollbackGenerator()
        plan = self._make_plan()
        rollback = gen.generate(plan)
        sql = rollback.to_sql()
        assert "BEGIN;" in sql
        assert "COMMIT;" in sql
        assert "Rollback script for:" in sql

    def test_non_reversible_step(self):
        gen = RollbackGenerator()
        plan = MigrationPlan(
            table_name="t",
            change_description="Type change",
            migration_type=MigrationType.DESTRUCTIVE,
            steps=[
                MigrationStep(
                    phase=MigrationPhase.CONTRACT,
                    description="Drop and rename",
                    sql_up="ALTER TABLE t DROP COLUMN old;",
                    sql_down="-- Manual restoration required",
                    is_reversible=False,
                ),
            ],
        )
        rollback = gen.generate(plan)
        assert not rollback.is_fully_reversible
        assert len(rollback.warnings) > 0

    def test_validate_rollback_issues(self):
        gen = RollbackGenerator()
        plan = MigrationPlan(
            table_name="t",
            change_description="Test",
            migration_type=MigrationType.DESTRUCTIVE,
            steps=[
                MigrationStep(
                    phase=MigrationPhase.CONTRACT,
                    description="Irreversible",
                    sql_up="DROP TABLE t;",
                    sql_down="",
                    is_reversible=False,
                ),
            ],
        )
        rollback = gen.generate(plan)
        issues = RollbackGenerator.validate_rollback(rollback)
        assert len(issues) >= 1

    def test_validate_empty_rollback(self):
        issues = RollbackGenerator.validate_rollback(
            RollbackScript(plan_description="empty", steps=[])
        )
        assert any("no steps" in i.lower() for i in issues)

    def test_generate_multi(self):
        gen = RollbackGenerator()
        plans = [self._make_plan(), self._make_plan()]
        rollbacks = gen.generate_multi(plans)
        assert len(rollbacks) == 2


# =========================================================================
# Integration tests
# =========================================================================


class TestDatabaseAgentIntegration:
    def test_full_workflow_add_nullable_column(self):
        analyzer = SchemaAnalyzer()
        planner = MigrationPlanner(analyzer=analyzer)
        detector = LockDetector()
        gen = RollbackGenerator()

        plan = planner.plan_add_column(
            "users", ColumnInfo(name="avatar_url", data_type="TEXT", nullable=True)
        )
        assert not plan.is_destructive

        # Check locks
        for step in plan.steps:
            warnings = detector.analyze(step.sql_up)
            assert not any(w.severity == LockSeverity.CRITICAL for w in warnings)

        # Generate rollback
        rollback = gen.generate(plan)
        assert rollback.is_fully_reversible

    def test_full_workflow_rename_column(self):
        planner = MigrationPlanner()
        detector = LockDetector()
        estimator = BackfillEstimator()
        gen = RollbackGenerator()

        plan = planner.plan_rename_column(
            "users", "email", "primary_email",
            data_type="VARCHAR(255)", estimated_rows=5_000_000,
        )
        assert plan.is_destructive
        assert plan.step_count == 4

        # Estimate backfill
        est = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=5_000_000)
        assert est.estimated_seconds > 0

        # Check for locks
        all_warnings = []
        for step in plan.steps:
            all_warnings.extend(detector.analyze(step.sql_up))

        # Generate rollback
        rollback = gen.generate(plan)
        sql = rollback.to_sql()
        assert "BEGIN;" in sql

    def test_ddl_to_migration_plan(self):
        analyzer = SchemaAnalyzer()
        planner = MigrationPlanner(analyzer=analyzer)

        ddl = "CREATE TABLE products (id SERIAL PRIMARY KEY, name TEXT NOT NULL, price DECIMAL(10,2));"
        tables = analyzer.analyze_ddl(ddl)
        assert len(tables) == 1

        # Plan adding a column to the parsed table
        plan = planner.plan_add_column(
            tables[0].name,
            ColumnInfo(name="description", data_type="TEXT", nullable=True),
        )
        assert plan.table_name == "products"
        assert not plan.is_destructive
