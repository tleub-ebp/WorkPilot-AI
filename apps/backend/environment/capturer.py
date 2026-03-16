"""Environment Capturer — Captures environment configuration from various sources.

Reads docker-compose files, .env files, and running Docker containers to build
a structured ``EnvironmentCapture`` that can be reproduced locally.

Example:
    >>> from environment.capturer import EnvironmentCapturer
    >>> capturer = EnvironmentCapturer(Path("/my/project"))
    >>> capture = capturer.capture_from_compose()
    >>> capturer.save_capture(capture, Path(".auto-claude/environment"))
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that look like secrets in .env values
_SECRET_PATTERNS = re.compile(
    r"(password|secret|token|key|api_key|apikey|auth|credential|private)",
    re.IGNORECASE,
)


@dataclass
class ServiceCapture:
    """Captured configuration for a single service.

    Attributes:
        name: Service name.
        image: Docker image name.
        tag: Docker image tag.
        ports: Port mappings (host → container).
        environment: Environment variables.
        volumes: Volume mounts.
        depends_on: Service dependencies.
        health_check: Health check configuration.
        command: Override command.
    """
    name: str
    image: str = ""
    tag: str = "latest"
    ports: list[dict[str, int]] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    health_check: dict[str, Any] = field(default_factory=dict)
    command: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "image": self.image,
            "tag": self.tag,
            "ports": self.ports,
            "environment": self.environment,
            "volumes": self.volumes,
            "depends_on": self.depends_on,
            "health_check": self.health_check,
            "command": self.command,
        }


@dataclass
class EnvironmentCapture:
    """Full environment capture result.

    Attributes:
        project_name: Name of the captured project.
        services: Captured service configurations.
        env_vars: Project-level environment variables.
        networks: Docker network names.
        volumes: Named Docker volumes.
        source: Capture source (compose_file, running_containers, manual).
        captured_at: ISO timestamp of capture.
    """
    project_name: str
    services: list[ServiceCapture] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    networks: list[str] = field(default_factory=list)
    volumes: list[str] = field(default_factory=list)
    source: str = ""
    captured_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "project_name": self.project_name,
            "services": [s.to_dict() for s in self.services],
            "env_vars": self.env_vars,
            "networks": self.networks,
            "volumes": self.volumes,
            "source": self.source,
            "captured_at": self.captured_at,
        }


def _sanitize_env_value(key: str, value: str) -> str:
    """Replace secret-looking values with placeholders."""
    if _SECRET_PATTERNS.search(key):
        return "<REPLACE_ME>"
    return value


class EnvironmentCapturer:
    """Captures environment configuration from various sources."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)

    def capture_from_compose(
        self, compose_path: Path | None = None
    ) -> EnvironmentCapture:
        """Parse an existing docker-compose file into a structured capture.

        Args:
            compose_path: Path to docker-compose file. Auto-detected if None.

        Returns:
            EnvironmentCapture with parsed service configs.
        """
        if compose_path is None:
            compose_path = self._find_compose_file()

        if compose_path is None or not compose_path.exists():
            logger.warning("No docker-compose file found in %s", self.project_dir)
            return EnvironmentCapture(
                project_name=self.project_dir.name,
                source="compose_file",
                captured_at=datetime.now(timezone.utc).isoformat(),
            )

        services: list[ServiceCapture] = []
        networks: list[str] = []
        volumes: list[str] = []

        try:
            import yaml
            with open(compose_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            for name, config in data.get("services", {}).items():
                if not isinstance(config, dict):
                    continue
                services.append(self._parse_compose_service(name, config))

            networks = list(data.get("networks", {}).keys())
            volumes = list(data.get("volumes", {}).keys())

        except ImportError:
            # Fallback: basic parsing without pyyaml
            services = self._parse_compose_basic(compose_path)

        env_vars = self.capture_env_files()

        return EnvironmentCapture(
            project_name=self.project_dir.name,
            services=services,
            env_vars=env_vars,
            networks=networks,
            volumes=volumes,
            source="compose_file",
            captured_at=datetime.now(timezone.utc).isoformat(),
        )

    def capture_from_running_containers(
        self, prefix: str = ""
    ) -> EnvironmentCapture:
        """Capture config from currently running Docker containers.

        Args:
            prefix: Only include containers whose name starts with prefix.

        Returns:
            EnvironmentCapture from running containers.
        """
        services: list[ServiceCapture] = []

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                logger.warning("docker ps failed: %s", result.stderr.strip())
                return EnvironmentCapture(
                    project_name=self.project_dir.name,
                    source="running_containers",
                    captured_at=datetime.now(timezone.utc).isoformat(),
                )

            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                container_id, name, image = parts[0], parts[1], parts[2]
                if prefix and not name.startswith(prefix):
                    continue
                service = self._inspect_container(container_id, name, image)
                if service:
                    services.append(service)

        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("Docker not available: %s", exc)

        env_vars = self.capture_env_files()

        return EnvironmentCapture(
            project_name=self.project_dir.name,
            services=services,
            env_vars=env_vars,
            source="running_containers",
            captured_at=datetime.now(timezone.utc).isoformat(),
        )

    def capture_env_files(
        self, patterns: list[str] | None = None
    ) -> dict[str, str]:
        """Capture environment variables from .env files.

        Secrets are automatically sanitized (replaced with ``<REPLACE_ME>``).

        Args:
            patterns: File patterns to read. Defaults to common .env files.

        Returns:
            Dict of sanitized key-value pairs.
        """
        if patterns is None:
            patterns = [".env", ".env.example", ".env.local", ".env.development"]

        result: dict[str, str] = {}
        for pattern in patterns:
            env_path = self.project_dir / pattern
            if not env_path.exists():
                continue
            try:
                content = env_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        result[key] = _sanitize_env_value(key, value)
            except OSError:
                continue

        return result

    def save_capture(self, capture: EnvironmentCapture, output_dir: Path) -> Path:
        """Save capture to a JSON file.

        Args:
            capture: The environment capture to save.
            output_dir: Directory to write the capture file to.

        Returns:
            Path to the saved file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "environment_capture.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(capture.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("Environment capture saved to %s", output_file)
        return output_file

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_compose_file(self) -> Path | None:
        """Find docker-compose configuration file."""
        candidates = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
            "docker-compose.dev.yml",
            "docker-compose.dev.yaml",
        ]
        for candidate in candidates:
            path = self.project_dir / candidate
            if path.exists():
                return path
        return None

    def _parse_compose_service(
        self, name: str, config: dict[str, Any]
    ) -> ServiceCapture:
        """Parse a single service from compose YAML data."""
        image = config.get("image", "")
        tag = "latest"
        if ":" in image:
            image, tag = image.rsplit(":", 1)

        ports: list[dict[str, int]] = []
        for p in config.get("ports", []):
            port_str = str(p)
            if ":" in port_str:
                try:
                    host, container = port_str.split(":")[:2]
                    ports.append({"host": int(host), "container": int(container)})
                except (ValueError, IndexError):
                    pass

        environment: dict[str, str] = {}
        env_config = config.get("environment", {})
        if isinstance(env_config, dict):
            for k, v in env_config.items():
                environment[k] = _sanitize_env_value(k, str(v) if v is not None else "")
        elif isinstance(env_config, list):
            for item in env_config:
                if "=" in str(item):
                    k, _, v = str(item).partition("=")
                    environment[k] = _sanitize_env_value(k, v)

        volumes = [str(v) for v in config.get("volumes", [])]
        depends_on = list(config.get("depends_on", []))
        if isinstance(depends_on, dict):
            depends_on = list(depends_on.keys())

        health_check: dict[str, Any] = {}
        hc = config.get("healthcheck", {})
        if hc:
            health_check = {
                "test": hc.get("test", ""),
                "interval": hc.get("interval", ""),
                "timeout": hc.get("timeout", ""),
                "retries": hc.get("retries", 3),
            }

        command = ""
        cmd = config.get("command", "")
        if isinstance(cmd, list):
            command = " ".join(str(c) for c in cmd)
        elif cmd:
            command = str(cmd)

        return ServiceCapture(
            name=name,
            image=image,
            tag=tag,
            ports=ports,
            environment=environment,
            volumes=volumes,
            depends_on=depends_on,
            health_check=health_check,
            command=command,
        )

    def _parse_compose_basic(self, compose_path: Path) -> list[ServiceCapture]:
        """Basic compose parsing without pyyaml."""
        services: list[ServiceCapture] = []
        content = compose_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        in_services = False
        for line in lines:
            if line.strip() == "services:":
                in_services = True
                continue
            if in_services and line.startswith("  ") and not line.startswith("    "):
                name = line.strip().rstrip(":")
                if name:
                    services.append(ServiceCapture(name=name))
        return services

    def _inspect_container(
        self, container_id: str, name: str, image: str
    ) -> ServiceCapture | None:
        """Inspect a running container for its configuration."""
        try:
            result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return ServiceCapture(name=name, image=image)

            data = json.loads(result.stdout)
            if not data:
                return ServiceCapture(name=name, image=image)

            info = data[0]
            config = info.get("Config", {})
            network_settings = info.get("NetworkSettings", {})

            # Parse image and tag
            img = config.get("Image", image)
            tag = "latest"
            if ":" in img:
                img, tag = img.rsplit(":", 1)

            # Parse environment
            environment: dict[str, str] = {}
            for env_str in config.get("Env", []):
                if "=" in env_str:
                    k, _, v = env_str.partition("=")
                    environment[k] = _sanitize_env_value(k, v)

            # Parse ports
            ports: list[dict[str, int]] = []
            port_bindings = info.get("HostConfig", {}).get("PortBindings", {})
            for container_port, bindings in port_bindings.items():
                if bindings:
                    try:
                        host_port = int(bindings[0].get("HostPort", 0))
                        c_port = int(container_port.split("/")[0])
                        if host_port:
                            ports.append({"host": host_port, "container": c_port})
                    except (ValueError, IndexError):
                        pass

            # Parse volumes
            volumes = []
            for mount in info.get("Mounts", []):
                src = mount.get("Source", "")
                dst = mount.get("Destination", "")
                if src and dst:
                    volumes.append(f"{src}:{dst}")

            return ServiceCapture(
                name=name,
                image=img,
                tag=tag,
                ports=ports,
                environment=environment,
                volumes=volumes,
            )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to inspect container %s: %s", container_id, exc)
            return ServiceCapture(name=name, image=image)
