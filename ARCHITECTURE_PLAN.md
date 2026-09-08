# Emily Architecture

```text
Telegram
   ↓
Python bot (`emily_ai_bot.py`)
   ├─ Memory
   ├─ Quota / credits
   ├─ Group features
   └─ Admin
   ↓
AI router (`ai_router.py`)
   ├─ Gemini keys 1–4
   └─ OpenAI keys 1–2
   ↓
SQLite
```

## AI routing

Each Telegram AI request uses one healthy key at a time. The router chooses the least-busy key, so separate user requests can run concurrently instead of waiting for one shared key. If the selected key is rate-limited, times out, or has a provider/network failure, Emily immediately tries another configured key. Authentication failure disables only that key.

The API keys are kept in `.env`/environment variables only and are never stored in SQLite.

## Product rules

Free: 50 AI replies/day  
Credits: 1 credit = 1 AI generation  
Premium later: higher quota + special features

## Termux design

No OpenAI/Gemini SDK is required. `ai_router.py` uses Python HTTPS directly. `run_emily.py` is the lightweight launcher that loads `.env` and enables concurrent Telegram update processing.

## Storage

SQLite remains the permanent database choice for this project's expected size. The old `alisa_bot.db` user records are migrated automatically into `emily.db` when appropriate.

## Deliberately excluded

PostgreSQL, Redis, FastAPI, CDN, microservices, vector database and payment infrastructure.
