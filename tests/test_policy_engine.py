"""
Tests for Policy-as-Code governance engine.

Covers: PolicyLoader, PolicyEngine, SemanticAnalyzer, ApprovalGate.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from core.governance.approval_gate import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
)
from core.governance.policy_engine import (
    AgentAction,
    PolicyEngine,
    PolicyEvaluation,
    PolicyVerdict,
)
from core.governance.policy_loader import (
    PolicyFile,
    PolicyLoader,
    PolicyRule,
    PolicyValidationError,
    RuleAction,
    RuleScope,
)
from core.governance.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticViolation,
    ViolationType,
)

# =========================================================================
# Fixtures
# =========================================================================

VALID_POLICY_DICT = {
    "version": "1.0",
    "rules": [
        {
            "id": "no-migration-direct",
            "description": "Never modify migration files directly",
            "scope": "file_path",
            "pattern": "**/migrations/**",
            "action": "block",
            "message": "Use the Database Schema Agent for migrations",
        },
        {
            "id": "orm-only",
            "description": "All DB queries must go through the ORM",
            "scope": "code_pattern",
            "pattern": "raw_sql|execute_raw|cursor.execute",
            "action": "warn",
            "severity": "high",
        },
        {
            "id": "no-test-deletion",
            "description": "Never delete existing test files or test functions",
            "scope": "diff_semantic",
            "condition": "deleted_lines contain test function definition",
            "action": "block",
        },
        {
            "id": "dep-review",
            "description": "New dependencies require human approval",
            "scope": "file_path",
            "pattern": "package.json",
            "condition": "diff adds new dependency",
            "action": "require_approval",
            "approvers": ["tech-lead"],
        },
        {
            "id": "max-file-size",
            "description": "No generated file > 500 lines",
            "scope": "file_metric",
            "condition": "new_file_lines > 500",
            "action": "warn",
        },
    ],
}


@pytest.fixture
def loader():
    return PolicyLoader()


@pytest.fixture
def engine():
    return PolicyEngine()


@pytest.fixture
def analyzer():
    return SemanticAnalyzer()


@pytest.fixture
def policy_file(loader):
    return loader.load_from_dict(VALID_POLICY_DICT)


@pytest.fixture
def loaded_engine(engine):
    engine.load_from_dict(VALID_POLICY_DICT)
    return engine


# =========================================================================
# PolicyLoader tests
# =========================================================================


class TestPolicyLoader:
    def test_load_from_dict_valid(self, loader):
        pf = loader.load_from_dict(VALID_POLICY_DICT)
        assert isinstance(pf, PolicyFile)
        assert pf.version == "1.0"
        assert len(pf.rules) == 5

    def test_load_from_dict_invalid_version(self, loader):
        with pytest.raises(PolicyValidationError, match="Unsupported policy version"):
            loader.load_from_dict({"version": "99.0", "rules": []})

    def test_load_from_dict_missing_version(self, loader):
        with pytest.raises(PolicyValidationError, match="Unsupported policy version"):
            loader.load_from_dict({"rules": []})

    def test_load_from_dict_duplicate_rule_id(self, loader):
        data = {
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "warn", "pattern": "*.py"},
                {"id": "r1", "scope": "file_path", "action": "block", "pattern": "*.js"},
            ],
        }
        with pytest.raises(PolicyValidationError, match="Duplicate rule id"):
            loader.load_from_dict(data)

    def test_load_from_dict_invalid_scope(self, loader):
        data = {
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "invalid_scope", "action": "warn"},
            ],
        }
        with pytest.raises(PolicyValidationError, match="invalid scope"):
            loader.load_from_dict(data)

    def test_load_from_dict_invalid_action(self, loader):
        data = {
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "destroy"},
            ],
        }
        with pytest.raises(PolicyValidationError, match="invalid action"):
            loader.load_from_dict(data)

    def test_load_from_dict_missing_rule_id(self, loader):
        data = {
            "version": "1.0",
            "rules": [
                {"scope": "file_path", "action": "warn"},
            ],
        }
        with pytest.raises(PolicyValidationError, match="missing a valid 'id'"):
            loader.load_from_dict(data)

    def test_load_from_dict_rules_not_list(self, loader):
        data = {"version": "1.0", "rules": "not a list"}
        with pytest.raises(PolicyValidationError, match="'rules' must be a list"):
            loader.load_from_dict(data)

    def test_load_from_dict_empty_rules(self, loader):
        pf = loader.load_from_dict({"version": "1.0", "rules": []})
        assert pf.rules == []

    def test_load_from_dict_no_rules_key(self, loader):
        pf = loader.load_from_dict({"version": "1.0"})
        assert pf.rules == []

    def test_load_missing_file(self, loader, tmp_path):
        pf = loader.load(tmp_path)
        assert pf.rules == []
        assert pf.source_path is None

    def test_load_yaml_file(self, loader, tmp_path):
        policy_path = tmp_path / "workpilot.policy.yaml"
        policy_path.write_text(
            """
