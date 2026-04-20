"""
engine/sic_classifier.py
SIC code utilities: range parsing, Fama-French 48 industry mapping,
and description lookup.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("orca")

# ---------------------------------------------------------------------------
# Fama-French 48 Industry Classification
# SIC ranges → industry label
# ---------------------------------------------------------------------------

_FF48: list[tuple[tuple[int, int], str]] = [
    ((100,   999), "Agriculture"),
    ((1000,  1499), "Mining"),
    ((1500,  1799), "Construction"),
    ((2000,  2099), "Food Products"),
    ((2100,  2199), "Tobacco Products"),
    ((2200,  2299), "Textiles"),
    ((2300,  2399), "Apparel"),
    ((2400,  2499), "Lumber & Wood"),
    ((2500,  2599), "Furniture"),
    ((2600,  2699), "Paper & Paper Products"),
    ((2700,  2799), "Printing & Publishing"),
    ((2800,  2829), "Chemicals"),
    ((2830,  2836), "Pharmaceutical Products"),
    ((2840,  2899), "Soap & Cleaning"),
    ((2900,  2999), "Petroleum & Natural Gas"),
    ((3000,  3099), "Rubber & Plastic Products"),
    ((3100,  3199), "Leather Products"),
    ((3200,  3299), "Stone, Clay, Glass"),
    ((3300,  3399), "Primary Metals"),
    ((3400,  3499), "Fabricated Metals"),
    ((3500,  3559), "Machinery"),
    ((3560,  3579), "Electrical Equipment"),
    ((3580,  3599), "Misc Manufacturing"),
    ((3600,  3674), "Electronic Equipment"),
    ((3675,  3699), "Measuring & Control Equipment"),
    ((3700,  3716), "Automobiles & Trucks"),
    ((3717,  3799), "Aircraft"),
    ((3800,  3879), "Scientific Instruments"),
    ((3880,  3999), "Misc Manufacturing"),
    ((4000,  4099), "Railroad"),
    ((4100,  4299), "Transportation"),
    ((4400,  4499), "Shipping Containers"),
    ((4500,  4599), "Transportation"),
    ((4600,  4799), "Communication"),
    ((4800,  4899), "Communication"),
    ((4900,  4991), "Utilities"),
    ((5000,  5199), "Wholesale"),
    ((5200,  5999), "Retail"),
    ((6000,  6099), "Banking"),
    ((6100,  6299), "Insurance"),
    ((6300,  6499), "Real Estate"),
    ((6500,  6552), "Real Estate"),
    ((6700,  6799), "Finance"),
    ((7000,  7299), "Services"),
    ((7300,  7371), "Business Services"),
    ((7372,  7379), "Computer Software"),
    ((7380,  7999), "Services"),
    ((8000,  8099), "Healthcare"),
    ((8100,  8999), "Services"),
    ((9000,  9999), "Public Administration"),
]

# Simple SIC description map (abbreviated)
_SIC_DESCRIPTIONS: dict[int, str] = {
    1311: "Crude Petroleum & Natural Gas",
    2830: "Drugs",
    2836: "Pharmaceutical Preparations",
    4911: "Electric Services",
    4941: "Water Supply",
    6020: "State Commercial Banks",
    6022: "National Commercial Banks",
    6035: "Savings Institution, Federally Chartered",
    6159: "Federal-Sponsored Credit Agencies",
    6311: "Life Insurance",
    6321: "Accident & Health Insurance",
    6411: "Insurance Agents, Brokers",
    6512: "Operators of Apartment Buildings",
    6552: "Land Subdividers & Developers",
    7370: "Computer Programming, Data Processing",
    7371: "Computer Programming Services",
    7372: "Prepackaged Software",
    7374: "Computer Processing, Data Preparation",
}


def sic_in_range(sic: int, range_str: str) -> bool:
    """
    Returns True if `sic` falls within the range string.
    Accepts "6020-6099" (range) or "1311" (exact).
    Always returns False on parse error.
    """
    try:
        s = str(range_str).strip()
        if "-" in s:
            parts = s.split("-", 1)
            lo, hi = int(parts[0]), int(parts[1])
            return lo <= sic <= hi
        else:
            return sic == int(s)
    except Exception:
        logger.debug("sic_in_range: could not parse range '%s'", range_str)
        return False


def get_fama_french_industry(sic: int) -> str:
    """Map a SIC code to Fama-French 48 industry label."""
    for (lo, hi), label in _FF48:
        if lo <= sic <= hi:
            return label
    return "Other"


def get_sic_description(sic: int) -> str:
    """Return a human-readable SIC description, falling back to FF48 industry."""
    if sic in _SIC_DESCRIPTIONS:
        return _SIC_DESCRIPTIONS[sic]
    return get_fama_french_industry(sic)


def get_sic(ticker: str) -> int:
    """
    Fetch SIC code for a ticker via edgartools Company.
    Returns 0 on failure.
    """
    try:
        from edgar import Company, set_identity
        import yaml, os
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        try:
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            identity = cfg.get("identity", {})
            set_identity(f"{identity.get('name','ORCA')} {identity.get('email','orca@example.com')}")
        except Exception:
            set_identity("ORCA orca@example.com")

        company = Company(ticker)
        sic = getattr(company, "sic", 0)
        return int(sic) if sic else 0
    except Exception as e:
        logger.error("get_sic(%s): %s", ticker, e)
        return 0
