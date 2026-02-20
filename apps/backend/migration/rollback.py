"""
Rollback Manager: Handles migration rollback and recovery.
"""

from typing import Dict, Optional, List
from pathlib import Path
import subprocess
from datetime import datetime

from .models import RollbackCheckpoint, MigrationContext


class RollbackManager:
    """Manages migration rollback and recovery."""

    def __init__(self, context: MigrationContext):
        self.context = context
        self.project_dir = Path(context.project_dir)

    def create_checkpoint(self, phase_id: str, description: str = "") -> RollbackCheckpoint:
        """Create a rollback checkpoint."""
        # Get current git commit
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            commit_hash = result.stdout.strip()
        except Exception as e:
            print(f"Warning: Could not get git commit: {e}")
            commit_hash = "unknown"

        checkpoint = RollbackCheckpoint(
            phase_id=phase_id,
            checkpoint_id=f"{phase_id}_{datetime.now().timestamp()}",
            git_commit=commit_hash,
            timestamp=datetime.now(),
            state_file=str(
                self.project_dir / f".auto-claude/migration/checkpoint_{phase_id}.json"
            ),
            description=description or f"Checkpoint before {phase_id}",
        )

        # Save state
        self.context.checkpoints[phase_id] = commit_hash

        return checkpoint

    def rollback_to_checkpoint(self, phase_id: str) -> Dict:
        """Rollback to a specific checkpoint."""
        if phase_id not in self.context.checkpoints:
            return {
                "success": False,
                "error": f"Checkpoint {phase_id} not found",
            }

        commit_hash = self.context.checkpoints[phase_id]
        
        try:
            result = subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                }

            return {
                "success": True,
                "checkpoint": phase_id,
                "commit": commit_hash,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def rollback_to_begin(self) -> Dict:
        """Rollback to the beginning (before any transformation started)."""
        if not self.context.checkpoints:
            return {
                "success": False,
                "error": "No checkpoints available",
            }

        # Get the earliest checkpoint (backup phase)
        phase_ids = list(self.context.checkpoints.keys())
        if not phase_ids:
            return {
                "success": False,
                "error": "No valid checkpoints found",
            }

        earliest_phase = "backup" if "backup" in phase_ids else phase_ids[0]
        return self.rollback_to_checkpoint(earliest_phase)

    def list_checkpoints(self) -> List[Dict]:
        """List all available checkpoints."""
        checkpoints = []
        for phase_id, commit in self.context.checkpoints.items():
            checkpoints.append({
                "phase_id": phase_id,
                "commit": commit,
            })
        return checkpoints

    def cleanup_checkpoints(self) -> Dict:
        """Cleanup old checkpoints from git history."""
        try:
            # Run git gc to clean up
            subprocess.run(
                ["git", "gc", "--aggressive"],
                cwd=self.project_dir,
                capture_output=True,
                timeout=60,
            )
            return {"success": True, "message": "Checkpoints cleaned up"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_rollback_possible(self) -> bool:
        """Verify that rollback is possible."""
        if not self.context.checkpoints:
            return False

        # Check if git is available and repo is valid
        try:
            result = subprocess.run(
                ["git", "status"],
                cwd=self.project_dir,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_rollback_plan(self, to_phase: str) -> Dict:
        """Get detailed rollback plan."""
        if to_phase not in self.context.checkpoints:
            return {"error": f"Phase {to_phase} not found"}

        checkpoint_commit = self.context.checkpoints[to_phase]
        
        # Get list of commits to be reverted
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"{checkpoint_commit}..HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            commits_to_revert = result.stdout.strip().split("\n")
        except Exception:
            commits_to_revert = []

        return {
            "to_phase": to_phase,
            "target_commit": checkpoint_commit,
            "commits_to_revert": commits_to_revert,
            "risk_level": "low" if len(commits_to_revert) < 10 else "medium",
        }
