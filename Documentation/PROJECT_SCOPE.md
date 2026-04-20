# PROJECT ORCA — Project Scope
## Opportunity Research & Catalyst Analyzer
*Version 1.0 · April 2026*

---

## 1. Executive Summary

Project ORCA is a local, self-contained equity intelligence terminal built for
an individual investor seeking to capture alpha through disciplined, data-driven
signal detection. It runs entirely inside a terminal emulator — no browser, no
cloud dependency, no subscription fees at runtime.

ORCA combines three data layers — SEC EDGAR filings, live market data, and
macroeconomic indicators — evaluates them against a user-defined ruleset of
Global Scan Rules (GSR), synthesizes the output through Claude AI, and produces
a structured investment signal report exportable as PDF or Excel.

The aesthetic is inspired by Ratatui (Rust TUI framework): dense, monospaced,
information-rich, zero chrome. Built in Python with Textual.

---

## 2. Objectives

| # | Objective |
|---|-----------|
| 1 | Surface high-conviction investment signals from SEC filings in real time |
| 2 | Evaluate signals against sector-aware, user-configurable rules |
| 3 | Benchmark a company against its top 10 EDGAR peers using XBRL data |
| 4 | Score each signal by directional strength AND rarity |
| 5 | Generate a composite ORCA Score (0–100) with a separate Confidence % |
| 6 | Provide qualitative synthesis via Claude Code CLI (no API cost) |
| 7 | Export a formatted investment report as PDF or Excel |
| 8 | Allow the user to add, edit, and refine scan rules over time |

---

## 3. Scope

### 3.1 In Scope

**Data Sources**
- SEC EDGAR via `edgartools`: Form 4 (insider trading), 8-K (material events),
  10-K/10-Q (annual/quarterly filings), 13F (institutional holdings), XBRL
  financial statements, peer universe by SIC code
- Market data via `yfinance`: OHLCV price history, short interest, options data,
  company info, financials
- Macroeconomic data via `FRED API`: yield curve (10Y-2Y spread), VIX, CPI,
  DXY, credit spreads, Fed funds rate
- News headlines via `feedparser`: RSS feeds from SEC, Reuters, Bloomberg

**Signal Engine**
- 40+ Global Scan Rules across 6 categories (Insider, Filing, Fundamental,
  Price/Technical, Macro, Confluence)
- Peer-relative scoring using Fama-French 48 industry classification
- SIC code overrides for sector-specific rule thresholds
- Signal scoring: Base Strength (60%) + Rarity (40%) = Signal Score %
- ORCA Score (0–100) + Confidence % (separate dimensions)

**Terminal UI (Textual)**
- 8 panels: Signals, Form 4, 8-K Filings, Financials, Peer Comparison,
  Macro, Claude Analysis, Rules Editor
- Ratatui-inspired aesthetic: dense, monospaced, block borders
- Mouse-clickable: tabs, collapsible rows, radio buttons, export buttons
- plotext charts: price bar chart (60d), sparklines, gauge bars
- Edgarian color theme throughout

**Claude Integration**
- Claude Code CLI subprocess (uses Claude Pro subscription, no API cost)
- Two modes: Quick Scan (~500 tokens) and Deep Dive (~3,000 tokens)
- Daily cache per ticker — no redundant calls
- User-editable prompt templates

**Export**
- PDF: monospaced Bloomberg-style printout via `reportlab`
- Excel: 6-sheet workbook via `openpyxl`
  (Summary, Signals, Form 4, Financials, Macro, Claude Analysis)

**Rules Management**
- `rules.yaml` — human-readable, user-editable at any time
- Inline rules editor panel in the TUI
- Live reload — changes apply on next scan without restarting

### 3.2 Out of Scope (v1.0)

- Real-time streaming data (WebSocket price feeds)
- Options flow analysis (deferred to v1.1)
- Portfolio tracking / position sizing
- Automated trade execution
- Multi-user / cloud deployment
- Mobile interface
- Non-US equities (ADRs limited support only)

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 · TUI  (Textual + textual-plotext)                     │
│  8 panels · Ratatui aesthetic · Mouse + keyboard                │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2 · DATA FETCHERS  (modular, fail-gracefully)            │
│  edgar_fetcher  │  price_fetcher  │  macro_fetcher  │  news     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3 · SIGNAL ENGINE                                        │
│  rule_loader  │  rule_evaluator  │  signal_report               │
│  peer_engine  │  sic_classifier  │  score_calculator            │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4 · CLAUDE ANALYSIS  (CLI subprocess)                    │
│  context_builder  │  claude_client  │  cache/                   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5 · EXPORT                                               │
│  pdf_exporter  │  excel_exporter                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. File Structure

