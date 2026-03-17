#!/usr/bin/env python3
"""
Self-Healing Runner
====================

CLI entry point for the Self-Healing Codebase + Incident Responder system.

Subcommands:
  cicd        Trigger CI/CD healing for a test failure
  production  Handle a production incident
  proactive   Run proactive fragility scan
  dashboard   Show self-healing dashboard data
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class SelfHealingRunner:
    """Runner for the Self-Healing Codebase + Incident Responder."""

    def __init__(self, project_dir: Path, model: str | None = None):
        self.project_dir = project_dir
        self.model = model

    def _get_orchestrator(self):
        from self_healing.incident_responder import IncidentResponderOrchestrator
        return IncidentResponderOrchestrator(project_dir=self.project_dir)

    async def run_cicd(
        self,
        commit_sha: str,
        branch: str,
        test_output: str | None = None,
        ci_log_url: str | None = None,
    ) -> bool:
        """Run CI/CD healing for a test failure."""
        orchestrator = self._get_orchestrator()

        # If no test output provided, run tests to get it
        if not test_output:
            print("🧪 Running test suite to detect failures...")
            passed, output, failing = await orchestrator.cicd.run_tests()
            if passed:
                print("✅ All tests passing. No healing needed.")
                return True  # This is appropriate - no healing needed when tests pass
            test_output = output
            print(f"❌ {len(failing)} test(s) failing. Starting healing pipeline...")

        operation = await orchestrator.handle_cicd_failure(
            commit_sha=commit_sha,
            branch=branch,
            test_output=test_output,
            ci_log_url=ci_log_url,
        )

        if operation.success:
            print(f"✅ Healing complete! Fix applied in branch: {operation.incident.fix_branch}")
            if operation.incident.fix_pr_url:
                print(f"   PR: {operation.incident.fix_pr_url}")
            return True
        else:
            print("❌ Healing failed. Incident escalated for manual review.")
            return False

    async def run_production(
        self,
        source: str,
        error_type: str,
        error_message: str,
        stack_trace: str = "",
        occurrence_count: int = 1,
    ) -> bool:
        """Handle a production incident."""
        from self_healing.incident_responder import IncidentSource

        orchestrator = self._get_orchestrator()

        try:
            incident_source = IncidentSource(source)
        except ValueError:
            print(f"❌ Unknown source: {source}. Valid: {[s.value for s in IncidentSource]}")
            return False

        operation = await orchestrator.handle_production_incident(
            source=incident_source,
            error_data={
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "occurrence_count": occurrence_count,
            },
        )

        if operation.success:
            print(f"✅ Incident resolved! Fix in branch: {operation.incident.fix_branch}")
            return True
        else:
            print("❌ Incident requires manual review.")
            return False

    async def run_proactive(self, risk_threshold: float = 40.0, top_n: int = 10) -> bool:
        """Run proactive fragility scan."""
        orchestrator = self._get_orchestrator()

        print(f"🔍 Running proactive fragility scan (threshold={risk_threshold})...")
        reports = await orchestrator.run_proactive_scan()

        if not reports:
            print("✅ No fragile code zones detected. Codebase is healthy!")
            return True

        print(f"\n📊 Found {len(reports)} file(s) above risk threshold:\n")
        print(f"{'File':<60} {'Risk':>6} {'Complexity':>11} {'Churn':>6} {'Coverage':>9}")
        print("-" * 95)

        for report in reports[:top_n]:
            path = report.file_path
            if len(path) > 58:
                path = "..." + path[-55:]
            print(
                f"{path:<60} {report.risk_score:>5.1f}% "
                f"{report.cyclomatic_complexity:>10.0f} "
                f"{report.git_churn_count:>5} "
                f"{report.test_coverage_percent:>8.1f}%"
            )

        summary = orchestrator.proactive.get_summary()
        print(f"\n📈 Average risk score: {summary['avg_risk']}")
        print(f"   Maximum risk score: {summary['max_risk']}")

        # Return False if high-risk files were found that need attention
        max_risk = summary.get('max_risk', 0)
        return max_risk <= risk_threshold

    def run_dashboard(self, json_output: bool = False) -> bool:
        """Show self-healing dashboard data."""
        orchestrator = self._get_orchestrator()
        data = orchestrator.get_dashboard_data()

        if json_output:
            try:
                print(json.dumps(data, indent=2))
                return bool(data)  # Return based on data availability
            except (TypeError, ValueError) as e:
                print(f"Error serializing dashboard data: {e}")
                return False

        stats = data["stats"]
        print("🩺 Self-Healing Dashboard")
        print("=" * 50)
        print(f"  Total incidents:    {stats['totalIncidents']}")
        print(f"  Resolved:           {stats['resolvedIncidents']}")
        print(f"  Active:             {stats['activeIncidents']}")
        print(f"  Avg resolution:     {stats['avgResolutionTime']}s")
        print(f"  Auto-fix rate:      {stats['autoFixRate']}%")

        incidents = data["incidents"]
        if incidents:
            print(f"\n📋 Recent incidents ({len(incidents)}):")
            for inc in incidents[:10]:
                status_icon = {
                    "resolved": "✅", "pr_created": "🔗",
                    "analyzing": "🔍", "fixing": "🔧",
                    "pending": "⏳", "failed": "❌",
                    "escalated": "⚠️",
                }.get(inc["status"], "❓")
                print(f"  {status_icon} [{inc['mode']}] {inc['title']}")

        fragility = data["fragilityReports"]
        if fragility:
            print(f"\n🔬 Fragility reports ({len(fragility)} files at risk):")
            for report in fragility[:5]:
                print(f"  ⚡ {report['file_path']} — risk {report['risk_score']}/100")

        return bool(data)  # Return False if no data available


def main():
    parser = argparse.ArgumentParser(
        description="Self-Healing Codebase + Incident Responder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use for agent operations",
    )

    subparsers = parser.add_subparsers(dest="command", help="Self-healing commands")

    # CI/CD subcommand
    cicd_parser = subparsers.add_parser("cicd", help="Handle CI/CD test failure")
    cicd_parser.add_argument("--commit", required=True, help="Failing commit SHA")
    cicd_parser.add_argument("--branch", default="main", help="Branch name")
    cicd_parser.add_argument("--test-output", help="Raw test output (reads stdin if omitted)")
    cicd_parser.add_argument("--ci-log-url", help="URL to CI pipeline logs")

    # Production subcommand
    prod_parser = subparsers.add_parser("production", help="Handle production incident")
    prod_parser.add_argument("--source", required=True, help="Source: sentry|datadog|cloudwatch|new_relic|pagerduty")
    prod_parser.add_argument("--error-type", required=True, help="Error type (e.g., TypeError)")
    prod_parser.add_argument("--error-message", required=True, help="Error message")
    prod_parser.add_argument("--stack-trace", default="", help="Stack trace")
    prod_parser.add_argument("--occurrences", type=int, default=1, help="Occurrence count")

    # Proactive subcommand
    proactive_parser = subparsers.add_parser("proactive", help="Run proactive fragility scan")
    proactive_parser.add_argument("--threshold", type=float, default=40.0, help="Risk threshold (0-100)")
    proactive_parser.add_argument("--top-n", type=int, default=10, help="Show top N files")

    # Dashboard subcommand
    dashboard_parser = subparsers.add_parser("dashboard", help="Show self-healing dashboard")
    dashboard_parser.add_argument("--json", action="store_true", help="Output dashboard data as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    runner = SelfHealingRunner(project_dir=args.project, model=args.model)

    if args.command == "cicd":
        test_output = args.test_output
        if not test_output and not sys.stdin.isatty():
            test_output = sys.stdin.read()
        success = asyncio.run(runner.run_cicd(
            commit_sha=args.commit,
            branch=args.branch,
            test_output=test_output,
            ci_log_url=args.ci_log_url,
        ))
    elif args.command == "production":
        success = asyncio.run(runner.run_production(
            source=args.source,
            error_type=args.error_type,
            error_message=args.error_message,
            stack_trace=args.stack_trace,
            occurrence_count=args.occurrences,
        ))
    elif args.command == "proactive":
        success = asyncio.run(runner.run_proactive(
            risk_threshold=args.threshold,
            top_n=args.top_n,
        ))
    elif args.command == "dashboard":
        success = runner.run_dashboard(json_output=args.json)
    else:
        parser.print_help()
        return

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
