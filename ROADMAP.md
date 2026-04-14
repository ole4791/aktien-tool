# Stock Analysis Tool – Feature Roadmap

## ✅ Completed Features
- [x] Basic DCF calculation with WACC
- [x] Value Score with fair weighting (sector-specific)
- [x] Historical charts (price, P/E, FCF, intrinsic value)
- [x] Persistent database via GitHub API
- [x] Portfolio tracking with recommendations
- [x] Batch analysis with index selection
- [x] Dashboard with Top 10 opportunities
- [x] Methodology page with sources
- [x] English language throughout
- [x] Search with autocomplete suggestions
- [x] Dividend display bug fixed
- [x] Decimal places standardized to 2
- [x] Value Score fair weighting – inapplicable categories skipped
- [x] PayPal/Fintech misclassification fixed
- [x] Automatic FCF growth rate calculation (per stock)
- [x] Rate limiting fix – 2s sleep, retry logic

---

## 🔴 Priority 0 – DCF Methodology Improvements
*Oberste Priorität: korrekte Berechnung vor neuen Features*

### 0.1 Three-Scenario DCF – HIGHEST PRIORITY
**Why:** A single DCF value is misleading. The range shows how sensitive the result is.
**Data available:** ✅ No new data needed – calculated from existing assumptions
**Impact:** Largest single improvement to analysis quality

Implementation:
```python
scenarios = {
    "Bear": {
        "growth":   growth * 0.70,   # -30% vs base
        "wacc":     wacc + 0.01,     # +100bps
        "terminal": terminal - 0.005, # -50bps
        "weight":   0.25
    },
    "Base": {
        "growth":   growth,
        "wacc":     wacc,
        "terminal": terminal,
        "weight":   0.50
    },
    "Bull": {
        "growth":   growth * 1.30,   # +30% vs base
        "wacc":     wacc - 0.01,     # -100bps
        "terminal": terminal + 0.005, # +50bps
        "weight":   0.25
    }
}

# Weighted fair value
weighted_value = sum(
    run_dcf_single(s["growth"], s["wacc"], s["terminal"]) * s["weight"]
    for s in scenarios.values()
)
```

Display in Analysis page:
- Three columns side by side: Bear | Base | Bull
- Each shows intrinsic value and deviation from current price
- Weighted fair value prominently shown
- Margin of Safety applied to weighted value
- Bar chart comparing all three scenarios

**Claude Code instruction:**
Read ROADMAP.md section 0.1 and app.py.
Implement three-scenario DCF analysis:

Calculate Bear/Base/Bull scenarios as defined in ROADMAP
Show all three intrinsic values side by side in Analysis page
Calculate weighted fair value (Bear 25%, Base 50%, Bull 25%)
Apply Margin of Safety to weighted value
Add bar chart comparing three scenarios
Keep existing single-value calculation as "Base Case"
Commit and push. Do nothing else.


### 0.2 Live Risk-Free Rate + Blume-Adjusted Beta
**Why:** Current WACC uses fixed 4.0% risk-free rate and raw beta – both imprecise
**Data available:**
- ✅ Live 10Y Treasury yield: `yf.Ticker("^TNX").info["regularMarketPrice"]`
- ✅ Raw beta: `info["beta"]`
- ✅ Region detection: from `info["country"]`
- ❌ Country Risk Premium: NOT implemented – requires Damodaran external data

Implementation:
```python
def get_risk_free_rate():
    """Live 10Y Treasury yield"""
    try:
        treasury = yf.Ticker("^TNX")
        rate = treasury.info.get("regularMarketPrice", 4.0)
        return rate / 100  # convert from percentage
    except:
        return 0.04  # fallback

def blume_adjusted_beta(raw_beta):
    """Blume adjustment: mean reversion toward 1.0"""
    if not raw_beta:
        return 1.0
    return 0.67 * raw_beta + 0.33 * 1.0

def get_equity_risk_premium(country):
    """ERP by region – based on Damodaran averages"""
    erp_map = {
        "United States": 0.055,
        "Germany": 0.060,
        "Switzerland": 0.058,
        "United Kingdom": 0.060,
        "France": 0.062,
        "Netherlands": 0.059,
        "Japan": 0.065,
    }
    return erp_map.get(country, 0.060)  # default 6% for unknown
```

Display changes:
- Show live risk-free rate with date fetched
- Show raw beta vs adjusted beta
- Show ERP used and which region detected
- Show final WACC with all components visible

**Claude Code instruction:**
Read ROADMAP.md section 0.2 and app.py.
Improve WACC calculation:

