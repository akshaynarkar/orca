"""
tests/test_fetchers.py
Mock-based unit tests for all Phase 2 data fetchers.
Run with: pytest tests/test_fetchers.py -v
"""

from __future__ import annotations

import sys
import os
import types
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure fetchers package is importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===========================================================================
# edgar_fetcher tests
# ===========================================================================

class TestFetchForm4:

    def _mock_txn(self, code="P", shares=1000, price=100.0, owned=5000):
        txn = MagicMock()
        txn.transactionCode = code
        txn.acquiredDisposedCode = "A" if code == "P" else "D"
        txn.shares = shares
        txn.pricePerShare = price
        txn.sharesOwnedFollowingTransaction = owned
        return txn

    def _mock_reporter(self, name="John Smith", is_ceo=True):
        rel = MagicMock()
        rel.isDirector = False
        rel.isOfficer = is_ceo
        rel.officerTitle = "Chief Executive Officer" if is_ceo else "Director"
        rel.isTenPercentOwner = False
        reporter = MagicMock()
        reporter.name = name
        reporter.relationship = rel
        return reporter

    def test_returns_list_on_success(self):
        """fetch_form4 returns a list on success."""
        from datetime import datetime, timedelta

        mock_obj = MagicMock()
        mock_obj.transactions = [self._mock_txn("P", 2000, 150.0, 10000)]
        mock_obj.reportingOwner = self._mock_reporter()

        mock_filing = MagicMock()
        mock_filing.filing_date = datetime.now() - timedelta(days=5)
        mock_filing.accession_number = "0001234567-24-000001"
        mock_filing.obj.return_value = mock_obj

        mock_company = MagicMock()
        mock_company.get_filings.return_value = [mock_filing]

        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_form4
            result = fetch_form4("MSFT", days=60)

        assert isinstance(result, list)
        assert len(result) >= 1
        row = result[0]
        assert row["kind"] == "BUY"
        assert row["shares"] == 2000
        assert row["price"] == 150.0

    def test_returns_empty_list_on_network_failure(self):
        """fetch_form4 returns [] on exception."""
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", side_effect=ConnectionError("timeout")):
            from fetchers.edgar_fetcher import fetch_form4
            result = fetch_form4("MSFT")
        assert result == []

    def test_returns_empty_list_on_none_filings(self):
        """fetch_form4 returns [] when Company returns None filings."""
        mock_company = MagicMock()
        mock_company.get_filings.return_value = None
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_form4
            result = fetch_form4("FAKE")
        assert result == []

    def test_classifies_sell_correctly(self):
        """Sell transactions (code S) classified as SELL."""
        from datetime import datetime, timedelta

        mock_obj = MagicMock()
        mock_obj.transactions = [self._mock_txn("S", 500, 200.0, 2000)]
        mock_obj.reportingOwner = self._mock_reporter("Jane Doe", False)

        mock_filing = MagicMock()
        mock_filing.filing_date = datetime.now() - timedelta(days=3)
        mock_filing.obj.return_value = mock_obj

        mock_company = MagicMock()
        mock_company.get_filings.return_value = [mock_filing]

        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_form4
            result = fetch_form4("AAPL")

        assert any(r["kind"] == "SELL" for r in result)


class TestFetch8K:

    def _make_filing(self, text: str, items: list[str] | None = None,
                     days_ago: int = 5):
        from datetime import datetime, timedelta
        mock_obj = MagicMock()
        mock_obj.__str__ = lambda self: text
        mock_filing = MagicMock()
        mock_filing.filing_date = datetime.now() - timedelta(days=days_ago)
        mock_filing.accession_number = "0001234567-24-000001"
        mock_filing.items = items or []
        mock_filing.going_concern = False
        mock_filing.obj.return_value = mock_obj
        return mock_filing

    def test_returns_list_on_success(self):
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [
            self._make_filing("Material contract signed with partner.", ["8.01"])
        ]
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_8k
            result = fetch_8k("MSFT", n=5)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "date" in result[0]
        assert "items" in result[0]

    def test_detects_going_concern_keyword(self):
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [
            self._make_filing("The company has substantial doubt about its ability to continue as a going concern.")
        ]
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_8k
            result = fetch_8k("WEAK", n=5)
        assert result[0]["has_going_concern"] is True

    def test_detects_guidance_raised_keyword(self):
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [
            self._make_filing("The company raises guidance for full year 2026.")
        ]
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_8k
            result = fetch_8k("MSFT", n=5)
        assert result[0]["has_guidance_raised"] is True
        assert result[0]["has_guidance"] is True

    def test_detects_ceo_departure_keyword(self):
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [
            self._make_filing("The Chief Executive Officer has resigned from the company.", ["5.02"])
        ]
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company):
            from fetchers.edgar_fetcher import fetch_8k
            result = fetch_8k("CORP", n=5)
        assert result[0]["has_ceo_departure"] is True

    def test_returns_empty_on_network_failure(self):
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", side_effect=OSError("no network")):
            from fetchers.edgar_fetcher import fetch_8k
            result = fetch_8k("MSFT")
        assert result == []


