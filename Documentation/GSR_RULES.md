# PROJECT ORCA — Global Scan Rules (GSR)
## Complete Rule Reference
*Version 1.0 · April 2026*

---

## 1. Understanding Rule IDs

Every rule in ORCA has a structured ID that tells you exactly what category
it belongs to, what number it is, and how to find it in `rules.yaml`.

### 1.1 ID Format

```
  CAT-NN
  │    │
  │    └── Two-digit sequence number within the category (01, 02, ...)
  └──────── Three-letter category prefix
```

### 1.2 Category Prefixes

| Prefix | Category | What it covers |
|--------|----------|----------------|
| `INS` | Insider Activity | SEC Form 4 open-market buys/sells, position changes |
| `FIL` | SEC Filing Signals | 8-K events, 10-K/Q language, 13F holdings, auditor changes |
| `FUN` | Fundamental / Financial | Revenue, margins, leverage, cash flow, valuation ratios |
| `PRC` | Price & Technical | Moving averages, 52-week levels, volume, short interest |
| `MAC` | Macro Signals | FRED data: yield curve, VIX, CPI, DXY, credit spreads |
| `CMP` | Confluence (Composite) | Fires when multiple base rules align — highest conviction |

### 1.3 Reading a Rule in the UI

When a signal fires in the ORCA terminal, you see:

```
▌ Insider cluster buy           INS-01    94% ◆
  2+ insiders buying open-market within 30 days
```

- **Flag color bar** (left edge) = directional signal (GREEN/RED/BLUE/AMBER/PURPLE)
- **Rule name** = plain-English description
- **Rule ID** (e.g. `INS-01`) = look this up in `rules.yaml` to view/edit the condition
- **Score %** (e.g. `94%`) = Base Strength × 0.6 + Rarity × 0.4
- **Rarity symbol**: `◆` RARE · `◈` UNCOMMON · `○` OCCASIONAL · `·` COMMON

### 1.4 Signal Score Formula

```
Signal Score % = (base_strength × 0.6) + (rarity × 0.4)
```

**Base Strength:** Historical predictive power of this signal type (0–100)
**Rarity:** How rarely this fires across ~6,000 NYSE + Nasdaq stocks (0–100)

| Rarity Score | Fires in | Symbol | Label |
|-------------|----------|--------|-------|
| 100 | <0.5% of stocks | ◆ | RARE |
| 75 | 0.5–2% of stocks | ◈ | UNCOMMON |
| 50 | 2–10% of stocks | ○ | OCCASIONAL |
| 25 | >10% of stocks | · | COMMON |

### 1.5 Signal Colors

| Color | Hex | Meaning | Action Bias |
|-------|-----|---------|-------------|
| 🟢 GREEN | `#44ff88` | Bullish | Buy · Long · Add |
| 🔴 RED | `#ff5555` | Bearish | Sell · Short · Exit |
| 🔵 BLUE | `#4499ff` | Neutral | Watch · Hold · Monitor |
| 🟡 AMBER | `#ffaa00` | Caution | Reduce · Hedge · Verify |
| 🟣 PURPLE | `#cc88ff` | Speculative | Small position · High R/R |

### 1.6 ORCA Score Weighting per Color

| Color | ORCA Score impact | Rationale |
|-------|------------------|-----------|
| GREEN | +12 per signal | Confirmed bullish |
| RED | −18 per signal | Asymmetric — capital preservation |
| AMBER | −5 per signal | Mild negative drag |
| BLUE | 0 | Informational only |
| PURPLE | +6 per signal | Discounted upside optionality |
| CMP rules | ×2 multiplier | Confluence = higher conviction |

### 1.7 SIC Code Overrides

Some rules use different conditions for different sectors because the same
absolute threshold means different things across industries. Example:
Debt/EBITDA of 4x is dangerous for a SaaS company but normal for a utility.

In `rules.yaml`, this is expressed as:

```yaml
- id: FUN-06
  name: "High leverage"
  condition: "peer.debt_ebitda_percentile < 25"
  color: RED
  sic_overrides:
    "6020-6099": "skip"     # Banks — high leverage is normal
    "6500-6552": "skip"     # REITs — high leverage is normal
    "4900-4991": "skip"     # Utilities — high leverage is normal
```

`"skip"` means: do not evaluate this rule for companies in this SIC range.
You can also provide an alternate condition instead of `"skip"`.

---

## 2. Rule Conditions — Namespace Reference

Rules are evaluated as safe Python expressions. Available variables:

### form4 namespace
```
form4.open_market_buys_30d        # count of open-market buy transactions
form4.open_market_sells_30d       # count of open-market sell transactions
form4.cluster_buy_30d             # bool: 2+ insiders bought in 30 days
form4.cluster_sell_14d            # bool: 3+ insiders sold in 14 days
form4.ceo_bought                  # bool: CEO made open-market purchase
form4.cfo_bought                  # bool: CFO made open-market purchase
form4.largest_buy_usd             # largest single buy in USD
form4.pct_holdings_sold           # largest single sell as % of holdings
form4.days_since_last_buy         # days since most recent buy
form4.near_52wk_low               # bool: price within 10% of 52wk low at buy
```

### filing namespace
```
filing.going_concern              # bool: going concern language detected
filing.auditor_changed            # bool: auditor change in current period
filing.guidance_raised            # bool: forward guidance raised
filing.guidance_lowered           # bool: forward guidance lowered
filing.ceo_departed               # bool: unscheduled CEO departure
filing.cfo_departed               # bool: unscheduled CFO departure
filing.buyback_pct_float          # share buyback authorization as % of float
filing.material_contract          # bool: material contract/partnership in 8-K
filing.equity_dilution_pct        # dilution as % of shares outstanding
filing.new_13f_tier1              # bool: tier-1 fund opened new position
filing.activist_13d               # bool: activist 13D filed
filing.short_seller_report        # bool: short-seller report published
filing.rpo_yoy                    # commercial RPO YoY growth rate (decimal)
```

