import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import requests
from datetime import datetime

st.set_page_config(
    page_title="Stock Analysis Tool",
    page_icon="📈",
    layout="wide"
)

# ================================================================
# GITHUB PERSISTENCE
# ================================================================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO", "")
DB_FILE      = "datenbank.json"
PORT_FILE    = "portfolio.json"

def github_load(filename):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None, None
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r       = requests.get(url, headers=headers)
    if r.status_code == 200:
        import base64
        content = r.json()
        return json.loads(base64.b64decode(content["content"]).decode()), content["sha"]
    return None, None

def github_save(filename, data, sha=None):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    import base64
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}",
               "Content-Type": "application/json"}
    content = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"Update {filename} – {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

def load_database():
    data, sha = github_load(DB_FILE)
    return data or [], sha

def save_database(data, sha=None):
    return github_save(DB_FILE, data, sha)

def load_portfolio():
    data, sha = github_load(PORT_FILE)
    return data or [], sha

def save_portfolio(data, sha=None):
    return github_save(PORT_FILE, data, sha)

# ================================================================
# SESSION STATE
# ================================================================
if "database" not in st.session_state:
    with st.spinner("Loading saved data..."):
        st.session_state.database, st.session_state.db_sha = load_database()
if "portfolio" not in st.session_state:
    st.session_state.portfolio, st.session_state.port_sha = load_portfolio()
if "db_sha" not in st.session_state:
    st.session_state.db_sha = None
if "port_sha" not in st.session_state:
    st.session_state.port_sha = None

