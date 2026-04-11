import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import time

st.set_page_config(
    page_title="Aktien-Analyse Tool",
    page_icon="📈",
    layout="wide"
)

# ================================================================
# SESSION STATE – immer zuerst initialisieren
# ================================================================
for key in ["datenbank", "portfolio"]:
    if key not in st.session_state:
        st.session_state[key] = []
for key in ["letztes_ergebnis", "such_namen", "such_symbole", "p_namen", "p_symbole"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "letztes_ergebnis" else []

# Altes Format zurücksetzen
if st.session_state.letztes_ergebnis is not None:
    if not isinstance(st.session_state.letztes_ergebnis, dict) or \
       "name" not in st.session_state.letztes_ergebnis:
        st.session_state.letztes_ergebnis = None

# ================================================================
# 200 VALUE-TITEL
# ================================================================
VALUE_UNIVERSUM = [
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
# HILFSFUNKTIONEN
# ================================================================
def fcf_basis_berechnen(cashflow):
    if "Free Cash Flow" not in cashflow.index:
        return None, "nicht verfügbar", [], []
    fcf_serie = cashflow.loc["Free Cash Flow"]
    fcf_jahre = list(fcf_serie.index[:5])
    fcf_werte = [round(float(v)/1e9, 2) for v in fcf_serie.values[:5]]
    positive  = [v for v in fcf_serie.values[:5] if v > 0]
    if not positive:
        return float(fcf_serie.values[0]), "⚠️ alle negativ", fcf_werte, fcf_jahre
    elif len(positive) < 3:
        fcf = sum(positive) / len(positive)
        return fcf, f"⚠️ Durchschnitt {len(positive)} pos. Jahre", fcf_werte, fcf_jahre
    else:
        fcf = sum(fcf_serie.values[:3]) / 3
        return float(fcf), "✅ Durchschnitt 3 Jahre", fcf_werte, fcf_jahre


def berechne_wacc(info):
    beta           = float(info.get("beta") or 1.0)
    schulden       = float(info.get("totalDebt") or 0)
    mktcap         = float(info.get("marketCap") or 0)
    zinsen         = float(info.get("interestExpense") or 0)
    steuer         = float(info.get("effectiveTaxRate") or 0.21)
    ek_kosten      = 0.04 + beta * 0.055
    fk_brutto      = abs(zinsen) / schulden if schulden > 0 and zinsen else 0.04
    fk_netto       = fk_brutto * (1 - steuer)
    gesamt         = mktcap + schulden
    ek_anteil      = mktcap / gesamt if gesamt > 0 else 1.0
    fk_anteil      = schulden / gesamt if gesamt > 0 else 0.0
    wacc           = ek_anteil * ek_kosten + fk_anteil * fk_netto
    return wacc, beta, ek_kosten, fk_netto, ek_anteil, fk_anteil


def berechne_value_score(e):
    punkte   = 0
    sektor   = e.get("sektor") or ""
    fcf      = e.get("fcf") or 0
    kein_dcf = any(s in sektor for s in ["Financial", "Utilities", "Real Estate"])

    if not kein_dcf and fcf > 0:
        abw = e.get("abweichung") or 0
        if abw < -40:    punkte += 25
        elif abw < -20:  punkte += 18
        elif abw < 0:    punkte += 10
        elif abw < 20:   punkte += 4

    fcf_cagr    = e.get("fcf_cagr") or 0
    marktcap    = e.get("marktcap") or 0
    fcf_rendite = (fcf / marktcap * 100) if marktcap > 0 and fcf > 0 else 0
    if not kein_dcf:
        if fcf > 0:            punkte += 5
        if fcf_rendite > 8:    punkte += 8
        elif fcf_rendite > 5:  punkte += 5
        elif fcf_rendite > 3:  punkte += 2
        if fcf_cagr > 10:      punkte += 7
        elif fcf_cagr > 5:     punkte += 4
        elif fcf_cagr > 0:     punkte += 2

    kgv  = e.get("kgv") or 0
    kbv  = e.get("kbv") or 0
    eveb = e.get("ev_ebitda") or 0
    roe  = e.get("roe") or 0
    roe  = roe * 100 if roe and abs(roe) < 2 else roe

    if "Financial" in sektor:
        if 0 < kbv < 0.8:    punkte += 15
        elif 0 < kbv < 1.2:  punkte += 10
        elif 0 < kbv < 1.8:  punkte += 5
        if roe > 15:          punkte += 10
        elif roe > 10:        punkte += 6
        elif roe > 7:         punkte += 3
    elif "Utilities" in sektor or "Real Estate" in sektor:
        div = e.get("dividende") or 0
        div = div * 100 if div and abs(div) < 1 else div
        if 0 < kgv < 15:     punkte += 12
        elif 0 < kgv < 20:   punkte += 7
        elif 0 < kgv < 25:   punkte += 3
        if div > 4:           punkte += 13
        elif div > 3:         punkte += 8
        elif div > 2:         punkte += 4
    elif "Energy" in sektor:
        if 0 < eveb < 5:     punkte += 15
        elif 0 < eveb < 8:   punkte += 9
        elif 0 < eveb < 12:  punkte += 4
        if 0 < kgv < 12:     punkte += 10
        elif 0 < kgv < 18:   punkte += 5
    else:
        if 0 < kgv < 12:     punkte += 9
        elif 0 < kgv < 18:   punkte += 5
        elif 0 < kgv < 25:   punkte += 2
        if 0 < kbv < 1.5:    punkte += 8
        elif 0 < kbv < 3:    punkte += 4
        elif 0 < kbv < 5:    punkte += 2
        if 0 < eveb < 8:     punkte += 8
        elif 0 < eveb < 12:  punkte += 4

    marge = e.get("nettomarge") or 0
    marge = marge * 100 if marge and abs(marge) < 1 else marge
    if roe > 20:      punkte += 8
    elif roe > 12:    punkte += 5
    elif roe > 8:     punkte += 2
    if marge > 20:    punkte += 7
    elif marge > 10:  punkte += 4
    elif marge > 5:   punkte += 2

    schulden_ratio = (e.get("nettoverschuldung") or 0) / marktcap if marktcap > 0 else 0
    div = e.get("dividende") or 0
    div = div * 100 if div and abs(div) < 1 else div
    grenze = (1.5, 3.0, 5.0) if kein_dcf else (0.3, 0.8, 1.5)
    if schulden_ratio < grenze[0]:    punkte += 8
    elif schulden_ratio < grenze[1]:  punkte += 5
    elif schulden_ratio < grenze[2]:  punkte += 2
    if div > 0:  punkte += 4
    if div > 3:  punkte += 3

    return min(round(punkte), 100)


def dcf_berechnen(symbol, wachstum, terminal, sicherheit, wacc_override=None):
    try:
        aktie    = yf.Ticker(symbol)
        info     = aktie.info
        cashflow = aktie.cashflow
        finanzen = aktie.financials
    except Exception as e:
        return None, str(e)

    if not info or not info.get("longName"):
        return None, "Aktie nicht gefunden"

    fcf, fcf_hinweis, fcf_historie, fcf_jahre = fcf_basis_berechnen(cashflow)
    if fcf is None:
        return None, "FCF nicht verfügbar"

    aktien = info.get("sharesOutstanding")
    if not aktien:
        return None, "Aktienanzahl nicht verfügbar"

    schulden          = float(info.get("totalDebt") or 0)
    cash              = float(info.get("totalCash") or 0)
    nettoverschuldung = schulden - cash
    mktcap            = float(info.get("marketCap") or 0)

    wacc_val, beta, ek_k, fk_k, ek_a, fk_a = berechne_wacc(info)
    wacc = wacc_override if wacc_override else wacc_val

    if wacc <= terminal:
        return None, "WACC muss größer sein als terminale Wachstumsrate"

    disk_fcfs     = []
    proj_fcfs     = []
    akt_fcf       = fcf
    for jahr in range(1, 11):
        akt_fcf *= (1 + wachstum)
        proj_fcfs.append(round(akt_fcf / 1e9, 2))
        disk_fcfs.append(akt_fcf / (1 + wacc) ** jahr)

    tv              = akt_fcf * (1 + terminal) / (wacc - terminal)
    tv_disk         = tv / (1 + wacc) ** 10
    uw              = sum(disk_fcfs) + tv_disk
    innerer_wert    = (uw - nettoverschuldung) / aktien
    mit_marge       = innerer_wert * (1 - sicherheit)
    kurs            = float(info.get("currentPrice") or 0)
    abweichung      = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert != 0 else 0

    fcf_cagr = None
    if len(fcf_historie) >= 2 and fcf_historie[-1] > 0 and fcf_historie[0] > 0:
        fcf_cagr = ((fcf_historie[0] / fcf_historie[-1]) ** (1/(len(fcf_historie)-1)) - 1) * 100

    umsatz_wachstum = None
    try:
        if "Total Revenue" in finanzen.index:
            umsatz = finanzen.loc["Total Revenue"].values
            if len(umsatz) >= 2 and umsatz[-1] > 0:
                umsatz_wachstum = ((umsatz[0] / umsatz[-1]) ** (1/(len(umsatz)-1)) - 1) * 100
    except:
        pass

    ergebnis = {
        "name":               info.get("longName", symbol),
        "symbol":             symbol,
        "sektor":             info.get("sector", "N/A"),
        "kurs":               round(kurs, 2),
        "innerer_wert":       round(innerer_wert, 2),
        "mit_marge":          round(mit_marge, 2),
        "abweichung":         round(abweichung, 1),
        "wacc":               round(wacc * 100, 2),
        "wacc_berechnet":     round(wacc_val * 100, 2),
        "beta":               round(beta, 2),
        "ek_kosten":          round(ek_k * 100, 2),
        "fk_kosten":          round(fk_k * 100, 2),
        "ek_anteil":          round(ek_a * 100, 1),
        "fk_anteil":          round(fk_a * 100, 1),
        "fcf_hinweis":        fcf_hinweis,
        "fcf":                round(fcf / 1e9, 2),
        "fcf_historie":       fcf_historie,
        "fcf_jahre":          fcf_jahre,
        "fcf_cagr":           round(fcf_cagr, 1) if fcf_cagr else None,
        "projizierte_fcfs":   proj_fcfs,
        "terminal_value":     round(tv_disk / 1e9, 2),
        "sum_disk_fcfs":      round(sum(disk_fcfs) / 1e9, 2),
        "nettoverschuldung":  round(nettoverschuldung / 1e9, 2),
        "marktcap":           round(mktcap / 1e9, 2),
        "aktien":             round(aktien / 1e9, 3),
        "gesamtschulden":     round(schulden / 1e9, 2),
        "cash":               round(cash / 1e9, 2),
        "kgv":                info.get("trailingPE"),
        "forward_kgv":        info.get("forwardPE"),
        "kbv":                info.get("priceToBook"),
        "ev_ebitda":          info.get("enterpriseToEbitda"),
        "kuv":                info.get("priceToSalesTrailing12Months"),
        "roe":                info.get("returnOnEquity"),
        "nettomarge":         info.get("profitMargins"),
        "dividende":          info.get("dividendYield"),
        "umsatzwachstum":     round(umsatz_wachstum, 1) if umsatz_wachstum else None,
        "wachstum_annahme":   round(wachstum * 100, 1),
        "terminal_annahme":   round(terminal * 100, 1),
        "sicherheit_annahme": round(sicherheit * 100, 0),
    }
    ergebnis["value_score"] = berechne_value_score(ergebnis)
    return ergebnis, None


def ergebnis_zu_db_eintrag(e):
    return {
        "Symbol":           e["symbol"],
        "Name":             e["name"],
        "Sektor":           e["sektor"],
        "Kurs":             e["kurs"],
        "Innerer Wert":     e["innerer_wert"],
        "Mit Marge":        e["mit_marge"],
        "Abweichung %":     e["abweichung"],
        "Value Score":      e.get("value_score", 0),
        "WACC %":           e["wacc"],
        "KGV":              e.get("kgv"),
        "Forward KGV":      e.get("forward_kgv"),
        "KBV":              e.get("kbv"),
        "EV/EBITDA":        e.get("ev_ebitda"),
        "FCF (Mrd.)":       e["fcf"],
        "FCF CAGR %":       e.get("fcf_cagr"),
        "ROE %":            round(e["roe"] * 100, 1) if e.get("roe") else None,
        "Nettomarge %":     round(e["nettomarge"] * 100, 1) if e.get("nettomarge") else None,
        "Dividende %":      round(e["dividende"] * 100, 2) if e.get("dividende") else None,
        "Umsatzwachstum %": e.get("umsatzwachstum"),
        "FCF Basis":        e["fcf_hinweis"],
        "Wachstum %":       e["wachstum_annahme"],
    }


def in_datenbank_speichern(ergebnis):
    eintrag = ergebnis_zu_db_eintrag(ergebnis)
    symbole = [e["Symbol"] for e in st.session_state.datenbank]
    if ergebnis["symbol"] in symbole:
        st.session_state.datenbank[symbole.index(ergebnis["symbol"])] = eintrag
        return "aktualisiert"
    else:
        st.session_state.datenbank.append(eintrag)
        return "neu"


def aktie_suchen(suchbegriff):
    try:
        ergebnis = yf.Search(suchbegriff, max_results=6)
        treffer  = ergebnis.quotes
        if treffer:
            namen   = [f"{t.get('shortname', t.get('longname', '?'))} – {t.get('symbol', '?')}" for t in treffer]
            symbole = [t.get("symbol", "") for t in treffer]
            return namen, symbole
    except:
        pass
    return [], []


# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.title("📈 Aktien-Tool")
seite = st.sidebar.radio(
    "Navigation",
    ["🔍 Einzelanalyse", "📊 Datenbank", "💼 Portfolio", "🔄 Batch-Analyse", "ℹ️ Anleitung"]
)
st.sidebar.divider()
st.sidebar.caption(f"Datenbank: {len(st.session_state.datenbank)} Einträge")
st.sidebar.caption(f"Portfolio: {len(st.session_state.portfolio)} Positionen")

# ================================================================
# SEITE 1: EINZELANALYSE
# ================================================================
if seite == "🔍 Einzelanalyse":
    st.title("Einzelanalyse")

    col1, col2 = st.columns([3, 1])
    with col1:
        suchbegriff = st.text_input("Aktie suchen", placeholder="z.B. Apple, AAPL, SAP, Novo Nordisk...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        suchen_btn = st.button("Suchen", use_container_width=True)

    if suchen_btn and suchbegriff:
        namen, symbole = aktie_suchen(suchbegriff)
        st.session_state.such_namen   = namen
        st.session_state.such_symbole = symbole

    ausgewaehltes_symbol = ""
    if st.session_state.such_symbole:
        auswahl = st.selectbox("Treffer:", st.session_state.such_namen)
        idx     = st.session_state.such_namen.index(auswahl)
        ausgewaehltes_symbol = st.session_state.such_symbole[idx]
        st.info(f"Ausgewähltes Symbol: **{ausgewaehltes_symbol}**")

    with st.expander("Oder Symbol direkt eingeben"):
        direkt = st.text_input("Symbol", placeholder="z.B. AAPL, SAP.DE, ASML.AS")
        if direkt:
            ausgewaehltes_symbol = direkt.upper()

    st.divider()
    st.subheader("Annahmen")
    col1, col2, col3 = st.columns(3)
    with col1:
        wachstum   = st.slider("FCF-Wachstum %", -20, 30, 8) / 100
    with col2:
        terminal   = st.slider("Terminale Wachstumsrate %", 0, 6, 3) / 100
    with col3:
        sicherheit = st.slider("Sicherheitsmarge %", 0, 50, 25) / 100

    wacc_modus    = st.radio("WACC", ["Automatisch", "Manuell"], horizontal=True)
    wacc_override = None
    if wacc_modus == "Manuell":
        wacc_override = st.slider("WACC manuell %", 1, 20, 8) / 100

    if st.button("Analysieren", type="primary", use_container_width=True):
        if ausgewaehltes_symbol:
            with st.spinner(f"Lade Daten für {ausgewaehltes_symbol}..."):
                ergebnis, fehler = dcf_berechnen(
                    ausgewaehltes_symbol, wachstum, terminal, sicherheit, wacc_override
                )
            if fehler:
                st.error(f"Fehler: {fehler}")
            else:
                st.session_state.letztes_ergebnis = ergebnis
        else:
            st.warning("Bitte zuerst eine Aktie suchen und auswählen.")

    # Ergebnis anzeigen
    if st.session_state.letztes_ergebnis:
        e = st.session_state.letztes_ergebnis
        st.divider()
        st.subheader(f"{e['name']} ({e['symbol']})")
        st.caption(f"Sektor: {e['sektor']}")

        # Hauptmetriken
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Aktueller Kurs",      f"${e['kurs']:.2f}")
        col2.metric("Innerer Wert",         f"${e['innerer_wert']:.2f}")
        col3.metric("Mit Sicherheitsmarge", f"${e['mit_marge']:.2f}")
        abw = e["abweichung"]
        col4.metric("Bewertung", f"{abw:+.1f}%",
                    delta="Überbewertet" if abw > 0 else "Unterbewertet",
                    delta_color="inverse")
        score = e.get("value_score", 0)
        col5.metric("Value Score", f"{score}/100",
                    delta="stark" if score > 60 else "mittel" if score > 40 else "schwach")

        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Kennzahlen", "💰 FCF & Cashflows", "🔢 DCF-Berechnung", "⚙️ WACC"
        ])

        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Bewertung**")
                st.write(f"KGV: {e['kgv']:.1f}" if e.get('kgv') else "KGV: N/A")
                st.write(f"Forward KGV: {e['forward_kgv']:.1f}" if e.get('forward_kgv') else "Forward KGV: N/A")
                st.write(f"KBV: {e['kbv']:.2f}" if e.get('kbv') else "KBV: N/A")
                st.write(f"EV/EBITDA: {e['ev_ebitda']:.1f}" if e.get('ev_ebitda') else "EV/EBITDA: N/A")
                st.write(f"KUV: {e['kuv']:.2f}" if e.get('kuv') else "KUV: N/A")
            with col2:
                st.markdown("**Profitabilität**")
                st.write(f"ROE: {e['roe']*100:.1f}%" if e.get('roe') else "ROE: N/A")
                st.write(f"Nettomarge: {e['nettomarge']*100:.1f}%" if e.get('nettomarge') else "Nettomarge: N/A")
                st.write(f"Umsatzwachstum: {e['umsatzwachstum']:.1f}%" if e.get('umsatzwachstum') else "Umsatzwachstum: N/A")
                st.write(f"Dividende: {e['dividende']*100:.2f}%" if e.get('dividende') else "Dividende: keine")
            with col3:
                st.markdown("**Bilanz**")
                st.write(f"Marktkapitalisierung: ${e['marktcap']:.1f} Mrd.")
                st.write(f"Gesamtschulden: ${e['gesamtschulden']:.2f} Mrd.")
                st.write(f"Cash: ${e['cash']:.2f} Mrd.")
                st.write(f"Nettoverschuldung: ${e['nettoverschuldung']:.2f} Mrd.")
                st.write(f"Aktien im Umlauf: {e['aktien']:.3f} Mrd.")

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Historische FCFs**")
                st.write(f"FCF-Basis: ${e['fcf']} Mrd.")
                st.write(f"Qualität: {e['fcf_hinweis']}")
                st.write(f"FCF CAGR: {e['fcf_cagr']:.1f}%" if e.get('fcf_cagr') else "FCF CAGR: N/A")
                if e.get('fcf_historie'):
                    fcf_df = pd.DataFrame({
                        "Jahr":         [str(j)[:4] for j in e['fcf_jahre']],
                        "FCF (Mrd. $)": e['fcf_historie']
                    })
                    st.dataframe(fcf_df, hide_index=True, use_container_width=True)
            with col2:
                if e.get('fcf_historie'):
                    fig = px.bar(
                        x=[str(j)[:4] for j in e['fcf_jahre']],
                        y=e['fcf_historie'],
                        labels={"x": "Jahr", "y": "FCF (Mrd. $)"},
                        title="FCF-Entwicklung",
                        color=e['fcf_historie'],
                        color_continuous_scale="RdYlGn"
                    )
                    fig.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"**Projizierte FCFs ({e['wachstum_annahme']:.0f}% Wachstum)**")
            proj_df = pd.DataFrame({
                "Jahr":             [f"Jahr {i+1}" for i in range(10)],
                "FCF (Mrd. $)":     e['projizierte_fcfs']
            })
            fig2 = px.bar(proj_df, x="Jahr", y="FCF (Mrd. $)",
                          title="Projizierte FCFs (10 Jahre)",
                          color="FCF (Mrd. $)",
                          color_continuous_scale="Blues")
            fig2.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Eingabewerte**")
                st.write(f"FCF-Basis: ${e['fcf']} Mrd.")
                st.write(f"Wachstumsannahme: {e['wachstum_annahme']}% p.a.")
                st.write(f"Terminale Wachstumsrate: {e['terminal_annahme']}%")
                st.write(f"WACC: {e['wacc']}%")
                st.write(f"Sicherheitsmarge: {e['sicherheit_annahme']:.0f}%")
            with col2:
                st.markdown("**Berechnung**")
                st.write(f"Summe disk. FCFs: ${e['sum_disk_fcfs']} Mrd.")
                st.write(f"Terminal Value (disk.): ${e['terminal_value']} Mrd.")
                gesamt = e['sum_disk_fcfs'] + e['terminal_value']
                st.write(f"Unternehmenswert: ${gesamt:.2f} Mrd.")
                st.write(f"– Nettoverschuldung: ${e['nettoverschuldung']} Mrd.")
                ew = gesamt - e['nettoverschuldung']
                st.write(f"= Eigenkapitalwert: ${ew:.2f} Mrd.")
                st.write(f"÷ Aktien: {e['aktien']} Mrd.")
                st.write(f"**= Innerer Wert: ${e['innerer_wert']:.2f}**")

            fig3 = px.bar(
                x=["Aktueller Kurs", "Innerer Wert", "Mit Sicherheitsmarge"],
                y=[e['kurs'], e['innerer_wert'], e['mit_marge']],
                color=["Kurs", "Innerer Wert", "Mit Marge"],
                color_discrete_map={
                    "Kurs": "#378ADD", "Innerer Wert": "#1D9E75", "Mit Marge": "#EF9F27"
                },
                labels={"x": "", "y": "Preis ($)"},
                title="Kurs vs. innerer Wert"
            )
            fig3.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig3, use_container_width=True)

        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Eigenkapitalkosten (CAPM)**")
                st.write("Risikofreier Zinssatz: 4.0%")
                st.write(f"Beta: {e['beta']}")
                st.write("Marktprämie: 5.5%")
                st.write(f"Eigenkapitalkosten: {e['ek_kosten']}%")
            with col2:
                st.markdown("**Gewichtung & Ergebnis**")
                st.write(f"EK-Anteil: {e['ek_anteil']}%")
                st.write(f"FK-Anteil: {e['fk_anteil']}%")
                st.write(f"Fremdkapitalkosten (netto): {e['fk_kosten']}%")
                st.write(f"WACC (berechnet): {e['wacc_berechnet']}%")
                st.write(f"**WACC (verwendet): {e['wacc']}%**")

        st.divider()
        if st.button("💾 In Datenbank speichern", type="primary"):
            status = in_datenbank_speichern(e)
            if status == "aktualisiert":
                st.success(f"✅ {e['name']} aktualisiert!")
            else:
                st.success(f"✅ {e['name']} gespeichert! ({len(st.session_state.datenbank)} Einträge)")

