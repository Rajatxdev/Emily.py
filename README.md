# Emily Telegram AI Bot

Emily is a lightweight Telegram AI companion and group assistant designed to run comfortably in Termux.

## Stack

- Python
- python-telegram-bot 22.x
- OpenAI Python SDK
- SQLite
- Pytest

No PostgreSQL, Redis, FastAPI or separate backend service is required.

## Usage model

**Free:** 50 AI replies/day

**Credits:** 1 credit = 1 AI generation

**Premium later:** higher quota + special features

Premium is only an internal plan flag for now; there is no payment system.

## Main features

- Persistent recent conversation memory
- User-controlled long-term memory
- `/memory`, `/remember`, `/forget`, `/forget_all`
- Personality modes: bestie, study, roast, calm, coding, hype
- Group-safe mention/reply behavior
- `/group_summary` for recent group-visible conversation
- `/moment` for creative Emily Moments
- SQLite quota + credit accounting
- Admin controls inside Telegram
- User bans, credits, plans, announcements and CSV export
- Error classification and an admin `/errors` view
- Small CI test suite
- Automatic migration of the old `alisa_bot.db` user table into `emily.db`

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

For a persistent Termux shell, put the three `export` lines in your shell startup file or use your preferred environment-variable manager. Do not commit secrets.

## Basic commands

User: `/help`, `/mode`, `/memory`, `/remember key = value`, `/forget key`, `/forget_all`, `/quota`, `/moment`, `/group_summary`, `/privacy`, `/about`.

Admin: `/admin`, `/stats`, `/user_info <id>`, `/ban_user <id>`, `/unban_user <id>`, `/add_credits <id> <amount>`, `/set_plan <id> free|premium`, `/errors`, `/export_data`, `/announce <message>`.

## Testing

```bash
python -m py_compile emily_ai_bot.py
pytest -q
```

The CI workflow runs the same two checks on pushes and pull requests.
