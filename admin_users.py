from __future__ import annotations

from contextlib import closing

from telegram import Update


def migrate_profile_columns(db_func) -> None:
    with closing(db_func()) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "first_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        if "last_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
        conn.commit()


def sync_user(update: Update, db_func) -> None:
    user = update.effective_user
    if not user:
        return
    with closing(db_func()) as conn:
        conn.execute(
            "INSERT INTO users(user_id, username, first_name, last_name, quota_date, last_interaction) "
            "VALUES(?,?,?,?,date('now'),CURRENT_TIMESTAMP) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, last_name=excluded.last_name, last_interaction=excluded.last_interaction",
            (user.id, user.username, user.first_name, user.last_name),
        )
        conn.commit()


def user_directory_rows(db_func, page: int = 0, per_page: int = 8):
    page = max(0, page)
    offset = page * per_page
    with closing(db_func()) as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        rows = conn.execute(
            "SELECT user_id, first_name, last_name, username, plan, credits, is_banned, total_messages FROM users ORDER BY last_interaction DESC, user_id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ).fetchall()
    return rows, total


def user_directory(db_func, page: int = 0, per_page: int = 8) -> tuple[str, int]:
    rows, total = user_directory_rows(db_func, page, per_page)
    offset = max(0, page) * per_page
    if not rows:
        return "👥 <b>User Directory</b>\n\nNo users found on this page.", total
    lines = [f"👥 <b>User Directory</b>  ·  {total} total\n"]
    for i, row in enumerate(rows, offset + 1):
        full_name = " ".join(x for x in (row["first_name"], row["last_name"]) if x).strip() or "Name not recorded"
        username = f"@{row['username']}" if row["username"] else "No username"
        status = "🚫 BANNED" if row["is_banned"] else row["plan"].title()
        lines.append(
            f"<b>{i}. {full_name}</b>\n"
            f"   👤 {username}\n"
            f"   🆔 <code>{row['user_id']}</code>\n"
            f"   💳 {status} · {row['credits']} credits · {row['total_messages']} replies"
        )
    lines.append(f"\n📄 Page {page + 1} · showing {offset + 1}-{offset + len(rows)}")
    return "\n\n".join(lines), total


def find_user(db_func, query: str) -> str:
    query = query.strip().lstrip("@").lower()
    if not query:
        return "🔎 Send a numeric Telegram ID or username after /find_user."
    with closing(db_func()) as conn:
        if query.isdigit():
            row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (int(query),)).fetchone()
            user_id = int(query) if row else None
        else:
            row = conn.execute("SELECT user_id FROM users WHERE lower(username)=?", (query,)).fetchone()
            user_id = int(row["user_id"]) if row else None
    if user_id is None:
        return "🔎 <b>User not found</b>\n\nThe user must have interacted with Emily at least once so Emily has their profile record."
    return f"🔎 <b>User Found</b>\n\nOpen the user profile for <code>{user_id}</code> from the User Directory, or use <code>/user_info {user_id}</code>."


def my_id_text(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "🆔 I couldn't read your Telegram profile."
    name = " ".join(x for x in (user.first_name, user.last_name) if x).strip() or "Unknown"
    username = f"@{user.username}" if user.username else "No username set"
    return f"🆔 <b>Your Telegram ID</b>\n\n👤 {name}\n🔗 {username}\n\n<code>{user.id}</code>\n\nCopy the number above and give it to the admin if needed."
