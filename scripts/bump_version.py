#!/usr/bin/env python3
"""Bump the package version across every manifest and port in one command.

The release version is duplicated across Python, JS and PHP manifests, port
source files, version-assertion tests, the CHANGELOG and README. Keeping them
in sync by hand is error-prone (it broke the 0.29.0 release), and
``scripts/check_version_sync.py`` only *detects* drift after the fact. This
script *writes* every literal that checker validates, so a release is one step:

    python scripts/bump_version.py 0.34.0
    python scripts/check_version_sync.py   # should print "Version sync OK"

What it updates:
  - pyproject.toml                      version = "..."
  - texthumanize/__init__.py            __version__ = "..."
  - package.json, js/package.json,
    js/package-lock.json (root + pkg),
    composer.json, php/composer.json    "version": "..."
  - js/src/version.ts                   VERSION = '...'
  - php/src/TextHumanize.php            public const VERSION = '...'
  - php/tests/TextHumanizeTest.php,
    js/tests/core.test.ts               version-assertion literals
  - CHANGELOG.md                        promotes [Unreleased] -> [X] - DATE
  - README.md                           install command, pinned PyPI badge,
                                        "TextHumanize vX", "What's New in vX"

Editorial content (the CHANGELOG entry body and the README "What's New" prose)
is still yours to write — the script reports what remains.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SEMVER = re.compile(r"^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8")


def _sub_once(rel: str, pattern: str, repl: str, changed: list[str]) -> None:
    text = _read(rel)
    new, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if n == 0:
        raise SystemExit(f"ERROR: no version literal matched in {rel} (pattern: {pattern})")
    if new != text:
        _write(rel, new)
        changed.append(rel)


def _sub_optional(rel: str, pattern: str, repl: str, changed: list[str]) -> None:
    """Like _sub_once but tolerates zero matches.

    Some port test files assert the version dynamically (comparing against the
    manifest) rather than hardcoding a literal, so there may be nothing to swap.
    """
    if not (ROOT / rel).exists():
        return
    text = _read(rel)
    new, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if n and new != text:
        _write(rel, new)
        changed.append(rel)


def _bump_json(rel: str, old: str, new: str, changed: list[str]) -> None:
    """Bump the package's own version in a JSON manifest, preserving formatting.

    Replaces every ``"version": "<old>"`` occurrence (the top-level field and,
    in npm lockfiles, ``packages[""].version``) via text substitution so the
    file's original indentation and key order are untouched. Dependency pins
    carry other version numbers and are not matched.
    """
    text = _read(rel)
    # Validate it's parseable and actually at `old` before touching it.
    obj = json.loads(text)
    if obj.get("version") != old:
        raise SystemExit(
            f"ERROR: {rel} version is {obj.get('version')!r}, expected {old!r}"
        )
    pattern = r'("version"\s*:\s*")' + re.escape(old) + r'(")'
    new_text, n = re.subn(pattern, rf"\g<1>{new}\g<2>", text)
    if n and new_text != text:
        _write(rel, new_text)
        changed.append(rel)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump TextHumanize version everywhere.")
    parser.add_argument("version", help="New version, e.g. 0.34.0")
    parser.add_argument("--date", default=None, help="Release date YYYY-MM-DD (CHANGELOG). Pass explicitly for reproducibility.")
    args = parser.parse_args()

    new = args.version.strip()
    if not _SEMVER.match(new):
        raise SystemExit(f"ERROR: {new!r} is not a valid semver version")

    old = re.search(r'^version\s*=\s*"([^"]+)"', _read("pyproject.toml"), re.MULTILINE)
    if not old:
        raise SystemExit("ERROR: could not read current version from pyproject.toml")
    old_v = old.group(1)
    if old_v == new:
        raise SystemExit(f"ERROR: version is already {new}")

    changed: list[str] = []

    # Manifests / source literals.
    _sub_once("pyproject.toml", r'^version\s*=\s*"[^"]+"', f'version = "{new}"', changed)
    _sub_once("texthumanize/__init__.py", r'^__version__\s*=\s*"[^"]+"', f'__version__ = "{new}"', changed)
    for rel in ("package.json", "js/package.json", "js/package-lock.json", "composer.json", "php/composer.json"):
        _bump_json(rel, old_v, new, changed)
    _sub_once("js/src/version.ts", r"VERSION\s*=\s*'[^']+'", f"VERSION = '{new}'", changed)
    _sub_once("php/src/TextHumanize.php", r"public const VERSION = '[^']+'", f"public const VERSION = '{new}'", changed)

    # Version-assertion tests (validated by check_version_sync). Optional:
    # some ports assert the version dynamically and carry no literal to swap.
    _sub_optional("php/tests/TextHumanizeTest.php", rf"(VERSION[^\n]*?'){re.escape(old_v)}(')", rf"\g<1>{new}\g<2>", changed)
    _sub_optional("js/tests/core.test.ts", rf"(toBe\(\s*'){re.escape(old_v)}('\s*\))", rf"\g<1>{new}\g<2>", changed)

    # CHANGELOG: promote [Unreleased] -> [new] - date, keep an empty Unreleased on top.
    changelog = _read("CHANGELOG.md")
    if f"## [{new}]" not in changelog:
        date = args.date or "UNDATED"
        promoted = changelog.replace(
            "## [Unreleased]",
            f"## [Unreleased]\n\n## [{new}] - {date}",
            1,
        )
        if promoted != changelog:
            _write("CHANGELOG.md", promoted)
            changed.append("CHANGELOG.md")

    # README version literals validated by check_version_sync.
    for pat, repl in (
        (rf"pip install texthumanize=={re.escape(old_v)}", f"pip install texthumanize=={new}"),
        (rf"pypi-v{re.escape(old_v)}-", f"pypi-v{new}-"),
        (rf"TextHumanize v{re.escape(old_v)}", f"TextHumanize v{new}"),
        (rf"What's New in v{re.escape(old_v)}", f"What's New in v{new}"),
    ):
        readme = _read("README.md")
        new_readme, n = re.subn(pat, repl, readme)
        if n:
            _write("README.md", new_readme)
            if "README.md" not in changed:
                changed.append("README.md")

    print(f"Bumped {old_v} -> {new}. Updated files:")
    for rel in changed:
        print(f"  - {rel}")
    print("\nStill TODO by hand:")
    print(f"  - Write the CHANGELOG entry body under ## [{new}]")
    print(f"  - Update the README 'What's New in v{new}' section prose")
    if args.date is None:
        print("  - Set the CHANGELOG date (re-run with --date YYYY-MM-DD, or edit UNDATED)")
    print("\nThen run: python scripts/check_version_sync.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
