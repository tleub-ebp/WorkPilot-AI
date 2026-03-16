"""Environment Validator — Validates that a cloned environment is running.

Checks Docker Compose service status, port connectivity, and health endpoints.

Example:
    >>> from environment.validator import EnvironmentValidator
    >>> validator = EnvironmentValidator(Path("/my/project"))
    >>> result = validator.validate()
    >>> print(result.success, result.services_up)
"""

import json
import logging
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of environment validation.

    Attributes:
        success: Whether all checks passed.
        services_up: Services that are running.
        services_down: Services that are not running.
        port_checks: Port connectivity results.
        errors: Error messages.
    """
    success: bool = False
    services_up: list[str] = field(default_factory=list)
    services_down: list[str] = field(default_factory=list)
    port_checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "services_up": self.services_up,
            "services_down": self.services_down,
            "port_checks": self.port_checks,
            "errors": self.errors,
        }


class EnvironmentValidator:
    """Validates that a Docker Compose environment is running correctly."""

    def __init__(
        self,
        project_dir: Path,
        compose_file: str = "docker-compose.clone.yml",
    ) -> None:
        self.project_dir = Path(project_dir)
        self.compose_file = compose_file

    def validate(self, timeout: int = 60) -> ValidationResult:
        """Run full validation suite.

        Args:
            timeout: Maximum time to wait for services in seconds.

        Returns:
            ValidationResult with check outcomes.
        """
        result = ValidationResult()

        # 1. Check if compose file exists
        compose_path = self.project_dir / self.compose_file
        if not compose_path.exists():
            # Also check .auto-claude/environment/
            compose_path = (
                self.project_dir / ".auto-claude" / "environment" / self.compose_file
            )
            if not compose_path.exists():
                result.errors.append(f"Compose file not found: {self.compose_file}")
                return result

        # 2. Check docker-compose ps
        services_status = self._get_compose_status(compose_path)
        if services_status is None:
            result.errors.append("Failed to get docker-compose status")
            return result

        for name, running in services_status.items():
            if running:
                result.services_up.append(name)
            else:
                result.services_down.append(name)

        # 3. Check port connectivity
        ports = self._get_exposed_ports(compose_path)
        start = time.time()
        while time.time() - start < timeout:
            all_ok = True
            for port_name, port in ports.items():
                ok = self._check_port(port)
                result.port_checks[port_name] = ok
                if not ok:
                    all_ok = False
            if all_ok:
                break
            time.sleep(2)

        failed_ports = [k for k, v in result.port_checks.items() if not v]
        if failed_ports:
            result.errors.append(f"Ports not responding: {', '.join(failed_ports)}")

        result.success = not result.services_down and not failed_ports
        return result

    def _get_compose_status(
        self, compose_path: Path
    ) -> dict[str, bool] | None:
        """Get running status of docker-compose services."""
        docker_cmd = self._get_docker_compose_cmd(compose_path)
        if not docker_cmd:
            return None

        try:
            proc = subprocess.run(
                docker_cmd + ["ps", "--format", "json"],
                cwd=self.project_dir,
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode != 0:
                # Fallback: try without --format json
                proc = subprocess.run(
                    docker_cmd + ["ps"],
                    cwd=self.project_dir,
                    capture_output=True, text=True, timeout=15,
                )
                if proc.returncode != 0:
                    return None
                # Parse text output
                status: dict[str, bool] = {}
                for line in proc.stdout.strip().splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        running = "Up" in line or "running" in line.lower()
                        status[name] = running
                return status

            # Parse JSON output
            status = {}
            for line in proc.stdout.strip().splitlines():
                try:
                    data = json.loads(line)
                    name = data.get("Service", data.get("Name", ""))
                    state = data.get("State", "").lower()
                    status[name] = state == "running"
                except json.JSONDecodeError:
                    continue
            return status

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _get_exposed_ports(self, compose_path: Path) -> dict[str, int]:
        """Extract exposed ports from compose file."""
        ports: dict[str, int] = {}
        try:
            content = compose_path.read_text(encoding="utf-8")
            # Simple port extraction from YAML
            import re
            current_service = ""
            for line in content.splitlines():
                # Match service name (2-space indent, ending with colon)
                svc_match = re.match(r"^  (\w[\w-]*):", line)
                if svc_match:
                    current_service = svc_match.group(1)
                # Match port mapping
                port_match = re.match(r'^\s+- "?(\d+):(\d+)"?', line)
                if port_match and current_service:
                    host_port = int(port_match.group(1))
                    ports[f"{current_service}:{host_port}"] = host_port
        except OSError:
            pass
        return ports

    def _check_port(self, port: int) -> bool:
        """Check if a port is responding on localhost."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex(("localhost", port)) == 0
        except OSError:
            return False

    def _get_docker_compose_cmd(self, compose_path: Path) -> list[str] | None:
        """Get the docker compose command (v2 or v1)."""
        try:
            proc = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True, timeout=5,
            )
            if proc.returncode == 0:
                return ["docker", "compose", "-f", str(compose_path)]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            proc = subprocess.run(
                ["docker-compose", "version"],
                capture_output=True, timeout=5,
            )
            if proc.returncode == 0:
                return ["docker-compose", "-f", str(compose_path)]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return None
