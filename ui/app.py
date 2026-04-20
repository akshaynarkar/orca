"""
ui/app.py — OrcaApp
Main Textual application class for Project ORCA.
Phase 4: Shell with layout, theme, placeholder panels.
Phase 5: Wired to data fetchers.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Button, Input, Label, Static

from ui.panels import (
    #ClaudePanel,
    EightKPanel,
    FinancialsPanel,
    Form4Panel,
    MacroPanel,
    PeerPanel,
    PricePanel,
    RulesPanel,
    SignalsPanel,
)

# ── Sidebar panel registry ──────────────────────────────────────────────────
# (button_id, label, panel_class, panel_id)
PANELS: list[tuple[str, str, type, str]] = [
    ("btn-sig", "SIG", SignalsPanel,    "panel-sig"),
    ("btn-frm", "FRM", Form4Panel,      "panel-frm"),
    ("btn-8k",  "8·K", EightKPanel,     "panel-8k"),
    ("btn-fin", "FIN", FinancialsPanel, "panel-fin"),
    ("btn-per", "PER", PeerPanel,       "panel-per"),
    ("btn-mac", "MAC", MacroPanel,      "panel-mac"),
    #("btn-ana", "ANA", ClaudePanel,     "panel-ana"),
    ("btn-rul", "RUL", RulesPanel,      "panel-rul"),
]

# Default two panels shown on launch
DEFAULT_LEFT  = "panel-sig"
DEFAULT_RIGHT = "panel-frm"

CSS_PATH = Path(__file__).parent / "theme.css"


class OrcaApp(App):
    """Project ORCA — Opportunity Research & Catalyst Analyzer."""

    CSS_PATH = CSS_PATH
    TITLE = "ORCA"
    SUB_TITLE = "Opportunity Research & Catalyst Analyzer"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q",       "quit",           "Quit",          show=True),
        Binding("ctrl+l",  "focus_search",   "Search",        show=True),
        Binding("r",       "refresh_claude", "Refresh Claude",show=True),
        Binding("e",       "export",         "Export",        show=True),
    ]

    # Reactive ticker drives header label updates
    ticker: reactive[str] = reactive("—")
    dark: reactive[bool]  = reactive(True)

    # Track which panel is in each slot
    _left_panel_id:  str = DEFAULT_LEFT
    _right_panel_id: str = DEFAULT_RIGHT

    # ── Layout ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # ── Topbar ──────────────────────────────────────────────────────────
        with Horizontal(id="topbar"):
            # Left cluster
            with Horizontal(id="topbar-left"):
                yield Input(
                    placeholder="ticker…",
                    id="search-input",
                    value=self._initial_ticker,
                )
                yield Button("LOAD", id="load-btn", classes="load")

            # Center: index ticker placeholder
            yield Static(
                "S&P  ——  ·  NASDAQ  ——  ·  VIX  ——  ·  10Y  ——  ·  DXY  ——",
                id="index-ticker",
            )

            # Right cluster
            with Horizontal(id="topbar-right"):
                yield Button("◐", id="theme-toggle")
                yield Static(
                    datetime.now().strftime("%d%b%y").upper(),
                    id="datetime-label",
                )

        # ── Body ─────────────────────────────────────────────────────────
        with Horizontal(id="body"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static(_logo(), id="logo")
                for btn_id, label, _, _ in PANELS:
                    active = "active" if btn_id in ("btn-sig",) else ""
                    yield Button(label, id=btn_id, classes=f"sidebar-btn {active}".strip())

            # Panel grid (2 columns, 1 row)
            with Horizontal(id="panel-grid"):
                # Instantiate all panels; hide non-default ones
                for btn_id, label, PanelClass, panel_id in PANELS:
                    visible = panel_id in (DEFAULT_LEFT, DEFAULT_RIGHT)
                    panel = PanelClass(
                        ticker=self._initial_ticker,
                        id=panel_id,
                        classes="panel",
                    )
                    if not visible:
                        panel.display = False
                    yield panel

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.ticker = self._initial_ticker
        self._update_status_bar(f"ORCA · {self._initial_ticker} · ready")

    # ── Actions ─────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_refresh_claude(self) -> None:
        """Phase 6: trigger Claude re-analysis."""
        try:
            panel = self.query_one("#panel-ana", ClaudePanel)
            panel.show_placeholder()
        except NoMatches:
            pass

    def action_export(self) -> None:
        """Phase 7: trigger export."""
        self._update_status_bar("Export: not yet implemented (Phase 7)")

    # ── Event handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#load-btn")
    def handle_load(self) -> None:
        ticker = self.query_one("#search-input", Input).value.strip().upper()
        if ticker:
            self._load_ticker(ticker)

    @on(Input.Submitted, "#search-input")
    def handle_search_submit(self, event: Input.Submitted) -> None:
        ticker = event.value.strip().upper()
        if ticker:
            self._load_ticker(ticker)

    @on(Button.Pressed, "#theme-toggle")
    def handle_theme_toggle(self) -> None:
        self.dark = not self.dark
        screen = self.screen
        if self.dark:
            screen.remove_class("-light-mode")
        else:
            screen.add_class("-light-mode")

    @on(Button.Pressed, ".sidebar-btn")
    def handle_sidebar_btn(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        # Find the panel_id for this button
        panel_id = None
        for b_id, _, _, p_id in PANELS:
            if b_id == btn_id:
                panel_id = p_id
                break
        if panel_id is None:
            return

        # Toggle: if clicking active left → do nothing; else swap into right slot
        # Simple strategy: click = set as RIGHT panel, unless it's already left
        if panel_id == self._left_panel_id:
            # Already left — move it to right, show first panel on left
            self._set_panels(PANELS[0][3], panel_id)
        elif panel_id == self._right_panel_id:
            # Already right — swap to left
            self._set_panels(panel_id, self._left_panel_id)
        else:
            # Show in right slot
            self._set_panels(self._left_panel_id, panel_id)

        self._update_sidebar_active(btn_id)

    # ── Panel management ─────────────────────────────────────────────────────

    def _set_panels(self, left_id: str, right_id: str) -> None:
        """Show left_id and right_id panels; hide all others."""
        self._left_panel_id  = left_id
        self._right_panel_id = right_id
        for _, _, _, p_id in PANELS:
            try:
                widget = self.query_one(f"#{p_id}")
                widget.display = p_id in (left_id, right_id)
            except NoMatches:
                pass

    def _update_sidebar_active(self, active_btn_id: str) -> None:
        for btn_id, _, _, panel_id in PANELS:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                if panel_id in (self._left_panel_id, self._right_panel_id):
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except NoMatches:
                pass

    # ── Ticker loading ───────────────────────────────────────────────────────

    def __init__(self, initial_ticker: str = "MSFT", **kwargs):
        super().__init__(**kwargs)
        self._initial_ticker = initial_ticker.upper()
        self._load_gen: int = 0  # generation counter to discard stale fetches

    def _load_ticker(self, ticker: str) -> None:
        """Phase 5: update headers and spawn background fetch."""
        self.ticker = ticker
        self._load_gen += 1
        gen = self._load_gen
        self._update_status_bar(f"Loading {ticker}… (peer data may take up to 60s first run)")
        for _, _, _, panel_id in PANELS:
            try:
                panel = self.query_one(f"#{panel_id}")
                if hasattr(panel, "set_ticker"):
                    panel.set_ticker(ticker)
            except NoMatches:
                pass
        self._fetch_and_populate(ticker, gen)

    @work(thread=True)
    def _fetch_and_populate(self, ticker: str, gen: int) -> None:
        """Background worker: fetch all data in parallel then push to UI thread."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from fetchers.edgar_fetcher import fetch_form4, fetch_8k, fetch_financials, fetch_company_info
        from fetchers.price_fetcher import fetch_ohlcv, fetch_info, fetch_technical, fetch_volume_ratio
        from fetchers.macro_fetcher import (
            fetch_yield_curve, fetch_vix, fetch_cpi,
            fetch_dxy, fetch_fed_rate, fetch_credit_spreads,
        )

        jobs = {
            "form4":      lambda: fetch_form4(ticker),
            "eightk":     lambda: fetch_8k(ticker),
            "financials":  lambda: fetch_financials(ticker),
            "company":    lambda: fetch_company_info(ticker),
            "ohlcv":      lambda: fetch_ohlcv(ticker, period="3mo"),
            "price_info": lambda: fetch_info(ticker),
            "technical":  lambda: fetch_technical(ticker),
            "volume":     lambda: fetch_volume_ratio(ticker),
            "yield_curve":lambda: fetch_yield_curve(),
            "vix":        lambda: fetch_vix(),
            "cpi":        lambda: fetch_cpi(),
            "dxy":        lambda: fetch_dxy(),
            "fed":        lambda: fetch_fed_rate(),
            "credit":     lambda: fetch_credit_spreads(),
        }

        results: dict = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fn): key for key, fn in jobs.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    import logging
                    logging.getLogger("orca").error("fetch %s failed: %s", key, exc)
                    results[key] = {} if key != "vix" else 0.0

        # Signal engine — runs on worker thread after all data arrives
        report = None
        fired = []
        try:
            from engine.rule_loader import RuleLoader
            from engine.rule_evaluator import build_namespace, evaluate_all
            from engine.peer_engine import get_peer_context
            from engine.score_calculator import compute_orca_score, compute_confidence
            from engine.signal_report import build_report
            from engine.sic_classifier import get_sic_description

            company_info = results.get("company") or {}
            sic = int(company_info.get("sic", 0))
            company_name = company_info.get("name", ticker)
            sector = company_info.get("industry", get_sic_description(sic))

            price_info = results.get("price_info") or {}
            financials = results.get("financials") or {}
            ohlcv = results.get("ohlcv")
            technical = results.get("technical") or {}
            volume_ratio = results.get("volume") or 0.0

            # Build peer context (slow on first run — uses SIC)
            subject_metrics = {
                "rev_growth":   price_info.get("rev_growth", 0.0),
                "gross_margin": price_info.get("gross_margin", 0.0),
                "fcf_yield":    0.0,
                "debt_ebitda":  0.0,
                "pe":           price_info.get("pe_ratio", 0.0),
                "op_leverage":  0.0,
                "ev_ebitda":    0.0,
                "pb":           0.0,
                "p_ffo":        0.0,
            }
            peer_ctx = get_peer_context(ticker, sic, subject_metrics) if sic else None

            rules = RuleLoader("rules.yaml").load()

            namespace = build_namespace(
                ticker=ticker,
                form4_data=results.get("form4") or [],
                eightk_data=results.get("eightk") or [],
                financials_data=financials,
                peer_context=peer_ctx,
                price_info=price_info,
                technicals=technical,
                volume_ratio=volume_ratio,
                ohlcv=ohlcv,
                yield_curve=results.get("yield_curve") or {},
                vix=results.get("vix") or 0.0,
                cpi=results.get("cpi") or {},
                dxy=results.get("dxy") or {},
                fed=results.get("fed") or {},
                spreads=results.get("credit") or {},
            )

            fired = evaluate_all(rules, namespace, sic)

            report = build_report(
                ticker=ticker,
                company_name=company_name,
                fired_signals=fired,
                peer_context=peer_ctx,
                price_data=price_info,
                macro_data={
                    "yield_curve": results.get("yield_curve") or {},
                    "vix":         results.get("vix") or 0.0,
                    "cpi":         results.get("cpi") or {},
                    "dxy":         results.get("dxy") or {},
                    "fed":         results.get("fed") or {},
                    "credit":      results.get("credit") or {},
                },
                financials_data=financials,
                sic=sic,
                sector=sector,
            )
        except Exception as exc:
            import logging
            logging.getLogger("orca").error("signal engine failed: %s", exc)

        # Push to UI — must use call_from_thread
        self.app.call_from_thread(self._populate, ticker, results, report, gen)

    def _populate(self, ticker: str, results: dict, report, gen: int) -> None:
        """Called on UI thread after all fetches complete. Discards stale loads."""
        if gen != self._load_gen:
            return  # a newer ticker was requested — discard

        price_info = results.get("price_info") or {}
        macro_data = {
            "yield_curve": results.get("yield_curve") or {},
            "vix":         results.get("vix") or 0.0,
            "cpi":         results.get("cpi") or {},
            "dxy":         results.get("dxy") or {},
            "fed":         results.get("fed") or {},
            "credit":      results.get("credit") or {},
        }

        try:
            self.query_one("#panel-sig", SignalsPanel).load(report)
        except (NoMatches, Exception):
            pass
        try:
            self.query_one("#panel-frm", Form4Panel).load(results.get("form4") or [])
        except (NoMatches, Exception):
            pass
        try:
            self.query_one("#panel-8k", EightKPanel).load(results.get("eightk") or [])
        except (NoMatches, Exception):
            pass
        try:
            self.query_one("#panel-fin", FinancialsPanel).load(
                results.get("financials") or {}, mode="annual"
            )
        except (NoMatches, Exception):
            pass
        try:
            peer_ctx = report.peer_context if report else None
            self.query_one("#panel-per", PeerPanel).load(peer_ctx)
        except (NoMatches, Exception):
            pass
        try:
            self.query_one("#panel-mac", MacroPanel).load(macro_data)
        except (NoMatches, Exception):
            pass
        try:
            self.query_one("#panel-ana", ClaudePanel).show_placeholder()
        except (NoMatches, Exception):
            pass

        # PricePanel is not in PANELS sidebar but may exist if added
        try:
            from ui.panels.price_panel import PricePanel as _PP
            self.query_one("#panel-prc", _PP).load(
                ticker, df=results.get("ohlcv"), info=price_info
            )
        except (NoMatches, Exception):
            pass

        # Update status bar
        n_signals = len(report.fired_signals) if report else 0
        price = price_info.get("price", "—")
        chg = price_info.get("change_1d", None)
        if chg is None and price_info.get("prev_close"):
            prev = price_info.get("prev_close", 0)
            chg = ((price - prev) / prev) if prev and price else 0.0
        chg_str = (f"+{chg:.1%}" if chg >= 0 else f"{chg:.1%}") if isinstance(chg, float) else "—"
        failed = [k for k, v in results.items() if not v]
        warn = f"  ⚠ {', '.join(failed)} unavailable" if failed else ""
        self.sub_title = f"{ticker}  ·  ${price}  {chg_str}  ·  {n_signals} signals{warn}"

    def _update_status_bar(self, message: str) -> None:
        try:
            self.sub_title = message
        except Exception:
            pass


# ── Logo helper ──────────────────────────────────────────────────────────────

def _logo() -> str:
    # E=white, D=green, G=red, R=white — rendered as plain text in TUI
    # Rich markup will style this in Phase 5; for now plain ASCII is sufficient
    return "ED\nGR"
