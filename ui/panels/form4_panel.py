"""
Form4Panel — Insider Form 4 transaction table.
Phase 4: empty DataTable. Phase 5: wired to edgar_fetcher.
"""
from textual.app import ComposeResult
from textual.widgets import Static, DataTable

from ui.panels.base_panel import BasePanel


class Form4Panel(BasePanel):
    PANEL_TYPE = "FORM 4"

    DEFAULT_CSS = """
    Form4Panel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #form4-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #form4-table {
        height: 1fr;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(f"FORM 4  {self.ticker}", id="form4-header")
        table = DataTable(id="form4-table", zebra_stripes=True)
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#form4-table", DataTable)
        table.add_columns("Date", "Insider", "Role", "Type", "Shares", "Price", "Owned After")
        table.add_row("—", "Load a ticker to fetch insider data", "—", "—", "—", "—", "—")

    def load(self, form4_rows: list) -> None:
        """Phase 5: receive list of Form4Transaction dicts."""
        table = self.query_one("#form4-table", DataTable)
        table.clear()
        if not form4_rows:
            table.add_row("—", "No insider transactions found", "—", "—", "—", "—", "—")
            return
        for row in form4_rows:
            kind = row.get("kind", "—")
            table.add_row(
                row.get("date", "—"),
                row.get("insider", "—"),
                row.get("role", "—"),
                kind,
                str(row.get("shares", "—")),
                f"${row.get('price', '—')}",
                str(row.get("owned_after", "—")),
            )
