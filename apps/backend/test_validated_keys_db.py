"""Tests for the validated_keys_db hardening pass.

Covers: hashing v1/v2 round-trip, TTL expiry, opportunistic v1→v2 migration,
optional Fernet encryption-at-rest, file-permission tightening on POSIX.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import validated_keys_db


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the module at a fresh temp DB and reset the Fernet singleton."""
    db = tmp_path / "vkdb.sqlite3"
    monkeypatch.setattr(validated_keys_db, "DB_PATH", str(db))
    validated_keys_db._reset_fernet_for_tests()
    monkeypatch.delenv("VALIDATED_KEYS_FERNET_KEY", raising=False)
    monkeypatch.delenv("VALIDATED_KEYS_TTL_DAYS", raising=False)
    yield
    validated_keys_db._reset_fernet_for_tests()


# ---------------------------------------------------------------------------
# Hashing round-trip


class TestRoundTrip:
    def test_set_then_is_validated(self) -> None:
        validated_keys_db.set_validated("anthropic", "sk-ant-test-12345", True)
        assert validated_keys_db.is_validated("anthropic", "sk-ant-test-12345")

    def test_wrong_key_not_validated(self) -> None:
        validated_keys_db.set_validated("openai", "sk-correct", True)
        assert not validated_keys_db.is_validated("openai", "sk-wrong")

    def test_unvalidated_flag_skipped(self) -> None:
        validated_keys_db.set_validated("openai", "sk-bad-key", False)
        assert not validated_keys_db.is_validated("openai", "sk-bad-key")

    def test_unknown_provider(self) -> None:
        assert not validated_keys_db.is_validated("ghost", "anything")


# ---------------------------------------------------------------------------
# TTL


class TestTtl:
    def test_recent_entry_within_ttl(self) -> None:
        validated_keys_db.set_validated("a", "k1", True)
        assert validated_keys_db.is_validated("a", "k1")

    def test_expired_entry_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Set TTL to 1 day, then backdate the row.
        monkeypatch.setenv("VALIDATED_KEYS_TTL_DAYS", "1")
        validated_keys_db.set_validated("a", "k1", True)

        # Backdate the row by 5 days directly in SQL.
        old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        conn.execute(
            "UPDATE validated_keys SET validated_at=? WHERE provider='a'", (old,)
        )
        conn.commit()
        conn.close()

        assert not validated_keys_db.is_validated("a", "k1")

    def test_prune_expired_removes_old_rows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VALIDATED_KEYS_TTL_DAYS", "1")
        validated_keys_db.set_validated("a", "k1", True)
        validated_keys_db.set_validated("a", "k2", True)

        # Backdate one row.
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        conn.execute(
            "UPDATE validated_keys SET validated_at=? WHERE provider='a' "
            "AND rowid IN (SELECT rowid FROM validated_keys WHERE provider='a' LIMIT 1)",
            (old,),
        )
        conn.commit()
        conn.close()

        removed = validated_keys_db.prune_expired()
        assert removed >= 1

    def test_invalid_validated_at_is_ignored(self) -> None:
        validated_keys_db.set_validated("a", "k1", True)
        # Corrupt the timestamp field directly.
        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        conn.execute(
            "UPDATE validated_keys SET validated_at='not a date' WHERE provider='a'"
        )
        conn.commit()
        conn.close()
        # Should be treated as expired (defensive default), not crash.
        assert not validated_keys_db.is_validated("a", "k1")

    def test_default_ttl_when_env_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VALIDATED_KEYS_TTL_DAYS", "not-an-int")
        validated_keys_db.set_validated("a", "k1", True)
        assert validated_keys_db.is_validated("a", "k1")


# ---------------------------------------------------------------------------
# Legacy v1 → v2 migration


