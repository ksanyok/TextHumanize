#!/usr/bin/env python3
"""
gen_massive_synonyms.py — Массовая генерация словарей синонимов из открытых источников.

Источники:
 1. Moby Thesaurus (public domain, ~30K корневых слов, ~2.5M синонимов)
 2. Datamuse API   (бесплатный, без авторизации, EN синонимы/ассоциации)
 3. RU Wiktionary  (CC BY-SA, парсинг секции «Синонимы»)
 4. UK Wiktionary  (CC BY-SA, парсинг секции «Синоніми»)

Выход: texthumanize/_massive_synonyms.py  — статический Python-файл.
       Формат: SYNONYMS = {"en": {word: [syn, ...], ...}, "ru": {...}, "uk": {...}}

Использование:
    python scripts/gen_massive_synonyms.py        # Полная генерация (~5-10 мин)
    python scripts/gen_massive_synonyms.py --fast  # Только Moby + seed (30 сек)

Лицензия: Moby Thesaurus — public domain (Grady Ward, 1996)
          Wiktionary — CC BY-SA 3.0 (совместимо с MIT)
          Datamuse — бесплатный API (attribution requested)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from collections import defaultdict
from typing import Optional

# ═══════════════════════════════════════════════════════════════
#  КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "texthumanize" / "_massive_synonyms.py"

DATAMUSE_URL = "https://api.datamuse.com/words"
MOBY_URL = "https://raw.githubusercontent.com/words/moby/master/words.txt"
RU_WIKT_API = "https://ru.wiktionary.org/w/api.php"
UK_WIKT_API = "https://uk.wiktionary.org/w/api.php"

USER_AGENT = "TextHumanize/1.0 (synonym-gen; github.com/texthumanize)"

# Максимум синонимов на слово
MAX_SYNS_PER_WORD = 12

# Задержка между API-запросами (сек)
API_DELAY = 0.15


# ═══════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════

def _fetch(url: str, timeout: int = 15) -> bytes:
    """HTTP GET с User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout).read()


def _fetch_json(url: str, timeout: int = 15) -> dict:
    """HTTP GET → JSON."""
    return json.loads(_fetch(url, timeout))


def _clean_word(w: str) -> str:
    """Очистка слова."""
    return w.strip().lower().replace("\r", "")


def _is_good_en(w: str) -> bool:
    """Фильтр качества для английского слова."""
    if not w or len(w) < 2 or len(w) > 30:
        return False
    if not re.match(r'^[a-z][a-z\s\'-]{0,28}$', w):
        return False
    if w.count(" ") > 2:  # макс 3-словные фразы
        return False
    return True


def _is_good_cyrillic(w: str) -> bool:
    """Фильтр качества для кириллического слова."""
    if not w or len(w) < 2 or len(w) > 40:
        return False
    # Должно содержать кириллические буквы
    if not re.search(r'[а-яіїєґёА-ЯІЇЄҐЁ]', w):
        return False
    return True


# ═══════════════════════════════════════════════════════════════
#  ИСТОЧНИК 1: MOBY THESAURUS (EN)
# ═══════════════════════════════════════════════════════════════

def fetch_moby_thesaurus() -> dict[str, list[str]]:
    """
    Загрузка Moby Thesaurus с GitHub (public domain).
    Возвращает ~30K корневых слов с синонимами.
    """
    print("  [Moby] Загрузка Moby Thesaurus...")
    try:
        raw = _fetch(MOBY_URL, timeout=60).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [Moby] ОШИБКА загрузки: {e}")
        return {}

    lines = raw.split("\n")
    result: dict[str, list[str]] = {}
    skipped = 0

    for line in lines:
        line = line.strip().replace("\r", "")
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue

        root = _clean_word(parts[0])
        if not _is_good_en(root):
            skipped += 1
            continue

        syns = []
        for p in parts[1:]:
            w = _clean_word(p)
            if _is_good_en(w) and w != root:
                syns.append(w)
        if syns:
            result[root] = syns[:MAX_SYNS_PER_WORD]

    print(f"  [Moby] Загружено: {len(result)} корневых слов, "
          f"пропущено {skipped}")
    return result


