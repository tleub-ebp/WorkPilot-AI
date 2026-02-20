"""Auto-detection and Task Creation — Automatic problem detection for WorkPilot AI.

Monitors various sources (GitHub issues, security alerts, logs, merge conflicts)
and automatically creates tasks when problems are detected.

Feature 8.2 — Auto-detection et création de tâches.

Example:
    >>> from apps.backend.scheduling.auto_detector import AutoDetector, DetectionSource
    >>> detector = AutoDetector()
    >>> detector.register_source(GitHubIssueSource(owner="org", repo="repo"))
    >>> findings = detector.scan_all()
    >>> tasks = detector.create_tasks_from_findings(findings)
"""

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Detection types ─────────────────────────────────────────────────


class DetectionType(Enum):
    """Types of detected issues."""

    GITHUB_ISSUE = "github_issue"
    SECURITY_VULNERABILITY = "security_vulnerability"
    DEPENDENCY_UPDATE = "dependency_update"
    LOG_ERROR = "log_error"
    MERGE_CONFLICT = "merge_conflict"
    CODE_SMELL = "code_smell"
    IDEATION_RESULT = "ideation_result"
    SONARQUBE_ISSUE = "sonarqube_issue"


class DetectionSeverity(Enum):
    """Severity level of a detection."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_PRIORITY_MAP: dict[DetectionSeverity, int] = {
    DetectionSeverity.CRITICAL: 1,
    DetectionSeverity.HIGH: 2,
    DetectionSeverity.MEDIUM: 5,
    DetectionSeverity.LOW: 7,
    DetectionSeverity.INFO: 9,
}


# ── Detection finding ──────────────────────────────────────────────


@dataclass
class DetectionFinding:
    """A single finding from an auto-detection scan.

    Attributes:
        finding_id: Unique identifier (hash of source + key fields).
        detection_type: The type of issue detected.
        severity: The severity level.
        title: Short title of the finding.
        description: Detailed description.
        source: The source that detected this finding.
        metadata: Additional source-specific data.
        detected_at: When the finding was detected.
        auto_create_task: Whether to automatically create a task.
        suggested_action: The suggested action type for the scheduler.
        suggested_tags: Tags for the created task.
    """

    finding_id: str = ""
    detection_type: DetectionType = DetectionType.GITHUB_ISSUE
    severity: DetectionSeverity = DetectionSeverity.MEDIUM
    title: str = ""
    description: str = ""
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auto_create_task: bool = True
    suggested_action: str = ""
    suggested_tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.finding_id:
            raw = f"{self.detection_type.value}:{self.source}:{self.title}"
            self.finding_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def priority(self) -> int:
        """Map severity to priority (1-10)."""
        return SEVERITY_PRIORITY_MAP.get(self.severity, 5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "finding_id": self.finding_id,
            "detection_type": self.detection_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "metadata": self.metadata,
            "detected_at": self.detected_at.isoformat(),
            "auto_create_task": self.auto_create_task,
            "suggested_action": self.suggested_action,
            "suggested_tags": self.suggested_tags,
            "priority": self.priority,
        }


# ── Detection source (abstract) ────────────────────────────────────


class DetectionSource(ABC):
    """Abstract base for detection sources.

    Each source knows how to scan a specific area (GitHub, logs, deps, etc.)
    and produce findings.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique name for this detection source."""

    @abstractmethod
    def scan(self) -> list[DetectionFinding]:
        """Scan the source and return findings.

        Returns:
            List of detected findings.
        """

    @property
    def enabled(self) -> bool:
        """Whether this source is currently enabled."""
        return True


# ── GitHub Issue Source ─────────────────────────────────────────────


class GitHubIssueSource(DetectionSource):
    """Detect newly assigned GitHub issues and create tasks.

    Monitors a GitHub repository for issues assigned to the configured
    user and converts them to WorkPilot tasks.

    Attributes:
        owner: Repository owner.
        repo: Repository name.
        assignee: GitHub username to filter by.
        labels_filter: Only include issues with these labels.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        assignee: str = "",
        labels_filter: list[str] | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.assignee = assignee
        self.labels_filter = labels_filter or []
        self._seen_issues: set[int] = set()

    @property
    def source_name(self) -> str:
        return f"github:{self.owner}/{self.repo}"

    def scan(self) -> list[DetectionFinding]:
        """Scan GitHub issues (stub — uses metadata for testing).

        In production this would call the GitHub API. For now,
        it accepts pre-loaded issue data via ``load_issues()``.

        Returns:
            List of findings from new issues.
        """
        return []

    def scan_from_data(self, issues: list[dict[str, Any]]) -> list[DetectionFinding]:
        """Create findings from pre-loaded issue data.

        Args:
            issues: List of issue dictionaries with ``number``, ``title``,
                ``body``, ``labels``, ``assignee`` keys.

        Returns:
            List of findings for new issues.
        """
        findings: list[DetectionFinding] = []

        for issue in issues:
            issue_number = issue.get("number", 0)
            if issue_number in self._seen_issues:
                continue

            # Apply label filter
            issue_labels = [
                lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
                for lbl in issue.get("labels", [])
            ]
            if self.labels_filter:
                if not any(lbl in issue_labels for lbl in self.labels_filter):
                    continue

            severity = self._assess_severity(issue_labels)
            self._seen_issues.add(issue_number)

            findings.append(DetectionFinding(
                detection_type=DetectionType.GITHUB_ISSUE,
                severity=severity,
                title=f"[#{issue_number}] {issue.get('title', 'Untitled')}",
                description=issue.get("body", "")[:500],
                source=self.source_name,
                metadata={
                    "issue_number": issue_number,
                    "labels": issue_labels,
                    "url": issue.get("html_url", ""),
                },
                suggested_action="implement_feature",
                suggested_tags=["github", "auto-detected"] + issue_labels,
            ))

        return findings

    def _assess_severity(self, labels: list[str]) -> DetectionSeverity:
        """Assess severity from issue labels.

        Args:
            labels: List of label names.

        Returns:
            The assessed severity.
        """
        labels_lower = [lbl.lower() for lbl in labels]

        if any(k in labels_lower for k in ("critical", "urgent", "p0")):
            return DetectionSeverity.CRITICAL
        if any(k in labels_lower for k in ("bug", "security", "p1")):
            return DetectionSeverity.HIGH
        if any(k in labels_lower for k in ("enhancement", "feature", "p2")):
            return DetectionSeverity.MEDIUM
        return DetectionSeverity.LOW


