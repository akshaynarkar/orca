"""
Edgarian — SEC Signal Scanner TUI
Usage: python scanner.py [TICKER]
Requires: pip install textual textual-plotext plotext yfinance edgartools
"""

from __future__ import annotations
import sys
import threading
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
import pandas as pd
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    RadioButton, RadioSet, RichLog, Static, TabbedContent, TabPane,
)
from textual.reactive import reactive
from textual_plotext import PlotextPlot

# ── EDGAR (graceful import) ───────────────────────────────────────────────────
try:
    from edgar import Company, set_identity
    set_identity("edgarian scanner scanner@edgarian.app")
    EDGAR_OK = True
except Exception:
    EDGAR_OK = False

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_large(v) -> str:
    try:
        v = float(v)
        if abs(v) >= 1e9:  return f"${v/1e9:.1f}B"
        if abs(v) >= 1e6:  return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"
    except Exception:
        return str(v)

def fmt_pct(v) -> str:
    try:
        return f"{float(v)*100:+.1f}%"
    except Exception:
        return ""

def tag(kind: str) -> str:
    return {"BUY": "[bold green] BUY [/]",
            "SELL": "[bold red] SELL[/]",
            "TAX":  "[dim] TAX [/]",
            "AWARD":"[dim]AWRD [/]"}.get(kind, kind)

def classify_form4(row) -> str:
    code = str(row.get("transaction_code", "")).upper()
    acq  = str(row.get("acquired_disposed", "")).upper()
    if code in ("M", "G", "A"):  return "AWARD"
    if code == "F":               return "TAX"
    if acq == "A":                return "BUY"
    if acq == "D":                return "SELL"
    return "OTHER"

# ── Data fetchers (run in threads) ────────────────────────────────────────────

def fetch_price_data(ticker: str, period: str = "3mo") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()

def fetch_form4(ticker: str, n: int = 25) -> list[dict]:
    if not EDGAR_OK:
        return []
    try:
        co      = Company(ticker)
        filings = co.get_filings(form="4").head(n)
        rows    = []
        for f in filings:
            try:
                obj = f.obj()
                df  = obj.to_dataframe().fillna("")
                for _, r in df.iterrows():
                    rows.append({
                        "date":     str(f.filing_date),
                        "insider":  str(r.get("reporting_owner_name", ""))[:22],
                        "role":     str(r.get("reporting_owner_relationship", ""))[:18],
                        "kind":     classify_form4(r),
                        "shares":   r.get("transaction_shares", ""),
                        "price":    r.get("transaction_price_per_share", ""),
                        "owned":    r.get("shares_owned_after", ""),
                    })
            except Exception:
                continue
        return rows
    except Exception:
        return []

def fetch_8k(ticker: str, n: int = 10) -> list[dict]:
    if not EDGAR_OK:
        return []
    try:
        co      = Company(ticker)
        filings = co.get_filings(form="8-K").head(n)
        rows    = []
        for f in filings:
            try:
                rows.append({
                    "date":   str(f.filing_date),
                    "acc":    f.accession_number,
                    "desc":   str(getattr(f, "description", "") or "")[:60],
                })
            except Exception:
                continue
        return rows
    except Exception:
        return []

def fetch_financials(ticker: str) -> dict:
    """Returns annual and quarterly income statement DataFrames via yfinance."""
    try:
        tk = yf.Ticker(ticker)
        return {
            "annual":    tk.financials,       # columns = fiscal year dates
            "quarterly": tk.quarterly_financials,
        }
    except Exception:
        return {"annual": pd.DataFrame(), "quarterly": pd.DataFrame()}

