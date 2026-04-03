"""Tests for Feature 8.2 — Auto-detection and Task Creation.

Tests for DetectionFinding, detection sources (GitHub, Security, Logs,
MergeConflict), and the AutoDetector orchestrator.
"""

import pytest

from apps.backend.scheduling.auto_detector import (
    AutoDetector,
    DetectionFinding,
    DetectionSeverity,
    DetectionType,
    GitHubIssueSource,
    LogErrorSource,
    MergeConflictSource,
    SecurityVulnerabilitySource,
)

# ── DetectionFinding tests ─────────────────────────────────────────


class TestDetectionFinding:
    """Tests for the DetectionFinding dataclass."""

    def test_auto_id_generation(self):
        """Finding should get a hash-based ID if none provided."""
        finding = DetectionFinding(
            detection_type=DetectionType.GITHUB_ISSUE,
            title="Test",
            source="test",
        )
        assert finding.finding_id
        assert len(finding.finding_id) == 12

    def test_explicit_id(self):
        """Explicit finding_id should be preserved."""
        finding = DetectionFinding(finding_id="explicit-123")
        assert finding.finding_id == "explicit-123"

    def test_priority_mapping(self):
        """Severity should map to correct priority."""
        critical = DetectionFinding(severity=DetectionSeverity.CRITICAL)
        assert critical.priority == 1
        low = DetectionFinding(severity=DetectionSeverity.LOW)
        assert low.priority == 7

    def test_to_dict(self):
        """to_dict should include all fields."""
        finding = DetectionFinding(
            detection_type=DetectionType.SECURITY_VULNERABILITY,
            severity=DetectionSeverity.HIGH,
            title="Vuln",
            source="test",
        )
        d = finding.to_dict()
        assert d["detection_type"] == "security_vulnerability"
        assert d["severity"] == "high"
        assert d["title"] == "Vuln"
        assert "finding_id" in d
        assert "priority" in d


# ── GitHubIssueSource tests ────────────────────────────────────────


class TestGitHubIssueSource:
    """Tests for GitHub issue detection source."""

    def setup_method(self):
        self.source = GitHubIssueSource(owner="org", repo="repo")

    def test_source_name(self):
        """source_name should include owner/repo."""
        assert self.source.source_name == "github:org/repo"

    def test_scan_from_data_creates_findings(self):
        """scan_from_data should create findings from issues."""
        issues = [
            {"number": 1, "title": "Bug in login", "body": "Details", "labels": [{"name": "bug"}]},
            {"number": 2, "title": "New feature", "body": "Request", "labels": [{"name": "enhancement"}]},
        ]
        findings = self.source.scan_from_data(issues)
        assert len(findings) == 2
        assert "[#1]" in findings[0].title
        assert findings[0].detection_type == DetectionType.GITHUB_ISSUE

    def test_deduplication(self):
        """Same issue should not produce duplicate findings."""
        issues = [{"number": 1, "title": "Bug", "body": "", "labels": []}]
        self.source.scan_from_data(issues)
        findings2 = self.source.scan_from_data(issues)
        assert len(findings2) == 0

    def test_label_filter(self):
        """Label filter should exclude non-matching issues."""
        source = GitHubIssueSource(owner="o", repo="r", labels_filter=["bug"])
        issues = [
            {"number": 1, "title": "Bug", "body": "", "labels": [{"name": "bug"}]},
            {"number": 2, "title": "Feature", "body": "", "labels": [{"name": "enhancement"}]},
        ]
        findings = source.scan_from_data(issues)
        assert len(findings) == 1
        assert "[#1]" in findings[0].title

    def test_severity_critical(self):
        """Issues with 'critical' label should get CRITICAL severity."""
        issues = [{"number": 1, "title": "X", "body": "", "labels": [{"name": "critical"}]}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].severity == DetectionSeverity.CRITICAL

    def test_severity_high_bug(self):
        """Issues with 'bug' label should get HIGH severity."""
        issues = [{"number": 10, "title": "X", "body": "", "labels": [{"name": "bug"}]}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].severity == DetectionSeverity.HIGH

    def test_severity_medium_enhancement(self):
        """Issues with 'enhancement' label should get MEDIUM severity."""
        issues = [{"number": 20, "title": "X", "body": "", "labels": [{"name": "enhancement"}]}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].severity == DetectionSeverity.MEDIUM

    def test_severity_low_default(self):
        """Issues with no known labels should get LOW severity."""
        issues = [{"number": 30, "title": "X", "body": "", "labels": [{"name": "docs"}]}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].severity == DetectionSeverity.LOW

    def test_string_labels(self):
        """Labels provided as strings (not dicts) should be handled."""
        issues = [{"number": 40, "title": "X", "body": "", "labels": ["bug"]}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].severity == DetectionSeverity.HIGH

    def test_metadata_includes_issue_number(self):
        """Metadata should contain the issue number."""
        issues = [{"number": 5, "title": "X", "body": "", "labels": []}]
        findings = self.source.scan_from_data(issues)
        assert findings[0].metadata["issue_number"] == 5


