from __future__ import annotations

import asyncio
import os
import time
from threading import Lock


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()

import emily_ai_bot as emily
from admin_users import find_user, migrate_profile_columns, my_id_text, sync_user
from ai_router import AIRouter
from ui_controller import patch as patch_ui
from telegram import Update
from telegram.error import BadRequest, Forbidden, RetryAfter
from telegram.ext import CommandHandler, TypeHandler

router = AIRouter()

# The legacy core still checks OPENAI_API_KEY during build_app(). The router now
# owns provider selection, so make that legacy check harmless when Gemini-only
# deployments are used.
if not os.getenv("OPENAI_API_KEY"):
    first_openai = os.getenv("OPENAI_API_KEY_1", "").strip()
    os.environ["OPENAI_API_KEY"] = first_openai or "router-managed"

# Keep the existing core filename and API, but route every generation through
# the multi-key pool. Also make the bot's actual AI identity consistent.
def generate_via_router(instructions, messages):
    return router.generate_sync(instructions.replace("Emily", "Alisa"), messages)


emily.openai_responses_create = generate_via_router
emily.VERSION = "3.5.0-performance-safety"
emily.init_db()
migrate_profile_columns(emily.db)
patch_ui(emily, router)

_original_builder = emily.ApplicationBuilder


def fast_builder():
    return (
        _original_builder()
        .concurrent_updates(32)
        .connection_pool_size(64)
        .pool_timeout(20.0)
        .connect_timeout(20.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .get_updates_pool_timeout(20.0)
        .get_updates_connect_timeout(20.0)
        .get_updates_read_timeout(30.0)
        .get_updates_write_timeout(30.0)
        .http_version("1.1")
    )


emily.ApplicationBuilder = fast_builder


# ---------- Access / moderation hardening ----------

_BAN_NOTICE = (
    "🚫 <b>Access suspended</b>\n\n"
    "Your access to Alisa has been suspended by the administrator.\n"
    "You can't use Alisa's AI features while this restriction is active.\n\n"
    "If you believe this was a mistake, contact the bot administrator."
)

_UNBAN_NOTICE = (
    "✅ <b>Access restored</b>\n\n"
    "Your access to Alisa has been restored. You can use the bot normally again. 💗"
)

_profile_seen: dict[int, tuple[object, ...]] = {}
_profile_lock = Lock()


def _is_banned(user_id: int) -> bool:
    try:
        return bool(emily.get_user(user_id)["is_banned"])
    except Exception:
        return False


async def _tell_banned(update, _context) -> bool:
    user = getattr(update, "effective_user", None)
    message = getattr(update, "effective_message", None)
    if not user or not message:
        return False
    if _is_banned(user.id):
        try:
            await message.reply_text(_BAN_NOTICE, parse_mode="HTML")
        except Exception:
            pass
        return True
    return False


async def _notify_access_change(bot, user_id: int, enabled: bool) -> tuple[bool, str]:
    try:
        await bot.send_message(
            chat_id=user_id,
            text=_UNBAN_NOTICE if enabled else _BAN_NOTICE,
            parse_mode="HTML",
        )
        return True, "notified"
    except RetryAfter as exc:
        try:
            await asyncio.sleep(float(exc.retry_after) + 0.15)
            await bot.send_message(
                chat_id=user_id,
                text=_UNBAN_NOTICE if enabled else _BAN_NOTICE,
                parse_mode="HTML",
            )
            return True, "notified after rate-limit delay"
        except Exception as retry_exc:
            emily.log_error("telegram_send", "access_change", user_id, None, repr(retry_exc))
            return False, "notification failed after retry"
    except (Forbidden, BadRequest) as exc:
        emily.log_error("telegram_send", "access_change", user_id, None, repr(exc))
        return False, "user could not be contacted in Telegram"
    except Exception as exc:
        emily.log_error("telegram_send", "access_change", user_id, None, repr(exc))
        return False, "notification failed"


async def moderated_ban(update, context):
    admin = update.effective_user
    message = update.effective_message
    if not admin or not emily.is_admin(admin.id) or not message:
        return
    if not context.args:
        await message.reply_text("Usage: /ban_user <user_id> [reason]")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ User ID must be numeric.")
        return
    if target == admin.id:
        await message.reply_text("❌ You cannot ban the administrator account.")
        return

    reason = " ".join(context.args[1:]).strip()
    with emily.closing(emily.db()) as conn:
        result = conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))
        conn.commit()
    if result.rowcount != 1:
        await message.reply_text("❌ User not found. The user must have a profile in Alisa first.")
        return

    notified, note = await _notify_access_change(context.bot, target, False)
    suffix = f"\nReason: {reason}" if reason else ""
    await message.reply_text(
        f"🚫 <b>User banned</b>\n\n🆔 <code>{target}</code>{suffix}\n📨 {note}",
        parse_mode="HTML",
    )


