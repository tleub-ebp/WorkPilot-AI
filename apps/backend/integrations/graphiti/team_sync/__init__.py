"""
Team Knowledge Sync — Feature 31
=================================

Shared Graphiti memory graph across all team members.
Architectural decisions, discovered patterns, and identified pitfalls
are accessible to the entire team.

Two sync modes:
- directory: Export/import snapshots via a shared folder (network drive,
             cloud-synced folder, or git-tracked path).
- http:      Start a local REST server; peers pull/push snapshots over HTTP.
"""

from .config import TeamSyncConfig
from .sync_manager import TeamSyncManager

__all__ = ["TeamSyncConfig", "TeamSyncManager"]
