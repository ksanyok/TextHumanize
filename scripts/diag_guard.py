"""Check if regression guard causes non-determinism."""
import hashlib
import sys
import os
sys.path.insert(0, ".")

# Test with different PYTHONHASHSEED simulation
# Since we can't change it within a process, test across 3 process invocations
# But we CAN check the actual scores coming from the detector

from texthumanize import humanize
from texthumanize.pipeline import Pipeline

INPUT = (
    "The implementation of artificial intelligence represents a considerable "
    "challenge. However, it is important to note that this technology "
    "facilitates the automation of various processes. Moreover, the utilization "
    "of AI ensures a significant increase in efficiency. Additionally, it is "
    "noteworthy that the development of this field is being actively pursued."
)

# Run humanization and capture intermediate state
p = Pipeline(lang="en", profile="web", intensity=60, seed=42)
result = p.run(INPUT)
print(f"Hash: {hashlib.md5(result.text.encode()).hexdigest()}")
print(f"Change ratio: {result.change_ratio}")
print(f"Score before: {result.metadata.get('score_before', 'N/A')}")
print(f"Score after: {result.metadata.get('score_after', 'N/A')}")
print(f"Stages: {result.metadata.get('stages_applied', 'N/A')}")
print(f"Guard triggered: {result.metadata.get('regression_guard', 'N/A')}")
print(f"PYTHONHASHSEED: {os.environ.get('PYTHONHASHSEED', 'random')}")
