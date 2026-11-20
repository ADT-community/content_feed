"""Database adapter.

The canonical schema is PostgreSQL (see ``schema.sql``). For zero-setup local
runs and tests the same logical model is created on SQLite. Select the engine
with the ``DATABASE_URL`` environment variable:

    sqlite:///./content_feed.db   (default)
    postgresql://user:pass@host/db (requires psycopg2)
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS creators (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    avatar_url TEXT,
    location TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    caption TEXT NOT NULL DEFAULT '',
    media_url TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_posts_creator_created ON posts (creator_id, created_at DESC);
CREATE TABLE IF NOT EXISTS follows (
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id INTEGER NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (follower_id, creator_id),
    CHECK (follower_id <> creator_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_creator ON follows (creator_id);
CREATE TABLE IF NOT EXISTS tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL REFERENCES users(id),
    to_creator_id INTEGER NOT NULL REFERENCES creators(user_id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL DEFAULT 'NGN',
    platform_fee_minor INTEGER NOT NULL CHECK (platform_fee_minor >= 0),
    creator_amount_minor INTEGER NOT NULL CHECK (creator_amount_minor >= 0),
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TEXT NOT NULL,
    CHECK (platform_fee_minor + creator_amount_minor = amount_minor)
);
CREATE INDEX IF NOT EXISTS idx_tips_creator_created ON tips (to_creator_id, created_at DESC);
CREATE TABLE IF NOT EXISTS payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL REFERENCES creators(user_id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL DEFAULT 'NGN',
    provider TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payouts_creator ON payouts (creator_id, created_at DESC);
CREATE TABLE IF NOT EXISTS login_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_codes_phone ON login_codes (phone, consumed, created_at DESC);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(value: datetime | None = None) -> str:
    """ISO-8601 UTC string; lexicographically sortable and comparable."""
    return (value or utcnow()).isoformat().replace("+00:00", "Z")


def expires_in(seconds: int) -> str:
    return stamp(utcnow() + timedelta(seconds=seconds))


class Database:
    """Minimal synchronous DB wrapper shared by the HTTP layer and tests."""

    def __init__(self, url: str | None = None):
        url = url or os.getenv("DATABASE_URL", "sqlite:///./content_feed.db")
        self.url = url
        self._lock = threading.RLock()

        if url.startswith("sqlite:"):
            self.kind = "sqlite"
            path = url.split("sqlite:///", 1)[1] if "sqlite:///" in url else url[len("sqlite:"):]
            if path in ("", ":memory:"):
                path = ":memory:"
            self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._placeholder = "?"
            self._conn.executescript(SQLITE_SCHEMA)
        elif url.startswith(("postgres://", "postgresql://")):
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
            except ImportError as exc:  # pragma: no cover - depends on deployment
                raise RuntimeError(
                    "PostgreSQL needs psycopg2: pip install psycopg2-binary"
                ) from exc
            self.kind = "postgres"
            self._conn = psycopg2.connect(url)
            self._conn.autocommit = True
            self._conn.cursor_factory = RealDictCursor
            self._placeholder = "%s"
            with self._conn.cursor() as cur:
                cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"Unsupported DATABASE_URL: {url!r}")

    def _sql(self, sql: str) -> str:
        return sql.replace("?", self._placeholder) if self.kind == "postgres" else sql

    def bool_value(self, value: bool):
        """Boolean literal matching the engine's column representation."""
        return value if self.kind == "postgres" else int(value)

    def execute(self, sql: str, params: tuple = ()) -> int | None:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._sql(sql), params)
                return cur.lastrowid
            finally:
                cur.close()

    def one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._sql(sql), params)
                row = cur.fetchone()
                return dict(row) if row is not None else None
            finally:
                cur.close()

    def all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._sql(sql), params)
                return [dict(row) for row in cur.fetchall()]
            finally:
                cur.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