for key in ["last_result", "search_names", "search_symbols", "p_names", "p_symbols", "last_query"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "last_result" else []

if st.session_state.last_result is not None:
    if not isinstance(st.session_state.last_result, dict) or \
       "name" not in st.session_state.last_result:
        st.session_state.last_result = None

# ================================================================
# VALUE UNIVERSE
# ================================================================
VALUE_UNIVERSE = [
    "KO","PEP","PG","CL","GIS","K","MKC","SJM","CAG","HRL",
    "MCD","YUM","DPZ","CMG","WMT","COST","TGT","KR","SYY","MO",
    "JNJ","ABT","MDT","SYK","BSX","BDX","ZBH","EW","ISRG","RMD",
    "PFE","MRK","LLY","ABBV","BMY","AMGN","GILD","BIIB","REGN","VRTX",
    "CVS","UNH","HUM","CI","ELV","MCK","CAH","ABC","MOH","CNC",
    "MMM","HON","GE","CAT","DE","EMR","ITW","ETN","PH","ROK",
    "DOV","AME","FTV","XYL","GNRC","ROP","IDEX","IR","TT","CARR",
    "UPS","FDX","CSX","NSC","UNP","WAB","EXPD","CHRW","JBHT","ODFL",
    "AAPL","MSFT","CSCO","IBM","ORCL","TXN","QCOM","ADI","KLAC","LRCX",
    "AMAT","MSI","CTSH","ACN","INTU","PAYX","ADP","FISV","FIS","GPN",
    "BRK-B","JPM","BAC","WFC","USB","TFC","PNC","MTB","CFG","FITB",
    "AXP","V","MA","DFS","COF","SYF","AIG","PRU","MET","AFL",
    "BLK","TROW","BEN","IVZ","AMG","WTW","AON","MMC","CB","TRV",
    "XOM","CVX","COP","SLB","HAL","BKR","PSX","VLO","MPC","PXD",
    "EOG","DVN","MRO","OXY","HES","EQT",
    "NEE","DUK","SO","D","AEP","EXC","SRE","XEL","ES","ETR",
    "AMT","PLD","CCI","EQIX","PSA","O","SPG","WELL","AVB","EQR",
    "SAP.DE","SIE.DE","ALV.DE","MUV2.DE","BMW.DE","MBG.DE","VOW3.DE",
    "BAS.DE","BAYN.DE","DBK.DE","DTE.DE","RWE.DE","HEN3.DE","ADS.DE","IFX.DE",
    "SHEL.L","BP.L","HSBA.L","AZN.L","GSK.L","ULVR.L","DGE.L","BATS.L",
    "NESN.SW","NOVN.SW","ROG.SW","ZURN.SW","ABBN.SW",
    "ASML.AS","INGA.AS","PHIA.AS","HEIA.AS",
    "OR.PA","TTE.PA","SAN.PA","BNP.PA","AIR.PA","MC.PA",
    "7203.T","6758.T","9432.T","8306.T","4502.T",
]

INDEX_GROUPS = {
    "⭐ Featured Stocks": [
        "NVDA","TSLA","UNH","NVO","PYPL","CEG","DTE.DE","BABA","JD","IRDM",
    ],
    "🇺🇸 S&P 500 – Consumer": [
        "KO","PEP","PG","CL","GIS","K","MKC","SJM","CAG","HRL",
        "MCD","YUM","DPZ","CMG","WMT","COST","TGT","KR","SYY","MO",
    ],
    "🇺🇸 S&P 500 – Healthcare": [
        "JNJ","ABT","MDT","SYK","BSX","BDX","ZBH","EW","ISRG","RMD",
        "PFE","MRK","LLY","ABBV","BMY","AMGN","GILD","BIIB","REGN","VRTX",
        "CVS","UNH","HUM","CI","ELV","MCK","CAH","ABC","MOH","CNC",
    ],
    "🇺🇸 S&P 500 – Industrials": [
        "MMM","HON","GE","CAT","DE","EMR","ITW","ETN","PH","ROK",
        "DOV","AME","FTV","XYL","GNRC","ROP","IDEX","IR","TT","CARR",
        "UPS","FDX","CSX","NSC","UNP","WAB","EXPD","CHRW","JBHT","ODFL",
    ],
    "🇺🇸 S&P 500 – Technology": [
        "AAPL","MSFT","CSCO","IBM","ORCL","TXN","QCOM","ADI","KLAC","LRCX",
        "AMAT","MSI","CTSH","ACN","INTU","PAYX","ADP","FISV","FIS","GPN",
    ],
    "🇺🇸 S&P 500 – Financials": [
        "BRK-B","JPM","BAC","WFC","USB","TFC","PNC","MTB","CFG","FITB",
        "AXP","V","MA","DFS","COF","SYF","AIG","PRU","MET","AFL",
        "BLK","TROW","BEN","IVZ","AMG","WTW","AON","MMC","CB","TRV",
    ],
    "🇺🇸 S&P 500 – Energy & Utilities": [
        "XOM","CVX","COP","SLB","HAL","BKR","PSX","VLO","MPC","PXD",
        "EOG","DVN","MRO","OXY","HES","EQT",
        "NEE","DUK","SO","D","AEP","EXC","SRE","XEL","ES","ETR",
        "AMT","PLD","CCI","EQIX","PSA","O","SPG","WELL","AVB","EQR",
    ],
    "🇩🇪 DAX": [
        "SAP.DE","SIE.DE","ALV.DE","MUV2.DE","BMW.DE","MBG.DE","VOW3.DE",
        "BAS.DE","BAYN.DE","DBK.DE","DTE.DE","RWE.DE","HEN3.DE","ADS.DE","IFX.DE",
    ],
    "🌍 Europe": [
        "SHEL.L","BP.L","HSBA.L","AZN.L","GSK.L","ULVR.L","DGE.L","BATS.L",
        "NESN.SW","NOVN.SW","ROG.SW","ZURN.SW","ABBN.SW",
        "ASML.AS","INGA.AS","PHIA.AS","HEIA.AS",
        "OR.PA","TTE.PA","SAN.PA","BNP.PA","AIR.PA","MC.PA",
    ],
    "🌏 Asia": [
        "7203.T","6758.T","9432.T","8306.T","4502.T",
    ],
    "🌐 Full Universe": VALUE_UNIVERSE,
}

# Traditional banks and insurers where DCF truly doesn't apply
DCF_EXEMPT = {
    "JPM","BAC","WFC","C","GS","MS","USB","TFC",
    "AIG","PRU","MET","AFL","BRK-B",
}

# Fintech/payments with strong FCF – DCF applies despite "Financial" sector label
DCF_APPLICABLE = {
    "PYPL","SQ","V","MA","AXP","COF","DFS","COIN",
}

# Stocks where DCF is not reliable due to volatile/insufficient FCF history
# Show a strong warning and suggest alternative valuation methods instead
DCF_UNRELIABLE = {
    "CEG",    # Constellation Energy – only 1 positive FCF year; nuclear earnings priced in
    "VWAPY",  # Volkswagen ADR – negative FCF
}

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def _median(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def calculate_fcf_base(cashflow):
    if "Free Cash Flow" not in cashflow.index:
        return None, "not available", [], [], []
    fcf_series = cashflow.loc["Free Cash Flow"]
    fcf_years  = list(fcf_series.index[:5])
    fcf_values = [round(float(v) / 1e9, 2) for v in fcf_series.values[:5]]

    # Pair each year with its raw value, skip NaN (v == v is False for NaN)
    year_raw = [(yr, float(v)) for yr, v in zip(fcf_years, fcf_series.values[:5]) if v == v]
    positive = [(yr, v) for yr, v in year_raw if v > 0]

    if not positive:
        return float(fcf_series.values[0]), "⚠️ all negative", fcf_values, fcf_years, []

    if len(positive) < 3:
        fcf = sum(v for _, v in positive) / len(positive)
        return fcf, f"⚠️ avg of {len(positive)} positive years", fcf_values, fcf_years, []

    median_val  = _median([v for _, v in positive])
    recent_raw  = year_raw[0][1]        # most recent year (may be ≤ 0)
    recent_yr   = str(year_raw[0][0])[:4]

    if recent_raw > 0 and recent_raw > median_val * 1.5:
        # Growth stock: most recent FCF well above historical median → best indicator
        fcf            = recent_raw
        outlier_labels = []
        note = (f"✅ most recent year ({recent_yr}) – "
                f"growth stock ({recent_raw/median_val:.1f}× above median)")

    elif recent_raw > 0 and recent_raw < median_val * 0.5:
        # Recent year is an anomalous dip → median of all positive years is more reliable
        fcf            = median_val
        outlier_labels = [recent_yr]
        note = (f"✅ median of {len(positive)} years – "
                f"{recent_yr} is outlier ({recent_raw/median_val:.0%} of median)")

    else:
        # Stable earnings → 3-year average of the most recent 3 positive years
        top3 = [v for _, v in positive[:3]]
        fcf  = sum(top3) / 3
        outlier_labels = []
        note = "✅ 3-year average (stable earnings)"

    return fcf, note, fcf_values, fcf_years, outlier_labels


_fx_cache: dict = {}

def get_fx_rate(from_ccy, to_ccy):
    """Fetch live FX rate from_ccy → to_ccy, e.g. DKK → USD. Returns 1.0 on failure."""
    if from_ccy == to_ccy:
        return 1.0
    key = f"{from_ccy}{to_ccy}"
    now = datetime.now()
    cached = _fx_cache.get(key)
    if cached and (now - cached["fetched_at"]).seconds < 3600:
        return cached["rate"]
    try:
        ticker = yf.Ticker(f"{from_ccy}{to_ccy}=X")
        rate   = ticker.fast_info.get("lastPrice") or ticker.info.get("regularMarketPrice")
        if rate and 0 < rate < 1e6:
            _fx_cache[key] = {"rate": float(rate), "fetched_at": now}
            return float(rate)
    except Exception:
        pass
    return 1.0


_rfr_cache: dict = {}

def get_risk_free_rate():
    """Live 10Y Treasury yield via ^TNX, cached for 1 hour."""
    now = datetime.now()
    if _rfr_cache.get("fetched_at") and (now - _rfr_cache["fetched_at"]).seconds < 3600:
        return _rfr_cache["rate"], _rfr_cache["live"], _rfr_cache["fetched_at"]
    try:
        rate = yf.Ticker("^TNX").info.get("regularMarketPrice", None)
        if rate and 0.5 < rate < 20:
            result = rate / 100
            _rfr_cache.update({"rate": result, "live": True, "fetched_at": now})
            return result, True, now
    except Exception:
        pass
    _rfr_cache.update({"rate": 0.04, "live": False, "fetched_at": now})
    return 0.04, False, now


def blume_adjusted_beta(raw_beta):
    """Blume adjustment: mean reversion toward 1.0"""
    if not raw_beta:
        return 1.0
    return round(0.67 * raw_beta + 0.33 * 1.0, 4)


def get_equity_risk_premium(country):
    """ERP by region – based on Damodaran averages."""
    erp_map = {
        "United States": 0.055,
        "Germany":        0.060,
        "Switzerland":    0.058,
        "United Kingdom": 0.060,
        "France":         0.062,
        "Netherlands":    0.059,
        "Japan":          0.065,
    }
    return erp_map.get(country, 0.060)  # default 6% for unknown regions


TOBACCO_SYMBOLS = {"MO", "PM", "BTI", "BATS.L", "IMB.L", "MO.SW", "MO.BA"}


def get_terminal_growth_default(sector, symbol, revenue_growth=None):
    """Return (default_rate, max_rate, description) based on sector/symbol characteristics."""
    sector      = sector or ""
    sym         = (symbol or "").upper()
    rev_g       = revenue_growth or 0.0
    GDP_CAP     = 0.030   # hard ceiling for any company

    if sym in TOBACCO_SYMBOLS or "tobacco" in sector.lower():
        return 0.010, 0.015, "Tobacco: declining industry (recommended 1.0–1.5%)"
    if "Utilities" in sector:
        return 0.015, 0.025, "Utilities: regulated, slow growth (recommended 1.5–2.5%)"
    if "Energy" in sector:
        return 0.015, 0.020, "Energy: commodity cyclical (recommended 1.5–2.0%)"
    if "Consumer" in sector and "Defensive" in sector and rev_g < 0:
        return 0.015, 0.020, "Consumer Defensive (declining revenue): recommended 1.5–2.0%"
    if ("Technology" in sector or "Healthcare" in sector) and rev_g > 0:
        return 0.020, GDP_CAP, "Technology/Healthcare (growing): recommended 2.0–3.0%"
    return 0.020, GDP_CAP, "Standard assumption (recommended 2.0–3.0%)"


def calculate_wacc(info, debt_fx=1.0):
    raw_beta   = float(info.get("beta") or 1.0)
    adj_beta   = blume_adjusted_beta(raw_beta)
    country    = info.get("country") or "United States"
    rfr, rfr_live, rfr_date = get_risk_free_rate()
    erp        = get_equity_risk_premium(country)
    debt       = float(info.get("totalDebt") or 0) * debt_fx   # convert to trading ccy
    mktcap     = float(info.get("marketCap") or 0)
    interest   = float(info.get("interestExpense") or 0)
    tax        = float(info.get("effectiveTaxRate") or 0.21)
    cost_eq    = rfr + adj_beta * erp
    cost_debt_estimated = False
    if debt > 0 and interest:
        cost_debt = abs(interest) / debt
    elif debt > 0:
        # Estimate pre-tax cost of debt from leverage when yfinance lacks interest expense
        debt_to_mktcap = debt / mktcap if mktcap > 0 else 99
        if debt_to_mktcap > 2:
            cost_debt = 0.055   # high leverage → speculative-grade spread
        elif debt_to_mktcap > 1:
            cost_debt = 0.045   # moderate leverage → investment-grade spread
        else:
            cost_debt = 0.040   # low leverage → strong investment-grade
        cost_debt_estimated = True
    else:
        cost_debt = 0.040
    cost_debt_at = cost_debt * (1 - tax)
    total      = mktcap + debt
    eq_weight  = mktcap / total if total > 0 else 1.0
    debt_weight = debt  / total if total > 0 else 0.0
    wacc       = eq_weight * cost_eq + debt_weight * cost_debt_at
    return {
        "wacc":               wacc,
        "raw_beta":           raw_beta,
        "adj_beta":           adj_beta,
        "cost_eq":            cost_eq,
        "cost_debt":          cost_debt,
        "cost_debt_at":       cost_debt_at,
        "cost_debt_estimated": cost_debt_estimated,
        "eq_weight":          eq_weight,
        "debt_weight":        debt_weight,
        "rfr":                rfr,
        "rfr_live":           rfr_live,
        "rfr_date":           rfr_date.strftime("%Y-%m-%d"),
        "erp":                erp,
        "country":            country,
    }


def calculate_value_score_detail(e):
    details     = {}
    sector      = e.get("sector") or ""
    symbol      = e.get("symbol") or e.get("Symbol") or ""
    fcf         = e.get("fcf") or 0
    mktcap      = e.get("market_cap") or 0
    div         = e.get("dividend") or 0
    # Financial sector: only true banks/insurers in DCF_EXEMPT skip DCF;
    # fintech/payments in DCF_APPLICABLE always use DCF regardless of sector label
    is_fin      = "Financial" in sector and symbol in DCF_EXEMPT and symbol not in DCF_APPLICABLE
    is_util_re  = "Utilities" in sector or "Real Estate" in sector
    has_div     = div > 0

    # --- DCF Deviation (max 25) ---
    if is_fin:
        details["DCF Deviation"] = {
            "points": 0, "max": 25, "applicable": False,
            "note": "Not applicable – Financial sector: banks have no operational FCF"
        }
    elif is_util_re:
        details["DCF Deviation"] = {
            "points": 0, "max": 25, "applicable": False,
            "note": "Not applicable – Utilities/REITs: dividend yield used instead"
        }
    else:
        dcf_pts = 0
        if fcf > 0:
            dev = e.get("deviation") or 0
            if dev < -40:   dcf_pts = 25
            elif dev < -20: dcf_pts = 18
            elif dev < 0:   dcf_pts = 10
            elif dev < 20:  dcf_pts = 4
        details["DCF Deviation"] = {"points": dcf_pts, "max": 25, "applicable": True, "note": ""}

    # --- FCF Quality (max 20) ---
    if is_fin:
        details["FCF Quality"] = {
            "points": 0, "max": 20, "applicable": False,
            "note": "Not applicable – Financial sector: asset-based business model"
        }
    else:
        fcf_yield = (fcf / mktcap * 100) if mktcap > 0 and fcf > 0 else 0
        fcf_cagr  = e.get("fcf_cagr") or 0
        fcf_pts   = 0
        if fcf > 0:         fcf_pts += 5
        if fcf_yield > 8:   fcf_pts += 8
        elif fcf_yield > 5: fcf_pts += 5
        elif fcf_yield > 3: fcf_pts += 2
        if fcf_cagr > 10:   fcf_pts += 7
        elif fcf_cagr > 5:  fcf_pts += 4
        elif fcf_cagr > 0:  fcf_pts += 2
        details["FCF Quality"] = {"points": fcf_pts, "max": 20, "applicable": True, "note": ""}

    # --- Valuation (max 25) ---
    pe   = e.get("pe") or 0
    pb   = e.get("pb") or 0
    eveb = e.get("ev_ebitda") or 0
    roe  = e.get("roe") or 0
    roe  = roe * 100 if roe and abs(roe) < 2 else roe
    neg_book_equity = pb < 0
    mult_pts = 0
    if is_fin:
        if 0 < pb < 0.8:    mult_pts += 15
        elif 0 < pb < 1.2:  mult_pts += 10
        elif 0 < pb < 1.8:  mult_pts += 5
        if roe > 15:        mult_pts += 10
        elif roe > 10:      mult_pts += 6
        elif roe > 7:       mult_pts += 3
    elif is_util_re:
        if 0 < pe < 15:     mult_pts += 12
        elif 0 < pe < 20:   mult_pts += 7
        elif 0 < pe < 25:   mult_pts += 3
        if div > 4:         mult_pts += 13
        elif div > 3:       mult_pts += 8
        elif div > 2:       mult_pts += 4
    elif "Energy" in sector:
        if 0 < eveb < 5:    mult_pts += 15
        elif 0 < eveb < 8:  mult_pts += 9
        elif 0 < eveb < 12: mult_pts += 4
        if 0 < pe < 12:     mult_pts += 10
        elif 0 < pe < 18:   mult_pts += 5
    else:
        if 0 < pe < 12:     mult_pts += 9
        elif 0 < pe < 18:   mult_pts += 5
        elif 0 < pe < 25:   mult_pts += 2
        if not neg_book_equity:
            if 0 < pb < 1.5:    mult_pts += 8
            elif 0 < pb < 3:    mult_pts += 4
            elif 0 < pb < 5:    mult_pts += 2
        if 0 < eveb < 8:    mult_pts += 8
        elif 0 < eveb < 12: mult_pts += 4
    # P/B is meaningless with negative book equity – remove it from the scoring max
    val_max  = 17 if (neg_book_equity and not is_fin and not is_util_re and "Energy" not in sector) else 25
    val_note = "P/B excluded – negative book equity (buyback-driven)" if (neg_book_equity and val_max == 17) else ""
    details["Valuation"] = {"points": mult_pts, "max": val_max, "applicable": True, "note": val_note}

    # --- Profitability (max 15) ---
    margin = e.get("net_margin") or 0
    margin = margin * 100 if margin and abs(margin) < 1 else margin
    prof_pts  = 0
    prof_note = ""
    if neg_book_equity and roe <= 0:
        # ROE is distorted by negative equity denominator – use ROA instead
        roa = e.get("return_on_assets") or 0
        roa = roa * 100 if roa and abs(roa) < 1 else roa
        if roa > 10:    prof_pts += 8
        elif roa > 6:   prof_pts += 5
        elif roa > 3:   prof_pts += 2
        prof_note = "ROE not meaningful (negative book equity) – ROA used instead"
    else:
        if roe > 20:      prof_pts += 8
        elif roe > 12:    prof_pts += 5
        elif roe > 8:     prof_pts += 2
    if margin > 20:   prof_pts += 7
    elif margin > 10: prof_pts += 4
    elif margin > 5:  prof_pts += 2
    details["Profitability"] = {"points": prof_pts, "max": 15, "applicable": True, "note": prof_note}

    # --- Stability (max 15, or 8 if no dividend) ---
    thresholds = (1.5, 3.0, 5.0) if (is_fin or is_util_re) else (0.3, 0.8, 1.5)
    net_debt_ratio = (e.get("net_debt") or 0) / mktcap if mktcap > 0 else 0
    stab_pts = 0
    if net_debt_ratio < thresholds[0]:   stab_pts += 8
    elif net_debt_ratio < thresholds[1]: stab_pts += 5
    elif net_debt_ratio < thresholds[2]: stab_pts += 2
    if has_div:
        if div > 0: stab_pts += 4
        if div > 3: stab_pts += 3
        stab_max  = 15
        stab_note = ""
    else:
        stab_max  = 8
        stab_note = "Dividend component skipped – no dividend paid"
    details["Stability"] = {"points": stab_pts, "max": stab_max, "applicable": True, "note": stab_note}

    # --- Final score: achieved / max_applicable * 100 ---
    achieved = sum(d["points"] for d in details.values() if d["applicable"])
    maximum  = sum(d["max"]    for d in details.values() if d["applicable"])
    score    = round(achieved / maximum * 100) if maximum > 0 else 0
    return min(score, 100), details


SECTOR_DEFAULTS = {
    "Technology":             0.10,
    "Healthcare":             0.07,
    "Consumer Staples":       0.05,
    "Consumer Discretionary": 0.07,
    "Industrials":            0.06,
    "Energy":                 0.04,
    "Utilities":              0.03,
    "Real Estate":            0.04,
    "Financial Services":     0.05,
    "Financials":             0.05,
    "Materials":              0.05,
    "Communication Services": 0.07,
}

def calculate_realistic_growth(symbol, info, cashflow):
    """Returns (rate, sources) where sources is a list of dicts with name/value/weight."""
    rates, weights, sources = [], [], []

    # Detect high-growth stock to shift source weights toward analyst estimates
    earnings_growth = info.get("earningsGrowth")
    is_high_growth  = bool(earnings_growth and earnings_growth > 0.15)
    fcf_cagr_weight = 0.30 if is_high_growth else 0.50
    analyst_weight  = 0.50 if is_high_growth else 0.30

    # Source 1: Historical FCF CAGR – outlier-aware for stable stocks,
    # full-span for growth stocks whose recent FCF is far above historical median
    try:
        if "Free Cash Flow" in cashflow.index:
            raw = cashflow.loc["Free Cash Flow"].values
            year_vals = [(i, float(v)) for i, v in enumerate(raw[:5])
                         if v == v and float(v) > 0]
            if len(year_vals) >= 3:
                median_v = _median([v for _, v in year_vals])
                recent_v = year_vals[0][1]   # most recent positive FCF

                if recent_v > median_v * 1.5:
                    # Growth stock: outlier filter would wrongly discard the recent
                    # explosive years. Measure CAGR from oldest to newest instead.
                    oldest_i, oldest_v = year_vals[-1]
                    n_yrs = oldest_i  # index 0 is most recent, so span = oldest_i years
                    if n_yrs > 0 and oldest_v > 0:
                        cagr = (recent_v / oldest_v) ** (1 / n_yrs) - 1
                        cagr = max(-0.10, min(0.25, cagr))
                        rates.append(cagr)
                        weights.append(fcf_cagr_weight)
                        sources.append({"name": "Historical FCF CAGR (growth span)",
                                        "value": round(cagr * 100, 1),
                                        "weight": int(fcf_cagr_weight * 100)})
                else:
                    # Stable stock: exclude outlier years and compute CAGR on clean set
                    clean = [(i, v) for i, v in year_vals
                             if median_v > 0 and abs(v - median_v) / median_v <= 0.50]
                    if len(clean) >= 2:
                        start_i, start_v = clean[0]
                        end_i,   end_v   = clean[-1]
                        n_yrs = end_i - start_i
                        if n_yrs > 0 and end_v > 0:
                            cagr = (start_v / end_v) ** (1 / n_yrs) - 1
                            cagr = max(-0.10, min(0.25, cagr))
                            rates.append(cagr)
                            weights.append(fcf_cagr_weight)
                            sources.append({"name": "Historical FCF CAGR",
                                            "value": round(cagr * 100, 1),
                                            "weight": int(fcf_cagr_weight * 100)})
    except Exception:
        pass

    # Source 2: Analyst EPS growth forecast – cap at 50% rather than exclude
    if earnings_growth and earnings_growth > -0.30:
        eg_used = min(earnings_growth, 0.50)
        rates.append(eg_used)
        weights.append(analyst_weight)
        sources.append({"name": "Analyst EPS estimate",
                        "value": round(eg_used * 100, 1),
                        "weight": int(analyst_weight * 100)})

    # Source 3: Revenue growth as proxy – cap at 40% rather than exclude
    rev_growth = info.get("revenueGrowth")
    if rev_growth and rev_growth > -0.20:
        rg_used = min(rev_growth, 0.40)
        rates.append(rg_used)
        weights.append(0.20)
        sources.append({"name": "Revenue growth proxy",
                        "value": round(rg_used * 100, 1),
                        "weight": 20})

    if not rates:
        fallback = SECTOR_DEFAULTS.get(info.get("sector", ""), 0.05)
        sector   = info.get("sector", "unknown sector")
        return fallback, [{"name": f"Sector default ({sector})", "value": round(fallback * 100, 1), "weight": 100}]

    weighted = sum(r * w for r, w in zip(rates, weights)) / sum(weights)
    return round(weighted * 0.80, 4), sources  # 20% conservative haircut


CYCLICAL_SECTORS = {"Industrials", "Energy", "Materials", "Consumer Cyclical"}


def generate_warnings(r):
    """
    Return list of (icon, title, explanation) tuples for the given result dict.
    Covers the 7 priority cases defined in ROADMAP 0.5.
    """
    warns = []

    # 1. Negative book equity (P/B < 0)
    if r.get("neg_book_equity"):
        if r.get("neg_equity_warning"):
            # Net debt exceeded DCF enterprise value – more severe
            warns.append(("🔴", "Negative book equity – DCF equity also negative",
                "Net debt exceeds discounted cash flows; intrinsic shown is enterprise value ÷ shares. "
                "Result is optimistic – verify debt figures manually."))
        else:
            warns.append(("🔴", "Negative book equity",
                "Company has more liabilities than assets (likely buyback-driven). "
                "P/B and ROE are not meaningful; Value Score adjusted."))

    # 2. Very high debt (net_debt > 2× market_cap)
    mktcap_bn = r.get("market_cap") or 0
    net_debt_bn = r.get("net_debt") or 0
    if mktcap_bn > 0 and net_debt_bn > 2.0 * mktcap_bn:
        ratio = net_debt_bn / mktcap_bn
        warns.append(("🔴", "Very high debt",
            f"Net debt is {ratio:.1f}× market cap. "
            "Company is highly leveraged – DCF result sensitive to assumptions."))

    # 3. Only 1–2 positive FCF years
    fcf_note = r.get("fcf_note") or ""
    if "1 positive" in fcf_note or "2 positive" in fcf_note or "avg of 1" in fcf_note or "avg of 2" in fcf_note:
        warns.append(("🔴", "Insufficient FCF history",
            "Fewer than 3 positive FCF years available – DCF result is highly uncertain."))

    # 4. Growth premium gap (price > 2.5× intrinsic AND P/E < 40)
    intrinsic = r.get("intrinsic") or 0
    price     = r.get("price") or 0
    pe        = r.get("pe") or 0
    if intrinsic > 0 and price > 2.5 * intrinsic and 0 < pe < 40:
        ratio = price / intrinsic
        warns.append(("⚠️", "Growth premium not captured",
            f"Market trades at {ratio:.1f}× our DCF value. "
            "Market is pricing in significantly higher future growth than the model assumes."))

    # 5. Cyclical sector
    if r.get("sector") in CYCLICAL_SECTORS:
        warns.append(("⚠️", "Cyclical sector",
            f"{r['sector']} earnings vary with the business cycle. "
            "FCF may be at cycle peak – DCF could overstate normalised earning power."))

    # 6. Currency conversion applied
    if r.get("fx_converted"):
        warns.append(("⚠️", "Currency conversion applied",
            f"Financials reported in {r.get('fx_from')}, converted to {r.get('fx_to')} "
            f"at {r.get('fx_rate', 1):.4f}. Exchange-rate moves affect the result."))

    # 7. Terminal growth capped
    if r.get("terminal_capped"):
        warns.append(("⚠️", "Terminal growth rate capped",
            f"Your input of {r.get('terminal_original', 0):.1f}% was reduced to "
            f"{r.get('terminal_assumption', 0):.1f}% based on sector limits. "
            f"{r.get('terminal_desc', '')}"))

    return warns


def check_terminal_value(tv_disc_bn, ebitda_bn, wacc, terminal_growth):
    """Plausibility checks for terminal value. Returns (warnings, implied_multiple)."""
    warnings       = []
    implied_multiple = None

    if terminal_growth > 0.025:
        warnings.append(
            f"⚠️ Terminal growth {terminal_growth*100:.1f}% exceeds long-term GDP growth "
            f"(~2.5%). Consider reducing."
        )

    if ebitda_bn and ebitda_bn > 0:
        implied_multiple = tv_disc_bn / ebitda_bn
        if implied_multiple > 25:
            warnings.append(
                f"⚠️ Terminal Value implies EV/EBITDA of {implied_multiple:.1f}x "
                f"– historically high. Most sectors trade at 8–15x."
            )
        elif implied_multiple < 4:
            warnings.append(
                f"⚠️ Terminal Value implies EV/EBITDA of {implied_multiple:.1f}x "
                f"– very low. Check WACC and growth assumptions."
            )

    return warnings, implied_multiple


def _dcf_intrinsic(fcf, shares, net_debt, growth, wacc, terminal):
    """Compute intrinsic value per share for one scenario."""
    if wacc <= terminal or shares == 0:
        return None
    current_fcf = fcf
    discounted  = []
    for yr in range(1, 11):
        current_fcf *= (1 + growth)
        discounted.append(current_fcf / (1 + wacc) ** yr)
    tv      = current_fcf * (1 + terminal) / (wacc - terminal)
    tv_disc = tv / (1 + wacc) ** 10
    equity  = sum(discounted) + tv_disc - net_debt
    return equity / shares


def reverse_dcf(price, fcf, wacc, terminal, shares, net_debt):
    """Binary search for FCF growth rate that makes DCF intrinsic value = current price."""
    if shares == 0 or price <= 0 or fcf <= 0:
        return None
    lo, hi = -0.10, 0.50
    for _ in range(50):
        mid = (lo + hi) / 2
        iv  = _dcf_intrinsic(fcf, shares, net_debt, mid, wacc, terminal)
        if iv is None:
            return None
        if iv < price:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2 * 100, 1)


def run_dcf(symbol, growth=None, terminal=0.03, margin_of_safety=0.25, wacc_override=None):
    try:
        ticker     = yf.Ticker(symbol)
        info       = ticker.info
        cashflow   = ticker.cashflow
        financials = ticker.financials
    except Exception as ex:
        return None, str(ex)

    if not info or not info.get("longName"):
        return None, "Stock not found"

    sym_upper = symbol.upper()
    if sym_upper in DCF_UNRELIABLE:
        pe = info.get("trailingPE") or info.get("forwardPE")
        pe_str = f"{pe:.1f}×" if pe else "N/A"
        return None, (
            f"DCF not reliable for {symbol} – highly volatile or insufficient FCF history. "
            f"Current P/E: {pe_str}. Consider P/E or EV/EBITDA valuation instead."
        )

    fcf, fcf_note, fcf_history, fcf_years, fcf_outliers = calculate_fcf_base(cashflow)
    if fcf is None:
        return None, "Free Cash Flow not available"

    shares = info.get("sharesOutstanding")
    if not shares:
        return None, "Shares outstanding not available"

    growth_auto    = growth is None
    growth_sources = []
    if growth_auto:
        growth, growth_sources = calculate_realistic_growth(symbol, info, cashflow)

    # --- Currency conversion: financials may be in a different currency than the stock price ---
    fin_ccy    = (info.get("financialCurrency") or "").upper()
    trade_ccy  = (info.get("currency") or "").upper()
    fx_rate        = 1.0
    fx_converted   = False
    if fin_ccy and trade_ccy and fin_ccy != trade_ccy:
        fx_rate = get_fx_rate(fin_ccy, trade_ccy)
        if fx_rate != 1.0:
            fcf          *= fx_rate
            fcf_history   = [round(v * fx_rate, 2) for v in fcf_history]
            fx_converted  = True

    debt     = float(info.get("totalDebt") or 0) * fx_rate
    cash     = float(info.get("totalCash") or 0) * fx_rate
    net_debt = debt - cash
    mktcap   = float(info.get("marketCap") or 0)

    wc         = calculate_wacc(info, debt_fx=fx_rate)
    wacc_calc  = wc["wacc"]
    beta       = wc["adj_beta"]
    cost_eq    = wc["cost_eq"]
    cost_debt  = wc["cost_debt_at"]
    eq_w       = wc["eq_weight"]
    debt_w     = wc["debt_weight"]
    wacc = wacc_override if wacc_override else wacc_calc

    # --- Sector-aware terminal growth cap ---
    rev_g_info  = info.get("revenueGrowth")   # fast proxy; full calc happens later
    term_default, term_max, term_desc = get_terminal_growth_default(
        info.get("sector", ""), symbol, rev_g_info
    )
    terminal_original = terminal
    terminal_capped   = terminal > term_max
    if terminal_capped:
        terminal = term_max

    if wacc <= terminal:
        return None, "WACC must be greater than terminal growth rate"

    discounted  = []
    projected   = []
    current_fcf = fcf
    for yr in range(1, 11):
        current_fcf *= (1 + growth)
        projected.append(round(current_fcf / 1e9, 2))
        discounted.append(current_fcf / (1 + wacc) ** yr)

    tv         = current_fcf * (1 + terminal) / (wacc - terminal)
    tv_disc    = tv / (1 + wacc) ** 10
    enterprise = sum(discounted) + tv_disc
    equity     = enterprise - net_debt
    neg_book_equity  = (info.get("priceToBook") or 1) < 0
    neg_equity_warning = None
    if equity <= 0:
        neg_equity_warning = (
            f"⚠️ Net debt (${net_debt/1e9:.1f}B) exceeds DCF enterprise value "
            f"(${enterprise/1e9:.1f}B). Intrinsic value shown uses enterprise value ÷ shares "
            f"(net debt adjustment omitted). Result is optimistic – verify debt figures."
        )
        equity = enterprise  # fallback: show enterprise value per share
    intrinsic  = equity / shares
    with_margin = intrinsic * (1 - margin_of_safety)
    price      = float(info.get("currentPrice") or 0)
    deviation  = (price - intrinsic) / intrinsic * 100 if intrinsic != 0 else 0

    ebitda_raw = float(info.get("ebitda") or 0) * fx_rate
    tv_pct     = tv_disc / enterprise * 100 if enterprise != 0 else 0
    tv_warnings, tv_implied_multiple = check_terminal_value(
        tv_disc / 1e9, ebitda_raw / 1e9, wacc, terminal
    )

    fcf_cagr = None
    if len(fcf_history) >= 2 and fcf_history[-1] > 0 and fcf_history[0] > 0:
        fcf_cagr = ((fcf_history[0]/fcf_history[-1]) ** (1/(len(fcf_history)-1)) - 1) * 100

    rev_growth = None
    try:
        if "Total Revenue" in financials.index:
            rev = financials.loc["Total Revenue"].values
            if len(rev) >= 2 and rev[-1] > 0:
                rev_growth = ((rev[0]/rev[-1]) ** (1/(len(rev)-1)) - 1) * 100
    except:
        pass

    # --- Three-Scenario DCF ---
    scenario_defs = {
        "Bear": {"growth": growth * 0.70, "wacc": wacc + 0.01, "terminal": terminal - 0.005, "weight": 0.25},
        "Base": {"growth": growth,         "wacc": wacc,         "terminal": terminal,         "weight": 0.50},
        "Bull": {"growth": growth * 1.30,  "wacc": wacc - 0.01,  "terminal": terminal + 0.005, "weight": 0.25},
    }
    scenarios = {}
    for sname, sp in scenario_defs.items():
        iv = _dcf_intrinsic(fcf, shares, net_debt, sp["growth"], sp["wacc"], sp["terminal"])
        if iv is not None:
            dev = (price - iv) / iv * 100 if iv != 0 else 0
            scenarios[sname] = {
                "intrinsic":    round(iv, 2),
                "with_margin":  round(iv * (1 - margin_of_safety), 2),
                "deviation":    round(dev, 1),
                "weight":       sp["weight"],
                "growth_pct":   round(sp["growth"] * 100, 1),
                "wacc_pct":     round(sp["wacc"] * 100, 2),
                "terminal_pct": round(sp["terminal"] * 100, 2),
            }
    if scenarios:
        weighted_iv  = sum(s["intrinsic"] * s["weight"] for s in scenarios.values())
        weighted_mos = weighted_iv * (1 - margin_of_safety)
        weighted_dev = (price - weighted_iv) / weighted_iv * 100 if weighted_iv != 0 else 0
    else:
        weighted_iv  = intrinsic
        weighted_mos = with_margin
        weighted_dev = deviation

    result = {
        "name":               info.get("longName", symbol),
        "symbol":             symbol,
        "sector":             info.get("sector", "N/A"),
        "price":              round(price, 2),
        "intrinsic":          round(intrinsic, 2),
        "with_margin":        round(with_margin, 2),
        "deviation":          round(deviation, 1),
        "wacc":               round(wacc * 100, 2),
        "wacc_calculated":    round(wacc_calc * 100, 2),
        "beta":               round(beta, 2),
        "raw_beta":           round(wc["raw_beta"], 2),
        "adj_beta":           round(wc["adj_beta"], 2),
        "rfr":                round(wc["rfr"] * 100, 2),
        "rfr_live":           wc["rfr_live"],
        "rfr_date":           wc["rfr_date"],
        "erp":                round(wc["erp"] * 100, 2),
        "country":            wc["country"],
        "cost_equity":        round(cost_eq * 100, 2),
        "cost_debt":          round(cost_debt * 100, 2),
        "equity_weight":      round(eq_w * 100, 1),
        "debt_weight":        round(debt_w * 100, 1),
        "fcf_note":           fcf_note,
        "fcf_outliers":       fcf_outliers,
        "fcf":                round(fcf / 1e9, 2),
        "fcf_history":        fcf_history,
        "fcf_years":          [str(y)[:10] for y in fcf_years],
        "fcf_cagr":           round(fcf_cagr, 1) if fcf_cagr else None,
        "projected_fcfs":     projected,
        "terminal_value":     round(tv_disc / 1e9, 2),
        "sum_discounted":     round(sum(discounted) / 1e9, 2),
        "net_debt":           round(net_debt / 1e9, 2),
        "market_cap":         round(mktcap / 1e9, 2),
        "shares":             round(shares / 1e9, 2),
        "total_debt":         round(debt / 1e9, 2),
        "cash":               round(cash / 1e9, 2),
        "pe":                 info.get("trailingPE"),
        "forward_pe":         info.get("forwardPE"),
        "pb":                 info.get("priceToBook"),
        "ev_ebitda":          info.get("enterpriseToEbitda"),
        "ps":                 info.get("priceToSalesTrailing12Months"),
        "roe":                info.get("returnOnEquity"),
        "net_margin":         info.get("profitMargins"),
        "dividend":           info.get("dividendYield"),
        "revenue_growth":     round(rev_growth, 1) if rev_growth else None,
        "growth_assumption":    round(growth * 100, 1),
        "growth_auto":          growth_auto,
        "growth_sources":       growth_sources,
        "terminal_assumption":  round(terminal * 100, 1),
        "terminal_original":    round(terminal_original * 100, 1),
        "terminal_capped":      terminal_capped,
        "terminal_recommendation": round(term_default * 100, 1),
        "terminal_max":         round(term_max * 100, 1),
        "terminal_desc":        term_desc,
        "cost_debt_estimated":  wc["cost_debt_estimated"],
        "mos_assumption":       round(margin_of_safety * 100, 0),
        "fx_converted":         fx_converted,
        "fx_from":              fin_ccy if fx_converted else None,
        "fx_to":                trade_ccy if fx_converted else None,
        "fx_rate":              round(fx_rate, 6) if fx_converted else None,
        "tv_pct":               round(tv_pct, 1),
        "tv_implied_multiple":  round(tv_implied_multiple, 1) if tv_implied_multiple else None,
        "tv_warnings":          tv_warnings,
        "scenarios":            scenarios,
        "weighted_intrinsic":   round(weighted_iv, 2),
        "weighted_with_margin": round(weighted_mos, 2),
        "weighted_deviation":   round(weighted_dev, 1),
        "neg_book_equity":      neg_book_equity,
        "neg_equity_warning":   neg_equity_warning,
        "return_on_assets":     info.get("returnOnAssets"),
        "last_updated":         datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    score, details = calculate_value_score_detail(result)
    result["value_score"]         = score
    result["value_score_details"] = details
    return result, None


def result_to_db_entry(r):
    return {
        "Symbol":           r["symbol"],
        "Name":             r["name"],
        "Sector":           r["sector"],
        "Price":            r["price"],
        "Intrinsic Value":  r["intrinsic"],
        "With MoS":         r["with_margin"],
        "Deviation %":      r["deviation"],
        "Value Score":      r.get("value_score", 0),
        "WACC %":           r["wacc"],
        "FCF Growth %":     r["growth_assumption"],
        "Terminal %":       r["terminal_assumption"],
        "MoS %":            r["mos_assumption"],
        "P/E":              round(r["pe"], 2) if r.get("pe") else None,
        "Forward P/E":      round(r["forward_pe"], 2) if r.get("forward_pe") else None,
        "P/B":              round(r["pb"], 2) if r.get("pb") else None,
        "EV/EBITDA":        round(r["ev_ebitda"], 2) if r.get("ev_ebitda") else None,
        "FCF (Bn)":         r["fcf"],
        "FCF CAGR %":       r.get("fcf_cagr"),
        "ROE %":            round(r["roe"]*100,2) if r.get("roe") else None,
        "Net Margin %":     round(r["net_margin"]*100,2) if r.get("net_margin") else None,
        "Dividend %":       round(r["dividend"] * 100, 2) if r.get("dividend") is not None and r["dividend"] < 1 else (round(r["dividend"], 2) if r.get("dividend") is not None else None),
        "Revenue Growth %": round(r.get("revenue_growth"), 2) if r.get("revenue_growth") else None,
        "Net Debt (Bn)":    r.get("net_debt"),
        "Market Cap (Bn)":  r.get("market_cap"),
        "FCF Note":         r["fcf_note"],
        "Last Updated":     r.get("last_updated", ""),
    }


def save_to_database(result):
    entry   = result_to_db_entry(result)
    symbols = [e["Symbol"] for e in st.session_state.database]
    if result["symbol"] in symbols:
        st.session_state.database[symbols.index(result["symbol"])] = entry
    else:
        st.session_state.database.append(entry)
    ok = save_database(st.session_state.database, st.session_state.db_sha)
    if ok:
        _, st.session_state.db_sha = load_database()
    return ok


def search_stock(query):
    try:
        res  = yf.Search(query, max_results=6)
        hits = res.quotes
        if hits:
            names   = [f"{h.get('shortname', h.get('longname','?'))} – {h.get('symbol','?')}" for h in hits]
            symbols = [h.get("symbol","") for h in hits]
            return names, symbols
    except:
        pass
    return [], []


def score_color(points, maximum):
    ratio = points / maximum if maximum > 0 else 0
    if ratio >= 0.75:   return "🟢"
    elif ratio >= 0.5:  return "🟡"
    elif ratio >= 0.25: return "🟠"
    else:               return "🔴"


def show_value_score(result):
    score   = result.get("value_score", 0)
    details = result.get("value_score_details", {})
    color   = "green" if score >= 60 else "orange" if score >= 40 else "red"
    st.markdown(f"### Value Score: :{color}[{score}/100]")
    if details:
        cols = st.columns(len(details))
        for i, (name, vals) in enumerate(details.items()):
            p          = vals["points"]
            m          = vals["max"]
            applicable = vals.get("applicable", True)
            note       = vals.get("note", "")
            if not applicable:
                cols[i].metric(label=f"⚪ {name}", value="N/A", delta="Skipped")
                if note:
                    cols[i].caption(note)
            else:
                ico = score_color(p, m)
                cols[i].metric(
                    label=f"{ico} {name}",
                    value=f"{p}/{m}",
                    delta=f"{round(p/m*100):.0f}%" if m > 0 else "N/A"
                )
                if note:
                    cols[i].caption(note)

        applicable_details = {k: v for k, v in details.items() if v.get("applicable", True)}
        if applicable_details:
            fig = go.Figure(go.Bar(
                x=list(applicable_details.keys()),
                y=[d["points"] for d in applicable_details.values()],
                marker_color=[
                    "#1D9E75" if d["points"]/d["max"] >= 0.75
                    else "#EF9F27" if d["points"]/d["max"] >= 0.5
                    else "#E8593C" if d["points"]/d["max"] >= 0.25
                    else "#A32D2D"
                    for d in applicable_details.values()
                ],
                text=[f"{d['points']}/{d['max']}" for d in applicable_details.values()],
                textposition="auto"
            ))
            fig.update_layout(
                title="Value Score Breakdown (applicable categories only)",
                yaxis_title="Points",
                height=260,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)


# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.title("📈 Stock Analysis")
page = st.sidebar.radio(
    "Navigation",
    ["🔍 Analysis", "📊 Database", "🔄 Batch Analysis", "📖 Methodology"]
)
st.sidebar.divider()
st.sidebar.caption(f"Database: {len(st.session_state.database)} stocks")
st.sidebar.caption(f"Portfolio: {len(st.session_state.portfolio)} positions")
if st.sidebar.button("🔄 Reload Data", key="reload_data"):
    st.session_state.database, st.session_state.db_sha   = load_database()
    st.session_state.portfolio, st.session_state.port_sha = load_portfolio()
    st.rerun()

# ================================================================
# PAGE 0: DASHBOARD
# ================================================================
if page == "🏠 Dashboard":
    st.title("Dashboard")
    st.caption(f"As of {datetime.now().strftime('%B %d, %Y %H:%M')}")

    if not st.session_state.database:
        st.info("No data yet. Run a batch analysis or analyze stocks individually.")
    else:
        df = pd.DataFrame(st.session_state.database)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stocks Analyzed", len(df))
        underval = len(df[df["Deviation %"] < 0]) if "Deviation %" in df.columns else 0
        col2.metric("Undervalued", underval)
        most_under = df.loc[df["Deviation %"].idxmin(), "Symbol"] if "Deviation %" in df.columns else "–"
        col3.metric("Most Undervalued", most_under)
        avg_dev = round(df["Deviation %"].mean(), 1) if "Deviation %" in df.columns else 0
        col4.metric("Avg Deviation", f"{avg_dev:+.1f}%")

        st.divider()
        st.subheader("🏆 Top 10 Buy Opportunities")
        st.caption("Ranked by deviation from intrinsic value – most undervalued first")

        top10 = df.nsmallest(10, "Deviation %")[
            ["Symbol","Name","Sector","Price","Intrinsic Value",
             "Deviation %","P/E","FCF CAGR %","Dividend %"]
        ]
        st.dataframe(
            top10.style
            .background_gradient(subset=["Deviation %"], cmap="RdYlGn_r")
            .format({"Deviation %": "{:+.1f}%", "Price": "${:.2f}",
                     "Intrinsic Value": "${:.2f}", "Dividend %": "{:.2f}%",
                     "P/E": "{:.2f}", "FCF CAGR %": "{:.2f}"}, na_rep="N/A"),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            sector_df = df.groupby("Sector")["Deviation %"].mean().reset_index()
            sector_df = sector_df.sort_values("Deviation %", ascending=True)
            fig = px.bar(sector_df, x="Sector", y="Deviation %",
                         title="Avg Deviation % by Sector",
                         color="Deviation %",
                         color_continuous_scale="RdYlGn_r")
            fig.update_layout(height=300, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            if "Deviation %" in df.columns:
                fig2 = px.histogram(
                    df, x="Deviation %",
                    title="Distribution of Valuations",
                    nbins=30,
                    color_discrete_sequence=["#378ADD"]
                )
                fig2.add_vline(x=0, line_dash="dash", line_color="gray")
                fig2.update_layout(height=300)
                st.plotly_chart(fig2, use_container_width=True)

# ================================================================
# PAGE 1: ANALYSIS
# ================================================================
elif page == "🔍 Analysis":
    st.title("Stock Analysis")

    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Search for a stock",
            placeholder="Type name or symbol and press Enter...",
            key="search_input"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.button("Search", use_container_width=True, key="search_btn")

    if (search_btn or query) and query:
        if search_btn or st.session_state.get("last_query") != query:
            names, symbols = search_stock(query)
            st.session_state.search_names   = names
            st.session_state.search_symbols = symbols
            st.session_state.last_query     = query

    selected_symbol = ""
    if st.session_state.search_symbols:
        choice = st.selectbox("Results:", st.session_state.search_names)
        idx    = st.session_state.search_names.index(choice)
        selected_symbol = st.session_state.search_symbols[idx]
        st.info(f"Selected: **{selected_symbol}**")

    with st.expander("Or enter symbol directly"):
        direct = st.text_input("Symbol", placeholder="e.g. AAPL, SAP.DE, ASML.AS")
        if direct:
            selected_symbol = direct.upper()

    st.divider()
    st.subheader("Assumptions")

    # FCF Growth: auto-calculated by default, manual slider as override
    auto_growth = st.checkbox("Auto-calculate FCF growth rate (recommended)", value=True)
    growth = None  # signals run_dcf() to use calculate_realistic_growth()
    if not auto_growth:
        last_auto = st.session_state.get("last_auto_growth_pct", 8)
        growth = st.slider("FCF Growth % (manual override)", -20, 30, last_auto) / 100

    col1, col2 = st.columns(2)
    with col1:
        terminal = st.slider("Terminal Growth %", 0, 6, 2) / 100
        _last = st.session_state.last_result
        if _last and _last.get("terminal_desc"):
            st.caption(f"💡 {_last['terminal_desc']}")
            if terminal * 100 > _last.get("terminal_max", 3.0):
                st.warning(
                    f"⚠️ Terminal growth {terminal*100:.1f}% above sector recommendation "
                    f"(max {_last['terminal_max']:.1f}% for this stock)"
                )
    with col2:
        mos = st.slider("Margin of Safety %", 0, 50, 25) / 100

    wacc_mode = st.radio("WACC", ["Automatic", "Manual"], horizontal=True)
    wacc_override = None
    if wacc_mode == "Manual":
        wacc_override = st.slider("WACC manual %", 1, 20, 8) / 100

    if st.button("Analyze", type="primary", use_container_width=True, key="analyze_btn"):
        if selected_symbol:
            with st.spinner(f"Loading data for {selected_symbol}..."):
                result, error = run_dcf(
                    selected_symbol, growth, terminal, mos, wacc_override
                )
            if result:
                st.session_state["last_auto_growth_pct"] = int(round(result["growth_assumption"]))
            if error:
                st.error(f"Error: {error}")
            else:
                st.session_state.last_result = result
        else:
            st.warning("Please search for and select a stock first.")

    if st.session_state.last_result:
        r = st.session_state.last_result
        st.divider()
        st.subheader(f"{r['name']} ({r['symbol']})")
        st.caption(f"Sector: {r['sector']}  ·  Last updated: {r.get('last_updated','')}")

        # --- Automatic warning flags ---
        warnings_list = generate_warnings(r)
        if warnings_list:
            with st.expander(f"⚠️ {len(warnings_list)} warning{'s' if len(warnings_list) > 1 else ''} – click to expand", expanded=True):
                for icon, title, explanation in warnings_list:
                    if icon == "🔴":
                        st.error(f"**{icon} {title}** – {explanation}")
                    else:
                        st.warning(f"**{icon} {title}** – {explanation}")

        # --- Cost of debt estimation notice ---
        if r.get("cost_debt_estimated"):
            st.info(
                "ℹ️ Interest expense not available from yfinance – cost of debt estimated "
                "from leverage ratio. WACC may be slightly imprecise."
            )

        # --- Growth rate info banner ---
        if r.get("growth_auto") and r.get("growth_sources"):
            src_parts = " · ".join(
                f"{s['name']} {s['value']:+.1f}% (weight {s['weight']}%)"
                for s in r["growth_sources"]
            )
            st.info(
                f"Auto-calculated FCF growth rate: **{r['growth_assumption']:.1f}%** "
                f"(20% conservative haircut applied)  \n"
                f"Sources: {src_parts}"
            )
        elif not r.get("growth_auto"):
            st.caption(f"Manual FCF growth rate: {r['growth_assumption']:.1f}%")

        # --- Weighted Fair Value (prominent) ---
        wdev = r.get("weighted_deviation", r["deviation"])
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price",        f"${r['price']:.2f}")
        col2.metric("Weighted Fair Value",  f"${r.get('weighted_intrinsic', r['intrinsic']):.2f}",
                    help="Bear×25% + Base×50% + Bull×25%")
        col3.metric("Weighted Max Buy",     f"${r.get('weighted_with_margin', r['with_margin']):.2f}",
                    help=f"Weighted fair value minus {r['mos_assumption']:.0f}% margin of safety")
        col4.metric("Valuation", f"{wdev:+.1f}%",
                    delta="Overvalued" if wdev > 0 else "Undervalued",
                    delta_color="inverse")

        # --- Three-Scenario Breakdown ---
        scenarios = r.get("scenarios", {})
        if scenarios:
            st.markdown("##### Scenario Analysis")
            colors = {"Bear": "#E57373", "Base": "#1D9E75", "Bull": "#64B5F6"}
            scol1, scol2, scol3 = st.columns(3)
            for scol, (sname, sc) in zip([scol1, scol2, scol3], scenarios.items()):
                dev_sign = f"{sc['deviation']:+.1f}%"
                label    = "Undervalued" if sc["deviation"] < 0 else "Overvalued"
                scol.metric(
                    f"{'🐻' if sname=='Bear' else '📊' if sname=='Base' else '🐂'} {sname}  (weight {int(sc['weight']*100)}%)",
                    f"${sc['intrinsic']:.2f}",
                    delta=f"{dev_sign} · {label}",
                    delta_color="normal" if sc["deviation"] < 0 else "inverse"
                )
                scol.caption(f"Growth {sc['growth_pct']:.1f}% · WACC {sc['wacc_pct']:.2f}% · Terminal {sc['terminal_pct']:.2f}%")

            fig_sc = go.Figure()
            fig_sc.add_trace(go.Bar(
                x=list(scenarios.keys()) + ["Weighted"],
                y=[s["intrinsic"] for s in scenarios.values()] + [r.get("weighted_intrinsic", r["intrinsic"])],
                marker_color=[colors.get(n, "#888") for n in scenarios.keys()] + ["#FFA726"],
                text=[f"${v:.2f}" for v in [s["intrinsic"] for s in scenarios.values()] + [r.get("weighted_intrinsic", r["intrinsic"])]],
                textposition="outside",
            ))
            fig_sc.add_hline(y=r["price"], line_dash="dash", line_color="#378ADD",
                             annotation_text=f"Current Price ${r['price']:.2f}")
            fig_sc.update_layout(
                title="Intrinsic Value by Scenario", height=320,
                yaxis_title="Intrinsic Value ($)", showlegend=False,
                margin=dict(t=50, b=20)
            )
            st.plotly_chart(fig_sc, use_container_width=True)

        # --- Reverse DCF box ---
        st.divider()
        _r_fcf   = r["fcf"] * 1e9   # back to raw units
        _r_nd    = r["net_debt"] * 1e9
        _r_sh    = r["shares"] * 1e9
        _r_wacc  = r["wacc"] / 100
        _r_term  = r["terminal_assumption"] / 100
        implied_g = reverse_dcf(r["price"], _r_fcf, _r_wacc, _r_term, _r_sh, _r_nd)
        our_g     = r["growth_assumption"]
        if implied_g is not None:
            diff = implied_g - our_g
            if diff > 5:
                interp = "Market expects significantly higher growth than our model. Stock may be fairly valued if growth materializes."
            elif diff < -5:
                interp = "Market expects lower growth than our model. Our DCF may be optimistic."
            else:
                interp = "Market and our model broadly agree on growth expectations."
            st.markdown(
                f"**📊 Market Implied Growth**\n\n"
                f"The current price of **${r['price']:.2f}** implies a FCF growth rate of **{implied_g:.1f}%**.\n\n"
                f"Our model assumes **{our_g:.1f}%**.\n\n"
                f"→ {interp}"
            )
        else:
            st.markdown("**📊 Market Implied Growth** – could not be computed (price outside model range).")

        # --- DCF Validation box ---
        st.divider()
        st.markdown("#### 🔍 Cross-check this valuation externally:")
        sym = r["symbol"].split(".")[0]   # strip exchange suffix for URL construction
        st.markdown(
            f"[Alpha Spread ↗](https://www.alphaspread.com/security/nyse/{sym}/summary)  "
            f"· [GuruFocus ↗](https://www.gurufocus.com/stock/{r['symbol']}/dcf)  "
            f"· [Simply Wall St ↗](https://simplywall.st/stocks/us/-/-{sym}/valuation)  "
            f"· [Macrotrends ↗](https://www.macrotrends.net/stocks/charts/{sym}/free-cash-flow)"
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Key Metrics", "💰 FCF & Cashflows",
            "🔢 DCF Calculation", "⚙️ WACC", "📈 Historical Charts"
        ])

        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Valuation**")
                st.write(f"P/E: {r['pe']:.1f}" if r.get('pe') else "P/E: N/A")
                st.write(f"Forward P/E: {r['forward_pe']:.1f}" if r.get('forward_pe') else "Forward P/E: N/A")
                st.write(f"P/B: {r['pb']:.2f}" if r.get('pb') else "P/B: N/A")
                st.write(f"EV/EBITDA: {r['ev_ebitda']:.1f}" if r.get('ev_ebitda') else "EV/EBITDA: N/A")
                st.write(f"P/S: {r['ps']:.2f}" if r.get('ps') else "P/S: N/A")
            with col2:
                st.markdown("**Profitability**")
                st.write(f"ROE: {r['roe']*100:.1f}%" if r.get('roe') else "ROE: N/A")
                st.write(f"Net Margin: {r['net_margin']*100:.1f}%" if r.get('net_margin') else "Net Margin: N/A")
                st.write(f"Revenue Growth: {r['revenue_growth']:.1f}%" if r.get('revenue_growth') else "Revenue Growth: N/A")
                st.write(f"Dividend Yield: {r['dividend']:.2f}%" if r.get('dividend') else "Dividend: none")
            with col3:
                st.markdown("**Balance Sheet**")
                st.write(f"Market Cap: ${r['market_cap']:.1f}B")
                st.write(f"Total Debt: ${r['total_debt']:.2f}B")
                st.write(f"Cash: ${r['cash']:.2f}B")
                st.write(f"Net Debt: ${r['net_debt']:.2f}B")
                st.write(f"Shares Outstanding: {r['shares']:.2f}B")

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Historical FCF**")
                st.write(f"FCF Base (used): ${r['fcf']}B")
                st.write(f"Quality: {r['fcf_note']}")
                for oy in r.get("fcf_outliers", []):
                    st.warning(f"⚠️ FCF outlier detected in {oy} – median used instead of average")
                st.write(f"FCF CAGR: {r['fcf_cagr']:.1f}%" if r.get('fcf_cagr') else "FCF CAGR: N/A")
                if r.get('fcf_history'):
                    fcf_df = pd.DataFrame({
                        "Year":     r['fcf_years'],
                        "FCF ($B)": r['fcf_history']
                    })
                    st.dataframe(fcf_df, hide_index=True, use_container_width=True)
            with col2:
                if r.get('fcf_history'):
                    fig = px.bar(
                        x=r['fcf_years'], y=r['fcf_history'],
                        labels={"x": "Year", "y": "FCF ($B)"},
                        title="Historical FCF",
                        color=r['fcf_history'],
                        color_continuous_scale="RdYlGn"
                    )
                    fig.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"**Projected FCFs ({r['growth_assumption']:.0f}% growth)**")
            proj_df = pd.DataFrame({
                "Year":     [f"Year {i+1}" for i in range(10)],
                "FCF ($B)": r['projected_fcfs']
            })
            fig2 = px.bar(proj_df, x="Year", y="FCF ($B)",
                          title="Projected FCFs (10 Years)",
                          color="FCF ($B)",
                          color_continuous_scale="Blues")
            fig2.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            st.markdown("**Complete DCF Calculation**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Inputs & Assumptions**")
                assumptions_df = pd.DataFrame({
                    "Parameter": [
                        "FCF Base", "FCF Growth p.a.", "Terminal Growth Rate",
                        "WACC (used)", "WACC (calculated)", "Margin of Safety",
                        "Forecast Period"
                    ],
                    "Value": [
                        f"${r['fcf']}B",
                        f"{r['growth_assumption']}%",
                        f"{r['terminal_assumption']}%",
                        f"{r['wacc']}%",
                        f"{r['wacc_calculated']}%",
                        f"{r['mos_assumption']:.0f}%",
                        "10 Years"
                    ]
                })
                st.dataframe(assumptions_df, hide_index=True, use_container_width=True)
            with col2:
                st.markdown("**Step-by-Step Calculation**")
                total      = r['sum_discounted'] + r['terminal_value']
                equity_val = total - r['net_debt']
                calc_df = pd.DataFrame({
                    "Step": [
                        "Sum of discounted FCFs (10Y)",
                        "Terminal Value (discounted)",
                        "= Enterprise Value",
                        "  Gross Debt",
                        "  – Cash & Equivalents",
                        "  = Net Debt",
                        "= Equity Value",
                        "÷ Shares Outstanding",
                        "= Intrinsic Value per Share",
                        "– Margin of Safety",
                        "= Max Buy Price"
                    ],
                    "Value": [
                        f"${r['sum_discounted']}B",
                        f"${r['terminal_value']}B",
                        f"${total:.2f}B",
                        f"${r['total_debt']:.2f}B",
                        f"${r['cash']:.2f}B",
                        f"${r['net_debt']:.2f}B",
                        f"${equity_val:.2f}B",
                        f"{r['shares']:.2f}B",
                        f"${r['intrinsic']:.2f}",
                        f"{r['mos_assumption']:.0f}%",
                        f"${r['with_margin']:.2f}"
                    ]
                })
                st.dataframe(calc_df, hide_index=True, use_container_width=True)

            # --- FCF Base Explanation ---
            st.markdown("**FCF Base Calculation**")
            fcf_yrs  = r.get("fcf_years", [])
            fcf_hist = r.get("fcf_history", [])
            fcf_note = r.get("fcf_note", "")
            if fcf_yrs and fcf_hist:
                yr_labels = [str(y)[:4] for y in fcf_yrs]
                outliers  = set(r.get("fcf_outliers", []))
                used_n    = len([v for v in fcf_hist if v is not None])
                used_yrs  = yr_labels[:used_n]
                used_vals = fcf_hist[:used_n]
                val_parts = []
                for yr, v in zip(used_yrs, used_vals):
                    tag = " ⚠️ outlier" if yr in outliers else ""
                    val_parts.append(f"${v:.2f}B ({yr}{tag})")
                st.write(
                    f"Method: **{fcf_note}**  \n"
                    f"Years: {', '.join(val_parts)} → **Base FCF: ${r['fcf']:.2f}B**"
                )
                for oy in r.get("fcf_outliers", []):
                    st.warning(f"⚠️ FCF outlier in {oy} – median used instead of average")
            if r.get("growth_auto") and r.get("growth_sources"):
                src_str = " + ".join(
                    f"{s['name']} {s['value']:+.1f}% (wt {s['weight']}%)"
                    for s in r["growth_sources"]
                )
                st.write(
                    f"Auto growth rate: **{r['growth_assumption']:.1f}%** "
                    f"(20% haircut applied)  ·  Sources: {src_str}"
                )

            fig3 = px.bar(
                x=["Current Price", "Intrinsic Value", "With MoS"],
                y=[r['price'], r['intrinsic'], r['with_margin']],
                color=["Price", "Intrinsic Value", "With MoS"],
                color_discrete_map={
                    "Price": "#378ADD",
                    "Intrinsic Value": "#1D9E75",
                    "With MoS": "#EF9F27"
                },
                labels={"x": "", "y": "Price ($)"},
                title="Price vs. Intrinsic Value"
            )
            fig3.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig3, use_container_width=True)

            # --- Terminal Value Plausibility Check ---
            st.markdown("**Terminal Value Plausibility**")
            tv_pct = r.get("tv_pct")
            tv_mul = r.get("tv_implied_multiple")
            tv_warn = r.get("tv_warnings", [])

            info_lines = []
            if tv_pct is not None:
                info_lines.append(f"TV as % of Enterprise Value: **{tv_pct:.1f}%**")
            if tv_mul is not None:
                info_lines.append(f"Implied EV/EBITDA multiple: **{tv_mul:.1f}x**")
            if info_lines:
                st.write("  ·  ".join(info_lines))

            if tv_warn:
                for w in tv_warn:
                    st.warning(w)
            else:
                st.success("✅ All terminal value checks passed.")

            # --- Sensitivity Table ---
            st.markdown("**Sensitivity Analysis – Intrinsic Value (Base Scenario)**")
            _wacc_base = r['wacc'] / 100
            _g_base    = r['growth_assumption'] / 100
            _term      = r['terminal_assumption'] / 100
            _fcf       = r['fcf']
            _shares    = r['shares']
            _nd        = r['net_debt']
            wacc_steps   = [_wacc_base - 0.01, _wacc_base, _wacc_base + 0.01]
            growth_steps = [_g_base - 0.01,    _g_base,    _g_base + 0.01]
            sens_rows = []
            for g in growth_steps:
                row = []
                for w in wacc_steps:
                    iv = _dcf_intrinsic(_fcf, _shares, _nd, g, w, _term)
                    row.append(round(iv, 2) if iv is not None else None)
                sens_rows.append(row)
            w_labels = [f"WACC {w*100:.1f}%" for w in wacc_steps]
            g_labels = [f"Growth {g*100:.1f}%" for g in growth_steps]
            sens_df  = pd.DataFrame(sens_rows, index=g_labels, columns=w_labels)

            def _style_sens(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                styles.iloc[1, 1] = 'background-color: #1D9E75; color: white; font-weight: bold'
                return styles

            styled = (
                sens_df.style
                .format(lambda v: f"${v:.2f}" if v is not None else "N/A")
                .apply(_style_sens, axis=None)
                .background_gradient(cmap="RdYlGn", axis=None, gmap=sens_df)
            )
            st.dataframe(styled, use_container_width=True)
            st.caption(
                f"Base scenario (green): WACC {_wacc_base*100:.1f}%, "
                f"Growth {_g_base*100:.1f}%  ·  "
                f"Current price: ${r['price']:.2f}"
            )

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Cost of Equity (CAPM)**")
                rfr_label = (f"{r.get('rfr', 4.0):.2f}% "
                             f"({'live' if r.get('rfr_live') else 'fallback'}, "
                             f"fetched {r.get('rfr_date', 'N/A')})")
                st.write(f"Risk-free rate: {rfr_label}")
                st.write(f"Country / Region: {r.get('country', 'N/A')}")
                st.write(f"Equity Risk Premium (ERP): {r.get('erp', 5.5):.2f}%")
                st.write(f"Raw Beta: {r.get('raw_beta', r['beta']):.2f}")
                adj = r.get('adj_beta', r['beta'])
                raw = r.get('raw_beta', r['beta'])
                st.write(f"Blume-Adjusted Beta: {adj:.2f}  "
                         f"(0.67 × {raw:.2f} + 0.33)")
                st.write(f"**Cost of Equity: {r['cost_equity']:.2f}%**  "
                         f"({r.get('rfr', 4.0):.2f}% + {adj:.2f} × {r.get('erp', 5.5):.2f}%)")
            with col2:
                st.markdown("**Weighting & Result**")
                st.write(f"Equity weight: {r['equity_weight']}%")
                st.write(f"Debt weight: {r['debt_weight']}%")
                st.write(f"After-tax cost of debt: {r['cost_debt']}%")
                st.write(f"**WACC (calculated): {r['wacc_calculated']}%**")
                if r['wacc'] != r['wacc_calculated']:
                    st.write(f"**WACC (manual override): {r['wacc']}%**")
                else:
                    st.write(f"**WACC (used): {r['wacc']}%**")

        with tab5:
            st.markdown("**Historical Analysis – 10 Years**")
            period_map = {
                "1 Year":  "1y",
                "3 Years": "3y",
                "5 Years": "5y",
                "10 Years":"10y",
                "Max":     "max"
            }
            selected_period = st.radio(
                "Time period",
                list(period_map.keys()),
                index=3,
                horizontal=True,
                key="hist_period"
            )
            period = period_map[selected_period]

            with st.spinner("Loading historical data..."):
                try:
                    ticker     = yf.Ticker(r["symbol"])
                    hist       = ticker.history(period=period)
                    info_hist  = ticker.info
                    cashflow_h = ticker.cashflow

                    if hist.empty:
                        st.warning("No historical data available.")
                    else:
                        hist.index = pd.to_datetime(hist.index)

                        # Chart 1: Price History
                        st.subheader("📉 Price History")
                        fig_h1 = px.line(
                            hist, x=hist.index, y="Close",
                            title=f"{r['name']} – Price History",
                            labels={"Close": "Price ($)", "index": "Date"},
                            color_discrete_sequence=["#378ADD"]
                        )
                        fig_h1.add_hline(
                            y=r["intrinsic"],
                            line_dash="dash",
                            line_color="#1D9E75",
                            annotation_text=f"Intrinsic Value ${r['intrinsic']:.2f}",
                            annotation_position="top left"
                        )
                        fig_h1.add_hline(
                            y=r["with_margin"],
                            line_dash="dot",
                            line_color="#EF9F27",
                            annotation_text=f"With MoS ${r['with_margin']:.2f}",
                            annotation_position="bottom left"
                        )
                        fig_h1.update_layout(height=400)
                        st.plotly_chart(fig_h1, use_container_width=True)
                        st.caption("Green dashed = intrinsic value · Orange dotted = max buy price with margin of safety")

                        st.divider()

                        # Chart 2: P/E History
                        st.subheader("📊 P/E Ratio History")
                        try:
                            eps_trail  = info_hist.get("trailingEps")
                            current_pe = r.get("pe") or 0
                            if eps_trail and eps_trail > 0:
                                hist["PE"] = hist["Close"] / eps_trail
                                fig_h2 = px.line(
                                    hist, x=hist.index, y="PE",
                                    title=f"{r['name']} – Estimated P/E Ratio",
                                    labels={"PE": "P/E Ratio", "index": "Date"},
                                    color_discrete_sequence=["#7F77DD"]
                                )
                                avg_pe = hist["PE"].mean()
                                fig_h2.add_hline(
                                    y=avg_pe,
                                    line_dash="dash",
                                    line_color="gray",
                                    annotation_text=f"Avg P/E: {avg_pe:.1f}",
                                    annotation_position="top left"
                                )
                                if current_pe > 0:
                                    fig_h2.add_hline(
                                        y=current_pe,
                                        line_dash="dot",
                                        line_color="#E24B4A",
                                        annotation_text=f"Current P/E: {current_pe:.1f}",
                                        annotation_position="bottom right"
                                    )
                                fig_h2.update_layout(height=350)
                                st.plotly_chart(fig_h2, use_container_width=True)
                                col1, col2, col3 = st.columns(3)
                                col1.metric("Current P/E", f"{current_pe:.1f}" if current_pe else "N/A")
                                col2.metric("Avg P/E",     f"{avg_pe:.1f}")
                                col3.metric(
                                    "vs. Average",
                                    f"{((current_pe/avg_pe)-1)*100:+.1f}%" if current_pe and avg_pe else "N/A",
                                    delta_color="inverse"
                                )
                                if current_pe and avg_pe:
                                    if current_pe < avg_pe * 0.8:
                                        st.success("✅ P/E significantly below average – historically cheap")
                                    elif current_pe < avg_pe:
                                        st.info("🟡 P/E below average – moderately attractive")
                                    elif current_pe < avg_pe * 1.2:
                                        st.warning("🟠 P/E above average – slightly expensive")
                                    else:
                                        st.error("🔴 P/E significantly above average – historically expensive")
                            else:
                                st.info("P/E history not available – EPS data missing.")
                        except Exception as pe_err:
                            st.info(f"P/E history not available: {pe_err}")

                        st.divider()

                        # Chart 3: FCF Development
                        st.subheader("💰 FCF Development")
                        try:
                            if "Free Cash Flow" in cashflow_h.index:
                                fcf_series = cashflow_h.loc["Free Cash Flow"]
                                fcf_hist_df = pd.DataFrame({
                                    "Year":     [str(d)[:4] for d in fcf_series.index],
                                    "FCF ($B)": [round(v/1e9, 2) for v in fcf_series.values]
                                }).sort_values("Year")
                                colors = ["#1D9E75" if v >= 0 else "#E24B4A"
                                          for v in fcf_hist_df["FCF ($B)"]]
                                fig_h3 = go.Figure(go.Bar(
                                    x=fcf_hist_df["Year"],
                                    y=fcf_hist_df["FCF ($B)"],
                                    marker_color=colors,
                                    text=[f"${v:.2f}B" for v in fcf_hist_df["FCF ($B)"]],
                                    textposition="auto"
                                ))
                                fig_h3.update_layout(
                                    title=f"{r['name']} – Free Cash Flow History",
                                    yaxis_title="FCF ($B)",
                                    height=350,
                                    showlegend=False
                                )
                                fig_h3.add_hline(y=0, line_color="gray", line_width=0.5)
                                st.plotly_chart(fig_h3, use_container_width=True)
                                pos_fcfs = [v for v in fcf_hist_df["FCF ($B)"] if v > 0]
                                if len(pos_fcfs) >= 2:
                                    fcf_trend = ((pos_fcfs[-1]/pos_fcfs[0]) ** (1/(len(pos_fcfs)-1)) - 1) * 100
                                    col1, col2, col3 = st.columns(3)
                                    col1.metric("Latest FCF",     f"${fcf_hist_df['FCF ($B)'].iloc[-1]:.2f}B")
                                    col2.metric("FCF CAGR",       f"{fcf_trend:+.1f}%")
                                    col3.metric("Positive Years", f"{len(pos_fcfs)}/{len(fcf_hist_df)}")
                            else:
                                st.info("FCF history not available.")
                        except Exception as fcf_err:
                            st.info(f"FCF history not available: {fcf_err}")

                        st.divider()

                        # Chart 4: Intrinsic Value vs Price
                        st.subheader("🎯 Intrinsic Value vs. Price")
                        try:
                            hist_annual         = hist["Close"].resample("YE").last().reset_index()
                            hist_annual.columns = ["Date", "Price"]
                            current_iv          = r["intrinsic"]
                            growth_rate         = r["growth_assumption"] / 100
                            years_back          = len(hist_annual)
                            iv_estimates        = []
                            for i in range(years_back, 0, -1):
                                iv_estimates.append(current_iv / ((1 + growth_rate) ** i))
                            hist_annual["Intrinsic Value"] = iv_estimates[:len(hist_annual)]
                            fig_h4 = go.Figure()
                            fig_h4.add_trace(go.Scatter(
                                x=hist_annual["Date"],
                                y=hist_annual["Price"],
                                name="Market Price",
                                line=dict(color="#378ADD", width=2)
                            ))
                            fig_h4.add_trace(go.Scatter(
                                x=hist_annual["Date"],
                                y=hist_annual["Intrinsic Value"],
                                name="Est. Intrinsic Value",
                                line=dict(color="#1D9E75", width=2, dash="dash")
                            ))
                            fig_h4.add_trace(go.Scatter(
                                x=hist_annual["Date"],
                                y=[v * (1 - r["mos_assumption"]/100)
                                   for v in hist_annual["Intrinsic Value"]],
                                name="With Margin of Safety",
                                line=dict(color="#EF9F27", width=1.5, dash="dot")
                            ))
                            fig_h4.update_layout(
                                title=f"{r['name']} – Price vs. Estimated Intrinsic Value",
                                yaxis_title="Price ($)",
                                height=400,
                                legend=dict(orientation="h", y=-0.2)
                            )
                            st.plotly_chart(fig_h4, use_container_width=True)
                            st.caption("⚠️ Intrinsic value estimated backwards from current calculation. Use as orientation only.")
                        except Exception as iv_err:
                            st.info(f"Intrinsic value chart not available: {iv_err}")

                except Exception as ex:
                    st.error(f"Error loading historical data: {ex}")

        st.divider()
        if st.button("💾 Save to Database", type="primary", key="save_btn"):
            with st.spinner("Saving..."):
                ok = save_to_database(r)
            if ok:
                st.success(f"✅ {r['name']} saved! ({len(st.session_state.database)} entries)")
            else:
                st.error("Save failed. Check the GitHub Token in Secrets.")

# ================================================================
# PAGE 2: DATABASE
# ================================================================
elif page == "📊 Database":
    st.title("Database")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh", key="db_refresh"):
            st.session_state.database, st.session_state.db_sha = load_database()
            st.rerun()

    if not st.session_state.database:
        st.info("No entries yet. Analyze stocks or run a batch analysis.")
    else:
        df = pd.DataFrame(st.session_state.database)

        col1, col2, col3 = st.columns(3)
        with col1:
            sectors       = ["All"] + sorted(df["Sector"].dropna().unique().tolist())
            sector_filter = st.selectbox("Sector", sectors)
        with col2:
            dev_range = st.slider("Deviation % filter", -300, 500, (-300, 500))
        with col3:
            sort_by = st.selectbox("Sort by",
                ["Value Score","Deviation %","P/E","FCF CAGR %","ROE %","Name"])

        filtered = df.copy()
        if sector_filter != "All":
            filtered = filtered[filtered["Sector"] == sector_filter]
        filtered = filtered[
            (filtered["Deviation %"] >= dev_range[0]) &
            (filtered["Deviation %"] <= dev_range[1])
        ]
        ascending = sort_by not in ["Value Score"]
        filtered  = filtered.sort_values(sort_by, ascending=ascending, na_position="last")

        st.caption(f"{len(filtered)} of {len(df)} entries")
        st.dataframe(
            filtered.style
            .background_gradient(subset=["Deviation %"], cmap="RdYlGn_r")
            .format({"Deviation %": "{:+.1f}%", "Price": "${:.2f}",
                     "Intrinsic Value": "${:.2f}", "With MoS": "${:.2f}",
                     "Dividend %": "{:.2f}%", "P/E": "{:.2f}",
                     "Forward P/E": "{:.2f}", "P/B": "{:.2f}",
                     "EV/EBITDA": "{:.2f}", "FCF CAGR %": "{:.2f}",
                     "ROE %": "{:.2f}", "Net Margin %": "{:.2f}",
                     "FCF Growth %": "{:.2f}", "Terminal %": "{:.2f}",
                     "MoS %": "{:.0f}", "WACC %": "{:.2f}"}, na_rep="N/A"),
            use_container_width=True,
            hide_index=True
        )

        if len(filtered) > 1:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.scatter(
                    filtered.dropna(subset=["P/E","Deviation %"]),
                    x="P/E", y="Deviation %",
                    hover_name="Name", color="Sector",
                    title="P/E vs. Deviation from Intrinsic Value"
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top10 = filtered.nsmallest(10, "Deviation %")
                fig2  = px.bar(top10, x="Symbol", y="Deviation %",
                               title="Top 10 Most Undervalued",
                               color="Deviation %",
                               color_continuous_scale="RdYlGn_r")
                fig2.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig2, use_container_width=True)

        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export CSV", csv, "database.csv", "text/csv")

# ================================================================
# PAGE 3: PORTFOLIO
# ================================================================
elif page == "💼 Portfolio":
    st.title("Portfolio")

    with st.expander("➕ Add Position", expanded=not bool(st.session_state.portfolio)):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_query  = st.text_input("Search", placeholder="Apple, AAPL...")
            p_search = st.button("Search", key="p_search_btn")
        with col2:
            p_cost   = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
        with col3:
            p_shares = st.number_input("Number of Shares", min_value=0.0, step=1.0)

        if p_search and p_query:
            names, symbols = search_stock(p_query)
            st.session_state.p_names   = names
            st.session_state.p_symbols = symbols

        p_symbol = ""
        if st.session_state.p_symbols:
            choice   = st.selectbox("Results:", st.session_state.p_names, key="p_choice")
            idx      = st.session_state.p_names.index(choice)
            p_symbol = st.session_state.p_symbols[idx]
            st.info(f"Symbol: **{p_symbol}**")

        if st.button("Add Position", type="primary", key="p_add"):
            if p_symbol and p_cost > 0 and p_shares > 0:
                with st.spinner(f"Loading {p_symbol}..."):
                    info  = yf.Ticker(p_symbol).info
                    price = float(info.get("currentPrice") or 0)
                    name  = info.get("longName", p_symbol)

                    intrinsic = 0
                    for db_e in st.session_state.database:
                        if db_e.get("Symbol") == p_symbol:
                            intrinsic = float(db_e.get("Intrinsic Value") or 0)
                            break

                    perf = (price - p_cost) / p_cost * 100
                    dev  = (price - intrinsic) / intrinsic * 100 if intrinsic > 0 else None

                    if intrinsic > 0 and dev is not None:
                        if dev > 40:    rec = "🔴 Strong Sell"
                        elif dev > 20:  rec = "🟠 Sell"
                        elif dev > 0:   rec = "🟡 Hold"
                        elif dev > -20: rec = "🟡 Hold"
                        elif dev > -40: rec = "🟢 Buy More"
                        else:           rec = "🟢 Strong Buy"
                    else:
                        rec = "⚠️ Analyze first"

                    position = {
                        "Symbol":          p_symbol,
                        "Name":            name,
                        "Shares":          p_shares,
                        "Purchase Price":  p_cost,
                        "Current Price":   round(price, 2),
                        "Invested ($)":    round(p_cost * p_shares, 2),
                        "Current Value":   round(price * p_shares, 2),
                        "Performance %":   round(perf, 1),
                        "Intrinsic Value": round(intrinsic, 2),
                        "Deviation %":     round(dev, 1) if dev else None,
                        "Recommendation":  rec,
                    }

                    symbols_p = [p["Symbol"] for p in st.session_state.portfolio]
                    if p_symbol in symbols_p:
                        st.session_state.portfolio[symbols_p.index(p_symbol)] = position
                    else:
                        st.session_state.portfolio.append(position)

                    with st.spinner("Saving portfolio..."):
                        save_portfolio(
                            st.session_state.portfolio,
                            st.session_state.port_sha
                        )
                    st.success(f"✅ {name} added!")
            else:
                st.warning("Please select a stock, enter purchase price and number of shares.")

    if st.session_state.portfolio:
        df_p         = pd.DataFrame(st.session_state.portfolio)
        total_invest = df_p["Invested ($)"].sum()
        total_value  = df_p["Current Value"].sum()
        total_perf   = (total_value - total_invest) / total_invest * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Positions",     len(df_p))
        col2.metric("Invested",      f"${total_invest:,.2f}")
        col3.metric("Current Value", f"${total_value:,.2f}")
        col4.metric("Performance",   f"{total_perf:+.1f}%")

        st.divider()
        st.dataframe(df_p, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_p, values="Current Value", names="Symbol",
                         title="Portfolio Allocation")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df_p, x="Symbol", y="Performance %",
                         color="Performance %",
                         color_continuous_scale="RdYlGn",
                         title="Performance by Position")
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)

        csv = df_p.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Portfolio", csv, "portfolio.csv", "text/csv")
    else:
        st.info("No positions yet. Add your first position above.")

