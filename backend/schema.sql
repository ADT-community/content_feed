-- backend/schema.sql
-- PostgreSQL schema for content feed

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- creators are a subset of users; we store extra info
CREATE TABLE creators (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    bio TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    creator_id BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- follow relationship: user follows a creator
CREATE TABLE follows (
    follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    followed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, creator_id)
);

-- tips: a user tips a creator for a post
CREATE TABLE tips (
    id BIGSERIAL PRIMARY KEY,
    tipper_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    gross_amount BIGINT NOT NULL,          -- amount in minor units (e.g., cents)
    platform_fee BIGINT NOT NULL,          -- fee taken by platform
    creator_amount BIGINT NOT NULL,        -- amount received by creator
    tipped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (gross_amount = platform_fee + creator_amount)
);

-- payouts: payments from platform to creators
CREATE TABLE payouts (
    id BIGSERIAL PRIMARY KEY,
    creator_id BIGINT NOT NULL REFERENCES creators(user_id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,                -- amount in minor units
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    paid_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (creator_id, period_start, period_end)
);

-- Indexes for feed: retrieve recent posts from creators a user follows
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_follows_creator_id ON follows(creator_id);
CREATE INDEX idx_tips_creator_id ON tips(creator_id);