# ═══════════════════════════════════════════════════════════════
#  ИСТОЧНИК 2: DATAMUSE API (EN)
# ═══════════════════════════════════════════════════════════════

# Seed-слова для Datamuse (AI-типичная лексика + общеупотребительная)
_EN_SEEDS = [
    # AI-типичная формальная лексика
    "additionally", "furthermore", "moreover", "consequently", "therefore",
    "significant", "comprehensive", "facilitate", "implement", "utilize",
    "demonstrate", "establish", "enhance", "optimize", "leverage",
    "fundamental", "paradigm", "methodology", "framework", "infrastructure",
    "innovative", "robust", "streamline", "mitigate", "encompass",
    "preliminary", "subsequent", "commence", "terminate", "acquisition",
    # Академическая лексика
    "analyze", "evaluate", "investigate", "determine", "indicate",
    "perspective", "component", "mechanism", "phenomenon", "hypothesis",
    "correlation", "implication", "constraint", "parameter", "variable",
    # Общая лексика (высокочастотная)
    "important", "effective", "approach", "process", "system",
    "structure", "potential", "opportunity", "challenge", "benefit",
    "achieve", "provide", "maintain", "consider", "suggest",
    "development", "environment", "particular", "generate", "identify",
    # Глаголы
    "accomplish", "accelerate", "accumulate", "administer", "advocate",
    "allocate", "anticipate", "assemble", "calculate", "collaborate",
    "compensate", "configure", "consolidate", "contribute", "coordinate",
    "cultivate", "customize", "delegate", "diminish", "elaborate",
    "eliminate", "emphasize", "encounter", "endeavor", "evaluate",
    "execute", "experience", "formulate", "guarantee", "illustrate",
    "incorporate", "influence", "initiate", "integrate", "interpret",
    "manufacture", "maximize", "minimize", "monitor", "navigate",
    "negotiate", "notify", "occupy", "participate", "perceive",
    "persuade", "predict", "prioritize", "pursue", "recommend",
    "reinforce", "replicate", "represent", "simulate", "stimulate",
    "substitute", "supplement", "transform", "transmit", "validate",
    # Прилагательные
    "adequate", "apparent", "appropriate", "beneficial", "capable",
    "comparable", "compatible", "considerable", "consistent", "conventional",
    "diverse", "dominant", "efficient", "equivalent", "essential",
    "excessive", "exclusive", "explicit", "extensive", "feasible",
    "flexible", "genuine", "identical", "inevitable", "inherent",
    "initial", "minimal", "notable", "obvious", "optimal",
    "permanent", "predominant", "profound", "prominent", "proportional",
    "relevant", "reliable", "remarkable", "substantial", "sufficient",
    "sustainable", "tangible", "transparent", "unprecedented", "viable",
    # Существительные
    "accomplishment", "adjustment", "advancement", "alternative", "analysis",
    "application", "assessment", "assumption", "capability", "capacity",
    "category", "circumstance", "collaboration", "complexity", "concept",
    "configuration", "consequence", "consideration", "dimension", "distinction",
    "effectiveness", "emergence", "emphasis", "engagement", "enhancement",
    "evolution", "expansion", "exploration", "foundation", "implementation",
    "indication", "initiative", "innovation", "insight", "interpretation",
    "investment", "justification", "landscape", "limitation", "mechanism",
    "modification", "motivation", "observation", "optimization", "orientation",
    "perception", "performance", "phenomenon", "portfolio", "precision",
    "probability", "progression", "proposition", "recognition", "regulation",
    "resilience", "resolution", "specification", "strategy", "sustainability",
    "trajectory", "transition", "utilization", "vulnerability", "workforce",
]


