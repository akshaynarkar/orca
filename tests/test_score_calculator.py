"""
tests/test_score_calculator.py
Tests for signal score, ORCA score, confidence, and rarity classification.
Run with: pytest tests/test_score_calculator.py -v
"""
from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.signal_report import FiredSignal, Rule
from engine.score_calculator import (
    classify_rarity,
    compute_confidence,
    compute_orca_score,
    compute_signal_score,
    get_orca_label,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(color="GREEN", category="insider", is_composite=False):
    return Rule(
        id="TST-01",
        name="Test",
        category="composite" if is_composite else category,
        color=color,
        base_strength=80,
        rarity=80,
        condition="True",
        description="Test rule",
        validity_period=30,
    )


def _make_signal(color="GREEN", score=80.0, is_composite=False):
    rule = _make_rule(color=color, is_composite=is_composite)
    return FiredSignal(rule=rule, score=score, rarity_label="UNCOMMON", rarity_symbol="◈")


# ---------------------------------------------------------------------------
# Signal Score
# ---------------------------------------------------------------------------

class TestSignalScore:

    def test_formula(self):
        """Score = base_strength * 0.6 + rarity * 0.4"""
        assert compute_signal_score(90, 100) == pytest.approx(94.0)
        assert compute_signal_score(85, 95)  == pytest.approx(89.0)
        assert compute_signal_score(80, 80)  == pytest.approx(80.0)
        assert compute_signal_score(70, 65)  == pytest.approx(68.0)

    def test_zero_values(self):
        assert compute_signal_score(0, 0) == pytest.approx(0.0)

    def test_max_values(self):
        assert compute_signal_score(100, 100) == pytest.approx(100.0)

    def test_returns_float(self):
        result = compute_signal_score(75, 70)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Rarity
# ---------------------------------------------------------------------------

class TestRarity:

    def test_rare(self):
        label, sym = classify_rarity(100)
        assert label == "RARE"
        assert sym == "◆"

    def test_rare_at_threshold(self):
        label, sym = classify_rarity(90)
        assert label == "RARE"

    def test_uncommon(self):
        label, sym = classify_rarity(75)
        assert label == "UNCOMMON"
        assert sym == "◈"

    def test_uncommon_at_threshold(self):
        label, sym = classify_rarity(60)
        assert label == "UNCOMMON"

    def test_occasional(self):
        label, sym = classify_rarity(50)
        assert label == "OCCASIONAL"
        assert sym == "○"

    def test_occasional_at_threshold(self):
        label, sym = classify_rarity(35)
        assert label == "OCCASIONAL"

    def test_common(self):
        label, sym = classify_rarity(25)
        assert label == "COMMON"
        assert sym == "·"

    def test_common_zero(self):
        label, sym = classify_rarity(0)
        assert label == "COMMON"


# ---------------------------------------------------------------------------
# ORCA Score
# ---------------------------------------------------------------------------

class TestOrcaScore:

    def test_baseline_no_signals(self):
        """No signals → baseline of 50."""
        assert compute_orca_score([]) == 50

    def test_single_green(self):
        """One GREEN signal: 50 + 12 = 62."""
        signals = [_make_signal("GREEN")]
        assert compute_orca_score(signals) == 62

    def test_single_red(self):
        """One RED signal: 50 - 18 = 32."""
        signals = [_make_signal("RED")]
        assert compute_orca_score(signals) == 32

    def test_single_amber(self):
        """One AMBER signal: 50 - 5 = 45."""
        signals = [_make_signal("AMBER")]
        assert compute_orca_score(signals) == 45

    def test_blue_no_change(self):
        """BLUE signals have zero weight."""
        signals = [_make_signal("BLUE")]
        assert compute_orca_score(signals) == 50

    def test_purple(self):
        """PURPLE: 50 + 6 = 56."""
        signals = [_make_signal("PURPLE")]
        assert compute_orca_score(signals) == 56

    def test_composite_green_2x(self):
        """Composite GREEN: 50 + 12*2 = 74."""
        signals = [_make_signal("GREEN", is_composite=True)]
        assert compute_orca_score(signals) == 74

    def test_composite_red_2x(self):
        """Composite RED: 50 - 18*2 = 14."""
        signals = [_make_signal("RED", is_composite=True)]
        assert compute_orca_score(signals) == 14

    def test_clamp_upper(self):
        """Score cannot exceed 100."""
        signals = [_make_signal("GREEN")] * 10
        result = compute_orca_score(signals)
        assert result == 100

    def test_clamp_lower(self):
        """Score cannot go below 0."""
        signals = [_make_signal("RED")] * 10
        result = compute_orca_score(signals)
        assert result == 0

    def test_mixed_signals(self):
        """3 GREEN + 1 RED: 50 + 36 - 18 = 68."""
        signals = [
            _make_signal("GREEN"),
            _make_signal("GREEN"),
            _make_signal("GREEN"),
            _make_signal("RED"),
        ]
        assert compute_orca_score(signals) == 68

    def test_score_is_int(self):
        assert isinstance(compute_orca_score([_make_signal("GREEN")]), int)


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

class TestConfidence:

    def test_no_signals_returns_zero(self):
        assert compute_confidence([]) == 0.0

    def test_single_signal(self):
        signals = [_make_signal(score=80.0)]
        assert compute_confidence(signals) == pytest.approx(80.0)

    def test_average_of_multiple(self):
        signals = [
            _make_signal(score=90.0),
            _make_signal(score=70.0),
        ]
        assert compute_confidence(signals) == pytest.approx(80.0)

    def test_returns_float(self):
        signals = [_make_signal(score=75.0)]
        result = compute_confidence(signals)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# ORCA Label
# ---------------------------------------------------------------------------

class TestOrcaLabel:

    def test_bullish(self):
        assert get_orca_label(66) == "BULLISH"
        assert get_orca_label(100) == "BULLISH"

    def test_neutral(self):
        assert get_orca_label(65) == "NEUTRAL"
        assert get_orca_label(35) == "NEUTRAL"
        assert get_orca_label(50) == "NEUTRAL"

    def test_bearish(self):
        assert get_orca_label(34) == "BEARISH"
        assert get_orca_label(0) == "BEARISH"
