# OTP Auth Backend

A tiny FastAPI service that implements phone‑number based OTP sign‑in.

## Features
- `POST /auth/otp` – generate a 6‑digit OTP, store it with a 5‑minute TTL and a max‑attempt count of 5. The OTP is printed to the console (no real SMS).
- `POST /auth/verify` – validate the OTP, enforce expiration and attempt limits, and return a JWT token.

## Setup
```bash
# Clone the repo and cd into the project root
python -m venv venv
source venv/bin/activate  # on Windows use `venv\Scripts\activate`
pip install -r backend/requirements.txt
```

## Running the server
```bash
uvicorn backend.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## Testing
```bash
pytest -q backend/tests
```
All tests should pass.

## Environment variables
- `JWT_SECRET` – secret key used to sign JWTs (defaults to `dev-secret-key`).

## Notes
- This is a **mock** implementation – OTPs are logged, not sent via SMS.
- SQLite is used for simplicity; replace with a production DB as needed.