```
project-orca/
│
├── orca.py                      ← Entry point: python orca.py MSFT
├── config.yaml                  ← API keys, identity, preferences
├── rules.yaml                   ← Global Scan Rules (user-editable)
│
├── docs/
│   ├── PROJECT_SCOPE.md         ← This document
│   ├── THEME.md                 ← Visual design system
│   ├── GSR_RULES.md             ← Global Scan Rules reference
│   └── BUILD_PLAN.md            ← Phase-by-phase build plan
│
├── fetchers/
│   ├── __init__.py
│   ├── edgar_fetcher.py         ← edgartools: 8-K, Form4, 10-K/Q, 13F, XBRL
│   ├── price_fetcher.py         ← yfinance: OHLCV, info, short interest
│   ├── macro_fetcher.py         ← FRED: yield curve, CPI, DXY, VIX
│   └── news_fetcher.py          ← RSS/feedparser: headlines
│
├── engine/
│   ├── __init__.py
│   ├── rule_loader.py           ← Parse + validate rules.yaml
│   ├── rule_evaluator.py        ← Safe eval, SIC override logic
│   ├── peer_engine.py           ← Top-10 peer fetch + XBRL comparison
│   ├── sic_classifier.py        ← Fama-French 48 mapping + SIC ranges
│   ├── score_calculator.py      ← ORCA Score + Confidence % computation
│   └── signal_report.py         ← SignalReport dataclass
│
├── analysis/
│   ├── __init__.py
│   ├── claude_client.py         ← Claude Code CLI subprocess wrapper
│   ├── context_builder.py       ← Minimal context assembly for Claude
│   └── cache/                   ← {ticker}_{date}.json daily cache
│
├── export/
│   ├── __init__.py
│   ├── pdf_exporter.py          ← reportlab: monospaced PDF report
│   └── excel_exporter.py        ← openpyxl: 6-sheet workbook
│
├── ui/
│   ├── __init__.py
│   ├── app.py                   ← EdgarianApp (main Textual App class)
│   ├── theme.css                ← All Textual CSS — Edgarian/Ratatui theme
│   └── panels/
│       ├── __init__.py
│       ├── price_panel.py       ← 60d bar chart + sparkline + key stats
│       ├── signals_panel.py     ← Flag list, ORCA Score, Confidence %
│       ├── form4_panel.py       ← Insider transaction table
│       ├── eightk_panel.py      ← 8-K filings table
│       ├── financials_panel.py  ← Collapsible income tree + radio toggle
│       ├── peer_panel.py        ← Peer comparison percentile bars
│       ├── macro_panel.py       ← FRED gauges + yield curve
│       ├── claude_panel.py      ← Streaming Claude analysis output
│       └── rules_panel.py       ← Inline rules editor
│
├── prompts/
│   ├── quick_scan.txt           ← Claude quick scan prompt template
│   └── deep_dive.txt            ← Claude deep dive prompt template
│
├── tests/
│   ├── test_rule_loader.py
│   ├── test_rule_evaluator.py
│   ├── test_peer_engine.py
│   ├── test_score_calculator.py
│   └── mock_data/               ← Sample signal data for tests
│
└── requirements.txt
```

---

## 6. Technology Stack

| Component | Library | Version | Notes |
|-----------|---------|---------|-------|
| TUI framework | `textual` | ≥0.80 | Ratatui-inspired UI |
| Charts | `textual-plotext` | ≥0.2.1 | ASCII bar/sparkline charts |
| SEC data | `edgartools` | ≥5.28 | EDGAR + XBRL + peer comparison |
| Market data | `yfinance` | ≥0.2 | Price, financials, short interest |
| Macro data | `fredapi` | ≥0.5 | FRED economic indicators |
| News | `feedparser` | ≥6.0 | RSS headline parsing |
| Rule eval | `asteval` | ≥0.9 | Safe sandboxed expression evaluation |
| Config | `PyYAML` | ≥6.0 | rules.yaml + config.yaml parsing |
| Data frames | `pandas` | ≥2.0 | All tabular data manipulation |
| PDF export | `reportlab` | ≥4.0 | Monospaced Bloomberg-style PDF |
| Excel export | `openpyxl` | ≥3.1 | Multi-sheet workbook |
| Claude | Claude Code CLI | latest | `npm install -g @anthropic-ai/claude-code` |
| Python | CPython | 3.11–3.14 | 3.12 recommended for stability |

---

## 7. Data Flow

