# Alisa — Telegram AI Companion

> A small Telegram AI bot I built to make chatting, group help, memory, and a few fun features feel simple and personal.

Alisa is a lightweight AI companion that runs directly through Telegram. It can chat with you, remember useful things you choose to save, change personality, help in groups, and give the admin a private control center.

It is intentionally a **small project**. There is no separate web dashboard, no large backend, and no complicated infrastructure.

## ✨ What can Alisa do?

- 💬 **AI chat** — talk naturally in Telegram.
- 🎭 **6 personalities** — Bestie, Study, Roast, Calm, Coding, Hype.
- 🧠 **Memory** — save, view, and delete things Alisa should remember.
- 👥 **Group assistant** — respond when mentioned or replied to.
- 🧾 **Group recap** — summarize recent group-visible conversation.
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
├── run_emily.py        # Production launcher + performance wiring
├── ai_router.py        # Gemini/OpenAI key pool and failover
├── ui_controller.py    # User and admin Telegram menus
├── admin_users.py      # User profiles and directory
├── admin_dashboard.py  # Admin statistics
├── admin_data.py       # Database tools
├── .env.example        # Configuration template
└── requirements.txt    # Runtime dependency
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

Copy `.env.example` to `.env` and add your own Telegram and AI keys.

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

GEMINI_API_KEY_1=your_key
GEMINI_API_KEY_2=your_key
GEMINI_API_KEY_3=your_key
GEMINI_API_KEY_4=your_key

OPENAI_API_KEY_1=your_key
OPENAI_API_KEY_2=your_key
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

Alisa keeps its local data in SQLite. User memory can be viewed and deleted with the memory commands. The AI provider keys are kept in environment variables and are not stored in the database.

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

## 💡 Why I built it

I wanted a small AI bot that feels more like a real Telegram product than a basic API demo — something with personality, memory, group support, usage control, and a practical admin side, without turning it into a huge system.

**Built as a small, practical project.**