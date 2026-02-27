"""Коррекция когерентности — этап пайплайна.

Улучшает связность текста:
- Добавляет переходные слова между абзацами
- Разнообразит начала предложений
- Исправляет проблемы с тематической связностью

Использует coherence.py для анализа и собственную логику для ремонта.
"""

from __future__ import annotations

import logging
import random
import re

from texthumanize.coherence import CoherenceAnalyzer
from texthumanize.segmenter import skip_placeholder_sentence
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# Переходные слова для вставки между абзацами (по языкам и категориям)
_TRANSITION_INSERTIONS: dict[str, dict[str, list[str]]] = {
    "en": {
        "additive": [
            "Moreover, ", "Furthermore, ", "Additionally, ",
            "In addition, ", "What is more, ", "Besides, ",
        ],
        "adversative": [
            "However, ", "Nevertheless, ", "On the other hand, ",
            "In contrast, ", "Yet, ", "Still, ",
        ],
        "causal": [
            "Therefore, ", "Consequently, ", "As a result, ",
            "Thus, ", "Hence, ", "Accordingly, ",
        ],
        "sequential": [
            "Next, ", "Then, ", "Subsequently, ",
            "Meanwhile, ", "Afterward, ",
        ],
    },
    "ru": {
        "additive": [
            "Кроме того, ", "Помимо этого, ", "Также ",
            "Более того, ", "Вдобавок, ", "К тому же, ",
        ],
        "adversative": [
            "Однако ", "Тем не менее, ", "С другой стороны, ",
            "Впрочем, ", "Вместе с тем, ", "Всё же ",
        ],
        "causal": [
            "Поэтому ", "Следовательно, ", "В результате ",
            "Таким образом, ", "Благодаря этому, ",
        ],
        "sequential": [
            "Далее, ", "Затем ", "После этого ",
            "Вслед за этим, ", "На следующем этапе ",
        ],
    },
    "uk": {
        "additive": [
            "Крім того, ", "Окрім цього, ", "Також ",
            "Більше того, ", "До того ж, ", "На додаток, ",
        ],
        "adversative": [
            "Однак ", "Проте ", "З іншого боку, ",
            "Водночас ", "Тим не менш, ", "Все ж ",
        ],
        "causal": [
            "Тому ", "Отже, ", "В результаті ",
            "Таким чином, ", "Завдяки цьому, ",
        ],
        "sequential": [
            "Далі, ", "Потім ", "Після цього ",
            "Слідом за цим, ", "На наступному етапі ",
        ],
    },
    "de": {
        "additive": [
            "Darüber hinaus ", "Außerdem ", "Zusätzlich ",
            "Des Weiteren ", "Ferner ", "Zudem ",
        ],
        "adversative": [
            "Jedoch ", "Allerdings ", "Andererseits ",
            "Dennoch ", "Gleichwohl ", "Nichtsdestotrotz ",
        ],
        "causal": [
            "Daher ", "Folglich ", "Infolgedessen ",
            "Somit ", "Dementsprechend ",
        ],
        "sequential": [
            "Anschließend ", "Danach ", "Im Folgenden ",
            "Daraufhin ", "Im nächsten Schritt ",
        ],
    },
    "fr": {
        "additive": [
            "De plus, ", "En outre, ", "Par ailleurs, ",
            "Qui plus est, ", "D'autre part, ",
        ],
        "adversative": [
            "Cependant, ", "Néanmoins, ", "Toutefois, ",
            "En revanche, ", "Pourtant, ",
        ],
        "causal": [
            "Par conséquent, ", "De ce fait, ", "Ainsi, ",
            "C'est pourquoi ", "En conséquence, ",
        ],
        "sequential": [
            "Ensuite, ", "Puis, ", "Par la suite, ",
            "Après cela, ", "À la suite de cela, ",
        ],
    },
    "es": {
        "additive": [
            "Además, ", "Asimismo, ", "Por otra parte, ",
            "Igualmente, ", "De igual modo, ",
        ],
        "adversative": [
            "Sin embargo, ", "No obstante, ", "Por el contrario, ",
            "A pesar de ello, ", "En cambio, ",
        ],
        "causal": [
            "Por lo tanto, ", "En consecuencia, ", "Así pues, ",
            "Por esta razón, ", "De ahí que ",
        ],
        "sequential": [
            "A continuación, ", "Luego, ", "Seguidamente, ",
            "Posteriormente, ", "Acto seguido, ",
        ],
    },
    "it": {
        "additive": [
            "Inoltre, ", "Per di più, ", "In aggiunta, ",
            "Altresì, ", "D'altra parte, ",
        ],
        "adversative": [
            "Tuttavia, ", "Ciononostante, ", "Al contrario, ",
            "Nonostante ciò, ", "Eppure, ",
        ],
        "causal": [
            "Pertanto, ", "Di conseguenza, ", "Dunque, ",
            "Per questo motivo, ", "Da ciò deriva che ",
        ],
        "sequential": [
            "Successivamente, ", "In seguito, ", "Poi, ",
            "Dopodiché, ", "Nel passaggio successivo, ",
        ],
    },
    "pl": {
        "additive": [
            "Ponadto, ", "Co więcej, ", "Dodatkowo, ",
            "Oprócz tego, ", "Również ",
        ],
        "adversative": [
            "Jednakże, ", "Niemniej jednak, ", "Z drugiej strony, ",
            "Mimo to, ", "Natomiast ",
        ],
        "causal": [
            "Dlatego ", "W konsekwencji, ", "W rezultacie, ",
            "Z tego powodu, ", "Tym samym ",
        ],
        "sequential": [
            "Następnie, ", "Potem, ", "W dalszej kolejności, ",
            "Po tym, ", "W kolejnym kroku ",
        ],
    },
    "pt": {
        "additive": [
            "Além disso, ", "Ademais, ", "Por outro lado, ",
            "Igualmente, ", "Do mesmo modo, ",
        ],
        "adversative": [
            "No entanto, ", "Todavia, ", "Pelo contrário, ",
            "Apesar disso, ", "Porém, ",
        ],
        "causal": [
            "Portanto, ", "Em consequência, ", "Desse modo, ",
            "Por essa razão, ", "Assim sendo, ",
        ],
        "sequential": [
            "Em seguida, ", "Depois, ", "Posteriormente, ",
            "Após isso, ", "No passo seguinte, ",
        ],
    },
    "ar": {
        "additive": ["بالإضافة إلى ذلك، ", "فضلاً عن ذلك، ", "كذلك، ", "علاوة على ذلك، "],
        "adversative": ["ومع ذلك، ", "لكن، ", "على الرغم من ذلك، ", "إلا أن "],
        "causal": ["لذلك، ", "من ثم، ", "نتيجة لذلك، ", "وبالتالي، "],
        "sequential": ["بعد ذلك، ", "ثم ", "لاحقاً، ", "في الخطوة التالية، "],
    },
    "zh": {
        "additive": ["此外，", "另外，", "而且，", "不仅如此，"],
        "adversative": ["然而，", "但是，", "不过，", "尽管如此，"],
        "causal": ["因此，", "所以，", "由此可见，", "正因如此，"],
        "sequential": ["接下来，", "随后，", "然后，", "紧接着，"],
    },
    "ja": {
        "additive": ["さらに、", "加えて、", "その上、", "また、"],
        "adversative": ["しかし、", "一方で、", "とはいえ、", "それにもかかわらず、"],
        "causal": ["したがって、", "そのため、", "よって、", "これにより、"],
        "sequential": ["次に、", "続いて、", "その後、", "引き続き、"],
    },
    "ko": {
        "additive": ["또한, ", "게다가, ", "아울러, ", "더불어, "],
        "adversative": ["그러나, ", "반면에, ", "하지만, ", "그럼에도 불구하고, "],
        "causal": ["따라서, ", "그러므로, ", "이에 따라, ", "결과적으로, "],
        "sequential": ["다음으로, ", "이어서, ", "그 후, ", "계속해서, "],
    },
    "tr": {
        "additive": ["Ayrıca, ", "Bunun yanı sıra, ", "Üstelik, ", "Buna ek olarak, "],
        "adversative": ["Ancak, ", "Bununla birlikte, ", "Öte yandan, ", "Ne var ki, "],
        "causal": ["Bu nedenle, ", "Dolayısıyla, ", "Sonuç olarak, ", "Bundan ötürü, "],
        "sequential": ["Ardından, ", "Daha sonra, ", "Akabinde, ", "Bunun ardından, "],
    },
}

