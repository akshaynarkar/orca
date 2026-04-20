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
        pass
