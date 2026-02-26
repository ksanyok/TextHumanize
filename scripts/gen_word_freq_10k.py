#!/usr/bin/env python3
"""Generate 10K+ word frequency data for word_lm.py."""
import math, zlib, base64, os, sys

# Execute gen script's word lists
exec_globals = {}
exec(open("scripts/gen_word_freq.py").read(), exec_globals)

curated_en = exec_globals['en_words']
print(f"Curated EN: {len(curated_en)}")

# Add system dictionary words
with open("/usr/share/dict/words") as f:
    sys_words = []
    for line in f:
        w = line.strip().lower()
        if w.isalpha() and 3 <= len(w) <= 14:
            sys_words.append(w)

seen = set(curated_en)
extra = []
for w in sys_words:
    if w not in seen:
        seen.add(w)
        extra.append(w)

target = 10000
all_en = curated_en + extra[:target - len(curated_en)]
print(f"Total EN: {len(all_en)}")

# Frequencies
def make_freq(words, top_f=0.069, alpha=1.07, d=2.7):
    C = top_f * (1 + d) ** alpha
    out = {}
    for r, w in enumerate(words, 1):
        f = C / (r + d) ** alpha
        out[w] = round(max(f, 1e-9), 9)
    return out

en_f = make_freq(all_en, 0.069)
ru_f = make_freq(exec_globals['ru_words'], 0.032)
de_f = make_freq(exec_globals['de_words'], 0.035)
fr_f = make_freq(exec_globals['fr_words'], 0.036)
es_f = make_freq(exec_globals['es_words'], 0.040)

en_bi = exec_globals['en_bi']
ru_bi = exec_globals['ru_bi']

print(f"EN uni: {len(en_f)}, bi: {len(en_bi)}")
print(f"RU uni: {len(ru_f)}, bi: {len(ru_bi)}")
print(f"DE: {len(de_f)}, FR: {len(fr_f)}, ES: {len(es_f)}")

# Encode
def enc_uni(d):
    data = "\n".join(f"{w}\t{f}" for w, f in d.items()).encode()
    return base64.b64encode(zlib.compress(data, 9)).decode()

def enc_bi(d):
    data = "\n".join(f"{a}\t{b}\t{f}" for (a, b), f in d.items()).encode()
    return base64.b64encode(zlib.compress(data, 9)).decode()

datasets = {
    "_EN_UNI_DATA": enc_uni(en_f),
    "_EN_BI_DATA": enc_bi(en_bi),
    "_RU_UNI_DATA": enc_uni(ru_f),
    "_RU_BI_DATA": enc_bi(ru_bi),
    "_DE_UNI_DATA": enc_uni(de_f),
    "_FR_UNI_DATA": enc_uni(fr_f),
    "_ES_UNI_DATA": enc_uni(es_f),
}

# Write
path = "texthumanize/_word_freq_data.py"
with open(path, "w") as out:
    out.write(f'"""Compressed word frequency data for word_lm.py.\n\n')
    out.write(f'Auto-generated. Do not edit manually.\n')
    out.write(f'EN: {len(en_f)} unigrams, {len(en_bi)} bigrams\n')
    out.write(f'RU: {len(ru_f)} unigrams, {len(ru_bi)} bigrams\n')
    out.write(f'DE: {len(de_f)} | FR: {len(fr_f)} | ES: {len(es_f)}\n')
    out.write(f'"""\n\nfrom __future__ import annotations\n\nimport base64\nimport zlib\n\n\n')

    out.write('def _decode_uni(data: str) -> dict[str, float]:\n')
    out.write('    """Decode compressed unigram frequency data."""\n')
    out.write('    raw = zlib.decompress(base64.b64decode(data)).decode("utf-8")\n')
    out.write('    result: dict[str, float] = {}\n')
    out.write('    for line in raw.split("\\n"):\n')
    out.write('        if "\\t" in line:\n')
    out.write('            w, freq = line.split("\\t", 1)\n')
    out.write('            result[w] = float(freq)\n')
    out.write('    return result\n\n\n')

    out.write('def _decode_bi(data: str) -> dict[tuple[str, str], float]:\n')
    out.write('    """Decode compressed bigram frequency data."""\n')
    out.write('    raw = zlib.decompress(base64.b64decode(data)).decode("utf-8")\n')
    out.write('    result: dict[tuple[str, str], float] = {}\n')
    out.write('    for line in raw.split("\\n"):\n')
    out.write('        parts = line.split("\\t")\n')
    out.write('        if len(parts) == 3:\n')
    out.write('            result[(parts[0], parts[1])] = float(parts[2])\n')
    out.write('    return result\n\n\n')

    for name, data in datasets.items():
        out.write(f'{name} = (\n')
        for i in range(0, len(data), 76):
            out.write(f'    "{data[i:i+76]}"\n')
        out.write(')\n\n')

    out.write('\n# ── Lazy-loaded cache ─────────────────────────────\n')
    out.write('_cache: dict[str, dict] = {}\n\n\n')

    for lang, uni_name, bi_name in [
        ("en", "_EN_UNI_DATA", "_EN_BI_DATA"),
        ("ru", "_RU_UNI_DATA", "_RU_BI_DATA"),
    ]:
        out.write(f'def get_{lang}_uni() -> dict[str, float]:\n')
        out.write(f'    """Get {lang.upper()} unigram frequencies (lazy-loaded)."""\n')
        out.write(f'    if "{lang}_uni" not in _cache:\n')
        out.write(f'        _cache["{lang}_uni"] = _decode_uni({uni_name})\n')
        out.write(f'    return _cache["{lang}_uni"]  # type: ignore[return-value]\n\n\n')
        out.write(f'def get_{lang}_bi() -> dict[tuple[str, str], float]:\n')
        out.write(f'    """Get {lang.upper()} bigram frequencies (lazy-loaded)."""\n')
        out.write(f'    if "{lang}_bi" not in _cache:\n')
        out.write(f'        _cache["{lang}_bi"] = _decode_bi({bi_name})\n')
        out.write(f'    return _cache["{lang}_bi"]  # type: ignore[return-value]\n\n\n')

    for lang, data_name in [("de", "_DE_UNI_DATA"), ("fr", "_FR_UNI_DATA"), ("es", "_ES_UNI_DATA")]:
        out.write(f'def get_{lang}_uni() -> dict[str, float]:\n')
        out.write(f'    """Get {lang.upper()} unigram frequencies (lazy-loaded)."""\n')
        out.write(f'    if "{lang}_uni" not in _cache:\n')
        out.write(f'        _cache["{lang}_uni"] = _decode_uni({data_name})\n')
        out.write(f'    return _cache["{lang}_uni"]  # type: ignore[return-value]\n\n\n')

sz = os.path.getsize(path)
print(f"\nWrote: {path} ({sz:,} bytes, {sz//1024} KB)")
lc = sum(1 for _ in open(path))
print(f"Lines: {lc}")
print("Done!")
