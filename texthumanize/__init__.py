"""TextHumanize — алгоритмическая гуманизация текста с антидетекцией.

Делает AI-тексты необнаружимыми для детекторов (GPTZero, Originality.ai, ZeroGPT,
Turnitin, Copyleaks): нормализует типографику, устраняет канцеляризмы,
разнообразит структуру, повышает burstiness и perplexity.

Полные словари: RU, UK, EN, DE, FR, ES, PL, PT, IT.
Универсальный процессор: любой язык.
Профили: chat, web, seo, docs, formal.

Использование:
    >>> from texthumanize import humanize, analyze, explain
    >>> result = humanize("Данный текст является примером.", lang="ru")
    >>> print(result.text)
"""

__version__ = "0.2.0"
__author__ = "TextHumanize Contributors"
__license__ = "MIT"

from texthumanize.core import humanize, analyze, explain
from texthumanize.utils import HumanizeOptions, HumanizeResult, AnalysisReport

__all__ = [
    "humanize",
    "analyze",
    "explain",
    "HumanizeOptions",
    "HumanizeResult",
    "AnalysisReport",
    "__version__",
]
