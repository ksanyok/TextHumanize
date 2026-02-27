"""AI backend provider for enhanced text processing.

Three-tier system:
1. OpenAI API (if key provided — default)
2. OSS model via Gradio (alternative, rate-limited)
3. Built-in rule-based (always available)

Usage:
    from texthumanize.ai_backend import AIBackend

    # Auto-detect best available backend
    backend = AIBackend()  # built-in only

    # With OpenAI (becomes default)
    backend = AIBackend(openai_api_key="sk-...")

    # With OSS model enabled (alternative)
    backend = AIBackend(enable_oss=True)

    # Paraphrase
    result = backend.paraphrase(
        "Text to paraphrase", lang="en"
    )

    # Rewrite sentence
    result = backend.rewrite_sentence(
        "Original sentence",
        lang="en",
        style="casual",
    )
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────
#  Prompt templates
# ───────────────────────────────────────────────────────

_PROMPT_PARAPHRASE = (
    "Rewrite the following text naturally in {lang}, "
    "preserving meaning but changing structure and "
    "word choice. Do not add explanations. "
    "Only output the rewritten text."
)

_PROMPT_REWRITE = (
    "Rewrite this single sentence to sound more "
    "natural and human-written in {lang}. "
    "{instruction} "
    "Only output the rewritten sentence."
)

_PROMPT_NATURALNESS = (
    "Improve the naturalness of this text. "
    "Make it sound like it was written by a human. "
    "Vary sentence lengths. Use natural transitions. "
    "Language: {lang}. "
    "Only output the improved text."
)

# ───────────────────────────────────────────────────────
#  Priority order for backend fallback
# ───────────────────────────────────────────────────────

_FALLBACK_ORDER = ("openai", "oss", "builtin")

# ═══════════════════════════════════════════════════════
#  OpenAI provider
# ═══════════════════════════════════════════════════════

class _OpenAIProvider:
    """Calls OpenAI Chat Completions API via urllib."""

    _API_URL = (
        "https://api.openai.com/v1/chat/completions"
    )

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._timeout = timeout

    # ── public ──────────────────────────────────────

    def call(
        self,
        system_prompt: str,
        user_text: str,
    ) -> str:
        """Send a chat completion request.

        Args:
            system_prompt: System-level instruction.
            user_text: The user content to process.

        Returns:
            The assistant's reply text.

        Raises:
            RuntimeError: On any HTTP / parsing error.
        """
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        req = urllib.request.Request(
            self._API_URL,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self._timeout
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")
            except Exception:
                pass
            raise RuntimeError(
                f"OpenAI API HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"OpenAI API connection error: {exc.reason}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"OpenAI API error: {exc}"
            ) from exc

        try:
            return str(
                data["choices"][0]["message"]["content"]
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "OpenAI API: unexpected response format"
            ) from exc

# ═══════════════════════════════════════════════════════
#  OSS Gradio provider (rate-limited, circuit-broken)
# ═══════════════════════════════════════════════════════

class _OSSProvider:
    """Calls amd/gpt-oss-120b-chatbot Gradio endpoint.

    Rate-limited to avoid overwhelming the free API.
    Circuit breaker disables after consecutive failures.
    """

    _DEFAULT_URL = (
        "https://amd-gpt-oss-120b-chatbot.hf.space"
        "/api/predict"
    )
    _MAX_CONSECUTIVE_FAILURES = 3
    _CIRCUIT_COOLDOWN = 300.0  # 5 minutes
    _MAX_RETRIES = 2

    def __init__(
        self,
        rate_limit: float = 10.0,
        timeout: float = 60.0,
        *,
        api_url: str | None = None,
    ) -> None:
        self._api_url = api_url or self._DEFAULT_URL
        self._rate_limit = rate_limit
        self._timeout = timeout
        self._lock = threading.Lock()
        self._last_request_ts: float = 0.0
        self._consecutive_failures: int = 0
        self._circuit_open_ts: float = 0.0

    # ── circuit breaker ────────────────────────────

    @property
    def is_available(self) -> bool:
        """Return False when circuit breaker is open."""
        if self._consecutive_failures < (
            self._MAX_CONSECUTIVE_FAILURES
        ):
            return True
        elapsed = time.monotonic() - self._circuit_open_ts
        if elapsed >= self._CIRCUIT_COOLDOWN:
            # Reset after cooldown
            self._consecutive_failures = 0
            return True
        return False

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= (
            self._MAX_CONSECUTIVE_FAILURES
        ):
            self._circuit_open_ts = time.monotonic()
            logger.warning(
                "OSS circuit breaker opened — "
                "disabled for %ds",
                int(self._CIRCUIT_COOLDOWN),
            )

    # ── rate limiter ───────────────────────────────

    def _wait_for_rate_limit(self) -> None:
        """Wait for rate limit window, non-blocking check first."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_ts
            if elapsed < self._rate_limit:
                wait = min(
                    self._rate_limit - elapsed,
                    self._rate_limit,
                )
                # Release lock during sleep to avoid blocking
                self._lock.release()
                try:
                    time.sleep(wait)
                finally:
                    self._lock.acquire()
            self._last_request_ts = time.monotonic()

    # ── public ─────────────────────────────────────

    def call(
        self,
        system_prompt: str,
        user_text: str,
    ) -> str:
        """Send request to OSS Gradio endpoint.

        Args:
            system_prompt: System-level instruction.
            user_text: The user content to process.

        Returns:
            The model's reply text.

        Raises:
            RuntimeError: On HTTP, rate-limit, or
                circuit breaker errors.
        """
        if not self.is_available:
            raise RuntimeError(
                "OSS provider circuit breaker is open"
            )

        self._wait_for_rate_limit()

        prompt = f"{system_prompt}\n\n{user_text}"
        payload: dict[str, Any] = {
            "data": [prompt],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }

        last_err: Exception | None = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            req = urllib.request.Request(
                self._api_url,
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    req, timeout=self._timeout
                ) as resp:
                    data = json.loads(
                        resp.read().decode("utf-8")
                    )
                # Parse response
                result = data.get("data", [None])[0]
                if result is None:
                    raise ValueError("empty response")
                self._record_success()
                return str(result).strip()
            except urllib.error.HTTPError as exc:
                last_err = exc
                code = exc.code
                # Retry on 5xx server errors
                if code >= 500 and attempt < self._MAX_RETRIES:
                    wait = 2.0 * attempt
                    time.sleep(wait)
                    continue
                self._record_failure()
                detail = ""
                try:
                    detail = exc.read().decode(
                        "utf-8", "replace"
                    )
                except Exception:
                    pass
                raise RuntimeError(
                    f"OSS API HTTP {exc.code}: {detail}"
                ) from exc
            except urllib.error.URLError as exc:
                last_err = exc
                if attempt < self._MAX_RETRIES:
                    time.sleep(2.0 * attempt)
                    continue
                self._record_failure()
                raise RuntimeError(
                    f"OSS API connection error: {exc.reason}"
                ) from exc
            except (
                KeyError, IndexError,
                TypeError, ValueError,
            ) as exc:
                self._record_failure()
                raise RuntimeError(
                    "OSS API: unexpected response format"
                ) from exc
            except Exception as exc:
                last_err = exc
                if attempt < self._MAX_RETRIES:
                    time.sleep(2.0 * attempt)
                    continue
                self._record_failure()
                raise RuntimeError(
                    f"OSS API error: {exc}"
                ) from exc

        self._record_failure()
        raise RuntimeError(
            f"OSS API: all {self._MAX_RETRIES} retries failed: "
            f"{last_err}"
        )

