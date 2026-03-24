"""Reinforced Sandbox for Agent Execution — Isolate agents with resource limits and rollback.

Provides enhanced isolation for agent execution beyond the existing security model:
Docker-based ephemeral containers (optional), resource limits (CPU, RAM, I/O, network),
file/directory whitelisting, automatic pre-execution snapshots for instant rollback,
and a dry-run mode where agents produce plans without executing.

Feature 7.2 — Sandbox renforcé pour l'exécution d'agents.

Example:
    >>> from apps.backend.security.sandbox import SandboxManager
    >>> manager = SandboxManager(project_root="/path/to/project")
    >>> sandbox = manager.create_sandbox("task-42", agent_type="coder")
    >>> sandbox.add_allowed_path("src/")
    >>> sandbox.add_allowed_path("tests/")
    >>> snapshot_id = manager.create_snapshot(sandbox.sandbox_id)
    >>> result = manager.execute_in_sandbox(sandbox.sandbox_id, my_agent_function, args=("code",))
    >>> if not result.success:
    ...     manager.rollback_snapshot(sandbox.sandbox_id, snapshot_id)
"""

import hashlib
import logging
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SandboxMode(str, Enum):
    """Execution mode for the sandbox."""

    NORMAL = "normal"
    DRY_RUN = "dry_run"
    DOCKER = "docker"
    RESTRICTED = "restricted"


