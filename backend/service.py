"""Business logic for accounts, profiles and follows.

Handlers raise :class:`ApiError`; the HTTP layer turns them into JSON responses.
The same functions are called directly by the test suite.
"""

from __future__ import annotations

import os
import re
import secrets
import string
from typing import Any

from .db import Database, expires_in, stamp

CODE_TTL_SECONDS = 300
MAX_ATTEMPTS = 5
HANDLE_RE = re.compile(r"^[a-z0-9_]{3,30}$")
PHONE_RE = re.compile(r"^\+[0-9]{8,15}$")

CREATOR_FIELDS = {
    "display_name": 80,
    "bio": 500,
    "avatar_url": 500,
    "location": 80,
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def normalize_phone(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ApiError(400, "invalid_phone", "phone must be a string")
    digits = re.sub(r"[^0-9]", "", raw)
    if not (8 <= len(digits) <= 15):
        raise ApiError(400, "invalid_phone", "phone must contain 8 to 15 digits")
    phone = "+" + digits
    if not PHONE_RE.match(phone):
        raise ApiError(400, "invalid_phone", "invalid phone number")
    return phone


def normalize_handle(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ApiError(400, "invalid_handle", "handle must be a string")
    handle = raw.strip().lower().lstrip("@")
    if not HANDLE_RE.match(handle):
        raise ApiError(
            400,
            "invalid_handle",
            "handle must be 3-30 lowercase letters, digits or underscores",
        )
    return handle


def generate_code() -> str:
    """Dev override via DEV_FIXED_CODE makes tests deterministic."""
    fixed = os.getenv("DEV_FIXED_CODE")
    if fixed and re.fullmatch(r"[0-9]{6}", fixed):
        return fixed
    return "".join(secrets.choice(string.digits) for _ in range(6))


def request_code(db: Database, phone_raw: Any) -> dict:
    phone = normalize_phone(phone_raw)
    code = generate_code()
    db.execute(
        "INSERT INTO login_codes (phone, code, expires_at, attempts, consumed, created_at) "
        "VALUES (?, ?, ?, 0, ?, ?)",
        (phone, code, expires_in(CODE_TTL_SECONDS), db.bool_value(False), stamp()),
    )
    print(f"[content_feed] login code for {phone}: {code} (valid 5 minutes)", flush=True)
    return {"sent": True, "phone": phone, "expires_in": CODE_TTL_SECONDS}


def verify_code(db: Database, phone_raw: Any, code_raw: Any) -> dict:
    phone = normalize_phone(phone_raw)
    if not isinstance(code_raw, str) or not re.fullmatch(r"[0-9]{6}", code_raw):
        raise ApiError(400, "invalid_code", "code must be exactly 6 digits")

    row = db.one(
        "SELECT * FROM login_codes WHERE phone = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        (phone,),
    )
    if row is None or row["consumed"]:
        raise ApiError(400, "invalid_code", "no active code for this phone")

    if stamp() > row["expires_at"]:
        db.execute("UPDATE login_codes SET consumed = ? WHERE id = ?",
                   (db.bool_value(True), row["id"]))
        raise ApiError(400, "code_expired", "code expired; request a new one")

    if row["attempts"] >= MAX_ATTEMPTS:
        db.execute("UPDATE login_codes SET consumed = ? WHERE id = ?",
                   (db.bool_value(True), row["id"]))
        raise ApiError(429, "too_many_attempts", "too many attempts; request a new code")

    if code_raw != row["code"]:
        attempts = row["attempts"] + 1
        db.execute("UPDATE login_codes SET attempts = ? WHERE id = ?", (attempts, row["id"]))
        left = MAX_ATTEMPTS - attempts
        if left <= 0:
            db.execute("UPDATE login_codes SET consumed = ? WHERE id = ?",
                       (db.bool_value(True), row["id"]))
            raise ApiError(429, "too_many_attempts", "too many attempts; request a new code")
        raise ApiError(400, "invalid_code", f"wrong code; {left} attempts left")

    db.execute("UPDATE login_codes SET consumed = ? WHERE id = ?",
               (db.bool_value(True), row["id"]))

    user = db.one("SELECT * FROM users WHERE phone = ?", (phone,))
    if user is None:
        user_id = db.execute(
            "INSERT INTO users (phone, display_name, created_at) VALUES (?, NULL, ?)",
            (phone, stamp()),
        )
        user = db.one("SELECT * FROM users WHERE id = ?", (user_id,))
    else:
        user_id = user["id"]

    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, stamp()),
    )
    return {"token": token, "user": public_user(user)}


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "phone": user["phone"],
        "display_name": user["display_name"],
        "created_at": user["created_at"],
    }


def user_from_token(db: Database, token: str | None) -> dict | None:
    if not token:
        return None
    return db.one(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    )


def require_user(db: Database, token: str | None) -> dict:
    user = user_from_token(db, token)
    if user is None:
        raise ApiError(401, "unauthorized", "valid bearer token required")
    return user


def creator_row(db: Database, handle: str) -> dict | None:
    return db.one("SELECT * FROM creators WHERE handle = ?", (handle,))


