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

Запуск:
    python -m texthumanize.api --port 8080
    # или
    from texthumanize.api import create_app, run_server
    run_server(port=8080)
"""

from __future__ import annotations

import json
import logging
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from texthumanize import __version__
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

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────

def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200) -> None:
    """Отправить JSON-ответ."""
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)

MAX_REQUEST_BODY = 5_000_000  # 5 MB

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
    result = humanize(
        text,
        lang=data.get("lang", "auto"),
        profile=data.get("profile", "web"),
        intensity=data.get("intensity", 60),
        seed=data.get("seed"),
    )
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
        return detect_ai(text, lang=data.get("lang", "auto"))
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
        self.send_header("Access-Control-Allow-Origin", "*")
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
                "endpoints": sorted(ROUTES.keys()),
            })
        elif self.path == "/":
            _json_response(self, {
                "name": "TextHumanize API",
                "version": __version__,
                "docs": "POST JSON to any endpoint with {'text': '...'} body",
                "endpoints": sorted(ROUTES.keys()),
            })
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
        self.send_header("Access-Control-Allow-Origin", "*")
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

def create_app(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer:
    """Создать HTTP-сервер."""
    return HTTPServer((host, port), TextHumanizeHandler)

def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Запустить HTTP-сервер."""
    server = create_app(host, port)
    print(f"TextHumanize API v{__version__} running on http://{host}:{port}")
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
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