Add get_risk_free_rate() to fetch live 10Y Treasury yield from ^TNX
Add blume_adjusted_beta() function as defined in ROADMAP
Add get_equity_risk_premium() with regional mapping
Update calculate_wacc() to use all three functions
Show all components in WACC tab: live rate, raw vs adjusted beta, ERP
Keep fallback values if live data unavailable
Commit and push. Do nothing else.


### 0.3 Terminal Value Plausibility Check
**Why:** Terminal Value is 60-80% of total DCF value – small errors have huge impact
**Data available:** ✅ All internally calculable – no new data needed

Implementation:
```python
def check_terminal_value(tv_total, ebitda, wacc, terminal_growth):
    """
    Plausibility checks for terminal value
    Returns warnings if assumptions seem unrealistic
    """
    warnings = []

    # Check 1: Terminal growth rate vs GDP growth
    if terminal_growth > 0.025:
        warnings.append(
            f"⚠️ Terminal growth {terminal_growth*100:.1f}% exceeds "
            f"long-term GDP growth (~2.5%). Consider reducing."
        )

    # Check 2: Implied EV/EBITDA multiple
    if ebitda and ebitda > 0:
        implied_multiple = tv_total / ebitda
        if implied_multiple > 25:
            warnings.append(
                f"⚠️ Terminal Value implies EV/EBITDA of {implied_multiple:.1f}x "
                f"– historically high. Most sectors trade at 8-15x."
            )
        elif implied_multiple < 4:
            warnings.append(
                f"⚠️ Terminal Value implies EV/EBITDA of {implied_multiple:.1f}x "
                f"– very low. Check WACC and growth assumptions."
            )

    # Check 3: TV as % of total enterprise value
    return warnings, implied_multiple if ebitda else None
```

Display:
- Show implied EV/EBITDA multiple in DCF tab
- Show TV as % of total enterprise value
- Show warnings if any checks fail
- Green checkmark if all checks pass

**Claude Code instruction:**
Read ROADMAP.md section 0.3 and app.py.
Add terminal value plausibility checks:

Add check_terminal_value() function as defined in ROADMAP
Show implied EV/EBITDA multiple in DCF Calculation tab
Show TV as % of total enterprise value
Show warnings if terminal growth > 2.5% or implied multiple > 25x
Show green checkmark if all checks pass
Commit and push. Do nothing else.


### 0.4 Full Transparency – All Calculation Steps Visible
**Why:** User must be able to follow and verify every number
**Data available:** ✅ All already calculated – only display improvements needed

Every analysis should show:

DCF Inputs:
- FCF base used (which years averaged, why)
- Growth rate (how calculated – historical CAGR, analyst estimate, sector default)
- Terminal growth rate
- WACC components (risk-free rate + source, beta raw vs adjusted, ERP + region)
- Margin of Safety

DCF Calculation steps:
- Sum of discounted FCFs years 1-10
- Terminal Value (absolute + as % of total)
- Implied EV/EBITDA from Terminal Value
- Enterprise Value
- Net Debt breakdown (gross debt, cash, net)
- Equity Value
- Diluted shares outstanding
- Intrinsic Value per share
- With Margin of Safety

Scenario Analysis:
- All three scenarios with assumptions
- Weighted fair value
- Sensitivity table: how intrinsic value changes with ±1% WACC and ±1% growth

**Claude Code instruction:**
Read ROADMAP.md section 0.4 and app.py.
Improve transparency in DCF Calculation tab:

Show FCF base calculation (which years used, average)
Show growth rate source (historical CAGR / analyst estimate / sector default)
Show WACC components: risk-free rate with source, raw beta, adjusted beta, ERP
Show Net Debt breakdown: gross debt, cash, net debt
Show Terminal Value as % of Enterprise Value
Add sensitivity table: intrinsic value for WACC ±1% and Growth ±1%
Commit and push. Do nothing else.


---



---

## 🟡 Priority 2 – Core Improvements

### 2.1 Index Selection for Batch Analysis
**Status:** Implemented
**Verify:** DAX, S&P, NASDAQ dropdowns work correctly

### 2.2 Index Filter in Database
Add "Index" column to database entries and filter in Database page.

**Claude Code instruction:**
Read ROADMAP.md section 2.2 and app.py.
Add index tracking:

When saving batch results add "Index" field with selected index name
Add index filter to Database page
Commit and push. Do nothing else.


### 2.3 Stock Detail View from Database
Make database rows clickable → opens full Analysis page for that stock.

