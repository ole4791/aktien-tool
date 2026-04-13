# Stock Analysis Tool – Feature Roadmap

## ✅ Completed Features
- [x] Basic DCF calculation with WACC
- [x] Value Score with fair weighting (sector-specific)
- [x] Historical charts (price, P/E, FCF, intrinsic value)
- [x] Persistent database via GitHub API
- [x] Portfolio tracking with recommendations
- [x] Batch analysis for 200 stocks
- [x] Dashboard with Top 10 opportunities
- [x] Methodology page with sources
- [x] English language throughout
- [x] Search with autocomplete suggestions
- [x] Dividend display bug fixed
- [x] Decimal places standardized to 2
- [x] Value Score fair weighting – inapplicable categories skipped

---

## 🔴 Priority 1 – Urgent Bugs & Fixes

### 1.4 Yahoo Finance Rate Limiting – CRITICAL
**Problem:** Batch analysis stops after ~5 stocks with "Too Many Requests" error

**Root cause analysis:**
- Each stock makes 4 separate yfinance API calls:
  - ticker.info
  - ticker.cashflow
  - ticker.financials
  - ticker.balance_sheet
- 70 stocks × 4 calls = 280 rapid requests
- Yahoo Finance blocks after ~50-100 requests without delays
- Current sleep between stocks is only 0.3s – far too short
- Historical charts are NOT the cause (they only load on click)

**Fix strategy for Claude Code:**
1. Increase sleep between batch stocks from 0.3s to 2.0s
   → 70 stocks × 2s = ~2.5 minutes total (acceptable)
2. Verify single Ticker object is reused for all 4 calls per stock
3. Add retry with exponential backoff:
   - Rate limited → wait 30s → retry once
   - Rate limited again → wait 60s → retry once
   - Rate limited third time → skip stock, log it, continue with next
4. Do NOT abort entire batch on rate limit – pause and resume
5. Show user: "Rate limited – waiting 30s before retry..."
6. Add cache: if same stock analyzed twice in session, reuse data
7. Recommended batch size: max 50 stocks per run

**Claude Code instruction:**
Read ROADMAP.md section 1.4 and app.py.
Fix the rate limiting problem in batch analysis:

Increase sleep between stocks to 2.0 seconds
Add retry logic: if rate limited, wait 30s and retry once, then 60s retry, then skip
Never abort the entire batch - just pause and continue
Show status message when rate limited and waiting
Reuse single Ticker object for all API calls per stock
Commit and push after. Do nothing else.


### 1.5 PayPal & Fintech Misclassification
**Problem:** PayPal (PYPL) classified as Financial/Bank → DCF incorrectly skipped

**Root cause:** yfinance sector label "Financial Services" is too broad

**Fix strategy:**
- Create two lists in code:
  1. `DCF_EXEMPT` – traditional banks/insurance where DCF truly doesn't apply:
     JPM, BAC, WFC, C, GS, MS, USB, TFC, AIG, PRU, MET, AFL, BRK-B
  2. `DCF_APPLICABLE` – fintech/payments that have strong FCF and need DCF:
     PYPL, SQ, V, MA, AXP, COF, DFS, COIN
- Logic: if sector == "Financial" AND symbol NOT in DCF_EXEMPT → use DCF
- Also check: if FCF > 0 consistently → always use DCF regardless of sector
- General rule: industry label is more specific than sector – use it when available

**Claude Code instruction:**
Read ROADMAP.md section 1.5 and app.py.
Fix PayPal misclassification:

Create DCF_EXEMPT list for true banks/insurance
Create DCF_APPLICABLE override list for fintech
Update detect_stock_type() or no_dcf logic to use these lists
Rule: if FCF positive for 3+ years → always apply DCF regardless of sector
Commit and push. Do nothing else.


---

## 🟡 Priority 2 – Core Improvements

### 2.1 Index Selection for Batch Analysis
**Problem:** Currently all stocks use same list with no organization by index

