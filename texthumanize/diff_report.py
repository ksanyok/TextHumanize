"""Отчёт об изменениях в нескольких форматах: text, HTML, JSON-patch.

Использование::

    from texthumanize import humanize, explain
    from texthumanize.diff_report import explain_html, explain_json_patch

    result = humanize("Некий текст для обработки.", lang="ru")
    print(explain_html(result))        # HTML с красными/зелёными блоками
    print(explain_json_patch(result))  # RFC 6902 JSON Patch
"""

from __future__ import annotations

import difflib
import html as html_mod
import json
import re
from typing import Any

from texthumanize.utils import HumanizeResult

# ═══════════════════════════════════════════════════════════════
#  HTML DIFF (inline, side-by-side)
# ═══════════════════════════════════════════════════════════════

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TextHumanize — Change Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 900px; margin: 2em auto; padding: 0 1em;
       color: #24292f; background: #fff; }}
h1 {{ font-size: 1.3em; border-bottom: 1px solid #d0d7de; padding-bottom: .4em; }}
.meta {{ color: #656d76; font-size: .85em; margin-bottom: 1em; }}
.diff {{ font-family: 'SFMono-Regular', Consolas, 'Courier New', monospace;
         font-size: .9em; line-height: 1.6; white-space: pre-wrap;
         word-wrap: break-word; background: #f6f8fa; padding: 1em;
         border-radius: 6px; border: 1px solid #d0d7de; }}
del {{ background: #ffd7d5; text-decoration: line-through; color: #82071e; }}
ins {{ background: #ccffd8; text-decoration: none; color: #116329; }}
.metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: .8em;
            margin: 1em 0; font-size: .9em; }}
.metric {{ background: #f6f8fa; padding: .6em; border-radius: 4px; }}
.metric .label {{ color: #656d76; }}
.metric .value {{ font-weight: 600; }}
.arrow-down {{ color: #1a7f37; }}
.arrow-up {{ color: #cf222e; }}
.changes {{ margin-top: 1.2em; }}
.change-item {{ padding: .3em 0; border-bottom: 1px solid #eee; }}
.change-type {{ display: inline-block; background: #ddf4ff; color: #0969da;
                border-radius: 3px; padding: 0 .4em; font-size: .8em;
                font-weight: 500; margin-right: .4em; }}
</style>
</head>
<body>
<h1>TextHumanize — Change Report</h1>
<div class="meta">{meta}</div>
<div class="metrics">{metrics}</div>
<h2>Inline Diff</h2>
<div class="diff">{diff}</div>
{changes_section}
</body>
</html>"""


def explain_html(
    result: HumanizeResult,
    *,
    title: str = "TextHumanize — Change Report",
    show_changes: bool = True,
) -> str:
    """Render an HTML change report with inline diff.

    Args:
        result: A ``HumanizeResult`` from ``humanize()``.
        title: Page title.
        show_changes: Include the per-change breakdown table.

    Returns:
        A self-contained HTML string.
    """
    esc = html_mod.escape

    # Meta line
    meta = (
        f"Language: <b>{esc(result.lang)}</b> &middot; "
        f"Profile: <b>{esc(result.profile)}</b> &middot; "
        f"Intensity: <b>{result.intensity}</b> &middot; "
        f"Change ratio: <b>{result.change_ratio:.1%}</b>"
    )

    # Metrics grid
    metrics_html = ""
    if result.metrics_before and result.metrics_after:
        items: list[tuple[str, str, float, float]] = [
            ("Artificiality", "", _g(result.metrics_before, "artificiality_score"),
             _g(result.metrics_after, "artificiality_score")),
            ("Avg sentence len", " words", _g(result.metrics_before, "avg_sentence_length"),
             _g(result.metrics_after, "avg_sentence_length")),
            ("Bureaucratic ratio", "", _g(result.metrics_before, "bureaucratic_ratio"),
             _g(result.metrics_after, "bureaucratic_ratio")),
            ("Connector ratio", "", _g(result.metrics_before, "connector_ratio"),
             _g(result.metrics_after, "connector_ratio")),
            ("Repetition", "", _g(result.metrics_before, "repetition_score"),
             _g(result.metrics_after, "repetition_score")),
            ("Typography", "", _g(result.metrics_before, "typography_score"),
             _g(result.metrics_after, "typography_score")),
        ]
        parts = []
        for label, unit, before, after in items:
            arrow_cls = (
                "arrow-down" if after < before else
                "arrow-up" if after > before else ""
            )
            arrow = "↓" if after < before else "↑" if after > before else "="
            parts.append(
                f'<div class="metric">'
                f'<span class="label">{esc(label)}</span><br>'
                f'<span class="value">{before:.2f}{unit} → '
                f'{after:.2f}{unit} '
                f'<span class="{arrow_cls}">{arrow}</span>'
                f'</span></div>'
            )
        metrics_html = "\n".join(parts)

    # Inline diff (word-level)
    diff_html = _word_diff_html(result.original, result.text)

    # Changes list
    changes_section = ""
    if show_changes and result.changes:
        items_html = []
        for ch in result.changes[:50]:
            ctype = ch.get("type", "unknown")
            if "original" in ch and "replacement" in ch:
                desc = (
                    f'<del>{esc(str(ch["original"]))}</del> → '
                    f'<ins>{esc(str(ch["replacement"]))}</ins>'
                )
            elif "description" in ch:
                desc = esc(str(ch["description"]))
            else:
                desc = esc(str(ch))
            items_html.append(
                f'<div class="change-item">'
                f'<span class="change-type">{esc(ctype)}</span> '
                f'{desc}</div>'
            )
        if len(result.changes) > 50:
            items_html.append(
                f'<div class="change-item" style="color: #656d76">'
                f'… and {len(result.changes) - 50} more changes</div>'
            )
        changes_section = (
            '<div class="changes">'
            f'<h2>Changes ({len(result.changes)})</h2>'
            + "\n".join(items_html) + '</div>'
        )

    return _HTML_TEMPLATE.format(
        meta=meta,
        metrics=metrics_html,
        diff=diff_html,
        changes_section=changes_section,
    )


# ═══════════════════════════════════════════════════════════════
#  JSON PATCH (RFC 6902-like)
# ═══════════════════════════════════════════════════════════════

def explain_json_patch(result: HumanizeResult) -> str:
    """Generate a JSON-patch-style change report.

    Each change is an operation with ``op``, ``path``, ``value``,
    and optional ``old`` fields, following the spirit of RFC 6902.

    Returns:
        JSON string (indented).
    """
    ops: list[dict[str, Any]] = []

    for i, ch in enumerate(result.changes):
        op: dict[str, Any] = {
            "op": "replace",
            "path": f"/text/change/{i}",
            "type": ch.get("type", "unknown"),
        }
        if "original" in ch and "replacement" in ch:
            op["old"] = ch["original"]
            op["value"] = ch["replacement"]
        elif "description" in ch:
            op["op"] = "info"
            op["value"] = ch["description"]
        ops.append(op)

    envelope: dict[str, Any] = {
        "version": "1.0",
        "lang": result.lang,
        "profile": result.profile,
        "intensity": result.intensity,
        "change_ratio": round(result.change_ratio, 4),
        "metrics_before": result.metrics_before,
        "metrics_after": result.metrics_after,
        "operations": ops,
    }
    return json.dumps(envelope, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════
#  SIDE-BY-SIDE TEXT DIFF
# ═══════════════════════════════════════════════════════════════

def explain_side_by_side(
    result: HumanizeResult,
    width: int = 80,
) -> str:
    """Render a side-by-side diff of original vs processed text.

    Args:
        result: A ``HumanizeResult`` from ``humanize()``.
        width: Column width for each side.

    Returns:
        Text string with side-by-side columns.
    """
    orig_lines = result.original.splitlines()
    new_lines = result.text.splitlines()

    differ = difflib.unified_diff(
        orig_lines, new_lines,
        fromfile="Original", tofile="Processed",
        lineterm="",
    )
    return "\n".join(differ)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _g(d: dict | None, key: str, default: float = 0.0) -> float:
    """Safely get a float from a dict (metrics_before/after)."""
    if not d:
        return default
    return float(d.get(key, default))


def _word_diff_html(original: str, modified: str) -> str:
    """Produce an inline word-level diff with <del>/<ins> tags."""
    esc = html_mod.escape

    orig_words = re.findall(r'\S+|\s+', original)
    mod_words = re.findall(r'\S+|\s+', modified)

    sm = difflib.SequenceMatcher(None, orig_words, mod_words)
    parts: list[str] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(esc("".join(orig_words[i1:i2])))
        elif tag == "delete":
            parts.append(f'<del>{esc("".join(orig_words[i1:i2]))}</del>')
        elif tag == "insert":
            parts.append(f'<ins>{esc("".join(mod_words[j1:j2]))}</ins>')
        elif tag == "replace":
            parts.append(f'<del>{esc("".join(orig_words[i1:i2]))}</del>')
            parts.append(f'<ins>{esc("".join(mod_words[j1:j2]))}</ins>')

    return "".join(parts)
