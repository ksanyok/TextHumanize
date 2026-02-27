# Tone Analysis & Adjustment

7-level formality scale for analyzing and adjusting text tone.

## Analyze Tone

```python
from texthumanize import analyze_tone

tone = analyze_tone("Please submit the required documentation.", lang="en")
print(tone)  # Formality level, register, suggestions
```

## Adjust Tone

```python
from texthumanize import adjust_tone

casual = adjust_tone(
    "It is imperative to proceed with the implementation.",
    target="casual",
    lang="en",
)
print(casual)
# → "We need to move forward with this."
```

## Tone Levels

| Level | Example Use |
|-------|------------|
| `very_formal` | Legal documents, contracts |
| `formal` | Business correspondence |
| `semi_formal` | Reports, presentations |
| `neutral` | News articles |
| `semi_casual` | Blog posts |
| `casual` | Social media, chat |
| `very_casual` | SMS, informal messaging |
