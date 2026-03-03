"""Tests for ASH™ (Adaptive Statistical Humanization) modules.

Covers all 5 proprietary technologies + the unified ASH Engine.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
#  HUMAN PROFILES
# ═══════════════════════════════════════════════════════════════

class TestHumanProfiles:
    """Tests for _human_profiles.py."""

    def test_get_human_profile_en(self):
        from texthumanize._human_profiles import get_human_profile
        p = get_human_profile("en")
        assert isinstance(p, dict)
        assert len(p) > 20
        assert "E_word_entropy" in p

    def test_get_human_profile_ru(self):
        from texthumanize._human_profiles import get_human_profile
        p = get_human_profile("ru")
        assert isinstance(p, dict)
        assert "E_word_entropy" in p

    def test_get_human_profile_uk(self):
        from texthumanize._human_profiles import get_human_profile
        p = get_human_profile("uk")
        assert isinstance(p, dict)
        assert "E_word_entropy" in p

    def test_get_human_profile_unknown_falls_back(self):
        from texthumanize._human_profiles import get_human_profile
        p = get_human_profile("xx")
        assert isinstance(p, dict)
        assert len(p) > 0

    def test_get_ai_profile(self):
        from texthumanize._human_profiles import get_ai_profile
        ai = get_ai_profile("en")
        assert isinstance(ai, dict)
        assert "E_word_entropy" in ai

    def test_signature_distance(self):
        from texthumanize._human_profiles import (
            get_ai_profile,
            get_human_profile,
            signature_distance,
        )
        human = get_human_profile("en")
        ai = get_ai_profile("en")
        # Convert AI profile to flat means (signature_distance expects dict[str, float])
        ai_flat = {k: v["mean"] for k, v in ai.items()}
        d = signature_distance(ai_flat, human)
        assert isinstance(d, float)
        assert d >= 0.0

    def test_metric_gaps(self):
        from texthumanize._human_profiles import (
            get_ai_profile,
            get_human_profile,
            metric_gaps,
        )
        human = get_human_profile("en")
        ai = get_ai_profile("en")
        # Convert AI profile to flat means
        ai_flat = {k: v["mean"] for k, v in ai.items()}
        gaps = metric_gaps(ai_flat, human)
        assert isinstance(gaps, list)
        assert len(gaps) > 0
        # Should be sorted by absolute delta
        if len(gaps) > 1:
            assert abs(gaps[0][1]) >= abs(gaps[1][1])


# ═══════════════════════════════════════════════════════════════
#  PERPLEXITY SCULPTOR
# ═══════════════════════════════════════════════════════════════

class TestPerplexitySculptor:
    """Tests for perplexity_sculptor.py."""

    SAMPLE_EN = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable. Each component works independently. "
        "The overall performance meets expectations. Results are consistent "
        "across multiple runs. Users report satisfaction with the speed."
    )

    SAMPLE_RU = (
        "Система обрабатывает данные эффективно. Она справляется с большими "
        "объёмами информации без задержек. Архитектура была спроектирована "
        "масштабируемой. Каждый компонент работает независимо. Общая "
        "производительность соответствует ожиданиям. Результаты стабильны "
        "при многократных запусках. Пользователи довольны скоростью."
    )

    def test_sculpt_en(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang="en", seed=42)
        result = ps.sculpt(self.SAMPLE_EN, intensity=0.5)
        assert result.text is not None
        assert isinstance(result.text, str)

    def test_sculpt_ru(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang="ru", seed=42)
        result = ps.sculpt(self.SAMPLE_RU, intensity=0.5)
        assert result.text is not None

    def test_sculpt_empty(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang="en")
        result = ps.sculpt("", intensity=0.5)
        assert result.text == ""
        assert result.surprises_injected == 0

    def test_analyze_curve(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang="en")
        analysis = ps.analyze_curve(self.SAMPLE_EN)
        assert isinstance(analysis, dict)
        assert "sentences" in analysis

    def test_sculpt_result_fields(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps = PerplexitySculptor(lang="en", seed=42)
        result = ps.sculpt(self.SAMPLE_EN, intensity=0.7)
        assert hasattr(result, "text")
        assert hasattr(result, "original_text")
        assert hasattr(result, "surprises_injected")

    def test_module_level_function(self):
        from texthumanize.perplexity_sculptor import sculpt_perplexity
        result = sculpt_perplexity(self.SAMPLE_EN, lang="en", seed=42)
        assert result.text is not None

    def test_seed_reproducibility(self):
        from texthumanize.perplexity_sculptor import PerplexitySculptor
        ps1 = PerplexitySculptor(lang="en", seed=123)
        ps2 = PerplexitySculptor(lang="en", seed=123)
        r1 = ps1.sculpt(self.SAMPLE_EN, intensity=0.5)
        r2 = ps2.sculpt(self.SAMPLE_EN, intensity=0.5)
        assert r1.text == r2.text


# ═══════════════════════════════════════════════════════════════
#  SIGNATURE TRANSFER
# ═══════════════════════════════════════════════════════════════

class TestSignatureTransfer:
    """Tests for signature_transfer.py."""

    SAMPLE = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable. Each component works independently. "
        "The overall performance meets expectations. Results are consistent "
        "across multiple runs. Users report satisfaction with the speed."
    )

    def test_transfer_en(self):
        from texthumanize.signature_transfer import SignatureTransfer
        st = SignatureTransfer(lang="en", seed=42)
        result = st.transfer(self.SAMPLE, intensity=0.5)
        assert result.text is not None
        assert isinstance(result.text, str)

    def test_transfer_empty(self):
        from texthumanize.signature_transfer import SignatureTransfer
        st = SignatureTransfer(lang="en")
        result = st.transfer("", intensity=0.5)
        assert result.text == ""

    def test_compute_signature(self):
        from texthumanize.signature_transfer import SignatureTransfer
        st = SignatureTransfer(lang="en")
        sig = st.compute_signature(self.SAMPLE)
        assert isinstance(sig, dict)
        assert len(sig) > 5

    def test_distance_to_human(self):
        from texthumanize.signature_transfer import SignatureTransfer
        st = SignatureTransfer(lang="en")
        dist = st.distance_to_human(self.SAMPLE)
        assert isinstance(dist, float)
        assert dist >= 0.0

    def test_transfer_result_distances(self):
        from texthumanize.signature_transfer import SignatureTransfer
        st = SignatureTransfer(lang="en", seed=42)
        result = st.transfer(self.SAMPLE, intensity=0.7)
        assert hasattr(result, "distance_before")
        assert hasattr(result, "distance_after")

    def test_module_level_function(self):
        from texthumanize.signature_transfer import transfer_signature
        result = transfer_signature(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None


# ═══════════════════════════════════════════════════════════════
#  WATERMARK FORENSICS
# ═══════════════════════════════════════════════════════════════

class TestWatermarkForensics:
    """Tests for watermark_forensics.py."""

    SAMPLE = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable. Each component works independently. "
        "The overall performance meets expectations."
    )

    def test_detect(self):
        from texthumanize.watermark_forensics import WatermarkForensics
        wf = WatermarkForensics(lang="en")
        result = wf.detect(self.SAMPLE)
        assert hasattr(result, "verdict")
        assert result.verdict in (
            "strong_watermark", "weak_watermark",
            "possible_watermark", "no_watermark",
        )

    def test_detect_empty(self):
        from texthumanize.watermark_forensics import WatermarkForensics
        wf = WatermarkForensics(lang="en")
        result = wf.detect("")
        assert result.verdict == "no_watermark"

    def test_neutralise(self):
        from texthumanize.watermark_forensics import WatermarkForensics
        wf = WatermarkForensics(lang="en", seed=42)
        result = wf.neutralise(self.SAMPLE, intensity=0.5)
        assert result.text is not None
        assert isinstance(result.text, str)

    def test_forensic_result_fields(self):
        from texthumanize.watermark_forensics import WatermarkForensics
        wf = WatermarkForensics(lang="en")
        result = wf.detect(self.SAMPLE)
        assert hasattr(result, "watermark_strength")
        assert hasattr(result, "green_ratio")
        assert isinstance(result.watermark_strength, float)

    def test_module_level_detect(self):
        from texthumanize.watermark_forensics import detect_statistical_watermark
        result = detect_statistical_watermark(self.SAMPLE, lang="en")
        assert hasattr(result, "verdict")

    def test_module_level_neutralise(self):
        from texthumanize.watermark_forensics import neutralise_watermark
        result = neutralise_watermark(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_neutralize_alias(self):
        from texthumanize.watermark_forensics import neutralize_watermark
        result = neutralize_watermark(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None


# ═══════════════════════════════════════════════════════════════
#  COGNITIVE MODELER
# ═══════════════════════════════════════════════════════════════

class TestCognitiveModeler:
    """Tests for cognitive_model.py."""

    SAMPLE = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable. Each component works independently. "
        "The overall performance meets expectations. Results are consistent "
        "across multiple runs. Users report satisfaction with the speed. "
        "The implementation follows best practices. Documentation is "
        "comprehensive. Testing covers all edge cases. Deployment is "
        "straightforward. Monitoring is built-in."
    )

    def test_model_en(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm = CognitiveModeler(lang="en", seed=42)
        result = cm.model(self.SAMPLE, intensity=0.7)
        assert result.text is not None
        assert isinstance(result.text, str)

    def test_model_empty(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm = CognitiveModeler(lang="en")
        result = cm.model("", intensity=0.5)
        assert result.text == ""
        assert result.total_artefacts == 0

    def test_model_short_text(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm = CognitiveModeler(lang="en")
        result = cm.model("Short text.", intensity=0.5)
        assert result.text == "Short text."

    def test_cognitive_result_fields(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm = CognitiveModeler(lang="en", seed=42)
        result = cm.model(self.SAMPLE, intensity=0.8)
        assert hasattr(result, "hedges_added")
        assert hasattr(result, "corrections_added")
        assert hasattr(result, "asides_added")
        assert hasattr(result, "fatigue_simplifications")
        assert isinstance(result.total_artefacts, int)

    def test_analyze_uniformity(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm = CognitiveModeler(lang="en")
        analysis = cm.analyze_uniformity(self.SAMPLE)
        assert isinstance(analysis, dict)
        assert "uniformity_score" in analysis or "verdict" in analysis

    def test_module_level_function(self):
        from texthumanize.cognitive_model import model_cognition
        result = model_cognition(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_seed_reproducibility(self):
        from texthumanize.cognitive_model import CognitiveModeler
        cm1 = CognitiveModeler(lang="en", seed=42)
        cm2 = CognitiveModeler(lang="en", seed=42)
        r1 = cm1.model(self.SAMPLE, intensity=0.5)
        r2 = cm2.model(self.SAMPLE, intensity=0.5)
        assert r1.text == r2.text

    def test_multilang_ru(self):
        from texthumanize.cognitive_model import CognitiveModeler
        text = (
            "Система обрабатывает данные эффективно. Она справляется с большими "
            "объёмами информации. Архитектура масштабируема. Компоненты работают "
            "независимо. Производительность соответствует ожиданиям. Результаты "
            "стабильны. Пользователи довольны скоростью."
        )
        cm = CognitiveModeler(lang="ru", seed=42)
        result = cm.model(text, intensity=0.7)
        assert result.text is not None


# ═══════════════════════════════════════════════════════════════
#  ADVERSARIAL PLAY
# ═══════════════════════════════════════════════════════════════

class TestAdversarialPlay:
    """Tests for adversarial_play.py."""

    SAMPLE = (
        "Additionally, the system processes data efficiently. "
        "Furthermore, it handles large volumes of information without "
        "significant delays. Moreover, the architecture was designed "
        "to be scalable. It is important to note that each component "
        "works independently. The overall performance meets expectations."
    )

    def test_play_en(self):
        from texthumanize.adversarial_play import AdversarialPlay
        ap = AdversarialPlay(lang="en", seed=42)
        result = ap.play(self.SAMPLE, intensity=0.5, max_rounds=2)
        assert result.text is not None
        assert isinstance(result.text, str)

    def test_play_empty(self):
        from texthumanize.adversarial_play import AdversarialPlay
        ap = AdversarialPlay(lang="en")
        result = ap.play("", intensity=0.5)
        assert result.text == ""

    def test_play_result_fields(self):
        from texthumanize.adversarial_play import AdversarialPlay
        ap = AdversarialPlay(lang="en", seed=42)
        result = ap.play(self.SAMPLE, intensity=0.5, max_rounds=2)
        assert hasattr(result, "rounds")
        assert hasattr(result, "initial_score")
        assert hasattr(result, "final_score")
        assert hasattr(result, "history")
        assert isinstance(result.score_drop, float)

    def test_problem_map(self):
        from texthumanize.adversarial_play import build_problem_map
        pm = build_problem_map(self.SAMPLE, lang="en")
        assert isinstance(pm, list)
        assert len(pm) > 0
        assert "flagged" in pm[0]
        assert "score" in pm[0]

    def test_module_level_function(self):
        from texthumanize.adversarial_play import adversarial_humanize
        result = adversarial_humanize(
            self.SAMPLE, lang="en", max_rounds=1, seed=42,
        )
        assert result.text is not None

    def test_ai_opener_removal(self):
        from texthumanize.adversarial_play import AdversarialPlay
        ap = AdversarialPlay(lang="en", seed=42)
        fixed = ap._fix_ai_opener("Additionally, the data is processed.")
        assert not fixed.startswith("Additionally,")

    def test_contractions(self):
        from texthumanize.adversarial_play import AdversarialPlay
        ap = AdversarialPlay(lang="en", seed=42)
        result = ap._fix_contractions("It is very important and it does not work.")
        assert "It's" in result or "it's" in result or "doesn't" in result


# ═══════════════════════════════════════════════════════════════
#  ASH ENGINE
# ═══════════════════════════════════════════════════════════════

class TestASHEngine:
    """Tests for ash_engine.py."""

    SAMPLE = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable. Each component works independently. "
        "The overall performance meets expectations. Results are consistent "
        "across multiple runs. Users report satisfaction with the speed."
    )

    def test_humanize_balanced(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en", seed=42)
        result = engine.humanize(self.SAMPLE, preset="balanced")
        assert result.text is not None
        assert result.methods_used > 0
        assert result.elapsed_ms > 0

    def test_humanize_light(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en", seed=42)
        result = engine.humanize(self.SAMPLE, preset="light")
        assert result.text is not None

    def test_humanize_forensic(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en", seed=42)
        result = engine.humanize(self.SAMPLE, preset="forensic")
        assert "watermark_forensics" in result.steps_applied

    def test_humanize_empty(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en")
        result = engine.humanize("")
        assert result.text == ""
        assert result.methods_used == 0

    def test_analyze(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en")
        analysis = engine.analyze(self.SAMPLE)
        assert isinstance(analysis, dict)
        assert "watermark" in analysis
        assert "perplexity_curve" in analysis
        assert "signature" in analysis
        assert "cognitive_uniformity" in analysis
        assert "problem_map" in analysis

    def test_ash_result_fields(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en", seed=42)
        result = engine.humanize(self.SAMPLE, preset="balanced")
        assert hasattr(result, "watermark")
        assert hasattr(result, "perplexity")
        assert hasattr(result, "signature")
        assert hasattr(result, "cognitive")
        assert hasattr(result, "adversarial")
        assert isinstance(result.steps_applied, list)

    def test_module_level_ash_humanize(self):
        from texthumanize.ash_engine import ash_humanize
        result = ash_humanize(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_module_level_ash_analyze(self):
        from texthumanize.ash_engine import ash_analyze
        analysis = ash_analyze(self.SAMPLE, lang="en")
        assert isinstance(analysis, dict)

    def test_list_presets(self):
        from texthumanize.ash_engine import list_ash_presets
        presets = list_ash_presets()
        assert isinstance(presets, dict)
        assert "stealth" in presets
        assert "balanced" in presets
        assert "light" in presets
        assert "forensic" in presets
        assert "academic" in presets

    def test_custom_config(self):
        from texthumanize.ash_engine import ASHEngine
        engine = ASHEngine(lang="en", seed=42)
        result = engine.humanize(
            self.SAMPLE,
            preset=None,
            intensity=0.3,
            enable_watermark=True,
            enable_perplexity=False,
            enable_signature=True,
            enable_cognitive=False,
            enable_adversarial=False,
        )
        assert result.text is not None
        assert "perplexity_sculpting" not in result.steps_applied


# ═══════════════════════════════════════════════════════════════
#  CORE.PY INTEGRATION
# ═══════════════════════════════════════════════════════════════

class TestCoreASHIntegration:
    """Tests for ASH™ functions exposed via core.py."""

    SAMPLE = (
        "The system processes data efficiently. It handles large volumes "
        "of information without significant delays. The architecture was "
        "designed to be scalable."
    )

    def test_core_ash_humanize(self):
        from texthumanize.core import ash_humanize
        result = ash_humanize(self.SAMPLE, lang="en", seed=42, preset="light")
        assert result.text is not None

    def test_core_ash_analyze(self):
        from texthumanize.core import ash_analyze
        analysis = ash_analyze(self.SAMPLE, lang="en")
        assert isinstance(analysis, dict)

    def test_core_sculpt_perplexity(self):
        from texthumanize.core import sculpt_perplexity
        result = sculpt_perplexity(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_core_transfer_signature(self):
        from texthumanize.core import transfer_signature
        result = transfer_signature(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_core_detect_statistical_watermark(self):
        from texthumanize.core import detect_statistical_watermark
        result = detect_statistical_watermark(self.SAMPLE, lang="en")
        assert hasattr(result, "verdict")

    def test_core_neutralise_watermark(self):
        from texthumanize.core import neutralise_watermark
        result = neutralise_watermark(self.SAMPLE, lang="en", seed=42)
        assert result.text is not None

    def test_core_model_cognition(self):
        text = (
            "The system processes data. It handles large volumes. "
            "The architecture was designed. Each component works. "
            "Performance meets expectations."
        )
        from texthumanize.core import model_cognition
        result = model_cognition(text, lang="en", seed=42)
        assert result.text is not None

    def test_core_adversarial_humanize(self):
        from texthumanize.core import adversarial_humanize
        result = adversarial_humanize(
            self.SAMPLE, lang="en", max_rounds=1, seed=42,
        )
        assert result.text is not None

    def test_core_list_ash_presets(self):
        from texthumanize.core import list_ash_presets
        presets = list_ash_presets()
        assert "balanced" in presets


# ═══════════════════════════════════════════════════════════════
#  __init__.py LAZY IMPORTS
# ═══════════════════════════════════════════════════════════════

class TestInitImports:
    """Test that ASH™ symbols are accessible via texthumanize package."""

    def test_ash_in_all(self):
        import texthumanize
        assert "ash_humanize" in texthumanize.__all__
        assert "ASHEngine" in texthumanize.__all__
        assert "PerplexitySculptor" in texthumanize.__all__
        assert "SignatureTransfer" in texthumanize.__all__
        assert "WatermarkForensics" in texthumanize.__all__
        assert "CognitiveModeler" in texthumanize.__all__
        assert "AdversarialPlay" in texthumanize.__all__

    def test_lazy_import_ash_humanize(self):
        import texthumanize
        fn = texthumanize.ash_humanize
        assert callable(fn)

    def test_lazy_import_ash_engine_class(self):
        import texthumanize
        cls = texthumanize.ASHEngine
        assert cls is not None

    def test_lazy_import_perplexity_sculptor(self):
        import texthumanize
        cls = texthumanize.PerplexitySculptor
        assert cls is not None

    def test_lazy_import_watermark_forensics(self):
        import texthumanize
        cls = texthumanize.WatermarkForensics
        assert cls is not None

    def test_lazy_import_cognitive_modeler(self):
        import texthumanize
        cls = texthumanize.CognitiveModeler
        assert cls is not None

    def test_lazy_import_adversarial_play(self):
        import texthumanize
        cls = texthumanize.AdversarialPlay
        assert cls is not None

    def test_neutralize_alias(self):
        import texthumanize
        fn = texthumanize.neutralize_watermark
        assert callable(fn)
