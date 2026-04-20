"""
fetchers/price_fetcher.py
Market data fetcher via yfinance: OHLCV, info, technicals, volume ratio.
All functions return empty dict/DataFrame on any failure.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore

logger = logging.getLogger("orca")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------

def fetch_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Returns OHLCV DataFrame indexed by date.
    Columns: Open, High, Low, Close, Volume
    Empty DataFrame on failure.
    """
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        # Normalise column names
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception as e:
        logger.error("fetch_ohlcv(%s): %s", ticker, e)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------

def fetch_info(ticker: str) -> dict:
    """
    Returns dict:
      price, prev_close, mktcap, volume, avg_volume,
      52wk_high, 52wk_low, pe_ratio, forward_pe,
      short_float, beta, sector, industry
    Empty dict on failure.
    """
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}
        fi   = t.fast_info

        price      = _safe_float(getattr(fi, "last_price", None) or info.get("currentPrice"))
        prev_close = _safe_float(getattr(fi, "previous_close", None) or info.get("previousClose"))
        mktcap     = _safe_float(getattr(fi, "market_cap", None) or info.get("marketCap"))
        volume     = _safe_float(getattr(fi, "last_volume", None) or info.get("volume"))
        avg_vol    = _safe_float(info.get("averageVolume") or info.get("averageVolume10days"))
        high_52    = _safe_float(getattr(fi, "year_high", None) or info.get("fiftyTwoWeekHigh"))
        low_52     = _safe_float(getattr(fi, "year_low", None) or info.get("fiftyTwoWeekLow"))

        return {
            "price":       price,
            "prev_close":  prev_close,
            "mktcap":      mktcap,
            "volume":      volume,
            "avg_volume":  avg_vol,
            "52wk_high":   high_52,
            "52wk_low":    low_52,
            "pe_ratio":    _safe_float(info.get("trailingPE")),
            "forward_pe":  _safe_float(info.get("forwardPE")),
            "short_float": _safe_float(info.get("shortPercentOfFloat")),
            "beta":        _safe_float(info.get("beta")),
            "sector":      str(info.get("sector", "")),
            "industry":    str(info.get("industry", "")),
        }

    except Exception as e:
        logger.error("fetch_info(%s): %s", ticker, e)
        return {}


# ---------------------------------------------------------------------------
# Technicals
# ---------------------------------------------------------------------------

def fetch_technical(ticker: str) -> dict:
    """
    Returns dict:
      above_200d_ma (bool), golden_cross (bool), death_cross (bool),
      ma_50, ma_200, short_float (float)
    Empty dict on failure.
    """
    try:
        df = fetch_ohlcv(ticker, period="1y")
        if df.empty or len(df) < 50:
            return {}

        close = df["Close"]

        ma50  = float(close.rolling(50).mean().iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        current_price = float(close.iloc[-1])
        above_200d_ma = bool(ma200 and current_price > ma200)

        # Golden / death cross: 50d crossed 200d in last 10 trading days
        golden_cross = False
        death_cross  = False
        if ma200 and len(close) >= 210:
            ma50_series  = close.rolling(50).mean()
            ma200_series = close.rolling(200).mean()
            window = 10
            recent_50  = ma50_series.iloc[-window:]
            recent_200 = ma200_series.iloc[-window:]
            diff       = recent_50 - recent_200
            # Sign changes
            signs = diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
            for i in range(1, len(signs)):
                prev_s, curr_s = signs.iloc[i - 1], signs.iloc[i]
                if prev_s < 0 and curr_s > 0:
                    golden_cross = True
                elif prev_s > 0 and curr_s < 0:
                    death_cross = True

        short_float = _safe_float((yf.Ticker(ticker).info or {}).get("shortPercentOfFloat"))

        return {
            "above_200d_ma": above_200d_ma,
            "golden_cross":  golden_cross,
            "death_cross":   death_cross,
            "ma_50":         ma50,
            "ma_200":        ma200,
            "short_float":   short_float,
        }

    except Exception as e:
        logger.error("fetch_technical(%s): %s", ticker, e)
        return {}


# ---------------------------------------------------------------------------
# Volume Ratio
# ---------------------------------------------------------------------------

def fetch_volume_ratio(ticker: str) -> float:
    """
    Returns today's volume / 30-day average volume.
    Returns 0.0 on failure.
    """
    try:
        df = fetch_ohlcv(ticker, period="2mo")
        if df.empty or len(df) < 2:
            return 0.0
        avg_30 = float(df["Volume"].iloc[-31:-1].mean()) if len(df) >= 31 else float(df["Volume"].iloc[:-1].mean())
        today  = float(df["Volume"].iloc[-1])
        return round(today / avg_30, 3) if avg_30 > 0 else 0.0
    except Exception as e:
        logger.error("fetch_volume_ratio(%s): %s", ticker, e)
        return 0.0
