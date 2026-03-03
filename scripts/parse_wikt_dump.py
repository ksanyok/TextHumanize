#!/usr/bin/env python3
"""Parse Wiktionary XML dumps to extract synonyms (streaming, low-memory).

Downloads & parses ruwiktionary / ukwiktionary dumps offline.
Outputs a compact Python dict file ready for SynonymDB integration.

Usage:
    python scripts/parse_wikt_dump.py                  # both RU + UK
    python scripts/parse_wikt_dump.py --lang ru        # RU only
    python scripts/parse_wikt_dump.py --lang uk        # UK only
    python scripts/parse_wikt_dump.py --skip-download  # reuse already downloaded dumps

The dumps are ~300MB (RU) and ~70MB (UK) compressed.
Downloaded to scripts/_dumps/ and deleted after parsing (unless --keep-dumps).
"""
from __future__ import annotations

import argparse
import bz2
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DUMP_DIR = Path(__file__).parent / "_dumps"
OUTPUT_DIR = Path(__file__).parent.parent / "texthumanize"

DUMP_URLS = {
    "ru": "https://dumps.wikimedia.org/ruwiktionary/latest/ruwiktionary-latest-pages-articles.xml.bz2",
    "uk": "https://dumps.wikimedia.org/ukwiktionary/latest/ukwiktionary-latest-pages-articles.xml.bz2",
}

# Max synonyms per word to keep (avoid bloat)
MAX_SYNONYMS = 15

# ─── Wikitext synonym extraction ────────────────────────────

# Patterns for synonym sections
_SYNONYM_HEADERS = {
    "ru": re.compile(
        r"^={3,4}\s*(?:Синонимы|синонимы)\s*={3,4}",
        re.MULTILINE,
    ),
    "uk": re.compile(
        r"^={3,4}\s*(?:Синоніми|синоніми)\s*={3,4}",
        re.MULTILINE,
    ),
}

# Next section header (stops synonym extraction)
_NEXT_SECTION = re.compile(r"^={2,4}\s*[^\s=]", re.MULTILINE)

# Extract [[word]] links from wiki text
_LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")

# Skip entries that look like templates, categories, etc.
_SKIP_RE = re.compile(r"[:{}/]")

# Only keep entries that look like real words (Cyrillic + basic punctuation)
_WORD_RE_RU = re.compile(r"^[а-яёА-ЯЁ][а-яёА-ЯЁ\s\-]{0,40}$")
_WORD_RE_UK = re.compile(r"^[а-яіїєґА-ЯІЇЄҐ'][а-яіїєґА-ЯІЇЄҐ'\s\-]{0,40}$")

_WORD_VALIDATORS = {
    "ru": _WORD_RE_RU,
    "uk": _WORD_RE_UK,
}

# Skip these titles (not actual dictionary entries)
_SKIP_TITLES = {"Заглавная страница", "Головна сторінка", "Шаблон:", "Категория:", "Категорія:"}


def _is_valid_word(word: str, lang: str) -> bool:
    """Check if word looks like a real dictionary entry."""
    if len(word) < 2 or len(word) > 40:
        return False
    if _SKIP_RE.search(word):
        return False
    validator = _WORD_VALIDATORS.get(lang)
    if validator and not validator.match(word):
        return False
    return True


def _extract_synonyms_from_wikitext(wikitext: str, lang: str) -> list[str]:
    """Extract synonyms from a Wiktionary article's wikitext."""
    header_re = _SYNONYM_HEADERS.get(lang)
    if not header_re:
        return []

    match = header_re.search(wikitext)
    if not match:
        return []

    # Find the content after the synonym header until next section
    start = match.end()
    next_sect = _NEXT_SECTION.search(wikitext, start)
    end = next_sect.start() if next_sect else len(wikitext)

    section = wikitext[start:end]

    # Extract all [[link]] references
    synonyms = []
    for m in _LINK_RE.finditer(section):
        word = m.group(1).strip()
        if _is_valid_word(word, lang):
            synonyms.append(word.lower())

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in synonyms:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique[:MAX_SYNONYMS]


# ─── Download ───────────────────────────────────────────────

