# PROJECT ORCA — Build Plan
## Phase-by-Phase Development Roadmap
*Version 1.0 · April 2026*

---

## Overview

Project ORCA is built in 8 sequential phases. Each phase is fully tested
before the next begins. No phase skips. No premature UI work before data
foundations are solid.

**Estimated total:** ~40–60 hours of development across all phases
**Stack:** Python 3.12+ · Textual · edgartools · yfinance · fredapi · reportlab · openpyxl

---

## Phase 0 — Environment & Prerequisites
*Estimated time: 1–2 hours*

### Goals
Verify all dependencies are installed and working before writing a line of ORCA code.

### Checklist

**Python environment**
- [ ] Python 3.12 recommended (3.14 supported but may have edge cases)
- [ ] Virtual environment created: `python -m venv .venv`
- [ ] `requirements.txt` installed: `pip install -r requirements.txt`

**Claude Code CLI**
- [ ] Node.js installed (v18+)
- [ ] Claude Code installed: `npm install -g @anthropic-ai/claude-code`
- [ ] Verify: `claude --version`
- [ ] Verify non-interactive mode: `echo "say hello" | claude -p "say hello" --output-format text`

**API Keys**
- [ ] FRED API key obtained from fred.stlouisfed.org
- [ ] FRED key added to `config.yaml`
- [ ] SEC identity set (name + email, required by edgartools)

**Network test**
- [ ] `python -c "from edgar import Company, set_identity; set_identity('name email'); c = Company('MSFT'); print(c.name)"`
- [ ] `python -c "import yfinance as yf; t = yf.Ticker('MSFT'); print(t.fast_info.last_price)"`
- [ ] `python -c "from fredapi import Fred; f = Fred(api_key='YOUR_KEY'); print(f.get_series('DGS10').iloc[-1])"`

### Deliverables
- `requirements.txt`
- `config.yaml` (with FRED key, SEC identity, Claude mode)
- `README.md` (setup instructions)

---

## Phase 1 — Project Scaffold + Config + Rules Schema
*Estimated time: 3–4 hours*

### Goals
Create the full folder structure, `config.yaml`, and `rules.yaml` with all
40+ GSR rules. Validate that rules load and parse correctly.

### Tasks

**Folder structure**
- [ ] Create all directories per PROJECT_SCOPE.md §5
- [ ] Create `__init__.py` in all Python packages

**config.yaml**
```yaml
identity:
  name: "Your Name"
  email: "your.email@example.com"

fred:
  api_key: "YOUR_FRED_KEY"

claude:
  mode: cli                    # "cli" or "api"
  api_key: ""                  # only if mode: api
  model: sonnet                # sonnet | haiku | opus
  cache_days: 1                # reuse cached analysis for N days

peers:
  max_peers: 10                # top N peers by market cap
  exchanges: ["NYSE", "Nasdaq"]
  cache_days: 1

ui:
  default_ticker: "MSFT"
  font_size: 13
  theme: dark                  # dark | light

export:
  output_dir: "./reports"
  pdf_font: Courier
  include_raw_data: true
```

**rules.yaml**
- [ ] Complete rules.yaml with all 40+ rules from GSR_RULES.md
- [ ] Validate YAML parses without errors

**engine/rule_loader.py**
- [ ] `RuleLoader` class: loads and validates `rules.yaml`
- [ ] Validates required fields: `id`, `name`, `category`, `color`, `condition`
- [ ] Validates color values: GREEN | RED | BLUE | AMBER | PURPLE
- [ ] Validates SIC override format
- [ ] Returns list of `Rule` dataclass objects

**engine/signal_report.py**
- [ ] `Rule` dataclass
- [ ] `FiredSignal` dataclass (rule + result + score)
- [ ] `SignalReport` dataclass (all fired signals + ORCA score + confidence)

### Tests
- [ ] `test_rule_loader.py`: rules.yaml loads without errors
- [ ] `test_rule_loader.py`: all 40+ rules present and valid
- [ ] `test_rule_loader.py`: invalid color raises ValueError
- [ ] `test_rule_loader.py`: SIC override parses correctly

