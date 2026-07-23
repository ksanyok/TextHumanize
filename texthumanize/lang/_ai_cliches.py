"""Клише, характерные для текстов, написанных ИИ.

Детектор уже штрафует эти обороты (см. ``HEDGING_PATTERNS`` в
``detector``), но в словарях языковых пакетов их не было — то есть
гуманизатор не умел их убирать. Из-за этого самые узнаваемые ИИ-зачины
(«In today's rapidly evolving digital landscape», «В современном мире…»)
переживали обработку, и оценка почти не менялась.

Здесь собраны именно *зачины и связки-штампы*, а не канцелярит: канцелярит
живёт в ``bureaucratic`` / ``bureaucratic_phrases`` каждого пакета. Записи
отсюда подмешиваются в ``bureaucratic_phrases`` при сборке ``LANGUAGES``
(см. ``lang/__init__.py``), поэтому их подхватывают и Python, и экспорт в
JS/PHP-порты без отдельной логики.

Формат: ``{фраза: [варианты замены]}``. Пустая строка среди вариантов
означает «допустимо просто удалить» — для зачинов это чаще всего самая
человечная правка. Ключи в нижнем регистре; регистр восстанавливается при
замене.

ВАЖНО про флективные языки (ru, uk, pl, de). Замена обязана сохранять
управление: следующее за фразой слово остаётся в исходном падеже, потому
что мы его не трогаем. Поэтому

    "стал неотъемлемой частью" → "прочно вошёл в"

недопустимо: «частью» требует родительного («частью нашей жизни»), а
«вошёл в» — винительного, и получается «вошёл в нашей жизни». По той же
причине «играет ключевую роль в» нельзя менять на «определяет»
(предложный → винительный) и «широкий спектр» на «разные» (родительный →
именительный). Если подходящей замены с тем же управлением нет, лучше
оставить один вариант, чем добавить грамматически ломающий.
"""

from __future__ import annotations

# ── Английский ──────────────────────────────────────────────
AI_CLICHES_EN: dict[str, list[str]] = {
    # Зачины «в наше время»
    "in today's rapidly evolving digital landscape": ["these days", "right now", ""],
    "in today's rapidly evolving world": ["these days", "right now", ""],
    "in today's fast-paced world": ["these days", "right now", ""],
    "in today's digital landscape": ["these days", "online today", ""],
    "in today's digital age": ["these days", "now", ""],
    "in today's world": ["these days", "now", ""],
    "in today's society": ["these days", "now", ""],
    "in the modern world": ["these days", "now", ""],
    "in an increasingly digital world": ["as more moves online", "these days", ""],
    "in the ever-evolving landscape of": ["in", "across"],
    "in the ever-changing world of": ["in", "across"],
    "in the realm of": ["in", "when it comes to"],
    "in the world of": ["in", "when it comes to"],
    "in the field of": ["in"],
    # Хеджирование
    "it is important to note that": ["note that", "importantly,", ""],
    "it is worth noting that": ["worth noting,", "note that", ""],
    "it is worth mentioning that": ["worth mentioning,", ""],
    "it is essential to understand that": ["understand that", ""],
    "it is crucial to recognize that": ["recognise that", ""],
    "it should be emphasized that": ["notably,", ""],
    "one must consider": ["consider", "think about"],
    "it is undeniable that": ["clearly,", ""],
    # Штампы-усилители
    "plays a crucial role in": ["matters for", "drives", "is central to"],
    "plays a vital role in": ["matters for", "drives", "is central to"],
    "plays a pivotal role in": ["matters for", "drives", "is central to"],
    "plays a significant role in": ["matters for", "shapes"],
    "has become an integral part of": ["is now part of", "is now built into"],
    "is an integral part of": ["is part of", "is built into"],
    "a testament to": ["a sign of", "proof of"],
    "stands as a testament to": ["shows", "proves"],
    "serves as a reminder": ["is a reminder", "reminds us"],
    "a wide range of": ["many", "plenty of", "all sorts of"],
    "a wide variety of": ["many", "plenty of", "all sorts of"],
    "a myriad of": ["many", "countless"],
    "a plethora of": ["plenty of", "lots of"],
    "an array of": ["a set of", "several"],
    "navigating the complexities of": ["working through", "dealing with"],
    "navigate the complexities of": ["work through", "deal with"],
    "delve deeper into": ["look closer at", "dig into"],
    "delve into": ["look at", "dig into"],
    "shed light on": ["clarify", "explain", "show"],
    "pave the way for": ["open the door to", "lead to", "make room for"],
    "at the forefront of": ["leading", "ahead in"],
    "unlock the potential of": ["get more out of", "make the most of"],
    "unlock unprecedented opportunities": ["open up new options", "create new openings"],
    "harness the power of": ["use", "put to work"],
    "revolutionize the way": ["change how", "reshape how"],
    "transform the way": ["change how", "reshape how"],
    "striking the right balance": ["getting the balance right", "finding a balance"],
    "in an era where": ["now that", "when"],
    "the rise of": ["the spread of", "the growth of"],
    # Концовки
    "in conclusion,": ["so,", "all told,", ""],
    "to sum up,": ["in short,", ""],
    "in summary,": ["in short,", ""],
    "ultimately,": ["in the end,", ""],
    "all in all,": ["overall,", ""],
    "at the end of the day,": ["in the end,", ""],
    # Ассистентский регистр (доминирует у чат-моделей 2025-2026)
    "great question": ["", "good point"],
    "great question!": [""],
    "let's dive in": ["", "here goes"],
    "let's dive into": ["let's look at"],
    "let's break it down": [""],
    "let's break down": ["here's"],
    "let's explore": ["look at"],
    "here's the thing": [""],
    "here's the deal": [""],
    "here are the key": ["the main"],
    "here are a few": ["a few"],
    "i hope this helps": [""],
    "hope this helps": [""],
    "feel free to": ["you can"],
    "rest assured": [""],
    "the good news is": [""],
    "in this article, we'll": ["this covers"],
    "in this guide, we'll": ["this covers"],
    "buckle up": [""],
    "you're not alone": [""],
    "that being said,": ["still,", ""],
    "when it comes to": ["for", "with"],
}

