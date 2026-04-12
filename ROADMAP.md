# Stock Analysis Tool – Feature Roadmap

## 🔴 Priority 1: Bug Fixes (do first)

### 1.1 Dividend Display Bug
- Dividends showing as 300%+ instead of 3%
- Root cause: yfinance returns dividend yield as decimal (0.03 = 3%)
  but somewhere it gets multiplied by 100 twice
- Fix: in result_to_db_entry() change to:
  "Dividend %": round(r["dividend"]*100, 2) if r.get("dividend") and r["dividend"] < 1 else r.get("dividend")
- Also fix in show_value_score() and all display functions

### 1.2 Decimal Places
- All numbers should show max 2 decimal places everywhere
- Apply to: database table, portfolio table, analysis view, value score
- Use round(value, 2) consistently throughout
- Format strings should use :.2f not :.4f or more

### 1.3 Value Score Fair Weighting
- Currently: inapplicable categories score 0/25 which unfairly penalizes stocks
- Fix: calculate score as percentage of applicable categories only
- Example: Bank gets DCF skipped entirely, not scored as 0
- Show explanation next to each category:
  "DCF not applicable – Financial sector: banks have no operational FCF"
  "DDM not applicable – No dividend paid"
- New formula:
  achieved = sum of points in applicable categories
  maximum = sum of max points in applicable categories only  
  final_score = round(achieved / maximum * 100)
- Categories skipped per stock type:
  Financial: skip DCF Deviation, skip FCF Quality
  Utilities/REITs: skip DCF Deviation (use DDM instead)
  No dividend: skip dividend component in Stability

---

## 🟡 Priority 2: Core Improvements

### 2.1 Index Selection for Batch Analysis
Organize VALUE_UNIVERSE into named index groups:

```python
INDEX_GROUPS = {
    "S&P 500 – Value": ["KO","PEP","PG","JNJ","MMM",...],  # top 100 value
    "S&P 500 – Quality Growth": ["AAPL","MSFT","GOOGL",...], # profitable tech
    "DAX 40": ["SAP.DE","SIE.DE","ALV.DE",...],             # all 40 DAX stocks
    "NASDAQ 100 – Profitable": ["AAPL","MSFT","CSCO",...],   # FCF positive only
    "STOXX Europe 50": ["NESN.SW","ASML.AS","OR.PA",...],
    "UK FTSE 100": ["SHEL.L","AZN.L","HSBA.L",...],
    "Swiss SMI": ["NESN.SW","NOVN.SW","ROG.SW",...],
    "All Value Universe": [...],                              # everything combined
}
```

Add to Batch Analysis page:
- Dropdown: "Select Index"
- Shows stock count and estimated duration
- Option to select multiple indexes

### 2.2 Index Column in Database
- Add "Index" field to every database entry during batch analysis
- Filter by index in Database page (add to existing sector filter)
- Allow filtering by multiple indexes simultaneously

### 2.3 Stock Detail View in Database
- Make database rows clickable
- Clicking opens expandable detail panel below the row showing:
  - Full DCF breakdown (same as Analysis page tab 3)
  - Value Score breakdown with explanations
  - Mini historical price chart (1 year)
  - Key metrics summary
  - Button: "Open Full Analysis" → navigates to Analysis page with stock loaded

### 2.4 Tooltips for All Metrics
Add help text to every metric using st.metric() description or custom tooltip:

| Metric | Tooltip text |
|--------|-------------|
| P/E | "Price-to-Earnings: how much investors pay per $1 of profit. Below 15 = cheap, 15-25 = fair, above 25 = expensive (sector-dependent)" |
| P/B | "Price-to-Book: market value vs. accounting value. Below 1 = trading below asset value. Key metric for banks." |
| EV/EBITDA | "Enterprise Value to EBITDA: removes debt and taxes for cross-company comparison. Below 8 = attractive, 8-12 = fair." |
| FCF Yield | "Free Cash Flow / Market Cap. Above 5% = attractive. Shows how much real cash the business generates per dollar invested." |
| WACC | "Weighted Average Cost of Capital: the discount rate used in DCF. Higher = more conservative valuation." |
| Value Score | "Composite score 0-100 combining DCF deviation, FCF quality, valuation multiples, profitability and stability. Score >60 = strong buy signal." |
| Deviation % | "How far the current price is from the calculated intrinsic value. Negative = undervalued, positive = overvalued." |
| Margin of Safety | "Buffer between intrinsic value and max buy price. 25% MoS means: only buy if price is 25% below intrinsic value." |