# ================================================================
# SEITE 2: DATENBANK
# ================================================================
elif seite == "📊 Datenbank":
    st.title("Datenbank")

    if not st.session_state.datenbank:
        st.info("Noch keine Einträge. Analysiere Aktien oder starte eine Batch-Analyse.")
    else:
        df = pd.DataFrame(st.session_state.datenbank)

        col1, col2, col3 = st.columns(3)
        with col1:
            sektoren      = ["Alle"] + sorted(df["Sektor"].dropna().unique().tolist())
            sektor_filter = st.selectbox("Sektor", sektoren)
        with col2:
            abw_range = st.slider("Abweichung % filtern", -300, 500, (-300, 500))
        with col3:
            sortierung = st.selectbox("Sortieren nach",
                ["Value Score", "Abweichung %", "KGV", "FCF CAGR %", "ROE %", "Name"])

        gefiltert = df.copy()
        if sektor_filter != "Alle":
            gefiltert = gefiltert[gefiltert["Sektor"] == sektor_filter]
        gefiltert = gefiltert[
            (gefiltert["Abweichung %"] >= abw_range[0]) &
            (gefiltert["Abweichung %"] <= abw_range[1])
        ]
        aufsteigend = sortierung not in ["Value Score"]
        gefiltert   = gefiltert.sort_values(sortierung, ascending=aufsteigend, na_position="last")

        st.caption(f"{len(gefiltert)} von {len(df)} Einträgen")
        st.dataframe(gefiltert, use_container_width=True, hide_index=True)

        if len(gefiltert) > 1:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.scatter(
                    gefiltert.dropna(subset=["KGV", "Abweichung %"]),
                    x="KGV", y="Abweichung %",
                    hover_name="Name", color="Sektor",
                    title="KGV vs. Abweichung"
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top10 = gefiltert.nsmallest(10, "Abweichung %")
                fig2  = px.bar(top10, x="Symbol", y="Abweichung %",
                               title="Top 10 günstigste Titel",
                               color="Abweichung %",
                               color_continuous_scale="RdYlGn_r")
                st.plotly_chart(fig2, use_container_width=True)

        csv = gefiltert.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV exportieren", csv, "datenbank.csv", "text/csv")

# ================================================================
# SEITE 3: PORTFOLIO
# ================================================================
elif seite == "💼 Portfolio":
    st.title("Portfolio")

    with st.expander("➕ Position hinzufügen", expanded=not bool(st.session_state.portfolio)):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_such     = st.text_input("Suche", placeholder="Apple, AAPL...")
            p_such_btn = st.button("Suchen", key="p_such_btn")
        with col2:
            p_einstand = st.number_input("Einstandskurs ($)", min_value=0.0, step=0.01)
        with col3:
            p_stueck   = st.number_input("Anzahl Stück", min_value=0.0, step=1.0)

        if p_such_btn and p_such:
            namen, symbole = aktie_suchen(p_such)
            st.session_state.p_namen   = namen
            st.session_state.p_symbole = symbole

        p_symbol = ""
        if st.session_state.p_symbole:
            auswahl  = st.selectbox("Treffer:", st.session_state.p_namen, key="p_auswahl")
            idx      = st.session_state.p_namen.index(auswahl)
            p_symbol = st.session_state.p_symbole[idx]
            st.info(f"Symbol: **{p_symbol}**")

        if st.button("Position hinzufügen", type="primary", key="p_hinzu"):
            if p_symbol and p_einstand > 0 and p_stueck > 0:
                with st.spinner(f"Lade {p_symbol}..."):
                    info = yf.Ticker(p_symbol).info
                    kurs = float(info.get("currentPrice") or 0)
                    name = info.get("longName", p_symbol)

                    innerer_wert = 0
                    for db_e in st.session_state.datenbank:
                        if db_e.get("Symbol") == p_symbol:
                            innerer_wert = float(db_e.get("Innerer Wert") or 0)
                            break

                    perf = (kurs - p_einstand) / p_einstand * 100
                    abw  = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert > 0 else None

                    if innerer_wert > 0 and abw is not None:
                        if abw > 40:    empf = "🔴 Dringend verkaufen"
                        elif abw > 20:  empf = "🟠 Verkaufen"
                        elif abw > 0:   empf = "🟡 Halten"
                        elif abw > -20: empf = "🟡 Halten"
                        elif abw > -40: empf = "🟢 Nachkaufen"
                        else:           empf = "🟢 Stark nachkaufen"
                    else:
                        empf = "⚠️ Erst in Einzelanalyse analysieren"

                    position = {
                        "Symbol":        p_symbol,
                        "Name":          name,
                        "Stück":         p_stueck,
                        "Einstand ($)":  p_einstand,
                        "Kurs ($)":      round(kurs, 2),
                        "Invest ($)":    round(p_einstand * p_stueck, 2),
                        "Wert ($)":      round(kurs * p_stueck, 2),
                        "Performance %": round(perf, 1),
                        "Innerer Wert":  round(innerer_wert, 2),
                        "Abweichung %":  round(abw, 1) if abw else None,
                        "Empfehlung":    empf,
                    }

                    symbole_p = [p["Symbol"] for p in st.session_state.portfolio]
                    if p_symbol in symbole_p:
                        st.session_state.portfolio[symbole_p.index(p_symbol)] = position
                        st.success(f"✅ {name} aktualisiert!")
                    else:
                        st.session_state.portfolio.append(position)
                        st.success(f"✅ {name} hinzugefügt!")
            else:
                st.warning("Bitte Aktie suchen, Einstandskurs und Stückzahl angeben.")

    if st.session_state.portfolio:
        df_p          = pd.DataFrame(st.session_state.portfolio)
        gesamt_invest = df_p["Invest ($)"].sum()
        gesamt_wert   = df_p["Wert ($)"].sum()
        gesamt_perf   = (gesamt_wert - gesamt_invest) / gesamt_invest * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Positionen",     len(df_p))
        col2.metric("Investiert",     f"${gesamt_invest:,.2f}")
        col3.metric("Aktueller Wert", f"${gesamt_wert:,.2f}")
        col4.metric("Performance",    f"{gesamt_perf:+.1f}%")

        st.divider()
        st.dataframe(df_p, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_p, values="Wert ($)", names="Symbol",
                         title="Portfolio-Verteilung")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df_p, x="Symbol", y="Performance %",
                         color="Performance %",
                         color_continuous_scale="RdYlGn",
                         title="Performance je Position")
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)

        csv = df_p.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Portfolio exportieren", csv, "portfolio.csv", "text/csv")
    else:
        st.info("Noch keine Positionen. Füge deine erste Position oben hinzu.")

