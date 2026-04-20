# PROJECT ORCA — Visual Theme & Design System
*Version 1.0 · April 2026*

---

## 1. Design Philosophy

ORCA is a terminal application. The aesthetic is deliberately inspired by two
sources:

- **Ratatui** (Rust TUI framework) — dense information layout, block borders,
  no rounded corners, maximum data-to-chrome ratio
- **Edgarian** (the parent design system) — dark terminal palette, IBM Plex Mono
  typography, signal color semantics

The guiding principle: **every pixel earns its place.**
No decorative elements. No gradients. No animations except functional ones
(scrolling index ticker, blinking cursor in filing reader).

If a Bloomberg terminal and a Rust TUI had a Python child, it would look like ORCA.

---

## 2. Typography

| Property | Value |
|----------|-------|
| **Primary font** | IBM Plex Mono |
| **Fallback fonts** | JetBrains Mono → Fira Code → Courier New |
| **Weight: muted labels** | 300 |
| **Weight: body text** | 400 |
| **Weight: values, headings** | 500 |
| **Size range** | 11px – 16px (user-selectable) |
| **Default size** | 13px |
| **Rule** | Monospace only. No serif. No sans-serif. No exceptions. |

### Text size roles
| Role | Size | Weight | Color token |
|------|------|--------|-------------|
| Panel type label | 10px | 400 | `--text3` |
| Ticker / heading | 15px | 500 | `--text` |
| Body / table rows | 12px | 400 | `--text` |
| Metric labels | 12px | 300 | `--text2` |
| Timestamps / muted | 11px | 300 | `--text3` |
| Disabled / placeholder | 11px | 300 | `--text4` |

---

## 3. Color System

### 3.1 Base Palette (Dark Mode — Default)

```
Background layers (darkest to lightest):
  --bg     #0a0a0a   App background
  --bg2    #0f0f0f   Panel background, side menu
  --bg3    #161616   Input background, hover states, table alternates
  --bg4    #1a1a1a   Dropdown, tooltip background

Border layers:
  --border   #222222   Panel borders, primary dividers
  --border2  #2a2a2a   Inner borders, panel headers
  --border3  #333333   Active/hover borders, focus rings
```

### 3.2 Text Palette

```
  --text    #ffffff   Primary values, ticker names, active labels
  --text2   #888888   Metric labels, column headers
  --text3   #555555   Muted content, timestamps, secondary info
  --text4   #444444   Placeholders, disabled states
```

### 3.3 Signal Colors (the core of ORCA)

These are the five semantic colors used throughout the signal system.
They do NOT change between light and dark mode — signal semantics must
remain unambiguous in all conditions.

| Token | Hex | Meaning | Action Bias |
|-------|-----|---------|-------------|
| `--green` | `#44ff88` | **Bullish** | Buy · Long · Add |
| `--green-bg` | `#091409` | Green flag background | — |
| `--green-border` | `#44ff88` | Green flag left border | — |
| `--green-text` | `#66ffaa` | Green flag text | — |
| | | | |
| `--red` | `#ff5555` | **Bearish** | Sell · Short · Exit |
| `--red-bg` | `#200a0a` | Red flag background | — |
| `--red-border` | `#ff4444` | Red flag left border | — |
| `--red-text` | `#ff6666` | Red flag text | — |
| | | | |
| `--blue` | `#4499ff` | **Neutral** | Watch · Hold · Monitor |
| `--blue-bg` | `#080f20` | Blue flag background | — |
| `--blue-border` | `#4499ff` | Blue flag left border | — |
| `--blue-text` | `#66bbff` | Blue flag text | — |
| | | | |
| `--amber` | `#ffaa00` | **Caution** | Reduce · Hedge · Verify |
| `--amber-bg` | `#1a1200` | Amber flag background | — |
| `--amber-border` | `#ffaa00` | Amber flag left border | — |
| `--amber-text` | `#ffcc44` | Amber flag text | — |
| | | | |
| `--purple` | `#cc88ff` | **Speculative** | Small position · High R/R |
| `--purple-bg` | `#150a20` | Purple flag background | — |
| `--purple-border` | `#cc88ff` | Purple flag left border | — |
| `--purple-text` | `#dd99ff` | Purple flag text | — |

### 3.4 Financial Display Colors