### 2.5 Value Score Category Explanations
Show dynamic explanation text per category based on actual values:

DCF Deviation examples:
- "25/25 – Stock trades 45% below intrinsic value. Strong buy signal."
- "10/25 – Stock trades 8% below intrinsic value. Modestly undervalued."
- "0/25 – Not applicable: Financial sector."
- "0/25 – FCF negative. DCF unreliable for this stock."

FCF Quality examples:
- "20/20 – FCF positive, 8.3% yield, growing 15% annually."
- "7/20 – FCF positive but FCF yield only 2.1%. Limited margin."
- "0/20 – Not applicable: bank/insurance business model."

---

## 🟠 Priority 3: Methodology Improvements

### 3.1 Stock Type Detection & Methodology Recommendation
Auto-detect stock type at start of every analysis:

```python
def detect_stock_type(info, cashflow):
    sector = info.get("sector","")
    fcf_positive = # check if FCF > 0 last 3 years
    fcf_cagr = # calculate historical FCF growth
    dividend_yield = info.get("dividendYield", 0) or 0
    
    if sector in ["Financials"]:
        return "financial"
    elif sector in ["Utilities", "Real Estate"]:
        return "dividend"
    elif dividend_yield > 0.04 and fcf_cagr < 0.06:
        return "dividend"
    elif fcf_cagr > 0.12 and sector in ["Technology","Healthcare"]:
        return "quality_growth"
    elif not fcf_positive:
        return "turnaround"
    else:
        return "value"
```

Show at top of Analysis page:
📊 Stock Type: Quality Growth
──────────────────────────────────────────────────
✅ DCF (Two-Stage)    Best method – high FCF CAGR supports growth model
✅ PEG Ratio          Useful – validates if growth justifies premium
⚠️  P/E Comparison    Use in sector context only – tech P/E typically 25-35x
❌  DDM               Not applicable – dividend too small to drive valuation
──────────────────────────────────────────────────

### 3.2 Two-Stage DCF Model
Replace single growth rate with two phases:

```python
def run_two_stage_dcf(fcf, phase1_growth, phase2_growth, terminal, wacc, years=10):
    """
    Phase 1: Years 1-5 at phase1_growth (high growth)
    Phase 2: Years 6-10 declining linearly to terminal rate
    """
    discounted = []
    current_fcf = fcf
    
    for yr in range(1, 11):
        if yr <= 5:
            growth = phase1_growth
        else:
            # Linear decline from phase1_growth to terminal over years 6-10
            progress = (yr - 5) / 5
            growth = phase1_growth - (phase1_growth - terminal) * progress
        
        current_fcf *= (1 + growth)
        discounted.append(current_fcf / (1 + wacc) ** yr)
    
    return discounted, current_fcf
```

UI change in Analysis page:
- Add second slider: "Phase 2 Growth %" (Years 6-10)
- Default: halfway between Phase 1 and terminal
- Show growth rate chart: how it declines over 10 years