**Fix:**
Add organized index groups to VALUE_UNIVERSE:

```python
INDEX_GROUPS = {
    "S&P 500 – Value": [
        "KO","PEP","PG","CL","GIS","MCD","WMT","COST","JNJ","ABT",
        "MDT","PFE","MRK","LLY","ABBV","MMM","HON","CAT","DE","EMR",
        "UPS","FDX","AAPL","MSFT","CSCO","IBM","ORCL","TXN","JPM","BAC",
        "WFC","AXP","V","MA","XOM","CVX","COP","NEE","DUK","AMT"
    ],
    "S&P 500 – Quality Growth": [
        "AAPL","MSFT","GOOGL","META","NVDA","AMZN","PYPL","CRM","NOW","ADBE"
    ],
    "DAX 40": [
        "SAP.DE","SIE.DE","ALV.DE","MUV2.DE","BMW.DE","MBG.DE","VOW3.DE",
        "BAS.DE","BAYN.DE","DBK.DE","DTE.DE","RWE.DE","HEN3.DE","ADS.DE",
        "IFX.DE","MRK.DE","BEI.DE","MTX.DE","ENR.DE","HNR1.DE",
        "CON.DE","FRE.DE","ZAL.DE","SHL.DE","DHL.DE","VNA.DE","RHM.DE",
        "DHER.DE","QIA.DE","HFG.DE","MBB.DE","EVT.DE","PUM.DE","LEG.DE",
        "SY1.DE","NDX1.DE","KGX.DE","1COV.DE","GN.DE","CBK.DE"
    ],
    "NASDAQ 100 – Profitable": [
        "AAPL","MSFT","GOOGL","META","AMZN","TSLA","NVDA","AVGO","CSCO",
        "ADBE","TXN","QCOM","INTU","AMAT","AMD","ISRG","REGN","VRTX",
        "GILD","BIIB","AMGN","MDLZ","MNST","KHC","PAYX","ADP","FISV"
    ],
    "STOXX Europe 50": [
        "NESN.SW","NOVN.SW","ROG.SW","ZURN.SW","ABBN.SW",
        "ASML.AS","INGA.AS","PHIA.AS","HEIA.AS",
        "OR.PA","TTE.PA","SAN.PA","BNP.PA","AIR.PA","MC.PA",
        "SHEL.L","BP.L","HSBA.L","AZN.L","GSK.L","ULVR.L","DGE.L",
        "SIE.DE","ALV.DE","SAP.DE","BAS.DE","MUV2.DE",
        "ENEL.MI","ISP.MI","UCG.MI","ENI.MI",
        "IBE.MC","SAN.MC","BBVA.MC"
    ],
    "UK FTSE 100": [
        "SHEL.L","BP.L","HSBA.L","AZN.L","GSK.L","ULVR.L",
        "DGE.L","BATS.L","RIO.L","BHP.L","GLEN.L","AAL.L",
        "LLOY.L","BARC.L","NWG.L","STAN.L","PRU.L","LGEN.L",
        "VOD.L","BT-A.L","NG.L","SSE.L","SVT.L","UU.L"
    ],
}
```

UI changes in Batch Analysis page:
- Replace current slider with:
  - Dropdown: "Select Index" with all options + "All stocks combined"
  - Shows stock count per index
  - Shows estimated duration (count × 2s)
- Keep growth/terminal/MoS sliders

**Claude Code instruction:**
Read ROADMAP.md section 2.1 and app.py.
Implement index groups for batch analysis:

Add INDEX_GROUPS dictionary as defined in ROADMAP
Add dropdown in Batch Analysis page to select index
Show stock count and estimated duration for selected index
Keep existing sliders for growth/terminal/MoS
Commit and push. Do nothing else.


### 2.2 Index Filter in Database
- Add "Index" field to every database entry during batch analysis
- Add index filter dropdown in Database page
- Allow filtering by multiple indexes simultaneously

