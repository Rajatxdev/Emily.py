from __future__ import annotations

import threading

from ai_router import AIProviderError, AIRouter, ProviderKey


def test_load_keys_uses_only_populated_numbered_slots(monkeypatch):
    names = [
        *(f"GEMINI_API_KEY_{i}" for i in range(1, 5)),
        *(f"OPENAI_API_KEY_{i}" for i in range(1, 3)),
        "OPENAI_API_KEY",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-test-key")
    monkeypatch.setenv("OPENAI_API_KEY_2", "openai-test-key")

    keys = AIRouter._load_keys()

    assert [(item.provider, item.slot, item.key) for item in keys] == [
        ("gemini", 1, "gemini-test-key"),
        ("openai", 2, "openai-test-key"),
    ]


def test_normalize_gemini_contents_merges_adjacent_roles():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "One more thing"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Thanks"},
    ]

    result = AIRouter._normalize_gemini_contents(messages)

    assert [item["role"] for item in result] == ["user", "model", "user"]
    assert result[0]["parts"] == [{"text": "Hello"}, {"text": "One more thing"}]
    assert result[1]["parts"] == [{"text": "Hi"}]


def test_openai_text_prefers_output_text_and_supports_output_parts():
    assert AIRouter._openai_text({"output_text": "  Hello  "}) == "Hello"
    assert AIRouter._openai_text({
        "output": [{"content": [{"type": "output_text", "text": "Fallback answer"}]}]
    }) == "Fallback answer"


def test_quota_exhaustion_detection_handles_provider_payloads():
    assert AIRouter._is_quota_exhausted(
        '{"error":{"code":"insufficient_quota","type":"insufficient_quota"}}'
    )
    assert AIRouter._is_quota_exhausted('{"error":{"status":"RESOURCE_EXHAUSTED"}}')
    assert not AIRouter._is_quota_exhausted('{"error":{"code":"rate_limit_exceeded"}}')


def test_generate_sync_fails_over_after_a_transient_provider_error(monkeypatch):
    router = AIRouter.__new__(AIRouter)
    router._lock = threading.Lock()
    router._cursor = 0
    router.keys = [
        ProviderKey("gemini", "test-gemini", "test-model", 1),
        ProviderKey("openai", "test-openai", "test-model", 1),
    ]

    def fail_gemini(item, instructions, messages):
        raise AIProviderError("rate_limit", "simulated temporary limit")

    monkeypatch.setattr(router, "_gemini", fail_gemini)
    monkeypatch.setattr(router, "_openai", lambda item, instructions, messages: "fallback answer")

    result = router.generate_sync("Be helpful.", [{"role": "user", "content": "Hi"}])

    assert result == "fallback answer"
    assert router.keys[0].total_failures == 1
    assert router.keys[0].inflight == 0
    assert router.keys[1].successes == 1
    assert router.keys[1].inflight == 0
