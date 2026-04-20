"""
PricePanel — 60-day price bar chart + key stats.
Phase 4: placeholder layout. Phase 5: wired to price_fetcher data.
"""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal, Vertical

from ui.panels.base_panel import BasePanel


class PricePanel(BasePanel):
    PANEL_TYPE = "PRICE"

    def __init__(self, ticker: str = "—", **kwargs):
        super().__init__(ticker=ticker, **kwargs)
        self._df = None    # set by load(); on_show checks this before drawing
        self._info = None

    DEFAULT_CSS = """
    PricePanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #price-stats {
        height: 2;
        layout: horizontal;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        align: left middle;
    }
    .price-stat {
        margin-right: 3;
        color: #888888;
    }
    .price-stat .value {
        color: #ffffff;
    }
    #chart-area {
        height: 1fr;
        content-align: center middle;
        color: #333333;
        padding: 1;
    }
    #sparkline-area {
        height: 3;
        background: #0a0a0a;
        border-top: solid #1a1a1a;
        content-align: center middle;
        color: #333333;
        padding: 0 1;
    }
    #range-bar {
        height: 2;
        layout: horizontal;
        padding: 0 1;
        align: left middle;
        color: #555555;
        border-top: solid #1a1a1a;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(
            f"PRICE  {self.ticker}",
            classes="panel-header panel-type-label",
            id="price-header",
        )
        yield Static(
            "$—.——   —.—%   Vol —   MktCap —",
            id="price-stats",
        )
        yield Static(
            "[ price chart loads after data fetch ]",
            id="chart-area",
        )
        yield Static(
            "[ sparkline ]",
            id="sparkline-area",
        )
        yield Static(
            "52wk  $—  ──────────────────  $—",
            id="range-bar",
        )

    def load(self, ticker: str, df=None, info: dict | None = None) -> None:
        """Phase 5: receive OHLCV DataFrame and price info dict."""
        self.ticker = ticker
        self._df = df
        self._info = info
        try:
            self.query_one("#price-header", Static).update(f"PRICE  {ticker}")
            if info:
                price = info.get("price", "—")
                chg = info.get("change_1d", 0)
                chg_str = f"+{chg:.1%}" if chg >= 0 else f"{chg:.1%}"
                mktcap = info.get("mktcap", "—")
                self.query_one("#price-stats", Static).update(
                    f"${price}   {chg_str}   MktCap {mktcap}"
                )
        except Exception:
            pass
        # If panel is currently visible, draw immediately.
        # If hidden, on_show will draw when panel becomes visible.
        if self.display:
            self._draw()

    def on_show(self) -> None:
        """Called by Textual when panel becomes visible. Redraws chart at correct size."""
        if self._df is not None:
            self._draw()

    def _draw(self) -> None:
        """
        Phase 5: render the plotext bar chart into #chart-area.
        Stub here — Phase 5 will replace with PlotextPlot rendering.
        Called from load() if visible, or from on_show() if was hidden at load time.
        """
        # Phase 5 implementation:
        #   plot = self.query_one("#chart-area", PlotextPlot)
        #   plt = plot.plt
        #   plt.clear_figure()
        #   colors = ["green" if c >= o else "red" for o, c in zip(df["Open"], df["Close"])]
        #   plt.bar(dates, df["Close"].tolist(), color=colors)
        #   plot.refresh()
        pass