def fetch_info(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        i  = tk.fast_info
        return {
            "price":  round(float(i.last_price), 2),
            "prev":   round(float(i.previous_close), 2),
            "mktcap": int(i.market_cap),
        }
    except Exception:
        return {}

# ── Financials tree widget ────────────────────────────────────────────────────

INCOME_ROWS = [
    ("Total Revenue",         [], True),
    ("Gross Profit",          ["Cost Of Revenue"], True),
    ("Operating Income",      ["Research And Development",
                               "Selling General Administrative"], True),
    ("Net Income",            ["Interest Expense", "Tax Provision"], True),
    ("EBITDA",                [], True),
]

class FinToggleButton(Button):
    """A financials-row button that carries its label key as an attribute.
    No DOM id needed — avoids DuplicateIds on re-render."""

    def __init__(self, row_label: str, text: str, **kwargs):
        # Never pass id= here — let Textual auto-generate unique ids
        super().__init__(text, classes="fin-row fin-toggle", **kwargs)
        self.row_label = row_label


class FinancialsTree(ScrollableContainer):
    """Collapsible income statement tree."""

    DEFAULT_CSS = """
    FinancialsTree { height: 1fr; border: solid $panel; }
    .fin-header { background: $surface; color: $text-muted; padding: 0 1; }
    .fin-row    { padding: 0 1; }
    .fin-child  { padding: 0 3; color: $text-muted; }
    .fin-toggle { color: $accent; }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data: pd.DataFrame = pd.DataFrame()
        self._cols: list[str]    = []
        self._expanded: set[str] = set()

    def load(self, df: pd.DataFrame) -> None:
        self._data = df
        self._cols = [str(c)[:10] for c in df.columns[:4]]
        self._expanded = set()
        self._render()

    def _build_widgets(self) -> list:
        """Build the full widget list without mounting — avoids duplicate-id race."""
        widgets = []
        if self._data.empty:
            widgets.append(Label("  No data", classes="fin-row"))
            return widgets

        col_hdr = "  ".join(f"{c:>10}" for c in self._cols)
        widgets.append(Label(f"  {'Metric':<28}{col_hdr}", classes="fin-header"))

        for row_label, children, _ in INCOME_ROWS:
            expanded = row_label in self._expanded
            arrow    = "▼" if expanded else "▶"
            vals     = self._get_vals(row_label)
            row_txt  = f"{arrow} {row_label:<26}{vals}"
            widgets.append(FinToggleButton(row_label, row_txt))

            if expanded and children:
                for child in children:
                    cvals = self._get_vals(child)
                    widgets.append(
                        Label(f"  · {child:<24}{cvals}", classes="fin-child")
                    )
        return widgets

    def _render(self) -> None:
        """Remove all children synchronously then mount fresh widgets."""
        # remove_children() schedules removal; calling it + mount() in the same
        # tick causes DuplicateIds.  Use with_lock to batch safely.
        for child in list(self.children):
            child.remove()
        self.mount(*self._build_widgets())

    def _get_vals(self, key: str) -> str:
        parts = []
        for col in self._data.columns[:4]:
            try:
                v = self._data.loc[key, col]
                parts.append(f"{fmt_large(v):>10}")
            except Exception:
                parts.append(f"{'—':>10}")
        return "  ".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Only handle FinToggleButton presses inside this container
        if not isinstance(event.button, FinToggleButton):
            return
        event.stop()
        row_label = event.button.row_label
        if row_label in self._expanded:
            self._expanded.discard(row_label)
        else:
            self._expanded.add(row_label)
        self._render()

# ── Price chart widget ─────────────────────────────────────────────────────────

class PriceChart(PlotextPlot):
    DEFAULT_CSS = "PriceChart { height: 18; border: solid $panel; }"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._df: pd.DataFrame = pd.DataFrame()
        self._ticker: str      = ""

    def load(self, ticker: str, df: pd.DataFrame) -> None:
        self._ticker = ticker
        self._df     = df
        self.refresh()

    def on_mount(self) -> None:
        self._draw()

    def _on_resize(self, event) -> None:
        self._draw()

    def _draw(self) -> None:
        plt = self.plt
        plt.clear_figure()
        if self._df.empty:
            plt.title("No price data")
            return

        df   = self._df.tail(60)
        closes = list(df["Close"].astype(float))
        dates  = [str(d)[:10] for d in df.index]

        # Color each bar green/red vs previous close
        colors = []
        for i, c in enumerate(closes):
            prev = closes[i-1] if i > 0 else c
            colors.append("green" if c >= prev else "red")

        plt.bar(dates, closes, color=colors, width=0.8)
        plt.title(f"{self._ticker} · Close price · {len(closes)}d")
        plt.xlabel("")
        plt.theme("dark")
        plt.xfrequency(max(1, len(dates)//8))
        plt.yfrequency(4)

# ── Signals panel ─────────────────────────────────────────────────────────────

class SignalsPanel(RichLog):
    DEFAULT_CSS = "SignalsPanel { height: 1fr; border: solid $panel; }"

    def load(self, form4_rows: list[dict], info: dict) -> None:
        self.clear()
        price = info.get("price", "—")
        prev  = info.get("prev",  "—")
        mktcap = info.get("mktcap", 0)
        try:
            chg = f"{(price/prev - 1)*100:+.2f}%" if prev else "—"
        except Exception:
            chg = "—"

        self.write(f"[bold]Price[/]  ${price}  {chg}  "
                   f"  MktCap {fmt_large(mktcap)}\n")
        self.write("─" * 60)

        buys  = [r for r in form4_rows if r["kind"] == "BUY"]
        sells = [r for r in form4_rows if r["kind"] == "SELL"]

        if buys:
            self.write(f"\n[bold green]▲ INSIDER BUYS ({len(buys)})[/]")
            for r in buys[:5]:
                try:
                    total = float(r["shares"]) * float(r["price"])
                    self.write(f"  {r['date']}  {r['insider']:<22}  "
                               f"{fmt_large(r['shares'])} sh @ ${r['price']}  "
                               f"= {fmt_large(total)}")
                except Exception:
                    self.write(f"  {r['date']}  {r['insider']}")

        if sells:
            self.write(f"\n[bold red]▼ INSIDER SELLS ({len(sells)})[/]")
            for r in sells[:5]:
                try:
                    total = float(r["shares"]) * float(r["price"])
                    self.write(f"  {r['date']}  {r['insider']:<22}  "
                               f"{fmt_large(r['shares'])} sh @ ${r['price']}  "
                               f"= {fmt_large(total)}")
                except Exception:
                    self.write(f"  {r['date']}  {r['insider']}")

        if not buys and not sells:
            self.write("\n[dim]No open-market buys or sells in recent filings.[/]")

# ── Main App ──────────────────────────────────────────────────────────────────

CSS = """
Screen         { background: #0a0a0a; color: #ffffff; }
Header         { background: #0f0f0f; color: #ffffff; }
Footer         { background: #0f0f0f; color: #555555; }
Input          { background: #161616; border: tall #333333; color: #ffffff; width: 16; }
Button.load    { background: #ffffff; color: #000000; width: 8; }
Button.load:hover { background: #cccccc; }
#topbar        { height: 3; background: #0f0f0f; border-bottom: solid #222222;
                 padding: 0 1; }
#logo          { width: 6; color: #ffffff; padding: 0 1; }
#sidebar       { width: 10; background: #0f0f0f; border-right: solid #222222; }
#sidebar Button { width: 9; background: #0f0f0f; border: none; color: #555555;
                  text-align: center; }
#sidebar Button:hover  { color: #ffffff; }
#sidebar Button.active { color: #ffffff; border-left: solid #ffffff; }
#main          { background: #0a0a0a; }
#radio-row     { height: 3; background: #0f0f0f; border-bottom: solid #222222;
                 padding: 0 1; align: left middle; }
RadioButton    { color: #888888; }
RadioButton:focus { color: #ffffff; }
DataTable      { background: #0f0f0f; border: solid #2a2a2a; height: 1fr; }
DataTable > .datatable--header { background: #161616; color: #888888; }
DataTable > .datatable--cursor { background: #222222; }
TabbedContent  { height: 1fr; }
TabPane        { padding: 0; }
"""

class EdgarianApp(App):
    CSS           = CSS
    TITLE         = "EDGARIAN"
    BINDINGS      = [
        Binding("q",      "quit",         "Quit"),
        Binding("ctrl+l", "focus_search", "Search"),
    ]

    ticker: reactive[str] = reactive("MSFT")
    _period: str          = "3mo"
    _fin_mode: str        = "annual"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="topbar"):
            yield Label("ED\nGR", id="logo")
            yield Input(placeholder="Ticker…", id="search", value=self.ticker)
            yield Button("LOAD", classes="load", id="load-btn")
            yield Label("  ", id="spacer")
            yield Label(id="status-bar")

        with Horizontal():
            # Sidebar nav
            with Vertical(id="sidebar"):
                yield Button("SIG", id="nav-sig", classes="active")
                yield Button("F·4", id="nav-f4")
                yield Button("8·K", id="nav-8k")
                yield Button("FIN", id="nav-fin")

            # Main content
            with Vertical(id="main"):
                yield PriceChart(id="price-chart")

                with TabbedContent(id="tabs"):
                    with TabPane("Signals", id="tab-sig"):
                        yield SignalsPanel(id="signals", highlight=True, markup=True)

                    with TabPane("Form 4", id="tab-f4"):
                        yield DataTable(id="f4-table", zebra_stripes=True)

                    with TabPane("8-K Filings", id="tab-8k"):
                        yield DataTable(id="eightk-table", zebra_stripes=True)

                    with TabPane("Financials", id="tab-fin"):
                        with Horizontal(id="radio-row"):
                            with RadioSet(id="period-radio"):
                                yield RadioButton("Annual",    id="r-annual",    value=True)
                                yield RadioButton("Quarterly", id="r-quarterly")
                            with RadioSet(id="metric-radio"):
                                yield RadioButton("Revenue",   id="r-rev",  value=True)
                                yield RadioButton("Income",    id="r-inc")
                                yield RadioButton("Margins",   id="r-mar")
                        yield FinancialsTree(id="fin-tree")

        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._setup_tables()
        self._load_ticker(self.ticker)

    def _setup_tables(self) -> None:
        f4 = self.query_one("#f4-table", DataTable)
        f4.add_columns("Date", "Kind", "Insider", "Role", "Shares", "Price", "Owned After")

        ek = self.query_one("#eightk-table", DataTable)
        ek.add_columns("Date", "Accession", "Description")

    # ── Interactions ──────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "load-btn":
            inp = self.query_one("#search", Input)
            if inp.value.strip():
                self._load_ticker(inp.value.strip().upper())
        elif btn_id.startswith("nav-"):
            tab_map = {"nav-sig": "tab-sig", "nav-f4": "tab-f4",
                       "nav-8k": "tab-8k",   "nav-fin": "tab-fin"}
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = tab_map.get(btn_id, "tab-sig")
            for b in self.query("#sidebar Button"):
                b.remove_class("active")
            event.button.add_class("active")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search" and event.value.strip():
            self._load_ticker(event.value.strip().upper())

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        radio_id = str(event.pressed.id or "")
        if radio_id in ("r-annual", "r-quarterly"):
            self._fin_mode = "annual" if radio_id == "r-annual" else "quarterly"
            self._refresh_financials()
        elif radio_id in ("r-rev", "r-inc", "r-mar"):
            self._metric_mode = radio_id
            self._refresh_financials()

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Label).update(msg)

    def _load_ticker(self, ticker: str) -> None:
        self.ticker = ticker
        self._set_status(f"[yellow]Loading {ticker}…[/]")
        self._fin_data: dict = {}

        def worker():
            price_df  = fetch_price_data(ticker)
            form4_rows = fetch_form4(ticker)
            eightk_rows = fetch_8k(ticker)
            fin_data   = fetch_financials(ticker)
            info       = fetch_info(ticker)
            self.call_from_thread(
                self._populate, ticker, price_df, form4_rows, eightk_rows, fin_data, info
            )

        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, ticker, price_df, form4_rows, eightk_rows, fin_data, info):
        self._fin_data = fin_data

        # Price chart
        chart = self.query_one("#price-chart", PriceChart)
        chart.load(ticker, price_df)
        chart._draw()

        # Signals
        sig = self.query_one("#signals", SignalsPanel)
        sig.load(form4_rows, info)

        # Form 4 table
        f4 = self.query_one("#f4-table", DataTable)
        f4.clear()
        kind_style = {"BUY": "[bold green]BUY[/]", "SELL": "[bold red]SELL[/]",
                      "TAX": "[dim]TAX[/]", "AWARD": "[dim]AWRD[/]"}
        for r in form4_rows:
            try:  shares = f"{float(r['shares']):,.0f}"
            except Exception: shares = str(r["shares"])
            try:  price = f"${float(r['price']):.2f}"
            except Exception: price = str(r["price"])
            try:  owned = f"{float(r['owned']):,.0f}"
            except Exception: owned = str(r["owned"])
            f4.add_row(
                r["date"], kind_style.get(r["kind"], r["kind"]),
                r["insider"], r["role"], shares, price, owned
            )

        # 8-K table
        ek = self.query_one("#eightk-table", DataTable)
        ek.clear()
        for r in eightk_rows:
            ek.add_row(r["date"], r["acc"], r["desc"])

        # Financials
        self._refresh_financials()

        price = info.get("price", "—")
        try:
            chg = f"{(info['price']/info['prev']-1)*100:+.2f}%"
            color = "green" if info["price"] >= info["prev"] else "red"
            self._set_status(f"[bold]{ticker}[/]  [bold {color}]${price}  {chg}[/]")
        except Exception:
            self._set_status(f"[bold]{ticker}[/]  ${price}")

    def _refresh_financials(self) -> None:
        if not self._fin_data:
            return
        df = self._fin_data.get(self._fin_mode, pd.DataFrame())
        tree = self.query_one("#fin-tree", FinancialsTree)
        tree.load(df)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "MSFT"
    app    = EdgarianApp()
    app.ticker = ticker
    app.run()
