"""
Team Knowledge Sync Manager
============================

Exports local memory episodes to a shared location and imports
snapshots from team members.

Snapshot format (JSON):
{
  "schema_version": "1",
  "member_id": "alice",
  "team_id": "my-team",
  "exported_at": "2026-03-17T...",
  "episodes": [
    {"type": "session_insight", "content": "...", "spec": "001-auth", "timestamp": "..."},
    {"type": "pattern",  "content": "...", "spec": "001-auth", "timestamp": "..."},
    ...
  ]
}

Episodes are collected from:
  1. File-based memory files   spec/{N}-name/memory/*.json  (always available)
  2. Graphiti state JSON       spec/{N}-name/.graphiti_state.json  (metadata only)

On import, episodes are injected via GraphitiMemory.add_* methods (if Graphiti
is enabled) AND written to local file-based memory for instant offline access.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .config import TeamSyncConfig

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1"
IMPORT_MARKER_FILE = ".team_sync_imported.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _episode_id(episode: dict) -> str:
    """Stable ID for deduplication: hash of (member_id + type + content[:200])."""
    key = f"{episode.get('member_id', '')}:{episode.get('type', '')}:{str(episode.get('content', ''))[:200]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _load_imported_ids(project_dir: Path) -> set[str]:
    """Load the set of already-imported episode IDs for this project."""
    marker = project_dir / ".auto-claude" / IMPORT_MARKER_FILE
    if not marker.exists():
        return set()
    try:
        with open(marker, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_imported_ids(project_dir: Path, ids: set[str]) -> None:
    marker_dir = project_dir / ".auto-claude"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / IMPORT_MARKER_FILE
    try:
        with open(marker, "w", encoding="utf-8") as f:
            json.dump(sorted(ids), f)
    except Exception as e:
        logger.warning(f"Could not save imported IDs: {e}")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def _collect_file_based_episodes(project_dir: Path, member_id: str) -> list[dict]:
    """
    Walk all spec directories and gather episodes from memory/*.json files.
    """
    episodes: list[dict] = []
    auto_claude_dir = project_dir / ".auto-claude"
    if not auto_claude_dir.exists():
        return episodes

    specs_dir = auto_claude_dir / "specs"
    if not specs_dir.exists():
        return episodes

    for spec_dir in sorted(specs_dir.iterdir()):
        if not spec_dir.is_dir():
            continue
        memory_dir = spec_dir / "memory"
        if not memory_dir.exists():
            continue
        for mem_file in sorted(memory_dir.glob("*.json")):
            try:
                with open(mem_file, encoding="utf-8") as f:
                    data = json.load(f)
                # data may be a dict or list
                if isinstance(data, list):
                    for entry in data:
                        episodes.append(
                            _normalise_episode(entry, spec_dir.name, member_id)
                        )
                elif isinstance(data, dict):
                    episodes.append(_normalise_episode(data, spec_dir.name, member_id))
            except Exception as e:
                logger.debug(f"Skipping {mem_file}: {e}")

    return episodes


def _normalise_episode(raw: Any, spec_name: str, member_id: str) -> dict:
    """Normalise a raw episode dict into the canonical snapshot format."""
    ep_type = raw.get("type") or raw.get("episode_type") or "session_insight"
    content = (
        raw.get("content") or raw.get("summary") or raw.get("text") or json.dumps(raw)
    )
    timestamp = (
        raw.get("timestamp")
        or raw.get("created_at")
        or datetime.now(timezone.utc).isoformat()
    )
    return {
        "type": ep_type,
        "content": str(content),
        "spec": spec_name,
        "timestamp": timestamp,
        "member_id": member_id,
        "tags": raw.get("tags", []),
        "metadata": {
            k: v
            for k, v in raw.items()
            if k not in ("type", "content", "timestamp", "tags")
        },
    }


# ---------------------------------------------------------------------------
# TeamSyncManager
# ---------------------------------------------------------------------------


class TeamSyncManager:
    """
    Orchestrates export, import, listing, and HTTP server operations
    for Team Knowledge Sync.
    """

    def __init__(self, config: TeamSyncConfig, project_dir: Path):
        self.config = config
        self.project_dir = project_dir

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_snapshot(self) -> dict:
        """
        Build and return the local snapshot dict (does NOT write to disk yet).
        """
        episodes = _collect_file_based_episodes(self.project_dir, self.config.member_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "member_id": self.config.member_id,
            "team_id": self.config.team_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "project": self.project_dir.name,
            "episode_count": len(episodes),
            "episodes": episodes,
        }

    def push(self) -> dict:
        """
        Export local snapshot and write it to the shared location.

        Returns:
            {"success": bool, "path": str, "episode_count": int, "error": str}
        """
        if self.config.mode == "directory":
            return self._push_directory()
        if self.config.mode == "http":
            return asyncio.run(self._push_http())
        return {"success": False, "error": f"Unknown sync mode: {self.config.mode}"}

    def _push_directory(self) -> dict:
        sync_dir = self.config.get_sync_dir()
        if sync_dir is None:
            return {"success": False, "error": "TEAM_SYNC_PATH is not set"}

        snapshot = self.export_snapshot()
        snapshot_path = sync_dir / self.config.get_snapshot_filename()
        try:
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            logger.info(
                f"[TeamSync] Pushed {snapshot['episode_count']} episodes → {snapshot_path}"
            )
            return {
                "success": True,
                "path": str(snapshot_path),
                "episode_count": snapshot["episode_count"],
            }
        except Exception as e:
            capture_exception(e, component="team_sync", operation="push_directory")
            return {"success": False, "error": str(e)}

    async def _push_http(self) -> dict:
        try:
            import aiohttp  # type: ignore
        except ImportError:
            return {
                "success": False,
                "error": "aiohttp not installed; use directory mode or install aiohttp",
            }

        snapshot = self.export_snapshot()
        try:
            async with aiohttp.ClientSession() as session:
                url = self.config.server_url.rstrip("/") + "/push"
                async with session.post(
                    url, json=snapshot, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return {
                            "success": True,
                            "episode_count": snapshot["episode_count"],
                        }
                    text = await resp.text()
                    return {
                        "success": False,
                        "error": f"Server returned {resp.status}: {text}",
                    }
        except Exception as e:
            capture_exception(e, component="team_sync", operation="push_http")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Pull / Import
    # ------------------------------------------------------------------

    def pull(self) -> dict:
        """
        Fetch all peer snapshots and import new episodes.

        Returns:
            {"success": bool, "imported": int, "peers": list[str], "error": str}
        """
        if self.config.mode == "directory":
            return self._pull_directory()
        if self.config.mode == "http":
            return asyncio.run(self._pull_http())
        return {"success": False, "error": f"Unknown sync mode: {self.config.mode}"}

    def _pull_directory(self) -> dict:
        sync_dir = self.config.get_sync_dir()
        if sync_dir is None:
            return {"success": False, "error": "TEAM_SYNC_PATH is not set"}

        imported_ids = _load_imported_ids(self.project_dir)
        total_imported = 0
        peers: list[str] = []

        for snapshot_file in sorted(sync_dir.glob("*_snapshot.json")):
            # Skip own snapshot
            if snapshot_file.name == self.config.get_snapshot_filename():
                continue
            try:
                with open(snapshot_file, encoding="utf-8") as f:
                    snapshot = json.load(f)
                peer = snapshot.get("member_id", snapshot_file.stem)
                peers.append(peer)
                count = self._import_snapshot(snapshot, imported_ids)
                total_imported += count
                logger.info(f"[TeamSync] Imported {count} new episodes from {peer}")
            except Exception as e:
                logger.warning(f"[TeamSync] Failed to import {snapshot_file}: {e}")

        _save_imported_ids(self.project_dir, imported_ids)
        return {"success": True, "imported": total_imported, "peers": peers}

    async def _pull_http(self) -> dict:
        try:
            import aiohttp  # type: ignore
        except ImportError:
            return {
                "success": False,
                "error": "aiohttp not installed; use directory mode",
            }

        imported_ids = _load_imported_ids(self.project_dir)
        total_imported = 0
        peers: list[str] = []

        try:
            async with aiohttp.ClientSession() as session:
                url = self.config.server_url.rstrip("/") + "/snapshots"
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        return {
                            "success": False,
                            "error": f"Server returned {resp.status}",
                        }
                    snapshots: list[dict] = await resp.json()

            for snapshot in snapshots:
                if snapshot.get("member_id") == self.config.member_id:
                    continue
                peer = snapshot.get("member_id", "unknown")
                peers.append(peer)
                count = self._import_snapshot(snapshot, imported_ids)
                total_imported += count
        except Exception as e:
            capture_exception(e, component="team_sync", operation="pull_http")
            return {"success": False, "error": str(e)}

        _save_imported_ids(self.project_dir, imported_ids)
        return {"success": True, "imported": total_imported, "peers": peers}

    def _import_snapshot(self, snapshot: dict, imported_ids: set[str]) -> int:
        """
        Inject new episodes from a peer snapshot into local file-based storage.
        Returns the number of newly imported episodes.
        """
        episodes = snapshot.get("episodes", [])
        if not episodes:
            return 0

        peer_member = snapshot.get("member_id", "unknown")
        imported_count = 0
        peer_memory_dir = (
            self.project_dir / ".auto-claude" / "team_sync" / "peers" / peer_member
        )
        peer_memory_dir.mkdir(parents=True, exist_ok=True)

        new_episodes: list[dict] = []
        for episode in episodes:
            ep_id = _episode_id(episode)
            if ep_id in imported_ids:
                continue
            imported_ids.add(ep_id)
            new_episodes.append(episode)
            imported_count += 1

        if new_episodes:
            # Write as a single consolidated file per-peer
            out_file = peer_memory_dir / "imported_episodes.json"
            existing: list[dict] = []
            if out_file.exists():
                try:
                    with open(out_file, encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            existing.extend(new_episodes)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

        return imported_count

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """
        Return current sync status: config validity, local snapshot info,
        number of peer snapshots available.
        """
        status: dict = {
            "enabled": self.config.is_valid(),
            "mode": self.config.mode,
            "team_id": self.config.team_id,
            "member_id": self.config.member_id,
            "sync_path": self.config.sync_path,
            "server_url": self.config.server_url,
            "auto_sync_interval": self.config.auto_sync_interval,
            "auto_push": self.config.auto_push,
            "peers": [],
            "last_export": None,
            "last_import": None,
            "local_episode_count": 0,
            "imported_episode_count": 0,
        }

        if not self.config.is_valid():
            return status

        if self.config.mode == "directory":
            sync_dir = self.config.get_sync_dir()
            if sync_dir:
                own_snapshot = sync_dir / self.config.get_snapshot_filename()
                if own_snapshot.exists():
                    try:
                        with open(own_snapshot, encoding="utf-8") as f:
                            snap = json.load(f)
                        status["last_export"] = snap.get("exported_at")
                        status["local_episode_count"] = snap.get("episode_count", 0)
                    except Exception:
                        pass

                peers = [
                    f.stem.replace("_snapshot", "")
                    for f in sync_dir.glob("*_snapshot.json")
                    if f.name != self.config.get_snapshot_filename()
                ]
                status["peers"] = peers

        # Count imported episodes
        peers_dir = self.project_dir / ".auto-claude" / "team_sync" / "peers"
        imported_total = 0
        if peers_dir.exists():
            for peer_dir in peers_dir.iterdir():
                ep_file = peer_dir / "imported_episodes.json"
                if ep_file.exists():
                    try:
                        with open(ep_file, encoding="utf-8") as f:
                            data = json.load(f)
                        imported_total += len(data) if isinstance(data, list) else 0
                    except Exception:
                        pass
        status["imported_episode_count"] = imported_total

        return status

    def list_peers(self) -> list[dict]:
        """List team members who have published a snapshot."""
        if not self.config.is_valid():
            return []

        result: list[dict] = []

        if self.config.mode == "directory":
            sync_dir = self.config.get_sync_dir()
            if not sync_dir:
                return []
            for snap_file in sorted(sync_dir.glob("*_snapshot.json")):
                try:
                    with open(snap_file, encoding="utf-8") as f:
                        snap = json.load(f)
                    result.append(
                        {
                            "member_id": snap.get("member_id", snap_file.stem),
                            "exported_at": snap.get("exported_at"),
                            "episode_count": snap.get("episode_count", 0),
                            "project": snap.get("project", ""),
                            "is_self": snap.get("member_id") == self.config.member_id,
                        }
                    )
                except Exception:
                    result.append(
                        {
                            "member_id": snap_file.stem.replace("_snapshot", ""),
                            "exported_at": None,
                            "episode_count": 0,
                            "project": "",
                            "is_self": False,
                        }
                    )

        return result

    def get_peer_episodes(self, member_id: str) -> list[dict]:
        """Return the episodes imported from a specific peer."""
        ep_file = (
            self.project_dir
            / ".auto-claude"
            / "team_sync"
            / "peers"
            / member_id
            / "imported_episodes.json"
        )
        if not ep_file.exists():
            return []
        try:
            with open(ep_file, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []
