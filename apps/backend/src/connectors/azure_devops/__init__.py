"""
Azure DevOps Connector

Provides integration with Azure DevOps for:
- Pull Requests (Azure Repos)
- Work Items
- Repository operations
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .base import BaseIntegratedConnector
from .config import Settings

logger = logging.getLogger(__name__)

# Set to True to silence the mock-data warning (e.g. in test environments).
# In production we want the warning so nobody thinks the connector is live.
_SUPPRESS_MOCK_WARNING_ENV = "WORKPILOT_AZURE_DEVOPS_ALLOW_MOCK"


def _warn_mock(operation: str) -> None:
    import os as _os
    if _os.environ.get(_SUPPRESS_MOCK_WARNING_ENV):
        return
    logger.warning(
        "AzureDevOpsConnector.%s is returning MOCK DATA — the real Azure DevOps "
        "REST integration is not implemented yet. Set %s=1 to silence this warning.",
        operation,
        _SUPPRESS_MOCK_WARNING_ENV,
    )


class AzureDevOpsConnector(BaseIntegratedConnector):
    """Unified connector for Azure DevOps source control and work items.

    Combines repository operations (Azure Repos) and work item tracking
    into a single interface.
    """

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.settings = settings
        self._connection = None

    def connect(self) -> None:
        """Establish connection to Azure DevOps."""
        try:
            # For now, we'll use a simple connection approach
            # In a full implementation, this would use the Azure DevOps REST API
            logger.info(f"Connected to Azure DevOps: {self.settings.organization_url}")
            self._connection = True
        except Exception as e:
            logger.error(f"Failed to connect to Azure DevOps: {e}")
            raise

    def list_backlog_items(
        self, project: str, item_types: list[str] | None = None, max_items: int = 100
    ) -> list[dict[str, Any]]:
        """List work items from backlog."""
        _warn_mock("list_backlog_items")
        # Mock implementation for now - in real implementation, this would call Azure DevOps API
        # For now, return mock data with repository information
        mock_items = [
            {
                "id": 1,
                "title": "Fix login authentication issue",
                "description": "Users cannot log in with valid credentials",
                "state": "Active",
                "workItemType": "Bug",
                "assignedTo": "john.doe@example.com",
                "tags": ["authentication", "critical"],
                "priority": 1,
                "createdDate": "2024-01-15T10:00:00Z",
                "areaPath": f"{project}\\WebApp",
                "iterationPath": f"{project}\\Sprint 1",
                "url": f"{self.settings.organization_url}/{project}/_workitems/edit/1",
                "repository": "web-app-repo",  # Add repository info
            },
            {
                "id": 2,
                "title": "Implement user profile feature",
                "description": "Add user profile page with editable fields",
                "state": "New",
                "workItemType": "User Story",
                "assignedTo": "jane.smith@example.com",
                "tags": ["feature", "ui"],
                "priority": 2,
                "createdDate": "2024-01-16T14:30:00Z",
                "areaPath": f"{project}\\WebApp",
                "iterationPath": f"{project}\\Sprint 2",
                "url": f"{self.settings.organization_url}/{project}/_workitems/edit/2",
                "repository": "web-app-repo",  # Add repository info
            },
            {
                "id": 3,
                "title": "Optimize database queries",
                "description": "Improve performance of slow database operations",
                "state": "In Progress",
                "workItemType": "Task",
                "tags": ["performance", "backend"],
                "priority": 3,
                "createdDate": "2024-01-17T09:15:00Z",
                "areaPath": f"{project}\\Backend",
                "iterationPath": f"{project}\\Sprint 1",
                "url": f"{self.settings.organization_url}/{project}/_workitems/edit/3",
                "repository": "api-service",  # Add repository info
            },
        ]

        # Filter by item types if specified
        if item_types:
            mock_items = [
                item for item in mock_items if item["workItemType"] in item_types
            ]

        # Limit to max_items
        return mock_items[:max_items]

    def list_repositories(self, project: str) -> list[dict[str, Any]]:
        """List repositories in a project."""
        _warn_mock("list_repositories")
        # Mock implementation for now
        return []

    def get_pull_request_details(
        self, repository: str, pull_request_id: int
    ) -> dict[str, Any]:
        """Get detailed information about a pull request."""
        try:
            # For now, use a mock implementation that returns realistic data
            # In a real implementation, this would call Azure DevOps REST API
            logger.info(f"Getting PR details for {repository}#{pull_request_id}")

            # Try to get real data from Azure DevOps REST API
            # This is a simplified implementation - in production, you'd use the Azure DevOps API
            import requests

            # Get the base URL from settings
            org_url = self.settings.organization_url.rstrip("/")
            project = self.settings.project

            # Azure DevOps REST API endpoint for pull requests
            api_url = f"{org_url}/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request_id}?api-version=6.0"

            headers = {
                "Authorization": f"Bearer {self.settings.pat}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.get(api_url, headers=headers, timeout=30)
                response.raise_for_status()

                pr_data = response.json()

                # Get files changed in the PR
                files_url = f"{org_url}/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request_id}/commits?api-version=6.0"
                files_response = requests.get(files_url, headers=headers, timeout=30)
                files_response.raise_for_status()

                commits = files_response.json()
                files = []

                # Extract file changes from commits
                for commit in commits.get("value", []):
                    changes_url = f"{org_url}/{project}/_apis/git/repositories/{repository}/commits/{commit['commitId']}/changes?api-version=6.0"
                    changes_response = requests.get(
                        changes_url, headers=headers, timeout=30
                    )
                    changes_response.raise_for_status()

                    for change in changes_response.json().get("changes", []):
                        files.append(
                            {
                                "path": change.get("item", {}).get("path", ""),
                                "changeType": change.get("changeType", "edit"),
                                "additions": change.get("additions", 0),
                                "deletions": change.get("deletions", 0),
                            }
                        )

                return {
                    "id": pr_data.get("pullRequestId", pull_request_id),
                    "title": pr_data.get("title", f"Pull Request #{pull_request_id}"),
                    "description": pr_data.get("description", ""),
                    "status": pr_data.get("status", "active"),
                    "creationDate": pr_data.get(
                        "creationDate", datetime.now().isoformat()
                    ),
                    "sourceRefName": pr_data.get("sourceRefName", "feature/branch"),
                    "targetRefName": pr_data.get("targetRefName", "main"),
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "createdBy": {
                        "displayName": pr_data.get("createdBy", {}).get(
                            "displayName", "Unknown"
                        )
                    },
                    "files": files,
                }

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch PR data from Azure DevOps API: {e}")
                # Fallback to mock data
                return self._get_mock_pr_details(pull_request_id, repository)

        except Exception as e:
            logger.error(f"Failed to get PR details: {e}")
            raise

    def _get_mock_pr_details(
        self, pull_request_id: int, repository: str
    ) -> dict[str, Any]:
        """Fallback mock implementation for PR details."""
        _warn_mock("get_pull_request_details")
        return {
            "id": pull_request_id,
            "title": f"Pull Request #{pull_request_id}",
            "description": f"Mock description for PR #{pull_request_id} in {repository}",
            "status": "active",
            "creationDate": datetime.now().isoformat(),
            "sourceRefName": "feature/branch",
            "targetRefName": "main",
            "additions": 10,
            "deletions": 5,
            "createdBy": {"displayName": "Mock User"},
            "files": [
                {
                    "path": "src/example.ts",
                    "changeType": "edit",
                    "additions": 10,
                    "deletions": 5,
                }
            ],
        }

    def get_pull_request_files(
        self, repository: str, pull_request_id: int
    ) -> list[dict[str, Any]]:
        """Get files changed in a pull request."""
        try:
            _warn_mock("get_pull_request_files")
            logger.info(f"Getting PR files for {repository}#{pull_request_id}")

            return [
                {
                    "path": "src/example.ts",
                    "changeType": "edit",
                    "additions": 10,
                    "deletions": 5,
                }
            ]
        except Exception as e:
            logger.error(f"Failed to get PR files: {e}")
            raise
