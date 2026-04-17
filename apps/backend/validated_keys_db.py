import hashlib
import sqlite3
from datetime import datetime

DB_PATH = "validated_keys.sqlite3"

_PBKDF2_SALT = b"workpilot-validated-keys-v1"
_PBKDF2_ITERATIONS = 100_000


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


def hash_key(api_key: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", api_key.encode("utf-8"), _PBKDF2_SALT, _PBKDF2_ITERATIONS
    ).hex()


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
    h = hash_key(api_key)
    cur = conn.execute(
        "SELECT validated FROM validated_keys WHERE provider=? AND api_key_hash=?",
        (provider, h),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0])
