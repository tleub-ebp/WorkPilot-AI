"""Tests for the AuditTrail."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from audit_trail import (
    AuditEvent,
    AuditEventKind,
    AuditTrail,
    Decision,
)


class TestNaming:
    def test_invalid_trail_name_rejected(self, tmp_path: Path) -> None:
        for bad in ("../escape", "with space", "/abs", "", ".hidden"):
            with pytest.raises(ValueError):
                AuditTrail(storage_dir=tmp_path, name=bad)

    def test_valid_names_accepted(self, tmp_path: Path) -> None:
        for ok in ("default", "spec-001", "audit_v2.log", "abc123"):
            AuditTrail(storage_dir=tmp_path, name=ok)


class TestAppend:
    def test_first_event_chains_from_genesis(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        evt = trail.append(
            kind=AuditEventKind.AGENT_INVOKED,
            actor="planner",
            correlation_id="spec-1",
            summary="Planner started",
        )
        assert evt.sequence == 0
        assert evt.prev_hash == "genesis"
        assert len(evt.event_hash) == 64  # sha256 hex

    def test_subsequent_events_chain_correctly(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        e1 = trail.append("agent_invoked", "planner", "spec-1", "first")
        e2 = trail.append("agent_completed", "planner", "spec-1", "second")
        assert e2.sequence == 1
        assert e2.prev_hash == e1.event_hash

    def test_append_requires_actor(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        with pytest.raises(ValueError):
            trail.append("agent_invoked", "", "spec-1", "x")

    def test_append_requires_correlation_id(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        with pytest.raises(ValueError):
            trail.append("agent_invoked", "planner", "", "x")

    def test_unserialisable_payload_rejected(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        # A set is not JSON-serialisable by default.
        with pytest.raises(ValueError):
            trail.append(
                "agent_invoked",
                "planner",
                "spec-1",
                "x",
                payload={"bad": {"nested-set"}},  # type: ignore[dict-item]
            )

    def test_string_kind_accepted(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        evt = trail.append("system_event", "system", "boot-1", "started")
        assert evt.kind == AuditEventKind.SYSTEM_EVENT


class TestPersistence:
    def test_events_survive_reopen(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        trail.append("agent_invoked", "planner", "spec-1", "alpha")
        trail.append("agent_completed", "planner", "spec-1", "beta")

        trail2 = AuditTrail(storage_dir=tmp_path, name="t1")
        events = trail2.all()
        assert [e.summary for e in events] == ["alpha", "beta"]
        assert trail2.length() == 2

    def test_appending_after_reopen_preserves_chain(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        e1 = trail.append("agent_invoked", "planner", "spec-1", "alpha")

        trail2 = AuditTrail(storage_dir=tmp_path, name="t1")
        e2 = trail2.append("agent_completed", "planner", "spec-1", "beta")
        # The chain must continue from the disk-loaded last event.
        assert e2.prev_hash == e1.event_hash
        assert e2.sequence == 1

    def test_jsonl_format_one_line_per_event(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        for i in range(3):
            trail.append("agent_invoked", "planner", f"spec-{i}", f"e{i}")
        lines = trail.path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        for line in lines:
            assert json.loads(line)  # each line is valid JSON


class TestReplay:
    def test_replay_filters_by_correlation_id(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        trail.append("agent_invoked", "planner", "spec-1", "a")
        trail.append("agent_invoked", "coder", "spec-2", "b")
        trail.append("agent_completed", "coder", "spec-2", "c")
        bundle = trail.replay("spec-2")
        assert bundle.correlation_id == "spec-2"
        assert [e.summary for e in bundle.events] == ["b", "c"]

    def test_replay_unknown_correlation_returns_empty(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        trail.append("agent_invoked", "planner", "spec-1", "a")
        bundle = trail.replay("ghost")
        assert bundle.events == []

    def test_filter_by_actor(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        trail.append("agent_invoked", "planner", "s-1", "a")
        trail.append("agent_invoked", "coder", "s-1", "b")
        events = trail.filter(actor="coder")
        assert len(events) == 1 and events[0].actor == "coder"

    def test_filter_by_kind_and_time(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        e1 = trail.append("agent_invoked", "planner", "s-1", "a")
        time.sleep(0.01)
        e2 = trail.append("agent_completed", "planner", "s-1", "b")

        invoked = trail.filter(kind="agent_invoked")
        assert [e.event_hash for e in invoked] == [e1.event_hash]

        recent = trail.filter(since=e1.timestamp + 0.005)
        assert [e.event_hash for e in recent] == [e2.event_hash]


class TestIntegrity:
    def test_clean_chain_passes_verify(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        for i in range(5):
            trail.append("agent_invoked", "a", f"s-{i}", f"x{i}")
        report = trail.verify()
        assert report.is_intact is True
        assert report.events_checked == 5
        assert report.first_broken_sequence is None

    def test_tampered_event_detected(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        for i in range(3):
            trail.append("agent_invoked", "a", f"s-{i}", f"x{i}")

        # Tamper directly on disk: rewrite the second event's summary
        # without recomputing the hash.
        lines = trail.path.read_text(encoding="utf-8").splitlines()
        evil = json.loads(lines[1])
        evil["summary"] = "I changed my mind"
        lines[1] = json.dumps(evil, separators=(",", ":"))
        trail.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Reload + verify.
        trail2 = AuditTrail(storage_dir=tmp_path, name="t1")
        report = trail2.verify()
        assert report.is_intact is False
        assert report.first_broken_sequence == 1
        assert "hash mismatch" in (report.breakage_reason or "")

    def test_verify_on_empty_trail(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        report = trail.verify()
        assert report.is_intact is True
        assert report.events_checked == 0


class TestDecisionHelper:
    def test_append_decision_round_trip(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        decision = Decision(
            decision_id="d-42",
            title="Pick a database",
            chosen_option="postgres",
            rejected_options=("mysql", "sqlite"),
            rationale="needs RLS + JSONB",
            risk_score=0.2,
        )
        evt = trail.append_decision(
            actor="planner", correlation_id="spec-1", decision=decision
        )
        assert evt.kind == AuditEventKind.DECISION_MADE
        assert evt.payload["chosen_option"] == "postgres"
        assert evt.payload["rejected_options"] == ["mysql", "sqlite"]


class TestDiscovery:
    def test_list_trails(self, tmp_path: Path) -> None:
        AuditTrail(storage_dir=tmp_path, name="t1").append(
            "system_event", "sys", "boot-1", "ok"
        )
        AuditTrail(storage_dir=tmp_path, name="t2").append(
            "system_event", "sys", "boot-1", "ok"
        )
        names = AuditTrail.list_trails(tmp_path)
        assert names == ["t1", "t2"]

    def test_list_trails_on_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        ghost = tmp_path / "missing"
        assert AuditTrail.list_trails(ghost) == []


class TestSerialisation:
    def test_event_to_dict_round_trip(self, tmp_path: Path) -> None:
        trail = AuditTrail(storage_dir=tmp_path, name="t1")
        original = trail.append(
            "agent_invoked", "planner", "spec-1", "x", payload={"k": [1, 2, 3]}
        )
        d = original.to_dict()
        rebuilt = AuditEvent.from_dict(d)
        assert rebuilt == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
