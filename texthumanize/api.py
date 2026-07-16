"""TextHumanize REST API — минимальный HTTP-сервер на stdlib.

Предоставляет JSON API для всех функций библиотеки:
    POST /humanize       — гуманизация текста
    POST /analyze        — анализ текста
    POST /detect-ai      — проверка AI-генерации
    POST /paraphrase     — перефразирование
    POST /tone/analyze   — анализ тональности
    POST /tone/adjust    — коррекция тональности
    POST /watermarks/detect — обнаружение водяных знаков
    POST /watermarks/clean  — очистка водяных знаков
    POST /spin           — спиннинг текста
    POST /spin/variants  — генерация вариантов
    POST /coherence      — анализ когерентности
    POST /readability    — полная читабельность
    GET  /health         — проверка работоспособности
    GET  /openapi.json   — OpenAPI 3.1 schema

Запуск:
    python -m texthumanize.api --port 8080
    # или
    from texthumanize.api import create_app, run_server
    run_server(port=8080)
"""

from __future__ import annotations

import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from typing import Any

from texthumanize import __version__
from texthumanize._urlguard import validate_outbound_url
from texthumanize.core import (
    adjust_tone,
    analyze,
    analyze_coherence,
    analyze_tone,
    clean_watermarks,
    detect_ai,
    detect_ai_batch,
    detect_watermarks,
    full_readability,
    humanize,
    paraphrase,
    spin,
    spin_variants,
)
from texthumanize.exceptions import UnsafeURLError

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────

def _cors_origin() -> str:
    """Allowed CORS origin.

    Defaults to ``*`` (open) for backward compatibility and local use.
    Set ``TEXTHUMANIZE_API_CORS_ORIGIN`` to a specific origin (e.g.
    ``https://app.example.com``) to lock browser access down.
    """
    return os.environ.get("TEXTHUMANIZE_API_CORS_ORIGIN", "*").strip() or "*"


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200) -> None:
    """Отправить JSON-ответ."""
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", _cors_origin())
    handler.end_headers()
    handler.wfile.write(body)

MAX_REQUEST_BODY = 5_000_000  # 5 MB


# ─── Remote-backend gate (SSRF hardening) ─────────────────────
#
# The REST API is an unauthenticated network boundary. Client-supplied
# AI-backend parameters (``backend``, ``oss_api_url``, ``openai_api_key``,
# ``ollama_url``) let a caller make the server perform outbound requests,
# which is an SSRF / abuse primitive (CWE-918). These parameters are
# therefore DISABLED by default and only honoured when the operator opts
# in via the environment. Even when enabled, any URL is SSRF-validated so
# it cannot target loopback/private/link-local (cloud-metadata) addresses.

_REMOTE_BACKEND_KEYS = (
    "oss_api_url",
    "openai_api_key",
    "openai_model",
    "ollama_url",
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class RemoteBackendDisabled(Exception):
    """Raised when a request uses remote-backend params that are gated off."""


def _remote_backends_allowed() -> bool:
    """Whether client-supplied remote AI backends are permitted.

    Controlled by ``TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS`` (off by default).
    Read per-request so operators/tests can toggle it without a restart.
    """
    val = os.environ.get("TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS", "")
    return val.strip().lower() in _TRUE_VALUES

# ─── Rate Limiter ─────────────────────────────────────────────

class _TokenBucketLimiter:
    """Simple per-IP token bucket rate limiter (in-memory)."""

    def __init__(self, rate: float = 10.0, burst: int = 20) -> None:
        self._rate = rate      # tokens per second
        self._burst = burst    # max tokens
        self._buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_time)

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(ip, (float(self._burst), now))
        elapsed = now - last
        tokens = min(self._burst, tokens + elapsed * self._rate)
        if tokens >= 1.0:
            self._buckets[ip] = (tokens - 1.0, now)
            return True
        self._buckets[ip] = (tokens, now)
        return False


_rate_limiter = _TokenBucketLimiter(rate=10.0, burst=20)

