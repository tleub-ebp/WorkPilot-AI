#!/usr/bin/env python3
"""Orchestrator for the WorkPilot AI wiki automation.

Clones / pulls the wiki repo, runs the requested update step(s), commits and
pushes any resulting changes. Designed to be called from GitHub Actions.

Examples:
    # Deterministic refresh only (fast, no API cost)
    python scripts/wiki/sync_wiki.py --mode inventories

    # Narrative refresh + translation (release cadence, uses Claude)
    python scripts/wiki/sync_wiki.py --mode narrative
    python scripts/wiki/sync_wiki.py --mode full

Environment:
    GITHUB_TOKEN          required to push
    ANTHROPIC_API_KEY     required for narrative / translation modes
    WIKI_REPO             override wiki remote (default: derived from origin)
    GIT_USER_NAME         commit author (default: "WorkPilot Wiki Bot")
    GIT_USER_EMAIL        commit email (default: "noreply@workpilot.ai")
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check, text=True)


def detect_wiki_url(repo: Path) -> str:
    if env := os.environ.get("WIKI_REPO"):
        return env
    origin = subprocess.check_output(
        ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
        text=True,
    ).strip()
    if origin.endswith(".git"):
        return origin.replace(".git", ".wiki.git")
    return f"{origin}.wiki.git"


def clone_or_pull_wiki(wiki_url: str, workdir: Path) -> Path:
    wiki_dir = workdir / "wiki"
    if wiki_dir.is_dir():
        run(["git", "-C", str(wiki_dir), "pull", "--ff-only"])
    else:
        run(["git", "clone", wiki_url, str(wiki_dir)])
    return wiki_dir


def configure_git(wiki: Path) -> None:
    name = os.environ.get("GIT_USER_NAME", "WorkPilot Wiki Bot")
    email = os.environ.get("GIT_USER_EMAIL", "noreply@workpilot.ai")
    run(["git", "-C", str(wiki), "config", "user.name", name])
    run(["git", "-C", str(wiki), "config", "user.email", email])


def has_changes(wiki: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(wiki), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def commit_and_push(wiki: Path, message: str) -> None:
    run(["git", "-C", str(wiki), "add", "-A"])
    run(["git", "-C", str(wiki), "commit", "-m", message])
    for attempt in range(3):
        result = subprocess.run(
            ["git", "-C", str(wiki), "push"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout, end="")
            return
        stderr = result.stderr or ""
        print(stderr, end="")
        if "rejected" not in stderr and "fetch first" not in stderr and "non-fast-forward" not in stderr:
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, stderr)
        print(f"[retry {attempt + 1}/3] remote moved — pulling with rebase")
        run(["git", "-C", str(wiki), "pull", "--rebase"])
    raise RuntimeError("wiki push rejected 3 times in a row")


def step_inventories(repo: Path, wiki: Path) -> None:
    run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "generate_inventories.py"),
            "--repo", str(repo),
            "--wiki", str(wiki),
        ]
    )


def step_narrative(repo: Path, wiki: Path) -> None:
    run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "update_narrative.py"),
            "refresh-narrative",
            "--repo", str(repo),
            "--wiki", str(wiki),
        ]
    )


def step_translate(repo: Path, wiki: Path) -> None:
    run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "update_narrative.py"),
            "translate-fr",
            "--repo", str(repo),
            "--wiki", str(wiki),
        ]
    )


def step_translate_en(repo: Path, wiki: Path) -> None:
    run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "update_narrative.py"),
            "translate-en",
            "--repo", str(repo),
            "--wiki", str(wiki),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["inventories", "narrative", "translate", "translate-en", "full", "bootstrap"],
        required=True,
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/workpilot-wiki-sync"))
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    args.workdir.mkdir(parents=True, exist_ok=True)

    wiki_url = detect_wiki_url(repo)
    wiki = clone_or_pull_wiki(wiki_url, args.workdir.resolve())
    configure_git(wiki)

    commit_msgs: list[str] = []

    if args.mode in {"inventories", "full", "bootstrap"}:
        step_inventories(repo, wiki)
        commit_msgs.append("chore(wiki): refresh inventories")
    if args.mode in {"narrative", "full"}:
        step_narrative(repo, wiki)
        commit_msgs.append("chore(wiki): refresh narrative sections")
    if args.mode in {"translate-en", "bootstrap"}:
        step_translate_en(repo, wiki)
        commit_msgs.append("chore(wiki): bootstrap English translations from French")
    if args.mode in {"translate", "full", "bootstrap"}:
        step_translate(repo, wiki)
        commit_msgs.append("chore(wiki): update French translations")

    if not has_changes(wiki):
        print("No wiki changes to commit.")
        return 0

    message = "\n".join(commit_msgs) + "\n\nAuto-generated by scripts/wiki/sync_wiki.py"
    if args.no_push:
        print(f"--no-push set, skipping commit/push. Would commit:\n{message}")
        return 0

    commit_and_push(wiki, message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
