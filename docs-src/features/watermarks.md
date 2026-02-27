# Watermark Detection & Cleaning

Detect and remove 5 types of invisible watermarks from text.

## Detect

```python
from texthumanize import detect_watermarks

result = detect_watermarks("Te\u200bxt wi\u200bth hid\u200bden ch\u200bars")
print(result)  # Types found, locations, confidence
```

## Clean

```python
from texthumanize import clean_watermarks

clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden ch\u200bars")
print(clean)  # "Text with hidden chars"
```

## Watermark Types

| Type | Description |
|------|------------|
| Zero-width characters | U+200B, U+200C, U+200D, U+FEFF |
| Homoglyph substitution | Latin/Cyrillic lookalikes |
| Invisible Unicode | Combining marks, variation selectors |
| Whitespace encoding | Tab/space patterns |
| Metadata | Hidden formatting markers |
