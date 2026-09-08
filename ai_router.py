from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
AI_TIMEOUT = float(os.getenv("EMILY_AI_TIMEOUT", "30"))
KEY_COOLDOWN = float(os.getenv("EMILY_KEY_COOLDOWN", "20"))
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENAI_URL = "https://api.openai.com/v1/responses"


class AIProviderError(RuntimeError):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


@dataclass
class ProviderKey:
    provider: str
    key: str
    model: str
    slot: int
    inflight: int = 0
    cooldown_until: float = 0.0
    disabled: bool = False
    failures: int = 0

    @property
    def label(self) -> str:
        return f"{self.provider}{self.slot}"


class AIRouter:
    """Small thread-safe pool that load-balances requests across six optional keys."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cursor = 0
        self.keys = self._load_keys()
        if not self.keys:
            raise RuntimeError(
                "No AI keys configured. Add GEMINI_API_KEY_1..4 and/or OPENAI_API_KEY_1..2 to .env"
            )

    @staticmethod
    def _load_keys() -> list[ProviderKey]:
        result: list[ProviderKey] = []
        for slot in range(1, 5):
            key = os.getenv(f"GEMINI_API_KEY_{slot}", "").strip()
            if key:
                result.append(
                    ProviderKey(
                        "gemini",
                        key,
                        os.getenv(f"GEMINI_MODEL_{slot}", GEMINI_MODEL),
                        slot,
                    )
                )
        for slot in range(1, 3):
            key = os.getenv(f"OPENAI_API_KEY_{slot}", "").strip()
            if key:
                result.append(
                    ProviderKey(
                        "openai",
                        key,
                        os.getenv(f"OPENAI_MODEL_{slot}", OPENAI_MODEL),
                        slot,
                    )
                )
        legacy = os.getenv("OPENAI_API_KEY", "").strip()
        if not result and legacy:
            result.append(ProviderKey("openai", legacy, OPENAI_MODEL, 1))
        return result

    def _pick(self, excluded: set[str]) -> Optional[ProviderKey]:
        now = time.monotonic()
        with self._lock:
            candidates = [
                item
                for item in self.keys
                if item.label not in excluded
                and not item.disabled
                and item.cooldown_until <= now
            ]
            if not candidates:
                return None
            load = min(item.inflight for item in candidates)
            least_busy = [item for item in candidates if item.inflight == load]
            item = least_busy[self._cursor % len(least_busy)]
            self._cursor += 1
            item.inflight += 1
            return item

    def _success(self, item: ProviderKey) -> None:
        with self._lock:
            item.inflight = max(0, item.inflight - 1)
            item.failures = 0

    def _failure(self, item: ProviderKey, error_type: str) -> None:
        with self._lock:
            item.inflight = max(0, item.inflight - 1)
            item.failures += 1
            if error_type == "authentication":
                item.disabled = True
            else:
                item.cooldown_until = time.monotonic() + KEY_COOLDOWN

    @staticmethod
    def _body_error(exc: urllib.error.HTTPError) -> str:
        try:
            return exc.read().decode("utf-8", errors="replace")[:600]
        except Exception:
            return ""

    @staticmethod
    def _openai_text(payload: dict) -> str:
        text = payload.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        parts: list[str] = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    parts.append(content["text"])
        return "\n".join(parts).strip()

    def _openai(self, item: ProviderKey, instructions: str, messages: list[dict[str, str]]) -> str:
        body = json.dumps(
            {
                "model": item.model,
                "instructions": instructions,
                "input": messages,
                "max_output_tokens": 500,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            OPENAI_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {item.key}",
                "Content-Type": "application/json",
                "User-Agent": "EmilyTelegramBot/3.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=AI_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = self._body_error(exc)
            if exc.code in {401, 403}:
                raise AIProviderError("authentication", f"OpenAI HTTP {exc.code}: {details}") from exc
            if exc.code == 429:
                raise AIProviderError("rate_limit", f"OpenAI HTTP 429: {details}") from exc
            raise AIProviderError("provider_error", f"OpenAI HTTP {exc.code}: {details}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            kind = "timeout" if "timed out" in str(exc).lower() else "network"
            raise AIProviderError(kind, str(exc)) from exc
        text = self._openai_text(payload)
        if not text:
            raise AIProviderError("provider_error", "OpenAI returned no text")
        return text

    def _gemini(self, item: ProviderKey, instructions: str, messages: list[dict[str, str]]) -> str:
        contents = [
            {
                "role": "user",
                "parts": [{"text": f"System instructions for Emily:\n{instructions}"}],
            }
        ]
        for message in messages:
            contents.append(
                {
                    "role": "model" if message["role"] == "assistant" else "user",
                    "parts": [{"text": message["content"]}],
                }
            )
        body = json.dumps({"contents": contents, "generationConfig": {"maxOutputTokens": 500}}).encode("utf-8")
        request = urllib.request.Request(
            GEMINI_URL.format(model=item.model),
            data=body,
            headers={
                "x-goog-api-key": item.key,
                "Content-Type": "application/json",
                "User-Agent": "EmilyTelegramBot/3.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=AI_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = self._body_error(exc)
            if exc.code in {401, 403}:
                raise AIProviderError("authentication", f"Gemini HTTP {exc.code}: {details}") from exc
            if exc.code == 429:
                raise AIProviderError("rate_limit", f"Gemini HTTP 429: {details}") from exc
            raise AIProviderError("provider_error", f"Gemini HTTP {exc.code}: {details}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            kind = "timeout" if "timed out" in str(exc).lower() else "network"
            raise AIProviderError(kind, str(exc)) from exc
        parts: list[str] = []
        for candidate in payload.get("candidates", []) or []:
            content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
            for part in content.get("parts", []) or []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        text = "\n".join(parts).strip()
        if not text:
            raise AIProviderError("provider_error", "Gemini returned no text")
        return text

    def generate_sync(self, instructions: str, messages: list[dict[str, str]]) -> str:
        excluded: set[str] = set()
        last_error: Optional[AIProviderError] = None
        for _ in range(len(self.keys)):
            item = self._pick(excluded)
            if item is None:
                break
            excluded.add(item.label)
            try:
                result = self._gemini(item, instructions, messages) if item.provider == "gemini" else self._openai(item, instructions, messages)
                self._success(item)
                return result
            except AIProviderError as exc:
                last_error = exc
                self._failure(item, exc.error_type)
                logger_message = f"{item.label} failed: {exc.error_type}"
                print(logger_message)
        raise last_error or AIProviderError("provider_error", "All configured AI keys are unavailable")

    def status_text(self) -> str:
        now = time.monotonic()
        with self._lock:
            lines = ["🤖 Emily AI pool", ""]
            for item in self.keys:
                if item.disabled:
                    state = "disabled"
                elif item.cooldown_until > now:
                    state = f"cooldown {max(1, int(item.cooldown_until - now))}s"
                else:
                    state = "ready"
                lines.append(f"• {item.label}: {state} | in-flight={item.inflight} | failures={item.failures}")
            return "\n".join(lines)
