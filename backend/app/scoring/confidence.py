"""Confidence presentation, owned by the backend as architecture.md requires.

Phase 2 replaces how confidence_score itself is computed. This module exists so
that the score and the word shown next to it can never disagree: there is one
mapping, and both the API and the UI read it.
"""

from typing import Literal

ConfidenceLabel = Literal["Low", "Medium", "High"]

# Provisional presentation bands, not a scoring model. They move together with
# the Phase 2 confidence computation.
HIGH_THRESHOLD = 75
MEDIUM_THRESHOLD = 50


def confidence_label(score: int) -> ConfidenceLabel:
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"
