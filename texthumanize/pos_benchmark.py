"""POS tagger benchmark — accuracy validation on gold-standard sentences.

Validates that :class:`~texthumanize.pos_tagger.POSTagger` achieves ≥93 %
accuracy on curated test corpora for each supported language (en, ru, uk, de).

The benchmark uses hand-tagged sentences that cover common grammatical
patterns: determiners, adjectives, nouns, verbs, adverbs, prepositions,
conjunctions, pronouns, numbers, and punctuation.

Usage:
    from texthumanize.pos_benchmark import run_benchmark, assert_accuracy

    # Run and print report
    report = run_benchmark()
    for lang, data in report.items():
        print(f"{lang}: {data['accuracy']:.1%}")

    # Assert thresholds (used in tests)
    assert_accuracy(min_accuracy=0.93)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from texthumanize.pos_tagger import (
    ADJ,
    ADV,
    CONJ,
    DET,
    NOUN,
    NUM,
    PART,
    PREP,
    PRON,
    PUNCT,
    VERB,
    POSTagger,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Gold-standard test corpora
# ═══════════════════════════════════════════════════════════════
# Each entry: (sentence_text, list_of_(word, expected_tag) tuples)
# Tags follow the universal tagset defined in pos_tagger.py.

GoldSentence = tuple[str, list[tuple[str, str]]]

_GOLD_EN: list[GoldSentence] = [
    (
        "The quick brown fox jumps over the lazy dog.",
        [
            ("The", DET), ("quick", ADJ), ("brown", ADJ),
            ("fox", NOUN), ("jumps", VERB), ("over", PREP),
            ("the", DET), ("lazy", ADJ), ("dog", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "She quickly ran to the store and bought some milk.",
        [
            ("She", PRON), ("quickly", ADV), ("ran", VERB),
            ("to", PREP), ("the", DET), ("store", NOUN),
            ("and", CONJ), ("bought", VERB), ("some", DET),
            ("milk", NOUN), (".", PUNCT),
        ],
    ),
    (
        "The beautiful garden was carefully maintained by the old gardener.",
        [
            ("The", DET), ("beautiful", ADJ), ("garden", NOUN),
            ("was", VERB), ("carefully", ADV), ("maintained", VERB),
            ("by", PREP), ("the", DET), ("old", ADJ),
            ("gardener", NOUN), (".", PUNCT),
        ],
    ),
    (
        "I have three large books on the wooden shelf.",
        [
            ("I", PRON), ("have", VERB), ("three", NUM),
            ("large", ADJ), ("books", NOUN), ("on", PREP),
            ("the", DET), ("wooden", ADJ), ("shelf", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "They will certainly enjoy this wonderful experience.",
        [
            ("They", PRON), ("will", VERB), ("certainly", ADV),
            ("enjoy", VERB), ("this", DET), ("wonderful", ADJ),
            ("experience", NOUN), (".", PUNCT),
        ],
    ),
    (
        "He slowly walked through the narrow passage.",
        [
            ("He", PRON), ("slowly", ADV), ("walked", VERB),
            ("through", PREP), ("the", DET), ("narrow", ADJ),
            ("passage", NOUN), (".", PUNCT),
        ],
    ),
    (
        "The children happily played in the park.",
        [
            ("The", DET), ("children", NOUN), ("happily", ADV),
            ("played", VERB), ("in", PREP), ("the", DET),
            ("park", NOUN), (".", PUNCT),
        ],
    ),
    (
        "My older brother is an excellent swimmer.",
        [
            ("My", DET), ("older", ADJ), ("brother", NOUN),
            ("is", VERB), ("an", DET), ("excellent", ADJ),
            ("swimmer", NOUN), (".", PUNCT),
        ],
    ),
    (
        "We should probably leave before the storm arrives.",
        [
            ("We", PRON), ("should", VERB), ("probably", ADV),
            ("leave", VERB), ("before", PREP), ("the", DET),
            ("storm", NOUN), ("arrives", VERB), (".", PUNCT),
        ],
    ),
    (
        "The cat sat on the mat and purred softly.",
        [
            ("The", DET), ("cat", NOUN), ("sat", VERB),
            ("on", PREP), ("the", DET), ("mat", NOUN),
            ("and", CONJ), ("purred", VERB), ("softly", ADV),
            (".", PUNCT),
        ],
    ),
    (
        "Running is a very popular activity among young adults.",
        [
            ("Running", VERB), ("is", VERB), ("a", DET),
            ("very", ADV), ("popular", ADJ), ("activity", NOUN),
            ("among", PREP), ("young", ADJ), ("adults", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "The new policy significantly improved employee satisfaction.",
        [
            ("The", DET), ("new", ADJ), ("policy", NOUN),
            ("significantly", ADV), ("improved", VERB),
            ("employee", NOUN), ("satisfaction", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "However, the results were not entirely conclusive.",
        [
            ("However", ADV), (",", PUNCT), ("the", DET),
            ("results", NOUN), ("were", VERB), ("not", ADV),
            ("entirely", ADV), ("conclusive", ADJ), (".", PUNCT),
        ],
    ),
    (
        "Five students submitted their assignments on time.",
        [
            ("Five", NUM), ("students", NOUN), ("submitted", VERB),
            ("their", DET), ("assignments", NOUN), ("on", PREP),
            ("time", NOUN), (".", PUNCT),
        ],
    ),
    (
        "It seems incredibly difficult to understand this concept.",
        [
            ("It", PRON), ("seems", VERB), ("incredibly", ADV),
            ("difficult", ADJ), ("to", PREP), ("understand", VERB),
            ("this", DET), ("concept", NOUN), (".", PUNCT),
        ],
    ),
]

_GOLD_RU: list[GoldSentence] = [
    (
        "Быстрая коричневая лиса прыгает через забор.",
        [
            ("Быстрая", ADJ), ("коричневая", ADJ), ("лиса", NOUN),
            ("прыгает", VERB), ("через", PREP), ("забор", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "Она быстро побежала в магазин.",
        [
            ("Она", PRON), ("быстро", ADV), ("побежала", VERB),
            ("в", PREP), ("магазин", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Красивый сад был тщательно ухожен старым садовником.",
        [
            ("Красивый", ADJ), ("сад", NOUN), ("был", VERB),
            ("тщательно", ADV), ("ухожен", VERB), ("старым", ADJ),
            ("садовником", NOUN), (".", PUNCT),
        ],
    ),
    (
        "У меня есть три большие книги на полке.",
        [
            ("У", PREP), ("меня", PRON), ("есть", VERB),
            ("три", NUM), ("большие", ADJ), ("книги", NOUN),
            ("на", PREP), ("полке", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Дети радостно играли в парке.",
        [
            ("Дети", NOUN), ("радостно", ADV), ("играли", VERB),
            ("в", PREP), ("парке", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Мой старший брат хорошо плавает.",
        [
            ("Мой", DET), ("старший", ADJ), ("брат", NOUN),
            ("хорошо", ADV), ("плавает", VERB), (".", PUNCT),
        ],
    ),
    (
        "Новая политика существенно повысила удовлетворённость.",
        [
            ("Новая", ADJ), ("политика", NOUN), ("существенно", ADV),
            ("повысила", VERB), ("удовлетворённость", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "Однако результаты были не совсем убедительны.",
        [
            ("Однако", CONJ), ("результаты", NOUN), ("были", VERB),
            ("не", PART), ("совсем", ADV), ("убедительны", ADJ),
            (".", PUNCT),
        ],
    ),
    (
        "Студенты сдали работы вовремя.",
        [
            ("Студенты", NOUN), ("сдали", VERB), ("работы", NOUN),
            ("вовремя", ADV), (".", PUNCT),
        ],
    ),
    (
        "Он медленно шёл по узкому коридору.",
        [
            ("Он", PRON), ("медленно", ADV), ("шёл", VERB),
            ("по", PREP), ("узкому", ADJ), ("коридору", NOUN),
            (".", PUNCT),
        ],
    ),
]

_GOLD_UK: list[GoldSentence] = [
    (
        "Швидка коричнева лисиця стрибає через паркан.",
        [
            ("Швидка", ADJ), ("коричнева", ADJ), ("лисиця", NOUN),
            ("стрибає", VERB), ("через", PREP), ("паркан", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "Вона швидко побігла до магазину.",
        [
            ("Вона", PRON), ("швидко", ADV), ("побігла", VERB),
            ("до", PREP), ("магазину", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Красивий сад був ретельно доглянутий.",
        [
            ("Красивий", ADJ), ("сад", NOUN), ("був", VERB),
            ("ретельно", ADV), ("доглянутий", ADJ),
            (".", PUNCT),
        ],
    ),
    (
        "Діти радісно грали у парку.",
        [
            ("Діти", NOUN), ("радісно", ADV), ("грали", VERB),
            ("у", PREP), ("парку", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Мій старший брат добре плаває.",
        [
            ("Мій", DET), ("старший", ADJ), ("брат", NOUN),
            ("добре", ADV), ("плаває", VERB), (".", PUNCT),
        ],
    ),
    (
        "Нова політика суттєво підвищила задоволеність.",
        [
            ("Нова", ADJ), ("політика", NOUN), ("суттєво", ADV),
            ("підвищила", VERB), ("задоволеність", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "Однак результати були не зовсім переконливі.",
        [
            ("Однак", CONJ), ("результати", NOUN), ("були", VERB),
            ("не", PART), ("зовсім", ADV), ("переконливі", ADJ),
            (".", PUNCT),
        ],
    ),
    (
        "Студенти здали роботи вчасно.",
        [
            ("Студенти", NOUN), ("здали", VERB), ("роботи", NOUN),
            ("вчасно", ADV), (".", PUNCT),
        ],
    ),
]

_GOLD_DE: list[GoldSentence] = [
    (
        "Der schnelle braune Fuchs springt über den Zaun.",
        [
            ("Der", DET), ("schnelle", ADJ), ("braune", ADJ),
            ("Fuchs", NOUN), ("springt", VERB), ("über", PREP),
            ("den", DET), ("Zaun", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Sie lief schnell zum Laden.",
        [
            ("Sie", PRON), ("lief", VERB), ("schnell", ADV),
            ("zum", PREP), ("Laden", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Der schöne Garten wurde sorgfältig gepflegt.",
        [
            ("Der", DET), ("schöne", ADJ), ("Garten", NOUN),
            ("wurde", VERB), ("sorgfältig", ADV), ("gepflegt", VERB),
            (".", PUNCT),
        ],
    ),
    (
        "Die Kinder spielten fröhlich im Park.",
        [
            ("Die", DET), ("Kinder", NOUN), ("spielten", VERB),
            ("fröhlich", ADV), ("im", PREP), ("Park", NOUN),
            (".", PUNCT),
        ],
    ),
    (
        "Mein älterer Bruder ist ein guter Schwimmer.",
        [
            ("Mein", DET), ("älterer", ADJ), ("Bruder", NOUN),
            ("ist", VERB), ("ein", DET), ("guter", ADJ),
            ("Schwimmer", NOUN), (".", PUNCT),
        ],
    ),
    (
        "Die neue Politik verbesserte die Zufriedenheit erheblich.",
        [
            ("Die", DET), ("neue", ADJ), ("Politik", NOUN),
            ("verbesserte", VERB), ("die", DET),
            ("Zufriedenheit", NOUN), ("erheblich", ADV),
            (".", PUNCT),
        ],
    ),
]

_GOLD_CORPORA: dict[str, list[GoldSentence]] = {
    "en": _GOLD_EN,
    "ru": _GOLD_RU,
    "uk": _GOLD_UK,
    "de": _GOLD_DE,
}


# ═══════════════════════════════════════════════════════════════
#  Benchmark result dataclasses
# ═══════════════════════════════════════════════════════════════


@dataclass
class ConfusionEntry:
    """Single confusion: expected tag was X, got Y."""
    word: str
    expected: str
    predicted: str
    sentence: str


@dataclass
class LangBenchmarkResult:
    """Benchmark result for one language."""
    lang: str
    total: int
    correct: int
    accuracy: float
    confusions: list[ConfusionEntry] = field(default_factory=list)
    per_tag_accuracy: dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Full benchmark report across all languages."""
    results: dict[str, LangBenchmarkResult] = field(default_factory=dict)
    overall_accuracy: float = 0.0
    overall_total: int = 0
    overall_correct: int = 0