**Claude Code instruction:**
Read ROADMAP.md section 2.3 and app.py.
Make database rows clickable:

Add "Analyze" button per row
Clicking sets st.session_state.selected_symbol
Navigates to Analysis page with stock pre-loaded
Commit and push. Do nothing else.


### 2.4 Tooltips & Terminology
Add ℹ️ tooltips to all metrics. Priority terms:

| Term | Explanation |
|------|-------------|
| MoS | Margin of Safety – buffer between intrinsic value and max buy price. Only buy if price is at least 25% below intrinsic value. |
| WACC | Weighted Average Cost of Capital – discount rate in DCF. Minimum return investors expect. Higher = more conservative valuation. |
| DCF | Discounted Cash Flow – values company by forecasting future cash flows and discounting to today. |
| FCF | Free Cash Flow – cash generated after all expenses and investments. Foundation of DCF. |
| Terminal Value | Present value of all cash flows beyond 10-year forecast. Usually 60-80% of total DCF value. |
| Beta | Stock volatility vs market. 1.0 = same as market. Higher = more volatile = higher WACC. |
| Blume Beta | Adjusted beta = 0.67 × raw beta + 0.33 × 1.0. Accounts for mean reversion toward market average. |
| ERP | Equity Risk Premium – extra return investors demand for stocks vs risk-free bonds. ~5.5% USA, ~6% Europe. |
| EV/EBITDA | Enterprise value multiple. Removes debt and tax effects. Below 8 = attractive, 8-12 = fair. |
| Deviation % | Distance from intrinsic value. Negative = undervalued. -20% = trades 20% below fair value. |
| Weighted Fair Value | Bear×25% + Base×50% + Bull×25% – more honest than single DCF estimate. |
| Implied Multiple | EV/EBITDA implied by Terminal Value. Should be 8-20x for most sectors. Warning if >25x. |

**Claude Code instruction:**
Read ROADMAP.md section 2.4 and app.py.
Add tooltips using st.metric() help parameter and ℹ️ expanders:

All metrics in Analysis page get tooltip
Value Score categories get explanation
Add Glossary section to Methodology page
Priority: MoS, WACC, DCF, FCF, Deviation %, Weighted Fair Value
Commit and push. Do nothing else.


### 2.5 Value Score Category Explanations
Show WHY each category received its score.

Examples:
- "DCF Deviation 18/25 – Stock trades 22% below weighted fair value."
- "FCF Quality 14/20 – FCF $8.2B positive, yield 4.1%, CAGR 12%."
- "Valuation 8/25 – P/E 24x above average, EV/EBITDA 14x elevated."
- "N/A – Financial sector: DCF not applicable for banks."

### 2.6 Additional Database Filters
Add to Database page:
- Market Cap: Mega (>$200B) / Large / Mid / Small
- Value Score minimum slider
- Undervalued only checkbox
- FCF positive only checkbox
- Dividend minimum %
- ROE minimum %
- Index filter (after 2.1)

**Claude Code instruction:**
Read ROADMAP.md section 2.6 and app.py.
Add filters to Database page:

Market Cap category filter
Value Score minimum slider
Undervalued only checkbox
FCF positive only checkbox
Dividend minimum slider
Commit and push. Do nothing else.


---

## 🟠 Priority 3 – Further Methodology

### 3.1 Stock Type Detection & Methodology Recommendation
Show at top of Analysis which method is best for this stock:
📊 Apple – Quality Growth
✅ Two-Stage DCF   Best – strong FCF CAGR 15%
✅ PEG Ratio       Useful – validates growth premium
⚠️  P/E            Use in tech sector context only
❌  DDM             Not applicable – dividend only 0.5%

### 3.2 Two-Stage DCF
- Phase 1 (Years 1-5): high growth rate
- Phase 2 (Years 6-10): linear decline toward terminal
- Especially important for growth stocks

### 3.3 PEG Ratio
```python
PEG = P/E / FCF_CAGR_percent
# PEG < 1.0 = attractive even for growth stocks
# PEG > 2.0 = expensive regardless of growth
```

### 3.4 Piotroski F-Score
9-point quality checklist. Proven +13.4% annual outperformance.
Full implementation in original ROADMAP.

### 3.5 DDM for Dividend Stocks
Gordon Growth Model for dividend yield > 2%:
V = D1 / (r - g)

---

## 🔵 Priority 4 – User Experience

### 4.1 Stock Comparison
Side-by-side comparison of 2-3 stocks.

### 4.2 Watchlist with Notes
Personal watchlist with target prices and notes.
Persist in watchlist.json on GitHub.