async def moderated_unban(update, context):
    admin = update.effective_user
    message = update.effective_message
    if not admin or not emily.is_admin(admin.id) or not message:
        return
    if not context.args:
        await message.reply_text("Usage: /unban_user <user_id>")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ User ID must be numeric.")
        return

    with emily.closing(emily.db()) as conn:
        result = conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target,))
        conn.commit()
    if result.rowcount != 1:
        await message.reply_text("❌ User not found.")
        return

    notified, note = await _notify_access_change(context.bot, target, True)
    await message.reply_text(
        f"✅ <b>User unbanned</b>\n\n🆔 <code>{target}</code>\n📨 {note}",
        parse_mode="HTML",
    )


async def guarded_command(original, update, context):
    if await _tell_banned(update, context):
        return
    return await original(update, context)


# Commands that should never silently do nothing for a banned user.
for _name in (
    "set_mode",
    "memory_command",
    "remember_command",
    "forget_command",
    "forget_all_command",
    "quota_command",
    "privacy_command",
    "moment_command",
    "group_summary_command",
    "group_moments_setting",
):
    _original = getattr(emily, _name)
    async def _wrapped(update, context, _original=_original):
        return await guarded_command(_original, update, context)
    setattr(emily, _name, _wrapped)

emily.admin_ban = moderated_ban
emily.admin_unban = moderated_unban


# ---------- Faster / safer message path ----------

async def fast_handle_message(update: Update, context) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat or not message.text:
        return

    # Keep this first so banned users are never silently ignored.
    if _is_banned(user.id):
        await message.reply_text(_BAN_NOTICE, parse_mode="HTML")
        return

    # Group privacy: only answer targeted messages.
    if chat.type in {"group", "supergroup"} and not emily.group_targeted(update, context):
        return

    # Keep profile data current without putting a blocking Telegram/DB action
    # in the response path. Core quota accounting remains transactional.
    try:
        emily.ensure_user(user.id, user.username)
    except Exception as exc:
        emily.log_error("database", "ensure_user", user.id, chat.id, repr(exc))

    for key, value in emily.extract_simple_memories(message.text):
        try:
            emily.save_memory(user.id, key, value)
        except Exception as exc:
            emily.log_error("database", "memory_extract", user.id, chat.id, repr(exc))

    kind = emily.consume_generation(user.id)
    if not kind:
        if _is_banned(user.id):
            await message.reply_text(_BAN_NOTICE, parse_mode="HTML")
            return
        try:
            quota = emily.quota_text(user.id)
        except Exception:
            quota = "Your usage information is temporarily unavailable."
        await message.reply_text(
            "⏳ <b>No AI generation available right now</b>\n\n"
            f"{quota}\n\n"
            "Free users receive 50 AI replies/day. Credits add 1 generation each.",
            parse_mode="HTML",
        )
        return

    row = emily.get_user(user.id)
    purpose = "playful roast" if row["mode"] == "roast" or any(k in message.text.lower() for k in emily.RUDE_KEYWORDS) else "normal chat"

    try:
        # Intentionally no send_chat_action(TYPING) here: that is an extra
        # Telegram API round-trip on every message and adds latency.
        reply = await emily.ask_ai(user.id, chat.id, message.text, row["mode"], purpose)
        emily.save_message(user.id, chat.id, "user", message.text)
        emily.save_message(user.id, chat.id, "assistant", reply)
        if purpose == "playful roast":
            with emily.closing(emily.db()) as conn:
                conn.execute(
                    "INSERT INTO roasts(user_id,user_message,roast_response,timestamp) VALUES(?,?,?,?)",
                    (user.id, message.text[:4000], reply[:4000], emily.now_iso()),
                )
                conn.execute("UPDATE users SET roasts_count=roasts_count+1 WHERE user_id=?", (user.id,))
                conn.commit()
        await message.reply_text(reply)
    except Exception as exc:
        emily.refund_generation(user.id, kind)
        error_type = emily.classify_ai_error(exc)
        emily.log_error(error_type, "chat", user.id, chat.id, repr(exc))
        emily.logger.exception("AI request failed")
        user_message = emily.user_error_message(error_type).replace("Emily", "Alisa")
        await message.reply_text(user_message)


