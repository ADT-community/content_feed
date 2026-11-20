"""Request dispatch: maps (method, path) to service calls."""

from __future__ import annotations

import re
from typing import Any

from . import service
from .db import Database

CREATOR_PATH = re.compile(r"^/creators/([^/]+)$")
FOLLOW_PATH = re.compile(r"^/follow/([^/]+)$")


def _token(headers: dict[str, str] | None) -> str | None:
    headers = headers or {}
    for key, value in headers.items():
        if key.lower() == "authorization" and isinstance(value, str):
            parts = value.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
    return None


def dispatch(
    method: str,
    path: str,
    body: Any = None,
    headers: dict[str, str] | None = None,
    db: Database | None = None,
) -> tuple[int, dict]:
    """Return (HTTP status, JSON-serialisable payload). Never raises."""
    db = db or Database()
    method = method.upper()
    path = path.split("?", 1)[0].rstrip("/") or "/"
    token = _token(headers)

    try:
        if method == "GET" and path == "/health":
            return 200, {"ok": True, "service": "content_feed"}

        if method == "POST" and path == "/auth/request-code":
            data = body if isinstance(body, dict) else {}
            return 200, service.request_code(db, data.get("phone"))

        if method == "POST" and path == "/auth/verify-code":
            data = body if isinstance(body, dict) else {}
            return 200, service.verify_code(db, data.get("phone"), data.get("code"))

        if path in ("/me/profile", "/me") and method in ("GET", "PUT"):
            user = service.require_user(db, token)
            if method == "GET":
                return 200, service.get_me(db, user)
            return 200, service.update_profile(db, user, body)

        match = CREATOR_PATH.match(path)
        if match and method == "GET":
            viewer = service.user_from_token(db, token)
            return 200, service.get_creator(db, match.group(1),
                                             viewer["id"] if viewer else None)

        match = FOLLOW_PATH.match(path)
        if match and method in ("POST", "DELETE"):
            user = service.require_user(db, token)
            if method == "POST":
                return 200, service.follow(db, user, match.group(1))
            return 200, service.unfollow(db, user, match.group(1))

        return 404, {"error": {"code": "not_found", "message": "unknown endpoint"}}
    except service.ApiError as exc:
        return exc.status, {"error": {"code": exc.code, "message": exc.message}}
