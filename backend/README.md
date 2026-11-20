# content_feed backend

FastAPI + SQLite skeleton. Right now it does one thing: **phone sign-in with a
6-digit one-time code**, the way most African apps work.

**SMS is mocked.** The code is written to the server console instead of being
texted, so there are no provider keys to get and none in this repo.

## Run it

Requires Python 3.10+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is on <http://127.0.0.1:8000>, interactive docs on
<http://127.0.0.1:8000/docs>. The database file `backend/feed.db` is created on
first use and is git-ignored.

## Sign in end to end

```bash
# 1. Ask for a code
curl -X POST http://127.0.0.1:8000/auth/otp \
  -H 'Content-Type: application/json' -d '{"phone":"08012345678"}'
# {"phone":"+2348012345678","expires_in":300,"max_attempts":5}
```

The code is now on the server console, where the SMS would have been:

```
INFO content_feed.auth SMS to +2348012345678: Your content_feed code is 351480. It expires in 5 minutes.
```

```bash
# 2. Trade the code for a token (creates the account the first time)
curl -X POST http://127.0.0.1:8000/auth/verify \
  -H 'Content-Type: application/json' -d '{"phone":"08012345678","code":"351480"}'
# {"token":"WguB5Y...","token_type":"bearer","user":{"id":1,...}}

# 3. Use the token
curl http://127.0.0.1:8000/auth/me -H 'Authorization: Bearer WguB5Y...'
# {"id":1,"phone":"+2348012345678","created_at":1795201501}
```

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/auth/otp` | Sends a 6-digit code to a phone number (logged, not texted) |
| `POST` | `/auth/verify` | Checks the code, creates the account if new, returns a bearer token |
| `GET` | `/auth/me` | The signed-in user, from `Authorization: Bearer <token>` |
| `GET` | `/health` | Liveness check |

Phone numbers are stored in one canonical E.164 form, so `08012345678`,
`+234 801 234 5678` and `2348012345678` are all the same account.

Other routers can depend on `app.auth.current_user` to require a signed-in user.

## Rules

- A code **expires after 5 minutes**.
- A code allows **5 wrong attempts**, then it is dead and you need a new one.
- Asking for a new code retires the previous one, so attempts cannot be
  stacked, and a code is single-use.
- Codes are stored as an HMAC-SHA256 hash and tokens as a SHA-256 hash; neither
  is ever written to the database in the clear, and the code never appears in
  an HTTP response.

## Tests

```bash
cd backend
pytest
```

Covers the whole sign-in flow, expiry, the attempt limit, phone
normalization, token checks and what ends up in the database.

## Settings

All optional, read from the environment.

| Variable | Default | Meaning |
|---|---|---|
| `FEED_DB` | `backend/feed.db` | SQLite file |
| `FEED_SECRET` | per-database random | Key used to hash one-time codes |
| `FEED_OTP_TTL_SECONDS` | `300` | How long a code is valid |
| `FEED_OTP_MAX_ATTEMPTS` | `5` | Wrong attempts allowed per code |
| `FEED_DEFAULT_CALLING_CODE` | `+234` | Calling code for local-format numbers |
| `FEED_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `FEED_LOG_LEVEL` | `INFO` | Must stay at `INFO` to see mocked codes |

In production set `FEED_SECRET` and a real `FEED_CORS_ORIGINS`. Keep secrets in
the environment, never in this repo.

## Connecting the web app

Point `apiUrl` in [`web/config.js`](../web/config.js) at this server, e.g.
`apiUrl: "http://127.0.0.1:8000"`. The web app does not have a sign-in screen
yet, so for now that only affects the endpoints it already calls.

## Not done yet

A real SMS provider, profiles, and a resend cooldown or per-number rate limit
on `POST /auth/otp` (nothing stops a caller requesting codes in a loop today).
