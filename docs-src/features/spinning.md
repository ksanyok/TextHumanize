# Text Spinning

Generate multiple unique variants of a text while preserving meaning.

```python
from texthumanize import spin, spin_variants

# Single spin
result = spin("Original text here.", lang="en")

# Multiple variants
variants = spin_variants("Original text.", count=5, lang="en")
for v in variants:
    print(v)
```
