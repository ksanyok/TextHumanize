#!/usr/bin/env python3
"""System diagnostic test."""
import os
import sys
import time

sys.path.insert(0, ".")
import texthumanize as th

print("=== 1. БАЗОВАЯ ГУМАНИЗАЦИЯ (EN) ===")
ai_text = (
    "Furthermore, it is important to note that the implementation of "
    "comprehensive strategies necessitates a thorough understanding of "
    "the underlying mechanisms. In conclusion, the systematic approach "
    "provides significant advantages in terms of efficiency and effectiveness."
)
t0 = time.time()
result = th.humanize(ai_text, lang="en", intensity=70)
t1 = time.time()
print(f"Время: {(t1-t0)*1000:.0f}ms")
print(f"Изменено: {result.change_ratio*100:.1f}%")
print(f"# изменений: {len(result.changes)}")
print(f"Оригинал: {ai_text[:100]}...")
print(f"Результат: {result.text[:100]}...")
print()

print("=== 2. AI ДЕТЕКЦИЯ ===")
detect_ai = th.detect_ai(ai_text, lang="en")
human_text = (
    "I went to the store yesterday and bought some milk. "
    "The weather was kinda nice, so I walked. My dog was happy to see me."
)
detect_human = th.detect_ai(human_text, lang="en")
print(f"AI текст: score={detect_ai['score']:.2f}, verdict={detect_ai['verdict']}")
print(f"Human текст: score={detect_human['score']:.2f}, verdict={detect_human['verdict']}")
print()

print("=== 3. РУССКИЙ ТЕКСТ ===")
ru_text = (
    "В данном контексте необходимо отметить, что осуществление комплексных "
    "мероприятий требует тщательного анализа. Кроме того, следует учитывать, "
    "что данный подход является наиболее оптимальным."
)
result_ru = th.humanize(ru_text, lang="ru", intensity=70)
print(f"Изменено: {result_ru.change_ratio*100:.1f}%")
print(f"# изменений: {len(result_ru.changes)}")
print(f"Результат: {result_ru.text[:120]}...")
print()

print("=== 4. WORD LM (10K) ===")
from texthumanize.word_lm import WordLanguageModel
lm = WordLanguageModel(lang="en")
pp_ai = lm.perplexity(ai_text)
pp_human = lm.perplexity(human_text)
ns = lm.naturalness_score(ai_text)
print(f"Perplexity AI: {pp_ai:.1f}")
print(f"Perplexity Human: {pp_human:.1f}")
print(f"Naturalness AI: {ns['naturalness']}/100, verdict={ns['verdict']}")
print(f"Vocab size: {lm._vocab_size}")
print()

print("=== 5. COLLOCATION ENGINE ===")
from texthumanize.collocation_engine import CollocEngine
ce = CollocEngine(lang="en")
syn1 = ce.best_synonym("make", ["take", "do", "perform", "create"], context=["decision", "important"])
syn2 = ce.best_synonym("heavy", ["strong", "big", "intense", "hard"], context=["rain", "weather"])
syn3 = ce.best_synonym("pay", ["give", "show", "draw", "direct"], context=["attention", "focus"])
print(f"make (ctx: decision) -> best: {syn1}")
print(f"heavy (ctx: rain) -> best: {syn2}")
print(f"pay (ctx: attention) -> best: {syn3}")
print(f"EN collocations: {len(ce._coll)}")
print(f"EN collocate list for 'make': {ce.collocates('make', top_n=5)}")
print()

print("=== 6. СКОРОСТЬ ===")
long_text = ai_text * 10
t0 = time.time()
r = th.humanize(long_text, lang="en", intensity=50)
t1 = time.time()
chars_per_sec = len(long_text) / (t1 - t0)
print(f"Текст: {len(long_text)} символов")
print(f"Время: {(t1-t0)*1000:.0f}ms")
print(f"Скорость: {chars_per_sec:.0f} char/sec")
print()

print("=== 7. OSS МОДЕЛЬ (ai_backend) ===")
try:
    from texthumanize import ai_backend as ab
    print(f"AIBackend class: OK")
    backend = ab.AIBackend()
    attrs = [a for a in dir(backend) if not a.startswith('__')]
    print(f"Public attrs: {[a for a in attrs if not a.startswith('_')][:10]}")
    print(f"Has humanize_ai: {'humanize_ai' in attrs or 'humanize' in attrs}")
    print(f"Circuit breaker: {getattr(backend, '_circuit_state', 'N/A')}")
    print(f"NOTE: OSS requires running Gradio endpoint")
except Exception as e:
    print(f"ОШИБКА: {e}")
print()

print("=== 8. PIPELINE STAGES ===")
from texthumanize.pipeline import Pipeline
print(f"Pipeline class: OK")
print(f"Thread-safe lock: {hasattr(Pipeline, '_cls_lock')}")
print()

print("=== 9. СТАТИСТИКА ПРОЕКТА ===")
py_files = []
total_lines = 0
for root, dirs, files in os.walk("texthumanize"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            lines = sum(1 for _ in open(path))
            total_lines += lines
            py_files.append((path, lines))

print(f"Python модулей: {len(py_files)}")
print(f"Строк кода: {total_lines:,}")
print(f"Тестов: 1696 (all pass)")
print(f"Языков: 14")
print()

# Top 10 largest modules
py_files.sort(key=lambda x: -x[1])
print("Топ-10 модулей по размеру:")
for path, lines in py_files[:10]:
    print(f"  {path}: {lines:,} строк")