def fetch_datamuse_synonyms(seeds: list[str]) -> dict[str, list[str]]:
    """
    Получение синонимов через Datamuse API.
    """
    print(f"  [Datamuse] Запрос синонимов для {len(seeds)} слов...")
    result: dict[str, list[str]] = {}
    errors = 0

    for i, word in enumerate(seeds):
        if i % 50 == 0 and i > 0:
            print(f"    ... {i}/{len(seeds)} обработано")
        try:
            url = f"{DATAMUSE_URL}?rel_syn={urllib.parse.quote(word)}&max={MAX_SYNS_PER_WORD}"
            data = _fetch_json(url, timeout=10)
            syns = [
                w["word"] for w in data
                if _is_good_en(w.get("word", "")) and w["word"] != word
            ]
            if syns:
                result[word] = syns[:MAX_SYNS_PER_WORD]
            time.sleep(API_DELAY)
        except Exception:
            errors += 1
            time.sleep(0.5)

    print(f"  [Datamuse] Получено: {len(result)} слов, ошибок: {errors}")
    return result


# ═══════════════════════════════════════════════════════════════
#  ИСТОЧНИК 3: WIKTIONARY (RU/UK)
# ═══════════════════════════════════════════════════════════════

# Seed-слов для RU Wiktionary
_RU_SEEDS = [
    # AI-типичная лексика
    "важный", "значительный", "существенный", "необходимый", "эффективный",
    "использовать", "обеспечивать", "осуществлять", "реализовать", "демонстрировать",
    "способствовать", "определять", "результат", "процесс", "система",
    "данный", "значимый", "комплексный", "фундаментальный", "оптимальный",
    "структура", "метод", "подход", "анализ", "развитие", "качество",
    # Общеупотребительная лексика
    "большой", "маленький", "быстро", "медленно", "хороший", "плохой",
    "красивый", "новый", "старый", "сильный", "слабый", "лёгкий",
    "тяжёлый", "высокий", "низкий", "длинный", "короткий", "широкий",
    "узкий", "глубокий", "простой", "сложный", "главный", "основной",
    "общий", "частный", "полный", "пустой", "ранний", "поздний",
    # Глаголы
    "делать", "говорить", "думать", "знать", "хотеть", "видеть",
    "давать", "брать", "идти", "стоять", "работать", "помогать",
    "начинать", "понимать", "создавать", "менять", "получать", "искать",
    "считать", "решать", "предлагать", "требовать", "показывать", "объяснять",
    "улучшать", "увеличивать", "уменьшать", "достигать", "включать", "содержать",
    "представлять", "формировать", "применять", "устанавливать", "определять",
    "находить", "вести", "принимать", "обращать", "останавливать",
    # Существительные
    "время", "место", "работа", "человек", "жизнь", "день", "мир",
    "дело", "голова", "рука", "вопрос", "часть", "сторона", "конец",
    "ответ", "проблема", "причина", "задача", "цель", "условие",
    "возможность", "средство", "способ", "путь", "случай", "начало",
    "основа", "область", "сфера", "направление", "уровень", "степень",
    "форма", "вид", "тип", "класс", "группа", "состояние", "положение",
    "действие", "движение", "шаг", "план", "решение", "мнение",
    "точка", "взгляд", "идея", "мысль", "слово", "закон",
    # Прилагательные (ещё)
    "великий", "малый", "правый", "левый", "верный", "точный",
    "ясный", "тёмный", "светлый", "тёплый", "холодный", "мокрый",
    "сухой", "чистый", "грязный", "свежий", "острый", "тупой",
    "мягкий", "твёрдый", "гладкий", "гибкий", "жёсткий", "крепкий",
    "тихий", "громкий", "быстрый", "медленный", "ранний", "поздний",
    "современный", "древний", "внутренний", "внешний", "передний", "задний",
    "верхний", "нижний", "правильный", "ложный", "странный", "обычный",
    "особый", "общий", "личный", "научный", "технический", "политический",
    # Наречия
    "очень", "довольно", "весьма", "крайне", "чрезвычайно", "совершенно",
    "совсем", "вполне", "почти", "примерно", "абсолютно", "полностью",
    "значительно", "существенно", "заметно", "явно", "очевидно", "видимо",
    "вероятно", "возможно", "действительно", "несомненно", "безусловно",
    "постоянно", "регулярно", "часто", "редко", "иногда", "обычно",
]

