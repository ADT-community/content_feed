"""Phone sign-in: happy path, expiry, attempt limits and code handling."""

import sqlite3

import pytest

from app import auth


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# --- happy path ------------------------------------------------------------

def test_sign_in_works_end_to_end(client, sms, phone, request_code):
    code = request_code(phone)
    assert len(code) == 6 and code.isdigit()

    verified = client.post("/auth/verify", json={"phone": phone, "code": code})
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["token_type"] == "bearer"
    assert body["token"]
    assert body["user"]["phone"] == phone

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200, me.text
    assert me.json() == body["user"]


def test_otp_request_advertises_the_five_minute_window(client, phone):
    body = client.post("/auth/otp", json={"phone": phone}).json()
    assert body == {"phone": phone, "expires_in": 300, "max_attempts": 5}


def test_code_is_only_sent_over_the_mocked_sms_channel(client, sms, phone):
    response = client.post("/auth/otp", json={"phone": phone})
    assert sms.last_code() not in response.text
    assert len(sms.messages) == 1
    assert phone in sms.messages[0]


def test_spaces_in_the_typed_code_are_forgiven(client, phone, request_code):
    code = request_code(phone)
    spaced = f"{code[:3]} {code[3:]}"
    assert client.post("/auth/verify", json={"phone": phone, "code": spaced}).status_code == 200


def test_returning_user_keeps_the_same_account(client, phone, request_code):
    first = client.post("/auth/verify", json={"phone": phone, "code": request_code(phone)}).json()
    second = client.post("/auth/verify", json={"phone": phone, "code": request_code(phone)}).json()
    assert first["user"]["id"] == second["user"]["id"]
    assert first["token"] != second["token"]


def test_local_and_international_formats_are_one_account(client, request_code):
    local = client.post("/auth/verify", json={"phone": "0801 234 5678", "code": request_code("08012345678")})
    intl = client.post("/auth/verify", json={"phone": "+234 801 234 5678", "code": request_code("+2348012345678")})
    assert local.status_code == 200, local.text
    assert intl.status_code == 200, intl.text
    assert local.json()["user"] == intl.json()["user"]


@pytest.mark.parametrize("bad", ["", "123", "abcdefgh", "+0801234567", "0", "++23480123456"])
def test_invalid_phone_numbers_are_rejected(client, bad):
    assert client.post("/auth/otp", json={"phone": bad}).status_code == 422


# --- expiry ----------------------------------------------------------------

def test_code_expires_after_five_minutes(client, phone, request_code, monkeypatch):
    code = request_code(phone)
    issued_at = auth._now()
    monkeypatch.setattr(auth, "_now", lambda: issued_at + auth.OTP_TTL_SECONDS + 1)

    response = client.post("/auth/verify", json={"phone": phone, "code": code})
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]


def test_code_still_works_just_inside_the_window(client, phone, request_code, monkeypatch):
    code = request_code(phone)
    issued_at = auth._now()
    monkeypatch.setattr(auth, "_now", lambda: issued_at + auth.OTP_TTL_SECONDS - 2)
    assert client.post("/auth/verify", json={"phone": phone, "code": code}).status_code == 200


def test_expired_code_cannot_be_retried_after_a_clock_change(client, phone, request_code, monkeypatch):
    """An expired code is retired, so winding the clock back does not revive it."""
    code = request_code(phone)
    issued_at = auth._now()
    monkeypatch.setattr(auth, "_now", lambda: issued_at + auth.OTP_TTL_SECONDS + 1)
    client.post("/auth/verify", json={"phone": phone, "code": code})

    monkeypatch.setattr(auth, "_now", lambda: issued_at)
    assert client.post("/auth/verify", json={"phone": phone, "code": code}).status_code == 400


# --- attempt limit ---------------------------------------------------------

def _wrong_code(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


def test_five_wrong_attempts_then_the_code_is_locked(client, phone, request_code):
    code = request_code(phone)
    wrong = _wrong_code(code)

    for remaining in range(4, -1, -1):
        response = client.post("/auth/verify", json={"phone": phone, "code": wrong})
        assert response.status_code == 400
        assert f"{remaining} attempt" in response.json()["detail"]

    sixth = client.post("/auth/verify", json={"phone": phone, "code": wrong})
    assert sixth.status_code == 429
    assert "Too many" in sixth.json()["detail"]


def test_right_code_is_refused_once_the_limit_is_spent(client, phone, request_code):
    code = request_code(phone)
    for _ in range(auth.MAX_ATTEMPTS):
        client.post("/auth/verify", json={"phone": phone, "code": _wrong_code(code)})

    locked = client.post("/auth/verify", json={"phone": phone, "code": code})
    assert locked.status_code == 429
    assert client.get("/auth/me").status_code == 401


def test_a_fresh_code_restores_the_attempt_budget(client, phone, request_code):
    first = request_code(phone)
    for _ in range(auth.MAX_ATTEMPTS):
        client.post("/auth/verify", json={"phone": phone, "code": _wrong_code(first)})

    second = request_code(phone)
    assert client.post("/auth/verify", json={"phone": phone, "code": second}).status_code == 200


def test_requesting_a_new_code_retires_the_old_one(client, phone, request_code):
    first = request_code(phone)
    second = request_code(phone)
    assert client.post("/auth/verify", json={"phone": phone, "code": first}).status_code == 400
    assert client.post("/auth/verify", json={"phone": phone, "code": second}).status_code == 200


def test_code_cannot_be_used_twice(client, phone, request_code):
    code = request_code(phone)
    assert client.post("/auth/verify", json={"phone": phone, "code": code}).status_code == 200
    assert client.post("/auth/verify", json={"phone": phone, "code": code}).status_code == 400


def test_verify_without_a_code_request_fails(client, phone):
    response = client.post("/auth/verify", json={"phone": phone, "code": "123456"})
    assert response.status_code == 400
    assert "never sent" in response.json()["detail"]


def test_a_code_only_works_for_the_number_it_was_sent_to(client, request_code):
    mine = request_code("+2348012345678")
    theirs = request_code("+2348099999999")

    crossed = client.post("/auth/verify", json={"phone": "+2348099999999", "code": mine})
    assert crossed.status_code == 400
    assert "Incorrect code" in crossed.json()["detail"]

    assert client.post("/auth/verify", json={"phone": "+2348099999999", "code": theirs}).status_code == 200


# --- tokens ----------------------------------------------------------------

@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": ""}, {"Authorization": "Bearer "}, {"Authorization": "nonsense"},
     {"Authorization": "Bearer not-a-real-token"}],
)
def test_me_needs_a_valid_bearer_token(client, headers):
    assert client.get("/auth/me", headers=headers).status_code == 401


# --- storage ---------------------------------------------------------------

def test_codes_and_tokens_are_never_stored_in_the_clear(client, tmp_path, phone, request_code):
    code = request_code(phone)
    token = client.post("/auth/verify", json={"phone": phone, "code": code}).json()["token"]

    db = sqlite3.connect(tmp_path / "test.db")
    try:
        stored_codes = [r[0] for r in db.execute("SELECT code_hash FROM otp_codes")]
        stored_tokens = [r[0] for r in db.execute("SELECT token_hash FROM sessions")]
    finally:
        db.close()

    assert stored_codes and code not in stored_codes
    assert stored_tokens and token not in stored_tokens
    assert (tmp_path / "test.db").read_bytes().find(code.encode()) == -1
