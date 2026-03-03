"""Data loading and preprocessing for training v2.

Supports loading training data from:
- JSONL files (one JSON object per line with 'text' and 'label' fields)
- CSV files (with 'text' and 'label' columns)
- HC3 dataset format (Hugging Face)
- Raw text directories (one file per sample)

Label convention:
    0.0 = human-written
    1.0 = AI-generated
"""

from __future__ import annotations

import csv
import json
import logging
import os
import random
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class TextSample:
    """A single training sample."""

    __slots__ = ("label", "lang", "source", "text")

    def __init__(
        self,
        text: str,
        label: float,
        lang: str = "en",
        source: str = "",
    ) -> None:
        self.text = text
        self.label = label
        self.lang = lang
        self.source = source

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "label": self.label,
            "lang": self.lang,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TextSample:
        return cls(
            text=d["text"],
            label=float(d.get("label", 0.5)),
            lang=d.get("lang", "en"),
            source=d.get("source", ""),
        )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_jsonl(path: str, max_samples: int = 0) -> list[TextSample]:
    """Load data from a JSONL file.

    Expected format per line::

        {"text": "...", "label": 1.0, "lang": "en", "source": "gpt4"}
    """
    samples: list[TextSample] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "text" not in obj:
                continue
            samples.append(TextSample.from_dict(obj))
            if max_samples > 0 and len(samples) >= max_samples:
                break
    logger.info("Loaded %d samples from %s", len(samples), path)
    return samples


def load_csv(path: str, text_col: str = "text", label_col: str = "label",
             lang_col: str = "lang", max_samples: int = 0) -> list[TextSample]:
    """Load data from a CSV file."""
    samples: list[TextSample] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get(text_col, "")
            if not text:
                continue
            label = float(row.get(label_col, 0.5))
            lang = row.get(lang_col, "en")
            samples.append(TextSample(text=text, label=label, lang=lang, source="csv"))
            if max_samples > 0 and len(samples) >= max_samples:
                break
    logger.info("Loaded %d samples from %s", len(samples), path)
    return samples


def load_hc3(path: str, max_samples: int = 0) -> list[TextSample]:
    """Load HC3 (Human ChatGPT Comparison) dataset.

    HC3 format (JSONL): each line has:
        {"question": "...", "human_answers": ["..."], "chatgpt_answers": ["..."]}
    """
    samples: list[TextSample] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Human answers
            for ans in obj.get("human_answers", []):
                if isinstance(ans, str) and len(ans) > 50:
                    samples.append(TextSample(
                        text=ans, label=0.0, lang="en", source="hc3_human",
                    ))
                    if max_samples > 0 and len(samples) >= max_samples:
                        return samples

            # ChatGPT answers
            for ans in obj.get("chatgpt_answers", []):
                if isinstance(ans, str) and len(ans) > 50:
                    samples.append(TextSample(
                        text=ans, label=1.0, lang="en", source="hc3_chatgpt",
                    ))
                    if max_samples > 0 and len(samples) >= max_samples:
                        return samples

    logger.info("Loaded %d HC3 samples from %s", len(samples), path)
    return samples


def load_directory(
    path: str,
    label: float,
    lang: str = "en",
    extensions: tuple[str, ...] = (".txt",),
    max_samples: int = 0,
) -> list[TextSample]:
    """Load text files from a directory, assigning the same label to all."""
    samples: list[TextSample] = []
    for fname in sorted(os.listdir(path)):
        if not any(fname.endswith(ext) for ext in extensions):
            continue
        fpath = os.path.join(path, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                text = f.read().strip()
        except (OSError, UnicodeDecodeError):
            continue
        if len(text) > 20:
            samples.append(TextSample(text=text, label=label, lang=lang, source="dir"))
            if max_samples > 0 and len(samples) >= max_samples:
                break
    logger.info("Loaded %d files from %s (label=%.1f)", len(samples), path, label)
    return samples


def load_auto(path: str, max_samples: int = 0) -> list[TextSample]:
    """Auto-detect format and load."""
    if os.path.isdir(path):
        return load_directory(path, label=0.5, max_samples=max_samples)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return load_csv(path, max_samples=max_samples)
    # Default to JSONL
    # Try HC3 format first
    with open(path, encoding="utf-8") as f:
        first_line = f.readline().strip()
    try:
        obj = json.loads(first_line)
        if "human_answers" in obj or "chatgpt_answers" in obj:
            return load_hc3(path, max_samples=max_samples)
    except (json.JSONDecodeError, KeyError):
        pass
    return load_jsonl(path, max_samples=max_samples)


# ---------------------------------------------------------------------------
# Data splitting and balancing
# ---------------------------------------------------------------------------


def train_val_test_split(
    samples: list[TextSample],
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[TextSample], list[TextSample], list[TextSample]]:
    """Split data into train/val/test sets."""
    rng = random.Random(seed)
    data = list(samples)
    rng.shuffle(data)

    n = len(data)
    n_test = int(n * test_ratio)
    n_val = int(n * val_ratio)

    test = data[:n_test]
    val = data[n_test:n_test + n_val]
    train = data[n_test + n_val:]

    logger.info("Split: train=%d, val=%d, test=%d", len(train), len(val), len(test))
    return train, val, test


def balance_dataset(
    samples: list[TextSample],
    seed: int = 42,
) -> list[TextSample]:
    """Balance dataset by oversampling the minority class."""
    human = [s for s in samples if s.label < 0.5]
    ai = [s for s in samples if s.label >= 0.5]

    if not human or not ai:
        return samples

    rng = random.Random(seed)
    target = max(len(human), len(ai))

    if len(human) < target:
        extra = rng.choices(human, k=target - len(human))
        human.extend(extra)
    elif len(ai) < target:
        extra = rng.choices(ai, k=target - len(ai))
        ai.extend(extra)

    result = human + ai
    rng.shuffle(result)
    logger.info("Balanced dataset: %d samples (%d human, %d AI)", len(result), target, target)
    return result


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def save_jsonl(samples: list[TextSample], path: str) -> int:
    """Save samples to JSONL file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    logger.info("Saved %d samples to %s", len(samples), path)
    return len(samples)


def dataset_stats(samples: list[TextSample]) -> dict[str, Any]:
    """Compute basic statistics about a dataset."""
    n = len(samples)
    if n == 0:
        return {"total": 0}

    labels = [s.label for s in samples]
    n_human = sum(1 for l in labels if l < 0.5)
    n_ai = sum(1 for l in labels if l >= 0.5)
    lengths = [len(s.text) for s in samples]
    langs = {}
    sources = {}
    for s in samples:
        langs[s.lang] = langs.get(s.lang, 0) + 1
        if s.source:
            sources[s.source] = sources.get(s.source, 0) + 1

    return {
        "total": n,
        "human": n_human,
        "ai": n_ai,
        "balance_ratio": round(min(n_human, n_ai) / max(n_human, n_ai, 1), 2),
        "avg_length": round(sum(lengths) / n),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "languages": langs,
        "sources": sources,
    }
