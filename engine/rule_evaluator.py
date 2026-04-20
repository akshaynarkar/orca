"""
engine/rule_evaluator.py
Namespace assembly, safe asteval evaluation, SIC override logic, CMP resolution.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from engine.signal_report import FiredSignal, PeerContext, Rule
from engine.score_calculator import classify_rarity, compute_signal_score
from engine.sic_classifier import sic_in_range

logger = logging.getLogger("orca")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return False


# ---------------------------------------------------------------------------
# Namespace assembly
# ---------------------------------------------------------------------------

def _build_form4_ns(form4_rows: list[dict], price_info: dict) -> dict:
    """
    Derive all form4.* namespace variables from the raw Form 4 transaction list.
    """
    now = datetime.now()
    cutoff_30 = now - timedelta(days=30)
    cutoff_14 = now - timedelta(days=14)

    buys_30: list[dict] = []
    sells_14: list[dict] = []
    all_buys: list[dict] = []

    for row in form4_rows:
        kind = str(row.get("kind", "")).upper()
        date_str = str(row.get("date", ""))
        try:
            txn_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            continue

        if kind == "BUY":
            all_buys.append(row)
            if txn_date >= cutoff_30:
                buys_30.append(row)
        elif kind == "SELL":
            if txn_date >= cutoff_14:
                sells_14.append(row)

    # CEO / CFO detection
    ceo_titles = {"ceo", "chief executive", "president and ceo"}
    cfo_titles = {"cfo", "chief financial", "principal financial"}

    ceo_bought = False
    cfo_bought = False
    for row in buys_30:
        role = str(row.get("role", "")).lower()
        if any(t in role for t in ceo_titles):
            ceo_bought = True
        if any(t in role for t in cfo_titles):
            cfo_bought = True

    # Largest single buy
    largest_buy_usd = max(
        (_safe_float(r.get("shares")) * _safe_float(r.get("price")) for r in buys_30),
        default=0.0,
    )

    # Pct holdings sold (largest single sell / owned_after + shares)
    pct_holdings_sold = 0.0
    for row in sells_14:
        shares = _safe_float(row.get("shares"))
        owned_after = _safe_float(row.get("owned_after"))
        total_before = shares + owned_after
        if total_before > 0:
            pct = shares / total_before
            pct_holdings_sold = max(pct_holdings_sold, pct)

    # Days since last buy
    days_since_last_buy = 9999
    if all_buys:
        try:
            last_buy = max(
                datetime.strptime(r["date"][:10], "%Y-%m-%d") for r in all_buys
            )
            days_since_last_buy = (now - last_buy).days
        except Exception:
            pass

    # Near 52wk low: price within 10% of 52wk low
    price_current = _safe_float(price_info.get("price"))
    low_52 = _safe_float(price_info.get("52wk_low"))
    near_52wk_low = (
        price_current > 0
        and low_52 > 0
        and price_current <= low_52 * 1.10
    )

    # Cluster sell: 3+ distinct insiders selling in 14d
    sell_insiders = set(str(r.get("insider", "")) for r in sells_14 if r.get("insider"))
    cluster_sell_14d = len(sell_insiders) >= 3

    # sell_is_scheduled: placeholder — Phase 2 fetcher doesn't expose 10b5-1 flag yet.
    # Defaults False (conservative: don't suppress signals we can't confirm are scheduled).
    sell_is_scheduled = False

    # days_since_earnings: fetch from yfinance calendar
    days_since_earnings = 9999
    try:
        import yfinance as yf
        cal = yf.Ticker(price_info.get("_ticker", "")).calendar
        if cal is not None:
            earnings_col = None
            for col in ("Earnings Date", "Earnings Dates"):
                if col in cal.columns:
                    earnings_col = col
                    break
            if earnings_col:
                dates = cal[earnings_col].dropna()
                past = [d for d in dates if pd.Timestamp(d) <= pd.Timestamp(now)]
                if past:
                    last_earnings = max(past)
                    days_since_earnings = (now.date() - pd.Timestamp(last_earnings).date()).days
    except Exception:
        pass

    return {
        "open_market_buys_30d":  len(buys_30),
        "open_market_sells_30d": len(sells_14),  # 14d window for sells
        "cluster_buy_30d":       len(set(str(r.get("insider","")) for r in buys_30 if r.get("insider"))) >= 2,
        "cluster_sell_14d":      cluster_sell_14d,
        "ceo_bought":            ceo_bought,
        "cfo_bought":            cfo_bought,
        "largest_buy_usd":       largest_buy_usd,
        "pct_holdings_sold":     round(pct_holdings_sold, 4),
        "days_since_last_buy":   days_since_last_buy,
        "near_52wk_low":         near_52wk_low,
        "sell_is_scheduled":     sell_is_scheduled,
        "days_since_earnings":   days_since_earnings,
    }


def _build_filing_ns(eightk_rows: list[dict]) -> dict:
    """
    Derive all filing.* namespace variables from the 8-K row list.
    New fields (crpo_yoy, shelf_registration, etc.) default to safe values
    until fetcher support is added in Phase 2 follow-up.
    """
    going_concern     = False
    auditor_changed   = False
    guidance_raised   = False
    guidance_lowered  = False
    ceo_departed      = False
    cfo_departed      = False
    material_contract = False

    for row in eightk_rows:
        if row.get("has_going_concern"):
            going_concern = True
        if row.get("has_auditor_changed"):
            auditor_changed = True
        if row.get("has_guidance_raised"):
            guidance_raised = True
        if row.get("has_guidance_lowered"):
            guidance_lowered = True
        if row.get("has_ceo_departure"):
            ceo_departed = True
        if row.get("has_cfo_departure"):
            cfo_departed = True
        if row.get("has_material_contract"):
            material_contract = True

    return {
        "going_concern":          going_concern,
        "auditor_changed":        auditor_changed,
        "guidance_raised":        guidance_raised,
        "guidance_lowered":       guidance_lowered,
        "ceo_departed":           ceo_departed,
        "cfo_departed":           cfo_departed,
        "material_contract":      material_contract,
        # Fields not yet populated by fetcher — safe defaults
        "buyback_pct_float":      0.0,
        "equity_dilution_pct":    0.0,
        "new_13f_tier1":          False,
        "activist_13d":           False,
        "short_seller_report":    False,
        "rpo_yoy":                0.0,
        "crpo_yoy":               0.0,   # new: current RPO YoY — Phase 2 follow-up
        "shelf_registration":     False,  # new: S-3 filing — Phase 2 follow-up
        "new_10b51_plan_type":    None,   # new: "PURCHASE" | "SALE" | None
        "tier1_avg_cost":         0.0,    # new: estimated Tier-1 cost basis
    }


def _build_financials_ns(financials: dict, price_info: dict) -> dict:
    """
    Derive all financials.* namespace variables from yfinance DataFrames.
    Returns safe zero-defaults on any missing data.
    """
    import pandas as pd

    def _get_row(df, *names) -> float:
        if df is None or (hasattr(df, "empty") and df.empty):
            return 0.0
        for n in names:
            if n in df.index:
                row = df.loc[n]
                vals = row.dropna() if hasattr(row, "dropna") else row
                if hasattr(vals, "iloc") and len(vals) > 0:
                    return _safe_float(vals.iloc[0])
                return _safe_float(row)
        return 0.0

    ai  = financials.get("annual_income")
    ab  = financials.get("annual_balance")
    ac  = financials.get("annual_cashflow")
    qi  = financials.get("quarterly_income")
    qb  = financials.get("quarterly_balance")
    qc  = financials.get("quarterly_cashflow")

    # --- Revenue growth ---
    rev_current  = _get_row(ai, "Total Revenue")
    rev_prev     = 0.0
    rev_growth   = 0.0
    if ai is not None and not ai.empty and len(ai.columns) >= 2:
        rev_prev = _safe_float(ai.loc["Total Revenue"].iloc[1]) if "Total Revenue" in ai.index else 0.0
    if rev_prev > 0:
        rev_growth = (rev_current - rev_prev) / rev_prev

    # --- Gross margin ---
    gross_profit   = _get_row(ai, "Gross Profit")
    gross_margin   = (gross_profit / rev_current) if rev_current > 0 else 0.0

    gross_profit_prev = 0.0
    rev_prev_gm = rev_prev
    if ai is not None and not ai.empty and len(ai.columns) >= 2:
        gross_profit_prev = _safe_float(ai.loc["Gross Profit"].iloc[1]) if "Gross Profit" in ai.index else 0.0
    gross_margin_prev = (gross_profit_prev / rev_prev_gm) if rev_prev_gm > 0 else 0.0
    gross_margin_delta = gross_margin - gross_margin_prev

    # --- Operating margin ---
    op_income = _get_row(ai, "Operating Income")
    operating_margin = (op_income / rev_current) if rev_current > 0 else 0.0

    # --- Net margin ---
    net_income = _get_row(ai, "Net Income")
    net_margin = (net_income / rev_current) if rev_current > 0 else 0.0

    # --- FCF yield ---
    operating_cf = _get_row(ac, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex        = abs(_get_row(ac, "Capital Expenditure", "Capital Expenditures"))
    fcf          = operating_cf - capex
    mktcap       = _safe_float(price_info.get("mktcap"))
    fcf_yield    = (fcf / mktcap) if mktcap > 0 else 0.0

    # --- Debt / EBITDA ---
    total_debt = _get_row(ab, "Total Debt", "Long Term Debt")
    da         = _get_row(ac, "Depreciation And Amortization", "Depreciation")
    ebitda     = op_income + da
    debt_ebitda = (total_debt / ebitda) if ebitda > 0 else 0.0

    # --- Cash runway ---
    cash  = _get_row(ab, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    burn  = abs(net_income) if net_income < 0 else 0.0
    cash_runway_months = (cash / (burn / 12)) if burn > 0 else 999.0
    cash_runway_months = min(cash_runway_months, 999.0)

    # --- Quarterly streaks ---
    eps_beat_streak          = 0
    revenue_growth_streak    = 0
    net_income_streak_neg    = 0
    rev_growth_delta         = 0.0

    if qi is not None and not qi.empty:
        q_rev_cols = qi.columns[:8] if len(qi.columns) >= 8 else qi.columns
        q_revs = []
        if "Total Revenue" in qi.index:
            q_revs = [_safe_float(qi.loc["Total Revenue", c]) for c in q_rev_cols]

        q_net = []
        if "Net Income" in qi.index:
            q_net = [_safe_float(qi.loc["Net Income", c]) for c in q_rev_cols]

        # Revenue growth streak: consecutive qtrs with >20% YoY growth
        if len(q_revs) >= 5:
            for i in range(min(4, len(q_revs) - 4)):
                if q_revs[i + 4] > 0:
                    g = (q_revs[i] - q_revs[i + 4]) / q_revs[i + 4]
                    if g > 0.20:
                        revenue_growth_streak += 1
                    else:
                        break

            # rev_growth_delta: most recent qtr growth vs prior qtr growth
            if len(q_revs) >= 6 and q_revs[4] > 0 and q_revs[5] > 0:
                g_latest = (q_revs[0] - q_revs[4]) / q_revs[4]
                g_prior  = (q_revs[1] - q_revs[5]) / q_revs[5]
                rev_growth_delta = g_latest - g_prior

        # Net income streak negative
        for val in q_net[:4]:
            if val < 0:
                net_income_streak_neg += 1
            else:
                break

    # --- Operating leverage ---
    # pp improvement in operating margin (simple proxy)
    op_income_prev = 0.0
    if ai is not None and not ai.empty and len(ai.columns) >= 2:
        op_income_prev = _safe_float(ai.loc["Operating Income"].iloc[1]) if "Operating Income" in ai.index else 0.0
    op_margin_prev = (op_income_prev / rev_prev) if rev_prev > 0 else 0.0
    op_leverage    = (operating_margin - op_margin_prev) * 100  # pp

    # --- P/E, EPS beat streak ---
    pe_ratio = _safe_float(price_info.get("pe_ratio"))
    eps_beat_streak = 0  # requires consensus data — stub 0 for v1.0

    return {
        "revenue_growth":        round(rev_growth, 4),
        "gross_margin":          round(gross_margin, 4),
        "gross_margin_delta":    round(gross_margin_delta, 4),
        "operating_margin":      round(operating_margin, 4),
        "net_margin":            round(net_margin, 4),
        "fcf_yield":             round(fcf_yield, 4),
        "debt_ebitda":           round(debt_ebitda, 4),
        "cash_runway_months":    round(cash_runway_months, 1),
        "eps_beat_streak":       eps_beat_streak,
        "revenue_growth_streak": revenue_growth_streak,
        "rev_growth_delta":      round(rev_growth_delta, 4),
        "pe_ratio":              round(pe_ratio, 2),
        "op_leverage":           round(op_leverage, 2),
        "net_income_streak_neg": net_income_streak_neg,
    }


def _build_peer_ns(peer_context: PeerContext | None) -> dict:
    """Map PeerContext into peer.* namespace dict."""
    defaults = {
        "rev_growth_percentile":   50.0,
        "gross_margin_percentile": 50.0,
        "fcf_yield_percentile":    50.0,
        "debt_ebitda_percentile":  50.0,
        "pe_percentile":           50.0,
        "op_leverage_percentile":  50.0,
        "ev_ebitda_percentile":    50.0,
        "pb_percentile":           50.0,
        "p_ffo_percentile":        50.0,
        "sector_name":             "",
        "fama_french_industry":    "",
        "sic":                     0,
        "peer_count":              0,
        "peer_tickers":            [],
    }
    if peer_context is None:
        return defaults

    result = dict(defaults)
    result.update({
        "sector_name":          peer_context.sector_name,
        "fama_french_industry": peer_context.fama_french_industry,
        "sic":                  peer_context.sic,
        "peer_count":           peer_context.peer_count,
        "peer_tickers":         peer_context.peer_tickers,
    })
    for k, v in peer_context.percentiles.items():
        result[k] = v
    return result


def _build_price_ns(price_info: dict, technicals: dict, volume_ratio: float, ohlcv) -> dict:
    """Assemble price.* namespace from fetcher outputs."""
    import pandas as pd

    current   = _safe_float(price_info.get("price"))
    prev      = _safe_float(price_info.get("prev_close"))
    high_52   = _safe_float(price_info.get("52wk_high"))
    low_52    = _safe_float(price_info.get("52wk_low"))

    change_1d = ((current - prev) / prev) if prev > 0 else 0.0

    # 30d and 90d change from OHLCV
    change_30d = 0.0
    change_90d = 0.0
    pct_from_ath = 0.0

    if ohlcv is not None and not ohlcv.empty:
        closes = ohlcv["Close"]
        if len(closes) >= 30:
            change_30d = (current - _safe_float(closes.iloc[-30])) / _safe_float(closes.iloc[-30]) if closes.iloc[-30] != 0 else 0.0
        if len(closes) >= 63:
            change_90d = (current - _safe_float(closes.iloc[-63])) / _safe_float(closes.iloc[-63]) if closes.iloc[-63] != 0 else 0.0
        ath = float(closes.max())
        pct_from_ath = ((current - ath) / ath) if ath > 0 else 0.0

    pct_from_52wk_low  = ((current - low_52) / low_52)   if low_52  > 0 else 0.0
    pct_from_52wk_high = ((current - high_52) / high_52) if high_52 > 0 else 0.0

    return {
        "current":           current,
        "prev_close":        prev,
        "change_1d":         round(change_1d, 4),
        "change_30d":        round(change_30d, 4),
        "change_90d":        round(change_90d, 4),
        "pct_from_52wk_low": round(pct_from_52wk_low, 4),
        "pct_from_52wk_high":round(pct_from_52wk_high, 4),
        "pct_from_ath":      round(pct_from_ath, 4),
        "volume_ratio_30d":  volume_ratio,
        "short_float":       _safe_float(technicals.get("short_float") or price_info.get("short_float")),
        "above_200d_ma":     _safe_bool(technicals.get("above_200d_ma")),
        "golden_cross":      _safe_bool(technicals.get("golden_cross")),
        "death_cross":       _safe_bool(technicals.get("death_cross")),
    }


def _build_macro_ns(yield_curve: dict, vix: float, cpi: dict, dxy: dict,
                    fed: dict, spreads: dict) -> dict:
    """Assemble macro.* namespace from all macro fetcher outputs."""
    return {
        "spread_10y_2y":      _safe_float(yield_curve.get("spread_10y_2y")),
        "vix":                vix,
        "cpi_surprise":       _safe_float(cpi.get("surprise")),
        "dxy_change_30d":     _safe_float(dxy.get("change_30d")),
        "fed_rate":           _safe_float(fed.get("rate")),
        "fed_cutting":        _safe_bool(fed.get("cutting")),
        "fed_hiking":         _safe_bool(fed.get("hiking")),
        "hy_spread_change_30d": _safe_float(spreads.get("hy_change_30d")),
        "ig_spread_change_30d": _safe_float(spreads.get("ig_change_30d")),
    }


def build_namespace(
    ticker: str,
    form4_data: list[dict],
    eightk_data: list[dict],
    financials_data: dict,
    peer_context: PeerContext | None,
    price_info: dict,
    technicals: dict,
    volume_ratio: float,
    ohlcv,
    yield_curve: dict,
    vix: float,
    cpi: dict,
    dxy: dict,
    fed: dict,
    spreads: dict,
) -> dict:
    """
    Assemble the complete evaluation namespace from all fetcher outputs.
    Returns a flat dict with sub-namespace objects (form4, filing, etc.)
    as SimpleNamespace-like objects for dot-access in asteval.
    """
    import types

    # Inject ticker into price_info so form4 ns can call yfinance
    price_info_copy = dict(price_info)
    price_info_copy["_ticker"] = ticker

    form4_ns     = _build_form4_ns(form4_data, price_info_copy)
    filing_ns    = _build_filing_ns(eightk_data)
    financials_ns = _build_financials_ns(financials_data, price_info)
    peer_ns      = _build_peer_ns(peer_context)
    price_ns     = _build_price_ns(price_info, technicals, volume_ratio, ohlcv)
    macro_ns     = _build_macro_ns(yield_curve, vix, cpi, dxy, fed, spreads)

    def _ns(d: dict):
        obj = types.SimpleNamespace()
        for k, v in d.items():
            setattr(obj, k, v)
        return obj

    return {
        "form4":     _ns(form4_ns),
        "filing":    _ns(filing_ns),
        "financials": _ns(financials_ns),
        "peer":      _ns(peer_ns),
        "price":     _ns(price_ns),
        "macro":     _ns(macro_ns),
    }


# ---------------------------------------------------------------------------
# SIC Override logic
# ---------------------------------------------------------------------------

def apply_sic_override(rule: Rule, sic: int) -> Rule | None:
    """
    Apply SIC overrides to a rule.
    Returns:
      None    → skip this rule for this SIC
      Rule    → original or modified rule (alternate condition)
    """
    if not rule.sic_overrides:
        return rule

    for sic_range, value in rule.sic_overrides.items():
        if sic_in_range(sic, str(sic_range)):
            if value == "skip":
                return None
            if isinstance(value, dict) and "condition" in value:
                import dataclasses
                return dataclasses.replace(rule, condition=value["condition"])

    return rule


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

def evaluate_rule(rule: Rule, namespace: dict, sic: int = 0) -> FiredSignal | None:
    """
    Evaluate a single rule against the namespace.
    Returns FiredSignal if the rule fires, None otherwise.
    Never raises — logs and returns None on eval error.
    """
    if not rule.enabled:
        return None

    effective_rule = apply_sic_override(rule, sic)
    if effective_rule is None:
        return None

    try:
        from asteval import Interpreter
        aeval = Interpreter(use_numpy=False)

        # Inject namespace objects
        for key, obj in namespace.items():
            aeval.symtable[key] = obj

        result = aeval(effective_rule.condition)

        if aeval.error:
            for err in aeval.error:
                logger.debug("rule %s eval error: %s", rule.id, err.get_error())
            return None

        if not result:
            return None

        score = compute_signal_score(effective_rule.base_strength, effective_rule.rarity)
        label, symbol = classify_rarity(effective_rule.rarity)

        return FiredSignal(
            rule=effective_rule,
            score=score,
            rarity_label=label,
            rarity_symbol=symbol,
        )

    except Exception as e:
        logger.debug("evaluate_rule(%s): %s", rule.id, e)
        return None


def evaluate_all(
    rules: list[Rule],
    namespace: dict,
    sic: int = 0,
) -> list[FiredSignal]:
    """
    Two-pass evaluation:
    Pass 1: evaluate all non-composite rules.
    Pass 2: evaluate composite (CMP) rules, with fired IDs and green/red counts
            injected into the namespace.
    """
    base_rules = [r for r in rules if not r.is_composite]
    cmp_rules  = [r for r in rules if r.is_composite]

    # Pass 1 — base rules
    fired: list[FiredSignal] = []
    for rule in base_rules:
        sig = evaluate_rule(rule, namespace, sic)
        if sig is not None:
            fired.append(sig)

    # Build fired-rule lookup for CMP conditions
    fired_ids = {fs.rule.id for fs in fired}
    green_count  = sum(1 for fs in fired if fs.rule.color == "GREEN")
    red_count    = sum(1 for fs in fired if fs.rule.color == "RED")
    amber_count  = sum(1 for fs in fired if fs.rule.color == "AMBER")
    blue_count   = sum(1 for fs in fired if fs.rule.color == "BLUE")
    purple_count = sum(1 for fs in fired if fs.rule.color == "PURPLE")

    # Pass 2 — composite rules
    # Inject fired() helper and count variables
    def fired_fn(rule_id: str) -> bool:
        return rule_id in fired_ids

    cmp_namespace = dict(namespace)
    cmp_namespace["fired"]        = fired_fn
    cmp_namespace["green_count"]  = green_count
    cmp_namespace["red_count"]    = red_count
    cmp_namespace["amber_count"]  = amber_count
    cmp_namespace["blue_count"]   = blue_count
    cmp_namespace["purple_count"] = purple_count

    for rule in cmp_rules:
        sig = _evaluate_cmp_rule(rule, cmp_namespace, sic)
        if sig is not None:
            fired.append(sig)

    return fired


def _evaluate_cmp_rule(rule: Rule, namespace: dict, sic: int) -> FiredSignal | None:
    """Evaluate a composite rule with fired() and count variables available."""
    if not rule.enabled:
        return None

    effective_rule = apply_sic_override(rule, sic)
    if effective_rule is None:
        return None

    try:
        from asteval import Interpreter
        aeval = Interpreter(use_numpy=False)

        for key, obj in namespace.items():
            aeval.symtable[key] = obj

        result = aeval(effective_rule.condition)

        if aeval.error:
            for err in aeval.error:
                logger.debug("CMP rule %s eval error: %s", rule.id, err.get_error())
            return None

        if not result:
            return None

        score = compute_signal_score(effective_rule.base_strength, effective_rule.rarity)
        label, symbol = classify_rarity(effective_rule.rarity)

        return FiredSignal(
            rule=effective_rule,
            score=score,
            rarity_label=label,
            rarity_symbol=symbol,
        )

    except Exception as e:
        logger.debug("_evaluate_cmp_rule(%s): %s", rule.id, e)
        return None
