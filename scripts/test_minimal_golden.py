"""Minimal golden test for debugging."""
import hashlib
from texthumanize import humanize

def test_hash():
    text = (
        "The implementation of artificial intelligence represents "
        "a considerable challenge. However, it is important to note that this "
        "technology facilitates the automation of various processes. Moreover, "
        "the utilization of AI ensures a significant increase in efficiency. "
        "Additionally, it is noteworthy that the development of this field "
        "is being actively pursued."
    )
    r = humanize(text, lang="en", profile="web", intensity=60, seed=42)
    h = hashlib.md5(r.text.encode()).hexdigest()
    print(f"\nHash: {h}")
    print(f"Text: {r.text[:120]}")
    assert h == "056b7d6948b11e6e0efe3635f6c2a8e7"
