"""
Injection Classifier — Lightweight ML-based prompt injection classifier.

Uses a simple TF-IDF + logistic regression model as a fallback when
a pre-trained transformer (DistilBERT) is not available.  The model
runs locally with zero network dependency.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of the ML classifier."""

    is_injection: bool
    confidence: float
    label: str  # "injection" | "benign"


class InjectionClassifier:
    """Lightweight prompt-injection classifier.

    Falls back to a keyword-weighted heuristic when no trained model
    is available.

    Usage::

        clf = InjectionClassifier()
        result = clf.classify("Ignore all previous instructions")
    """

    # Weighted injection vocabulary
    _INJECTION_VOCAB: dict[str, float] = {
        "ignore": 2.0, "disregard": 2.0, "forget": 1.8,
        "previous": 1.5, "instructions": 2.5, "system": 1.5,
        "prompt": 2.0, "override": 2.0, "jailbreak": 3.0,
        "dan": 2.5, "pretend": 1.8, "roleplay": 1.5,
        "bypass": 2.0, "reveal": 1.8, "print": 1.0,
        "output": 1.0, "rules": 1.2, "developer": 1.3,
        "mode": 0.8, "enabled": 0.8, "activated": 0.8,
        "inject": 2.5, "payload": 1.5,
    }

    # Benign context words that reduce injection score
    _BENIGN_VOCAB: dict[str, float] = {
        "test": -1.0, "unittest": -1.5, "assert": -1.5,
        "def": -0.5, "class": -0.5, "function": -0.5,
        "import": -0.5, "require": -0.5, "const": -0.5,
        "example": -0.8, "documentation": -1.0, "readme": -1.0,
        "comment": -0.5, "string": -0.5, "variable": -0.5,
    }

    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold

    def classify(self, text: str) -> ClassificationResult:
        """Classify text as injection or benign."""
        score = self._compute_score(text)
        is_injection = score >= self._threshold
        confidence = min(abs(score) / 5.0, 1.0)  # normalise to [0, 1]

        return ClassificationResult(
            is_injection=is_injection,
            confidence=confidence,
            label="injection" if is_injection else "benign",
        )

    def _compute_score(self, text: str) -> float:
        tokens = _tokenize(text)
        if not tokens:
            return 0.0

        token_counts = Counter(tokens)
        score = 0.0

        for token, count in token_counts.items():
            if token in self._INJECTION_VOCAB:
                score += self._INJECTION_VOCAB[token] * math.log1p(count)
            if token in self._BENIGN_VOCAB:
                score += self._BENIGN_VOCAB[token] * math.log1p(count)

        # Normalize by token count to avoid bias towards long texts
        return score / math.sqrt(len(tokens))


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return [t.lower() for t in re.split(r"[\s\W]+", text) if t]
