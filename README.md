# Emily Telegram AI Bot

Emily is a lightweight Telegram AI companion and group assistant designed for easy Termux use.

## Product rules

**Free:**  
50 AI replies/day

**Credits:**  
1 credit = 1 AI generation

**Premium later:**  
higher quota + special features

Premium is only an internal plan flag for now; there is no payment system.

## Stack

Python + python-telegram-bot 22.8 + SQLite + direct HTTPS calls to Gemini and OpenAI.

The runtime uses no OpenAI or Gemini SDK, keeping Termux installation small and avoiding unnecessary native build dependencies.

## AI reliability

Emily can use up to 6 API keys:

- `GEMINI_API_KEY_1` ... `GEMINI_API_KEY_4`
- `OPENAI_API_KEY_1` ... `OPENAI_API_KEY_2`

Each request is assigned to the least-busy healthy key. If a key is rate-limited, times out, or hits a provider/network failure, it is cooled down and another key is tried. Authentication failures disable only that key. Multiple Telegram updates can be processed concurrently.

Keys live only in environment variables; they are never stored in SQLite.

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
- Automatic migration from old `alisa_bot.db` user records into `emily.db`
- Lightweight GitHub CI checks

## Termux setup

```bash
pkg update
pkg install python git

git clone https://github.com/Rajatxdev/Emily.py.git
cd Emily.py
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a local `.env` file from `.env.example` and fill in your own values. Do not commit `.env`.

Start Emily with:

```bash
python run_emily.py
```

The official bot source remains `emily_ai_bot.py`; `run_emily.py` only wires the multi-key router and concurrent Telegram processing.

## Configuration

```text
TELEGRAM_TOKEN=...
ADMIN_USER_ID=...
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
GEMINI_API_KEY_3=...
GEMINI_API_KEY_4=...
OPENAI_API_KEY_1=...
OPENAI_API_KEY_2=...
GEMINI_MODEL=gemini-3.8-flash
OPENAI_MODEL=gpt-5-mini
```

Optional: `EMILY_AI_TIMEOUT`, `EMILY_KEY_COOLDOWN`, `EMILY_FREE_DAILY`, `EMILY_PREMIUM_DAILY`, `EMILY_HISTORY_MESSAGES`, `EMILY_MAX_MEMORIES`.

## Useful commands

User: `/start`, `/help`, `/mode`, `/memory`, `/remember key = value`, `/forget key`, `/forget_all`, `/quota`, `/moment`, `/group_summary`, `/group_moments on|off`, `/privacy`, `/about`.

Admin: `/admin`, `/stats`, `/user_info <id>`, `/ai_status`, `/ban_user <id>`, `/unban_user <id>`, `/add_credits <id> <amount>`, `/set_plan <id> free|premium`, `/errors`, `/export_data`, `/announce <message>`.

## Testing

Development-only dependencies are in `requirements-dev.txt`.

```bash
python -m pip install -r requirements-dev.txt
python -m py_compile emily_ai_bot.py ai_router.py run_emily.py
pytest -q
```