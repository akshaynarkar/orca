"""
FinancialsPanel — Collapsible income statement tree with period toggle.
Phase 4: placeholder rows. Phase 5: wired to edgar_fetcher XBRL data.

Radio toggle uses class-based approach (no fixed string DOM IDs for buttons)
to avoid collisions if multiple instances are mounted.
"""
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.containers import Horizontal, VerticalScroll

from ui.panels.base_panel import BasePanel


_PLACEHOLDER_ROWS = [
    ("Revenue", "$—", "—%", False),
    ("  Cloud Services", "$—", "—%", True),
    ("  Enterprise SW", "$—", "—%", True),
    ("  Other", "$—", "—%", True),
    ("Gross Profit", "$—", "—%", False),
    ("Operating Income", "$—", "—%", False),
    ("Net Income", "$—", "—%", False),
    ("EPS (diluted)", "$—", "—%", False),
]


class FinancialsPanel(BasePanel):
    PANEL_TYPE = "FINANCIALS"

    DEFAULT_CSS = """
    FinancialsPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #fin-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #fin-controls {
        height: 3;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-bottom: solid #1a1a1a;
        background: #0f0f0f;
    }
    #fin-controls Button {
        margin-right: 1;
    }
    #fin-scroll {
        height: 1fr;
    }
    .fin-row-widget {
        height: 2;
        layout: horizontal;
        border-bottom: solid #181818;
        padding: 0 1;
        align: left middle;
    }
    .fin-row-widget:hover {
        background: #161616;
    }
    .fin-lbl {
        width: 1fr;
        color: #4499ff;
    }
    .fin-lbl.child {
        color: #888888;
    }
    .fin-val {
        width: 12;
        color: #44ff88;
        text-align: right;
    }
    .fin-delta {
        width: 8;
        color: #555555;
        text-align: right;
    }
    .fin-placeholder {
        color: #444444;
        padding: 1;
    }
    """

    def __init__(self, ticker: str = "—", **kwargs):
        super().__init__(ticker=ticker, **kwargs)
        self._period = "annual"   # "annual" | "quarterly"

    def _compose_body(self) -> ComposeResult:
        yield Static(f"FINANCIALS  {self.ticker}", id="fin-header")
        with Horizontal(id="fin-controls"):
            yield Button("● Annual", classes="radio-btn selected", id="fin-btn-annual")
            yield Button("○ Quarterly", classes="radio-btn", id="fin-btn-quarterly")
        with VerticalScroll(id="fin-scroll"):
            for label, value, delta, is_child in _PLACEHOLDER_ROWS:
                lbl_class = "fin-lbl child" if is_child else "fin-lbl"
                yield Static(
                    f"{label:<30} {value:>10}   {delta:>6}",
                    classes=f"fin-row-widget {lbl_class}",
                )
            yield Static(
                "[ Financials load after data fetch ]",
                classes="fin-placeholder",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id not in ("fin-btn-annual", "fin-btn-quarterly"):
            return
        event.stop()
        self._set_period("annual" if btn_id == "fin-btn-annual" else "quarterly")

    def _set_period(self, period: str) -> None:
        self._period = period
        annual_btn = self.query_one("#fin-btn-annual", Button)
        qtr_btn = self.query_one("#fin-btn-quarterly", Button)
        if period == "annual":
            annual_btn.label = "● Annual"
            annual_btn.add_class("selected")
            qtr_btn.label = "○ Quarterly"
            qtr_btn.remove_class("selected")
        else:
            annual_btn.label = "○ Annual"
            annual_btn.remove_class("selected")
            qtr_btn.label = "● Quarterly"
            qtr_btn.add_class("selected")

    def load(self, df=None, mode: str = "annual") -> None:
        """Phase 5: receive financials DataFrame and period mode."""
        self._set_period(mode)