emily.handle_message = fast_handle_message


# ---------- Non-blocking profile sync ----------

async def profile_sync(update: Update, context) -> None:
    user = update.effective_user
    if not user:
        return
    signature = (user.id, user.username, user.first_name, user.last_name)
    with _profile_lock:
        if _profile_seen.get(user.id) == signature:
            return
        _profile_seen[user.id] = signature
    try:
        await asyncio.to_thread(sync_user, update, emily.db)
    except Exception:
        emily.logger.exception("Profile sync failed")


async def ai_status(update, context) -> None:
    user = update.effective_user
    message = update.effective_message
    if user and emily.is_admin(user.id) and message:
        await message.reply_text(router.status_text(), parse_mode="HTML")


async def myid(update, context) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(my_id_text(update), parse_mode="HTML")


async def find_user_command(update, context) -> None:
    user = update.effective_user
    if not user or not emily.is_admin(user.id) or not update.effective_message:
        return
    query = " ".join(context.args).strip()
    await update.effective_message.reply_text(find_user(emily.db, query), parse_mode="HTML")


async def users_command(update, context) -> None:
    user = update.effective_user
    if not user or not emily.is_admin(user.id) or not update.effective_message:
        return
    from admin_users import user_directory_rows
    from ui_controller import admin_users_keyboard
    rows, total = user_directory_rows(emily.db, 0)
    lines = [f"👥 <b>User Directory</b> · {total} total", ""]
    for row in rows:
        name = " ".join(x for x in (row["first_name"], row["last_name"]) if x).strip() or "Name not recorded"
        username = f"@{row['username']}" if row["username"] else "No username"
        status = "🚫 BANNED" if row["is_banned"] else row["plan"].title()
        lines.append(f"<b>{name}</b> · {username}\n🆔 <code>{row['user_id']}</code> · 💰 {row['credits']} credits · {status}")
    await update.effective_message.reply_text("\n\n".join(lines), parse_mode="HTML", reply_markup=admin_users_keyboard(0, total, rows))


# ---------- Faster broadcast ----------

async def fast_announce(update, context) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not emily.is_admin(user.id) or not message:
        return
    if not context.args:
        await message.reply_text("Usage: /announce <message>")
        return

    announcement = " ".join(context.args)
    with emily.closing(emily.db()) as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

    semaphore = asyncio.Semaphore(8)

    async def deliver(user_id: int):
        async with semaphore:
            for attempt in range(3):
                try:
                    await context.bot.send_message(chat_id=user_id, text=announcement)
                    return True
                except RetryAfter as exc:
                    if attempt == 2:
                        emily.log_error("telegram_send", "announce", user_id, None, repr(exc))
                        return False
                    await asyncio.sleep(float(exc.retry_after) + 0.15)
                except (Forbidden, BadRequest) as exc:
                    emily.log_error("telegram_send", "announce", user_id, None, repr(exc))
                    return False
                except Exception as exc:
                    if attempt == 2:
                        emily.log_error("telegram_send", "announce", user_id, None, repr(exc))
                        return False
                    await asyncio.sleep(0.5 * (attempt + 1))
        return False

    results = await asyncio.gather(*(deliver(int(row["user_id"])) for row in rows), return_exceptions=False)
    sent = sum(1 for ok in results if ok)
    failed = len(results) - sent
    await message.reply_text(f"📢 <b>Broadcast finished</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}", parse_mode="HTML")


emily.admin_announce = fast_announce


def main() -> None:
    print(f"Alisa v{emily.VERSION} starting with {len(router.keys)} AI key(s)…")
    app = emily.build_app()
    app.add_handler(TypeHandler(Update, profile_sync), group=-1)
    app.add_handler(CommandHandler("ai_status", ai_status))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("find_user", find_user_command))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