### financials namespace (absolute values)
```
financials.revenue_growth         # YoY revenue growth (decimal, e.g. 0.17)
financials.gross_margin           # gross margin (decimal)
financials.gross_margin_delta     # YoY change in gross margin (bps / 100)
financials.operating_margin       # operating margin (decimal)
financials.net_margin             # net margin (decimal)
financials.fcf_yield              # free cash flow yield at current price
financials.debt_ebitda            # debt / EBITDA ratio
financials.cash_runway_months     # months of cash at current burn rate
financials.eps_beat_streak        # consecutive quarters of EPS beat
financials.revenue_growth_streak  # consecutive quarters of >20% rev growth
financials.rev_growth_delta       # revenue growth acceleration/decel
financials.pe_ratio               # trailing P/E
financials.op_leverage            # operating leverage (pp improvement)
financials.net_income_streak_neg  # consecutive quarters of negative net income
```

### peer namespace (sector-relative percentiles)
```
peer.rev_growth_percentile        # percentile vs top-10 SIC peers (0–100)
peer.gross_margin_percentile
peer.fcf_yield_percentile
peer.debt_ebitda_percentile
peer.pe_percentile
peer.op_leverage_percentile
peer.ev_ebitda_percentile         # for energy/industrials
peer.pb_percentile                # for banks
peer.p_ffo_percentile             # for REITs
peer.sector_name                  # e.g. "Prepackaged Software"
peer.fama_french_industry         # e.g. "Business Services"
peer.sic                          # SIC code integer
peer.peer_count                   # number of peers in universe
peer.peer_tickers                 # list of peer ticker symbols
```

### price namespace
```
price.current                     # current price
price.prev_close                  # previous close
price.change_1d                   # 1-day price change (decimal)
price.change_30d                  # 30-day price change (decimal)
price.change_90d                  # 90-day price change (decimal)
price.pct_from_52wk_low           # % above 52-week low
price.pct_from_52wk_high          # % below 52-week high
price.pct_from_ath                # % below all-time high
price.volume_ratio_30d            # today's volume / 30d average
price.short_float                 # short interest as % of float
price.above_200d_ma               # bool: price above 200-day MA
price.golden_cross                # bool: 50d MA crossed above 200d MA (recent)
price.death_cross                 # bool: 50d MA crossed below 200d MA (recent)
```

### macro namespace
```
macro.spread_10y_2y               # 10Y minus 2Y yield (decimal, e.g. 0.21)
macro.vix                         # VIX index value
macro.cpi_surprise                # CPI beat vs estimate (decimal)
macro.dxy_change_30d              # DXY 30-day change (decimal)
macro.fed_rate                    # current Fed funds rate
macro.fed_cutting                 # bool: Fed in rate cut cycle
macro.fed_hiking                  # bool: Fed in rate hike cycle
macro.hy_spread_change_30d        # HY credit spread change in 30d (bps)
macro.ig_spread_change_30d        # IG credit spread change in 30d (bps)
```

---

## 3. Complete Rule Catalog

---

### CATEGORY 1 — INSIDER ACTIVITY (INS)

*Source: SEC Form 4 filings via edgartools*
*Note: Only open-market transactions count. RSU awards, option exercises,*
*and tax withholdings are classified separately and do not trigger INS rules.*

---

#### INS-01 · Insider Cluster Buy 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 90 |
| **Rarity** | 100 |
| **Signal Score** | **94%** ◆ RARE |
| **Condition** | `form4.open_market_buys_30d >= 2` |
| **Description** | 2+ insiders making open-market purchases within 30 days |
| **Rationale** | Multiple insiders buying simultaneously is one of the strongest known signals in academic finance. Insiders have material non-public context. A cluster buy near a drawdown is particularly high-conviction. |
| **SIC overrides** | None |

---

#### INS-02 · Large Insider Buy 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 85 |
| **Rarity** | 95 |
| **Signal Score** | **91%** ◆ RARE |
| **Condition** | `form4.largest_buy_usd >= 1_000_000` |
| **Description** | Single insider makes open-market purchase ≥$1M |
| **Rationale** | A $1M+ open-market buy is a material personal commitment. Insiders rarely risk significant personal capital unless they have high conviction. |
| **SIC overrides** | None |

---

#### INS-03 · CEO or CFO Buys 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 90 |
| **Rarity** | 98 |
| **Signal Score** | **93%** ◆ RARE |
| **Condition** | `form4.ceo_bought or form4.cfo_bought` |
| **Description** | CEO or CFO makes any open-market purchase |
| **Rationale** | The two executives with the most complete financial picture of the business chose to buy. Any amount at market signals confidence in near-term trajectory. |
| **SIC overrides** | None |

---

#### INS-04 · Insider Cluster Sell 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 80 |
| **Rarity** | 90 |
| **Signal Score** | **86%** ◆ RARE |
| **Condition** | `form4.cluster_sell_14d == True` |
| **Description** | 3+ insiders selling open-market within 14 days |
| **Rationale** | Coordinated insider selling near a price peak is a distribution signal. Single sells may be diversification; cluster sells within 14 days suggest shared concern. |
| **SIC overrides** | None |

---

#### INS-05 · Insider Buy Near 52-Week Low 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 88 |
| **Rarity** | 95 |
| **Signal Score** | **92%** ◆ RARE |
| **Condition** | `form4.near_52wk_low and form4.open_market_buys_30d >= 1` |
| **Description** | Insider buys while stock is within 10% of 52-week low |
| **Rationale** | Buying at a price near the annual low is a strong contrarian conviction signal. Insider is effectively calling the bottom with personal capital. |
| **SIC overrides** | None |

