from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def user_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✨ What can Emily do?", callback_data="user:help")],
        [InlineKeyboardButton("🎭 Personality", callback_data="user:modes"), InlineKeyboardButton("🧠 Memory", callback_data="user:memory")],
        [InlineKeyboardButton("💳 My Usage", callback_data="user:quota"), InlineKeyboardButton("🔐 Privacy", callback_data="user:privacy")],
        [InlineKeyboardButton("✨ Emily Moment", callback_data="user:moment"), InlineKeyboardButton("🧾 Group Tools", callback_data="user:group")],
        [InlineKeyboardButton("ℹ️ About Emily", callback_data="user:about")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛠 ADMIN CONTROL CENTER", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def user_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎭 Modes", callback_data="user:modes"), InlineKeyboardButton("🧠 Memory", callback_data="user:memory")],
        [InlineKeyboardButton("👥 Groups", callback_data="user:group"), InlineKeyboardButton("💳 Usage", callback_data="user:quota")],
        [InlineKeyboardButton("🔐 Privacy", callback_data="user:privacy")],
        [InlineKeyboardButton("⬅️ Back", callback_data="user:home")],
    ])


def admin_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard"), InlineKeyboardButton("🤖 AI Pool", callback_data="admin:ai")],
        [InlineKeyboardButton("👥 Users", callback_data="admin:users"), InlineKeyboardButton("👥 Groups", callback_data="admin:groups")],
        [InlineKeyboardButton("💳 Credits & Plans", callback_data="admin:billing"), InlineKeyboardButton("🚫 Moderation", callback_data="admin:moderation")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast"), InlineKeyboardButton("🧠 Emily", callback_data="admin:emily")],
        [InlineKeyboardButton("⚠️ Errors", callback_data="admin:errors"), InlineKeyboardButton("📤 Data", callback_data="admin:data")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin:settings"), InlineKeyboardButton("🏥 Health", callback_data="admin:health")],
    ])


def admin_back_keyboard(section: str = "home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")]])


def admin_users_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Find User", callback_data="admin:user_find"), InlineKeyboardButton("📋 User Count", callback_data="admin:dashboard")],
        [InlineKeyboardButton("💳 Manage Credits", callback_data="admin:billing"), InlineKeyboardButton("⭐ Manage Plans", callback_data="admin:billing")],
        [InlineKeyboardButton("🚫 Ban / Unban", callback_data="admin:moderation")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])


def admin_billing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Credits", callback_data="admin:add_credits"), InlineKeyboardButton("⭐ Set Plan", callback_data="admin:set_plan")],
        [InlineKeyboardButton("📊 Usage", callback_data="admin:dashboard")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])


def admin_moderation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin:ban"), InlineKeyboardButton("✅ Unban User", callback_data="admin:unban")],
        [InlineKeyboardButton("🔎 User Info", callback_data="admin:user_find")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])


def admin_data_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Export Data", callback_data="admin:export"), InlineKeyboardButton("⚠️ Errors", callback_data="admin:errors")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])


def admin_emily_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎭 Personality Modes", callback_data="admin:modes"), InlineKeyboardButton("✨ Moments", callback_data="admin:moments")],
        [InlineKeyboardButton("ℹ️ Bot Info", callback_data="admin:about")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])


def admin_ai_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh AI Status", callback_data="admin:ai")],
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin:home")],
    ])
