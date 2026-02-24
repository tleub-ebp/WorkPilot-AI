"""
Azure DevOps integration module facade.

Provides Azure DevOps work item tracking integration.
Re-exports from integrations.azure_devops.integration for clean imports.
"""

import sys
from pathlib import Path

# CRITICAL: Ensure project root is at the FRONT of sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
else:
    # Move project root to the front if it's already in the path but not at the front
    if sys.path[0] != str(project_root):
        sys.path.remove(str(project_root))
        sys.path.insert(0, str(project_root))

# Add backend directory to Python path for integrations module
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

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
