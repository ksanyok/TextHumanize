"""Тональный анализатор и регулятор стиля.

Определяет тон текста (формальный, нейтральный, дружелюбный,
академический, маркетинговый, разговорный) и может корректировать его.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ToneLevel(Enum):
    """Уровни тональности."""
    FORMAL = "formal"
    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    MARKETING = "marketing"


@dataclass
class ToneReport:
    """Результат тонального анализа."""

    primary_tone: ToneLevel = ToneLevel.NEUTRAL
    scores: dict[str, float] = field(default_factory=dict)
    formality: float = 0.5  # 0=разговорный, 1=формальный
    subjectivity: float = 0.5  # 0=объективный, 1=субъективный
    confidence: float = 0.0
    markers: dict[str, list[str]] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
#  МАРКЕРЫ ФОРМАЛЬНОСТИ
# ═══════════════════════════════════════════════════════════════

_FORMAL_MARKERS = {
    "en": {
        "very_formal": [
            "herein", "thereof", "whereby", "aforementioned", "notwithstanding",
            "pursuant", "hereunder", "hitherto", "therein", "theretofore",
            "inasmuch", "heretofore", "whomsoever", "insofar",
        ],
        "formal": [
            "consequently", "furthermore", "moreover", "nevertheless",
            "accordingly", "subsequently", "pertaining", "regarding",
            "concerning", "facilitate", "commence", "endeavor",
            "implement", "utilize", "constitute", "demonstrate",
            "establish", "incorporate", "subsequent", "prior to",
            "in accordance with", "with respect to", "in regard to",
        ],
        "informal": [
            "gonna", "wanna", "gotta", "kinda", "sorta", "dunno",
            "yeah", "yep", "nope", "hey", "oh", "wow", "huh",
            "ok", "okay", "stuff", "thing", "things", "like",
            "basically", "literally", "actually", "pretty",
            "awesome", "cool", "super", "totally", "honestly",
            "damn", "hell", "crap", "mess", "weird", "crazy",
        ],
        "subjective": [
            "i think", "i believe", "in my opinion", "i feel",
            "it seems", "perhaps", "maybe", "probably", "possibly",
            "hopefully", "unfortunately", "surprisingly", "obviously",
            "clearly", "certainly", "definitely", "absolutely",
            "amazing", "terrible", "wonderful", "horrible",
            "fantastic", "awful", "brilliant", "stunning",
        ],
        "academic": [
            "hypothesis", "methodology", "paradigm", "empirical",
            "theoretical", "significant", "correlation", "variables",
            "findings", "literature", "framework", "furthermore",
            "et al", "cf.", "ibid", "viz.", "i.e.", "e.g.",
            "in contrast", "on the other hand", "taken together",
            "it is worth noting", "it should be noted",
        ],
        "marketing": [
            "revolutionary", "exclusive", "premium", "innovative",
            "best-in-class", "cutting-edge", "world-class", "unique",
            "limited", "free", "guaranteed", "proven", "powerful",
            "effortless", "seamless", "transform", "unlock",
            "supercharge", "game-changing", "breakthrough", "ultimate",
            "discover", "unleash", "skyrocket", "maximize",
        ],
    },
    "ru": {
        "very_formal": [
            "нижеследующий", "вышеизложенный", "нижеуказанный",
            "сим", "настоящим", "надлежащий", "оный",
            "таковой", "каковой", "коего", "сего",
        ],
        "formal": [
            "осуществлять", "обеспечивать", "предусматривать",
            "регламентировать", "следовательно", "вследствие",
            "в соответствии с", "ввиду", "касательно", "относительно",
            "содействовать", "способствовать", "являться",
            "представлять собой", "в рамках", "в целях",
        ],
        "informal": [
            "прям", "щас", "типа", "короче", "ваще", "блин",
            "фигня", "норм", "ок", "лол", "чё", "ну",
            "вообще-то", "кстати", "кароче", "прикольно",
            "классно", "круто", "фигово", "реально", "жесть",
        ],
        "subjective": [
            "я думаю", "я считаю", "по-моему", "мне кажется",
            "наверное", "возможно", "может быть", "вероятно",
            "к сожалению", "к счастью", "очевидно", "безусловно",
            "конечно", "определённо", "несомненно",
            "потрясающий", "ужасный", "замечательный", "отвратительный",
        ],
        "academic": [
            "гипотеза", "методология", "парадигма", "эмпирический",
            "теоретический", "корреляция", "переменная", "детерминант",
            "результаты", "рассмотрим", "анализ показывает",
            "следует отметить", "необходимо подчеркнуть",
        ],
    },
    "uk": {
        "formal": [
            "здійснювати", "забезпечувати", "передбачати",
            "регламентувати", "отже", "внаслідок",
            "відповідно до", "зважаючи на", "стосовно",
            "сприяти", "являти собою", "в межах", "з метою",
        ],
        "informal": [
            "типу", "короче", "взагалі", "блін", "фігня",
            "норм", "ок", "ну", "до речі", "класно",
            "круто", "реально",
        ],
        "subjective": [
            "я думаю", "я вважаю", "на мою думку", "мені здається",
            "мабуть", "можливо", "напевно", "безумовно",
            "на жаль", "на щастя", "очевидно",
        ],
    },
    "de": {
        "formal": [
            "durchführen", "bereitstellen", "gewährleisten",
            "implementieren", "diesbezüglich", "dementsprechend",
            "folglich", "infolgedessen", "hinsichtlich",
            "gemäß", "entsprechend", "darüber hinaus",
        ],
        "informal": [
            "halt", "eben", "quasi", "irgendwie", "sozusagen",
            "krass", "geil", "cool", "mega", "voll",
            "echt", "total", "na ja", "also",
        ],
        "subjective": [
            "ich denke", "ich glaube", "meiner meinung nach",
            "wahrscheinlich", "vielleicht", "möglicherweise",
            "offensichtlich", "leider", "glücklicherweise",
        ],
    },
    "fr": {
        "formal": [
            "effectuer", "mettre en œuvre", "conformément",
            "en conséquence", "néanmoins", "toutefois",
            "préalablement", "notamment", "en ce qui concerne",
            "afin de", "dans le cadre de", "à cet égard",
        ],
        "informal": [
            "genre", "carrément", "trop", "vachement", "bof",
            "ouais", "ben", "bah", "quoi", "du coup",
            "franchement", "grave", "en mode", "kiffer",
        ],
        "subjective": [
            "je pense", "je crois", "à mon avis",
            "probablement", "peut-être", "évidemment",
            "malheureusement", "heureusement", "apparemment",
        ],
    },
    "es": {
        "formal": [
            "realizar", "implementar", "conforme a",
            "en consecuencia", "no obstante", "sin embargo",
            "previamente", "asimismo", "en lo que respecta",
            "con el fin de", "en el marco de", "al respecto",
        ],
        "informal": [
            "mola", "flipar", "currar", "tío", "chaval",
            "guay", "vale", "bueno", "pues", "o sea",
            "es que", "la verdad", "en plan", "mogollón",
        ],
        "subjective": [
            "creo que", "pienso que", "en mi opinión",
            "probablemente", "quizás", "tal vez",
            "obviamente", "desafortunadamente", "afortunadamente",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
#  ЗАМЕНЫ ДЛЯ КОРРЕКЦИИ ТОНАЛЬНОСТИ
# ═══════════════════════════════════════════════════════════════

_TONE_REPLACEMENTS = {
    "en": {
        # informal → formal
        ("informal", "formal"): {
            "get": "obtain", "buy": "purchase", "ask": "inquire",
            "help": "assist", "start": "commence", "end": "conclude",
            "big": "significant", "good": "favorable", "bad": "unfavorable",
            "show": "demonstrate", "need": "require", "try": "attempt",
            "find out": "determine", "set up": "establish",
            "look at": "examine", "think about": "consider",
            "put off": "postpone", "come up with": "devise",
            "deal with": "address", "go up": "increase",
            "go down": "decrease", "talk about": "discuss",
        },
        # formal → informal
        ("formal", "informal"): {
            "obtain": "get", "purchase": "buy", "inquire": "ask",
            "assist": "help", "commence": "start", "conclude": "end",
            "demonstrate": "show", "require": "need", "attempt": "try",
            "determine": "find out", "establish": "set up",
            "examine": "look at", "consider": "think about",
            "postpone": "put off", "devise": "come up with",
            "address": "deal with", "utilize": "use",
            "facilitate": "help with", "implement": "do",
        },
    },
    "ru": {
        ("informal", "formal"): {
            "делать": "осуществлять", "начать": "приступить",
            "показать": "продемонстрировать", "нужно": "необходимо",
            "помочь": "оказать содействие", "думать": "полагать",
            "сделать": "выполнить", "большой": "значительный",
            "хороший": "надлежащий", "плохой": "неудовлетворительный",
        },
        ("formal", "informal"): {
            "осуществлять": "делать", "обеспечивать": "давать",
            "необходимо": "нужно", "полагать": "думать",
            "содействовать": "помогать", "являться": "быть",
            "представлять собой": "быть", "в целях": "чтобы",
            "в рамках": "в", "вследствие": "из-за",
        },
    },
    "uk": {
        ("informal", "formal"): {
            "робити": "здійснювати", "почати": "розпочати",
            "показати": "продемонструвати", "треба": "необхідно",
            "допомогти": "сприяти", "думати": "вважати",
            "зробити": "виконати", "великий": "значний",
            "гарний": "належний", "поганий": "незадовільний",
            "дати": "надати", "сказати": "зазначити",
        },
        ("formal", "informal"): {
            "здійснювати": "робити", "забезпечувати": "давати",
            "необхідно": "треба", "вважати": "думати",
            "сприяти": "допомагати", "являти собою": "бути",
            "з метою": "щоб", "в межах": "в",
            "внаслідок": "через", "передбачати": "планувати",
        },
    },
    "de": {
        ("informal", "formal"): {
            "machen": "durchführen", "anfangen": "beginnen",
            "zeigen": "demonstrieren", "brauchen": "benötigen",
            "helfen": "unterstützen", "denken": "erwägen",
            "kriegen": "erhalten", "kaufen": "erwerben",
            "sagen": "mitteilen", "fragen": "erkundigen",
            "gucken": "betrachten", "echt": "tatsächlich",
        },
        ("formal", "informal"): {
            "durchführen": "machen", "bereitstellen": "geben",
            "benötigen": "brauchen", "erwägen": "denken",
            "unterstützen": "helfen", "darstellen": "sein",
            "erhalten": "kriegen", "erwerben": "kaufen",
            "mitteilen": "sagen", "betrachten": "gucken",
            "implementieren": "umsetzen", "gewährleisten": "sicherstellen",
        },
    },
    "fr": {
        ("informal", "formal"): {
            "faire": "effectuer", "commencer": "débuter",
            "montrer": "démontrer", "aider": "assister",
            "penser": "considérer", "acheter": "acquérir",
            "demander": "solliciter", "regarder": "examiner",
            "trouver": "identifier", "dire": "indiquer",
            "parler": "communiquer", "essayer": "tenter",
        },
        ("formal", "informal"): {
            "effectuer": "faire", "débuter": "commencer",
            "démontrer": "montrer", "assister": "aider",
            "considérer": "penser", "acquérir": "acheter",
            "solliciter": "demander", "examiner": "regarder",
            "identifier": "trouver", "indiquer": "dire",
            "mettre en œuvre": "faire", "faciliter": "aider",
        },
    },
    "es": {
        ("informal", "formal"): {
            "hacer": "realizar", "empezar": "iniciar",
            "mostrar": "demostrar", "ayudar": "asistir",
            "pensar": "considerar", "comprar": "adquirir",
            "pedir": "solicitar", "mirar": "examinar",
            "buscar": "identificar", "decir": "indicar",
            "hablar": "comunicar", "intentar": "procurar",
        },
        ("formal", "informal"): {
            "realizar": "hacer", "iniciar": "empezar",
            "demostrar": "mostrar", "asistir": "ayudar",
            "considerar": "pensar", "adquirir": "comprar",
            "solicitar": "pedir", "examinar": "mirar",
            "identificar": "buscar", "indicar": "decir",
            "implementar": "hacer", "facilitar": "ayudar",
        },
    },
}


class ToneAnalyzer:
    """Анализатор тональности текста."""

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._markers = _FORMAL_MARKERS.get(lang, _FORMAL_MARKERS.get("en", {}))

    def analyze(self, text: str) -> ToneReport:
        """Анализ тональности текста.

        Args:
            text: Текст для анализа.

        Returns:
            ToneReport с подробным разбором.
        """
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        word_count = len(words)

        if word_count < 5:
            return ToneReport()

        report = ToneReport()

        # Подсчёт маркеров каждой категории
        category_counts: dict[str, int] = {}
        category_found: dict[str, list[str]] = {}

        for category, marker_list in self._markers.items():
            count = 0
            found: list[str] = []
            for marker in marker_list:
                occurrences = text_lower.count(marker)
                if occurrences > 0:
                    count += occurrences
                    found.append(marker)
            category_counts[category] = count
            category_found[category] = found

        report.markers = category_found

        # ─── Формальность ───
        formal_score = (
            category_counts.get("very_formal", 0) * 3 +
            category_counts.get("formal", 0) * 2 +
            category_counts.get("academic", 0) * 2
        )
        informal_score = category_counts.get("informal", 0) * 2

        total_markers = formal_score + informal_score + 1
        report.formality = formal_score / total_markers

        # Дополнительные сигналы формальности
        # Средняя длина слова
        avg_word_len = sum(len(w) for w in words) / word_count
        if avg_word_len > 6:
            report.formality = min(report.formality + 0.1, 1.0)
        elif avg_word_len < 4.5:
            report.formality = max(report.formality - 0.1, 0.0)

        # Сокращения (don't, can't) → неформальность
        contractions = len(re.findall(r"\b\w+'\w+\b", text))
        if contractions > word_count * 0.02:
            report.formality = max(report.formality - 0.15, 0.0)

        # ─── Субъективность ───
        subj_count = category_counts.get("subjective", 0)
        report.subjectivity = min(subj_count / max(word_count / 50, 1), 1.0)

        # ─── Оценки по тонам ───
        scores: dict[str, float] = {}

        scores["formal"] = report.formality
        scores["academic"] = min(
            category_counts.get("academic", 0) / max(word_count / 100, 1), 1.0
        )
        scores["marketing"] = min(
            category_counts.get("marketing", 0) / max(word_count / 80, 1), 1.0
        )
        scores["casual"] = 1.0 - report.formality
        scores["friendly"] = max(
            0, min(0.7 - report.formality + report.subjectivity * 0.3, 1.0)
        )
        scores["neutral"] = 1.0 - max(
            report.formality, report.subjectivity, scores.get("marketing", 0)
        )
        scores["professional"] = max(
            0, report.formality * 0.7 + (1 - report.subjectivity) * 0.3
        )

        report.scores = scores

        # ─── Primary tone ───
        best_tone = max(scores, key=lambda k: scores[k])
        try:
            report.primary_tone = ToneLevel(best_tone)
        except ValueError:
            report.primary_tone = ToneLevel.NEUTRAL

        # ─── Confidence ───
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            gap = sorted_scores[0] - sorted_scores[1]
            report.confidence = min(gap * 2 + 0.3, 1.0)

        return report


class ToneAdjuster:
    """Корректировщик тональности текста."""

    def __init__(self, lang: str = "en", seed: int | None = None):
        self.lang = lang
        self._replacements = _TONE_REPLACEMENTS.get(lang, {})
        self._analyzer = ToneAnalyzer(lang)
        import random
        self.rng = random.Random(seed)

    def adjust(
        self,
        text: str,
        target: ToneLevel = ToneLevel.NEUTRAL,
        intensity: float = 0.5,
    ) -> str:
        """Скорректировать тональность текста.

        Args:
            text: Исходный текст.
            target: Целевая тональность.
            intensity: 0..1, степень коррекции.

        Returns:
            Текст с скорректированной тональностью.
        """
        report = self._analyzer.analyze(text)
        current = report.primary_tone

        if current == target:
            return text

        # Определить направление изменения
        direction = self._get_direction(current, target)
        if not direction:
            return text

        replacements = self._replacements.get(direction, {})
        if not replacements:
            return text

        result = text
        changes_made = 0
        max_changes = max(1, int(len(text.split()) * intensity * 0.1))

        for old, new in replacements.items():
            if changes_made >= max_changes:
                break

            # Заменяем с учётом регистра
            pattern = re.compile(r'\b' + re.escape(old) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))

            for match in matches:
                if self.rng.random() > intensity:
                    continue

                original = match.group()
                replacement = new
                if original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                if original.isupper():
                    replacement = replacement.upper()

                result = result[:match.start()] + replacement + result[match.end():]
                changes_made += 1
                break  # Одна замена за итерацию чтобы не сбить индексы

        return result

    @staticmethod
    def _get_direction(
        current: ToneLevel, target: ToneLevel
    ) -> tuple[str, str] | None:
        """Определить направление коррекции."""
        formal_levels = {
            ToneLevel.FORMAL, ToneLevel.ACADEMIC,
            ToneLevel.PROFESSIONAL, ToneLevel.MARKETING,
        }
        informal_levels = {ToneLevel.CASUAL, ToneLevel.FRIENDLY}

        if current in informal_levels and target in formal_levels:
            return ("informal", "formal")
        elif current in formal_levels and target in informal_levels:
            return ("formal", "informal")
        elif current == ToneLevel.NEUTRAL and target in formal_levels:
            return ("informal", "formal")
        elif current == ToneLevel.NEUTRAL and target in informal_levels:
            return ("formal", "informal")

        return None


# ═══════════════════════════════════════════════════════════════
#  УДОБНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def analyze_tone(text: str, lang: str = "en") -> ToneReport:
    """Быстрый тональный анализ."""
    return ToneAnalyzer(lang).analyze(text)


def adjust_tone(
    text: str,
    target: str = "neutral",
    lang: str = "en",
    intensity: float = 0.5,
) -> str:
    """Скорректировать тональность.

    Args:
        target: "formal", "casual", "friendly", "academic", "professional",
                "neutral", "marketing".
    """
    try:
        tone_level = ToneLevel(target)
    except ValueError:
        tone_level = ToneLevel.NEUTRAL

    return ToneAdjuster(lang).adjust(text, target=tone_level, intensity=intensity)