version: "1.0"
rules:
  - id: test-rule
    description: "A test rule"
    scope: file_path
    pattern: "*.secret"
    action: block
    message: "No secret files"
""",
            encoding="utf-8",
        )
        pf = loader.load(tmp_path)
        assert len(pf.rules) == 1
        assert pf.rules[0].id == "test-rule"
        assert pf.rules[0].action == RuleAction.BLOCK

    def test_load_caches_by_mtime(self, loader, tmp_path):
        policy_path = tmp_path / "workpilot.policy.yaml"
        policy_path.write_text(
            'version: "1.0"\nrules: []', encoding="utf-8"
        )
        pf1 = loader.load(tmp_path)
        pf2 = loader.load(tmp_path)
        assert pf1 is pf2  # same object from cache

    def test_get_rule_by_id(self, policy_file):
        rule = policy_file.get_rule("orm-only")
        assert rule is not None
        assert rule.action == RuleAction.WARN

    def test_get_rule_nonexistent(self, policy_file):
        assert policy_file.get_rule("nonexistent") is None

    def test_merge_policies_child_adds_rule(self, loader):
        parent = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "warn", "pattern": "*.py"},
            ],
        })
        child = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r2", "scope": "file_path", "action": "block", "pattern": "*.secret"},
            ],
        })
        merged = loader.merge(parent, child)
        assert len(merged.rules) == 2

    def test_merge_policies_child_cannot_weaken(self, loader):
        parent = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "block", "pattern": "*.py"},
            ],
        })
        child = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "warn", "pattern": "*.py"},
            ],
        })
        with pytest.raises(PolicyValidationError, match="cannot weaken"):
            loader.merge(parent, child)

    def test_merge_policies_child_can_tighten(self, loader):
        parent = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "warn", "pattern": "*.py"},
            ],
        })
        child = loader.load_from_dict({
            "version": "1.0",
            "rules": [
                {"id": "r1", "scope": "file_path", "action": "block", "pattern": "*.py"},
            ],
        })
        merged = loader.merge(parent, child)
        assert merged.get_rule("r1").action == RuleAction.BLOCK


# =========================================================================
# PolicyRule tests
# =========================================================================


class TestPolicyRule:
    def test_matches_file_path_glob(self):
        rule = PolicyRule(
            id="t", description="", scope=RuleScope.FILE_PATH,
            action=RuleAction.BLOCK, pattern="**/migrations/**"
        )
        assert rule.matches_file_path("src/migrations/0001.py")
        assert not rule.matches_file_path("src/models.py")

    def test_matches_code_pattern(self):
        rule = PolicyRule(
            id="t", description="", scope=RuleScope.CODE_PATTERN,
            action=RuleAction.WARN, pattern="raw_sql|cursor.execute"
        )
        assert rule.matches_code_pattern("db.raw_sql('SELECT 1')")
        assert rule.matches_code_pattern("cursor.execute('DROP TABLE')")
        assert not rule.matches_code_pattern("Model.objects.filter()")

    def test_evaluate_file_metric(self):
        rule = PolicyRule(
            id="t", description="", scope=RuleScope.FILE_METRIC,
            action=RuleAction.WARN, condition="new_file_lines > 500"
        )
        assert rule.evaluate_file_metric(501)
        assert not rule.evaluate_file_metric(500)
        assert not rule.evaluate_file_metric(100)


# =========================================================================
# PolicyEngine tests
# =========================================================================


class TestPolicyEngine:
    def test_evaluate_no_policies_loaded(self, engine):
        action = AgentAction(tool_name="write_file", file_path="test.py")
        result = engine.evaluate(action)
        assert result.verdict == PolicyVerdict.ALLOW
        assert result.is_allowed

    def test_evaluate_no_violations(self, loaded_engine):
        action = AgentAction(tool_name="write_file", file_path="src/models.py")
        result = loaded_engine.evaluate(action)
        assert result.verdict == PolicyVerdict.ALLOW

    def test_evaluate_file_path_block(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file", file_path="src/migrations/0001.py"
        )
        result = loaded_engine.evaluate(action)
        assert result.is_blocked
        assert result.verdict == PolicyVerdict.BLOCK
        assert "Database Schema Agent" in result.messages[0]

    def test_evaluate_code_pattern_warn(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file",
            file_path="src/service.py",
            file_content="result = cursor.execute('SELECT 1')",
        )
        result = loaded_engine.evaluate(action)
        assert result.verdict == PolicyVerdict.WARN
        assert not result.is_blocked

    def test_evaluate_diff_semantic_test_deletion(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file",
            file_path="tests/test_foo.py",
            diff_removed=["def test_important_feature():", "    assert True"],
        )
        result = loaded_engine.evaluate(action)
        assert result.is_blocked

    def test_evaluate_file_metric_warn(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file",
            file_path="src/big_file.py",
            new_file_lines=600,
        )
        result = loaded_engine.evaluate(action)
        assert result.verdict == PolicyVerdict.WARN

    def test_evaluate_require_approval(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file",
            file_path="package.json",
            diff_added=['"new-package": "^1.0.0"'],
        )
        result = loaded_engine.evaluate(action)
        assert result.requires_approval
        assert result.verdict == PolicyVerdict.REQUIRE_APPROVAL

    def test_most_restrictive_wins(self, loaded_engine):
        # File in migrations + has raw sql → block + warn → block wins
        action = AgentAction(
            tool_name="write_file",
            file_path="src/migrations/0001.py",
            file_content="cursor.execute('ALTER TABLE')",
        )
        result = loaded_engine.evaluate(action)
        assert result.verdict == PolicyVerdict.BLOCK

    def test_dry_run_does_not_log(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file", file_path="src/migrations/0001.py"
        )
        results = loaded_engine.dry_run([action])
        assert results[0].is_blocked
        assert len(loaded_engine.violation_log) == 0

    def test_evaluate_records_violations(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file", file_path="src/migrations/0001.py"
        )
        loaded_engine.evaluate(action)
        assert len(loaded_engine.violation_log) >= 1

    def test_violation_stats(self, loaded_engine):
        loaded_engine.evaluate(
            AgentAction(tool_name="w", file_path="src/migrations/0001.py")
        )
        loaded_engine.evaluate(
            AgentAction(tool_name="w", file_path="src/x.py", new_file_lines=600)
        )
        stats = loaded_engine.get_violation_stats()
        assert stats["block"] >= 1
        assert stats["warn"] >= 1

    def test_code_pattern_in_diff_added(self, loaded_engine):
        action = AgentAction(
            tool_name="write_file",
            file_path="src/service.py",
            diff_added=["result = execute_raw('SELECT 1')"],
        )
        result = loaded_engine.evaluate(action)
        assert result.verdict == PolicyVerdict.WARN


# =========================================================================
# SemanticAnalyzer tests
# =========================================================================


class TestSemanticAnalyzer:
    def test_detect_python_test_deletion(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="tests/test_foo.py",
            added_lines=[],
            removed_lines=["def test_login_success():", "    assert user.is_authenticated"],
        )
        assert any(v.violation_type == ViolationType.TEST_DELETION for v in violations)

    def test_detect_js_test_deletion(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="tests/foo.test.ts",
            added_lines=[],
            removed_lines=["it('should handle empty input', () => {"],
        )
        assert any(v.violation_type == ViolationType.TEST_DELETION for v in violations)

    def test_no_false_positive_non_test(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/main.py",
            added_lines=[],
            removed_lines=["def calculate_total():", "    return sum(items)"],
        )
        assert not any(v.violation_type == ViolationType.TEST_DELETION for v in violations)

    def test_detect_raw_sql(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/repo.py",
            added_lines=["cursor.execute('SELECT * FROM users')"],
            removed_lines=[],
        )
        assert any(v.violation_type == ViolationType.RAW_SQL for v in violations)

    def test_detect_typescript_any(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/component.tsx",
            added_lines=["const data: any = fetchData();"],
            removed_lines=[],
        )
        assert any(v.violation_type == ViolationType.TYPESCRIPT_ANY for v in violations)

    def test_no_ts_any_in_py_file(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/main.py",
            added_lines=["result: any = 5"],
            removed_lines=[],
        )
        assert not any(v.violation_type == ViolationType.TYPESCRIPT_ANY for v in violations)

    def test_detect_security_sensitive(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/handler.py",
            added_lines=["eval(user_input)"],
            removed_lines=[],
        )
        assert any(v.violation_type == ViolationType.SECURITY_SENSITIVE for v in violations)

    def test_detect_dependency_change(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="package.json",
            added_lines=['"lodash": "^4.17.21"'],
            removed_lines=[],
        )
        assert any(v.violation_type == ViolationType.DEPENDENCY_CHANGE for v in violations)

    def test_no_dep_change_for_non_manifest(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="src/utils.py",
            added_lines=["import os"],
            removed_lines=[],
        )
        assert not any(v.violation_type == ViolationType.DEPENDENCY_CHANGE for v in violations)

    def test_python_ast_eval_detection(self, analyzer):
        code = 'result = eval("2+2")\n'
        violations = analyzer.analyze_diff(
            file_path="src/danger.py",
            added_lines=[],
            removed_lines=[],
            full_content=code,
        )
        assert any(
            v.violation_type == ViolationType.SECURITY_SENSITIVE
            and "AST" in v.description
            for v in violations
        )

    def test_python_ast_syntax_error_graceful(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="bad.py",
            added_lines=[],
            removed_lines=[],
            full_content="def broken(:\n",
        )
        # Should not crash
        assert isinstance(violations, list)

    def test_detect_async_test_deletion(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="tests/test_async.py",
            added_lines=[],
            removed_lines=["async def test_async_handler():"],
        )
        assert any(v.violation_type == ViolationType.TEST_DELETION for v in violations)

    def test_detect_class_test_deletion(self, analyzer):
        violations = analyzer.analyze_diff(
            file_path="tests/test_models.py",
            added_lines=[],
            removed_lines=["class TestUserModel:"],
        )
        assert any(v.violation_type == ViolationType.TEST_DELETION for v in violations)


# =========================================================================
# ApprovalGate tests
# =========================================================================


class TestApprovalGate:
    def test_create_request(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="dep-review", action_summary="Add lodash")
        assert req.status == ApprovalStatus.PENDING
        assert req.rule_id == "dep-review"

    def test_approve_request(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="dep-review")
        gate.approve(req.id, approved_by="alice")
        assert gate.is_approved(req.id)
        assert req.resolved_by == "alice"

    def test_deny_request(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="dep-review")
        gate.deny(req.id, denied_by="bob", reason="Not needed")
        assert gate.is_denied(req.id)
        assert req.denial_reason == "Not needed"

    def test_cannot_approve_already_resolved(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="dep-review")
        gate.approve(req.id)
        with pytest.raises(ValueError, match="already approved"):
            gate.approve(req.id)

    def test_cannot_deny_already_resolved(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="dep-review")
        gate.deny(req.id)
        with pytest.raises(ValueError, match="already denied"):
            gate.deny(req.id)

    def test_list_pending(self):
        gate = ApprovalGate()
        gate.create_request(rule_id="r1")
        gate.create_request(rule_id="r2")
        r3 = gate.create_request(rule_id="r3")
        gate.approve(r3.id)
        pending = gate.list_pending()
        assert len(pending) == 2

    def test_list_all(self):
        gate = ApprovalGate()
        gate.create_request(rule_id="r1")
        r2 = gate.create_request(rule_id="r2")
        gate.approve(r2.id)
        assert len(gate.list_all()) == 2

    def test_clear_resolved(self):
        gate = ApprovalGate()
        gate.create_request(rule_id="r1")
        r2 = gate.create_request(rule_id="r2")
        gate.approve(r2.id)
        removed = gate.clear_resolved()
        assert removed == 1
        assert len(gate.list_all()) == 1

    def test_get_request(self):
        gate = ApprovalGate()
        req = gate.create_request(rule_id="r1")
        fetched = gate.get_request(req.id)
        assert fetched is not None
        assert fetched.rule_id == "r1"

    def test_get_request_nonexistent(self):
        gate = ApprovalGate()
        assert gate.get_request("nonexistent") is None

    def test_persistence(self, tmp_path):
        persistence_file = tmp_path / "approvals.json"
        gate = ApprovalGate(persistence_path=persistence_file)
        gate.create_request(rule_id="r1", action_summary="test")

        # Load from disk
        gate2 = ApprovalGate(persistence_path=persistence_file)
        assert len(gate2.list_all()) == 1
        assert gate2.list_all()[0].rule_id == "r1"

    def test_approval_request_serialization(self):
        req = ApprovalRequest(
            rule_id="r1",
            rule_description="Test rule",
            action_summary="Test action",
            approvers=["alice"],
        )
        data = req.to_dict()
        assert data["status"] == "pending"
        restored = ApprovalRequest.from_dict(data)
        assert restored.rule_id == "r1"
        assert restored.status == ApprovalStatus.PENDING

    def test_key_error_on_missing_request(self):
        gate = ApprovalGate()
        with pytest.raises(KeyError):
            gate.approve("nonexistent")


# =========================================================================
# Integration tests
# =========================================================================


class TestPolicyIntegration:
    """End-to-end tests combining loader + engine + analyzer."""

    def test_full_workflow_block_migration(self):
        engine = PolicyEngine()
        engine.load_from_dict(VALID_POLICY_DICT)

        action = AgentAction(
            tool_name="write_file",
            file_path="app/migrations/0042_add_field.py",
            file_content="ALTER TABLE users ADD COLUMN email VARCHAR(255);",
        )
        result = engine.evaluate(action)
        assert result.is_blocked
        assert len(result.violations) >= 1

    def test_full_workflow_allow_normal_file(self):
        engine = PolicyEngine()
        engine.load_from_dict(VALID_POLICY_DICT)

        action = AgentAction(
            tool_name="write_file",
            file_path="src/services/user_service.py",
            file_content="class UserService:\n    pass\n",
            new_file_lines=2,
        )
        result = engine.evaluate(action)
        assert result.is_allowed

    def test_semantic_analyzer_with_engine(self):
        analyzer = SemanticAnalyzer()
        violations = analyzer.analyze_diff(
            file_path="tests/test_auth.py",
            added_lines=[],
            removed_lines=[
                "def test_login_with_valid_credentials():",
                "    response = client.post('/login', data={'user': 'admin', 'pass': 'secret'})",
                "    assert response.status_code == 200",
            ],
        )
        assert len(violations) >= 1
        assert violations[0].violation_type == ViolationType.TEST_DELETION

    def test_approval_gate_with_engine(self):
        engine = PolicyEngine()
        engine.load_from_dict(VALID_POLICY_DICT)
        gate = ApprovalGate()

        action = AgentAction(
            tool_name="write_file",
            file_path="package.json",
            diff_added=['"new-dep": "^1.0.0"'],
        )
        result = engine.evaluate(action)

        if result.requires_approval:
            req = gate.create_request(
                rule_id=result.violations[0].rule.id,
                action_summary="Add new-dep to package.json",
                approvers=result.violations[0].rule.approvers,
            )
            assert req.status == ApprovalStatus.PENDING
            gate.approve(req.id, approved_by="tech-lead")
            assert gate.is_approved(req.id)
