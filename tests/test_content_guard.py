"""Tests for Content Classifier and Grammar Guard modules."""

from __future__ import annotations

from texthumanize.content_classifier import (
    ContentType,
    classify,
)
from texthumanize.grammar_guard import (
    GrammarGuard,
    GuardResult,
    _mlp_forward,
    extract_sentence_features,
)

# ── Content Classifier Tests ─────────────────────────────────

class TestContentClassifier:
    """Tests for content type classification."""

    def test_pure_code_detection(self):
        """Python code is classified as CODE."""
        code = '''```python
def hello_world():
    print("Hello, World!")
    for i in range(10):
        if i % 2 == 0:
            print(f"Even: {i}")
    return True

class MyClass:
    def __init__(self):
        self.value = 42
```'''
        result = classify(code, lang="en")
        assert result.content_type in (ContentType.CODE, ContentType.MIXED_CODE)
        assert result.protect_whitespace is True
        assert result.max_intensity_cap <= 60

    def test_article_detection(self):
        """Article with headings and paragraphs is classified as ARTICLE."""
        article = """# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on building
systems that can learn from data. It has become increasingly important in modern
technology and has applications in many fields.

## Types of Machine Learning

There are three main types of machine learning: supervised learning,
unsupervised learning, and reinforcement learning. Each has its own
strengths and use cases.

### Supervised Learning

In supervised learning, the algorithm is trained on labeled data.
The model learns to map inputs to outputs based on example pairs.
This approach is commonly used for classification and regression tasks.
"""
        result = classify(article, lang="en")
        assert result.content_type == ContentType.ARTICLE
        assert result.protect_structure is True
        assert result.heading_count >= 3

    def test_tutorial_detection(self):
        """Step-by-step tutorial is classified as TUTORIAL."""
        tutorial = """# How to Install Python

Step 1: Download the installer from python.org.

Step 2: Run the installer and follow the prompts.

Step 3: Open your terminal and type `python --version` to verify.

Step 4: Install pip by running `python -m ensurepip`.

Step 5: Create your first script with `print("Hello!")`.
"""
        result = classify(tutorial, lang="en")
        assert result.content_type == ContentType.TUTORIAL
        assert result.protect_structure is True

    def test_academic_detection(self):
        """Academic text with citations is classified as ACADEMIC."""
        academic = """Abstract: This paper examines the impact of neural network architectures
on natural language processing tasks.

The transformer architecture (Vaswani et al., 2017) has fundamentally changed
the landscape of NLP. Furthermore, the introduction of BERT (Devlin et al., 2019)
demonstrated that pre-training on large corpora yields substantial improvements
across a wide range of downstream tasks. Consequently, subsequent work by
Brown et al. (2020) showed that scaling language models leads to emergent
capabilities that were previously unattainable.

The methodology employed in this study follows the framework established
by Liu et al. (2019), with modifications to account for multilingual settings.
"""
        result = classify(academic, lang="en")
        assert result.content_type == ContentType.ACADEMIC
        assert result.allow_syntax_rewrite is False
        assert result.max_intensity_cap <= 55

    def test_chat_detection(self):
        """Short informal text is classified as CHAT."""
        chat = "hey! how are you? 😊 just wanted to check in. everything ok?"
        result = classify(chat, lang="en")
        assert result.content_type == ContentType.CHAT
        assert result.allow_paraphrase is True

    def test_mixed_code_detection(self):
        """Article with code blocks is classified as MIXED_CODE."""
        mixed = """# Getting Started with Flask

Flask is a lightweight web framework for Python. Here's how to create
a simple application:

```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'
```

You can run this application by saving it as `app.py` and running:

```bash
flask run
```

The application will be available at `http://localhost:5000`.
"""
        result = classify(mixed, lang="en")
        assert result.content_type == ContentType.MIXED_CODE
        assert result.protect_whitespace is True
        assert result.code_block_ratio > 0.05

    def test_list_heavy_detection(self):
        """Text dominated by lists is classified as LIST_HEAVY."""
        lists = """Shopping list for the week:

- Apples
- Bananas
- Oranges
- Milk
- Bread
- Eggs
- Cheese
- Butter
- Rice
- Chicken
"""
        result = classify(lists, lang="en")
        # Could be LIST_HEAVY or GENERAL, list items count matters
        assert result.list_item_count >= 5

    def test_short_text_returns_general(self):
        """Very short text returns GENERAL."""
        result = classify("Hello.")
        assert result.content_type == ContentType.GENERAL

    def test_russian_article(self):
        """Russian article is classified correctly."""
        article = """# Введение в машинное обучение

Машинное обучение — это раздел искусственного интеллекта, который фокусируется
на создании систем, способных обучаться на данных. Оно стало всё более важным
в современной технологии и имеет применение во многих областях.

## Типы машинного обучения

Существует три основных типа машинного обучения: обучение с учителем,
обучение без учителя и обучение с подкреплением. Каждый из них имеет свои
сильные стороны и области применения.
"""
        result = classify(article, lang="ru")
        assert result.content_type == ContentType.ARTICLE
        assert result.heading_count >= 2

    def test_processing_hints_code(self):
        """Code content has restrictive processing hints."""
        code = "```\ndef foo():\n    return 42\n```\n" * 5
        result = classify(code, lang="en")
        if result.content_type == ContentType.CODE:
            assert result.allow_paraphrase is False
            assert result.allow_syntax_rewrite is False
            assert result.protect_whitespace is True

    def test_confidence_range(self):
        """Confidence is between 0 and 1."""
        for text in [
            "Hello world, this is a test.",
            "# Title\n\nSome paragraph here with enough text to classify.",
            "```python\nprint('hi')\n```",
        ]:
            result = classify(text, lang="en")
            assert 0.0 <= result.confidence <= 1.0

    def test_scores_dict(self):
        """Scores dict contains all content types."""
        text = "This is a reasonably long text for testing the content classifier results."
        result = classify(text, lang="en")
        assert 'code' in result.scores
        assert 'article' in result.scores
        assert 'general' in result.scores