# Альтернативные начала предложений для разнообразия
_ALTERNATIVE_OPENINGS: dict[str, list[str]] = {
    "en": [
        "Notably, ", "Interestingly, ", "In fact, ", "Indeed, ",
        "Specifically, ", "In particular, ", "Essentially, ",
        "Importantly, ", "Significantly, ", "Remarkably, ",
    ],
    "ru": [
        "Примечательно, что ", "Важно, что ", "По сути, ",
        "В частности, ", "Стоит отметить, что ",
        "Особенно важно, что ", "Существенно, что ",
        "Характерно, что ", "Интересно, что ",
    ],
    "uk": [
        "Примітно, що ", "Важливо, що ", "По суті, ",
        "Зокрема, ", "Варто зазначити, що ",
        "Особливо важливо, що ", "Суттєво, що ",
        "Характерно, що ", "Цікаво, що ",
    ],
    "de": [
        "Bemerkenswert ist, dass ", "Tatsächlich ", "Insbesondere ",
        "Im Wesentlichen ", "Wichtig ist, dass ",
        "Hervorzuheben ist, dass ", "Bezeichnenderweise ",
    ],
    "fr": [
        "Il est à noter que ", "En fait, ", "En particulier, ",
        "Essentiellement, ", "Il convient de souligner que ",
        "De manière significative, ", "Certes, ",
    ],
    "es": [
        "Cabe destacar que ", "De hecho, ", "En particular, ",
        "Esencialmente, ", "Es importante señalar que ",
        "Significativamente, ", "Ciertamente, ",
    ],
}


