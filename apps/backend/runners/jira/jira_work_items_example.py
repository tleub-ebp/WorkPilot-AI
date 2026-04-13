#!/usr/bin/env python3
"""
Example usage of JIRA WorkItemsClient

This example shows how to use the JIRA connector to:
1. List backlog items from a project
2. Get detailed issue information
3. Search for issues using JQL
4. List available projects

Setup:
1. Set environment variables:
   - JIRA_URL: Your JIRA instance URL (e.g., "https://your-domain.atlassian.net")
   - JIRA_EMAIL: Your JIRA email
   - JIRA_API_TOKEN: Your JIRA API token

2. Install dependencies:
   pip install requests

3. Run the example:
   python apps/backend/runners/jira/jira_work_items_example.py
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.connectors.jira.client import JiraClient
from src.connectors.jira.work_items import JiraWorkItemsClient


def main():
    """Example usage of JIRA WorkItemsClient."""

    print("🚀 JIRA WorkItemsClient Example")
    print("=" * 50)

    try:
        # Create and connect the JIRA client
        print("\n📡 Connecting to JIRA...")
        client = JiraClient.from_env()
        client.connect()
        print("✅ Connected to JIRA successfully!")

        # Create the work items client
        wit_client = JiraWorkItemsClient(client)

        # List all available projects
        print("\n📋 Available Projects:")
        projects = wit_client.list_projects()
        if projects:
            for project in projects[:5]:  # Show first 5 projects
                print(f"  - {project.key}: {project.name}")
        else:
            print("  No projects found or accessible")

        # Example: List backlog items for a project
        # Replace "PROJ" with your actual project key
        project_key = os.getenv("JIRA_PROJECT", "PROJ")
        print(f"\n📝 Backlog items for project '{project_key}':")

        try:
            backlog_items = wit_client.list_backlog_items(
                project=project_key, max_items=10
            )

            if backlog_items:
                for item in backlog_items:
                    print(f"  - {item.key}: {item.summary}")
                    print(f"    Type: {item.issue_type}")
                    print(f"    Status: {item.status.name}")
                    print(f"    Priority: {item.priority}")
                    if item.assignee:
                        print(f"    Assignee: {item.assignee.display_name}")
                    print()
            else:
                print("  No backlog items found")

        except Exception as e:
            print(f"  Error listing backlog items: {e}")

        # Example: Get details for a specific issue
        # Replace "PROJ-123" with an actual issue key
        example_issue_key = f"{project_key}-1"
        print(f"\n🔍 Getting details for issue '{example_issue_key}':")

        try:
            issue = wit_client.get_issue_details(example_issue_key)
            print(f"  Summary: {issue.summary}")
            print(f"  Type: {issue.issue_type}")
            print(f"  Status: {issue.status.name}")
            print(f"  Priority: {issue.priority}")
            print(f"  Created: {issue.created}")
            print(f"  Updated: {issue.updated}")
            if issue.description:
                desc_preview = (
                    issue.description[:100] + "..."
                    if len(issue.description) > 100
                    else issue.description
                )
                print(f"  Description: {desc_preview}")

        except Exception as e:
            print(f"  Error getting issue details: {e}")

        # Example: Search issues using JQL
        print("\n🔎 Searching issues with custom JQL...")

        try:
            # Search for high priority issues
            jql = f'project = "{project_key}" AND priority in ("Highest", "High") ORDER BY created DESC'
            search_results = wit_client.search_issues(jql, max_results=5)

            if search_results:
                print(f"  Found {len(search_results)} high priority issues:")
                for issue in search_results:
                    print(f"    - {issue.key}: {issue.summary}")
            else:
                print("  No high priority issues found")

        except Exception as e:
            print(f"  Error searching issues: {e}")

        print("\n✅ Example completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you have set the required environment variables:")
        print("   - JIRA_URL")
        print("   - JIRA_EMAIL")
        print("   - JIRA_API_TOKEN")
        print("   - JIRA_PROJECT (optional)")


if __name__ == "__main__":
    main()
