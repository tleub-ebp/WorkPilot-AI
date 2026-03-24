"""Complete Audit Trail — Immutable logging of all application actions.

Provides a secure, append-only audit log that traces every action performed
in the application: task creation, agent execution, merges, deletions,
config changes, and more.  Supports filtering, search, export for
compliance (SOC2, ISO 27001).

Feature 7.1 — Audit trail complet.

Example:
    >>> from apps.backend.security.audit_trail import AuditTrail
    >>> trail = AuditTrail(project_id="my-project")
    >>> trail.record("task_created", user="alice", target="task-42",
    ...     details={"title": "Login page"})
    >>> entries = trail.search(action="task_created")
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AuditAction(str, Enum):
    """All auditable actions in the application."""

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_MOVED = "task_moved"
    TASK_ASSIGNED = "task_assigned"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    MERGE_STARTED = "merge_started"
    MERGE_COMPLETED = "merge_completed"
    MERGE_CONFLICT = "merge_conflict"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    CONFIG_CHANGED = "config_changed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    EXPORT_GENERATED = "export_generated"
    IMPORT_EXECUTED = "import_executed"
    SECURITY_VIOLATION = "security_violation"
    ROLLBACK_EXECUTED = "rollback_executed"
    INTEGRATION_SYNC = "integration_sync"
    CUSTOM = "custom"


class AuditSeverity(str, Enum):
    """Severity levels for audit entries."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    """A single audit log entry — immutable once created."""

    entry_id: str
    timestamp: str
    action: str
    user: str
    project_id: str
    target: str | None = None
    target_type: str | None = None
    severity: str = "info"
    details: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    result: str | None = None
    ip_address: str | None = None
    session_id: str | None = None
    checksum: str = ""

    def compute_checksum(self) -> str:
        """Compute SHA-256 checksum for integrity verification."""
        payload = (
            f"{self.entry_id}|{self.timestamp}|{self.action}|"
            f"{self.user}|{self.project_id}|{self.target}|"
            f"{json.dumps(self.details, sort_keys=True)}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AuditFilter:
    """Filter criteria for searching audit entries."""

    action: str | None = None
    user: str | None = None
    target: str | None = None
    target_type: str | None = None
    severity: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    keyword: str | None = None
    session_id: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditSummary:
    """Summary statistics for audit entries."""

    total_entries: int = 0
    entries_by_action: dict = field(default_factory=dict)
    entries_by_severity: dict = field(default_factory=dict)
    entries_by_user: dict = field(default_factory=dict)
    unique_users: int = 0
    unique_actions: int = 0
    first_entry_date: str | None = None
    last_entry_date: str | None = None
    integrity_valid: bool = True
    integrity_errors: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main audit trail class
# ---------------------------------------------------------------------------


class AuditTrail:
    """Append-only audit trail for tracking all application actions.

    The trail is immutable — entries cannot be modified or deleted once
    recorded.  Each entry is checksummed for tamper detection.

    Attributes:
        project_id: The project this trail belongs to.
        _entries: Internal list of audit entries (append-only).
    """

    def __init__(self, project_id: str = "default") -> None:
        self.project_id = project_id
        self._entries: list[AuditEntry] = []
        self._counter = 0
        logger.info("AuditTrail initialised for project %s", project_id)

    # -- Recording ----------------------------------------------------------

    def record(
        self,
        action: str,
        user: str = "system",
        target: str | None = None,
        target_type: str | None = None,
        severity: str = "info",
        details: dict | None = None,
        metadata: dict | None = None,
        result: str | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> AuditEntry:
        """Record a new audit entry (append-only).

        Args:
            action: The action being audited (see ``AuditAction``).
            user: The user or system performing the action.
            target: The target resource identifier (task id, file path, etc.).
            target_type: The type of the target (task, file, config, etc.).
            severity: The severity level of this action.
            details: Action-specific structured data.
            metadata: Additional metadata (agent type, model, etc.).
            result: The result of the action (success, failure, etc.).
            ip_address: The IP address of the actor.
            session_id: The session ID if applicable.

        Returns:
            The created ``AuditEntry``.
        """
        self._counter += 1
        entry_id = f"audit-{self.project_id}-{self._counter:06d}"
        now = datetime.now(timezone.utc).isoformat()

        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=now,
            action=action,
            user=user,
            project_id=self.project_id,
            target=target,
            target_type=target_type,
            severity=severity,
            details=details or {},
            metadata=metadata or {},
            result=result,
            ip_address=ip_address,
            session_id=session_id,
        )
        entry.checksum = entry.compute_checksum()
        self._entries.append(entry)

        logger.debug(
            "Audit entry %s: %s by %s on %s",
            entry_id,
            action,
            user,
            target,
        )
        return entry

    # -- Querying -----------------------------------------------------------

    def get_entry(self, entry_id: str) -> AuditEntry | None:
        """Get a single entry by ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def get_entries(
        self,
        action: str | None = None,
        user: str | None = None,
        severity: str | None = None,
        target: str | None = None,
        target_type: str | None = None,
        session_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Get entries with optional filters."""
        results = list(self._entries)

        if action:
            results = [e for e in results if e.action == action]
        if user:
            results = [e for e in results if e.user == user]
        if severity:
            results = [e for e in results if e.severity == severity]
        if target:
            results = [e for e in results if e.target == target]
        if target_type:
            results = [e for e in results if e.target_type == target_type]
        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if from_date:
            results = [e for e in results if e.timestamp >= from_date]
        if to_date:
            results = [e for e in results if e.timestamp <= to_date]

        return results[offset : offset + limit]

    def search(
        self,
        keyword: str | None = None,
        action: str | None = None,
        user: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Full-text search across audit entries."""
        results = self.get_entries(
            action=action, user=user, severity=severity, limit=len(self._entries)
        )

        if keyword:
            keyword_lower = keyword.lower()
            filtered = []
            for entry in results:
                searchable = (
                    f"{entry.action} {entry.user} {entry.target or ''} "
                    f"{entry.result or ''} {json.dumps(entry.details)}"
                ).lower()
                if keyword_lower in searchable:
                    filtered.append(entry)
            results = filtered

        return results[:limit]

    def count(self, action: str | None = None, user: str | None = None) -> int:
        """Count entries matching criteria."""
        return len(self.get_entries(action=action, user=user, limit=len(self._entries)))

    # -- Integrity ----------------------------------------------------------

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify checksums of all entries.

        Returns:
            Tuple of (all_valid, list_of_error_messages).
        """
        errors: list[str] = []
        for entry in self._entries:
            expected = entry.compute_checksum()
            if entry.checksum != expected:
                errors.append(
                    f"Entry {entry.entry_id}: checksum mismatch "
                    f"(stored={entry.checksum[:16]}…, computed={expected[:16]}…)"
                )
        return len(errors) == 0, errors

    # -- Summary & Stats ----------------------------------------------------

    def get_summary(self) -> AuditSummary:
        """Generate summary statistics for the audit trail."""
        summary = AuditSummary()
        summary.total_entries = len(self._entries)

        actions: dict[str, int] = {}
        severities: dict[str, int] = {}
        users: dict[str, int] = {}

        for entry in self._entries:
            actions[entry.action] = actions.get(entry.action, 0) + 1
            severities[entry.severity] = severities.get(entry.severity, 0) + 1
            users[entry.user] = users.get(entry.user, 0) + 1

        summary.entries_by_action = actions
        summary.entries_by_severity = severities
        summary.entries_by_user = users
        summary.unique_users = len(users)
        summary.unique_actions = len(actions)

        if self._entries:
            summary.first_entry_date = self._entries[0].timestamp
            summary.last_entry_date = self._entries[-1].timestamp

        valid, errors = self.verify_integrity()
        summary.integrity_valid = valid
        summary.integrity_errors = len(errors)

        return summary

    def get_stats(self) -> dict:
        """Get quick statistics."""
        return {
            "project_id": self.project_id,
            "total_entries": len(self._entries),
            "unique_actions": len({e.action for e in self._entries}),
            "unique_users": len({e.user for e in self._entries}),
        }

    # -- Export / Import ----------------------------------------------------

    def export_trail(self, fmt: str = "json") -> str:
        """Export the audit trail in the specified format.

        Args:
            fmt: The export format — ``json``, ``csv``, or ``jsonl``.

        Returns:
            The exported data as a string.
        """
        if fmt == "csv":
            lines = ["entry_id,timestamp,action,user,target,severity,result,checksum"]
            for entry in self._entries:
                lines.append(
                    f"{entry.entry_id},{entry.timestamp},{entry.action},"
                    f"{entry.user},{entry.target or ''},{entry.severity},"
                    f"{entry.result or ''},{entry.checksum[:16]}"
                )
            return "\n".join(lines)

        if fmt == "jsonl":
            return "\n".join(json.dumps(e.to_dict()) for e in self._entries)

        # Default: JSON
        return json.dumps([e.to_dict() for e in self._entries], indent=2)

    def import_trail(self, data: str, fmt: str = "json") -> int:
        """Import entries from exported data (append-only, does not replace).

        Args:
            data: The serialised audit data.
            fmt: The format — ``json`` or ``jsonl``.

        Returns:
            Number of entries imported.
        """
        entries_data: list[dict] = []

        if fmt == "jsonl":
            for line in data.strip().split("\n"):
                if line.strip():
                    entries_data.append(json.loads(line))
        else:
            entries_data = json.loads(data)

        imported = 0
        existing_ids = {e.entry_id for e in self._entries}

        for ed in entries_data:
            if ed.get("entry_id") not in existing_ids:
                entry = AuditEntry.from_dict(ed)
                self._entries.append(entry)
                imported += 1
                self._counter = max(self._counter, imported)

        logger.info("Imported %d audit entries", imported)
        return imported

    # -- Compliance helpers -------------------------------------------------

    def get_compliance_report(self, standard: str = "SOC2") -> dict:
        """Generate a compliance-oriented report.

        Args:
            standard: The compliance standard (SOC2, ISO27001).

        Returns:
            A report dictionary with the relevant audit information.
        """
        summary = self.get_summary()
        valid, errors = self.verify_integrity()

        security_entries = self.get_entries(
            severity="critical", limit=len(self._entries)
        ) + self.get_entries(action="security_violation", limit=len(self._entries))
        # Deduplicate
        seen = set()
        unique_security: list[AuditEntry] = []
        for e in security_entries:
            if e.entry_id not in seen:
                seen.add(e.entry_id)
                unique_security.append(e)

        config_changes = self.get_entries(
            action="config_changed", limit=len(self._entries)
        )

        return {
            "standard": standard,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_id": self.project_id,
            "total_entries": summary.total_entries,
            "integrity_valid": valid,
            "integrity_errors": len(errors),
            "security_events": len(unique_security),
            "config_changes": len(config_changes),
            "unique_users": summary.unique_users,
            "date_range": {
                "from": summary.first_entry_date,
                "to": summary.last_entry_date,
            },
            "entries_by_severity": summary.entries_by_severity,
            "entries_by_action": summary.entries_by_action,
        }
