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
    ClaudePanel,
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
    ("btn-ana", "ANA", ClaudePanel,     "panel-ana"),
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

    def __init__(self, initial_ticker: str = "MSFT", **kwargs):
        super().__init__(**kwargs)
        self._initial_ticker = initial_ticker.upper()

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

    def _load_ticker(self, ticker: str) -> None:
        """
        Phase 4: update ticker display.
        Phase 5: spawns background thread to fetch all data.
        """
        self.ticker = ticker
        self._update_status_bar(f"Loading {ticker}…")
        # Update all panel headers
        for _, _, _, panel_id in PANELS:
            try:
                panel = self.query_one(f"#{panel_id}")
                if hasattr(panel, "set_ticker"):
                    panel.set_ticker(ticker)
            except NoMatches:
                pass
        self._update_status_bar(f"ORCA · {ticker} · ready  (Phase 5: data not yet wired)")

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
