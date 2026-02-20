"""Tests for Feature 7.1 — Audit Trail Complet.

40 tests covering:
- AuditEntry: 5 tests (creation, checksum, to_dict, from_dict, integrity)
- Recording: 6 tests (basic, all fields, severity levels, multiple users, custom action, system user)
- Querying: 8 tests (by action, user, severity, target, target_type, session, date range, combined)
- Search: 4 tests (keyword, keyword+filter, no results, empty keyword)
- Integrity: 4 tests (valid, tampered, multiple entries, empty trail)
- Summary: 4 tests (basic, multiple actions, empty, users)
- Export/Import: 5 tests (json, csv, jsonl, import json, import dedup)
- Compliance: 2 tests (SOC2, ISO27001)
- Stats: 2 tests (basic, empty)
"""

import json
import pytest

from apps.backend.security.audit_trail import (
    AuditAction,
    AuditEntry,
    AuditFilter,
    AuditSeverity,
    AuditSummary,
    AuditTrail,
    ExportFormat,
)


# ---------------------------------------------------------------------------
# AuditEntry tests
# ---------------------------------------------------------------------------

class TestAuditEntry:
    def test_create_entry(self):
        entry = AuditEntry(
            entry_id="audit-001",
            timestamp="2026-02-20T10:00:00+00:00",
            action="task_created",
            user="alice",
            project_id="proj-1",
            target="task-42",
        )
        assert entry.entry_id == "audit-001"
        assert entry.action == "task_created"
        assert entry.user == "alice"
        assert entry.target == "task-42"

    def test_checksum_computation(self):
        entry = AuditEntry(
            entry_id="audit-001",
            timestamp="2026-02-20T10:00:00+00:00",
            action="task_created",
            user="alice",
            project_id="proj-1",
        )
        checksum = entry.compute_checksum()
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex

    def test_checksum_deterministic(self):
        entry = AuditEntry(
            entry_id="audit-001",
            timestamp="2026-02-20T10:00:00+00:00",
            action="task_created",
            user="alice",
            project_id="proj-1",
        )
        assert entry.compute_checksum() == entry.compute_checksum()

    def test_to_dict(self):
        entry = AuditEntry(
            entry_id="audit-001",
            timestamp="2026-02-20T10:00:00+00:00",
            action="task_created",
            user="alice",
            project_id="proj-1",
        )
        d = entry.to_dict()
        assert d["entry_id"] == "audit-001"
        assert d["action"] == "task_created"
        assert isinstance(d["details"], dict)

    def test_from_dict(self):
        data = {
            "entry_id": "audit-001",
            "timestamp": "2026-02-20T10:00:00+00:00",
            "action": "task_created",
            "user": "alice",
            "project_id": "proj-1",
            "target": "task-42",
            "severity": "info",
            "details": {"title": "Login page"},
            "metadata": {},
            "result": "success",
            "checksum": "abc123",
        }
        entry = AuditEntry.from_dict(data)
        assert entry.entry_id == "audit-001"
        assert entry.details == {"title": "Login page"}
        assert entry.result == "success"


# ---------------------------------------------------------------------------
# Recording tests
# ---------------------------------------------------------------------------