### 3.3 Automatic Growth Rate Calculation
```python
def calculate_realistic_growth(symbol, info, cashflow):
    rates = []
    weights = []
    
    # Source 1: Historical FCF CAGR (50% weight) – most reliable
    if "Free Cash Flow" in cashflow.index:
        fcf_values = cashflow.loc["Free Cash Flow"].values
        positive = [v for v in fcf_values[:5] if v > 0]
        if len(positive) >= 3:
            cagr = (positive[0]/positive[-1]) ** (1/(len(positive)-1)) - 1
            cagr = max(-0.10, min(0.25, cagr))  # cap -10% to +25%
            rates.append(cagr)
            weights.append(0.50)
    
    # Source 2: Analyst EPS growth forecast (30% weight) – forward looking
    earnings_growth = info.get("earningsGrowth")
    if earnings_growth and -0.30 < earnings_growth < 0.50:
        rates.append(earnings_growth)
        weights.append(0.30)
    
    # Source 3: Revenue growth as proxy (20% weight) – always available
    rev_growth = info.get("revenueGrowth")
    if rev_growth and -0.20 < rev_growth < 0.40:
        rates.append(rev_growth)
        weights.append(0.20)
    
    if not rates:
        return get_sector_default(info.get("sector",""))
    
    # Weighted average with 20% conservative haircut
    weighted = sum(r*w for r,w in zip(rates,weights)) / sum(weights)
    return round(weighted * 0.80, 4)  # 20% haircut

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

### 3.4 PEG Ratio
```python
def calculate_peg(pe, fcf_cagr):
    if pe and fcf_cagr and fcf_cagr > 0:
        return round(pe / (fcf_cagr * 100), 2)
    return None
```

Display with color coding:
- Green: PEG < 1.0 "Attractive even for growth stock"
- Yellow: PEG 1.0-1.5 "Fairly valued"
- Orange: PEG 1.5-2.0 "Slightly expensive"
- Red: PEG > 2.0 "Expensive – growth must materialize"

### 3.5 Piotroski F-Score Implementation
```python
def calculate_piotroski(info, financials, balance_sheet, cashflow):
    score = 0
    details = {}
    
    # === PROFITABILITY (4 points) ===
    # 1. ROA positive
    roa = info.get("returnOnAssets", 0) or 0
    p1 = 1 if roa > 0 else 0
    details["ROA positive"] = p1
    score += p1
    
    # 2. Operating cash flow positive
    try:
        cfo = cashflow.loc["Operating Cash Flow"].iloc[0]
        p2 = 1 if cfo > 0 else 0
    except: p2 = 0
    details["Cash flow positive"] = p2
    score += p2
    
    # 3. ROA increasing
    try:
        roa_current = financials.loc["Net Income"].iloc[0] / balance_sheet.loc["Total Assets"].iloc[0]
        roa_prior = financials.loc["Net Income"].iloc[1] / balance_sheet.loc["Total Assets"].iloc[1]
        p3 = 1 if roa_current > roa_prior else 0
    except: p3 = 0
    details["ROA improving"] = p3
    score += p3
    
    # 4. Accruals: CFO > Net Income
    try:
        net_income = financials.loc["Net Income"].iloc[0]
        total_assets = balance_sheet.loc["Total Assets"].iloc[0]
        accrual = (net_income - cfo) / total_assets
        p4 = 1 if accrual < 0 else 0
    except: p4 = 0
    details["Low accruals"] = p4
    score += p4
    
    # === FINANCIAL HEALTH (3 points) ===
    # 5. Leverage not increasing
    try:
        lev_curr = balance_sheet.loc["Long Term Debt"].iloc[0] / balance_sheet.loc["Total Assets"].iloc[0]
        lev_prior = balance_sheet.loc["Long Term Debt"].iloc[1] / balance_sheet.loc["Total Assets"].iloc[1]
        p5 = 1 if lev_curr <= lev_prior else 0
    except: p5 = 0
    details["Leverage stable/declining"] = p5
    score += p5
    
    # 6. Current ratio improving
    try:
        cr_curr = balance_sheet.loc["Current Assets"].iloc[0] / balance_sheet.loc["Current Liabilities"].iloc[0]
        cr_prior = balance_sheet.loc["Current Assets"].iloc[1] / balance_sheet.loc["Current Liabilities"].iloc[1]
        p6 = 1 if cr_curr > cr_prior else 0
    except: p6 = 0
    details["Liquidity improving"] = p6
    score += p6
    
    # 7. No new shares issued
    try:
        shares_curr = balance_sheet.loc["Common Stock"].iloc[0]
        shares_prior = balance_sheet.loc["Common Stock"].iloc[1]
        p7 = 1 if shares_curr <= shares_prior else 0
    except: p7 = 0
    details["No share dilution"] = p7
    score += p7
    
    # === EFFICIENCY (2 points) ===
    # 8. Gross margin improving
    try:
        gm_curr = financials.loc["Gross Profit"].iloc[0] / financials.loc["Total Revenue"].iloc[0]
        gm_prior = financials.loc["Gross Profit"].iloc[1] / financials.loc["Total Revenue"].iloc[1]
        p8 = 1 if gm_curr > gm_prior else 0
    except: p8 = 0
    details["Gross margin improving"] = p8
    score += p8
    
    # 9. Asset turnover improving
    try:
        at_curr = financials.loc["Total Revenue"].iloc[0] / balance_sheet.loc["Total Assets"].iloc[0]
        at_prior = financials.loc["Total Revenue"].iloc[1] / balance_sheet.loc["Total Assets"].iloc[1]
        p9 = 1 if at_curr > at_prior else 0
    except: p9 = 0
    details["Asset turnover improving"] = p9
    score += p9
    
    interpretation = (
        "Strong – likely outperformer" if score >= 8
        else "Neutral – average quality" if score >= 5
        else "Weak – potential value trap"
    )
    
    return score, details, interpretation
