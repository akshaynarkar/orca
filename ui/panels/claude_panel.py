"""
ClaudePanel — Claude AI analysis output panel.
Phase 4: static placeholder. Phase 5: Quick/Deep Dive buttons + streaming.
"""
from textual.app import ComposeResult
from textual.widgets import Static, Button, RichLog
from textual.containers import Horizontal, VerticalScroll

from ui.panels.base_panel import BasePanel


class ClaudePanel(BasePanel):
    PANEL_TYPE = "ANALYSIS"

    DEFAULT_CSS = """
    ClaudePanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #claude-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #claude-controls {
        height: 3;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-bottom: solid #1a1a1a;
        background: #0f0f0f;
    }
    #claude-controls Button {
        margin-right: 1;
    }
    #claude-output {
        height: 1fr;
        background: #0f0f0f;
        color: #888888;
        border: none;
        padding: 1;
    }
    #claude-status {
        height: 2;
        padding: 0 1;
        color: #333333;
        border-top: solid #1a1a1a;
        content-align: left middle;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(f"ANALYSIS  {self.ticker}", id="claude-header")
        with Horizontal(id="claude-controls"):
            yield Button("⚡ Quick Scan", id="btn-quick", classes="radio-btn")
            yield Button("🔍 Deep Dive", id="btn-deep", classes="radio-btn")
            yield Button("⟳ Refresh", id="btn-refresh", classes="radio-btn")
        yield RichLog(id="claude-output", markup=True, highlight=True)
        yield Static("—", id="claude-status")

    def on_mount(self) -> None:
        self.show_placeholder()

    def show_placeholder(self) -> None:
        """Display the default placeholder message."""
        output = self.query_one("#claude-output", RichLog)
        output.clear()
        output.write(
            "[dim]Press \\[R] to run analysis[/dim]\n\n"
            "[dim]· Quick Scan  — concise signal summary (~30s)[/dim]\n"
            "[dim]· Deep Dive  — full qualitative analysis (~2m)[/dim]"
        )
        self.query_one("#claude-status", Static).update("No analysis loaded")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("btn-quick", "btn-deep", "btn-refresh"):
            event.stop()
            # Phase 5 will wire these to claude_client

    def load(self, analysis_text: str | None = None, cache_age: str = "") -> None:
        """Phase 5: receive Claude analysis text."""
        if not analysis_text:
            self.show_placeholder()
            return
        output = self.query_one("#claude-output", RichLog)
        output.clear()
        output.write(analysis_text)
        status = f"Analysis cached {cache_age}" if cache_age else "Analysis complete"
        self.query_one("#claude-status", Static).update(status)