# ── Русский ─────────────────────────────────────────────────
AI_CLICHES_RU: dict[str, list[str]] = {
    "в современном мире стремительно развивающихся технологий": [
        "сегодня", "сейчас", ""],
    "в современном быстро меняющемся мире": ["сегодня", "сейчас", ""],
    "в современном цифровом мире": ["сегодня", "сейчас", ""],
    "в современном мире": ["сегодня", "сейчас", ""],
    "в современном обществе": ["сегодня", "сейчас", ""],
    "в наши дни": ["сегодня", "сейчас", ""],
    "в эпоху цифровых технологий": ["сейчас", "сегодня", ""],
    "в условиях стремительного развития": ["на фоне быстрого роста", "пока всё быстро меняется"],
    "стремительно развивающийся": ["быстрорастущий", "быстро меняющийся"],
    "стремительно развивающихся": ["быстрорастущих", "быстро меняющихся"],
    # Хеджирование
    "важно отметить, что": ["отмечу, что", "заметим:", ""],
    "следует отметить, что": ["отмечу, что", "заметим:", ""],
    "необходимо отметить, что": ["отмечу, что", ""],
    "стоит отметить, что": ["отмечу, что", "заметим:", ""],
    "стоит подчеркнуть, что": ["подчеркну:", ""],
    "нельзя не отметить": ["отмечу", "замечу"],
    "важно понимать, что": ["поймите:", "суть в том, что", ""],
    "необходимо учитывать, что": ["учтите:", ""],
    # Штампы
    # «роль в чём» — предложный падеж, замена его сохраняет
    "играет ключевую роль в": ["многое решает в", "многое значит в"],
    "играет важную роль в": ["многое значит в", "заметно сказывается в"],
    "играет решающую роль в": ["решает дело в", "многое решает в"],
    # «частью чего» — родительный падеж
    "стал неотъемлемой частью": ["стал частью", "давно стал частью"],
    "стала неотъемлемой частью": ["стала частью", "давно стала частью"],
    "является неотъемлемой частью": ["остаётся частью", "давно стал частью"],
    # «спектр чего» — родительный, поэтому «разные» не подходит
    "широкий спектр": ["много", "множество", "масса"],
    "широкий круг": ["много", "множество"],
    "целый ряд": ["несколько", "много"],
    "открывает новые горизонты": ["даёт новые возможности", "открывает новое"],
    "открывает беспрецедентные возможности": ["даёт новые возможности", "открывает новое"],
    "раскрывать беспрецедентные возможности": ["находить новые возможности"],
    "позволяет раскрыть потенциал": ["помогает раскрыть потенциал"],
    "в конечном итоге": ["в итоге", "в конце концов", ""],
    "таким образом,": ["значит,", "выходит,", ""],
    "подводя итог,": ["короче,", "итого:", ""],
    "в заключение,": ["напоследок,", ""],
    "в заключение": ["напоследок", ""],
    # Ассистентский регистр
    "отличный вопрос": ["", "хороший вопрос"],
    "отличный вопрос!": [""],
    "давайте разберёмся": ["разберёмся"],
    "давайте разберемся": ["разберёмся"],
    "давайте рассмотрим": ["рассмотрим"],
    "надеюсь, это поможет": [""],
    "надеюсь, это было полезно": [""],
    "не переживайте": [""],
    "вот в чём дело": [""],
    "хорошая новость в том, что": [""],
    "стоит помнить, что": ["помните:", ""],
    "когда речь идёт о": ["для", "что касается"],
    "когда дело доходит до": ["для", "что касается"],
    "поиск правильного баланса": ["баланс", "поиск баланса"],
    # «изучить что» — винительный; «разобраться в чём» его бы сломало
    "более глубоко изучить": ["изучить глубже", "внимательнее изучить"],
    "необходимо более глубоко изучить": ["стоит изучить глубже", "надо изучить внимательнее"],
}

