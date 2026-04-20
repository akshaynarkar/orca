"""
fetchers/edgar_fetcher.py
EDGAR data fetcher: Form 4, 8-K, financials, XBRL facts, company info.
All functions return empty dict/list on any failure — never raise to caller.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("orca")

# Top-level imports so tests can patch("fetchers.edgar_fetcher.Company")
try:
    from edgar import Company, set_identity as _edgar_set_identity
except ImportError:
    Company = None              # type: ignore
    _edgar_set_identity = None  # type: ignore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identity() -> tuple[str, str]:
    """Load SEC identity from config.yaml."""
    try:
        import yaml, os
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        identity = cfg.get("identity", {})
        return identity.get("name", "ORCA User"), identity.get("email", "orca@example.com")
    except Exception:
        return "ORCA User", "orca@example.com"


def _set_identity() -> None:
    name, email = _identity()
    if _edgar_set_identity is not None:
        _edgar_set_identity(f"{name} {email}")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Form 4 — Insider Transactions
# ---------------------------------------------------------------------------

def fetch_form4(ticker: str, days: int = 60) -> list[dict]:
    """
    Returns list of Form 4 open-market transactions within `days` window.
    Fields: date, insider, role, kind, shares, price, owned_after
    kind: BUY | SELL | TAX | AWARD
    """
    try:
        _set_identity()
        import pandas as pd

        company = Company(ticker)
        filings = company.get_filings(form="4")
        if filings is None:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        results: list[dict] = []

        # edgartools returns Filing objects; iterate recent ones
        for filing in filings[:40]:  # cap to avoid rate limit
            try:
                filed_date = filing.filing_date
                if isinstance(filed_date, str):
                    filed_date = datetime.strptime(filed_date[:10], "%Y-%m-%d")
                if filed_date < cutoff:
                    break

                obj = filing.obj()
                if obj is None:
                    continue

                # Iterate non-derivative transactions
                txns = getattr(obj, "transactions", None) or []
                for txn in txns:
                    try:
                        acq_disp = str(getattr(txn, "acquiredDisposedCode", "") or "").upper()
                        txn_code  = str(getattr(txn, "transactionCode", "") or "").upper()

                        # Classify transaction kind
                        if txn_code in ("P",):
                            kind = "BUY"
                        elif txn_code in ("S",):
                            kind = "SELL"
                        elif txn_code in ("F", "W"):
                            kind = "TAX"
                        elif txn_code in ("A", "M", "G"):
                            kind = "AWARD"
                        else:
                            kind = "OTHER"

                        shares = _safe_float(getattr(txn, "shares", 0))
                        price  = _safe_float(getattr(txn, "pricePerShare", 0))

                        reporter = getattr(obj, "reportingOwner", None)
                        insider  = ""
                        role     = ""
                        if reporter:
                            insider = str(getattr(reporter, "name", "") or "")
                            rel     = getattr(reporter, "relationship", None)
                            if rel:
                                roles = []
                                if getattr(rel, "isDirector", False): roles.append("Director")
                                if getattr(rel, "isOfficer", False):
                                    title = getattr(rel, "officerTitle", "") or "Officer"
                                    roles.append(str(title))
                                if getattr(rel, "isTenPercentOwner", False): roles.append("10% Owner")
                                role = ", ".join(roles)

                        owned_after = _safe_float(getattr(txn, "sharesOwnedFollowingTransaction", 0))

                        results.append({
                            "date":        filed_date.strftime("%Y-%m-%d"),
                            "insider":     insider,
                            "role":        role,
                            "kind":        kind,
                            "shares":      shares,
                            "price":       price,
                            "owned_after": owned_after,
                        })
                    except Exception as e:
                        logger.debug("form4 txn parse error: %s", e)
                        continue

            except Exception as e:
                logger.debug("form4 filing parse error: %s", e)
                continue

            time.sleep(0.12)  # ~8 req/s, stay under SEC 10/s limit

        return results

    except Exception as e:
        logger.error("fetch_form4(%s): %s", ticker, e)
        return []


# ---------------------------------------------------------------------------
# 8-K Filings
# ---------------------------------------------------------------------------

_GOING_CONCERN_KEYWORDS = [
    "going concern", "substantial doubt", "ability to continue as a going concern",
    "raise substantial doubt",
]

_AUDITOR_CHANGE_KEYWORDS = [
    "dismissal of", "resigned as", "appointment of", "engagement of",
    "change in registrant's certifying accountant",
]

_GUIDANCE_RAISED_KEYWORDS = [
    "raises guidance", "raised guidance", "raised its outlook", "increased guidance",
    "raised its full-year", "increases its outlook", "raises full year",
]

_GUIDANCE_LOWERED_KEYWORDS = [
    "lowers guidance", "lowered guidance", "lowered its outlook", "reduced guidance",
    "lowered its full-year", "decreases its outlook", "cuts guidance",
]

_CEO_DEPARTURE_KEYWORDS = ["chief executive officer", "president and ceo", "ceo"]
_CFO_DEPARTURE_KEYWORDS = ["chief financial officer", "cfo"]
_DEPARTURE_VERBS       = ["departure", "resign", "stepped down", "will depart", "terminated"]


def _keyword_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _detect_departure(text: str, role_keywords: list[str]) -> bool:
    t = text.lower()
    for role in role_keywords:
        if role in t:
            if _keyword_any(t, _DEPARTURE_VERBS):
                return True
    return False


def fetch_8k(ticker: str, n: int = 10) -> list[dict]:
    """
    Returns list of recent 8-K filing dicts.
    Fields: date, accession, items, description, has_going_concern,
            has_guidance, has_ceo_departure, has_guidance_raised, has_guidance_lowered
    """
    try:
        _set_identity()

        company = Company(ticker)
        filings = company.get_filings(form="8-K")
        if filings is None:
            return []

        results: list[dict] = []

        for filing in filings[:n * 2]:  # overfetch to account for skips
            if len(results) >= n:
                break
            try:
                filed_date = filing.filing_date
                if isinstance(filed_date, str):
                    filed_date = datetime.strptime(filed_date[:10], "%Y-%m-%d")

                accession = str(getattr(filing, "accession_number", "") or "")

                # Try structured items first
                items_list: list[str] = []
                try:
                    items_attr = getattr(filing, "items", None)
                    if items_attr:
                        if isinstance(items_attr, (list, tuple)):
                            items_list = [str(i) for i in items_attr]
                        else:
                            items_list = [str(items_attr)]
                except Exception:
                    pass

                # Get text for keyword fallback
                full_text = ""
                try:
                    obj = filing.obj()
                    if obj is not None:
                        full_text = str(obj) or ""
                except Exception:
                    pass

                # Combine structured items + description for keyword search
                search_text = " ".join(items_list) + " " + full_text

                # --- Boolean flags ---
                # Going concern
                has_going_concern = False
                try:
                    has_going_concern = bool(getattr(filing, "going_concern", False))
                except Exception:
                    pass
                if not has_going_concern:
                    has_going_concern = _keyword_any(search_text, _GOING_CONCERN_KEYWORDS)

                # Auditor change (Item 4.02)
                has_auditor_changed = "4.02" in " ".join(items_list)
                if not has_auditor_changed:
                    has_auditor_changed = _keyword_any(search_text, _AUDITOR_CHANGE_KEYWORDS)

                # Guidance
                has_guidance_raised  = _keyword_any(search_text, _GUIDANCE_RAISED_KEYWORDS)
                has_guidance_lowered = _keyword_any(search_text, _GUIDANCE_LOWERED_KEYWORDS)
                has_guidance         = has_guidance_raised or has_guidance_lowered

                # Executive departures (Item 5.02)
                has_ceo_departure = False
                has_cfo_departure = False
                if "5.02" in " ".join(items_list) or _keyword_any(search_text, _DEPARTURE_VERBS):
                    has_ceo_departure = _detect_departure(search_text, _CEO_DEPARTURE_KEYWORDS)
                    has_cfo_departure = _detect_departure(search_text, _CFO_DEPARTURE_KEYWORDS)

                # Description: first 120 chars of text or items
                description = "; ".join(items_list[:3]) if items_list else full_text[:120].strip()

                results.append({
                    "date":               filed_date.strftime("%Y-%m-%d"),
                    "accession":          accession,
                    "items":              items_list,
                    "description":        description,
                    "has_going_concern":  has_going_concern,
                    "has_guidance":       has_guidance,
                    "has_guidance_raised":  has_guidance_raised,
                    "has_guidance_lowered": has_guidance_lowered,
                    "has_ceo_departure":  has_ceo_departure,
                    "has_cfo_departure":  has_cfo_departure,
                    "has_auditor_changed": has_auditor_changed,
                })

            except Exception as e:
                logger.debug("8k filing parse error: %s", e)
                continue

            time.sleep(0.12)

        return results

    except Exception as e:
        logger.error("fetch_8k(%s): %s", ticker, e)
        return []


# ---------------------------------------------------------------------------
# Financials (annual + quarterly DataFrames)
# ---------------------------------------------------------------------------

def fetch_financials(ticker: str) -> dict:
    """
    Returns dict with keys:
      annual_income, annual_balance, annual_cashflow   (DataFrames)
      quarterly_income, quarterly_balance, quarterly_cashflow  (DataFrames)
    Empty dict on failure.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        return {
            "annual_income":      t.financials,
            "annual_balance":     t.balance_sheet,
            "annual_cashflow":    t.cashflow,
            "quarterly_income":   t.quarterly_financials,
            "quarterly_balance":  t.quarterly_balance_sheet,
            "quarterly_cashflow": t.quarterly_cashflow,
        }
    except Exception as e:
        logger.error("fetch_financials(%s): %s", ticker, e)
        return {}


