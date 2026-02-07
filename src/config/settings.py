"""Configuration settings module for Azure DevOps connector.

Manages environment variable loading and validation for Azure DevOps
credentials and connection parameters. Uses python-dotenv to load
variables from a .env file when available.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass
class Settings:
    """Azure DevOps connector configuration settings.

    Loads configuration from environment variables, with optional support
    for .env files via python-dotenv. Required fields are validated at
    initialization time.

    Attributes:
        pat: Personal Access Token for Azure DevOps authentication.
        organization_url: Azure DevOps organization URL
            (e.g., https://dev.azure.com/your-organization).
        project: Default project name. Optional; if not set, a project
            must be specified explicitly in API calls.

    Example:
        >>> settings = Settings.from_env()
        >>> print(settings.organization_url)
        'https://dev.azure.com/my-org'
    """

    pat: str
    organization_url: str
    project: str | None = field(default=None)

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "Settings":
        """Create Settings by loading values from environment variables.

        Loads a .env file if present (or from a custom path), then reads
        the required Azure DevOps environment variables.

        Args:
            env_file: Optional path to a .env file. If None, python-dotenv
                searches for a .env file in the current directory and parent
                directories.

        Returns:
            A fully initialized Settings instance.

        Raises:
            ValueError: If required environment variables are missing.
        """
        if env_file:
            load_dotenv(dotenv_path=env_file)
        else:
            load_dotenv()

        pat = os.getenv("AZURE_DEVOPS_PAT")
        organization_url = os.getenv("AZURE_DEVOPS_ORG_URL")
        project = os.getenv("AZURE_DEVOPS_PROJECT")

        missing = []
        if not pat:
            missing.append("AZURE_DEVOPS_PAT")
        if not organization_url:
            missing.append("AZURE_DEVOPS_ORG_URL")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "See .env.example for configuration details."
            )

        # Normalize organization URL by removing trailing slash
        organization_url = organization_url.rstrip("/")

        return cls(
            pat=pat,
            organization_url=organization_url,
            project=project if project else None,
        )

    def validate(self) -> None:
        """Validate that all required settings have valid values.

        Performs basic validation on setting values beyond presence checks.

        Raises:
            ValueError: If any setting value is invalid.
        """
        if not self.pat.strip():
            raise ValueError("AZURE_DEVOPS_PAT cannot be empty or whitespace.")

        if not self.organization_url.startswith("https://"):
            raise ValueError(
                "AZURE_DEVOPS_ORG_URL must start with 'https://'. "
                f"Got: '{self.organization_url}'"
            )
