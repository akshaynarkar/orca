"""
SignalsPanel — fired signal flags + ORCA Score block.
Phase 4: static placeholder. Phase 5: wired to SignalReport.
"""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll

from ui.panels.base_panel import BasePanel


_PLACEHOLDER_FLAGS = [
    ("flag-green", "Insider cluster buy", "INS-01", "94%◆"),
    ("flag-blue",  "No data loaded yet", "—",      "—"),
]

_SCORE_PLACEHOLDER = """\
╔══════════════════════════════════════╗
║  ORCA SCORE   ░░░░░░░░░░    —/100   ║
║  Confidence   ░░░░░░░░░░    —%      ║
║  —  ·  — GREEN  ·  — RED  ·  — AMB ║
╚══════════════════════════════════════╝"""


class SignalsPanel(BasePanel):
    PANEL_TYPE = "SIGNALS"

    DEFAULT_CSS = """
    SignalsPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #signals-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #signals-scroll {
        height: 1fr;
        padding: 1;
    }
    .flag {
        height: 3;
        padding: 0 1;
        margin-bottom: 1;
        layout: horizontal;
        align: left middle;
    }
    .flag-name {
        width: 1fr;
    }
    .flag-meta {
        width: 12;
        text-align: right;
        color: #555555;
    }
    #orca-score-block {
        height: 7;
        border: solid #2a2a2a;
        background: #0a0a0a;
        margin: 1;
        padding: 0 1;
        color: #555555;
        content-align: left middle;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(
            f"SIGNALS  {self.ticker}",
            id="signals-header",
        )
        with VerticalScroll(id="signals-scroll"):
            for css_class, name, rule_id, score in _PLACEHOLDER_FLAGS:
                yield Static(
                    f" {name:<36} {rule_id:<8} {score}",
                    classes=f"flag {css_class}",
                )
            yield Static("", classes="placeholder")
        yield Static(_SCORE_PLACEHOLDER, id="orca-score-block")

    def load(self, report=None) -> None:
        """Phase 5: receive SignalReport and render flags."""
        scroll = self.query_one("#signals-scroll", VerticalScroll)
        score_block = self.query_one("#orca-score-block", Static)

        # Clear existing dynamic content (keep the placeholder static)
        for child in list(scroll.children):
            child.remove()

        if not report or not report.fired_signals:
            scroll.mount(Static("No signals fired — load a ticker to scan.", classes="placeholder"))
            score_block.update(_SCORE_PLACEHOLDER)
            return

        # Render one flag widget per fired signal
        for sig in report.fired_signals:
            color = sig.rule.color.lower()
            score_str = f"{sig.score:.0f}%{sig.rarity_symbol}"
            line1 = f" {sig.rule.name:<34} {sig.rule.id:<8} {score_str}"
            line2 = f"  {sig.rule.description[:68]}"
            scroll.mount(Static(f"{line1}\n{line2}", classes=f"flag flag-{color}"))

        # ORCA score bar
        width = 10
        filled = round(report.orca_score / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        conf_filled = round(report.confidence / 100 * width)
        conf_bar = "█" * conf_filled + "░" * (width - conf_filled)
        label = report.orca_label
        g = report.green_count
        r = report.red_count
        a = report.amber_count
        score_block.update(
            f"╔══════════════════════════════════════╗\n"
            f"║  ORCA SCORE   {bar}  {report.orca_score:>3}/100   ║\n"
            f"║  Confidence   {conf_bar}  {report.confidence:>5.1f}%    ║\n"
            f"║  {label:<8}  ·  {g} GREEN  ·  {r} RED  ·  {a} AMB ║\n"
            f"╚══════════════════════════════════════╝"
        )
