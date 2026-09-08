from __future__ import annotations

import sqlite3
from contextlib import closing


def database_stats(db_func) -> str:
    tables = ("users", "messages", "memories", "roasts", "group_settings", "errors")
    with closing(db_func()) as conn:
        lines = ["📊 <b>Database Overview</b>"]
        total = 0
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                count = 0
            total += count
            lines.append(f"• {table}: <b>{count}</b>")
        lines.append(f"\n📦 Total stored rows: <b>{total}</b>")
        return "\n".join(lines)


def clear_database(db_func) -> str:
    tables = ("messages", "memories", "roasts", "group_settings", "errors", "users")
    with closing(db_func()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        deleted = 0
        for table in tables:
            try:
                deleted += conn.execute(f"DELETE FROM {table}").rowcount
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    return f"✅ <b>Database cleared</b>\n\nDeleted <b>{deleted}</b> stored rows.\nThe SQLite schema remains intact and the admin account will be recreated when the next admin update arrives."
