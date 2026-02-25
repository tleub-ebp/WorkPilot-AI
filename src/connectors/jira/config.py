"""
JIRA Connector Configuration

Configuration management for JIRA integration.
"""

import os
from typing import Optional


class Settings:
    """JIRA connector settings."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        project: Optional[str] = None,
    ):
        """Initialize JIRA settings.

        Args:
            server_url: JIRA server URL (e.g., "https://your-domain.atlassian.net")
            username: JIRA username/email
            api_token: JIRA API token
            project: Default JIRA project key
        """
        self.server_url = server_url or os.getenv("JIRA_SERVER_URL")
        self.username = username or os.getenv("JIRA_USERNAME")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        self.project = project or os.getenv("JIRA_PROJECT")

    def validate(self) -> None:
        """Validate required settings."""
        if not self.server_url:
            raise ValueError("JIRA server URL is required")
        if not self.username:
            raise ValueError("JIRA username is required")
        if not self.api_token:
            raise ValueError("JIRA API token is required")

    @property
    def auth_tuple(self) -> tuple[str, str]:
        """Get authentication tuple for requests."""
        return (self.username, self.api_token)
