from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from admin_users import find_user, my_id_text, user_directory
from admin_data import database_stats


def user_home(emily) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✨ What can Emily do?", callback_data="user:help")],
        [InlineKeyboardButton("🆔 My Telegram ID", callback_data="user:myid")],
        [InlineKeyboardButton("🎭 Personality", callback_data="user:modes"), InlineKeyboardButton("🧠 Memory", callback_data="user:memory")],
        [InlineKeyboardButton("💳 Usage & Credits", callback_data="user:quota"), InlineKeyboardButton("🔐 Privacy", callback_data="user:privacy")],
        [InlineKeyboardButton("👥 Group Tools", callback_data="user:group"), InlineKeyboardButton("✨ Emily Moment", callback_data="user:moment")],
        [InlineKeyboardButton("📖 All Commands", callback_data="user:commands"), InlineKeyboardButton("ℹ️ About", callback_data="user:about")],
    ]
    if emily.is_admin(getattr(emily, "_ui_user_id", None)):
        rows.append([InlineKeyboardButton("🛠 ADMIN CONTROL CENTER", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def back(target="user:home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def admin_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard"), InlineKeyboardButton("🤖 AI Pool", callback_data="admin:ai")],
        [InlineKeyboardButton("👥 Users", callback_data="admin:users"), InlineKeyboardButton("👥 Groups", callback_data="admin:groups")],
        [InlineKeyboardButton("💳 Credits & Plans", callback_data="admin:billing"), InlineKeyboardButton("🚫 Moderation", callback_data="admin:moderation")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast"), InlineKeyboardButton("🧠 Emily", callback_data="admin:emily")],
        [InlineKeyboardButton("⚠️ Error Monitor", callback_data="admin:errors"), InlineKeyboardButton("📤 Data", callback_data="admin:data")],
        [InlineKeyboardButton("🏥 System Health", callback_data="admin:health"), InlineKeyboardButton("📖 Admin Commands", callback_data="admin:commands")],
    ])


def admin_users_keyboard(page: int, total: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"admin:users:{page}"), InlineKeyboardButton("🔎 Find User", callback_data="admin:find_user")],
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Previous", callback_data=f"admin:users:{page - 1}"))
    if (page + 1) * 8 < total:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin:users:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_data_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Database Stats", callback_data="admin:db_stats")],
        [InlineKeyboardButton("📤 Export Data", callback_data="admin:export")],
        [InlineKeyboardButton("🗑️ Clear Entire Database", callback_data="admin:clear_db")],
        [InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")],
    ])


def admin_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ YES, DELETE EVERYTHING", callback_data="admin:clear_db_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin:data")],
    ])


def admin_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")]])


def user_commands_text() -> str:
    return (
        "📖 <b>Emily Command Guide</b>\n\n"
        "💬 <b>Chat</b>\nJust message Emily in DM. In groups, mention her or reply to her.\n\n"
        "🆔 <b>Account ID</b>\n/myid — instantly show your Telegram user ID.\n\n"
        "🎭 <b>Personality</b>\n/mode — choose Bestie, Study, Roast, Calm, Coding or Hype.\n\n"
        "🧠 <b>Memory</b>\n/memory — see what Emily remembers.\n/remember key = value — save something.\n/forget key — delete one memory.\n/forget_all — erase all saved memories.\n\n"
        "💳 <b>Account</b>\n/quota — see today's usage, plan and credits.\n/privacy — see storage/privacy controls.\n/about — version and product info.\n\n"
        "✨ <b>Fun & Groups</b>\n/moment — generate an Emily Moment.\n/group_summary — recap recent group-visible conversation.\n/group_moments on|off — group admins control Moments.\n\n"
        "🆘 <b>Navigation</b>\n/start — open this menu.\n/help — quick command reference."
    )


def admin_commands_text() -> str:
    return (
        "📖 <b>Admin Command Reference</b>\n\n"
        "/admin — open Control Center.\n/stats — bot usage dashboard.\n/ai_status — live AI key/model health.\n"
        "/users — paginated user directory with name, username and ID.\n/find_user &lt;id|username&gt; — find a known user.\n/user_info &lt;id&gt; — inspect a user.\n"
        "/ban_user &lt;id&gt; — ban a user.\n/unban_user &lt;id&gt; — restore a user.\n/add_credits &lt;id&gt; &lt;amount&gt; — add credits.\n"
        "/set_plan &lt;id&gt; free|premium — change plan.\n/errors — recent recorded failures.\n/export_data — export user data as CSV.\n"
        "/announce &lt;message&gt; — broadcast to non-banned users.\n\nUse the buttons for navigation; use commands when an operation needs text input."
    )


