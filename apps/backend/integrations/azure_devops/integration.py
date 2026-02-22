"""
Azure DevOps Integration Manager.

Manages synchronization between Auto-Claude tasks and Azure DevOps work items.
Provides a high-level interface for importing work items as tasks.

The integration is OPTIONAL - if AZURE_DEVOPS_PAT is not set, all operations
gracefully no-op and the application continues with local tracking only.
"""

import logging
from pathlib import Path

# Try different import paths for git_provider
try:
    from src.core.git_provider import extract_azure_devops_project
except ImportError:
    try:
        from core.git_provider import extract_azure_devops_project
    except ImportError:
        # Fallback: define a dummy function
        def extract_azure_devops_project(path):
            return None

from src.config.settings import Settings
from src.connectors.azure_devops import AzureDevOpsConnector

# Import config directly to avoid relative import issues
try:
    from .config import AzureDevOpsConfig
except ImportError:
    # Fallback for direct execution
    import importlib.util
    import sys
    config_path = Path(__file__).parent / 'config.py'
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    AzureDevOpsConfig = config_module.AzureDevOpsConfig

logger = logging.getLogger(__name__)


class AzureDevOpsManager:
    """
    Manages Azure DevOps integration for an Auto-Claude project.

    This class provides a high-level interface for:
    - Fetching work items from Azure DevOps
    - Importing work items as Auto-Claude tasks
    - Managing connection state

    All operations are graceful and handle Azure DevOps being unavailable.
    """

    def __init__(self, project_dir: Path):
        """
        Initialize Azure DevOps manager.

        Args:
            project_dir: Project root directory
        """
        self.project_dir = project_dir
        self.config = AzureDevOpsConfig.from_env()
        self._connector: AzureDevOpsConnector | None = None

        # Auto-detect project from Git remote if not configured
        if not self.config.project:
            detected_project = extract_azure_devops_project(project_dir)
            if detected_project:
                self.config.project = detected_project
                logger.info(
                    f"Auto-detected Azure DevOps project from Git remote: {detected_project}"
                )

    @property
    def is_enabled(self) -> bool:
        """Check if Azure DevOps integration is enabled and configured."""
        return self.config.is_valid()

    def get_connector(self) -> AzureDevOpsConnector | None:
        """
        Get or create an Azure DevOps connector.

        Returns:
            AzureDevOpsConnector instance if configured, None otherwise
        """
        if not self.is_enabled:
            logger.debug("Azure DevOps integration not enabled")
            return None

        if self._connector is None:
            try:
                settings = Settings(
                    pat=self.config.pat,
                    organization_url=self.config.organization_url,
                    project=self.config.project,
                )
                self._connector = AzureDevOpsConnector(settings)
                self._connector.connect()
                logger.info("Azure DevOps connector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure DevOps connector: {e}")
                return None

        return self._connector

    def test_connection(self) -> tuple[bool, str | None]:
        """
        Test the Azure DevOps connection.

        Returns:
            Tuple of (success, error_message)
        """
        if not self.is_enabled:
            return False, "Azure DevOps is not configured"

        try:
            connector = self.get_connector()
            if connector is None:
                return False, "Failed to create connector"

            # Try to list repositories as a connection test
            if self.config.project:
                connector.list_repositories(self.config.project)
            return True, None
        except Exception as e:
            logger.error(f"Azure DevOps connection test failed: {e}")
            return False, str(e)

    def list_work_items(
        self,
        project: str | None = None,
        item_types: list[str] | None = None,
        max_items: int = 100,
    ) -> list:
        """
        List work items from Azure DevOps backlog.

        Args:
            project: Project name (uses default from config if not provided)
            item_types: Filter by work item types (e.g., ["Bug", "User Story"])
            max_items: Maximum number of items to return

        Returns:
            List of WorkItem objects
        """
        connector = self.get_connector()
        if connector is None:
            logger.warning("Azure DevOps connector not available")
            return []

        project_name = project or self.config.project
        if not project_name:
            logger.error("No project specified and no default project in config")
            return []

        try:
            items = connector.list_backlog_items(
                project=project_name, item_types=item_types, max_items=max_items
            )
            logger.info(f"Retrieved {len(items)} work items from Azure DevOps")
            return items
        except Exception as e:
            logger.error(f"Failed to list work items: {e}")
            return []

    def get_work_item(self, project: str, item_id: int):
        """
        Get a single work item by ID.

        Args:
            project: Project name
            item_id: Work item ID

        Returns:
            WorkItem object or None if not found
        """
        connector = self.get_connector()
        if connector is None:
            return None

        try:
            return connector.get_item(project, item_id)
        except Exception as e:
            logger.error(f"Failed to get work item {item_id}: {e}")
            return None


def get_azure_devops_manager(project_dir: Path) -> AzureDevOpsManager:
    """
    Factory function to create an Azure DevOps manager.

    Args:
        project_dir: Project root directory

    Returns:
        AzureDevOpsManager instance
    """
    return AzureDevOpsManager(project_dir)


def is_azure_devops_enabled() -> bool:
    """
    Check if Azure DevOps integration is enabled.

    Returns:
        True if AZURE_DEVOPS_PAT is set and valid
    """
    config = AzureDevOpsConfig.from_env()
    return config.is_valid()
