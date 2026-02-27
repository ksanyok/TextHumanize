# Paraphrasing

Syntactic transforms that preserve meaning while changing structure.

```python
from texthumanize import paraphrase

result = paraphrase("The system works efficiently.", lang="en")
print(result)
```

## With Options

```python
result = paraphrase(
    "The implementation utilizes advanced methodologies.",
    lang="en",
    intensity=70,
    seed=42,
)
```
