# Stock Analysis Tool – Feature Roadmap

## ✅ Completed Features
- [x] DCF calculation with WACC (three scenarios Bear/Base/Bull)
- [x] Weighted fair value (Bear 25% / Base 50% / Bull 25%)
- [x] Live risk-free rate from ^TNX
- [x] Blume-adjusted beta (0.67 × raw + 0.33 × 1.0)
- [x] Regional ERP mapping (USA 5.5%, Europe 6.0%, EM 6.5%)
- [x] Terminal Value plausibility check (implied EV/EBITDA, TV%)
- [x] Full transparency of all calculation steps
- [x] Sensitivity table (WACC ±1% / Growth ±1%)
- [x] Automatic FCF growth rate per stock (3 sources, 20% haircut)
- [x] Median FCF base (outlier protection)
- [x] Currency conversion with reliability indicator
- [x] Value Score with fair weighting (inapplicable categories skipped)
- [x] Dividend display bug fixed
- [x] Decimal places standardized to 2
- [x] PayPal/Fintech misclassification fixed (DCF_EXEMPT / DCF_APPLICABLE)
- [x] Rate limiting fix (2s sleep, retry logic)
- [x] Historical charts (price, P/E, FCF, intrinsic value)
- [x] Persistent database via GitHub API
- [x] Portfolio tracking with recommendations
- [x] Batch analysis with index selection
- [x] Dashboard with Top 10 opportunities
- [x] Methodology page with sources
- [x] Search with autocomplete

---

## 🔴 Priority 0 – DCF Accuracy Fixes
*These affect calculation quality for many stocks – fix before adding features*

### 0.1 Negative Equity Fix – CRITICAL
**Problem:** Stocks with negative book equity (ABBV, CL, MO, MCD, YUM, ITW, HON)
show wrong intrinsic values because the equity bridge breaks.
**Root cause:** When totalStockholdersEquity < 0, dividing by shares gives
a misleading result. The DCF enterprise value is correct but the equity
conversion fails.
**Affected stocks:** ABBV ($260 tool vs ~$180 external), CL ($104 vs ~$70),
MO ($128 vs ~$40), MCD ($173 vs ~$120), ITW ($127 vs ~$260 – opposite direction)

**Fix:**
```python
# In run_dcf(), after calculating equity value:
equity = enterprise - net_debt

# Add check:
book_equity = info.get("totalStockholdersEquity", 0) or 0
if book_equity < 0:
    # Use enterprise value approach directly
    # Do not subtract net debt twice
    # Show warning
    warnings.append("⚠️ Negative book equity – intrinsic value based on 
    Enterprise Value directly. Treat with caution.")
    # Cap intrinsic value: cannot be negative
    intrinsic = max(equity / shares, 0)
```

**Display:** Show warning banner in Analysis page when negative equity detected.

**Claude Code instruction:**
Read ROADMAP.md section 0.1 and app.py.
Fix negative equity issue in run_dcf():

Detect when totalStockholdersEquity < 0
Show warning: "Negative book equity detected – valuation less reliable"
Ensure intrinsic value cannot go negative
Test with ABBV, MO, MCD after fix
Commit and push. Do nothing else.


### 0.2 Growth Stock Undervaluation Fix
**Problem:** COST ($252 tool vs ~$400–600 external), WMT ($28 vs ~$60–90),
ETN ($92 vs ~$280–360), GE ($54 vs ~$200–350), BSX ($25 vs ~$50–80),
SYK ($135 vs ~$200–300) all severely undervalued by tool.
**Root cause:** These stocks have low historical FCF relative to their
current earning power. Market prices in much higher future FCF.
**Signal:** When Price/Intrinsic Value > 2.5 AND P/E < 40 → market
disagrees strongly with our DCF → growth premium not captured.

**Fix:**
```python
# Detect growth premium mismatch
price_to_iv_ratio = price / intrinsic if intrinsic > 0 else 0

if price_to_iv_ratio > 2.5 and pe and pe < 40:
    show_warning("""
    ⚠️ Growth Premium Gap: Market price is {ratio:.1f}× our DCF value.
    The market is pricing in significantly higher future growth than 
    our model assumes. Consider:
    - Increasing FCF growth rate manually
    - Using P/E or EV/EBITDA comparison instead
    - Our DCF represents a conservative floor value
    """)

# Also: for stocks where analyst growth > 15%, 
# use analyst growth as primary source (increase weight from 30% to 50%)
```

**Claude Code instruction:**
Read ROADMAP.md section 0.2 and app.py.
Add growth premium gap detection:

Calculate price_to_iv_ratio = current price / intrinsic value
If ratio > 2.5 AND P/E < 40: show warning about growth premium
Increase analyst growth weight to 50% when earningsGrowth > 0.15
Test with COST, WMT, ETN after fix
Commit and push. Do nothing else.


