from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional

from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.ext import AIORateLimiter


# -----------------------------
# Configuration
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_USER_ID_RAW = os.getenv("ADMIN_USER_ID")
DB_FILE = os.getenv("EMILY_DB_FILE", "emily.db")
MODEL = os.getenv("EMILY_MODEL", "gpt-5-mini")
DAILY_FREE_MESSAGES = int(os.getenv("EMILY_DAILY_FREE_MESSAGES", "50"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is required")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ADMIN_USER_ID_RAW or not ADMIN_USER_ID_RAW.isdigit():
    raise RuntimeError("ADMIN_USER_ID must be a numeric Telegram user ID")
ADMIN_USER_ID = int(ADMIN_USER_ID_RAW)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("emily")
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=30.0, max_retries=2)


# -----------------------------
# SQLite persistence (foundation)
# -----------------------------
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db() -> None:
    with closing(db()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                daily_messages INTEGER NOT NULL DEFAULT 0,
                total_messages INTEGER NOT NULL DEFAULT 0,
                credits INTEGER NOT NULL DEFAULT 0,
                quota_date TEXT,
                is_banned INTEGER NOT NULL DEFAULT 0,
                roasts_count INTEGER NOT NULL DEFAULT 0,
                mode TEXT NOT NULL DEFAULT 'bestie',
                last_interaction TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user_time
                ON messages(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_chat_time
                ON messages(chat_id, created_at DESC);
            """
        )
        conn.commit()


def ensure_user(user_id: int, username: Optional[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with closing(db()) as conn:
        conn.execute(
            """
            INSERT INTO users(user_id, username, quota_date, last_interaction)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_interaction=excluded.last_interaction
            """,
            (user_id, username, now[:10], now),
        )
        conn.commit()


def get_user(user_id: int) -> sqlite3.Row:
    with closing(db()) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        raise RuntimeError("User record was not created")
    return row


def consume_quota(user_id: int) -> bool:
    """Atomically consume one free message or one credit."""
    today = datetime.now(timezone.utc).date().isoformat()
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT daily_messages, credits, quota_date FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            return False

        used = 0 if row["quota_date"] != today else row["daily_messages"]
        if used < DAILY_FREE_MESSAGES:
            updated = conn.execute(
                """
                UPDATE users
                SET daily_messages=?, quota_date=?, total_messages=total_messages+1,
                    last_interaction=?
                WHERE user_id=?
                """,
                (used + 1, today, datetime.now(timezone.utc).isoformat(), user_id),
            )
            ok = updated.rowcount == 1
        elif row["credits"] > 0:
            updated = conn.execute(
                """
                UPDATE users
                SET credits=credits-1, total_messages=total_messages+1,
                    last_interaction=?
                WHERE user_id=? AND credits>0
                """,
                (datetime.now(timezone.utc).isoformat(), user_id),
            )
            ok = updated.rowcount == 1
        else:
            ok = False

        if ok:
            conn.commit()
        else:
            conn.rollback()
        return ok


def has_access(user_id: int) -> bool:
    row = get_user(user_id)
    return not bool(row["is_banned"])


def save_message(user_id: int, chat_id: int, role: str, content: str) -> None:
    with closing(db()) as conn:
        conn.execute(
            "INSERT INTO messages(user_id, chat_id, role, content, created_at) VALUES(?,?,?,?,?)",
            (user_id, chat_id, role, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def recent_history(user_id: int, limit: int = 12) -> list[sqlite3.Row]:
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


# -----------------------------
# Emily brain
# -----------------------------
MODES = {
    "bestie": "Warm, playful, caring best friend. Tease lightly, never manipulate.",
    "study": "Patient study buddy. Explain clearly, motivate, and use practical examples.",
    "roast": "Witty roast mode. Tease the behavior, not protected traits, and keep it playful.",
    "calm": "Calm supportive friend. Be grounded, gentle, and concise.",
}


async def get_ai_response(user_id: int, user_message: str, mode: str) -> str:
    history = recent_history(user_id)
    mode_instruction = MODES.get(mode, MODES["bestie"])
    system = (
        "You are Emily, a Telegram AI companion and group assistant. "
        "Be warm, concise, useful, and natural. Never claim to be human. "
        "Do not encourage emotional dependency or exclusivity. "
        "Respect boundaries and avoid sexual content involving minors. "
        "Match the user's language naturally; Hindi-English is welcome. "
        f"Current mode: {mode_instruction} "
        "For ordinary chat, answer in 1-4 short paragraphs or a few short lines."
    )
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in history)
    messages.append({"role": "user", "content": user_message})

    response = await ai_client.responses.create(model=MODEL, input=messages)
    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("AI returned empty output")
    return text


# -----------------------------
# Telegram helpers / handlers
# -----------------------------
def is_admin(user_id: Optional[int]) -> bool:
    return user_id == ADMIN_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return
    ensure_user(update.effective_user.id, update.effective_user.username)
    await update.effective_message.reply_text(
        "Hey, I'm Emily 💗\n"
        "Add me to a group and reply to me or mention me.\n\n"
        "/mode bestie • /mode study • /mode roast • /mode calm"
    )


async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return
    mode = context.args[0].lower() if context.args else ""
    if mode not in MODES:
        await update.effective_message.reply_text("Modes: bestie, study, roast, calm")
        return
    ensure_user(update.effective_user.id, update.effective_user.username)
    with closing(db()) as conn:
        conn.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, update.effective_user.id))
        conn.commit()
    await update.effective_message.reply_text(f"Emily mode → {mode} ✨")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message or not is_admin(update.effective_user.id):
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin:stats"), InlineKeyboardButton("👤 User", callback_data="admin:user")],
        [InlineKeyboardButton("🚫 Ban", callback_data="admin:ban"), InlineKeyboardButton("✅ Unban", callback_data="admin:unban")],
    ])
    await update.effective_message.reply_text("Emily Control Center", reply_markup=keyboard)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        if query:
            await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()
    if query.data == "admin:stats":
        with closing(db()) as conn:
            users = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
            messages = conn.execute("SELECT COUNT(*) AS n FROM messages WHERE role='user'").fetchone()["n"]
        await query.message.reply_text(f"📊 Users: {users}\n💬 User messages: {messages}")
    elif query.data in {"admin:user", "admin:ban", "admin:unban"}:
        await query.message.reply_text("Use /user_info, /ban_user <id>, or /unban_user <id>." )


async def admin_simple_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message or not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.effective_message.reply_text("Provide a numeric user ID.")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("User ID must be numeric.")
        return
    command = update.effective_message.text.split()[0].lstrip("/").split("@")[0]
    value = 1 if command == "ban_user" else 0
    with closing(db()) as conn:
        result = conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (value, target))
        conn.commit()
    await update.effective_message.reply_text(
        f"{'🚫 Banned' if value else '✅ Unbanned'} {target}." if result.rowcount else "User not found."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat or not message.text:
        return

    ensure_user(user.id, user.username)
    if not has_access(user.id):
        return

    # In groups, respond when explicitly addressed. This works safely with Telegram privacy mode.
    if chat.type in {"group", "supergroup"}:
        bot_username = context.bot.username or ""
        mentioned = f"@{bot_username}".lower() in message.text.lower() if bot_username else False
        replied_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == context.bot.id)
        if not mentioned and not replied_to_bot:
            return

    if not consume_quota(user.id):
        await message.reply_text("I'm out of free replies for today 🥺 Try again tomorrow or use a credit.")
        return

    row = get_user(user.id)
    mode = row["mode"]
    save_message(user.id, chat.id, "user", message.text)
    try:
        async with context.bot.chat_action(chat_id=chat.id, action="typing"):
            reply = await get_ai_response(user.id, message.text, mode)
    except Exception:
        logger.exception("AI response failed", extra={"user_id": user.id, "chat_id": chat.id})
        await message.reply_text("My brain glitched for a second 😭 Try again.")
        return

    save_message(user.id, chat.id, "assistant", reply)
    await message.reply_text(reply)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled Telegram error", exc_info=context.error)


def build_app() -> Application:
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mode", set_mode))
    app.add_handler(CommandHandler("help_admin", admin_panel))
    app.add_handler(CommandHandler("stats", admin_callback))
    app.add_handler(CommandHandler("ban_user", admin_simple_action))
    app.add_handler(CommandHandler("unban_user", admin_simple_action))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    return app


if __name__ == "__main__":
    init_db()
    build_app().run_polling(drop_pending_updates=True)
