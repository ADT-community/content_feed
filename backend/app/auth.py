"""Phone sign-in: ask for a one-time code, verify it, get a bearer token.

SMS is mocked. The code is written to the application log instead of being
sent, so no provider keys are needed anywhere -- see send_otp_sms().
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .db import get_db, get_or_create_secret

logger = logging.getLogger("content_feed.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

CODE_LENGTH = 6
OTP_TTL_SECONDS = int(os.environ.get("FEED_OTP_TTL_SECONDS", "300"))   # 5 minutes
MAX_ATTEMPTS = int(os.environ.get("FEED_OTP_MAX_ATTEMPTS", "5"))
# Numbers typed in local form (0801...) get this calling code. Nigeria is the
# launch market in the README; override with FEED_DEFAULT_CALLING_CODE.
DEFAULT_CALLING_CODE = os.environ.get("FEED_DEFAULT_CALLING_CODE", "+234")

_NOT_PHONE_RE = re.compile(r"[^\d+]")
_E164_RE = re.compile(r"\+[1-9]\d{7,14}")


# --- models ----------------------------------------------------------------

class OtpRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=24, examples=["+2348012345678"])


class OtpResponse(BaseModel):
    phone: str
    expires_in: int
    max_attempts: int


class VerifyRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=24, examples=["+2348012345678"])
    code: str = Field(..., min_length=4, max_length=12, examples=["123456"])


class User(BaseModel):
    id: int
    phone: str
    created_at: int


class VerifyResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: User


# --- helpers ---------------------------------------------------------------

def _now() -> int:
    """Current unix time. One place to patch in tests."""
    return int(time.time())


def normalize_phone(raw: str) -> str:
    """Accept what people actually type and return one canonical E.164 string.

    "0801 234 5678", "+234 801 234 5678" and "2348012345678" are the same
    person, so they must normalize to the same key or they would each end up
    with their own account.
    """
    cleaned = _NOT_PHONE_RE.sub("", raw or "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("0"):
        cleaned = DEFAULT_CALLING_CODE + cleaned[1:]
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not _E164_RE.fullmatch(cleaned):
        # Literal 422: Starlette renamed its constant for this code, so the
        # number is the portable spelling.
        raise HTTPException(422, "Enter a phone number like 08012345678 or +2348012345678.")
    return cleaned


def _generate_code() -> str:
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def _hash_code(db: sqlite3.Connection, phone: str, code: str) -> str:
    """Codes are stored as a keyed hash, bound to the phone they were sent to."""
    return hmac.new(
        get_or_create_secret(db), f"{phone}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def send_otp_sms(phone: str, code: str, ttl_seconds: int) -> None:
    """Mock SMS gateway: log the code instead of sending it.

    This is the only place that needs to change when a real provider is added
    (out of scope here). Keys belong in the environment, never in this repo.
    """
    logger.info(
        "SMS to %s: Your content_feed code is %s. It expires in %d minutes.",
        phone,
        code,
        max(1, ttl_seconds // 60),
    )


def _get_or_create_user(db: sqlite3.Connection, phone: str, now: int) -> sqlite3.Row:
    db.execute("INSERT OR IGNORE INTO users (phone, created_at) VALUES (?, ?)", (phone, now))
    return db.execute(
        "SELECT id, phone, created_at FROM users WHERE phone = ?", (phone,)
    ).fetchone()


def _create_session(db: sqlite3.Connection, user_id: int, now: int) -> str:
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
        (_hash_token(token), user_id, now),
    )
    return token


def current_user(
    authorization: str | None = Header(default=None),
    db: sqlite3.Connection = Depends(get_db),
) -> User:
    """Dependency for protected endpoints: Authorization: Bearer <token>."""
    scheme, _, token = (authorization or "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sign in first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    row = db.execute(
        "SELECT u.id, u.phone, u.created_at"
        " FROM sessions s JOIN users u ON u.id = s.user_id"
        " WHERE s.token_hash = ?",
        (_hash_token(token),),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "That session is no longer valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(**dict(row))


# --- endpoints -------------------------------------------------------------

@router.post("/otp", response_model=OtpResponse)
def request_otp(payload: OtpRequest, db: sqlite3.Connection = Depends(get_db)) -> OtpResponse:
    """Send a 6-digit code to a phone number (logged, not texted)."""
    phone = normalize_phone(payload.phone)
    now = _now()
    code = _generate_code()

    # One live code per phone: asking for a new one retires the old one, so the
    # attempt limit cannot be sidestepped by stacking codes.
    db.execute(
        "UPDATE otp_codes SET consumed_at = ? WHERE phone = ? AND consumed_at IS NULL",
        (now, phone),
    )
    db.execute(
        "INSERT INTO otp_codes (phone, code_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (phone, _hash_code(db, phone, code), now, now + OTP_TTL_SECONDS),
    )
    db.commit()

    send_otp_sms(phone, code, OTP_TTL_SECONDS)
    # The code is deliberately absent from the response: the point of a code
    # sent to a phone is that it travels over a different channel.
    return OtpResponse(phone=phone, expires_in=OTP_TTL_SECONDS, max_attempts=MAX_ATTEMPTS)


@router.post("/verify", response_model=VerifyResponse)
def verify_otp(payload: VerifyRequest, db: sqlite3.Connection = Depends(get_db)) -> VerifyResponse:
    """Exchange a valid code for a bearer token, creating the account if new."""
    phone = normalize_phone(payload.phone)
    code = re.sub(r"\D", "", payload.code or "")   # people paste "123 456"
    now = _now()

    row = db.execute(
        "SELECT id, code_hash, expires_at, attempts FROM otp_codes"
        " WHERE phone = ? AND consumed_at IS NULL"
        " ORDER BY id DESC LIMIT 1",
        (phone,),
    ).fetchone()

    if row is None or row["expires_at"] <= now:
        if row is not None:
            db.execute("UPDATE otp_codes SET consumed_at = ? WHERE id = ?", (now, row["id"]))
            db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That code has expired or was never sent. Ask for a new one.",
        )

    if row["attempts"] >= MAX_ATTEMPTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many wrong attempts. Ask for a new code.",
        )

    # Count the attempt before checking it, so a crash cannot hand out a free try.
    attempts = row["attempts"] + 1
    db.execute("UPDATE otp_codes SET attempts = ? WHERE id = ?", (attempts, row["id"]))
    db.commit()

    if not hmac.compare_digest(row["code_hash"], _hash_code(db, phone, code)):
        left = max(0, MAX_ATTEMPTS - attempts)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Incorrect code. {left} attempt{'' if left == 1 else 's'} left.",
        )

    db.execute("UPDATE otp_codes SET consumed_at = ? WHERE id = ?", (now, row["id"]))
    user = _get_or_create_user(db, phone, now)
    token = _create_session(db, user["id"], now)
    db.commit()
    return VerifyResponse(token=token, user=User(**dict(user)))


@router.get("/me", response_model=User)
def read_me(user: User = Depends(current_user)) -> User:
    """Who the bearer token belongs to. Proves sign-in worked end to end."""
    return user
