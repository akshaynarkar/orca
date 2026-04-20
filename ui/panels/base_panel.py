"""
BasePanel — common superclass for all ORCA panels.
All panels subclass this and override load() in Phase 5.
"""
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult
from textual.containers import Vertical


class BasePanel(Widget):
    """Base class for all ORCA panels."""

    PANEL_TYPE: str = "PANEL"   # e.g. "SIGNALS", "PRICE"
    PANEL_TITLE: str = ""       # set dynamically or overridden

    DEFAULT_CSS = """
    BasePanel {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self, ticker: str = "—", **kwargs):
        super().__init__(**kwargs)
        self.ticker = ticker

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self.PANEL_TYPE}  {self.ticker}",
            classes="panel-header panel-type-label",
        )
        yield from self._compose_body()

    def _compose_body(self) -> ComposeResult:
        """Override in subclasses to provide panel content."""
        yield Static("No content", classes="placeholder panel-body")

    def load(self, *args, **kwargs) -> None:
        """
        Phase 5 entry point.
        Subclasses receive fetcher data here and update their widgets.
        """

    def set_ticker(self, ticker: str) -> None:
        """Update displayed ticker in header."""
        self.ticker = ticker
        try:
            header = self.query_one(".panel-header", Static)
            header.update(f"{self.PANEL_TYPE}  {ticker}")
        except Exception:
            pass
