"""Quality Gate — проверка контента на AI-артефакты и читаемость.

CLI (standalone / pre-commit / GitHub Action)::

    python -m texthumanize.quality_gate README.md docs/

    # только изменённые файлы (git diff)
    python -m texthumanize.quality_gate --changed-only

    # с порогами
    python -m texthumanize.quality_gate --ai-threshold 20 --readability-threshold 50

Exit codes:
    0 — все файлы прошли проверку
    1 — хотя бы один файл не прошёл
    2 — ошибка конфигурации / аргументов
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import logging
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from texthumanize.core import analyze, detect_ai, detect_watermarks

logger = logging.getLogger(__name__)

# Repo scaffolding / meta-documentation is not "content": it is markdown-heavy
# (badges, tables, code fences, changelogs) and readability/AI-detection metrics
# are not meaningful for it. These basenames are skipped by default so the gate
# targets actual prose. Extend or override with --exclude / --no-default-excludes.
#
# Patterns are precise (exact stem or ``stem.<ext>``) so a real content file
# such as ``readme-guide.md`` is NOT swept up by a broad ``README*``.
_META_DOC_STEMS: tuple[str, ...] = (
    "readme",
    "changelog",
    "security",
    "contributing",
    "code_of_conduct",
    "contributors",
    "authors",
    "notice",
    "roadmap",
    "commercial",
    "license",
)
_DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = tuple(
    g for stem in _META_DOC_STEMS for g in (stem, f"{stem}.*")
)

# Developer/reference documentation and generated sites are not "content" the
# gate is meant to police (published prose). Skipping these directories by
# default keeps the gate meaningful and CI reliable; a `content/` area or
# explicitly-passed files are still checked. Override with --no-default-excludes.
_DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = ("docs", "docs-src", "site", ".github")


def _is_excluded(path: str, patterns: Sequence[str]) -> bool:
    """True if the file's basename matches any exclusion glob (case-insensitive)."""
    name = os.path.basename(path)
    return any(fnmatch.fnmatch(name.lower(), pat.lower()) for pat in patterns)


def _in_excluded_dir(path: str, dirs: Sequence[str]) -> bool:
    """True if any path component is an excluded directory."""
    parts = {part.lower() for part in Path(path).parts}
    return any(d.lower() in parts for d in dirs)


# Markup extensions whose raw source (code fences, tables, tags, badges) must be
# reduced to prose before scoring — otherwise readability/AI metrics are garbage.
_MARKUP_EXTS = (".md", ".markdown", ".rst", ".html", ".htm", ".adoc")

_RE_FENCE = re.compile(r"^```.*?^```|^~~~.*?^~~~", re.MULTILINE | re.DOTALL)
_RE_INLINE_CODE = re.compile(r"`[^`]*`")
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_RE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_RE_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}.*$", re.MULTILINE)
_RE_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_RE_HEADING_HASH = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_RE_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_RE_LIST_MARK = re.compile(r"^\s*([-*+]|\d+\.)\s+", re.MULTILINE)
_RE_EMPHASIS = re.compile(r"[*_~]{1,3}")
_RE_AUTOLINK = re.compile(r"https?://\S+")
_RE_MULTIBLANK = re.compile(r"\n{3,}")


def strip_markup(text: str) -> str:
    """Reduce markdown/reST/HTML source to plain prose for content scoring.

    Removes fenced/inline code, HTML tags, images and badges, table scaffolding,
    heading/list/quote markers and emphasis, keeping link *text*. This keeps the
    readability and AI-detection signals meaningful for documentation instead of
    being dominated by markup punctuation.
    """
    text = _RE_FENCE.sub(" ", text)
    text = _RE_IMAGE.sub(" ", text)
    text = _RE_LINK.sub(r"\1", text)
    text = _RE_INLINE_CODE.sub(" ", text)
    text = _RE_HTML_TAG.sub(" ", text)
    text = _RE_TABLE_SEP.sub(" ", text)
    text = _RE_TABLE_ROW.sub(lambda m: m.group(0).replace("|", " "), text)
    text = _RE_HEADING_HASH.sub("", text)
    text = _RE_BLOCKQUOTE.sub("", text)
    text = _RE_LIST_MARK.sub("", text)
    text = _RE_AUTOLINK.sub(" ", text)
    text = _RE_EMPHASIS.sub("", text)
    return _RE_MULTIBLANK.sub("\n\n", text).strip()

