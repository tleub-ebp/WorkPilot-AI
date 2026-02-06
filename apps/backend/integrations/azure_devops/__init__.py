"""
Azure DevOps integration module.

Provides Azure DevOps work item tracking integration.
"""

from .integration import (
    AzureDevOpsManager,
    get_azure_devops_manager,
    is_azure_devops_enabled,
)

__all__ = [
    "AzureDevOpsManager",
    "get_azure_devops_manager",
    "is_azure_devops_enabled",
]
