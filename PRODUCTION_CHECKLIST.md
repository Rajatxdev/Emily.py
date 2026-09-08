# Emily v2 Status

## Implemented

- [x] Free: 50 AI replies/day
- [x] Credits: 1 credit = 1 AI generation
- [x] Premium later: higher quota + special features (plan flag only)
- [x] Atomic quota handling and daily reset
- [x] Failed AI generation refund
- [x] SQLite persistence
- [x] Recent conversation memory
- [x] Long-term user memory with inspect/delete controls
- [x] Automatic simple memory capture
- [x] Bestie / Study / Roast / Calm / Coding / Hype modes
- [x] Group mention/reply behavior
- [x] Group-visible summary
- [x] Emily Moments
- [x] In-bot admin panel
- [x] User lookup, ban/unban, credits, plan flag
- [x] Error classification and `/errors`
- [x] CSV export and announcements
- [x] Legacy user migration from `alisa_bot.db`
- [x] Lightweight GitHub CI

## Intentionally kept out

PostgreSQL, Redis, FastAPI, CDN, microservices, vector database and payment infrastructure.

## Next stage after real Termux run

Live integration testing with the actual Telegram bot and OpenAI key, followed by fixing any environment-specific issues discovered during runtime.
