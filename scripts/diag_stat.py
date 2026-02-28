"""Diagnostic: why does statistical detector return ~0.000?"""
import math
import sys
sys.path.insert(0, ".")

from texthumanize.statistical_detector import (
    extract_features, _predict_proba, _LR_WEIGHTS, _LR_BIAS,
    _get_feat_norm, _sigmoid, StatisticalDetector
)

AI_TEXT = (
    "Artificial intelligence has revolutionized numerous industries, "
    "fundamentally transforming how organizations approach complex problems. "
    "The integration of machine learning algorithms has enabled unprecedented "
    "advances in data analysis and pattern recognition. Furthermore, the "
    "implementation of neural networks has demonstrated remarkable capabilities "
    "in natural language processing and computer vision applications. It is "
    "worth noting that these technological developments have significant "
    "implications for the future of human-computer interaction."
)

HUMAN_TEXT = (
    "I was at the store yesterday and bumped into Sarah - haven't seen her in "
    "ages! She told me about her new job, which sounds amazing tbh. Can't "
    "believe how fast time flies. Anyway, we grabbed coffee and just chatted "
    "for like two hours. It reminded me why I should really make more effort "
    "to see old friends, you know?"
)

det = StatisticalDetector(lang="en")

for label, text in [("AI", AI_TEXT), ("HUMAN", HUMAN_TEXT)]:
    feats = det.extract_features(text)
    ntok = len(text.split())
    feat_norm = _get_feat_norm("en")

    z = _LR_BIAS
    contributions = []
    for name, w in _LR_WEIGHTS.items():
        raw = feats.get(name, 0.0)
        mu, std = feat_norm.get(name, (0.0, 1.0))
        normed = (raw - mu) / std if std > 0 else raw - mu
        normed = max(-3.0, min(3.0, normed))
        contrib = w * normed
        z += contrib
        contributions.append((name, raw, normed, w, contrib))

    prob = _sigmoid(-z)
    print(f"\n=== {label} TEXT ===")
    print(f"z = {z:.4f}, -z = {-z:.4f}, prob = {prob:.6f}")
    print(f"Bias = {_LR_BIAS}")

    contributions.sort(key=lambda x: abs(x[4]), reverse=True)
    print("\nTop 15 feature contributions:")
    for name, raw, normed, w, contrib in contributions[:15]:
        print(f"  {name:30s} raw={raw:.4f} normed={normed:+.3f} w={w:+.3f} contrib={contrib:+.4f}")

    print(f"\nSum of all contributions (excl bias): {sum(c[4] for c in contributions):.4f}")
    print(f"Official prob from _predict_proba: {_predict_proba(feats, ntok, 'en'):.6f}")
