"""Regression: humanizing non-English text must never inject English asides.

Before 0.36.0 several stages fell back to English word lists for languages
without their own list, producing e.g. "— to be fair —" inside Portuguese.
"""
import re

import pytest

from texthumanize import humanize

TEXTS = {
    "pl": (
        "W dzisiejszym dynamicznie zmieniającym się świecie cyfrowym pozycjonowanie odgrywa "
        "kluczową rolę w rozwoju każdej firmy. Ponadto należy zauważyć, że wysokiej jakości linki "
        "mają znaczący wpływ na widoczność witryny. Co więcej, kompleksowa strategia stanowi "
        "nieodłączny element sukcesu. W związku z tym firmy mogą optymalizować swoje zasoby."
    ),
    "es": (
        "En el panorama digital actual, el posicionamiento web desempeña un papel fundamental en el "
        "desarrollo de cualquier negocio. Además, cabe destacar que los enlaces de alta calidad tienen "
        "un impacto significativo en la visibilidad del sitio. Asimismo, una estrategia integral "
        "constituye una parte esencial del éxito. Por lo tanto, las empresas pueden optimizar sus recursos."
    ),
    "pt": (
        "No cenário digital atual, o posicionamento desempenha um papel fundamental no desenvolvimento "
        "de qualquer negócio. Além disso, vale ressaltar que os links de alta qualidade exercem um "
        "impacto significativo na visibilidade do site. Ademais, uma estratégia abrangente constitui "
        "uma parte essencial do sucesso. Portanto, as empresas podem otimizar seus recursos."
    ),
}
ENGLISH = re.compile(
    r"\b(the|honestly|interestingly|surprisingly|to be fair|oddly|actually|anyway|here's|"
    r"that said|basically|arguably|in fact|mind you|granted|in practice|notably)\b",
    re.I,
)


@pytest.mark.parametrize("lang", sorted(TEXTS))
@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_no_english_injected(lang, seed):
    out = humanize(TEXTS[lang], lang=lang, profile="web", intensity=80, seed=seed).text
    assert not ENGLISH.findall(out), out