class CoherenceRepairer:
    """Корректор когерентности текста для пайплайна.

    Анализирует связность текста и исправляет проблемы:
    - Добавляет переходные слова между абзацами
    - Разнообразит начала предложений
    - Улучшает тематическую связность

    Работает для ВСЕХ 14 языков (с разной глубиной).
    """

    def __init__(
        self,
        lang: str = "en",
        profile: str = "default",
        intensity: int = 50,
        seed: int | None = None,
    ):
        self.lang = lang
        self.profile = profile
        self.intensity = intensity
        self.seed = seed
        self.changes: list[dict] = []
        self._rng = random.Random(seed)

    def process(self, text: str) -> str:
        """Улучшить когерентность текста.

        Returns:
            Текст с улучшенной связностью.
        """
        if not text or not text.strip():
            return text

        # Анализируем когерентность
        analyzer = CoherenceAnalyzer(self.lang)
        report = analyzer.analyze(text)

        # Если всё хорошо (>0.7) — не трогаем
        if report.overall >= 0.7 and not report.issues:
            return text

        result = text
        fixes_applied: list[str] = []

        # 1. Добавляем переходные слова между абзацами
        if "few_transitions" in report.issues:
            result, added = self._add_transitions(result)
            if added > 0:
                fixes_applied.append(f"добавлено {added} связующих слов")

        # 2. Разнообразим начала предложений
        if "repetitive_sentence_openings" in report.issues:
            result, varied = self._vary_openings(result)
            if varied > 0:
                fixes_applied.append(f"разнообразено {varied} начал")

        if fixes_applied:
            # Пересчитываем когерентность
            report_after = analyzer.analyze(result)
            self.changes.append({
                "type": "coherence_repair",
                "description": (
                    f"Когерентность: {', '.join(fixes_applied)} "
                    f"(балл {report.overall:.2f}→{report_after.overall:.2f})"
                ),
            })

        return result

    def _add_transitions(self, text: str) -> tuple[str, int]:
        """Добавить переходные слова между абзацами."""
        transitions = _TRANSITION_INSERTIONS.get(
            self.lang,
            _TRANSITION_INSERTIONS.get("en", {}),
        )
        if not transitions:
            return text, 0

        paragraphs = re.split(r'\n\s*\n', text.strip())
        if len(paragraphs) < 2:
            return text, 0

        # Собираем все категории переходных слов
        all_categories = list(transitions.keys())
        added = 0
        new_paragraphs = [paragraphs[0]]

        for i in range(1, len(paragraphs)):
            para = paragraphs[i].strip()
            if not para:
                new_paragraphs.append(para)
                continue

            # Проверяем, есть ли уже переходное слово
            para_lower = para.lower()[:80]
            has_transition = False
            for cat_words in transitions.values():
                for tw in cat_words:
                    if para_lower.startswith(tw.lower().strip()):
                        has_transition = True
                        break
                if has_transition:
                    break

            if has_transition or skip_placeholder_sentence(para[:100]):
                new_paragraphs.append(para)
                continue

            # Добавляем с вероятностью зависящей от intensity
            if self._rng.random() > self.intensity / 100:
                new_paragraphs.append(para)
                continue

            # Выбираем категорию чередованием
            cat = all_categories[i % len(all_categories)]
            words = transitions[cat]
            chosen = self._rng.choice(words)

            # Вставляем перед абзацем
            if para[0].isupper():
                # Делаем первую букву после перехода строчной
                new_para = chosen + para[0].lower() + para[1:]
            else:
                new_para = chosen + para
            new_paragraphs.append(new_para)
            added += 1

        if added == 0:
            return text, 0

        return "\n\n".join(new_paragraphs), added

    def _vary_openings(self, text: str) -> tuple[str, int]:
        """Разнообразить начала предложений."""
        openings = _ALTERNATIVE_OPENINGS.get(
            self.lang,
            _ALTERNATIVE_OPENINGS.get("en", []),
        )
        if not openings:
            return text, 0

        sentences = split_sentences(text, self.lang)
        if len(sentences) < 4:
            return text, 0

        # Найти повторяющиеся начала
        first_words: dict[str, list[int]] = {}
        for idx, sent in enumerate(sentences):
            words = sent.strip().split()
            if words:
                fw = words[0].lower()
                first_words.setdefault(fw, []).append(idx)

        varied = 0
        result = text

        for fw, indices in first_words.items():
            if len(indices) < 3:
                continue  # Повторение менее 3 раз — ок

            # Заменяем начала у части (кроме первого вхождения)
            for idx in indices[1:]:
                if self._rng.random() > 0.5:
                    continue
                if skip_placeholder_sentence(sentences[idx]):
                    continue

                sent = sentences[idx].strip()
                opening = self._rng.choice(openings)

                # Заменяем первое слово/фразу
                words = sent.split(maxsplit=1)
                if len(words) < 2:
                    continue

                # Делаем остаток строчным
                rest = words[1]
                new_sent = opening + rest[0].lower() + rest[1:] if rest else opening
                result = result.replace(sent, new_sent, 1)
                varied += 1
                break  # Одна замена за группу

        return result, varied
