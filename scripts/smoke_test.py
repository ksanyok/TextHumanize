#!/usr/bin/env python3
"""Quick smoke test for humanization on EN/RU/UK."""

import sys
sys.path.insert(0, ".")

import texthumanize as th

ru_text = (
    "Искусственный интеллект представляет собой одну из наиболее значительных "
    "технологий современности. Данная технология оказывает существенное влияние "
    "на различные аспекты жизнедеятельности общества. В настоящее время "
    "наблюдается значительный рост интереса к данной области. Необходимо "
    "отметить, что развитие искусственного интеллекта осуществляется "
    "беспрецедентными темпами. Кроме того, важно подчеркнуть, что данная "
    "технология обладает колоссальным потенциалом для трансформации общества."
)

uk_text = (
    "Штучний інтелект являє собою одну з найбільш значущих технологій "
    "сучасності. Дана технологія чинить суттєвий вплив на різноманітні аспекти "
    "життєдіяльності суспільства. На сьогоднішній день спостерігається значне "
    "зростання інтересу до даної галузі. Необхідно зазначити, що розвиток "
    "штучного інтелекту здійснюється безпрецедентними темпами. Крім того, "
    "важливо підкреслити, що дана технологія володіє колосальним потенціалом "
    "для трансформації суспільства."
)

en_text = (
    "Artificial intelligence represents one of the most significant technologies "
    "of our time. This technology has a substantial impact on various aspects of "
    "society. Currently, there is a significant increase in interest in this "
    "field. It is necessary to note that the development of artificial "
    "intelligence is proceeding at unprecedented rates. Furthermore, it is "
    "important to emphasize that this technology possesses enormous potential "
    "for societal transformation."
)

for lang, text in [("en", en_text), ("ru", ru_text), ("uk", uk_text)]:
    result = th.humanize(text, lang=lang, intensity=75)
    out_text = result.text if hasattr(result, 'text') else str(result)
    print(f"=== {lang.upper()} ===")
    print(out_text[:400])
    print()
    
    # Also check AI score if detector is available
    try:
        score_obj = th.detect_ai(out_text, lang=lang)
        orig_obj = th.detect_ai(text, lang=lang)
        if isinstance(score_obj, dict):
            score = score_obj.get('ai_score', score_obj.get('score', 0))
            orig_score = orig_obj.get('ai_score', orig_obj.get('score', 0))
        elif hasattr(score_obj, 'ai_score'):
            score = score_obj.ai_score
            orig_score = orig_obj.ai_score
        else:
            score = float(score_obj)
            orig_score = float(orig_obj)
        print(f"  Original AI score: {orig_score:.3f}")
        print(f"  Humanized AI score: {score:.3f}")
        print(f"  Delta: {orig_score - score:+.3f}")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  Detector error: {e}")
    print()