---

#### INS-06 · Large Position Liquidation 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 70 |
| **Rarity** | 75 |
| **Signal Score** | **72%** ◈ UNCOMMON |
| **Condition** | `form4.pct_holdings_sold > 0.30` |
| **Description** | Insider sells >30% of their total position |
| **Rationale** | Selling more than 30% of holdings in a single transaction is unusual and suggests the insider is materially reducing exposure, not routine diversification. |
| **SIC overrides** | None |

---

#### INS-07 · No Insider Activity 12 Months 🔵 BLUE

| Property | Value |
|----------|-------|
| **Signal** | Neutral |
| **Base Strength** | 20 |
| **Rarity** | 25 |
| **Signal Score** | **22%** · COMMON |
| **Condition** | `form4.days_since_last_buy > 365` |
| **Description** | No open-market insider buying in over 12 months |
| **Rationale** | Informational context. Not bearish (many insiders avoid trading). But absence of buying during a significant drawdown weakens the bull case. |
| **SIC overrides** | None |

---

### CATEGORY 2 — SEC FILING SIGNALS (FIL)

*Source: EDGAR 8-K, 10-K, 10-Q, 13F via edgartools*

---

#### FIL-01 · RPO Acceleration 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 85 |
| **Rarity** | 95 |
| **Signal Score** | **89%** ◆ RARE |
| **Condition** | `filing.rpo_yoy > 0.50` |
| **Description** | Commercial remaining performance obligation growing >50% YoY |
| **Rationale** | RPO is contracted future revenue — the single best leading indicator of cloud/SaaS revenue visibility. >50% YoY growth means the company has locked in significant future billings. |
| **SIC overrides** | Relevant primarily for SIC 7370–7379 (software/cloud) |

---

#### FIL-02 · Unscheduled CEO/CFO Departure 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 92 |
| **Rarity** | 99 |
| **Signal Score** | **95%** ◆ RARE |
| **Condition** | `filing.ceo_departed or filing.cfo_departed` |
| **Description** | Unscheduled departure of CEO or CFO filed in 8-K |
| **Rationale** | Sudden executive departures are one of the most reliable leading indicators of undisclosed problems. Planned retirements/transitions are excluded. |
| **SIC overrides** | None |

---

#### FIL-03 · Material Contract or Partnership 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 65 |
| **Rarity** | 70 |
| **Signal Score** | **67%** ◈ UNCOMMON |
| **Condition** | `filing.material_contract == True` |
| **Description** | Material contract or strategic partnership disclosed in 8-K |
| **Rationale** | A signed material contract represents confirmed future revenue. The signal strength depends on deal size — moderate by default, upgrades if deal is >5% of annual revenue. |
| **SIC overrides** | None |

---

#### FIL-04 · Revenue Guidance Raised 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 75 |
| **Rarity** | 80 |
| **Signal Score** | **77%** ◈ UNCOMMON |
| **Condition** | `filing.guidance_raised == True` |
| **Description** | Company raises forward revenue guidance in filing or earnings call |
| **Rationale** | Management is increasing their own targets with material non-public context. Guidance raises tend to be conservative — actual results often exceed the raised guidance. |
| **SIC overrides** | None |

---

#### FIL-05 · Revenue Guidance Lowered 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 78 |
| **Rarity** | 82 |
| **Signal Score** | **80%** ◆ RARE |
| **Condition** | `filing.guidance_lowered == True` |
| **Description** | Company lowers forward revenue guidance |
| **Rationale** | Guidance cuts often come in sequences — the first cut is rarely the last. Management is signaling deteriorating visibility. |
| **SIC overrides** | None |

---

#### FIL-06 · Going Concern Language 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 95 |
| **Rarity** | 99 |
| **Signal Score** | **96%** ◆ RARE |
| **Condition** | `filing.going_concern == True` |
| **Description** | Auditor includes going concern language in 10-K or 10-Q |
| **Rationale** | Going concern opinion means the auditor has substantial doubt about the company's ability to continue operating. This is an extreme flag — almost universally precedes severe equity impairment. |
| **SIC overrides** | None |

---

#### FIL-07 · Auditor Change 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 88 |
| **Rarity** | 97 |
| **Signal Score** | **92%** ◆ RARE |
| **Condition** | `filing.auditor_changed == True` |
| **Description** | Auditor change filed (Item 4.02 in 8-K) |
| **Rationale** | Auditor dismissals, especially unplanned ones, frequently precede accounting restatements or fraud disclosures. Voluntary auditor changes by large companies are rare. |
| **SIC overrides** | None |

---

#### FIL-08 · Share Buyback Authorization 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 80 |
| **Rarity** | 90 |
| **Signal Score** | **84%** ◆ RARE |
| **Condition** | `filing.buyback_pct_float > 0.05` |
| **Description** | Share buyback authorized >5% of shares outstanding |
| **Rationale** | A board-authorized buyback >5% of float signals management confidence in intrinsic value and reduces share count. Most reliable when stock is near multi-year lows. |
| **SIC overrides** | None |

---

#### FIL-09 · Tier-1 Fund New Position (13F) 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 70 |
| **Rarity** | 85 |
| **Signal Score** | **76%** ◈ UNCOMMON |
| **Condition** | `filing.new_13f_tier1 == True` |
| **Description** | Tier-1 institutional fund opens new position (Berkshire, Pershing, Ackman, etc.) |
| **Rationale** | Tier-1 funds conduct extensive due diligence before initiating positions. A new 13F position signals deep fundamental conviction with large capital commitment. |
| **SIC overrides** | None |

---

#### FIL-10 · Activist 13D Filed 🔵 BLUE

