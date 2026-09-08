# Emily Production Checklist

## Stage 0 — Safety and correctness
- [ ] Secrets only through environment variables.
- [ ] Atomic quota/credit accounting.
- [ ] Correct callback-query handling.
- [ ] UTC timestamps stored consistently.
- [ ] External AI calls have timeout/retry policy.
- [ ] No raw prompts/responses in default logs.
- [ ] Telegram group trigger behavior is intentional.

## Stage 1 — Core quality
- [ ] Modular bot/service/data/AI boundaries.
- [ ] Conversation history with bounded context.
- [ ] User-controlled memory.
- [ ] Per-user mode and per-group settings.
- [ ] Model and token/cost telemetry.
- [ ] Graceful AI failure response.
- [ ] Admin audit log.

## Stage 2 — Product differentiation
- [ ] Emily Modes.
- [ ] Memory Cards.
- [ ] Group chemistry / lightweight games.
- [ ] Study mode and smart utilities.
- [ ] Voice messages.
- [ ] Image understanding.
- [ ] Scheduled Emily Moments.

## Stage 3 — Production backend
- [ ] Migrate SQLite to managed PostgreSQL.
- [ ] Add Alembic migrations.
- [ ] Add Redis only when distributed rate limiting/cache is needed.
- [ ] Optional FastAPI admin/API surface.
- [ ] Backup and restore test.

## Stage 4 — Operations
- [ ] GitHub Actions: Ruff + pytest + import/syntax checks.
- [ ] Sentry or equivalent error tracking.
- [ ] Health checks and uptime monitoring.
- [ ] Deployment with rollback.
- [ ] Cost and usage alerts.

## Stage 5 — Scale only if needed
- [ ] Queue worker for broadcasts/scheduled jobs.
- [ ] Multiple bot instances.
- [ ] Redis distributed coordination.
- [ ] CDN/object storage for media-heavy Mini App features.