# ── Security Vulnerability Source ──────────────────────────────────


class SecurityVulnerabilitySource(DetectionSource):
    """Detect security vulnerabilities from dependency scanning.

    Parses security scan results (e.g., npm audit, pip-audit, safety)
    and creates findings for vulnerable dependencies.
    """

    def __init__(self) -> None:
        self._seen_vulns: set[str] = set()

    @property
    def source_name(self) -> str:
        return "security:dependency-scan"

    def scan(self) -> list[DetectionFinding]:
        """Stub for live scanning."""
        return []

    def scan_from_data(
        self, vulnerabilities: list[dict[str, Any]]
    ) -> list[DetectionFinding]:
        """Create findings from vulnerability scan data.

        Args:
            vulnerabilities: List of vulnerability dictionaries with
                ``package``, ``severity``, ``description``, ``fix_version`` keys.

        Returns:
            List of findings for new vulnerabilities.
        """
        findings: list[DetectionFinding] = []

        for vuln in vulnerabilities:
            pkg = vuln.get("package", "unknown")
            vuln_id = vuln.get("id", f"{pkg}-{vuln.get('version', '')}")

            if vuln_id in self._seen_vulns:
                continue
            self._seen_vulns.add(vuln_id)

            severity_str = vuln.get("severity", "medium").lower()
            severity_map = {
                "critical": DetectionSeverity.CRITICAL,
                "high": DetectionSeverity.HIGH,
                "moderate": DetectionSeverity.MEDIUM,
                "medium": DetectionSeverity.MEDIUM,
                "low": DetectionSeverity.LOW,
            }
            severity = severity_map.get(severity_str, DetectionSeverity.MEDIUM)

            findings.append(DetectionFinding(
                detection_type=DetectionType.SECURITY_VULNERABILITY,
                severity=severity,
                title=f"Security: {pkg} — {vuln.get('title', vuln_id)}",
                description=vuln.get("description", "")[:500],
                source=self.source_name,
                metadata={
                    "package": pkg,
                    "current_version": vuln.get("version", ""),
                    "fix_version": vuln.get("fix_version", ""),
                    "vuln_id": vuln_id,
                    "cve": vuln.get("cve", ""),
                },
                suggested_action="fix_vulnerability",
                suggested_tags=["security", "dependency", "auto-detected"],
            ))

        return findings


# ── Log Error Source ───────────────────────────────────────────────


