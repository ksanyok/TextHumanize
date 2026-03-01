"""Diagnose neural features before/after humanization."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import texthumanize as th
from texthumanize.neural_detector import NeuralAIDetector, extract_features, normalize_features

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

FEAT_NAMES = [
    'sent_len_mean','sent_len_std','sent_len_cv',
    'word_len_mean','word_len_std','word_len_cv',
    'type_token_ratio','hapax_ratio','yule_k',
    'char_entropy','word_entropy','bigram_entropy',
    'function_word_ratio','punct_diversity','comma_rate',
    'burstiness_score','sentence_length_variance',
    'vocab_richness','avg_parse_depth','lexical_density',
    'flesh_kincaid','gunning_fog','smog_index',
    'pronoun_rate','contraction_rate','question_rate',
    'named_entity_rate','ai_pattern_rate','passive_voice_rate',
    'discourse_marker_rate','sentence_start_variety',
    'avg_word_frequency','repetition_rate',
    'conjunction_rate','transition_word_rate',
]

# Neural weights (from analysis)
WEIGHTS = [
    -0.15, 0.50, 0.55,    # sent_len_mean, _std, _cv
    -0.08, 0.22, 0.30,    # word_len_mean, _std, _cv
    0.35, 0.62, -0.40,    # ttr, hapax, yule_k
    0.18, 0.58, 0.25,     # char_entropy, word_entropy, bigram_entropy
    -0.12, 0.15, -0.05,   # func_word, punct_div, comma_rate
    0.55, 0.50,            # burstiness, sent_len_var
    0.38, 0.10, 0.32,     # vocab_richness, parse_depth, lexical_density
    -0.18, -0.15, -0.12,  # flesh, fog, smog
    0.25, 0.30, 0.15,     # pronoun, contraction, question
    -0.08, -2.10, -0.20,  # NER, ai_pattern, passive
    0.15, 0.40,            # discourse_marker, sent_start_variety
    -0.10, -0.28,          # avg_word_freq, repetition
    -0.05, -0.45,          # conjunction, transition
]

def show_features(text, lang, label):
    feats = extract_features(text, lang)
    nfeats = normalize_features(feats, lang)
    print(f'\n--- {label} ---')
    contribution = []
    for i, (name, raw, norm) in enumerate(zip(FEAT_NAMES, feats, nfeats)):
        w = WEIGHTS[i] if i < len(WEIGHTS) else 0
        c = norm * w
        contribution.append((name, raw, norm, w, c))
    
    # Sort by absolute contribution (biggest impact first)
    contribution.sort(key=lambda x: abs(x[4]), reverse=True)
    total = sum(c for _, _, _, _, c in contribution)
    print(f'  {"Feature":<28} {"raw":>8} {"norm":>8} {"w":>6} {"contrib":>8}')
    for name, raw, norm, w, c in contribution[:15]:
        flag = " ★" if abs(c) > 0.3 else ""
        print(f'  {name:<28} {raw:8.4f} {norm:+8.4f} {w:+6.2f} {c:+8.4f}{flag}')
    print(f'  --- total contribution: {total:+.4f}')
    return feats, nfeats

for lang in ["en", "ru", "uk"]:
    print(f"\n{'='*70}")
    print(f"  LANGUAGE: {lang.upper()}")
    print(f"{'='*70}")
    
    # Original
    show_features(AI_TEXTS[lang], lang, f"{lang.upper()} AI ORIGINAL")
    
    # Humanized i=60
    r60 = th.humanize(AI_TEXTS[lang], lang=lang, intensity=60)
    show_features(r60.text, lang, f"{lang.upper()} HUMANIZED i=60")
    
    print(f"\n  Humanized text (i=60):")
    print(f"  {r60.text[:300]}...")
    print(f"\n  Changes: {len(r60.changes)}")
    for c in r60.changes[:10]:
        print(f"    - {c.get('type','?')}: {c.get('description','')[:80]}")