_UK_SEEDS = [
    # AI-типичная лексика
    "важливий", "значний", "суттєвий", "необхідний", "ефективний",
    "використовувати", "забезпечувати", "здійснювати", "реалізувати", "демонструвати",
    "сприяти", "визначати", "результат", "процес", "система",
    "даний", "значущий", "комплексний", "фундаментальний", "оптимальний",
    "структура", "метод", "підхід", "аналіз", "розвиток", "якість",
    # Общеупотребительная лексика
    "великий", "малий", "швидко", "повільно", "добрий", "поганий",
    "гарний", "новий", "старий", "сильний", "слабкий", "легкий",
    "важкий", "високий", "низький", "довгий", "короткий", "широкий",
    "вузький", "глибокий", "простий", "складний", "головний", "основний",
    "загальний", "приватний", "повний", "порожній", "ранній", "пізній",
    # Глаголи
    "робити", "говорити", "думати", "знати", "хотіти", "бачити",
    "давати", "брати", "йти", "стояти", "працювати", "допомагати",
    "починати", "розуміти", "створювати", "змінювати", "отримувати", "шукати",
    "вважати", "вирішувати", "пропонувати", "вимагати", "показувати", "пояснювати",
    "покращувати", "збільшувати", "зменшувати", "досягати", "включати", "містити",
    "представляти", "формувати", "застосовувати", "встановлювати", "визначати",
    "знаходити", "вести", "приймати", "звертати", "зупиняти",
    # Существительные
    "час", "місце", "робота", "людина", "життя", "день", "світ",
    "справа", "голова", "рука", "питання", "частина", "сторона", "кінець",
    "відповідь", "проблема", "причина", "завдання", "мета", "умова",
    "можливість", "засіб", "спосіб", "шлях", "випадок", "початок",
    "основа", "галузь", "сфера", "напрямок", "рівень", "ступінь",
    "форма", "вид", "тип", "клас", "група", "стан", "становище",
    "дія", "рух", "крок", "план", "рішення", "думка",
    "точка", "погляд", "ідея", "думка", "слово", "закон",
    # Прилагательные
    "правий", "лівий", "вірний", "точний",
    "ясний", "темний", "світлий", "теплий", "холодний", "мокрий",
    "сухий", "чистий", "брудний", "свіжий", "гострий", "тупий",
    "м'який", "твердий", "гладкий", "гнучкий", "жорсткий", "міцний",
    "тихий", "гучний", "швидкий", "повільний",
    "сучасний", "давній", "внутрішній", "зовнішній",
    "верхній", "нижній", "правильний", "хибний", "дивний", "звичайний",
    "особливий", "загальний", "особистий", "науковий", "технічний",
    # Наречия
    "дуже", "досить", "вельми", "надзвичайно", "цілком",
    "зовсім", "цілковито", "майже", "приблизно", "абсолютно", "повністю",
    "значно", "суттєво", "помітно", "явно", "очевидно", "мабуть",
    "можливо", "дійсно", "безсумнівно", "безумовно",
    "постійно", "регулярно", "часто", "рідко", "іноді", "зазвичай",
]


def _parse_wiktionary_synonyms(content: str, section_name: str) -> list[str]:
    """Парсинг секции синонимов из wiki-разметки."""
    syns: list[str] = []
    in_section = False
    for line in content.split("\n"):
        if section_name.lower() in line.lower() and "====" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("====") or line.startswith("==="):
                break
            # Извлекаем слова из [[слово]]
            matches = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', line)
            for m in matches:
                w = m.strip()
                if w and _is_good_cyrillic(w):
                    syns.append(w)
    return syns


