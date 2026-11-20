-- content_feed backend: canonical PostgreSQL schema.
--
-- Money is always stored in MINOR units (kobo/cents): INTEGER/BIGINT, never floats.
-- Every tip stores its own fee split, so historic splits survive fee changes.
-- Apply with:  psql "$DATABASE_URL" -f backend/schema.sql

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    phone         TEXT        NOT NULL UNIQUE,          -- E.164, e.g. +2348012345678
    display_name  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per creator. A creator is a user who claimed a handle.
CREATE TABLE IF NOT EXISTS creators (
    user_id      BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    handle       TEXT   NOT NULL UNIQUE CHECK (handle ~ '^[a-z0-9_]{3,30}$'),
    display_name TEXT   NOT NULL,
    bio          TEXT   NOT NULL DEFAULT '',
    avatar_url   TEXT,
    location     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL PRIMARY KEY,
    creator_id BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    caption    TEXT   NOT NULL DEFAULT '',
    media_url  TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_posts_creator_created ON posts (creator_id, created_at DESC);

CREATE TABLE IF NOT EXISTS follows (
    follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id  BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, creator_id),
    CHECK (follower_id <> creator_id)
);

CREATE INDEX IF NOT EXISTS idx_follows_creator ON follows (creator_id);

-- amount_minor = platform_fee_minor + creator_amount_minor (the split is immutable).
CREATE TABLE IF NOT EXISTS tips (
    id                   BIGSERIAL PRIMARY KEY,
    from_user_id         BIGINT NOT NULL REFERENCES users(id),
    to_creator_id        BIGINT NOT NULL REFERENCES creators(user_id),
    amount_minor         BIGINT NOT NULL CHECK (amount_minor > 0),
    currency             CHAR(3) NOT NULL DEFAULT 'NGN',
    platform_fee_minor   BIGINT NOT NULL CHECK (platform_fee_minor >= 0),
    creator_amount_minor BIGINT NOT NULL CHECK (creator_amount_minor >= 0),
    status               TEXT NOT NULL DEFAULT 'completed',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (platform_fee_minor + creator_amount_minor = amount_minor)
);

CREATE INDEX IF NOT EXISTS idx_tips_creator_created ON tips (to_creator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tips_from_user       ON tips (from_user_id);

CREATE TABLE IF NOT EXISTS payouts (
    id          BIGSERIAL PRIMARY KEY,
    creator_id  BIGINT NOT NULL REFERENCES creators(user_id),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    currency    CHAR(3) NOT NULL DEFAULT 'NGN',
    provider    TEXT   NOT NULL,       -- OPay, PalmPay, MTN MoMo, M-Pesa, ...
    destination TEXT   NOT NULL,
    status      TEXT   NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payouts_creator ON payouts (creator_id, created_at DESC);

-- Supporting tables for phone sign-in and sessions (not part of the public data model).
CREATE TABLE IF NOT EXISTS login_codes (
    id         BIGSERIAL PRIMARY KEY,
    phone      TEXT        NOT NULL,
    code       TEXT        NOT NULL CHECK (code ~ '^[0-9]{6}$'),
    expires_at TIMESTAMPTZ NOT NULL,
    attempts   INTEGER     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    consumed   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_codes_phone ON login_codes (phone, consumed, created_at DESC);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