def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    """Прочитать JSON из тела запроса."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    if length > MAX_REQUEST_BODY:
        raise ValueError(
            f"Request body too large ({length} bytes, max {MAX_REQUEST_BODY})"
        )
    raw = handler.rfile.read(length)
    return dict(json.loads(raw.decode("utf-8")))

def _require_text(data: dict) -> str:
    """Извлечь обязательное поле text."""
    text = data.get("text")
    if not text or not isinstance(text, str):
        raise ValueError("Поле 'text' обязательно и должно быть строкой")
    return str(text)

# ─── Route handlers ──────────────────────────────────────────

def _handle_humanize(data: dict) -> dict:
    text = _require_text(data)
    kwargs: dict[str, Any] = {
        "lang": data.get("lang", "auto"),
        "profile": data.get("profile", "web"),
        "intensity": data.get("intensity", 60),
        "seed": data.get("seed"),
    }
    # AI backend support — gated off by default (SSRF hardening).
    backend = data.get("backend", "local")
    wants_remote = backend not in ("local", "builtin") or any(
        data.get(k) for k in _REMOTE_BACKEND_KEYS
    )
    if wants_remote and not _remote_backends_allowed():
        raise RemoteBackendDisabled(
            "Remote AI backends are disabled on this server. "
            "Set TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS=1 to enable them; "
            "the default 'local' backend requires no network access."
        )

    if backend != "local":
        kwargs["backend"] = backend
    if data.get("openai_api_key"):
        kwargs["openai_api_key"] = data["openai_api_key"]
    if data.get("openai_model"):
        kwargs["openai_model"] = data["openai_model"]
    if data.get("oss_api_url"):
        # Validate before it reaches urllib in the OSS provider (CWE-918).
        kwargs["oss_api_url"] = validate_outbound_url(str(data["oss_api_url"]))
    result = humanize(text, **kwargs)
    return {
        "text": result.text,
        "lang": result.lang,
        "profile": result.profile,
        "change_ratio": round(result.change_ratio, 4),
        "changes_count": len(result.changes),
    }

def _handle_analyze(data: dict) -> dict:
    text = _require_text(data)
    report = analyze(text, lang=data.get("lang", "auto"))
    return {
        "lang": report.lang,
        "total_words": report.total_words,
        "total_sentences": report.total_sentences,
        "avg_sentence_length": round(report.avg_sentence_length, 2),
        "burstiness_score": round(report.burstiness_score, 4),
        "artificiality_score": round(report.artificiality_score, 4),
        "flesch_kincaid_grade": round(report.flesch_kincaid_grade, 2),
        "coleman_liau_index": round(report.coleman_liau_index, 2),
    }

def _handle_detect_ai(data: dict) -> dict:
    text = data.get("text")
    texts = data.get("texts")
    if texts and isinstance(texts, list):
        return {"results": detect_ai_batch(texts, lang=data.get("lang", "auto"))}
    if text:
        return detect_ai(text, lang=data.get("lang", "auto"))  # type: ignore[return-value]
    raise ValueError("Поле 'text' или 'texts' обязательно")

def _handle_paraphrase(data: dict) -> dict:
    text = _require_text(data)
    result = paraphrase(
        text,
        lang=data.get("lang", "auto"),
        intensity=data.get("intensity", 0.5),
        seed=data.get("seed"),
    )
    return {"text": result}

def _handle_tone_analyze(data: dict) -> dict:
    text = _require_text(data)
    return analyze_tone(text, lang=data.get("lang", "auto"))

def _handle_tone_adjust(data: dict) -> dict:
    text = _require_text(data)
    result = adjust_tone(
        text,
        target=data.get("target", "neutral"),
        lang=data.get("lang", "auto"),
        intensity=data.get("intensity", 0.5),
    )
    return {"text": result}

def _handle_watermarks_detect(data: dict) -> dict:
    text = _require_text(data)
    return detect_watermarks(text, lang=data.get("lang", "auto"))

def _handle_watermarks_clean(data: dict) -> dict:
    text = _require_text(data)
    result = clean_watermarks(text, lang=data.get("lang", "auto"))
    return {"text": result}

def _handle_spin(data: dict) -> dict:
    text = _require_text(data)
    count = data.get("count")
    if count and isinstance(count, int) and count > 1:
        variants = spin_variants(
            text,
            count=count,
            lang=data.get("lang", "auto"),
            intensity=data.get("intensity", 0.5),
        )
        return {"variants": variants, "count": len(variants)}
    result = spin(
        text,
        lang=data.get("lang", "auto"),
        intensity=data.get("intensity", 0.5),
        seed=data.get("seed"),
    )
    return {"text": result}

def _handle_coherence(data: dict) -> dict:
    text = _require_text(data)
    return analyze_coherence(text, lang=data.get("lang", "auto"))

def _handle_readability(data: dict) -> dict:
    text = _require_text(data)
    return full_readability(text, lang=data.get("lang", "auto"))

# ─── Router ──────────────────────────────────────────────────

ROUTES: dict[str, Any] = {
    "/humanize": _handle_humanize,
    "/analyze": _handle_analyze,
    "/detect-ai": _handle_detect_ai,
    "/paraphrase": _handle_paraphrase,
    "/tone/analyze": _handle_tone_analyze,
    "/tone/adjust": _handle_tone_adjust,
    "/watermarks/detect": _handle_watermarks_detect,
    "/watermarks/clean": _handle_watermarks_clean,
    "/spin": _handle_spin,
    "/spin/variants": _handle_spin,
    "/coherence": _handle_coherence,
    "/readability": _handle_readability,
}

OPENAPI_JSON_PATH = "/openapi.json"
PUBLIC_ENDPOINTS = sorted([*ROUTES.keys(), "/sse/humanize"])


def _schema_ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def _json_request(schema_name: str, *, required: bool = True) -> dict[str, Any]:
    return {
        "required": required,
        "content": {
            "application/json": {
                "schema": _schema_ref(schema_name),
            },
        },
    }


def _json_response_schema(
    schema_name: str,
    description: str = "Successful response",
) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": _schema_ref(schema_name),
            },
        },
    }


def get_openapi_schema(server_url: str = "http://localhost:8080") -> dict[str, Any]:
    """Return an OpenAPI 3.1 schema for the stdlib REST API."""
    paths: dict[str, Any] = {
        "/": {
            "get": {
                "summary": "API index",
                "operationId": "getApiIndex",
                "responses": {
                    "200": _json_response_schema("ApiIndexResponse"),
                },
            },
        },
        "/health": {
            "get": {
                "summary": "Health check",
                "operationId": "getHealth",
                "responses": {
                    "200": _json_response_schema("HealthResponse"),
                },
            },
        },
        OPENAPI_JSON_PATH: {
            "get": {
                "summary": "OpenAPI schema",
                "operationId": "getOpenApiSchema",
                "responses": {
                    "200": {
                        "description": "OpenAPI 3.1 schema",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                            },
                        },
                    },
                },
            },
        },
        "/humanize": {
            "post": {
                "summary": "Humanize text",
                "operationId": "humanizeText",
                "requestBody": _json_request("HumanizeRequest"),
                "responses": {
                    "200": _json_response_schema("HumanizeResponse"),
                    "400": _json_response_schema("ErrorResponse", "Bad request"),
                    "429": _json_response_schema("ErrorResponse", "Rate limited"),
                    "500": _json_response_schema("ErrorResponse", "Server error"),
                },
            },
        },
        "/analyze": {
            "post": {
                "summary": "Analyze text metrics",
                "operationId": "analyzeText",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("AnalyzeResponse")},
            },
        },
        "/detect-ai": {
            "post": {
                "summary": "Detect AI-generated text",
                "operationId": "detectAi",
                "requestBody": _json_request("DetectAIRequest"),
                "responses": {"200": _json_response_schema("GenericObject")},
            },
        },
        "/paraphrase": {
            "post": {
                "summary": "Paraphrase text",
                "operationId": "paraphraseText",
                "requestBody": _json_request("ParaphraseRequest"),
                "responses": {"200": _json_response_schema("TextResponse")},
            },
        },
        "/tone/analyze": {
            "post": {
                "summary": "Analyze tone",
                "operationId": "analyzeTone",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("GenericObject")},
            },
        },
        "/tone/adjust": {
            "post": {
                "summary": "Adjust tone",
                "operationId": "adjustTone",
                "requestBody": _json_request("ToneAdjustRequest"),
                "responses": {"200": _json_response_schema("TextResponse")},
            },
        },
        "/watermarks/detect": {
            "post": {
                "summary": "Detect watermark signatures",
                "operationId": "detectWatermarks",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("GenericObject")},
            },
        },
        "/watermarks/clean": {
            "post": {
                "summary": "Remove watermark signatures",
                "operationId": "cleanWatermarks",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("TextResponse")},
            },
        },
        "/spin": {
            "post": {
                "summary": "Spin text or generate variants",
                "operationId": "spinText",
                "requestBody": _json_request("SpinRequest"),
                "responses": {
                    "200": {
                        "description": "Single spin or variants response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        _schema_ref("TextResponse"),
                                        _schema_ref("VariantsResponse"),
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        },
        "/spin/variants": {
            "post": {
                "summary": "Generate spin variants",
                "operationId": "spinVariants",
                "requestBody": _json_request("SpinRequest"),
                "responses": {"200": _json_response_schema("VariantsResponse")},
            },
        },
        "/coherence": {
            "post": {
                "summary": "Analyze coherence",
                "operationId": "analyzeCoherence",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("GenericObject")},
            },
        },
        "/readability": {
            "post": {
                "summary": "Analyze readability",
                "operationId": "analyzeReadability",
                "requestBody": _json_request("TextRequest"),
                "responses": {"200": _json_response_schema("GenericObject")},
            },
        },
        "/sse/humanize": {
            "post": {
                "summary": "Stream humanized chunks with Server-Sent Events",
                "operationId": "streamHumanize",
                "requestBody": _json_request("HumanizeRequest"),
                "responses": {
                    "200": {
                        "description": "text/event-stream response",
                        "content": {
                            "text/event-stream": {
                                "schema": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "TextHumanize REST API",
            "version": __version__,
            "description": (
                "Zero-dependency JSON API for text humanization, AI detection, "
                "watermark analysis, tone tools, spinning, coherence, and readability."
            ),
        },
        "servers": [{"url": server_url}],
        "paths": paths,
        "components": {
            "schemas": {
                "TextRequest": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string", "minLength": 1},
                        "lang": {"type": "string", "default": "auto"},
                    },
                    "additionalProperties": True,
                },
                "HumanizeRequest": {
                    "allOf": [
                        _schema_ref("TextRequest"),
                        {
                            "type": "object",
                            "properties": {
                                "profile": {"type": "string", "default": "web"},
                                "intensity": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                    "default": 60,
                                },
                                "seed": {"type": ["integer", "null"]},
                                "backend": {"type": "string", "default": "local"},
                                "openai_api_key": {"type": "string"},
                                "openai_model": {"type": "string"},
                                "oss_api_url": {"type": "string"},
                            },
                        },
                    ],
                },
                "DetectAIRequest": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 1},
                        "texts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "lang": {"type": "string", "default": "auto"},
                    },
                    "anyOf": [
                        {"required": ["text"]},
                        {"required": ["texts"]},
                    ],
                },
                "ParaphraseRequest": {
                    "allOf": [
                        _schema_ref("TextRequest"),
                        {
                            "type": "object",
                            "properties": {
                                "intensity": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "default": 0.5,
                                },
                                "seed": {"type": ["integer", "null"]},
                            },
                        },
                    ],
                },
                "ToneAdjustRequest": {
                    "allOf": [
                        _schema_ref("TextRequest"),
                        {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string", "default": "neutral"},
                                "intensity": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "default": 0.5,
                                },
                            },
                        },
                    ],
                },
                "SpinRequest": {
                    "allOf": [
                        _schema_ref("TextRequest"),
                        {
                            "type": "object",
                            "properties": {
                                "intensity": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "default": 0.5,
                                },
                                "seed": {"type": ["integer", "null"]},
                                "count": {"type": "integer", "minimum": 1},
                            },
                        },
                    ],
                },
                "HumanizeResponse": {
                    "type": "object",
                    "required": ["text", "lang", "profile", "change_ratio", "changes_count"],
                    "properties": {
                        "text": {"type": "string"},
                        "lang": {"type": "string"},
                        "profile": {"type": "string"},
                        "change_ratio": {"type": "number"},
                        "changes_count": {"type": "integer"},
                        "_elapsed_ms": {"type": "number"},
                    },
                },
                "AnalyzeResponse": {
                    "type": "object",
                    "properties": {
                        "lang": {"type": "string"},
                        "total_words": {"type": "integer"},
                        "total_sentences": {"type": "integer"},
                        "avg_sentence_length": {"type": "number"},
                        "burstiness_score": {"type": "number"},
                        "artificiality_score": {"type": "number"},
                        "flesch_kincaid_grade": {"type": "number"},
                        "coleman_liau_index": {"type": "number"},
                        "_elapsed_ms": {"type": "number"},
                    },
                },
                "TextResponse": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string"},
                        "_elapsed_ms": {"type": "number"},
                    },
                },
                "VariantsResponse": {
                    "type": "object",
                    "required": ["variants", "count"],
                    "properties": {
                        "variants": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "count": {"type": "integer"},
                        "_elapsed_ms": {"type": "number"},
                    },
                },
                "HealthResponse": {
                    "type": "object",
                    "required": ["status", "version", "endpoints"],
                    "properties": {
                        "status": {"type": "string", "const": "ok"},
                        "version": {"type": "string"},
                        "endpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "openapi": {"type": "string"},
                    },
                },
                "ApiIndexResponse": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "docs": {"type": "string"},
                        "endpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "openapi": {"type": "string"},
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {"type": "string"},
                        "type": {"type": "string"},
                    },
                },
                "GenericObject": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        },
    }

# ─── Request Handler ─────────────────────────────────────────

class TextHumanizeHandler(BaseHTTPRequestHandler):
    """HTTP handler для TextHumanize API."""

    server_version = f"TextHumanize/{__version__}"

    def log_message(self, fmt: str, *args: Any) -> None:
        """Compact logging."""
        pass  # Тихий режим; переопределить для логирования

    def do_OPTIONS(self) -> None:
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self) -> None:
        """GET endpoints."""
        if self.path == "/health":
            _json_response(self, {
                "status": "ok",
                "version": __version__,
                "endpoints": PUBLIC_ENDPOINTS,
                "openapi": OPENAPI_JSON_PATH,
            })
        elif self.path == "/":
            _json_response(self, {
                "name": "TextHumanize API",
                "version": __version__,
                "docs": "POST JSON to any endpoint with {'text': '...'} body",
                "endpoints": PUBLIC_ENDPOINTS,
                "openapi": OPENAPI_JSON_PATH,
            })
        elif self.path == OPENAPI_JSON_PATH:
            _json_response(self, get_openapi_schema())
        else:
            _json_response(self, {"error": "Not Found"}, status=404)

    def do_POST(self) -> None:
        """POST endpoints."""
        # Rate limiting
        client_ip = self.client_address[0] if self.client_address else "unknown"
        if not _rate_limiter.allow(client_ip):
            _json_response(self, {"error": "Rate limit exceeded. Try again later."}, status=429)
            return

        path = self.path.rstrip("/")

        # SSE streaming endpoint
        if path == "/sse/humanize":
            self._handle_sse_humanize()
            return

        handler_fn = ROUTES.get(path)
        if handler_fn is None:
            _json_response(self, {"error": f"Unknown endpoint: {path}"}, status=404)
            return

        t0 = time.monotonic()
        try:
            data = _read_json(self)
            result = handler_fn(data)
            elapsed = time.monotonic() - t0
            result["_elapsed_ms"] = round(elapsed * 1000, 1)
            _json_response(self, result)
        except RemoteBackendDisabled as exc:
            _json_response(
                self,
                {"error": str(exc), "type": "RemoteBackendDisabled"},
                status=403,
            )
        except UnsafeURLError as exc:
            _json_response(
                self,
                {"error": str(exc), "type": "UnsafeURLError"},
                status=400,
            )
        except ValueError as exc:
            _json_response(self, {"error": str(exc)}, status=400)
        except Exception as exc:
            logger.exception("Unhandled error in %s", path)
            _json_response(self, {
                "error": "Internal server error",
                "type": type(exc).__name__,
            }, status=500)

    def _handle_sse_humanize(self) -> None:
        """Server-Sent Events streaming for humanize."""
        try:
            data = _read_json(self)
        except ValueError as exc:
            _json_response(
                self, {"error": str(exc)}, status=400,
            )
            return

        text = data.get("text", "")
        lang = data.get("lang", "auto")
        profile = data.get("profile", "web")
        intensity = data.get("intensity", 60)
        seed = data.get("seed")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", _cors_origin())
        self.end_headers()

        try:
            from texthumanize.core import humanize_stream
            idx = 0
            time.monotonic()
            for chunk in humanize_stream(
                text, lang=lang, profile=profile,
                intensity=intensity, seed=seed,
            ):
                event_data = json.dumps(
                    {"chunk": chunk, "index": idx},
                    ensure_ascii=False,
                )
                self.wfile.write(
                    f"id: {idx}\nevent: chunk\ndata: {event_data}\n\n".encode(),
                )
                self.wfile.flush()
                idx += 1
                time.monotonic()

            done = json.dumps(
                {"done": True, "total_chunks": idx},
            )
            self.wfile.write(
                f"id: {idx}\nevent: done\ndata: {done}\n\n".encode(),
            )
            self.wfile.flush()
        except Exception:
            logger.exception("SSE streaming error")
            err = json.dumps(
                {"error": "Internal server error"}, ensure_ascii=False,
            )
            self.wfile.write(
                f"event: error\ndata: {err}\n\n".encode(),
            )
            self.wfile.flush()

# ─── Server factory ──────────────────────────────────────────

def create_app(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    """Создать HTTP-сервер.

    Uses :class:`~http.server.ThreadingHTTPServer` so concurrent clients
    (and the SSE streaming endpoint) don't block each other.

    Binds to loopback (``127.0.0.1``) by default so the unauthenticated
    API is not exposed to the network unintentionally. Pass
    ``host="0.0.0.0"`` explicitly to expose it (and put it behind auth /
    a reverse proxy when you do).

    This stdlib server is intended for local use, development, and
    self-hosted single-tenant deployment. For internet-facing production
    traffic, run it behind a reverse proxy (TLS, auth, timeouts) or wrap
    the pure functions in an ASGI/WSGI app.
    """
    return ThreadingHTTPServer((host, port), TextHumanizeHandler)

def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Запустить HTTP-сервер."""
    server = create_app(host, port)
    print(f"TextHumanize API v{__version__} running on http://{host}:{port}")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "  ⚠ Bound to a non-loopback address: this API is "
            "UNAUTHENTICATED. Restrict access or place it behind a proxy."
        )
    print(f"Endpoints: {', '.join(sorted(ROUTES.keys()))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

# ─── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TextHumanize API Server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default 127.0.0.1; use 0.0.0.0 to expose on all "
        "interfaces — the API is unauthenticated, so secure it first)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