# ================================================================
# SEITE 4: BATCH-ANALYSE
# ================================================================
elif seite == "🔄 Batch-Analyse":
    st.title("Batch-Analyse")
    st.write("Analysiere automatisch viele Aktien und speichere sie in der Datenbank.")

    col1, col2, col3 = st.columns(3)
    with col1:
        b_wachstum   = st.slider("FCF-Wachstum %", 0, 15, 6) / 100
    with col2:
        b_terminal   = st.slider("Terminal %", 1, 5, 3) / 100
    with col3:
        b_sicherheit = st.slider("Sicherheitsmarge %", 0, 40, 25) / 100

    anzahl = st.slider("Wie viele Aktien?", 10, len(VALUE_UNIVERSUM), 50)
    st.caption(f"{anzahl} Aktien · ca. {anzahl//10}–{anzahl//6} Minuten")

    if st.button("Batch-Analyse starten", type="primary"):
        auswahl      = VALUE_UNIVERSUM[:anzahl]
        fortschritt  = st.progress(0)
        status_text  = st.empty()
        fehler_liste = []
        erfolge      = 0

        for i, symbol in enumerate(auswahl):
            status_text.text(f"[{i+1}/{len(auswahl)}] {symbol}...")
            try:
                ergebnis, fehler = dcf_berechnen(symbol, b_wachstum, b_terminal, b_sicherheit)
                if ergebnis:
                    in_datenbank_speichern(ergebnis)
                    erfolge += 1
                else:
                    fehler_liste.append(f"{symbol}: {fehler}")
            except Exception as ex:
                fehler_liste.append(f"{symbol}: {str(ex)}")
            fortschritt.progress((i + 1) / len(auswahl))
            time.sleep(0.3)

        status_text.text("Fertig!")
        st.success(f"✅ {erfolge} Aktien gespeichert, {len(fehler_liste)} übersprungen.")
        if fehler_liste:
            with st.expander("Übersprungene Aktien"):
                for f in fehler_liste:
                    st.write(f)
        st.info("Geh zur Datenbank-Seite um die Ergebnisse zu sehen.")