class LogErrorSource(DetectionSource):
    """Detect recurring errors from application logs.

    Analyzes log entries to find recurring error patterns and creates
    debugging tasks when an error appears multiple times.

    Attributes:
        error_threshold: Minimum occurrences before creating a finding.
    """

    def __init__(self, error_threshold: int = 3) -> None:
        self.error_threshold = error_threshold
        self._error_counts: dict[str, int] = {}
        self._reported_errors: set[str] = set()

    @property
    def source_name(self) -> str:
        return "logs:error-monitor"

    def scan(self) -> list[DetectionFinding]:
        """Stub for live log scanning."""
        return []

    def ingest_log_entry(self, log_line: str) -> DetectionFinding | None:
        """Process a single log line and return a finding if threshold is reached.

        Args:
            log_line: The log line to analyze.

        Returns:
            A finding if the error threshold is reached, None otherwise.
        """
        error_key = self._normalize_error(log_line)
        if not error_key:
            return None

        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        if (
            self._error_counts[error_key] >= self.error_threshold
            and error_key not in self._reported_errors
        ):
            self._reported_errors.add(error_key)
            return DetectionFinding(
                detection_type=DetectionType.LOG_ERROR,
                severity=DetectionSeverity.HIGH,
                title=f"Recurring error: {error_key[:80]}",
                description=(
                    f"Error occurred {self._error_counts[error_key]} times:\n"
                    f"{log_line[:300]}"
                ),
                source=self.source_name,
                metadata={
                    "error_key": error_key,
                    "count": self._error_counts[error_key],
                    "sample_line": log_line[:500],
                },
                suggested_action="debug_error",
                suggested_tags=["error", "recurring", "auto-detected"],
            )

        return None

    def scan_from_data(self, log_lines: list[str]) -> list[DetectionFinding]:
        """Scan multiple log lines and return findings.

        Args:
            log_lines: List of log line strings.

        Returns:
            List of findings for recurring errors.
        """
        findings: list[DetectionFinding] = []
        for line in log_lines:
            finding = self.ingest_log_entry(line)
            if finding:
                findings.append(finding)
        return findings

    def _normalize_error(self, log_line: str) -> str:
        """Normalize a log line into an error key for deduplication.

        Removes timestamps, PIDs, and variable data to group similar errors.

        Args:
            log_line: The raw log line.

        Returns:
            Normalized error key, or empty string if not an error.
        """
        line = log_line.strip()
        if not line:
            return ""

        # Check if it looks like an error
        error_patterns = ["error", "exception", "traceback", "failed", "critical"]
        if not any(p in line.lower() for p in error_patterns):
            return ""

        # Remove timestamps (ISO format, common log formats)
        normalized = re.sub(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*\s*", "", line
        )
        # Remove PID/thread numbers
        normalized = re.sub(r"\b\d{4,}\b", "<NUM>", normalized)
        # Remove hex addresses
        normalized = re.sub(r"0x[0-9a-fA-F]+", "<ADDR>", normalized)
        # Remove file paths with line numbers
        normalized = re.sub(r'["\']?/[\w/._-]+:\d+["\']?', "<FILE>", normalized)
        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized[:200]


# ── Merge Conflict Source ──────────────────────────────────────────


class MergeConflictSource(DetectionSource):
    """Detect frequent merge conflicts and suggest refactoring.

    Tracks files with repeated merge conflicts and creates
    refactoring tasks when a threshold is reached.

    Attributes:
        conflict_threshold: Number of conflicts before flagging.
    """

    def __init__(self, conflict_threshold: int = 3) -> None:
        self.conflict_threshold = conflict_threshold
        self._conflict_counts: dict[str, int] = {}
        self._reported_files: set[str] = set()

    @property
    def source_name(self) -> str:
        return "git:merge-conflicts"

    def scan(self) -> list[DetectionFinding]:
        """Stub for live conflict scanning."""
        return []

    def record_conflict(self, file_path: str) -> DetectionFinding | None:
        """Record a merge conflict for a file.

        Args:
            file_path: The conflicted file path.

        Returns:
            A finding if the threshold is reached, None otherwise.
        """
        self._conflict_counts[file_path] = (
            self._conflict_counts.get(file_path, 0) + 1
        )

        if (
            self._conflict_counts[file_path] >= self.conflict_threshold
            and file_path not in self._reported_files
        ):
            self._reported_files.add(file_path)
            return DetectionFinding(
                detection_type=DetectionType.MERGE_CONFLICT,
                severity=DetectionSeverity.MEDIUM,
                title=f"Frequent merge conflicts: {file_path}",
                description=(
                    f"File '{file_path}' has had "
                    f"{self._conflict_counts[file_path]} merge conflicts. "
                    f"Consider refactoring to reduce coupling."
                ),
                source=self.source_name,
                metadata={
                    "file_path": file_path,
                    "conflict_count": self._conflict_counts[file_path],
                },
                suggested_action="refactor_file",
                suggested_tags=["merge-conflict", "refactoring", "auto-detected"],
            )

        return None

    def scan_from_data(
        self, conflict_files: list[str]
    ) -> list[DetectionFinding]:
        """Record multiple conflict files and return findings.

        Args:
            conflict_files: List of file paths with conflicts.

        Returns:
            List of findings for frequently conflicted files.
        """
        findings: list[DetectionFinding] = []
        for fp in conflict_files:
            finding = self.record_conflict(fp)
            if finding:
                findings.append(finding)
        return findings


