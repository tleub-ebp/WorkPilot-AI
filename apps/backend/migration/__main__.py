"""
CLI for Auto-Migration Engine.
Usage: python -m apps.backend.migration [command] [options]
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from .orchestrator import MigrationOrchestrator
from .reporter import MigrationReporter
from .config import SUPPORTED_MIGRATIONS


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-Migration Engine - Automatic technology stack migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start interactive migration
  python -m apps.backend.migration --interactive
  
  # List supported migrations
  python -m apps.backend.migration list-migrations
  
  # Analyze without executing
  python -m apps.backend.migration analyze --to vue
  
  # Execute migration
  python -m apps.backend.migration migrate --to vue --auto
  
  # Rollback
  python -m apps.backend.migration rollback --migration-id <id> --to-phase backup
  
  # Resume migration
  python -m apps.backend.migration resume --migration-id <id>
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List migrations
    list_cmd = subparsers.add_parser(
        "list-migrations",
        help="List supported migrations"
    )

    # Analyze
    analyze_cmd = subparsers.add_parser(
        "analyze",
        help="Analyze project and assess migration complexity"
    )
    analyze_cmd.add_argument("--to", required=True, help="Target framework")
    analyze_cmd.add_argument("--project-dir", default=".", help="Project directory")
    analyze_cmd.add_argument("--verbose", action="store_true", help="Verbose output")

    # Start migration
    migrate_cmd = subparsers.add_parser(
        "migrate",
        help="Start a new migration"
    )
    migrate_cmd.add_argument("--to", required=True, help="Target framework")
    migrate_cmd.add_argument("--project-dir", default=".", help="Project directory")
    migrate_cmd.add_argument("--dry-run", action="store_true", help="Don't apply changes")
    migrate_cmd.add_argument("--auto", action="store_true", help="Skip confirmations")
    migrate_cmd.add_argument("--interactive", action="store_true", help="Interactive mode")

    # Resume migration
    resume_cmd = subparsers.add_parser(
        "resume",
        help="Resume a paused migration"
    )
    resume_cmd.add_argument("--migration-id", required=True, help="Migration ID")
    resume_cmd.add_argument("--project-dir", default=".", help="Project directory")

    # Rollback
    rollback_cmd = subparsers.add_parser(
        "rollback",
        help="Rollback a migration"
    )
    rollback_cmd.add_argument("--migration-id", required=True, help="Migration ID")
    rollback_cmd.add_argument("--to-phase", default="backup", help="Rollback to phase")
    rollback_cmd.add_argument("--project-dir", default=".", help="Project directory")

    # Status
    status_cmd = subparsers.add_parser(
        "status",
        help="Show migration status"
    )
    status_cmd.add_argument("--migration-id", help="Migration ID")
    status_cmd.add_argument("--project-dir", default=".", help="Project directory")

    # Report
    report_cmd = subparsers.add_parser(
        "report",
        help="Generate migration report"
    )
    report_cmd.add_argument("--migration-id", required=True, help="Migration ID")
    report_cmd.add_argument("--output", "-o", help="Output file path")
    report_cmd.add_argument("--project-dir", default=".", help="Project directory")
    report_cmd.add_argument("--format", choices=["markdown", "html"], default="markdown", help="Report format")

    args = parser.parse_args()

    # Route to command
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "list-migrations":
        return cmd_list_migrations()
    elif args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "migrate":
        return cmd_migrate(args)
    elif args.command == "resume":
        return cmd_resume(args)
    elif args.command == "rollback":
        return cmd_rollback(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "report":
        return cmd_report(args)

    return 1


def cmd_list_migrations() -> int:
    """List supported migrations."""
    print("✨ Supported Migrations:\n")
    for (source, target), config in SUPPORTED_MIGRATIONS.items():
        complexity = config.get("complexity", "unknown").upper()
        effort = config.get("estimated_effort_hours", "?")
        print(f"  {source.upper()} → {target.upper()}")
        print(f"    Complexity: {complexity}")
        print(f"    Estimated: {effort}h")
        print()
    return 0


def cmd_analyze(args) -> int:
    """Analyze project for migration."""
    print(f"🔍 Analyzing project at {args.project_dir}...")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        result = orchestrator.plan_phase()
        
        print("\n✅ Analysis complete!")
        print(f"\nComplexity Assessment:")
        print(f"  Supported: {result['complexity'].get('supported')}")
        print(f"  Affected Files: {result['complexity'].get('affected_files')}")
        print(f"  Risk Level: {result['complexity'].get('risk_level')}")
        print(f"  Estimated Effort: {result['complexity'].get('estimated_effort')}h")
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_migrate(args) -> int:
    """Start a new migration."""
    print(f"🚀 Starting migration to {args.to}...")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        context = orchestrator.start_migration(args.to, "unknown")
        
        print(f"\n✅ Migration initialized!")
        print(f"  Migration ID: {context.migration_id}")
        print(f"  Source: {context.source_stack.framework}")
        print(f"  Target: {context.target_stack.framework}")
        print(f"  Status: {context.state.value}")
        
        if context.plan:
            print(f"  Total Steps: {context.plan.total_steps}")
            print(f"  Risk Level: {context.plan.risk_level.value}")
        
        if not args.auto:
            print("\n⚠️  Review the migration plan before proceeding.")
            print("   Run: python -m apps.backend.migration report --migration-id <id>")
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_resume(args) -> int:
    """Resume a paused migration."""
    print(f"▶️  Resuming migration {args.migration_id}...")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        context = orchestrator.resume_migration(args.migration_id)
        
        print(f"\n✅ Migration resumed!")
        print(f"  Status: {context.state.value}")
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_rollback(args) -> int:
    """Rollback a migration."""
    print(f"⏮️  Rolling back migration {args.migration_id}...")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        context = orchestrator.resume_migration(args.migration_id)
        
        result = orchestrator.rollback_migration(args.to_phase)
        
        if result.get("status") == "rolled_back":
            print(f"\n✅ Migration rolled back!")
            print(f"  Checkpoint: {result.get('checkpoint')}")
            print(f"  Commit: {result.get('commit')}")
        else:
            print(f"\n❌ Rollback failed: {result.get('message')}")
            return 1
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_status(args) -> int:
    """Show migration status."""
    if args.migration_id:
        print(f"📊 Status of migration {args.migration_id}:\n")
    else:
        print("📊 Migration Status:\n")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        status = orchestrator.get_status()
        
        if status["status"] == "no_migration":
            print("No active migration")
            return 0
        
        print(f"  State: {status['state']}")
        print(f"  Source: {status['source_stack']['framework']}")
        print(f"  Target: {status['target_stack']['framework']}")
        print(f"  Current Phase: {status['current_phase']}")
        print(f"  Checkpoints: {len(status.get('checkpoints', []))}")
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_report(args) -> int:
    """Generate migration report."""
    print(f"📋 Generating report for {args.migration_id}...")
    
    try:
        orchestrator = MigrationOrchestrator(args.project_dir)
        context = orchestrator.resume_migration(args.migration_id)
        
        reporter = MigrationReporter(context)
        output_path = reporter.save_report(args.output)
        
        print(f"\n✅ Report generated!")
        print(f"  Path: {output_path}")
        print(f"  Format: {args.format}")
        
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