# ================================================================
# SEITE 5: ANLEITUNG
# ================================================================
elif seite == "ℹ️ Anleitung":
    st.title("Anleitung")
    st.markdown("""
    ## Wie du das Tool nutzt

    ### 1. Einzelanalyse
    Suche eine Aktie nach Name oder Symbol. Das Tool zeigt inneren Wert,
    alle Kennzahlen, FCF-Historie, projizierte Cashflows und WACC-Details.
    Speichere interessante Aktien in die Datenbank.

    ### 2. Batch-Analyse
    Analysiere bis zu 200 vorausgewählte Value-Titel automatisch.
    Ideal für einen schnellen Marktüberblick.

    ### 3. Datenbank
    Alle gespeicherten Aktien – filterbar, sortierbar, exportierbar.

    ### 4. Portfolio
    Trage deine Positionen ein und erhalte Handlungsempfehlungen.

    ---

    ## Welche Aktien eignen sich?

    | Typ | Beispiele | Empfehlung |
    |-----|-----------|------------|
    | Value-Titel | Coca-Cola, J&J, SAP | DCF voll vertrauen, Wachstum 4–8% |
    | Wachstum | ASML, Microsoft | Wachstum 12–20%, Score ignorieren |
    | Banken/Versorger | JPMorgan, Duke | Nur Kennzahlen, DCF ignorieren |

    ## Symbole
    - **USA:** AAPL, MSFT, KO
    - **Deutschland:** SAP.DE, SIE.DE, ALV.DE
    - **Niederlande:** ASML.AS
    - **Schweiz:** NESN.SW, NOVN.SW
    - **UK:** SHEL.L, AZN.L
    """)
