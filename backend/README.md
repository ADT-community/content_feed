# content_feed backend (v1)

Accounts, creator profiles and follows. No third-party packages are required —
only Python 3.10+ and the standard library.

## Run locally — one command

```bash
python -m backend
```

The server listens on `http://127.0.0.1:8000` and prints every 6-digit login code
to the console. Data is stored in `content_feed.db` (SQLite) in the current
directory. Configuration via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address |
| `DATABASE_URL` | `sqlite:///./content_feed.db` | `sqlite:///...` or `postgresql://...` |
| `DEV_FIXED_CODE` | unset | Pin the code for manual/testing convenience |

### PostgreSQL

The canonical data model lives in [`schema.sql`](schema.sql) — apply it with:

```bash
psql "$DATABASE_URL" -f backend/schema.sql
pip install psycopg2-binary
DATABASE_URL=postgresql://user:pass@host/db python -m backend
```

Money is stored in **minor units** (integer kobo/cents), never floats. Each tip
stores its own `platform_fee_minor` and `creator_amount_minor` split, enforced by
a `CHECK` constraint so historical splits cannot change. Unique handles are
enforced by a `UNIQUE` constraint.

## Tests

```bash
python -m unittest discover -s backend/tests -v
```

Tests use an in-memory SQLite database, so they need no running server or
external service.

## API

All responses are JSON. Authenticated endpoints expect
`Authorization: Bearer <token>`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | no | Health check |
| `POST` | `/auth/request-code` | no | `{ "phone": "+234..." }` → sends a 6-digit code (printed to console), valid 5 minutes |
| `POST` | `/auth/verify-code` | no | `{ "phone": "+234...", "code": "123456" }` → `{ "token", "user" }`; 5 wrong attempts void the code |
| `GET` | `/me/profile` | yes | Current user and creator profile (if any) |
| `PUT` | `/me/profile` | yes | `handle`, `display_name`, `bio`, `avatar_url`, `location` — claiming a handle creates the creator profile |
| `GET` | `/creators/{handle}` | no | Public creator profile with follower/post counts (includes `following` when authenticated) |
| `POST` | `/follow/{handle}` | yes | Follow a creator (idempotent) |
| `DELETE` | `/follow/{handle}` | yes | Unfollow (idempotent) |

Example:

```bash
curl -X POST localhost:8000/auth/request-code \
  -H 'Content-Type: application/json' -d '{"phone":"+2348012345678"}'
# read the code printed by the server, then:
curl -X POST localhost:8000/auth/verify-code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+2348012345678","code":"123456"}'
curl -X PUT localhost:8000/me/profile \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer TOKEN' \
  -d '{"handle":"ada","display_name":"Ada O."}'
curl localhost:8000/creators/ada
curl -X POST localhost:8000/follow/ada -H 'Authorization: Bearer TOKEN'
```

Errors are returned as `{"error": {"code": "...", "message": "..."}}` with a
meaningful HTTP status (`400`, `401`, `404`, `409`, `429`).

## Tables

`users`, `creators`, `posts`, `follows`, `tips`, `payouts` plus `login_codes` and
`sessions` for sign-in. Video and payments are out of scope for this task; the
`posts`, `tips` and `payouts` tables are part of the data model but are not
exposed by v1 endpoints.
