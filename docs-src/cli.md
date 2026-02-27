# CLI Reference

TextHumanize provides a full-featured command-line interface.

## Commands

```bash
# Humanize a file
texthumanize input.txt -l en -p web -i 70 -o output.txt

# Pipe from stdin
echo "Text to humanize" | texthumanize - -l en

# AI detection
texthumanize input.txt --detect-ai

# Text analysis
texthumanize input.txt --analyze

# Paraphrasing
texthumanize input.txt --paraphrase -o out.txt

# Tone adjustment
texthumanize input.txt --tone casual

# Start API server
texthumanize dummy --api --port 8080

# Run benchmarks
texthumanize benchmark -l en
texthumanize benchmark -l en --json
```

## Options

| Flag | Description | Default |
|------|------------|---------|
| `-l`, `--lang` | Language code | `auto` |
| `-p`, `--profile` | Processing profile | `web` |
| `-i`, `--intensity` | Intensity 0-100 | `60` |
| `-o`, `--output` | Output file | stdout |
| `-s`, `--seed` | Random seed | None |
| `--detect-ai` | AI detection mode | |
| `--analyze` | Analysis mode | |
| `--paraphrase` | Paraphrasing mode | |
| `--tone` | Tone adjustment target | |
| `--api` | Start API server | |
| `--port` | API server port | `8080` |
| `--json` | JSON output (benchmark) | |

## Benchmark

```bash
$ texthumanize benchmark -l en

============================================================
  TextHumanize Benchmark — v0.16.0
  Language: en
============================================================

  [short] 98 chars
    Humanize: 142.3ms (689 chars/sec)
    Detect:   2.1ms
    Change:   15.2%
    Quality:  0.82
    AI score: 89% → 45% (ai_generated → mixed)

  [medium] 489 chars
    Humanize: 385.1ms (1,270 chars/sec)
    Detect:   5.8ms
    Change:   12.8%
    Quality:  0.87
    AI score: 92% → 38% (ai_generated → mixed)

  [long] 1467 chars
    Humanize: 1,021.4ms (1,436 chars/sec)
    Detect:   9.2ms
    Change:   11.5%
    Quality:  0.85
    AI score: 94% → 42% (ai_generated → mixed)

============================================================
  SUMMARY
============================================================
  Deterministic: ✅
============================================================
```
