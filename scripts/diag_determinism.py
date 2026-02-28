"""Check if pipeline non-determinism is from restructurer or pre-existing."""
import hashlib
import sys
sys.path.insert(0, ".")

# Test 1: Full pipeline across runs in same process
from texthumanize import humanize

INPUT = (
    "The implementation of artificial intelligence represents a considerable "
    "challenge. However, it is important to note that this technology "
    "facilitates the automation of various processes. Moreover, the utilization "
    "of AI ensures a significant increase in efficiency. Additionally, it is "
    "noteworthy that the development of this field is being actively pursued."
)

print("=== Full pipeline (3 runs, same process) ===")
for i in range(3):
    r = humanize(INPUT, lang="en", profile="web", intensity=60, seed=42)
    print(hashlib.md5(r.text.encode()).hexdigest())

# Test 2: Just the restructurer
from texthumanize.sentence_restructurer import SentenceRestructurer
print("\n=== Restructurer only (3 runs, same process) ===")
for i in range(3):
    sr = SentenceRestructurer(lang="en", intensity=60, seed=42)
    out = sr.process(INPUT)
    print(hashlib.md5(out.encode()).hexdigest())
