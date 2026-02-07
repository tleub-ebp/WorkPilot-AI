"""
Azure DevOps integration configuration.

Manages environment variables and connection settings for Azure DevOps.

Important: AZURE_DEVOPS_PROJECT should be the Azure DevOps PROJECT name,
not the repository name. In the URL pattern:
  https://dev.azure.com/{org}/{project}/_git/{repository}

The PROJECT is the second segment, and REPOSITORY is after _git/.

Example:
  URL: https://dev.azure.com/ebp-informatique/MéCa/_git/MeCa%20Web
  - Organization: ebp-informatique
  - Project: MéCa (this goes in AZURE_DEVOPS_PROJECT)
  - Repository: MeCa Web
"""

import os
import re
from dataclasses import dataclass
from urllib.parse import unquote


@dataclass
class AzureDevOpsConfig:
    """Configuration for Azure DevOps integration."""

    pat: str | None = None
    organization_url: str | None = None
    project: str | None = None

    @classmethod
    def from_env(cls) -> "AzureDevOpsConfig":
        """Load configuration from environment variables."""
        return cls(
            pat=os.getenv("AZURE_DEVOPS_PAT"),
            organization_url=os.getenv("AZURE_DEVOPS_ORG_URL"),
            project=os.getenv("AZURE_DEVOPS_PROJECT"),
        )

    @staticmethod
    def extract_project_from_repo_url(repo_url: str) -> str | None:
        """
        Extract the project name from an Azure DevOps repository URL.

        Args:
            repo_url: Repository URL like
                https://dev.azure.com/{org}/{project}/_git/{repo}

        Returns:
            Project name (unquoted) or None if parsing fails

        Example:
            >>> url = "https://dev.azure.com/ebp/MéCa/_git/MeCa%20Web"
            >>> AzureDevOpsConfig.extract_project_from_repo_url(url)
            'MéCa'
        """
        # Pattern: https://dev.azure.com/{org}/{project}/_git/{repo}
        # or: https://{org}.visualstudio.com/{project}/_git/{repo}
        pattern = (
            r"https://(?:dev\.azure\.com/[^/]+|[^/]+\.visualstudio\.com)/([^/]+)/_git/"
        )
        match = re.search(pattern, repo_url)
        if match:
            return unquote(match.group(1))
        return None

    def is_valid(self) -> bool:
        """Check if the configuration has all required values."""
        return bool(
            self.pat
            and self.organization_url
            and self.organization_url.startswith("https://")
        )

    def validate(self) -> tuple[bool, str | None]:
        """
        Validate the configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.pat:
            return False, "Azure DevOps PAT is required"

        if not self.organization_url:
            return False, "Azure DevOps organization URL is required"

        if not self.organization_url.startswith("https://"):
            return (
                False,
                f"Organization URL must use HTTPS: {self.organization_url}",
            )

        return True, None
