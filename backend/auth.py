import os
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db, OTPCode, Base, engine

router = APIRouter()

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Configure logger
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

class OTPRequest(BaseModel):
    phone: str = Field(..., regex=r"^\+?[0-9]{7,15}$")

class VerifyRequest(BaseModel):
    phone: str = Field(..., regex=r"^\+?[0-9]{7,15}$")
    code: str = Field(..., min_length=6, max_length=6)

def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))

def _create_jwt(phone: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": phone, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@router.post("/otp", status_code=status.HTTP_200_OK)
async def send_otp(request: OTPRequest, db: Session = Depends(get_db)):
    code = _generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    # Upsert logic – delete any existing entry for the phone
    db.query(OTPCode).filter(OTPCode.phone == request.phone).delete()
    otp_entry = OTPCode(
        phone=request.phone,
        code=code,
        expires_at=expires_at,
        attempts=0,
    )
    db.add(otp_entry)
    db.commit()
    logger.info(f"OTP for {request.phone}: {code}")
    return {"detail": "OTP sent (logged)"}

@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_otp(request: VerifyRequest, db: Session = Depends(get_db)):
    otp_entry: Optional[OTPCode] = (
        db.query(OTPCode)
        .filter(OTPCode.phone == request.phone)
        .first()
    )
    if not otp_entry:
        raise HTTPException(status_code=400, detail="OTP not requested for this phone")

    # Check expiration
    if datetime.utcnow() > otp_entry.expires_at:
        db.delete(otp_entry)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired")

    # Check attempt limit
    if otp_entry.attempts >= 5:
        db.delete(otp_entry)
        db.commit()
        raise HTTPException(status_code=429, detail="Maximum verification attempts exceeded")

    if otp_entry.code != request.code:
        otp_entry.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Successful verification – clean up and issue token
    db.delete(otp_entry)
    db.commit()
    token = _create_jwt(request.phone)
    return {"access_token": token, "token_type": "bearer"}
