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
import random
import re
from typing import Any


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

        Randomly adds/removes trailing spaces before newlines,
        varies paragraph spacing.
        """
        if self.jitter < 0.1:
            return text

        lines = text.split('\n')
        result = []

        for line in lines:
            # Random trailing space removal / addition
            line = line.rstrip()

            # Occasionally add soft variation
            if (
                self.rng.random() < self.jitter * 0.15
                and line
                and not line.endswith((' ', '\t'))
            ):
                # Variation: sometimes no change, sometimes
                # add invisible zero-width space (optional)
                pass  # Keep clean for now

            result.append(line)

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
        - Vary quote styles occasionally
        - Optional Unicode normalization differences
        """
        if self.jitter < 0.1:
            return text

        result = text

        # Randomly swap some em-dashes ↔ en-dashes
        if '—' in result and self.rng.random() < 0.2:
            dashes = list(
                re.finditer(r'—', result),
            )
            if dashes:
                pick = self.rng.choice(dashes)
                result = (
                    result[:pick.start()]
                    + ' — '
                    + result[pick.end():]
                )

        # Randomly swap straight/curly quotes (subtle)
        if '"' in result and self.rng.random() < 0.15:
            # Replace one pair of straight quotes with curly
            m = re.search(r'"([^"]{1,100})"', result)
            if m:
                inner = m.group(1)
                result = (
                    result[:m.start()]
                    + '\u201c' + inner + '\u201d'
                    + result[m.end():]
                )

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