# ── Украинский ──────────────────────────────────────────────
AI_CLICHES_UK: dict[str, list[str]] = {
    "у сучасному світі стрімкого розвитку технологій": ["сьогодні", "зараз", ""],
    "у сучасному швидкозмінному світі": ["сьогодні", "зараз", ""],
    "у сучасному цифровому світі": ["сьогодні", "зараз", ""],
    "у сучасному світі": ["сьогодні", "зараз", ""],
    "у сучасному суспільстві": ["сьогодні", "зараз", ""],
    "в епоху цифрових технологій": ["зараз", "сьогодні", ""],
    "стрімкого розвитку": ["швидкого зростання", "швидких змін"],
    "стрімко розвивається": ["швидко зростає", "швидко змінюється"],
    # Хеджування
    "важливо зазначити, що": ["зазначу, що", "звернімо увагу:", ""],
    "слід зазначити, що": ["зазначу, що", "звернімо увагу:", ""],
    "варто зазначити, що": ["зазначу, що", ""],
    "необхідно зазначити, що": ["зазначу, що", ""],
    "варто підкреслити, що": ["підкреслю:", ""],
    "важливо розуміти, що": ["зрозумійте:", "суть у тому, що", ""],
    # Штампи
    "відіграє ключову роль у": ["багато вирішує у", "багато важить у"],
    "відіграє важливу роль у": ["багато важить у", "помітно позначається у"],
    "став невід'ємною частиною": ["став частиною", "давно став частиною"],
    "стала невід'ємною частиною": ["стала частиною", "давно стала частиною"],
    "є невід'ємною частиною": ["залишається частиною", "давно став частиною"],
    "широкий спектр": ["багато", "безліч"],
    "низку переваг": ["кілька переваг", "чимало переваг"],
    "відкриває нові горизонти": ["дає нові можливості", "відкриває нове"],
    "зрештою,": ["врешті-решт,", ""],
    "таким чином,": ["отже,", "виходить,", ""],
    "підсумовуючи,": ["коротко:", ""],
    "на завершення,": ["наостанок,", ""],
    "на завершення": ["наостанок", ""],
}

# ── Немецкий ────────────────────────────────────────────────
AI_CLICHES_DE: dict[str, list[str]] = {
    "in der heutigen schnelllebigen digitalen landschaft": ["heute", "derzeit", ""],
    "in der heutigen sich schnell entwickelnden digitalen landschaft": [
        "heute", "derzeit", ""],
    "in der heutigen digitalen welt": ["heute", "derzeit", ""],
    "in der heutigen zeit": ["heute", "derzeit", ""],
    "in der heutigen welt": ["heute", "derzeit", ""],
    "in der heutigen gesellschaft": ["heute", "derzeit", ""],
    "im digitalen zeitalter": ["heute", "derzeit", ""],
    "sich schnell entwickelnden": ["schnell wachsenden", "sich wandelnden"],
    # Absicherung
    "es ist wichtig zu beachten, dass": ["beachte:", "wichtig:", ""],
    "es ist wichtig zu betonen, dass": ["betont sei:", ""],
    "es sei darauf hingewiesen, dass": ["übrigens:", ""],
    "es ist erwähnenswert, dass": ["erwähnenswert:", ""],
    # Floskeln
    "spielt eine entscheidende rolle": ["ist entscheidend", "entscheidet viel"],
    "spielt eine wichtige rolle": ["ist wichtig", "zählt"],
    "spielt eine zentrale rolle": ["steht im Zentrum", "ist zentral"],
    # «Bestandteil» верховодит родительным — замена его сохраняет
    "ist ein integraler bestandteil": ["ist fester Bestandteil", "ist ein Teil"],
    "eine vielzahl von": ["viele", "etliche"],
    "ein breites spektrum an": ["viele", "etliche"],
    "vielfältige auswirkungen": ["viele Folgen", "unterschiedliche Folgen"],
    "vielfältigen auswirkungen": ["vielen Folgen", "unterschiedlichen Folgen"],
    "eröffnet neue möglichkeiten": ["schafft neue Optionen", "öffnet Türen"],
    "zusammenfassend lässt sich sagen, dass": ["kurz gesagt:", "unterm Strich:", ""],
    "zusammenfassend": ["kurz gesagt", "unterm Strich", ""],
    "letztendlich": ["am Ende", ""],
    "abschließend": ["zum Schluss", ""],
}