### 0.3 Cyclical Stock Warning
**Problem:** CAT ($171), DE ($138), ROK ($90), ETN ($92) are cyclicals
whose FCF is measured at cycle peak. 3-year average overstates
normalized earning power.
**Root cause:** Industrial cyclicals have FCF that swings 50-100%
through the cycle. A peak-cycle 3-year average is not representative.

**Fix:**
```python
CYCLICAL_SECTORS = ["Industrials", "Energy", "Materials", 
                    "Consumer Cyclical"]
CYCLICAL_SYMBOLS = ["CAT", "DE", "ROK", "ETN", "EMR", "DOV",
                    "PH", "AME", "IR", "XOM", "CVX", "COP"]

if sector in CYCLICAL_SECTORS or symbol in CYCLICAL_SYMBOLS:
    # Use 5-year average instead of 3-year
    # Show warning about cyclicality
    warning = """⚠️ Cyclical company – FCF varies significantly 
    through economic cycle. DCF based on recent peak FCF may 
    overstate normalized earning power. Treat as upper bound."""
    
    # Also cap growth rate at sector default (4-6%)
    growth = min(growth, SECTOR_DEFAULTS.get(sector, 0.05))
```

**Claude Code instruction:**
Read ROADMAP.md section 0.3 and app.py.
Add cyclical stock handling:

Create CYCLICAL_SECTORS and CYCLICAL_SYMBOLS lists
For cyclicals: use 5-year FCF average instead of 3-year
Cap growth rate at sector default for cyclicals
Show warning: "Cyclical company – DCF represents peak-cycle estimate"
Test with CAT, DE, ROK after fix
Commit and push. Do nothing else.


### 0.4 FMP API Validation – Second DCF Opinion
**Purpose:** Cross-check our intrinsic value against Financial Modeling
Prep's independent DCF calculation.
**Data source:** FMP free API, 250 requests/day, no scraping needed.

**Implementation:**
```python
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "")

def get_fmp_dcf(symbol):
    """Fetch FMP's DCF value as independent cross-check"""
    if not FMP_API_KEY:
        return None
    try:
        url = f"https://financialmodelingprep.com/api/v3/discounted-cash-flow/{symbol}?apikey={FMP_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                return round(data[0]["dcf"], 2)
    except:
        pass
    return None

def validate_dcf(our_value, fmp_value):
    """Compare our DCF with FMP's"""
    if not fmp_value or not our_value:
        return None
    diff_pct = abs(our_value - fmp_value) / fmp_value * 100
    if diff_pct < 20:
        return "✅ Consistent", diff_pct
    elif diff_pct < 50:
        return "⚠️ Some divergence", diff_pct
    else:
        return "🔴 Large divergence – verify inputs", diff_pct
```

**Display in Analysis page (new section after DCF results):**
┌─────────────────────────────────────────────┐
│ 🔍 DCF Validation                           │
│ Our Tool (Base):    $119.56                 │
│ FMP Independent:    $112.40                 │
│ Difference:         6.3%  ✅ Consistent     │
│                                             │
│ Cross-check manually:                       │
│ [Alpha Spread ↗] [GuruFocus ↗] [Simply Wall St ↗] │
└─────────────────────────────────────────────┘

**Setup required:**
1. Get free API key at financialmodelingprep.com
2. Add to Streamlit Cloud secrets: FMP_API_KEY = "your_key"

**Claude Code instruction:**
Read ROADMAP.md section 0.4 and app.py.
Add FMP DCF validation:

Add get_fmp_dcf() function as defined in ROADMAP
Add validate_dcf() comparison function
Show validation box in Analysis page after DCF results
Add external links: Alpha Spread, GuruFocus, Simply Wall St
Links should use symbol to open correct page, e.g.:
https://www.alphaspread.com/security/nyse/{symbol}/dcf-valuation
https://www.gurufocus.com/stock/{symbol}/dcf
https://simplywall.st/stocks/us/-/-{symbol}/valuation
FMP_API_KEY read from st.secrets with fallback if not set
Commit and push. Do nothing else.


### 0.5 Automatic Warning Flags
**Purpose:** Auto-generate reliability warnings for problematic situations.
Show prominently in Analysis page.

