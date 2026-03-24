"""
Self-Healing CLI
================

Command-line interface for the self-healing system.

Usage:
    python -m self_healing check
    python -m self_healing heal
    python -m self_healing monitor
    python -m self_healing report
"""

import argparse
import asyncio
import sys
from pathlib import Path

try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from .config import get_preset_config
from .monitor import SelfHealingMonitor
from .scheduler import HealthCheckScheduler


def print_status(message: str, status: str = "info") -> None:
    """Print status message."""
    emoji = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }
    print(f"{emoji.get(status, 'ℹ️')} {message}")


async def cmd_check(args) -> int:
    """Run health check."""
    print_status("Running health check...", "info")

    config = get_preset_config(args.preset)
    monitor = SelfHealingMonitor(args.project_dir, config)

    report = await monitor.run_health_check()

    # Display results
    print(f"\n🧬 Health Score: {report.overall_score:.1f}/100")
    print(f"Status: {report.status.value.upper()}")
    print(f"Total Issues: {len(report.all_issues)}")
    print(f"Critical Issues: {len(report.get_critical_issues())}")

    if args.verbose:
        print("\n📊 Detailed Scores:")
        print(f"  Quality: {report.quality_score.score:.1f}/100")
        print(f"  Performance: {report.performance_score.score:.1f}/100")
        print(f"  Security: {report.security_score.score:.1f}/100")
        print(f"  Maintainability: {report.maintainability_score.score:.1f}/100")
        print(f"  Testing: {report.testing_score.score:.1f}/100")
        print(f"  Documentation: {report.documentation_score.score:.1f}/100")

        if report.all_issues and args.show_issues:
            print(f"\n🔍 Issues (showing first {args.max_issues}):")
            for issue in report.all_issues[: args.max_issues]:
                print(f"\n  [{issue.severity.upper()}] {issue.title}")
                print(f"    File: {issue.file}")
                if issue.line:
                    print(f"    Line: {issue.line}")
                print(f"    {issue.description}")
                if issue.suggestion:
                    print(f"    💡 Suggestion: {issue.suggestion}")

    return 0 if report.overall_score >= 70 else 1


async def cmd_heal(args) -> int:
    """Run auto-healing."""
    print_status("Running auto-healing...", "info")

    config = get_preset_config(args.preset)
    if args.mode:
        from .config import HealingMode

        config.mode = HealingMode(args.mode)

    monitor = SelfHealingMonitor(args.project_dir, config)

    result = await monitor.auto_heal(max_fixes=args.max_fixes)

    # Display results
    status = result.get("status")

    if status == "healthy":
        print_status(f"Codebase is healthy (score: {result['score']:.1f})", "success")
        return 0

    elif status == "completed":
        print_status(
            f"Auto-healing completed ({result['actions_applied']} actions applied)",
            "success",
        )
        print(f"\nScore: {result['score_before']:.1f} → {result['score_after']:.1f}")
        print(f"Improvement: {result['improvement']:+.1f}")

        if result.get("branch"):
            print(f"Branch: {result['branch']}")
        if result.get("pr_url"):
            print(f"PR: {result['pr_url']}")

        return 0 if result["success"] else 1

    elif status == "passive_mode":
        print_status(f"Passive mode: {result['issues_found']} issues found", "info")
        return 0

    else:
        print_status(f"Status: {status}", "warning")
        return 1


async def cmd_monitor(args) -> int:
    """Start continuous monitoring."""
    print_status("Starting continuous monitoring...", "info")

    config = get_preset_config(args.preset)
    scheduler = HealthCheckScheduler(args.project_dir, config)

    try:
        await scheduler.start_monitoring()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print_status("\nStopping monitoring...", "info")
        await scheduler.stop_monitoring()
        return 0


async def cmd_report(args) -> int:
    """Generate comprehensive report."""
    print_status("Generating health report...", "info")

    config = get_preset_config(args.preset)
    monitor = SelfHealingMonitor(args.project_dir, config)

    report = await monitor.generate_health_report()

    if args.output:
        # Save to file
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print_status(f"Report saved to {output_path}", "success")
    else:
        # Print to console
        print("\n" + report)

    return 0


async def cmd_debt(args) -> int:
    """Show technical debt."""
    from .debt_tracker import TechnicalDebtTracker

    tracker = TechnicalDebtTracker(args.project_dir)

    if args.report:
        report = tracker.generate_report()
        print("\n" + report)
    else:
        stats = tracker.get_statistics()
        print("\n📊 Technical Debt Statistics")
        print(f"Active Items: {stats['total_active']}")
        print(f"Resolved Items: {stats['total_resolved']}")
        print(f"Auto-fixable: {stats['auto_fixable']}")
        print("\nBy Severity:")
        for severity, count in stats["by_severity"].items():
            print(f"  {severity}: {count}")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Self-Healing Codebase System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current directory)",
    )

    parser.add_argument(
        "--preset",
        choices=["conservative", "balanced", "aggressive"],
        default="balanced",
        help="Configuration preset (default: balanced)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Run health check")
    check_parser.add_argument("-v", "--verbose", action="store_true")
    check_parser.add_argument("--show-issues", action="store_true")
    check_parser.add_argument("--max-issues", type=int, default=10)

    # Heal command
    heal_parser = subparsers.add_parser("heal", help="Run auto-healing")
    heal_parser.add_argument(
        "--mode",
        choices=["passive", "active", "aggressive"],
        help="Healing mode",
    )
    heal_parser.add_argument(
        "--max-fixes",
        type=int,
        help="Maximum fixes per run",
    )

    # Monitor command
    subparsers.add_parser("monitor", help="Start continuous monitoring")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: print to console)",
    )

    # Debt command
    debt_parser = subparsers.add_parser("debt", help="Show technical debt")
    debt_parser.add_argument("--report", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run command
    commands = {
        "check": cmd_check,
        "heal": cmd_heal,
        "monitor": cmd_monitor,
        "report": cmd_report,
        "debt": cmd_debt,
    }

    try:
        return asyncio.run(commands[args.command](args))
    except KeyboardInterrupt:
        print_status("\nInterrupted", "warning")
        return 130
    except Exception as e:
        print_status(f"Error: {e}", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