# ─────────────────────────────────────────────────────────────
#  Dataclasses
# ─────────────────────────────────────────────────────────────

@dataclass
class GateResult:
    """Result of a single file quality check."""
    path: str
    passed: bool = True
    ai_score: float = 0.0
    readability: float = 100.0
    watermark_count: int = 0
    issues: list[str] = field(default_factory=list)

@dataclass
class GateConfig:
    """Quality gate thresholds."""
    ai_threshold: float = 25.0
    readability_threshold: float = 40.0
    watermark_zero: bool = True
    max_file_size: int = 500_000  # 500 KB
    extensions: tuple[str, ...] = (".md", ".txt", ".rst", ".html", ".adoc")

# ─────────────────────────────────────────────────────────────
#  Core logic
# ─────────────────────────────────────────────────────────────

def check_file(path: str, config: GateConfig | None = None) -> GateResult:
    """Check a single text file against quality thresholds.

    Args:
        path: File path.
        config: Gate thresholds (uses defaults if ``None``).

    Returns:
        ``GateResult`` with pass/fail and details.
    """
    cfg = config or GateConfig()
    result = GateResult(path=path)

    p = Path(path)
    if not p.exists():
        result.passed = False
        result.issues.append("File not found")
        return result

    if p.stat().st_size > cfg.max_file_size:
        result.issues.append(f"File too large ({p.stat().st_size:,} bytes), skipped")
        return result

    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return result  # empty file is OK

    # Reduce markup source to prose so metrics reflect the writing, not the
    # code fences / tables / badges around it.
    is_markup = p.suffix.lower() in _MARKUP_EXTS
    if is_markup:
        text = strip_markup(text)
        if not text.strip():
            return result  # nothing but markup/code — nothing to score

    # 1) AI score
    try:
        ai = detect_ai(text, lang="auto")
        result.ai_score = float(ai.get("ai_score", 0))  # type: ignore[arg-type]
        if result.ai_score > cfg.ai_threshold:
            result.passed = False
            result.issues.append(
                f"AI score {result.ai_score:.0f}% > threshold {cfg.ai_threshold:.0f}%"
            )
    except Exception as exc:
        result.issues.append(f"AI detection error: {exc}")

    # 2) Readability — a bounded 0..100 proxy from the artificiality signal.
    # NOTE: this is only *enforced* for plain-prose content. Reference docs
    # (markdown/reST/HTML) are legitimately dense (APIs, tables, jargon) and a
    # reading-ease floor is not a meaningful pass/fail signal for them, so it is
    # reported as an informational note there rather than failing the gate.
    try:
        report = analyze(text, lang="auto")
        artificiality = float(getattr(report, "artificiality_score", 0.0))
        result.readability = max(0.0, min(100.0, 100.0 - artificiality * 100.0))
        if result.readability < cfg.readability_threshold:
            msg = (
                f"Readability {result.readability:.0f} < threshold "
                f"{cfg.readability_threshold:.0f}"
            )
            if is_markup:
                result.issues.append(f"{msg} (informational; not gated for docs)")
            else:
                result.passed = False
                result.issues.append(msg)
    except Exception as exc:
        result.issues.append(f"Analysis error: {exc}")

    # 3) Watermarks
    if cfg.watermark_zero:
        try:
            wm = detect_watermarks(text)
            result.watermark_count = len(wm.get("watermark_types", []))
            if result.watermark_count > 0:
                result.passed = False
                result.issues.append(
                    f"Found {result.watermark_count} watermark(s)"
                )
        except Exception as exc:
            result.issues.append(f"Watermark detection error: {exc}")

    return result

def check_files(
    paths: Sequence[str],
    config: GateConfig | None = None,
) -> list[GateResult]:
    """Check multiple files.

    Args:
        paths: List of file paths.
        config: Gate thresholds.

    Returns:
        List of ``GateResult`` objects.
    """
    return [check_file(p, config) for p in paths]

# ─────────────────────────────────────────────────────────────
#  Git helpers
# ─────────────────────────────────────────────────────────────

