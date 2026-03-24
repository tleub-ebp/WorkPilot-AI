"""
QA Security Scanner
====================

Integrates SAST/DAST-style security scanning into the QA pipeline.

Before merge, automatically:
- Runs SAST tools (Bandit, Semgrep, ESLint security)
- Scans for exposed secrets
- Checks dependency vulnerabilities (npm audit, pip-audit)
- Pattern-matches common web vulnerabilities (SQL injection, XSS, CSRF)
- Generates a structured security report embedded in the QA report

The QA fixer can auto-resolve critical issues.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .vulnerability_scanner import (
    ScanResult,
    Severity,
    Vulnerability,
    VulnerabilityScanner,
    VulnerabilitySource,
)

# =============================================================================
# WEB VULNERABILITY PATTERNS (no external tools required)
# =============================================================================


@dataclass
class PatternRule:
    """A regex-based code pattern that signals a potential vulnerability."""

    id: str
    title: str
    pattern: str  # Regex to search
    severity: Severity
    description: str
    remediation: str
    file_extensions: set[str]  # Extensions to scan
    cwe: str | None = None


_WEB_VULN_PATTERNS: list[PatternRule] = [
    # SQL Injection
    PatternRule(
        id="SQL-001",
        title="Potential SQL Injection",
        pattern=r'(?:execute|query|raw)\s*\(\s*["\'].*?%s|f["\'].*?SELECT|f["\'].*?INSERT|f["\'].*?UPDATE|f["\'].*?DELETE',
        severity=Severity.CRITICAL,
        description="String interpolation in SQL query detected. Use parameterized queries.",
        remediation="Replace string formatting in SQL with parameterized queries or an ORM.",
        file_extensions={".py", ".js", ".ts", ".php"},
        cwe="CWE-89",
    ),
    PatternRule(
        id="SQL-002",
        title="Raw SQL with format string",
        pattern=r'\.execute\s*\(\s*f["\']|\.execute\s*\(\s*["\'].*?\s*\+\s*',
        severity=Severity.HIGH,
        description="Dynamic SQL construction via f-string or concatenation.",
        remediation="Use parameterized queries: cursor.execute('SELECT ... WHERE id = %s', (id,))",
        file_extensions={".py"},
        cwe="CWE-89",
    ),
    # XSS
    PatternRule(
        id="XSS-001",
        title="Potential XSS: innerHTML / dangerouslySetInnerHTML",
        pattern=r"innerHTML\s*=|dangerouslySetInnerHTML\s*=\s*\{",
        severity=Severity.HIGH,
        description="Direct DOM manipulation or dangerouslySetInnerHTML can introduce XSS.",
        remediation="Sanitize user input with DOMPurify before inserting into DOM.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        cwe="CWE-79",
    ),
    PatternRule(
        id="XSS-002",
        title="Potential XSS: document.write",
        pattern=r"document\.write\s*\(",
        severity=Severity.HIGH,
        description="document.write with user-controlled data enables XSS.",
        remediation="Use safer DOM APIs (textContent, createElement) instead of document.write.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        cwe="CWE-79",
    ),
    # CSRF
    PatternRule(
        id="CSRF-001",
        title="Missing CSRF protection on state-changing endpoint",
        pattern=r'@app\.route.*methods=.*["\']POST["\']|@router\.(post|put|delete|patch)\(',
        severity=Severity.MEDIUM,
        description="State-changing endpoint detected. Verify CSRF token validation is in place.",
        remediation="Ensure CSRF middleware is applied or use SameSite cookie policy.",
        file_extensions={".py", ".js", ".ts"},
        cwe="CWE-352",
    ),
    # Hardcoded credentials
    PatternRule(
        id="SECRET-001",
        title="Hardcoded password or secret",
        pattern=r'(?:password|passwd|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{8,}["\']',
        severity=Severity.CRITICAL,
        description="Possible hardcoded credential detected.",
        remediation="Move secrets to environment variables. Use a secrets manager in production.",
        file_extensions={".py", ".js", ".ts", ".env", ".json", ".yaml", ".yml"},
        cwe="CWE-798",
    ),
    # Command injection
    PatternRule(
        id="CMD-001",
        title="Potential command injection",
        pattern=r"subprocess\.(run|call|Popen|check_output)\s*\(.*shell\s*=\s*True",
        severity=Severity.HIGH,
        description="shell=True with user-controlled input enables command injection.",
        remediation="Use shell=False and pass arguments as a list. Validate all inputs.",
        file_extensions={".py"},
        cwe="CWE-78",
    ),
    PatternRule(
        id="CMD-002",
        title="Potential command injection via exec/eval",
        pattern=r"\beval\s*\(|\bexec\s*\(",
        severity=Severity.HIGH,
        description="eval/exec with user-controlled input enables code injection.",
        remediation="Avoid eval/exec. Use safe alternatives (ast.literal_eval for data).",
        file_extensions={".py", ".js", ".ts"},
        cwe="CWE-95",
    ),
    # Path traversal
    PatternRule(
        id="PATH-001",
        title="Potential path traversal",
        pattern=r"open\s*\(\s*(?:request\.|user_input|params\[)",
        severity=Severity.HIGH,
        description="File path constructed from user input may enable path traversal.",
        remediation="Validate and sanitize file paths. Use os.path.abspath and check against allowed base.",
        file_extensions={".py"},
        cwe="CWE-22",
    ),
]


# =============================================================================
# QA SECURITY SCANNER
# =============================================================================


@dataclass
class SecurityScanSummary:
    """Summary of a QA security scan — ready for embedding in a QA report."""

    scan_result: ScanResult
    pattern_findings: list[Vulnerability] = field(default_factory=list)
    passed: bool = True  # True if no critical/high issues
    blocking: bool = False  # True if build should be blocked (critical issues)
    duration_seconds: float = 0.0

    @property
    def all_vulnerabilities(self) -> list[Vulnerability]:
        return self.scan_result.vulnerabilities + self.pattern_findings

    @property
    def critical_count(self) -> int:
        return sum(
            1 for v in self.all_vulnerabilities if v.severity == Severity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.all_vulnerabilities if v.severity == Severity.HIGH)

    def to_markdown(self) -> str:
        """Render the security scan results as a Markdown section for the QA report."""
        lines: list[str] = []
        lines.append("\n## 🔐 Security Scan Results\n")

        all_vulns = self.all_vulnerabilities
        if not all_vulns:
            lines.append("✅ **No security issues detected.**\n")
            lines.append(
                f"Scans run: {', '.join(self.scan_result.scans_run) or 'pattern-scan'}\n"
            )
            return "\n".join(lines)

        # Summary table
        c = self.critical_count
        h = self.high_count
        m = sum(1 for v in all_vulns if v.severity == Severity.MEDIUM)
        lo = sum(1 for v in all_vulns if v.severity == Severity.LOW)

        status_icon = "🚨" if self.blocking else ("⚠️" if not self.passed else "ℹ️")
        lines.append(
            f"{status_icon} **Security Summary:** Critical: {c} | High: {h} | Medium: {m} | Low: {lo}\n"
        )

        if self.blocking:
            lines.append(
                "> ❌ **BUILD BLOCKED** — Critical security vulnerabilities must be fixed before merge.\n"
            )
        elif not self.passed:
            lines.append(
                "> ⚠️ High-severity issues found. Review and fix before merge.\n"
            )

        lines.append(
            f"Scans run: {', '.join(self.scan_result.scans_run + ['pattern-scan'])}\n"
        )
        lines.append(f"Scan duration: {self.duration_seconds:.1f}s\n")

        # Detail sections by severity
        for severity in (
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
        ):
            group = [v for v in all_vulns if v.severity == severity]
            if not group:
                continue
            lines.append(f"\n### {severity.value.upper()} ({len(group)})\n")
            for v in group:
                location = (
                    f"`{v.file}:{v.line}`"
                    if v.file and v.line
                    else (f"`{v.file}`" if v.file else "")
                )
                lines.append(f"- **[{v.id}] {v.title}**")
                if location:
                    lines.append(f"  - Location: {location}")
                if v.cwe:
                    lines.append(f"  - CWE: {v.cwe}")
                lines.append(f"  - {v.description}")
                if v.remediation:
                    lines.append(f"  - 💡 Fix: {v.remediation}")

        if self.scan_result.scan_errors:
            lines.append("\n### Scan Errors\n")
            for err in self.scan_result.scan_errors:
                lines.append(f"- {err}")

        return "\n".join(lines)

    def to_qa_issues(self) -> list[dict]:
        """Convert high+ vulnerabilities to QA issue format for implementation_plan.json."""
        issues = []
        for v in self.all_vulnerabilities:
            if v.severity in (Severity.CRITICAL, Severity.HIGH):
                issues.append(
                    {
                        "type": v.severity.value,
                        "title": f"Security: {v.title}",
                        "location": f"{v.file}:{v.line}"
                        if v.file and v.line
                        else v.file or "",
                        "fix_required": v.remediation
                        or "Fix this security vulnerability",
                        "source": v.source.value,
                        "cwe": v.cwe,
                    }
                )
        return issues


class QASecurityScanner:
    """
    Runs security scans as part of the QA pipeline.

    Combines:
    1. Tool-based scans (Bandit, Semgrep, npm audit, pip-audit, secrets)
       via the existing VulnerabilityScanner
    2. Regex pattern-matching for common web vulnerabilities
       (SQL injection, XSS, CSRF, hardcoded secrets, command injection, path traversal)
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self._scanner = VulnerabilityScanner(self.project_dir)

    def scan(
        self,
        include_tool_scans: bool = True,
        include_pattern_scans: bool = True,
    ) -> SecurityScanSummary:
        """
        Run all security scans and return a summary.

        Args:
            include_tool_scans: Run Bandit/Semgrep/npm audit/pip-audit
            include_pattern_scans: Run regex pattern matching
        """
        start = time.time()

        # Tool-based scanning
        if include_tool_scans:
            scan_result = self._scanner.scan_all(
                include_secrets=True,
                include_sast=True,
                include_dependencies=True,
                include_containers=False,
            )
        else:
            scan_result = ScanResult(project_path=self.project_dir)

        # Pattern-based scanning
        pattern_findings: list[Vulnerability] = []
        if include_pattern_scans:
            pattern_findings = self._run_pattern_scan()
            scan_result.scans_run.append("pattern-scan")

        duration = time.time() - start

        # Combine and assess
        all_vulns = scan_result.vulnerabilities + pattern_findings
        critical = sum(1 for v in all_vulns if v.severity == Severity.CRITICAL)
        high = sum(1 for v in all_vulns if v.severity == Severity.HIGH)

        summary = SecurityScanSummary(
            scan_result=scan_result,
            pattern_findings=pattern_findings,
            passed=(critical == 0 and high == 0),
            blocking=(critical > 0),
            duration_seconds=duration,
        )
        return summary

    # ── Pattern scanner ────────────────────────────────────────────────────

    def _run_pattern_scan(self) -> list[Vulnerability]:
        """Scan source files for web vulnerability patterns."""
        findings: list[Vulnerability] = []

        for source_file in self._iter_source_files():
            rel_path = str(source_file.relative_to(self.project_dir)).replace("\\", "/")
            ext = source_file.suffix.lower()

            try:
                lines = source_file.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
            except OSError:
                continue

            for rule in _WEB_VULN_PATTERNS:
                if ext not in rule.file_extensions:
                    continue
                for lineno, line in enumerate(lines, start=1):
                    # Skip obvious comment lines
                    stripped = line.lstrip()
                    if stripped.startswith(("#", "//", "*", "/*")):
                        continue
                    if re.search(rule.pattern, line, re.IGNORECASE):
                        findings.append(
                            Vulnerability(
                                id=rule.id,
                                severity=rule.severity,
                                source=VulnerabilitySource.CUSTOM,
                                title=rule.title,
                                description=rule.description,
                                file=rel_path,
                                line=lineno,
                                cwe=rule.cwe,
                                remediation=rule.remediation,
                            )
                        )

        return findings

    _SKIP_DIRS = {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        "out",
        ".next",
        "coverage",
        ".workpilot",
    }
    _SCAN_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".env",
        ".yaml",
        ".yml",
        ".json",
    }

    def _iter_source_files(self):
        for path in self.project_dir.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self._SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in self._SCAN_EXTENSIONS:
                yield path


# =============================================================================
# INTEGRATION HELPER
# =============================================================================


async def run_qa_security_scan(
    project_dir: Path,
    spec_dir: Path,
) -> tuple[bool, str, list[dict]]:
    """
    Run a security scan and append the findings to the QA report.

    Args:
        project_dir: Project root
        spec_dir: Spec directory (for writing the report)

    Returns:
        (passed, markdown_section, qa_issues)
        - passed: True if no critical/high issues
        - markdown_section: Markdown to append to qa_report.md
        - qa_issues: List of issue dicts for implementation_plan.json
    """
    scanner = QASecurityScanner(project_dir)
    summary = scanner.scan()

    # Append to qa_report.md
    qa_report = spec_dir / "qa_report.md"
    security_section = summary.to_markdown()
    try:
        existing = qa_report.read_text(encoding="utf-8") if qa_report.exists() else ""
        # Replace existing security section if present, otherwise append
        if "## 🔐 Security Scan Results" in existing:
            before, _, _ = existing.partition("## 🔐 Security Scan Results")
            updated = before + security_section
        else:
            updated = existing + security_section
        qa_report.write_text(updated, encoding="utf-8")
    except OSError:
        pass

    return summary.passed, security_section, summary.to_qa_issues()
