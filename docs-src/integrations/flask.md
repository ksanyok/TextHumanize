# Flask Integration

Blueprint-based integration with caching support.

## Installation

```bash
pip install texthumanize flask
```

## Complete Example

```python
"""TextHumanize + Flask — blueprint with caching."""
from flask import Flask, Blueprint, request, jsonify
from texthumanize import humanize, detect_ai, analyze

# --- Blueprint ---
th_bp = Blueprint("texthumanize", __name__, url_prefix="/api/v1")

# Simple in-memory cache (use Redis in production)
_cache: dict[str, dict] = {}


def _cache_key(text: str, lang: str, profile: str, intensity: int) -> str:
    import hashlib
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

    # Check cache
    key = _cache_key(text, lang, profile, intensity)
    if seed is None and key in _cache:
        return jsonify(_cache[key])

    try:
        result = humanize(
            text, lang=lang, profile=profile,
            intensity=intensity, seed=seed,
        )
        response = {
            "text": result.text,
            "change_ratio": result.change_ratio,
            "quality_score": getattr(result, "quality_score", 0),
            "lang": result.lang,
        }
        if seed is None:
            _cache[key] = response
        return jsonify(response)
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
```

## Run

```bash
python app.py
# or
flask --app app:create_app run --port 5000
```

## With Redis Cache (Production)

```python
import redis
import json

r = redis.Redis(host="localhost", port=6379, db=0)

@th_bp.route("/humanize", methods=["POST"])
def humanize_cached():
    data = request.get_json(force=True)
    key = f"th:{_cache_key(data['text'], data.get('lang', 'auto'), data.get('profile', 'web'), data.get('intensity', 60))}"

    cached = r.get(key)
    if cached:
        return jsonify(json.loads(cached))

    result = humanize(data["text"], lang=data.get("lang", "auto"))
    response = {"text": result.text, "change_ratio": result.change_ratio}
    r.setex(key, 3600, json.dumps(response))  # Cache 1 hour
    return jsonify(response)
```
