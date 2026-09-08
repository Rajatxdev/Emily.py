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
from ai_router import AIRouter
from ui_controller import patch as patch_ui
from telegram.ext import CommandHandler


router = AIRouter()

# Preserve compatibility with the original bot's single-key environment check.
if not os.getenv("OPENAI_API_KEY"):
    first_openai = os.getenv("OPENAI_API_KEY_1", "").strip()
    if first_openai:
        os.environ["OPENAI_API_KEY"] = first_openai

# Route every existing OpenAI call through the six-key provider pool.
emily.openai_responses_create = router.generate_sync
emily.VERSION = "3.2.0-ui"

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


def main() -> None:
    print(f"Emily v{emily.VERSION} starting with {len(router.keys)} AI key(s)…")
    app = emily.build_app()
    app.add_handler(CommandHandler("ai_status", ai_status))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__": main()
