#!/usr/bin/env python3
"""Generate a high-quality 50K word frequency list using wordfreq.

This replaces the synthetic freq data from /usr/share/dict padding.
Output: _data/en_freq_50k.json.gz — compact frequency mapping.
Build-time only (wordfreq is not a runtime dependency).
"""
import sys, json, gzip
from pathlib import Path
from wordfreq import top_n_list, word_frequency

OUT_DIR = Path(__file__).parent.parent / "texthumanize" / "_data"
OUT_DIR.mkdir(exist_ok=True)

# Generate top 50K English words with real frequencies
print("Generating EN 50K frequency list...")
en_words = top_n_list("en", 50000)
en_freq = {}
for w in en_words:
    f = word_frequency(w, "en")
    if f > 0 and w.isalpha() and len(w) >= 2:
        en_freq[w] = round(f, 8)

print(f"EN: {len(en_freq)} words")

# Also generate RU and UK lists (50K each for better Wiktionary coverage) 
print("Generating RU 50K frequency list...")
ru_words = top_n_list("ru", 50000)
ru_freq = {}
for w in ru_words:
    f = word_frequency(w, "ru")
    if f > 0 and len(w) >= 2:
        ru_freq[w] = round(f, 8)

print(f"RU: {len(ru_freq)} words")

print("Generating UK 50K frequency list...")
uk_words = top_n_list("uk", 50000)
uk_freq = {}
for w in uk_words:
    f = word_frequency(w, "uk")
    if f > 0 and len(w) >= 2:
        uk_freq[w] = round(f, 8)

print(f"UK: {len(uk_freq)} words")

# Save as compressed JSON
data = {"en": en_freq, "ru": ru_freq, "uk": uk_freq}
out_path = OUT_DIR / "word_freq.json.gz"
with gzip.open(out_path, "wt", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

size_mb = out_path.stat().st_size / 1024 / 1024
print(f"\nSaved to {out_path} ({size_mb:.2f} MB)")

# Verify quality 
print("\n--- Quality check ---")
test_words = {
    "en": ["abecedarian", "aboriginal", "vast", "important", "fundamental",
           "gongoresque", "brobdingnagian", "atlantean", "significant",
           "the", "good", "technology", "amplitudinous"],
    "ru": ["важный", "искусственный", "технология", "великий"],
    "uk": ["важливий", "штучний", "технологія", "великий"],
}
for lang, words in test_words.items():
    freqs = data[lang]
    print(f"\n{lang.upper()}:")
    for w in words:
        f = freqs.get(w, 0)
        status = "✓ in list" if w in freqs else "✗ NOT"
        print(f"  {w:20s}: {f:.8f}  {status}")
