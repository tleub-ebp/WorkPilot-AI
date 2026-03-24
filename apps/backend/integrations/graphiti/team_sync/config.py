"""
Team Knowledge Sync Configuration
===================================

Environment Variables:
    TEAM_SYNC_MODE:              directory | http  (default: directory)
    TEAM_SYNC_PATH:              Shared folder path (required in directory mode)
    TEAM_SYNC_TEAM_ID:           Team identifier used as a sub-folder name
    TEAM_SYNC_MEMBER_ID:         Local member name (default: OS username)
    TEAM_SYNC_SERVER_URL:        Remote server URL (required in http mode)
    TEAM_SYNC_SERVER_HOST:       Bind address for the local HTTP server (default: 0.0.0.0)
    TEAM_SYNC_SERVER_PORT:       Port for the local HTTP server (default: 7749)
    TEAM_SYNC_AUTO_SYNC_INTERVAL: Minutes between automatic pulls (0 = disabled, default: 30)
    TEAM_SYNC_AUTO_PUSH:         Push snapshot after each task (default: true)
"""

import getpass
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TeamSyncConfig:
    """Configuration for Team Knowledge Sync (Feature 31)."""

    # Sync mode
    mode: str = "directory"  # 'directory' or 'http'

    # Directory-mode settings
    sync_path: str = ""  # Shared folder accessible to all team members

    # Identity
    team_id: str = "default"
    member_id: str = ""  # Defaults to OS username if empty

    # HTTP-mode settings
    server_url: str = ""  # Remote server to connect to
    server_host: str = "0.0.0.0"
    server_port: int = 7749

    # Sync behaviour
    auto_sync_interval: int = 30  # minutes; 0 = disabled
    auto_push: bool = True

    def __post_init__(self) -> None:
        if not self.member_id:
            try:
                self.member_id = getpass.getuser()
            except Exception:
                self.member_id = "unknown"

    @classmethod
    def from_env(cls) -> "TeamSyncConfig":
        mode = os.environ.get("TEAM_SYNC_MODE", "directory").lower()
        sync_path = os.environ.get("TEAM_SYNC_PATH", "")
        team_id = os.environ.get("TEAM_SYNC_TEAM_ID", "default")
        member_id = os.environ.get("TEAM_SYNC_MEMBER_ID", "")
        server_url = os.environ.get("TEAM_SYNC_SERVER_URL", "")
        server_host = os.environ.get("TEAM_SYNC_SERVER_HOST", "0.0.0.0")
        try:
            server_port = int(os.environ.get("TEAM_SYNC_SERVER_PORT", "7749"))
        except ValueError:
            server_port = 7749
        try:
            auto_sync_interval = int(
                os.environ.get("TEAM_SYNC_AUTO_SYNC_INTERVAL", "30")
            )
        except ValueError:
            auto_sync_interval = 30
        auto_push = os.environ.get("TEAM_SYNC_AUTO_PUSH", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        return cls(
            mode=mode,
            sync_path=sync_path,
            team_id=team_id,
            member_id=member_id,
            server_url=server_url,
            server_host=server_host,
            server_port=server_port,
            auto_sync_interval=auto_sync_interval,
            auto_push=auto_push,
        )

    def is_valid(self) -> bool:
        if self.mode == "directory":
            return bool(self.sync_path)
        if self.mode == "http":
            return bool(self.server_url)
        return False

    def get_sync_dir(self) -> Path | None:
        """Return the resolved team directory inside the shared folder."""
        if not self.sync_path:
            return None
        base = Path(self.sync_path).expanduser()
        team_dir = base / self.team_id
        team_dir.mkdir(parents=True, exist_ok=True)
        return team_dir

    def get_snapshot_filename(self) -> str:
        return f"{self.member_id}_snapshot.json"