| Property | Value |
|----------|-------|
| **Signal** | Neutral |
| **Base Strength** | 50 |
| **Rarity** | 80 |
| **Signal Score** | **62%** ◈ UNCOMMON |
| **Condition** | `filing.activist_13d == True` |
| **Description** | Activist investor files 13D (>5% position with intent to influence) |
| **Rationale** | Direction depends entirely on the activist's agenda. Elliott pushing for margin improvement = bullish. Icahn pushing for breakup under duress = mixed. Classified as BLUE (neutral) until intent is clear. User may reclassify. |
| **SIC overrides** | None |

---

#### FIL-11 · Short-Seller Report 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 85 |
| **Rarity** | 95 |
| **Signal Score** | **89%** ◆ RARE |
| **Condition** | `filing.short_seller_report == True` |
| **Description** | Prominent short-seller publishes research report targeting this stock |
| **Rationale** | Short-sellers publish only when they have high conviction and are already positioned. The report itself is the first public signal of the thesis. |
| **SIC overrides** | None |

---

#### FIL-12 · Equity Dilution >10% 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 82 |
| **Rarity** | 88 |
| **Signal Score** | **85%** ◆ RARE |
| **Condition** | `filing.equity_dilution_pct > 0.10` |
| **Description** | New equity issuance >10% of shares outstanding |
| **Rationale** | Significant dilution directly impairs per-share value and signals the company cannot fund operations or growth through cash flow. |
| **SIC overrides** | `"2830-2836": "skip"` (Biotech — frequent dilution is normal for pipeline funding) |

---

### CATEGORY 3 — FUNDAMENTAL / FINANCIAL (FUN)

*Source: XBRL financials via edgartools + yfinance*
*All peer-relative conditions use top-10 SIC peers by market cap*

---

#### FUN-01 · Sustained Revenue Growth 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 80 |
| **Rarity** | 75 |
| **Signal Score** | **78%** ◈ UNCOMMON |
| **Condition** | `financials.revenue_growth_streak >= 3 and financials.revenue_growth > 0.20` |
| **Description** | Revenue growing >20% YoY for 3+ consecutive quarters |
| **Rationale** | Sustained high-rate organic growth is the most durable value creation driver. Three consecutive quarters eliminates noise and confirms trend. |
| **SIC overrides** | None |

---

#### FUN-02 · Gross Margin Expanding + Above Sector 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 75 |
| **Rarity** | 70 |
| **Signal Score** | **73%** ◈ UNCOMMON |
| **Condition** | `peer.gross_margin_percentile > 60 and financials.gross_margin_delta > 0` |
| **Description** | Gross margin above sector P60 AND expanding YoY |
| **Rationale** | Expanding margin above sector median signals pricing power and operational leverage. Sector-relative condition avoids penalizing low-margin sectors (retail, services). |
| **SIC overrides** | None |

---

#### FUN-03 · Strong FCF Yield vs Sector 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 72 |
| **Rarity** | 68 |
| **Signal Score** | **70%** ◈ UNCOMMON |
| **Condition** | `peer.fcf_yield_percentile > 60` |
| **Description** | Free cash flow yield above sector P60 |
| **Rationale** | FCF yield is the cleanest measure of earnings quality — harder to manipulate than EPS. Above-sector FCF yield signals the company converts revenue to real cash better than peers. |
| **SIC overrides** | None |

---

#### FUN-04 · Positive Operating Leverage 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 78 |
| **Rarity** | 72 |
| **Signal Score** | **76%** ◈ UNCOMMON |
| **Condition** | `financials.op_leverage > 2.0` |
| **Description** | Revenue growing significantly faster than operating expenses (>2pp improvement) |
| **Rationale** | Positive operating leverage means each incremental revenue dollar flows increasingly to profit. This is the compounding engine of durable businesses. |
| **SIC overrides** | None |

---

#### FUN-05 · EPS Beat Streak 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 70 |
| **Rarity** | 65 |
| **Signal Score** | **68%** ◈ UNCOMMON |
| **Condition** | `financials.eps_beat_streak >= 3` |
| **Description** | EPS beat consensus estimates 3+ consecutive quarters |
| **Rationale** | Three consecutive beats suggests management consistently under-promises and over-delivers — a strong indicator of conservative guidance culture and execution quality. |
| **SIC overrides** | None |

---

#### FUN-06 · High Leverage vs Sector 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 85 |
| **Rarity** | 80 |
| **Signal Score** | **83%** ◆ RARE |
| **Condition** | `peer.debt_ebitda_percentile < 25` |
| **Description** | Debt/EBITDA in bottom quartile vs sector peers |
| **Rationale** | Sector-relative leverage flags companies that are more indebted than peers — not an absolute threshold, which would incorrectly flag utilities and REITs. |
| **SIC overrides** | `"6020-6099": "skip"` · `"6500-6552": "skip"` · `"4900-4991": "skip"` |

---

#### FUN-07 · Persistent Losses 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 82 |
| **Rarity** | 78 |
| **Signal Score** | **80%** ◈ UNCOMMON |
| **Condition** | `financials.net_income_streak_neg >= 3` |
| **Description** | Net income negative 3+ consecutive quarters |
| **Rationale** | Three quarters of losses indicates a structural problem, not a one-off. Excludes pre-revenue growth companies (see SIC overrides). |
| **SIC overrides** | `"2830-2836": "skip"` · `"7372-7379": {condition: "financials.net_income_streak_neg >= 6"}` |

---

#### FUN-08 · Critical Cash Runway 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 90 |
| **Rarity** | 92 |
| **Signal Score** | **91%** ◆ RARE |
| **Condition** | `financials.cash_runway_months < 12` |
| **Description** | Cash burn implies <12 months of remaining runway |
| **Rationale** | Sub-12-month runway forces dilutive capital raises or debt at unfavorable terms, or worse. This is an existential signal for pre-profitability companies. |
| **SIC overrides** | None |

---