```python
def generate_warnings(result, info):
    warnings = []
    
    # Negative equity
    if (info.get("totalStockholdersEquity") or 0) < 0:
        warnings.append(("🔴", "Negative book equity",
            "Company has more liabilities than assets. "
            "DCF result less reliable – verify manually."))
    
    # Growth premium gap
    ratio = result["price"] / result["intrinsic"] if result["intrinsic"] > 0 else 0
    if ratio > 2.5 and result.get("pe") and result["pe"] < 40:
        warnings.append(("⚠️", "Growth premium not captured",
            f"Market trades at {ratio:.1f}× our DCF value. "
            "Market prices in higher future growth than model assumes."))
    
    # Cyclical at peak
    if result["sector"] in ["Industrials", "Energy", "Materials"]:
        warnings.append(("⚠️", "Cyclical sector",
            "FCF may be at cycle peak. DCF could overstate "
            "normalized earning power."))
    
    # Very high debt
    net_debt_ratio = result.get("net_debt", 0) / result.get("market_cap", 1)
    if net_debt_ratio > 2.0:
        warnings.append(("🔴", "Very high debt",
            f"Net debt is {net_debt_ratio:.1f}× market cap. "
            "Company highly leveraged – DCF sensitive to assumptions."))
    
    # FCF outlier used
    if result.get("fcf_note") and "outlier" in result["fcf_note"].lower():
        warnings.append(("⚠️", "FCF outlier detected",
            "Recent FCF deviates significantly from historical average. "
            "Median used as base – verify with company reports."))
    
    # Currency conversion
    if result.get("currency_converted"):
        warnings.append(("⚠️", "Currency conversion applied",
            f"FCF reported in {result['financial_currency']}, "
            f"converted to {result['currency']}. "
            "Exchange rate fluctuations affect result."))
    
    # Only 1 positive FCF year
    if result.get("fcf_note") and "1 positive" in result["fcf_note"]:
        warnings.append(("🔴", "Insufficient FCF history",
            "Only 1 positive FCF year available. "
            "DCF result highly uncertain."))
    
    return warnings
```

**Claude Code instruction:**
Read ROADMAP.md section 0.5 and app.py.
Add automatic warning flags:

Add generate_warnings() function as defined in ROADMAP
Show warnings prominently at top of Analysis page
Each warning shows: icon, title, explanation
Also show warning count in Database table (new column)
Commit and push. Do nothing else.


---

## 🟡 Priority 1 – Remaining Bug Fixes

### 1.1 NVDA FCF Base Logic
**Problem:** NVDA shows $44 (tool) vs $77–166 (external)
**Root cause:** Despite recent-year logic, growth rate still too low
**Fix:** Debug FCF base and growth rate, verify recent-year branch triggers

### 1.2 CEG Constellation Energy
**Problem:** $50 (tool) vs $226–382 (external)
**Root cause:** Only 1 positive FCF year – DCF unreliable
**Fix:** Add to DCF_UNRELIABLE list, show strong warning, suggest P/E instead

### 1.3 JD.com / Deutsche Telekom Currency
**Problem:** JD $168 (tool) vs $51–119 (external) – too high
**Root cause:** CNY→USD conversion may be incorrect for ADR structure
**Fix:** Verify ADR ratio and currency conversion for Chinese stocks

---

## 🟡 Priority 2 – Core Improvements

### 2.1 Index Selection for Batch Analysis ✅ Done

### 2.2 Index Filter in Database
Add "Index" column to entries, filter in Database page.

**Claude Code instruction:**
Read ROADMAP.md section 2.2 and app.py.
Add index tracking to database:

Add "Index" field when saving batch results
Add index filter dropdown in Database page
Commit and push. Do nothing else.


### 2.3 Stock Detail View from Database
Make database rows clickable → opens full Analysis page.

**Claude Code instruction:**
Read ROADMAP.md section 2.3 and app.py.
Add "Analyze" button to each database row.
Clicking sets st.session_state.selected_symbol and navigates to Analysis page.
Analysis page auto-loads the symbol if selected_symbol is set in session_state.
Add "← Back to Database" button at top of Analysis page.
Commit and push. Do nothing else.

### 2.4 Tooltips & Terminology
Add ℹ️ tooltips to all metrics using st.metric() help parameter.

Priority terms: MoS, WACC, DCF, FCF, Deviation %, Weighted Fair Value,
Blume Beta, ERP, Implied Multiple, Terminal Value, Piotroski.

Full glossary already documented in ROADMAP – see Glossary section below.

### 2.5 Value Score Category Explanations
Show WHY each category received its score dynamically.

### 2.6 Additional Database Filters
Add: Market Cap category, Value Score minimum, Undervalued only checkbox,
FCF positive only, Dividend minimum, ROE minimum, Index filter.

---

## 🟠 Priority 3 – Further Methodology

### 3.1 Stock Type Detection & Methodology Recommendation
Show at top of Analysis which method is best:
📊 Apple – Quality Growth
✅ Two-Stage DCF    Best – strong FCF CAGR 15%
✅ PEG Ratio        Useful – validates growth premium
⚠️  P/E             Tech sector context only
❌  DDM              Not applicable – dividend 0.5%

### 3.2 Two-Stage DCF
Phase 1 (Years 1–5): high growth · Phase 2 (Years 6–10): linear decline.

### 3.3 PEG Ratio
PEG = P/E / FCF CAGR%. Below 1.0 = attractive even for growth stocks.

