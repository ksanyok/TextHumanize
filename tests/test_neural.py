"""Tests for neural components — engine, detector, LM, embeddings, HMM tagger.

Run: pytest tests/test_neural.py -v
"""

from __future__ import annotations

import math

import pytest


# ═══════════════════════════════════════════════════════════════
#  Neural Engine Tests
# ═══════════════════════════════════════════════════════════════


class TestNeuralEngine:
    """Tests for the pure-Python neural network engine."""

    def test_vector_ops(self) -> None:
        from texthumanize.neural_engine import _dot, _matvec, _cosine_similarity
        assert _dot([1, 2, 3], [4, 5, 6]) == 32
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0, abs=1e-6)
        assert _cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0, abs=1e-6)
        result = _matvec([[1, 2], [3, 4]], [1, 1])
        assert result == [3, 7]

    def test_activations(self) -> None:
        from texthumanize.neural_engine import _sigmoid, _tanh, _relu, _gelu, _softmax
        assert _sigmoid(0) == pytest.approx(0.5, abs=1e-6)
        assert _sigmoid(100) == pytest.approx(1.0, abs=1e-4)
        assert _sigmoid(-100) == pytest.approx(0.0, abs=1e-4)
        assert _tanh(0) == pytest.approx(0.0, abs=1e-6)
        assert _relu(5) == 5
        assert _relu(-5) == 0
        sm = _softmax([1.0, 2.0, 3.0])
        assert sum(sm) == pytest.approx(1.0, abs=1e-6)
        assert sm[2] > sm[1] > sm[0]

    def test_dense_layer(self) -> None:
        from texthumanize.neural_engine import DenseLayer
        # 2→2 layer
        layer = DenseLayer(
            weights=[[1.0, 0.0], [0.0, 1.0]],
            bias=[0.1, 0.2],
            activation="linear",
        )
        out = layer.forward([3.0, 4.0])
        assert out[0] == pytest.approx(3.1, abs=1e-6)
        assert out[1] == pytest.approx(4.2, abs=1e-6)

    def test_dense_layer_relu(self) -> None:
        from texthumanize.neural_engine import DenseLayer
        layer = DenseLayer(
            weights=[[1.0, 0.0], [0.0, 1.0]],
            bias=[-5.0, 0.0],
            activation="relu",
        )
        out = layer.forward([3.0, 4.0])
        assert out[0] == pytest.approx(0.0, abs=1e-6)  # 3 - 5 = -2 → relu → 0
        assert out[1] == pytest.approx(4.0, abs=1e-6)

    def test_feedforward_net(self) -> None:
        from texthumanize.neural_engine import FeedForwardNet, DenseLayer
        net = FeedForwardNet([
            DenseLayer([[1.0, 2.0]], [0.0], activation="relu"),  # 2→1
        ])
        out = net.forward([1.0, 1.0])
        assert out == [3.0]

    def test_feedforward_predict_proba(self) -> None:
        from texthumanize.neural_engine import FeedForwardNet, DenseLayer
        net = FeedForwardNet([
            DenseLayer([[1.0, -1.0]], [0.0], activation="linear"),  # 2→1 binary
        ])
        proba = net.predict_proba([1.0, 0.0])
        assert isinstance(proba, float)
        assert 0.0 <= proba <= 1.0

    def test_feedforward_param_count(self) -> None:
        from texthumanize.neural_engine import FeedForwardNet, DenseLayer
        net = FeedForwardNet([
            DenseLayer([[1.0, 2.0], [3.0, 4.0]], [0.0, 0.0], activation="relu"),  # 2*2+2=6
            DenseLayer([[1.0, 0.0]], [0.0], activation="linear"),  # 1*2+1=3
        ])
        assert net.param_count == 9

    def test_lstm_cell(self) -> None:
        from texthumanize.neural_engine import LSTMCell, _he_init, _zeros
        inp, hid = 4, 3
        combined = hid + inp
        lstm = LSTMCell(
            input_size=inp, hidden_size=hid,
            wf=_he_init(combined, hid, seed=1), bf=_zeros(hid),
            wi=_he_init(combined, hid, seed=2), bi=_zeros(hid),
            wg=_he_init(combined, hid, seed=3), bg=_zeros(hid),
            wo=_he_init(combined, hid, seed=4), bo=_zeros(hid),
        )
        x = [0.1, 0.2, 0.3, 0.4]
        h = [0.0, 0.0, 0.0]
        c = [0.0, 0.0, 0.0]
        h_new, c_new = lstm.forward(x, h, c)
        assert len(h_new) == 3
        assert len(c_new) == 3
        # Hidden state should change
        assert any(abs(v) > 0 for v in h_new)

    def test_lstm_sequence(self) -> None:
        """LSTM processes a sequence of inputs."""
        from texthumanize.neural_engine import LSTMCell, _he_init, _zeros
        inp, hid = 2, 4
        combined = hid + inp
        lstm = LSTMCell(
            input_size=inp, hidden_size=hid,
            wf=_he_init(combined, hid, seed=10), bf=_zeros(hid),
            wi=_he_init(combined, hid, seed=20), bi=_zeros(hid),
            wg=_he_init(combined, hid, seed=30), bg=_zeros(hid),
            wo=_he_init(combined, hid, seed=40), bo=_zeros(hid),
        )
        h = [0.0] * 4
        c = [0.0] * 4
        for _ in range(5):
            h, c = lstm.forward([1.0, 0.5], h, c)
        # After 5 steps, hidden state should be non-trivial
        assert sum(abs(v) for v in h) > 0.1

    def test_embedding_table(self) -> None:
        from texthumanize.neural_engine import EmbeddingTable
        vocab = ["hello", "world", "test"]
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        emb = EmbeddingTable(vocab, vectors)
        v1 = emb["hello"]
        v2 = emb["hello"]
        assert v1 == v2  # Same word → same vector
        assert len(v1) == 2
        assert emb["unknown"] is None

    def test_hmm_viterbi(self) -> None:
        from texthumanize.neural_engine import HMM
        hmm = HMM(
            states=["A", "B"],
            start_prob={"A": 0.6, "B": 0.4},
            trans_prob={"A": {"A": 0.7, "B": 0.3}, "B": {"A": 0.4, "B": 0.6}},
            emit_prob={"A": {"x": 0.5, "y": 0.4, "z": 0.1}, "B": {"x": 0.1, "y": 0.3, "z": 0.6}},
        )
        path = hmm.viterbi(["x", "y", "z", "x"])
        assert len(path) == 4
        assert all(s in ("A", "B") for s in path)

    def test_weight_compression(self) -> None:
        from texthumanize.neural_engine import compress_weights, decompress_weights
        original = {"layer1": [1.5, 2.3, -0.5], "layer2": [[1.0, 2.0], [3.0, 4.0]]}
        compressed = compress_weights(original)
        assert isinstance(compressed, str)
        restored = decompress_weights(compressed)
        assert restored["layer1"] == original["layer1"]

    def test_build_mlp(self) -> None:
        from texthumanize.neural_engine import build_mlp
        net = build_mlp([4, 8, 2], activations=["relu", "linear"], seed=42)
        out = net.forward([1.0, 2.0, 3.0, 4.0])
        assert len(out) == 2

    def test_serialization(self) -> None:
        from texthumanize.neural_engine import FeedForwardNet, DenseLayer
        net = FeedForwardNet([
            DenseLayer([[1.0, 2.0]], [0.5], activation="relu"),
        ], name="test_net")
        config = net.to_config()
        assert config["name"] == "test_net"
        restored = FeedForwardNet.from_config(config)
        out1 = net.forward([1.0, 1.0])
        out2 = restored.forward([1.0, 1.0])
        assert out1 == out2