#### FUN-09 · Gross Margin Compression 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 78 |
| **Rarity** | 72 |
| **Signal Score** | **76%** ◈ UNCOMMON |
| **Condition** | `financials.gross_margin_delta < -0.02` |
| **Description** | Gross margin contracting >200bps YoY |
| **Rationale** | Sustained margin compression signals pricing pressure, rising input costs, or competitive deterioration. More than 200bps is material and usually difficult to reverse quickly. |
| **SIC overrides** | None |

---

#### FUN-10 · Revenue Growth Decelerating 🟡 AMBER

| Property | Value |
|----------|-------|
| **Signal** | Caution |
| **Base Strength** | 45 |
| **Rarity** | 40 |
| **Signal Score** | **43%** ○ OCCASIONAL |
| **Condition** | `financials.rev_growth_delta < -0.03` |
| **Description** | Revenue growth decelerating >3pp from prior quarter |
| **Rationale** | Deceleration alone is not bearish — it depends on the absolute level. Classified AMBER: worth watching, especially if paired with elevated valuation. |
| **SIC overrides** | None |

---

#### FUN-11 · Cheap Relative to Sector 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 65 |
| **Rarity** | 55 |
| **Signal Score** | **61%** ○ OCCASIONAL |
| **Condition** | `peer.pe_percentile < 35` |
| **Description** | P/E ratio below sector P35 — cheap relative to peers |
| **Rationale** | Valuation alone is not a catalyst, but relative cheapness combined with other signals is a high-quality setup. Sector-relative avoids penalizing industries that structurally trade at lower multiples. |
| **SIC overrides** | `"6020-6099": {condition: "peer.pb_percentile < 35"}` · `"6500-6552": {condition: "peer.p_ffo_percentile < 35"}` · `"1311": {condition: "peer.ev_ebitda_percentile < 35"}` |

---

#### FUN-12 · Expensive + Decelerating 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 70 |
| **Rarity** | 65 |
| **Signal Score** | **68%** ◈ UNCOMMON |
| **Condition** | `peer.pe_percentile > 80 and financials.rev_growth_delta < 0` |
| **Description** | P/E above sector P80 while revenue growth is decelerating |
| **Rationale** | The most dangerous equity setup: paying a premium multiple for a business whose growth is slowing. Multiple compression + EPS deceleration = double impairment. |
| **SIC overrides** | `"6020-6099": {condition: "peer.pb_percentile > 80 and financials.rev_growth_delta < 0"}` |

---

### CATEGORY 4 — PRICE & TECHNICAL (PRC)

*Source: yfinance OHLCV data*

---

#### PRC-01 · Deep Drawdown, Intact Fundamentals 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 75 |
| **Rarity** | 70 |
| **Signal Score** | **73%** ◈ UNCOMMON |
| **Condition** | `price.pct_from_ath < -0.30 and financials.revenue_growth > 0` |
| **Description** | Stock down >30% from all-time high while revenue still growing |
| **Rationale** | A 30%+ drawdown on a fundamentally sound business frequently represents sentiment overshoot rather than fundamental deterioration — a potential value entry. |
| **SIC overrides** | None |

---

#### PRC-02 · Near 52-Week Low 🔵 BLUE

| Property | Value |
|----------|-------|
| **Signal** | Neutral |
| **Base Strength** | 40 |
| **Rarity** | 45 |
| **Signal Score** | **42%** ○ OCCASIONAL |
| **Condition** | `price.pct_from_52wk_low < 0.05` |
| **Description** | Stock within 5% of 52-week low |
| **Rationale** | Informational context. Directional signal depends on fundamentals. Raises alert level for other rules to fire in combination. |
| **SIC overrides** | None |

---

#### PRC-03 · Short Squeeze Setup 🟡 AMBER

| Property | Value |
|----------|-------|
| **Signal** | Caution / Speculative |
| **Base Strength** | 50 |
| **Rarity** | 55 |
| **Signal Score** | **52%** ○ OCCASIONAL |
| **Condition** | `price.short_float > 0.15 and price.change_30d > 0.10` |
| **Description** | Short float >15% with price already rising >10% in 30 days |
| **Rationale** | Rising price + high short interest creates mechanical short-covering pressure. Not directionally confirmed — classified AMBER. Upgrades to PURPLE if combined with catalyst. |
| **SIC overrides** | None |

---

#### PRC-04 · Volume Spike 🟡 AMBER

| Property | Value |
|----------|-------|
| **Signal** | Caution |
| **Base Strength** | 45 |
| **Rarity** | 50 |
| **Signal Score** | **47%** ○ OCCASIONAL |
| **Condition** | `price.volume_ratio_30d > 3.0` |
| **Description** | Today's volume >3x the 30-day average |
| **Rationale** | Unusual volume precedes significant price moves but does not indicate direction. Classified AMBER as a context signal requiring confirmation from other rules. |
| **SIC overrides** | None |

---

#### PRC-05 · New 52-Week High 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 65 |
| **Rarity** | 50 |
| **Signal Score** | **59%** ○ OCCASIONAL |
| **Condition** | `price.pct_from_52wk_high > -0.01` |
| **Description** | Stock making new 52-week high |
| **Rationale** | New highs signal that all holders are in profit — no overhead resistance. Trend-following signal, strongest when accompanied by fundamental confirmation. |
| **SIC overrides** | None |

---

#### PRC-06 · Momentum Breakdown 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 70 |
| **Rarity** | 60 |
| **Signal Score** | **66%** ◈ UNCOMMON |
| **Condition** | `price.change_30d < -0.20` |
| **Description** | Stock down >20% in 30 days |
| **Rationale** | A 20% drop in 30 days indicates active selling pressure, not normal volatility. Often a leading indicator of further declines unless accompanied by clear identifiable catalyst resolution. |
| **SIC overrides** | None |

---