# ── Auto detector orchestrator ─────────────────────────────────────


class AutoDetector:
    """Orchestrates multiple detection sources and creates tasks.

    Manages registration of detection sources, runs scans,
    deduplicates findings, and converts findings into schedulable tasks.

    Attributes:
        _sources: Registered detection sources.
        _findings: All detected findings (deduplicated).
        _created_task_ids: Set of finding IDs that have been converted to tasks.

    Example:
        >>> detector = AutoDetector()
        >>> detector.register_source(GitHubIssueSource("org", "repo"))
        >>> detector.register_source(SecurityVulnerabilitySource())
        >>> findings = detector.scan_all()
    """

    def __init__(self) -> None:
        self._sources: list[DetectionSource] = []
        self._findings: dict[str, DetectionFinding] = {}
        self._created_task_ids: set[str] = set()

    def register_source(self, source: DetectionSource) -> None:
        """Register a detection source.

        Args:
            source: The detection source to register.
        """
        self._sources.append(source)
        logger.info("Registered detection source: %s", source.source_name)

    def scan_all(self) -> list[DetectionFinding]:
        """Run all registered sources and collect findings.

        Returns:
            List of new (deduplicated) findings.
        """
        new_findings: list[DetectionFinding] = []

        for source in self._sources:
            if not source.enabled:
                continue

            try:
                findings = source.scan()
                for finding in findings:
                    if finding.finding_id not in self._findings:
                        self._findings[finding.finding_id] = finding
                        new_findings.append(finding)
            except Exception as e:
                logger.error(
                    "Error scanning source '%s': %s",
                    source.source_name, e,
                )

        logger.info(
            "Scan complete: %d new findings from %d sources.",
            len(new_findings), len(self._sources),
        )
        return new_findings

    def add_findings(self, findings: list[DetectionFinding]) -> list[DetectionFinding]:
        """Add externally-produced findings (e.g., from scan_from_data).

        Deduplicates against existing findings.

        Args:
            findings: List of findings to add.

        Returns:
            List of newly added (non-duplicate) findings.
        """
        new_findings: list[DetectionFinding] = []
        for finding in findings:
            if finding.finding_id not in self._findings:
                self._findings[finding.finding_id] = finding
                new_findings.append(finding)
        return new_findings

    def get_findings(
        self,
        detection_type: DetectionType | None = None,
        min_severity: DetectionSeverity | None = None,
    ) -> list[DetectionFinding]:
        """Get all findings, optionally filtered.

        Args:
            detection_type: Filter by detection type.
            min_severity: Filter by minimum severity.

        Returns:
            Sorted list of findings (highest severity first).
        """
        findings = list(self._findings.values())

        if detection_type:
            findings = [f for f in findings if f.detection_type == detection_type]

        if min_severity:
            max_priority = SEVERITY_PRIORITY_MAP.get(min_severity, 5)
            findings = [f for f in findings if f.priority <= max_priority]

        findings.sort(key=lambda f: f.priority)
        return findings

    def create_tasks_from_findings(
        self,
        findings: list[DetectionFinding] | None = None,
        auto_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Convert findings into task creation requests.

        Args:
            findings: Findings to convert. If None, uses all pending findings.
            auto_only: Only convert findings marked for auto-creation.

        Returns:
            List of task dictionaries ready for the scheduler.
        """
        if findings is None:
            findings = [
                f for f in self._findings.values()
                if f.finding_id not in self._created_task_ids
            ]

        if auto_only:
            findings = [f for f in findings if f.auto_create_task]

        tasks: list[dict[str, Any]] = []
        for finding in findings:
            if finding.finding_id in self._created_task_ids:
                continue

            task = {
                "task_id": f"auto-{finding.finding_id}",
                "name": finding.title,
                "action": finding.suggested_action or "generic_task",
                "priority": finding.priority,
                "metadata": {
                    "finding_id": finding.finding_id,
                    "detection_type": finding.detection_type.value,
                    "severity": finding.severity.value,
                    "description": finding.description,
                    "source": finding.source,
                    **finding.metadata,
                },
                "tags": finding.suggested_tags,
            }
            tasks.append(task)
            self._created_task_ids.add(finding.finding_id)

        logger.info("Created %d tasks from findings.", len(tasks))
        return tasks

    def get_stats(self) -> dict[str, Any]:
        """Get detector statistics.

        Returns:
            Dictionary with counts by type and severity.
        """
        findings = list(self._findings.values())

        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for f in findings:
            by_type[f.detection_type.value] = by_type.get(f.detection_type.value, 0) + 1
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

        return {
            "total_findings": len(findings),
            "tasks_created": len(self._created_task_ids),
            "sources_registered": len(self._sources),
            "by_type": by_type,
            "by_severity": by_severity,
        }
