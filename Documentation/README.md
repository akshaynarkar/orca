# Edgarian — SEC Signal Scanner TUI

Terminal-based stock signal scanner. Dark theme, mouse-clickable, zero LLM tokens at runtime.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python scanner.py MSFT
python scanner.py AAPL
python scanner.py NVDA
```

## Controls

| Key / Action        | Effect                        |
|---------------------|-------------------------------|
| Type ticker + Enter | Load new ticker               |
| Click LOAD          | Load ticker from input        |
| Click SIG/F·4/8·K/FIN sidebar | Switch main panel  |
| Click tab headers   | Switch content tabs           |
| Click ▶ row (FIN)  | Expand/collapse sub-line items|
| Annual / Quarterly  | Toggle financials period      |
| Revenue / Income / Margins | Filter financials view |
| q                   | Quit                          |
| Ctrl+L              | Focus search input            |

## Layout

```
┌─ ED ─────────────────────────────────────────────┐
│ GR  [MSFT   ] [LOAD]              $422  +1.2%    │
├──────┬───────────────────────────────────────────┤
│ SIG  │  ▓▓▓ Price bar chart (60d close) ▓▓▓      │
│ F·4  ├───────────────────────────────────────────┤
│ 8·K  │ [Signals] [Form 4] [8-K] [Financials]     │
│ FIN  │  ▲ INSIDER BUYS (1)                       │
│      │    2026-02-18  Stanton  5,000 @ $397      │
│      │  ▼ INSIDER SELLS (1)                      │
│      │    2026-03-06  Hogan   12,321 @ $409      │
└──────┴───────────────────────────────────────────┘
```

## Data Sources

| Data          | Source             | Cost  |
|---------------|--------------------|-------|
| Price / Info  | yfinance           | Free  |
| Form 4        | SEC EDGAR          | Free  |
| 8-K filings   | SEC EDGAR          | Free  |
| Financials    | yfinance (Yahoo)   | Free  |

No API keys required.

## Future Panels (roadmap)

Add a new tab + fetch function for each:

| Panel              | Data source            | Notes                            |
|--------------------|------------------------|----------------------------------|
| Peer Comparison    | EDGAR XBRL             | Percentile bars vs. sector       |
| Filing Reader      | EDGAR 10-K/10-Q text   | Item 1A, Item 7, diff markers    |
| Insider Clusters   | Form 4 aggregation     | Flag 3+ buys within 30d window   |
| 13F Flow           | EDGAR 13F-HR           | Who's been adding / cutting      |
| Short Interest     | yfinance shortInfo     | Overlay on price chart           |
| Earnings Est.      | yfinance .earnings     | Actual vs. consensus             |
| Options Flow       | yfinance .options      | Put/call ratio, unusual vol      |

Each panel follows the same pattern:
1. Add a fetch function in the `Data fetchers` section
2. Add a new `TabPane` in `compose()`  
3. Add a sidebar nav button
4. Wire up in `_populate()`
