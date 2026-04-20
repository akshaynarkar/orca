"""ui/panels — all ORCA panel widgets."""
from ui.panels.signals_panel import SignalsPanel
from ui.panels.form4_panel import Form4Panel
from ui.panels.eightk_panel import EightKPanel
from ui.panels.financials_panel import FinancialsPanel
from ui.panels.peer_panel import PeerPanel
from ui.panels.macro_panel import MacroPanel
#from ui.panels.claude_panel import ClaudePanel
from ui.panels.rules_panel import RulesPanel
from ui.panels.price_panel import PricePanel

__all__ = [
    "SignalsPanel",
    "Form4Panel",
    "EightKPanel",
    "FinancialsPanel",
    "PeerPanel",
    "MacroPanel",
    "ClaudePanel",
    "RulesPanel",
    "PricePanel",
]
