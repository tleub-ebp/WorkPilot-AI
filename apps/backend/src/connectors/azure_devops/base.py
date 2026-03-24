"""
Base connector for Azure DevOps integration.

Provides common functionality for Azure DevOps connectors.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseIntegratedConnector(ABC):
    """Base class for Azure DevOps integrated connectors."""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to Azure DevOps."""
        pass

    @abstractmethod
    def list_backlog_items(self, project: str, item_types=None, max_items: int = 100):
        """List work items from backlog."""
        pass

    @abstractmethod
    def list_repositories(self, project: str):
        """List repositories in a project."""
        pass
