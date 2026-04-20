"""
MacroPanel — FRED macroeconomic indicators panel.
Phase 4: placeholder rows. Phase 5: wired to macro_fetcher data.
"""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from ui.panels.base_panel import BasePanel


def _gauge(value: float, lo: float, hi: float, width: int = 12) -> str:
    """Render a simple ASCII gauge bar. Value clamped to [lo, hi]."""
    if hi == lo:
        filled = 0
    else:
        pct = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_rate(v: float) -> str:
    return f"{v:.2f}%"


def _fmt_pct(v: float) -> str:
    return f"{v*100:.1f}%"


def _fmt_bps(v: float) -> str:
    return f"{v:+.0f}bp"


def _fmt_vix(v: float) -> str:
    return f"{v:.1f}"


def _fmt_spread(v: float) -> str:
    return f"{v:.0f}bp"


class MacroPanel(BasePanel):
    PANEL_TYPE = "MACRO"

    DEFAULT_CSS = """
    MacroPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #macro-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #macro-col-header {
        height: 2;
        layout: horizontal;
        padding: 0 1;
        border-bottom: solid #222222;
        align: left middle;
        color: #444444;
    }
    #macro-scroll {
        height: 1fr;
    }
    .macro-row {
        height: 3;
        layout: horizontal;
        border-bottom: solid #181818;
        padding: 0 1;
        align: left middle;
    }
    .macro-row:hover {
        background: #161616;
    }
    .macro-lbl {
        width: 16;
        color: #888888;
    }
    .macro-val {
        width: 10;
        color: #ffffff;
        text-align: right;
    }
    .macro-bar {
        width: 1fr;
        color: #333333;
        padding-left: 2;
    }
    .macro-status {
        width: 12;
        color: #555555;
        text-align: right;
    }
    #macro-timestamp {
        height: 2;
        padding: 0 1;
        color: #333333;
        border-top: solid #1a1a1a;
        content-align: left middle;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(f"MACRO  {self.ticker}", id="macro-header")
        with VerticalScroll(id="macro-scroll"):
            yield Static("[ Macro data loads after fetch ]", classes="placeholder")
        yield Static("Last updated: —", id="macro-timestamp")

    def load(self, macro_data: dict | None = None) -> None:
        """Phase 5: receive macro dict and render gauge rows."""
        scroll = self.query_one("#macro-scroll", VerticalScroll)
        timestamp = self.query_one("#macro-timestamp", Static)

        for child in list(scroll.children):
            child.remove()

        if not macro_data:
            scroll.mount(Static("[ No macro data — check FRED API key in config.yaml ]", classes="placeholder"))
            return

        yc = macro_data.get("yield_curve") or {}
        vix = float(macro_data.get("vix") or 0.0)
        cpi = macro_data.get("cpi") or {}
        dxy = macro_data.get("dxy") or {}
        fed = macro_data.get("fed") or {}
        credit = macro_data.get("credit") or {}

        spread = float(yc.get("spread_10y_2y") or 0.0)
        rate10 = float(yc.get("rate_10y") or 0.0)
        rate2  = float(yc.get("rate_2y") or 0.0)
        cpi_yoy = float(cpi.get("latest") or 0.0)
        dxy_chg = float(dxy.get("change_30d") or 0.0)
        fed_rate = float(fed.get("rate") or 0.0)
        fed_cutting = bool(fed.get("cutting"))
        fed_hiking  = bool(fed.get("hiking"))
        hy_spread = float(credit.get("hy_spread") or 0.0)
        hy_chg    = float(credit.get("hy_change_30d") or 0.0)
        ig_spread = float(credit.get("ig_spread") or 0.0)

        # Determine status labels
        if spread < 0:
            yc_status = "[red]INVERTED[/red]"
        elif spread < 0.5:
            yc_status = "[yellow]FLAT[/yellow]"
        else:
            yc_status = "[green]NORMAL[/green]"

        if vix > 30:
            vix_status = "[green]FEAR[/green]"
        elif vix < 15:
            vix_status = "[blue]COMPLACENT[/blue]"
        else:
            vix_status = "NEUTRAL"

        if fed_cutting:
            fed_status = "[green]CUTTING[/green]"
        elif fed_hiking:
            fed_status = "[red]HIKING[/red]"
        else:
            fed_status = "STABLE"

        rows = [
            ("10Y-2Y Spread", f"{spread:+.2f}%",  _gauge(spread, -1.5, 2.0),  yc_status),
            ("10Y Yield",     _fmt_rate(rate10),   _gauge(rate10, 0, 6),        ""),
            ("2Y Yield",      _fmt_rate(rate2),    _gauge(rate2, 0, 6),         ""),
            ("VIX",           _fmt_vix(vix),       _gauge(vix, 10, 50),         vix_status),
            ("CPI YoY",       _fmt_pct(cpi_yoy),   _gauge(cpi_yoy, 0, 0.1),    ""),
            ("DXY Chg 30d",   _fmt_pct(dxy_chg),   _gauge(abs(dxy_chg), 0, 0.1), ""),
            ("Fed Rate",      _fmt_rate(fed_rate),  _gauge(fed_rate, 0, 6),      fed_status),
            ("HY Spread",     _fmt_spread(hy_spread), _gauge(hy_spread, 200, 800), ""),
            ("HY Chg 30d",    _fmt_bps(hy_chg),    _gauge(abs(hy_chg), 0, 150),  ""),
            ("IG Spread",     _fmt_spread(ig_spread), _gauge(ig_spread, 50, 300),  ""),
        ]

        for label, val, bar, status in rows:
            row_text = f" {label:<15} {val:>8}   {bar}   {status}"
            scroll.mount(Static(row_text, classes="macro-row macro-lbl", markup=True))

        from datetime import datetime
        timestamp.update(f"Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}")
