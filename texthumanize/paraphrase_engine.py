"""Sentence-level paraphrase engine for deep text humanization.

Performs structural rewrites that go beyond word-level synonym substitution:
- Multi-word expression simplification ("in order to" → "to")
- Connector deletion (remove AI-typical discourse markers)
- Perspective rotation ("The study shows X" → "X, as the study shows")
- Clause embedding (merge two sentences into one)
- Sentence type variation (statement → question/fragment)
- Hedging modulation ("clearly demonstrates" → "suggests")
- Information reordering (move adverbials, swap clauses)

Supports EN, RU, UK languages. Zero external dependencies.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Optional

from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  Multi-word expression simplification
# ═══════════════════════════════════════════════════════════════

_MWE_EN: list[tuple[str, str]] = [
    ("in order to", "to"),
    ("in the context of", "about"),
    ("in light of the fact that", "since"),
    ("due to the fact that", "because"),
    ("owing to the fact that", "because"),
    ("on the basis of", "based on"),
    ("with regard to", "about"),
    ("with respect to", "about"),
    ("in terms of", "for"),
    ("in the event that", "if"),
    ("in the case of", "for"),
    ("in spite of the fact that", "although"),
    ("for the purpose of", "to"),
    ("by means of", "by"),
    ("as a result of", "from"),
    ("at the present time", "now"),
    ("at this point in time", "now"),
    ("in the near future", "soon"),
    ("a significant number of", "many"),
    ("a considerable amount of", "much"),
    ("the vast majority of", "most"),
    ("a wide range of", "many"),
    ("a wide variety of", "many"),
    ("an extensive range of", "many"),
    ("it is important to note that", "notably,"),
    ("it is worth noting that", "notably,"),
    ("it should be noted that", "note that"),
    ("it is essential to", "we must"),
    ("it is necessary to", "we need to"),
    ("it is crucial to", "we must"),
    ("it is evident that", "clearly,"),
    ("it is clear that", "clearly,"),
    ("it is undeniable that", "indeed,"),
    ("there is no doubt that", "certainly,"),
    ("it can be argued that", "perhaps"),
    ("it goes without saying that", "of course,"),
    ("has the potential to", "can"),
    ("has the ability to", "can"),
    ("is capable of", "can"),
    ("is able to", "can"),
    ("plays a crucial role in", "matters for"),
    ("plays a pivotal role in", "matters for"),
    ("plays a significant role in", "matters for"),
    ("is a key factor in", "shapes"),
    ("serves as a catalyst for", "drives"),
    ("lays the groundwork for", "prepares for"),
    ("paves the way for", "enables"),
    ("give rise to", "cause"),
    ("take into account", "consider"),
    ("take into consideration", "consider"),
    ("make use of", "use"),
    ("make a contribution to", "contribute to"),
    ("come to the conclusion that", "conclude that"),
    ("reach the conclusion that", "conclude that"),
    ("first and foremost", "first"),
    ("last but not least", "finally"),
    ("in conclusion", "overall"),
    ("to summarize", "overall"),
    ("all things considered", "overall"),
    ("as a consequence", "so"),
    ("as a matter of fact", "actually"),
    ("needless to say", "of course"),
    ("on the other hand", "but"),
    ("at the same time", "also"),
    ("for this reason", "so"),
    ("in addition to this", "also"),
    ("in this regard", "here"),
]

_MWE_RU: list[tuple[str, str]] = [
    ("в связи с тем, что", "потому что"),
    ("в связи с тем что", "потому что"),
    ("в силу того, что", "потому что"),
    ("в силу того что", "потому что"),
    ("по причине того, что", "из-за того что"),
    ("исходя из того, что", "раз"),
    ("вследствие того, что", "из-за того что"),
    ("с целью обеспечения", "чтобы обеспечить"),
    ("для того чтобы", "чтобы"),
    ("с тем чтобы", "чтобы"),
    ("в целях обеспечения", "чтобы"),
    ("необходимо отметить, что", "заметим, что"),
    ("необходимо подчеркнуть, что", "важно, что"),
    ("следует отметить, что", "стоит сказать, что"),
    ("важно понимать, что", "надо понимать:"),
    ("в настоящее время", "сейчас"),
    ("на сегодняшний день", "сегодня"),
    ("в первую очередь", "прежде всего"),
    ("в рамках данного", "в этом"),
    ("представляет собой", "это"),
    ("является ключевым", "важен"),
    ("является одним из", "один из"),
    ("в конечном счёте", "в итоге"),
    ("таким образом", "так"),
    ("вместе с тем", "при этом"),
    ("в частности", "например"),
    ("помимо этого", "ещё"),
    ("кроме того", "ещё"),
    ("более того", "и даже"),
    ("по мнению экспертов", "по оценкам"),
    ("согласно данным", "по данным"),
    ("значительное количество", "много"),
    ("в значительной степени", "во многом"),
    ("на протяжении длительного времени", "долго"),
    ("играет ключевую роль", "важен"),
    ("имеет большое значение", "важно"),
    ("оказывает влияние на", "влияет на"),
    ("оказывает воздействие на", "действует на"),
    ("принимая во внимание", "учитывая"),
    ("с учётом того, что", "раз"),
    # ── Phase 1-2 expansion ──
    ("на основании вышеизложенного", "итак"),
    ("в соответствии с", "по"),
    ("в совокупности с", "вместе с"),
    ("в процессе реализации", "при выполнении"),
    ("на данном этапе", "пока"),
    ("в данном контексте", "тут"),
    ("при всём при том", "и всё же"),
    ("не представляется возможным", "нельзя"),
    ("имеет место быть", "есть"),
    ("осуществлять деятельность", "работать"),
    ("предпринимать действия", "действовать"),
    ("оказывать содействие", "помогать"),
    ("осуществлять контроль", "контролировать"),
    ("обеспечивать реализацию", "выполнять"),
    ("производить оценку", "оценивать"),
    ("выполнять функции", "работать как"),
    ("на регулярной основе", "регулярно"),
    ("в обязательном порядке", "обязательно"),
    ("в кратчайшие сроки", "быстро"),
    ("в должной мере", "достаточно"),
    ("надлежащим образом", "как следует"),
    ("в полной мере", "полностью"),
    ("в той или иной степени", "в какой-то мере"),
    ("тем не менее", "но"),
    ("наряду с этим", "а ещё"),
    ("об этом свидетельствует", "это показывает"),
    ("способствует формированию", "помогает создать"),
    ("обуславливает необходимость", "делает нужным"),
    ("характеризуется наличием", "имеет"),
    ("обладает способностью", "может"),
    ("демонстрирует тенденцию", "склоняется к"),
    ("по мере возможности", "если получится"),
    ("без каких-либо исключений", "без исключений"),
    ("исключительно важным является", "очень важно"),
    ("ключевым аспектом является", "главное тут"),
    ("в контексте рассматриваемой", "если говорить про"),
    ("данный подход позволяет", "так можно"),
    ("вышеуказанный метод", "этот способ"),
    ("нижеследующий перечень", "список ниже"),
    ("в целом и общем", "в общем"),
    ("по существу вопроса", "по делу"),
    ("что касается вопроса", "насчёт"),
    ("в отношении данного", "про это"),
    ("применительно к данному", "для этого"),
    ("как правило", "обычно"),
    ("само собой разумеется", "конечно"),
    ("не вызывает сомнений", "ясно"),
    ("нет никаких сомнений", "ясно, что"),
    ("ввиду вышесказанного", "поэтому"),
    ("сопряжён с определёнными", "связан с кое-какими"),
    ("влечёт за собой", "ведёт к"),
    ("обусловлен рядом факторов", "зависит от нескольких вещей"),
    ("заслуживает особого внимания", "стоит обратить внимание"),
    ("приобретает всё большее значение", "становится важнее"),
    ("выходит на первый план", "становится главным"),
    ("занимает особое место", "стоит особняком"),
    ("носит комплексный характер", "сложный"),
    ("представляется целесообразным", "пожалуй, стоит"),
]

_MWE_UK: list[tuple[str, str]] = [
    ("у зв'язку з тим, що", "тому що"),
    ("у зв'язку з тим що", "тому що"),
    ("внаслідок того, що", "через те що"),
    ("з метою забезпечення", "щоб забезпечити"),
    ("для того щоб", "щоб"),
    ("з тим щоб", "щоб"),
    ("необхідно зазначити, що", "зазначимо, що"),
    ("слід відзначити, що", "варто сказати, що"),
    ("важливо розуміти, що", "треба розуміти:"),
    ("на сьогоднішній день", "сьогодні"),
    ("в першу чергу", "насамперед"),
    ("в рамках даного", "у цьому"),
    ("являє собою", "це"),
    ("є ключовим", "важливий"),
    ("є одним із", "один із"),
    ("таким чином", "так"),
    ("разом з тим", "при цьому"),
    ("зокрема", "наприклад"),
    ("крім того", "ще"),
    ("більш того", "і навіть"),
    ("відіграє ключову роль", "важливий"),
    ("має велике значення", "важливо"),
    ("чинить вплив на", "впливає на"),
    ("зважаючи на те, що", "оскільки"),
    ("значна кількість", "багато"),
    # ── Phase 1-2 expansion ──
    ("на підставі вищевикладеного", "отже"),
    ("відповідно до", "за"),
    ("у сукупності з", "разом з"),
    ("у процесі реалізації", "під час виконання"),
    ("на даному етапі", "поки що"),
    ("у даному контексті", "тут"),
    ("не видається можливим", "не можна"),
    ("має місце бути", "є"),
    ("здійснювати діяльність", "працювати"),
    ("вживати заходів", "діяти"),
    ("надавати сприяння", "допомагати"),
    ("здійснювати контроль", "контролювати"),
    ("забезпечувати реалізацію", "виконувати"),
    ("проводити оцінку", "оцінювати"),
    ("виконувати функції", "працювати як"),
    ("на регулярній основі", "регулярно"),
    ("в обов'язковому порядку", "обов'язково"),
    ("у найкоротші терміни", "швидко"),
    ("належним чином", "як слід"),
    ("повною мірою", "повністю"),
    ("тією чи іншою мірою", "якоюсь мірою"),
    ("тим не менш", "але"),
    ("поряд з цим", "а ще"),
    ("про це свідчить", "це показує"),
    ("сприяє формуванню", "допомагає створити"),
    ("зумовлює необхідність", "робить потрібним"),
    ("характеризується наявністю", "має"),
    ("володіє здатністю", "може"),
    ("демонструє тенденцію", "схиляється до"),
    ("по можливості", "якщо вийде"),
    ("без жодних винятків", "без винятків"),
    ("винятково важливим є", "дуже важливо"),
    ("ключовим аспектом є", "головне тут"),
    ("у контексті розглядуваної", "якщо говорити про"),
    ("даний підхід дозволяє", "так можна"),
    ("вищевказаний метод", "цей спосіб"),
    ("загалом і в цілому", "загалом"),
    ("що стосується питання", "щодо"),
    ("стосовно даного", "про це"),
    ("як правило", "зазвичай"),
    ("само собою зрозуміло", "звісно"),
    ("не викликає сумнівів", "зрозуміло"),
    ("зважаючи на вищесказане", "тому"),
    ("пов'язаний з певними", "пов'язаний з деякими"),
    ("тягне за собою", "веде до"),
    ("заслуговує на особливу увагу", "варто звернути увагу"),
    ("набуває дедалі більшого значення", "стає важливішим"),
    ("виходить на перший план", "стає головним"),
    ("посідає особливе місце", "стоїть окремо"),
    ("має комплексний характер", "складний"),
    ("видається доцільним", "мабуть, варто"),
]

# ── French MWE simplification ───────────────────────────────────

_MWE_FR: list[tuple[str, str]] = [
    ("dans le cadre de", "dans"),
    ("en vue de", "pour"),
    ("afin de", "pour"),
    ("de manière significative", "beaucoup"),
    ("de façon significative", "beaucoup"),
    ("il convient de noter que", "notons que"),
    ("il est important de souligner que", "soulignons que"),
    ("il est essentiel de", "il faut"),
    ("il est nécessaire de", "il faut"),
    ("il est à noter que", "notons que"),
    ("il va sans dire que", "bien sûr,"),
    ("dans un premier temps", "d'abord"),
    ("dans un second temps", "ensuite"),
    ("à l'heure actuelle", "aujourd'hui"),
    ("au jour d'aujourd'hui", "aujourd'hui"),
    ("en ce qui concerne", "pour"),
    ("eu égard à", "vu"),
    ("compte tenu de", "vu"),
    ("en dépit de", "malgré"),
    ("à cet égard", "ici"),
    ("par conséquent", "donc"),
    ("en outre", "aussi"),
    ("de surcroît", "aussi"),
    ("néanmoins", "mais"),
    ("toutefois", "mais"),
    ("par ailleurs", "aussi"),
    ("en définitive", "au final"),
    ("en l'occurrence", "ici"),
    ("dans la mesure où", "puisque"),
    ("au sein de", "dans"),
    ("a pour objectif de", "vise à"),
    ("joue un rôle crucial dans", "compte pour"),
    ("joue un rôle déterminant dans", "pèse sur"),
    ("représente un enjeu majeur", "est important"),
    ("constitue un élément fondamental", "est essentiel"),
    ("un nombre considérable de", "beaucoup de"),
    ("une quantité significative de", "beaucoup de"),
    ("la grande majorité de", "la plupart de"),
]

# ── Spanish MWE simplification ──────────────────────────────────

_MWE_ES: list[tuple[str, str]] = [
    ("en el marco de", "en"),
    ("con el objetivo de", "para"),
    ("con el fin de", "para"),
    ("a fin de", "para"),
    ("de manera significativa", "mucho"),
    ("de forma significativa", "mucho"),
    ("es importante señalar que", "cabe señalar que"),
    ("es necesario destacar que", "destaquemos que"),
    ("es fundamental que", "es clave que"),
    ("es imprescindible", "hay que"),
    ("cabe destacar que", "hay que notar que"),
    ("resulta evidente que", "está claro que"),
    ("no cabe duda de que", "sin duda,"),
    ("en la actualidad", "hoy"),
    ("hoy en día", "hoy"),
    ("en primer lugar", "primero"),
    ("en segundo lugar", "segundo"),
    ("en lo que respecta a", "sobre"),
    ("con respecto a", "sobre"),
    ("en relación con", "sobre"),
    ("a pesar de", "aunque"),
    ("no obstante", "pero"),
    ("sin embargo", "pero"),
    ("por consiguiente", "así que"),
    ("en consecuencia", "por eso"),
    ("además", "también"),
    ("asimismo", "también"),
    ("por otra parte", "además"),
    ("en definitiva", "al final"),
    ("en el ámbito de", "en"),
    ("desempeña un papel fundamental", "es clave"),
    ("desempeña un papel crucial", "es importante"),
    ("constituye un elemento esencial", "es esencial"),
    ("un número significativo de", "muchos"),
    ("una cantidad considerable de", "mucho"),
    ("la gran mayoría de", "la mayoría de"),
    ("tiene como objetivo", "busca"),
    ("por lo tanto", "así que"),
]

# ── German MWE simplification ───────────────────────────────────

_MWE_DE: list[tuple[str, str]] = [
    ("aufgrund der Tatsache, dass", "weil"),
    ("aufgrund der Tatsache dass", "weil"),
    ("im Hinblick auf", "für"),
    ("in Bezug auf", "zu"),
    ("im Rahmen von", "bei"),
    ("zum Zwecke der", "für"),
    ("mit dem Ziel", "um zu"),
    ("in Anbetracht der Tatsache, dass", "da"),
    ("unter Berücksichtigung von", "mit Blick auf"),
    ("es ist wichtig zu beachten, dass", "beachtenswert ist, dass"),
    ("es ist hervorzuheben, dass", "wichtig ist, dass"),
    ("es sei darauf hingewiesen, dass", "hinzuzufügen ist, dass"),
    ("es ist unbestreitbar, dass", "klar ist, dass"),
    ("es steht außer Frage, dass", "zweifellos"),
    ("zum gegenwärtigen Zeitpunkt", "derzeit"),
    ("in der heutigen Zeit", "heute"),
    ("darüber hinaus", "außerdem"),
    ("des Weiteren", "außerdem"),
    ("nichtsdestotrotz", "trotzdem"),
    ("nichtsdestoweniger", "trotzdem"),
    ("demzufolge", "daher"),
    ("infolgedessen", "daher"),
    ("dessen ungeachtet", "trotzdem"),
    ("im Übrigen", "übrigens"),
    ("in erster Linie", "vor allem"),
    ("in diesem Zusammenhang", "hierbei"),
    ("spielt eine entscheidende Rolle", "ist entscheidend"),
    ("spielt eine wesentliche Rolle", "ist wichtig"),
    ("stellt einen wesentlichen Faktor dar", "ist ein wichtiger Faktor"),
    ("eine beträchtliche Anzahl von", "viele"),
    ("eine erhebliche Menge an", "viel"),
    ("die überwiegende Mehrheit der", "die meisten"),
    ("hat zum Ziel", "zielt darauf ab"),
    ("es lässt sich feststellen, dass", "man kann sagen, dass"),
    ("abschließend lässt sich sagen", "zusammenfassend"),
]


# ═══════════════════════════════════════════════════════════════
#  AI-style connector patterns to remove or simplify
# ═══════════════════════════════════════════════════════════════

_CONNECTOR_STRIP_EN = re.compile(
    r"^(Furthermore|Moreover|Additionally|Consequently|Subsequently|"
    r"In addition|What is more|Correspondingly|Importantly|Notably|"
    r"Significantly|Specifically|Essentially|Fundamentally),?\s+",
    re.IGNORECASE,
)

_CONNECTOR_STRIP_RU = re.compile(
    r"^(Более того|Кроме того|Помимо этого|Вследствие этого|"
    r"В дополнение к этому|Следовательно|Соответственно|"
    r"Необходимо отметить),?\s+",
    re.IGNORECASE,
)

_CONNECTOR_STRIP_UK = re.compile(
    r"^(Більш того|Крім того|Окрім цього|Внаслідок цього|"
    r"На додаток до цього|Відповідно|Необхідно зазначити),?\s+",
    re.IGNORECASE,
)

_CONNECTOR_STRIP_FR = re.compile(
    r"^(En outre|De surcroît|Par conséquent|Néanmoins|Toutefois|"
    r"Par ailleurs|De plus|Qui plus est|En définitive|"
    r"Il convient de noter que|En ce qui concerne|"
    r"Dans cette perspective|Force est de constater que),?\s+",
    re.IGNORECASE,
)

_CONNECTOR_STRIP_ES = re.compile(
    r"^(Además|Sin embargo|No obstante|Por consiguiente|"
    r"En consecuencia|Asimismo|Por otra parte|Por lo tanto|"
    r"Cabe destacar que|Es importante señalar que|"
    r"En este sentido|Resulta evidente que),?\s+",
    re.IGNORECASE,
)

_CONNECTOR_STRIP_DE = re.compile(
    r"^(Darüber hinaus|Des Weiteren|Nichtsdestotrotz|"
    r"Demzufolge|Infolgedessen|Dessen ungeachtet|Im Übrigen|"
    r"Zusammenfassend lässt sich sagen|Es ist hervorzuheben|"
    r"In diesem Zusammenhang|Ferner|Überdies),?\s+",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
#  Hedging modulation
# ═══════════════════════════════════════════════════════════════

_HEDGE_EN: list[tuple[str, list[str]]] = [
    (r"\bclearly\s+demonstrates?\b", ["suggests", "shows", "indicates"]),
    (r"\bclearly\s+indicates?\b", ["suggests", "hints at", "points to"]),
    (r"\bundeniably\b", ["arguably", "likely"]),
    (r"\bundoubtedly\b", ["probably", "likely"]),
    (r"\bsignificantly\s+impact", ["affect", "influence"]),
    (r"\bfundamentally\s+transform", ["change", "reshape"]),
    (r"\bprofoundly\s+affect", ["influence", "shape"]),
    (r"\bcrucially\b", ["importantly"]),
    (r"\bparamount\b", ["very important", "critical"]),
    (r"\binvaluable\b", ["very useful", "helpful"]),
    (r"\bindispensable\b", ["essential", "needed"]),
    (r"\bpivotal\b", ["important", "key"]),
    (r"\bgroundbreaking\b", ["innovative", "new"]),
    (r"\bseamlessly\b", ["smoothly", "easily"]),
    (r"\bmeticulously\b", ["carefully", "with care"]),
    (r"\bcomprehensively\b", ["fully", "broadly"]),
    (r"\bsystematically\b", ["step by step", "methodically"]),
    (r"\bholistic\b", ["broad", "complete"]),
    (r"\bmultifaceted\b", ["complex", "layered"]),
]

_HEDGE_RU: list[tuple[str, list[str]]] = [
    (r"\bбезусловно\b", ["скорее всего", "вероятно"]),
    (r"\bнесомненно\b", ["вероятно", "похоже"]),
    (r"\bсущественно\b", ["заметно", "ощутимо"]),
    (r"\bзначительно\b", ["заметно", "во многом"]),
    (r"\bпринципиально\b", ["по сути", "во многом"]),
    (r"\bкардинально\b", ["сильно", "заметно"]),
    (r"\bколоссальн(ый|ая|ое|ые|ого|ой|ому|ую|ым|ом|ых|ыми)\b", ["огромн{}", "серьёзн{}"]),
    (r"\bфундаментальн(ый|ая|ое|ые|ого|ой|ому|ую|ым|ом|ых|ыми)\b", ["основн{}", "базов{}"]),
    (r"\bбеспрецедентн(ый|ая|ое|ые|ого|ой|ому|ую|ым|ом|ых|ыми)\b", ["небывал{}", "уникальн{}"]),
    # Phase 1-2 expansion
    (r"\bочевидно\b", ["видимо", "по всей видимости"]),
    (r"\bнеизбежно\b", ["скорее всего", "видимо"]),
    (r"\bабсолютно\b", ["совершенно", "полностью"]),
    (r"\bкатегорически\b", ["решительно", "твёрдо"]),
    (r"\bисключительно\b", ["только", "лишь"]),
    (r"\bглобальн(ый|ая|ое|ые|ого|ой|ому|ую|ым|ом|ых|ыми)\b", ["общ{}", "масштабн{}"]),
    (r"\bкомплексн(ый|ая|ое|ые|ого|ой|ому|ую|ым|ом|ых|ыми)\b", ["сложн{}", "составн{}"]),
    (r"\bсистематическ(ий|ая|ое|ие|ого|ой|ому|ую|им|ом|их|ими)\b", ["планомерн{}", "постоянн{}"]),
    (r"\bмаксимально\b", ["как можно больше", "по полной"]),
    (r"\bминимально\b", ["как можно меньше", "по минимуму"]),
]

_HEDGE_UK: list[tuple[str, list[str]]] = [
    (r"\bбезумовно\b", ["мабуть", "ймовірно"]),
    (r"\bбезперечно\b", ["ймовірно", "схоже"]),
    (r"\bсуттєво\b", ["помітно", "відчутно"]),
    (r"\bзначно\b", ["помітно", "багато в чому"]),
    (r"\bпринципово\b", ["по суті", "багато в чому"]),
    (r"\bкардинально\b", ["сильно", "помітно"]),
    (r"\bфундаментальн(ий|а|е|і|ого|ій|ому|у|им|ім|их|ими)\b", ["основн{}", "базов{}"]),
    (r"\bбезпрецедентн(ий|а|е|і|ого|ій|ому|у|им|ім|их|ими)\b", ["небувал{}", "унікальн{}"]),
    # Phase 1-2 expansion
    (r"\bочевидно\b", ["видимо", "вочевидь"]),
    (r"\bневідворотно\b", ["мабуть", "видимо"]),
    (r"\bабсолютно\b", ["цілком", "повністю"]),
    (r"\bкатегорично\b", ["рішуче", "твердо"]),
    (r"\bвиключно\b", ["тільки", "лише"]),
    (r"\bглобальн(ий|а|е|і|ого|ій|ому|у|им|ім|их|ими)\b", ["загальн{}", "масштабн{}"]),
    (r"\bкомплексн(ий|а|е|і|ого|ій|ому|у|им|ім|их|ими)\b", ["складн{}", "складен{}"]),
    (r"\bсистематичн(ий|а|е|і|ого|ій|ому|у|им|ім|их|ими)\b", ["планомірн{}", "постійн{}"]),
    (r"\bмаксимально\b", ["якнайбільше", "на повну"]),
    (r"\bмінімально\b", ["якнайменше", "по мінімуму"]),
]

_HEDGE_FR: list[tuple[str, list[str]]] = [
    (r"\bincontestablement\b", ["sans doute", "probablement"]),
    (r"\bindéniablement\b", ["probablement", "vraisemblablement"]),
    (r"\bindubitablement\b", ["sans doute", "probablement"]),
    (r"\bfondamentalement\b", ["en grande partie", "surtout"]),
    (r"\bconsidérablement\b", ["beaucoup", "nettement"]),
    (r"\bsignificativement\b", ["nettement", "bien"]),
    (r"\bcrucial(?:e|es|ement)?\b", ["important", "clé"]),
    (r"\bindispensable\b", ["essentiel", "nécessaire"]),
    (r"\bprimordial(?:e|es)?\b", ["important", "central"]),
    (r"\bexhaustiv(?:e|es|ement)?\b", ["complet", "large"]),
    (r"\bsystématiquement\b", ["régulièrement", "souvent"]),
    (r"\bméticuleusement\b", ["avec soin", "soigneusement"]),
]

_HEDGE_ES: list[tuple[str, list[str]]] = [
    (r"\bindudablemente\b", ["probablemente", "seguramente"]),
    (r"\binnegablemente\b", ["posiblemente", "quizás"]),
    (r"\bincuestionablemente\b", ["probablemente", "seguramente"]),
    (r"\bfundamentalmente\b", ["en gran medida", "sobre todo"]),
    (r"\bconsiderablemente\b", ["mucho", "bastante"]),
    (r"\bsignificativamente\b", ["notablemente", "bastante"]),
    (r"\bcrucial(?:es|mente)?\b", ["importante", "clave"]),
    (r"\bindispensable\b", ["esencial", "necesario"]),
    (r"\bprimordial(?:es|mente)?\b", ["importante", "central"]),
    (r"\bexhaustiv(?:o|a|os|as|amente)?\b", ["completo", "amplio"]),
    (r"\bsistemáticamente\b", ["regularmente", "a menudo"]),
    (r"\bmeticulosamente\b", ["con cuidado", "cuidadosamente"]),
]

_HEDGE_DE: list[tuple[str, list[str]]] = [
    (r"\bzweifellos\b", ["wahrscheinlich", "vermutlich"]),
    (r"\bunbestreitbar\b", ["wohl", "möglicherweise"]),
    (r"\bunbestritten\b", ["wahrscheinlich", "offenbar"]),
    (r"\bgrundlegend\b", ["weitgehend", "vor allem"]),
    (r"\berheblich\b", ["deutlich", "merklich"]),
    (r"\bmaßgeblich\b", ["weitgehend", "wesentlich"]),
    (r"\bentscheidend\b", ["wichtig", "wesentlich"]),
    (r"\bunverzichtbar\b", ["wichtig", "nötig"]),
    (r"\bsystematisch\b", ["regelmäßig", "Schritt für Schritt"]),
    (r"\bakribisch\b", ["sorgfältig", "gründlich"]),
    (r"\bumfassend\b", ["breit", "weitgehend"]),
    (r"\bbahnbrechend\b", ["innovativ", "neuartig"]),
]

# ═══════════════════════════════════════════════════════════════
#  Perspective rotation patterns
# ═══════════════════════════════════════════════════════════════

_PERSPECTIVE_EN: list[tuple[re.Pattern[str], list[str]]] = [
    # "The X shows/demonstrates/indicates that Y" → "Y, as X shows"
    (re.compile(
        r"^(The\s+\w+(?:\s+\w+)?)\s+"
        r"(?:shows?|demonstrates?|indicates?|reveals?|suggests?)\s+"
        r"(?:that\s+)?(.+)$",
        re.IGNORECASE,
    ), [
        r"\2 — as \1 shows",
        r"According to \1, \2",
        r"Based on \1, \2",
    ]),
    # "It is important/worth/essential to note/consider that Y" → "Notably, Y"
    (re.compile(
        r"^[Ii]t\s+is\s+(?:important|worth|essential|crucial|noteworthy)"
        r"\s+(?:to\s+(?:note|consider|mention|recognize|highlight)\s+)?"
        r"that\s+(.+)$",
    ), [
        r"Notably, \1",
        r"\1",
    ]),
    # "X ensures that Y" → "Y thanks to X" / "With X, Y"
    (re.compile(
        r"^(.+?)\s+ensures?\s+(?:that\s+)?(.+)$",
        re.IGNORECASE,
    ), [
        r"\2, thanks to \1",
        r"With \1, \2",
    ]),
]

# RU perspective rotation: «Исследование показывает, что X» → «X — так следует из исследования»
_PERSPECTIVE_RU: list[tuple[re.Pattern[str], list[str]]] = [
    # "X показывает/демонстрирует/свидетельствует (о том,) что Y"
    (re.compile(
        r"^(.+?)\s+(?:показыва(?:ет|ют)|демонстрир(?:ует|уют)|свидетельству(?:ет|ют)|"
        r"указыва(?:ет|ют)|подтвержда(?:ет|ют))"
        r"(?:\s*,?\s*(?:о\s+том\s*,?\s*)?(?:что)\s+)(.+)$",
        re.IGNORECASE,
    ), [
        r"\2 — так следует из того, что \1",
        r"Согласно \1, \2",
        r"Судя по \1, \2",
    ]),
    # "Важно отметить/учитывать, что Y" → "Y"
    (re.compile(
        r"^(?:Важно|Стоит|Необходимо|Нужно)\s+"
        r"(?:отметить|учитывать|подчеркнуть|учесть)"
        r"(?:\s*,?\s*что\s+)(.+)$",
        re.IGNORECASE,
    ), [
        r"\1",
    ]),
    # "X обеспечивает (то,) что Y" → "Благодаря X, Y"
    (re.compile(
        r"^(.+?)\s+обеспечива(?:ет|ют)\s*(?:то\s*,?\s*)?(?:что\s+)?(.+)$",
        re.IGNORECASE,
    ), [
        r"Благодаря тому, что \1, \2",
        r"За счёт \1 \2",
    ]),
]

# UK perspective rotation
_PERSPECTIVE_UK: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(
        r"^(.+?)\s+(?:показу(?:є|ють)|демонстру(?:є|ють)|свідч(?:ить|ать)|"
        r"вказу(?:є|ють)|підтвердж(?:ує|ують))"
        r"(?:\s*,?\s*(?:те\s*,?\s*)?(?:що)\s+)(.+)$",
        re.IGNORECASE,
    ), [
        r"\2 — так випливає з \1",
        r"Згідно з \1, \2",
        r"Судячи з \1, \2",
    ]),
    (re.compile(
        r"^(?:Важливо|Варто|Необхідно|Потрібно)\s+"
        r"(?:зазначити|відзначити|підкреслити|врахувати)"
        r"(?:\s*,?\s*що\s+)(.+)$",
        re.IGNORECASE,
    ), [
        r"\1",
    ]),
    (re.compile(
        r"^(.+?)\s+забезпеч(?:ує|ують)\s*(?:те\s*,?\s*)?(?:що\s+)?(.+)$",
        re.IGNORECASE,
    ), [
        r"Завдяки тому, що \1, \2",
        r"За рахунок \1 \2",
    ]),
]

# ═══════════════════════════════════════════════════════════════
#  Clause embedding patterns (merge 2 sentences into 1)
# ═══════════════════════════════════════════════════════════════

_MERGE_CONNECTORS_EN = [
    "which also {verb_phrase}",
    "and {pronoun} {verb_phrase}",
    ", {verb_phrase_ing}",
]

# Sentence split patterns (kept for backward compat; prefer split_sentences())
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# ═══════════════════════════════════════════════════════════════
#  Fragment creation patterns
# ═══════════════════════════════════════════════════════════════

_FRAGMENT_TRIGGERS_EN = {
    "result": ["The result?", "And the result?", "What came out of it?"],
    "problem": ["The problem?", "But the problem?", "One issue though:"],
    "reason": ["The reason?", "Why?", "The reason is simple:"],
    "answer": ["The answer?", "Simple answer:", "Short answer:"],
    "solution": ["The fix?", "The solution?", "One way around this:"],
    "point": ["The point?", "The key thing?", "Bottom line:"],
    "catch": ["The catch?", "But here's the catch:", "One caveat:"],
    "truth": ["The truth?", "Honestly?", "The honest answer:"],
}

# ═══════════════════════════════════════════════════════════════
#  Main paraphrase engine
# ═══════════════════════════════════════════════════════════════


class ParaphraseEngine:
    """Sentence-level paraphrase engine for deep humanization.

    Applies structural transformations that reduce AI detection scores
    by changing sentence patterns rather than just swapping words.

    Transformations (in order):
    1. Multi-word expression simplification
    2. Connector deletion
    3. Hedging modulation
    4. Perspective rotation
    5. Clause embedding (sentence merging)
    6. Fragment creation
    """

    def __init__(
        self,
        lang: str = "en",
        intensity: int = 50,
        seed: Optional[int] = None,
    ) -> None:
        self.lang = lang.lower()
        self.intensity = max(0, min(100, intensity))
        self._rng = random.Random(seed if seed is not None else 42)
        self._changes: list[str] = []

    @property
    def changes(self) -> list[str]:
        """List of changes applied during last transform()."""
        return list(self._changes)

    def transform(self, text: str) -> str:
        """Apply paraphrase transformations to text.

        Args:
            text: input text

        Returns:
            Paraphrased text with structural changes.
        """
        if not text or not text.strip():
            return text

        self._changes = []

        # Preserve paragraph structure — process each paragraph independently
        paragraphs = re.split(r'(\n\s*\n)', text)
        result_parts: list[str] = []
        for part in paragraphs:
            # Paragraph separators (whitespace-only) — keep as-is
            if not part.strip():
                result_parts.append(part)
                continue
            result_parts.append(self._transform_paragraph(part))

        return "".join(result_parts)

    def _transform_paragraph(self, text: str) -> str:
        """Apply transforms to a single paragraph."""
        prob = self.intensity / 100.0  # base probability for each transform

        # Step 1: Multi-word expression simplification (always applies)
        text = self._simplify_mwe(text, min(prob * 1.5, 0.95))

        # Step 2: Split into sentences for per-sentence transforms
        sentences = split_sentences(text.strip(), self.lang)

        if not sentences:
            return text

        result_sentences: list[str] = []
        i = 0

        while i < len(sentences):
            sent = sentences[i]

            # Step 3: Connector deletion (high probability — these are red flags)
            if self._rng.random() < prob * 1.2:
                sent = self._strip_connector(sent)

            # Step 4: Hedging modulation
            if self._rng.random() < prob * 0.7:
                sent = self._modulate_hedging(sent)

            # Step 5: Perspective rotation
            if self._rng.random() < prob * 0.5:
                sent = self._rotate_perspective(sent)

            # Step 6: Clause embedding (merge with next sentence)
            if (i + 1 < len(sentences)
                    and self._rng.random() < prob * 0.3
                    and len(sent.split()) + len(sentences[i + 1].split()) < 40):
                merged = self._embed_clause(sent, sentences[i + 1])
                if merged:
                    sent = merged
                    i += 1  # skip next sentence (merged)

            # Step 7: Fragment creation (low probability, high impact)
            if self._rng.random() < prob * 0.15:
                fragmented = self._create_fragment(sent)
                if fragmented:
                    sent = fragmented

            result_sentences.append(sent)
            i += 1

        return " ".join(result_sentences)

    # ---------------------------------------------------------------
    #  Multi-word expression simplification
    # ---------------------------------------------------------------

    def _simplify_mwe(self, text: str, prob: float) -> str:
        """Replace multi-word expressions with simpler alternatives."""
        if self.lang == "ru":
            mwe_list = _MWE_RU
        elif self.lang == "uk":
            mwe_list = _MWE_UK
        elif self.lang == "fr":
            mwe_list = _MWE_FR
        elif self.lang == "es":
            mwe_list = _MWE_ES
        elif self.lang == "de":
            mwe_list = _MWE_DE
        else:
            mwe_list = _MWE_EN

        for pattern, replacement in mwe_list:
            if self._rng.random() < prob:
                lower_text = text.lower()
                pat_lower = pattern.lower()
                idx = lower_text.find(pat_lower)
                if idx >= 0:
                    end = idx + len(pattern)
                    old = text[idx:end]
                    # If at start of sentence, capitalize replacement
                    at_start = (idx == 0)
                    if not at_start and idx > 0:
                        # Check if preceded by sentence-ending punctuation + space
                        before = text[:idx].rstrip()
                        if before and before[-1] in ".!?\n":
                            at_start = True
                    if at_start:
                        new = replacement[0].upper() + replacement[1:]
                    else:
                        new = replacement
                    after = text[end:]
                    # Strip trailing comma+space left by connector-style MWEs
                    # e.g. "Кроме того, ..." → "Ещё ..." (not "Ещё, ...")
                    if after.startswith(", ") and not new.endswith(",") and len(new.split()) <= 3:
                        # Only strip if the replacement is a short word/phrase
                        # (connectors, not clause-level replacements)
                        after = " " + after[2:]
                    text = text[:idx] + new + after
                    self._changes.append(f"mwe: '{old}' → '{new}'")

        return text

    # ---------------------------------------------------------------
    #  Connector deletion
    # ---------------------------------------------------------------

    def _strip_connector(self, sent: str) -> str:
        """Remove AI-typical sentence-initial connectors."""
        if self.lang == "ru":
            pattern = _CONNECTOR_STRIP_RU
        elif self.lang == "uk":
            pattern = _CONNECTOR_STRIP_UK
        elif self.lang == "fr":
            pattern = _CONNECTOR_STRIP_FR
        elif self.lang == "es":
            pattern = _CONNECTOR_STRIP_ES
        elif self.lang == "de":
            pattern = _CONNECTOR_STRIP_DE
        else:
            pattern = _CONNECTOR_STRIP_EN

        m = pattern.match(sent)
        if m:
            rest = sent[m.end():]
            if rest and len(rest) > 5:
                # Capitalize first letter of remaining text
                rest = rest[0].upper() + rest[1:]
                self._changes.append(f"connector_strip: removed '{m.group().strip()}'")
                return rest
        return sent

    # ---------------------------------------------------------------
    #  Hedging modulation
    # ---------------------------------------------------------------

    def _modulate_hedging(self, sent: str) -> str:
        """Replace AI-confident language with natural hedging."""
        if self.lang == "ru":
            hedges = _HEDGE_RU
        elif self.lang == "uk":
            hedges = _HEDGE_UK
        elif self.lang == "fr":
            hedges = _HEDGE_FR
        elif self.lang == "es":
            hedges = _HEDGE_ES
        elif self.lang == "de":
            hedges = _HEDGE_DE
        else:
            hedges = _HEDGE_EN

        for pattern_str, replacements in hedges:
            m = re.search(pattern_str, sent, re.IGNORECASE)
            if m:
                replacement = self._rng.choice(replacements)
                old = m.group()
                # For RU/UK: if replacement contains {}, substitute the capture group
                if m.lastindex and m.lastindex >= 1 and "{}" in replacement:
                    suffix = m.group(1)
                    replacement = replacement.format(suffix)
                # Preserve capitalization
                if old[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                sent = sent[:m.start()] + replacement + sent[m.end():]
                self._changes.append(f"hedge: '{old}' → '{replacement}'")
                break  # one hedge per sentence

        return sent

    # ---------------------------------------------------------------
    #  Perspective rotation
    # ---------------------------------------------------------------

    def _rotate_perspective(self, sent: str) -> str:
        """Rotate sentence perspective (e.g., topic-focus rewrite)."""
        if self.lang == "en":
            patterns = _PERSPECTIVE_EN
        elif self.lang == "ru":
            patterns = _PERSPECTIVE_RU
        elif self.lang == "uk":
            patterns = _PERSPECTIVE_UK
        else:
            return sent

        for pattern, replacements in patterns:
            m = pattern.match(sent.rstrip(".!?"))
            if m:
                template = self._rng.choice(replacements)
                try:
                    new = m.expand(template)
                    # Ensure proper ending
                    if not new.endswith((".", "!", "?")):
                        new = new.rstrip(",; ") + "."
                    # Capitalize first letter
                    new = new[0].upper() + new[1:]
                    self._changes.append(f"perspective: rotated '{sent[:40]}...'")
                    return new
                except Exception:
                    pass
        return sent

    # ---------------------------------------------------------------
    #  Clause embedding (merge two sentences)
    # ---------------------------------------------------------------

    def _embed_clause(self, sent1: str, sent2: str) -> Optional[str]:
        """Try to merge two sentences into one by embedding.

        Supports EN, RU, and UK with language-appropriate connectors.
        """
        s1 = sent1.rstrip(".!?").strip()
        s2 = sent2.strip()

        if not s1 or not s2:
            return None

        # Don't merge numbered list items (e.g., "1. First", "2. Second")
        # The sentence splitter may produce "Первый\n2." where the number
        # is at the end, or "2. Второй" where it's at the start.
        if (re.search(r'(?:^|\n)\d+[.)]\s?', sent1)
                or re.search(r'(?:^|\n)\d+[.)]\s?', sent2)
                or re.search(r'\d+[.)]$', s1)
                or re.search(r'\d+[.)]$', s2)):
            return None

        s2_first_word = s2.split()[0].lower() if s2.split() else ""

        # Don't merge if second sentence starts with a connector
        skip_starters = {
            "furthermore", "moreover", "additionally", "however",
            "consequently", "therefore", "nevertheless", "meanwhile",
            "кроме", "более", "помимо", "следовательно", "тем",
            "крім", "більше", "окрім", "відповідно", "тим",
        }
        if s2_first_word in skip_starters:
            return None

        # Lowercase the second sentence's first letter
        s2_lower = s2[0].lower() + s2[1:] if s2 else s2

        if self.lang == "ru":
            connectors = [
                f"{s1}, и {s2_lower}",
                f"{s1} — {s2_lower}",
                f"{s1}; {s2_lower}",
                f"{s1}, причём {s2_lower}",
            ]
        elif self.lang == "uk":
            connectors = [
                f"{s1}, і {s2_lower}",
                f"{s1} — {s2_lower}",
                f"{s1}; {s2_lower}",
                f"{s1}, причому {s2_lower}",
            ]
        else:
            connectors = [
                f"{s1}, and {s2_lower}",
                f"{s1} — {s2_lower}",
                f"{s1}; {s2_lower}",
            ]

        result = self._rng.choice(connectors)
        if not result.endswith((".", "!", "?")):
            result += "."

        self._changes.append("embed: merged 2 sentences")
        return result

    # ---------------------------------------------------------------
    #  Fragment creation
    # ---------------------------------------------------------------

    # Fragment triggers for Russian
    _FRAGMENT_TRIGGERS_RU: dict[str, list[str]] = {
        "потому": ["И вот почему.", "Причина проста."],
        "однако": ["Но есть нюанс.", "Впрочем."],
        "важно": ["И вот что ещё.", "Ключевой момент."],
        "результат": ["И что в итоге?", "Результат?"],
    }

    # Fragment triggers for Ukrainian
    _FRAGMENT_TRIGGERS_UK: dict[str, list[str]] = {
        "тому": ["І ось чому.", "Причина проста."],
        "однак": ["Але є нюанс.", "Втім."],
        "важливо": ["І ось що ще.", "Ключовий момент."],
        "результат": ["І що в підсумку?", "Результат?"],
    }

    def _create_fragment(self, sent: str) -> Optional[str]:
        """Create a rhetorical fragment for naturalness.

        Supports EN, RU, and UK.
        """
        words = sent.lower().split()

        if self.lang == "ru":
            triggers = self._FRAGMENT_TRIGGERS_RU
        elif self.lang == "uk":
            triggers = self._FRAGMENT_TRIGGERS_UK
        elif self.lang == "en":
            triggers = _FRAGMENT_TRIGGERS_EN
        else:
            return None

        for trigger, fragments in triggers.items():
            if trigger in words:
                sent_clean = sent.rstrip(".!?")
                idx = sent_clean.lower().find(trigger)
                if idx > 10:
                    before = sent_clean[:idx].rstrip(" ,;:—-").strip()
                    after = sent_clean[idx:].strip()
                    fragment = self._rng.choice(fragments)
                    result = f"{before}. {fragment} {after[0].upper() + after[1:]}."
                    self._changes.append(f"fragment: created at '{trigger}'")
                    return result
        return None


# ═══════════════════════════════════════════════════════════════
#  Convenience API
# ═══════════════════════════════════════════════════════════════

def paraphrase(
    text: str,
    lang: str = "en",
    intensity: int = 50,
    seed: Optional[int] = None,
) -> str:
    """Paraphrase text with structural transformations.

    Args:
        text: input text
        lang: language code ("en", "ru", "uk", etc.)
        intensity: aggressiveness 0–100
        seed: random seed for reproducibility

    Returns:
        Paraphrased text
    """
    engine = ParaphraseEngine(lang=lang, intensity=intensity, seed=seed)
    return engine.transform(text)
