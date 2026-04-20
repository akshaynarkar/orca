"""
engine/signal_report.py
Dataclasses for rules, fired signals, and the full signal report.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Rule:
    """A single GSR rule loaded from rules.yaml."""
    id: str
    name: str
    category: str
    color: str                  # GREEN | RED | BLUE | AMBER | PURPLE
    base_strength: int          # 0–100
    rarity: int                 # 0–100
    condition: str              # Python expression
    description: str
    enabled: bool = True
    sic_overrides: dict = field(default_factory=dict)
    validity_period: int = 30           # days this signal stays active for CMP decay logic

    @property
    def signal_score(self) -> float:
        """Signal Score = (base_strength × 0.6) + (rarity × 0.4)"""
        return round((self.base_strength * 0.6) + (self.rarity * 0.4), 1)

    @property
    def is_composite(self) -> bool:
        return self.category == "composite"


@dataclass
class FiredSignal:
    """A rule that evaluated to True for a given ticker."""
    rule: Rule
    score: float                # computed signal score
    rarity_label: str           # RARE | UNCOMMON | OCCASIONAL | COMMON
    rarity_symbol: str          # ◆ | ◈ | ○ | ·
    result: bool = True         # always True (rule fired)
    notes: str = ""             # optional context


@dataclass
class PeerContext:
    """Peer comparison data for a ticker."""
    ticker: str
    sic: int
    sector_name: str
    fama_french_industry: str
    peer_tickers: list[str]
    peer_count: int
    percentiles: dict           # metric -> percentile (0–100)


@dataclass
class SignalReport:
    """Complete signal report for a ticker after full evaluation."""
    ticker: str
    company_name: str
    price: float
    change_1d: float
    market_cap: float
    sic: int
    sector: str

    fired_signals: list[FiredSignal] = field(default_factory=list)
    orca_score: int = 50
    confidence: float = 0.0
    orca_label: str = "NEUTRAL"  # BULLISH | NEUTRAL | BEARISH

    peer_context: Optional[PeerContext] = None
    price_data: dict = field(default_factory=dict)
    macro_data: dict = field(default_factory=dict)
    financials_data: dict = field(default_factory=dict)

    # Signal counts by color
    green_count: int = 0
    red_count: int = 0
    blue_count: int = 0
    amber_count: int = 0
    purple_count: int = 0

    def to_dict(self) -> dict:
        """Serialize for Claude context builder."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "price": self.price,
            "change_1d": self.change_1d,
            "market_cap": self.market_cap,
            "sic": self.sic,
            "sector": self.sector,
            "orca_score": self.orca_score,
            "confidence": self.confidence,
            "orca_label": self.orca_label,
            "green_count": self.green_count,
            "red_count": self.red_count,
            "amber_count": self.amber_count,
            "blue_count": self.blue_count,
            "purple_count": self.purple_count,
            "signals": [
                {
                    "id": s.rule.id,
                    "name": s.rule.name,
                    "color": s.rule.color,
                    "score": s.score,
                    "rarity": s.rarity_label,
                    "description": s.rule.description,
                }
                for s in self.fired_signals
            ],
            "peer": self.peer_context.percentiles if self.peer_context else {},
            "macro": self.macro_data,
        }

    def summary_string(self) -> str:
        """Short display string for status bar."""
        return (
            f"{self.ticker} · ${self.price:.2f} · "
            f"{'+' if self.change_1d >= 0 else ''}{self.change_1d:.1%} · "
            f"ORCA {self.orca_score}/100 · "
            f"{len(self.fired_signals)} signals"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_report(
    ticker: str,
    company_name: str,
    fired_signals: list,
    peer_context,
    price_data: dict,
    macro_data: dict,
    financials_data: dict,
    sic: int = 0,
    sector: str = "",
) -> "SignalReport":
    """
    Build a complete SignalReport from evaluated signals and fetched data.
    Computes ORCA score, confidence, label, and color counts.
    """
    from engine.score_calculator import (
        compute_confidence,
        compute_orca_score,
        get_orca_label,
    )

    orca_score = compute_orca_score(fired_signals)
    confidence = compute_confidence(fired_signals)
    orca_label = get_orca_label(orca_score)

    green_count  = sum(1 for fs in fired_signals if fs.rule.color == "GREEN")
    red_count    = sum(1 for fs in fired_signals if fs.rule.color == "RED")
    blue_count   = sum(1 for fs in fired_signals if fs.rule.color == "BLUE")
    amber_count  = sum(1 for fs in fired_signals if fs.rule.color == "AMBER")
    purple_count = sum(1 for fs in fired_signals if fs.rule.color == "PURPLE")

    price     = float(price_data.get("price", 0.0))
    prev      = float(price_data.get("prev_close", price))
    change_1d = ((price - prev) / prev) if prev > 0 else 0.0
    mktcap    = float(price_data.get("mktcap", 0.0))

    return SignalReport(
        ticker=ticker,
        company_name=company_name,
        price=round(price, 2),
        change_1d=round(change_1d, 4),
        market_cap=mktcap,
        sic=sic,
        sector=sector,
        fired_signals=fired_signals,
        orca_score=orca_score,
        confidence=confidence,
        orca_label=orca_label,
        peer_context=peer_context,
        price_data=price_data,
        macro_data=macro_data,
        financials_data=financials_data,
        green_count=green_count,
        red_count=red_count,
        blue_count=blue_count,
        amber_count=amber_count,
        purple_count=purple_count,
    )
