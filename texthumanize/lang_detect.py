"""Определение языка текста на основе триграмм и маркеров."""

from __future__ import annotations

from collections import Counter

from texthumanize.lang import LANGUAGES


def _extract_trigrams(text: str, limit: int = 300) -> Counter:
    """Извлечь триграммы из текста."""
    text = text.lower()[:5000]  # Ограничиваем длинные тексты
    trigrams: Counter = Counter()
    for i in range(len(text) - 2):
        tri = text[i:i + 3]
        if tri.strip():  # Пропускаем полностью пробельные
            trigrams[tri] += 1
    return Counter(dict(trigrams.most_common(limit)))


def _cyrillic_ratio(text: str) -> float:
    """Доля кириллических символов в тексте."""
    if not text:
        return 0.0
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    alpha = sum(1 for c in text if c.isalpha())
    return cyrillic / alpha if alpha > 0 else 0.0


def _has_ukrainian_markers(text: str) -> bool:
    """Проверить наличие уникальных украинских букв/слов."""
    uk_chars = {'і', 'ї', 'є', 'ґ'}
    text_lower = text.lower()

    # Уникальные украинские буквы
    char_hits = sum(1 for c in text_lower if c in uk_chars)
    if char_hits > 2:
        return True

    # Уникальные украинские слова
    uk_markers = [
        " є ", " та ", " або ", " що ", " як ", " бо ", " але ",
        " цей ", " ця ", " це ", " ці ", " від ", " між ", " під ",
        " щоб ", " якщо ", " тому ", " також ", " ще ", " вже ",
        " їх ", " його ", " її ", " наш ", " ваш ", " який ",
        " яка ", " яке ", " які ",
    ]
    marker_hits = sum(1 for m in uk_markers if m in text_lower)
    return marker_hits >= 3


def _has_russian_markers(text: str) -> bool:
    """Проверить наличие уникальных русских букв/слов."""
    ru_chars = {'ё', 'ы', 'э', 'ъ'}
    text_lower = text.lower()

    char_hits = sum(1 for c in text_lower if c in ru_chars)
    if char_hits > 1:
        return True

    # Типичные русские слова (отсутствующие в украинском)
    ru_markers = [
        " это ", " что ", " как ", " но ", " или ", " для ",
        " если ", " уже ", " ещё ", " еще ", " тоже ", " также ",
        " только ", " он ", " она ", " они ", " мы ", " вы ",
        " его ", " её ", " ее ", " их ", " был ", " были ",
        " будет ", " может ", " этот ", " эта ", " эти ",
        " который ", " которая ", " которые ",
    ]
    marker_hits = sum(1 for m in ru_markers if m in text_lower)
    return marker_hits >= 3


# ─── Маркеры для латинских языков ─────────────────────────────

