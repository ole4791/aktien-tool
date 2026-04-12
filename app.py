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

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def normalize_dividend(div):
    """Convert dividend to percentage format (0-100 range). If > 20, divide by 100."""
    if div is None or div == 0:
        return div
    if div > 20:  # Safety check: if already multiplied twice
        div = div / 100
    return div


def calculate_fcf_base(cashflow):
    if "Free Cash Flow" not in cashflow.index:
        return None, "not available", [], []
    fcf_series = cashflow.loc["Free Cash Flow"]
    fcf_years  = list(fcf_series.index[:5])
    fcf_values = [round(float(v)/1e9, 2) for v in fcf_series.values[:5]]
    positive   = [v for v in fcf_series.values[:5] if v > 0]
    if not positive:
        return float(fcf_series.values[0]), "⚠️ all negative", fcf_values, fcf_years
    elif len(positive) < 3:
        fcf = sum(positive) / len(positive)
        return fcf, f"⚠️ avg of {len(positive)} positive years", fcf_values, fcf_years
    else:
        fcf = sum(fcf_series.values[:3]) / 3
        return float(fcf), "✅ 3-year average", fcf_values, fcf_years


def calculate_wacc(info):
    beta       = float(info.get("beta") or 1.0)
    debt       = float(info.get("totalDebt") or 0)
    mktcap     = float(info.get("marketCap") or 0)
    interest   = float(info.get("interestExpense") or 0)
    tax        = float(info.get("effectiveTaxRate") or 0.21)
    cost_eq    = 0.04 + beta * 0.055
    cost_debt  = abs(interest) / debt if debt > 0 and interest else 0.04
    cost_debt_at = cost_debt * (1 - tax)
    total      = mktcap + debt
    eq_weight  = mktcap / total if total > 0 else 1.0
    debt_weight = debt / total if total > 0 else 0.0
    wacc       = eq_weight * cost_eq + debt_weight * cost_debt_at
    return wacc, beta, cost_eq, cost_debt_at, eq_weight, debt_weight


def calculate_value_score_detail(e):
    details  = {}
    sector   = e.get("sector") or ""
    fcf      = e.get("fcf") or 0
    no_dcf   = any(s in sector for s in ["Financial","Utilities","Real Estate"])

    dcf_pts = 0
    if not no_dcf and fcf > 0:
        dev = e.get("deviation") or 0
        if dev < -40:   dcf_pts = 25
        elif dev < -20: dcf_pts = 18
        elif dev < 0:   dcf_pts = 10
        elif dev < 20:  dcf_pts = 4
    details["DCF Deviation"] = {"points": dcf_pts, "max": 25}

    fcf_pts   = 0
    mktcap    = e.get("market_cap") or 0
    fcf_yield = (fcf / mktcap * 100) if mktcap > 0 and fcf > 0 else 0
    fcf_cagr  = e.get("fcf_cagr") or 0
    if not no_dcf:
        if fcf > 0:          fcf_pts += 5
        if fcf_yield > 8:    fcf_pts += 8
        elif fcf_yield > 5:  fcf_pts += 5
        elif fcf_yield > 3:  fcf_pts += 2
        if fcf_cagr > 10:    fcf_pts += 7
        elif fcf_cagr > 5:   fcf_pts += 4
        elif fcf_cagr > 0:   fcf_pts += 2
    details["FCF Quality"] = {"points": fcf_pts, "max": 20}

    mult_pts = 0
    pe   = e.get("pe") or 0
    pb   = e.get("pb") or 0
    eveb = e.get("ev_ebitda") or 0
    roe  = e.get("roe") or 0
    roe  = roe * 100 if roe and abs(roe) < 2 else roe
    if "Financial" in sector:
        if 0 < pb < 0.8:    mult_pts += 15
        elif 0 < pb < 1.2:  mult_pts += 10
        elif 0 < pb < 1.8:  mult_pts += 5
        if roe > 15:        mult_pts += 10
        elif roe > 10:      mult_pts += 6
        elif roe > 7:       mult_pts += 3
    elif "Utilities" in sector or "Real Estate" in sector:
        div = normalize_dividend(e.get("dividend") or 0)
        div = div * 100 if div and abs(div) < 1 else div
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
        if 0 < pb < 1.5:    mult_pts += 8
        elif 0 < pb < 3:    mult_pts += 4
        elif 0 < pb < 5:    mult_pts += 2
        if 0 < eveb < 8:    mult_pts += 8
        elif 0 < eveb < 12: mult_pts += 4
    details["Valuation"] = {"points": mult_pts, "max": 25}

    prof_pts = 0
    margin   = e.get("net_margin") or 0
    margin   = margin * 100 if margin and abs(margin) < 1 else margin
    if roe > 20:     prof_pts += 8
    elif roe > 12:   prof_pts += 5
    elif roe > 8:    prof_pts += 2
    if margin > 20:  prof_pts += 7
    elif margin > 10: prof_pts += 4
    elif margin > 5: prof_pts += 2
    details["Profitability"] = {"points": prof_pts, "max": 15}

    stab_pts = 0
    net_debt_ratio = (e.get("net_debt") or 0) / mktcap if mktcap > 0 else 0
    div = normalize_dividend(e.get("dividend") or 0)
    div = div * 100 if div and abs(div) < 1 else div
    thresholds = (1.5, 3.0, 5.0) if no_dcf else (0.3, 0.8, 1.5)
    if net_debt_ratio < thresholds[0]:   stab_pts += 8
    elif net_debt_ratio < thresholds[1]: stab_pts += 5
    elif net_debt_ratio < thresholds[2]: stab_pts += 2
    if div > 0: stab_pts += 4
    if div > 3: stab_pts += 3
    details["Stability"] = {"points": stab_pts, "max": 15}

    total = sum(d["points"] for d in details.values())
    return min(round(total), 100), details