class TestMigration:
    def test_v1_row_read_and_migrated(self) -> None:
        # Inject a v1 hash directly.
        legacy = validated_keys_db._hash_v1("legacy-key")
        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS validated_keys ("
            "provider TEXT, api_key_hash TEXT, validated INTEGER, validated_at TEXT, "
            "PRIMARY KEY (provider, api_key_hash))"
        )
        conn.execute(
            "INSERT INTO validated_keys VALUES (?, ?, ?, ?)",
            ("openai", legacy, 1, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        # Reads succeed and migrate the row in place.
        assert validated_keys_db.is_validated("openai", "legacy-key")

        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        cur = conn.execute(
            "SELECT api_key_hash FROM validated_keys WHERE provider='openai'"
        )
        row = cur.fetchone()
        conn.close()
        # The bare v1 hex digest is gone; the row is now v2-formatted (or
        # encrypted v2 if Fernet is enabled).
        assert not row[0] == legacy
        # The migrated value is either a plain v2$ entry or wrapped as fernet:.
        assert row[0].startswith("v2$") or row[0].startswith("fernet:")


# ---------------------------------------------------------------------------
# Encryption-at-rest


def _has_cryptography() -> bool:
    try:
        import cryptography.fernet  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_cryptography(), reason="cryptography not installed")
class TestEncryption:
    def test_fernet_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "VALIDATED_KEYS_FERNET_KEY", validated_keys_db.generate_fernet_key()
        )
        validated_keys_db._reset_fernet_for_tests()
        validated_keys_db.set_validated("anthropic", "sk-secret", True)

        # The on-disk hash column starts with "fernet:" — not the bare hash.
        conn = sqlite3.connect(validated_keys_db.DB_PATH)
        cur = conn.execute("SELECT api_key_hash FROM validated_keys")
        row = cur.fetchone()
        conn.close()
        assert row[0].startswith("fernet:")

        assert validated_keys_db.is_validated("anthropic", "sk-secret")

    def test_encrypted_row_with_no_key_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "VALIDATED_KEYS_FERNET_KEY", validated_keys_db.generate_fernet_key()
        )
        validated_keys_db._reset_fernet_for_tests()
        validated_keys_db.set_validated("anthropic", "sk-secret", True)

        # Drop the key — the encrypted row becomes unreadable, treated as miss.
        monkeypatch.delenv("VALIDATED_KEYS_FERNET_KEY", raising=False)
        validated_keys_db._reset_fernet_for_tests()

        assert not validated_keys_db.is_validated("anthropic", "sk-secret")

    def test_invalid_fernet_key_falls_back_to_cleartext(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VALIDATED_KEYS_FERNET_KEY", "not-a-valid-base64-key")
        validated_keys_db._reset_fernet_for_tests()
        # Should not crash — just warn and store cleartext hash.
        validated_keys_db.set_validated("openai", "sk-x", True)
        assert validated_keys_db.is_validated("openai", "sk-x")


class TestEncryptionWithoutCrypto:
    def test_missing_lib_falls_back_silently(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Even if env var is set, if cryptography is unavailable we just warn
        # and store cleartext. The test doesn't actually uninstall the lib —
        # it just verifies that a successful set/is_validated still works.
        validated_keys_db._reset_fernet_for_tests()
        validated_keys_db.set_validated("openai", "sk-y", True)
        assert validated_keys_db.is_validated("openai", "sk-y")


# ---------------------------------------------------------------------------
# Filesystem permissions


@pytest.mark.skipif(os.name != "posix", reason="POSIX-only chmod")
class TestPermissions:
    def test_db_file_is_0600(self, tmp_path: Path) -> None:
        validated_keys_db.set_validated("a", "k", True)
        mode = os.stat(validated_keys_db.DB_PATH).st_mode & 0o777
        assert mode == 0o600


class TestKeyGen:
    def test_generate_fernet_key_returns_valid_key(self) -> None:
        key = validated_keys_db.generate_fernet_key()
        # Must be 44 chars urlsafe-base64 (32 bytes).
        assert len(key) == 44
        assert isinstance(key, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