# ── SecurityVulnerabilitySource tests ──────────────────────────────


class TestSecurityVulnerabilitySource:
    """Tests for security vulnerability detection source."""

    def setup_method(self):
        self.source = SecurityVulnerabilitySource()

    def test_source_name(self):
        assert self.source.source_name == "security:dependency-scan"

    def test_scan_from_data(self):
        """Should create findings from vulnerability data."""
        vulns = [
            {
                "id": "CVE-2026-001",
                "package": "lodash",
                "severity": "high",
                "title": "Prototype Pollution",
                "description": "Details here",
                "version": "4.17.15",
                "fix_version": "4.17.21",
            },
        ]
        findings = self.source.scan_from_data(vulns)
        assert len(findings) == 1
        assert findings[0].severity == DetectionSeverity.HIGH
        assert "lodash" in findings[0].title
        assert findings[0].metadata["package"] == "lodash"

    def test_deduplication(self):
        """Same vulnerability should not be reported twice."""
        vulns = [{"id": "V1", "package": "pkg", "severity": "medium", "title": "T"}]
        self.source.scan_from_data(vulns)
        assert len(self.source.scan_from_data(vulns)) == 0

    def test_critical_severity(self):
        """Critical vulns should get CRITICAL severity."""
        vulns = [{"id": "V2", "package": "p", "severity": "critical", "title": "T"}]
        findings = self.source.scan_from_data(vulns)
        assert findings[0].severity == DetectionSeverity.CRITICAL

    def test_moderate_maps_to_medium(self):
        """'moderate' severity should map to MEDIUM."""
        vulns = [{"id": "V3", "package": "p", "severity": "moderate", "title": "T"}]
        findings = self.source.scan_from_data(vulns)
        assert findings[0].severity == DetectionSeverity.MEDIUM


# ── LogErrorSource tests ──────────────────────────────────────────


class TestLogErrorSource:
    """Tests for log error detection source."""

    def setup_method(self):
        self.source = LogErrorSource(error_threshold=3)

    def test_source_name(self):
        assert self.source.source_name == "logs:error-monitor"

    def test_threshold_detection(self):
        """Finding should be created only after threshold is reached."""
        line = "2026-02-20T14:00:00 ERROR: Connection failed to database"
        assert self.source.ingest_log_entry(line) is None
        assert self.source.ingest_log_entry(line) is None
        finding = self.source.ingest_log_entry(line)
        assert finding is not None
        assert finding.severity == DetectionSeverity.HIGH
        assert "Recurring error" in finding.title

    def test_no_false_positives(self):
        """Non-error lines should not produce findings."""
        line = "2026-02-20 INFO: Application started successfully"
        for _ in range(5):
            assert self.source.ingest_log_entry(line) is None

    def test_different_errors_tracked_separately(self):
        """Different errors should have separate counters."""
        line_a = "ERROR: Connection failed"
        line_b = "ERROR: Timeout on request"
        for _ in range(2):
            self.source.ingest_log_entry(line_a)
            self.source.ingest_log_entry(line_b)
        finding_a = self.source.ingest_log_entry(line_a)
        finding_b = self.source.ingest_log_entry(line_b)
        assert finding_a is not None
        assert finding_b is not None

    def test_scan_from_data(self):
        """scan_from_data should process multiple lines."""
        lines = ["ERROR: something broke"] * 5
        findings = self.source.scan_from_data(lines)
        assert len(findings) == 1

    def test_no_duplicate_reports(self):
        """Same error beyond threshold should not re-report."""
        line = "ERROR: db failure"
        for _ in range(3):
            self.source.ingest_log_entry(line)
        # 4th occurrence should not create a new finding
        assert self.source.ingest_log_entry(line) is None

    def test_empty_line_ignored(self):
        """Empty lines should be ignored."""
        assert self.source.ingest_log_entry("") is None
        assert self.source.ingest_log_entry("   ") is None


# ── MergeConflictSource tests ─────────────────────────────────────


