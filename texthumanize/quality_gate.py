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
import glob
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from texthumanize.core import analyze, detect_ai, detect_watermarks

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

    # 1) AI score
    try:
        ai = detect_ai(text, lang="auto")
        result.ai_score = ai.get("ai_score", 0)
        if result.ai_score > cfg.ai_threshold:
            result.passed = False
            result.issues.append(
                f"AI score {result.ai_score:.0f}% > threshold {cfg.ai_threshold:.0f}%"
            )
    except Exception as exc:
        result.issues.append(f"AI detection error: {exc}")

    # 2) Readability
    try:
        report = analyze(text, lang="auto")
        # Use a basic readability proxy from report
        result.readability = 100.0 - getattr(report, "artificiality_score", 0.0) * 100
        if result.readability < cfg.readability_threshold:
            result.passed = False
            result.issues.append(
                f"Readability {result.readability:.0f} < threshold "
                f"{cfg.readability_threshold:.0f}"
            )
    except Exception as exc:
        result.issues.append(f"Analysis error: {exc}")

    # 3) Watermarks
    if cfg.watermark_zero:
        try:
            wm = detect_watermarks(text)
            result.watermark_count = sum(
                1 for f in wm.findings if f.get("severity") in ("high", "critical")
            )
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
