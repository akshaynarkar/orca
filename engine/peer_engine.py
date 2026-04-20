"""
engine/peer_engine.py
Peer universe fetch by SIC code, XBRL metric comparison, percentile computation.
Cache: cache/peers_{sic}_{date}.parquet — built once per sector per day.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from engine.sic_classifier import get_fama_french_industry, get_sic_description
from engine.signal_report import PeerContext

logger = logging.getLogger("orca")

CACHE_DIR = Path("cache")
MAX_PEERS = 10
VALID_EXCHANGES = {"NYSE", "NASDAQ", "NMS", "NYQ", "NGM", "NCM"}

# Metrics we compute percentiles for
PEER_METRICS = [
    "rev_growth",
    "gross_margin",
    "fcf_yield",
    "debt_ebitda",
    "pe",
    "op_leverage",
    "ev_ebitda",
    "pb",
    "p_ffo",
]


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(sic: int) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()
    return CACHE_DIR / f"peers_{sic}_{today}.parquet"


def _load_cache(sic: int) -> pd.DataFrame | None:
    p = _cache_path(sic)
    if p.exists():
        try:
            df = pd.read_parquet(p)
            logger.debug("peer cache hit: %s", p)
            return df
        except Exception as e:
            logger.debug("peer cache read error: %s", e)
    return None


def _save_cache(sic: int, df: pd.DataFrame) -> None:
    p = _cache_path(sic)
    try:
        df.to_parquet(p, index=False)
        logger.debug("peer cache saved: %s", p)
    except Exception as e:
        logger.debug("peer cache write error: %s", e)


# ---------------------------------------------------------------------------
# Metric extraction helpers
# ---------------------------------------------------------------------------

def _get_yf_metrics(ticker: str) -> dict:
    """Extract peer metrics for a single ticker via yfinance. Returns {} on failure."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}

        fi = t.fast_info
        price = _safe_float(getattr(fi, "last_price", None) or info.get("currentPrice"))
        mktcap = _safe_float(getattr(fi, "market_cap", None) or info.get("marketCap"))

        # Revenue growth: (ttm revenue - prev year revenue) / prev year revenue
        rev_growth = _safe_float(info.get("revenueGrowth"))

        # Gross margin
        gross_margin = _safe_float(info.get("grossMargins"))

        # FCF yield: freeCashflow / marketCap
        fcf = _safe_float(info.get("freeCashflow"))
        fcf_yield = (fcf / mktcap) if mktcap > 0 else 0.0

        # Debt / EBITDA
        total_debt = _safe_float(info.get("totalDebt"))
        ebitda = _safe_float(info.get("ebitda"))
        debt_ebitda = (total_debt / ebitda) if ebitda > 0 else 0.0

        # P/E
        pe = _safe_float(info.get("trailingPE"))

        # Operating leverage: rough proxy — operatingMargins YoY change
        # Can't compute true op leverage from info alone; use operatingMargins as proxy
        op_leverage = _safe_float(info.get("operatingMargins")) * 100  # as pp

        # EV/EBITDA
        ev = _safe_float(info.get("enterpriseValue"))
        ev_ebitda = (ev / ebitda) if ebitda > 0 else 0.0

        # P/B
        pb = _safe_float(info.get("priceToBook"))

        # P/FFO: not in yfinance — set 0 (relevant for REITs only)
        p_ffo = 0.0

        exchange = str(info.get("exchange", "") or "")

        return {
            "ticker": ticker,
            "mktcap": mktcap,
            "exchange": exchange,
            "rev_growth": rev_growth,
            "gross_margin": gross_margin,
            "fcf_yield": fcf_yield,
            "debt_ebitda": debt_ebitda,
            "pe": pe,
            "op_leverage": op_leverage,
            "ev_ebitda": ev_ebitda,
            "pb": pb,
            "p_ffo": p_ffo,
        }
    except Exception as e:
        logger.debug("_get_yf_metrics(%s): %s", ticker, e)
        return {}


# ---------------------------------------------------------------------------
# Peer universe fetch
# ---------------------------------------------------------------------------

