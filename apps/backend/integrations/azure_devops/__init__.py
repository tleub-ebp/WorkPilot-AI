"""
Azure DevOps integration module.

Provides Azure DevOps work item tracking integration.
"""

# CRITICAL: Add project root to Python path FIRST before any other imports
import sys
from pathlib import Path

# Calculate project root (5 levels up from this file: azure_devops -> integrations -> backend -> apps -> project root)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
project_root_str = str(project_root)

# CRITICAL: Ensure project root is at the FRONT of sys.path
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
else:
    # Move project root to the front if it's already in the path but not at the front
    if sys.path[0] != project_root_str:
        sys.path.remove(project_root_str)
        sys.path.insert(0, project_root_str)

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
