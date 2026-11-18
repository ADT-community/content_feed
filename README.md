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

## Web app (`web/`)

A mobile web app built around a full-screen, swipe-up video feed:

- **Feed:** videos autoplay as you swipe; tap to pause, double-tap to like, sound toggle. Comment, share, and open a creator's profile to follow them.
- **Tips and gifts:** the gift button opens gifts (🌳 Baobab ₦200 → 👑 Crown ₦5,000) or plain tips, paid from mobile money (OPay, PalmPay, MTN MoMo, M-Pesa, Airtel Money). It shows exactly what the creator receives (80% by default).
- **Post:** record or pick a video (up to 60 s / 50 MB), add a caption, post it to the top of the feed.
- **Earnings:** balance, tips this week, recent supporters, your posts, and **cash out to mobile money**.
- **Safety from day one:** every video has a **Report** option (spam, sexual content, violence, hate, child safety, false information); reported videos are hidden right away pending review.

Out of the box it runs in **demo mode** with fictional creators and generated placeholder videos (`web/data.js`, `web/media/`). Uploads stay on the phone, and tips and payouts are simulated. Settings such as the platform fee, minimum payout and upload limits live in `web/config.js`; set `apiUrl` there to connect a backend.

**Try it:** serve `web/` (for example `npx serve web`) and open it on a phone.

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

- [x] Web prototype: feed, tips and gifts, profiles, posting, earnings, reporting (`web/`)
- [ ] Choose a video hosting approach and estimate cost per 1,000 views (research bounty)
- [ ] Data model: users, creators, posts, follows, tips, payouts
- [ ] Sign up and creator profiles
- [ ] Video upload and playback
- [ ] Feed: following + simple trending
- [ ] Tipping flow with a payment sandbox
- [ ] Report button and moderation queue

## Contribute

See the [website](https://adt-community.github.io) for how bounties and goals work, then pick an open issue in this repo.