# ---------------------------------------------------------------------------
# XBRL Facts
# ---------------------------------------------------------------------------

def fetch_xbrl_facts(ticker: str) -> dict:
    """
    Returns dict of key XBRL-derived financial concepts:
      revenue, gross_profit, operating_income, net_income, ebitda,
      total_debt, cash, shares_outstanding, rpo
    Values are floats (most recent annual period). Empty dict on failure.
    """
    try:
        _set_identity()
        import pandas as pd

        company = Company(ticker)
        facts: dict[str, float] = {}

        # Try edgartools XBRL facts API
        try:
            xbrl = company.get_facts()
            if xbrl is not None:
                concept_map = {
                    "Revenues":                          "revenue",
                    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
                    "GrossProfit":                       "gross_profit",
                    "OperatingIncomeLoss":               "operating_income",
                    "NetIncomeLoss":                     "net_income",
                    "CashAndCashEquivalentsAtCarryingValue": "cash",
                    "LongTermDebt":                      "total_debt",
                    "CommonStockSharesOutstanding":      "shares_outstanding",
                    "RevenueRemainingPerformanceObligation": "rpo",
                }
                for concept, key in concept_map.items():
                    if key in facts:
                        continue
                    try:
                        series = xbrl.get_fact(concept)
                        if series is not None and len(series) > 0:
                            # Take most recent annual value
                            annual = series[series.get("form", pd.Series()).isin(["10-K"])] if "form" in series.columns else series
                            if len(annual) > 0:
                                facts[key] = _safe_float(annual.iloc[-1].get("val", annual.iloc[-1].get("value", 0)))
                            else:
                                facts[key] = _safe_float(series.iloc[-1].get("val", series.iloc[-1].get("value", 0)))
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("xbrl facts parse error for %s: %s", ticker, e)

        # Fallback: derive from yfinance financials
        if not facts:
            fin = fetch_financials(ticker)
            ai  = fin.get("annual_income")
            ab  = fin.get("annual_balance")
            ac  = fin.get("annual_cashflow")

            def _get_row(df, *names):
                if df is None: return 0.0
                for n in names:
                    if n in df.index:
                        row = df.loc[n]
                        return _safe_float(row.iloc[0] if hasattr(row, "iloc") else row)
                return 0.0

            facts["revenue"]           = _get_row(ai, "Total Revenue")
            facts["gross_profit"]      = _get_row(ai, "Gross Profit")
            facts["operating_income"]  = _get_row(ai, "Operating Income")
            facts["net_income"]        = _get_row(ai, "Net Income")
            facts["cash"]              = _get_row(ab, "Cash And Cash Equivalents")
            facts["total_debt"]        = _get_row(ab, "Long Term Debt", "Total Debt")
            facts["shares_outstanding"]= _get_row(ab, "Ordinary Shares Number", "Common Stock")
            da = _get_row(ac, "Depreciation And Amortization", "Depreciation")
            facts["ebitda"]            = facts["operating_income"] + da

        return facts

    except Exception as e:
        logger.error("fetch_xbrl_facts(%s): %s", ticker, e)
        return {}


# ---------------------------------------------------------------------------
# Company Info
# ---------------------------------------------------------------------------

def fetch_company_info(ticker: str) -> dict:
    """
    Returns dict: name, sic, industry, exchange, website, description.
    Empty dict on failure.
    """
    try:
        _set_identity()

        company = Company(ticker)
        name     = str(getattr(company, "name", "") or ticker)
        sic      = _safe_int(getattr(company, "sic", 0))
        industry = str(getattr(company, "sic_description", "") or "")
        exchange = str(getattr(company, "exchange", "") or "")
        website  = ""
        desc     = ""

        # Supplement with yfinance for website / description
        try:
            import yfinance as yf
            info    = yf.Ticker(ticker).info or {}
            website = info.get("website", "")
            desc    = info.get("longBusinessSummary", "")[:500]
            if not exchange:
                exchange = info.get("exchange", "")
        except Exception:
            pass

        return {
            "name":        name,
            "sic":         sic,
            "industry":    industry,
            "exchange":    exchange,
            "website":     website,
            "description": desc,
        }

    except Exception as e:
        logger.error("fetch_company_info(%s): %s", ticker, e)
        return {}
