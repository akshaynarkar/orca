"""
tests/test_peer_engine.py
Tests for peer percentile computation on mock data.
Run with: pytest tests/test_peer_engine.py -v
"""
from __future__ import annotations

import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.peer_engine import compute_peer_percentiles, get_peer_context
from engine.sic_classifier import get_fama_french_industry, sic_in_range


# ---------------------------------------------------------------------------
# Mock peer set (10 companies)
# ---------------------------------------------------------------------------

def _mock_peer_rows():
    """10 mock peer rows with varied metrics."""
    return [
        {"ticker": "A", "mktcap": 100e9, "rev_growth": 0.30, "gross_margin": 0.75, "fcf_yield": 0.04, "debt_ebitda": 0.5, "pe": 25, "op_leverage": 5.0, "ev_ebitda": 20, "pb": 8.0, "p_ffo": 0.0},
        {"ticker": "B", "mktcap":  90e9, "rev_growth": 0.25, "gross_margin": 0.70, "fcf_yield": 0.035,"debt_ebitda": 0.8, "pe": 28, "op_leverage": 4.0, "ev_ebitda": 22, "pb": 7.0, "p_ffo": 0.0},
        {"ticker": "C", "mktcap":  80e9, "rev_growth": 0.20, "gross_margin": 0.65, "fcf_yield": 0.03, "debt_ebitda": 1.0, "pe": 30, "op_leverage": 3.0, "ev_ebitda": 24, "pb": 6.0, "p_ffo": 0.0},
        {"ticker": "D", "mktcap":  70e9, "rev_growth": 0.15, "gross_margin": 0.60, "fcf_yield": 0.025,"debt_ebitda": 1.5, "pe": 22, "op_leverage": 2.5, "ev_ebitda": 18, "pb": 5.0, "p_ffo": 0.0},
        {"ticker": "E", "mktcap":  60e9, "rev_growth": 0.10, "gross_margin": 0.55, "fcf_yield": 0.02, "debt_ebitda": 2.0, "pe": 20, "op_leverage": 2.0, "ev_ebitda": 16, "pb": 4.5, "p_ffo": 0.0},
        {"ticker": "F", "mktcap":  50e9, "rev_growth": 0.05, "gross_margin": 0.50, "fcf_yield": 0.015,"debt_ebitda": 2.5, "pe": 18, "op_leverage": 1.5, "ev_ebitda": 14, "pb": 4.0, "p_ffo": 0.0},
        {"ticker": "G", "mktcap":  40e9, "rev_growth": 0.02, "gross_margin": 0.45, "fcf_yield": 0.01, "debt_ebitda": 3.0, "pe": 15, "op_leverage": 1.0, "ev_ebitda": 12, "pb": 3.0, "p_ffo": 0.0},
        {"ticker": "H", "mktcap":  30e9, "rev_growth": 0.00, "gross_margin": 0.40, "fcf_yield": 0.005,"debt_ebitda": 3.5, "pe": 12, "op_leverage": 0.5, "ev_ebitda": 10, "pb": 2.5, "p_ffo": 0.0},
        {"ticker": "I", "mktcap":  20e9, "rev_growth":-0.05, "gross_margin": 0.35, "fcf_yield": 0.0,  "debt_ebitda": 4.0, "pe": 10, "op_leverage": 0.0, "ev_ebitda":  8, "pb": 2.0, "p_ffo": 0.0},
        {"ticker": "J", "mktcap":  10e9, "rev_growth":-0.10, "gross_margin": 0.30, "fcf_yield":-0.01, "debt_ebitda": 5.0, "pe":  8, "op_leverage":-1.0, "ev_ebitda":  6, "pb": 1.5, "p_ffo": 0.0},
    ]


# ---------------------------------------------------------------------------
# Percentile computation
# ---------------------------------------------------------------------------

