#!/usr/bin/env python3
"""Real benchmark for TextHumanize — speed, predictability, memory, detection, change reports."""
import time
import tracemalloc
import texthumanize as th

# --- Speed benchmark ---
samples = {
    "100w_en": (
        "The implementation of this methodology provides a comprehensive "
        "framework for understanding the underlying mechanisms. It is important "
        "to note that the utilization of these approaches has been demonstrated "
        "to yield significant improvements. Furthermore the systematic analysis "
        "of the data reveals patterns. "
    ) * 3,
    "500w_en": (
        "The implementation of this methodology provides a comprehensive framework. "
        "It is important to note that the utilization of these approaches yields "
        "significant improvements. Furthermore the systematic analysis of the data "
        "reveals patterns that can be utilized for optimization. The examination "
        "of these results demonstrates the effectiveness of this approach. "
    ) * 10,
    "1000w_en": (
        "The implementation of this methodology provides a comprehensive framework. "
        "It is important to note that utilization of these approaches yields improvements. "
        "Furthermore the systematic analysis of data reveals patterns for optimization. "
        "The examination of these results demonstrates effectiveness. "
    ) * 20,
}

print("=== SPEED BENCHMARK ===")
for name, text in samples.items():
    wcount = len(text.split())
    ccount = len(text)
    th.humanize(text, seed=42)  # warmup
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        th.humanize(text, seed=42)
        times.append(time.perf_counter() - t0)
    avg_ms = (sum(times) / len(times)) * 1000
    chars_sec = ccount / (sum(times) / len(times))
    print(f"  {name}: {wcount} words, {ccount} chars, avg {avg_ms:.1f}ms, {chars_sec:,.0f} chars/sec")

# --- Predictability ---
print("\n=== PREDICTABILITY (deterministic output) ===")
t1 = th.humanize(samples["500w_en"], seed=12345)
t2 = th.humanize(samples["500w_en"], seed=12345)
t3 = th.humanize(samples["500w_en"], seed=99999)
print(f"  Same seed identical output: {t1.text == t2.text}")
print(f"  Diff seed different output: {t1.text != t3.text}")
print(f"  Change ratio: {t1.change_ratio:.1%}")
print(f"  Quality score: {t1.quality_score:.2f}")
print(f"  Similarity: {t1.similarity:.2f}")

# --- Memory ---
print("\n=== MEMORY ===")
tracemalloc.start()
big = samples["1000w_en"] * 5
r = th.humanize(big, seed=42)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"  Text size: {len(big):,} chars ({len(big.split())} words)")
print(f"  Current memory: {current / 1024:.1f} KB")
print(f"  Peak memory: {peak / 1024:.1f} KB")

# --- AI Detection ---
print("\n=== AI DETECTION ===")
ai_texts = [
    "The implementation of this methodology provides a comprehensive framework for understanding the underlying mechanisms that drive innovation in the field. It is important to note that the utilization of advanced techniques has been demonstrated to yield significant improvements in overall performance metrics. Furthermore, the systematic analysis of available data reveals meaningful patterns that can be effectively utilized for process optimization. The examination of these results indicates a clear correlation between the proposed approach and measurable outcomes.",
    "Moreover, the comprehensive evaluation of the proposed methodology demonstrates its effectiveness across multiple dimensions of analysis. The integration of these components creates a robust system that addresses the fundamental challenges inherent in the current paradigm. Additionally, the iterative refinement process ensures continuous improvement and adaptation to evolving requirements.",
]
human_texts = [
    "So I tried this new coffee shop yesterday and honestly? Best latte Ive ever had, no joke. The barista was super chill too, we ended up talking about music for like 20 minutes. Gonna go back tomorrow probably. My friend Sarah says their croissants are amazing but I didnt try one yet.",
    "cant believe the game last night!! what a comeback, nobody saw that coming. my brother texted me like 50 times during the 4th quarter lol. we were screaming so loud the neighbors probably hate us now. worth it tho, best game this season for sure",
]
correct = 0
total = 0
for t in ai_texts:
    d = th.detect_ai(t)
    is_ai = d["score"] >= 50 or d["verdict"] in ("ai", "AI", "likely_ai")
    if is_ai:
        correct += 1
    total += 1
    print(f"  AI text -> verdict={d['verdict']} score={d['score']:.0f}% conf={d['confidence']:.0%} {'OK' if is_ai else 'MISS'}")
for t in human_texts:
    d = th.detect_ai(t)
    is_human = d["score"] < 50 or d["verdict"] in ("human", "Human", "likely_human")
    if is_human:
        correct += 1
    total += 1
    print(f"  Human text -> verdict={d['verdict']} score={d['score']:.0f}% conf={d['confidence']:.0%} {'OK' if is_human else 'MISS'}")
print(f"  Accuracy: {correct}/{total} ({correct / total:.0%})")

# --- Change Report ---
print("\n=== CHANGE REPORT (explain) ===")
r = th.humanize(
    "The implementation of this methodology provides a comprehensive framework for understanding.",
    seed=42,
    profile="web",
)
print(f"  Original:  {r.original}")
print(f"  Processed: {r.text}")
print(f"  Change ratio: {r.change_ratio:.1%}")
print(f"  Quality: {r.quality_score:.2f}")
print(f"  Similarity: {r.similarity:.2f}")
exp = th.explain(r)
print(f"  Explain:\n{exp}")

# --- AI detection speed ---
print("\n=== AI DETECTION SPEED ===")
for name, text in samples.items():
    th.detect_ai(text)  # warmup
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        th.detect_ai(text)
        times.append(time.perf_counter() - t0)
    avg_ms = (sum(times) / len(times)) * 1000
    print(f"  {name}: {avg_ms:.1f}ms")

# --- Quality benchmark ---
print("\n=== QUALITY BENCHMARK (45 samples) ===")
from benchmarks.quality_bench import run_benchmarks
results = run_benchmarks(verbose=False)
total = len(results)
passed = sum(1 for r in results if not r.issues)
avg_q = sum(r.quality_score for r in results) / total if total else 0
avg_speed = sum(r.chars_per_sec for r in results) / total if total else 0
print(f"  Pass rate: {passed}/{total} ({passed/total:.0%})")
print(f"  Avg quality: {avg_q:.2f}")
print(f"  Avg speed: {avg_speed:,.0f} chars/sec")
