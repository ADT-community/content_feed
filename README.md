# content_feed — Creator social app

Social media that actually pays African creators.

Part of the [ADT community](https://adt-community.github.io). Contributors are paid through bounties and goals.

## The problem

Big platforms largely don't pay creators in most African countries, so huge audiences rarely turn into income.

## What we're building

- Short video and posts built for African audiences
- Creators earn from **tips, gifts, shopping and brand deals**, paid out by mobile money
- Launch in one or two countries and one niche (for example music or comedy), then grow

Ads pay little in many African markets, so this app earns from fans and brands paying creators directly, with the app taking a cut.

## How it earns

- A cut of tips, gifts and sales
- Brand-deal matching fees
- Later: premium creator tools

## Suggested stack

- **App:** React Native (Expo) or Flutter, Android first
- **Video:** a managed video/CDN service for upload, storage and streaming (costs matter, so plan this early)
- **Backend:** Postgres (e.g. Supabase) + object storage
- **Payments:** Flutterwave/Paystack and mobile money for payouts
- **Safety:** reporting tools and moderation queue from day one

## Goals

| Goal | Done when |
|---|---|
| **G1: MVP** | Creators can post short videos, users can follow and watch a feed |
| **G2: Tipping** | Fans can tip, creators can cash out to mobile money |
| **G3: Launch** | 100 creators and 5,000 users in the launch country |
| **G4: First revenue** | Platform earning from tips and gifts every month |

## Starter tasks (bounty candidates)

- [ ] Choose a video hosting approach and estimate cost per 1,000 views (research bounty)
- [ ] Data model: users, creators, posts, follows, tips, payouts
- [ ] Sign up and creator profiles
- [ ] Video upload and playback
- [ ] Feed: following + simple trending
- [ ] Tipping flow with a payment sandbox
- [ ] Report button and moderation queue

## Contribute

See the [website](https://adt-community.github.io) for how bounties and goals work, then pick an open issue in this repo.
