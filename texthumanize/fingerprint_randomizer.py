"""Anti-fingerprint randomizer.

Prevents detectable patterns in humanized output by
randomizing substitution order, varying synonym pools,
adding processing jitter, and diversifying whitespace.

Usage:
    from texthumanize.fingerprint_randomizer import (
        FingerprintRandomizer,
    )

    rand = FingerprintRandomizer(seed=None)
    plan = rand.randomize_plan(substitutions)
    text = rand.apply_jitter(text)
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
from typing import Any

logger = logging.getLogger(__name__)

class FingerprintRandomizer:
    """Anti-fingerprint diversification engine.

    Ensures no two runs of humanize produce identical
    substitution patterns, preventing reverse-engineering.
    """

    def __init__(
        self,
        seed: int | None = None,
        *,
        jitter_level: float = 0.3,
    ) -> None:
        """Init.

        Args:
            seed: Random seed (None = non-deterministic).
            jitter_level: 0.0-1.0, how much to vary.
        """
        self.rng = random.Random(seed)
        self.jitter = max(0.0, min(1.0, jitter_level))

    # ── Substitution randomization ────────────────────────

    def randomize_plan(
        self,
        substitutions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Shuffle & thin substitution plan.

        Each substitution dict has:
            "original", "replacement", "position"

        Some substitutions are randomly dropped to prevent
        100% replacement rate (which is detectable).
        """
        if not substitutions:
            return []

        # Shuffle order
        plan = list(substitutions)
        self.rng.shuffle(plan)

        # Randomly drop 10-30% of substitutions
        drop_rate = 0.1 + self.jitter * 0.2
        plan = [
            s for s in plan
            if self.rng.random() > drop_rate
        ]

        return plan

    def vary_synonym_pool(
        self,
        synonyms: list[str],
        *,
        min_keep: int = 2,
    ) -> list[str]:
        """Randomly reorder and thin synonym pool.

        Prevents always picking the same "top" synonym.
        """
        if len(synonyms) <= min_keep:
            return list(synonyms)

        pool = list(synonyms)
        self.rng.shuffle(pool)

        # Randomly drop some options
        keep = max(
            min_keep,
            int(len(pool) * (0.6 + self.rng.random() * 0.4)),
        )
        return pool[:keep]

    def pick_synonym(
        self,
        synonyms: list[str],
        weights: list[float] | None = None,
    ) -> str:
        """Pick a synonym with weighted randomness.

        If weights provided, use them with added noise.
        Otherwise uniform random choice.
        """
        if not synonyms:
            return ""
        if len(synonyms) == 1:
            return synonyms[0]

        if weights and len(weights) == len(synonyms):
            # Add noise to weights
            noisy = [
                max(0.01, w + self.rng.gauss(0, 0.1 * w))
                for w in weights
            ]
            total = sum(noisy)
            noisy = [w / total for w in noisy]
            # Weighted random pick
            r = self.rng.random()
            cumulative = 0.0
            for i, w in enumerate(noisy):
                cumulative += w
                if r <= cumulative:
                    return synonyms[i]
            return synonyms[-1]

        return self.rng.choice(synonyms)

    # ── Whitespace diversification ────────────────────────

    def diversify_whitespace(self, text: str) -> str:
        """Vary whitespace patterns to prevent fingerprinting.

        Randomly adjusts spacing around punctuation, varies
        paragraph breaks, changes list indentation style.
        """
        if self.jitter < 0.1:
            return text

        lines = text.split('\n')
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip()

            # 1. Occasionally double-space after period (human quirk)
            if (
                stripped.endswith('.')
                and self.rng.random() < self.jitter * 0.08
                and i + 1 < len(lines)
                and lines[i + 1].strip()
            ):
                result.append(stripped)
                # Insert extra blank line between paragraphs
                if not (i + 1 < len(lines) and lines[i + 1] == ''):
                    result.append('')
                i += 1
                continue

            # 2. Randomly vary spacing after commas/semicolons
            if self.rng.random() < self.jitter * 0.12:
                # Normalize double-spaces after punct to single
                stripped = re.sub(r'([,;:])  ', r'\1 ', stripped)

            # 3. Vary indentation of list-like items
            if (
                re.match(r'^(\s*)([-*•])\s', stripped)
                and self.rng.random() < self.jitter * 0.15
            ):
                m = re.match(r'^(\s*)([-*•])\s', stripped)
                if m:
                    indent = m.group(1)
                    marker = m.group(2)
                    rest = stripped[m.end():]
                    # Vary: switch bullet style
                    alt_markers = ['-', '•', '*']
                    alt_markers = [
                        x for x in alt_markers if x != marker
                    ]
                    new_marker = self.rng.choice(alt_markers)
                    stripped = f"{indent}{new_marker} {rest}"

            result.append(stripped)
            i += 1

        return '\n'.join(result)

    # ── Processing jitter ─────────────────────────────────

    def should_skip(self, *, base_prob: float = 0.5) -> bool:
        """Randomly decide whether to skip a transformation.

        Prevents all transformations being applied
        uniformly (which is detectable).
        """
        threshold = base_prob + self.rng.gauss(
            0, self.jitter * 0.2,
        )
        return self.rng.random() > max(0.1, min(0.95, threshold))

    def jitter_intensity(
        self,
        base: float,
        *,
        spread: float = 0.15,
    ) -> float:
        """Add random jitter to transformation intensity.

        Returns base ± spread, clamped to [0.05, 1.0].
        """
        noise = self.rng.gauss(0, spread * self.jitter)
        return max(0.05, min(1.0, base + noise))

    # ── Paragraph-level variation ─────────────────────────

    def vary_paragraph_intensity(
        self,
        paragraphs: list[str],
        base_intensity: float = 0.5,
    ) -> list[float]:
        """Assign different intensities to each paragraph.

        AI text has uniform structure; human text varies.
        Random intensity per paragraph adds realism.
        """
        intensities: list[float] = []
        for _ in paragraphs:
            i = self.jitter_intensity(
                base_intensity, spread=0.2,
            )
            intensities.append(round(i, 3))
        return intensities

    # ── Output hash diversification ───────────────────────

    def diversify_output(self, text: str) -> str:
        """Final pass: add micro-variations.

        - Vary em-dash vs en-dash style
        - Vary quote styles (straight/curly)
        - Vary ellipsis style
        - Vary comma-before-and (Oxford comma)
        - Vary abbreviation style
        - Vary number formatting
        """
        if self.jitter < 0.1:
            return text

        result = text

        # 1. Em-dash ↔ en-dash with spaces
        if '—' in result and self.rng.random() < 0.25:
            dashes = list(re.finditer(r'\s?—\s?', result))
            if dashes:
                pick = self.rng.choice(dashes)
                styles = [' – ', ' — ', '—']
                replacement = self.rng.choice(styles)
                result = (
                    result[:pick.start()]
                    + replacement
                    + result[pick.end():]
                )

        # 2. Straight quotes → curly quotes (or vice versa)
        if self.rng.random() < 0.2:
            if '"' in result:
                m = re.search(r'"([^"]{1,200})"', result)
                if m:
                    inner = m.group(1)
                    result = (
                        result[:m.start()]
                        + '\u201c' + inner + '\u201d'
                        + result[m.end():]
                    )
            elif '\u201c' in result:
                m = re.search(
                    r'\u201c([^\u201d]{1,200})\u201d', result,
                )
                if m:
                    inner = m.group(1)
                    result = (
                        result[:m.start()]
                        + '"' + inner + '"'
                        + result[m.end():]
                    )

        # 3. Vary ellipsis: "..." ↔ "…"
        if self.rng.random() < 0.3:
            if '...' in result:
                result = result.replace('...', '…', 1)
            elif '…' in result:
                result = result.replace('…', '...', 1)

        # 4. Oxford comma variation: ", and" ↔ " and"
        if self.rng.random() < self.jitter * 0.15:
            m = re.search(
                r',\s+and\s+(?=[a-z])', result, re.IGNORECASE,
            )
            if m and self.rng.random() < 0.5:
                result = (
                    result[:m.start()]
                    + ' and '
                    + result[m.end():]
                )

        # 5. Abbreviation variation: "e.g." ↔ "for example"
        if self.rng.random() < self.jitter * 0.12:
            abbrev_map = {
                'e.g.': 'for example',
                'i.e.': 'that is',
                'etc.': 'and so on',
            }
            for abbr, expanded in abbrev_map.items():
                if abbr in result.lower():
                    idx = result.lower().find(abbr)
                    orig = result[idx:idx + len(abbr)]
                    # Preserve capitalization at sentence start
                    repl = expanded
                    if orig[0].isupper():
                        repl = repl[0].upper() + repl[1:]
                    result = (
                        result[:idx] + repl + result[idx + len(orig):]
                    )
                    break

        # 6. Number formatting: "100" ↔ "one hundred"
        # (only for small numbers in prose)
        if self.rng.random() < self.jitter * 0.08:
            small_nums = {
                ' 2 ': ' two ', ' 3 ': ' three ',
                ' 4 ': ' four ', ' 5 ': ' five ',
                ' 10 ': ' ten ',
            }
            for num, word in small_nums.items():
                if num in result:
                    result = result.replace(num, word, 1)
                    break

        return result

    # ── Determinism fingerprint ───────────────────────────

    def text_fingerprint(self, text: str) -> str:
        """Compute a content fingerprint for the text.

        Can be used to verify the output is actually
        different across runs.
        """
        # Normalize for comparison
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(
            normalized.encode('utf-8'),
        ).hexdigest()[:16]

    def verify_diversity(
        self,
        outputs: list[str],
    ) -> dict[str, Any]:
        """Check that multiple outputs are diverse.

        Returns diversity metrics.
        """
        if len(outputs) < 2:
            return {
                "unique_ratio": 1.0,
                "fingerprints": [],
                "diverse": True,
            }

        fps = [self.text_fingerprint(o) for o in outputs]
        unique = len(set(fps))
        ratio = unique / len(fps)
        return {
            "unique_ratio": round(ratio, 3),
            "fingerprints": fps,
            "diverse": ratio > 0.5,
        }

# ── Convenience ───────────────────────────────────────────

def randomize_substitutions(
    substitutions: list[dict[str, Any]],
    *,
    jitter: float = 0.3,
) -> list[dict[str, Any]]:
    """Randomize a substitution plan."""
    return FingerprintRandomizer(
        jitter_level=jitter,
    ).randomize_plan(substitutions)

def diversify_text(
    text: str,
    *,
    jitter: float = 0.3,
) -> str:
    """Apply anti-fingerprint diversification."""
    r = FingerprintRandomizer(jitter_level=jitter)
    text = r.diversify_whitespace(text)
    text = r.diversify_output(text)
    return text
