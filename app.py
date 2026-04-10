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
# 200 VALUE-TITEL VORDEFINIERT
# ================================================================
VALUE_UNIVERSUM = [
    # USA – Konsumgüter
    "KO","PEP","PG","CL","GIS","K","MKC","SJM","CAG","HRL",
    "MCD","YUM","DPZ","CMG","WMT","COST","TGT","KR","SYY","MO",
    # USA – Gesundheit
    "JNJ","ABT","MDT","SYK","BSX","BDX","ZBH","EW","ISRG","RMD",
    "PFE","MRK","LLY","ABBV","BMY","AMGN","GILD","BIIB","REGN","VRTX",
    "CVS","UNH","HUM","CI","ELV","MCK","CAH","ABC","MOH","CNC",
    # USA – Industrie
    "MMM","HON","GE","CAT","DE","EMR","ITW","ETN","PH","ROK",
    "DOV","AME","FTV","XYL","GNRC","ROP","IDEX","IR","TT","carrier",
    "UPS","FDX","CSX","NSC","UNP","WAB","EXPD","CHRW","JBHT","ODFL",
    # USA – Technologie (stabile FCF)
    "AAPL","MSFT","CSCO","IBM","ORCL","TXN","QCOM","ADI","KLAC","LRCX",
    "AMAT","MSI","CTSH","ACN","INTU","PAYX","ADP","FISV","FIS","GPN",
    # USA – Finanzen
    "BRK-B","JPM","BAC","WFC","USB","TFC","PNC","MTB","CFG","FITB",
    "AXP","V","MA","DFS","COF","SYF","AIG","PRU","MET","AFL",
    "BLK","TROW","BEN","IVZ","AMG","WTW","AON","MMC","CB","TRV",
    # USA – Energie
    "XOM","CVX","COP","SLB","HAL","BKR","PSX","VLO","MPC","PXD",
    "EOG","DVN","FANG","MRO","APA","OXY","HES","CTRA","EQT","AR",
    # USA – Versorger & Immobilien
    "NEE","DUK","SO","D","AEP","EXC","SRE","XEL","ES","ETR",
    "AMT","PLD","CCI","EQIX","PSA","O","SPG","WELL","AVB","EQR",
    # Deutschland
    "SAP.DE","SIE.DE","ALV.DE","MUV2.DE","BMW.DE","MBG.DE","VOW3.DE",
    "BAS.DE","BAYN.DE","DBK.DE","DTE.DE","ENR.DE","RWE.DE","HEN3.DE",
    "ADS.DE","IFX.DE","MTX.DE","MRK.DE","FRE.DE","HNKG_p.DE",
    # Großbritannien
    "SHEL.L","BP.L","HSBA.L","LLOY.L","BARC.L","AZN.L","GSK.L",
    "ULVR.L","DGE.L","BATS.L","IMB.L","VOD.L","BT-A.L","NG.L","SSE.L",
    # Schweiz
    "NESN.SW","NOVN.SW","ROG.SW","ZURN.SW","ABBN.SW","CSGN.SW",
    "UBSG.SW","SREN.SW","SCMN.SW","LONN.SW",
    # Niederlande & Frankreich
    "ASML.AS","INGA.AS","PHIA.AS","REN.AS","HEIA.AS",
    "OR.PA","TTE.PA","SAN.PA","BNP.PA","ACA.PA","AIR.PA","MC.PA",
    # Japan
    "7203.T","6758.T","9432.T","8306.T","4502.T","6501.T","7751.T",
    # Sonstige
    "NOVOB.CO","NOVO-B.CO","ABB.ST","ERIC-B.ST","ATCO-A.ST",
    "RIO.L","BHP.L","GLEN.L","AAL.L","ANTO.L",
]

# ================================================================
# HILFSFUNKTIONEN
# ================================================================
def fcf_basis_berechnen(cashflow):
    if "Free Cash Flow" not in cashflow.index:
        return None, "nicht verfügbar", [], []
    fcf_serie  = cashflow.loc["Free Cash Flow"]
    fcf_jahre  = list(fcf_serie.index[:5])
    fcf_werte  = [round(v/1e9, 2) for v in fcf_serie.values[:5]]
    positive   = [f for f in fcf_serie.values[:5] if f > 0]
    if not positive:
        return fcf_serie.values[0], "⚠️ alle negativ", fcf_werte, fcf_jahre
    elif len(positive) < 3:
        fcf = sum(positive) / len(positive)
        return fcf, f"⚠️ Durchschnitt {len(positive)} pos. Jahre", fcf_werte, fcf_jahre
    else:
        fcf = sum(fcf_serie.values[:3]) / 3
        return fcf, "✅ Durchschnitt 3 Jahre", fcf_werte, fcf_jahre


