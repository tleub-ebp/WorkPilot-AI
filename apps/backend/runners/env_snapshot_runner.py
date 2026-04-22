"""
Environment Snapshot Runner
===========================

Captures a reproducible snapshot of a project's runtime environment:
tool versions (Node/Python/Git/OS), lockfile contents, environment
variables (secrets stripped), and git state (commit, branch, dirty
files).

Snapshots are stored under ``<projectPath>/.workpilot/env-snapshots/``,
one JSON file per snapshot keyed by id.

Commands
--------

``capture``  — build a new snapshot, write the JSON, return the object.
``list``     — return all snapshots (newest first).
``get``      — return a single snapshot.
``replay``   — rebuild a Dockerfile / flake.nix / shell script that
               reproduces the snapshot and return it as a string; does
               not execute.
``export``   — write the replay payload to disk as a file and return
               the path.

Output protocol
---------------

All commands print **one line of JSON** on stdout then exit. Errors go
to stderr plus ``{"error": "..."}`` on stdout with exit code 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SECRET_PATTERNS = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|KEY|AUTH|CREDENTIAL|PRIVATE)",
    re.IGNORECASE,
)

LOCKFILES = [
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "requirements.txt",
    "Cargo.lock",
    "go.sum",
    "composer.lock",
    "Gemfile.lock",
]


def _snapshots_dir(project_path: Path) -> Path:
    d = project_path / ".workpilot" / "env-snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        out = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or out.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def _tool_version(name: str, arg: str = "--version") -> str | None:
    exe = shutil.which(name)
    if not exe:
        return None
    out = _run_cmd([exe, arg])
    return out.splitlines()[0] if out else None


def _safe_env() -> dict[str, str]:
    safe: dict[str, str] = {}
    for k, v in os.environ.items():
        if SECRET_PATTERNS.search(k):
            safe[k] = "<redacted>"
        else:
            safe[k] = v
    return safe


def _hash_file(p: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _git_state(project_path: Path) -> dict[str, str | list[str]]:
    return {
        "commit": _run_cmd(["git", "rev-parse", "HEAD"], cwd=project_path),
        "branch": _run_cmd(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path
        ),
        "remote": _run_cmd(
            ["git", "config", "--get", "remote.origin.url"], cwd=project_path
        ),
        "dirty": _run_cmd(
            ["git", "status", "--porcelain"], cwd=project_path
        ).splitlines(),
    }


def _capture_lockfiles(project_path: Path) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []
    for name in LOCKFILES:
        p = project_path / name
        if p.is_file():
            entries.append(
                {
                    "name": name,
                    "sha256": _hash_file(p),
                    "size": str(p.stat().st_size),
                }
            )
    return entries


def _capture(project_path: Path, spec_id: str | None, label: str | None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    snap_id = (
        f"snap-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6]}"
    )

    snapshot = {
        "id": snap_id,
        "createdAt": now,
        "label": label or "",
        "specId": spec_id,
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "tools": {
            "node": _tool_version("node"),
            "npm": _tool_version("npm"),
            "pnpm": _tool_version("pnpm"),
            "yarn": _tool_version("yarn"),
            "python": _tool_version("python") or _tool_version("python3"),
            "uv": _tool_version("uv"),
            "git": _tool_version("git"),
            "docker": _tool_version("docker"),
            "dotnet": _tool_version("dotnet"),
            "go": _tool_version("go", "version"),
            "cargo": _tool_version("cargo"),
        },
        "lockfiles": _capture_lockfiles(project_path),
        "git": _git_state(project_path),
        "env": _safe_env(),
    }

    target = _snapshots_dir(project_path) / f"{snap_id}.json"
    target.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return snapshot


def _list(project_path: Path) -> list[dict]:
    d = _snapshots_dir(project_path)
    items: list[dict] = []
    for f in d.glob("snap-*.json"):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    items.sort(key=lambda s: s.get("createdAt", ""), reverse=True)
    return items


def _get(project_path: Path, snap_id: str) -> dict | None:
    p = _snapshots_dir(project_path) / f"{snap_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _replay_payload(snapshot: dict, fmt: str) -> str:
    tools = snapshot.get("tools", {})
    node = tools.get("node") or "node"
    python = tools.get("python") or "python"
    git = snapshot.get("git", {})
    commit = git.get("commit") or "HEAD"
    remote = git.get("remote") or "<remote-url>"

    if fmt == "dockerfile":
        return (
            f"# Reproduces snapshot {snapshot['id']} ({snapshot['createdAt']})\n"
            f"FROM ubuntu:24.04\n"
            f"# Tools at capture: node={node}, python={python}\n"
            f"RUN apt-get update && apt-get install -y curl git python3 python3-pip\n"
            f"RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs\n"
            f"WORKDIR /work\n"
            f"RUN git clone {remote} repo && cd repo && git checkout {commit}\n"
            f"WORKDIR /work/repo\n"
            f'CMD ["bash"]\n'
        )
    if fmt == "nix":
        return (
            f"# Reproduces snapshot {snapshot['id']}\n"
            "{ pkgs ? import <nixpkgs> {} }:\n"
            "pkgs.mkShell {\n"
            "  buildInputs = [ pkgs.nodejs_20 pkgs.python3 pkgs.git ];\n"
            f"  shellHook = ''\n"
            f'    echo "Snapshot {snapshot["id"]} — commit {commit}"\n'
            f"  '';\n"
            "}\n"
        )
    if fmt == "script":
        return (
            f"#!/usr/bin/env bash\n"
            f"# Replay snapshot {snapshot['id']}\n"
            f"set -euo pipefail\n"
            f"echo '— Expected tools —'\n"
            f"echo 'node : {node}'\n"
            f"echo 'python: {python}'\n"
            f"git checkout {commit}\n"
        )
    raise ValueError(f"Unknown replay format: {fmt}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Environment Snapshot Runner")
    parser.add_argument(
        "--command",
        required=True,
        choices=["capture", "list", "get", "replay", "export"],
    )
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--snap-id", default=None)
    parser.add_argument("--spec-id", default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--format", default="dockerfile", choices=["dockerfile", "nix", "script"]
    )
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(json.dumps({"error": f"Project not found: {project_path}"}), flush=True)
        sys.exit(1)

    try:
        if args.command == "capture":
            snap = _capture(project_path, args.spec_id, args.label)
            print(json.dumps({"snapshot": snap}), flush=True)
            return

        if args.command == "list":
            print(json.dumps({"snapshots": _list(project_path)}), flush=True)
            return

        if args.command == "get":
            if not args.snap_id:
                raise ValueError("--snap-id required for get")
            snap = _get(project_path, args.snap_id)
            if snap is None:
                raise FileNotFoundError(args.snap_id)
            print(json.dumps({"snapshot": snap}), flush=True)
            return

        if args.command in {"replay", "export"}:
            if not args.snap_id:
                raise ValueError("--snap-id required")
            snap = _get(project_path, args.snap_id)
            if snap is None:
                raise FileNotFoundError(args.snap_id)
            payload = _replay_payload(snap, args.format)
            if args.command == "replay":
                print(
                    json.dumps({"payload": payload, "format": args.format}), flush=True
                )
                return
            out_dir = _snapshots_dir(project_path) / "exports"
            out_dir.mkdir(parents=True, exist_ok=True)
            ext = {
                "dockerfile": "Dockerfile",
                "nix": "flake.nix",
                "script": "replay.sh",
            }
            filename = args.output or f"{snap['id']}.{ext[args.format]}"
            target = out_dir / filename
            target.write_text(payload, encoding="utf-8")
            print(
                json.dumps({"path": str(target), "format": args.format}),
                flush=True,
            )
            return
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
