#!/usr/bin/env python3
"""Test humanization quality."""
from texthumanize import humanize

text = (
    "The implementation of artificial intelligence in healthcare represents "
    "a significant paradigm shift. This comprehensive approach leverages "
    "cutting-edge technology to facilitate unprecedented improvements in "
    "diagnostic accuracy. Furthermore, these innovative solutions demonstrate "
    "remarkable potential to transform the landscape of modern medicine."
)

result = humanize(text, lang="en", intensity=70)
print("INPUT:", text[:200])
print()
print("OUTPUT:", result["text"][:500])
print()
print("CHANGES:", len(result.get("changes", [])))
for c in result.get("changes", []):
    orig = c.get("original", "")
    repl = c.get("replacement", "")
    desc = c.get("description", "")
    if orig:
        print(f"  {c['type']}: '{orig}' -> '{repl}'")
    elif desc:
        print(f"  {c['type']}: {desc}")
print()
print("SCORE BEFORE:", result.get("metrics_before", {}).get("artificiality_score"))
print("SCORE AFTER:", result.get("metrics_after", {}).get("artificiality_score"))
print("CHANGE RATIO:", result.get("change_ratio"))