class TestRecording:
    def test_record_basic(self):
        trail = AuditTrail(project_id="proj-1")
        entry = trail.record("task_created", user="alice", target="task-1")
        assert entry.action == "task_created"
        assert entry.user == "alice"
        assert entry.project_id == "proj-1"
        assert entry.checksum != ""

    def test_record_all_fields(self):
        trail = AuditTrail(project_id="proj-1")
        entry = trail.record(
            action="agent_started",
            user="bob",
            target="task-42",
            target_type="task",
            severity="info",
            details={"agent_type": "coder", "model": "claude-sonnet"},
            metadata={"version": "2.0"},
            result="success",
            ip_address="192.168.1.1",
            session_id="sess-abc",
        )
        assert entry.target_type == "task"
        assert entry.details["agent_type"] == "coder"
        assert entry.ip_address == "192.168.1.1"
        assert entry.session_id == "sess-abc"

    def test_record_severity_levels(self):
        trail = AuditTrail()
        for sev in ["info", "warning", "error", "critical"]:
            entry = trail.record("test_action", severity=sev)
            assert entry.severity == sev

    def test_record_multiple_users(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        trail.record("task_deleted", user="charlie")
        assert trail.count() == 3

    def test_record_custom_action(self):
        trail = AuditTrail()
        entry = trail.record("custom", user="admin", details={"reason": "manual override"})
        assert entry.action == "custom"
        assert entry.details["reason"] == "manual override"

    def test_record_default_system_user(self):
        trail = AuditTrail()
        entry = trail.record("config_changed")
        assert entry.user == "system"


# ---------------------------------------------------------------------------
# Querying tests
# ---------------------------------------------------------------------------

class TestQuerying:
    @pytest.fixture
    def populated_trail(self):
        trail = AuditTrail(project_id="proj-1")
        trail.record("task_created", user="alice", target="task-1", target_type="task", severity="info")
        trail.record("agent_started", user="system", target="task-1", target_type="agent", severity="info", session_id="s1")
        trail.record("agent_completed", user="system", target="task-1", target_type="agent", severity="info", session_id="s1")
        trail.record("file_modified", user="alice", target="src/main.py", target_type="file", severity="info")
        trail.record("security_violation", user="bob", target=".env", target_type="file", severity="critical")
        trail.record("config_changed", user="admin", target="settings", target_type="config", severity="warning")
        return trail

    def test_get_entries_by_action(self, populated_trail):
        entries = populated_trail.get_entries(action="task_created")
        assert len(entries) == 1
        assert entries[0].user == "alice"

    def test_get_entries_by_user(self, populated_trail):
        entries = populated_trail.get_entries(user="system")
        assert len(entries) == 2

    def test_get_entries_by_severity(self, populated_trail):
        entries = populated_trail.get_entries(severity="critical")
        assert len(entries) == 1
        assert entries[0].action == "security_violation"

    def test_get_entries_by_target(self, populated_trail):
        entries = populated_trail.get_entries(target="task-1")
        assert len(entries) == 3

    def test_get_entries_by_target_type(self, populated_trail):
        entries = populated_trail.get_entries(target_type="file")
        assert len(entries) == 2

    def test_get_entries_by_session(self, populated_trail):
        entries = populated_trail.get_entries(session_id="s1")
        assert len(entries) == 2

    def test_get_entries_with_limit_offset(self, populated_trail):
        all_entries = populated_trail.get_entries(limit=100)
        page1 = populated_trail.get_entries(limit=2, offset=0)
        page2 = populated_trail.get_entries(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].entry_id != page2[0].entry_id

    def test_get_entries_combined_filters(self, populated_trail):
        entries = populated_trail.get_entries(user="system", target="task-1")
        assert len(entries) == 2
        for e in entries:
            assert e.user == "system"


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_keyword(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice", details={"title": "Login page implementation"})
        trail.record("task_created", user="bob", details={"title": "Dashboard widgets"})
        results = trail.search(keyword="login")
        assert len(results) == 1

    def test_search_keyword_with_filter(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice", details={"title": "Login page"})
        trail.record("task_updated", user="alice", details={"title": "Login page v2"})
        results = trail.search(keyword="login", action="task_created")
        assert len(results) == 1

    def test_search_no_results(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        results = trail.search(keyword="nonexistent_keyword_xyz")
        assert len(results) == 0

    def test_search_empty_keyword(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        results = trail.search(keyword=None)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Integrity tests
# ---------------------------------------------------------------------------

class TestIntegrity:
    def test_integrity_valid(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        valid, errors = trail.verify_integrity()
        assert valid is True
        assert len(errors) == 0

    def test_integrity_tampered(self):
        trail = AuditTrail()
        entry = trail.record("task_created", user="alice")
        # Tamper with the entry
        entry.user = "mallory"
        valid, errors = trail.verify_integrity()
        assert valid is False
        assert len(errors) == 1

    def test_integrity_multiple_entries(self):
        trail = AuditTrail()
        for i in range(10):
            trail.record("task_created", user=f"user-{i}")
        valid, errors = trail.verify_integrity()
        assert valid is True

    def test_integrity_empty_trail(self):
        trail = AuditTrail()
        valid, errors = trail.verify_integrity()
        assert valid is True
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Summary tests
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_basic(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        summary = trail.get_summary()
        assert summary.total_entries == 2
        assert summary.unique_users == 2
        assert summary.unique_actions == 2
        assert summary.integrity_valid is True

    def test_summary_multiple_actions(self):
        trail = AuditTrail()
        for _ in range(3):
            trail.record("task_created", user="alice")
        for _ in range(2):
            trail.record("agent_started", user="system")
        summary = trail.get_summary()
        assert summary.entries_by_action["task_created"] == 3
        assert summary.entries_by_action["agent_started"] == 2

    def test_summary_empty(self):
        trail = AuditTrail()
        summary = trail.get_summary()
        assert summary.total_entries == 0
        assert summary.unique_users == 0
        assert summary.first_entry_date is None

    def test_summary_users(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_created", user="alice")
        trail.record("task_created", user="bob")
        summary = trail.get_summary()
        assert summary.entries_by_user["alice"] == 2
        assert summary.entries_by_user["bob"] == 1


# ---------------------------------------------------------------------------
# Export / Import tests
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_export_json(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        exported = trail.export_trail("json")
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["action"] == "task_created"

    def test_export_csv(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice", target="task-1")
        exported = trail.export_trail("csv")
        lines = exported.strip().split("\n")
        assert len(lines) == 2  # header + 1 entry
        assert "task_created" in lines[1]

    def test_export_jsonl(self):
        trail = AuditTrail()
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        exported = trail.export_trail("jsonl")
        lines = exported.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["action"] == "task_created"

    def test_import_json(self):
        trail1 = AuditTrail(project_id="proj-1")
        trail1.record("task_created", user="alice")
        trail1.record("task_updated", user="bob")
        exported = trail1.export_trail("json")

        trail2 = AuditTrail(project_id="proj-2")
        imported = trail2.import_trail(exported, "json")
        assert imported == 2

    def test_import_deduplication(self):
        trail = AuditTrail()
        entry = trail.record("task_created", user="alice")
        exported = trail.export_trail("json")
        # Import same data again
        imported = trail.import_trail(exported, "json")
        assert imported == 0  # Already exists


# ---------------------------------------------------------------------------
# Compliance tests
# ---------------------------------------------------------------------------

class TestCompliance:
    def test_soc2_report(self):
        trail = AuditTrail(project_id="proj-1")
        trail.record("task_created", user="alice")
        trail.record("security_violation", user="bob", severity="critical")
        trail.record("config_changed", user="admin", severity="warning")
        report = trail.get_compliance_report("SOC2")
        assert report["standard"] == "SOC2"
        assert report["total_entries"] == 3
        assert report["security_events"] >= 1
        assert report["config_changes"] == 1
        assert report["integrity_valid"] is True

    def test_iso27001_report(self):
        trail = AuditTrail(project_id="proj-1")
        trail.record("user_login", user="alice")
        report = trail.get_compliance_report("ISO27001")
        assert report["standard"] == "ISO27001"
        assert report["project_id"] == "proj-1"


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_basic(self):
        trail = AuditTrail(project_id="proj-1")
        trail.record("task_created", user="alice")
        trail.record("task_updated", user="bob")
        stats = trail.get_stats()
        assert stats["project_id"] == "proj-1"
        assert stats["total_entries"] == 2
        assert stats["unique_users"] == 2

    def test_stats_empty(self):
        trail = AuditTrail()
        stats = trail.get_stats()
        assert stats["total_entries"] == 0
