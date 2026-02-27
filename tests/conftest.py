"""Общие фикстуры для тестов TextHumanize."""
from __future__ import annotations

import pytest

# ═══════════════════════════════════════════════════════════════
#  Тексты-образцы для разных языков
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def en_ai_text() -> str:
    """Типичный AI-сгенерированный текст на английском."""
    return (
        "Furthermore, it is important to note that the implementation of "
        "artificial intelligence constitutes a significant paradigm shift. "
        "Additionally, the utilization of machine learning facilitates "
        "comprehensive optimization of various processes. Nevertheless, "
        "it is worth mentioning that considerable challenges remain. "
        "In conclusion, it is imperative to implement robust solutions."
    )


@pytest.fixture
def en_human_text() -> str:
    """Типичный человеческий текст на английском."""
    return (
        "I tried that new coffee shop downtown yesterday. Their espresso was "
        "actually decent — not as burnt as the place on 5th. The barista "
        "was nice too, recommended this Ethiopian blend I'd never heard of. "
        "Might go back this weekend."
    )


@pytest.fixture
def ru_ai_text() -> str:
    """Типичный AI-сгенерированный текст на русском."""
    return (
        "Данный документ является руководством по осуществлению настройки "
        "программного обеспечения. Необходимо осуществить установку всех "
        "компонентов. Кроме того, следует обратить внимание на "
        "конфигурационные параметры. В заключение необходимо отметить "
        "важность надлежащего тестирования."
    )


@pytest.fixture
def ru_human_text() -> str:
    """Типичный человеческий текст на русском."""
    return (
        "Вчера попробовал новую кофейню в центре. Эспрессо там нормальный, "
        "не пережаренный. Бариста посоветовал эфиопскую смесь — раньше такую "
        "не пил. Наверное зайду ещё на выходных."
    )


@pytest.fixture
def uk_ai_text() -> str:
    """Типичный AI-сгенерированный текст на украинском."""
    return (
        "Даний матеріал є яскравим прикладом здійснення сучасних підходів. "
        "Крім того, необхідно зазначити важливість впровадження інноваційних "
        "рішень. Зважаючи на це, необхідно здійснити відповідний аналіз."
    )


@pytest.fixture
def short_text() -> str:
    """Короткий текст (edge case)."""
    return "Hello world."


@pytest.fixture
def empty_text() -> str:
    """Пустая строка."""
    return ""


@pytest.fixture
def multiline_text() -> str:
    """Многоабзацный текст на английском."""
    return (
        "The first paragraph introduces the topic. It provides context.\n\n"
        "The second paragraph goes into detail. It explains the methodology "
        "and provides examples for clarity.\n\n"
        "The final paragraph summarizes. Quick and done."
    )


@pytest.fixture
def watermarked_text() -> str:
    """Текст с zero-width водяными знаками."""
    return "This te\u200bxt has hid\u200bden wat\u200bermarks ins\u200bide."


# ═══════════════════════════════════════════════════════════════
#  Параметры и опции
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def default_profiles() -> list[str]:
    """Все доступные профили."""
    return ["chat", "web", "seo", "docs", "formal", "academic", "marketing", "social", "email"]


@pytest.fixture
def all_langs() -> list[str]:
    """Все поддерживаемые языки."""
    return ["ru", "uk", "en", "de", "fr", "es", "pl", "pt", "it"]


@pytest.fixture
def seed() -> int:
    """Фиксированный seed для воспроизводимости."""
    return 42
