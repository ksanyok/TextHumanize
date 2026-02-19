"""Content Spinner — перезапись и перемешивание текста.

Генерирует уникальные версии текста:
- Spintax формат {вариант1|вариант2|вариант3}
- Многоуровневый спиннинг (слово/фраза/предложение/абзац)
- Уникализация с контролем качества
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from texthumanize.morphology import get_morphology


@dataclass
class SpinResult:
    """Результат спиннинга."""

    original: str
    spun: str
    spintax: str  # spintax формат
    uniqueness: float  # 0..1, отличие от оригинала
    variants_count: int  # сколько вариантов можно сгенерировать


# ═══════════════════════════════════════════════════════════════
#  СЛОВАРИ СИНОНИМОВ ДЛЯ СПИННИНГА
# ═══════════════════════════════════════════════════════════════

_SPIN_SYNONYMS = {
    "en": {
        # Verbs
        "use": ["utilize", "employ", "apply", "leverage", "make use of"],
        "make": ["create", "produce", "generate", "build", "construct"],
        "get": ["obtain", "acquire", "receive", "gain", "secure"],
        "show": ["demonstrate", "display", "reveal", "illustrate", "present"],
        "help": ["assist", "support", "aid", "facilitate", "enable"],
        "need": ["require", "necessitate", "demand", "call for"],
        "think": ["believe", "consider", "regard", "suppose", "reckon"],
        "give": ["provide", "offer", "supply", "deliver", "present"],
        "find": ["discover", "locate", "identify", "uncover", "detect"],
        "know": ["understand", "recognize", "realize", "comprehend"],
        "want": ["desire", "wish", "seek", "aim for"],
        "try": ["attempt", "endeavor", "strive", "seek to"],
        "start": ["begin", "commence", "initiate", "launch"],
        "end": ["finish", "conclude", "complete", "terminate"],
        "change": ["modify", "alter", "adjust", "transform"],
        "improve": ["enhance", "upgrade", "boost", "optimize"],
        "reduce": ["decrease", "diminish", "lower", "minimize"],
        "increase": ["raise", "elevate", "boost", "amplify"],
        "include": ["encompass", "incorporate", "comprise", "contain"],
        "develop": ["create", "build", "design", "establish"],
        # Adjectives
        "important": ["crucial", "vital", "essential", "significant", "critical"],
        "good": ["excellent", "outstanding", "great", "superior", "fine"],
        "bad": ["poor", "inferior", "substandard", "inadequate"],
        "big": ["large", "substantial", "considerable", "significant"],
        "small": ["tiny", "minor", "slight", "modest", "compact"],
        "new": ["novel", "recent", "fresh", "modern", "latest"],
        "old": ["previous", "former", "traditional", "established"],
        "fast": ["rapid", "quick", "swift", "speedy", "prompt"],
        "easy": ["simple", "straightforward", "effortless", "uncomplicated"],
        "hard": ["difficult", "challenging", "complex", "demanding"],
        "clear": ["obvious", "evident", "apparent", "transparent"],
        "different": ["various", "diverse", "distinct", "alternative"],
        # Adverbs
        "also": ["additionally", "furthermore", "moreover", "besides"],
        "however": ["nevertheless", "nonetheless", "yet", "still"],
        "therefore": ["consequently", "thus", "hence", "accordingly"],
        "often": ["frequently", "regularly", "commonly", "repeatedly"],
        "usually": ["typically", "generally", "normally", "commonly"],
        "quickly": ["rapidly", "swiftly", "promptly", "speedily"],
        "very": ["extremely", "highly", "remarkably", "exceptionally"],
        # Connectors
        "because": ["since", "as", "due to the fact that", "given that"],
        "but": ["however", "yet", "nevertheless", "on the other hand"],
        "and": ["as well as", "along with", "in addition to", "plus"],
    },
    "ru": {
        # Глаголы
        "использовать": ["применять", "задействовать", "употреблять"],
        "делать": ["выполнять", "осуществлять", "производить", "совершать"],
        "получать": ["обретать", "приобретать", "добывать"],
        "показывать": ["демонстрировать", "отображать", "иллюстрировать"],
        "помогать": ["содействовать", "способствовать", "поддерживать"],
        "начинать": ["приступать", "стартовать", "инициировать"],
        "заканчивать": ["завершать", "оканчивать", "финализировать"],
        "менять": ["изменять", "модифицировать", "трансформировать"],
        "улучшать": ["совершенствовать", "оптимизировать", "повышать"],
        "увеличивать": ["повышать", "наращивать", "усиливать"],
        "уменьшать": ["сокращать", "снижать", "минимизировать"],
        "создавать": ["формировать", "разрабатывать", "конструировать"],
        "думать": ["полагать", "считать", "рассуждать"],
        # Прилагательные
        "важный": ["существенный", "значимый", "ключевой", "принципиальный"],
        "хороший": ["отличный", "прекрасный", "качественный", "достойный"],
        "плохой": ["скверный", "некачественный", "неудачный"],
        "большой": ["крупный", "масштабный", "значительный", "солидный"],
        "маленький": ["небольшой", "компактный", "незначительный"],
        "новый": ["современный", "свежий", "актуальный", "недавний"],
        "быстрый": ["стремительный", "оперативный", "скоростной"],
        "разный": ["различный", "разнообразный", "многообразный"],
        # Наречия
        "также": ["кроме того", "помимо этого", "вдобавок"],
        "однако": ["тем не менее", "впрочем", "вместе с тем"],
        "поэтому": ["следовательно", "таким образом", "вследствие этого"],
        "часто": ["нередко", "зачастую", "регулярно"],
        "обычно": ["как правило", "зачастую", "в большинстве случаев"],
        "очень": ["чрезвычайно", "крайне", "весьма", "исключительно"],
    },
    "uk": {
        "використовувати": ["застосовувати", "вживати", "задіювати"],
        "робити": ["виконувати", "здійснювати", "чинити"],
        "отримувати": ["здобувати", "набувати", "одержувати"],
        "показувати": ["демонструвати", "відображати", "ілюструвати"],
        "допомагати": ["сприяти", "підтримувати", "підсобляти"],
        "починати": ["розпочинати", "стартувати", "ініціювати"],
        "закінчувати": ["завершувати", "фіналізувати"],
        "змінювати": ["модифікувати", "трансформувати", "перетворювати"],
        "покращувати": ["вдосконалювати", "оптимізувати", "підвищувати"],
        "важливий": ["суттєвий", "значущий", "ключовий", "принциповий"],
        "добрий": ["чудовий", "прекрасний", "якісний", "гідний"],
        "поганий": ["невдалий", "неякісний"],
        "великий": ["значний", "масштабний", "чималий", "солідний"],
        "малий": ["невеликий", "компактний", "незначний"],
        "новий": ["сучасний", "свіжий", "актуальний", "недавній"],
        "швидкий": ["стрімкий", "оперативний", "хуткий"],
        "також": ["крім того", "окрім цього", "на додаток"],
        "однак": ["проте", "тим не менш", "втім"],
        "тому": ["отже", "відтак", "внаслідок цього"],
        "часто": ["нерідко", "регулярно", "почасти"],
        "зазвичай": ["як правило", "здебільшого", "переважно"],
        "дуже": ["надзвичайно", "вкрай", "вельми", "винятково"],
    },
}


class ContentSpinner:
    """Спиннер контента — генерация уникальных версий текста."""

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
        intensity: float = 0.5,
    ):
        """
        Args:
            lang: Язык текста.
            seed: Зерно RNG.
            intensity: 0..1, доля слов для замены.
        """
        self.lang = lang
        self.rng = random.Random(seed)
        self.intensity = intensity
        self.morph = get_morphology(lang)
        self._synonyms = _SPIN_SYNONYMS.get(lang, {})

    def spin(self, text: str) -> SpinResult:
        """Спиннинг текста — создание уникальной версии.

        Args:
            text: Исходный текст.

        Returns:
            SpinResult с уникальной версией и spintax.
        """
        spintax = self._generate_spintax(text)
        spun = self._resolve_spintax(spintax)
        uniqueness = self._calculate_uniqueness(text, spun)
        variants = self._count_variants(spintax)

        return SpinResult(
            original=text,
            spun=spun,
            spintax=spintax,
            uniqueness=uniqueness,
            variants_count=variants,
        )

    def generate_spintax(self, text: str) -> str:
        """Генерировать spintax-формат текста.

        Args:
            text: Исходный текст.

        Returns:
            Текст в формате spintax.
        """
        return self._generate_spintax(text)

    def resolve_spintax(self, spintax: str) -> str:
        """Развернуть spintax в один из вариантов.

        Args:
            spintax: Текст в формате {вариант1|вариант2|...}.

        Returns:
            Один случайный вариант.
        """
        return self._resolve_spintax(spintax)

    def generate_variants(self, text: str, count: int = 5) -> list[str]:
        """Генерировать несколько уникальных вариантов текста.

        Args:
            text: Исходный текст.
            count: Количество вариантов.

        Returns:
            Список уникальных версий.
        """
        spintax = self._generate_spintax(text)
        variants: list[str] = []
        seen: set[str] = set()

        max_attempts = count * 3
        for _ in range(max_attempts):
            if len(variants) >= count:
                break
            variant = self._resolve_spintax(spintax)
            if variant not in seen:
                seen.add(variant)
                variants.append(variant)

        return variants

    # ───────────────────────────────────────────────────────────
    #  PRIVATE
    # ───────────────────────────────────────────────────────────

    def _generate_spintax(self, text: str) -> str:
        """Сгенерировать spintax из обычного текста."""
        words = text.split()
        result: list[str] = []

        for word in words:
            # Извлекаем слово и пунктуацию
            clean = word.strip('.,;:!?"\'()[]{}')
            prefix = word[:word.index(clean)] if clean and clean in word else ""
            suffix = word[word.index(clean) + len(clean):] if clean and clean in word else ""

            if not clean:
                result.append(word)
                continue

            # Ищем синонимы
            lower = clean.lower()
            syns = self._synonyms.get(lower, [])

            if not syns or self.rng.random() > self.intensity:
                result.append(word)
                continue

            # Создаём spintax варианты
            variants = [clean]
            for syn in syns[:4]:  # Максимум 4 синонима
                # Согласуем форму
                matched = self.morph.find_synonym_form(clean, syn)
                # Сохраняем регистр
                if clean[0].isupper():
                    matched = matched[0].upper() + matched[1:]
                if clean.isupper():
                    matched = matched.upper()
                variants.append(matched)

            # Убираем дубликаты сохраняя порядок
            seen: list[str] = []
            for v in variants:
                if v not in seen:
                    seen.append(v)
            variants = seen

            if len(variants) > 1:
                spintax_word = "{" + "|".join(variants) + "}"
                result.append(prefix + spintax_word + suffix)
            else:
                result.append(word)

        return " ".join(result)

    def _resolve_spintax(self, spintax: str) -> str:
        """Развернуть spintax, выбирая случайные варианты."""
        def resolve_match(m: re.Match) -> str:
            options = m.group(1).split("|")
            return str(self.rng.choice(options))

        # Многоуровневый spintax — разворачиваем изнутри
        result = spintax
        max_depth = 5
        for _ in range(max_depth):
            new_result = re.sub(r'\{([^{}]+)\}', resolve_match, result)
            if new_result == result:
                break
            result = new_result

        return result

    @staticmethod
    def _calculate_uniqueness(original: str, spun: str) -> float:
        """Рассчитать уникальность (1 - сходство)."""
        orig_words = original.lower().split()
        spun_words = spun.lower().split()

        if not orig_words:
            return 1.0

        # Считаем совпадающие слова в позициях
        matches = sum(
            1 for a, b in zip(orig_words, spun_words) if a == b
        )
        max_len = max(len(orig_words), len(spun_words))
        return 1.0 - matches / max_len

    @staticmethod
    def _count_variants(spintax: str) -> int:
        """Подсчитать количество возможных вариантов."""
        groups = re.findall(r'\{([^{}]+)\}', spintax)
        if not groups:
            return 1

        count = 1
        for group in groups:
            options = group.split("|")
            count *= len(options)
            if count > 1_000_000:
                return 1_000_000  # Cap

        return count


# ═══════════════════════════════════════════════════════════════
#  УДОБНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def spin_text(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
    seed: int | None = None,
) -> str:
    """Спиннинг текста — создать уникальную версию."""
    spinner = ContentSpinner(lang=lang, seed=seed, intensity=intensity)
    return spinner.spin(text).spun


def generate_spintax(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
) -> str:
    """Преобразовать текст в spintax формат."""
    spinner = ContentSpinner(lang=lang, intensity=intensity)
    return spinner.generate_spintax(text)


def generate_variants(
    text: str,
    count: int = 5,
    lang: str = "en",
    intensity: float = 0.5,
) -> list[str]:
    """Сгенерировать несколько уникальных версий текста."""
    spinner = ContentSpinner(lang=lang, intensity=intensity)
    return spinner.generate_variants(text, count=count)