**Claude Code instruction:**
Read ROADMAP.md section 2.2 and app.py.
Add index tracking to database:

When saving batch results, add "Index" field with the selected index name
Add index filter to Database page alongside existing sector filter
Commit and push. Do nothing else.


### 2.3 Stock Detail View from Database
**Problem:** Clicking a stock in database shows nothing – need full detail view

**Fix:**
- Make database rows clickable
- Clicking loads that stock into Analysis page automatically
- Show same information as Analysis page:
  - Value Score breakdown with explanations
  - DCF calculation step by step
  - All key metrics with tooltips
  - Historical charts
- Add "Back to Database" button

**Claude Code instruction:**
Read ROADMAP.md section 2.3 and app.py.
Make database rows clickable:

Add a "Analyze" button per row in database table
Clicking sets st.session_state.selected_symbol and navigates to Analysis page
Analysis page auto-loads the symbol if selected_symbol is set
Commit and push. Do nothing else.


### 2.4 Tooltips & Terminology Explanations
**Problem:** Financial terms are complex and unexplained

**Glossary to implement as tooltips:**

| Term | Tooltip explanation |
|------|-------------------|
| MoS | Margin of Safety – buffer between intrinsic value and max buy price. 25% MoS means: only buy if price is 25% below intrinsic value. Protects against valuation errors. |
| WACC | Weighted Average Cost of Capital – the discount rate used in DCF. Represents the minimum return investors expect from this company. Higher WACC = more conservative valuation. |
| DCF | Discounted Cash Flow – values a company by forecasting future free cash flows and discounting them to today's value. The most theoretically sound valuation method. |
| FCF | Free Cash Flow – cash the company generates after all expenses and capital investments. The foundation of DCF valuation. More reliable than reported earnings. |
| Terminal Value | Present value of all cash flows beyond the 10-year forecast. Usually represents 60-70% of total DCF value. Very sensitive to terminal growth rate assumption. |
| Beta | Measures stock volatility vs. the market. Beta 1.0 = moves with market. Beta 1.5 = 50% more volatile. Beta 0.5 = half as volatile. Higher beta = higher WACC. |
| EV/EBITDA | Enterprise Value / EBITDA. Removes effects of debt and taxes for fair cross-company comparison. Below 8 = attractive, 8-12 = fair, above 15 = expensive. |
| P/B | Price-to-Book – market value vs. accounting book value. Below 1.0 = buying assets cheaper than stated value. Key metric for banks. |
| P/E | Price-to-Earnings – how much investors pay per $1 of profit. Below 15 = cheap, 15-25 = fair, above 25 = expensive (sector dependent). |
| FCF CAGR | Compound Annual Growth Rate of Free Cash Flow. Shows how fast the company's cash generation grows. Above 10% = strong growth. |
| ROE | Return on Equity – profit generated per dollar of shareholder equity. Above 15% = excellent. Buffett's favorite profitability metric. |
| Piotroski | 9-point financial health checklist. Score 8-9 = strong fundamentals. Score 0-2 = potential value trap. Based on Stanford professor Joseph Piotroski's 2000 research. |
| Value Score | Composite score 0-100. Combines DCF deviation, FCF quality, valuation multiples, profitability and stability. Sector-specific weighting. Above 60 = strong buy signal. |
| Intrinsic Value | The calculated fair value of a stock based on DCF. If current price is below intrinsic value, the stock may be undervalued. |
| Deviation % | How far current price is from intrinsic value. Negative = undervalued. Positive = overvalued. -20% means stock trades 20% below fair value. |

**Claude Code instruction:**
Read ROADMAP.md section 2.4 and app.py.
Add tooltips to all metrics:

Use st.metric() help parameter where possible
Add ℹ️ expander with explanation for complex terms
Add glossary section to Methodology page
Priority: MoS, WACC, DCF, FCF, Deviation %, Value Score
Commit and push. Do nothing else.


