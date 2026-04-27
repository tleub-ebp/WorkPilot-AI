"""Tests for the improved `AzDOClient.get_pr_diff`.

We don't hit Azure — we mock the underlying repos client. The point is
to confirm that the rewritten diff path produces a real unified-diff
output and falls back to a pseudo-diff on the documented failure modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from runners.azure_devops.azdo_client import AzDOClient


@dataclass
class _FakePRFile:
    path: str
    change_type: str = "edit"
    additions: int = 0
    deletions: int = 0


@dataclass
class _FakePRDetails:
    source_ref_name: str = "refs/heads/feature-branch"
    target_ref_name: str = "refs/heads/main"


def _make_client() -> AzDOClient:
    """Build an AzDOClient and inject a fully mocked repos client."""
    client = AzDOClient.__new__(AzDOClient)
    client.project_dir = None  # unused in these tests
    client.pat = "pat"
    client.organization_url = "https://dev.azure.com/x"
    client.project = "ProjectX"
    client.repository_id = "RepoX"
    client._repos_client = MagicMock()
    return client


class TestUnifiedDiff:
    def test_modified_file_produces_unified_diff(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [_FakePRFile(path="src/x.py")]
        repos.get_pull_request_details.return_value = _FakePRDetails()
        # First call (target/main) returns old content, second (source/feature) returns new.
        repos.get_file_content.side_effect = [
            "def f():\n    return 1\n",  # target = main
            "def f():\n    return 2\n",  # source = feature
        ]

        diff = client.get_pr_diff(pr_id=42)

        assert "--- a/src/x.py" in diff
        assert "+++ b/src/x.py" in diff
        # Real diff content, not just a comment.
        assert "-    return 1" in diff
        assert "+    return 2" in diff

    def test_added_file_uses_empty_target_side(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [
            _FakePRFile(path="new.py", change_type="add")
        ]
        repos.get_pull_request_details.return_value = _FakePRDetails()
        # Only the source side is fetched (target is short-circuited to "")
        repos.get_file_content.return_value = "print('hi')\n"

        diff = client.get_pr_diff(pr_id=1)
        assert "+print('hi')" in diff
        # `add` skips the target fetch, so get_file_content is called once
        assert repos.get_file_content.call_count == 1

    def test_deleted_file_uses_empty_source_side(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [
            _FakePRFile(path="old.py", change_type="delete")
        ]
        repos.get_pull_request_details.return_value = _FakePRDetails()
        repos.get_file_content.return_value = "print('bye')\n"

        diff = client.get_pr_diff(pr_id=1)
        assert "-print('bye')" in diff
        assert repos.get_file_content.call_count == 1


class TestFallbacks:
    def test_pseudo_diff_when_pr_details_fail(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [
            _FakePRFile(path="x.py", additions=3, deletions=1)
        ]
        repos.get_pull_request_details.side_effect = RuntimeError("API down")

        diff = client.get_pr_diff(pr_id=1)
        assert "# Change type: edit" in diff
        assert "# +3 additions" in diff
        assert "# -1 deletions" in diff

    def test_pseudo_diff_when_branches_missing(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [_FakePRFile(path="x.py")]
        # Returns details object but with empty refs
        repos.get_pull_request_details.return_value = _FakePRDetails(
            source_ref_name="", target_ref_name=""
        )

        diff = client.get_pr_diff(pr_id=1)
        assert "# Change type" in diff

    def test_pseudo_diff_per_file_when_content_fetch_fails(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [
            _FakePRFile(path="ok.py"),
            _FakePRFile(path="broken.py"),
        ]
        repos.get_pull_request_details.return_value = _FakePRDetails()

        # ok.py succeeds (and the contents differ so the diff isn't empty);
        # broken.py raises and triggers the per-file fallback.
        call_index = {"i": 0}

        def fake_content(*args, **kwargs):
            file_path = kwargs.get("file_path", "")
            if "broken.py" in file_path:
                raise RuntimeError("404")
            # Return alternating contents for ok.py so we get a real diff
            call_index["i"] += 1
            return f"x = {call_index['i']}\n"

        repos.get_file_content.side_effect = fake_content

        diff = client.get_pr_diff(pr_id=1)
        assert "ok.py" in diff
        # broken.py falls back to pseudo-diff
        assert "broken.py" in diff
        assert "# Change type" in diff

    def test_max_files_cap_emits_pseudo_diff_for_excess(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [
            _FakePRFile(path=f"f{i}.py") for i in range(5)
        ]
        repos.get_pull_request_details.return_value = _FakePRDetails()
        repos.get_file_content.return_value = "x = 1\n"

        diff = client.get_pr_diff(pr_id=1, max_files=2)
        # 2 real diffs + 3 pseudo-diff entries
        assert diff.count("# Change type") == 3

    def test_huge_file_falls_back(self) -> None:
        client = _make_client()
        repos = client._repos_client
        repos.get_pull_request_files.return_value = [_FakePRFile(path="huge.bin")]
        repos.get_pull_request_details.return_value = _FakePRDetails()
        repos.get_file_content.return_value = "x" * 1_000_000  # past max_file_bytes

        diff = client.get_pr_diff(pr_id=1, max_file_bytes=10_000)
        assert "# Change type" in diff
        # No actual diff lines since we fell back early
        assert "+xxx" not in diff


class TestRefStripping:
    def test_strip_ref_handles_heads_and_tags(self) -> None:
        assert AzDOClient._strip_ref("refs/heads/main") == "main"
        assert AzDOClient._strip_ref("refs/tags/v1.0") == "v1.0"
        assert AzDOClient._strip_ref("feature-x") == "feature-x"
        assert AzDOClient._strip_ref(None) is None
        assert AzDOClient._strip_ref("") is None

    def test_read_attr_handles_obj_dict_or_none(self) -> None:
        assert AzDOClient._read_attr(None, "x") is None
        assert AzDOClient._read_attr({"x": 1}, "x") == 1
        assert AzDOClient._read_attr({"x": 1}, "missing") is None
        obj: Any = type("T", (), {"x": 42})()
        assert AzDOClient._read_attr(obj, "x") == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