def run_dcf(symbol, growth, terminal, margin_of_safety, wacc_override=None):
    try:
        ticker     = yf.Ticker(symbol)
        info       = ticker.info
        cashflow   = ticker.cashflow
        financials = ticker.financials
    except Exception as ex:
        return None, str(ex)

    if not info or not info.get("longName"):
        return None, "Stock not found"

    fcf, fcf_note, fcf_history, fcf_years = calculate_fcf_base(cashflow)
    if fcf is None:
        return None, "Free Cash Flow not available"

    shares = info.get("sharesOutstanding")
    if not shares:
        return None, "Shares outstanding not available"

    debt     = float(info.get("totalDebt") or 0)
    cash     = float(info.get("totalCash") or 0)
    net_debt = debt - cash
    mktcap   = float(info.get("marketCap") or 0)

    wacc_calc, beta, cost_eq, cost_debt, eq_w, debt_w = calculate_wacc(info)
    wacc = wacc_override if wacc_override else wacc_calc

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
    intrinsic  = equity / shares
    with_margin = intrinsic * (1 - margin_of_safety)
    price      = float(info.get("currentPrice") or 0)
    deviation  = (price - intrinsic) / intrinsic * 100 if intrinsic != 0 else 0

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
        "cost_equity":        round(cost_eq * 100, 2),
        "cost_debt":          round(cost_debt * 100, 2),
        "equity_weight":      round(eq_w * 100, 1),
        "debt_weight":        round(debt_w * 100, 1),
        "fcf_note":           fcf_note,
        "fcf":                round(fcf / 1e9, 2),
        "fcf_history":        fcf_history,
        "fcf_years":          [str(y)[:10] for y in fcf_years],
        "fcf_cagr":           round(fcf_cagr, 1) if fcf_cagr else None,
        "projected_fcfs":     projected,
        "terminal_value":     round(tv_disc / 1e9, 2),
        "sum_discounted":     round(sum(discounted) / 1e9, 2),
        "net_debt":           round(net_debt / 1e9, 2),
        "market_cap":         round(mktcap / 1e9, 2),
        "shares":             round(shares / 1e9, 3),
        "total_debt":         round(debt / 1e9, 2),
        "cash":               round(cash / 1e9, 2),
        "pe":                 info.get("trailingPE"),
        "forward_pe":         info.get("forwardPE"),
        "pb":                 info.get("priceToBook"),
        "ev_ebitda":          info.get("enterpriseToEbitda"),
        "ps":                 info.get("priceToSalesTrailing12Months"),
        "roe":                info.get("returnOnEquity"),
        "net_margin":         info.get("profitMargins"),
        "dividend":           normalize_dividend(info.get("dividendYield")),
        "revenue_growth":     round(rev_growth, 1) if rev_growth else None,
        "growth_assumption":  round(growth * 100, 1),
        "terminal_assumption": round(terminal * 100, 1),
        "mos_assumption":     round(margin_of_safety * 100, 0),
        "last_updated":       datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        "P/E":              r.get("pe"),
        "Forward P/E":      r.get("forward_pe"),
        "P/B":              r.get("pb"),
        "EV/EBITDA":        r.get("ev_ebitda"),
        "FCF (Bn)":         r["fcf"],
        "FCF CAGR %":       r.get("fcf_cagr"),
        "ROE %":            round(r["roe"]*100,1) if r.get("roe") else None,
        "Net Margin %":     round(r["net_margin"]*100,1) if r.get("net_margin") else None,
        "Dividend %":       round(normalize_dividend(r["dividend"])*100,2) if r.get("dividend") is not None else None,
        "Revenue Growth %": r.get("revenue_growth"),
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
            p   = vals["points"]
            m   = vals["max"]
            ico = score_color(p, m)
            cols[i].metric(
                label=f"{ico} {name}",
                value=f"{p}/{m}",
                delta=f"{round(p/m*100):.0f}%" if m > 0 else "N/A"
            )
        fig = go.Figure(go.Bar(
            x=list(details.keys()),
            y=[d["points"] for d in details.values()],
            marker_color=[
                "#1D9E75" if d["points"]/d["max"] >= 0.75
                else "#EF9F27" if d["points"]/d["max"] >= 0.5
                else "#E8593C" if d["points"]/d["max"] >= 0.25
                else "#A32D2D"
                for d in details.values()
            ],
            text=[f"{d['points']}/{d['max']}" for d in details.values()],
            textposition="auto"
        ))
        fig.update_layout(
            title="Value Score Breakdown",
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
    ["🏠 Dashboard", "🔍 Analysis", "📊 Database",
     "💼 Portfolio", "🔄 Batch Analysis", "📖 Methodology"]
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
        top_score = df["Value Score"].max() if "Value Score" in df.columns else 0
        col3.metric("Highest Value Score", f"{top_score}/100")
        avg_score = round(df["Value Score"].mean(), 1) if "Value Score" in df.columns else 0
        col4.metric("Avg Value Score", f"{avg_score}/100")

        st.divider()
        st.subheader("🏆 Top 10 Buy Opportunities")
        st.caption("Ranked by Value Score – highest score = strongest buy signals")

        top10 = df.nlargest(10, "Value Score")[
            ["Symbol","Name","Sector","Price","Intrinsic Value",
             "Deviation %","Value Score","P/E","FCF CAGR %","Dividend %"]
        ]
        st.dataframe(
            top10.style
            .background_gradient(subset=["Value Score"], cmap="RdYlGn")
            .background_gradient(subset=["Deviation %"], cmap="RdYlGn_r")
            .format({"Deviation %": "{:+.1f}%", "Price": "${:.2f}",
                     "Intrinsic Value": "${:.2f}"}, na_rep="N/A"),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            sector_df = df.groupby("Sector")["Value Score"].mean().reset_index()
            sector_df = sector_df.sort_values("Value Score", ascending=False)
            fig = px.bar(sector_df, x="Sector", y="Value Score",
                         title="Avg Value Score by Sector",
                         color="Value Score",
                         color_continuous_scale="RdYlGn")
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
    col1, col2, col3 = st.columns(3)
    with col1:
        growth = st.slider("FCF Growth %", -20, 30, 8) / 100
    with col2:
        terminal = st.slider("Terminal Growth %", 0, 6, 3) / 100
    with col3:
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

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price",   f"${r['price']:.2f}")
        col2.metric("Intrinsic Value", f"${r['intrinsic']:.2f}")
        col3.metric("With MoS",        f"${r['with_margin']:.2f}")
        dev = r["deviation"]
        col4.metric("Valuation", f"{dev:+.1f}%",
                    delta="Overvalued" if dev > 0 else "Undervalued",
                    delta_color="inverse")

        st.divider()
        show_value_score(r)
        st.divider()

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
                st.write(f"Dividend Yield: {normalize_dividend(r['dividend'])*100:.2f}%" if r.get('dividend') is not None else "Dividend: none")
            with col3:
                st.markdown("**Balance Sheet**")
                st.write(f"Market Cap: ${r['market_cap']:.1f}B")
                st.write(f"Total Debt: ${r['total_debt']:.2f}B")
                st.write(f"Cash: ${r['cash']:.2f}B")
                st.write(f"Net Debt: ${r['net_debt']:.2f}B")
                st.write(f"Shares Outstanding: {r['shares']:.3f}B")

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Historical FCF**")
                st.write(f"FCF Base (used): ${r['fcf']}B")
                st.write(f"Quality: {r['fcf_note']}")
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
                        "– Net Debt",
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
                        f"${r['net_debt']}B",
                        f"${equity_val:.2f}B",
                        f"{r['shares']}B",
                        f"${r['intrinsic']:.2f}",
                        f"{r['mos_assumption']:.0f}%",
                        f"${r['with_margin']:.2f}"
                    ]
                })
                st.dataframe(calc_df, hide_index=True, use_container_width=True)

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

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Cost of Equity (CAPM)**")
                st.write("Risk-free rate: 4.0%")
                st.write(f"Beta: {r['beta']}")
                st.write("Market risk premium: 5.5%")
                st.write(f"Cost of equity: {r['cost_equity']}%")
            with col2:
                st.markdown("**Weighting & Result**")
                st.write(f"Equity weight: {r['equity_weight']}%")
                st.write(f"Debt weight: {r['debt_weight']}%")
                st.write(f"After-tax cost of debt: {r['cost_debt']}%")
                st.write(f"**WACC (calculated): {r['wacc_calculated']}%**")
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
            .background_gradient(subset=["Value Score"], cmap="RdYlGn")
            .background_gradient(subset=["Deviation %"], cmap="RdYlGn_r")
            .format({"Deviation %": "{:+.1f}%", "Price": "${:.2f}",
                     "Intrinsic Value": "${:.2f}"}, na_rep="N/A"),
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
                top10 = filtered.nlargest(10, "Value Score")
                fig2  = px.bar(top10, x="Symbol", y="Value Score",
                               title="Top 10 by Value Score",
                               color="Value Score",
                               color_continuous_scale="RdYlGn")
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

    col1, col2, col3 = st.columns(3)
    with col1:
        b_growth   = st.slider("FCF Growth %", 0, 15, 6) / 100
    with col2:
        b_terminal = st.slider("Terminal Growth %", 1, 5, 3) / 100
    with col3:
        b_mos      = st.slider("Margin of Safety %", 0, 40, 25) / 100

    count = st.slider("How many stocks?", 10, len(VALUE_UNIVERSE), 50)
    st.caption(f"{count} stocks · approx. {count//10}–{count//6} minutes")

    if st.button("Start Batch Analysis", type="primary", key="batch_btn"):
        selection = VALUE_UNIVERSE[:count]
        progress  = st.progress(0)
        status    = st.empty()
        errors    = []
        successes = 0

        for i, symbol in enumerate(selection):
            status.text(f"[{i+1}/{len(selection)}] Analyzing {symbol}...")
            try:
                result, error = run_dcf(symbol, b_growth, b_terminal, b_mos)
                if result:
                    entry   = result_to_db_entry(result)
                    symbols = [e["Symbol"] for e in st.session_state.database]
                    if symbol in symbols:
                        st.session_state.database[symbols.index(symbol)] = entry
                    else:
                        st.session_state.database.append(entry)
                    successes += 1
                else:
                    errors.append(f"{symbol}: {error}")
            except Exception as ex:
                errors.append(f"{symbol}: {str(ex)}")
            progress.progress((i + 1) / len(selection))
            time.sleep(0.3)

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
