"""Quick humanization quality/artifact check across languages."""
import re
from texthumanize import humanize, detect_ai

samples = {
    "en": (
        "Furthermore, it is important to note that the implementation of cloud computing "
        "facilitates the optimization of business processes. Additionally, the utilization "
        "of microservices constitutes a significant advancement. Nevertheless, considerable "
        "challenges remain in the area of security. It is worth mentioning that these "
        "challenges necessitate comprehensive solutions."
    ),
    "ru": (
        "Необходимо отметить, что данный подход является оптимальным решением для "
        "осуществления поставленных задач. Кроме того, следует подчеркнуть важность "
        "реализации инновационных методологий. В рамках данного исследования было "
        "установлено, что применение современных технологий способствует повышению эффективности."
    ),
    "uk": (
        "Необхідно зазначити, що даний підхід є фундаментальним для здійснення "
        "оптимізації процесів. Крім того, варто підкреслити, що реалізація інноваційних "
        "методологій забезпечує всебічне покращення ефективності. Таким чином, систематичне "
        "впровадження відповідних заходів сприяє досягненню стратегічних цілей."
    ),
    "de": (
        "Es ist wichtig zu beachten, dass die Implementierung von Cloud Computing die "
        "Optimierung von Geschäftsprozessen erleichtert. Darüber hinaus stellt die Nutzung "
        "von Microservices einen bedeutenden Fortschritt dar. Nichtsdestotrotz bestehen "
        "erhebliche Herausforderungen im Bereich der Sicherheit."
    ),
    "fr": (
        "Il est important de noter que la mise en œuvre du cloud computing facilite "
        "l'optimisation des processus métier. De plus, l'utilisation des microservices "
        "constitue une avancée significative. Néanmoins, des défis considérables subsistent "
        "dans le domaine de la sécurité."
    ),
    "es": (
        "Es importante señalar que la implementación de la computación en la nube facilita "
        "la optimización de los procesos empresariales. Además, la utilización de microservicios "
        "constituye un avance significativo. No obstante, persisten desafíos considerables "
        "en el ámbito de la seguridad."
    ),
}

# Artifact patterns to detect
artifact_patterns = {
    "en_bes": r'\bbes\b',
    "mixed_lang": r'\b(?:and|the|but)\b.*(?:[а-яіїєґ]|processus|además|außerdem)',
    "truncated_word": r'\b\w{3,}(?:ац|яц|ниц|заци)\b[,.\s]',  # Truncated -ация/-яция/-ниция words
    "double_conj": r'\b(и|і|and|und|et|y)\s+\1\b',
    "stacked_fragments": r'[.!?]\s+\w{1,15}[.!?]\s+\w{1,15}[.!?]',
}

# Test 3 seeds for each language
for lang, text in samples.items():
    issues = []
    for seed in [42, 100, 777]:
        r = humanize(text, lang=lang, seed=seed)
        d_a = detect_ai(r.text, lang=lang)
        
        # Check for artifacts
        for name, pat in artifact_patterns.items():
            if re.search(pat, r.text, re.IGNORECASE):
                issues.append(f"  seed={seed}: {name}")
    
    d_b = detect_ai(text, lang=lang)
    r42 = humanize(text, lang=lang, seed=42)
    d_a42 = detect_ai(r42.text, lang=lang)
    print(f"=== {lang.upper()} === AI: {d_b['score']:.0%} -> {d_a42['score']:.0%}  changes={len(r42.changes)}")
    if issues:
        print(f"  ARTIFACTS FOUND:")
        for i in issues:
            print(f"    {i}")
    else:
        print(f"  ✓ No artifacts detected")
    print(f"  OUT[42]: {r42.text[:250]}")
    print()