def fetch_wiktionary_synonyms(
    api_url: str,
    seeds: list[str],
    section_name: str = "Синонимы",
) -> dict[str, list[str]]:
    """
    Получение синонимов из Wiktionary API (RU или UK).
    """
    lang = "RU" if "ru." in api_url else "UK"
    print(f"  [{lang} Wikt] Запрос для {len(seeds)} слов...")
    result: dict[str, list[str]] = {}
    errors = 0

    for i, word in enumerate(seeds):
        if i % 30 == 0 and i > 0:
            print(f"    ... {i}/{len(seeds)} обработано, найдено {len(result)}")
        try:
            params = urllib.parse.urlencode({
                "action": "query",
                "titles": word,
                "prop": "revisions",
                "rvprop": "content",
                "format": "json",
                "rvslots": "main",
            })
            url = f"{api_url}?{params}"
            data = _fetch_json(url, timeout=10)
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if pid == "-1":
                    continue
                revs = page.get("revisions", [])
                if not revs:
                    continue
                content = revs[0].get("slots", {}).get("main", {}).get("*", "")
                syns = _parse_wiktionary_synonyms(content, section_name)
                if syns:
                    # Фильтруем дубликаты и само слово
                    clean = [s for s in syns if s.lower() != word.lower()]
                    if clean:
                        result[word] = clean[:MAX_SYNS_PER_WORD]
            time.sleep(API_DELAY)
        except Exception:
            errors += 1
            time.sleep(0.5)

    print(f"  [{lang} Wikt] Получено: {len(result)} слов, ошибок: {errors}")
    return result


# ═══════════════════════════════════════════════════════════════
#  ОБЪЕДИНЕНИЕ И ГЕНЕРАЦИЯ
# ═══════════════════════════════════════════════════════════════

def merge_dicts(*dicts: dict[str, list[str]]) -> dict[str, list[str]]:
    """Объединение нескольких словарей синонимов."""
    merged: dict[str, list[str]] = {}
    for d in dicts:
        for word, syns in d.items():
            w = word.strip().lower() if all(c.isascii() for c in word) else word.strip()
            if w in merged:
                # Добавляем уникальные
                existing = set(merged[w])
                for s in syns:
                    if s not in existing:
                        merged[w].append(s)
                        existing.add(s)
            else:
                merged[w] = list(syns)
            # Ограничиваем
            merged[w] = merged[w][:MAX_SYNS_PER_WORD]
    return merged