class TestMergeConflictSource:
    """Tests for merge conflict detection source."""

    def setup_method(self):
        self.source = MergeConflictSource(conflict_threshold=3)

    def test_source_name(self):
        assert self.source.source_name == "git:merge-conflicts"

    def test_threshold_detection(self):
        """Finding should be created after threshold conflicts."""
        assert self.source.record_conflict("src/app.py") is None
        assert self.source.record_conflict("src/app.py") is None
        finding = self.source.record_conflict("src/app.py")
        assert finding is not None
        assert "src/app.py" in finding.title
        assert finding.metadata["conflict_count"] == 3

    def test_different_files(self):
        """Different files should have separate counters."""
        for _ in range(3):
            self.source.record_conflict("a.py")
        finding_b = self.source.record_conflict("b.py")
        assert finding_b is None  # b.py only has 1 conflict

    def test_scan_from_data(self):
        """scan_from_data should process multiple conflict events."""
        files = ["x.py"] * 4
        findings = self.source.scan_from_data(files)
        assert len(findings) == 1

    def test_no_duplicate_report(self):
        """Same file beyond threshold should not re-report."""
        for _ in range(3):
            self.source.record_conflict("c.py")
        assert self.source.record_conflict("c.py") is None


# ── AutoDetector tests ─────────────────────────────────────────────


class TestAutoDetector:
    """Tests for the AutoDetector orchestrator."""

    def test_register_source(self):
        """Should register detection sources."""
        detector = AutoDetector()
        detector.register_source(GitHubIssueSource("o", "r"))
        assert detector.get_stats()["sources_registered"] == 1

    def test_add_findings(self):
        """add_findings should deduplicate."""
        detector = AutoDetector()
        f1 = DetectionFinding(finding_id="a", title="A")
        f2 = DetectionFinding(finding_id="b", title="B")
        f1_dup = DetectionFinding(finding_id="a", title="A dup")

        new = detector.add_findings([f1, f2, f1_dup])
        assert len(new) == 2
        assert detector.get_stats()["total_findings"] == 2

    def test_get_findings_filtered_by_type(self):
        """get_findings should filter by type."""
        detector = AutoDetector()
        detector.add_findings([
            DetectionFinding(finding_id="g1", detection_type=DetectionType.GITHUB_ISSUE, title="GH"),
            DetectionFinding(finding_id="s1", detection_type=DetectionType.SECURITY_VULNERABILITY, title="Sec"),
        ])
        gh = detector.get_findings(detection_type=DetectionType.GITHUB_ISSUE)
        assert len(gh) == 1
        assert gh[0].title == "GH"

    def test_get_findings_filtered_by_severity(self):
        """get_findings should filter by minimum severity."""
        detector = AutoDetector()
        detector.add_findings([
            DetectionFinding(finding_id="h1", severity=DetectionSeverity.HIGH, title="High"),
            DetectionFinding(finding_id="l1", severity=DetectionSeverity.LOW, title="Low"),
        ])
        high_only = detector.get_findings(min_severity=DetectionSeverity.HIGH)
        assert len(high_only) == 1
        assert high_only[0].title == "High"

    def test_create_tasks_from_findings(self):
        """Should create task dicts from findings."""
        detector = AutoDetector()
        detector.add_findings([
            DetectionFinding(
                finding_id="t1",
                title="Task 1",
                severity=DetectionSeverity.HIGH,
                suggested_action="fix",
                suggested_tags=["auto"],
            ),
        ])
        tasks = detector.create_tasks_from_findings()
        assert len(tasks) == 1
        assert tasks[0]["name"] == "Task 1"
        assert tasks[0]["action"] == "fix"
        assert tasks[0]["priority"] == 2

    def test_create_tasks_deduplication(self):
        """Should not create duplicate tasks."""
        detector = AutoDetector()
        detector.add_findings([
            DetectionFinding(finding_id="d1", title="D"),
        ])
        detector.create_tasks_from_findings()
        second_run = detector.create_tasks_from_findings()
        assert len(second_run) == 0

    def test_auto_only_filter(self):
        """auto_only=True should skip findings with auto_create_task=False."""
        detector = AutoDetector()
        detector.add_findings([
            DetectionFinding(finding_id="a1", title="Auto", auto_create_task=True),
            DetectionFinding(finding_id="m1", title="Manual", auto_create_task=False),
        ])
        tasks = detector.create_tasks_from_findings(auto_only=True)
        assert len(tasks) == 1
        assert tasks[0]["name"] == "Auto"

    def test_get_stats(self):
        """get_stats should return correct counts."""
        detector = AutoDetector()
        detector.register_source(GitHubIssueSource("o", "r"))
        detector.add_findings([
            DetectionFinding(
                finding_id="s1",
                detection_type=DetectionType.SECURITY_VULNERABILITY,
                severity=DetectionSeverity.HIGH,
            ),
        ])
        stats = detector.get_stats()
        assert stats["total_findings"] == 1
        assert stats["sources_registered"] == 1
        assert stats["by_type"]["security_vulnerability"] == 1
        assert stats["by_severity"]["high"] == 1
