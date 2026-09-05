"""
Confidence scoring.

Central place for turning "how many/strong are the signals behind
this claim" into a 0-1 confidence score. Keep the scoring function
here so reasoning.py and enrichment.py never hand-roll their own
number and drift out of sync.
"""

from __future__ import annotations


def score_from_signal_count(signal_count: int, max_signals: int = 4) -> float:
    """Simple monotonic mapping: more corroborating signals -> higher confidence.
    Caps below 0.95 — Orvyra should never claim certainty on an inference."""
    if signal_count <= 0:
        return 0.3
    return round(min(0.3 + (signal_count / max_signals) * 0.65, 0.95), 2)


def pursue_threshold() -> float:
    """Below this opportunity confidence, recommend against pursuing."""
    return 0.35
