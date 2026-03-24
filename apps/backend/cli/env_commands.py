"""CLI commands for Environment Cloner.

Provides capture, reproduce, and validate commands for environment cloning.
"""

from pathlib import Path


def handle_env_capture_command(project_dir: Path, source: str = "auto") -> None:
    """Capture environment configuration.

    Args:
        project_dir: Path to the project root.
        source: Capture source — ``'auto'``, ``'compose'``, or ``'containers'``.
    """
    from environment.capturer import EnvironmentCapturer

    capturer = EnvironmentCapturer(project_dir)
    print(f"Capturing environment from {project_dir}...")

    if source == "containers":
        capture = capturer.capture_from_running_containers()
    else:
        capture = capturer.capture_from_compose()
        if not capture.services and source == "auto":
            print("No compose file found, trying running containers...")
            capture = capturer.capture_from_running_containers()

    if not capture.services:
        print(
            "No services detected. Make sure you have a docker-compose file or running containers."
        )
        return

    output_dir = project_dir / ".auto-claude" / "environment"
    saved = capturer.save_capture(capture, output_dir)

    print(f"\nCaptured {len(capture.services)} services:")
    for svc in capture.services:
        image_info = f" ({svc.image}:{svc.tag})" if svc.image else ""
        ports_info = ""
        if svc.ports:
            ports_info = " ports=" + ",".join(
                f"{p['host']}:{p['container']}" for p in svc.ports
            )
        print(f"  - {svc.name}{image_info}{ports_info}")

    if capture.env_vars:
        print(f"\nCaptured {len(capture.env_vars)} environment variables")

    print(f"\nSaved to: {saved}")


def handle_env_reproduce_command(project_dir: Path) -> None:
    """Reproduce captured environment via Docker Compose.

    Args:
        project_dir: Path to the project root.
    """
    import json

    from environment.capturer import EnvironmentCapture, ServiceCapture
    from environment.generator import ComposeGenerator

    capture_file = (
        project_dir / ".auto-claude" / "environment" / "environment_capture.json"
    )
    if not capture_file.exists():
        print("No capture found. Run --env-capture first.")
        return

    with open(capture_file, encoding="utf-8") as f:
        data = json.load(f)

    services = [
        ServiceCapture(
            name=s.get("name", ""),
            image=s.get("image", ""),
            tag=s.get("tag", "latest"),
            ports=s.get("ports", []),
            environment=s.get("environment", {}),
            volumes=s.get("volumes", []),
            depends_on=s.get("depends_on", []),
            health_check=s.get("health_check", {}),
            command=s.get("command", ""),
        )
        for s in data.get("services", [])
    ]

    capture = EnvironmentCapture(
        project_name=data.get("project_name", ""),
        services=services,
        env_vars=data.get("env_vars", {}),
        networks=data.get("networks", []),
        volumes=data.get("volumes", []),
        source=data.get("source", ""),
        captured_at=data.get("captured_at", ""),
    )

    generator = ComposeGenerator(capture)
    output_dir = project_dir / ".auto-claude" / "environment"
    files = generator.write_all(output_dir)

    print("Generated files:")
    for f in files:
        print(f"  - {f}")
    print(f"\nTo start: docker compose -f {files[0]} --env-file {files[1]} up -d")


def handle_env_validate_command(project_dir: Path) -> None:
    """Validate that cloned environment is running.

    Args:
        project_dir: Path to the project root.
    """
    from environment.validator import EnvironmentValidator

    print("Validating environment...")
    validator = EnvironmentValidator(project_dir)
    result = validator.validate(timeout=30)

    if result.services_up:
        print(f"\nServices UP: {', '.join(result.services_up)}")
    if result.services_down:
        print(f"Services DOWN: {', '.join(result.services_down)}")
    if result.port_checks:
        print("\nPort checks:")
        for port, ok in result.port_checks.items():
            status = "OK" if ok else "FAIL"
            print(f"  {port}: {status}")
    if result.errors:
        print(f"\nErrors: {', '.join(result.errors)}")

    if result.success:
        print("\nValidation PASSED")
    else:
        print("\nValidation FAILED")
