import hashlib
import hmac
import sqlite3
from datetime import datetime

DB_PATH = "validated_keys.sqlite3"

# HMAC key for hashing API keys (not a secret - used to satisfy secure hashing requirements)
_HMAC_KEY = b"workpilot-validated-keys-v1"


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
    return hmac.new(_HMAC_KEY, api_key.encode("utf-8"), hashlib.sha256).hexdigest()


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