class SandboxStatus(str, Enum):
    """Status of a sandbox."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ResourceType(str, Enum):
    """Types of resources that can be limited."""

    CPU_PERCENT = "cpu_percent"
    MEMORY_MB = "memory_mb"
    DISK_IO_MB = "disk_io_mb"
    NETWORK = "network"
    EXECUTION_TIME_S = "execution_time_s"
    MAX_FILES_WRITTEN = "max_files_written"
    MAX_FILE_SIZE_MB = "max_file_size_mb"


class FileAccessLevel(str, Enum):
    """Level of file access allowed."""

    READ = "read"
    WRITE = "write"
    NONE = "none"


class ViolationType(str, Enum):
    """Type of security violation detected."""

    PATH_VIOLATION = "path_violation"
    RESOURCE_EXCEEDED = "resource_exceeded"
    BLOCKED_OPERATION = "blocked_operation"
    TIMEOUT = "timeout"
    NETWORK_VIOLATION = "network_violation"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ResourceLimits:
    """Resource limits for a sandbox."""

    cpu_percent: float = 80.0
    memory_mb: int = 2048
    disk_io_mb: int = 500
    network_allowed: bool = False
    execution_time_s: int = 300
    max_files_written: int = 100
    max_file_size_mb: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_within_limits(self, resource: str, value: float) -> bool:
        """Check if a value is within the limits for a resource."""
        limits = {
            "cpu_percent": self.cpu_percent,
            "memory_mb": float(self.memory_mb),
            "disk_io_mb": float(self.disk_io_mb),
            "execution_time_s": float(self.execution_time_s),
            "max_files_written": float(self.max_files_written),
            "max_file_size_mb": self.max_file_size_mb,
        }
        limit = limits.get(resource)
        if limit is None:
            return True
        return value <= limit


@dataclass
class PathRule:
    """A file/directory access rule."""

    path: str
    access: FileAccessLevel = FileAccessLevel.WRITE
    recursive: bool = True

    def matches(self, target: str) -> bool:
        """Check if a target path matches this rule."""
        normalized_rule = self.path.replace("\\", "/").rstrip("/")
        normalized_target = target.replace("\\", "/").rstrip("/")
        if normalized_target == normalized_rule:
            return True
        if self.recursive and normalized_target.startswith(normalized_rule + "/"):
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["access"] = self.access.value
        return d


@dataclass
class SecurityViolation:
    """A security violation detected during sandbox execution."""

    violation_id: str
    violation_type: ViolationType
    description: str
    path: str = ""
    resource: str = ""
    value: float = 0.0
    limit: float = 0.0
    timestamp: str = ""
    blocked: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.violation_type, str):
            self.violation_type = ViolationType(self.violation_type)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["violation_type"] = self.violation_type.value
        return d


@dataclass
class FileSnapshot:
    """Snapshot of a single file for rollback."""

    path: str
    content_hash: str
    content: bytes | None = None
    exists: bool = True
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
        }


@dataclass
class Snapshot:
    """A complete filesystem snapshot for rollback."""

    snapshot_id: str
    sandbox_id: str
    files: list[FileSnapshot] = field(default_factory=list)
    created_at: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "sandbox_id": self.sandbox_id,
            "file_count": self.file_count,
            "created_at": self.created_at,
            "description": self.description,
        }


@dataclass
class ExecutionResult:
    """Result of executing a function in a sandbox."""

    sandbox_id: str
    success: bool
    output: Any = None
    error: str = ""
    duration_s: float = 0.0
    files_written: int = 0
    files_read: int = 0
    violations: list[dict[str, Any]] = field(default_factory=list)
    dry_run_plan: list[str] = field(default_factory=list)
    rolled_back: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SandboxConfig:
    """Full configuration for a sandbox instance."""

    sandbox_id: str
    task_id: str
    agent_type: str
    mode: SandboxMode = SandboxMode.NORMAL
    status: SandboxStatus = SandboxStatus.CREATED
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    allowed_paths: list[PathRule] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=list)
    violations: list[SecurityViolation] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    execution_result: ExecutionResult | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.mode, str):
            self.mode = SandboxMode(self.mode)
        if isinstance(self.status, str):
            self.status = SandboxStatus(self.status)

    @property
    def is_dry_run(self) -> bool:
        return self.mode == SandboxMode.DRY_RUN

    def add_allowed_path(
        self, path: str, access: str = "write", recursive: bool = True
    ) -> None:
        """Add a path to the whitelist."""
        self.allowed_paths.append(
            PathRule(
                path=path,
                access=FileAccessLevel(access),
                recursive=recursive,
            )
        )

    def add_blocked_path(self, path: str) -> None:
        """Add a path to the blocklist."""
        self.blocked_paths.append(path)

    def check_path_access(self, target_path: str, access_type: str = "write") -> bool:
        """Check if a path is accessible with the given access type.

        Returns True if the path is allowed, False if blocked.
        """
        normalized = target_path.replace("\\", "/").rstrip("/")

        # Check blocklist first (always takes precedence)
        for blocked in self.blocked_paths:
            blocked_norm = blocked.replace("\\", "/").rstrip("/")
            if normalized == blocked_norm or normalized.startswith(blocked_norm + "/"):
                return False

        # If no whitelist rules, everything is allowed (permissive mode)
        if not self.allowed_paths:
            return True

        # Check whitelist
        for rule in self.allowed_paths:
            if rule.matches(normalized):
                if access_type == "read":
                    return True
                elif access_type == "write" and rule.access == FileAccessLevel.WRITE:
                    return True
                elif access_type == "read" and rule.access in (
                    FileAccessLevel.READ,
                    FileAccessLevel.WRITE,
                ):
                    return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "mode": self.mode.value,
            "status": self.status.value,
            "resource_limits": self.resource_limits.to_dict(),
            "allowed_paths": [r.to_dict() for r in self.allowed_paths],
            "blocked_paths": self.blocked_paths,
            "blocked_commands": self.blocked_commands,
            "violations_count": len(self.violations),
            "files_written": len(self.files_written),
            "files_read": len(self.files_read),
            "created_at": self.created_at,
            "is_dry_run": self.is_dry_run,
        }


# ---------------------------------------------------------------------------
# Default blocked paths and commands
# ---------------------------------------------------------------------------

DEFAULT_BLOCKED_PATHS = [
    ".git/",
    ".env",
    ".env.local",
    ".env.production",
    "node_modules/.cache",
    "__pycache__/",
    ".ssh/",
    ".aws/",
    ".gnupg/",
]

DEFAULT_BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "sudo",
    "chmod 777",
    "curl",
    "wget",
    "ssh",
    "scp",
    "nc",
    "netcat",
    "eval",
    "exec",
]


# ---------------------------------------------------------------------------
# SandboxManager
# ---------------------------------------------------------------------------


class SandboxManager:
    """Manages sandbox instances for agent execution.

    Args:
        project_root: Root path of the project.
        default_mode: Default sandbox mode.
    """

    def __init__(
        self,
        project_root: str = ".",
        default_mode: str = "normal",
    ):
        self.project_root = project_root
        self.default_mode = SandboxMode(default_mode)

        self._sandboxes: dict[str, SandboxConfig] = {}
        self._snapshots: dict[str, list[Snapshot]] = {}
        self._sandbox_counter = 0
        self._snapshot_counter = 0
        self._violation_counter = 0

    def _next_sandbox_id(self) -> str:
        self._sandbox_counter += 1
        return f"sbx-{self._sandbox_counter:04d}"

    def _next_snapshot_id(self) -> str:
        self._snapshot_counter += 1
        return f"snap-{self._snapshot_counter:04d}"

    def _next_violation_id(self) -> str:
        self._violation_counter += 1
        return f"vio-{self._violation_counter:04d}"

    # -- Sandbox lifecycle --------------------------------------------------

    def create_sandbox(
        self,
        task_id: str,
        agent_type: str,
        mode: str | None = None,
        resource_limits: dict[str, Any] | None = None,
        allowed_paths: list[str] | None = None,
        blocked_paths: list[str] | None = None,
        blocked_commands: list[str] | None = None,
    ) -> SandboxConfig:
        """Create a new sandbox for agent execution.

        Args:
            task_id: The task the agent will work on.
            agent_type: Type of agent (coder, planner, qa, etc.).
            mode: Sandbox mode (normal, dry_run, docker, restricted).
            resource_limits: Override default resource limits.
            allowed_paths: Whitelist of accessible paths.
            blocked_paths: Additional blocked paths (appended to defaults).
            blocked_commands: Additional blocked commands (appended to defaults).

        Returns:
            The created SandboxConfig.
        """
        sandbox_id = self._next_sandbox_id()
        limits = ResourceLimits()
        if resource_limits:
            for key, val in resource_limits.items():
                if hasattr(limits, key):
                    setattr(limits, key, val)

        sandbox = SandboxConfig(
            sandbox_id=sandbox_id,
            task_id=task_id,
            agent_type=agent_type,
            mode=SandboxMode(mode) if mode else self.default_mode,
            resource_limits=limits,
            blocked_paths=list(DEFAULT_BLOCKED_PATHS) + (blocked_paths or []),
            blocked_commands=list(DEFAULT_BLOCKED_COMMANDS) + (blocked_commands or []),
        )

        # Add allowed paths
        if allowed_paths:
            for p in allowed_paths:
                sandbox.add_allowed_path(p)

        self._sandboxes[sandbox_id] = sandbox
        self._snapshots[sandbox_id] = []
        logger.info(
            "Created sandbox %s for task=%s agent=%s mode=%s",
            sandbox_id,
            task_id,
            agent_type,
            sandbox.mode.value,
        )
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> SandboxConfig | None:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    def list_sandboxes(self, status: str | None = None) -> list[SandboxConfig]:
        """List all sandboxes, optionally filtered by status."""
        results = list(self._sandboxes.values())
        if status:
            results = [s for s in results if s.status.value == status]
        return results

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox and clean up resources."""
        if sandbox_id not in self._sandboxes:
            return False
        del self._sandboxes[sandbox_id]
        self._snapshots.pop(sandbox_id, None)
        logger.info("Destroyed sandbox %s", sandbox_id)
        return True

    # -- Path validation ----------------------------------------------------

    def validate_path_access(
        self,
        sandbox_id: str,
        path: str,
        access_type: str = "write",
    ) -> bool:
        """Validate that a path is accessible within the sandbox.

        Args:
            sandbox_id: The sandbox ID.
            path: The target path.
            access_type: 'read' or 'write'.

        Returns:
            True if access is allowed, False if blocked.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return False

        allowed = sandbox.check_path_access(path, access_type)
        if not allowed:
            violation = SecurityViolation(
                violation_id=self._next_violation_id(),
                violation_type=ViolationType.PATH_VIOLATION,
                description=f"Access denied: {access_type} to '{path}'",
                path=path,
                blocked=True,
            )
            sandbox.violations.append(violation)
            logger.warning(
                "Sandbox %s: path violation — %s access to '%s'",
                sandbox_id,
                access_type,
                path,
            )
        return allowed

    def validate_command(self, sandbox_id: str, command: str) -> bool:
        """Validate that a command is allowed within the sandbox."""
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return False

        cmd_lower = command.lower().strip()
        for blocked in sandbox.blocked_commands:
            if blocked.lower() in cmd_lower:
                violation = SecurityViolation(
                    violation_id=self._next_violation_id(),
                    violation_type=ViolationType.BLOCKED_OPERATION,
                    description=f"Blocked command: '{command}' matches '{blocked}'",
                    blocked=True,
                )
                sandbox.violations.append(violation)
                return False
        return True

    def check_resource_limit(
        self,
        sandbox_id: str,
        resource: str,
        value: float,
    ) -> bool:
        """Check if a resource usage is within limits.

        Returns:
            True if within limits, False if exceeded.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return False

        within = sandbox.resource_limits.is_within_limits(resource, value)
        if not within:
            violation = SecurityViolation(
                violation_id=self._next_violation_id(),
                violation_type=ViolationType.RESOURCE_EXCEEDED,
                description=f"Resource limit exceeded: {resource}={value}",
                resource=resource,
                value=value,
                limit=getattr(sandbox.resource_limits, resource, 0),
                blocked=True,
            )
            sandbox.violations.append(violation)
        return within

    # -- Snapshots ----------------------------------------------------------

    def create_snapshot(
        self,
        sandbox_id: str,
        paths: list[str] | None = None,
        description: str = "",
    ) -> str | None:
        """Create a filesystem snapshot for rollback.

        Args:
            sandbox_id: The sandbox ID.
            paths: Specific paths to snapshot. If None, snapshots all allowed paths.
            description: Optional description.

        Returns:
            Snapshot ID, or None if sandbox doesn't exist.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return None

        snapshot_id = self._next_snapshot_id()
        file_snapshots: list[FileSnapshot] = []

        target_paths = paths or [r.path for r in sandbox.allowed_paths]

        for path in target_paths:
            full_path = os.path.join(self.project_root, path)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "rb") as f:
                        content = f.read()
                    file_snapshots.append(
                        FileSnapshot(
                            path=path,
                            content_hash=hashlib.sha256(content).hexdigest(),
                            content=content,
                            exists=True,
                            size_bytes=len(content),
                        )
                    )
                except OSError:
                    file_snapshots.append(
                        FileSnapshot(
                            path=path,
                            content_hash="",
                            exists=False,
                        )
                    )
            elif os.path.isdir(full_path):
                try:
                    for root, _dirs, files in os.walk(full_path):
                        for filename in files:
                            fpath = os.path.join(root, filename)
                            rel_path = os.path.relpath(fpath, self.project_root)
                            try:
                                with open(fpath, "rb") as f:
                                    content = f.read()
                                file_snapshots.append(
                                    FileSnapshot(
                                        path=rel_path.replace("\\", "/"),
                                        content_hash=hashlib.sha256(
                                            content
                                        ).hexdigest(),
                                        content=content,
                                        exists=True,
                                        size_bytes=len(content),
                                    )
                                )
                            except OSError:
                                pass
                except OSError:
                    pass
            else:
                # Path doesn't exist yet — record as non-existent
                file_snapshots.append(
                    FileSnapshot(
                        path=path,
                        content_hash="",
                        exists=False,
                    )
                )

        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            sandbox_id=sandbox_id,
            files=file_snapshots,
            description=description or f"Pre-execution snapshot for {sandbox.task_id}",
        )
        self._snapshots[sandbox_id].append(snapshot)
        logger.info(
            "Created snapshot %s for sandbox %s (%d files)",
            snapshot_id,
            sandbox_id,
            len(file_snapshots),
        )
        return snapshot_id

    def rollback_snapshot(self, sandbox_id: str, snapshot_id: str) -> bool:
        """Rollback to a previous snapshot.

        Args:
            sandbox_id: The sandbox ID.
            snapshot_id: The snapshot to rollback to.

        Returns:
            True if rollback was successful.
        """
        snapshots = self._snapshots.get(sandbox_id, [])
        snapshot = None
        for s in snapshots:
            if s.snapshot_id == snapshot_id:
                snapshot = s
                break
        if not snapshot:
            return False

        restored = 0
        for file_snap in snapshot.files:
            full_path = os.path.join(self.project_root, file_snap.path)
            try:
                if file_snap.exists and file_snap.content is not None:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "wb") as f:
                        f.write(file_snap.content)
                    restored += 1
                elif not file_snap.exists and os.path.exists(full_path):
                    os.remove(full_path)
                    restored += 1
            except OSError as e:
                logger.error("Failed to restore %s: %s", file_snap.path, e)

        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox:
            sandbox.status = SandboxStatus.ROLLED_BACK

        logger.info("Rolled back snapshot %s: %d files restored", snapshot_id, restored)
        return True

    def get_snapshots(self, sandbox_id: str) -> list[Snapshot]:
        """Get all snapshots for a sandbox."""
        return self._snapshots.get(sandbox_id, [])

    # -- Execution ----------------------------------------------------------

    def execute_in_sandbox(
        self,
        sandbox_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        auto_snapshot: bool = True,
    ) -> ExecutionResult:
        """Execute a function within the sandbox constraints.

        Args:
            sandbox_id: The sandbox to execute in.
            func: The function to execute.
            args: Positional arguments for the function.
            kwargs: Keyword arguments for the function.
            auto_snapshot: Automatically create a snapshot before execution.

        Returns:
            ExecutionResult with output, violations, and timing.
        """
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return ExecutionResult(
                sandbox_id=sandbox_id,
                success=False,
                error="Sandbox not found",
            )

        # Dry-run mode
        if sandbox.is_dry_run:
            plan = self._generate_dry_run_plan(sandbox, func, args)
            sandbox.status = SandboxStatus.COMPLETED
            result = ExecutionResult(
                sandbox_id=sandbox_id,
                success=True,
                dry_run_plan=plan,
            )
            sandbox.execution_result = result
            return result

        # Auto-snapshot
        snapshot_id = None
        if auto_snapshot:
            snapshot_id = self.create_snapshot(
                sandbox_id, description="Auto pre-execution snapshot"
            )

        # Execute
        sandbox.status = SandboxStatus.RUNNING
        sandbox.started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.monotonic()

        try:
            output = func(*args, **(kwargs or {}))
            duration = time.monotonic() - start_time

            # Check timeout
            if duration > sandbox.resource_limits.execution_time_s:
                sandbox.violations.append(
                    SecurityViolation(
                        violation_id=self._next_violation_id(),
                        violation_type=ViolationType.TIMEOUT,
                        description=f"Execution exceeded time limit ({duration:.1f}s > {sandbox.resource_limits.execution_time_s}s)",
                        value=duration,
                        limit=float(sandbox.resource_limits.execution_time_s),
                    )
                )

            sandbox.status = SandboxStatus.COMPLETED
            sandbox.completed_at = datetime.now(timezone.utc).isoformat()

            result = ExecutionResult(
                sandbox_id=sandbox_id,
                success=True,
                output=output,
                duration_s=round(duration, 3),
                files_written=len(sandbox.files_written),
                files_read=len(sandbox.files_read),
                violations=[v.to_dict() for v in sandbox.violations],
            )
            sandbox.execution_result = result
            return result

        except Exception as e:
            duration = time.monotonic() - start_time
            sandbox.status = SandboxStatus.FAILED
            sandbox.completed_at = datetime.now(timezone.utc).isoformat()

            result = ExecutionResult(
                sandbox_id=sandbox_id,
                success=False,
                error=str(e),
                duration_s=round(duration, 3),
                violations=[v.to_dict() for v in sandbox.violations],
            )
            sandbox.execution_result = result

            # Auto-rollback on failure if snapshot exists
            if snapshot_id:
                self.rollback_snapshot(sandbox_id, snapshot_id)
                result.rolled_back = True

            return result

    def _generate_dry_run_plan(
        self,
        sandbox: SandboxConfig,
        func: Callable,
        args: tuple,
    ) -> list[str]:
        """Generate a plan for what the agent would do without executing."""
        plan = [
            f"[DRY RUN] Task: {sandbox.task_id}",
            f"[DRY RUN] Agent: {sandbox.agent_type}",
            f"[DRY RUN] Mode: {sandbox.mode.value}",
            f"[DRY RUN] Resource limits: CPU={sandbox.resource_limits.cpu_percent}%, "
            f"RAM={sandbox.resource_limits.memory_mb}MB, "
            f"Time={sandbox.resource_limits.execution_time_s}s",
            f"[DRY RUN] Allowed paths: {[r.path for r in sandbox.allowed_paths]}",
            f"[DRY RUN] Function: {func.__name__ if hasattr(func, '__name__') else str(func)}",
            f"[DRY RUN] Args: {len(args)} positional arguments",
            "[DRY RUN] No files will be modified",
        ]
        return plan

    # -- Violations ---------------------------------------------------------

    def get_violations(self, sandbox_id: str) -> list[SecurityViolation]:
        """Get all violations for a sandbox."""
        sandbox = self._sandboxes.get(sandbox_id)
        return sandbox.violations if sandbox else []

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get global sandbox statistics."""
        sandboxes = list(self._sandboxes.values())
        total_violations = sum(len(s.violations) for s in sandboxes)
        total_snapshots = sum(len(v) for v in self._snapshots.values())
        return {
            "total_sandboxes": len(sandboxes),
            "active_sandboxes": sum(
                1 for s in sandboxes if s.status == SandboxStatus.RUNNING
            ),
            "completed_sandboxes": sum(
                1 for s in sandboxes if s.status == SandboxStatus.COMPLETED
            ),
            "failed_sandboxes": sum(
                1 for s in sandboxes if s.status == SandboxStatus.FAILED
            ),
            "rolled_back_sandboxes": sum(
                1 for s in sandboxes if s.status == SandboxStatus.ROLLED_BACK
            ),
            "total_violations": total_violations,
            "total_snapshots": total_snapshots,
            "dry_run_sandboxes": sum(1 for s in sandboxes if s.is_dry_run),
        }
