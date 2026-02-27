# Django Integration

Middleware, template filters, and management commands.

## Installation

```bash
pip install texthumanize django
```

## Setup

Add to your Django project:

### settings.py

```python
INSTALLED_APPS = [
    # ...
    "texthumanize_django",
]

MIDDLEWARE = [
    # ...
    "texthumanize_django.middleware.TextHumanizeMiddleware",
]

# TextHumanize settings
TEXTHUMANIZE = {
    "lang": "en",
    "profile": "web",
    "intensity": 60,
    "cache_backend": "default",  # Django cache backend
    "cache_timeout": 3600,
}
```

## Middleware Example

```python
"""texthumanize_django/middleware.py"""
from django.conf import settings
from texthumanize import humanize


class TextHumanizeMiddleware:
    """Auto-humanize text responses (opt-in via header)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, "TEXTHUMANIZE", {})

    def __call__(self, request):
        response = self.get_response(request)

        # Only process if explicitly requested
        if request.headers.get("X-Humanize") != "true":
            return response

        if (
            response.get("Content-Type", "").startswith("application/json")
            and hasattr(response, "content")
        ):
            import json
            try:
                data = json.loads(response.content)
                if "text" in data:
                    result = humanize(
                        data["text"],
                        lang=self.config.get("lang", "en"),
                        profile=self.config.get("profile", "web"),
                        intensity=self.config.get("intensity", 60),
                    )
                    data["text"] = result.text
                    data["_humanized"] = True
                    response.content = json.dumps(data).encode()
            except (json.JSONDecodeError, Exception):
                pass

        return response
```

## Template Filter

```python
"""texthumanize_django/templatetags/humanize_text.py"""
from django import template
from texthumanize import humanize as th_humanize

register = template.Library()


@register.filter(name="humanize_text")
def humanize_text(value, lang="en"):
    """Template filter: {{ text|humanize_text:"en" }}"""
    if not value:
        return value
    try:
        result = th_humanize(str(value), lang=lang, profile="web", intensity=50)
        return result.text
    except Exception:
        return value


@register.filter(name="detect_ai_score")
def detect_ai_score(value, lang="en"):
    """Template filter: {{ text|detect_ai_score:"en" }}"""
    from texthumanize import detect_ai
    if not value:
        return 0.0
    try:
        result = detect_ai(str(value), lang=lang)
        return round(result["score"], 2)
    except Exception:
        return 0.0
```

### Usage in Templates

```html
{% load humanize_text %}

<p>{{ article.body|humanize_text:"en" }}</p>
<p>AI Score: {{ article.body|detect_ai_score:"en" }}</p>
```

## Views

```python
"""texthumanize_django/views.py"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from texthumanize import humanize, detect_ai
import json


@csrf_exempt
@require_POST
def humanize_view(request):
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
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_POST
def detect_ai_view(request):
    try:
        data = json.loads(request.body)
        result = detect_ai(data["text"], lang=data.get("lang", "en"))
        return JsonResponse({
            "score": result["score"],
            "verdict": result["verdict"],
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
```

### urls.py

```python
from django.urls import path
from texthumanize_django.views import humanize_view, detect_ai_view

urlpatterns = [
    path("api/humanize/", humanize_view, name="humanize"),
    path("api/detect-ai/", detect_ai_view, name="detect-ai"),
]
```

## Management Command

```python
"""texthumanize_django/management/commands/humanize_content.py"""
from django.core.management.base import BaseCommand
from texthumanize import humanize


class Command(BaseCommand):
    help = "Humanize text from database fields"

    def add_arguments(self, parser):
        parser.add_argument("--model", required=True)
        parser.add_argument("--field", required=True)
        parser.add_argument("--lang", default="en")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        from django.apps import apps
        Model = apps.get_model(options["model"])
        field = options["field"]
        count = 0

        for obj in Model.objects.all():
            text = getattr(obj, field, "")
            if not text:
                continue
            result = humanize(text, lang=options["lang"])
            if not options["dry_run"]:
                setattr(obj, field, result.text)
                obj.save(update_fields=[field])
            count += 1
            self.stdout.write(f"  {obj.pk}: ratio={result.change_ratio:.2f}")

        self.stdout.write(self.style.SUCCESS(f"Processed {count} objects"))
```

```bash
python manage.py humanize_content --model=blog.Article --field=body --lang=en
python manage.py humanize_content --model=blog.Article --field=body --dry-run
```