Used specifically in the Financials panel for income statement hierarchy:

```
  --fin-blue   #4499ff   Revenue, gross profit, top-line metrics
  --fin-green  #44ff88   Operating income, net income, EPS, margins
```

### 3.5 Light Mode

Toggled via `◐` button in topbar. Signal colors are UNCHANGED.

| Dark token | Light equivalent |
|-----------|-----------------|
| `--bg` #0a0a0a | #f5f5f5 |
| `--bg2` #0f0f0f | #ffffff |
| `--bg3` #161616 | #f0f0f0 |
| `--bg4` #1a1a1a | #e8e8e8 |
| `--border` #222 | #e0e0e0 |
| `--border2` #2a2a2a | #d8d8d8 |
| `--border3` #333 | #cccccc |
| `--text` #ffffff | #0a0a0a |
| `--text2` #888 | #555555 |
| `--text3` #555 | #888888 |
| `--text4` #444 | #aaaaaa |
| All signal colors | UNCHANGED |

---

## 4. Layout System

### 4.1 Shell Structure

```
┌─ TOPBAR (44px) ────────────────────────────────────────────────────┐
│ [ED]  [MSFT    ] [LOAD]   S&P·5612  VIX·18  10Y·4.3%   19Apr26   │
│ [GR]                                                                │
├──────┬─────────────────────────────────────────────────────────────┤
│ SIDE │                                                              │
│ MENU │   MAIN PANEL GRID (fluid, default 2-column)                 │
│ 48px │                                                              │
│      │                                                              │
└──────┴─────────────────────────────────────────────────────────────┘
```

### 4.2 Topbar (44px)

```
  Background:    --bg2 (#0f0f0f)
  Border-bottom: 1px solid --border (#222)

  LEFT:   Logo (ED/GR, 6-char) + Search input (180px) + LOAD button
  CENTER: Rolling index ticker (S&P, NASDAQ, DOW, VIX, 10Y, DXY)
  RIGHT:  Font selector + Size selector + ◐ toggle + Datetime
```

**LOAD button:** `background: #ffffff; color: #000000; font-weight: 500`
**Search input:** `background: --bg3; border: 1px solid --border3; focus-border: #fff`

### 4.3 Side Menu (48px wide)

```
  Background:   --bg2
  Border-right: 1px solid --border

  LOGO (top):
    ED  ← E=white, D=#44ff88 (green)
    GR  ← G=#ff5555 (red), R=white
    Font: IBM Plex Mono 500, 15px, letter-spacing 0.02em

  PANEL BUTTONS (40×40px each):
    Active:   border: 1px solid #fff; color: #fff
    Inactive: border: 1px solid transparent; color: #555
    Hover:    tooltip slides right showing full panel name

  3-char abbreviations:
    SIG  FRM  8·K  FIN  PER  MAC  ANA  RUL
```

### 4.4 Panels

```
  Border:     1px solid --border2 (#2a2a2a)
  Background: --bg2 (#0f0f0f)
  Border-radius: 0  ← no rounded corners (Ratatui rule)

  PANEL HEADER:
    padding: 8px 12px
    border-bottom: 1px solid --border2
    Top line:    panel type — 10px, #666, UPPERCASE, letter-spacing 0.15em
    Bottom line: ticker name — 15px, #fff, weight 500
    Close [✕]:  top-right, color #555, hover #fff
```

---

## 5. Component Library

### 5.1 Signal Flag

Every fired rule renders as a flag:

```
┌─────────────────────────────────────────────────────┐
│▌ RULE NAME                          ID    SCORE%    │
│  Description or source citation                     │
└─────────────────────────────────────────────────────┘

CSS:
  border-left: 2px solid [--{color}-border]
  background:  [--{color}-bg]
  color:       [--{color}-text]
  font-size:   12px
  font-weight: 500
  padding:     8px 10px
  margin-bottom: 7px
```

Rarity indicator appended to score:
- `94% ◆` = RARE (fires in <0.5% of stocks)
- `72% ◈` = UNCOMMON
- `47% ○` = OCCASIONAL
- `31% ·` = COMMON

### 5.2 ORCA Score Block