### Deliverables
- `config.yaml`
- `rules.yaml` (complete)
- `engine/rule_loader.py`
- `engine/signal_report.py`
- `tests/test_rule_loader.py`

---

## Phase 2 — Data Fetchers
*Estimated time: 6–8 hours*

### Goals
Build all four data fetchers. Each must fail gracefully — network errors,
missing data, and rate limits must never crash the application.

### Tasks

**fetchers/edgar_fetcher.py**
- [ ] `fetch_form4(ticker, days=60)` → list of Form4Transaction dicts
  - Open-market buys/sells only (exclude tax withholdings, awards)
  - Fields: date, insider, role, kind (BUY/SELL/TAX/AWARD), shares, price, owned_after
- [ ] `fetch_8k(ticker, n=10)` → list of EightK dicts
  - Fields: date, accession, items, description, has_going_concern, has_guidance, has_ceo_departure
- [ ] `fetch_financials(ticker)` → dict with annual + quarterly DataFrames
- [ ] `fetch_xbrl_facts(ticker)` → dict of key XBRL concepts
  - Revenue, gross profit, operating income, net income, EBITDA
  - Total debt, cash, shares outstanding
  - RPO (commercial remaining performance obligation)
- [ ] `fetch_company_info(ticker)` → dict: name, SIC, industry, exchange, website

**fetchers/price_fetcher.py**
- [ ] `fetch_ohlcv(ticker, period="3mo")` → DataFrame
- [ ] `fetch_info(ticker)` → dict: price, prev_close, mktcap, 52wk_high, 52wk_low
- [ ] `fetch_technical(ticker)` → dict: above_200d_ma, golden_cross, death_cross, short_float
- [ ] `fetch_volume_ratio(ticker)` → float: today volume / 30d avg

**fetchers/macro_fetcher.py**
- [ ] `fetch_yield_curve()` → dict: spread_10y_2y, rate_10y, rate_2y
- [ ] `fetch_vix()` → float
- [ ] `fetch_cpi()` → dict: latest, estimate, surprise
- [ ] `fetch_dxy()` → dict: current, change_30d
- [ ] `fetch_fed_rate()` → dict: rate, cutting, hiking
- [ ] `fetch_credit_spreads()` → dict: hy_spread, hy_change_30d, ig_spread

**fetchers/news_fetcher.py**
- [ ] `fetch_headlines(ticker, n=5)` → list of headline dicts
  - Fields: date, title, source, url

### Error handling requirements
- All functions return empty dict/list (never None) on failure
- All functions log errors to `orca.log`, never raise to caller
- Timeout: 10 seconds per request
- Rate limit: respect SEC's 10 req/sec limit

### Tests
- [ ] Each fetcher tested with mock data (monkeypatch requests)
- [ ] Each fetcher returns correct type on success
- [ ] Each fetcher returns empty result on network failure
- [ ] Each fetcher returns empty result on 404/403

### Deliverables
- `fetchers/edgar_fetcher.py`
- `fetchers/price_fetcher.py`
- `fetchers/macro_fetcher.py`
- `fetchers/news_fetcher.py`
- `tests/test_fetchers.py`

---

## Phase 3 — Signal Engine
*Estimated time: 6–8 hours*

### Goals
Build the rule evaluator, peer engine, and score calculator. This is the
analytical core of ORCA.

### Tasks

**engine/sic_classifier.py**
- [ ] `get_sic(ticker)` → int
- [ ] `get_fama_french_industry(sic)` → str
- [ ] `sic_in_range(sic, range_str)` → bool (parses "6020-6099" format)
- [ ] `get_sic_description(sic)` → str

**engine/peer_engine.py**
- [ ] `get_peers(ticker, max_peers=10)` → list of peer tickers
  - Fetch companies by SIC, filter to NYSE+Nasdaq, sort by mktcap, take top 10
  - Cache result as `cache/peers_{sic}_{date}.parquet`