### 2.5 Value Score Category Explanations
**Problem:** Score shows numbers but no explanation why

**Fix:**
Show dynamic explanation text per category:
DCF Deviation 18/25
→ "Stock trades 22% below intrinsic value. Strong buy signal."
FCF Quality 14/20
→ "FCF positive ($8.2B), FCF yield 4.1%, growing 12% annually."
Valuation 8/25
→ "P/E 24x (above sector average), P/B 3.2x (fair), EV/EBITDA 14x (elevated)."
Profitability 12/15
→ "ROE 28% (excellent), Net Margin 18% (strong)."
Stability 10/15
→ "Low debt ratio 0.2x, dividend yield 2.8% (sustainable)."
DCF Deviation N/A
→ "Not applicable – Financial sector. DCF skipped for banks and insurers."

Also add Value Score breakdown columns to Database table.

**Claude Code instruction:**
Read ROADMAP.md section 2.5 and app.py.
Add explanations to Value Score categories:

Below each score bar show a one-sentence explanation
Explanation is generated dynamically based on actual values
Add Value Score category columns to Database table
Commit and push. Do nothing else.


### 2.6 Additional Database Filters
**Current filters:** Sector, Deviation %, Sort by

**Add these filters:**
Market Cap:      Mega (>$200B) | Large ($10-200B) | Mid ($2-10B) | Small (<$2B)
Value Score:     Minimum score slider (0-100)
P/E Range:       Slider 0-50
Dividend Yield:  Minimum % (show only stocks with >X% dividend)
FCF:             Positive only checkbox
Valuation:       Undervalued only checkbox (Deviation % < 0)
Index:           Filter by index (after 2.1)
ROE minimum:     e.g. >15% = quality filter
Debt/Equity:     Maximum ratio e.g. <1.0 = low debt filter
FCF CAGR:        Minimum growth e.g. >5%
Net Margin:      Minimum % e.g. >10%

**Claude Code instruction:**
Read ROADMAP.md section 2.6 and app.py.
Add filters to Database page:

Market Cap category filter (Mega/Large/Mid/Small)
Value Score minimum slider
Undervalued only checkbox
FCF positive only checkbox
Dividend minimum slider
Keep existing filters, add new ones below.
Commit and push. Do nothing else.


---

## 🟠 Priority 3 – Methodology Improvements

### 3.0 Automatic FCF Growth Rate (for Batch)
**Impact:** Makes intrinsic values much more accurate – most important accuracy fix
**Effort:** ~20-30 minutes for Claude Code

```python
def calculate_realistic_growth(symbol, info, cashflow):
    rates, weights = [], []
    
    # Source 1: Historical FCF CAGR (50% weight)
    if "Free Cash Flow" in cashflow.index:
        fcf_values = cashflow.loc["Free Cash Flow"].values
        positive = [v for v in fcf_values[:5] if v > 0]
        if len(positive) >= 3:
            cagr = (positive[0]/positive[-1]) ** (1/(len(positive)-1)) - 1
            cagr = max(-0.10, min(0.25, cagr))
            rates.append(cagr)
            weights.append(0.50)
    
    # Source 2: Analyst EPS growth forecast (30% weight)
    earnings_growth = info.get("earningsGrowth")
    if earnings_growth and -0.30 < earnings_growth < 0.50:
        rates.append(earnings_growth)
        weights.append(0.30)
    
    # Source 3: Revenue growth as proxy (20% weight)
    rev_growth = info.get("revenueGrowth")
    if rev_growth and -0.20 < rev_growth < 0.40:
        rates.append(rev_growth)
        weights.append(0.20)
    
    if not rates:
        return SECTOR_DEFAULTS.get(info.get("sector",""), 0.05)
    
    weighted = sum(r*w for r,w in zip(rates,weights)) / sum(weights)
    return round(weighted * 0.80, 4)  # 20% conservative haircut

SECTOR_DEFAULTS = {
    "Technology": 0.10,
    "Healthcare": 0.07,
    "Consumer Staples": 0.05,
    "Consumer Discretionary": 0.07,
    "Industrials": 0.06,
    "Energy": 0.04,
    "Utilities": 0.03,
    "Real Estate": 0.04,
    "Financials": 0.05,
    "Materials": 0.05,
    "Communication Services": 0.07,
}
```