```

### 3.6 DDM (Dividend Discount Model)
For dividend stocks only (dividend yield > 2%):

```python
def calculate_ddm(info):
    dividend = info.get("dividendRate")       # annual dividend per share
    price = info.get("currentPrice")
    wacc = # calculate from calculate_wacc()
    
    # Sustainable dividend growth = historical dividend CAGR, max 6%
    div_growth = min(info.get("earningsGrowth", 0.03) or 0.03, 0.06)
    
    if not dividend or not price or wacc <= div_growth:
        return None, "DDM not applicable"
    
    # Gordon Growth Model: V = D1 / (r - g)
    d1 = dividend * (1 + div_growth)
    intrinsic_ddm = d1 / (wacc - div_growth)
    deviation_ddm = (price - intrinsic_ddm) / intrinsic_ddm * 100
    
    return {
        "intrinsic_ddm": round(intrinsic_ddm, 2),
        "deviation_ddm": round(deviation_ddm, 1),
        "div_growth_used": round(div_growth * 100, 1),
        "annual_dividend": dividend,
    }, None
```

### 3.7 Improved Value Score by Stock Type
See stock type detection in 3.1. 
Score weights change based on detected type.
Always show which weights were used and why.

---

## 🔵 Priority 4: User Experience

### 4.1 Stock Comparison Page
- New page: "⚖️ Compare"
- Search and select 2-3 stocks
- Side-by-side comparison table: all key metrics
- Overlay chart: price history of all selected stocks
- Value Score comparison bar chart

### 4.2 Watchlist with Personal Notes
- New page: "⭐ Watchlist"  
- Add stocks with personal notes and target price
- Persist in watchlist.json on GitHub
- Show alert indicator if current price < target price
- Columns: Symbol, Name, Target Price, Current Price, Gap %, Note, Date Added

### 4.3 Risk Analysis
Auto-generate risk flags for every stock:

```python
RISK_FLAGS = {
    "High debt": lambda r: r.get("net_debt",0) / r.get("market_cap",1) > 0.5,
    "FCF negative": lambda r: (r.get("fcf") or 0) < 0,
    "Declining revenue": lambda r: (r.get("revenue_growth") or 0) < -0.05,
    "FCF volatile": lambda r: # std dev of FCF history > 30%
    "Cyclical sector": lambda r: r.get("sector","") in ["Energy","Materials","Consumer Discretionary"],
    "Regulatory risk": lambda r: r.get("sector","") in ["Healthcare","Utilities","Financials"],
    "No moat signals": lambda r: (r.get("net_margin") or 0) < 0.05 and (r.get("roe") or 0) < 0.10,
}
```

Show as colored badge list at top of analysis:
🔴 High risk · 🟠 Medium risk · 🟡 Low risk

### 4.4 Scenario Analysis
Add "Scenarios" tab to Analysis page:
- Three columns: Bear / Base / Bull
- Bear: FCF growth -30%, WACC +2%, MoS 35%
- Base: current assumptions
- Bull: FCF growth +30%, WACC -1%, MoS 15%
- Show all three intrinsic values and deviation %
- Chart: bar chart comparing three scenarios

### 4.5 Color & Design Improvements
Replace harsh red/green with soft gradients:
- Undervalued: soft green (#E8F5E9 background, #2E7D32 text)
- Overvalued: soft red (#FFEBEE background, #C62828 text)  
- Neutral: soft blue (#E3F2FD background, #1565C0 text)
- Value Score high: soft green gradient
- Value Score low: soft amber gradient
Apply consistently: database table, portfolio, value score bars, metrics

---

## 🟣 Priority 5: Automation & Scale

### 5.1 Daily Auto-Update via GitHub Actions
Create .github/workflows/update_database.yml:

```yaml
name: Daily Database Update
on:
  schedule:
    - cron: '0 6 * * 1-5'  # 6am UTC Monday-Friday
  workflow_dispatch:         # also allow manual trigger

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
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPO: ${{ secrets.GITHUB_REPO }}
      - uses: actions/upload-artifact@v3
