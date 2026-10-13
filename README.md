# Alisa — Telegram AI Companion

[![Alisa checks](https://github.com/Rajatxdev/Emily.py/actions/workflows/test.yml/badge.svg)](https://github.com/Rajatxdev/Emily.py/actions/workflows/test.yml)

> A small Telegram AI bot I built to make chatting, group help, memory, and a few fun features feel simple and personal.

Alisa is a lightweight AI companion that runs directly through Telegram. It can chat with you, remember useful details, change personality, help in groups, and give the admin a private control center.

It is intentionally a **small project**. There is no separate web dashboard, no large backend, and no complicated infrastructure.

## ✨ What can Alisa do?

- 💬 **AI chat** — talk naturally in Telegram.
- 🎭 **6 personalities** — Bestie, Study, Roast, Calm, Coding, Hype.
- 🧠 **Memory** — save, review, and delete memories, including simple facts recognized from messages.
- 👥 **Group assistant** — respond when mentioned or replied to.
- 🧾 **Group recap** — summarize recent interactions with Alisa in a group.
- ✨ **Alisa Moments** — small creative prompts and fun interactions.
- 💳 **Usage system** — 50 free AI replies per day + 1 credit per extra generation.
- 🚫 **Moderation** — admin can ban/unban users and the affected user is clearly told what happened.
- 📊 **Admin Control Center** — users, AI keys, usage, errors, moderation, broadcasts, data and health.
- ⚡ **Fast processing** — concurrent Telegram updates, non-blocking database work, and multiple AI keys with automatic failover.

## 🧠 How it works

The flow is simple:

**Telegram → Alisa → AI provider → Telegram**

SQLite stores the small amount of information Alisa needs, such as user profiles, usage, memories, conversation history, and errors.

For AI requests, Alisa can use up to 6 configured API keys:

- 4 Gemini keys
- 2 OpenAI keys

Alisa chooses a healthy/less-busy key and switches to another when a provider or key fails.

## 🛠️ Built with

- Python
- `python-telegram-bot`
- SQLite
- Direct HTTPS calls to Gemini and OpenAI
- Termux-friendly runtime

The project intentionally avoids heavyweight SDKs and extra backend services so it stays easy to run and maintain.

## 📁 Project structure

```text
Emily.py/
├── emily_ai_bot.py     # Core bot and main features
├── run_emily.py        # Recommended launcher + performance wiring
├── ai_router.py        # Gemini/OpenAI key pool and failover
├── ui_controller.py    # User and admin Telegram menus
├── admin_users.py      # User profiles and directory
├── admin_dashboard.py  # Admin statistics
├── admin_data.py       # Database tools
├── .env.example        # Configuration template
├── requirements.txt    # Runtime dependency
├── test_emily_ai_bot.py # Bot/database unit tests
├── requirements-dev.txt # Offline test dependency
├── tests/
│   └── test_ai_router.py # Router unit tests
└── .github/
    └── workflows/
        └── test.yml # Automated compile + test checks
```

The repository and core filename still use `Emily.py` / `emily_ai_bot.py` for compatibility. **The actual bot name shown to users is Alisa.**

## 🚀 Run it

### Termux

```bash
pkg update
pkg install python git

git clone https://github.com/Rajatxdev/Emily.py.git
cd Emily.py
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your private environment file and edit it:

```bash
cp .env.example .env
nano .env
```

Create your Telegram bot using `@BotFather` and get your numeric Telegram user ID (for example, from a Telegram ID helper bot). Get at least one API key from Gemini or OpenAI, then add those values to `.env`.

Set your Telegram bot token, your numeric Telegram user ID as `ADMIN_USER_ID`, and at least one AI API key. **Leave unused AI key slots blank**; don't leave the template's placeholder text in them.

Then start Alisa:

```bash
python run_emily.py
```

Keep `.env` private. Never commit API keys or your Telegram bot token.

## ⚙️ Configuration

Required values are simple:

```env
TELEGRAM_TOKEN=your_bot_token
ADMIN_USER_ID=your_telegram_user_id

# Add at least one AI key. Keep unused slots blank.
GEMINI_API_KEY_1=your_gemini_key
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=

OPENAI_API_KEY_1=
OPENAI_API_KEY_2=
```

Model names can be left empty. Alisa discovers a usable text-generation model for each provider key automatically. Individual model overrides are also supported with names such as `GEMINI_MODEL_1` or `OPENAI_MODEL_1`.

Optional settings include the AI timeout, key cooldown, free/premium quota, conversation history size, memory limit, and SQLite database filename.

## 👤 User commands

```text
/start
/help
/mode
/memory
/remember key = value
/forget key
/forget_all
/quota
/moment
/group_summary
/group_moments on|off
/privacy
/about
/myid
```

In a group, Alisa normally answers when she is mentioned or when someone replies to her.

## 🛠 Admin

Only the configured admin can open the private Control Center.

```text
/admin
/stats
/ai_status
/users
/find_user <id|username>
/user_info <id>
/ban_user <id> [reason]
/unban_user <id>
/add_credits <id> <amount>
/set_plan <id> free|premium
/errors
/export_data
/announce <message>
```

The Telegram admin menu also provides buttons for user profiles, moderation, AI-key controls, dashboard statistics, error monitoring, data tools, and system health.

## 🔐 Data and privacy

Alisa keeps user profiles, usage, recent chat history, saved memories, group settings, and recorded errors in a local SQLite database. The recent conversation context and your current message are sent to the configured AI provider when Alisa generates a reply.

Memory can be saved with `/remember`; Alisa also recognizes a small set of simple phrases (such as “my name is” and “I like”) and may save them automatically. Review memories with `/memory`, remove one with `/forget`, or clear them with `/forget_all`.

API keys are read from `.env`, not stored in SQLite. Keep `.env` private and protect the device/server and database file. SQLite data is not encrypted by this bot. Review the privacy terms of your chosen AI provider before using it with sensitive information.

There is no payment system yet. `premium` is currently just an internal plan flag for future use.

## ⚡ Performance and reliability

The bot is designed to stay responsive even when several users message it around the same time.

- Multiple Telegram updates can run concurrently.
- Slow SQLite work is moved away from the main Telegram event loop.
- AI requests use a multi-key pool with failover.
- Failed AI generations are refunded.
- Temporary provider failures cool down the affected key instead of stopping the whole bot.
- Broadcasts use controlled concurrency.
- Ban/unban actions give the affected user a clear access message.

No system can guarantee zero latency or zero provider downtime, but the project is designed to fail clearly and recover where possible.

## 🧪 Test

```bash
python -m pip install -r requirements-dev.txt
python -m py_compile emily_ai_bot.py ai_router.py run_emily.py ui_controller.py admin_users.py admin_data.py admin_dashboard.py
pytest -q
```

The tests use mocked/local inputs only; they do not call Telegram or consume AI API quota. The GitHub Actions workflow runs the same compile and test checks on pushes and pull requests.

## 💡 Why I built it

I wanted a small AI bot that feels more like a real Telegram product than a basic API demo — something with personality, memory, group support, usage control, and a practical admin side, without turning it into a huge system.

**Built as a small, practical project.**

## 📄 Reuse

This repository does not currently include a license file. Before redistributing or reusing the code in another project, ask the author or add an explicit open-source license.
