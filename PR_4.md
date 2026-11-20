Closes #4

## Summary

Implements a working zero-dependency Python backend in `backend/` for phone sign-in, creator profiles and follows, plus the full PostgreSQL data model for the product.

## Changes

- **`backend/schema.sql`** — canonical PostgreSQL schema with all six required tables (`users`, `creators`, `posts`, `follows`, `tips`, `payouts`) plus `login_codes` and `sessions`. Money is integer **minor units** (kobo), never floats; each tip stores its own `platform_fee_minor` / `creator_amount_minor` split enforced by a `CHECK (fee + creator = amount)` constraint. Unique handles are enforced by both a `CHECK` format rule and a `UNIQUE` constraint; foreign keys, cascade deletes and supporting indexes are included.
- **`backend/db.py`** — small DB adapter. Runs against PostgreSQL (`DATABASE_URL=postgresql://...`, needs `psycopg2`) or SQLite out of the box, with the same logical schema in both engines.
- **`backend/service.py`** — sign-in (6-digit code printed to console, 5-minute expiry, 5 attempts then lock), user/session creation, profile updates with handle validation and uniqueness (409 on a taken handle), public creator profiles with follower/post counts, and follow/unfollow.
- **`backend/api.py`** + **`backend/server.py`** — JSON HTTP layer with CORS: `GET /health`, `POST /auth/request-code`, `POST /auth/verify-code`, `GET|PUT /me/profile`, `GET /creators/{handle}`, `POST|DELETE /follow/{handle}`. Bearer-token auth; meaningful 400/401/404/409/429 errors.
- **`backend/tests/test_api.py`** — 13 tests covering every endpoint and all acceptance criteria.
- **`backend/README.md`** and root **`README.md`** — one-command run instructions, configuration table, PostgreSQL setup, API reference and curl examples.

## Acceptance criteria

- **All endpoints tested** — 13 tests cover health, request/verify code (success, expiry, wrong-code attempt lock, reuse, invalid input), profile read/update, creator lookup (404, public payload, following flag), follow/unfollow (idempotent, counts, self-follow rejected, auth required), and schema constraints.
- **Unique handles enforced** — pre-check returns `409 handle_taken` and the database `UNIQUE` constraint is the backstop; a test asserts both duplicate rejection and format validation.
- **Runs locally with one command** — `python -m backend` starts the server on `http://127.0.0.1:8000` with no external services or third-party packages.

## Verification

```
$ python -m unittest discover -s backend/tests -v
Ran 13 tests in 0.055s
OK
```

HTTP smoke test: `GET /health` → `{"ok":true,"service":"content_feed"}`.
`python -m compileall -q backend` — OK.

A live PostgreSQL server/`psql` is not available in this environment, so `schema.sql` was not loaded against a real instance here; it uses only core PostgreSQL syntax and is exercised via the equivalent SQLite schema in the tests.
