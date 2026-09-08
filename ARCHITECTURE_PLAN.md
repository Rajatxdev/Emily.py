# Emily — Production Architecture Plan

## Current assessment

The repository is a small Telegram bot with one monolithic Python file, SQLite persistence, OpenAI chat completions, simple quota/credits, group-only replies, and admin commands.

## Target architecture

Telegram Bot API
    -> python-telegram-bot application
    -> update routing / authorization / anti-spam guards
    -> service layer
       -> conversation memory
       -> quota + credits
       -> AI gateway
       -> admin operations
    -> PostgreSQL (production) / SQLite (development fallback)

Optional later:
    -> Redis for distributed rate limiting / short-lived cache
    -> FastAPI for a web admin dashboard, Mini App, and external API endpoints
    -> background worker only when jobs such as broadcasts, scheduled digests, or media processing become large enough to need one

## Deliberately not included yet

CDN, Kubernetes, Celery, Kafka, vector databases, and a separate frontend/backend deployment are not justified by the current 20–50 user scale unless a concrete requirement appears.

## Product priorities

1. Make every reply reliable and fast.
2. Give Emily real continuity instead of one-message prompts.
3. Make group behavior intentional: mention/reply triggers, per-group personality settings, and useful group tools.
4. Add opt-in memory with clear user controls.
5. Make quotas, credits, moderation, and admin operations atomic and auditable.
6. Track model usage/cost and failures.
7. Add high-value features before cosmetic complexity.

## Standout features

- Emily Modes: Bestie, Study Buddy, Roast Queen, Calm Mode, Group Host.
- Opt-in Memory Cards: nickname, language preference, interests, recurring preferences; `/memory`, `/forget`, and `/forget_all` controls.
- Conversation continuity with a bounded recent-history window plus compact user memory.
- Group-aware personality: inside-joke friendly but respectful; only answer when mentioned/replied to unless the group explicitly enables ambient mode.
- Emily Moments: occasional prompts, compliments, mini challenges, and weekly recap — configurable per chat.
- Smart utilities: summarize a discussion, translate, explain, create a poll, convert a request into a task/reminder.
- Fun layer: roast battles, trivia, mood/vibe check, streaks, and lightweight group games.
- Admin control center later: users, groups, quota, model usage, moderation, feature flags, broadcasts, health, and audit log.

## Security baseline

- Secrets must be environment variables; no placeholder credentials in executable defaults.
- Admin authorization must be explicit and checked for every privileged operation.
- Treat Telegram user/chat IDs as identifiers, not display names.
- Keep personal message retention minimal and configurable.
- Never log raw user prompts or model responses by default.
- Add request timeouts, bounded retries, and backoff for external APIs.
- Make quota/credit consumption atomic to prevent double-spending under concurrent messages.
- Do not let model output execute arbitrary application actions without validated tool permissions.

## Deployment recommendation

Start with one long-running worker/container. Use managed PostgreSQL for production persistence. Add Redis only when multiple bot instances or distributed throttling are actually required. Add FastAPI when a web admin/Mini App becomes a real product surface.

## CI/CD

GitHub Actions should run syntax checks, linting, unit tests, and import checks on every pull request. Deployment should happen only after those checks pass. Secrets stay in the hosting provider, not in Git.