def berechne_wacc(info):
    beta                 = info.get("beta", 1.0) or 1.0
    gesamtschulden       = info.get("totalDebt", 0) or 0
    marktkapitalisierung = info.get("marketCap", 0) or 0
    zinsen               = info.get("interestExpense", 0) or 0
    steuerrate           = info.get("effectiveTaxRate", 0.21) or 0.21
    eigenkapitalkosten   = 0.04 + beta * 0.055
    fk_brutto            = abs(zinsen) / gesamtschulden if gesamtschulden > 0 and zinsen else 0.04
    fk_netto             = fk_brutto * (1 - steuerrate)
    gesamt               = marktkapitalisierung + gesamtschulden
    ek_anteil            = marktkapitalisierung / gesamt if gesamt > 0 else 1.0
    fk_anteil            = gesamtschulden / gesamt if gesamt > 0 else 0.0
    return ek_anteil * eigenkapitalkosten + fk_anteil * fk_netto, beta, eigenkapitalkosten, fk_netto, ek_anteil, fk_anteil


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

    gesamtschulden    = info.get("totalDebt", 0) or 0
    cash              = info.get("totalCash", 0) or 0
    nettoverschuldung = gesamtschulden - cash

    wacc_berechnet, beta, ek_kosten, fk_kosten, ek_anteil, fk_anteil = berechne_wacc(info)
    wacc = wacc_override if wacc_override else wacc_berechnet

    if wacc <= terminal:
        return None, "WACC muss größer sein als terminale Wachstumsrate"

    # Diskontierte FCFs
    diskontierte_fcfs  = []
    projizierte_fcfs   = []
    aktueller_fcf      = fcf
    for jahr in range(1, 11):
        aktueller_fcf *= (1 + wachstum)
        projizierte_fcfs.append(round(aktueller_fcf / 1e9, 2))
        diskontierte_fcfs.append(aktueller_fcf / (1 + wacc) ** jahr)

    terminal_value      = aktueller_fcf * (1 + terminal) / (wacc - terminal)
    terminal_value_disk = terminal_value / (1 + wacc) ** 10
    unternehmenswert    = sum(diskontierte_fcfs) + terminal_value_disk
    innerer_wert        = (unternehmenswert - nettoverschuldung) / aktien
    mit_marge           = innerer_wert * (1 - sicherheit)
    kurs                = info.get("currentPrice", 0) or 0
    abweichung          = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert != 0 else 0

    # FCF CAGR
    fcf_cagr = None
    if len(fcf_historie) >= 2 and fcf_historie[-1] > 0 and fcf_historie[0] > 0:
        fcf_cagr = ((fcf_historie[0] / fcf_historie[-1]) ** (1/(len(fcf_historie)-1)) - 1) * 100

    # Umsatzwachstum
    umsatz_wachstum = None
    if "Total Revenue" in finanzen.index:
        umsatz = finanzen.loc["Total Revenue"].values
        if len(umsatz) >= 2 and umsatz[-1] > 0:
            umsatz_wachstum = ((umsatz[0] / umsatz[-1]) ** (1/(len(umsatz)-1)) - 1) * 100

    return {
        "name":               info.get("longName", symbol),
        "symbol":             symbol,
        "sektor":             info.get("sector", "N/A"),
        "kurs":               round(kurs, 2),
        "innerer_wert":       round(innerer_wert, 2),
        "mit_marge":          round(mit_marge, 2),
        "abweichung":         round(abweichung, 1),
        "wacc":               round(wacc * 100, 2),
        "wacc_berechnet":     round(wacc_berechnet * 100, 2),
        "beta":               round(beta, 2),
        "ek_kosten":          round(ek_kosten * 100, 2),
        "fk_kosten":          round(fk_kosten * 100, 2),
        "ek_anteil":          round(ek_anteil * 100, 1),
        "fk_anteil":          round(fk_anteil * 100, 1),
        "fcf_hinweis":        fcf_hinweis,
        "fcf":                round(fcf / 1e9, 2),
        "fcf_historie":       fcf_historie,
        "fcf_jahre":          fcf_jahre,
        "fcf_cagr":           round(fcf_cagr, 1) if fcf_cagr else None,
        "projizierte_fcfs":   projizierte_fcfs,
        "terminal_value":     round(terminal_value_disk / 1e9, 2),
        "sum_disk_fcfs":      round(sum(diskontierte_fcfs) / 1e9, 2),
        "nettoverschuldung":  round(nettoverschuldung / 1e9, 2),
        "marktcap":           round((info.get("marketCap", 0) or 0) / 1e9, 2),
        "aktien":             round(aktien / 1e9, 3),
        "gesamtschulden":     round(gesamtschulden / 1e9, 2),
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
    }, None


