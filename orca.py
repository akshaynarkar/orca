#!/usr/bin/env python3
"""
orca.py — Project ORCA entry point.

Usage:
    python orca.py MSFT
    python orca.py AAPL
    python orca.py          # defaults to MSFT
"""
import sys
from pathlib import Path

# Ensure project root is on the import path
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import OrcaApp


def main() -> None:
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "MSFT"
    app = OrcaApp(initial_ticker=ticker)
    app.run()


if __name__ == "__main__":
    main()
