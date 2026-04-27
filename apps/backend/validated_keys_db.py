"""Validated-keys store.

Stores **hashes** of API keys we've already verified against their
provider, so we don't re-validate the same key on every restart.

Hash format
-----------
``v2$<salt_hex>$<digest_hex>`` — PBKDF2-HMAC-SHA256, 600 000 iterations,
16-byte per-record random salt. Reads of legacy v1 entries (single fixed
salt, 100 000 iterations) are still supported but are migrated to v2 on
first successful verification.

Hardening (this file)
---------------------
* Per-record salt + 600k iterations (already documented above).
* **Filesystem permissions** restricted to 0600 on POSIX so other local
  users on the box can't read the DB.
* **TTL**: entries older than ``VALIDATED_KEYS_TTL_DAYS`` are ignored
  on read and proactively deleted on write paths.
* **Optional encryption-at-rest**: when ``VALIDATED_KEYS_FERNET_KEY``
  is set, the *value* of the hash column is wrapped with Fernet before
  insertion (the column then stores ``fernet:<token>`` instead of the
  bare hash). Useful for shared-host deployments. Cleartext hashes
  remain readable for backward-compat.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DB_PATH = "validated_keys.sqlite3"

# Hashing parameters. v2 uses a per-record random salt and PBKDF2 iterations
# at the OWASP 2023 recommended floor for PBKDF2-HMAC-SHA256.
_PBKDF2_ITERATIONS_V2 = 600_000
_SALT_LEN = 16

# Legacy parameters kept only to recompute v1 hashes for backward-compat reads.
_LEGACY_SALT = b"workpilot-validated-keys-v1"
_LEGACY_ITERATIONS = 100_000

# TTL — default 30 days. Override with VALIDATED_KEYS_TTL_DAYS.
_DEFAULT_TTL_DAYS = 30


def _ttl_days() -> int:
    raw = os.environ.get("VALIDATED_KEYS_TTL_DAYS", "")
    try:
        return max(1, int(raw)) if raw else _DEFAULT_TTL_DAYS
    except ValueError:
        return _DEFAULT_TTL_DAYS


# ---------------------------------------------------------------------------
# Optional encryption-at-rest


_FERNET_PREFIX = "fernet:"
_fernet_cipher = None  # cached `Fernet` instance once we successfully load one


def _get_fernet():
    """Return a `Fernet` cipher if ``VALIDATED_KEYS_FERNET_KEY`` is set.

    The env var must be a 32-byte urlsafe-base64 string (a regular Fernet
    key). Returns None silently if the key is missing or `cryptography`
    isn't installed — encryption is opt-in.
    """
    global _fernet_cipher
    if _fernet_cipher is not None:
        return _fernet_cipher
    raw_key = os.environ.get("VALIDATED_KEYS_FERNET_KEY", "").strip()
    if not raw_key:
        return None
    try:
        from cryptography.fernet import Fernet  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "VALIDATED_KEYS_FERNET_KEY is set but `cryptography` is not "
            "installed — falling back to unencrypted storage."
        )
        return None
    try:
        _fernet_cipher = Fernet(raw_key.encode("ascii"))
    except (ValueError, TypeError) as e:
        logger.warning("VALIDATED_KEYS_FERNET_KEY is invalid: %s", e)
        return None
    return _fernet_cipher


def _maybe_encrypt(value: str) -> str:
    cipher = _get_fernet()
    if cipher is None:
        return value
    token = cipher.encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_FERNET_PREFIX}{token}"


def _maybe_decrypt(value: str) -> str:
    if not value.startswith(_FERNET_PREFIX):
        return value
    cipher = _get_fernet()
    if cipher is None:
        # Encrypted row but no key available → unreadable. Treat as miss.
        raise ValueError("Fernet-wrapped row but no key available")
    token = value[len(_FERNET_PREFIX) :].encode("ascii")
    return cipher.decrypt(token).decode("utf-8")


def generate_fernet_key() -> str:
    """Helper for ops: emit a fresh Fernet key. Not used at runtime."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


# ---------------------------------------------------------------------------
# Filesystem permissions


def _restrict_db_permissions(path: str) -> None:
    """Set the DB file to 0600 on POSIX. No-op on Windows."""
    try:
        if os.name == "posix":
            os.chmod(path, 0o600)
    except OSError as e:
        # Don't fail to read/write because of a permission tweak failure.
        logger.debug("Could not chmod %s: %s", path, e)


# ---------------------------------------------------------------------------
# Connection + schema


