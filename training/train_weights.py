#!/usr/bin/env python3
"""Fit the detector's metric weights from a labelled corpus.

This is TextHumanize's "learned model" — and it is deliberately a *transparent*
one. The detector turns each text into a vector of interpretable metric scores
(pattern, burstiness, structure, voice, …); the model is just the per-metric
weight applied to that vector. That is a single-layer logistic classifier — a
one-neuron net — whose parameters are these weights. We fit it OFFLINE here and
ship only the fitted numbers (``texthumanize/detector_weights.json``): no model
runtime, no black box, every parameter readable and diffable in git.

Guardrails baked in so an automated refit can never quietly make things worse:
  * weights are constrained non-negative and to the probability simplex, so the
    "each metric votes toward AI" meaning of the ensemble is preserved;
  * the fit is L2-regularised toward the current shipped weights, so a small or
    skewed corpus nudges rather than overwrites;
  * a held-out split gates the result — a candidate is only recommended when it
    does not regress held-out accuracy/AUROC versus the current weights.

Usage:
    python training/train_weights.py                 # fit + report, no write
    python training/train_weights.py --write         # write if the gate passes
    python training/train_weights.py --corpus x.jsonl --seed 0

Corpus format: one JSON object per line — {"text", "label": "ai"|"human", "lang"}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from texthumanize.detectors import AIDetector  # noqa: E402

# Metric order = the keys of the detector's weight table. Kept explicit so the
# feature vector and the emitted weights line up 1:1 with the detector.
METRICS = list(AIDetector._WEIGHTS.keys())

# Attribute on DetectionResult for each metric (a few names differ from the key).
_ATTR = {
    "pattern": "pattern_score", "burstiness": "burstiness_score",
    "voice": "voice_score", "stylometry": "stylometry_score",
    "entity": "entity_score", "structure": "structure_score",
    "discourse": "discourse_score", "rhythm": "rhythm_score",
    "entropy": "entropy_score", "opening": "opening_score",
    "grammar": "grammar_score", "vocabulary": "vocabulary_score",
    "perplexity": "perplexity_score", "semantic_rep": "semantic_rep_score",
    "topic_sentence": "topic_sent_score", "coherence": "coherence_score",
    "readability": "readability_score", "punctuation": "punctuation_score",
    "zipf": "zipf_score",
}


def load_corpus(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def extract_features(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Run the detector on each sample → feature matrix X and labels y."""
    det = AIDetector()
    X, y = [], []
    for r in rows:
        res = det.detect(r["text"], r.get("lang", "auto"))
        X.append([getattr(res, _ATTR[m], 0.5) for m in METRICS])
        y.append(1.0 if r["label"] == "ai" else 0.0)
    return np.asarray(X, float), np.asarray(y, float)


def project_to_simplex(v: np.ndarray) -> np.ndarray:
    """Euclidean projection onto {w >= 0, sum w = 1} (Duchi et al. 2008)."""
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1.0
    ind = np.arange(1, len(v) + 1)
    cond = u - css / ind > 0
    rho = ind[cond][-1]
    theta = css[cond][-1] / rho
    return np.maximum(v - theta, 0.0)


def fit(X, y, w0, l2=6.0, iters=4000, lr=0.4, seed=0):
    """Projected-gradient logistic fit of simplex weights + scale/bias.

    Minimises BCE(sigmoid(a*<w,x> + b), y) + l2 * ||w - w0||^2, with w kept on
    the simplex. Only w is shipped; a,b emulate the detector's own calibration
    during fitting so the weights land in a usable range.
    """
    rng = np.random.default_rng(seed)
    w = w0.copy()
    a, b = 8.0, -4.0
    n = len(y)
    for _ in range(iters):
        m = X @ w
        z = a * m + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        err = p - y
        gw = (X.T @ (err * a)) / n + 2.0 * l2 * (w - w0)
        ga = float((err * m).mean())
        gb = float(err.mean())
        w = project_to_simplex(w - lr * gw)
        a -= lr * ga
        b -= lr * gb
        _ = rng  # reserved for optional stochastic variants
    return w, a, b


