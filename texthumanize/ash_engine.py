"""ASH™ Engine — Adaptive Statistical Humanization.

Unified pipeline that orchestrates all five ASH™ proprietary
technologies into a single, coherent humanization pass:

1. **Watermark Forensics™** — detect and neutralize LLM watermarks
2. **Perplexity Sculpting™** — reshape the perplexity curve
3. **Statistical Signature Transfer™** — shift statistical fingerprint
4. **Cognitive Load Modeling™** — introduce human cognitive patterns
5. **Adversarial Ensemble Self-Play™** — iterative detector-guided polish

The ordering is deliberate: watermark removal first (changes tokens),
then sculpting + signature transfer (global statistical pass), then
cognitive patterns (document-level), and finally adversarial polish
(the quality gate).

───────────────────────────────────────────────────────────
ASH™ (Adaptive Statistical Humanization) is a proprietary
technology developed by Oleksandr K. for TextHumanize.
All sub-methods (Perplexity Sculpting™, Statistical Signature
Transfer™, Watermark Forensics™, Cognitive Load Modeling™,
Adversarial Ensemble Self-Play™) are original works of the author.
───────────────────────────────────────────────────────────

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  RESULT
# ═══════════════════════════════════════════════════════════════

@dataclass
class ASHResult:
    """Combined result of ASH™ pipeline."""
    text: str
    original_text: str
    lang: str = "en"

    # Sub-method results (None if skipped)
    watermark: Any | None = None
    perplexity: Any | None = None
    signature: Any | None = None
    cognitive: Any | None = None
    adversarial: Any | None = None
    restructure: Any | None = None

    # Overall metrics
    elapsed_ms: float = 0.0
    steps_applied: list[str] = field(default_factory=list)

    @property
    def methods_used(self) -> int:
        """Number of ASH™ methods actually applied."""
        return len(self.steps_applied)


# ═══════════════════════════════════════════════════════════════
#  PRESETS
# ═══════════════════════════════════════════════════════════════

ASH_PRESETS: dict[str, dict[str, Any]] = {
    "stealth": {
        "description": "Maximum evasion — all 6 methods, high intensity",
        "intensity": 0.8,
        "enable_watermark": True,
        "enable_perplexity": True,
        "enable_signature": True,
        "enable_cognitive": True,
        "enable_adversarial": True,
        "enable_restructure": True,
        "adversarial_rounds": 4,
        "adversarial_target": 0.25,
    },
    "balanced": {
        "description": "Good evasion with minimal text changes",
        "intensity": 0.5,
        "enable_watermark": True,
        "enable_perplexity": True,
        "enable_signature": True,
        "enable_cognitive": True,
        "enable_adversarial": True,
        "enable_restructure": True,
        "adversarial_rounds": 3,
        "adversarial_target": 0.35,
    },
    "light": {
        "description": "Light touch — signature + sculpting only",
        "intensity": 0.3,
        "enable_watermark": True,
        "enable_perplexity": True,
        "enable_signature": True,
        "enable_cognitive": False,
        "enable_adversarial": False,
        "enable_restructure": False,
        "adversarial_rounds": 0,
        "adversarial_target": 0.5,
    },
    "forensic": {
        "description": "Watermark detection + neutralization only",
        "intensity": 0.6,
        "enable_watermark": True,
        "enable_perplexity": False,
        "enable_signature": False,
        "enable_cognitive": False,
        "enable_adversarial": False,
        "enable_restructure": False,
        "adversarial_rounds": 0,
        "adversarial_target": 0.5,
    },
    "academic": {
        "description": "Subtle changes preserving academic register",
        "intensity": 0.35,
        "enable_watermark": True,
        "enable_perplexity": True,
        "enable_signature": True,
        "enable_cognitive": True,
        "enable_adversarial": True,
        "enable_restructure": True,
        "adversarial_rounds": 2,
        "adversarial_target": 0.40,
    },
}


# ═══════════════════════════════════════════════════════════════
#  ENGINE
# ═══════════════════════════════════════════════════════════════

class ASHEngine:
    """Unified ASH™ (Adaptive Statistical Humanization) pipeline.

    Orchestrates all five proprietary technologies:

    1. Watermark Forensics™
    2. Perplexity Sculpting™
    3. Statistical Signature Transfer™
    4. Cognitive Load Modeling™
    5. Adversarial Ensemble Self-Play™

    Usage::

        engine = ASHEngine(lang="en")
        result = engine.humanize(text, preset="balanced")
        print(result.text)
        print(f"Used {result.methods_used} methods in {result.elapsed_ms:.0f}ms")

    Preset selection::

        # Maximum evasion
        result = engine.humanize(text, preset="stealth")

        # Minimal changes
        result = engine.humanize(text, preset="light")

        # Custom configuration
        result = engine.humanize(
            text,
            intensity=0.6,
            enable_watermark=True,
            enable_perplexity=True,
            enable_signature=True,
            enable_cognitive=False,
            enable_adversarial=True,
        )
    """

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
        *,
        pipeline_intensity: int = 60,
        pipeline_profile: str = "web",
    ) -> None:
        self.lang = lang
        self.seed = seed
        self.pipeline_intensity = pipeline_intensity
        self.pipeline_profile = pipeline_profile

    def humanize(
        self,
        text: str,
        *,
        preset: str | None = "balanced",
        intensity: float | None = None,
        enable_watermark: bool | None = None,
        enable_perplexity: bool | None = None,
        enable_signature: bool | None = None,
        enable_restructure: bool | None = None,
        enable_cognitive: bool | None = None,
        enable_adversarial: bool | None = None,
        adversarial_rounds: int | None = None,
        adversarial_target: float | None = None,
        use_pipeline: bool = True,
    ) -> ASHResult:
        """Run the full ASH™ pipeline.

        Parameters
        ----------
        text : str
            Input text to humanize.
        preset : str or None
            One of: "stealth", "balanced", "light", "forensic", "academic".
            If None, uses individual enable_* flags.
        intensity : float or None
            Override preset intensity (0.0–1.0).
        enable_* : bool or None
            Override preset per-method toggles.
        adversarial_rounds : int or None
            Override max adversarial rounds.
        adversarial_target : float or None
            Override adversarial target score.

        Returns
        -------
        ASHResult
        """
        if not text or not text.strip():
            return ASHResult(text=text, original_text=text, lang=self.lang)

        t0 = time.monotonic()

        # Resolve configuration
        cfg = self._resolve_config(
            preset=preset,
            intensity=intensity,
            enable_watermark=enable_watermark,
            enable_perplexity=enable_perplexity,
            enable_signature=enable_signature,
            enable_restructure=enable_restructure,
            enable_cognitive=enable_cognitive,
            enable_adversarial=enable_adversarial,
            adversarial_rounds=adversarial_rounds,
            adversarial_target=adversarial_target,
        )

        current = text
        steps: list[str] = []

        wm_result = None
        ppl_result = None
        sig_result = None
        rst_result = None
        cog_result = None
        adv_result = None

        # ── Step 1: Watermark Forensics™ ──
        if cfg["enable_watermark"]:
            try:
                from texthumanize.watermark_forensics import WatermarkForensics
                wf = WatermarkForensics(lang=self.lang, seed=self.seed)
                wm_result = wf.neutralise(current, intensity=cfg["intensity"])
                current = wm_result.text
                steps.append("watermark_forensics")
                logger.info("ASH: Watermark Forensics™ done (verdict=%s)", wm_result.verdict)
            except Exception:
                logger.warning("ASH: Watermark Forensics™ failed", exc_info=True)

        # ── Step 2: Perplexity Sculpting™ ──
        if cfg["enable_perplexity"]:
            try:
                from texthumanize.perplexity_sculptor import PerplexitySculptor
                ps = PerplexitySculptor(lang=self.lang, seed=self.seed)
                ppl_result = ps.sculpt(current, intensity=cfg["intensity"])
                current = ppl_result.text
                steps.append("perplexity_sculpting")
                logger.info("ASH: Perplexity Sculpting™ done (surprises=%d)", ppl_result.surprises_injected)
            except Exception:
                logger.warning("ASH: Perplexity Sculpting™ failed", exc_info=True)

        # ── Step 3: Statistical Signature Transfer™ ──
        if cfg["enable_signature"]:
            try:
                from texthumanize.signature_transfer import SignatureTransfer
                st = SignatureTransfer(lang=self.lang, seed=self.seed)
                sig_result = st.transfer(current, intensity=cfg["intensity"])
                current = sig_result.text
                steps.append("signature_transfer")
                logger.info("ASH: Signature Transfer™ done (distance %.3f → %.3f)",
                            sig_result.distance_before, sig_result.distance_after)
            except Exception:
                logger.warning("ASH: Signature Transfer™ failed", exc_info=True)

        # ── Step 3½: Main pipeline humanization ──────────────
        # The core 20-stage pipeline handles the heavy lifting:
        # typography, debureaucratization, structure diversification,
        # repetition reduction, paraphrasing, syntax rewriting,
        # tone harmonization, naturalization, entropy injection, etc.
        # ASH pre-processing (steps 1-3) prepares the text, and
        # ASH post-processing (steps 4-6) fine-tunes after pipeline.
        if use_pipeline:
            try:
                from texthumanize.pipeline import HumanizeOptions, Pipeline
                opts = HumanizeOptions(
                    lang=self.lang,
                    profile=self.pipeline_profile,
                    intensity=self.pipeline_intensity,
                    seed=self.seed,
                )
                pipe = Pipeline(options=opts)
                pipe_result = pipe.run(current, self.lang)
                if pipe_result.text and pipe_result.text.strip():
                    current = pipe_result.text
                    steps.append("base_pipeline")
                    logger.info("ASH: Base pipeline done")
            except Exception:
                logger.warning("ASH: Base pipeline failed, continuing with ASH-only", exc_info=True)

        # ── Step 4: Sentence Restructuring™ ──
        if cfg.get("enable_restructure", True):
            try:
                from texthumanize.sentence_restructurer import SentenceRestructurer
                sr = SentenceRestructurer(
                    lang=self.lang,
                    intensity=int(cfg["intensity"] * 100),
                    seed=self.seed,
                )
                restructured = sr.process(current)
                if restructured != current:
                    rst_result = {
                        "changes": sr.changes,
                        "num_changes": len(sr.changes),
                    }
                    current = restructured
                    steps.append("sentence_restructuring")
                    logger.info("ASH: Sentence Restructuring done (%d changes)", len(sr.changes))
            except Exception:
                logger.warning("ASH: Sentence Restructuring failed", exc_info=True)

        # ── Step 5: Cognitive Load Modeling™ ──
        if cfg["enable_cognitive"]:
            try:
                from texthumanize.cognitive_model import CognitiveModeler
                cm = CognitiveModeler(lang=self.lang, seed=self.seed)
                cog_result = cm.model(current, intensity=cfg["intensity"])
                current = cog_result.text
                steps.append("cognitive_modeling")
                logger.info("ASH: Cognitive Modeling™ done (artefacts=%d)", cog_result.total_artefacts)
            except Exception:
                logger.warning("ASH: Cognitive Modeling™ failed", exc_info=True)

        # ── Step 6: Adversarial Ensemble Self-Play™ ──
        if cfg["enable_adversarial"]:
            try:
                from texthumanize.adversarial_play import AdversarialPlay
                ap = AdversarialPlay(lang=self.lang, seed=self.seed)
                adv_result = ap.play(
                    current,
                    intensity=cfg["intensity"],
                    max_rounds=cfg["adversarial_rounds"],
                    target_score=cfg["adversarial_target"],
                )
                current = adv_result.text
                steps.append("adversarial_play")
                logger.info(
                    "ASH: Adversarial Play™ done (%d rounds, score %.3f → %.3f)",
                    adv_result.rounds, adv_result.initial_score, adv_result.final_score,
                )
            except Exception:
                logger.warning("ASH: Adversarial Play™ failed", exc_info=True)

        elapsed = (time.monotonic() - t0) * 1000

        return ASHResult(
            text=current,
            original_text=text,
            lang=self.lang,
            watermark=wm_result,
            perplexity=ppl_result,
            signature=sig_result,
            cognitive=cog_result,
            adversarial=adv_result,
            restructure=rst_result,
            elapsed_ms=round(elapsed, 1),
            steps_applied=steps,
        )

    def analyze(self, text: str) -> dict[str, Any]:
        """Analyze text using all ASH™ diagnostic tools.

        Returns a comprehensive analysis dict covering:
        - Watermark detection
        - Perplexity curve analysis
        - Signature distance
        - Cognitive uniformity
        - Per-sentence problem map
        """
        analysis: dict[str, Any] = {"lang": self.lang}

        # Watermark detection
        try:
            from texthumanize.watermark_forensics import WatermarkForensics
            wf = WatermarkForensics(lang=self.lang)
            wm = wf.detect(text)
            analysis["watermark"] = {
                "verdict": wm.verdict,
                "watermark_strength": wm.watermark_strength,
                "green_ratio": wm.green_ratio,
            }
        except Exception as e:
            analysis["watermark"] = {"error": str(e)}

        # Perplexity curve
        try:
            from texthumanize.perplexity_sculptor import PerplexitySculptor
            ps = PerplexitySculptor(lang=self.lang)
            analysis["perplexity_curve"] = ps.analyze_curve(text)
        except Exception as e:
            analysis["perplexity_curve"] = {"error": str(e)}

        # Signature distance
        try:
            from texthumanize.signature_transfer import SignatureTransfer
            st = SignatureTransfer(lang=self.lang)
            sig = st.compute_signature(text)
            dist = st.distance_to_human(text)
            analysis["signature"] = {
                "distance_to_human": dist,
                "signature": sig,
            }
        except Exception as e:
            analysis["signature"] = {"error": str(e)}

        # Cognitive uniformity
        try:
            from texthumanize.cognitive_model import CognitiveModeler
            cm = CognitiveModeler(lang=self.lang)
            analysis["cognitive_uniformity"] = cm.analyze_uniformity(text)
        except Exception as e:
            analysis["cognitive_uniformity"] = {"error": str(e)}

        # Problem map
        try:
            from texthumanize.adversarial_play import AdversarialPlay
            ap = AdversarialPlay(lang=self.lang)
            pm = ap._build_problem_map(text, 0.5)
            flagged = sum(1 for s in pm if s["flagged"])
            analysis["problem_map"] = {
                "total_sentences": len(pm),
                "flagged_sentences": flagged,
                "flagged_ratio": flagged / max(1, len(pm)),
                "sentences": pm,
            }
        except Exception as e:
            analysis["problem_map"] = {"error": str(e)}

        return analysis

    # ── Config Resolution ──

    def _resolve_config(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve preset + overrides into a config dict."""
        preset_name = kwargs.get("preset", "balanced")

        if preset_name and preset_name in ASH_PRESETS:
            cfg = dict(ASH_PRESETS[preset_name])
        else:
            cfg = dict(ASH_PRESETS["balanced"])

        # Apply overrides
        for key in (
            "intensity", "enable_watermark", "enable_perplexity",
            "enable_signature", "enable_restructure", "enable_cognitive",
            "enable_adversarial", "adversarial_rounds", "adversarial_target",
        ):
            val = kwargs.get(key)
            if val is not None:
                cfg[key] = val

        return cfg


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def ash_humanize(
    text: str,
    lang: str = "en",
    *,
    preset: str = "balanced",
    intensity: float | None = None,
    seed: int | None = None,
    use_pipeline: bool = True,
    pipeline_intensity: int = 60,
    pipeline_profile: str = "web",
) -> ASHResult:
    """Humanize text using the full ASH™ pipeline.

    ASH™ (Adaptive Statistical Humanization) — orchestrates
    all five proprietary technologies in optimal order, integrated
    with the core 20-stage humanization pipeline.

    Parameters
    ----------
    text : str
        Input text.
    lang : str
        Language code ("en", "ru", "uk").
    preset : str
        "stealth", "balanced", "light", "forensic", "academic".
    intensity : float or None
        Override preset intensity.
    seed : int or None
        Random seed for reproducibility.
    use_pipeline : bool
        If True (default), run the base humanization pipeline
        between ASH pre-processing and post-processing stages.
    pipeline_intensity : int
        Intensity for the base pipeline (0-100).
    pipeline_profile : str
        Profile for the base pipeline ("web", "chat", "formal", etc.).
    """
    return ASHEngine(
        lang=lang, seed=seed,
        pipeline_intensity=pipeline_intensity,
        pipeline_profile=pipeline_profile,
    ).humanize(
        text, preset=preset, intensity=intensity,
        use_pipeline=use_pipeline,
    )


def ash_analyze(
    text: str,
    lang: str = "en",
) -> dict[str, Any]:
    """Analyze text using all ASH™ diagnostic tools.

    Returns watermark verdict, perplexity curve, signature
    distance, cognitive uniformity, and per-sentence problem map.
    """
    return ASHEngine(lang=lang).analyze(text)


def list_ash_presets() -> dict[str, dict[str, Any]]:
    """Return available ASH™ presets and their configurations."""
    return dict(ASH_PRESETS)