def get_peers(ticker: str, sic: int, max_peers: int = MAX_PEERS) -> list[str]:
    """
    Return up to max_peers ticker symbols in the same SIC group,
    sorted by market cap descending, excluding the subject ticker.
    Uses Parquet cache. Returns [] on failure.
    """
    try:
        cached = _load_cache(sic)
        if cached is not None and len(cached) > 0:
            peers = cached[cached["ticker"] != ticker]["ticker"].tolist()
            return peers[:max_peers]

        # Fetch peer universe from EDGAR
        from edgar import Company, set_identity
        import yaml

        try:
            cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            identity = cfg.get("identity", {})
            set_identity(f"{identity.get('name','ORCA')} {identity.get('email','orca@example.com')}")
        except Exception:
            set_identity("ORCA orca@example.com")

        # edgartools: get companies by SIC
        try:
            from edgar import get_company_facts, get_companies
            companies_df = get_companies(sic=sic)
        except Exception:
            companies_df = None

        candidate_tickers: list[str] = []
        if companies_df is not None and len(companies_df) > 0:
            # edgartools returns a DataFrame with 'ticker' column or similar
            for col in ("ticker", "Ticker", "symbol", "Symbol"):
                if col in companies_df.columns:
                    candidate_tickers = companies_df[col].dropna().tolist()
                    break

        if not candidate_tickers:
            logger.warning("get_peers: no EDGAR companies found for SIC %d", sic)
            return []

        # Filter to NYSE/NASDAQ, fetch metrics, sort by mktcap
        rows: list[dict] = []
        for t in candidate_tickers[:60]:  # cap to avoid rate limit storm
            if str(t).upper() == ticker.upper():
                continue
            m = _get_yf_metrics(str(t))
            if not m or m.get("mktcap", 0) <= 0:
                continue
            if m.get("exchange", "").upper() not in VALID_EXCHANGES:
                continue
            rows.append(m)

        if not rows:
            return []

        df = pd.DataFrame(rows)
        df = df.sort_values("mktcap", ascending=False).reset_index(drop=True)
        _save_cache(sic, df)

        peers = df[df["ticker"] != ticker]["ticker"].tolist()
        return peers[:max_peers]

    except Exception as e:
        logger.error("get_peers(%s, sic=%d): %s", ticker, sic, e)
        return []


# ---------------------------------------------------------------------------
# Percentile computation
# ---------------------------------------------------------------------------

def _percentile_rank(value: float, series: list[float]) -> float:
    """Return percentile rank (0–100) of value within series. Higher is better for all metrics."""
    if not series:
        return 50.0
    below = sum(1 for v in series if v < value)
    return round((below / len(series)) * 100, 1)


def _percentile_rank_lower_better(value: float, series: list[float]) -> float:
    """Percentile where LOWER value = HIGHER percentile (e.g. debt_ebitda)."""
    if not series:
        return 50.0
    above = sum(1 for v in series if v > value)
    return round((above / len(series)) * 100, 1)


def compute_peer_percentiles(
    subject_metrics: dict,
    peer_rows: list[dict],
) -> dict:
    """
    Compute percentile ranks for the subject ticker vs peer rows.
    Returns dict: {metric}_percentile -> 0–100.
    """
    percentiles: dict[str, float] = {}

    for metric in PEER_METRICS:
        subject_val = _safe_float(subject_metrics.get(metric))
        peer_vals = [_safe_float(r.get(metric)) for r in peer_rows if r.get(metric) is not None]

        if not peer_vals:
            percentiles[f"{metric}_percentile"] = 50.0
            continue

        # debt_ebitda: lower is better (less debt relative to earnings)
        if metric == "debt_ebitda":
            percentiles[f"{metric}_percentile"] = _percentile_rank_lower_better(subject_val, peer_vals)
        else:
            percentiles[f"{metric}_percentile"] = _percentile_rank(subject_val, peer_vals)

    return percentiles


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_peer_context(ticker: str, sic: int, subject_metrics: dict) -> PeerContext:
    """
    Build a full PeerContext for the subject ticker.
    Falls back to empty percentiles (all 50) on any failure.
    """
    default_percentiles = {f"{m}_percentile": 50.0 for m in PEER_METRICS}

    try:
        # Check cache first for peer metric rows
        cached = _load_cache(sic)

        if cached is not None and len(cached) > 0:
            peer_df = cached[cached["ticker"] != ticker].head(MAX_PEERS)
        else:
            peer_tickers = get_peers(ticker, sic)
            if not peer_tickers:
                return PeerContext(
                    ticker=ticker,
                    sic=sic,
                    sector_name=get_sic_description(sic),
                    fama_french_industry=get_fama_french_industry(sic),
                    peer_tickers=[],
                    peer_count=0,
                    percentiles=default_percentiles,
                )
            cached = _load_cache(sic)
            peer_df = cached[cached["ticker"] != ticker].head(MAX_PEERS) if cached is not None else pd.DataFrame()

        if peer_df.empty:
            return PeerContext(
                ticker=ticker,
                sic=sic,
                sector_name=get_sic_description(sic),
                fama_french_industry=get_fama_french_industry(sic),
                peer_tickers=[],
                peer_count=0,
                percentiles=default_percentiles,
            )

        peer_rows = peer_df.to_dict("records")
        percentiles = compute_peer_percentiles(subject_metrics, peer_rows)

        return PeerContext(
            ticker=ticker,
            sic=sic,
            sector_name=get_sic_description(sic),
            fama_french_industry=get_fama_french_industry(sic),
            peer_tickers=peer_df["ticker"].tolist(),
            peer_count=len(peer_df),
            percentiles=percentiles,
        )

    except Exception as e:
        logger.error("get_peer_context(%s): %s", ticker, e)
        return PeerContext(
            ticker=ticker,
            sic=sic,
            sector_name=get_sic_description(sic),
            fama_french_industry=get_fama_french_industry(sic),
            peer_tickers=[],
            peer_count=0,
            percentiles=default_percentiles,
        )