```

Create update_database.py:
- Loads existing datenbank.json
- Updates price and key metrics (not full DCF recalculation)
- Saves back to GitHub
- Logs which stocks were updated

### 5.2 Expanded Stock Universe (500+)
Organize into clean index lists:
- S&P 500 complete list
- DAX 40 complete
- STOXX Europe 600 value subset
- FTSE 100
- Nikkei 225 top 50
- Total: ~500-600 stocks

### 5.3 Trade Republic Integration
Note: Trade Republic has no official public API.
Options:
- Option A: Manual CSV import from TR export function
- Option B: Unofficial TR API (pytr library) – use at own risk
- Option C: Manual portfolio entry (current approach)

Recommended approach: start with CSV import
- TR allows portfolio export as CSV
- Build CSV importer in Portfolio page
- Map TR format to our portfolio format

---

## 📝 Technical Notes for Claude Code

### Project Overview
Value investing stock analysis tool with DCF as core methodology.
Streamlit frontend, yfinance data, GitHub persistence, Streamlit Cloud deployment.

### Architecture
- Single file app: app.py (all Streamlit pages)
- Data persistence: GitHub API (read/write JSON files)
- Stock data: yfinance (free, no API key)
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
yfinance
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

### Known Bugs (fix first)
1. Dividend % shows 300%+ → yfinance returns 0.03, multiply by 100 once only
2. Too many decimal places → round everything to 2 decimals
3. Value Score penalizes with 0 for inapplicable categories → skip and reweight

### Core Design Principles
1. DCF is always the primary method – never remove it
2. Value Score is composite – no single metric dominates
3. Sector-specific logic everywhere – no one-size-fits-all
4. Conservative assumptions – 20% haircut on growth rates
5. Transparency – always show assumptions and explain scores
6. Soft colors – no harsh red/green, use gradients
7. Mobile-friendly – works on phone too

### How to Work with This Codebase
- Read ROADMAP.md first to understand priorities
- Fix bugs before adding features
- Test each change before moving to next
- Keep app.py as single file (do not split into modules yet)
- Commit after each completed feature with descriptive message

### Suggested Session Workflow
1. Claude Code reads ROADMAP.md and app.py
2. Tackles one priority level per session
3. Tests locally if possible
4. Commits to GitHub with clear message
5. Streamlit Cloud auto-deploys

---

## ✅ Completed Features
- [x] Basic DCF calculation with WACC
- [x] Value Score (basic version – needs improvement per Priority 3)
- [x] Historical charts (price, P/E, FCF, intrinsic value)
- [x] Persistent database via GitHub API
- [x] Portfolio tracking with recommendations
- [x] Batch analysis for 200 stocks
- [x] Dashboard with Top 10 opportunities
- [x] Methodology page with sources
- [x] English language throughout
- [x] Search with autocomplete suggestions
- [x] Sector-specific Value Score weights