#### PRC-07 · Reclaim of 200-Day MA 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 72 |
| **Rarity** | 65 |
| **Signal Score** | **69%** ◈ UNCOMMON |
| **Condition** | `price.above_200d_ma == True and price.change_30d > 0` |
| **Description** | Price reclaims 200-day moving average after being below it |
| **Rationale** | The 200-day MA is watched by institutional managers. Reclaiming it after a period below is a technical regime change signal and often triggers systematic buying. |
| **SIC overrides** | None |

---

#### PRC-08 · Death Cross 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 75 |
| **Rarity** | 68 |
| **Signal Score** | **72%** ◈ UNCOMMON |
| **Condition** | `price.death_cross == True` |
| **Description** | 50-day MA crosses below 200-day MA (death cross) |
| **Rationale** | A death cross confirms that short-term price action has deteriorated below long-term trend. While a lagging indicator, it signals that momentum has structurally shifted bearish. |
| **SIC overrides** | None |

---

#### PRC-09 · Golden Cross 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 72 |
| **Rarity** | 65 |
| **Signal Score** | **69%** ◈ UNCOMMON |
| **Condition** | `price.golden_cross == True` |
| **Description** | 50-day MA crosses above 200-day MA (golden cross) |
| **Rationale** | A golden cross confirms that short-term price action has recovered above long-term trend. Often triggers systematic momentum buying from algorithmic and trend-following funds. |
| **SIC overrides** | None |

---

### CATEGORY 5 — MACRO SIGNALS (MAC)

*Source: FRED API (requires FRED API key in config.yaml)*
*These rules are ticker-independent — they reflect the macro environment*
*for all equity positions, not company-specific signals.*

---

#### MAC-01 · Yield Curve Inverted 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 70 |
| **Rarity** | 90 |
| **Signal Score** | **78%** ◆ RARE |
| **Condition** | `macro.spread_10y_2y < 0` |
| **Description** | 10Y-2Y Treasury yield spread is negative |
| **Rationale** | Yield curve inversion has preceded every US recession of the past 50 years. It reflects expectations of near-term rate cuts driven by economic weakness. |
| **SIC overrides** | None |

---

#### MAC-02 · Yield Curve Normalizing 🔵 BLUE

| Property | Value |
|----------|-------|
| **Signal** | Neutral |
| **Base Strength** | 50 |
| **Rarity** | 80 |
| **Signal Score** | **62%** ◈ UNCOMMON |
| **Condition** | `macro.spread_10y_2y > 0 and macro.spread_10y_2y < 0.50` |
| **Description** | Yield curve dis-inverting (was negative, now 0–50bps) |
| **Rationale** | Transition state between inversion and normal. Historically, this phase is actually associated with the worst equity drawdowns as recession becomes apparent. Informational — classified BLUE. |
| **SIC overrides** | None |

---

#### MAC-03 · VIX Fear Spike 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 75 |
| **Rarity** | 85 |
| **Signal Score** | **79%** ◆ RARE |
| **Condition** | `macro.vix > 30` |
| **Description** | VIX above 30 — extreme fear / potential buying opportunity |
| **Rationale** | VIX >30 marks capitulation conditions. Historically, buying during VIX spikes above 30 has produced significantly above-average forward returns. Contrarian signal. |
| **SIC overrides** | None |

---

#### MAC-04 · VIX Complacency 🔵 BLUE

| Property | Value |
|----------|-------|
| **Signal** | Neutral |
| **Base Strength** | 55 |
| **Rarity** | 60 |
| **Signal Score** | **57%** ○ OCCASIONAL |
| **Condition** | `macro.vix < 15` |
| **Description** | VIX below 15 — low fear, elevated complacency |
| **Rationale** | Low VIX means options are cheap but also means markets are not pricing any risk premium. Historically, prolonged low-VIX periods precede volatility spikes. Monitor, not actionable alone. |
| **SIC overrides** | None |

---

#### MAC-05 · Fed Rate Cut Cycle 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 80 |
| **Rarity** | 88 |
| **Signal Score** | **83%** ◆ RARE |
| **Condition** | `macro.fed_cutting == True` |
| **Description** | Federal Reserve has entered a rate cutting cycle |
| **Rationale** | Rate cut cycles expand P/E multiples, reduce discount rates on future cash flows, and lower corporate borrowing costs. Historically one of the strongest macro tailwinds for equities. |
| **SIC overrides** | None |

---

#### MAC-06 · Fed Rate Hike Cycle 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 75 |
| **Rarity** | 82 |
| **Signal Score** | **78%** ◆ RARE |
| **Condition** | `macro.fed_hiking == True` |
| **Description** | Federal Reserve is actively raising rates |
| **Rationale** | Rate hike cycles compress P/E multiples, increase discount rates, and raise corporate borrowing costs. Most damaging to long-duration assets (growth equities). |
| **SIC overrides** | None |

---

#### MAC-07 · CPI Surprise 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 72 |
| **Rarity** | 80 |
| **Signal Score** | **75%** ◈ UNCOMMON |
| **Condition** | `macro.cpi_surprise > 0.003` |
| **Description** | CPI came in >0.3pp above consensus estimate |
| **Rationale** | A significant upside CPI surprise forces markets to price more Fed tightening. Causes rapid P/E compression, especially in growth names. |
| **SIC overrides** | None |

---

#### MAC-08 · Strong Dollar Headwind 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 65 |
| **Rarity** | 70 |
| **Signal Score** | **67%** ◈ UNCOMMON |
| **Condition** | `macro.dxy_change_30d > 0.05` |
| **Description** | US Dollar index (DXY) rising >5% in 30 days |
| **Rationale** | A rapidly strengthening dollar is a headwind for multinationals reporting international revenue in USD. Particularly impacts large-cap tech and industrials with >40% international revenue. |
| **SIC overrides** | None |