class TestComputePeerPercentiles:

    def test_top_performer_near_100(self):
        """Subject with best metrics across all peers → high percentiles."""
        subject = {
            "rev_growth": 0.35,   # above all 10 peers
            "gross_margin": 0.80,
            "fcf_yield": 0.05,
            "debt_ebitda": 0.3,   # lower is better
            "pe": 35,
            "op_leverage": 6.0,
            "ev_ebitda": 25,
            "pb": 9.0,
            "p_ffo": 0.0,
        }
        peers = _mock_peer_rows()
        result = compute_peer_percentiles(subject, peers)

        assert result["rev_growth_percentile"] == pytest.approx(100.0)
        assert result["gross_margin_percentile"] == pytest.approx(100.0)
        assert result["fcf_yield_percentile"] == pytest.approx(100.0)
        # debt_ebitda: lower is better, 0.3 < all peers → 100th percentile
        assert result["debt_ebitda_percentile"] == pytest.approx(100.0)

    def test_bottom_performer_near_zero(self):
        """Subject with worst metrics → low percentiles."""
        subject = {
            "rev_growth": -0.20,
            "gross_margin": 0.20,
            "fcf_yield": -0.05,
            "debt_ebitda": 6.0,   # higher than all peers → worst
            "pe": 5,
            "op_leverage": -2.0,
            "ev_ebitda": 4,
            "pb": 1.0,
            "p_ffo": 0.0,
        }
        peers = _mock_peer_rows()
        result = compute_peer_percentiles(subject, peers)

        assert result["rev_growth_percentile"] == pytest.approx(0.0)
        assert result["gross_margin_percentile"] == pytest.approx(0.0)
        # debt_ebitda: 6.0 is worse than all peers (higher) → 0th percentile
        assert result["debt_ebitda_percentile"] == pytest.approx(0.0)

    def test_median_performer_near_50(self):
        """Subject at the median of the peer set → ~50th percentile."""
        # Median of 10 peers for rev_growth is between F (0.05) and E (0.10)
        subject = {
            "rev_growth": 0.075,
            "gross_margin": 0.525,
            "fcf_yield": 0.0125,
            "debt_ebitda": 2.25,
            "pe": 19,
            "op_leverage": 1.75,
            "ev_ebitda": 15,
            "pb": 4.25,
            "p_ffo": 0.0,
        }
        peers = _mock_peer_rows()
        result = compute_peer_percentiles(subject, peers)

        # Should be roughly in the 40–60 range
        assert 30.0 <= result["rev_growth_percentile"] <= 70.0
        assert 30.0 <= result["gross_margin_percentile"] <= 70.0

    def test_returns_all_expected_keys(self):
        """All 9 percentile keys present in result."""
        subject = {"rev_growth": 0.10, "gross_margin": 0.50, "fcf_yield": 0.02,
                   "debt_ebitda": 2.0, "pe": 20, "op_leverage": 2.0,
                   "ev_ebitda": 15, "pb": 4.0, "p_ffo": 0.0}
        result = compute_peer_percentiles(subject, _mock_peer_rows())
        expected_keys = {
            "rev_growth_percentile", "gross_margin_percentile", "fcf_yield_percentile",
            "debt_ebitda_percentile", "pe_percentile", "op_leverage_percentile",
            "ev_ebitda_percentile", "pb_percentile", "p_ffo_percentile",
        }
        assert expected_keys.issubset(result.keys())

    def test_empty_peers_returns_50(self):
        """No peers → all percentiles default to 50."""
        subject = {"rev_growth": 0.20, "gross_margin": 0.60}
        result = compute_peer_percentiles(subject, [])
        for key in result:
            assert result[key] == pytest.approx(50.0)

    def test_percentile_range_0_to_100(self):
        """All percentile values are within 0–100."""
        subject = {"rev_growth": 0.12, "gross_margin": 0.55, "fcf_yield": 0.02,
                   "debt_ebitda": 1.8, "pe": 21, "op_leverage": 2.2,
                   "ev_ebitda": 17, "pb": 4.2, "p_ffo": 0.0}
        result = compute_peer_percentiles(subject, _mock_peer_rows())
        for key, val in result.items():
            assert 0.0 <= val <= 100.0, f"{key} = {val} out of range"

    def test_debt_ebitda_lower_is_better(self):
        """debt_ebitda percentile: lower debt → higher percentile rank."""
        peers = _mock_peer_rows()
        low_debt  = {"debt_ebitda": 0.1, "rev_growth": 0, "gross_margin": 0,
                     "fcf_yield": 0, "pe": 0, "op_leverage": 0, "ev_ebitda": 0, "pb": 0, "p_ffo": 0}
        high_debt = {"debt_ebitda": 9.0, "rev_growth": 0, "gross_margin": 0,
                     "fcf_yield": 0, "pe": 0, "op_leverage": 0, "ev_ebitda": 0, "pb": 0, "p_ffo": 0}

        low_result  = compute_peer_percentiles(low_debt, peers)
        high_result = compute_peer_percentiles(high_debt, peers)

        assert low_result["debt_ebitda_percentile"] > high_result["debt_ebitda_percentile"]