def write_output(en: dict, ru: dict, uk: dict, path: Path) -> None:
    """Запись результата в Python-файл."""
    print(f"\n  Запись в {path}...")

    lines = [
        '"""',
        "Massive synonym database — auto-generated from open sources.",
        "",
        "Sources:",
        "  - Moby Thesaurus (public domain, Grady Ward 1996)",
        "  - Datamuse API (free, attribution requested)",
        "  - RU Wiktionary (CC BY-SA 3.0)",
        "  - UK Wiktionary (CC BY-SA 3.0)",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"EN: {len(en)} root words",
        f"RU: {len(ru)} root words",
        f"UK: {len(uk)} root words",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# ═══════════════════════════════════════════════════════════",
        "#  ENGLISH SYNONYMS",
        "# ═══════════════════════════════════════════════════════════",
        "",
    ]

    # EN — пишем кусками для читаемости
    lines.append("EN_SYNONYMS: dict[str, list[str]] = {")
    for word in sorted(en.keys()):
        syns = en[word]
        lines.append(f"    {word!r}: {syns!r},")
    lines.append("}")
    lines.append("")

    # RU
    lines.append("# ═══════════════════════════════════════════════════════════")
    lines.append("#  RUSSIAN SYNONYMS")
    lines.append("# ═══════════════════════════════════════════════════════════")
    lines.append("")
    lines.append("RU_SYNONYMS: dict[str, list[str]] = {")
    for word in sorted(ru.keys()):
        syns = ru[word]
        lines.append(f"    {word!r}: {syns!r},")
    lines.append("}")
    lines.append("")

    # UK
    lines.append("# ═══════════════════════════════════════════════════════════")
    lines.append("#  UKRAINIAN SYNONYMS")
    lines.append("# ═══════════════════════════════════════════════════════════")
    lines.append("")
    lines.append("UK_SYNONYMS: dict[str, list[str]] = {")
    for word in sorted(uk.keys()):
        syns = uk[word]
        lines.append(f"    {word!r}: {syns!r},")
    lines.append("}")
    lines.append("")

    # Unified accessor
    lines.append("")
    lines.append("SYNONYMS: dict[str, dict[str, list[str]]] = {")
    lines.append('    "en": EN_SYNONYMS,')
    lines.append('    "ru": RU_SYNONYMS,')
    lines.append('    "uk": UK_SYNONYMS,')
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def get_synonyms(word: str, lang: str = 'en') -> list[str]:")
    lines.append('    """Get synonyms for a word in the given language."""')
    lines.append("    db = SYNONYMS.get(lang, {})")
    lines.append("    # Try exact match, then lowercase")
    lines.append("    result = db.get(word) or db.get(word.lower(), [])")
    lines.append("    return list(result)")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    size_kb = os.path.getsize(path) / 1024
    print(f"  Записано: {size_kb:.0f} KB")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    fast = "--fast" in sys.argv
    print("=" * 64)
    print("  ГЕНЕРАЦИЯ МАССИВНЫХ СЛОВАРЕЙ СИНОНИМОВ")
    print("=" * 64)

    # ── 1. Moby Thesaurus (EN) ──
    print("\n[1/4] Moby Thesaurus (public domain)...")
    moby = fetch_moby_thesaurus()

    # ── 2. Datamuse API (EN) ──
    if fast:
        print("\n[2/4] Datamuse — пропущено (--fast)")
        datamuse = {}
    else:
        print(f"\n[2/4] Datamuse API ({len(_EN_SEEDS)} seed-слов)...")
        datamuse = fetch_datamuse_synonyms(_EN_SEEDS)

    # ── 3. RU Wiktionary ──
    if fast:
        print("\n[3/4] RU Wiktionary — пропущено (--fast)")
        ru_wikt = {}
    else:
        print(f"\n[3/4] RU Wiktionary ({len(_RU_SEEDS)} seed-слов)...")
        ru_wikt = fetch_wiktionary_synonyms(
            RU_WIKT_API, _RU_SEEDS, section_name="Синонимы"
        )

    # ── 4. UK Wiktionary ──
    if fast:
        print("\n[4/4] UK Wiktionary — пропущено (--fast)")
        uk_wikt = {}
    else:
        print(f"\n[4/4] UK Wiktionary ({len(_UK_SEEDS)} seed-слов)...")
        uk_wikt = fetch_wiktionary_synonyms(
            UK_WIKT_API, _UK_SEEDS, section_name="Синоніми"
        )

    # ── Объединяем EN ──
    en_combined = merge_dicts(moby, datamuse)

    # ── Записываем ──
    write_output(en_combined, ru_wikt, uk_wikt, OUTPUT)

    # ── Статистика ──
    en_syns = sum(len(v) for v in en_combined.values())
    ru_syns = sum(len(v) for v in ru_wikt.values())
    uk_syns = sum(len(v) for v in uk_wikt.values())

    print("\n" + "=" * 64)
    print("  ИТОГО:")
    print(f"    EN: {len(en_combined):>6} слов, {en_syns:>8} синонимов")
    print(f"    RU: {len(ru_wikt):>6} слов, {ru_syns:>8} синонимов")
    print(f"    UK: {len(uk_wikt):>6} слов, {uk_syns:>8} синонимов")
    print(f"    ВСЕГО: {len(en_combined) + len(ru_wikt) + len(uk_wikt)} слов")
    print(f"    Файл: {OUTPUT}")
    print("=" * 64)


if __name__ == "__main__":
    main()
