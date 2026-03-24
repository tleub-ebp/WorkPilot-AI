#!/usr/bin/env python3
"""
Security Report Generator
=========================

Generates comprehensive security reports from vulnerability scans and compliance checks.
Supports multiple output formats:
- JSON (for API integration)
- HTML (for human-readable reports)
- Markdown (for documentation)
- PDF (for executive summaries)
- SARIF (for GitHub Security tab integration)

Part of Feature 8: Security-First Features.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class SecurityReportGenerator:
    """
    Generates security reports in various formats.

    This generator combines:
    - Vulnerability scan results
    - Compliance analysis results
    - Secret detection findings
    - Executive summaries
    - Remediation recommendations
    """

    def __init__(self):
        """Initialize report generator."""
        self.console = Console() if HAS_RICH else None

    def generate_json_report(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None = None,
        output_path: Path | None = None,
    ) -> str:
        """
        Generate JSON report.

        Args:
            vulnerability_results: Results from vulnerability scanner
            compliance_results: Results from compliance analyzer (optional)
            output_path: Where to save the report (optional)

        Returns:
            JSON string
        """
        report = {
            "report_type": "security_scan",
            "generated_at": datetime.now().isoformat(),
            "vulnerability_scan": vulnerability_results,
        }

        if compliance_results:
            report["compliance_analysis"] = compliance_results

        # Calculate overall risk score
        report["risk_assessment"] = self._calculate_risk_score(
            vulnerability_results, compliance_results
        )

        json_str = json.dumps(report, indent=2)

        if output_path:
            output_path.write_text(json_str, encoding="utf-8")

        return json_str

    def generate_markdown_report(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None = None,
        output_path: Path | None = None,
    ) -> str:
        """
        Generate Markdown report.

        Args:
            vulnerability_results: Results from vulnerability scanner
            compliance_results: Results from compliance analyzer (optional)
            output_path: Where to save the report (optional)

        Returns:
            Markdown string
        """
        md_lines = []

        # Header
        md_lines.append("# 🔒 Security Scan Report")
        md_lines.append("")
        md_lines.append(
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        md_lines.append(
            f"**Project:** {vulnerability_results.get('project_path', 'Unknown')}"
        )
        md_lines.append("")

        # Executive Summary
        md_lines.append("## 📊 Executive Summary")
        md_lines.append("")

        summary = vulnerability_results.get("summary", {})
        risk = self._calculate_risk_score(vulnerability_results, compliance_results)

        md_lines.append(
            f"**Overall Risk Score:** {risk['score']}/100 - {risk['level']}"
        )
        md_lines.append("")
        md_lines.append("### Vulnerability Summary")
        md_lines.append("")
        md_lines.append(f"- 🔴 **Critical:** {summary.get('critical', 0)}")
        md_lines.append(f"- 🟠 **High:** {summary.get('high', 0)}")
        md_lines.append(f"- 🟡 **Medium:** {summary.get('medium', 0)}")
        md_lines.append(f"- 🟢 **Low:** {summary.get('low', 0)}")
        md_lines.append(f"- **Total:** {summary.get('total', 0)}")
        md_lines.append("")

        # Scan Details
        md_lines.append("### Scan Details")
        md_lines.append("")
        md_lines.append(
            f"- **Scans Run:** {', '.join(vulnerability_results.get('scans_run', []))}"
        )
        md_lines.append(
            f"- **Files Scanned:** {vulnerability_results.get('total_files_scanned', 0)}"
        )
        md_lines.append(
            f"- **Duration:** {vulnerability_results.get('scan_duration_seconds', 0):.2f}s"
        )
        md_lines.append("")

        # Blocking Status
        if vulnerability_results.get("should_block", False):
            md_lines.append(
                "⛔ **STATUS: BLOCKING** - Critical vulnerabilities must be fixed before deployment"
            )
        elif vulnerability_results.get("should_warn", False):
            md_lines.append(
                "⚠️ **STATUS: WARNING** - High/Medium vulnerabilities should be reviewed"
            )
        else:
            md_lines.append("✅ **STATUS: PASSED** - No critical issues detected")
        md_lines.append("")

        # Critical Vulnerabilities
        critical_vulns = [
            v
            for v in vulnerability_results.get("vulnerabilities", [])
            if v.get("severity") == "critical"
        ]

        if critical_vulns:
            md_lines.append("## 🚨 Critical Vulnerabilities")
            md_lines.append("")
            for i, vuln in enumerate(critical_vulns, 1):
                md_lines.append(f"### {i}. {vuln.get('title', 'Unknown')}")
                md_lines.append("")
                md_lines.append(f"**ID:** {vuln.get('id', 'N/A')}")
                md_lines.append(f"**Source:** {vuln.get('source', 'N/A')}")
                if vuln.get("file"):
                    location = vuln["file"]
                    if vuln.get("line"):
                        location += f":{vuln['line']}"
                    md_lines.append(f"**Location:** `{location}`")
                md_lines.append("")
                md_lines.append(f"**Description:** {vuln.get('description', 'N/A')}")
                md_lines.append("")
                if vuln.get("remediation"):
                    md_lines.append(f"**Remediation:** {vuln['remediation']}")
                    md_lines.append("")
                if vuln.get("references"):
                    md_lines.append("**References:**")
                    for ref in vuln["references"]:
                        if ref:
                            md_lines.append(f"- {ref}")
                    md_lines.append("")

        # High Severity Vulnerabilities
        high_vulns = [
            v
            for v in vulnerability_results.get("vulnerabilities", [])
            if v.get("severity") == "high"
        ]

        if high_vulns:
            md_lines.append("## ⚠️ High Severity Vulnerabilities")
            md_lines.append("")
            for i, vuln in enumerate(high_vulns, 1):
                md_lines.append(f"### {i}. {vuln.get('title', 'Unknown')}")
                md_lines.append("")
                md_lines.append(f"**ID:** {vuln.get('id', 'N/A')}")
                md_lines.append(f"**Source:** {vuln.get('source', 'N/A')}")
                if vuln.get("file"):
                    location = vuln["file"]
                    if vuln.get("line"):
                        location += f":{vuln['line']}"
                    md_lines.append(f"**Location:** `{location}`")
                md_lines.append("")
                if vuln.get("remediation"):
                    md_lines.append(f"**Remediation:** {vuln['remediation']}")
                    md_lines.append("")

        # Compliance Results
        if compliance_results:
            md_lines.append("## 📋 Compliance Analysis")
            md_lines.append("")

            comp_summary = compliance_results.get("summary", {})
            md_lines.append(
                f"**Frameworks Checked:** {', '.join(compliance_results.get('frameworks', []))}"
            )
            md_lines.append("")
            md_lines.append(
                f"- 🔴 **Critical Violations:** {comp_summary.get('critical', 0)}"
            )
            md_lines.append(f"- 🟠 **High Violations:** {comp_summary.get('high', 0)}")
            md_lines.append(f"- **Total Violations:** {comp_summary.get('total', 0)}")
            md_lines.append("")

            if comp_summary.get("is_compliant"):
                md_lines.append("✅ **Compliance Status: COMPLIANT**")
            else:
                md_lines.append("❌ **Compliance Status: NON-COMPLIANT**")
            md_lines.append("")

            # Critical compliance violations
            critical_violations = [
                v
                for v in compliance_results.get("violations", [])
                if v.get("severity") == "critical"
            ]

            if critical_violations:
                md_lines.append("### Critical Compliance Violations")
                md_lines.append("")
                for i, violation in enumerate(critical_violations, 1):
                    md_lines.append(
                        f"{i}. **{violation.get('framework', 'N/A')} - {violation.get('rule_id', 'N/A')}:** {violation.get('title', 'Unknown')}"
                    )
                    md_lines.append(f"   - Location: `{violation.get('file', 'N/A')}`")
                    md_lines.append(
                        f"   - Remediation: {violation.get('remediation', 'See documentation')}"
                    )
                    md_lines.append("")

        # Recommendations
        md_lines.append("## 💡 Recommendations")
        md_lines.append("")
        recommendations = self._generate_recommendations(
            vulnerability_results, compliance_results
        )
        for i, rec in enumerate(recommendations, 1):
            md_lines.append(f"{i}. {rec}")
        md_lines.append("")

        # Next Steps
        md_lines.append("## 🎯 Next Steps")
        md_lines.append("")
        md_lines.append(
            "1. **Address Critical Issues:** Fix all critical vulnerabilities immediately"
        )
        md_lines.append(
            "2. **Review High Severity:** Assess and prioritize high severity issues"
        )
        md_lines.append(
            "3. **Update Dependencies:** Check for available security patches"
        )
        md_lines.append("4. **Run Tests:** Ensure fixes don't break functionality")
        md_lines.append("5. **Re-scan:** Run security scan again after fixes")
        md_lines.append("")

        # Footer
        md_lines.append("---")
        md_lines.append("")
        md_lines.append("*Report generated by WorkPilot AI Security Scanner*")
        md_lines.append("")

        markdown = "\n".join(md_lines)

        if output_path:
            output_path.write_text(markdown, encoding="utf-8")

        return markdown

    def generate_html_report(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None = None,
        output_path: Path | None = None,
    ) -> str:
        """
        Generate HTML report.

        Args:
            vulnerability_results: Results from vulnerability scanner
            compliance_results: Results from compliance analyzer (optional)
            output_path: Where to save the report (optional)

        Returns:
            HTML string
        """
        risk = self._calculate_risk_score(vulnerability_results, compliance_results)
        summary = vulnerability_results.get("summary", {})

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Scan Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            margin-top: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .metric {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric.critical {{ color: #dc3545; }}
        .metric.high {{ color: #fd7e14; }}
        .metric.medium {{ color: #ffc107; }}
        .metric.low {{ color: #28a745; }}
        .risk-score {{
            text-align: center;
            font-size: 4em;
            font-weight: bold;
        }}
        .risk-high {{ color: #dc3545; }}
        .risk-medium {{ color: #ffc107; }}
        .risk-low {{ color: #28a745; }}
        .status {{
            padding: 10px 20px;
            border-radius: 5px;
            display: inline-block;
            font-weight: bold;
            margin: 20px 0;
        }}
        .status.blocking {{
            background-color: #dc3545;
            color: white;
        }}
        .status.warning {{
            background-color: #ffc107;
            color: #000;
        }}
        .status.passed {{
            background-color: #28a745;
            color: white;
        }}
        .vulnerability {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid;
        }}
        .vulnerability.critical {{ border-left-color: #dc3545; }}
        .vulnerability.high {{ border-left-color: #fd7e14; }}
        .vulnerability h4 {{
            margin-top: 0;
            color: #333;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 10px;
        }}
        .badge.critical {{ background-color: #dc3545; color: white; }}
        .badge.high {{ background-color: #fd7e14; color: white; }}
        .badge.medium {{ background-color: #ffc107; color: #000; }}
        .badge.low {{ background-color: #28a745; color: white; }}
        .code-location {{
            background-color: #f8f9fa;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
            margin: 10px 0;
        }}
        .recommendations {{
            background: #e7f3ff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #0066cc;
        }}
        .recommendations ul {{
            margin: 10px 0;
        }}
        footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 Security Scan Report</h1>
        <div class="subtitle">
            Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
            Project: {vulnerability_results.get("project_path", "Unknown")}
        </div>
    </div>

    <div class="summary">
        <div class="card">
            <h3>Risk Score</h3>
            <div class="risk-score risk-{risk["level"].lower()}">{risk["score"]}/100</div>
            <div>{risk["level"]}</div>
        </div>
        <div class="card">
            <h3>Critical</h3>
            <div class="metric critical">{summary.get("critical", 0)}</div>
        </div>
        <div class="card">
            <h3>High</h3>
            <div class="metric high">{summary.get("high", 0)}</div>
        </div>
        <div class="card">
            <h3>Medium</h3>
            <div class="metric medium">{summary.get("medium", 0)}</div>
        </div>
        <div class="card">
            <h3>Low</h3>
            <div class="metric low">{summary.get("low", 0)}</div>
        </div>
    </div>
"""

        # Status
        if vulnerability_results.get("should_block"):
            html += '<div class="status blocking">⛔ BLOCKING - Critical issues must be fixed</div>'
        elif vulnerability_results.get("should_warn"):
            html += '<div class="status warning">⚠️ WARNING - Review required</div>'
        else:
            html += '<div class="status passed">✅ PASSED - No critical issues</div>'

        # Critical Vulnerabilities
        critical_vulns = [
            v
            for v in vulnerability_results.get("vulnerabilities", [])
            if v.get("severity") == "critical"
        ]

        if critical_vulns:
            html += "<h2>🚨 Critical Vulnerabilities</h2>"
            for vuln in critical_vulns:
                html += f"""
                <div class="vulnerability critical">
                    <h4>
                        <span class="badge critical">CRITICAL</span>
                        {vuln.get("title", "Unknown")}
                    </h4>
                    <p><strong>ID:</strong> {vuln.get("id", "N/A")}</p>
                    <p><strong>Source:</strong> {vuln.get("source", "N/A")}</p>
                """
                if vuln.get("file"):
                    location = vuln["file"]
                    if vuln.get("line"):
                        location += f":{vuln['line']}"
                    html += f'<div class="code-location">📍 {location}</div>'

                html += f"<p>{vuln.get('description', 'N/A')}</p>"

                if vuln.get("remediation"):
                    html += (
                        f"<p><strong>Remediation:</strong> {vuln['remediation']}</p>"
                    )

                html += "</div>"

        # Recommendations
        recommendations = self._generate_recommendations(
            vulnerability_results, compliance_results
        )
        html += """
    <div class="recommendations">
        <h2>💡 Recommendations</h2>
        <ul>
"""
        for rec in recommendations:
            html += f"            <li>{rec}</li>\n"

        html += """
        </ul>
    </div>

    <footer>
        <p>Report generated by WorkPilot AI Security Scanner</p>
    </footer>
</body>
</html>
"""

        if output_path:
            output_path.write_text(html, encoding="utf-8")

        return html

    def generate_sarif_report(
        self,
        vulnerability_results: dict[str, Any],
        output_path: Path | None = None,
    ) -> str:
        """
        Generate SARIF report for GitHub Security integration.

        Args:
            vulnerability_results: Results from vulnerability scanner
            output_path: Where to save the report (optional)

        Returns:
            SARIF JSON string
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "WorkPilot AI Security Scanner",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/auto-claude/security",
                        }
                    },
                    "results": [],
                }
            ],
        }

        # Convert vulnerabilities to SARIF format
        for vuln in vulnerability_results.get("vulnerabilities", []):
            level_map = {
                "critical": "error",
                "high": "error",
                "medium": "warning",
                "low": "note",
                "info": "note",
            }

            result = {
                "ruleId": vuln.get("id", "unknown"),
                "level": level_map.get(vuln.get("severity", "medium"), "warning"),
                "message": {
                    "text": vuln.get("description", vuln.get("title", "Security issue"))
                },
            }

            if vuln.get("file"):
                result["locations"] = [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": vuln["file"]},
                            "region": {
                                "startLine": vuln.get("line", 1),
                            },
                        }
                    }
                ]

            sarif["runs"][0]["results"].append(result)

        sarif_str = json.dumps(sarif, indent=2)

        if output_path:
            output_path.write_text(sarif_str, encoding="utf-8")

        return sarif_str

    def print_console_summary(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None = None,
    ) -> None:
        """
        Print a beautiful console summary using Rich.

        Args:
            vulnerability_results: Results from vulnerability scanner
            compliance_results: Results from compliance analyzer (optional)
        """
        if not HAS_RICH or not self.console:
            # Fallback to plain text
            self._print_plain_summary(vulnerability_results, compliance_results)
            return

        # Header
        self.console.print(
            Panel.fit(
                "[bold cyan]🔒 Security Scan Report[/bold cyan]",
                subtitle=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            )
        )
        self.console.print()

        # Summary table
        summary = vulnerability_results.get("summary", {})
        table = Table(title="Vulnerability Summary", show_header=True)
        table.add_column("Severity", style="bold")
        table.add_column("Count", justify="right")

        table.add_row(
            "🔴 Critical", f"[bold red]{summary.get('critical', 0)}[/bold red]"
        )
        table.add_row(
            "🟠 High", f"[bold orange1]{summary.get('high', 0)}[/bold orange1]"
        )
        table.add_row(
            "🟡 Medium", f"[bold yellow]{summary.get('medium', 0)}[/bold yellow]"
        )
        table.add_row("🟢 Low", f"[bold green]{summary.get('low', 0)}[/bold green]")
        table.add_row("[bold]Total[/bold]", f"[bold]{summary.get('total', 0)}[/bold]")

        self.console.print(table)
        self.console.print()

        # Status
        if vulnerability_results.get("should_block"):
            self.console.print(
                Panel(
                    "[bold red]⛔ BLOCKING[/bold red]\nCritical vulnerabilities must be fixed before deployment",
                    style="red",
                )
            )
        elif vulnerability_results.get("should_warn"):
            self.console.print(
                Panel(
                    "[bold yellow]⚠️ WARNING[/bold yellow]\nHigh/Medium vulnerabilities should be reviewed",
                    style="yellow",
                )
            )
        else:
            self.console.print(
                Panel(
                    "[bold green]✅ PASSED[/bold green]\nNo critical issues detected",
                    style="green",
                )
            )

    def _print_plain_summary(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None = None,
    ) -> None:
        """Plain text fallback for console summary."""
        print("\n" + "=" * 60)
        print("🔒 Security Scan Report")
        print("=" * 60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        summary = vulnerability_results.get("summary", {})
        print("Vulnerability Summary:")
        print(f"  🔴 Critical: {summary.get('critical', 0)}")
        print(f"  🟠 High: {summary.get('high', 0)}")
        print(f"  🟡 Medium: {summary.get('medium', 0)}")
        print(f"  🟢 Low: {summary.get('low', 0)}")
        print(f"  Total: {summary.get('total', 0)}")
        print()

        if vulnerability_results.get("should_block"):
            print("⛔ STATUS: BLOCKING - Critical issues must be fixed")
        elif vulnerability_results.get("should_warn"):
            print("⚠️ STATUS: WARNING - Review required")
        else:
            print("✅ STATUS: PASSED - No critical issues")
        print("=" * 60 + "\n")

    def _calculate_risk_score(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Calculate overall risk score."""
        summary = vulnerability_results.get("summary", {})

        # Calculate base score (0-100, lower is better)
        score = 0
        score += summary.get("critical", 0) * 25  # Each critical = 25 points
        score += summary.get("high", 0) * 10  # Each high = 10 points
        score += summary.get("medium", 0) * 3  # Each medium = 3 points
        score += summary.get("low", 0) * 1  # Each low = 1 point

        # Add compliance violations
        if compliance_results:
            comp_summary = compliance_results.get("summary", {})
            score += comp_summary.get("critical", 0) * 20
            score += comp_summary.get("high", 0) * 8

        # Cap at 100
        score = min(score, 100)

        # Determine risk level
        if score >= 50:
            level = "HIGH"
        elif score >= 20:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {"score": score, "level": level}

    def _generate_recommendations(
        self,
        vulnerability_results: dict[str, Any],
        compliance_results: dict[str, Any] | None,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        summary = vulnerability_results.get("summary", {})

        if summary.get("critical", 0) > 0:
            recommendations.append(
                "**URGENT:** Fix all critical vulnerabilities immediately - these pose severe security risks"
            )

        if summary.get("high", 0) > 0:
            recommendations.append(
                "Review and address high severity vulnerabilities - prioritize those with known exploits"
            )

        # Check for specific vulnerability types
        vulns = vulnerability_results.get("vulnerabilities", [])
        has_secrets = any(v.get("source") == "secrets" for v in vulns)
        has_deps = any(v.get("dependency") for v in vulns)

        if has_secrets:
            recommendations.append(
                "Remove all hardcoded secrets and use environment variables or secret management services (e.g., AWS Secrets Manager, HashiCorp Vault)"
            )

        if has_deps:
            recommendations.append(
                "Update vulnerable dependencies to their latest secure versions"
            )

        # Compliance recommendations
        if compliance_results and not compliance_results.get("summary", {}).get(
            "is_compliant", True
        ):
            recommendations.append(
                "Address compliance violations to meet regulatory requirements"
            )

        # General recommendations
        if not recommendations:
            recommendations.append(
                "Continue monitoring for new vulnerabilities with regular security scans"
            )

        recommendations.append(
            "Consider implementing automated security scanning in your CI/CD pipeline"
        )

        return recommendations