def get_db():
    is_new = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS validated_keys (
        provider TEXT,
        api_key_hash TEXT,
        validated INTEGER,
        validated_at TEXT,
        PRIMARY KEY (provider, api_key_hash)
    )"""
    )
    if is_new:
        _restrict_db_permissions(DB_PATH)
    return conn


# ---------------------------------------------------------------------------
# Hashing


def _hash_v2(api_key: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", api_key.encode("utf-8"), salt, _PBKDF2_ITERATIONS_V2
    )
    return f"v2${salt.hex()}${digest.hex()}"


def _hash_v1(api_key: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", api_key.encode("utf-8"), _LEGACY_SALT, _LEGACY_ITERATIONS
    ).hex()


def hash_key(api_key: str, salt: bytes | None = None) -> str:
    """Hash an API key with PBKDF2-HMAC-SHA256 (v2 format).

    Format: ``v2$<hex_salt>$<hex_digest>``.
    """
    if salt is None:
        salt = secrets.token_bytes(_SALT_LEN)
    return _hash_v2(api_key, salt)


def _verify(stored_hash: str, api_key: str) -> bool:
    """Constant-time comparison against either v2 or legacy v1 hashes."""
    if stored_hash.startswith("v2$"):
        try:
            _, salt_hex, _digest_hex = stored_hash.split("$", 2)
            salt = bytes.fromhex(salt_hex)
        except ValueError:
            return False
        return secrets.compare_digest(stored_hash, _hash_v2(api_key, salt))
    # Legacy v1: bare hex digest with the constant module-level salt.
    return secrets.compare_digest(stored_hash, _hash_v1(api_key))


# ---------------------------------------------------------------------------
# Public API


def set_validated(provider: str, api_key: str, validated: bool):
    conn = get_db()
    try:
        # Opportunistically prune expired rows so the DB doesn't grow forever.
        _prune_expired(conn)
        h = hash_key(api_key)
        conn.execute(
            """INSERT OR REPLACE INTO validated_keys (provider, api_key_hash, validated, validated_at)
                    VALUES (?, ?, ?, ?)""",
            (
                provider,
                _maybe_encrypt(h),
                int(validated),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def is_validated(provider: str, api_key: str) -> bool:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT api_key_hash, validated, validated_at FROM validated_keys WHERE provider=?",
            (provider,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    cutoff = datetime.now(timezone.utc) - timedelta(days=_ttl_days())

    for stored_hash, validated_flag, validated_at in rows:
        if not validated_flag:
            continue
        if not _within_ttl(validated_at, cutoff):
            continue
        try:
            decrypted = _maybe_decrypt(stored_hash)
        except ValueError:
            # Encrypted row we can't decrypt — skip silently.
            continue
        if _verify(decrypted, api_key):
            # Opportunistically migrate v1 → v2 in place.
            if not decrypted.startswith("v2$"):
                _migrate_legacy_row(provider, stored_hash, api_key)
            return True
    return False


def _within_ttl(validated_at: str | None, cutoff: datetime) -> bool:
    if not validated_at:
        return False
    try:
        ts = datetime.fromisoformat(validated_at)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff


def _migrate_legacy_row(provider: str, old_stored_hash: str, api_key: str) -> None:
    """Replace a legacy v1 row with the v2-hashed equivalent."""
    new_hash = hash_key(api_key)
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM validated_keys WHERE provider=? AND api_key_hash=?",
            (provider, old_stored_hash),
        )
        conn.execute(
            """INSERT OR REPLACE INTO validated_keys (provider, api_key_hash, validated, validated_at)
                    VALUES (?, ?, ?, ?)""",
            (
                provider,
                _maybe_encrypt(new_hash),
                1,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _prune_expired(conn: sqlite3.Connection) -> int:
    """Delete rows older than the TTL. Returns the number of rows removed."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_ttl_days())).isoformat()
    cur = conn.execute("DELETE FROM validated_keys WHERE validated_at < ?", (cutoff,))
    removed = cur.rowcount or 0
    if removed:
        conn.commit()
        logger.info("Pruned %d expired validated_keys rows", removed)
    return removed


def prune_expired() -> int:
    """Public convenience wrapper. Returns the number of rows removed."""
    conn = get_db()
    try:
        return _prune_expired(conn)
    finally:
        conn.close()


# Reset hook for tests (singletons are evil in test contexts).
def _reset_fernet_for_tests() -> None:
    global _fernet_cipher
    _fernet_cipher = None