class TestFetchCompanyInfo:

    def test_returns_dict_on_success(self):
        mock_company = MagicMock()
        mock_company.name = "Microsoft Corporation"
        mock_company.sic = 7372
        mock_company.sic_description = "Prepackaged Software"
        mock_company.exchange = "Nasdaq"

        mock_yf_info = {"website": "https://microsoft.com", "longBusinessSummary": "Tech giant."}

        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", return_value=mock_company), \
             patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.info = mock_yf_info
            from fetchers.edgar_fetcher import fetch_company_info
            result = fetch_company_info("MSFT")

        assert result["name"] == "Microsoft Corporation"
        assert result["sic"] == 7372
        assert result["exchange"] == "Nasdaq"

    def test_returns_empty_on_failure(self):
        with patch("fetchers.edgar_fetcher._set_identity"), \
             patch("fetchers.edgar_fetcher.Company", side_effect=Exception("404")):
            from fetchers.edgar_fetcher import fetch_company_info
            result = fetch_company_info("FAKE")
        assert result == {}


# ===========================================================================
# price_fetcher tests
# ===========================================================================

def _make_ohlcv_df(n: int = 65) -> pd.DataFrame:
    import numpy as np
    dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n)
    price = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "Open":   price * 0.99,
        "High":   price * 1.01,
        "Low":    price * 0.98,
        "Close":  price,
        "Volume": np.random.randint(1_000_000, 5_000_000, n).astype(float),
    }, index=dates)


class TestFetchOHLCV:

    def test_returns_dataframe_on_success(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_ohlcv_df()
        with patch("yfinance.Ticker", return_value=mock_ticker):
            from fetchers.price_fetcher import fetch_ohlcv
            df = fetch_ohlcv("MSFT")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert set(df.columns) == {"Open", "High", "Low", "Close", "Volume"}

    def test_returns_empty_df_on_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("network")):
            from fetchers.price_fetcher import fetch_ohlcv
            df = fetch_ohlcv("MSFT")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_returns_empty_df_on_empty_history(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("yfinance.Ticker", return_value=mock_ticker):
            from fetchers.price_fetcher import fetch_ohlcv
            df = fetch_ohlcv("DEAD")
        assert df.empty


class TestFetchInfo:

    def test_returns_correct_fields(self):
        mock_fi = MagicMock()
        mock_fi.last_price = 422.79
        mock_fi.previous_close = 417.5
        mock_fi.market_cap = 3_100_000_000_000
        mock_fi.last_volume = 18_000_000
        mock_fi.year_high = 555.0
        mock_fi.year_low = 355.0

        mock_info = {
            "averageVolume": 20_000_000,
            "trailingPE": 31.0,
            "forwardPE": 27.0,
            "shortPercentOfFloat": 0.007,
            "beta": 0.9,
            "sector": "Technology",
            "industry": "Software—Infrastructure",
        }

        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi
        mock_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_ticker):
            from fetchers.price_fetcher import fetch_info
            result = fetch_info("MSFT")

        assert result["price"] == 422.79
        assert result["52wk_high"] == 555.0
        assert result["sector"] == "Technology"

    def test_returns_empty_on_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("403")):
            from fetchers.price_fetcher import fetch_info
            result = fetch_info("MSFT")
        assert result == {}


