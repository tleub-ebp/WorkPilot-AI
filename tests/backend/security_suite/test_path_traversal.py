"""Path-traversal detection tests for ``anomaly_detector``.

We earlier replaced the naive ``".." in path or path.startswith("/etc/")``
check with a normalized prefix match against a broader set of sensitive
directories. These tests lock the hardened behavior down so a future
simplification can't silently regress it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[3] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from security.anomaly_detector import (  # noqa: E402
    AnomalyDetector,
    AnomalyType,
    EventType,
)


def _make_session():
    detector = AnomalyDetector()
    session = detector.start_session("test-task", agent_type="coder")
    return detector, session


@pytest.mark.parametrize(
    "path",
    [
        # Plain sensitive prefixes.
        "/etc/passwd",
        "/root/.ssh/id_rsa",
        "/proc/self/environ",
        "/sys/class",
        "/var/log/auth.log",
        "/boot/grub/grub.cfg",
        # Windows sensitive prefixes — case-insensitive.
        "C:/Windows/System32/config/SAM",
        "c:/WINDOWS/system32/config/SAM",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "C:/Program Files/SomeApp/config",
        "C:/ProgramData/ssh/ssh_host_rsa_key",
        # Path traversal segments that resolve into sensitive dirs.
        "src/../../etc/passwd",
        "src/..\\..\\etc\\passwd",
        "./foo/../../../etc/shadow",
        "a/b/../../etc/passwd",
        # Doubled slashes — normpath flattens them.
        "/etc//passwd",
        "/etc///passwd",
        # Parent-dir segment on its own (no resolution target) is still
        # considered a traversal attempt — see _check_path_traversal.
        "..",
        "src/../secret",
    ],
)
def test_sensitive_or_traversal_paths_are_flagged(path: str) -> None:
    detector, session = _make_session()
    detector.record_event(
        session.session_id,
        EventType.FILE_READ.value,
        {"path": path},
    )
    anomaly_types = {a.anomaly_type for a in session.anomalies}
    assert AnomalyType.PATH_TRAVERSAL_ATTEMPT.value in anomaly_types, (
        f"expected PATH_TRAVERSAL_ATTEMPT for {path!r}, got {anomaly_types}"
    )


@pytest.mark.parametrize(
    "path",
    [
        # Project-relative paths — the common case, must NOT flag.
        "src/main.py",
        "apps/frontend/src/App.tsx",
        "tests/conftest.py",
        # A relative path with a dot segment but no escape — not a traversal.
        "./src/main.py",
        # Windows-style relative path without sensitive prefix.
        "src\\main.py",
        "apps\\frontend\\src\\App.tsx",
        # Absolute path to user space is allowed (we only block system dirs).
        "/home/user/project/src/main.py",
        "/tmp/workpilot-test/output.txt",
    ],
)
def test_safe_paths_do_not_trigger(path: str) -> None:
    detector, session = _make_session()
    detector.record_event(
        session.session_id,
        EventType.FILE_READ.value,
        {"path": path},
    )
    anomaly_types = {a.anomaly_type for a in session.anomalies}
    assert AnomalyType.PATH_TRAVERSAL_ATTEMPT.value not in anomaly_types, (
        f"{path!r} should be safe, was flagged as traversal"
    )


def test_detection_applies_to_writes_not_just_reads() -> None:
    """A write into /etc must be caught too — reads are not the only vector."""
    detector, session = _make_session()
    detector.record_event(
        session.session_id,
        EventType.FILE_WRITE.value,
        {"path": "/etc/shadow"},
    )
    assert any(
        a.anomaly_type == AnomalyType.PATH_TRAVERSAL_ATTEMPT.value
        for a in session.anomalies
    )


def test_non_file_events_are_not_subjected_to_path_checks() -> None:
    """Record a command-execution event pointing at /etc — should not be
    picked up by the file-path checker (different detector is responsible)."""
    detector, session = _make_session()
    # An EventType that isn't FILE_READ / FILE_WRITE.
    detector.record_event(
        session.session_id,
        EventType.COMMAND_EXEC.value,
        {"path": "/etc/passwd"},
    )
    path_anomalies = [
        a
        for a in session.anomalies
        if a.anomaly_type == AnomalyType.PATH_TRAVERSAL_ATTEMPT.value
    ]
    assert path_anomalies == []
