"""Data models for the Azure DevOps connector.

Defines dataclass representations for Azure DevOps entities including
repositories, work items, and file items. Each model includes factory
methods for converting raw Azure DevOps API responses into clean,
typed data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Repository:
    """Azure DevOps Git repository representation.

    Represents a repository within an Azure DevOps project, including
    metadata such as the default branch and web URL.

    Attributes:
        id: The unique identifier of the repository.
        name: The display name of the repository.
        project: The name of the project containing this repository.
        default_branch: The default branch name (e.g., 'refs/heads/main').
            None if the repository is empty or uninitialized.
        web_url: The browser-accessible URL for the repository.
            None if not available.
    """

    id: str
    name: str
    project: str
    default_branch: str | None = None
    web_url: str | None = None

    @classmethod
    def from_api_response(cls, api_repo: Any) -> "Repository":
        """Create a Repository from an Azure DevOps API response object.

        Converts a GitRepository object returned by the Azure DevOps SDK
        into a clean Repository dataclass.

        Args:
            api_repo: A GitRepository object from the Azure DevOps SDK.
                Expected to have attributes: id, name, project (with name),
                default_branch, and remote_url.

        Returns:
            A Repository instance populated from the API response.
        """
        project_name = ""
        if hasattr(api_repo, "project") and api_repo.project:
            project_name = getattr(api_repo.project, "name", "")

        return cls(
            id=str(api_repo.id),
            name=api_repo.name,
            project=project_name,
            default_branch=getattr(api_repo, "default_branch", None),
            web_url=getattr(api_repo, "remote_url", None),
        )


@dataclass
class WorkItem:
    """Azure DevOps work item representation.

    Represents a work item (bug, task, user story, etc.) from Azure
    Boards, with all commonly used fields extracted from the raw API
    response.

    Attributes:
        id: The unique integer identifier of the work item.
        title: The work item title.
        state: The current state (e.g., 'New', 'Active', 'Closed').
        work_item_type: The type of work item (e.g., 'Bug', 'Task',
            'User Story').
        assigned_to: The display name of the assigned user, or None
            if unassigned.
        description: The HTML description of the work item, or None
            if empty.
        tags: A list of tags applied to the work item.
        created_date: The date and time the work item was created,
            or None if unavailable.
        area_path: The area path for the work item, or None if
            unavailable.
        iteration_path: The iteration/sprint path, or None if
            unavailable.
        priority: The priority level (integer), or None if unset.
        url: The API URL for the work item, or None if unavailable.
    """

    id: int
    title: str
    state: str
    work_item_type: str
    assigned_to: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    created_date: datetime | None = None
    area_path: str | None = None
    iteration_path: str | None = None
    priority: int | None = None
    url: str | None = None

    @classmethod
    def from_api_response(cls, api_work_item: Any) -> "WorkItem":
        """Create a WorkItem from an Azure DevOps API response object.

        Converts a WorkItem object returned by the Azure DevOps SDK
        into a clean WorkItem dataclass. Handles missing fields
        gracefully by using safe dictionary access.

        Args:
            api_work_item: A WorkItem object from the Azure DevOps SDK.
                Expected to have attributes: id, fields (dict), and url.

        Returns:
            A WorkItem instance populated from the API response.
        """
        fields = getattr(api_work_item, "fields", {}) or {}

        # Extract assigned_to display name from identity object
        assigned_to_field = fields.get("System.AssignedTo")
        assigned_to = None
        if isinstance(assigned_to_field, dict):
            assigned_to = assigned_to_field.get("displayName")
        elif isinstance(assigned_to_field, str):
            assigned_to = assigned_to_field

        # Parse tags from semicolon-separated string
        tags_str = fields.get("System.Tags", "")
        tags = (
            [tag.strip() for tag in tags_str.split(";") if tag.strip()]
            if tags_str
            else []
        )

        # Parse priority as integer if present
        raw_priority = fields.get("Microsoft.VSTS.Common.Priority")
        priority = None
        if raw_priority is not None:
            try:
                priority = int(raw_priority)
            except (ValueError, TypeError):
                priority = None

        return cls(
            id=api_work_item.id,
            title=fields.get("System.Title", ""),
            state=fields.get("System.State", ""),
            work_item_type=fields.get("System.WorkItemType", ""),
            assigned_to=assigned_to,
            description=fields.get("System.Description"),
            tags=tags,
            created_date=fields.get("System.CreatedDate"),
            area_path=fields.get("System.AreaPath"),
            iteration_path=fields.get("System.IterationPath"),
            priority=priority,
            url=getattr(api_work_item, "url", None),
        )


@dataclass
class FileItem:
    """Azure DevOps repository file or directory item.

    Represents a file or directory entry within an Azure DevOps Git
    repository, as returned by the repository items API.

    Attributes:
        path: The full path of the item within the repository
            (e.g., '/src/main.py').
        name: The file or directory name (e.g., 'main.py').
        is_folder: True if the item is a directory, False if it is
            a file.
        size: The size of the file in bytes, or None for directories.
        object_id: The Git object SHA hash, or None if unavailable.
        commit_id: The last commit ID that modified this item, or
            None if unavailable.
        url: The API URL for the item, or None if unavailable.
    """

    path: str
    name: str
    is_folder: bool
    size: int | None = None
    object_id: str | None = None
    commit_id: str | None = None
    url: str | None = None

    @classmethod
    def from_api_response(cls, api_item: Any) -> "FileItem":
        """Create a FileItem from an Azure DevOps API response object.

        Converts a GitItem object returned by the Azure DevOps SDK
        into a clean FileItem dataclass. Extracts the file name from
        the path and determines if the item is a folder.

        Args:
            api_item: A GitItem object from the Azure DevOps SDK.
                Expected to have attributes: path, git_object_type,
                object_id, commit_id, url, and size.

        Returns:
            A FileItem instance populated from the API response.
        """
        path = getattr(api_item, "path", "")

        # Extract name from path (last segment)
        name = path.rsplit("/", 1)[-1] if path else ""

        # Determine if folder from git_object_type
        git_object_type = getattr(api_item, "git_object_type", None)
        is_folder = git_object_type == "tree"

        return cls(
            path=path,
            name=name,
            is_folder=is_folder,
            size=getattr(api_item, "size", None) if not is_folder else None,
            object_id=getattr(api_item, "object_id", None),
            commit_id=getattr(api_item, "commit_id", None),
            url=getattr(api_item, "url", None),
        )
