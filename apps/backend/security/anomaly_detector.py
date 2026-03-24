"""Behavioral Anomaly Detection — Monitor agent behavior and alert on suspicious activity.

Watches agent sessions for abnormal patterns such as mass file deletions,
unexpected network access, system config modifications, excessive resource usage,
or unusual token consumption. Each session receives a trust score that drops when
anomalies are detected.  When the score falls below a configurable threshold the
agent is automatically paused and an alert is emitted.

Feature 7.3 — Détection d'anomalies comportementales.

Example:
    >>> from apps.backend.security.anomaly_detector import AnomalyDetector
    >>> detector = AnomalyDetector()
    >>> session = detector.start_session("task-42", agent_type="coder")
    >>> detector.record_event(session.session_id, "file_delete", {"path": "src/main.py"})
    >>> detector.record_event(session.session_id, "file_delete", {"path": "src/utils.py"})
    >>> score = detector.get_trust_score(session.session_id)
"""

import logging
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnomalyType(str, Enum):
    """Types of behavioral anomalies detected."""

    MASS_FILE_DELETION = "mass_file_deletion"
    UNEXPECTED_NETWORK_ACCESS = "unexpected_network_access"
    SYSTEM_CONFIG_MODIFICATION = "system_config_modification"
    EXCESSIVE_TOKEN_USAGE = "excessive_token_usage"
    RAPID_FILE_CHANGES = "rapid_file_changes"
    SENSITIVE_FILE_ACCESS = "sensitive_file_access"
    UNUSUAL_COMMAND_EXECUTION = "unusual_command_execution"
    LONG_RUNNING_SESSION = "long_running_session"
    REPETITIVE_ERRORS = "repetitive_errors"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionStatus(str, Enum):
    """Status of a monitored session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class EventType(str, Enum):
    """Types of events that agents can produce."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXEC = "command_exec"
    NETWORK_REQUEST = "network_request"
    TOKEN_USAGE = "token_usage"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    CONFIG_CHANGE = "config_change"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AgentEvent:
    """A single event recorded during an agent session."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Anomaly:
    """A detected behavioral anomaly."""

    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_type: str = ""
    severity: str = "medium"
    description: str = ""
    session_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evidence: dict[str, Any] = field(default_factory=dict)
    score_impact: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MonitoredSession:
    """An agent session being monitored for anomalies."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    agent_type: str = ""
    status: str = "active"
    trust_score: float = 100.0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: str | None = None
    events: list[AgentEvent] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "trust_score": self.trust_score,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "events_count": len(self.events),
            "anomalies_count": len(self.anomalies),
            "metadata": self.metadata,
        }
        return result

    @property
    def duration_seconds(self) -> float | None:
        if self.ended_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.ended_at)
            return (end - start).total_seconds()
        return None


@dataclass
class BehaviorBaseline:
    """Baseline behavior statistics for a given agent type."""

    agent_type: str = ""
    avg_files_written: float = 10.0
    avg_files_deleted: float = 1.0
    avg_commands_executed: float = 5.0
    avg_token_usage: float = 5000.0
    avg_session_duration_s: float = 300.0
    avg_errors: float = 2.0
    sample_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnomalyAlert:
    """Alert emitted when trust score drops below threshold."""

    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    task_id: str = ""
    agent_type: str = ""
    trust_score: float = 0.0
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    action_taken: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Thresholds and rules
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = {
    "mass_deletion_count": 5,
    "rapid_file_change_count": 20,
    "rapid_file_change_window_s": 10,
    "max_token_multiplier": 3.0,
    "max_session_duration_s": 1800,
    "max_error_count": 10,
    "trust_score_pause_threshold": 40.0,
    "trust_score_terminate_threshold": 20.0,
}

SENSITIVE_PATHS = [
    ".env",
    ".git/",
    ".ssh/",
    ".aws/",
    ".gnupg/",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "secrets",
    "/etc/passwd",
    "/etc/shadow",
    "node_modules/.cache",
]

DANGEROUS_COMMANDS = [
    "rm -rf /",
    "sudo",
    "curl",
    "wget",
    "ssh",
    "scp",
    "nc ",
    "netcat",
    "eval",
    "exec",
    "mkfs",
    "dd if=",
    "chmod 777",
    "> /dev/",
    "base64 -d",
]

