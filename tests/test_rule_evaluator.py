"""
tests/test_rule_evaluator.py
Tests for rule evaluation, SIC overrides, and CMP logic.
Run with: pytest tests/test_rule_evaluator.py -v
"""
from __future__ import annotations

import sys
import os
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.signal_report import Rule, PeerContext
from engine.rule_evaluator import (
    apply_sic_override,
    build_namespace,
    evaluate_rule,
    evaluate_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(rule_id="INS-01", color="GREEN", condition="form4.open_market_buys_30d >= 2",
               category="insider", base_strength=90, rarity=100, sic_overrides=None):
    return Rule(
        id=rule_id,
        name="Test rule",
        category=category,
        color=color,
        base_strength=base_strength,
        rarity=rarity,
        condition=condition,
        description="Test",
        enabled=True,
        sic_overrides=sic_overrides or {},
        validity_period=30,
    )


def _minimal_namespace(form4_overrides=None, filing_overrides=None,
                        financials_overrides=None, peer_overrides=None,
                        price_overrides=None, macro_overrides=None) -> dict:
    """Build a minimal namespace with safe defaults, applying any overrides."""

    def _ns(**kwargs):
        obj = types.SimpleNamespace()
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    form4 = _ns(
        open_market_buys_30d=0,
        open_market_sells_30d=0,
        cluster_buy_30d=False,
        cluster_sell_14d=False,
        ceo_bought=False,
        cfo_bought=False,
        largest_buy_usd=0.0,
        pct_holdings_sold=0.0,
        days_since_last_buy=9999,
        near_52wk_low=False,
        sell_is_scheduled=False,
        days_since_earnings=9999,
    )
    filing = _ns(
        going_concern=False,
        auditor_changed=False,
        guidance_raised=False,
        guidance_lowered=False,
        ceo_departed=False,
        cfo_departed=False,
        material_contract=False,
        buyback_pct_float=0.0,
        equity_dilution_pct=0.0,
        new_13f_tier1=False,
        activist_13d=False,
        short_seller_report=False,
        rpo_yoy=0.0,
        crpo_yoy=0.0,
        shelf_registration=False,
        new_10b51_plan_type=None,
        tier1_avg_cost=0.0,
    )
    financials = _ns(
        revenue_growth=0.0,
        gross_margin=0.5,
        gross_margin_delta=0.0,
        operating_margin=0.15,
        net_margin=0.10,
        fcf_yield=0.03,
        debt_ebitda=1.0,
        cash_runway_months=24.0,
        eps_beat_streak=0,
        revenue_growth_streak=0,
        rev_growth_delta=0.0,
        pe_ratio=20.0,
        op_leverage=0.0,
        net_income_streak_neg=0,
    )
    peer = _ns(
        rev_growth_percentile=50.0,
        gross_margin_percentile=50.0,
        fcf_yield_percentile=50.0,
        debt_ebitda_percentile=50.0,
        pe_percentile=50.0,
        op_leverage_percentile=50.0,
        ev_ebitda_percentile=50.0,
        pb_percentile=50.0,
        p_ffo_percentile=50.0,
        sector_name="Software",
        fama_french_industry="Computer Software",
        sic=7372,
        peer_count=8,
        peer_tickers=[],
    )
    price = _ns(
        current=100.0,
        prev_close=99.0,
        change_1d=0.01,
        change_30d=0.05,
        change_90d=0.10,
        pct_from_52wk_low=0.20,
        pct_from_52wk_high=-0.10,
        pct_from_ath=-0.15,
        volume_ratio_30d=1.0,
        short_float=0.05,
        above_200d_ma=True,
        golden_cross=False,
        death_cross=False,
    )
    macro = _ns(
        spread_10y_2y=0.30,
        vix=18.0,
        cpi_surprise=0.0,
        dxy_change_30d=0.01,
        fed_rate=5.25,
        fed_cutting=False,
        fed_hiking=False,
        hy_spread_change_30d=0.0,
        ig_spread_change_30d=0.0,
    )

    ns = {
        "form4": form4,
        "filing": filing,
        "financials": financials,
        "peer": peer,
        "price": price,
        "macro": macro,
    }

    # Apply overrides
    for ns_name, overrides in [
        ("form4", form4_overrides),
        ("filing", filing_overrides),
        ("financials", financials_overrides),
        ("peer", peer_overrides),
        ("price", price_overrides),
        ("macro", macro_overrides),
    ]:
        if overrides:
            obj = ns[ns_name]
            for k, v in overrides.items():
                setattr(obj, k, v)

    return ns


# ---------------------------------------------------------------------------
# INS-01: Insider cluster buy
# ---------------------------------------------------------------------------

class TestINS01:

    def test_fires_when_two_buys(self):
        """INS-01 fires when open_market_buys_30d >= 2."""
        rule = _make_rule("INS-01", condition="form4.open_market_buys_30d >= 2")
        ns = _minimal_namespace(form4_overrides={"open_market_buys_30d": 3})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is not None
        assert result.rule.id == "INS-01"
        assert result.score > 0

    def test_does_not_fire_with_one_buy(self):
        """INS-01 does not fire with only 1 buy."""
        rule = _make_rule("INS-01", condition="form4.open_market_buys_30d >= 2")
        ns = _minimal_namespace(form4_overrides={"open_market_buys_30d": 1})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is None

    def test_does_not_fire_with_zero_buys(self):
        rule = _make_rule("INS-01", condition="form4.open_market_buys_30d >= 2")
        ns = _minimal_namespace()
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is None

    def test_disabled_rule_never_fires(self):
        rule = _make_rule("INS-01", condition="form4.open_market_buys_30d >= 2")
        rule = Rule(**{**rule.__dict__, "enabled": False})
        ns = _minimal_namespace(form4_overrides={"open_market_buys_30d": 5})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is None

    def test_signal_score_formula(self):
        """Score = base_strength * 0.6 + rarity * 0.4"""
        rule = _make_rule("INS-01", base_strength=90, rarity=100,
                          condition="form4.open_market_buys_30d >= 2")
        ns = _minimal_namespace(form4_overrides={"open_market_buys_30d": 2})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is not None
        assert result.score == pytest.approx(94.0)

    def test_rarity_label_rare(self):
        rule = _make_rule("INS-01", base_strength=90, rarity=100,
                          condition="form4.open_market_buys_30d >= 2")
        ns = _minimal_namespace(form4_overrides={"open_market_buys_30d": 2})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is not None
        assert result.rarity_label == "RARE"
        assert result.rarity_symbol == "◆"


# ---------------------------------------------------------------------------
# SIC Overrides
# ---------------------------------------------------------------------------

class TestSICOverrides:

    def test_fun06_skipped_for_utility_sic(self):
        """FUN-06 must be skipped for SIC 4900–4991 (utilities)."""
        rule = _make_rule(
            "FUN-06",
            color="RED",
            condition="peer.debt_ebitda_percentile < 25",
            sic_overrides={
                "6020-6099": "skip",
                "6500-6552": "skip",
                "4900-4991": "skip",
            }
        )
        ns = _minimal_namespace(peer_overrides={"debt_ebitda_percentile": 10})
        # Utility SIC — should be skipped
        result = evaluate_rule(rule, ns, sic=4911)
        assert result is None

    def test_fun06_fires_for_software_sic(self):
        """FUN-06 fires normally for software SIC."""
        rule = _make_rule(
            "FUN-06",
            color="RED",
            condition="peer.debt_ebitda_percentile < 25",
            sic_overrides={
                "6020-6099": "skip",
                "6500-6552": "skip",
                "4900-4991": "skip",
            }
        )
        ns = _minimal_namespace(peer_overrides={"debt_ebitda_percentile": 10})
        result = evaluate_rule(rule, ns, sic=7372)
        assert result is not None

    def test_sic_override_alternate_condition(self):
        """Alternate condition replaces default for matching SIC range."""
        rule = _make_rule(
            "FUN-07",
            color="RED",
            condition="financials.net_income_streak_neg >= 3",
            sic_overrides={
                "7372-7379": {"condition": "financials.net_income_streak_neg >= 6"},
            }
        )
        ns_3 = _minimal_namespace(financials_overrides={"net_income_streak_neg": 3})
        ns_6 = _minimal_namespace(financials_overrides={"net_income_streak_neg": 6})

        # SIC 7372: alternate condition requires >= 6, so 3 should NOT fire
        assert evaluate_rule(rule, ns_3, sic=7372) is None
        # SIC 7372 with 6 losses: should fire
        assert evaluate_rule(rule, ns_6, sic=7372) is not None
        # Non-matching SIC (biotech skip) — use default condition, 3 losses fires
        rule_biotech = _make_rule(
            "FUN-07",
            color="RED",
            condition="financials.net_income_streak_neg >= 3",
            sic_overrides={"2830-2836": "skip"},
        )
        assert evaluate_rule(rule_biotech, ns_3, sic=7372) is not None

    def test_exact_sic_override(self):
        """Single SIC code override (not a range) works."""
        rule = _make_rule(
            "FUN-11",
            color="GREEN",
            condition="peer.pe_percentile < 35",
            sic_overrides={"1311": {"condition": "peer.ev_ebitda_percentile < 35"}},
        )
        ns_ev = _minimal_namespace(peer_overrides={"ev_ebitda_percentile": 20, "pe_percentile": 60})
        # SIC 1311: uses ev_ebitda condition, ev=20 < 35 → fires
        assert evaluate_rule(rule, ns_ev, sic=1311) is not None
        # SIC 1311: pe=60 doesn't matter, ev_ebitda=20 fires it
        ns_pe = _minimal_namespace(peer_overrides={"pe_percentile": 20, "ev_ebitda_percentile": 60})
        # ev_ebitda=60 >= 35 → should NOT fire
        assert evaluate_rule(rule, ns_pe, sic=1311) is None


# ---------------------------------------------------------------------------
# CMP-01: Strong long setup
# ---------------------------------------------------------------------------

class TestCMP01:

    def _make_cmp_rule(self):
        return Rule(
            id="CMP-01",
            name="Strong long setup",
            category="composite",
            color="GREEN",
            base_strength=95,
            rarity=99,
            condition="fired('INS-01') and fired('PRC-01') and fired('FUN-01')",
            description="Test CMP",
            enabled=True,
            sic_overrides={},
            validity_period=30,
        )

    def _make_base_rules(self):
        return [
            _make_rule("INS-01", condition="form4.open_market_buys_30d >= 2"),
            _make_rule("PRC-01", color="GREEN",
                       condition="price.pct_from_ath < -0.30 and financials.revenue_growth > 0"),
            _make_rule("FUN-01", color="GREEN",
                       condition="financials.revenue_growth_streak >= 3 and financials.revenue_growth > 0.20"),
            self._make_cmp_rule(),
        ]

    def test_cmp01_fires_when_all_three_base_rules_fire(self):
        """CMP-01 fires when INS-01, PRC-01, and FUN-01 all fire."""
        ns = _minimal_namespace(
            form4_overrides={"open_market_buys_30d": 3},
            price_overrides={"pct_from_ath": -0.40},
            financials_overrides={
                "revenue_growth": 0.25,
                "revenue_growth_streak": 4,
            },
        )
        rules = self._make_base_rules()
        fired = evaluate_all(rules, ns, sic=7372)
        fired_ids = {fs.rule.id for fs in fired}
        assert "CMP-01" in fired_ids

    def test_cmp01_does_not_fire_when_one_base_rule_missing(self):
        """CMP-01 does not fire when FUN-01 is not met."""
        ns = _minimal_namespace(
            form4_overrides={"open_market_buys_30d": 3},
            price_overrides={"pct_from_ath": -0.40},
            financials_overrides={
                "revenue_growth": 0.05,   # below 20% threshold
                "revenue_growth_streak": 0,
            },
        )
        rules = self._make_base_rules()
        fired = evaluate_all(rules, ns, sic=7372)
        fired_ids = {fs.rule.id for fs in fired}
        assert "CMP-01" not in fired_ids

    def test_cmp04_fires_on_four_green_no_red(self):
        """CMP-04: 4+ GREEN signals with zero RED fires."""
        rules = [
            _make_rule("INS-01", color="GREEN", condition="form4.open_market_buys_30d >= 2"),
            _make_rule("INS-02", color="GREEN", condition="form4.largest_buy_usd >= 1000000"),
            _make_rule("INS-03", color="GREEN", condition="form4.ceo_bought or form4.cfo_bought"),
            _make_rule("FUN-01", color="GREEN",
                       condition="financials.revenue_growth_streak >= 3 and financials.revenue_growth > 0.20"),
            Rule(
                id="CMP-04",
                name="Clean bull setup",
                category="composite",
                color="GREEN",
                base_strength=88,
                rarity=97,
                condition="green_count >= 4 and red_count == 0",
                description="Test",
                enabled=True,
                sic_overrides={},
                validity_period=7,
            ),
        ]
        ns = _minimal_namespace(
            form4_overrides={
                "open_market_buys_30d": 3,
                "largest_buy_usd": 2_000_000,
                "ceo_bought": True,
            },
            financials_overrides={
                "revenue_growth": 0.30,
                "revenue_growth_streak": 4,
            },
        )
        fired = evaluate_all(rules, ns, sic=7372)
        fired_ids = {fs.rule.id for fs in fired}
        assert "CMP-04" in fired_ids

    def test_evaluate_all_two_pass_order(self):
        """CMP rules never appear before base rules in evaluate_all."""
        ns = _minimal_namespace(
            form4_overrides={"open_market_buys_30d": 3},
            price_overrides={"pct_from_ath": -0.40},
            financials_overrides={"revenue_growth": 0.25, "revenue_growth_streak": 4},
        )
        rules = self._make_base_rules()
        fired = evaluate_all(rules, ns, sic=7372)
        # CMP-01 must appear after base rules
        ids_in_order = [fs.rule.id for fs in fired]
        if "CMP-01" in ids_in_order:
            cmp_idx = ids_in_order.index("CMP-01")
            base_ids = {"INS-01", "PRC-01", "FUN-01"}
            for base_id in base_ids:
                if base_id in ids_in_order:
                    assert ids_in_order.index(base_id) < cmp_idx


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestEvalResilience:

    def test_bad_condition_returns_none(self):
        """A rule with a broken condition returns None (never raises)."""
        rule = _make_rule("TST-01", condition="this is not valid python !!!")
        ns = _minimal_namespace()
        result = evaluate_rule(rule, ns, sic=0)
        assert result is None

    def test_missing_namespace_variable_returns_none(self):
        """A rule referencing a non-existent variable returns None."""
        rule = _make_rule("TST-02", condition="form4.nonexistent_field > 0")
        ns = _minimal_namespace()
        result = evaluate_rule(rule, ns, sic=0)
        assert result is None

    def test_evaluate_all_returns_list(self):
        """evaluate_all always returns a list."""
        result = evaluate_all([], _minimal_namespace(), sic=0)
        assert isinstance(result, list)