---

#### MAC-09 · Credit Spreads Widening 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 78 |
| **Rarity** | 82 |
| **Signal Score** | **80%** ◈ UNCOMMON |
| **Condition** | `macro.hy_spread_change_30d > 50` |
| **Description** | High-yield credit spreads widening >50bps in 30 days |
| **Rationale** | Credit markets lead equity markets. Widening HY spreads signal rising perceived default risk and often precede equity selloffs by 2-6 weeks. |
| **SIC overrides** | None |

---

#### MAC-10 · Credit Spreads Tightening 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 75 |
| **Rarity** | 80 |
| **Signal Score** | **77%** ◈ UNCOMMON |
| **Condition** | `macro.hy_spread_change_30d < -50` |
| **Description** | High-yield credit spreads tightening >50bps in 30 days |
| **Rationale** | Tightening spreads signal improving risk appetite and reduced perceived default probability across the market — a systemic tailwind for equity risk premiums. |
| **SIC overrides** | None |

---

### CATEGORY 6 — CONFLUENCE RULES (CMP)

*Composite rules fire only when multiple base rules align simultaneously.*
*They carry 2× the ORCA Score weight of individual rules.*
*These represent the highest-conviction signals in the ORCA system.*

---

#### CMP-01 · Strong Long Setup 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long (HIGH CONVICTION) |
| **Base Strength** | 95 |
| **Rarity** | 99 |
| **Signal Score** | **97%** ◆ RARE |
| **Condition** | `INS-01 and PRC-01 and FUN-01` |
| **Description** | Insider cluster buy + deep drawdown + sustained revenue growth all fire simultaneously |
| **Rationale** | The classic "buy the dip on a fundamentally strong business with insider conviction" setup. All three elements must be present to confirm. |
| **ORCA weight** | +24 (2× multiplier) |

---

#### CMP-02 · Distress Signal 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short (HIGH CONVICTION) |
| **Base Strength** | 96 |
| **Rarity** | 99 |
| **Signal Score** | **97%** ◆ RARE |
| **Condition** | `FIL-06 and FUN-08 and INS-04` |
| **Description** | Going concern + critical cash runway + insider cluster sell |
| **Rationale** | Three independent indicators of existential distress firing simultaneously. The combination of auditor doubt, cash crisis, and insider exit is the highest-conviction bearish composite. |
| **ORCA weight** | −36 (2× multiplier) |

---

#### CMP-03 · Crisis Buy Window 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long (CONTRARIAN) |
| **Base Strength** | 93 |
| **Rarity** | 99 |
| **Signal Score** | **96%** ◆ RARE |
| **Condition** | `MAC-03 and PRC-02 and INS-02` |
| **Description** | VIX >30 + stock near 52-week low + large insider buy |
| **Rationale** | Market-wide fear (VIX), individual stock fear (52wk low), and insider conviction (large buy) converge. This is the setup that produces the highest forward returns in backtesting. |
| **ORCA weight** | +24 (2× multiplier) |

---

#### CMP-04 · Clean Bull Setup 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 88 |
| **Rarity** | 97 |
| **Signal Score** | **92%** ◆ RARE |
| **Condition** | `green_count >= 4 and red_count == 0` |
| **Description** | 4+ GREEN signals firing with zero RED signals |
| **Rationale** | Multiple independent bullish signals with no conflicting bearish signals is a clean, unambiguous setup. The absence of RED is as important as the presence of GREEN. |
| **ORCA weight** | +24 (2× multiplier) |

---

#### CMP-05 · Distribution Top 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 90 |
| **Rarity** | 98 |
| **Signal Score** | **93%** ◆ RARE |
| **Condition** | `INS-04 and PRC-06 and FUN-10` |
| **Description** | Insider cluster sell + price momentum breakdown + revenue deceleration |
| **Rationale** | The classic distribution top: insiders exiting, price breaking down, and fundamentals deteriorating. Often precedes 30–60% drawdowns in growth names. |
| **ORCA weight** | −36 (2× multiplier) |

---

#### CMP-06 · Value Trap Warning 🔴 RED

| Property | Value |
|----------|-------|
| **Signal** | Bearish — Sell / Short |
| **Base Strength** | 88 |
| **Rarity** | 97 |
| **Signal Score** | **92%** ◆ RARE |
| **Condition** | `FUN-07 and FUN-09 and PRC-06` |
| **Description** | Persistent losses + gross margin compression + price breakdown |
| **Rationale** | A stock can look "cheap" on P/E or P/B while the business is structurally deteriorating. This composite identifies value traps before they destroy capital. |
| **ORCA weight** | −36 (2× multiplier) |

---

#### CMP-07 · Breakout Confirmation 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long |
| **Base Strength** | 85 |
| **Rarity** | 95 |
| **Signal Score** | **89%** ◆ RARE |
| **Condition** | `PRC-05 and PRC-09 and FUN-01` |
| **Description** | New 52-week high + golden cross + sustained revenue growth |
| **Rationale** | Technical breakout confirmed by fundamental momentum. New highs on a golden cross with accelerating fundamentals is the classic institutional accumulation setup. |
| **ORCA weight** | +24 (2× multiplier) |

---

#### CMP-08 · Insider Conviction Low 🟢 GREEN

| Property | Value |
|----------|-------|
| **Signal** | Bullish — Buy / Long (CONTRARIAN) |
| **Base Strength** | 90 |
| **Rarity** | 98 |
| **Signal Score** | **93%** ◆ RARE |
| **Condition** | `INS-05 and PRC-01 and MAC-03` |
| **Description** | Insider buy near 52-week low + deep drawdown + VIX spike |
| **Rationale** | Insider conviction at a price near the annual low during a market fear spike is one of the most historically reliable long setups. Three independent signals converge on the same conclusion. |
| **ORCA weight** | +24 (2× multiplier) |

