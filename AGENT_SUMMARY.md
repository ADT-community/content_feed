# Backend skeleton and phone sign-in (OTP, SMS mocked) — issue #5

## Root cause

Not a bug: this is the repo's first backend. Before this commit `content_feed`
was a static web app only (`web/`), with `web/config.js` carrying an empty
`apiUrl` and a comment promising a backend that did not exist. There was no
`backend/`, no server code, no dependency manifest and no test suite anywhere
in the repo. Users had no way to identify themselves, which blocks everything
downstream (profiles, follows, tips, payouts) because none of it has an account
to attach to.

## Fix

A new `backend/` holding a FastAPI + SQLite skeleton whose single feature is
phone sign-in with one-time codes.

| File | Role |
|---|---|
| `backend/app/main.py` | App, CORS, `/health`, router wiring |
| `backend/app/db.py` | SQLite connection, schema, runtime secret |
| `backend/app/auth.py` | `/auth/otp`, `/auth/verify`, `/auth/me`, all OTP logic |
| `backend/conftest.py` | Test fixtures (tmp database, mocked-SMS inbox) |
| `backend/tests/test_auth.py` | 29 cases |
| `backend/README.md` | Run instructions, endpoints, settings |
| `backend/requirements.txt`, `backend/.gitignore` | Deps, ignore local `*.db`/`.env` |

Reasoning behind the choices that were not spelled out in the issue:

- **FastAPI over Express.** The issue allowed either. The repo has no
  `package.json` and no JS toolchain, so Python added nothing to the root of
  the repo; SQLite is the standard library, so storage cost zero dependencies.
- **SMS is one function.** `send_otp_sms()` in `app/auth.py` logs the code and
  is the only thing a real provider has to replace. Nothing else in the flow
  knows how a code is delivered.
- **The code never leaves over HTTP.** `POST /auth/otp` returns only
  `{phone, expires_in, max_attempts}`. A code that came back in the response
  would defeat the point of sending it to a phone, and it is an easy thing to
  leave switched on by accident.
- **Codes and tokens are stored hashed** — codes as HMAC-SHA256 keyed on a
  secret and bound to the phone they were sent to, tokens as SHA-256. A code
  issued for one number cannot be redeemed on another.
- **A new code retires the previous one.** Otherwise stacking codes would let a
  caller spend 5 attempts per code against the same account, and the attempt
  limit would mean much less than it looks like.
- **The attempt is counted before it is checked**, so an error mid-verify
  cannot hand out a free guess.
- **Phones are normalized to E.164** (`08012345678`, `+234 801 234 5678` and
  `2348012345678` all collapse to `+2348012345678`). The web app already strips
  non-digits before sending numbers, and without one canonical key the same
  person would collect several accounts. Local `0…` numbers get
  `FEED_DEFAULT_CALLING_CODE`, default `+234` (Nigeria is the launch market in
  the README).
- **`GET /auth/me` was added** beyond the literal ask because a token nothing
  accepts cannot be shown to work end to end. Its dependency,
  `app.auth.current_user`, is what later routers (tips, posts) should depend on
  to require a signed-in user. It returns id/phone/created-at only — profiles
  are explicitly out of scope.
- **CORS is on** (`FEED_CORS_ORIGINS`, default `*` for dev) because `web/` is
  served from a different origin than the API.
- **No secret is committed.** `FEED_SECRET` comes from the environment; with it
  unset, a random secret is generated once per database file rather than
  falling back to a hard-coded default in a public repo.

Scope kept to the issue: no SMS provider, no profiles, no change to any
existing behaviour. `web/` is untouched; the only edit outside `backend/` is a
9-line README section pointing at it.

## Verification

Tests — from `backend/`, `pip install -r requirements.txt && pytest`:

```
29 passed in 2.13s
```

They cover the full flow (`/auth/otp` → code read out of the mocked SMS log →
`/auth/verify` → `/auth/me`), the 5-minute expiry from both sides of the
boundary, the 5-attempt limit and the 429 that follows it, a correct code being
refused once the budget is spent, a fresh code restoring it, single-use codes,
code/phone binding, phone normalization, six malformed numbers, five bad
`Authorization` headers, and an assertion that neither the code nor the token
appears anywhere in the database file.

Also driven for real against `uvicorn app.main:app` over HTTP, which is how the
"sign-in works end to end" box was checked rather than by trusting TestClient:

```
POST /auth/otp  {"phone":"0801 234 5678"}
  → {"phone":"+2348012345678","expires_in":300,"max_attempts":5}
  console: SMS to +2348012345678: Your content_feed code is 351480. It expires in 5 minutes.
POST /auth/verify  wrong code  → 400 {"detail":"Incorrect code. 4 attempts left."}
POST /auth/verify  351480      → 200 token WguB5Y9dJ5I5…
GET  /auth/me      Bearer …    → 200 {"id":1,"phone":"+2348012345678",…}
GET  /auth/me      no header   → 401
POST /auth/verify  351480 again → 400 (single use)
attempts 1–5 on a fresh code   → 400, "4/3/2/1/0 attempts left"
attempt 6                      → 429 "Too many wrong attempts."
```

`grep -rniE "twilio|africastalking|termii|api[_-]?key|secret_key|sk_live|auth_token" backend`
returns nothing, and `*.db`/`.env` are git-ignored.

There is no repo-wide test, lint or typecheck setup to run (no `package.json`,
no TypeScript; `.github/workflows/pages.yml` only deploys `web/`).

## Concerns for a reviewer

1. **I did not `git add -A`.** Seven files (`LICENSE`, `.github/workflows/pages.yml`,
   `web/*`) were already modified in the working tree before I started, and the
   diff is pure CRLF line-ending churn — 1,012 lines across files this task
   does not touch. I staged only `backend/`, `README.md` and `BOUNTY_TASK.md`;
   the churn is still sitting unstaged. Deliberate, so the PR stays readable.
2. **File count.** The stop condition mentions ~5 files; this commit touches
   11. The issue asks for a whole new `backend/` with tests and run
   instructions, so a new directory is the deliverable rather than scope creep.
   Only one pre-existing file (`README.md`, 9 lines) was modified.
3. **`POST /auth/otp` has no rate limit.** Anyone can request codes for a
   number in a loop — SMS-pumping cost, and a nuisance to the person who owns
   the number. Out of scope here (noted in `backend/README.md`) but it should
   land before a real provider does; a resend cooldown plus a per-number and
   per-IP cap is the usual shape.
4. **Tokens never expire** and there is no sign-out. The `sessions` table has
   `created_at`, so adding a TTL and a `DELETE /auth/session` later is cheap.
5. **`FEED_SECRET` should be set in production.** With it unset the per-database
   secret lives in the same SQLite file as the code hashes, so a database leak
   would expose both; 6-digit codes are brute-forceable once the key is known.
   The 5-minute window and the attempt limit are the real defences.
6. **Competition.** PR #23 ("Add FastAPI OTP auth skeleton") already targets
   issue #5 — one open attempt, below the 3+ threshold to stop, but a
   maintainer will want to pick one.
7. `BOUNTY_TASK.md` and this file are task scaffolding, not product code — drop
   them if they should not be in the PR.
8. Two pinned dev conveniences worth a glance: the installed Starlette prefers
   `httpx2` and warns about `httpx` (harmless, from the library not this code),
   and `HTTPException(422, …)` uses the literal status code because Starlette
   renamed its constant for it between versions.
