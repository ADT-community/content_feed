"""SQLite storage for the content_feed backend.

SQLite keeps this skeleton dependency-free and easy to run locally. The README
plans Postgres later, so every statement lives in this module and the routers
only ever touch a connection handed to them.
"""

import os
import secrets
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "feed.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT    NOT NULL UNIQUE,   -- E.164, e.g. +2348012345678
    created_at  INTEGER NOT NULL           -- unix seconds
);

CREATE TABLE IF NOT EXISTS otp_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT    NOT NULL,
    code_hash   TEXT    NOT NULL,          -- HMAC-SHA256; the code itself is never stored
    created_at  INTEGER NOT NULL,
    expires_at  INTEGER NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    consumed_at INTEGER                    -- set when used, expired or superseded
);
CREATE INDEX IF NOT EXISTS otp_codes_phone_idx ON otp_codes (phone);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT    PRIMARY KEY,       -- SHA-256 of the bearer token
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at  INTEGER NOT NULL
);

-- Server-side secrets generated at runtime. Nothing here is ever committed.
CREATE TABLE IF NOT EXISTS app_secrets (
    name        TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);
"""

_initialised: set[str] = set()


def db_path() -> str:
    """Database file, overridable with FEED_DB (tests point this at a tmp dir)."""
    return os.environ.get("FEED_DB") or str(DEFAULT_DB_PATH)


def connect() -> sqlite3.Connection:
    path = db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path not in _initialised:
        conn.executescript(SCHEMA)
        _initialised.add(path)
    return conn


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_or_create_secret(conn: sqlite3.Connection, name: str = "otp_hmac") -> bytes:
    """Secret used to HMAC one-time codes.

    Prefer FEED_SECRET so a stolen database alone cannot be used to recover
    codes. Without it we generate one per database, which still beats shipping
    a hard-coded default in a public repo.
    """
    from_env = os.environ.get("FEED_SECRET")
    if from_env:
        return from_env.encode()

    row = conn.execute("SELECT value FROM app_secrets WHERE name = ?", (name,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT OR IGNORE INTO app_secrets (name, value) VALUES (?, ?)",
            (name, secrets.token_bytes(32).hex()),
        )
        conn.commit()
        row = conn.execute("SELECT value FROM app_secrets WHERE name = ?", (name,)).fetchone()
    return bytes.fromhex(row["value"])
