import hashlib
import secrets
import sqlite3
from datetime import datetime

DB_PATH = "validated_keys.sqlite3"

# Hashing parameters. v2 uses a per-record random salt and PBKDF2 iterations
# at the OWASP 2023 recommended floor for PBKDF2-HMAC-SHA256.
_PBKDF2_ITERATIONS_V2 = 600_000
_SALT_LEN = 16

# Legacy parameters kept only to recompute v1 hashes for backward-compat reads.
_LEGACY_SALT = b"workpilot-validated-keys-v1"
_LEGACY_ITERATIONS = 100_000


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS validated_keys (
        provider TEXT,
        api_key_hash TEXT,
        validated INTEGER,
        validated_at TEXT,
        PRIMARY KEY (provider, api_key_hash)
    )""")
    return conn


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


def set_validated(provider: str, api_key: str, validated: bool):
    conn = get_db()
    h = hash_key(api_key)
    conn.execute(
        """INSERT OR REPLACE INTO validated_keys (provider, api_key_hash, validated, validated_at)
                    VALUES (?, ?, ?, ?)""",
        (provider, h, int(validated), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def is_validated(provider: str, api_key: str) -> bool:
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT api_key_hash, validated FROM validated_keys WHERE provider=?",
            (provider,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    for stored_hash, validated_flag in rows:
        if not validated_flag:
            continue
        if _verify(stored_hash, api_key):
            # Opportunistically migrate v1 → v2 in place
            if not stored_hash.startswith("v2$"):
                _migrate_legacy_row(provider, stored_hash, api_key)
            return True
    return False


def _migrate_legacy_row(provider: str, old_hash: str, api_key: str) -> None:
    """Replace a legacy v1 row with the v2-hashed equivalent."""
    new_hash = hash_key(api_key)
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM validated_keys WHERE provider=? AND api_key_hash=?",
            (provider, old_hash),
        )
        conn.execute(
            """INSERT OR REPLACE INTO validated_keys (provider, api_key_hash, validated, validated_at)
                        VALUES (?, ?, ?, ?)""",
            (provider, new_hash, 1, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