ANOMALY_SCORE_IMPACT = {
    AnomalyType.MASS_FILE_DELETION.value: 25.0,
    AnomalyType.UNEXPECTED_NETWORK_ACCESS.value: 20.0,
    AnomalyType.SYSTEM_CONFIG_MODIFICATION.value: 15.0,
    AnomalyType.EXCESSIVE_TOKEN_USAGE.value: 10.0,
    AnomalyType.RAPID_FILE_CHANGES.value: 10.0,
    AnomalyType.SENSITIVE_FILE_ACCESS.value: 20.0,
    AnomalyType.UNUSUAL_COMMAND_EXECUTION.value: 20.0,
    AnomalyType.LONG_RUNNING_SESSION.value: 5.0,
    AnomalyType.REPETITIVE_ERRORS.value: 10.0,
    AnomalyType.PATH_TRAVERSAL_ATTEMPT.value: 30.0,
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class AnomalyDetector:
    """Monitors agent sessions for behavioral anomalies.

    Tracks events from agent sessions, detects abnormal patterns, computes
    a trust score per session, and automatically pauses or terminates sessions
    that fall below configurable thresholds.

    Args:
        thresholds: Override default detection thresholds.
        baselines: Pre-existing behavior baselines per agent type.
    """

    def __init__(
        self,
        thresholds: dict[str, Any] | None = None,
        baselines: dict[str, BehaviorBaseline] | None = None,
    ) -> None:
        self._thresholds: dict[str, Any] = {**DEFAULT_THRESHOLDS}
        if thresholds:
            self._thresholds.update(thresholds)

        self._sessions: dict[str, MonitoredSession] = {}
        self._baselines: dict[str, BehaviorBaseline] = baselines or {}
        self._alerts: list[AnomalyAlert] = []
        self._listeners: list[Any] = []
        self._completed_sessions: list[MonitoredSession] = []

    # -- Session lifecycle ---------------------------------------------------

    def start_session(
        self,
        task_id: str,
        agent_type: str = "coder",
        metadata: dict[str, Any] | None = None,
    ) -> MonitoredSession:
        """Start monitoring a new agent session."""
        session = MonitoredSession(
            task_id=task_id,
            agent_type=agent_type,
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        logger.info(
            "Started monitoring session %s for task %s", session.session_id, task_id
        )
        return session

    def end_session(
        self, session_id: str, status: str = "completed"
    ) -> MonitoredSession:
        """End monitoring of a session."""
        session = self._get_session(session_id)
        session.status = status
        session.ended_at = datetime.now(timezone.utc).isoformat()
        self._completed_sessions.append(session)
        self._update_baseline(session)
        return session

    def get_session(self, session_id: str) -> MonitoredSession:
        """Get a monitored session by ID."""
        return self._get_session(session_id)

    def list_sessions(
        self,
        status: str | None = None,
        agent_type: str | None = None,
    ) -> list[MonitoredSession]:
        """List all sessions, optionally filtered."""
        all_sessions = list(self._sessions.values()) + self._completed_sessions
        if status:
            all_sessions = [s for s in all_sessions if s.status == status]
        if agent_type:
            all_sessions = [s for s in all_sessions if s.agent_type == agent_type]
        return all_sessions

    # -- Event recording & analysis ------------------------------------------

    def record_event(
        self,
        session_id: str,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> AgentEvent:
        """Record an event and run anomaly detection rules."""
        session = self._get_session(session_id)
        if session.status not in ("active",):
            raise ValueError(
                f"Cannot record events on session with status '{session.status}'"
            )

        event = AgentEvent(
            event_type=event_type,
            session_id=session_id,
            metadata=metadata or {},
        )
        session.events.append(event)

        # Run detection rules
        self._check_anomalies(session, event)

        return event

    def get_trust_score(self, session_id: str) -> float:
        """Get the current trust score for a session."""
        session = self._get_session(session_id)
        return session.trust_score

    def get_anomalies(
        self,
        session_id: str | None = None,
        anomaly_type: str | None = None,
        min_severity: str | None = None,
    ) -> list[Anomaly]:
        """Get detected anomalies, optionally filtered."""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        all_sessions = list(self._sessions.values()) + self._completed_sessions

        anomalies: list[Anomaly] = []
        for s in all_sessions:
            if session_id and s.session_id != session_id:
                continue
            anomalies.extend(s.anomalies)

        if anomaly_type:
            anomalies = [a for a in anomalies if a.anomaly_type == anomaly_type]
        if min_severity:
            min_level = severity_order.get(min_severity, 0)
            anomalies = [
                a for a in anomalies if severity_order.get(a.severity, 0) >= min_level
            ]

        return anomalies

    def get_alerts(self, session_id: str | None = None) -> list[AnomalyAlert]:
        """Get alerts emitted."""
        if session_id:
            return [a for a in self._alerts if a.session_id == session_id]
        return list(self._alerts)

    # -- Baseline management -------------------------------------------------

    def get_baseline(self, agent_type: str) -> BehaviorBaseline:
        """Get or create a baseline for an agent type."""
        if agent_type not in self._baselines:
            self._baselines[agent_type] = BehaviorBaseline(agent_type=agent_type)
        return self._baselines[agent_type]

    def set_baseline(self, baseline: BehaviorBaseline) -> None:
        """Manually set a baseline."""
        self._baselines[baseline.agent_type] = baseline

    # -- Listeners -----------------------------------------------------------

    def on_alert(self, callback: Any) -> None:
        """Register a callback for anomaly alerts."""
        self._listeners.append(callback)

    # -- Analysis helpers ----------------------------------------------------

    def analyze_session(self, session_id: str) -> dict[str, Any]:
        """Produce a post-mortem analysis for a session."""
        session = self._get_session(session_id)

        event_counts: dict[str, int] = {}
        for ev in session.events:
            event_counts[ev.event_type] = event_counts.get(ev.event_type, 0) + 1

        anomaly_counts: dict[str, int] = {}
        for an in session.anomalies:
            anomaly_counts[an.anomaly_type] = anomaly_counts.get(an.anomaly_type, 0) + 1

        return {
            "session_id": session.session_id,
            "task_id": session.task_id,
            "agent_type": session.agent_type,
            "status": session.status,
            "trust_score": session.trust_score,
            "total_events": len(session.events),
            "total_anomalies": len(session.anomalies),
            "event_breakdown": event_counts,
            "anomaly_breakdown": anomaly_counts,
            "duration_seconds": session.duration_seconds,
            "was_paused": session.status in ("paused", "terminated"),
        }

    def get_stats(self) -> dict[str, Any]:
        """Global statistics across all sessions."""
        all_sessions = list(self._sessions.values()) + self._completed_sessions
        total_anomalies = sum(len(s.anomalies) for s in all_sessions)
        total_events = sum(len(s.events) for s in all_sessions)

        anomaly_type_counts: dict[str, int] = {}
        for s in all_sessions:
            for a in s.anomalies:
                anomaly_type_counts[a.anomaly_type] = (
                    anomaly_type_counts.get(a.anomaly_type, 0) + 1
                )

        scores = [s.trust_score for s in all_sessions]

        return {
            "total_sessions": len(all_sessions),
            "active_sessions": len([s for s in all_sessions if s.status == "active"]),
            "paused_sessions": len([s for s in all_sessions if s.status == "paused"]),
            "terminated_sessions": len(
                [s for s in all_sessions if s.status == "terminated"]
            ),
            "total_events": total_events,
            "total_anomalies": total_anomalies,
            "total_alerts": len(self._alerts),
            "anomaly_type_counts": anomaly_type_counts,
            "avg_trust_score": statistics.mean(scores) if scores else 100.0,
            "min_trust_score": min(scores) if scores else 100.0,
            "baselines_count": len(self._baselines),
        }

    # -- Internal detection rules --------------------------------------------

    def _get_session(self, session_id: str) -> MonitoredSession:
        if session_id in self._sessions:
            return self._sessions[session_id]
        for s in self._completed_sessions:
            if s.session_id == session_id:
                return s
        raise KeyError(f"Session '{session_id}' not found")

    def _check_anomalies(self, session: MonitoredSession, event: AgentEvent) -> None:
        """Run all anomaly detection rules against the latest event."""
        self._check_mass_deletion(session, event)
        self._check_sensitive_file_access(session, event)
        self._check_dangerous_command(session, event)
        self._check_network_access(session, event)
        self._check_path_traversal(session, event)
        self._check_rapid_file_changes(session)
        self._check_excessive_tokens(session, event)
        self._check_repetitive_errors(session)
        self._check_config_modification(session, event)

        # Check score thresholds
        self._check_score_thresholds(session)

    def _register_anomaly(
        self,
        session: MonitoredSession,
        anomaly_type: str,
        severity: str,
        description: str,
        evidence: dict[str, Any] | None = None,
    ) -> Anomaly:
        score_impact = ANOMALY_SCORE_IMPACT.get(anomaly_type, 10.0)
        anomaly = Anomaly(
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            session_id=session.session_id,
            evidence=evidence or {},
            score_impact=score_impact,
        )
        session.anomalies.append(anomaly)
        session.trust_score = max(0.0, session.trust_score - score_impact)
        logger.warning(
            "Anomaly detected in session %s: [%s] %s (score now %.1f)",
            session.session_id,
            anomaly_type,
            description,
            session.trust_score,
        )
        return anomaly

    def _check_mass_deletion(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type != EventType.FILE_DELETE.value:
            return
        delete_count = sum(
            1 for e in session.events if e.event_type == EventType.FILE_DELETE.value
        )
        threshold = self._thresholds["mass_deletion_count"]
        if delete_count >= threshold:
            existing = [
                a
                for a in session.anomalies
                if a.anomaly_type == AnomalyType.MASS_FILE_DELETION.value
            ]
            if not existing:
                self._register_anomaly(
                    session,
                    AnomalyType.MASS_FILE_DELETION.value,
                    "critical",
                    f"Mass file deletion detected: {delete_count} files deleted (threshold: {threshold})",
                    {"delete_count": delete_count, "threshold": threshold},
                )

    def _check_sensitive_file_access(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type not in (
            EventType.FILE_READ.value,
            EventType.FILE_WRITE.value,
            EventType.FILE_DELETE.value,
        ):
            return
        path = event.metadata.get("path", "")
        for sensitive in SENSITIVE_PATHS:
            if sensitive in path:
                self._register_anomaly(
                    session,
                    AnomalyType.SENSITIVE_FILE_ACCESS.value,
                    "high",
                    f"Access to sensitive path detected: {path}",
                    {
                        "path": path,
                        "matched_pattern": sensitive,
                        "event_type": event.event_type,
                    },
                )
                return

    def _check_dangerous_command(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type != EventType.COMMAND_EXEC.value:
            return
        command = event.metadata.get("command", "")
        for dangerous in DANGEROUS_COMMANDS:
            if dangerous in command:
                self._register_anomaly(
                    session,
                    AnomalyType.UNUSUAL_COMMAND_EXECUTION.value,
                    "critical",
                    f"Dangerous command detected: {command}",
                    {"command": command, "matched_pattern": dangerous},
                )
                return

    def _check_network_access(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type != EventType.NETWORK_REQUEST.value:
            return
        url = event.metadata.get("url", "")
        self._register_anomaly(
            session,
            AnomalyType.UNEXPECTED_NETWORK_ACCESS.value,
            "high",
            f"Unexpected network access: {url}",
            {"url": url},
        )

    def _check_path_traversal(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type not in (
            EventType.FILE_READ.value,
            EventType.FILE_WRITE.value,
        ):
            return
        path = event.metadata.get("path", "")
        if ".." in path or path.startswith("/etc/") or path.startswith("/root/"):
            self._register_anomaly(
                session,
                AnomalyType.PATH_TRAVERSAL_ATTEMPT.value,
                "critical",
                f"Path traversal attempt detected: {path}",
                {"path": path},
            )

    def _check_rapid_file_changes(self, session: MonitoredSession) -> None:
        threshold_count = self._thresholds["rapid_file_change_count"]
        window_s = self._thresholds["rapid_file_change_window_s"]
        write_events = [
            e for e in session.events if e.event_type == EventType.FILE_WRITE.value
        ]
        if len(write_events) < threshold_count:
            return

        recent = write_events[-threshold_count:]
        first_ts = datetime.fromisoformat(recent[0].timestamp)
        last_ts = datetime.fromisoformat(recent[-1].timestamp)
        elapsed = (last_ts - first_ts).total_seconds()

        if elapsed <= window_s:
            existing = [
                a
                for a in session.anomalies
                if a.anomaly_type == AnomalyType.RAPID_FILE_CHANGES.value
            ]
            if not existing:
                self._register_anomaly(
                    session,
                    AnomalyType.RAPID_FILE_CHANGES.value,
                    "medium",
                    f"{len(write_events)} file writes in {elapsed:.1f}s (threshold: {threshold_count} in {window_s}s)",
                    {"write_count": len(write_events), "window_seconds": elapsed},
                )

    def _check_excessive_tokens(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type != EventType.TOKEN_USAGE.value:
            return
        total_tokens = sum(
            e.metadata.get("tokens", 0)
            for e in session.events
            if e.event_type == EventType.TOKEN_USAGE.value
        )
        baseline = self.get_baseline(session.agent_type)
        max_tokens = baseline.avg_token_usage * self._thresholds["max_token_multiplier"]
        if total_tokens > max_tokens:
            existing = [
                a
                for a in session.anomalies
                if a.anomaly_type == AnomalyType.EXCESSIVE_TOKEN_USAGE.value
            ]
            if not existing:
                self._register_anomaly(
                    session,
                    AnomalyType.EXCESSIVE_TOKEN_USAGE.value,
                    "medium",
                    f"Excessive token usage: {total_tokens} (baseline avg: {baseline.avg_token_usage})",
                    {
                        "total_tokens": total_tokens,
                        "baseline_avg": baseline.avg_token_usage,
                    },
                )

    def _check_repetitive_errors(self, session: MonitoredSession) -> None:
        error_count = sum(
            1 for e in session.events if e.event_type == EventType.ERROR.value
        )
        threshold = self._thresholds["max_error_count"]
        if error_count >= threshold:
            existing = [
                a
                for a in session.anomalies
                if a.anomaly_type == AnomalyType.REPETITIVE_ERRORS.value
            ]
            if not existing:
                self._register_anomaly(
                    session,
                    AnomalyType.REPETITIVE_ERRORS.value,
                    "high",
                    f"Repetitive errors detected: {error_count} errors (threshold: {threshold})",
                    {"error_count": error_count, "threshold": threshold},
                )

    def _check_config_modification(
        self, session: MonitoredSession, event: AgentEvent
    ) -> None:
        if event.event_type != EventType.CONFIG_CHANGE.value:
            return
        path = event.metadata.get("path", "")
        self._register_anomaly(
            session,
            AnomalyType.SYSTEM_CONFIG_MODIFICATION.value,
            "high",
            f"System configuration modification: {path}",
            {"path": path},
        )

    def _check_score_thresholds(self, session: MonitoredSession) -> None:
        """Check if trust score has crossed alert thresholds."""
        pause_threshold = self._thresholds["trust_score_pause_threshold"]
        terminate_threshold = self._thresholds["trust_score_terminate_threshold"]

        if session.trust_score <= terminate_threshold and session.status == "active":
            session.status = "terminated"
            alert = self._emit_alert(session, "terminated")
            logger.critical(
                "Session %s TERMINATED — trust score %.1f below threshold %.1f",
                session.session_id,
                session.trust_score,
                terminate_threshold,
            )
        elif session.trust_score <= pause_threshold and session.status == "active":
            session.status = "paused"
            alert = self._emit_alert(session, "paused")
            logger.warning(
                "Session %s PAUSED — trust score %.1f below threshold %.1f",
                session.session_id,
                session.trust_score,
                pause_threshold,
            )

    def _emit_alert(self, session: MonitoredSession, action: str) -> AnomalyAlert:
        alert = AnomalyAlert(
            session_id=session.session_id,
            task_id=session.task_id,
            agent_type=session.agent_type,
            trust_score=session.trust_score,
            anomalies=[a.to_dict() for a in session.anomalies],
            action_taken=action,
        )
        self._alerts.append(alert)
        for listener in self._listeners:
            try:
                listener(alert)
            except Exception as exc:
                logger.error("Alert listener error: %s", exc)
        return alert

    def _update_baseline(self, session: MonitoredSession) -> None:
        """Update the baseline for an agent type based on a completed session."""
        baseline = self.get_baseline(session.agent_type)
        n = baseline.sample_count

        files_written = sum(
            1 for e in session.events if e.event_type == EventType.FILE_WRITE.value
        )
        files_deleted = sum(
            1 for e in session.events if e.event_type == EventType.FILE_DELETE.value
        )
        commands = sum(
            1 for e in session.events if e.event_type == EventType.COMMAND_EXEC.value
        )
        tokens = sum(
            e.metadata.get("tokens", 0)
            for e in session.events
            if e.event_type == EventType.TOKEN_USAGE.value
        )
        errors = sum(1 for e in session.events if e.event_type == EventType.ERROR.value)
        duration = session.duration_seconds or 0

        # Incremental running average
        def _update_avg(old: float, new_val: float, count: int) -> float:
            if count == 0:
                return new_val
            return (old * count + new_val) / (count + 1)

        # Only update baseline from non-anomalous sessions
        if len(session.anomalies) == 0:
            baseline.avg_files_written = _update_avg(
                baseline.avg_files_written, files_written, n
            )
            baseline.avg_files_deleted = _update_avg(
                baseline.avg_files_deleted, files_deleted, n
            )
            baseline.avg_commands_executed = _update_avg(
                baseline.avg_commands_executed, commands, n
            )
            baseline.avg_token_usage = _update_avg(baseline.avg_token_usage, tokens, n)
            baseline.avg_session_duration_s = _update_avg(
                baseline.avg_session_duration_s, duration, n
            )
            baseline.avg_errors = _update_avg(baseline.avg_errors, errors, n)
            baseline.sample_count = n + 1