- [ ] `compute_peer_percentiles(ticker, peers)` → dict of percentile scores
  - Metrics: rev_growth, gross_margin, fcf_yield, debt_ebitda, pe, op_leverage, ev_ebitda, pb, p_ffo
  - Returns peer.{metric}_percentile for each metric (0–100)
- [ ] `get_peer_context(ticker)` → PeerContext dataclass

**engine/rule_evaluator.py**
- [ ] `build_namespace(ticker, form4_data, filing_data, financials_data, peer_data, price_data, macro_data)` → dict
  - Assembles the complete evaluation namespace from all fetcher outputs
  - All variables listed in GSR_RULES.md §2
- [ ] `evaluate_rule(rule, namespace)` → FiredSignal | None
  - Safe evaluation using `asteval` (sandboxed, no builtins)
  - Applies SIC override logic before evaluation
  - Returns None if rule disabled or skipped by SIC override
- [ ] `evaluate_all(rules, namespace)` → list[FiredSignal]
- [ ] `apply_sic_override(rule, sic)` → Rule | None

**engine/score_calculator.py**
- [ ] `compute_signal_score(rule)` → float
  - `(base_strength × 0.6) + (rarity × 0.4)`
- [ ] `classify_rarity(rarity_score)` → tuple[str, str]
  - Returns (label, symbol): ("RARE", "◆"), ("UNCOMMON", "◈"), etc.
- [ ] `compute_orca_score(fired_signals)` → int (0–100)
  - GREEN: +12, RED: -18, AMBER: -5, BLUE: 0, PURPLE: +6
  - CMP rules: ×2 multiplier
  - Clamp to 0–100, baseline 50
- [ ] `compute_confidence(fired_signals)` → float (0–100)
  - Weighted average signal score of all fired rules
- [ ] `get_orca_label(score)` → str
  - >65: "BULLISH", 35–65: "NEUTRAL", <35: "BEARISH"

**engine/signal_report.py** (extend from Phase 1)
- [ ] `build_report(ticker, fired_signals, peer_context, price_data, macro_data)` → SignalReport
- [ ] `SignalReport.to_dict()` → dict (for Claude context builder)
- [ ] `SignalReport.summary_string()` → str (for display)

### Tests
- [ ] `test_rule_evaluator.py`: INS-01 fires correctly on mock data
- [ ] `test_rule_evaluator.py`: SIC override skips FUN-06 for utility SIC
- [ ] `test_rule_evaluator.py`: CMP-01 fires when all three base rules fire
- [ ] `test_score_calculator.py`: ORCA score calculation correct
- [ ] `test_score_calculator.py`: score clamped 0–100
- [ ] `test_peer_engine.py`: percentile computation correct on 10-company mock set

### Deliverables
- `engine/sic_classifier.py`
- `engine/peer_engine.py`
- `engine/rule_evaluator.py`
- `engine/score_calculator.py`
- `engine/signal_report.py` (updated)
- `tests/test_rule_evaluator.py`
- `tests/test_score_calculator.py`
- `tests/test_peer_engine.py`

---

## Phase 4 — TUI Shell
*Estimated time: 6–8 hours*

### Goals
Build the Textual application with correct layout, theme, and empty panels.
No live data yet — panels display placeholder content.

### Tasks

**ui/theme.css**
- [ ] Full Edgarian/Ratatui theme as specified in THEME.md
- [ ] All signal flag classes: `.flag-green`, `.flag-red`, `.flag-blue`, `.flag-amber`, `.flag-purple`
- [ ] No border-radius anywhere (Ratatui rule)
- [ ] Light/dark mode via Textual's reactive dark property

**ui/app.py**
- [ ] `OrcaApp(App)` class
- [ ] Topbar: logo, search, LOAD, index ticker, controls
- [ ] Side menu: 8 panel toggle buttons with 3-char labels
- [ ] Main area: panel grid (default 2-column)
- [ ] Footer: key bindings display
- [ ] Key bindings: `q` quit, `Ctrl+L` focus search, `r` refresh Claude, `e` export

