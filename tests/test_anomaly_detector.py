"""Tests for Feature 7.3 — Behavioral Anomaly Detection.

40 tests covering:
- AgentEvent: 3
- Anomaly: 3
- MonitoredSession: 4
- BehaviorBaseline: 2
- AnomalyAlert: 2
- Session lifecycle: 4
- Event recording: 4
- Mass deletion detection: 3
- Sensitive file access: 2
- Dangerous command detection: 2
- Network access detection: 1
- Path traversal detection: 2
- Rapid file changes: 1
- Excessive tokens: 2
- Repetitive errors: 1
- Score thresholds (pause/terminate): 3
- Analysis & stats: 3
- Baseline updates: 2
- Alert listeners: 1
"""

import pytest

from apps.backend.security.anomaly_detector import (
    AgentEvent,
    Anomaly,
    AnomalyAlert,
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
    BehaviorBaseline,
    EventType,
    MonitoredSession,
    SessionStatus,
)

# ---------------------------------------------------------------------------
# AgentEvent tests (3)
# ---------------------------------------------------------------------------

class TestAgentEvent:
    def test_creation_defaults(self):
        ev = AgentEvent(event_type="file_write", session_id="s1")
        assert ev.event_type == "file_write"
        assert ev.session_id == "s1"
        assert ev.event_id  # auto-generated
        assert ev.timestamp  # auto-generated

    def test_to_dict(self):
        ev = AgentEvent(event_type="command_exec", metadata={"command": "ls"})
        d = ev.to_dict()
        assert d["event_type"] == "command_exec"
        assert d["metadata"]["command"] == "ls"

    def test_metadata_default_empty(self):
        ev = AgentEvent()
        assert ev.metadata == {}


# ---------------------------------------------------------------------------
# Anomaly tests (3)
# ---------------------------------------------------------------------------

class TestAnomaly:
    def test_creation(self):
        a = Anomaly(anomaly_type="mass_file_deletion", severity="critical")
        assert a.anomaly_type == "mass_file_deletion"
        assert a.severity == "critical"
        assert a.anomaly_id

    def test_to_dict(self):
        a = Anomaly(anomaly_type="sensitive_file_access", evidence={"path": ".env"})
        d = a.to_dict()
        assert d["evidence"]["path"] == ".env"

    def test_score_impact(self):
        a = Anomaly(score_impact=25.0)
        assert a.score_impact == 25.0


# ---------------------------------------------------------------------------
# MonitoredSession tests (4)
# ---------------------------------------------------------------------------

class TestMonitoredSession:
    def test_creation_defaults(self):
        s = MonitoredSession(task_id="t1", agent_type="coder")
        assert s.trust_score == 100.0
        assert s.status == "active"
        assert s.events == []
        assert s.anomalies == []

    def test_to_dict(self):
        s = MonitoredSession(task_id="t1", agent_type="qa")
        d = s.to_dict()
        assert d["task_id"] == "t1"
        assert d["events_count"] == 0

    def test_duration_none_when_active(self):
        s = MonitoredSession()
        assert s.duration_seconds is None

    def test_duration_calculated(self):
        s = MonitoredSession(
            started_at="2026-01-01T10:00:00+00:00",
            ended_at="2026-01-01T10:05:00+00:00",
        )
        assert s.duration_seconds == 300.0


# ---------------------------------------------------------------------------
# BehaviorBaseline tests (2)
# ---------------------------------------------------------------------------

class TestBehaviorBaseline:
    def test_defaults(self):
        b = BehaviorBaseline(agent_type="coder")
        assert b.avg_files_written == 10.0
        assert b.sample_count == 0

    def test_to_dict(self):
        b = BehaviorBaseline(agent_type="qa", avg_token_usage=3000)
        d = b.to_dict()
        assert d["agent_type"] == "qa"
        assert d["avg_token_usage"] == 3000


# ---------------------------------------------------------------------------
# AnomalyAlert tests (2)
# ---------------------------------------------------------------------------

class TestAnomalyAlert:
    def test_creation(self):
        a = AnomalyAlert(session_id="s1", action_taken="paused")
        assert a.session_id == "s1"
        assert a.action_taken == "paused"

    def test_to_dict(self):
        a = AnomalyAlert(trust_score=35.0, anomalies=[{"type": "test"}])
        d = a.to_dict()
        assert d["trust_score"] == 35.0
        assert len(d["anomalies"]) == 1


# ---------------------------------------------------------------------------
# Session lifecycle (4)
# ---------------------------------------------------------------------------