# ═══════════════════════════════════════════════════════
#  Built-in provider (always available)
# ═══════════════════════════════════════════════════════

class _BuiltinProvider:
    """Wraps the library's own rule-based engine.

    Uses humanize(), paraphrase(), and spin() from
    ``texthumanize.core``. Always available, never
    raises on normal input.
    """

    def paraphrase(
        self, text: str, lang: str = "en"
    ) -> str:
        """Paraphrase via built-in engine.

        Args:
            text: Text to paraphrase.
            lang: Language code.

        Returns:
            Paraphrased text.
        """
        from texthumanize.core import paraphrase
        return paraphrase(text, lang=lang, intensity=0.6)

    def rewrite_sentence(
        self,
        sentence: str,
        lang: str = "en",
    ) -> str:
        """Rewrite a single sentence via spin.

        Args:
            sentence: Sentence to rewrite.
            lang: Language code.

        Returns:
            Rewritten sentence.
        """
        from texthumanize.core import spin
        return spin(sentence, lang=lang, intensity=0.5)

    def improve_naturalness(
        self, text: str, lang: str = "en"
    ) -> str:
        """Improve naturalness via humanize.

        Args:
            text: Text to improve.
            lang: Language code.

        Returns:
            More natural version of the text.
        """
        from texthumanize.core import humanize
        result = humanize(
            text, lang=lang, profile="web", intensity=70
        )
        return result.text

