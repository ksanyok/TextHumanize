import json
from texthumanize import humanize

result = humanize(
    "The implementation of artificial intelligence in healthcare represents a significant paradigm shift. This comprehensive approach leverages cutting-edge technology to facilitate unprecedented improvements in diagnostic accuracy. Furthermore, these innovative solutions demonstrate remarkable potential to transform the landscape of modern medicine.",
    lang="en", intensity=70,
)
print("TEXT:", result.text)
print()
print("CHANGES:")
for c in result.changes:
    print(" ", c)
print()
print("CHANGE_RATIO:", result.change_ratio)
print("SCORE_BEFORE:", result.metrics_before.get("artificiality_score") if isinstance(result.metrics_before, dict) else getattr(result.metrics_before, "artificiality_score", None))
print("SCORE_AFTER:", result.metrics_after.get("artificiality_score") if isinstance(result.metrics_after, dict) else getattr(result.metrics_after, "artificiality_score", None))
