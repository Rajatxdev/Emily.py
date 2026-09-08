# Emily Telegram AI Bot

Emily is a lightweight Telegram AI companion and group assistant built for simple Termux use.

## Product rules

**Free:**  
50 AI replies/day

**Credits:**  
1 credit = 1 AI generation

**Premium later:**  
higher quota + special features

Premium is only an internal plan flag for now; there is no payment system.

## Stack

Python + python-telegram-bot 22.x + OpenAI Python SDK + SQLite + Pytest.

No PostgreSQL, Redis, FastAPI, CDN, microservices, vector database or payment backend is required.

## Features

- Recent conversation memory
- User-controlled long-term memory
- Automatic capture of simple facts such as name/study/likes
- Personality modes: bestie, study, roast, calm, coding, hype
- Group-safe mention/reply behavior
- Group-visible history and `/group_summary`
- `/moment` creative Emily Moments
- SQLite quotas and one-credit-per-generation accounting
- Failed AI generations are refunded
- Telegram-only admin control center
- User lookup, ban/unban, credits, plan flag, errors, CSV export and announcements
- Automatic user migration from the old `alisa_bot.db` into `emily.db`
- Lightweight GitHub CI checks

## Termux setup

```bash
pkg update
pkg install python git

git clone https://github.com/Rajatxdev/Emily.py.git
cd Emily.py
python -m pip install -r requirements.txt

export TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
export ADMIN_USER_ID="YOUR_NUMERIC_TELEGRAM_USER_ID"

python emily_ai_bot.py
```

Do not commit secrets.

## Useful commands

User: `/help`, `/mode`, `/memory`, `/remember key = value`, `/forget key`, `/forget_all`, `/quota`, `/moment`, `/group_summary`, `/group_moments on|off`, `/privacy`, `/about`.

Admin: `/admin`, `/stats`, `/user_info <id>`, `/ban_user <id>`, `/unban_user <id>`, `/add_credits <id> <amount>`, `/set_plan <id> free|premium`, `/errors`, `/export_data`, `/announce <message>`.

## Testing

```bash
python -m py_compile emily_ai_bot.py
pytest -q
```
