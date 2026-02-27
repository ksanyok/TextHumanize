"""TextHumanize + Django — views, middleware, template filter.

Install:
    pip install texthumanize django

Usage:
    1. Add views to urls.py
    2. Use TextHumanizeMiddleware for auto-humanize (opt-in via header)
    3. Use template filter: {{ text|humanize_text:"en" }}

See docs/integrations/django.md for full setup guide.
"""

from __future__ import annotations

import json

from texthumanize import analyze, detect_ai, humanize

# ── Views ────────────────────────────────────────────────────


def humanize_view(request):
    """POST /api/humanize/ — humanize text."""
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        result = humanize(
            data["text"],
            lang=data.get("lang", "en"),
            profile=data.get("profile", "web"),
            intensity=data.get("intensity", 60),
        )
        return JsonResponse({
            "text": result.text,
            "change_ratio": result.change_ratio,
            "quality_score": getattr(result, "quality_score", 0),
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def detect_ai_view(request):
    """POST /api/detect-ai/ — AI detection."""
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        result = detect_ai(data["text"], lang=data.get("lang", "en"))
        return JsonResponse({
            "score": result["score"],
            "verdict": result["verdict"],
            "confidence": result["confidence"],
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def analyze_view(request):
    """POST /api/analyze/ — text analysis."""
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        report = analyze(data["text"], lang=data.get("lang", "en"))
        return JsonResponse({
            "artificiality_score": report.artificiality_score,
            "word_count": report.word_count,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ── Middleware ────────────────────────────────────────────────


class TextHumanizeMiddleware:
    """Auto-humanize JSON responses (opt-in via X-Humanize header)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.headers.get("X-Humanize") != "true":
            return response

        content_type = response.get("Content-Type", "")
        if (
            content_type.startswith("application/json")
            and hasattr(response, "content")
        ):
            try:
                data = json.loads(response.content)
                if "text" in data:
                    result = humanize(
                        data["text"], lang="en", profile="web",
                    )
                    data["text"] = result.text
                    data["_humanized"] = True
                    response.content = json.dumps(data).encode()
            except (json.JSONDecodeError, Exception):
                pass

        return response


# ── Template filter ──────────────────────────────────────────
# Register in your app's templatetags/__init__.py:
#
#   from django import template
#   register = template.Library()
#
#   @register.filter(name="humanize_text")
#   def humanize_text(value, lang="en"):
#       from texthumanize import humanize
#       if not value:
#           return value
#       result = humanize(str(value), lang=lang, intensity=50)
#       return result.text
