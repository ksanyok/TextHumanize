# Self-improving detector weights

TextHumanize's AI-text detector is a **transparent learned model**, not a hand-
wavy "neural net" and not a black box. Every text becomes a vector of readable
metric scores — `pattern`, `burstiness`, `structure`, `voice`, `stylometry`, … —
and the model is simply the per-metric weight applied to that vector. That is a
single-layer logistic classifier (one neuron); its parameters are the weights in
[`texthumanize/detector_weights.json`](../texthumanize/detector_weights.json).

We fit those weights **offline** from a labelled corpus and ship only the fitted
numbers. The library carries no ML runtime, downloads no model, and every
parameter is readable and diffable in git. This is what lets the detector get
**better with each release** while staying tiny and fully offline.

## The loop

```
training/corpus.jsonl   →   train_weights.py   →   detector_weights.json   →   detector
   (labelled data)          (numpy fit + gate)      (versioned weights)        (uses them)
        ▲                                                                          │
        └──────────────  new labels grow the corpus, next refit improves  ◄────────┘
```

1. **Corpus** — `corpus.jsonl`, one object per line: `{"text", "label":"ai"|"human", "lang"}`.
   Seeded with public-domain human prose (guaranteed human) and characteristic
   AI patterns across en/ru/uk/de/es/pl. **It grows over time** — that is the
   "learning".
2. **Fit** — `train_weights.py` runs the detector to extract each sample's metric
   vector, then fits non-negative weights on the probability simplex with a
   projected-gradient logistic objective.
3. **Guardrails** so an automated refit can never quietly regress:
   - **Non-negative + simplex** — preserves the "each metric votes toward AI"
     meaning of the ensemble.
   - **Shrinkage by evidence** — the fit is trusted only in proportion to corpus
     size (`alpha = min(1, n/trust_n)`, `trust_n=500`). With today's small corpus
     the candidate barely moves off the shipped weights; as the corpus grows past
     `trust_n` the data takes over. This is the mechanism by which more labels =
     a genuinely better model, without a lucky small split zeroing out a strong
     metric.
   - **Held-out gate** — a candidate is only accepted if it does not regress
     held-out accuracy/AUROC versus the current weights.
4. **Ship** — an accepted candidate is written to `detector_weights.json`; the
   detector loads it (falling back to the hand-tuned defaults if absent/invalid).

## Run it

```bash
python training/train_weights.py            # fit + report, writes nothing
python training/train_weights.py --write    # write the candidate iff the gate passes
```

## Contributing labels

The most useful contribution is **more, cleaner labelled data**. Add lines to
`corpus.jsonl` — real human writing (ideally with a verifiable public-domain or
self-authored source) and real AI output, tagged by language. Keep classes and
languages roughly balanced. Open a PR; CI re-fits and reports the effect.

## Privacy — what the corpus is NOT

This corpus is **curated and public / explicitly contributed**. It is **not**
harvested from users. The browser extension's 👍/👎 detection feedback is stored
on-device and is **content-free** (it records the outcome and structural hints,
never your text), so there is no user text to ingest here even in principle. Site
detection has a parallel, structural-only feedback path (see the extension's
`engine/site-forensics.js`) — those hints carry no personal content either.

## Automated retraining

`.github/workflows/retrain.yml` runs the fit on a schedule / manual dispatch /
when `corpus.jsonl` changes. If the gate passes and the weights actually move, it
opens a pull request with the new `detector_weights.json` and the training
report. A human reviews and merges — the model never updates itself unattended.
