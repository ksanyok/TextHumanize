#!/usr/bin/env python3
"""Export the Python language packs into the TypeScript and PHP ports.

The JS/TS port (``js/``) is what runs inside Node pipelines, so it must not
drift from the curated Python dictionaries. This script copies the
*publication-safe* subset of each pack into ``js/src/lang/generated/<code>.ts``:

* ``bureaucratic`` — single-word officialese, filtered so inflected
  languages keep agreement (replacement must share the key's ending);
* ``bureaucratic_phrases`` — multi-word officialese and AI cliches
  (``lang/_ai_cliches.py`` is already merged in by ``lang/__init__``);
* ``ai_connectors`` — sentence-initial connectors and their alternatives.

Entries that are known to break grammar (bare copulas such as "является" ->
"—", which change case government) are dropped. Run after editing any
language pack:

    python3 scripts/export_js_langs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from texthumanize.lang import LANGUAGES  # noqa: E402

LANGS = ["en", "ru", "uk", "de", "fr", "es", "pl", "pt", "it"]
INFLECTED = {"ru", "uk", "pl", "de"}
# Romance adjectives agree in gender/number: keep the final letter.
ROMANCE = {"es", "pt", "it", "fr"}
OUT = ROOT / "js" / "src" / "lang" / "generated"
PHP_OUT = ROOT / "php" / "src" / "Safe" / "data"

# Bare copulas: replacing them with a dash or "это" breaks case government
# ("является ключевым фактором" -> "— ключевым фактором").
COPULA_KEYS = {
    "является", "являются", "являлся", "являлась", "являлось", "являлись",
    "є", "являє", "являють", "jest", "są", "stanowi", "stanowią",
    "constituye", "constituyen", "constitui", "constituem",
}
GOVERNING_NOUNS = {
    "контроль", "контролю", "мониторинг", "моніторинг", "влияние", "вплив", "воздействие",
    "kontrolę", "wpływ", "control", "controle", "contrôle", "controllo",
}
# Replacements that are too colloquial / opinionated for published SEO copy.
BANNED_REPLACEMENTS = {"ojo:", "подчеркну:", "destaco que", "zaznaczmy", "total,"}


# Discourse classes of connectors. An alternative is kept only if it has the
# same class as the key (or either is unclassified), so "Além disso" (adding)
# never becomes "Por outro lado" (contrasting).
CONNECTOR_CLASSES = {
    "add": [
        "furthermore", "moreover", "additionally", "in addition", "also", "plus", "besides",
        "what's more", "on top of that", "кроме того", "более того", "помимо", "также", "ещё",
        "еще", "плюс", "к тому же", "крім того", "більш того", "окрім", "також", "ще", "до того ж",
        "ponadto", "co więcej", "poza tym", "oprócz tego", "do tego", "na dodatek", "także",
        "również", "además", "asimismo", "también", "aparte", "igualmente", "encima",
        "de igual modo", "além disso", "ademais", "também", "mais ainda", "outrossim",
        "darüber hinaus", "außerdem", "zudem", "de plus", "en outre", "inoltre", "per di più",
    ],
    "contrast": [
        "however", "nevertheless", "nonetheless", "but", "yet", "still", "even so",
        "on the other hand", "that said", "однако", "тем не менее", "но", "впрочем", "всё же",
        "все же", "правда", "зато", "с другой стороны", "однак", "проте", "але", "втім",
        "тим не менш", "все ж", "щоправда", "з іншого боку", "jednak", "niemniej", "ale",
        "mimo to", "z drugiej strony", "choć", "sin embargo", "no obstante", "pero", "aun así",
        "por otro lado", "en cambio", "no entanto", "contudo", "todavia", "porém", "mas",
        "por outro lado", "entretanto", "jedoch", "aber", "dennoch", "cependant", "toutefois",
        "pourtant", "mais", "tuttavia", "però", "ma ",
    ],
    "result": [
        "therefore", "consequently", "thus", "hence", "so", "as a result", "in conclusion",
        "ultimately", "in the end", "to sum up", "because of this", "поэтому", "следовательно",
        "таким образом", "итак", "в итоге", "в заключение", "так что", "значит", "в результате",
        "тому", "отже", "таким чином", "у підсумку", "тож", "на завершення", "значить",
        "dlatego", "w związku z tym", "zatem", "więc", "w efekcie", "podsumowując", "w skrócie",
        "ostatecznie", "por lo tanto", "por consiguiente", "en consecuencia", "así que", "por eso",
        "en conclusión", "en resumen", "en definitiva", "portanto", "por isso", "assim", "logo",
        "em conclusão", "em resumo", "para concluir", "em suma", "deshalb", "daher", "folglich",
        "donc", "ainsi", "par conséquent", "quindi", "pertanto", "dunque",
    ],
}


def _conn_class(text: str):
    t = text.lower().strip() + " "
    for cls, prefixes in CONNECTOR_CLASSES.items():
        for pre in prefixes:
            if t.startswith(pre.rstrip() + " ") or t.startswith(pre.rstrip() + ","):
                return cls
    return None


def _ending_ok(key: str, repl: str, lang: str) -> bool:
    if " " in key or " " in repl:
        return True  # phrases are curated by hand in the pack
    if lang in INFLECTED:
        return key[-2:] == repl[-2:]
    if lang in ROMANCE:
        return key[-1:] == repl[-1:]
    return True


# "осуществлять контроль" → "делать контроль" is not Russian: officialese
# light verbs are only replaced by verbs that keep their collocations.
LIGHT_VERB_KEY = re.compile(r"^(осуществ|здійсн|реализ|реаліз|realizow|realizar|realizzare)", re.I)
LIGHT_VERB_BAD = re.compile(r"^(с?дела|з?роб|robi|zrobi|hacer|fazer|fare)", re.I)


def _clean(key: str, cands, lang: str, single_word: bool):
    out = []
    for c in cands:
        if isinstance(c, str) and LIGHT_VERB_KEY.match(key) and LIGHT_VERB_BAD.match(c.strip()):
            continue
        if not isinstance(c, str):
            continue
        c = c.strip()
        if c.lower() == key.lower() or c in out or c.lower() in BANNED_REPLACEMENTS:
            continue
        if single_word and not c:
            continue
        if single_word and not _ending_ok(key, c, lang):
            continue
        out.append(c)
    return out


def export(lang: str) -> dict:
    pack = LANGUAGES[lang]
    data = {"code": lang, "name": pack.get("name", lang)}

    bur = {}
    for k, v in pack.get("bureaucratic", {}).items():
        k = k.strip().lower()
        if len(k) < 3 or k in COPULA_KEYS:
            continue
        c = _clean(k, v, lang, single_word=" " not in k)
        if c:
            bur[k] = c
    data["bureaucratic"] = bur

    phr = {}
    for k, v in pack.get("bureaucratic_phrases", {}).items():
        k = " ".join(k.strip().lower().split())
        if len(k) < 3 or k in COPULA_KEYS:
            continue
        # "осуществлять контроль над X" → "контролировать над X" breaks
        # government; light-verb + noun phrases ending in a noun that takes
        # its own preposition are skipped.
        if k.split()[-1] in GOVERNING_NOUNS:
            continue
        c = _clean(k, v, lang, single_word=False)
        # a pure dash / "это" replacement of a one-word key changes case government
        if " " not in k:
            c = [x for x in c if x and not x.startswith("—") and x not in ("это", "це", "— это")]
        # "Zauważmy: X" / "Заметим: X" read as chatty; keep colon variants only
        # when the entry has nothing else.
        plain = [x for x in c if not x.endswith(":")]
        if plain:
            c = plain
        if c:
            phr[k] = c
    data["phrases"] = phr

    con = {}
    for k, v in pack.get("ai_connectors", {}).items():
        k = k.strip()
        c = [x.strip() for x in v if isinstance(x, str) and x.strip() and x.strip() != k]
        kc = _conn_class(k)
        c = [x for x in c if kc is None or _conn_class(x) in (None, kc)]
        if c:
            con[k] = list(dict.fromkeys(c))
    data["connectors"] = con
    # Contrastive connectors carry meaning ("However, X"): never dropped.
    data["contrast"] = sorted(k for k in con if _conn_class(k) == "contrast")
    return data


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        data = export(lang)
        body = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
        (OUT / f"{lang}.ts").write_text(
            "// AUTO-GENERATED by scripts/export_js_langs.py from texthumanize/lang — do not edit.\n"
            "import type { LangData } from '../../types';\n\n"
            f"export const {lang}: LangData = {body};\n",
            encoding="utf-8",
        )
        # Same data for the PHP port (php/src/Safe), loaded with json_decode.
        PHP_OUT.mkdir(parents=True, exist_ok=True)
        (PHP_OUT / f"{lang}.json").write_text(
            json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        print(f"{lang}: {len(data['bureaucratic'])} words, {len(data['phrases'])} phrases, "
              f"{len(data['connectors'])} connectors")


if __name__ == "__main__":
    main()