# ═══════════════════════════════════════════════════════
#  Main AIBackend facade
# ═══════════════════════════════════════════════════════

class AIBackend:
    """Unified AI backend with three-tier fallback.

    Priority (when ``prefer="auto"``):
        1. OpenAI — if ``openai_api_key`` provided
        2. OSS   — if ``enable_oss=True``
        3. Built-in — always available

    On failure of a higher-priority backend the next
    one in the list is tried. Built-in never fails on
    valid input.

    Args:
        openai_api_key: OpenAI API key (optional).
        openai_model: Model for OpenAI calls.
        enable_oss: Enable the OSS Gradio backend.
        oss_rate_limit: Min seconds between OSS calls.
        prefer: Backend preference strategy.
            ``"auto"`` picks the best available.
            ``"openai"``, ``"oss"``, ``"builtin"``
            force a specific backend (with fallback).
    """

    _VALID_PREFER = ("auto", "openai", "oss", "builtin")

    def __init__(
        self,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4o-mini",
        enable_oss: bool = False,
        oss_rate_limit: float = 10.0,
        oss_api_url: str | None = None,
        prefer: str = "auto",
    ) -> None:
        if prefer not in self._VALID_PREFER:
            raise ValueError(
                f"prefer must be one of "
                f"{self._VALID_PREFER}, got {prefer!r}"
            )

        self._prefer = prefer
        self._builtin = _BuiltinProvider()

        # OpenAI provider
        self._openai: _OpenAIProvider | None = None
        if openai_api_key:
            self._openai = _OpenAIProvider(
                api_key=openai_api_key,
                model=openai_model,
            )

        # OSS provider
        self._oss: _OSSProvider | None = None
        if enable_oss:
            self._oss = _OSSProvider(
                rate_limit=oss_rate_limit,
                api_url=oss_api_url,
            )

        # Resolved active backend name (cached)
        self._lock = threading.Lock()
        self._last_used: str = "builtin"

    # ── backend resolution ─────────────────────────

    def available_backends(self) -> list[str]:
        """Return names of currently available backends.

        Returns:
            List such as ``["openai", "builtin"]``.
        """
        result: list[str] = []
        if self._openai is not None:
            result.append("openai")
        if (
            self._oss is not None
            and self._oss.is_available
        ):
            result.append("oss")
        result.append("builtin")
        return result

    def active_backend(self) -> str:
        """Return the name of the last used backend.

        Returns:
            ``"openai"``, ``"oss"``, or ``"builtin"``.
        """
        return self._last_used

    def _resolve_order(self) -> list[str]:
        """Build ordered list of backends to try.

        Returns:
            List of backend names in priority order.
        """
        if self._prefer == "auto":
            order: list[str] = []
            if self._openai is not None:
                order.append("openai")
            if (
                self._oss is not None
                and self._oss.is_available
            ):
                order.append("oss")
            order.append("builtin")
            return order

        first = self._prefer
        remaining = [
            b for b in _FALLBACK_ORDER if b != first
        ]
        return [first] + remaining

    # ── internal dispatch ──────────────────────────

    def _call_external(
        self,
        backend: str,
        system_prompt: str,
        user_text: str,
    ) -> str | None:
        """Try calling an external backend.

        Args:
            backend: ``"openai"`` or ``"oss"``.
            system_prompt: The system instruction.
            user_text: The user text.

        Returns:
            Response text, or None on failure.
        """
        try:
            if backend == "openai" and self._openai:
                return self._openai.call(
                    system_prompt, user_text
                )
            if backend == "oss" and self._oss:
                return self._oss.call(
                    system_prompt, user_text
                )
        except RuntimeError:
            logger.debug(
                "Backend %s failed, falling back",
                backend,
                exc_info=True,
            )
        return None

    def _dispatch(
        self,
        system_prompt: str,
        user_text: str,
        builtin_fn: Any,
    ) -> str:
        """Try backends in priority order.

        Always succeeds — falls back to built-in.

        Args:
            system_prompt: The prompt for AI backends.
            user_text: The text to process.
            builtin_fn: Callable for built-in fallback.

        Returns:
            Processed text from the best available
            backend.
        """
        order = self._resolve_order()
        for name in order:
            if name == "builtin":
                with self._lock:
                    self._last_used = "builtin"
                logger.debug(
                    "Using built-in backend"
                )
                return str(builtin_fn())

            result = self._call_external(
                name, system_prompt, user_text
            )
            if result is not None:
                with self._lock:
                    self._last_used = name
                logger.debug(
                    "Used backend: %s", name
                )
                return result

        # Guaranteed fallback
        with self._lock:
            self._last_used = "builtin"
        return str(builtin_fn())

    # ── public API ─────────────────────────────────

    def paraphrase(
        self,
        text: str,
        lang: str = "en",
        style: str = "natural",
    ) -> str:
        """Paraphrase text using the best backend.

        Args:
            text: Text to paraphrase.
            lang: Language code (e.g. ``"en"``).
            style: Desired style hint (used in prompt).

        Returns:
            Paraphrased text.
        """
        if not text or not text.strip():
            return text
        prompt = _PROMPT_PARAPHRASE.format(lang=lang)
        if style and style != "natural":
            prompt += f" Style: {style}."
        return self._dispatch(
            system_prompt=prompt,
            user_text=text,
            builtin_fn=lambda: (
                self._builtin.paraphrase(text, lang=lang)
            ),
        )

    def rewrite_sentence(
        self,
        sentence: str,
        lang: str = "en",
        instruction: str = "",
    ) -> str:
        """Rewrite a single sentence more naturally.

        Args:
            sentence: The sentence to rewrite.
            lang: Language code.
            instruction: Extra instruction for the AI
                (e.g. ``"make it more formal"``).

        Returns:
            Rewritten sentence.
        """
        if not sentence or not sentence.strip():
            return sentence
        prompt = _PROMPT_REWRITE.format(
            lang=lang,
            instruction=instruction or "",
        )
        return self._dispatch(
            system_prompt=prompt,
            user_text=sentence,
            builtin_fn=lambda: (
                self._builtin.rewrite_sentence(
                    sentence, lang=lang
                )
            ),
        )

    def improve_naturalness(
        self,
        text: str,
        lang: str = "en",
    ) -> str:
        """Improve text naturalness overall.

        Args:
            text: Text to improve.
            lang: Language code.

        Returns:
            Text with improved naturalness.
        """
        if not text or not text.strip():
            return text
        prompt = _PROMPT_NATURALNESS.format(lang=lang)
        return self._dispatch(
            system_prompt=prompt,
            user_text=text,
            builtin_fn=lambda: (
                self._builtin.improve_naturalness(
                    text, lang=lang
                )
            ),
        )
