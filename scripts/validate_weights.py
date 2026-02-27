#!/usr/bin/env python3
"""Quick validation that trained weights load and produce good results."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from texthumanize.neural_detector import NeuralAIDetector
from texthumanize.neural_lm import NeuralPerplexity

det = NeuralAIDetector()

ai_text = (
    "Furthermore, it is important to note that the utilization of advanced "
    "methodologies has significantly contributed to the overall improvement "
    "of systemic outcomes. The implementation of comprehensive strategies "
    "ensures that all stakeholders benefit from the enhanced framework."
)
r = det.detect(ai_text, "en")
print(f"AI text: score={r['score']}, verdict={r['verdict']}, conf={r['confidence']}")

human_text = (
    "So I was thinking about this the other day - you know how sometimes "
    "things just dont work the way youd expect? Yeah, that happened again. "
    "Tried to fix the sink, ended up flooding half the kitchen."
)
r = det.detect(human_text, "en")
print(f"Human text: score={r['score']}, verdict={r['verdict']}, conf={r['confidence']}")

lm = NeuralPerplexity()
ppl_ai = lm.perplexity(ai_text)
ppl_human = lm.perplexity(human_text)
print(f"AI perplexity: {ppl_ai:.2f}")
print(f"Human perplexity: {ppl_human:.2f}")

print(f"\nDetector params: {det.param_count}")
print(f"Detector arch: {det.architecture}")