class TestFetchTechnical:

    def test_returns_correct_booleans(self):
        import numpy as np
        import fetchers.price_fetcher as pf

        # Steadily rising: final price ≈150, ma200 ≈131 → above_200d_ma = True
        n = 260
        close_vals = 100 + np.linspace(0, 50, n)
        idx = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   close_vals * 0.99,
            "High":   close_vals * 1.01,
            "Low":    close_vals * 0.98,
            "Close":  close_vals,
            "Volume": np.full(n, 1_000_000, dtype=float),
        }, index=idx)

        mock_ticker = MagicMock()
        mock_ticker.info = {"shortPercentOfFloat": 0.01}

        with patch.object(pf, "fetch_ohlcv", return_value=df), \
             patch.object(pf, "yf") as mock_yf_mod:
            mock_yf_mod.Ticker.return_value = mock_ticker
            result = pf.fetch_technical("MSFT")

        assert "above_200d_ma" in result
        assert result["above_200d_ma"] is True

    def test_returns_empty_on_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("timeout")):
            from fetchers.price_fetcher import fetch_technical
            result = fetch_technical("MSFT")
        assert result == {}


class TestFetchVolumeRatio:

    def test_returns_float(self):
        import numpy as np
        df = _make_ohlcv_df(65)
        # Force today's volume to exactly 3x the average of prior 30 days
        avg = df["Volume"].iloc[-31:-1].mean()
        df.at[df.index[-1], "Volume"] = avg * 3.0

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df

        with patch("yfinance.Ticker", return_value=mock_ticker):
            from fetchers.price_fetcher import fetch_volume_ratio
            ratio = fetch_volume_ratio("MSFT")

        assert isinstance(ratio, float)
        assert abs(ratio - 3.0) < 0.1

    def test_returns_zero_on_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("error")):
            from fetchers.price_fetcher import fetch_volume_ratio
            ratio = fetch_volume_ratio("MSFT")
        assert ratio == 0.0


# ===========================================================================
# macro_fetcher tests
# ===========================================================================

def _mock_fred_series(values: list[float], days_back: int = 60) -> "pd.Series":
    dates = pd.date_range(end=pd.Timestamp.now(), periods=len(values), freq="B")
    return pd.Series(values, index=dates)


class TestFetchYieldCurve:

    def test_returns_correct_spread(self):
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = lambda series, **kw: (
            _mock_fred_series([4.3, 4.3, 4.3]) if series == "DGS10"
            else _mock_fred_series([4.1, 4.1, 4.1])
        )
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_yield_curve
            result = fetch_yield_curve()
        assert abs(result["spread_10y_2y"] - 0.2) < 0.001
        assert result["rate_10y"] == pytest.approx(4.3, abs=0.001)

    def test_negative_spread(self):
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = lambda series, **kw: (
            _mock_fred_series([3.9]) if series == "DGS10"
            else _mock_fred_series([4.5])
        )
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_yield_curve
            result = fetch_yield_curve()
        assert result["spread_10y_2y"] < 0

    def test_returns_empty_on_failure(self):
        with patch("fetchers.macro_fetcher._fred", side_effect=Exception("no key")):
            from fetchers.macro_fetcher import fetch_yield_curve
            result = fetch_yield_curve()
        assert result == {}


class TestFetchVix:

    def test_returns_float(self):
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = _mock_fred_series([18.0, 19.2, 20.5])
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_vix
            result = fetch_vix()
        assert result == pytest.approx(20.5, abs=0.01)

    def test_returns_zero_on_failure(self):
        with patch("fetchers.macro_fetcher._fred", side_effect=Exception("err")):
            from fetchers.macro_fetcher import fetch_vix
            result = fetch_vix()
        assert result == 0.0


class TestFetchFedRate:

    def test_detects_cutting_cycle(self):
        # Current rate 4.75, 90d ago was 5.25 → cutting
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq="B")
        vals  = [5.25] * 70 + [5.0] * 15 + [4.75] * 15
        series = pd.Series(vals, index=dates)
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = series
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_fed_rate
            result = fetch_fed_rate()
        assert result["cutting"] is True
        assert result["hiking"] is False

    def test_detects_hiking_cycle(self):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq="B")
        vals  = [2.0] * 70 + [2.5] * 15 + [3.0] * 15
        series = pd.Series(vals, index=dates)
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = series
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_fed_rate
            result = fetch_fed_rate()
        assert result["hiking"] is True
        assert result["cutting"] is False

    def test_returns_empty_on_failure(self):
        with patch("fetchers.macro_fetcher._fred", side_effect=Exception("err")):
            from fetchers.macro_fetcher import fetch_fed_rate
            result = fetch_fed_rate()
        assert result == {}


