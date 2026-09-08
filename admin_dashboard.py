from __future__ import annotations

from contextlib import closing


def _count(conn, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def dashboard_text(db_func, router) -> str:
    with closing(db_func()) as conn:
        users = _count(conn, "users")
        messages = _count(conn, "messages")
        memories = _count(conn, "memories")
        groups = _count(conn, "group_settings")
        errors = _count(conn, "errors")
        free = int(conn.execute("SELECT COUNT(*) FROM users WHERE plan='free'").fetchone()[0])
        premium = int(conn.execute("SELECT COUNT(*) FROM users WHERE plan='premium'").fetchone()[0])
        banned = int(conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0])
        credits = int(conn.execute("SELECT COALESCE(SUM(credits),0) FROM users").fetchone()[0])
        today_messages = int(conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant' AND date(created_at)=date('now')").fetchone()[0])
        recent_errors = int(conn.execute("SELECT COUNT(*) FROM errors WHERE datetime(created_at) >= datetime('now','-24 hours')").fetchone()[0])

    total_requests = sum(getattr(item, "requests", 0) for item in router.keys)
    total_successes = sum(getattr(item, "successes", 0) for item in router.keys)
    total_failures = sum(getattr(item, "total_failures", 0) for item in router.keys)
    healthy = sum(1 for item in router.keys if not item.disabled and getattr(item, "manual_disabled", False) is False)

    return (
        "📊 <b>Emily Live Dashboard</b>\n\n"
        f"👥 Users: <b>{users}</b>  ·  🟢 Free {free}  ·  ⭐ Premium {premium}\n"
        f"🚫 Banned: <b>{banned}</b>\n"
        f"💬 Assistant replies today: <b>{today_messages}</b>\n"
        f"💬 Stored messages: <b>{messages}</b>\n"
        f"🧠 Memories: <b>{memories}</b>\n"
        f"👥 Groups configured: <b>{groups}</b>\n"
        f"💳 Credits remaining: <b>{credits}</b>\n"
        f"⚠️ Errors: <b>{errors}</b>  ·  Last 24h: {recent_errors}\n\n"
        "🤖 <b>AI generation engine</b>\n"
        f"Keys available: <b>{len(router.keys)}</b>  ·  Ready: <b>{healthy}</b>\n"
        f"Requests: <b>{total_requests}</b>  ·  Successes: <b>{total_successes}</b>  ·  Failures: <b>{total_failures}</b>"
    )


def user_profile(db_func, user_id: int) -> str | None:
    with closing(db_func()) as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if user is None:
            return None
        messages = int(conn.execute("SELECT COUNT(*) FROM messages WHERE user_id=?", (user_id,)).fetchone()[0])
        memories = int(conn.execute("SELECT COUNT(*) FROM memories WHERE user_id=?", (user_id,)).fetchone()[0])
        roasts = int(conn.execute("SELECT COUNT(*) FROM roasts WHERE user_id=?", (user_id,)).fetchone()[0])
        chats = int(conn.execute("SELECT COUNT(DISTINCT chat_id) FROM messages WHERE user_id=?", (user_id,)).fetchone()[0])
        last_message = conn.execute(
            "SELECT created_at FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()

    name = " ".join(x for x in (user["first_name"], user["last_name"]) if x).strip() or "Name not recorded"
    username = f"@{user['username']}" if user["username"] else "No username"
    status = "🚫 Banned" if user["is_banned"] else "✅ Active"
    return (
        "👤 <b>User Profile</b>\n\n"
        f"<b>{name}</b>\n"
        f"🔗 {username}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"🟢 Status: <b>{status}</b>\n"
        f"💳 Plan: <b>{user['plan'].title()}</b>\n"
        f"💰 Credits: <b>{user['credits']}</b>\n"
        f"🎭 Mode: <b>{user['mode'].title()}</b>\n"
        f"📅 Today: <b>{user['daily_messages']}</b>\n"
        f"💬 Total replies: <b>{user['total_messages']}</b>\n"
        f"🗂 Stored messages: <b>{messages}</b>\n"
        f"🧠 Memories: <b>{memories}</b>\n"
        f"🔥 Roasts: <b>{roasts}</b>\n"
        f"👥 Chats: <b>{chats}</b>\n"
        f"🕒 Last interaction: {user['last_interaction'] or 'Unknown'}\n"
        f"💬 Last stored message: {last_message['created_at'] if last_message else 'None'}"
    )
