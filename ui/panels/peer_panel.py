"""
PeerPanel — Peer comparison percentile bars.
Phase 4: static placeholder rows. Phase 5: wired to peer_engine data.
"""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from ui.panels.base_panel import BasePanel


_METRICS = [
    ("Rev Growth",    None),
    ("Gross Margin",  None),
    ("FCF Yield",     None),
    ("Debt/EBITDA",   None),
    ("P/E Ratio",     None),
    ("Op. Leverage",  None),
    ("EV/EBITDA",     None),
]


def _bar(percentile: int | None, width: int = 20) -> str:
    if percentile is None:
        return "░" * width + "  —"
    filled = round(percentile / 100 * width)
    empty = width - filled
    color = "green" if percentile >= 67 else ("red" if percentile < 34 else "blue")
    return "█" * filled + "░" * empty + f"  P{percentile}"


class PeerPanel(BasePanel):
    PANEL_TYPE = "PEERS"

    DEFAULT_CSS = """
    PeerPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #peer-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #peer-subheader {
        height: 2;
        padding: 0 1;
        color: #444444;
        border-bottom: solid #1a1a1a;
        content-align: left middle;
    }
    #peer-col-header {
        height: 2;
        layout: horizontal;
        padding: 0 1;
        border-bottom: solid #222222;
        align: left middle;
        color: #555555;
    }
    .peer-col-metric { width: 14; }
    .peer-col-value  { width: 8; }
    .peer-col-bar    { width: 1fr; }
    #peer-scroll {
        height: 1fr;
    }
    .peer-metric-row {
        height: 3;
        layout: horizontal;
        border-bottom: solid #181818;
        padding: 0 1;
        align: left middle;
    }
    .peer-metric-row:hover {
        background: #161616;
    }
    .peer-metric-lbl {
        width: 14;
        color: #888888;
    }
    .peer-metric-val {
        width: 8;
        color: #ffffff;
    }
    .peer-metric-bar {
        width: 1fr;
        color: #333333;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(f"PEERS  {self.ticker}", id="peer-header")
        yield Static(
            "SIC —  ·  Sector: load a ticker",
            id="peer-subheader",
        )
        with VerticalScroll(id="peer-scroll"):
            for label, pct in _METRICS:
                yield Static(
                    f" {label:<13} {'—':>6}   {_bar(pct)}",
                    classes="peer-metric-row peer-metric-lbl",
                )
            yield Static("[ Peer data loads after fetch ]", classes="placeholder")

    def load(self, peer_context=None) -> None:
        """Phase 5: receive PeerContext dataclass."""
        pass