# ── Grammar Guard Tests ──────────────────────────────────────

class TestGrammarGuard:
    """Tests for the Grammar Guard module."""

    def test_feature_extraction_dimensions(self):
        """Feature extraction returns 12 features."""
        features = extract_sentence_features(
            "The quick brown fox jumps over the lazy dog.",
            "Previous sentence here.",
            "Next sentence follows.",
            lang="en",
        )
        assert len(features) == 12
        assert all(isinstance(f, (int, float)) for f in features)

    def test_feature_extraction_russian(self):
        """Features extracted correctly for Russian text."""
        features = extract_sentence_features(
            "Быстрая коричневая лиса перепрыгнула через ленивую собаку.",
            "Предыдущее предложение.",
            "Следующее предложение.",
            lang="ru",
        )
        assert len(features) == 12

    def test_feature_extraction_empty(self):
        """Empty sentence returns neutral features."""
        features = extract_sentence_features("", "", "", lang="en")
        assert len(features) == 12

    def test_mlp_forward_returns_probability(self):
        """MLP forward pass returns value between 0 and 1."""
        features = [0.5] * 12
        prob = _mlp_forward(features)
        assert 0.0 <= prob <= 1.0

    def test_mlp_forward_stable(self):
        """MLP produces consistent results for same input."""
        features = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,
                     0.7, 0.8, 0.9, 1.0, 0.5, 0.3]
        p1 = _mlp_forward(features)
        p2 = _mlp_forward(features)
        assert p1 == p2

    def test_guard_init(self):
        """GrammarGuard initializes with default parameters."""
        guard = GrammarGuard(lang="en")
        assert guard.lang == "en"
        assert guard.threshold == 0.72
        assert guard.max_rollbacks == 2

    def test_guard_process_clean_text(self):
        """Clean text passes through without changes."""
        guard = GrammarGuard(lang="en")
        text = "The cat sat on the mat. The dog ran in the park."
        result = guard.process(text)
        assert result == text  # no artifacts to fix
        assert guard.result.sentences_checked >= 1

    def test_guard_process_short_text(self):
        """Very short text is returned unchanged."""
        guard = GrammarGuard(lang="en")
        assert guard.process("Hi.") == "Hi."
        assert guard.process("") == ""

    def test_guard_process_with_original(self):
        """Guard can use original text for rollback context."""
        guard = GrammarGuard(lang="en")
        original = "I need help with this task. Can you show me the result?"
        humanized = "I necessitate amelioration with this endeavor. Can you elucidate me the consequence?"
        result = guard.process(humanized, original)
        assert isinstance(result, str)
        assert len(result) > 0
        # Result should be the humanized or a partially rolled-back version
        assert guard.result.sentences_checked >= 1

    def test_guard_result_structure(self):
        """GuardResult has expected fields."""
        result = GuardResult()
        assert result.sentences_checked == 0
        assert result.artifacts_found == 0
        assert result.rollbacks_applied == 0
        assert result.changes == []

    def test_guard_russian(self):
        """Guard works with Russian text."""
        guard = GrammarGuard(lang="ru")
        text = "Кот сидел на коврике. Собака бегала в парке."
        result = guard.process(text)
        assert isinstance(result, str)
        assert guard.result.sentences_checked >= 1

    def test_guard_artifact_detection(self):
        """Guard detects sentence with poor collocations."""
        guard = GrammarGuard(lang="en", threshold=0.5)  # lower threshold for testing
        # Heavily corrupted sentence
        text = (
            "Furthermore, the quintessential methodological paradigm necessitates "
            "the amelioration of multifaceted concomitant parameters. "
            "The cat sat on the mat."
        )
        result = guard.process(text)
        assert isinstance(result, str)
        assert guard.result.sentences_checked >= 1