def _download_dump(lang: str) -> Path:
    """Download Wiktionary dump, showing progress."""
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    url = DUMP_URLS[lang]
    filename = f"{lang}wiktionary-latest-pages-articles.xml.bz2"
    dest = DUMP_DIR / filename

    if dest.exists():
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  [skip] {dest.name} already exists ({size_mb:.1f} MB)")
        return dest

    print(f"  Downloading {url}")
    print(f"  → {dest}")

    req = urllib.request.Request(url, headers={"User-Agent": "TextHumanize/1.0 (synonym extraction)"})

    start_time = time.time()
    downloaded = 0

    with urllib.request.urlopen(req, timeout=600) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        total_mb = total / (1024 * 1024) if total else 0

        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)  # 256KB chunks
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                elapsed = time.time() - start_time
                speed = downloaded / (1024 * 1024) / max(elapsed, 0.1)
                done_mb = downloaded / (1024 * 1024)

                if total:
                    pct = downloaded / total * 100
                    eta = (total - downloaded) / max(downloaded / max(elapsed, 0.1), 1)
                    sys.stdout.write(
                        f"\r  {done_mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%) "
                        f"@ {speed:.1f} MB/s  ETA {eta:.0f}s   "
                    )
                else:
                    sys.stdout.write(f"\r  {done_mb:.1f} MB @ {speed:.1f} MB/s   ")
                sys.stdout.flush()

    print(f"\n  Done: {downloaded / (1024*1024):.1f} MB in {time.time()-start_time:.1f}s")
    return dest


# ─── Parse ──────────────────────────────────────────────────

def _parse_dump(dump_path: Path, lang: str) -> dict[str, list[str]]:
    """Stream-parse a bz2-compressed Wiktionary XML dump.
    
    Uses incremental XML parsing to avoid loading the full
    (2-4 GB decompressed) file into memory.
    """
    synonyms: dict[str, list[str]] = {}
    
    print(f"  Parsing {dump_path.name} (streaming bz2→XML)...")
    t0 = time.time()
    
    pages_total = 0
    pages_with_syns = 0
    ns_tag = None  # Will discover the namespace prefix dynamically
    
    # Stream-read the bz2 file
    with bz2.open(dump_path, "rb") as f:
        context = ET.iterparse(f, events=("end",))
        
        title = ""
        text_content = ""
        ns_value = ""
        
        for event, elem in context:
            tag = elem.tag
            # Strip namespace prefix if present
            if "}" in tag:
                if ns_tag is None:
                    ns_tag = tag[:tag.index("}") + 1]
                tag = tag[tag.index("}") + 1:]
            
            if tag == "title":
                title = (elem.text or "").strip()
            elif tag == "ns":
                ns_value = (elem.text or "").strip()
            elif tag == "text":
                text_content = elem.text or ""
            elif tag == "page":
                pages_total += 1
                
                # Only process main namespace (ns=0) articles
                if ns_value == "0" and title and text_content:
                    # Skip non-word titles
                    skip = False
                    for prefix in _SKIP_TITLES:
                        if title.startswith(prefix):
                            skip = True
                            break
                    
                    if not skip and _is_valid_word(title, lang):
                        syns = _extract_synonyms_from_wikitext(text_content, lang)
                        if syns:
                            key = title.lower()
                            # Don't include self
                            syns = [s for s in syns if s != key]
                            if syns:
                                synonyms[key] = syns
                                pages_with_syns += 1
                
                # Progress
                if pages_total % 50000 == 0:
                    elapsed = time.time() - t0
                    sys.stdout.write(
                        f"\r  Pages: {pages_total:,}  Synonyms found: {pages_with_syns:,}  "
                        f"({elapsed:.0f}s)   "
                    )
                    sys.stdout.flush()
                
                # Free memory — critical for large dumps
                title = ""
                text_content = ""
                ns_value = ""
                elem.clear()
    
    elapsed = time.time() - t0
    print(
        f"\n  Done: {pages_total:,} pages, {pages_with_syns:,} with synonyms, "
        f"{sum(len(v) for v in synonyms.values()):,} total synonym pairs, "
        f"{elapsed:.1f}s"
    )
    return synonyms


# ─── Output ─────────────────────────────────────────────────

