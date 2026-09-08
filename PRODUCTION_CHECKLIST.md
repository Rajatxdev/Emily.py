# Emily v2 Implementation Checklist

## Stage 1 — Stability

- [x] Atomic daily quota reset
- [x] Free = 50 AI replies/day
- [x] Credit = 1 AI generation
- [x] Failed AI generation refunds allowance
- [x] Secure required environment variables
- [x] Telegram rate limiter
- [x] Callback handling fixed
- [x] Central error classification + logging

## Stage 2 — Memory

- [x] Recent conversation history
- [x] Persistent user memory
- [x] Automatic capture of common facts
- [x] `/memory`
- [x] `/remember`
- [x] `/forget`
- [x] `/forget_all`

## Stage 3 — Personality

- [x] Bestie
- [x] Study
- [x] Roast
- [x] Calm
- [x] Coding
- [x] Hype

## Stage 4 — Group intelligence

- [x] Mention/reply-to-Emily behavior
- [x] Group-visible history
- [x] `/group_summary`
- [x] `/group_moments on|off`

## Stage 5 — Emily Moments

- [x] `/moment`
- [x] AI-generated tiny prompts/challenges

## Stage 6 — Operations

- [x] In-bot admin panel
- [x] Stats
- [x] User lookup
- [x] Ban/unban
- [x] Credits
- [x] Free/premium plan flag
- [x] Error viewer
- [x] CSV export
- [x] Announcements
- [x] Lightweight GitHub CI

## Deliberately not included

PostgreSQL, Redis, FastAPI, CDN, microservices, vector database and payment infrastructure.