**ui/panels/** (all empty/placeholder)
- [ ] `price_panel.py` — PricePanel (empty chart frame)
- [ ] `signals_panel.py` — SignalsPanel (empty flag list)
- [ ] `form4_panel.py` — Form4Panel (empty table)
- [ ] `eightk_panel.py` — EightKPanel (empty table)
- [ ] `financials_panel.py` — FinancialsPanel (empty tree)
- [ ] `peer_panel.py` — PeerPanel (empty percentile bars)
- [ ] `macro_panel.py` — MacroPanel (empty gauges)
- [ ] `claude_panel.py` — ClaudePanel (empty text area)
- [ ] `rules_panel.py` — RulesPanel (empty list)

### Tests
- [ ] App launches without errors: `python orca.py MSFT`
- [ ] All 8 panels visible and switchable
- [ ] Light/dark toggle works
- [ ] Search input focuses on Ctrl+L
- [ ] Quit on `q`

### Deliverables
- `ui/app.py`
- `ui/theme.css`
- `ui/panels/*.py` (all 9 files)

---

## Phase 5 — Wire Panels to Data
*Estimated time: 8–10 hours*

### Goals
Connect each panel to its data source. Load ticker → fetch data in background
thread → populate all panels simultaneously.

### Tasks

**Loading flow**
- [ ] `OrcaApp._load_ticker(ticker)` → spawns background thread
- [ ] Thread runs all fetchers in parallel (ThreadPoolExecutor, max_workers=4)
- [ ] On completion, calls `app.call_from_thread(self._populate, data)`
- [ ] Status bar shows: "Loading MSFT..." → "MSFT · $422 · +1.2% · 5 signals"
- [ ] Graceful partial load: show available data even if one fetcher fails

**Panel data wiring**
- [ ] `PricePanel.load(ticker, df, info)` → renders 60d bar chart + stats
- [ ] `SignalsPanel.load(report)` → renders flag list + ORCA score block
- [ ] `Form4Panel.load(form4_rows)` → renders DataTable with color coding
- [ ] `EightKPanel.load(eightk_rows)` → renders DataTable
- [ ] `FinancialsPanel.load(df, mode)` → renders collapsible tree
- [ ] `PeerPanel.load(peer_context)` → renders percentile bar rows
- [ ] `MacroPanel.load(macro_data)` → renders gauge rows
- [ ] `ClaudePanel.show_placeholder()` → "Press [R] to run analysis"

**Charts (textual-plotext)**
- [ ] 60-day price bar chart: green bars = up days, red bars = down days
- [ ] Sparkline below main chart
- [ ] Peer comparison percentile bars (horizontal, ASCII)
- [ ] Macro gauge bars

**FinancialsPanel**
- [ ] Fix the `FinToggleButton` pattern from earlier (no DOM ID collisions)
- [ ] Annual / Quarterly radio toggle
- [ ] Expand/collapse sub-line items on click
- [ ] Correct `on_mount` placeholder (no NoneType crash)

### Tests
- [ ] Full load cycle with mock data completes without errors
- [ ] Each panel displays expected content
- [ ] Switching tickers clears and reloads all panels
- [ ] One fetcher failure does not block other panels

### Deliverables
- Updated `ui/app.py` with full load/populate flow
- Updated all panel files with `load()` methods

---

## Phase 6 — Claude Analysis Integration
*Estimated time: 4–5 hours*

### Goals
Wire Claude Code CLI to the analysis panel. Build the context assembler
that feeds structured, token-efficient input to Claude.

### Tasks

**analysis/context_builder.py**
- [ ] `build_quick_context(report)` → str (≤800 tokens)
  - Fired signals only, key metrics, ticker + price
- [ ] `build_deep_context(report)` → str (≤3000 tokens)
  - All signals, peer data, macro, recent 8-K titles, financial highlights

**analysis/claude_client.py**
- [ ] `run_quick_scan(ticker, context)` → str
  - `subprocess.run(["claude", "-p", prompt, "--output-format", "text"])`
  - Timeout: 30 seconds
- [ ] `run_deep_dive(ticker, context)` → str
  - Timeout: 120 seconds
- [ ] `get_cached(ticker)` → str | None
  - Check `analysis/cache/{ticker}_{date}.json`
- [ ] `save_cache(ticker, result)` → None
- [ ] Full flow: check cache → build context → run CLI → save cache → return

**prompts/quick_scan.txt**
```
You are a senior equity analyst. A signal scanner has fired the following
signals for {ticker} ({company_name}).

PRICE: ${price} ({change_1d}) | MktCap: {mktcap}
SECTOR: {sector} (SIC {sic})
ORCA SCORE: {orca_score}/100 | Confidence: {confidence}%

FIRED SIGNALS:
{signals_list}

KEY METRICS vs PEERS:
{peer_metrics}

In 3-4 sentences, provide a concise qualitative assessment of what these
signals collectively suggest about {ticker}'s near-term investment merit.
Be direct. State a bias (bullish/bearish/neutral) and your primary reason.
```

**prompts/deep_dive.txt**
```
You are a senior equity analyst conducting a deep-dive signal analysis.

[full structured context]

Provide a structured analysis covering:
1. Signal Quality: Which fired signals are most meaningful and why
2. Risk Factors: What the RED/AMBER signals imply
3. Peer Context: How the company compares vs sector
4. Macro Overlay: How the current macro environment affects this name
5. Investment Bias: Bullish / Bearish / Neutral with specific reasoning
6. Key Catalyst: What single event would most likely confirm or invalidate this thesis

Keep each section to 2-3 sentences. Total: ~400 words.
```

**ui/panels/claude_panel.py** (update)
- [ ] [Quick] and [Deep Dive] buttons
- [ ] [⟳ Refresh] button clears cache and re-runs
- [ ] Streaming output display (RichLog with markup=True)
- [ ] Shows cache age: "Analysis from 2h ago · [⟳ Refresh]"

### Tests
- [ ] Mock Claude CLI: `subprocess.run` patched to return test response
- [ ] Cache saves and loads correctly
- [ ] Expired cache (>1 day) triggers new CLI call
- [ ] Timeout handled gracefully (shows error in panel)

### Deliverables
- `analysis/context_builder.py`
- `analysis/claude_client.py`
- `prompts/quick_scan.txt`
- `prompts/deep_dive.txt`
- Updated `ui/panels/claude_panel.py`

---

## Phase 7 — Export
*Estimated time: 4–5 hours*

### Goals
Build PDF and Excel exporters that produce professional, well-formatted
reports from a `SignalReport`.

### Tasks

**export/pdf_exporter.py**
- [ ] `export_pdf(report, filepath)` → None
- [ ] Font: Courier 10pt (monospaced Bloomberg-style)
- [ ] Sections (in order):
  1. Header: ORCA logo + ticker + date + ORCA Score
  2. Signal Summary: all fired signals with color indicators
  3. Insider Activity: Form 4 transaction table
  4. Peer Comparison: metric percentile table
  5. Financials: income statement highlights
  6. Macro: key macro indicators
  7. Claude Analysis: full text
  8. Footnotes: data sources, disclaimer
- [ ] Color indicators rendered as text symbols (● = colored dot via Unicode)
- [ ] Filename: `ORCA_{TICKER}_{DATE}.pdf`

**export/excel_exporter.py**
- [ ] `export_excel(report, filepath)` → None
- [ ] 6 sheets: Summary, Signals, Form4, Financials, Macro, Claude
- [ ] Conditional formatting: cell background = signal color
  - GREEN: `#091409` bg, `#44ff88` text
  - RED: `#200a0a` bg, `#ff6666` text
  - AMBER: `#1a1200` bg, `#ffcc44` text
- [ ] Column widths auto-fitted to content
- [ ] Summary sheet: all key numbers in one view
- [ ] Filename: `ORCA_{TICKER}_{DATE}.xlsx`

**ui/app.py export wiring**
- [ ] Export button in Claude panel: [↓ PDF] [↓ XLS]
- [ ] Status bar shows: "Exporting... → Saved: ORCA_MSFT_20260419.pdf"
- [ ] Export runs in background thread (no UI freeze)

### Tests
- [ ] PDF generates without errors on mock SignalReport
- [ ] Excel generates without errors on mock SignalReport
- [ ] All 6 Excel sheets present
- [ ] PDF file is valid (opens without error)

### Deliverables
- `export/pdf_exporter.py`
- `export/excel_exporter.py`
- Updated `ui/app.py` export flow

---

## Phase 8 — Rules Editor UI
*Estimated time: 3–4 hours*

### Goals
Build the inline rules editor so users can add, edit, enable/disable, and
delete rules without ever opening a text editor.

### Tasks

**ui/panels/rules_panel.py** (complete implementation)
- [ ] DataTable showing all rules: ID | Name | Category | Color | Score | Enabled
- [ ] Click row → expand to show condition + description
- [ ] [Enable/Disable] toggle button per row
- [ ] [Edit] button → opens simple inline form
  - Fields: name, condition, description, color, base_strength, rarity
- [ ] [Add Rule] button → blank form with ID auto-incremented
- [ ] [Delete] button → confirmation prompt
- [ ] [Save] → writes back to `rules.yaml` immediately
- [ ] Changes take effect on next scan (no restart)
- [ ] [Reset to defaults] → restores original rules.yaml from backup

### Tests
- [ ] Enable/disable rule persists to rules.yaml
- [ ] New rule appears in evaluator after save
- [ ] Deleted rule no longer fires
- [ ] Invalid YAML condition shows error, does not save

### Deliverables
- Complete `ui/panels/rules_panel.py`
- `rules_default_backup.yaml` (pristine copy)

---

## Integration Checklist (Full System Test)

Run after Phase 8 is complete:

- [ ] `python orca.py MSFT` — full load, all panels populate
- [ ] Switch to AAPL — all panels reload correctly
- [ ] Switch to a utility (AEP) — FUN-06 skipped per SIC override
- [ ] Switch to a biotech (MRNA) — FIL-12 skipped per SIC override
- [ ] Run Quick Scan Claude analysis
- [ ] Run Deep Dive Claude analysis
- [ ] Export PDF — opens and looks correct
- [ ] Export Excel — all 6 sheets present
- [ ] Add a custom rule via Rules Editor — fires correctly on next scan
- [ ] Disable INS-01 — no longer shows in signals panel
- [ ] Light mode toggle — all panels render correctly
- [ ] Resize terminal — panels reflow correctly
- [ ] `q` to quit — clean exit, no error

---

## Known Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| edgartools blocked by SEC rate limits | Medium | Built-in rate limiter (10 req/s) + peer cache |
| Claude Code CLI breaks on update | Low | Version pin in README; fallback to API mode |
| Python 3.14 Textual edge cases | Medium | Test on 3.12 first; document any 3.14 workarounds |
| FRED API key quota | Low | FRED has generous free tier; cache all results |
| asteval expression parsing edge case | Low | Catch all eval exceptions; log + skip failing rule |
| Peer fetch too slow for large SIC groups | Medium | Cap at top 10, Parquet cache per sector per day |
| yfinance data gaps for small caps | Medium | Graceful empty return; panels show "No data" |

---

## Dependency Versions (requirements.txt)

```
textual>=0.80.0
textual-plotext>=0.2.1
plotext>=5.3.0
edgartools>=5.28.0
yfinance>=0.2.0
fredapi>=0.5.0
feedparser>=6.0.0
asteval>=0.9.31
PyYAML>=6.0.0
pandas>=2.0.0
pyarrow>=12.0.0
reportlab>=4.0.0
openpyxl>=3.1.0
requests>=2.31.0
```

---

*Project ORCA · Build Plan v1.0 · April 2026*
*Update this document as decisions change. Never skip a phase.*
