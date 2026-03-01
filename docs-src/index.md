# TextHumanize

**The most advanced open-source text naturalization engine**

Normalize style, improve readability, and ensure brand-safe content — offline, private, and blazing fast.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| **Lines of Code** | 56,800+ Python |
| **Pipeline Stages** | 17 |
| **Languages** | 14 + universal |
| **Tests** | 1,995+ passing |
| **Dependencies** | Zero |
| **Platforms** | Python · JS/TS · PHP |

## Why TextHumanize?

!!! success "Core Advantages"
    - **~3,000 chars/sec** — process a full article in milliseconds
    - **100% private** — all processing is local, your text never leaves your machine
    - **Precise control** — intensity 0–100, 9 profiles, keyword preservation
    - **14 languages** — full dictionaries + universal processor for any language
    - **Zero dependencies** — pure Python stdlib, starts in <100ms
    - **Reproducible** — seed-based PRNG, same input + seed = identical output
    - **AI detection** — 13-metric ensemble + 35-feature statistical detector

## Quick Example

```python
from texthumanize import humanize, detect_ai

# Humanize text
result = humanize(
    "Furthermore, it is important to note that the implementation "
    "of this approach facilitates optimization.",
    lang="en",
    profile="web",
    intensity=70,
)
print(result.text)
# → "But this approach helps with optimization."

# Detect AI-generated text
ai = detect_ai("Text to check.", lang="en")
print(f"AI: {ai['score']:.0%} — {ai['verdict']}")
```

## 🎮 Live Demo

Try TextHumanize online: **[humanizekit.tester-buyreadysite.website](https://humanizekit.tester-buyreadysite.website/)**

## Getting Started

<div class="grid cards" markdown>

- :material-download: **[Installation](getting-started/installation.md)**

    pip install, from source, Docker, PHP, TypeScript

- :material-rocket-launch: **[Quick Start](getting-started/quickstart.md)**

    First steps with humanize(), detect_ai(), and more

- :material-cog: **[Profiles](getting-started/profiles.md)**

    9 built-in profiles for different content types

</div>

## Integrations

TextHumanize works with all popular Python web frameworks:

- [FastAPI](integrations/fastapi.md) — async endpoints with dependency injection
- [Flask](integrations/flask.md) — blueprint with caching
- [Django](integrations/django.md) — middleware + template filters
- [WordPress](integrations/wordpress.md) — PHP plugin for WP content
