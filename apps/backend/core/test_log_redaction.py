"""Tests for the global log redaction filter."""

from __future__ import annotations

import io
import logging
import os
import re

import pytest
from core.log_redaction import (
    RedactingFilter,
    install_global_redaction,
    reset_for_tests,
)


@pytest.fixture(autouse=True)
def _clean_root() -> None:
    # Snapshot + restore the root logger's handlers/filters so we don't
    # interfere with pytest's own caplog/streamhandler.
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_filters = list(root.filters)
    saved_level = root.level
    root.handlers = []
    root.filters = []
    reset_for_tests()
    yield
    reset_for_tests()
    root.handlers = saved_handlers
    root.filters = saved_filters
    root.level = saved_level


def _make_logger() -> tuple[logging.Logger, io.StringIO]:
    """Spin up an isolated logger writing to a StringIO so we can assert.

    The handler is attached to the **root** logger so the global redaction
    filter (which the install function attaches to root + root handlers)
    actually fires. We capture-then-detach in a finally block via the
    autouse fixture's reset_for_tests().
    """
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    logger = logging.getLogger(f"test_{id(buf)}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    return logger, buf


class TestPatternRedaction:
    def test_anthropic_key_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("key=sk-ant-api03-AbCdEf1234567890zzzzzzzzzzzzzzzz")
        out = buf.getvalue()
        assert "AbCdEf1234567890" not in out
        assert "sk-ant-[REDACTED]" in out

    def test_openai_key_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("openai key sk-proj-1234567890abcdefghijklmnop1234567890")
        out = buf.getvalue()
        assert "1234567890abcdef" not in out
        assert "sk-[REDACTED]" in out

    def test_github_pat_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("auth: ghp_abcdefghijklmnopqrstuvwxyz0123456789")
        out = buf.getvalue()
        assert "abcdefghijklmnop" not in out
        assert "gh*_[REDACTED]" in out

    def test_jwt_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        logger.info(f"received {jwt}")
        out = buf.getvalue()
        assert "SflKxwRJSMeKKF2QT" not in out
        assert "[JWT_REDACTED]" in out

    def test_aws_access_key_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
        out = buf.getvalue()
        assert "AKIAIOSFODNN7EXAMPLE" not in out
        assert "AWS_KEY_[REDACTED]" in out

    def test_bearer_token_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("Authorization: Bearer abc.def.ghi-jkl_mnopqrst1234567890")
        out = buf.getvalue()
        assert "abc.def.ghi-jkl_mnopqrst" not in out
        assert "[REDACTED]" in out

    def test_generic_secret_assignment_redacted(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info('config: api_key="myverysecretvalue1234"')
        out = buf.getvalue()
        assert "myverysecretvalue1234" not in out
        assert "[REDACTED]" in out


class TestSafeBehaviour:
    def test_clean_message_passes_through(self) -> None:
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("nothing sensitive here, just a regular log")
        assert "nothing sensitive here, just a regular log" in buf.getvalue()

    def test_filter_does_not_drop_records_on_error(self) -> None:
        # Force a record whose .getMessage() raises — the filter must
        # still return True (don't drop the record).
        install_global_redaction()
        logger, buf = _make_logger()

        # Format string with one %s but zero args → render error.
        logger.handle(
            logging.LogRecord(
                name="x",
                level=logging.INFO,
                pathname="x",
                lineno=1,
                msg="value=%s",
                args=(),  # missing arg
                exc_info=None,
            )
        )
        # The record should reach the buffer (formatted as best as Python can).
        assert buf.getvalue() != ""

    def test_install_is_idempotent(self) -> None:
        a = install_global_redaction()
        b = install_global_redaction()
        assert a is b
        # Only one filter on the root logger.
        root = logging.getLogger()
        count = sum(1 for f in root.filters if isinstance(f, RedactingFilter))
        assert count == 1


class TestEnvVarPatterns:
    def test_env_value_redacted_when_var_name_looks_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Set an env var BEFORE installing the filter so it gets snapshotted.
        monkeypatch.setenv("DEMO_API_KEY", "myverysecretenvvalue1234")
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("connecting with myverysecretenvvalue1234")
        out = buf.getvalue()
        assert "myverysecretenvvalue1234" not in out
        assert "[ENV:DEMO_API_KEY_REDACTED]" in out

    def test_short_env_values_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 11-char value — below the 12-char floor → not added to patterns.
        monkeypatch.setenv("SOMETHING_TOKEN", "shortvalue1")
        install_global_redaction()
        logger, buf = _make_logger()
        logger.info("payload: shortvalue1")
        # We expect the 11-char value to leak through (intentional).
        assert "shortvalue1" in buf.getvalue()


class TestExtraPatterns:
    def test_caller_can_inject_extra_patterns(self) -> None:
        install_global_redaction(
            extra_patterns=[(re.compile(r"FOOBAR123"), "[CUSTOM]")]
        )
        logger, buf = _make_logger()
        logger.info("input had FOOBAR123 in it")
        assert "FOOBAR123" not in buf.getvalue()
        assert "[CUSTOM]" in buf.getvalue()

    def test_add_pattern_runtime(self) -> None:
        f = install_global_redaction()
        # Replacement intentionally avoids the original token to keep the
        # match self-stable across multiple filter passes.
        f.add_pattern(re.compile(r"BLOOP"), "[GONE]")
        logger, buf = _make_logger()
        logger.info("BLOOP detected")
        assert "BLOOP" not in buf.getvalue()
        assert "[GONE]" in buf.getvalue()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