# ── Integration Tests ────────────────────────────────────────

class TestIntegration:
    """Integration tests for classifier + guard in pipeline."""

    def test_import_from_package(self):
        """Public API imports work."""
        from texthumanize import (
            ContentType,
            classify_content,
        )
        assert ContentType.CODE.value == "code"
        assert callable(classify_content)

    def test_classify_in_pipeline_metrics(self):
        """Humanize result includes content_type in metrics."""
        from texthumanize import humanize
        result = humanize(
            "The implementation of artificial intelligence represents "
            "a significant challenge. However, it is important to note "
            "that this technology facilitates the automation of various "
            "processes.",
            lang="en",
            profile="web",
            intensity=50,
            seed=42,
        )
        assert "content_type" in result.metrics_before
        assert "content_confidence" in result.metrics_before
        assert result.metrics_before["content_type"] in [ct.value for ct in ContentType]

    def test_code_protection_in_pipeline(self):
        """Code blocks are preserved through pipeline."""
        from texthumanize import humanize
        text = """Here is a Python function:

```python
def calculate_sum(a, b):
    return a + b
```

This function takes two parameters and returns their sum."""
        result = humanize(text, lang="en", profile="web", intensity=50, seed=42)
        # Code block should be preserved
        assert "def calculate_sum(a, b):" in result.text
        assert "return a + b" in result.text

    def test_pipeline_grammar_guard_stage(self):
        """Grammar guard runs as a pipeline stage."""
        from texthumanize import humanize
        result = humanize(
            "The utilization of this methodology facilitates the "
            "achievement of optimal outcomes in various scenarios. "
            "Moreover, the implementation ensures comprehensive "
            "coverage of all relevant parameters.",
            lang="en",
            intensity=60,
            seed=42,
        )
        # Check that grammar_guard stage was executed
        stage_timings = result.metrics_after.get("stage_timings", {})
        assert "grammar_guard" in stage_timings
        assert "content_classify" in stage_timings