```
User types: MSFT  →  [LOAD]
                         │
                         ▼
              ┌─────────────────────┐
              │   Parallel fetch    │
              │  (threaded workers) │
              └──────┬──────┬───────┘
                     │      │
           ┌─────────▼──┐  ┌▼──────────┐
           │  EDGAR      │  │  yfinance │
           │  Form4      │  │  Price    │
           │  8-K        │  │  Info     │
           │  10-K/Q     │  │  Short    │
           │  Peers XBRL │  └──────┬────┘
           └──────┬──────┘         │
                  │           ┌────▼─────┐
                  │           │   FRED   │
                  │           │  Macro   │
                  │           └────┬─────┘
                  └────────┬───────┘
                           ▼
                  ┌─────────────────┐
                  │  Rule Evaluator │
                  │  SIC detection  │
                  │  Peer percentiles│
                  │  Score calc     │
                  └────────┬────────┘
                           ▼
                  ┌─────────────────┐
                  │  SignalReport   │
                  │  dataclass      │
                  └────────┬────────┘
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │  TUI      │  │  Claude  │
              │  Panels  │  │  Context │
              └──────────┘  └──────────┘
                                  ▼
                           ┌──────────────┐
                           │ Claude CLI   │
                           │ subprocess   │
                           └──────┬───────┘
                                  ▼
                           ┌──────────────┐
                           │  Export      │
                           │  PDF / Excel │
                           └──────────────┘
```

---

## 8. Signal Scoring System

### 8.1 Per-Signal Score

Each rule carries two intrinsic values set in `rules.yaml`:

```
Signal Score = (base_strength × 0.6) + (rarity × 0.4)
```

- **Base Strength (0–100):** Historical predictive power of this signal type
- **Rarity (0–100):** Inverse frequency — how rarely this fires across ~6,000 stocks

| Rarity Score | Fires in | Label |
|-------------|----------|-------|
| 100 | <0.5% of stocks | ◆ RARE |
| 75 | 0.5–2% of stocks | ◈ UNCOMMON |
| 50 | 2–10% of stocks | ○ OCCASIONAL |
| 25 | >10% of stocks | · COMMON |

### 8.2 ORCA Score (0–100)

Directional composite score weighted by fired signals:

| Color | Weight |
|-------|--------|
| GREEN | +12 per signal |
| RED | −18 per signal (asymmetric — capital preservation) |
| AMBER | −5 per signal |
| BLUE | 0 |
| PURPLE | +6 per signal |
| Composite (CMP) rules | ×2 multiplier |

Score is clamped 0–100, baseline 50 (no signals fired).

### 8.3 Confidence % (separate from ORCA Score)

Weighted average Signal Score of all fired rules.
Answers: *how much should I trust this ORCA Score?*

A score of `81/100` at `83% confidence` (all RARE signals) is very different
from `81/100` at `31% confidence` (all COMMON signals).

---

## 9. Peer Comparison Engine

1. Detect subject company SIC code via `company.sic` (edgartools)
2. Map SIC to Fama-French 48 industry (automatic in edgartools v5.22+)
3. Fetch all companies in same SIC via `get_companies_by_industry(sic=sic)`
4. Filter to NYSE + Nasdaq only, sort by market cap descending
5. Take top 10 by market cap as peer universe
6. Fetch XBRL financials for each peer (cached as Parquet per sector/day)
7. Compute percentile rank for each metric across peer set
8. Expose as `peer.{metric}_percentile` in rule conditions

**Cache strategy:** `cache/peers_{sic}_{date}.parquet`
First run of a sector: ~30–60 seconds. Subsequent: instant.

---

## 10. Claude Integration

### Mode: CLI Subprocess (default)
```python
result = subprocess.run(
    ["claude", "-p", prompt_text, "--output-format", "text"],
    capture_output=True, text=True
)
```
Uses Claude Pro subscription. No API key. No cost beyond subscription.

### Two prompt modes
| Mode | Tokens in | Tokens out | Use |
|------|-----------|-----------|-----|
| Quick Scan | ~800 | ~400 | Summary of fired signals |
| Deep Dive | ~3,000 | ~1,500 | Full qualitative analysis |

### Cache
`analysis/cache/{ticker}_{date}.json`
If today's cache exists → skip CLI call, display cached analysis.
User can force-refresh with `R` key.

---

## 11. Export Formats

### PDF
- Library: `reportlab`
- Font: Courier (monospaced, Bloomberg-style)
- Sections: Header → ORCA Score → Signals → Insider Activity →
  Peer Comparison → Financials → Macro → Claude Analysis → Footnotes
- Filename: `ORCA_{TICKER}_{DATE}.pdf`

### Excel
- Library: `openpyxl`
- 6 sheets: Summary, Signals, Form4, Financials, Macro, Claude
- Conditional formatting: GREEN/RED/AMBER/BLUE/PURPLE cell colors
- Filename: `ORCA_{TICKER}_{DATE}.xlsx`

---

## 12. Version Roadmap

| Version | Focus |
|---------|-------|
| **v1.0** | Core engine: fetchers, rules, scoring, TUI, Claude, export |
| **v1.1** | Options flow panel, earnings whisper, sector rotation signals |
| **v1.2** | Portfolio watchlist (scan multiple tickers), alert system |
| **v1.3** | Biotech/pharma specialist rules (FDA calendar, trial data) |
| **v2.0** | Screener mode: scan entire sector for ORCA Score >70 |

---

*Project ORCA · v1.0 · April 2026 · Confidential*
