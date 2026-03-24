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
  incidents   List incidents as JSON
  operations  List healing operations as JSON
  fix         Trigger fix for a specific incident
  dismiss     Dismiss an incident
  retry       Retry a failed incident
  cancel      Cancel an in-progress operation
  config      Save mode configuration
  connect     Connect a production monitoring source
  disconnect  Disconnect a production monitoring source
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AUTO_CLAUDE_DIR = ".workpilot"
SELF_HEALING_DATA_DIR = AUTO_CLAUDE_DIR + "/self-healing"

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class SelfHealingRunner:
    """Runner for the Self-Healing Codebase + Incident Responder."""

    def __init__(self, project_dir: Path, model: str | None = None):
        self.project_dir = project_dir
        self.model = model

    def _load_config(self) -> dict:
        config_path = self.project_dir / SELF_HEALING_DATA_DIR / "config.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _get_orchestrator(self):
        from self_healing.incident_responder import IncidentResponderOrchestrator

        config = self._load_config()
        cicd_cfg = config.get("cicd", {})
        proactive_cfg = config.get("proactive", {})
        return IncidentResponderOrchestrator(
            project_dir=self.project_dir,
            auto_fix=cicd_cfg.get("autoFixEnabled", True),
            auto_create_pr=cicd_cfg.get("autoCreatePR", True),
            risk_threshold=float(proactive_cfg.get("riskThreshold", 40.0)),
        )

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
            print(
                f"✅ Healing complete! Fix applied in branch: {operation.incident.fix_branch}"
            )
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
            print(
                f"❌ Unknown source: {source}. Valid: {[s.value for s in IncidentSource]}"
            )
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
            print(
                f"✅ Incident resolved! Fix in branch: {operation.incident.fix_branch}"
            )
            return True
        else:
            print("❌ Incident requires manual review.")
            return False

    async def run_proactive(
        self, risk_threshold: float = 40.0, top_n: int = 10, json_output: bool = False
    ) -> bool:
        """Run proactive fragility scan."""
        orchestrator = self._get_orchestrator()

        if not json_output:
            print(
                f"🔍 Running proactive fragility scan (threshold={risk_threshold})..."
            )

        reports = await orchestrator.run_proactive_scan()

        if json_output:
            print(json.dumps([r.to_dict() for r in reports], indent=2))
            return True

        if not reports:
            print("✅ No fragile code zones detected. Codebase is healthy!")
            return True

        print(f"\n📊 Found {len(reports)} file(s) above risk threshold:\n")
        print(
            f"{'File':<60} {'Risk':>6} {'Complexity':>11} {'Churn':>6} {'Coverage':>9}"
        )
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

        max_risk = summary.get("max_risk", 0)
        return max_risk <= risk_threshold

    def run_dashboard(self, json_output: bool = False) -> bool:
        """Show self-healing dashboard data."""
        orchestrator = self._get_orchestrator()
        data = orchestrator.get_dashboard_data()

        if json_output:
            try:
                print(json.dumps(data, indent=2, default=str))
                return bool(data)
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
                    "resolved": "✅",
                    "pr_created": "🔗",
                    "analyzing": "🔍",
                    "fixing": "🔧",
                    "pending": "⏳",
                    "failed": "❌",
                    "escalated": "⚠️",
                }.get(inc["status"], "❓")
                print(f"  {status_icon} [{inc['mode']}] {inc['title']}")

        fragility = data["fragilityReports"]
        if fragility:
            print(f"\n🔬 Fragility reports ({len(fragility)} files at risk):")
            for report in fragility[:5]:
                print(f"  ⚡ {report['file_path']} — risk {report['risk_score']}/100")

        return bool(data)

    def run_incidents(self, mode: str | None = None) -> bool:
        """List incidents as JSON, optionally filtered by mode."""
        data_dir = self.project_dir / SELF_HEALING_DATA_DIR
        incidents_file = data_dir / "incidents.json"

        if not incidents_file.exists():
            print(json.dumps([]))
            return True

        try:
            incidents = json.loads(incidents_file.read_text(encoding="utf-8"))
            if mode:
                incidents = [i for i in incidents if i.get("mode") == mode]
            print(json.dumps(incidents, indent=2, default=str))
            return True
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": str(e)}))
            return False

    def run_operations(self) -> bool:
        """List healing operations as JSON."""
        data_dir = self.project_dir / SELF_HEALING_DATA_DIR
        ops_file = data_dir / "operations.json"

        if not ops_file.exists():
            print(json.dumps([]))
            return True

        try:
            operations = json.loads(ops_file.read_text(encoding="utf-8"))
            print(json.dumps(operations, indent=2, default=str))
            return True
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": str(e)}))
            return False

    async def run_fix(self, incident_id: str) -> bool:
        """Trigger a fix for a specific incident, streaming JSON progress lines."""
        orchestrator = self._get_orchestrator()

        incident = orchestrator._find_incident(incident_id)
        if not incident:
            print(
                json.dumps(
                    {"step": "failed", "error": f"Incident {incident_id} not found"}
                )
            )
            return False

        print(
            json.dumps(
                {
                    "step": "analyzing",
                    "incident_id": incident_id,
                    "title": incident.title,
                }
            ),
            flush=True,
        )

        operation = await orchestrator.trigger_fix(incident_id)

        if operation is None:
            print(
                json.dumps(
                    {
                        "step": "failed",
                        "error": "Incident already resolved or no fix needed",
                    }
                )
            )
            return False

        print(
            json.dumps(
                {
                    "step": "complete",
                    "success": operation.success,
                    "operation": operation.to_dict(),
                },
                default=str,
            )
        )
        return operation.success

    def run_dismiss(self, incident_id: str) -> bool:
        """Dismiss an incident (mark as resolved without fixing)."""
        orchestrator = self._get_orchestrator()
        success = orchestrator.dismiss_incident(incident_id)
        print(json.dumps({"success": success, "incident_id": incident_id}))
        return success

    async def run_retry(self, incident_id: str) -> bool:
        """Retry a failed incident, streaming JSON progress lines."""
        orchestrator = self._get_orchestrator()

        incident = orchestrator._find_incident(incident_id)
        if not incident:
            print(
                json.dumps(
                    {"step": "failed", "error": f"Incident {incident_id} not found"}
                )
            )
            return False

        print(
            json.dumps(
                {
                    "step": "retrying",
                    "incident_id": incident_id,
                    "title": incident.title,
                }
            ),
            flush=True,
        )

        operation = await orchestrator.retry_incident(incident_id)

        if operation is None:
            print(
                json.dumps(
                    {"step": "failed", "error": "Retry failed: incident not found"}
                )
            )
            return False

        print(
            json.dumps(
                {
                    "step": "complete",
                    "success": operation.success,
                    "operation": operation.to_dict(),
                },
                default=str,
            )
        )
        return operation.success

    def run_cancel(self, operation_id: str) -> bool:
        """Cancel an in-progress operation by updating the persisted JSON state."""
        data_dir = self.project_dir / SELF_HEALING_DATA_DIR
        ops_file = data_dir / "operations.json"
        inc_file = data_dir / "incidents.json"

        if not ops_file.exists():
            print(json.dumps({"success": False, "error": "No operations found"}))
            return False

        try:
            operations = json.loads(ops_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"success": False, "error": str(e)}))
            return False

        operation = next((o for o in operations if o.get("id") == operation_id), None)
        if not operation:
            print(
                json.dumps(
                    {"success": False, "error": f"Operation {operation_id} not found"}
                )
            )
            return False

        # Mark operation as cancelled
        operation["success"] = False
        operation["completed_at"] = datetime.now(timezone.utc).isoformat()
        ops_file.write_text(
            json.dumps(operations, indent=2, default=str), encoding="utf-8"
        )

        # Update the linked incident to "failed"
        if operation.get("incident") and inc_file.exists():
            try:
                incidents = json.loads(inc_file.read_text(encoding="utf-8"))
                incident_id = operation["incident"].get("id")
                for inc in incidents:
                    if inc.get("id") == incident_id:
                        inc["status"] = "failed"
                        break
                inc_file.write_text(
                    json.dumps(incidents, indent=2, default=str), encoding="utf-8"
                )
            except (json.JSONDecodeError, OSError):
                pass

        print(json.dumps({"success": True, "operation_id": operation_id}))
        return True

    def run_config(self, mode: str, data_json: str) -> bool:
        """Persist configuration for a given mode (cicd, production, proactive)."""
        config_path = self.project_dir / SELF_HEALING_DATA_DIR / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        try:
            new_config = json.loads(data_json)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
            return False

        existing[mode] = {**existing.get(mode, {}), **new_config}
        config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        print(json.dumps({"success": True, "mode": mode, "config": existing[mode]}))
        return True

    async def run_connect(self, source: str, config_json: str) -> bool:
        """Connect a production monitoring source."""
        from self_healing.incident_responder.mcp_connector import MCPSourceConfig
        from self_healing.incident_responder.models import IncidentSource

        try:
            source_enum = IncidentSource(source)
        except ValueError:
            valid = [s.value for s in IncidentSource]
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Unknown source '{source}'. Valid: {valid}",
                    }
                )
            )
            return False

        try:
            cfg_dict = json.loads(config_json)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
            return False

        source_config = MCPSourceConfig(
            source=source_enum,
            server_url=cfg_dict.get("server_url", ""),
            api_key=cfg_dict.get("api_key"),
            project_id=cfg_dict.get("project_id"),
            environment=cfg_dict.get("environment", "production"),
        )

        orchestrator = self._get_orchestrator()
        success = await orchestrator.connect_production_source(source_config)
        print(json.dumps({"success": success, "source": source}))
        return success

    async def run_disconnect(self, source: str) -> bool:
        """Disconnect a production monitoring source."""
        from self_healing.incident_responder.models import IncidentSource

        try:
            source_enum = IncidentSource(source)
        except ValueError:
            valid = [s.value for s in IncidentSource]
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Unknown source '{source}'. Valid: {valid}",
                    }
                )
            )
            return False

        orchestrator = self._get_orchestrator()
        success = await orchestrator.disconnect_production_source(source_enum)
        print(json.dumps({"success": success, "source": source}))
        return success


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
    cicd_parser.add_argument(
        "--test-output", help="Raw test output (reads stdin if omitted)"
    )
    cicd_parser.add_argument("--ci-log-url", help="URL to CI pipeline logs")

    # Production subcommand
    prod_parser = subparsers.add_parser("production", help="Handle production incident")
    prod_parser.add_argument(
        "--source",
        required=True,
        help="Source: sentry|datadog|cloudwatch|new_relic|pagerduty",
    )
    prod_parser.add_argument(
        "--error-type", required=True, help="Error type (e.g., TypeError)"
    )
    prod_parser.add_argument("--error-message", required=True, help="Error message")
    prod_parser.add_argument("--stack-trace", default="", help="Stack trace")
    prod_parser.add_argument(
        "--occurrences", type=int, default=1, help="Occurrence count"
    )

    # Proactive subcommand
    proactive_parser = subparsers.add_parser(
        "proactive", help="Run proactive fragility scan"
    )
    proactive_parser.add_argument(
        "--threshold", type=float, default=40.0, help="Risk threshold (0-100)"
    )
    proactive_parser.add_argument(
        "--top-n", type=int, default=10, help="Show top N files"
    )
    proactive_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON array"
    )

    # Dashboard subcommand
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Show self-healing dashboard"
    )
    dashboard_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output dashboard data as JSON",
    )

    # Incidents subcommand
    incidents_parser = subparsers.add_parser("incidents", help="List incidents as JSON")
    incidents_parser.add_argument(
        "--mode", choices=["cicd", "production", "proactive"], help="Filter by mode"
    )

    # Operations subcommand
    subparsers.add_parser("operations", help="List healing operations as JSON")

    # Fix subcommand
    fix_parser = subparsers.add_parser(
        "fix", help="Trigger fix for a specific incident"
    )
    fix_parser.add_argument("--incident-id", required=True, help="Incident ID to fix")

    # Dismiss subcommand
    dismiss_parser = subparsers.add_parser("dismiss", help="Dismiss an incident")
    dismiss_parser.add_argument(
        "--incident-id", required=True, help="Incident ID to dismiss"
    )

    # Retry subcommand
    retry_parser = subparsers.add_parser("retry", help="Retry a failed incident")
    retry_parser.add_argument(
        "--incident-id", required=True, help="Incident ID to retry"
    )

    # Cancel subcommand
    cancel_parser = subparsers.add_parser(
        "cancel", help="Cancel an in-progress operation"
    )
    cancel_parser.add_argument(
        "--operation-id", required=True, help="Operation ID to cancel"
    )

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Save mode configuration")
    config_parser.add_argument(
        "--mode",
        required=True,
        choices=["cicd", "production", "proactive"],
        help="Config mode",
    )
    config_parser.add_argument("--data", required=True, help="JSON config data")

    # Connect subcommand
    connect_parser = subparsers.add_parser(
        "connect", help="Connect a production monitoring source"
    )
    connect_parser.add_argument(
        "--source", required=True, help="Source name (sentry, datadog, etc.)"
    )
    connect_parser.add_argument(
        "--config", required=True, dest="config_json", help="JSON source configuration"
    )

    # Disconnect subcommand
    disconnect_parser = subparsers.add_parser(
        "disconnect", help="Disconnect a production monitoring source"
    )
    disconnect_parser.add_argument(
        "--source", required=True, help="Source name to disconnect"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    runner = SelfHealingRunner(project_dir=args.project, model=args.model)
    success = _dispatch(runner, args, parser)
    sys.exit(0 if success else 1)


def _dispatch(
    runner: "SelfHealingRunner",
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> bool:
    """Dispatch parsed CLI args to the appropriate runner method."""
    cmd = args.command

    if cmd == "cicd":
        test_output = args.test_output
        if not test_output and not sys.stdin.isatty():
            test_output = sys.stdin.read()
        return asyncio.run(
            runner.run_cicd(
                commit_sha=args.commit,
                branch=args.branch,
                test_output=test_output,
                ci_log_url=args.ci_log_url,
            )
        )
    if cmd == "production":
        return asyncio.run(
            runner.run_production(
                source=args.source,
                error_type=args.error_type,
                error_message=args.error_message,
                stack_trace=args.stack_trace,
                occurrence_count=args.occurrences,
            )
        )
    if cmd == "proactive":
        return asyncio.run(
            runner.run_proactive(
                risk_threshold=args.threshold,
                top_n=args.top_n,
                json_output=args.json_output,
            )
        )
    if cmd == "dashboard":
        return runner.run_dashboard(json_output=args.json_output)
    if cmd == "incidents":
        return runner.run_incidents(mode=getattr(args, "mode", None))
    if cmd == "operations":
        return runner.run_operations()
    if cmd == "fix":
        return asyncio.run(runner.run_fix(incident_id=args.incident_id))
    if cmd == "dismiss":
        return runner.run_dismiss(incident_id=args.incident_id)
    if cmd == "retry":
        return asyncio.run(runner.run_retry(incident_id=args.incident_id))
    if cmd == "cancel":
        return runner.run_cancel(operation_id=args.operation_id)
    if cmd == "config":
        return runner.run_config(mode=args.mode, data_json=args.data)
    if cmd == "connect":
        return asyncio.run(
            runner.run_connect(source=args.source, config_json=args.config_json)
        )
    if cmd == "disconnect":
        return asyncio.run(runner.run_disconnect(source=args.source))

    parser.print_help()
    return False


if __name__ == "__main__":
    main()