# ---------------------------------------------------------------------------
# SIC Classifier
# ---------------------------------------------------------------------------

class TestSICClassifier:

    def test_sic_in_range_basic(self):
        assert sic_in_range(4911, "4900-4991") is True
        assert sic_in_range(4899, "4900-4991") is False
        assert sic_in_range(4992, "4900-4991") is False

    def test_sic_in_range_exact(self):
        assert sic_in_range(1311, "1311") is True
        assert sic_in_range(1312, "1311") is False

    def test_sic_in_range_bad_input(self):
        assert sic_in_range(7372, "not-a-range") is False

    def test_fama_french_software(self):
        assert get_fama_french_industry(7372) == "Computer Software"

    def test_fama_french_pharma(self):
        assert get_fama_french_industry(2836) == "Pharmaceutical Products"

    def test_fama_french_utilities(self):
        assert get_fama_french_industry(4911) == "Utilities"

    def test_fama_french_banking(self):
        assert get_fama_french_industry(6022) == "Banking"

    def test_fama_french_unknown(self):
        assert get_fama_french_industry(9999) == "Public Administration"


# ---------------------------------------------------------------------------
# get_peer_context — graceful failure
# ---------------------------------------------------------------------------

class TestGetPeerContextFallback:

    def test_returns_peer_context_on_edgar_failure(self):
        """get_peer_context returns a PeerContext with 50-defaults when EDGAR fails."""
        with patch("engine.peer_engine._load_cache", return_value=None), \
             patch("engine.peer_engine.get_peers", return_value=[]):
            ctx = get_peer_context("MSFT", sic=7372, subject_metrics={})

        assert ctx is not None
        assert ctx.ticker == "MSFT"
        assert ctx.sic == 7372
        assert ctx.peer_count == 0
        for key, val in ctx.percentiles.items():
            assert val == pytest.approx(50.0), f"{key} should default to 50"

    def test_peer_context_uses_cache(self):
        """get_peer_context uses Parquet cache when available."""
        mock_df = pd.DataFrame(_mock_peer_rows())

        subject_metrics = {
            "rev_growth": 0.20, "gross_margin": 0.65, "fcf_yield": 0.03,
            "debt_ebitda": 1.0, "pe": 30, "op_leverage": 3.0,
            "ev_ebitda": 24, "pb": 6.0, "p_ffo": 0.0,
        }

        with patch("engine.peer_engine._load_cache", return_value=mock_df):
            ctx = get_peer_context("C", sic=7372, subject_metrics=subject_metrics)

        assert ctx is not None
        assert ctx.peer_count > 0
        # Percentiles should be computed (not all 50)
        assert isinstance(ctx.percentiles, dict)
        assert len(ctx.percentiles) > 0
