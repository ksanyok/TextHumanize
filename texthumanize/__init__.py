"""TextHumanize — алгоритмическая гуманизация текста.

Преобразует автоматически сгенерированные тексты в естественные: нормализует типографику,
устраняет канцеляризмы, разнообразит структуру, повышает burstiness и perplexity.

Полные словари: RU, UK, EN, DE, FR, ES, PL, PT, IT.
Универсальный процессор: любой язык.
Профили: chat, web, seo, docs, formal.

Использование:
    >>> from texthumanize import humanize, analyze, explain
    >>> result = humanize("Данный текст является примером.", lang="ru")
    >>> print(result.text)
"""

__version__ = "0.3.0"
__author__ = "TextHumanize Contributors"
__license__ = "Personal Use Only"

from texthumanize.core import humanize, analyze, explain, humanize_chunked
from texthumanize.pipeline import Pipeline
from texthumanize.utils import HumanizeOptions, HumanizeResult, AnalysisReport

__all__ = [
    "humanize",
    "humanize_chunked",
    "analyze",
    "explain",
    "Pipeline",
    "HumanizeOptions",
    "HumanizeResult",
    "AnalysisReport",
    "__version__",
]