---

## 4. Adding Custom Rules

Edit `rules.yaml` directly. ORCA reloads rules on every new scan — no restart needed.

### Template for a new rule

```yaml
- id: INS-08                        # Next available ID in category
  name: "Your rule name"            # Short plain-English name (shown in UI)
  category: insider                 # insider | filing | fundamental | price | macro | composite
  color: GREEN                      # GREEN | RED | BLUE | AMBER | PURPLE
  base_strength: 75                 # 0–100, your assessment of predictive power
  rarity: 70                        # 0–100, how rarely this fires
  condition: "form4.ceo_bought"     # Python expression using namespace variables
  description: "Detailed description shown in tooltip and report"
  enabled: true                     # set false to disable without deleting
  sic_overrides:                    # optional
    "2830-2836": "skip"             # skip for biotech
    "6020-6099":                    # alternate condition for banks
      condition: "form4.ceo_bought and form4.largest_buy_usd > 500000"
```

### Available namespace variables
See Section 2 of this document for the complete list of variables available
in rule conditions (`form4.*`, `filing.*`, `financials.*`, `peer.*`,
`price.*`, `macro.*`).

---

## 5. Quick Reference Card

```
INS-01  Insider cluster buy (2+ in 30d)          GREEN  94% ◆
INS-02  Large insider buy (>$1M)                 GREEN  91% ◆
INS-03  CEO/CFO buys                             GREEN  93% ◆
INS-04  Insider cluster sell (3+ in 14d)          RED   86% ◆
INS-05  Insider buy near 52wk low                GREEN  92% ◆
INS-06  Large position liquidation (>30%)          RED   72% ◈
INS-07  No buying in 12 months                   BLUE   22% ·

FIL-01  RPO growth >50% YoY                     GREEN  89% ◆
FIL-02  Unscheduled CEO/CFO departure             RED   95% ◆
FIL-03  Material contract/partnership            GREEN  67% ◈
FIL-04  Guidance raised                          GREEN  77% ◈
FIL-05  Guidance lowered                          RED   80% ◆
FIL-06  Going concern language                    RED   96% ◆
FIL-07  Auditor change                            RED   92% ◆
FIL-08  Buyback >5% of float                    GREEN  84% ◆
FIL-09  Tier-1 fund new 13F position            GREEN  76% ◈
FIL-10  Activist 13D filed                       BLUE   62% ◈
FIL-11  Short-seller report                       RED   89% ◆
FIL-12  Equity dilution >10%                      RED   85% ◆

FUN-01  Revenue growth >20% × 3 quarters        GREEN  78% ◈
FUN-02  Gross margin > P60 + expanding          GREEN  73% ◈
FUN-03  FCF yield > P60 vs sector               GREEN  70% ◈
FUN-04  Operating leverage >2pp                 GREEN  76% ◈
FUN-05  EPS beat streak (3+ quarters)           GREEN  68% ◈
FUN-06  Leverage bottom quartile vs sector        RED   83% ◆
FUN-07  Net loss 3+ consecutive quarters          RED   80% ◈
FUN-08  Cash runway <12 months                    RED   91% ◆
FUN-09  Gross margin compression >200bps          RED   76% ◈
FUN-10  Revenue growth decelerating >3pp        AMBER  43% ○
FUN-11  P/E below sector P35                    GREEN  61% ○
FUN-12  P/E above P80 + decelerating             RED   68% ◈

PRC-01  >30% from ATH, fundamentals intact      GREEN  73% ◈
PRC-02  Within 5% of 52-week low                BLUE   42% ○
PRC-03  Short float >15% + rising 10% in 30d   AMBER  52% ○
PRC-04  Volume spike >3x 30d average            AMBER  47% ○
PRC-05  New 52-week high                        GREEN  59% ○
PRC-06  Price down >20% in 30 days               RED   66% ◈
PRC-07  Reclaim of 200-day MA                   GREEN  69% ◈
PRC-08  Death cross                               RED   72% ◈
PRC-09  Golden cross                            GREEN  69% ◈

MAC-01  Yield curve inverted (10Y-2Y < 0)        RED   78% ◆
MAC-02  Yield curve normalizing (0–50bps)        BLUE   62% ◈
MAC-03  VIX > 30 (fear spike)                   GREEN  79% ◆
MAC-04  VIX < 15 (complacency)                  BLUE   57% ○
MAC-05  Fed rate cut cycle confirmed             GREEN  83% ◆
MAC-06  Fed rate hike cycle active                RED   78% ◆
MAC-07  CPI surprise >0.3pp above estimate        RED   75% ◈
MAC-08  DXY rising >5% in 30d                    RED   67% ◈
MAC-09  HY spreads widening >50bps in 30d        RED   80% ◈
MAC-10  HY spreads tightening >50bps in 30d    GREEN  77% ◈

CMP-01  Strong long setup              GREEN  97% ◆  INS-01+PRC-01+FUN-01
CMP-02  Distress signal                  RED  97% ◆  FIL-06+FUN-08+INS-04
CMP-03  Crisis buy window              GREEN  96% ◆  MAC-03+PRC-02+INS-02
CMP-04  Clean bull setup (4+ GREEN)    GREEN  92% ◆
CMP-05  Distribution top                 RED  93% ◆  INS-04+PRC-06+FUN-10
CMP-06  Value trap warning               RED  92% ◆  FUN-07+FUN-09+PRC-06
CMP-07  Breakout confirmation          GREEN  89% ◆  PRC-05+PRC-09+FUN-01
CMP-08  Insider conviction low         GREEN  93% ◆  INS-05+PRC-01+MAC-03
```

---

*Project ORCA · GSR Reference v1.0 · April 2026*
*Edit rules.yaml to modify, add, or disable any rule.*