### 4.3 Risk Flags
Auto-generate risk warnings:
- 🔴 FCF negative 2+ years
- 🔴 High debt ratio
- 🟠 Cyclical sector
- 🟠 Regulatory risk

### 4.4 Soft Color Scheme
Replace harsh red/green with soft gradients throughout.

---

## 🟣 Priority 5 – Automation & Scale

### 5.0 Pre-populated Database for Launch
Run full batch before first public rollout.
Target: 150+ stocks with valid DCF results.

### 5.1 Daily Auto-Update via GitHub Actions
```yaml
name: Daily Update
on:
  schedule:
    - cron: '0 6 * * 1-5'
```

### 5.2 Expanded Universe (500+ stocks)
Full S&P 500, DAX 40, STOXX 600 value subset, FTSE 100.

### 5.3 Trade Republic Integration
CSV import from TR export as first step.

---

## 📝 Technical Notes for Claude Code

### Project Overview
Value investing tool. DCF is core methodology.
Streamlit + yfinance + GitHub persistence + Streamlit Cloud.

### Key Files
aktien-tool/
├── app.py              # main application
├── requirements.txt    # dependencies
├── ROADMAP.md          # this file
├── datenbank.json      # stock database
└── portfolio.json      # portfolio data

### Dependencies
yfinance>=0.2.67
pandas
streamlit
plotly
requests
matplotlib

### Secrets
```toml
GITHUB_TOKEN = "ghp_..."
GITHUB_REPO = "username/aktien-tool"
```

### Session Start Command
Read ROADMAP.md and app.py.
Tell me which Priority 0 items are still open.
Do not make any changes yet.

### Stable Fallback Version
Commit: 3c1a1f0
Restore: git checkout 3c1a1f0 -- app.py

### Rate Limit Recovery
If app shows rate limit error:
1. Streamlit: Manage app → Reboot
2. Local: pip3 install yfinance --upgrade

### DCF Methodology Decisions
Based on analysis of available yfinance data:

✅ IMPLEMENT:
- Three-scenario DCF (Bear/Base/Bull) – no new data needed
- Live risk-free rate from ^TNX – available via yfinance
- Blume-adjusted beta – calculated from raw beta
- Regional ERP mapping – hardcoded constants
- Terminal Value plausibility check – calculated internally
- Full transparency of all calculation steps

❌ DO NOT IMPLEMENT (data not reliably available):
- FCFF bottom-up (EBIT - taxes + D&A - ΔNWC - CapEx)
  → EBIT not reliable in yfinance for all stocks
  → ΔNWC calculation too error-prone
  → Risk: breaks calculation for many stocks
- Country Risk Premium
  → Requires Damodaran external data not in yfinance
- Pension liabilities, minority interests
  → Not consistently available in yfinance
- Full historical normalization of one-off items
  → Requires human judgment, not automatable

INSTEAD: Use 3-year average FCF as robust base
(already implemented – handles outliers naturally)

---

## 📋 Glossary

| Term | Explanation |
|------|-------------|
| MoS | Margin of Safety – only buy at 25%+ discount to intrinsic value |
| WACC | Weighted Average Cost of Capital – DCF discount rate |
| DCF | Discounted Cash Flow – core valuation method |
| FCF | Free Cash Flow – cash after all expenses and investments |
| FCFF | Free Cash Flow to Firm – available to all capital providers |
| Terminal Value | PV of all cash flows beyond 10-year forecast |
| Blume Beta | Adjusted beta = 0.67×raw + 0.33×1.0 (mean reversion) |
| ERP | Equity Risk Premium – ~5.5% USA, ~6% Europe |
| Implied Multiple | EV/EBITDA implied by Terminal Value (should be 8-20x) |
| Weighted Fair Value | Bear×25% + Base×50% + Bull×25% |
| Deviation % | Price vs intrinsic value. Negative = undervalued |
| PEG | P/E divided by growth rate. Below 1.0 = attractive |
| Piotroski | 9-point quality score. Above 7 = strong fundamentals |

Commit mit Update ROADMAP - DCF methodology improvements auf GitHub.
Für die nächste Claude Code Session:
Read ROADMAP.md and app.py.
Start with Priority 0.1 – Three-Scenario DCF.
Implement Bear/Base/Bull scenarios as defined in ROADMAP.
Show weighted fair value prominently.
Commit and push after. Do nothing else until I confirm.
Das ist der wichtigste nächste Schritt – alles andere baut darauf auf.Sonnet 4.6
