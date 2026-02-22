"""
Azure DevOps Configuration

Settings and configuration for Azure DevOps integration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Azure DevOps connection settings."""
    
    pat: str
    organization_url: str
    project: str
    
    def __post_init__(self):
        """Validate settings after initialization."""
        if not self.pat:
            raise ValueError("Personal Access Token (PAT) is required")
        if not self.organization_url:
            raise ValueError("Organization URL is required")
        if not self.project:
            raise ValueError("Project name is required")


@dataclass
class AzureDevOpsConfig:
    """Configuration for Azure DevOps integration."""
    
    pat: Optional[str] = None
    organization_url: Optional[str] = None
    project: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'AzureDevOpsConfig':
        """Create configuration from environment variables."""
        return cls(
            pat=os.getenv('AZURE_DEVOPS_PAT'),
            organization_url=os.getenv('AZURE_DEVOPS_ORG_URL'),
            project=os.getenv('AZURE_DEVOPS_PROJECT')
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return bool(self.pat and self.organization_url and self.project)
