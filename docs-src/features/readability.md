# Readability Analysis

6 readability indices for comprehensive text analysis.

```python
from texthumanize import full_readability

scores = full_readability("Your text here.", lang="en")
print(scores)
```

## Indices

| Index | Range | Best For |
|-------|-------|----------|
| Flesch Reading Ease | 0–100 | General readability |
| Flesch-Kincaid Grade | 0–18+ | Grade level |
| Coleman-Liau Index | 0–18+ | Grade level (character-based) |
| Automated Readability Index | 0–14+ | Grade level |
| SMOG Index | 3–18+ | Healthcare/technical |
| Dale-Chall | 0–10 | Grade level (vocabulary) |
