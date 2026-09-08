from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

AI_TIMEOUT = float(os.getenv("EMILY_AI_TIMEOUT", "30"))
KEY_COOLDOWN = float(os.getenv("EMILY_KEY_COOLDOWN", "20"))
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"


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
    """Thread-safe AI pool. Balances requests and fails over across all configured keys."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cursor = 0
        self.keys = self._load_keys()
        if not self.keys:
            raise RuntimeError("No AI keys configured. Add GEMINI_API_KEY_1..4 and/or OPENAI_API_KEY_1..2 to .env")

    @staticmethod
    def _load_keys() -> list[ProviderKey]:
        result: list[ProviderKey] = []
        for slot in range(1, 5):
            key = os.getenv(f"GEMINI_API_KEY_{slot}", "").strip()
            if key:
                result.append(ProviderKey("gemini", key, os.getenv(f"GEMINI_MODEL_{slot}", "").strip(), slot))
        for slot in range(1, 3):
            key = os.getenv(f"OPENAI_API_KEY_{slot}", "").strip()
            if key:
                result.append(ProviderKey("openai", key, os.getenv(f"OPENAI_MODEL_{slot}", "").strip(), slot))
        legacy = os.getenv("OPENAI_API_KEY", "").strip()
        if not result and legacy:
            result.append(ProviderKey("openai", legacy, os.getenv("OPENAI_MODEL", "").strip(), 1))
        return result

    @staticmethod
    def _get_json(url: str, headers: dict[str, str]) -> dict:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=AI_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    def _discover_gemini_model(self, item: ProviderKey) -> str:
        payload = self._get_json(GEMINI_MODELS_URL, {"x-goog-api-key": item.key})
        models = payload.get("models", []) or []
        usable = []
        for model in models:
            if not isinstance(model, dict):
                continue
            methods = model.get("supportedGenerationMethods", []) or []
            name = str(model.get("name", ""))
            if "generateContent" in methods and name.startswith("models/"):
                usable.append(name.split("/", 1)[1])
        if not usable:
            raise AIProviderError("provider_error", f"{item.label}: no Gemini generateContent model is available")
        preferred = [m for m in usable if "flash" in m.lower() and "image" not in m.lower()]
        return sorted(preferred or usable)[0]

    def _discover_openai_model(self, item: ProviderKey) -> str:
        payload = self._get_json(OPENAI_MODELS_URL, {"Authorization": f"Bearer {item.key}"})
        ids = [str(row.get("id", "")) for row in payload.get("data", []) or [] if isinstance(row, dict)]
        ids = [m for m in ids if m]
        preferred = ["gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"]
        for candidate in preferred:
            if candidate in ids:
                return candidate
        usable = [m for m in ids if m.lower().startswith(("gpt-", "chatgpt-")) and "audio" not in m.lower()]
        if not usable:
            raise AIProviderError("provider_error", f"{item.label}: no suitable OpenAI text model is available")
        return sorted(usable)[0]

    def _ensure_model(self, item: ProviderKey) -> None:
        if item.model:
            return
        try:
            item.model = self._discover_gemini_model(item) if item.provider == "gemini" else self._discover_openai_model(item)
            print(f"{item.label} selected model: {item.model}")
        except urllib.error.HTTPError as exc:
            details = self._body_error(exc)
            if exc.code in {401, 403}:
                raise AIProviderError("authentication", f"{item.label} model discovery HTTP {exc.code}: {details}") from exc
            if exc.code == 429:
                if self._is_quota_exhausted(details):
                    raise AIProviderError("quota_exhausted", f"{item.label} model discovery quota exhausted: {details}") from exc
                raise AIProviderError("rate_limit", f"{item.label} model discovery HTTP 429: {details}") from exc
            raise AIProviderError("provider_error", f"{item.label} model discovery HTTP {exc.code}: {details}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AIProviderError("network", f"{item.label} model discovery failed: {exc}") from exc

    def _pick(self, excluded: set[str]) -> Optional[ProviderKey]:
        now = time.monotonic()
        with self._lock:
            candidates = [item for item in self.keys if item.label not in excluded and not item.disabled and item.cooldown_until <= now]
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
            if error_type in {"authentication", "quota_exhausted"}:
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
    def _is_quota_exhausted(details: str) -> bool:
        try:
            payload = json.loads(details)
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            code = str(error.get("code", "")).lower()
            kind = str(error.get("type", "")).lower()
            status = str(error.get("status", "")).lower()
            return code in {"credit_balance_exhausted", "insufficient_quota", "quota_exceeded"} or kind == "insufficient_quota" or status in {"resource_exhausted", "quota_exceeded"}
        except (TypeError, ValueError, json.JSONDecodeError):
            lowered = details.lower()
            return any(marker in lowered for marker in ("insufficient_quota", "credit_balance_exhausted", "quota exceeded", "quota_exhausted"))

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
        self._ensure_model(item)
        body = json.dumps({"model": item.model, "instructions": instructions, "input": messages, "max_output_tokens": 500}).encode("utf-8")
        request = urllib.request.Request(OPENAI_URL, data=body, headers={"Authorization": f"Bearer {item.key}", "Content-Type": "application/json", "User-Agent": "EmilyTelegramBot/3.1"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=AI_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = self._body_error(exc)
            if exc.code in {401, 403}:
                raise AIProviderError("authentication", f"OpenAI HTTP {exc.code}: {details}") from exc
            if exc.code == 429:
                error_type = "quota_exhausted" if self._is_quota_exhausted(details) else "rate_limit"
                raise AIProviderError(error_type, f"OpenAI HTTP 429: {details}") from exc
            if exc.code in {400, 404}:
                raise AIProviderError("model_error", f"OpenAI HTTP {exc.code}: {details}") from exc
            raise AIProviderError("provider_error", f"OpenAI HTTP {exc.code}: {details}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AIProviderError("timeout" if "timed out" in str(exc).lower() else "network", str(exc)) from exc
        text = self._openai_text(payload)
        if not text:
            raise AIProviderError("provider_error", "OpenAI returned no text")
        return text

    @staticmethod
    def _normalize_gemini_contents(messages: list[dict[str, str]]) -> list[dict[str, object]]:
        contents: list[dict[str, object]] = []
        for message in messages:
            role = "model" if message.get("role") == "assistant" else "user"
            text = str(message.get("content", ""))
            if not text:
                continue
            if contents and contents[-1]["role"] == role:
                parts = contents[-1]["parts"]
                assert isinstance(parts, list)
                parts.append({"text": text})
            else:
                contents.append({"role": role, "parts": [{"text": text}]})
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Please respond helpfully to the user."}]})
        return contents

    def _gemini(self, item: ProviderKey, instructions: str, messages: list[dict[str, str]]) -> str:
        self._ensure_model(item)
        contents = self._normalize_gemini_contents(messages)
        body = json.dumps({
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 500},
        }).encode("utf-8")
        request = urllib.request.Request(GEMINI_URL.format(model=item.model), data=body, headers={"x-goog-api-key": item.key, "Content-Type": "application/json", "User-Agent": "EmilyTelegramBot/3.1"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=AI_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = self._body_error(exc)
            if exc.code in {401, 403}:
                raise AIProviderError("authentication", f"Gemini HTTP {exc.code}: {details}") from exc
            if exc.code == 429:
                error_type = "quota_exhausted" if self._is_quota_exhausted(details) else "rate_limit"
                raise AIProviderError(error_type, f"Gemini HTTP 429: {details}") from exc
            if exc.code in {400, 404}:
                raise AIProviderError("model_error", f"Gemini HTTP {exc.code}: {details}") from exc
            raise AIProviderError("provider_error", f"Gemini HTTP {exc.code}: {details}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AIProviderError("timeout" if "timed out" in str(exc).lower() else "network", str(exc)) from exc
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
                print(f"{item.label} failed: {exc.error_type}: {exc}")
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
                model = item.model or "auto"
                lines.append(f"• {item.label}: {state} | model={model} | in-flight={item.inflight} | failures={item.failures}")
            return "\n".join(lines)
