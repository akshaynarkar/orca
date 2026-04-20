"""
engine/score_calculator.py
Signal score, ORCA score, confidence, and rarity classification.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.signal_report import FiredSignal

logger = logging.getLogger("orca")

# ORCA score weights per color
_COLOR_WEIGHT: dict[str, int] = {
    "GREEN":  12,
    "RED":   -18,
    "AMBER":  -5,
    "BLUE":    0,
    "PURPLE":  6,
}

_RARITY_THRESHOLDS: list[tuple[int, str, str]] = [
    (90, "RARE",       "◆"),
    (60, "UNCOMMON",   "◈"),
    (35, "OCCASIONAL", "○"),
    (0,  "COMMON",     "·"),
]


# ---------------------------------------------------------------------------
# Signal Score
# ---------------------------------------------------------------------------

def compute_signal_score(base_strength: int, rarity: int) -> float:
    """Signal Score = (base_strength × 0.6) + (rarity × 0.4)"""
    return round((base_strength * 0.6) + (rarity * 0.4), 1)


# ---------------------------------------------------------------------------
# Rarity
# ---------------------------------------------------------------------------

def classify_rarity(rarity_score: int) -> tuple[str, str]:
    """
    Returns (label, symbol) for a given rarity score.
    E.g. classify_rarity(100) -> ("RARE", "◆")
    """
    for threshold, label, symbol in _RARITY_THRESHOLDS:
        if rarity_score >= threshold:
            return label, symbol
    return "COMMON", "·"


# ---------------------------------------------------------------------------
# ORCA Score
# ---------------------------------------------------------------------------

def compute_orca_score(fired_signals: list[FiredSignal]) -> int:
    """
    Compute composite ORCA Score (0–100) from all fired signals.
    Baseline: 50
    GREEN: +12, RED: -18, AMBER: -5, BLUE: 0, PURPLE: +6
    CMP (composite) rules: ×2 multiplier
    Clamped 0–100.
    """
    score = 50

    for fs in fired_signals:
        weight = _COLOR_WEIGHT.get(fs.rule.color, 0)
        if fs.rule.is_composite:
            weight *= 2
        score += weight

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def compute_confidence(fired_signals: list[FiredSignal]) -> float:
    """
    Weighted average signal score of all fired rules.
    Returns 0.0 if no signals fired.
    """
    if not fired_signals:
        return 0.0
    total = sum(fs.score for fs in fired_signals)
    return round(total / len(fired_signals), 1)


# ---------------------------------------------------------------------------
# ORCA Label
# ---------------------------------------------------------------------------

def get_orca_label(score: int) -> str:
    """Returns BULLISH / NEUTRAL / BEARISH based on ORCA score."""
    if score > 65:
        return "BULLISH"
    if score < 35:
        return "BEARISH"
    return "NEUTRAL"
