"""
RulesPanel — Inline rules editor.
Phase 4: empty DataTable shell. Phase 8: full CRUD implementation.
"""
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, Button
from textual.containers import Horizontal

from ui.panels.base_panel import BasePanel


class RulesPanel(BasePanel):
    PANEL_TYPE = "RULES"

    DEFAULT_CSS = """
    RulesPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #rules-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #rules-controls {
        height: 3;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-bottom: solid #1a1a1a;
    }
    #rules-controls Button {
        margin-right: 1;
    }
    #rules-table {
        height: 1fr;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static("RULES  editor", id="rules-header")
        with Horizontal(id="rules-controls"):
            yield Button("+ Add Rule", id="btn-add-rule", classes="radio-btn")
            yield Button("↺ Reset Defaults", id="btn-reset-rules", classes="radio-btn")
        table = DataTable(id="rules-table", zebra_stripes=True)
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.add_columns("ID", "Name", "Category", "Color", "Score", "Enabled")
        table.add_row("—", "Rules load on first scan", "—", "—", "—", "—")

    def load(self, rules: list | None = None) -> None:
        """Phase 8: receive list of Rule dataclass objects."""
        if not rules:
            return
        table = self.query_one("#rules-table", DataTable)
        table.clear()
        for rule in rules:
            score = round(rule.base_strength * 0.6 + rule.rarity * 0.4)
            table.add_row(
                rule.id,
                rule.name,
                rule.category,
                rule.color,
                f"{score}%",
                "✓" if rule.enabled else "✗",
            )
