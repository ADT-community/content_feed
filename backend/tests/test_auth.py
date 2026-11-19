import asyncio
import time
from datetime import datetime, timedelta

import pytest
import httpx
from fastapi import status

from ..main import app

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def client():
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

@pytest.mark.anyio
async def test_successful_flow(client: httpx.AsyncClient, caplog):
    phone = "+12345678901"
    # Request OTP
    resp = await client.post("/auth/otp", json={"phone": phone})
    assert resp.status_code == status.HTTP_200_OK
    # Extract OTP from logs
    otp_log = None
    for record in caplog.records:
        if phone in record.getMessage():
            otp_log = record.getMessage().split(":")[-1].strip()
            break
    assert otp_log is not None, "OTP not logged"
    # Verify OTP
    resp = await client.post("/auth/verify", json={"phone": phone, "code": otp_log})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.anyio
async def test_expired_otp(client: httpx.AsyncClient, caplog):
    phone = "+19876543210"
    await client.post("/auth/otp", json={"phone": phone})
    otp_log = None
    for record in caplog.records:
        if phone in record.getMessage():
            otp_log = record.getMessage().split(":")[-1].strip()
            break
    assert otp_log is not None
    # Fast‑forward time by monkey‑patching datetime (simplified by waiting 6 minutes)
    await asyncio.sleep(0)  # no real wait; rely on backend expiry check
    # Manually set the DB entry to be expired for the test
    from backend.database import SessionLocal, OTPCode
    db = SessionLocal()
    entry = db.query(OTPCode).filter(OTPCode.phone == phone).first()
    entry.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()
    # Attempt verification
    resp = await client.post("/auth/verify", json={"phone": phone, "code": otp_log})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "OTP expired"

@pytest.mark.anyio
async def test_attempt_limit(client: httpx.AsyncClient, caplog):
    phone = "+11223344556"
    await client.post("/auth/otp", json={"phone": phone})
    otp_log = None
    for record in caplog.records:
        if phone in record.getMessage():
            otp_log = record.getMessage().split(":")[-1].strip()
            break
    assert otp_log is not None
    # Use wrong code 5 times
    for i in range(5):
        resp = await client.post("/auth/verify", json={"phone": phone, "code": "000000"})
        if i < 4:
            assert resp.status_code == status.HTTP_400_BAD_REQUEST
            assert resp.json()["detail"] == "Invalid OTP"
        else:
            # 5th attempt should hit limit
            assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert resp.json()["detail"] == "Maximum verification attempts exceeded"