```
  ╔══════════════════════════════════════╗
  ║  ORCA SCORE   ████████░░   81/100   ║
  ║  Confidence   ████████░░   83%      ║
  ║  BULLISH · 5 GREEN · 0 RED · 1 AMB ║
  ╚══════════════════════════════════════╝

  Score bar:   filled = --green, empty = --border2
  Score color: >65 = --green, 35–65 = --amber, <35 = --red
```

### 5.3 Metric Row

```
  Revenue Growth    +17.0%    ████████░░  P62
  ──────────────────────────────────────────
  label: --text2 (12px, weight 300)
  value: --text  (12px, weight 500)
  delta positive: --green
  delta negative: --red
  bar:   filled = signal color, empty = --border2
  border-bottom: 1px solid #181818
  padding: 5px 0
```

### 5.4 Percentile Bar (Peer Comparison)

```
  Gross Margin  69%   ████████░░░   P71  GREEN
                      ↑ filled portion = percentile rank
  bar width: proportional, 20 chars wide
  color:
    P67–P100: --green
    P34–P66:  --blue (neutral)
    P0–P33:   --red
```

### 5.5 Table Rows

```
  Alternating rows:
    Even: background --bg2
    Odd:  background --bg3
  Selected row: background --border2; border-left: 2px solid #fff
  Header row:   background --bg3; color --text2; UPPERCASE
  Cell padding: 4px 8px
```

### 5.6 Collapsible Tree Row (Financials)

```
  ▶ Revenue          $81.3B    +17%
    ▶ Azure           $32.9B   +39%    (expanded child)
    ▶ M365 Commercial $34.1B   +16%

  ▶ collapsed  ▼ expanded
  click anywhere on row to toggle
  child rows: indented 2 spaces, color --text2
```

### 5.7 Radio Buttons

```
  [● Annual]  [○ Quarterly]

  Selected: color --green, border --green
  Inactive: color --text3, border --border2
```

### 5.8 Tooltips

```
  Background: --bg4 (#1a1a1a)
  Border:     1px solid --border3 (#333)
  Font size:  10px
  Text color: --text2 (#888)
  Title:      10px, --text (#fff), weight 500
  Line height: 1.7
  Appear on hover, no animation delay
```

### 5.9 Index Ticker (Topbar)

```
  Scrolls left continuously, pauses on hover

  S&P 500  5,612.34  +0.38%    NASDAQ  17,432  +0.51%  ...
  ↑name    ↑value    ↑change
  name:   11px, --text3 (#555)
  value:  12px, --text (#fff), weight 500
  change: 10px, --green or --red
  separator: 3 spaces
```

---

## 6. Panel Layouts

### 6.1 Signals Panel

```
┌─ SIGNALS ─────────────────── MSFT ──┐
│                                      │
│ ▌ Insider cluster buy    INS-01  94%◆│
│   2+ open-market buys in 30 days    │
│                                      │
│ ▌ RPO >50% YoY           FIL-01  89%◆│
│   Commercial RPO +110% YoY          │
│                                      │
│ ▌ Revenue decel.         FUN-10  43%○│
│   Growth slowing 2 qtrs             │
│                                      │
│ ╔════════════════════════════════╗   │
│ ║ ORCA SCORE  ████████░░  81/100║   │
│ ║ Confidence  ████████░░  83%   ║   │
│ ║ BULLISH · 3 GREEN · 1 AMBER  ║   │
│ ╚════════════════════════════════╝   │
└──────────────────────────────────────┘
```

### 6.2 Price Panel

```
┌─ PRICE ──────────────────── MSFT ───┐
│ $422.79  +1.2%  Vol 18.4M  MktCap 3.1T│
│                                      │
│ ▓▓▓ ▓▓▓▓ ▓▓▓  ▓▓  ▓▓▓▓▓▓▓▓▓▓▓  60d │
│ ▓▓▓ ▓▓▓▓ ▓▓▓ ▓▓▓  ▓▓▓▓▓▓▓▓▓▓▓     │
│ █▓▓ ▓▓▓▓ ▓▓▓ ▓▓▓▓ ▓▓▓▓▓▓▓▓▓▓▓     │
│ Mar                            Apr  │
│ ────────────────── sparkline ─────  │
│ 52wk: $355 ──────────────── $555    │
└──────────────────────────────────────┘
  green bars = up day, red bars = down day
```

### 6.3 Peer Comparison Panel