**Claude Code instruction:**
Read ROADMAP.md section 3.0 and app.py.
Implement automatic FCF growth rate calculation:

Add calculate_realistic_growth() function as defined in ROADMAP
In run_dcf(), if no manual growth rate provided, call this function
Show the calculated rate in the Analysis page so user can see it
In batch analysis, use this function instead of manual slider
but keep manual slider as override option
Commit and push. Do nothing else.


### 3.1 Stock Type Detection & Methodology Recommendation
Show at top of Analysis page which method is best for this stock:
📊 Apple Inc. – Quality Growth Stock
──────────────────────────────────────
✅ Two-Stage DCF    Best method – strong FCF CAGR of 15%
✅ PEG Ratio        Useful – validates growth premium
⚠️  P/E Comparison  Use in tech sector context only
❌  DDM              Not applicable – dividend yield only 0.5%
──────────────────────────────────────

### 3.2 Two-Stage DCF Model
```python
# Phase 1: Years 1-5 at high growth rate
# Phase 2: Years 6-10 declining linearly toward terminal rate
for yr in range(1, 11):
    if yr <= 5:
        growth = phase1_growth
    else:
        progress = (yr - 5) / 5
        growth = phase1_growth - (phase1_growth - terminal) * progress
    current_fcf *= (1 + growth)
```

### 3.3 PEG Ratio
```python
# PEG = P/E / FCF Growth Rate %
# PEG < 1.0 = attractive even for growth stocks
# PEG 1.0-1.5 = fairly valued
# PEG > 2.0 = expensive
```

### 3.4 Piotroski F-Score
9-point quality checklist – full implementation in original ROADMAP below.
Proven to outperform market by 13.4% annually over 20 years (Piotroski, 2000).

### 3.5 DDM (Dividend Discount Model)
For dividend stocks only (yield > 2%):
Gordon Growth Model: V = D1 / (r - g)

---

## 🔵 Priority 4 – User Experience

### 4.1 Stock Comparison Page
- New page: "⚖️ Compare"
- Select 2-3 stocks side by side
- Compare all key metrics and Value Score
- Overlay price history chart

### 4.2 Watchlist with Personal Notes
- New page: "⭐ Watchlist"
- Add stocks with personal notes and target price
- Alert when price drops below target
- Persist in watchlist.json on GitHub

### 4.3 Risk Analysis
Auto-generate risk flags:
- 🔴 FCF negative 2+ years
- 🔴 High debt (Net Debt/EBITDA > 4x)
- 🔴 Declining revenue 2+ years
- 🟠 FCF volatile
- 🟠 Cyclical sector
- 🟠 Regulatory risk
- 🟡 Currency risk

### 4.4 Scenario Analysis
Three scenarios with one click:
- Bear: FCF -30%, WACC +2%
- Base: current assumptions
- Bull: FCF +30%, WACC -1%