# ── Испанский ───────────────────────────────────────────────
AI_CLICHES_ES: dict[str, list[str]] = {
    "en el mundo actual de tecnologías en rápida evolución": ["hoy", "ahora", ""],
    "en el mundo actual, en rápida evolución": ["hoy", "ahora", ""],
    "en el mundo digital actual": ["hoy", "ahora", ""],
    "en el mundo actual": ["hoy", "ahora", ""],
    "en la sociedad actual": ["hoy", "ahora", ""],
    "en la era digital": ["hoy", "ahora", ""],
    "en rápida evolución": ["que cambia rápido", "en pleno cambio"],
    # Matización
    "es importante señalar que": ["ojo:", "conviene señalar que", ""],
    "es importante destacar que": ["destaco que", "conviene destacar que", ""],
    "cabe señalar que": ["señalo que", ""],
    "cabe destacar que": ["destaco que", ""],
    "es fundamental comprender que": ["hay que entender que", ""],
    # Muletillas
    "desempeña un papel crucial en": ["es clave en", "pesa mucho en"],
    "desempeña un papel fundamental en": ["es clave en", "pesa mucho en"],
    "juega un papel importante en": ["es importante en", "cuenta en"],
    "se ha convertido en una parte integral de": ["ya forma parte de", "ya está dentro de"],
    "es una parte integral de": ["forma parte de", "está dentro de"],
    "una amplia gama de": ["muchos", "todo tipo de"],
    "una amplia variedad de": ["muchos", "todo tipo de"],
    "un sinfín de": ["muchísimos", "un montón de"],
    "abre nuevas oportunidades": ["abre puertas", "crea opciones nuevas"],
    "en conclusión,": ["en resumen,", "total,", ""],
    "en resumen,": ["resumiendo,", ""],
    "en última instancia,": ["al final,", ""],
    "finalmente,": ["por último,", ""],
}

# ── Польский ────────────────────────────────────────────────
AI_CLICHES_PL: dict[str, list[str]] = {
    "w dzisiejszym szybko zmieniającym się świecie cyfrowym": ["dziś", "teraz", ""],
    "w dzisiejszym szybko zmieniającym się świecie": ["dziś", "teraz", ""],
    "w dzisiejszym cyfrowym świecie": ["dziś", "teraz", ""],
    "w dzisiejszym świecie": ["dziś", "teraz", ""],
    "w dzisiejszych czasach": ["dziś", "teraz", ""],
    "w erze cyfrowej": ["dziś", "teraz", ""],
    "szybko rozwijający się": ["szybko rosnący", "zmieniający się"],
    # Asekuracja
    "warto zauważyć, że": ["zauważmy:", "warto dodać:", ""],
    "należy zauważyć, że": ["zauważmy:", ""],
    "warto podkreślić, że": ["podkreślę:", ""],
    "należy podkreślić, że": ["podkreślę:", ""],
    "ważne jest, aby zrozumieć, że": ["trzeba zrozumieć, że", ""],
    # Frazesy
    "odgrywa kluczową rolę w": ["wiele znaczy w", "wiele decyduje w"],
    "odgrywa istotną rolę w": ["liczy się w", "wiele znaczy w"],
    "stał się nieodłączną częścią": ["stał się częścią", "od dawna jest częścią"],
    "stała się nieodłączną częścią": ["stała się częścią", "od dawna jest częścią"],
    "jest nieodłączną częścią": ["należy do", "jest częścią"],
    "szeroki zakres": ["wiele", "mnóstwo"],
    "szeroką gamę": ["wiele", "mnóstwo"],
    "otwiera nowe możliwości": ["daje nowe opcje", "otwiera drzwi"],
    "podsumowując,": ["krótko mówiąc,", "w skrócie,", ""],
    "ostatecznie,": ["w końcu,", ""],
    "na zakończenie,": ["na koniec,", ""],
}

AI_CLICHES: dict[str, dict[str, list[str]]] = {
    "en": AI_CLICHES_EN,
    "ru": AI_CLICHES_RU,
    "uk": AI_CLICHES_UK,
    "de": AI_CLICHES_DE,
    "es": AI_CLICHES_ES,
    "pl": AI_CLICHES_PL,
}


def merge_into(pack: dict) -> dict:
    """Подмешать клише языка в ``bureaucratic_phrases`` пакета.

    Существующие записи пакета имеют приоритет: они выверены дольше и
    могут быть точнее для конкретного языка.
    """
    cliches = AI_CLICHES.get(pack.get("code", ""))
    if not cliches:
        return pack
    phrases = dict(pack.get("bureaucratic_phrases") or {})
    for key, alts in cliches.items():
        phrases.setdefault(key, list(alts))
    pack["bureaucratic_phrases"] = phrases
    return pack