def _detect_latin_language(text: str) -> str:
    """Определить конкретный латинский язык по маркерам и триграммам."""
    text_lower = text.lower()

    # Быстрая проверка по уникальным символам / словам
    scores: dict[str, int] = {}

    # Немецкий: ä/ö/ü/ß + характерные слова
    de_score = 0
    de_score += text_lower.count('ä') + text_lower.count('ö') + text_lower.count('ü')
    de_score += text_lower.count('ß') * 3
    de_markers = [
        " und ", " der ", " die ", " das ", " ist ", " ein ", " eine ",
        " nicht ", " mit ", " auf ", " für ", " von ", " werden ",
        " haben ", " sich ", " sind ", " auch ", " nach ", " wird ",
        " über ", " aber ", " oder ", " noch ", " kann ",
    ]
    de_score += sum(2 for m in de_markers if m in text_lower)
    scores["de"] = de_score

    # Французский: é/è/ê/ë/ç/à/ù/î/ô + характерные слова
    fr_score = 0
    for c in 'éèêëçàùîô':
        fr_score += text_lower.count(c)
    fr_markers = [
        " les ", " des ", " une ", " est ", " dans ", " pour ",
        " que ", " qui ", " pas ", " sur ", " avec ", " sont ",
        " mais ", " par ", " nous ", " vous ", " cette ", " tout ",
        " plus ", " elle ", " être ", " avoir ", " fait ",
        " c'est ", " l'on ", " qu'il ", " n'est ",
    ]
    fr_score += sum(2 for m in fr_markers if m in text_lower)
    scores["fr"] = fr_score

    # Испанский: ñ, ¿, ¡ + характерные слова
    es_score = 0
    es_score += text_lower.count('ñ') * 3
    es_score += text.count('¿') * 3
    es_score += text.count('¡') * 3
    es_markers = [
        " los ", " las ", " una ", " del ", " por ", " con ",
        " para ", " que ", " pero ", " como ", " más ", " ser ",
        " este ", " esta ", " esto ", " son ", " han ", " hay ",
        " todo ", " puede ", " muy ", " también ", " sobre ",
        " entre ", " cuando ", " donde ", " porque ",
    ]
    es_score += sum(2 for m in es_markers if m in text_lower)
    scores["es"] = es_score

    # Польский: ą/ę/ó/ś/ź/ż/ł/ń/ć + характерные слова
    pl_score = 0
    for c in 'ąęśźżłńć':
        pl_score += text_lower.count(c) * 2
    pl_markers = [
        " nie ", " jest ", " się ", " na ", " to ", " że ",
        " ale ", " jak ", " lub ", " dla ", " ich ", " był ",
        " może ", " tylko ", " być ", " został ", " przez ",
        " które ", " który ", " która ", " można ", " bardzo ",
        " jest ", " są ", " było ", " będzie ",
    ]
    pl_score += sum(2 for m in pl_markers if m in text_lower)
    scores["pl"] = pl_score

    # Португальский: ã/õ/ç + характерные слова
    pt_score = 0
    pt_score += text_lower.count('ã') * 2
    pt_score += text_lower.count('õ') * 2
    pt_score += text_lower.count('ç')
    pt_markers = [
        " não ", " uma ", " para ", " com ", " são ", " dos ",
        " das ", " nos ", " nas ", " mais ", " pelo ", " pela ",
        " como ", " pode ", " também ", " muito ", " sobre ",
        " entre ", " quando ", " onde ", " porque ", " ainda ",
        " tem ", " já ", " seu ", " sua ", " isso ", " esta ",
    ]
    pt_score += sum(2 for m in pt_markers if m in text_lower)
    scores["pt"] = pt_score

    # Итальянский: характерные слова (нет уникальных символов)
    it_score = 0
    it_markers = [
        " gli ", " delle ", " della ", " dello ", " nella ",
        " sono ", " che ", " per ", " con ", " una ",
        " questo ", " questa ", " anche ", " come ", " può ",
        " più ", " molto ", " tutto ", " ogni ", " fra ",
        " essere ", " avere ", " fatto ", " stato ",
        " perché ", " quando ", " dove ", " quale ",
    ]
    it_score += sum(2 for m in it_markers if m in text_lower)
    scores["it"] = it_score

    # Английский
    en_score = 0
    en_markers = [
        " the ", " and ", " that ", " have ", " for ", " are ",
        " with ", " this ", " from ", " they ", " been ",
        " which ", " their ", " would ", " there ", " about ",
        " could ", " other ", " into ", " than ", " these ",
        " its ", " were ", " will ", " does ", " should ",
    ]
    en_score += sum(2 for m in en_markers if m in text_lower)
    scores["en"] = en_score

    # Если все скоры низкие — триграммный анализ
    max_score = max(scores.values()) if scores else 0

    if max_score < 4:
        # Фоллбэк: триграммный анализ
        trigrams = _extract_trigrams(text)
        trigram_scores = {}
        for lang_code in LANGUAGES:
            pack = LANGUAGES[lang_code]
            lang_trigrams = set(pack.get("trigrams", []))
            if lang_trigrams:
                score = sum(trigrams.get(tri, 0) for tri in lang_trigrams)
                trigram_scores[lang_code] = score

        if trigram_scores:
            best = max(trigram_scores, key=lambda k: trigram_scores.get(k, 0))
            if trigram_scores[best] > 5:
                return best

        return "en"  # Ultimate fallback

    # Возвращаем язык с наибольшим score
    best_lang = max(scores, key=lambda k: scores.get(k, 0))

    # Порог: если лучший score < 6 — вероятно неизвестный язык
    if scores[best_lang] < 6:
        # Дополнительная проверка триграммами
        trigrams = _extract_trigrams(text)
        trigram_scores = {}
        for lang_code in LANGUAGES:
            pack = LANGUAGES[lang_code]
            lang_trigrams = set(pack.get("trigrams", []))
            if lang_trigrams:
                score = sum(trigrams.get(tri, 0) for tri in lang_trigrams)
                trigram_scores[lang_code] = score

        if trigram_scores:
            best_tri = max(trigram_scores, key=lambda k: trigram_scores.get(k, 0))
            if trigram_scores[best_tri] > sum(trigrams.values()) * 0.05:
                return best_tri

        return "en"

    return best_lang


def detect_language(text: str) -> str:
    """Определить язык текста.

    Поддерживает: ru, uk, en, de, fr, es, pl, pt, it.
    Для неизвестных латинских языков возвращает 'en' (обработка
    через универсальный процессор всё равно сработает).

    Args:
        text: Текст для анализа.

    Returns:
        Код языка: 'ru', 'uk', 'en', 'de', 'fr', 'es', 'pl', 'pt', 'it'.
    """
    if not text or len(text.strip()) < 10:
        return "en"

    text = " " + text + " "

    # Быстрая проверка: кириллический текст?
    cyr_ratio = _cyrillic_ratio(text)

    if cyr_ratio > 0.5:
        # Кириллический текст — определяем RU/UK
        if _has_ukrainian_markers(text):
            return "uk"
        if _has_russian_markers(text):
            return "ru"

        # Фоллбэк: триграммный анализ для кириллических языков
        trigrams = _extract_trigrams(text)
        scores = {}
        for lang_code in ("ru", "uk"):
            pack = LANGUAGES[lang_code]
            lang_trigrams = set(pack.get("trigrams", []))
            score = sum(trigrams.get(tri, 0) for tri in lang_trigrams)
            scores[lang_code] = score

        if scores.get("uk", 0) > scores.get("ru", 0) * 1.1:
            return "uk"
        return "ru"

    elif cyr_ratio > 0.1:
        # Смешанный текст — скорее всего RU/UK с вкраплениями латиницы
        if _has_ukrainian_markers(text):
            return "uk"
        return "ru"

    else:
        # Латиница — детальный анализ
        return _detect_latin_language(text)
