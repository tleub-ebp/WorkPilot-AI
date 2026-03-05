#!/usr/bin/env python3
"""
Security Orchestrator
=====================

Main orchestrator for Feature 8: Security-First Features.

This module coordinates:
1. Automatic vulnerability scanning on every commit
2. Secret detection
3. Compliance analysis (GDPR, SOC2, HIPAA, PCI-DSS)
4. Security report generation
5. Integration with external tools (Snyk, Dependabot, etc.)
6. GitHub/GitLab security integration

Usage:
    from security.security_orchestrator import SecurityOrchestrator

    orchestrator = SecurityOrchestrator(project_path)
    result = orchestrator.run_full_scan()

    if result.should_block:
        print("❌ Security scan failed - blocking deployment")
    else:
        print("✅ Security scan passed")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .compliance_analyzer import ComplianceAnalyzer, ComplianceFramework
from .security_report_generator import SecurityReportGenerator
from .vulnerability_scanner import VulnerabilityScanner


@dataclass
class SecurityScanConfig:
    """Configuration for security scans."""

    # Vulnerability scanning
    scan_secrets: bool = True
    scan_sast: bool = True
    scan_dependencies: bool = True
    scan_containers: bool = False

    # Compliance frameworks to check
    compliance_frameworks: list[ComplianceFramework] = field(
        default_factory=lambda: [ComplianceFramework.GDPR, ComplianceFramework.SOC2]
    )

    # Blocking policy
    block_on_critical: bool = True
    block_on_secrets: bool = True
    block_on_compliance_critical: bool = False

    # Report generation
    generate_json: bool = True
    generate_markdown: bool = True
    generate_html: bool = True
    generate_sarif: bool = True  # For GitHub Security tab

    # Output paths
    output_dir: Path | None = None


@dataclass
class SecurityScanResult:
    """Complete security scan result."""

    vulnerability_scan: dict[str, Any]
    compliance_report: dict[str, Any] | None = None
    reports_generated: dict[str, Path] = field(default_factory=dict)
    scan_timestamp: datetime = field(default_factory=datetime.now)

    @property
    def should_block(self) -> bool:
        """Whether this scan should block deployment."""
        # Check vulnerabilities
        if self.vulnerability_scan.get("should_block", False):
            return True

        # Check compliance
        if self.compliance_report:
            if not self.compliance_report.get("summary", {}).get("is_compliant", True):
                return True

        return False

    @property
    def summary(self) -> dict[str, Any]:
        """Get summary of scan results."""
        vuln_summary = self.vulnerability_scan.get("summary", {})
        comp_summary = (
            self.compliance_report.get("summary", {})
            if self.compliance_report
            else {}
        )

        return {
            "vulnerabilities": {
                "critical": vuln_summary.get("critical", 0),
                "high": vuln_summary.get("high", 0),
                "medium": vuln_summary.get("medium", 0),
                "low": vuln_summary.get("low", 0),
                "total": vuln_summary.get("total", 0),
            },
            "compliance": {
                "critical": comp_summary.get("critical", 0),
                "high": comp_summary.get("high", 0),
                "total": comp_summary.get("total", 0),
                "is_compliant": comp_summary.get("is_compliant", True),
            },
            "should_block": self.should_block,
            "scan_timestamp": self.scan_timestamp.isoformat(),
        }


class SecurityOrchestrator:
    """
    Main orchestrator for security-first features.
    
    This class:
    1. Runs comprehensive security scans
    2. Generates multiple report formats
    3. Integrates with CI/CD pipelines
    4. Provides hooks for pre-commit and pre-push
    5. Supports GitHub/GitLab security tabs
    """

    def __init__(
        self,
        project_path: Path | str,
        config: SecurityScanConfig | None = None,
    ):
        """
        Initialize security orchestrator.

        Args:
            project_path: Path to the project
            config: Scan configuration (uses defaults if None)
        """
        self.project_path = Path(project_path)
        self.config = config or SecurityScanConfig()

        # Initialize components
        self.vulnerability_scanner = VulnerabilityScanner(self.project_path)
        self.compliance_analyzer = ComplianceAnalyzer(self.project_path)
        self.report_generator = SecurityReportGenerator()

        # Set output directory
        if self.config.output_dir is None:
            self.config.output_dir = self.project_path / ".security-reports"
        self.config.output_dir.mkdir(exist_ok=True)

    def run_full_scan(self) -> SecurityScanResult:
        """
        Run complete security scan.

        Returns:
            Complete scan results with reports
        """
        print("🔒 Running security scan...")
        print()

        # Run vulnerability scan
        print("  📡 Scanning for vulnerabilities...")
        vuln_result = self.vulnerability_scanner.scan_all(
            include_secrets=self.config.scan_secrets,
            include_sast=self.config.scan_sast,
            include_dependencies=self.config.scan_dependencies,
            include_containers=self.config.scan_containers,
        )

        # Run compliance analysis
        compliance_result = None
        if self.config.compliance_frameworks:
            print("  📋 Analyzing compliance...")
            compliance_result = self.compliance_analyzer.analyze(
                frameworks=self.config.compliance_frameworks
            )

        # Convert to dicts
        vuln_dict = vuln_result.to_dict()
        comp_dict = compliance_result.to_dict() if compliance_result else None

        # Generate reports
        print("  📄 Generating reports...")
        reports = self._generate_reports(vuln_dict, comp_dict)

        # Create result
        result = SecurityScanResult(
            vulnerability_scan=vuln_dict,
            compliance_report=comp_dict,
            reports_generated=reports,
        )

        # Print summary
        print()
        self.report_generator.print_console_summary(vuln_dict, comp_dict)
        print()

        # Print report locations
        if reports:
            print("📁 Reports saved to:")
            for format_type, path in reports.items():
                print(f"  - {format_type.upper()}: {path}")
            print()

        return result

    def run_quick_scan(self) -> SecurityScanResult:
        """
        Run quick security scan (secrets + critical SAST only).

        Returns:
            Quick scan results
        """
        print("🔒 Running quick security scan...")

        # Run only secrets and SAST
        vuln_result = self.vulnerability_scanner.scan_all(
            include_secrets=True,
            include_sast=True,
            include_dependencies=False,
            include_containers=False,
        )

        vuln_dict = vuln_result.to_dict()

        # Generate minimal reports
        reports = {}
        if self.config.generate_json:
            json_path = (
                self.config.output_dir
                / f"security-scan-quick-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )
            self.report_generator.generate_json_report(vuln_dict, None, json_path)
            reports["json"] = json_path

        result = SecurityScanResult(
            vulnerability_scan=vuln_dict, reports_generated=reports
        )

        self.report_generator.print_console_summary(vuln_dict, None)

        return result

    def scan_commit(self, changed_files: list[str]) -> SecurityScanResult:
        """
        Scan specific files (for commit hooks).

        Args:
            changed_files: List of files that changed

        Returns:
            Scan results for changed files
        """
        print(f"🔒 Scanning {len(changed_files)} changed files...")

        # For commit scans, focus on secrets
        # TODO: Implement file-specific scanning in vulnerability_scanner
        vuln_result = self.vulnerability_scanner.scan_all(
            include_secrets=True,
            include_sast=False,  # Too slow for commits
            include_dependencies=False,
            include_containers=False,
        )

        vuln_dict = vuln_result.to_dict()

        # Filter vulnerabilities to only changed files
        vuln_dict["vulnerabilities"] = [
            v
            for v in vuln_dict.get("vulnerabilities", [])
            if v.get("file") in changed_files
        ]

        # Update summary
        vuln_dict["summary"] = {
            "critical": sum(
                1 for v in vuln_dict["vulnerabilities"] if v.get("severity") == "critical"
            ),
            "high": sum(
                1 for v in vuln_dict["vulnerabilities"] if v.get("severity") == "high"
            ),
            "medium": sum(
                1 for v in vuln_dict["vulnerabilities"] if v.get("severity") == "medium"
            ),
            "low": sum(
                1 for v in vuln_dict["vulnerabilities"] if v.get("severity") == "low"
            ),
            "total": len(vuln_dict["vulnerabilities"]),
        }

        result = SecurityScanResult(vulnerability_scan=vuln_dict)

        if result.should_block:
            print("❌ Security issues found in changed files!")
            self.report_generator.print_console_summary(vuln_dict, None)

        return result

    def generate_github_security_report(self) -> Path:
        """
        Generate SARIF report for GitHub Security tab.

        Returns:
            Path to SARIF file
        """
        # Run full scan
        vuln_result = self.vulnerability_scanner.scan_all()
        vuln_dict = vuln_result.to_dict()

        # Generate SARIF
        sarif_path = self.config.output_dir / "security-scan.sarif"
        self.report_generator.generate_sarif_report(vuln_dict, sarif_path)

        return sarif_path

    def check_policy_compliance(self) -> tuple[bool, str]:
        """
        Check if scan results comply with security policy.

        Returns:
            Tuple of (is_compliant, reason)
        """
        result = self.run_full_scan()

        if self.config.block_on_critical:
            critical_count = result.vulnerability_scan.get("summary", {}).get(
                "critical", 0
            )
            if critical_count > 0:
                return False, f"Found {critical_count} critical vulnerabilities"

        if self.config.block_on_secrets:
            secrets_count = len(result.vulnerability_scan.get("secrets", []))
            if secrets_count > 0:
                return False, f"Found {secrets_count} hardcoded secrets"

        if self.config.block_on_compliance_critical and result.compliance_report:
            if not result.compliance_report.get("summary", {}).get(
                "is_compliant", True
            ):
                return False, "Critical compliance violations found"

        return True, "Security policy compliance verified"

    def _generate_reports(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None,
    ) -> dict[str, Path]:
        """Generate all configured report formats."""
        reports = {}
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # JSON report
        if self.config.generate_json:
            json_path = self.config.output_dir / f"security-scan-{timestamp}.json"
            self.report_generator.generate_json_report(
                vulnerability_results, compliance_results, json_path
            )
            reports["json"] = json_path

        # Markdown report
        if self.config.generate_markdown:
            md_path = self.config.output_dir / f"security-scan-{timestamp}.md"
            self.report_generator.generate_markdown_report(
                vulnerability_results, compliance_results, md_path
            )
            reports["markdown"] = md_path

        # HTML report
        if self.config.generate_html:
            html_path = self.config.output_dir / f"security-scan-{timestamp}.html"
            self.report_generator.generate_html_report(
                vulnerability_results, compliance_results, html_path
            )
            reports["html"] = html_path

        # SARIF report (for GitHub)
        if self.config.generate_sarif:
            sarif_path = self.config.output_dir / "security-scan.sarif"
            self.report_generator.generate_sarif_report(
                vulnerability_results, sarif_path
            )
            reports["sarif"] = sarif_path

        return reports


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point for security scanning."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WorkPilot AI Security Scanner - Feature 8: Security-First"
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="Path to project to scan (default: current directory)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick scan (secrets + SAST only)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for reports (default: .security-reports)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "html", "sarif", "all"],
        default="all",
        help="Report format (default: all)",
    )
    parser.add_argument(
        "--compliance",
        choices=["gdpr", "soc2", "hipaa", "pci-dss", "iso27001", "ccpa", "all"],
        nargs="+",
        help="Compliance frameworks to check",
    )
    parser.add_argument(
        "--no-block",
        action="store_true",
        help="Don't fail on critical issues (report only)",
    )

    args = parser.parse_args()

    # Build config
    config = SecurityScanConfig()
    config.block_on_critical = not args.no_block

    if args.output_dir:
        config.output_dir = args.output_dir

    # Set report formats
    if args.format != "all":
        config.generate_json = args.format == "json"
        config.generate_markdown = args.format == "markdown"
        config.generate_html = args.format == "html"
        config.generate_sarif = args.format == "sarif"

    # Set compliance frameworks
    if args.compliance:
        framework_map = {
            "gdpr": ComplianceFramework.GDPR,
            "soc2": ComplianceFramework.SOC2,
            "hipaa": ComplianceFramework.HIPAA,
            "pci-dss": ComplianceFramework.PCI_DSS,
            "iso27001": ComplianceFramework.ISO_27001,
            "ccpa": ComplianceFramework.CCPA,
        }
        if "all" in args.compliance:
            config.compliance_frameworks = list(ComplianceFramework)
        else:
            config.compliance_frameworks = [
                framework_map[f.lower()] for f in args.compliance
            ]

    # Run scan
    orchestrator = SecurityOrchestrator(args.project_path, config)

    if args.quick:
        result = orchestrator.run_quick_scan()
    else:
        result = orchestrator.run_full_scan()

    # Exit with appropriate code
    if result.should_block and not args.no_block:
        print()
        print("❌ Security scan FAILED - blocking deployment")
        exit(1)
    else:
        print()
        print("✅ Security scan PASSED")
        exit(0)


if __name__ == "__main__":
    main()