# ================================================================
# PAGE 4: BATCH ANALYSIS
# ================================================================
elif page == "🔄 Batch Analysis":
    st.title("Batch Analysis")
    st.write("Automatically analyze many stocks and save them to the database.")

    b_auto_growth = st.checkbox("Use automatic per-stock growth rate (recommended)", value=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        b_growth_override = st.slider("Override Growth Rate %", 0, 15, 6) / 100
        if b_auto_growth:
            st.caption("Automatic rate active – slider ignored")
    with col2:
        b_terminal = st.slider("Terminal Growth % (max)", 1, 5, 2) / 100
        st.caption("Sector-aware caps applied per stock (e.g. tobacco ≤ 1.5%, energy ≤ 2.0%)")
    with col3:
        b_mos      = st.slider("Margin of Safety %", 0, 40, 25) / 100

    index_choice = st.selectbox("Select index / group", list(INDEX_GROUPS.keys()))
    selection_preview = INDEX_GROUPS[index_choice]
    n = len(selection_preview)
    st.caption(f"{n} stocks · approx. {n//10}–{n//6} minutes")

    if st.button("Start Batch Analysis", type="primary", key="batch_btn"):
        selection = selection_preview
        progress  = st.progress(0)
        status    = st.empty()
        errors    = []
        successes = 0

        for i, symbol in enumerate(selection):
            status.text(f"[{i+1}/{len(selection)}] Analyzing {symbol}...")
            result, error = None, None
            for attempt, wait_s in enumerate([0, 30, 60]):
                if wait_s > 0:
                    status.text(f"[{i+1}/{len(selection)}] Rate limited – waiting {wait_s}s before retry ({symbol})...")
                    time.sleep(wait_s)
                    status.text(f"[{i+1}/{len(selection)}] Retrying {symbol} (attempt {attempt+1})...")
                try:
                    growth_arg = None if b_auto_growth else b_growth_override
                    result, error = run_dcf(symbol, growth_arg, b_terminal, b_mos)
                    rate_limited = error and any(k in str(error).lower() for k in ["429", "too many requests", "rate"])
                    if rate_limited:
                        result = None
                        if attempt < 2:
                            continue
                        else:
                            errors.append(f"{symbol}: rate limited after 3 attempts")
                            break
                    break
                except Exception as ex:
                    error_str = str(ex)
                    rate_limited = any(k in error_str.lower() for k in ["429", "too many requests", "rate"])
                    if rate_limited and attempt < 2:
                        error = error_str
                        result = None
                        continue
                    errors.append(f"{symbol}: {error_str}")
                    result = None
                    break
            if result:
                entry   = result_to_db_entry(result)
                symbols = [e["Symbol"] for e in st.session_state.database]
                if symbol in symbols:
                    st.session_state.database[symbols.index(symbol)] = entry
                else:
                    st.session_state.database.append(entry)
                successes += 1
            elif error and not any(symbol in e for e in errors):
                errors.append(f"{symbol}: {error}")
            progress.progress((i + 1) / len(selection))
            time.sleep(2.0)

        status.text("Saving to database...")
        with st.spinner("Saving to GitHub..."):
            ok = save_database(st.session_state.database, st.session_state.db_sha)
            if ok:
                _, st.session_state.db_sha = load_database()

        status.text("Done!")
        if ok:
            st.success(f"✅ {successes} stocks analyzed and saved permanently!")
        else:
            st.warning(f"✅ {successes} stocks analyzed but save failed.")
        if errors:
            with st.expander("Skipped stocks"):
                for e in errors:
                    st.write(e)
        st.info("Go to the Dashboard to see your results.")

# ================================================================
# PAGE 5: METHODOLOGY
# ================================================================
elif page == "📖 Methodology":
    st.title("Methodology & Sources")
    st.markdown("""
    ## What this tool calculates – and what it does not

    This tool is a quantitative screening instrument. It helps identify
    potentially undervalued stocks systematically. It does not replace
    in-depth qualitative analysis and does not constitute investment advice.

    ---

    ## DCF Method (Discounted Cash Flow)

    ### How it works
    The intrinsic value of a stock is the sum of all future free cash flows,
    discounted to today. The formula is:

    **Intrinsic Value = Σ (FCF_t / (1+WACC)^t) + Terminal Value – Net Debt**

    ### Strengths
    - Based on real cash flows, not accounting earnings
    - Accounts for the time value of money
    - Industry and academic standard (Damodaran, McKinsey)
    - Forces explicit assumptions about growth

    ### Weaknesses & Limitations
    - Very sensitive to growth assumptions – small changes, big impact
    - Not suitable for banks, insurance companies, REITs
    - Past data does not guarantee future results
    - Creates false sense of precision

    ---

    ## WACC Calculation

    The WACC (Weighted Average Cost of Capital) is the discount rate.
    We calculate it using the CAPM model:

    **Cost of Equity = Risk-Free Rate + Beta × Market Risk Premium**
    - Risk-free rate: 4.0% (10-year US Treasury)
    - Market risk premium: 5.5% (historical S&P 500 average)
    - Beta: from Yahoo Finance (yfinance)

    ---

    ## Value Score

    The Value Score is a proprietary score from 5 categories:

    | Category | Max Points | Key Criteria |
    |----------|------------|--------------|
    | DCF Deviation | 25 | Price vs. intrinsic value |
    | FCF Quality | 20 | FCF yield, FCF CAGR |
    | Valuation | 25 | P/E, P/B, EV/EBITDA |
    | Profitability | 15 | ROE, Net Margin |
    | Stability | 15 | Leverage, Dividend |

    The score is **sector-specific** – banks and utilities are evaluated
    by different criteria than industrial companies.

    ---

    ## Which stocks work well with this tool?

    ✅ **Well suited:**
    - Stable companies with positive, growing FCF
    - Consumer staples, industrials, healthcare, technology (profitable)
    - Companies with at least 3 years of FCF history

    ⚠️ **Limited suitability:**
    - Cyclical companies (energy, materials) – FCF fluctuates strongly
    - Growth companies – manually increase growth rate to 12–20%

    ❌ **Not suitable:**
    - Banks and insurance companies – different business model, no operational FCF
    - REITs – use Price/FFO instead of DCF
    - Loss-making companies without positive FCF
    - Early-stage growth companies (pre-revenue)

    ---

    ## Sources & Further Reading

    **Books:**
    - Damodaran, A. (2012): *Investment Valuation* – standard reference for DCF
    - Graham, B. (1949): *The Intelligent Investor* – foundation of value investing
    - Koller, T. et al. (2020): *Valuation* (McKinsey) – professional DCF practice

    **Online Resources:**
    - [Damodaran Online](http://pages.stern.nyu.edu/~adamodar/) – data & methodology
    - [Gurufocus](https://www.gurufocus.com) – DCF comparison values
    - [Macrotrends](https://www.macrotrends.net) – historical FCF data

    **Academic Foundations:**
    - Sharpe (1964): Capital Asset Pricing Model (CAPM) – basis of WACC
    - Modigliani & Miller (1958): Capital structure and firm value

    ---

    *This tool is for informational purposes only and does not constitute
    investment advice. All investment decisions are the sole responsibility
    of the user.*
    """)
