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

# Переходные слова для вставки между абзацами (по языкам и категориям).
# ВАЖНО: Используем ТОЛЬКО естественные, «человечные» переходы.
# Формальные маркеры ("Moreover", "Furthermore", "Therefore", "Consequently"...)
# являются AI-индикаторами и НЕ ДОЛЖНЫ вставляться, т.к. naturalizer их удаляет.
_TRANSITION_INSERTIONS: dict[str, dict[str, list[str]]] = {
    "en": {
        "additive": [
            "On top of that, ", "Plus, ", "And ",
            "Also worth noting — ", "Along the same lines, ",
            "Another thing: ",
        ],
        "adversative": [
            "That said, ", "But ", "Then again, ",
            "At the same time, ", "Still, ",
            "Oddly enough, ",
        ],
        "causal": [
            "So ", "Because of this, ", "That's why ",
            "This means ", "Naturally, ",
        ],
        "sequential": [
            "Next up, ", "From there, ", "After that, ",
            "Moving on, ", "Then ",
        ],
    },
    "ru": {
        "additive": [
            "Ещё один момент: ", "Плюс к этому ", "А ещё ",
            "И ", "Стоит добавить, что ", "К тому же ",
        ],
        "adversative": [
            "Правда, ", "Но ", "При этом ",
            "Впрочем, ", "Хотя ", "С другой стороны, ",
        ],
        "causal": [
            "Поэтому ", "Отсюда и ", "Из-за этого ",
            "А значит, ", "Вот почему ",
        ],
        "sequential": [
            "Дальше — ", "Потом ", "После этого ",
            "Следующий шаг: ", "Идём дальше. ",
        ],
    },
    "uk": {
        "additive": [
            "Ще один момент: ", "Плюс до цього ", "А ще ",
            "І ", "Варто додати, що ", "До того ж ",
        ],
        "adversative": [
            "Щоправда, ", "Але ", "При цьому ",
            "Втім, ", "Хоча ", "З іншого боку, ",
        ],
        "causal": [
            "Тому ", "Звідси й ", "Через це ",
            "А отже, ", "Ось чому ",
        ],
        "sequential": [
            "Далі — ", "Потім ", "Після цього ",
            "Наступний крок: ", "Ідемо далі. ",
        ],
    },
    "de": {
        "additive": [
            "Dazu kommt: ", "Außerdem ", "Und ",
            "Noch ein Punkt: ", "Nebenbei gesagt, ", "Zudem ",
        ],
        "adversative": [
            "Aber ", "Allerdings ", "Dabei ",
            "Gleichzeitig ", "Trotzdem ",
        ],
        "causal": [
            "Deshalb ", "Genau deshalb ", "Das heißt, ",
            "Darum ", "Und so ",
        ],
        "sequential": [
            "Dann ", "Danach ", "Als Nächstes ",
            "Weiter geht's: ", "Im nächsten Schritt ",
        ],
    },
    "fr": {
        "additive": [
            "Et ", "En plus, ", "D'ailleurs, ",
            "Autre point : ", "À cela s'ajoute ",
        ],
        "adversative": [
            "Mais ", "Pourtant, ", "Alors que ",
            "En même temps, ", "Malgré tout, ",
        ],
        "causal": [
            "Du coup, ", "Voilà pourquoi ", "C'est pour ça que ",
            "Résultat : ", "Et donc, ",
        ],
        "sequential": [
            "Après, ", "Puis ", "Ensuite, ",
            "Étape suivante : ", "On passe à ",
        ],
    },
    "es": {
        "additive": [
            "Y ", "Aparte de eso, ", "Otro punto: ",
            "También ", "Sumado a esto, ",
        ],
        "adversative": [
            "Pero ", "Eso sí, ", "Ahora bien, ",
            "Aunque ", "Al mismo tiempo, ",
        ],
        "causal": [
            "Por eso ", "Así que ", "De ahí que ",
            "Esto explica por qué ", "Y entonces, ",
        ],
        "sequential": [
            "Después, ", "Luego, ", "Lo siguiente: ",
            "Y entonces ", "Pasamos a ",
        ],
    },
    "it": {
        "additive": [
            "E ", "In più, ", "C'è anche ",
            "Altro punto: ", "A questo si aggiunge che ",
        ],
        "adversative": [
            "Ma ", "Però, ", "Eppure, ",
            "Allo stesso tempo, ", "Detto questo, ",
        ],
        "causal": [
            "Per questo, ", "Ecco perché ", "E allora, ",
            "Il risultato è che ", "Dunque, ",
        ],
        "sequential": [
            "Poi, ", "Dopo, ", "A seguire, ",
            "Il passo successivo: ", "Si passa a ",
        ],
    },
    "pl": {
        "additive": [
            "I ", "Poza tym, ", "Warto też dodać, że ",
            "Kolejna rzecz: ", "Również ",
        ],
        "adversative": [
            "Ale ", "Tyle że ", "Z drugiej strony, ",
            "Mimo to, ", "Jednocześnie ",
        ],
        "causal": [
            "Dlatego ", "Stąd ", "Z tego powodu, ",
            "I w efekcie ", "Właśnie dlatego ",
        ],
        "sequential": [
            "Potem, ", "Dalej — ", "Następnie, ",
            "Kolejny krok: ", "Idąc dalej, ",
        ],
    },
    "pt": {
        "additive": [
            "E ", "Fora isso, ", "Outro ponto: ",
            "Vale acrescentar que ", "Também ",
        ],
        "adversative": [
            "Mas ", "Só que ", "Por outro lado, ",
            "Apesar disso, ", "Ao mesmo tempo, ",
        ],
        "causal": [
            "Por isso, ", "É por isso que ", "Daí que ",
            "O resultado é ", "E então, ",
        ],
        "sequential": [
            "Depois, ", "Em seguida, ", "O próximo passo: ",
            "A partir daí, ", "Seguindo em frente, ",
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

# Альтернативные начала предложений для разнообразия.
# Используем только разговорные, «живые» стартеры — без AI-маркеров.
_ALTERNATIVE_OPENINGS: dict[str, list[str]] = {
    "en": [
        "The thing is, ", "Point being, ", "What stands out is ",
        "One clear example: ", "Here, ", "In practice, ",
        "As it turns out, ", "A closer look shows ",
        "This is where ", "Worth noting: ",
    ],
    "ru": [
        "Дело в том, что ", "Суть в том, что ", "Тут ",
        "На практике ", "Если присмотреться, ",
        "Вот что бросается в глаза: ", "Здесь ",
        "Яркий пример — ", "Как показывает практика, ",
    ],
    "uk": [
        "Справа в тому, що ", "Суть у тому, що ", "Тут ",
        "На практиці ", "Якщо придивитися, ",
        "Ось що впадає в очі: ", "Тут ",
        "Яскравий приклад — ", "Як показує практика, ",
    ],
    "de": [
        "Fakt ist: ", "In der Praxis ", "Wichtig dabei: ",
        "Ein gutes Beispiel: ", "Wenn man genauer hinschaut, ",
        "Hier zeigt sich, dass ", "Es fällt auf, dass ",
    ],
    "fr": [
        "Le fait est que ", "En pratique, ", "Ce qui frappe, c'est ",
        "Un bon exemple : ", "Si on y regarde de plus près, ",
        "Là où ça se voit, c'est ", "Ce qui ressort, c'est ",
    ],
    "es": [
        "El punto es que ", "En la práctica, ", "Lo que llama la atención es ",
        "Un buen ejemplo: ", "Si miramos más de cerca, ",
        "Aquí se nota que ", "Lo que resalta es ",
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

        for _fw, indices in first_words.items():
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