### 4.5 Soft Color Scheme
- Replace harsh red/green with soft gradients
- Undervalued: soft green (#E8F5E9 background)
- Overvalued: soft red (#FFEBEE background)
- Neutral: soft blue (#E3F2FD background)

---

## 🟣 Priority 5 – Automation & Scale

### 5.0 Pre-populated Database for Launch
- Run complete batch analysis of all 200 stocks before launch
- Save to datenbank.json on GitHub
- Users see data immediately without running batch
- Target: 150+ stocks with valid DCF results
- Update weekly via GitHub Actions

### 5.1 Daily Auto-Update via GitHub Actions
```yaml
name: Daily Database Update
on:
  schedule:
    - cron: '0 6 * * 1-5'  # 6am UTC Monday-Friday
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install yfinance pandas requests
      - run: python update_database.py
```

### 5.2 Expanded Stock Universe (500+)
- Full S&P 500
- Full DAX 40
- STOXX Europe 600 value subset
- FTSE 100
- Total: ~500 stocks

### 5.3 Trade Republic Integration
- Option A: Manual CSV import from TR export
- Option B: pytr library (unofficial, use at own risk)
- Recommended: start with CSV import

---

## 📝 Technical Notes for Claude Code

### Project Overview
Value investing stock analysis tool with DCF as core methodology.
Streamlit frontend, yfinance data, GitHub persistence, Streamlit Cloud deployment.

### Architecture
- Single file app: app.py (all Streamlit pages)
- Data persistence: GitHub API (read/write JSON files)
- Stock data: yfinance (free, no API key needed)
- Charts: Plotly
- Deployment: Streamlit Cloud (auto-deploys on GitHub push)

### Key Files
aktien-tool/
├── app.py              # main application
├── requirements.txt    # dependencies
├── ROADMAP.md          # this file
├── datenbank.json      # stock database (auto-created)
└── portfolio.json      # portfolio data (auto-created)

### Current Dependencies
yfinance>=0.2.67
pandas
streamlit
plotly
requests
matplotlib

### Secrets (Streamlit Cloud)
```toml
GITHUB_TOKEN = "ghp_..."
GITHUB_REPO = "username/aktien-tool"
```

### How to Work with This Codebase
1. Always read ROADMAP.md first
2. Fix bugs before adding features
3. One feature at a time – commit after each
4. Never make architectural changes without explicit instruction
5. Never switch data sources without explicit instruction
6. If unsure – ask before making changes
7. Always commit and push after each completed item

### Suggested Session Start
Read ROADMAP.md and app.py.
Tell me the current state and what Priority 1 items are still open.
Do not make any changes yet.

### Known Stable Version
- Commit: 3c1a1f0 (Update app.py – 11 hours ago)
- This is the fallback if something breaks
- Restore with: git checkout 3c1a1f0 -- app.py

### Rate Limiting Protection
- Always use time.sleep(2.0) between batch API calls
- Reuse single Ticker object per stock for all 4 calls
- If Streamlit shows rate limit error: Manage app → Reboot app
- If local yfinance blocked: pip3 install yfinance --upgrade

---

## 📋 Glossary

| Term | Explanation |
|------|-------------|
| MoS | Margin of Safety – discount to intrinsic value before buying. Protects against valuation errors. |
| WACC | Weighted Average Cost of Capital – discount rate in DCF |
| DCF | Discounted Cash Flow – core valuation method based on future cash flows |
| FCF | Free Cash Flow – cash generated after all expenses and investments |
| Terminal Value | Value of all cash flows beyond the 10-year forecast period |
| Beta | Stock volatility vs. market (1.0 = same as market) |
| EV/EBITDA | Enterprise value multiple – good for cross-company comparison |
| P/B | Price-to-Book – market vs. accounting value |
| P/E | Price-to-Earnings – how much paid per dollar of profit |
| FCF CAGR | Annual growth rate of Free Cash Flow |
| ROE | Return on Equity – profitability of shareholders' investment |
| Piotroski | 9-point financial health score (0-9) |
| Value Score | Composite score 0-100, sector-specific weighting |
| Intrinsic Value | Calculated fair value based on DCF |
| Deviation % | Distance of current price from intrinsic value |
| Phase 1 Growth | FCF growth rate for years 1-5 in two-stage DCF |
| Terminal Growth | Long-term sustainable growth rate (usually ~3%) |

Commit auf GitHub mit Update ROADMAP - complete priority list with Claude Code instructions.
Für morgen – starte Claude Code mit:
Read ROADMAP.md and app.py.
Tell me what Priority 1 items are still open.
Do not make any changes yet.