def creator_public(db: Database, row: dict, viewer_id: int | None = None) -> dict:
    followers = db.one(
        "SELECT COUNT(*) AS n FROM follows WHERE creator_id = ?", (row["user_id"],)
    )["n"]
    posts = db.one(
        "SELECT COUNT(*) AS n FROM posts WHERE creator_id = ?", (row["user_id"],)
    )["n"]
    following = False
    if viewer_id is not None:
        following = db.one(
            "SELECT 1 AS yes FROM follows WHERE follower_id = ? AND creator_id = ?",
            (viewer_id, row["user_id"]),
        ) is not None
    return {
        "user_id": row["user_id"],
        "handle": row["handle"],
        "display_name": row["display_name"],
        "bio": row["bio"],
        "avatar_url": row["avatar_url"],
        "location": row["location"],
        "created_at": row["created_at"],
        "follower_count": followers,
        "post_count": posts,
        "following": following,
    }


def get_creator(db: Database, handle_raw: Any, viewer_id: int | None = None) -> dict:
    handle = normalize_handle(handle_raw)
    row = creator_row(db, handle)
    if row is None:
        raise ApiError(404, "not_found", f"creator @{handle} not found")
    return creator_public(db, row, viewer_id)


def get_me(db: Database, user: dict) -> dict:
    row = db.one("SELECT * FROM creators WHERE user_id = ?", (user["id"],))
    return {
        "user": public_user(user),
        "creator": creator_public(db, row, user["id"]) if row else None,
    }


def _text(data: dict, key: str, max_len: int) -> str | None:
    if key not in data:
        return None
    value = data[key]
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ApiError(400, "invalid_profile", f"{key} must be a string")
    value = value.strip()
    if len(value) > max_len:
        raise ApiError(400, "invalid_profile", f"{key} is longer than {max_len} characters")
    return value


def update_profile(db: Database, user: dict, data: Any) -> dict:
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_profile", "body must be a JSON object")

    allowed = {"handle", *CREATOR_FIELDS}
    unknown = set(data) - allowed
    if unknown:
        raise ApiError(400, "invalid_profile", f"unknown field(s): {', '.join(sorted(unknown))}")

    handle = normalize_handle(data["handle"]) if "handle" in data else None
    fields = {key: _text(data, key, limit) for key, limit in CREATOR_FIELDS.items()}
    fields = {key: value for key, value in fields.items() if value is not None}

    creator = db.one("SELECT * FROM creators WHERE user_id = ?", (user["id"],))

    if handle is not None:
        taken = db.one("SELECT user_id FROM creators WHERE handle = ?", (handle,))
        if taken is not None and taken["user_id"] != user["id"]:
            raise ApiError(409, "handle_taken", f"handle @{handle} is already taken")

    if creator is None:
        if handle is None:
            if "display_name" in fields:
                db.execute("UPDATE users SET display_name = ? WHERE id = ?",
                           (fields["display_name"], user["id"]))
                user = db.one("SELECT * FROM users WHERE id = ?", (user["id"],))
            return get_me(db, user)
        display_name = fields.get("display_name") or user["display_name"] or handle
        db.execute(
            "INSERT INTO creators (user_id, handle, display_name, bio, avatar_url, location, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                user["id"], handle, display_name, fields.get("bio", ""),
                fields.get("avatar_url"), fields.get("location"), stamp(),
            ),
        )
    else:
        if handle is not None and handle != creator["handle"]:
            db.execute("UPDATE creators SET handle = ? WHERE user_id = ?",
                       (handle, user["id"]))
        if fields:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            db.execute(
                f"UPDATE creators SET {assignments} WHERE user_id = ?",
                (*fields.values(), user["id"]),
            )

    user = db.one("SELECT * FROM users WHERE id = ?", (user["id"],))
    return get_me(db, user)


def follow(db: Database, user: dict, handle_raw: Any) -> dict:
    handle = normalize_handle(handle_raw)
    row = creator_row(db, handle)
    if row is None:
        raise ApiError(404, "not_found", f"creator @{handle} not found")
    if row["user_id"] == user["id"]:
        raise ApiError(400, "cannot_follow_self", "you cannot follow yourself")
    db.execute(
        "INSERT INTO follows (follower_id, creator_id, created_at) VALUES (?, ?, ?) "
        "ON CONFLICT DO NOTHING",
        (user["id"], row["user_id"], stamp()),
    )
    return {"following": True, "handle": handle, "follower_count": creator_public(db, row)["follower_count"]}


def unfollow(db: Database, user: dict, handle_raw: Any) -> dict:
    handle = normalize_handle(handle_raw)
    row = creator_row(db, handle)
    if row is None:
        raise ApiError(404, "not_found", f"creator @{handle} not found")
    db.execute(
        "DELETE FROM follows WHERE follower_id = ? AND creator_id = ?",
        (user["id"], row["user_id"]),
    )
    return {"following": False, "handle": handle, "follower_count": creator_public(db, row)["follower_count"]}
