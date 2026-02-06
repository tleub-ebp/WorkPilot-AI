"""
Azure DevOps integration module facade.

Provides Azure DevOps work item tracking integration.
Re-exports from integrations.azure_devops.integration for clean imports.
"""

from integrations.azure_devops.integration import (
    AzureDevOpsManager,
    get_azure_devops_manager,
    is_azure_devops_enabled,
)

__all__ = [
    "AzureDevOpsManager",
    "get_azure_devops_manager",
    "is_azure_devops_enabled",
]