# ═══════════════════════════════════════════════════════════════
#  Benchmark runner
# ═══════════════════════════════════════════════════════════════


def run_benchmark(
    languages: Optional[list[str]] = None,
    verbose: bool = False,
) -> BenchmarkReport:
    """Run POS tagger benchmark on gold-standard corpora.

    Args:
        languages: Language codes to test (default: all available)
        verbose: If True, log individual mismatches

    Returns:
        BenchmarkReport with detailed accuracy metrics
    """
    if languages is None:
        languages = list(_GOLD_CORPORA.keys())

    report = BenchmarkReport()
    total_all = 0
    correct_all = 0

    for lang in languages:
        gold = _GOLD_CORPORA.get(lang)
        if not gold:
            logger.warning("No gold corpus for language '%s'", lang)
            continue

        tagger = POSTagger(lang=lang)
        total = 0
        correct = 0
        confusions: list[ConfusionEntry] = []
        tag_correct: dict[str, int] = {}
        tag_total: dict[str, int] = {}

        for sentence_text, expected_tags in gold:
            predicted = tagger.tag(sentence_text)

            # Align by token text
            pred_map = {word: tag for word, tag in predicted}

            for exp_word, exp_tag in expected_tags:
                total += 1
                tag_total[exp_tag] = tag_total.get(exp_tag, 0) + 1

                pred_tag = pred_map.get(exp_word)
                if pred_tag is None:
                    # Try case-insensitive
                    for pw, pt in predicted:
                        if pw.lower() == exp_word.lower():
                            pred_tag = pt
                            break

                if pred_tag == exp_tag:
                    correct += 1
                    tag_correct[exp_tag] = tag_correct.get(exp_tag, 0) + 1
                else:
                    confusion = ConfusionEntry(
                        word=exp_word,
                        expected=exp_tag,
                        predicted=pred_tag or "MISSING",
                        sentence=sentence_text,
                    )
                    confusions.append(confusion)
                    if verbose:
                        logger.info(
                            "[%s] '%s': expected %s, got %s -- '%s'",
                            lang, exp_word, exp_tag,
                            pred_tag or "MISSING", sentence_text,
                        )

        accuracy = correct / total if total > 0 else 0.0

        # Per-tag accuracy
        per_tag: dict[str, float] = {}
        for tag in tag_total:
            tc = tag_correct.get(tag, 0)
            tt = tag_total[tag]
            per_tag[tag] = tc / tt if tt > 0 else 0.0

        result = LangBenchmarkResult(
            lang=lang,
            total=total,
            correct=correct,
            accuracy=accuracy,
            confusions=confusions,
            per_tag_accuracy=per_tag,
        )
        report.results[lang] = result

        total_all += total
        correct_all += correct

        logger.info(
            "POS benchmark [%s]: %d/%d = %.1f%% (%d mismatches)",
            lang, correct, total, accuracy * 100, len(confusions),
        )

    report.overall_total = total_all
    report.overall_correct = correct_all
    report.overall_accuracy = correct_all / total_all if total_all > 0 else 0.0

    return report


