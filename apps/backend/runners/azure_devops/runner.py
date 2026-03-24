"""
Azure DevOps PR Review Runner
===============================

CLI entry point for Azure DevOps PR review.

Usage:
    python runner.py review-pr <PR_ID> --project <PROJECT> --repo <REPO_ID> [options]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add apps/backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))
# Add project root for src/connectors
project_root = backend_dir.parent.parent
sys.path.insert(0, str(project_root))

from runners.azure_devops.models import AzureDevOpsRunnerConfig
from runners.azure_devops.orchestrator import AzureDevOpsOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Azure DevOps PR Review Runner")
    subparsers = parser.add_subparsers(dest="command")

    # review-pr command
    review_parser = subparsers.add_parser("review-pr", help="Review a PR")
    review_parser.add_argument("pr_id", type=int, help="Pull Request ID")
    review_parser.add_argument(
        "--project", required=True, help="Azure DevOps project name"
    )
    review_parser.add_argument("--repo", required=True, help="Repository ID or name")
    review_parser.add_argument("--project-dir", help="Project directory")
    review_parser.add_argument("--model", default="sonnet", help="Model to use")
    review_parser.add_argument("--thinking", default="medium", help="Thinking level")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "review-pr":
        # Get credentials from environment
        pat = os.environ.get("AZURE_DEVOPS_PAT")
        org_url = os.environ.get("AZURE_DEVOPS_ORG_URL")

        if not pat or not org_url:
            print(
                "Error: AZURE_DEVOPS_PAT and AZURE_DEVOPS_ORG_URL must be set",
                file=sys.stderr,
            )
            sys.exit(1)

        project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()

        config = AzureDevOpsRunnerConfig(
            pat=pat,
            organization_url=org_url,
            project=args.project,
            repository_id=args.repo,
            model=args.model,
            thinking_level=args.thinking,
        )

        orchestrator = AzureDevOpsOrchestrator(
            project_dir=project_dir,
            config=config,
        )

        result = asyncio.run(orchestrator.review_pr(args.pr_id))
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