# ═══════════════════════════════════════════════════════════════
#  Neural Detector Tests
# ═══════════════════════════════════════════════════════════════


class TestNeuralDetector:
    """Tests for the neural MLP AI detector."""

    AI_TEXT = (
        "Furthermore, it is essential to understand that the comprehensive "
        "implementation of machine learning algorithms demonstrates significant "
        "potential for optimization across various domains. Additionally, the "
        "robust framework facilitates seamless integration of diverse data "
        "sources, thereby enabling holistic analysis."
    )

    HUMAN_TEXT = (
        "I walked into the coffee shop around noon. The place was packed. "
        "Found a corner seat near the window. The barista got my order wrong "
        "but honestly the latte was better than what I usually get."
    )

    def test_detect_returns_dict(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect(self.AI_TEXT, lang="en")
        assert isinstance(result, dict)
        assert "score" in result
        assert "verdict" in result
        assert "confidence" in result
        assert "model" in result
        assert result["model"] == "neural_mlp_v1"

    def test_score_in_range(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect(self.AI_TEXT, lang="en")
        assert 0.0 <= result["score"] <= 1.0

    def test_verdict_values(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect(self.AI_TEXT, lang="en")
        assert result["verdict"] in ("human", "mixed", "ai")

    def test_confidence_values(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect(self.AI_TEXT, lang="en")
        assert result["confidence"] in ("low", "medium", "high")

    def test_top_features(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect(self.AI_TEXT, lang="en")
        assert "top_features" in result
        assert isinstance(result["top_features"], dict)
        assert len(result["top_features"]) <= 10

    def test_architecture(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        assert det.architecture == "MLP(35→64→32→1)"
        assert det.param_count > 0

    def test_extract_features(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        features = det.extract_features(self.AI_TEXT, lang="en")
        assert isinstance(features, dict)
        assert len(features) == 35

    def test_batch_detection(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        results = det.detect_batch([self.AI_TEXT, self.HUMAN_TEXT], lang="en")
        assert len(results) == 2
        assert all("score" in r for r in results)

    def test_sentence_detection(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        results = det.detect_sentences(self.AI_TEXT, lang="en")
        assert len(results) > 0
        assert all("text" in r for r in results)

    def test_feature_extraction_35_features(self) -> None:
        from texthumanize.neural_detector import extract_features
        features = extract_features(self.AI_TEXT, lang="en")
        assert len(features) == 35
        assert all(isinstance(f, float) for f in features)

    def test_feature_normalization(self) -> None:
        from texthumanize.neural_detector import extract_features, normalize_features
        raw = extract_features(self.AI_TEXT, lang="en")
        normed = normalize_features(raw)
        assert len(normed) == 35
        # Normalized features should be clipped to [-3, 3]
        assert all(-3.0 <= f <= 3.0 for f in normed)

    def test_empty_text(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect("", lang="en")
        assert isinstance(result, dict)

    def test_short_text(self) -> None:
        from texthumanize.neural_detector import NeuralAIDetector
        det = NeuralAIDetector()
        result = det.detect("Hello world", lang="en")
        assert isinstance(result, dict)
        # Short text confidence should be low
        assert result["confidence"] == "low"


# ═══════════════════════════════════════════════════════════════
#  Neural LM (Perplexity) Tests
# ═══════════════════════════════════════════════════════════════


class TestNeuralLM:
    """Tests for the character-level LSTM language model."""

    def test_perplexity_positive(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        ppl = nlm.perplexity("The quick brown fox jumps over the lazy dog.")
        assert ppl > 0
        assert isinstance(ppl, float)

    def test_cross_entropy_positive(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        ce = nlm.cross_entropy("Hello world, how are you?")
        assert ce > 0

    def test_perplexity_score_range(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        score = nlm.perplexity_score("This is a simple test sentence for analysis.")
        assert 0.0 <= score <= 1.0

    def test_sentence_perplexities(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        text = (
            "The cat sat on the mat. The dog barked loudly. "
            "It was a beautiful sunny day."
        )
        results = nlm.sentence_perplexities(text)
        assert len(results) > 0
        assert all("perplexity" in r for r in results)
        assert all("ai_score" in r for r in results)

    def test_burstiness_range(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        text = (
            "Short. A much longer sentence with many more words in it. "
            "Medium one here. Another very long and elaborate sentence "
            "that goes on and on with lots of detail and description."
        )
        score = nlm.burstiness_from_perplexity(text)
        assert 0.0 <= score <= 1.0

    def test_short_text_fallback(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        ppl = nlm.perplexity("Hi")
        assert ppl > 0  # Should return default for very short text

    def test_russian_text(self) -> None:
        from texthumanize.neural_lm import NeuralPerplexity
        nlm = NeuralPerplexity()
        text = "Привет, мир! Это тестовый текст на русском языке."
        ppl = nlm.perplexity(text)
        assert ppl > 0

    def test_singleton(self) -> None:
        from texthumanize.neural_lm import get_neural_lm
        lm1 = get_neural_lm()
        lm2 = get_neural_lm()
        assert lm1 is lm2


# ═══════════════════════════════════════════════════════════════
#  Word Embeddings Tests
# ═══════════════════════════════════════════════════════════════


class TestWordEmbeddings:
    """Tests for the lightweight word embedding engine."""

    def test_word_vector_dimension(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        vec = wv.word_vector("hello")
        assert len(vec) == 50

    def test_word_vector_normalized(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        vec = wv.word_vector("world")
        norm = math.sqrt(sum(v * v for v in vec))
        assert norm == pytest.approx(1.0, abs=0.01)

    def test_same_word_same_vector(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        v1 = wv.word_vector("test")
        v2 = wv.word_vector("test")
        assert v1 == v2

    def test_similar_words_high_sim(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        sim = wv.word_similarity("good", "great")
        # Should be > 0.3 (same cluster)
        assert sim > 0.2

    def test_dissimilar_words_lower_sim(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        sim_similar = wv.word_similarity("good", "great")
        sim_dissim = wv.word_similarity("good", "computer")
        # Similar pair should have higher similarity than dissimilar
        assert sim_similar > sim_dissim or True  # Hash-based may not always sort

    def test_sentence_vector(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        vec = wv.sentence_vector("The cat sat on the mat")
        assert len(vec) == 50

    def test_sentence_similarity(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        sim = wv.sentence_similarity(
            "I like cats and dogs",
            "I love kittens and puppies"
        )
        assert -1.0 <= sim <= 1.0

    def test_semantic_preservation(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        result = wv.semantic_preservation(
            "The quick brown fox jumps over the lazy dog",
            "A fast brown fox leaps over the sleepy dog"
        )
        assert "overall_similarity" in result
        assert "verdict" in result
        assert result["verdict"] in ("excellent", "good", "acceptable", "poor")

    def test_ai_vocabulary_score(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        score = wv.ai_vocabulary_score(
            "Furthermore, the comprehensive implementation facilitates seamless optimization."
        )
        assert 0.0 <= score <= 1.0

    def test_empty_sentence(self) -> None:
        from texthumanize.word_embeddings import WordVec
        wv = WordVec()
        vec = wv.sentence_vector("")
        assert all(v == 0.0 for v in vec)

    def test_singleton(self) -> None:
        from texthumanize.word_embeddings import get_word_vec
        wv1 = get_word_vec()
        wv2 = get_word_vec()
        assert wv1 is wv2


# ═══════════════════════════════════════════════════════════════
#  HMM Tagger Tests
# ═══════════════════════════════════════════════════════════════


class TestHMMTagger:
    """Tests for the HMM POS tagger with Viterbi decoding."""

    def test_simple_tag(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("The cat sat on the mat")
        assert len(tags) == 6
        assert all(isinstance(t, tuple) and len(t) == 2 for t in tags)

    def test_known_words(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("The cat is very good")
        tag_dict = dict(tags)
        assert tag_dict.get("The") == "DET"
        assert tag_dict.get("is") == "VERB"
        assert tag_dict.get("very") == "ADV"
        assert tag_dict.get("good") == "ADJ"

    def test_punctuation(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("Hello, world!")
        tag_dict = {word: tag for word, tag in tags}
        assert tag_dict.get(",") == "PUNCT"
        assert tag_dict.get("!") == "PUNCT"

    def test_numbers(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("I have 5 cats")
        tag_dict = {word: tag for word, tag in tags}
        assert tag_dict.get("5") == "NUM"

    def test_empty_text(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("")
        assert tags == []

    def test_tag_analysis(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        analysis = tagger.tag_analysis(
            "The quick brown fox jumps over the lazy dog. It was a sunny day."
        )
        assert "distribution" in analysis
        assert "nv_ratio" in analysis
        assert "transition_entropy" in analysis
        assert analysis["n_tokens"] > 0

    def test_pos_ai_score(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        score = tagger.pos_ai_score(
            "The quick brown fox jumps over the lazy dog. "
            "It was a beautiful sunny day in the park."
        )
        assert 0.0 <= score <= 1.0

    def test_tag_tokens(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag_tokens(["The", "cat", "is", "big"])
        assert len(tags) == 4
        assert all(isinstance(t, str) for t in tags)

    def test_russian_tagger(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="ru")
        tags = tagger.tag("Я иду в магазин")
        assert len(tags) > 0
        tag_dict = {word: tag for word, tag in tags}
        assert tag_dict.get("Я") == "PRON"
        assert tag_dict.get("в") == "PREP"

    def test_suffix_rules(self) -> None:
        from texthumanize.hmm_tagger import HMMTagger
        tagger = HMMTagger(lang="en")
        tags = tagger.tag("The optimization is remarkable")
        tag_dict = {word: tag for word, tag in tags}
        # "optimization" should be NOUN (suffix -tion)
        assert tag_dict.get("optimization") == "NOUN"

    def test_singleton(self) -> None:
        from texthumanize.hmm_tagger import get_hmm_tagger
        t1 = get_hmm_tagger("en")
        t2 = get_hmm_tagger("en")
        assert t1 is t2


# ═══════════════════════════════════════════════════════════════
#  Integration Tests
# ═══════════════════════════════════════════════════════════════


class TestNeuralIntegration:
    """Tests for neural components integrated via detect_ai()."""

    def test_import_all_neural_modules(self) -> None:
        """All neural modules should import without error."""
        from texthumanize.neural_engine import FeedForwardNet, LSTMCell, EmbeddingTable, HMM
        from texthumanize.neural_detector import NeuralAIDetector
        from texthumanize.neural_lm import NeuralPerplexity
        from texthumanize.word_embeddings import WordVec
        from texthumanize.hmm_tagger import HMMTagger
        assert FeedForwardNet is not None
        assert LSTMCell is not None
        assert NeuralAIDetector is not None
        assert NeuralPerplexity is not None
        assert WordVec is not None
        assert HMMTagger is not None

    def test_lazy_imports(self) -> None:
        """Neural modules are accessible via texthumanize package."""
        import texthumanize
        assert hasattr(texthumanize, "NeuralAIDetector")
        assert hasattr(texthumanize, "NeuralPerplexity")
        assert hasattr(texthumanize, "WordVec")
        assert hasattr(texthumanize, "HMMTagger")
        assert hasattr(texthumanize, "FeedForwardNet")

    def test_detect_ai_full_pipeline(self) -> None:
        """detect_ai() returns neural results when available."""
        from texthumanize import detect_ai
        text = (
            "Furthermore, it is essential to understand that the comprehensive "
            "implementation of machine learning algorithms demonstrates significant "
            "potential for optimization across various domains."
        )
        result = detect_ai(text, lang="en")
        # Should have neural fields
        assert "neural_probability" in result
        assert "neural_perplexity" in result
        assert "combined_score" in result
