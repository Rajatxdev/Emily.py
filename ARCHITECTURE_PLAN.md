# Emily v2 Architecture

```text
Telegram
   ↓
One Python process
   ├─ AI
   ├─ Memory
   ├─ Quota / credits
   ├─ Group features
   └─ Admin panel
   ↓
SQLite
```

## Rules

Free: 50 AI replies/day  
Credits: 1 credit = 1 AI generation  
Premium later: higher quota + special features

## AI context

Small recent history + saved memories + current request + current mode.

## Storage

SQLite remains the intended database for this project's size. The old `alisa_bot.db` user data is migrated automatically into `emily.db` when the new database is empty.

## Deliberately excluded

PostgreSQL, Redis, FastAPI, CDN, microservices, vector database and payment infrastructure.
