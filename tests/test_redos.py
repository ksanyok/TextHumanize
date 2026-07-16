"""Adversarial regex regression tests."""

from __future__ import annotations

import random
import sys
import time

from texthumanize.paraphrase_engine import ParaphraseEngine
from texthumanize.segmenter import Segmenter
from texthumanize.sentence_restructurer import _front_adverbial_clause
from texthumanize.sentence_validator import SentenceValidator


def _elapsed_seconds(fn) -> float:
    started = time.perf_counter()
    fn()
    return time.perf_counter() - started


def _budget(seconds: float) -> float:
    """A wall-clock ReDoS ceiling, scaled up under instrumentation.

    Coverage / debugger tracing (``sys.gettrace()`` non-None) slows execution
    by roughly an order of magnitude, which spuriously trips a tight fixed
    budget. True catastrophic backtracking is *exponential*, so it still
    blows past the scaled ceiling — the guard stays meaningful while the
    coverage gate stays reliable.
    """
    instrumented = sys.gettrace() is not None or "coverage" in sys.modules
    return seconds * 30.0 if instrumented else seconds


def test_segmenter_handles_unclosed_html_without_regex_blowup() -> None:
    tag_count = 3_000
    text = "<script>" + ("<script>" * tag_count) + ("x" * 3_000)

    segmenter = Segmenter()
    elapsed = _elapsed_seconds(lambda: segmenter.segment(text))
    segmented = segmenter.segment(text)

    assert elapsed < _budget(1.0)
    assert len(segmented.segments) >= tag_count
    assert segmented.restore(segmented.text) == text


def test_segmenter_still_protects_valid_html_block_as_single_segment() -> None:
    text = "<script>" + ("const value = 1;\n" * 100) + "</script>"

    segmented = Segmenter().segment(text)

    assert len(segmented.segments) == 1
    assert segmented.segments[0].kind == "html_block"
    assert segmented.restore(segmented.text) == text


def test_sentence_regex_transforms_bound_adversarial_non_matches() -> None:
    validator = SentenceValidator("en")
    paraphraser = ParaphraseEngine(lang="en")
    long_connector_chain = ("and " * 3_000) + "x"
    long_no_connector_sentence = ("A" * 50_000) + "."
    long_perspective_noise = (("A " * 20_000).strip()) + "."

    elapsed = _elapsed_seconds(
        lambda: (
            validator.validate(long_connector_chain, long_connector_chain),
            _front_adverbial_clause(long_no_connector_sentence, "en", random.Random(1)),
            paraphraser._rotate_perspective(long_perspective_noise),
        )
    )

    assert elapsed < _budget(1.0)
