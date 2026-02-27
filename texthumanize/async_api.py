"""TextHumanize Async API — async/await wrappers for asyncio/FastAPI.

Provides non-blocking versions of core functions by running them
in a thread pool executor. Zero additional dependencies.

Usage:
    >>> import asyncio
    >>> from texthumanize import async_humanize, async_detect_ai
    >>>
    >>> async def main():
    ...     result = await async_humanize("Text here.", lang="en")
    ...     print(result.text)
    ...     ai = await async_detect_ai("Check this.", lang="en")
    ...     print(ai["verdict"])
    >>>
    >>> asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from texthumanize.utils import AnalysisReport, HumanizeResult

logger = logging.getLogger(__name__)


async def _run_in_executor(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Run a sync function in the default thread pool executor."""
    loop = asyncio.get_running_loop()
    partial = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, partial)


async def async_humanize(
    text: str,
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    preserve: dict | None = None,
    constraints: dict | None = None,
    seed: int | None = None,
    target_style: object | str | None = None,
    only_flagged: bool = False,
    custom_dict: dict[str, str | list[str]] | None = None,
) -> HumanizeResult:
    """Async version of humanize().

    Runs the synchronous humanize() in a thread pool executor,
    making it safe to use in async frameworks like FastAPI.

    Args:
        Same as humanize().

    Returns:
        HumanizeResult — same as humanize().
    """
    from texthumanize.core import humanize

    return cast("HumanizeResult", await _run_in_executor(
        humanize,
        text,
        lang=lang,
        profile=profile,
        intensity=intensity,
        preserve=preserve,
        constraints=constraints,
        seed=seed,
        target_style=target_style,
        only_flagged=only_flagged,
        custom_dict=custom_dict,
    ))


async def async_detect_ai(
    text: str,
    lang: str = "auto",
) -> dict:
    """Async version of detect_ai().

    Args:
        text: Text to check for AI generation.
        lang: Language code ('auto' for auto-detection).

    Returns:
        dict with score, verdict, confidence, metrics.
    """
    from texthumanize.core import detect_ai

    return cast(dict, await _run_in_executor(detect_ai, text, lang=lang))  # type: ignore[type-arg]


async def async_analyze(
    text: str,
    lang: str = "auto",
) -> AnalysisReport:
    """Async version of analyze().

    Args:
        text: Text to analyze.
        lang: Language code.

    Returns:
        AnalysisReport.
    """
    from texthumanize.core import analyze

    return cast("AnalysisReport", await _run_in_executor(analyze, text, lang=lang))


async def async_paraphrase(
    text: str,
    lang: str = "auto",
    intensity: int = 60,
    seed: int | None = None,
) -> str:
    """Async version of paraphrase().

    Args:
        text: Text to paraphrase.
        lang: Language code.
        intensity: Processing intensity 0-100.
        seed: Random seed.

    Returns:
        Paraphrased text string.
    """
    from texthumanize.core import paraphrase

    return cast(str, await _run_in_executor(
        paraphrase, text, lang=lang, intensity=intensity, seed=seed,
    ))


async def async_humanize_batch(
    texts: list[str],
    lang: str = "auto",
    profile: str = "web",
    intensity: int = 60,
    max_workers: int = 4,
    seed: int | None = None,
) -> list[HumanizeResult]:
    """Async version of humanize_batch().

    For true async parallelism, consider using asyncio.gather()
    with multiple async_humanize() calls instead.

    Args:
        texts: List of texts to process.
        lang: Language code.
        profile: Processing profile.
        intensity: Processing intensity.
        max_workers: Thread pool size (for sync batch).
        seed: Random seed.

    Returns:
        List of HumanizeResult objects.
    """
    from texthumanize.core import humanize_batch

    return cast(list, await _run_in_executor(
        humanize_batch,
        texts,
        lang=lang,
        profile=profile,
        intensity=intensity,
        max_workers=max_workers,
        seed=seed,
    ))  # type: ignore[return-value]


async def async_detect_ai_batch(
    texts: list[str],
    lang: str = "auto",
) -> list[dict]:
    """Async version of detect_ai_batch().

    Args:
        texts: List of texts to check.
        lang: Language code.

    Returns:
        List of detection result dicts.
    """
    from texthumanize.core import detect_ai_batch

    return cast(list, await _run_in_executor(detect_ai_batch, texts, lang=lang))  # type: ignore[return-value]
