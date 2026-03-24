#!/usr/bin/env python3
"""
Team Knowledge Sync Runner — Feature 31
=========================================

CLI entry point for managing shared team memory.

Usage:
    cd apps/backend
    # Push local snapshot to shared location
    python runners/team_sync_runner.py --push --project /path/to/project

    # Pull snapshots from teammates
    python runners/team_sync_runner.py --pull --project /path/to/project

    # Show sync status and available peers
    python runners/team_sync_runner.py --status --project /path/to/project

    # Start HTTP server (share your memory over the network)
    python runners/team_sync_runner.py --serve --project /path/to/project

    # Override sync path for one-off operations
    python runners/team_sync_runner.py --push --project /path --sync-path /mnt/shared/team

Environment:
    TEAM_SYNC_MODE             directory | http   (default: directory)
    TEAM_SYNC_PATH             /path/to/shared/folder
    TEAM_SYNC_TEAM_ID          my-team
    TEAM_SYNC_MEMBER_ID        alice
    TEAM_SYNC_SERVER_URL       http://alice:7749  (http mode, for pull/push)
    TEAM_SYNC_SERVER_HOST      0.0.0.0            (http mode, for serve)
    TEAM_SYNC_SERVER_PORT      7749               (http mode, for serve)
"""

import sys
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dependency_validator import validate_platform_dependencies

validate_platform_dependencies()

from cli.utils import import_dotenv

load_dotenv = import_dotenv()
env_file = Path(__file__).parent.parent.parent.parent / ".env-files" / ".env"
if env_file.exists():
    load_dotenv(env_file)

import argparse
import logging

from integrations.graphiti.team_sync.config import TeamSyncConfig
from integrations.graphiti.team_sync.sync_manager import TeamSyncManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


def _print_result(result: dict) -> None:
    """Pretty-print a result dict."""
    if result.get("success") is False:
        print(f"  ✗ Error: {result.get('error', 'unknown error')}")
    else:
        for k, v in result.items():
            if k == "success":
                continue
            print(f"  {k}: {v}")


def cmd_push(manager: TeamSyncManager) -> None:
    print("Exporting local memory snapshot…")
    result = manager.push()
    _print_result(result)
    if result.get("success"):
        print(f"  ✓ Pushed {result.get('episode_count', 0)} episodes")


def cmd_pull(manager: TeamSyncManager) -> None:
    print("Pulling team memory snapshots…")
    result = manager.pull()
    _print_result(result)
    if result.get("success"):
        peers = result.get("peers", [])
        imported = result.get("imported", 0)
        print(
            f"  ✓ Imported {imported} new episodes from {len(peers)} peer(s): {', '.join(peers) or '(none)'}"
        )


def cmd_status(manager: TeamSyncManager) -> None:
    status = manager.get_status()
    print("Team Knowledge Sync Status")
    print("─" * 40)
    for k, v in status.items():
        print(f"  {k:<28} {v}")
    print()
    peers = manager.list_peers()
    if peers:
        print(f"  {'Member':<20} {'Episodes':>8}  {'Exported at'}")
        print("  " + "─" * 55)
        for p in peers:
            marker = " (you)" if p.get("is_self") else ""
            print(
                f"  {p['member_id']:<20} {p['episode_count']:>8}  {p['exported_at'] or '?'}{marker}"
            )
    else:
        print("  No peer snapshots found.")


def cmd_serve(config: TeamSyncConfig, project_dir: Path) -> None:
    print(
        f"Starting Team Knowledge Sync HTTP server on {config.server_host}:{config.server_port}…"
    )
    print(f"  Team ID  : {config.team_id}")
    print(f"  Member   : {config.member_id}")
    print("  Ctrl+C to stop")
    from integrations.graphiti.team_sync.http_server import start_server

    start_server(
        project_dir=project_dir,
        team_id=config.team_id,
        member_id=config.member_id,
        host=config.server_host,
        port=config.server_port,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Team Knowledge Sync — share Graphiti memory with your team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the project root directory",
    )
    parser.add_argument("--push", action="store_true", help="Export local snapshot")
    parser.add_argument("--pull", action="store_true", help="Import peer snapshots")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--serve", action="store_true", help="Start HTTP server")
    parser.add_argument("--sync-path", help="Override TEAM_SYNC_PATH")
    parser.add_argument("--team-id", help="Override TEAM_SYNC_TEAM_ID")
    parser.add_argument("--member-id", help="Override TEAM_SYNC_MEMBER_ID")
    parser.add_argument(
        "--mode", choices=["directory", "http"], help="Override TEAM_SYNC_MODE"
    )
    parser.add_argument("--server-url", help="Override TEAM_SYNC_SERVER_URL")
    parser.add_argument("--port", type=int, help="Override TEAM_SYNC_SERVER_PORT")
    args = parser.parse_args()

    if not any([args.push, args.pull, args.status, args.serve]):
        parser.print_help()
        sys.exit(0)

    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}")
        sys.exit(1)

    config = TeamSyncConfig.from_env()
    if args.mode:
        config.mode = args.mode
    if args.sync_path:
        config.sync_path = args.sync_path
    if args.team_id:
        config.team_id = args.team_id
    if args.member_id:
        config.member_id = args.member_id
    if args.server_url:
        config.server_url = args.server_url
    if args.port:
        config.server_port = args.port

    print(f"Project : {project_dir}")
    print(f"Mode    : {config.mode}")
    print(f"Team    : {config.team_id} / {config.member_id}")
    print()

    manager = TeamSyncManager(config=config, project_dir=project_dir)

    if args.status:
        cmd_status(manager)
    if args.push:
        cmd_push(manager)
    if args.pull:
        cmd_pull(manager)
    if args.serve:
        cmd_serve(config, project_dir)


if __name__ == "__main__":
    main()
