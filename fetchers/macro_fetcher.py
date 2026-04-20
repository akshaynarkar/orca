"""
fetchers/macro_fetcher.py
Macroeconomic data via FRED API.
All series fetched from FRED — VIX via VIXCLS, credit spreads via BAML series.
FRED API key loaded from config.yaml.
All functions return empty dict / float 0.0 on failure.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("orca")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _fred_key() -> str:
    try:
        import yaml
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        return str(cfg.get("fred", {}).get("api_key", ""))
    except Exception:
        return ""


def _fred():
    from fredapi import Fred
    key = _fred_key()
    if not key:
        raise ValueError("FRED API key not configured in config.yaml")
    return Fred(api_key=key)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _latest(series, n: int = 1) -> float:
    """Return the most recent non-NaN value from a FRED series."""
    try:
        clean = series.dropna()
        if clean.empty:
            return 0.0
        return _safe_float(clean.iloc[-n])
    except Exception:
        return 0.0


def _change(series, days: int = 30) -> float:
    """Absolute change over last `days` calendar days."""
    try:
        clean = series.dropna()
        if clean.empty:
            return 0.0
        cutoff = clean.index[-1] - timedelta(days=days)
        before = clean[clean.index <= cutoff]
        if before.empty:
            return 0.0
        return _safe_float(clean.iloc[-1]) - _safe_float(before.iloc[-1])
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Yield Curve
# ---------------------------------------------------------------------------

def fetch_yield_curve() -> dict:
    """
    Returns dict:
      spread_10y_2y (float, percentage points, e.g. 0.21)
      rate_10y (float)
      rate_2y (float)
    """
    try:
        f = _fred()
        r10 = f.get_series("DGS10", observation_start=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"))
        r2  = f.get_series("DGS2",  observation_start=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"))
        rate_10 = _latest(r10)
        rate_2  = _latest(r2)
        return {
            "spread_10y_2y": round(rate_10 - rate_2, 4),
            "rate_10y":      round(rate_10, 4),
            "rate_2y":       round(rate_2, 4),
        }
    except Exception as e:
        logger.error("fetch_yield_curve: %s", e)
        return {}


# ---------------------------------------------------------------------------
# VIX
# ---------------------------------------------------------------------------

def fetch_vix() -> float:
    """Returns current VIX value via FRED VIXCLS series. 0.0 on failure."""
    try:
        f   = _fred()
        vix = f.get_series("VIXCLS", observation_start=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"))
        return round(_latest(vix), 2)
    except Exception as e:
        logger.error("fetch_vix: %s", e)
        return 0.0


# ---------------------------------------------------------------------------
# CPI
# ---------------------------------------------------------------------------

def fetch_cpi() -> dict:
    """
    Returns dict:
      latest (float, YoY % change),
      mom (float, month-over-month change),
      surprise (float — requires manual estimate; set to 0.0 if unavailable)
    Note: FRED CPIAUCSL is monthly; surprise vs consensus is not available
    from FRED alone — it defaults to 0.0 (wire in a consensus source in v1.1).
    """
    try:
        f   = _fred()
        # CPIAUCSL: All items, seasonally adjusted
        cpi = f.get_series("CPIAUCSL", observation_start=(datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d"))
        cpi = cpi.dropna()
        if len(cpi) < 13:
            return {}
        latest_val = _safe_float(cpi.iloc[-1])
        year_ago   = _safe_float(cpi.iloc[-13])
        prev_month = _safe_float(cpi.iloc[-2])

        yoy = ((latest_val - year_ago) / year_ago) if year_ago != 0 else 0.0
        mom = ((latest_val - prev_month) / prev_month) if prev_month != 0 else 0.0

        return {
            "latest":   round(yoy, 4),
            "mom":      round(mom, 4),
            "surprise": 0.0,  # Placeholder — wire in consensus data source in v1.1
        }
    except Exception as e:
        logger.error("fetch_cpi: %s", e)
        return {}


# ---------------------------------------------------------------------------
# DXY (Dollar Index)
# ---------------------------------------------------------------------------

def fetch_dxy() -> dict:
    """
    Returns dict:
      current (float),
      change_30d (float, decimal — e.g. 0.032 = +3.2%)
    Uses FRED DTWEXBGS (Nominal Broad Dollar Index as proxy; DXY not in FRED).
    """
    try:
        f   = _fred()
        # DTWEXBGS: Nominal Broad U.S. Dollar Index (closest FRED proxy to DXY)
        dxy = f.get_series("DTWEXBGS", observation_start=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"))
        dxy = dxy.dropna()
        if dxy.empty:
            return {}
        current = _safe_float(dxy.iloc[-1])
        cutoff  = dxy.index[-1] - timedelta(days=30)
        before  = dxy[dxy.index <= cutoff]
        past    = _safe_float(before.iloc[-1]) if not before.empty else current
        change  = (current - past) / past if past != 0 else 0.0
        return {
            "current":    round(current, 2),
            "change_30d": round(change, 4),
        }
    except Exception as e:
        logger.error("fetch_dxy: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Fed Rate
# ---------------------------------------------------------------------------

def fetch_fed_rate() -> dict:
    """
    Returns dict:
      rate (float, current effective fed funds rate),
      cutting (bool),
      hiking (bool)
    """
    try:
        f    = _fred()
        # EFFR: Effective Federal Funds Rate (daily)
        effr = f.get_series("EFFR", observation_start=(datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"))
        effr = effr.dropna()
        if effr.empty:
            return {}
        current = _safe_float(effr.iloc[-1])

        # Detect cycle: compare 3-month-ago rate to current
        cutoff   = effr.index[-1] - timedelta(days=90)
        past_ser = effr[effr.index <= cutoff]
        past_val = _safe_float(past_ser.iloc[-1]) if not past_ser.empty else current

        delta   = current - past_val
        cutting = delta < -0.10   # Fed cut by at least 10bps in 90d
        hiking  = delta > 0.10    # Fed hiked by at least 10bps in 90d

        return {
            "rate":    round(current, 4),
            "cutting": cutting,
            "hiking":  hiking,
        }
    except Exception as e:
        logger.error("fetch_fed_rate: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Credit Spreads
# ---------------------------------------------------------------------------

def fetch_credit_spreads() -> dict:
    """
    Returns dict:
      hy_spread (float, bps),
      hy_change_30d (float, bps change),
      ig_spread (float, bps),
      ig_change_30d (float, bps change)

    FRED series:
      BAMLH0A0HYM2  — ICE BofA US High Yield OAS (%)
      BAMLC0A0CM    — ICE BofA US Corporate Master OAS (%) [IG proxy]
    Spreads stored as % in FRED; multiply by 100 for bps.
    """
    try:
        f    = _fred()
        obs_start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        hy_raw = f.get_series("BAMLH0A0HYM2", observation_start=obs_start).dropna()
        ig_raw = f.get_series("BAMLC0A0CM",   observation_start=obs_start).dropna()

        def _spread_and_change(series):
            if series.empty:
                return 0.0, 0.0
            current_bps = _safe_float(series.iloc[-1]) * 100
            cutoff = series.index[-1] - timedelta(days=30)
            before = series[series.index <= cutoff]
            past_bps = _safe_float(before.iloc[-1]) * 100 if not before.empty else current_bps
            return round(current_bps, 1), round(current_bps - past_bps, 1)

        hy_spread, hy_chg = _spread_and_change(hy_raw)
        ig_spread, ig_chg = _spread_and_change(ig_raw)

        return {
            "hy_spread":      hy_spread,
            "hy_change_30d":  hy_chg,
            "ig_spread":      ig_spread,
            "ig_change_30d":  ig_chg,
        }
    except Exception as e:
        logger.error("fetch_credit_spreads: %s", e)
        return {}
