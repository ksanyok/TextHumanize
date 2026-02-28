"""Check detector scores across PYTHONHASHSEED values."""
import hashlib
import sys
import os
sys.path.insert(0, ".")

from texthumanize import humanize

INPUT = (
    "The implementation of artificial intelligence represents a considerable "
    "challenge. However, it is important to note that this technology "
    "facilitates the automation of various processes. Moreover, the utilization "
    "of AI ensures a significant increase in efficiency. Additionally, it is "
    "noteworthy that the development of this field is being actively pursued."
)

r = humanize(INPUT, lang="en", profile="web", intensity=60, seed=42)
h = hashlib.md5(r.text.encode()).hexdigest()
print(f"PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED', 'random')}")
print(f"Hash: {h}")
print(f"Change ratio: {r.change_ratio}")
print(f"Text[:120]: {r.text[:120]}")
# Check metadata
for k, v in sorted(r.metadata.items()):
    if isinstance(v, (int, float, str, bool)):
        print(f"  {k}: {v}")