def ergebnis_zu_db_eintrag(e):
    return {
        "Symbol":            e["symbol"],
        "Name":              e["name"],
        "Sektor":            e["sektor"],
        "Kurs":              e["kurs"],
        "Innerer Wert":      e["innerer_wert"],
        "Mit Marge":         e["mit_marge"],
        "Abweichung %":      e["abweichung"],
        "WACC %":            e["wacc"],
        "KGV":               e["kgv"],
        "Forward KGV":       e["forward_kgv"],
        "KBV":               e["kbv"],
        "EV/EBITDA":         e["ev_ebitda"],
        "FCF (Mrd.)":        e["fcf"],
        "FCF CAGR %":        e["fcf_cagr"],
        "Umsatzwachstum %":  e["umsatzwachstum"],
        "ROE %":             round(e["roe"] * 100, 1) if e["roe"] else None,
        "Nettomarge %":      round(e["nettomarge"] * 100, 1) if e["nettomarge"] else None,
        "Dividende %":       round(e["dividende"] * 100, 2) if e["dividende"] else None,
        "FCF Basis":         e["fcf_hinweis"],
        "Wachstum Annahme":  e["wachstum_annahme"],
    }


def in_datenbank_speichern(ergebnis):
    eintrag  = ergebnis_zu_db_eintrag(ergebnis)
    symbole  = [e["Symbol"] for e in st.session_state.datenbank]
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
            return [
                f"{t.get('shortname', t.get('longname', '?'))} – {t.get('symbol', '?')}"
                for t in treffer
            ], [t.get('symbol', '') for t in treffer]
    except:
        pass
    return [], []


# ================================================================
# SESSION STATE
# ================================================================
if "datenbank" not in st.session_state:
    st.session_state.datenbank = []
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "such_symbole" not in st.session_state:
    st.session_state.such_symbole = []
