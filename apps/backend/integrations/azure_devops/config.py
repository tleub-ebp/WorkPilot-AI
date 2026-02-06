"""
Azure DevOps integration configuration.

Manages environment variables and connection settings for Azure DevOps.
"""

import os
from dataclasses import dataclass


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
