import sys
import trace
from unittest.mock import MagicMock
from texthumanize.tone import ToneAdjuster, ToneLevel, ToneReport

adj = ToneAdjuster("en", seed=42)
adj.rng = MagicMock()
adj.rng.random.return_value = 0.0
adj._analyzer = MagicMock()
adj._analyzer.analyze.return_value = ToneReport(
    primary_tone=ToneLevel.FORMAL,
    confidence=0.9,
    scores={},
)

text = "I obtain data and obtain results."

# Trace execution
tracer = trace.Trace(count=False, trace=True)
tracer.runfunc(adj.adjust, text, target=ToneLevel.CASUAL, intensity=0.1)