### 3.4 Piotroski F-Score
9-point quality checklist. Proven +13.4% annual outperformance.
Full implementation documented in original ROADMAP.

### 3.5 DDM for Dividend Stocks
Gordon Growth Model for dividend yield > 2%: V = D1 / (r - g)

---

## 🔵 Priority 4 – User Experience

### 4.1 Stock Comparison
Side-by-side comparison of 2–3 stocks.

### 4.2 Watchlist with Notes
Personal watchlist with target prices and notes.
Persist in watchlist.json on GitHub.

### 4.3 Risk Flags (extended)
Auto-generate risk warnings beyond DCF:
- 🔴 FCF negative 2+ years
- 🔴 High debt ratio (Net Debt/EBITDA > 4×)
- 🟠 Cyclical sector
- 🟠 Patent cliff risk (Healthcare with declining revenue)
- 🟡 Currency risk (non-USD reporting)

### 4.4 Soft Color Scheme
Replace harsh red/green with soft gradients throughout.
Undervalued: #E8F5E9 · Overvalued: #FFEBEE · Neutral: #E3F2FD

---

## 🟣 Priority 5 – Automation & Scale

### 5.0 Pre-populated Database for Launch
Run full batch before first public rollout.
Target: 200+ stocks with valid DCF results.

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
CSV import as first step.

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

### Secrets (Streamlit Cloud)
```toml
GITHUB_TOKEN = "ghp_..."
GITHUB_REPO  = "username/aktien-tool"
FMP_API_KEY  = "your_fmp_key"   ← new, get free at financialmodelingprep.com
```

### Session Start Command
Read ROADMAP.md and app.py.
Tell me which Priority 0 items are still open.
Do not make any changes yet.

### Stable Fallback Version
Commit: 3c1a1f0
Restore: git checkout 3c1a1f0 -- app.py

### Rate Limit Recovery
Streamlit: Manage app → Reboot app
Local: pip3 install yfinance --upgrade

### DCF Methodology Decisions
✅ IMPLEMENT:
- Three-scenario DCF (Bear/Base/Bull)
- Live risk-free rate from ^TNX
- Blume-adjusted beta
- Regional ERP mapping
- Terminal Value plausibility check
- Full transparency
- FMP API cross-validation
- Automatic warning flags

❌ DO NOT IMPLEMENT:
- FCFF bottom-up (EBIT unreliable in yfinance)
- Country Risk Premium (external data needed)
- Pension liabilities (not in yfinance)
- Full historical normalization (requires human judgment)

### Known Validation Issues (from testing April 2026)
Stocks where tool diverges significantly from external DCF tools:

TOO LOW (tool underestimates):
- NVDA: $44 vs $77–166 external → FCF base logic
- CEG: $50 vs $226–382 → only 1 positive FCF year
- ETN: $92 vs $280–360 → cyclical peak FCF
- GE: $54 vs $200–350 → same issue
- COST: $252 vs $400–600 → growth premium
- WMT: $28 vs $60–90 → growth premium

TOO HIGH (tool overestimates):
- CI: $1140 → FCF volatile from acquisitions
- BIIB: $429 vs $205 → FCF declining
- CAG: $139 vs ~$20–30 → negative earnings

UNRELIABLE (DCF not suitable):
- CEG → volatile/negative FCF
- JPM → bank, DCF not applicable
- VWAPY → negative FCF

CURRENCY ISSUES (verify):
- JD: $168 vs $51–119 → CNY/ADR conversion
- BABA → CNY/ADR conversion
- DTE.DE → EUR conversion

---

## 📋 Glossary

| Term | Explanation |
|------|-------------|
| MoS | Margin of Safety – only buy at 25%+ discount to intrinsic value |
| WACC | Weighted Average Cost of Capital – DCF discount rate |
| DCF | Discounted Cash Flow – core valuation method |
| FCF | Free Cash Flow – cash after all expenses and investments |
| Terminal Value | PV of all cash flows beyond 10-year forecast (60–80% of total) |
| Blume Beta | 0.67 × raw beta + 0.33 × 1.0 – accounts for mean reversion |
| ERP | Equity Risk Premium – ~5.5% USA, ~6% Europe |
| Implied Multiple | EV/EBITDA implied by Terminal Value (should be 8–20×) |
| Weighted Fair Value | Bear×25% + Base×50% + Bull×25% |
| Deviation % | Price vs intrinsic value. Negative = undervalued |
| PEG | P/E / growth rate. Below 1.0 = attractive |
| Piotroski | 9-point quality score. Above 7 = strong fundamentals |
| Negative Equity | Book equity < 0 – often from buybacks or losses |
| Growth Premium | Market prices in higher growth than DCF model captures |
| Cyclical | FCF swings with economic cycle – peak FCF overstates normal earnings |
