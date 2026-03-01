"""Полная диагностика качества: детекция AI + гуманизация EN/RU/UK."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import texthumanize as th

# ── Тексты для тестирования ──────────────────────────────────

AI_TEXTS = {
    "en": (
        "Artificial intelligence has fundamentally transformed the landscape of modern technology. "
        "The implementation of machine learning algorithms has enabled unprecedented capabilities "
        "in data processing and pattern recognition. Furthermore, the integration of neural networks "
        "has significantly enhanced the accuracy of predictive models. It is important to note that "
        "these advancements have far-reaching implications for various industries and sectors. "
        "The continuous evolution of AI systems promises to reshape how we approach complex problems "
        "and drive innovation across multiple domains."
    ),
    "ru": (
        "Искусственный интеллект кардинально трансформировал ландшафт современных технологий. "
        "Внедрение алгоритмов машинного обучения обеспечило беспрецедентные возможности в обработке "
        "данных и распознавании паттернов. Более того, интеграция нейронных сетей значительно "
        "повысила точность предиктивных моделей. Важно отметить, что данные достижения имеют "
        "далеко идущие последствия для различных отраслей. Непрерывное развитие систем ИИ "
        "обещает кардинально изменить подходы к решению сложных задач."
    ),
    "uk": (
        "Штучний інтелект кардинально трансформував ландшафт сучасних технологій. "
        "Впровадження алгоритмів машинного навчання забезпечило безпрецедентні можливості "
        "в обробці даних та розпізнаванні патернів. Більш того, інтеграція нейронних мереж "
        "значно підвищила точність предиктивних моделей. Важливо зазначити, що дані досягнення "
        "мають далекосяжні наслідки для різних галузей. Безперервний розвиток систем ШІ "
        "обіцяє кардинально змінити підходи до розв'язання складних завдань."
    ),
}

HUMAN_TEXTS = {
    "en": (
        "So I was walking home yesterday and it hit me — we really take technology for granted. "
        "Like, my grandma still can't figure out how to send a text message, but my 5-year-old "
        "nephew is already making YouTube videos. Crazy, right? Anyway, the point is that AI "
        "isn't some far-off sci-fi thing anymore. It's here. And honestly? I'm not sure if "
        "that's exciting or terrifying. Maybe both."
    ),
    "ru": (
        "Короче, шёл я вчера домой и вдруг подумал — мы ведь реально воспринимаем технологии "
        "как должное. Бабушка моя до сих пор не может разобраться, как SMS отправить, а "
        "пятилетний племянник уже ролики на Ютуб снимает. Бред какой-то, да? Ну вот, собственно "
        "к чему я — ИИ это уже не какая-то фантастика далёкого будущего. Он уже тут. И чес слово, "
        "не знаю, радоваться или бояться. Наверное, и то и другое."
    ),
    "uk": (
        "Коротше, йшов я вчора додому і раптом подумав — ми ж реально сприймаємо технології "
        "як належне. Бабуся моя досі не може розібратися, як СМС відправити, а п'ятирічний "
        "племінник вже ролики на Ютуб знімає. Маячня якась, так? Ну ось, власне до чого я — "
        "ШІ це вже не якась фантастика далекого майбутнього. Він вже тут. І чесне слово, "
        "не знаю, радіти чи боятися. Мабуть, і те й інше."
    ),
}

print("=" * 70)
print("ДІАГНОСТИКА: Детекція AI vs Human")
print("=" * 70)

for lang in ["en", "ru", "uk"]:
    ai_det = th.detect_ai(AI_TEXTS[lang], lang=lang)
    hu_det = th.detect_ai(HUMAN_TEXTS[lang], lang=lang)
    
    ai_score = ai_det.get("combined_score", ai_det.get("score", 0))
    hu_score = hu_det.get("combined_score", hu_det.get("score", 0))
    separation = ai_score - hu_score
    
    print(f"\n{'─'*40}")
    print(f"  {lang.upper()}: AI={ai_score:.3f}  Human={hu_score:.3f}  Δ={separation:.3f}")
    print(f"  AI verdict: {ai_det.get('verdict')}  |  Human verdict: {hu_det.get('verdict')}")
    
    # Подробные метрики
    ai_m = ai_det.get("metrics", {})
    hu_m = hu_det.get("metrics", {})
    print(f"  {'Метрика':<25} {'AI':>7} {'Human':>7} {'Δ':>7}")
    for k in ["entropy", "burstiness", "vocabulary", "zipf", "stylometry", 
              "ai_patterns", "punctuation", "coherence", "grammar_perfection",
              "opening_diversity", "readability_consistency", "rhythm"]:
        a = ai_m.get(k, 0)
        h = hu_m.get(k, 0)
        flag = " ←" if abs(a - h) < 0.1 else ""
        print(f"  {k:<25} {a:7.3f} {h:7.3f} {a-h:+7.3f}{flag}")

    # Компоненты ансамбля
    print(f"  --- Ансамбль ---")
    print(f"  heuristic:  AI={ai_det.get('heuristic_score',0):.3f}  Human={hu_det.get('heuristic_score',0):.3f}")
    print(f"  stat:       AI={ai_det.get('stat_probability',0):.3f}  Human={hu_det.get('stat_probability',0):.3f}")
    print(f"  neural:     AI={ai_det.get('neural_probability',0):.3f}  Human={hu_det.get('neural_probability',0):.3f}")

print("\n" + "=" * 70)
print("ДІАГНОСТИКА: Гуманизация")
print("=" * 70)

for lang in ["en", "ru", "uk"]:
    txt = AI_TEXTS[lang]
    det_before = th.detect_ai(txt, lang=lang)
    score_before = det_before.get("combined_score", 0)
    
    # intensity 60
    r60 = th.humanize(txt, lang=lang, intensity=60)
    d60 = th.detect_ai(r60.text, lang=lang)
    s60 = d60.get("combined_score", 0)
    
    # intensity 80
    r80 = th.humanize(txt, lang=lang, intensity=80)
    d80 = th.detect_ai(r80.text, lang=lang)
    s80 = d80.get("combined_score", 0)
    
    # adaptive
    r_ad = th.humanize_until_human(txt, lang=lang, intensity=50, target_score=0.35, max_attempts=3, strategy="adaptive")
    d_ad = th.detect_ai(r_ad.text, lang=lang)
    s_ad = d_ad.get("combined_score", 0)
    
    print(f"\n{'─'*40}")
    print(f"  {lang.upper()}: Оригинал={score_before:.3f}")
    print(f"    intensity=60:  {s60:.3f}  (Δ={score_before-s60:+.3f})  ratio={r60.change_ratio:.1%}")
    print(f"    intensity=80:  {s80:.3f}  (Δ={score_before-s80:+.3f})  ratio={r80.change_ratio:.1%}")
    print(f"    adaptive:      {s_ad:.3f}  (Δ={score_before-s_ad:+.3f})  ratio={r_ad.change_ratio:.1%}")
    
    # Покажем что изменилось по метрикам для лучшего варианта
    best = min([(s60, d60, "60"), (s80, d80, "80"), (s_ad, d_ad, "adapt")], key=lambda x: x[0])
    print(f"    Лучший: intensity={best[2]}, score={best[0]:.3f}")
    bm = best[1].get("metrics", {})
    om = det_before.get("metrics", {})
    for k in ["entropy", "burstiness", "vocabulary", "ai_patterns", "stylometry",
              "grammar_perfection", "opening_diversity", "rhythm",
              "punctuation", "coherence", "readability_consistency"]:
        print(f"      {k}: {om.get(k,0):.3f} → {bm.get(k,0):.3f}")
    # Показать ансамбль для лучшего
    print(f"    Ансамбль: heuristic={best[1].get('heuristic_score',0):.3f}  stat={best[1].get('stat_probability',0):.3f}  neural={best[1].get('neural_probability',0):.3f}")

print("\nDone.")