def patch(emily, router):
    async def start(update, context):
        user = update.effective_user; msg = update.effective_message
        if not user or not msg: return
        emily.ensure_user(user.id, user.username)
        emily._ui_user_id = user.id
        text = (
            f"💗 <b>Hey, I'm Emily</b>  ·  v{emily.VERSION}\n\n"
            "Your AI companion + group assistant.\n"
            "Chat naturally, switch personalities, let me remember useful things, or use group tools.\n\n"
            "🎁 Free: <b>50 AI replies/day</b>\n💳 1 credit = <b>1 AI generation</b>\n⭐ Premium: higher quota + special features"
        )
        await msg.reply_text(text, parse_mode="HTML", reply_markup=user_home(emily))

    async def admin_panel(update, context):
        user = update.effective_user; msg = update.effective_message
        if not user or not msg or not emily.is_admin(user.id): return
        emily._ui_user_id = user.id
        await msg.reply_text("🛠 <b>Emily Control Center</b>\n\nEverything important is available below. Use Back buttons to move around.", parse_mode="HTML", reply_markup=admin_home())

    async def callback(update, context):
        query = update.callback_query
        if not query or not query.message: return
        data = query.data or ""
        uid = query.from_user.id
        emily._ui_user_id = uid
        await query.answer()

        if data.startswith("mode:"):
            mode = data.split(":", 1)[1]
            if mode in emily.MODES:
                emily.ensure_user(uid, query.from_user.username)
                with emily.closing(emily.db()) as conn:
                    conn.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, uid)); conn.commit()
                await query.message.edit_text(f"🎭 <b>Mode changed</b>\n\nEmily is now in <b>{mode.title()}</b> mode.", parse_mode="HTML", reply_markup=back("user:modes"))
            return

        if data.startswith("user:"):
            key = data.split(":", 1)[1]
            emily.ensure_user(uid, query.from_user.username)
            if key == "home":
                await query.message.edit_text("💗 <b>Emily</b>\n\nChoose what you want to explore:", parse_mode="HTML", reply_markup=user_home(emily))
            elif key == "myid": await query.message.edit_text(my_id_text(update), parse_mode="HTML", reply_markup=back())
            elif key in {"help", "commands"}: await query.message.edit_text(user_commands_text(), parse_mode="HTML", reply_markup=back())
            elif key == "modes": await query.message.edit_text("🎭 <b>Choose Emily's personality</b>\n\nEach mode changes her tone and how she approaches your request.", parse_mode="HTML", reply_markup=emily.mode_keyboard())
            elif key == "memory": await query.message.edit_text("🧠 <b>Your Memory</b>\n\n" + ("\n".join(f"• <b>{r['memory_key']}</b>: {r['memory_value']}" for r in emily.get_memories(uid)) or "Nothing saved yet."), parse_mode="HTML", reply_markup=back())
            elif key == "quota": await query.message.edit_text("💳 <b>Your Emily account</b>\n\n" + emily.quota_text(uid), reply_markup=back())
            elif key == "privacy": await query.message.edit_text("🔐 <b>Privacy</b>\n\n• Long-term memories are stored locally in SQLite.\n• /memory lets you inspect them.\n• /forget deletes one.\n• /forget_all deletes everything.\n• Emily uses a limited recent conversation window.", reply_markup=back())
            elif key == "group": await query.message.edit_text("👥 <b>Group tools</b>\n\n• Mention Emily or reply to her to chat.\n• /group_summary — summarize recent visible conversation.\n• /group_moments on|off — group admins control Emily Moments.", reply_markup=back())
            elif key == "moment": await query.message.edit_text("✨ <b>Emily Moment</b>\n\nUse /moment for a short creative prompt, challenge or fun community moment.", reply_markup=back())
            elif key == "about": await query.message.edit_text(f"ℹ️ <b>Emily v{emily.VERSION}</b>\n\nSQLite memory + quotas + credits + personality modes + group tools.\n\nAI providers are routed through the configured multi-key pool.", parse_mode="HTML", reply_markup=back())
            return

        if not emily.is_admin(uid):
            await query.answer("Not authorized.", show_alert=True); return

        if data == "admin:home": await query.message.edit_text("🛠 <b>Emily Control Center</b>\n\nEverything important is available below.", parse_mode="HTML", reply_markup=admin_home())
        elif data.startswith("admin:users"):
            parts = data.split(":")
            page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            text, total = user_directory(emily.db, page)
            await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_users_keyboard(page, total))
        elif data == "admin:find_user":
            await query.message.edit_text("🔎 <b>Find a User</b>\n\nUse <code>/find_user 123456789</code> or <code>/find_user username</code>.\n\nYou can also use the user's numeric ID with the existing admin commands.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:dashboard": await query.message.edit_text(await emily.admin_stats_message(), reply_markup=admin_back())
        elif data == "admin:ai": await query.message.edit_text(router.status_text(), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="admin:ai")],[InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")]]))
        elif data == "admin:groups": await query.message.edit_text("👥 <b>Group Management</b>\n\n/group_moments on|off — group admin setting\n/group_summary — group-visible recap\n\nEmily only responds to mentions/replies in groups unless explicitly targeted.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:billing": await query.message.edit_text("💳 <b>Credits & Plans</b>\n\n/add_credits &lt;id&gt; &lt;amount&gt;\n/set_plan &lt;id&gt; free|premium\n\nFree: 50 AI replies/day\nPremium: 500 AI replies/day\nCredits: 1 credit = 1 generation", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:moderation": await query.message.edit_text("🚫 <b>Moderation</b>\n\n/ban_user &lt;id&gt; — block AI usage\n/unban_user &lt;id&gt; — restore access\n/user_info &lt;id&gt; — inspect account status", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:broadcast": await query.message.edit_text("📢 <b>Broadcast</b>\n\nUse:\n/announce Your message here\n\nEmily sends it to non-banned users and reports sent/failed counts.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:emily": await query.message.edit_text("🧠 <b>Emily Controls</b>\n\n🎭 Six user personality modes\n✨ Emily Moments\n🧠 Long-term memory\n💬 Recent conversation context\n\nUser-facing controls are available from /start.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:errors": await query.message.edit_text("⚠️ <b>Error Monitor</b>\n\nUse /errors to inspect recent recorded failures.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:data": await query.message.edit_text("📤 <b>Data & Maintenance</b>\n\nChoose a safe maintenance action below. Destructive actions require an explicit confirmation.", parse_mode="HTML", reply_markup=admin_data_keyboard())
        elif data == "admin:db_stats": await query.message.edit_text(database_stats(emily.db), parse_mode="HTML", reply_markup=admin_data_keyboard())
        elif data == "admin:export": await query.message.edit_text("📤 <b>Export Data</b>\n\nUse /export_data to generate the current user CSV export.", parse_mode="HTML", reply_markup=admin_data_keyboard())
        elif data == "admin:clear_db":
            stats = database_stats(emily.db)
            await query.message.edit_text("⚠️ <b>Danger Zone</b>\n\nThis will permanently delete the current SQLite data for all users, memories, messages, roasts, group settings and recorded errors.\n\n<b>This cannot be undone.</b>\n\n" + stats, parse_mode="HTML", reply_markup=admin_clear_confirm_keyboard())
        elif data == "admin:clear_db_confirm":
            from admin_data import clear_database
            result = clear_database(emily.db)
            await query.message.edit_text(result, parse_mode="HTML", reply_markup=admin_home())
        elif data == "admin:health":
            health = await emily.admin_stats_message()
            await query.message.edit_text("🏥 <b>System Health</b>\n\n" + health + "\n\n🤖 AI pool: use the AI Pool button for per-key status.", parse_mode="HTML", reply_markup=admin_back())
        elif data == "admin:commands": await query.message.edit_text(admin_commands_text(), parse_mode="HTML", reply_markup=admin_back())

    emily.start = start
    emily.admin_panel = admin_panel
    emily.callback_handler = callback
    return emily
