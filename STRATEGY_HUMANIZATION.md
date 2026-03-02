# Стратегия улучшения гуманизации TextHumanize

**Дата:** 2026-03-02  
**Версия:** 0.25.0 → 0.26.0+  
**Цель:** Достичь ≥50% evasion rate на собственном детекторе (с 0% текущих), оставаясь 100% offline/zero-dependency библиотекой.

---

## Диагноз: Почему гуманизация не работает

### Корневая проблема
Текущий пайплайн основан на **лексических подменах** (замена слов синонимами). Это не меняет **статистические распределения**, которые детектор реально измеряет:

| Что меняет пайплайн | Что измеряет детектор |
|:---------------------|:---------------------|
| Заменяет "значительный" → "существенный" | Энтропию (Shannon) — синонимы имеют схожую частотность |
| Удаляет "более того", "кроме того" | Burstiness (CV длин предложений) — длины не меняются |
| Добавляет дискурс-маркеры | Перплексию — шаблонные вставки предсказуемы |
| Заменяет AI-слова | Zipf-распределение — синонимы в тех же частотных диапазонах |

### Архитектура детектора — 7 "сильных" метрик
Детектор использует 3-уровневую агрегацию: weighted sum (40%) + strong-signal (40%) + majority voting (20%). Ключевые 7 метрик для strong-signal:

| Метрика | Вес | AI-скор | Текущий эффект пайплайна |
|:--------|:----|:--------|:------------------------|
| **pattern** | 0.20 | ~0.72 | Частично — удаляет коннекторы, но не hedging и enumeration |
| **burstiness** | 0.14 | ~0.68 | Слабо — target CV=0.35, нужно ≥0.55 |
| **stylometry** | 0.09 | ~0.55 | Слабо — мало записей в словаре упрощений |
| **voice** | 0.08 | ~0.76 | Очень слабо — voice имеет лучшую разделяющую способность |
| **entity** | 0.07 | ~0.62 | Никак — генерики не удаляются, конкретика не добавляется |
| **opening** | 0.06 | ~0.65 | Частично — только consecutive starts, не глобальная статистика |
| **grammar** | 0.05 | ~0.58 | Слабо — грамматика/readability этапы отменяют entropy injection |

---

## Стратегия: 3 фазы

### Фаза 1: Detector-Feedback Pass (P0 — максимальный ROI)

**Идея:** Добавить финальный этап пайплайна `_detector_feedback_pass()`, который:
1. Запускает детектор на текущем результате
2. Определяет какие из 7 strong-signal метрик > 0.55
3. Применяет **точечные** коррекции для каждой проблемной метрики

```
if pattern > 0.55:    → удалить hedging-конструкции, neutralize enumeration
if burstiness > 0.55: → split/merge до CV > 0.55
if voice > 0.55:      → конвертировать 2+ passive→active, inject pronouns
if opening > 0.55:    → fronting adverbials для повторяющихся стартеров
if grammar > 0.55:    → inject 2 фрагмента + 1 informal punct
if discourse > 0.55:  → удалить conclusion/intro markers
if stylometry > 0.55: → shorten 5 longest words, inject stop-words
```

**Преимущество:** В отличие от текущего `humanize_until_human()` (который перезапускает весь пайплайн), feedback pass **целенаправленно** исправляет конкретные слабые места.

**Реализация:** Pure Python, zero dependencies, ~300 строк. Интеграция — новый pipeline stage после `validation`, перед `restore`.

### Фаза 2: Структурные трансформации (P1)

Изменения, которые работают на уровне **структуры текста**, а не слов:

1. **Burstiness engineering:**
   - Raise target CV: 0.35 → 0.55-0.60
   - Асимметричный split: 30/70 вместо 50/50
   - Гарантировать ≥15% "экстремальных" предложений (≤5 слов или ≥30 слов)
   - Protect entropy-injected fragments от grammar stage

2. **Voice transformation:**
   - Увеличить probability SyntaxRewriter для voice transforms: 0.3 → 0.6+
   - Personal pronoun injection для web/blog профилей
   - Nominalization→verb словарь: 50 → 300+ записей
   - Расширить на RU/UK/DE

3. **Entity specificity:**
   - Generic quantifier zapper: "various" → "several" → "[X] like A and B"
   - Personal reference injection для casual профилей
   - Hedging word reduction

4. **Opening diversity:**
   - Global first-word histogram enforcement (uniqueness ≥ 0.6)
   - Subject-demotion transforms (subject-first ≤ 50%)
   - Adverbial fronting для repetitive starters

5. **Discourse structure:**
   - Conclusion/intro marker deletion
   - Body paragraph length variance
   - List de-formatting (bullets → prose)

### Фаза 3: Статистическая оптимизация (P2)

Тонкая настройка статистических распределений:

1. **Frequency-aware synonym selection:**
   - Выбирать замены из **разных** частотных диапазонов (rank 5000-15000 вместо rank 500)
   - Это реально меняет энтропию и Zipf-распределение

2. **Rhythm anti-correlation:**
   - Enforce lag-1 autocorrelation < 0.15
   - Чередование S/M/L категорий длин

3. **Perplexity variance:**
   - Style-register mixing внутри текста
   - "Неожиданные" предложения с редкими триграммами символов

4. **Cross-paragraph semantic dedup:**
   - Jaccard > 0.30 между удалёнными предложениями → synonym swap

5. **Readability oscillation:**
   - Не нормализовать readability к среднему, а инжектить variance

---

## Ключевое ограничение

**Все техники выше — pure Python, zero dependencies, offline.** Это наше конкурентное преимущество: ни одна SaaS-библиотека не может работать без интернета и без API-ключей.

Даже без LLM мы можем значительно улучшить гуманизацию через:
- Структурные трансформации (split/merge/reorder sentences)
- Частотно-осведомлённый выбор синонимов
- Detector-in-the-loop feedback
- Статистическое enforcement (measure → correct → re-measure)

**Реалистичная цель:** 40-60% evasion rate на собственном детекторе. Для 90%+ нужен neural paraphraser — но это optional dependency, а не блокер.

---

## Приоритет реализации

| # | Задача | Ожидаемый эффект | Сложность |
|:--|:-------|:-----------------|:----------|
| 1 | Detector feedback pass | -15-20% AI score | Средняя (300 строк) |
| 2 | Hedging-pattern zapper | -5-8% pattern score | Низкая (50 строк) |
| 3 | Burstiness CV raise + fragment protection | -10-15% burstiness score | Низкая (100 строк) |
| 4 | Voice: aggressive passive→active + pronouns | -20-30% voice score | Средняя (200 строк) |
| 5 | Entity: generic zapper + personal refs | -10-15% entity score | Низкая (100 строк) |
| 6 | Opening: global distribution reshaping | -10% opening score | Средняя (150 строк) |
| 7 | Frequency-aware synonym selection | -5% entropy + vocab | Высокая (300 строк) |
