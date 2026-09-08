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


# Keep the official bot filename as emily_ai_bot.py.
# This launcher only wires the six-key AI pool and concurrent Telegram processing.
router = AIRouter()

# Preserve backward compatibility with emily_ai_bot.py's legacy environment check.
if not os.getenv("OPENAI_API_KEY"):
    first_openai = os.getenv("OPENAI_API_KEY_1", "").strip()
    if first_openai:
        os.environ["OPENAI_API_KEY"] = first_openai

# Replace the old single-key OpenAI function with the multi-provider pool.
emily.openai_responses_create = router.generate_sync
emily.VERSION = "3.1.0-multikey"

# Emily does not use ConversationHandler or other sequential stateful flow.
_original_builder = emily.ApplicationBuilder


def fast_builder():
    return (
        _original_builder()
        .concurrent_updates(32)
        .connection_pool_size(64)
        .pool_timeout(10.0)
    )


emily.ApplicationBuilder = fast_builder

if __name__ == "__main__":
    emily.main()
