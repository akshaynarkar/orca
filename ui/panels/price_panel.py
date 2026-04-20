"""
PricePanel — 60-day price bar chart + key stats.
Phase 4: placeholder layout. Phase 5: wired to price_fetcher data.
"""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal, Vertical

from ui.panels.base_panel import BasePanel

try:
    from textual_plotext import PlotextPlot
    _HAS_PLOTEXT = True
except ImportError:
    _HAS_PLOTEXT = False


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
        if _HAS_PLOTEXT:
            yield PlotextPlot(id="chart-area")
        else:
            yield Static(
                "[ install textual-plotext for price chart ]",
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
        """Render the 60-day bar chart into #chart-area. Called from load() or on_show()."""
        df = self._df
        info = self._info or {}

        # Update 52-week range bar
        try:
            low = info.get("52wk_low", 0)
            high = info.get("52wk_high", 0)
            price = info.get("price", 0)
            if low and high:
                self.query_one("#range-bar", Static).update(
                    f"52wk  ${low:.2f}  {'─' * 16}  ${high:.2f}   now ${price:.2f}"
                )
        except Exception:
            pass

        if df is None or df.empty:
            if not _HAS_PLOTEXT:
                try:
                    self.query_one("#chart-area", Static).update("[ No price data ]")
                except Exception:
                    pass
            return

        if not _HAS_PLOTEXT:
            # ASCII fallback sparkline
            closes = df["Close"].tolist()[-60:]
            lo, hi = min(closes), max(closes)
            rng = hi - lo or 1
            bars = "▁▂▃▄▅▆▇█"
            spark = "".join(bars[round((v - lo) / rng * 7)] for v in closes)
            try:
                self.query_one("#chart-area", Static).update(spark)
            except Exception:
                pass
            return

        # PlotextPlot rendering
        try:
            plot = self.query_one("#chart-area", PlotextPlot)
            plt = plot.plt
            plt.clear_figure()
            plt.theme("dark")

            tail = df.tail(60)
            dates = list(range(len(tail)))
            closes = tail["Close"].tolist()
            opens = tail["Open"].tolist()
            colors = ["green" if c >= o else "red" for o, c in zip(opens, closes)]

            plt.bar(dates, closes, color=colors, width=0.8)
            plt.xfrequency(0)
            plt.title(f"{self.ticker}  60d")
            plt.xlabel("")
            plot.refresh()
        except Exception:
            pass

        # ASCII sparkline in the sparkline widget
        try:
            closes = df["Close"].tolist()[-30:]
            lo, hi = min(closes), max(closes)
            rng = hi - lo or 1
            bars_chars = "▁▂▃▄▅▆▇█"
            spark = "".join(bars_chars[round((v - lo) / rng * 7)] for v in closes)
            self.query_one("#sparkline-area", Static).update(f" 30d  {spark}")
        except Exception:
            pass
