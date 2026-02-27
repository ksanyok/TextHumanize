"""TextHumanize + Flask — blueprint with simple caching.

Install:
    pip install texthumanize flask

Run:
    python examples/flask_integration.py
    # or
    flask --app examples.flask_integration:create_app run --port 5000
"""

from __future__ import annotations

import hashlib

from flask import Blueprint, Flask, jsonify, request

from texthumanize import analyze, detect_ai, humanize

# --- Blueprint ---
th_bp = Blueprint("texthumanize", __name__, url_prefix="/api/v1")

# Simple in-memory cache (use Redis in production)
_cache: dict[str, dict] = {}


def _cache_key(text: str, lang: str, profile: str, intensity: int) -> str:
    data = f"{text}:{lang}:{profile}:{intensity}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


@th_bp.route("/humanize", methods=["POST"])
def humanize_endpoint():
    """Humanize text."""
    data = request.get_json(force=True)
    text = data.get("text", "")
    lang = data.get("lang", "auto")
    profile = data.get("profile", "web")
    intensity = data.get("intensity", 60)
    seed = data.get("seed")

    if not text:
        return jsonify({"error": "text is required"}), 400

    key = _cache_key(text, lang, profile, intensity)
    if seed is None and key in _cache:
        return jsonify(_cache[key])

    try:
        result = humanize(
            text, lang=lang, profile=profile,
            intensity=intensity, seed=seed,
        )
        resp = {
            "text": result.text,
            "change_ratio": result.change_ratio,
            "quality_score": getattr(result, "quality_score", 0),
            "lang": result.lang,
        }
        if seed is None:
            _cache[key] = resp
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@th_bp.route("/detect-ai", methods=["POST"])
def detect_ai_endpoint():
    """AI detection."""
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400

    try:
        result = detect_ai(text, lang=data.get("lang", "auto"))
        return jsonify({
            "score": result["score"],
            "verdict": result["verdict"],
            "confidence": result["confidence"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@th_bp.route("/analyze", methods=["POST"])
def analyze_endpoint():
    """Text analysis."""
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400

    report = analyze(text, lang=data.get("lang", "auto"))
    return jsonify({
        "artificiality_score": report.artificiality_score,
        "word_count": report.word_count,
    })


# --- App factory ---
def create_app():
    app = Flask(__name__)
    app.register_blueprint(th_bp)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
