from __future__ import annotations

import os

import emily_ai_bot as emily
from ai_router import AIRouter


# Keep the official bot filename as emily_ai_bot.py.
# This tiny launcher only wires the multi-key AI pool and concurrency settings.
router = AIRouter()

# Preserve backward compatibility with emily_ai_bot.py's existing environment check.
if not os.getenv("OPENAI_API_KEY"):
    first_openai = os.getenv("OPENAI_API_KEY_1", "").strip()
    if first_openai:
        os.environ["OPENAI_API_KEY"] = first_openai

# Replace the old single-key OpenAI function with the provider pool.
emily.openai_responses_create = router.generate_sync
emily.VERSION = "3.1.0-multikey"

# Emily has no ConversationHandler/stateful sequential flow, so concurrent updates are safe.
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
