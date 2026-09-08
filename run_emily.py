from __future__ import annotations

import os


# Tiny dependency-free .env loader for Termux.
def load_env_file(path: str = ".env") -> None:
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
from telegram.ext import CommandHandler, TypeHandler


router = AIRouter()

# Preserve compatibility with the original bot's single-key environment check.
if not os.getenv("OPENAI_API_KEY"):
    first_openai = os.getenv("OPENAI_API_KEY_1", "").strip()
    if first_openai:
        os.environ["OPENAI_API_KEY"] = first_openai

# Route every existing OpenAI call through the six-key provider pool.
emily.openai_responses_create = router.generate_sync
emily.VERSION = "3.3.0-users"

# Add persistent Telegram profile fields without changing the core bot architecture.
emily.init_db()
migrate_profile_columns(emily.db)

# Replace the old text-only menus with the navigable Telegram UI.
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


async def ai_status(update, context) -> None:
    if update.effective_user and emily.is_admin(update.effective_user.id) and update.effective_message:
        await update.effective_message.reply_text(router.status_text())


async def profile_sync(update: Update, context) -> None:
    # This runs before normal handlers and quietly keeps name/username current.
    try:
        sync_user(update, emily.db)
    except Exception:
        emily.logger.exception("Profile sync failed")


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
    from admin_users import user_directory
    from ui_controller import admin_users_keyboard
    text, total = user_directory(emily.db, 0)
    await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=admin_users_keyboard(0, total))


def main() -> None:
    print(f"Emily v{emily.VERSION} starting with {len(router.keys)} AI key(s)…")
    app = emily.build_app()
    # Keep profile information fresh for every incoming Telegram update.
    app.add_handler(TypeHandler(Update, profile_sync), group=-1)
    app.add_handler(CommandHandler("ai_status", ai_status))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("find_user", find_user_command))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__": main()