class TestSessionLifecycle:
    def test_start_session(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1", agent_type="coder")
        assert session.status == "active"
        assert session.trust_score == 100.0

    def test_end_session(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        ended = detector.end_session(session.session_id)
        assert ended.status == "completed"
        assert ended.ended_at is not None

    def test_get_session(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        fetched = detector.get_session(session.session_id)
        assert fetched.session_id == session.session_id

    def test_list_sessions_filter(self):
        detector = AnomalyDetector()
        detector.start_session("t1", agent_type="coder")
        detector.start_session("t2", agent_type="qa")
        coders = detector.list_sessions(agent_type="coder")
        assert len(coders) == 1


# ---------------------------------------------------------------------------
# Event recording (4)
# ---------------------------------------------------------------------------

class TestEventRecording:
    def test_record_event(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        ev = detector.record_event(session.session_id, "file_write", {"path": "src/main.py"})
        assert ev.event_type == "file_write"
        assert len(session.events) == 1

    def test_record_multiple_events(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        for i in range(5):
            detector.record_event(session.session_id, "file_write", {"path": f"src/f{i}.py"})
        assert len(session.events) == 5

    def test_record_event_on_paused_session_raises(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        session.status = "paused"
        with pytest.raises(ValueError, match="Cannot record events"):
            detector.record_event(session.session_id, "file_write")

    def test_record_event_returns_agent_event(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        ev = detector.record_event(session.session_id, "tool_call", {"tool": "grep"})
        assert isinstance(ev, AgentEvent)
        assert ev.metadata["tool"] == "grep"


# ---------------------------------------------------------------------------
# Mass deletion detection (3)
# ---------------------------------------------------------------------------

class TestMassDeletion:
    def test_no_anomaly_below_threshold(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        for i in range(4):
            detector.record_event(session.session_id, "file_delete", {"path": f"f{i}"})
        assert len(session.anomalies) == 0

    def test_anomaly_at_threshold(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        for i in range(5):
            detector.record_event(session.session_id, "file_delete", {"path": f"f{i}"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.MASS_FILE_DELETION.value]
        assert len(anomalies) == 1
        assert anomalies[0].severity == "critical"

    def test_custom_threshold(self):
        detector = AnomalyDetector(thresholds={"mass_deletion_count": 2})
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "file_delete", {"path": "b"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.MASS_FILE_DELETION.value]
        assert len(anomalies) == 1


# ---------------------------------------------------------------------------
# Sensitive file access (2)
# ---------------------------------------------------------------------------

class TestSensitiveFileAccess:
    def test_env_file_access(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_read", {"path": "/project/.env"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.SENSITIVE_FILE_ACCESS.value]
        assert len(anomalies) == 1

    def test_ssh_key_access(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_read", {"path": "/home/user/.ssh/id_rsa"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.SENSITIVE_FILE_ACCESS.value]
        assert len(anomalies) >= 1


# ---------------------------------------------------------------------------
# Dangerous command detection (2)
# ---------------------------------------------------------------------------

class TestDangerousCommand:
    def test_sudo_detected(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "command_exec", {"command": "sudo apt install"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.UNUSUAL_COMMAND_EXECUTION.value]
        assert len(anomalies) == 1
        assert anomalies[0].severity == "critical"

    def test_safe_command_no_anomaly(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "command_exec", {"command": "python test.py"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.UNUSUAL_COMMAND_EXECUTION.value]
        assert len(anomalies) == 0


# ---------------------------------------------------------------------------
# Network access (1)
# ---------------------------------------------------------------------------

class TestNetworkAccess:
    def test_network_request_detected(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "network_request", {"url": "http://evil.com"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.UNEXPECTED_NETWORK_ACCESS.value]
        assert len(anomalies) == 1


# ---------------------------------------------------------------------------
# Path traversal (2)
# ---------------------------------------------------------------------------

class TestPathTraversal:
    def test_dotdot_detected(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_read", {"path": "../../etc/passwd"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.PATH_TRAVERSAL_ATTEMPT.value]
        assert len(anomalies) == 1

    def test_etc_path_detected(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_write", {"path": "/etc/hosts"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.PATH_TRAVERSAL_ATTEMPT.value]
        assert len(anomalies) == 1


# ---------------------------------------------------------------------------
# Rapid file changes (1)
# ---------------------------------------------------------------------------

class TestRapidFileChanges:
    def test_rapid_writes_detected(self):
        detector = AnomalyDetector(thresholds={
            "rapid_file_change_count": 5,
            "rapid_file_change_window_s": 100,
        })
        session = detector.start_session("task-1")
        # All events get the same timestamp (within the window)
        for i in range(5):
            detector.record_event(session.session_id, "file_write", {"path": f"f{i}.py"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.RAPID_FILE_CHANGES.value]
        assert len(anomalies) == 1


# ---------------------------------------------------------------------------
# Excessive tokens (2)
# ---------------------------------------------------------------------------

class TestExcessiveTokens:
    def test_excessive_tokens_detected(self):
        detector = AnomalyDetector()
        baseline = BehaviorBaseline(agent_type="coder", avg_token_usage=1000)
        detector.set_baseline(baseline)

        session = detector.start_session("task-1", agent_type="coder")
        # 3x the baseline
        detector.record_event(session.session_id, "token_usage", {"tokens": 3500})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.EXCESSIVE_TOKEN_USAGE.value]
        assert len(anomalies) == 1

    def test_normal_tokens_no_anomaly(self):
        detector = AnomalyDetector()
        baseline = BehaviorBaseline(agent_type="coder", avg_token_usage=5000)
        detector.set_baseline(baseline)

        session = detector.start_session("task-1", agent_type="coder")
        detector.record_event(session.session_id, "token_usage", {"tokens": 4000})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.EXCESSIVE_TOKEN_USAGE.value]
        assert len(anomalies) == 0


# ---------------------------------------------------------------------------
# Repetitive errors (1)
# ---------------------------------------------------------------------------

class TestRepetitiveErrors:
    def test_errors_detected(self):
        detector = AnomalyDetector(thresholds={"max_error_count": 3})
        session = detector.start_session("task-1")
        for i in range(3):
            detector.record_event(session.session_id, "error", {"message": f"Error {i}"})
        anomalies = [a for a in session.anomalies if a.anomaly_type == AnomalyType.REPETITIVE_ERRORS.value]
        assert len(anomalies) == 1


# ---------------------------------------------------------------------------
# Score thresholds — pause & terminate (3)
# ---------------------------------------------------------------------------

class TestScoreThresholds:
    def test_session_paused_at_threshold(self):
        detector = AnomalyDetector(thresholds={
            "trust_score_pause_threshold": 60.0,
            "mass_deletion_count": 1,
        })
        session = detector.start_session("task-1")
        # Mass deletion = -25, sensitive access = -20 => score 55 < 60 => paused
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "file_read", {"path": ".env"})
        assert session.status == "paused"

    def test_session_terminated_at_threshold(self):
        detector = AnomalyDetector(thresholds={
            "trust_score_terminate_threshold": 50.0,
            "trust_score_pause_threshold": 20.0,
            "mass_deletion_count": 1,
        })
        session = detector.start_session("task-1")
        # Mass deletion (-25) + sensitive (-20) => score 55, then 55-20=35 < 50 => terminated
        # pause_threshold is very low (20) so we skip pause and go straight to terminate
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "file_read", {"path": ".env"})
        detector.record_event(session.session_id, "file_read", {"path": ".ssh/key"})
        assert session.status == "terminated"

    def test_alert_emitted_on_pause(self):
        detector = AnomalyDetector(thresholds={
            "trust_score_pause_threshold": 60.0,
            "mass_deletion_count": 1,
        })
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "file_read", {"path": ".env"})
        alerts = detector.get_alerts(session.session_id)
        assert len(alerts) >= 1
        assert alerts[0].action_taken == "paused"


# ---------------------------------------------------------------------------
# Analysis & stats (3)
# ---------------------------------------------------------------------------

class TestAnalysisAndStats:
    def test_analyze_session(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_write", {"path": "a"})
        detector.record_event(session.session_id, "file_write", {"path": "b"})
        analysis = detector.analyze_session(session.session_id)
        assert analysis["total_events"] == 2
        assert analysis["event_breakdown"]["file_write"] == 2

    def test_get_stats(self):
        detector = AnomalyDetector()
        detector.start_session("t1")
        detector.start_session("t2")
        stats = detector.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2

    def test_get_anomalies_filtered(self):
        detector = AnomalyDetector(thresholds={"mass_deletion_count": 1})
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "network_request", {"url": "http://x"})
        all_anomalies = detector.get_anomalies(session_id=session.session_id)
        assert len(all_anomalies) == 2
        filtered = detector.get_anomalies(anomaly_type=AnomalyType.MASS_FILE_DELETION.value)
        assert len(filtered) == 1


# ---------------------------------------------------------------------------
# Baseline updates (2)
# ---------------------------------------------------------------------------

class TestBaselineUpdates:
    def test_baseline_updated_on_clean_session(self):
        detector = AnomalyDetector()
        session = detector.start_session("task-1", agent_type="coder")
        detector.record_event(session.session_id, "file_write", {"path": "a"})
        detector.end_session(session.session_id)
        baseline = detector.get_baseline("coder")
        assert baseline.sample_count == 1

    def test_baseline_not_updated_on_anomalous_session(self):
        detector = AnomalyDetector(thresholds={"mass_deletion_count": 1})
        session = detector.start_session("task-1", agent_type="coder")
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        initial_count = detector.get_baseline("coder").sample_count
        detector.end_session(session.session_id)
        assert detector.get_baseline("coder").sample_count == initial_count


# ---------------------------------------------------------------------------
# Alert listeners (1)
# ---------------------------------------------------------------------------

class TestAlertListeners:
    def test_listener_called_on_alert(self):
        alerts_received = []
        detector = AnomalyDetector(thresholds={
            "trust_score_pause_threshold": 60.0,
            "mass_deletion_count": 1,
        })
        detector.on_alert(lambda a: alerts_received.append(a))
        session = detector.start_session("task-1")
        detector.record_event(session.session_id, "file_delete", {"path": "a"})
        detector.record_event(session.session_id, "file_read", {"path": ".env"})
        assert len(alerts_received) >= 1
