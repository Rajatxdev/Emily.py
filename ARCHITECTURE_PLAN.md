# Emily v2 Architecture

Keep Emily intentionally small.

```text
Telegram
   ↓
Python bot (one process)
   ├─ AI brain
   ├─ Memory
   ├─ Quota / credits
   ├─ Group features
   └─ Admin panel
   ↓
SQLite
```

## Storage

One SQLite database: `emily.db`.

Tables: `users`, `messages`, `memories`, `roasts`, `group_settings`, `errors`.

The old `alisa_bot.db` user records are migrated automatically on first startup when the new database is empty.

## AI context

Each generation uses:

```text
small recent history
+
relevant saved memories
+
current request
+
current Emily mode
```

No vector database is needed at this size.

## Product rules

- Free: 50 AI replies/day
- Credits: 1 credit = 1 AI generation
- Premium later: higher quota + special features

A failed AI generation is refunded so a temporary provider/network failure does not consume the user's allowance.

## Scaling decision

Do not add PostgreSQL, Redis, FastAPI, CDN or microservices unless a real requirement appears. SQLite remains the intended long-term database for this project's expected size.