def assert_accuracy(
    min_accuracy: float = 0.93,
    languages: Optional[list[str]] = None,
) -> BenchmarkReport:
    """Run benchmark and assert minimum accuracy threshold.

    Args:
        min_accuracy: Minimum acceptable accuracy (0.0-1.0)
        languages: Languages to test (default: all)

    Returns:
        BenchmarkReport

    Raises:
        POSBenchmarkError: If overall accuracy is below threshold
    """
    report = run_benchmark(languages=languages, verbose=True)

    if report.overall_accuracy < min_accuracy:
        # Build detailed error message
        lines = [
            f"POS tagger accuracy {report.overall_accuracy:.1%} "
            f"is below threshold {min_accuracy:.1%}",
            "",
        ]
        for lang, result in report.results.items():
            lines.append(
                f"  {lang}: {result.accuracy:.1%} "
                f"({result.correct}/{result.total})"
            )
            for conf in result.confusions[:5]:
                lines.append(
                    f"    ✗ '{conf.word}': "
                    f"expected {conf.expected}, got {conf.predicted}"
                )

        raise POSBenchmarkError("\n".join(lines))

    return report


def format_report(report: BenchmarkReport) -> str:
    """Format benchmark report as a readable string.

    Args:
        report: BenchmarkReport from run_benchmark()

    Returns:
        Multi-line formatted string
    """
    lines = [
        "=" * 60,
        "POS Tagger Benchmark Report",
        "=" * 60,
        "",
        f"Overall: {report.overall_accuracy:.1%} "
        f"({report.overall_correct}/{report.overall_total})",
        "",
    ]

    for lang, result in sorted(report.results.items()):
        lines.append(f"─── {lang.upper()} ───")
        lines.append(
            f"  Accuracy: {result.accuracy:.1%} "
            f"({result.correct}/{result.total})"
        )

        # Per-tag accuracy
        if result.per_tag_accuracy:
            lines.append("  Per-tag accuracy:")
            for tag in sorted(result.per_tag_accuracy):
                acc = result.per_tag_accuracy[tag]
                lines.append(f"    {tag:8s}: {acc:.1%}")

        # Mismatches
        if result.confusions:
            lines.append(f"  Mismatches ({len(result.confusions)}):")
            for conf in result.confusions:
                lines.append(
                    f"    '{conf.word}': "
                    f"{conf.expected} → {conf.predicted}"
                )
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


class POSBenchmarkError(Exception):
    """Raised when benchmark accuracy is below threshold."""

