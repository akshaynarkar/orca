"""
EightKPanel — SEC 8-K filings table.
Phase 4: empty DataTable. Phase 5: wired to edgar_fetcher.
"""
from textual.app import ComposeResult
from textual.widgets import Static, DataTable

from ui.panels.base_panel import BasePanel


class EightKPanel(BasePanel):
    PANEL_TYPE = "8-K"

    DEFAULT_CSS = """
    EightKPanel {
        height: 1fr;
        width: 1fr;
        border: solid #2a2a2a;
        background: #0f0f0f;
    }
    #eightk-header {
        height: 2;
        background: #161616;
        border-bottom: solid #2a2a2a;
        padding: 0 1;
        color: #666666;
        content-align: left middle;
    }
    #eightk-table {
        height: 1fr;
    }
    """

    def _compose_body(self) -> ComposeResult:
        yield Static(f"8-K  {self.ticker}", id="eightk-header")
        table = DataTable(id="eightk-table", zebra_stripes=True)
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#eightk-table", DataTable)
        table.add_columns("Date", "Items", "Description", "Flags")
        table.add_row("—", "—", "Load a ticker to fetch 8-K filings", "—")

    def load(self, eightk_rows: list) -> None:
        """Phase 5: receive list of EightK dicts."""
        table = self.query_one("#eightk-table", DataTable)
        table.clear()
        if not eightk_rows:
            table.add_row("—", "—", "No 8-K filings found", "—")
            return
        for row in eightk_rows:
            flags = []
            if row.get("has_going_concern"):
                flags.append("GC")
            if row.get("has_guidance"):
                flags.append("GUID")
            if row.get("has_ceo_departure"):
                flags.append("CEO↓")
            table.add_row(
                row.get("date", "—"),
                row.get("items", "—"),
                row.get("description", "—")[:60],
                " ".join(flags) or "—",
            )