def evaluate(rows, weights):
    """Accuracy + AUROC on the FULL detector with `weights` installed."""
    AIDetector._fitted_weights_cache = dict(weights)
    det = AIDetector()
    probs, y = [], []
    for r in rows:
        probs.append(det.detect(r["text"], r.get("lang", "auto")).ai_probability)
        y.append(1 if r["label"] == "ai" else 0)
    AIDetector._fitted_weights_cache = None  # reset
    probs, y = np.asarray(probs), np.asarray(y)
    acc = float(((probs >= 0.5).astype(int) == y).mean())
    auroc = _auroc(y, probs)
    return acc, auroc


def _auroc(y, s):
    pos = s[y == 1]
    neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins) / (len(pos) * len(neg))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(Path(__file__).parent / "corpus.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "texthumanize" / "detector_weights.json"))
    ap.add_argument("--l2", type=float, default=6.0)
    ap.add_argument("--trust-n", type=int, default=500,
                    help="corpus size at which the fit is fully trusted (shrinkage)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--write", action="store_true", help="write weights if the held-out gate passes")
    args = ap.parse_args()

    rows = load_corpus(Path(args.corpus))
    n_ai = sum(1 for r in rows if r["label"] == "ai")
    print(f"corpus: {len(rows)} samples ({n_ai} ai / {len(rows) - n_ai} human)")

    X, y = extract_features(rows)
    w0 = np.array([AIDetector._WEIGHTS[m] for m in METRICS], float)
    w0 = w0 / w0.sum()

    # Deterministic held-out split (every 3rd sample), stratified enough for a gate.
    idx = np.arange(len(rows))
    held = idx % 3 == 0
    train_mask = ~held

    w_fit, a, b = fit(X[train_mask], y[train_mask], w0, l2=args.l2, seed=args.seed)

    # Shrinkage by evidence: trust the fit only in proportion to how much
    # labelled data backs it. With a tiny corpus the candidate barely moves off
    # the shipped weights (so a lucky separable split can't zero out a strong
    # metric like `pattern`); as the corpus grows past TRUST_N the fit takes
    # over. This is the mechanism by which the model genuinely improves as the
    # community contributes more labels.
    n_train = int(train_mask.sum())
    alpha = min(1.0, n_train / args.trust_n)
    w = project_to_simplex(alpha * w_fit + (1.0 - alpha) * w0)
    print(f"shrinkage: alpha={alpha:.3f} (n_train={n_train}, trust_n={args.trust_n})")

    cur = {m: AIDetector._WEIGHTS[m] for m in METRICS}
    cand = {m: round(float(wi), 5) for m, wi in zip(METRICS, w)}

    held_rows = [r for r, h in zip(rows, held) if h]
    acc_cur, auroc_cur = evaluate(held_rows, cur)
    acc_new, auroc_new = evaluate(held_rows, cand)

    print(f"\nheld-out ({len(held_rows)} samples):")
    print(f"  current  acc={acc_cur:.3f}  auroc={auroc_cur:.3f}")
    print(f"  candidate acc={acc_new:.3f}  auroc={auroc_new:.3f}")
    print("\ntop candidate weights:")
    for m, wi in sorted(cand.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {m:14} {wi:.4f}  (was {cur[m]:.4f})")

    # Gate: never regress held-out accuracy, and keep AUROC within a small margin.
    passes = (acc_new >= acc_cur - 1e-9) and (auroc_new >= auroc_cur - 0.02)
    print(f"\ngate: {'PASS' if passes else 'FAIL'} (candidate must not regress held-out)")

    if args.write:
        if not passes:
            print("not writing — gate failed.")
            return 1
        payload = {
            "schema": "texthumanize.detector_weights.v1",
            "fitted": True,
            "note": "Fitted by training/train_weights.py from training/corpus.jsonl. "
                    "Non-negative simplex weights, L2-regularised toward the previous "
                    "weights, gated on a held-out split. Retrain via the GitHub workflow.",
            "trained_at": None,  # stamped by the workflow (Date unavailable here)
            "corpus_size": len(rows),
            "metrics": {"held_out_accuracy": round(acc_new, 4), "held_out_auroc": round(auroc_new, 4)},
            "weights": cand,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
