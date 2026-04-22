"""
Offline-Mode Runner
===================

Powers the offline-first routing dashboard. It introspects the local
environment for offline-capable tooling (Ollama, Llama.cpp, lm-studio)
and reads/writes a JSON policy file at
``<projectPath>/.workpilot/offline-mode.json`` describing the task
routing: which task type maps to which model, whether airgap-strict is
enabled, etc.

Commands
--------

``status``       — detect local runtimes + list installed models.
``list-models``  — same as status but focused on the model list (same
                   JSON shape, `models` key).
``get-policy``   — read the current routing policy.
``set-policy``   — write a new routing policy (supplied via --policy-json).
``report``       — audit of last N routing decisions (from the
                   policy's `history` array).

Output: one JSON object on stdout per invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCAN_CACHE_TTL_SECONDS = 900  # 15 minutes

KNOWN_CLOUD_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-3-7-sonnet-latest",
        "claude-3-5-haiku-latest",
    ],
    "openai": [
        "gpt-5",
        "gpt-5-mini",
        "gpt-4o",
        "gpt-4o-mini",
        "o3",
        "o3-mini",
    ],
    "zai": [
        "glm-4.6",
        "glm-4.5-air",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ],
    "mistral": [
        "mistral-large-latest",
        "mistral-small-latest",
        "codestral-latest",
    ],
}

DEFAULT_POLICY: dict = {
    "version": 1,
    "airgapStrict": False,
    "defaultProvider": "anthropic",
    "routing": {
        "commit_message": {"provider": "ollama", "model": "qwen2.5-coder:1.5b"},
        "summary": {"provider": "ollama", "model": "qwen2.5-coder:1.5b"},
        "triage": {"provider": "ollama", "model": "qwen2.5-coder:1.5b"},
        "planner": {"provider": "anthropic", "model": "claude-opus-4-7"},
        "coder": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
        "qa_reviewer": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    },
    "history": [],
}


def _policy_path(project_path: Path) -> Path:
    return project_path / ".workpilot" / "offline-mode.json"


def _load_policy(project_path: Path) -> dict:
    p = _policy_path(project_path)
    if not p.exists():
        return dict(DEFAULT_POLICY)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_POLICY)


def _save_policy(project_path: Path, policy: dict) -> None:
    p = _policy_path(project_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(policy, indent=2), encoding="utf-8")


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=8, check=False
        )
        return out.stdout.strip() or out.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def _detect_ollama() -> dict:
    exe = shutil.which("ollama")
    if not exe:
        return {"available": False, "models": []}
    raw = _run([exe, "list"])
    models: list[dict] = []
    # Parse "NAME ID SIZE MODIFIED" table, skipping header.
    for line in raw.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        models.append({"name": parts[0], "size": parts[2] if len(parts) > 2 else ""})
    return {"available": True, "models": models, "exe": exe}


def _detect_llama_cpp() -> dict:
    for name in ("llama", "llama-cli", "llama-server", "llamafile"):
        exe = shutil.which(name)
        if exe:
            return {"available": True, "exe": exe, "name": name}
    return {"available": False}


def _detect_lm_studio() -> dict:
    for name in ("lms", "lm-studio"):
        exe = shutil.which(name)
        if exe:
            models: list[dict] = []
            if name == "lms":
                raw = _run([exe, "ls"])
                # lms ls prints a table — the model id is usually first column.
                for line in raw.splitlines():
                    line = line.strip()
                    if not line or line.lower().startswith(("name", "path", "---")):
                        continue
                    parts = line.split()
                    if parts:
                        models.append({"name": parts[0]})
            return {"available": True, "exe": exe, "models": models}
    return {"available": False, "models": []}


def _detect_llama_cpp_models() -> list[dict]:
    """Scan known llama.cpp model locations for .gguf files."""
    candidates: list[Path] = []
    env_dir = os.environ.get("LLAMA_MODELS")
    if env_dir:
        candidates.append(Path(env_dir))
    home = Path.home()
    candidates.extend(
        [
            home / ".cache" / "llama.cpp",
            home / ".cache" / "lm-studio" / "models",
            home / "models",
            home / ".local" / "share" / "llama.cpp",
        ]
    )
    seen: set[str] = set()
    models: list[dict] = []
    for root in candidates:
        if not root.exists() or not root.is_dir():
            continue
        try:
            for p in root.rglob("*.gguf"):
                key = p.name.lower()
                if key in seen:
                    continue
                seen.add(key)
                models.append({"name": p.stem, "path": str(p)})
                if len(models) >= 50:
                    return models
        except (OSError, PermissionError):
            continue
    return models


def _cache_path(project_path: Path) -> Path:
    return project_path / ".workpilot" / "offline-mode-cache.json"


def _scan_models(project_path: Path, force: bool = False) -> dict:
    cache_file = _cache_path(project_path)
    now = datetime.now(timezone.utc)
    if not force and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(cached["cachedAt"])
            age = (now - cached_at).total_seconds()
            if age < SCAN_CACHE_TTL_SECONDS:
                cached["fromCache"] = True
                cached["ageSeconds"] = int(age)
                return cached
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass

    ollama = _detect_ollama()
    lm_studio = _detect_lm_studio()
    llama_cpp = _detect_llama_cpp()
    llama_models = (
        _detect_llama_cpp_models() if llama_cpp.get("available") or True else []
    )

    providers: dict[str, list[str]] = {
        provider: list(models) for provider, models in KNOWN_CLOUD_MODELS.items()
    }
    providers["ollama"] = [m["name"] for m in ollama.get("models", [])]
    providers["lm-studio"] = [m["name"] for m in lm_studio.get("models", [])]
    providers["llama-cpp"] = [m["name"] for m in llama_models]

    result = {
        "cachedAt": now.isoformat(),
        "ttlSeconds": SCAN_CACHE_TTL_SECONDS,
        "providers": providers,
        "local": {
            "ollama": ollama.get("available", False),
            "lmStudio": lm_studio.get("available", False),
            "llamaCpp": llama_cpp.get("available", False),
        },
        "fromCache": False,
        "ageSeconds": 0,
    }

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except OSError:
        pass

    return result


def _status() -> dict:
    ollama = _detect_ollama()
    llama_cpp = _detect_llama_cpp()
    lm_studio = _detect_lm_studio()
    local_models = [f"ollama:{m['name']}" for m in ollama.get("models", [])]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtimes": {
            "ollama": ollama,
            "llamaCpp": llama_cpp,
            "lmStudio": lm_studio,
        },
        "localModels": local_models,
        "offlineReady": any(
            [
                ollama.get("available"),
                llama_cpp.get("available"),
                lm_studio.get("available"),
            ]
        ),
    }


def _report(project_path: Path) -> dict:
    policy = _load_policy(project_path)
    history = policy.get("history", [])
    counts: dict[str, int] = {}
    for entry in history:
        provider = entry.get("provider", "unknown")
        counts[provider] = counts.get(provider, 0) + 1
    total = sum(counts.values()) or 1
    mix = {k: round(v / total, 3) for k, v in counts.items()}
    return {
        "total": sum(counts.values()),
        "providers": counts,
        "mix": mix,
        "history": history[-50:],
        "confidentialityLevel": (
            "local"
            if counts and set(counts) <= {"ollama", "llama-cpp", "lm-studio", "local"}
            else ("mixed" if counts else "unknown")
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Mode Runner")
    parser.add_argument(
        "--command",
        required=True,
        choices=[
            "status",
            "list-models",
            "scan-models",
            "get-policy",
            "set-policy",
            "report",
        ],
    )
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--policy-json", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(json.dumps({"error": f"Project not found: {project_path}"}), flush=True)
        sys.exit(1)

    try:
        if args.command in {"status", "list-models"}:
            print(json.dumps(_status()), flush=True)
            return

        if args.command == "scan-models":
            print(json.dumps(_scan_models(project_path, force=args.force)), flush=True)
            return

        if args.command == "get-policy":
            print(json.dumps({"policy": _load_policy(project_path)}), flush=True)
            return

        if args.command == "set-policy":
            if not args.policy_json:
                raise ValueError("--policy-json is required")
            new_policy = json.loads(args.policy_json)
            if not isinstance(new_policy, dict):
                raise ValueError("policy must be a JSON object")
            _save_policy(project_path, new_policy)
            print(json.dumps({"policy": new_policy}), flush=True)
            return

        if args.command == "report":
            print(json.dumps(_report(project_path)), flush=True)
            return
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