def _write_python_dict(
    data: dict[str, dict[str, list[str]]],
    output_path: Path,
) -> None:
    """Write synonym data as a compact Python file."""
    lines: list[str] = [
        '"""Wiktionary offline synonyms — auto-generated.',
        "",
        "DO NOT EDIT MANUALLY. Regenerate via:",
        "    python scripts/parse_wikt_dump.py",
        '"""',
        "from __future__ import annotations",
        "",
    ]
    
    total_words = 0
    total_syns = 0
    
    for lang, syns in sorted(data.items()):
        var_name = f"{lang.upper()}_WIKT_SYNONYMS"
        total_words += len(syns)
        total_syns += sum(len(v) for v in syns.values())
        
        lines.append(f"# {lang.upper()}: {len(syns):,} words, "
                      f"{sum(len(v) for v in syns.values()):,} synonyms")
        lines.append(f"{var_name}: dict[str, list[str]] = {{")
        
        for word in sorted(syns.keys()):
            syn_list = syns[word]
            # Compact repr
            syn_str = ", ".join(f'"{s}"' for s in syn_list)
            lines.append(f'    "{word}": [{syn_str}],')
        
        lines.append("}")
        lines.append("")
    
    # Unified accessor
    lines.append("")
    lines.append("WIKT_SYNONYMS: dict[str, dict[str, list[str]]] = {")
    for lang in sorted(data.keys()):
        lines.append(f'    "{lang}": {lang.upper()}_WIKT_SYNONYMS,')
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def get_wikt_synonyms(word: str, lang: str = \"ru\") -> list[str]:")
    lines.append('    """Get synonyms for a word from Wiktionary offline data."""')
    lines.append("    db = WIKT_SYNONYMS.get(lang, {})")
    lines.append("    return list(db.get(word.lower(), []))")
    lines.append("")
    
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    
    size_kb = len(content.encode("utf-8")) / 1024
    print(f"\n  Output: {output_path}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Total: {total_words:,} words, {total_syns:,} synonyms")


def _write_json_compressed(
    data: dict[str, dict[str, list[str]]],
    output_path: Path,
) -> None:
    """Also write a compressed JSON backup."""
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    
    size_kb = json_path.stat().st_size / 1024
    print(f"  JSON backup: {json_path} ({size_kb:.1f} KB)")


# ─── Main ───────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Wiktionary dumps to extract synonyms."
    )
    parser.add_argument(
        "--lang", choices=["ru", "uk", "both"], default="both",
        help="Which language to process (default: both)",
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip download, use existing dumps in scripts/_dumps/",
    )
    parser.add_argument(
        "--keep-dumps", action="store_true",
        help="Keep downloaded dump files after parsing",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: texthumanize/_wikt_synonyms.py)",
    )
    args = parser.parse_args()
    
    languages = ["ru", "uk"] if args.lang == "both" else [args.lang]
    output_path = Path(args.output) if args.output else OUTPUT_DIR / "_wikt_synonyms.py"
    
    all_synonyms: dict[str, dict[str, list[str]]] = {}
    dump_paths: list[Path] = []
    
    for lang in languages:
        print(f"\n{'='*60}")
        print(f"  Processing {lang.upper()} Wiktionary")
        print(f"{'='*60}")
        
        # Download
        if not args.skip_download:
            dump_path = _download_dump(lang)
        else:
            filename = f"{lang}wiktionary-latest-pages-articles.xml.bz2"
            dump_path = DUMP_DIR / filename
            if not dump_path.exists():
                print(f"  ERROR: {dump_path} not found. Run without --skip-download first.")
                sys.exit(1)
        
        dump_paths.append(dump_path)
        
        # Parse
        synonyms = _parse_dump(dump_path, lang)
        all_synonyms[lang] = synonyms
    
    # Write output
    print(f"\n{'='*60}")
    print("  Writing output")
    print(f"{'='*60}")
    
    _write_python_dict(all_synonyms, output_path)
    _write_json_compressed(all_synonyms, output_path)
    
    # Cleanup dumps
    if not args.keep_dumps:
        for p in dump_paths:
            if p.exists():
                p.unlink()
                print(f"  Deleted: {p}")
        # Remove empty dir
        if DUMP_DIR.exists() and not list(DUMP_DIR.iterdir()):
            DUMP_DIR.rmdir()
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