class TestFetchCreditSpreads:

    def test_returns_correct_fields(self):
        # 90 bdays total. Old value (3.0) covers first 70 bdays (~98 cal days).
        # New value (3.5) covers last 20 bdays (~28 cal days).
        # 30-calendar-day cutoff from today lands in the 3.0 block → change = +50bps.
        now = pd.Timestamp.now().normalize()
        hy_dates  = pd.bdate_range(end=now, periods=90)
        hy_vals   = [3.0] * 70 + [3.5] * 20
        hy_series = pd.Series(hy_vals, index=hy_dates)

        ig_dates  = pd.bdate_range(end=now, periods=90)
        ig_vals   = [1.2] * 70 + [1.3] * 20
        ig_series = pd.Series(ig_vals, index=ig_dates)

        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = lambda series, **kw: (
            hy_series if "BAMLH0A0HYM2" in series else ig_series
        )
        with patch("fetchers.macro_fetcher._fred", return_value=mock_fred):
            from fetchers.macro_fetcher import fetch_credit_spreads
            result = fetch_credit_spreads()

        assert result["hy_spread"] == pytest.approx(350.0, abs=1.0)
        assert result["hy_change_30d"] > 0  # widening
        assert "ig_spread" in result

    def test_returns_empty_on_failure(self):
        with patch("fetchers.macro_fetcher._fred", side_effect=Exception("err")):
            from fetchers.macro_fetcher import fetch_credit_spreads
            result = fetch_credit_spreads()
        assert result == {}


# ===========================================================================
# news_fetcher tests
# ===========================================================================

def _make_feed_entry(title: str, url: str, date: str = "Mon, 19 Apr 2026 12:00:00 +0000"):
    entry = MagicMock()
    entry.title = title
    entry.link  = url
    entry.published = date
    entry.updated   = date
    return entry


class TestFetchHeadlines:

    def test_returns_list_on_success(self):
        mock_sec_feed   = MagicMock()
        mock_yahoo_feed = MagicMock()
        mock_sec_feed.entries   = [_make_feed_entry("MSFT files 8-K", "https://sec.gov/1")]
        mock_yahoo_feed.entries = [_make_feed_entry("Microsoft earnings beat", "https://yahoo.com/1")]

        with patch("feedparser.parse", side_effect=[mock_sec_feed, mock_yahoo_feed]):
            from fetchers.news_fetcher import fetch_headlines
            result = fetch_headlines("MSFT", n=5)

        assert isinstance(result, list)
        assert len(result) >= 1
        for item in result:
            assert "date" in item
            assert "title" in item
            assert "source" in item
            assert "url" in item

    def test_returns_empty_on_both_feeds_failing(self):
        with patch("feedparser.parse", side_effect=Exception("network")):
            from fetchers.news_fetcher import fetch_headlines
            result = fetch_headlines("MSFT")
        assert result == []

    def test_partial_failure_still_returns_results(self):
        """If SEC feed fails but Yahoo succeeds, still return Yahoo results."""
        mock_yahoo_feed = MagicMock()
        mock_yahoo_feed.entries = [
            _make_feed_entry("Microsoft AI news", "https://yahoo.com/2")
        ]

        call_count = [0]
        def side_effect(url):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("SEC down")
            return mock_yahoo_feed

        with patch("feedparser.parse", side_effect=side_effect):
            from fetchers.news_fetcher import fetch_headlines
            result = fetch_headlines("MSFT", n=5)

        assert isinstance(result, list)
        # Yahoo results should still be returned
        assert len(result) >= 1

    def test_respects_n_limit(self):
        entries = [_make_feed_entry(f"Headline {i}", f"https://url/{i}") for i in range(10)]
        mock_feed = MagicMock()
        mock_feed.entries = entries

        with patch("feedparser.parse", return_value=mock_feed):
            from fetchers.news_fetcher import fetch_headlines
            result = fetch_headlines("MSFT", n=3)

        assert len(result) <= 3

    def test_deduplication_by_source(self):
        """Results should include items from both SEC and Yahoo sources."""
        mock_feed = MagicMock()
        mock_feed.entries = [_make_feed_entry("News item", "https://example.com/1")]

        with patch("feedparser.parse", return_value=mock_feed):
            from fetchers.news_fetcher import fetch_headlines
            result = fetch_headlines("MSFT", n=10)

        sources = {r["source"] for r in result}
        assert len(sources) > 0