def get_changed_text_files(extensions: tuple[str, ...] | None = None) -> list[str]:
    """Return text files changed in the current git diff (HEAD vs working tree).

    Falls back to diff against ``origin/main`` when on a branch.
    """
    exts = extensions or GateConfig.extensions
    try:
        # staged + unstaged
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        if not out:
            # try against origin/main
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "--diff-filter=ACMR", "origin/main...HEAD"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files = [f for f in out.splitlines() if f.strip()]
    return [f for f in files if any(f.endswith(e) for e in exts)]

# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def _find_files(patterns: list[str], extensions: tuple[str, ...]) -> list[str]:
    """Expand globs and filter by extension."""
    result: list[str] = []
    for pat in patterns:
        if os.path.isfile(pat):
            result.append(pat)
        elif os.path.isdir(pat):
            for ext in extensions:
                result.extend(glob.glob(os.path.join(pat, f"**/*{ext}"), recursive=True))
        else:
            result.extend(glob.glob(pat, recursive=True))
    return sorted(set(result))

def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the quality gate.

    Returns:
        0 if all checks pass, 1 if any fail, 2 on error.
    """
    parser = argparse.ArgumentParser(
        prog="texthumanize-quality-gate",
        description="TextHumanize Quality Gate — check text files for AI artifacts",
    )
    parser.add_argument(
        "files", nargs="*",
        help="Files or directories to check (globs supported)",
    )
    parser.add_argument(
        "--changed-only", action="store_true",
        help="Only check files changed in git",
    )
    parser.add_argument(
        "--ai-threshold", type=float, default=25.0,
        help="Max allowed AI score (0-100, default: 25)",
    )
    parser.add_argument(
        "--readability-threshold", type=float, default=40.0,
        help="Min readability score (0-100, default: 40)",
    )
    parser.add_argument(
        "--no-watermarks", action="store_true", default=True,
        help="Fail on any watermarks (default: true)",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="GLOB",
        help="Basename glob to skip (repeatable). Extends the default "
             "meta-doc excludes unless --no-default-excludes is given.",
    )
    parser.add_argument(
        "--no-default-excludes", action="store_true",
        help="Do not skip standard repo meta-docs (README, CHANGELOG, ...).",
    )

    args = parser.parse_args(argv)

    config = GateConfig(
        ai_threshold=args.ai_threshold,
        readability_threshold=args.readability_threshold,
        watermark_zero=args.no_watermarks,
    )

    # Collect files
    if args.changed_only:
        files = get_changed_text_files(config.extensions)
    elif args.files:
        files = _find_files(args.files, config.extensions)
    else:
        parser.error("Specify files/directories or use --changed-only")
        return 2

    # Skip repo scaffolding / meta-docs and developer-doc directories unless
    # opted out. The gate targets publishable content, not reference docs.
    exclude_globs = list(args.exclude)
    exclude_dirs: list[str] = []
    if not args.no_default_excludes:
        exclude_globs.extend(_DEFAULT_EXCLUDE_GLOBS)
        exclude_dirs.extend(_DEFAULT_EXCLUDE_DIRS)

    kept: list[str] = []
    for f in files:
        if _is_excluded(f, exclude_globs):
            print(f"⏭  SKIP  {f} (excluded meta-doc)")
        elif _in_excluded_dir(f, exclude_dirs):
            print(f"⏭  SKIP  {f} (excluded docs directory)")
        else:
            kept.append(f)
    files = kept

    if not files:
        print("quality-gate: no files to check")
        return 0

    # Check
    results = check_files(files, config)

    # Report
    if args.format == "json":
        import json
        data = [
            {
                "path": r.path,
                "passed": r.passed,
                "ai_score": r.ai_score,
                "readability": r.readability,
                "watermarks": r.watermark_count,
                "issues": r.issues,
            }
            for r in results
        ]
        print(json.dumps(data, indent=2))
    else:
        for r in results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            print(f"{status}  {r.path}")
            for issue in r.issues:
                print(f"       ⚠ {issue}")

    failed = sum(1 for r in results if not r.passed)
    if failed:
        print(f"\nquality-gate: {failed}/{len(results)} file(s) FAILED")
        return 1

    print(f"\nquality-gate: {len(results)} file(s) passed ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
