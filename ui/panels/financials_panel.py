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
        """Phase 5: receive financials dict and period mode, render real rows."""
        self._set_period(mode)
        scroll = self.query_one("#fin-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()

        if not df:
            scroll.mount(Static("[ No financial data available ]", classes="fin-placeholder"))
            return

        # Pick annual vs quarterly DataFrames
        if mode == "annual":
            inc = df.get("annual_income")
            bal = df.get("annual_balance")
            cf  = df.get("annual_cashflow")
        else:
            inc = df.get("quarterly_income")
            bal = df.get("quarterly_balance")
            cf  = df.get("quarterly_cashflow")

        def _get(frame, *names) -> float:
            if frame is None or (hasattr(frame, "empty") and frame.empty):
                return 0.0
            for n in names:
                if n in frame.index:
                    row = frame.loc[n]
                    vals = row.dropna() if hasattr(row, "dropna") else row
                    if hasattr(vals, "iloc") and len(vals) > 0:
                        return float(vals.iloc[0])
            return 0.0

        def _get_prev(frame, *names) -> float:
            if frame is None or (hasattr(frame, "empty") and frame.empty):
                return 0.0
            if not hasattr(frame, "columns") or len(frame.columns) < 2:
                return 0.0
            for n in names:
                if n in frame.index:
                    row = frame.loc[n]
                    vals = row.dropna() if hasattr(row, "dropna") else row
                    if hasattr(vals, "iloc") and len(vals) > 1:
                        return float(vals.iloc[1])
            return 0.0

        def _fmt(v: float) -> str:
            if v == 0.0:
                return "$—"
            abs_v = abs(v)
            if abs_v >= 1e12:
                return f"${v/1e12:.2f}T"
            if abs_v >= 1e9:
                return f"${v/1e9:.2f}B"
            if abs_v >= 1e6:
                return f"${v/1e6:.1f}M"
            return f"${v:.0f}"

        def _delta(curr: float, prev: float) -> str:
            if prev == 0 or curr == 0:
                return "—%"
            chg = (curr - prev) / abs(prev)
            return f"{chg:+.1%}"

        rev       = _get(inc, "Total Revenue")
        rev_prev  = _get_prev(inc, "Total Revenue")
        gp        = _get(inc, "Gross Profit")
        gp_prev   = _get_prev(inc, "Gross Profit")
        op        = _get(inc, "Operating Income")
        op_prev   = _get_prev(inc, "Operating Income")
        ni        = _get(inc, "Net Income")
        ni_prev   = _get_prev(inc, "Net Income")
        ocf       = _get(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        ocf_prev  = _get_prev(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex     = abs(_get(cf, "Capital Expenditure", "Capital Expenditures"))
        capex_prev = abs(_get_prev(cf, "Capital Expenditure", "Capital Expenditures"))
        fcf       = ocf - capex
        fcf_prev  = ocf_prev - capex_prev
        cash      = _get(bal, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
        debt      = _get(bal, "Total Debt", "Long Term Debt")

        gm  = f"{gp/rev:.1%}" if rev else "—"
        opm = f"{op/rev:.1%}" if rev else "—"
        npm = f"{ni/rev:.1%}" if rev else "—"

        income_rows = [
            # (label, value_str, delta_str, is_child)
            ("Revenue",          _fmt(rev),  _delta(rev, rev_prev),   False),
            ("Gross Profit",     _fmt(gp),   _delta(gp, gp_prev),     False),
            ("  Gross Margin",   gm,         "",                       True),
            ("Operating Income", _fmt(op),   _delta(op, op_prev),     False),
            ("  Op. Margin",     opm,        "",                       True),
            ("Net Income",       _fmt(ni),   _delta(ni, ni_prev),     False),
            ("  Net Margin",     npm,        "",                       True),
        ]
        cashflow_rows = [
            ("Op. Cash Flow",    _fmt(ocf),  _delta(ocf, ocf_prev),   False),
            ("  CapEx",          _fmt(capex),_delta(capex, capex_prev),True),
            ("Free Cash Flow",   _fmt(fcf),  _delta(fcf, fcf_prev),   False),
        ]
        balance_rows = [
            ("Cash",             _fmt(cash), "",                       False),
            ("Total Debt",       _fmt(debt), "",                       False),
        ]

        all_rows = income_rows + [("─── Cash Flow ───", "", "", False)] + cashflow_rows + \
                   [("─── Balance ─────", "", "", False)] + balance_rows

        for label, val, delta, is_child in all_rows:
            lbl_class = "fin-lbl child" if is_child else "fin-lbl"
            if label.startswith("───"):
                scroll.mount(Static(f" {label}", classes="fin-row-widget fin-placeholder"))
            else:
                scroll.mount(Static(
                    f" {label:<22} {val:>10}   {delta:>7}",
                    classes=f"fin-row-widget {lbl_class}",
                ))