```
┌─ PEERS ──── SIC 7372 · Prepackaged Software ─┐
│ vs GOOGL  ORCL  CRM  ADBE  NOW  +5 others    │
│                                               │
│ Metric         MSFT   Sector  Rank  Signal   │
│ ──────────────────────────────────────────── │
│ Rev Growth     +17%   P62     ████████░░  ●  │
│ Gross Margin    69%   P71     █████████░  ●  │
│ FCF Yield      2.8%   P64     ████████░░  ●  │
│ Debt/EBITDA    0.4x   P82     ██████████  ●  │
│ P/E Ratio       31x   P54     ███████░░░  ●  │
│ Op. Leverage  +4.2pp  P78     █████████░  ●  │
│                                               │
│ PEER SCORE  P71 · Top Quartile               │
└───────────────────────────────────────────────┘
  bar color: P67+ = green, P34–66 = blue, <P34 = red
```

### 6.4 Macro Panel

```
┌─ MACRO ──────────────────────────────┐
│ 10Y-2Y   +0.21%  ████░░░░  NORMAL   │
│ VIX       18.2   ███░░░░░  NEUTRAL  │
│ CPI       +3.2%  █████░░░  ELEVATED │
│ DXY      103.4   ████░░░░  NEUTRAL  │
│ FedFunds  5.25%  ███████░  HIGH     │
│ HY Spread +342bp ████░░░░  NORMAL   │
│                                      │
│ Last updated: 19 Apr 2026 14:32      │
└──────────────────────────────────────┘
  gauge fill: green = healthy, amber = watch, red = risk
```

---

## 7. Textual CSS Implementation

All styles live in `ui/theme.css`. Key rules:

```css
/* ── Base ──────────────────────────────── */
Screen         { background: #0a0a0a; color: #ffffff; }
Header         { background: #0f0f0f; color: #ffffff; height: 1; }

/* ── No rounded corners anywhere ───────── */
*              { border-radius: 0 !important; }

/* ── Topbar ─────────────────────────────── */
#topbar        { height: 3; background: #0f0f0f;
                 border-bottom: solid #222222; }

/* ── Side menu ──────────────────────────── */
#sidebar       { width: 6; background: #0f0f0f;
                 border-right: solid #222222; }

/* ── Panels ─────────────────────────────── */
.panel         { border: solid #2a2a2a; background: #0f0f0f; }
.panel-header  { background: #161616; color: #888888;
                 border-bottom: solid #2a2a2a; padding: 0 1; }

/* ── Signal flags ───────────────────────── */
.flag-green    { border-left: tall #44ff88; background: #091409;
                 color: #66ffaa; }
.flag-red      { border-left: tall #ff4444; background: #200a0a;
                 color: #ff6666; }
.flag-blue     { border-left: tall #4499ff; background: #080f20;
                 color: #66bbff; }
.flag-amber    { border-left: tall #ffaa00; background: #1a1200;
                 color: #ffcc44; }
.flag-purple   { border-left: tall #cc88ff; background: #150a20;
                 color: #dd99ff; }

/* ── Tables ─────────────────────────────── */
DataTable      { background: #0f0f0f; border: solid #2a2a2a; }
DataTable > .datatable--header
               { background: #161616; color: #888888; }
DataTable > .datatable--cursor
               { background: #222222; }

/* ── Inputs ─────────────────────────────── */
Input          { background: #161616; border: tall #333333;
                 color: #ffffff; }
Input:focus    { border: tall #ffffff; }

/* ── Buttons ─────────────────────────────── */
Button.load    { background: #ffffff; color: #000000; }
Button.load:hover { background: #cccccc; }
#sidebar Button { background: #0f0f0f; border: none;
                  color: #555555; }
#sidebar Button.active { color: #ffffff;
                          border-left: solid #ffffff; }
```

---

## 8. Logo

```
ED
GR
```

| Character | Color |
|-----------|-------|
| E | `#ffffff` (white) |
| D | `#44ff88` (green) |
| G | `#ff5555` (red) |
| R | `#ffffff` (white) |

Font: IBM Plex Mono 500, 15px, letter-spacing 0.02em
Position: top of side menu

The logo encodes the product name (EDGaRian) and its two primary signal
colors (green = bullish, red = bearish) in four characters.

---

*Project ORCA · Theme v1.0 · April 2026*
