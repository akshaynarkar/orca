"""
fetchers/news_fetcher.py
News headline fetcher via RSS: SEC EDGAR + Yahoo Finance.
Returns empty list on any failure.
"""

from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

logger = logging.getLogger("orca")

# SEC EDGAR full-text search RSS (company-specific via CIK or ticker)
_SEC_RSS_TEMPLATE    = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&forms=8-K&hits.hits._source=period_of_report,entity_name,file_date,form_type,biz_location,inc_states"
_SEC_FILINGS_RSS     = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=8-K&dateb=&owner=include&count=10&search_text=&output=atom"

# Yahoo Finance RSS
_YAHOO_RSS_TEMPLATE  = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


def _parse_date(entry: Any) -> str:
    """Extract and normalize RSS entry date to YYYY-MM-DD string."""
    for attr in ("published", "updated", "pubDate"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
            except Exception:
                try:
                    return str(raw)[:10]
                except Exception:
                    pass
    return datetime.now().strftime("%Y-%m-%d")


def fetch_headlines(ticker: str, n: int = 5) -> list[dict]:
    """
    Returns up to `n` headline dicts merged from SEC EDGAR + Yahoo Finance RSS.
    Fields: date, title, source, url
    Empty list on failure.
    """
    results: list[dict] = []

    # --- SEC EDGAR RSS ---
    try:
        import feedparser
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        sec_url    = _SEC_FILINGS_RSS.format(ticker=ticker)
        feed       = feedparser.parse(sec_url)

        for entry in feed.entries[:n]:
            try:
                title = str(getattr(entry, "title", "") or "").strip()
                link  = str(getattr(entry, "link", "") or getattr(entry, "id", "")).strip()
                date  = _parse_date(entry)
                if title:
                    results.append({
                        "date":   date,
                        "title":  title,
                        "source": "SEC EDGAR",
                        "url":    link,
                    })
            except Exception as e:
                logger.debug("sec rss entry parse: %s", e)

    except Exception as e:
        logger.error("fetch_headlines SEC RSS (%s): %s", ticker, e)

    # --- Yahoo Finance RSS ---
    try:
        import feedparser
        yahoo_url = _YAHOO_RSS_TEMPLATE.format(ticker=ticker)
        feed      = feedparser.parse(yahoo_url)

        for entry in feed.entries[:n]:
            try:
                title = str(getattr(entry, "title", "") or "").strip()
                link  = str(getattr(entry, "link", "") or "").strip()
                date  = _parse_date(entry)
                if title:
                    results.append({
                        "date":   date,
                        "title":  title,
                        "source": "Yahoo Finance",
                        "url":    link,
                    })
            except Exception as e:
                logger.debug("yahoo rss entry parse: %s", e)

    except Exception as e:
        logger.error("fetch_headlines Yahoo RSS (%s): %s", ticker, e)

    # Sort by date descending, return top n
    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results[:n]