if "letztes_ergebnis" not in st.session_state:
    st.session_state.letztes_ergebnis = None

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

    # Suche mit Vorschlägen
    st.subheader("Aktie suchen")
    col1, col2 = st.columns([3, 1])
    with col1:
        suchbegriff = st.text_input(
            "Name oder Symbol",
            placeholder="z.B. Apple, AAPL, SAP, Novo Nordisk..."
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        suchen_btn = st.button("Suchen", use_container_width=True)

    # Vorschläge anzeigen
    ausgewaehltes_symbol = ""
    if suchen_btn and suchbegriff:
        namen, symbole = aktie_suchen(suchbegriff)
        st.session_state.such_namen   = namen
        st.session_state.such_symbole = symbole

    if st.session_state.such_symbole:
        auswahl = st.selectbox(
            "Treffer – bitte auswählen:",
            options=st.session_state.such_namen,
            index=0
        )
        idx = st.session_state.such_namen.index(auswahl)
        ausgewaehltes_symbol = st.session_state.such_symbole[idx]
        st.info(f"Ausgewähltes Symbol: **{ausgewaehltes_symbol}**")

    # Direkteingabe als Alternative
    with st.expander("Oder Symbol direkt eingeben"):
        direkteingabe = st.text_input("Symbol", placeholder="z.B. AAPL, SAP.DE, ASML.AS")
        if direkteingabe:
            ausgewaehltes_symbol = direkteingabe.upper()

    st.divider()

    # Annahmen
    st.subheader("Annahmen")
    col1, col2, col3 = st.columns(3)
    with col1:
        wachstum   = st.slider("FCF-Wachstum %", -20, 30, 8) / 100
    with col2:
        terminal   = st.slider("Terminale Wachstumsrate %", 0, 6, 3) / 100
    with col3:
        sicherheit = st.slider("Sicherheitsmarge %", 0, 50, 25) / 100

    wacc_modus = st.radio("WACC", ["Automatisch berechnen", "Manuell eingeben"], horizontal=True)
    wacc_override = None
    if wacc_modus == "Manuell eingeben":
        wacc_override = st.slider("WACC manuell %", 1, 20, 8) / 100

    analysieren_btn = st.button("Analysieren", type="primary", use_container_width=True)

    # Analyse durchführen
    if analysieren_btn and ausgewaehltes_symbol:
        with st.spinner(f"Lade Daten für {ausgewaehltes_symbol}..."):
            ergebnis, fehler = dcf_berechnen(
                ausgewaehltes_symbol, wachstum, terminal, sicherheit, wacc_override
            )

        if fehler:
            st.error(f"Fehler: {fehler}")
        elif ergebnis:
            st.session_state.letztes_ergebnis = ergebnis
    elif analysieren_btn:
        st.warning("Bitte zuerst eine Aktie suchen und auswählen.")

    # Ergebnis anzeigen
    ergebnis = st.session_state.letztes_ergebnis
    if ergebnis:
        st.divider()
        st.subheader(f"{ergebnis['name']} ({ergebnis['symbol']})")
        st.caption(f"Sektor: {ergebnis['sektor']}")

        # Hauptkennzahlen
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Aktueller Kurs", f"${ergebnis['kurs']:.2f}")
        col2.metric("Innerer Wert", f"${ergebnis['innerer_wert']:.2f}")
        col3.metric("Mit Sicherheitsmarge", f"${ergebnis['mit_marge']:.2f}")
        abw = ergebnis['abweichung']
        col4.metric(
            "Bewertung",
            f"{abw:+.1f}%",
            delta="Überbewertet" if abw > 0 else "Unterbewertet",
            delta_color="inverse"
        )

        st.divider()

        # Tab-Layout für übersichtliche Darstellung
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Kennzahlen", "💰 FCF & Cashflows", "🔢 DCF-Berechnung", "⚙️ WACC"
        ])

        # --- Tab 1: Kennzahlen ---
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Bewertung**")
                st.write(f"KGV: {ergebnis['kgv']:.1f}" if ergebnis['kgv'] else "KGV: N/A")
                st.write(f"Forward KGV: {ergebnis['forward_kgv']:.1f}" if ergebnis['forward_kgv'] else "Forward KGV: N/A")
                st.write(f"KBV: {ergebnis['kbv']:.2f}" if ergebnis['kbv'] else "KBV: N/A")
                st.write(f"EV/EBITDA: {ergebnis['ev_ebitda']:.1f}" if ergebnis['ev_ebitda'] else "EV/EBITDA: N/A")
                st.write(f"KUV: {ergebnis['kuv']:.2f}" if ergebnis['kuv'] else "KUV: N/A")
            with col2:
                st.markdown("**Profitabilität**")
                st.write(f"ROE: {ergebnis['roe']*100:.1f}%" if ergebnis['roe'] else "ROE: N/A")
                st.write(f"Nettomarge: {ergebnis['nettomarge']*100:.1f}%" if ergebnis['nettomarge'] else "Nettomarge: N/A")
                st.write(f"Umsatzwachstum: {ergebnis['umsatzwachstum']:.1f}%" if ergebnis['umsatzwachstum'] else "Umsatzwachstum: N/A")
                st.write(f"Dividende: {ergebnis['dividende']*100:.2f}%" if ergebnis['dividende'] else "Dividende: keine")
            with col3:
                st.markdown("**Bilanz**")
                st.write(f"Marktkapitalisierung: ${ergebnis['marktcap']:.1f} Mrd.")
                st.write(f"Gesamtschulden: ${ergebnis['gesamtschulden']:.2f} Mrd.")
                st.write(f"Cash: ${ergebnis['cash']:.2f} Mrd.")
                st.write(f"Nettoverschuldung: ${ergebnis['nettoverschuldung']:.2f} Mrd.")
                st.write(f"Aktien im Umlauf: {ergebnis['aktien']:.3f} Mrd.")

        # --- Tab 2: FCF & Cashflows ---
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Historische FCFs**")
                st.write(f"FCF-Basis (verwendet): ${ergebnis['fcf']} Mrd.")
                st.write(f"FCF-Qualität: {ergebnis['fcf_hinweis']}")
                st.write(f"FCF CAGR: {ergebnis['fcf_cagr']:.1f}%" if ergebnis['fcf_cagr'] else "FCF CAGR: N/A")

                if ergebnis['fcf_historie']:
                    fcf_df = pd.DataFrame({
                        "Jahr":          [str(j)[:4] for j in ergebnis['fcf_jahre']],
                        "FCF (Mrd. $)":  ergebnis['fcf_historie']
                    })
                    st.dataframe(fcf_df, hide_index=True, use_container_width=True)

            with col2:
                if ergebnis['fcf_historie']:
                    fig = px.bar(
                        x=[str(j)[:4] for j in ergebnis['fcf_jahre']],
                        y=ergebnis['fcf_historie'],
                        labels={"x": "Jahr", "y": "FCF (Mrd. $)"},
                        title="FCF-Entwicklung (historisch)",
                        color=ergebnis['fcf_historie'],
                        color_continuous_scale="RdYlGn"
                    )
                    fig.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Projizierte FCFs (Annahme: {:.0f}% Wachstum)**".format(
                ergebnis['wachstum_annahme']))
            proj_df = pd.DataFrame({
                "Jahr":               [f"Jahr {i+1}" for i in range(10)],
                "Projizierter FCF":   ergebnis['projizierte_fcfs']
            })
            fig2 = px.bar(
                proj_df, x="Jahr", y="Projizierter FCF",
                title="Projizierte FCFs (nächste 10 Jahre)",
                color="Projizierter FCF",
                color_continuous_scale="Blues"
            )
            fig2.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig2, use_container_width=True)

        # --- Tab 3: DCF-Berechnung ---
        with tab3:
            st.markdown("**Basiswerte**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"FCF-Basis: ${ergebnis['fcf']} Mrd.")
                st.write(f"Wachstumsannahme: {ergebnis['wachstum_annahme']}% p.a.")
                st.write(f"Terminale Wachstumsrate: {ergebnis['terminal_annahme']}%")
                st.write(f"WACC (verwendet): {ergebnis['wacc']}%")
                st.write(f"Sicherheitsmarge: {ergebnis['sicherheit_annahme']:.0f}%")
            with col2:
                st.write(f"Summe disk. FCFs: ${ergebnis['sum_disk_fcfs']} Mrd.")
                st.write(f"Terminal Value (disk.): ${ergebnis['terminal_value']} Mrd.")
                gesamt = ergebnis['sum_disk_fcfs'] + ergebnis['terminal_value']
                st.write(f"Unternehmenswert: ${gesamt:.2f} Mrd.")
                st.write(f"– Nettoverschuldung: ${ergebnis['nettoverschuldung']} Mrd.")
                st.write(f"= Eigenkapitalwert: ${gesamt - ergebnis['nettoverschuldung']:.2f} Mrd.")
                st.write(f"÷ Aktien: {ergebnis['aktien']} Mrd.")
                st.write(f"**= Innerer Wert: ${ergebnis['innerer_wert']:.2f}**")

            st.divider()

            # Visualisierung Kurs vs Wert
            fig = px.bar(
                x=["Aktueller Kurs", "Innerer Wert", "Mit Sicherheitsmarge"],
                y=[ergebnis['kurs'], ergebnis['innerer_wert'], ergebnis['mit_marge']],
                color=["Kurs", "Innerer Wert", "Mit Marge"],
                color_discrete_map={
                    "Kurs":         "#378ADD",
                    "Innerer Wert": "#1D9E75",
                    "Mit Marge":    "#EF9F27"
                },
                labels={"x": "", "y": "Preis ($)"},
                title="Kurs vs. innerer Wert"
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        # --- Tab 4: WACC ---
        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Eigenkapitalkosten (CAPM)**")
                st.write(f"Risikofreier Zinssatz: 4.0%")
                st.write(f"Beta: {ergebnis['beta']}")
                st.write(f"Marktprämie: 5.5%")
                st.write(f"Eigenkapitalkosten: {ergebnis['ek_kosten']}%")
            with col2:
                st.markdown("**Gewichtung**")
                st.write(f"EK-Anteil: {ergebnis['ek_anteil']}%")
                st.write(f"FK-Anteil: {ergebnis['fk_anteil']}%")
                st.write(f"Fremdkapitalkosten (netto): {ergebnis['fk_kosten']}%")
                st.write(f"**WACC (berechnet): {ergebnis['wacc_berechnet']}%**")
                st.write(f"**WACC (verwendet): {ergebnis['wacc']}%**")

        st.divider()

        # In Datenbank speichern
        if st.button("💾 In Datenbank speichern", type="primary"):
            status = in_datenbank_speichern(ergebnis)
            if status == "aktualisiert":
                st.success(f"✅ {ergebnis['name']} in der Datenbank aktualisiert!")
            else:
                st.success(f"✅ {ergebnis['name']} in der Datenbank gespeichert! ({len(st.session_state.datenbank)} Einträge)")

    elif not st.session_state.letztes_ergebnis:
        st.info("Suche eine Aktie und klicke auf Analysieren.")

# ================================================================
# SEITE 2: DATENBANK
# ================================================================
elif seite == "📊 Datenbank":
    st.title("Datenbank")

    if not st.session_state.datenbank:
        st.info("Noch keine Aktien gespeichert. Analysiere Aktien auf der Einzelanalyse-Seite oder starte eine Batch-Analyse.")
    else:
        df = pd.DataFrame(st.session_state.datenbank)

        # Filter
        col1, col2, col3 = st.columns(3)
        with col1:
            sektoren      = ["Alle"] + sorted(df["Sektor"].dropna().unique().tolist())
            sektor_filter = st.selectbox("Sektor", sektoren)
        with col2:
            abw_min, abw_max = st.slider(
                "Abweichung % (Unter-/Überbewertung)",
                -300, 500, (-300, 500)
            )
        with col3:
            sortierung = st.selectbox(
                "Sortieren nach",
                ["Abweichung %", "KGV", "FCF CAGR %", "ROE %", "Name"]
            )

        gefiltert = df.copy()
        if sektor_filter != "Alle":
            gefiltert = gefiltert[gefiltert["Sektor"] == sektor_filter]
        gefiltert = gefiltert[
            (gefiltert["Abweichung %"] >= abw_min) &
            (gefiltert["Abweichung %"] <= abw_max)
        ]
        gefiltert = gefiltert.sort_values(sortierung, na_position="last")

        st.caption(f"{len(gefiltert)} von {len(df)} Einträgen")
        st.dataframe(gefiltert, use_container_width=True, hide_index=True)

        # Charts
        if len(gefiltert) > 1:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.scatter(
                    gefiltert.dropna(subset=["KGV", "Abweichung %"]),
                    x="KGV", y="Abweichung %",
                    hover_name="Name", color="Sektor",
                    title="KGV vs. Abweichung",
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top10 = gefiltert.nsmallest(10, "Abweichung %")
                fig2  = px.bar(
                    top10, x="Symbol", y="Abweichung %",
                    title="Top 10 günstigste Titel",
                    color="Abweichung %",
                    color_continuous_scale="RdYlGn_r"
                )
                st.plotly_chart(fig2, use_container_width=True)

        csv = gefiltert.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV exportieren", csv, "datenbank.csv", "text/csv")

# ================================================================
# SEITE 3: PORTFOLIO
# ================================================================
elif seite == "💼 Portfolio":
    st.title("Portfolio")

    with st.expander("➕ Position hinzufügen", expanded=not st.session_state.portfolio):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_such  = st.text_input("Suche", placeholder="Apple, AAPL...")
            p_such_btn = st.button("Suchen", key="p_such")
        with col2:
            p_einstand = st.number_input("Einstandskurs ($)", min_value=0.0, step=0.01)
        with col3:
            p_stueck = st.number_input("Anzahl Stück", min_value=0.0, step=1.0)

        if p_such_btn and p_such:
            namen, symbole = aktie_suchen(p_such)
            st.session_state.p_namen   = namen
            st.session_state.p_symbole = symbole

        p_symbol = ""
        if "p_symbole" in st.session_state and st.session_state.p_symbole:
            auswahl = st.selectbox("Treffer:", st.session_state.p_namen, key="p_auswahl")
            idx     = st.session_state.p_namen.index(auswahl)
            p_symbol = st.session_state.p_symbole[idx]
            st.info(f"Symbol: **{p_symbol}**")

        if st.button("Position hinzufügen", type="primary", key="p_hinzu"):
            if p_symbol and p_einstand > 0 and p_stueck > 0:
                with st.spinner(f"Lade {p_symbol}..."):
                    info = yf.Ticker(p_symbol).info
                    kurs = info.get("currentPrice", 0) or 0
                    name = info.get("longName", p_symbol)

                    innerer_wert = 0
                    for e in st.session_state.datenbank:
                        if e["Symbol"] == p_symbol:
                            innerer_wert = e.get("Innerer Wert", 0) or 0
                            break

                    perf = (kurs - p_einstand) / p_einstand * 100
                    abw  = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert > 0 else None

                    if innerer_wert > 0 and abw is not None:
                        if abw > 40:     empfehlung = "🔴 Dringend verkaufen"
                        elif abw > 20:   empfehlung = "🟠 Verkaufen"
                        elif abw > 0:    empfehlung = "🟡 Halten"
                        elif abw > -20:  empfehlung = "🟡 Halten"
                        elif abw > -40:  empfehlung = "🟢 Nachkaufen"
                        else:            empfehlung = "🟢 Stark nachkaufen"
                    else:
                        empfehlung = "⚠️ Erst in Einzelanalyse analysieren"

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
                        "Empfehlung":    empfehlung,
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
        df_p = pd.DataFrame(st.session_state.portfolio)

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

# ================================================================
# SEITE 4: BATCH-ANALYSE
# ================================================================
elif seite == "🔄 Batch-Analyse":
    st.title("Batch-Analyse")
    st.write("Analysiere automatisch viele Aktien auf einmal und speichere sie in der Datenbank.")

    col1, col2, col3 = st.columns(3)
    with col1:
        b_wachstum   = st.slider("FCF-Wachstum %", 0, 15, 6) / 100
    with col2:
        b_terminal   = st.slider("Terminal %", 1, 5, 3) / 100
    with col3:
        b_sicherheit = st.slider("Sicherheitsmarge %", 0, 40, 25) / 100

    anzahl = st.slider(
        "Wie viele Aktien analysieren?",
        10, len(VALUE_UNIVERSUM), 50
    )
    auswahl = VALUE_UNIVERSUM[:anzahl]
    st.caption(f"{anzahl} Aktien aus dem Value-Universum werden analysiert. Dauert ca. {anzahl//10}-{anzahl//6} Minuten.")

    if st.button("Batch-Analyse starten", type="primary"):
        fortschritt  = st.progress(0)
        status_text  = st.empty()
        fehler_liste = []
        erfolge      = 0

        for i, symbol in enumerate(auswahl):
            status_text.text(f"[{i+1}/{len(auswahl)}] Analysiere {symbol}...")
            try:
                ergebnis, fehler = dcf_berechnen(
                    symbol, b_wachstum, b_terminal, b_sicherheit
                )
                if ergebnis:
                    in_datenbank_speichern(ergebnis)
                    erfolge += 1
                else:
                    fehler_liste.append(f"{symbol}: {fehler}")
            except Exception as e:
                fehler_liste.append(f"{symbol}: {str(e)}")

            fortschritt.progress((i + 1) / len(auswahl))
            time.sleep(0.3)

        status_text.text("Fertig!")
        st.success(f"✅ {erfolge} Aktien analysiert und gespeichert. {len(fehler_liste)} übersprungen.")

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
    Suche eine Aktie nach Name oder Symbol. Das Tool zeigt dir den inneren Wert,
    alle Kennzahlen, die FCF-Historie, projizierte Cashflows und die vollständige
    WACC-Berechnung. Speichere interessante Aktien in die Datenbank.

    ### 2. Batch-Analyse
    Analysiere bis zu 200 Value-Titel auf einmal mit einheitlichen Annahmen.
    Ideal um schnell einen Überblick zu bekommen welche Titel besonders günstig sind.

    ### 3. Datenbank
    Alle gespeicherten Aktien gefiltert und sortierbar. Exportierbar als CSV.

    ### 4. Portfolio
    Trage deine echten Positionen ein und erhalte Handlungsempfehlungen.

    ---

    ## Welche Aktien eignen sich für das Tool?

    | Typ | Beispiele | Annahmen |
    |-----|-----------|----------|
    | Value-Titel | Coca-Cola, J&J, SAP | Wachstum 4–8%, voll vertrauen |
    | Wachstum | ASML, Microsoft | Wachstum 12–20%, Score ignorieren |
    | Banken/Versorger | JPMorgan, Duke | Nur Kennzahlen, kein DCF |

    ## Symbole
    - **USA:** AAPL, MSFT, KO
    - **Deutschland:** SAP.DE, SIE.DE, ALV.DE
    - **Niederlande:** ASML.AS, INGA.AS
    - **Schweiz:** NESN.SW, NOVN.SW
    - **UK:** SHEL.L, AZN.L
    """)
