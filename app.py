import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Aktien-Analyse Tool",
    page_icon="📈",
    layout="wide"
)

# --- Hilfsfunktionen ---
def fcf_basis_berechnen(cashflow):
    if "Free Cash Flow" not in cashflow.index:
        return None, "nicht verfügbar"
    fcf_werte = cashflow.loc["Free Cash Flow"].values[:5]
    positive  = [f for f in fcf_werte if f > 0]
    if not positive:
        return fcf_werte[0], "⚠️ alle negativ"
    elif len(positive) < len(fcf_werte[:3]):
        fcf = sum(positive) / len(positive)
        return fcf, f"⚠️ Durchschnitt {len(positive)} pos. Jahre"
    else:
        fcf = sum(fcf_werte[:3]) / 3
        return fcf, "✅ Durchschnitt 3 Jahre"


def berechne_wacc(info):
    beta                  = info.get("beta", 1.0) or 1.0
    gesamtschulden        = info.get("totalDebt", 0) or 0
    marktkapitalisierung  = info.get("marketCap", 0) or 0
    zinsen                = info.get("interestExpense", 0) or 0
    steuerrate            = info.get("effectiveTaxRate", 0.21) or 0.21

    eigenkapitalkosten        = 0.04 + beta * 0.055
    fremdkapitalkosten_brutto = abs(zinsen) / gesamtschulden if gesamtschulden > 0 and zinsen else 0.04
    fremdkapitalkosten        = fremdkapitalkosten_brutto * (1 - steuerrate)
    gesamtkapital             = marktkapitalisierung + gesamtschulden
    ek_anteil = marktkapitalisierung / gesamtkapital if gesamtkapital > 0 else 1.0
    fk_anteil = gesamtschulden / gesamtkapital if gesamtkapital > 0 else 0.0
    return ek_anteil * eigenkapitalkosten + fk_anteil * fremdkapitalkosten


def dcf_berechnen(symbol, wachstum, terminal, sicherheit, wacc_override=None):
    aktie    = yf.Ticker(symbol)
    info     = aktie.info
    cashflow = aktie.cashflow

    if not info or not info.get("longName"):
        return None, "Aktie nicht gefunden"

    fcf, fcf_hinweis = fcf_basis_berechnen(cashflow)
    if fcf is None:
        return None, "FCF nicht verfügbar"

    aktien        = info.get("sharesOutstanding")
    if not aktien:
        return None, "Aktienanzahl nicht verfügbar"

    gesamtschulden    = info.get("totalDebt", 0) or 0
    cash              = info.get("totalCash", 0) or 0
    nettoverschuldung = gesamtschulden - cash
    wacc              = wacc_override if wacc_override else berechne_wacc(info)

    if wacc <= terminal:
        return None, "WACC muss größer sein als terminale Wachstumsrate"

    diskontierte_fcfs = []
    aktueller_fcf = fcf
    for jahr in range(1, 11):
        aktueller_fcf *= (1 + wachstum)
        diskontierte_fcfs.append(aktueller_fcf / (1 + wacc) ** jahr)

    terminal_value             = aktueller_fcf * (1 + terminal) / (wacc - terminal)
    terminal_value_disk        = terminal_value / (1 + wacc) ** 10
    unternehmenswert           = sum(diskontierte_fcfs) + terminal_value_disk
    innerer_wert               = (unternehmenswert - nettoverschuldung) / aktien
    innerer_wert_mit_marge     = innerer_wert * (1 - sicherheit)
    kurs                       = info.get("currentPrice", 0) or 0
    abweichung                 = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert != 0 else 0

    return {
        "name":                 info.get("longName", symbol),
        "symbol":               symbol,
        "kurs":                 round(kurs, 2),
        "innerer_wert":         round(innerer_wert, 2),
        "mit_marge":            round(innerer_wert_mit_marge, 2),
        "abweichung":           round(abweichung, 1),
        "wacc":                 round(wacc * 100, 2),
        "fcf_hinweis":          fcf_hinweis,
        "fcf":                  round(fcf / 1e9, 2),
        "kgv":                  info.get("trailingPE"),
        "kbv":                  info.get("priceToBook"),
        "ev_ebitda":            info.get("enterpriseToEbitda"),
        "roe":                  info.get("returnOnEquity"),
        "nettomarge":           info.get("profitMargins"),
        "dividende":            info.get("dividendYield"),
        "beta":                 info.get("beta"),
        "sektor":               info.get("sector", "N/A"),
        "marktcap":             info.get("marketCap", 0),
    }, None


# --- Session State initialisieren ---
if "datenbank" not in st.session_state:
    st.session_state.datenbank = []
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- Sidebar Navigation ---
st.sidebar.title("📈 Aktien-Tool")
seite = st.sidebar.radio(
    "Navigation",
    ["🔍 Einzelanalyse", "📊 Datenbank", "💼 Portfolio", "ℹ️ Anleitung"]
)

# ================================================================
# SEITE 1: EINZELANALYSE
# ================================================================
if seite == "🔍 Einzelanalyse":
    st.title("Einzelanalyse")

    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("Aktien-Symbol", value="AAPL",
                               placeholder="z.B. AAPL, SAP.DE, ASML.AS")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analysieren = st.button("Analysieren", type="primary", use_container_width=True)

    st.subheader("Annahmen")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        wachstum = st.slider("FCF-Wachstum %", -20, 30, 8) / 100
    with col2:
        terminal = st.slider("Terminal %", 0, 6, 3) / 100
    with col3:
        sicherheit = st.slider("Sicherheitsmarge %", 0, 50, 25) / 100
    with col4:
        wacc_modus = st.selectbox("WACC", ["Automatisch", "Manuell"])
    wacc_override = None
    if wacc_modus == "Manuell":
        wacc_override = st.slider("WACC manuell %", 1, 20, 8) / 100

    if analysieren and symbol:
        with st.spinner(f"Lade Daten für {symbol}..."):
            ergebnis, fehler = dcf_berechnen(
                symbol.upper(), wachstum, terminal, sicherheit, wacc_override
            )

        if fehler:
            st.error(f"Fehler: {fehler}")
        elif ergebnis:
            # Ergebnis-Karten
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Aktueller Kurs", f"${ergebnis['kurs']:.2f}")
            col2.metric("Innerer Wert", f"${ergebnis['innerer_wert']:.2f}")
            col3.metric("Mit Sicherheitsmarge", f"${ergebnis['mit_marge']:.2f}")
            abw = ergebnis['abweichung']
            col4.metric(
                "Bewertung",
                f"{abw:+.1f}%",
                delta=f"{'Überbewertet' if abw > 0 else 'Unterbewertet'}",
                delta_color="inverse"
            )

            st.divider()

            # Kennzahlen
            st.subheader("Kennzahlen")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("KGV", f"{ergebnis['kgv']:.1f}" if ergebnis['kgv'] else "N/A")
            col2.metric("KBV", f"{ergebnis['kbv']:.2f}" if ergebnis['kbv'] else "N/A")
            col3.metric("EV/EBITDA", f"{ergebnis['ev_ebitda']:.1f}" if ergebnis['ev_ebitda'] else "N/A")
            col4.metric("ROE", f"{ergebnis['roe']*100:.1f}%" if ergebnis['roe'] else "N/A")
            col5.metric("Nettomarge", f"{ergebnis['nettomarge']*100:.1f}%" if ergebnis['nettomarge'] else "N/A")

            st.divider()

            # WACC & FCF Details
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("WACC & Annahmen")
                st.write(f"**WACC:** {ergebnis['wacc']}%")
                st.write(f"**FCF-Basis:** {ergebnis['fcf_hinweis']} (${ergebnis['fcf']} Mrd.)")
                st.write(f"**Sektor:** {ergebnis['sektor']}")
                st.write(f"**Beta:** {ergebnis['beta']}")

            with col2:
                # Bewertungs-Visualisierung
                fig = px.bar(
                    x=["Aktueller Kurs", "Innerer Wert", "Mit Marge"],
                    y=[ergebnis['kurs'], ergebnis['innerer_wert'], ergebnis['mit_marge']],
                    color=["Kurs", "Innerer Wert", "Mit Marge"],
                    color_discrete_map={
                        "Kurs": "#378ADD",
                        "Innerer Wert": "#1D9E75",
                        "Mit Marge": "#EF9F27"
                    },
                    labels={"x": "", "y": "Preis ($)"},
                    title="Kurs vs. innerer Wert"
                )
                fig.update_layout(showlegend=False, height=250)
                st.plotly_chart(fig, use_container_width=True)

            # In Datenbank speichern
            st.divider()
            if st.button("In Datenbank speichern"):
                symbole = [e["symbol"] for e in st.session_state.datenbank]
                eintrag = {
                    "Symbol":       ergebnis["symbol"],
                    "Name":         ergebnis["name"],
                    "Sektor":       ergebnis["sektor"],
                    "Kurs":         ergebnis["kurs"],
                    "Innerer Wert": ergebnis["innerer_wert"],
                    "Mit Marge":    ergebnis["mit_marge"],
                    "Abweichung %": ergebnis["abweichung"],
                    "WACC %":       ergebnis["wacc"],
                    "KGV":          ergebnis["kgv"],
                    "KBV":          ergebnis["kbv"],
                    "EV/EBITDA":    ergebnis["ev_ebitda"],
                    "ROE %":        round(ergebnis["roe"] * 100, 1) if ergebnis["roe"] else None,
                    "Nettomarge %": round(ergebnis["nettomarge"] * 100, 1) if ergebnis["nettomarge"] else None,
                    "FCF (Mrd.)":   ergebnis["fcf"],
                    "FCF Basis":    ergebnis["fcf_hinweis"],
                }
                if ergebnis["symbol"] in symbole:
                    st.session_state.datenbank[symbole.index(ergebnis["symbol"])] = eintrag
                    st.success(f"✅ {ergebnis['name']} aktualisiert!")
                else:
                    st.session_state.datenbank.append(eintrag)
                    st.success(f"✅ {ergebnis['name']} gespeichert!")

# ================================================================
# SEITE 2: DATENBANK
# ================================================================
elif seite == "📊 Datenbank":
    st.title("Datenbank")

    if not st.session_state.datenbank:
        st.info("Noch keine Aktien gespeichert. Analysiere zuerst Aktien auf der Einzelanalyse-Seite.")
    else:
        df = pd.DataFrame(st.session_state.datenbank)

        # Filter
        col1, col2 = st.columns(2)
        with col1:
            sektoren = ["Alle"] + sorted(df["Sektor"].dropna().unique().tolist())
            sektor_filter = st.selectbox("Sektor filtern", sektoren)
        with col2:
            abw_filter = st.slider("Abweichung % filtern", -200, 200, (-200, 200))

        gefiltert = df.copy()
        if sektor_filter != "Alle":
            gefiltert = gefiltert[gefiltert["Sektor"] == sektor_filter]
        gefiltert = gefiltert[
            (gefiltert["Abweichung %"] >= abw_filter[0]) &
            (gefiltert["Abweichung %"] <= abw_filter[1])
        ]

        st.dataframe(
            gefiltert.sort_values("Abweichung %"),
            use_container_width=True,
            hide_index=True
        )

        # Chart
        if len(gefiltert) > 0:
            fig = px.scatter(
                gefiltert,
                x="KGV", y="Abweichung %",
                size="KBV", color="Sektor",
                hover_name="Name",
                title="KGV vs. Abweichung vom inneren Wert",
                labels={"Abweichung %": "Abweichung vom inneren Wert (%)"}
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)

        # Export
        csv = gefiltert.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Als CSV exportieren", csv,
                           "aktien_datenbank.csv", "text/csv")

# ================================================================
# SEITE 3: PORTFOLIO
# ================================================================
elif seite == "💼 Portfolio":
    st.title("Portfolio")

    # Position hinzufügen
    with st.expander("➕ Position hinzufügen", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_symbol = st.text_input("Symbol", placeholder="z.B. AAPL")
        with col2:
            p_einstand = st.number_input("Einstandskurs ($)", min_value=0.0, step=0.01)
        with col3:
            p_stueck = st.number_input("Anzahl Stück", min_value=0.0, step=1.0)

        if st.button("Position hinzufügen", type="primary"):
            if p_symbol and p_einstand > 0 and p_stueck > 0:
                with st.spinner(f"Lade {p_symbol}..."):
                    info = yf.Ticker(p_symbol.upper()).info
                    kurs = info.get("currentPrice", 0) or 0
                    name = info.get("longName", p_symbol)

                    # Innerer Wert aus Datenbank holen falls vorhanden
                    innerer_wert = 0
                    for e in st.session_state.datenbank:
                        if e["Symbol"] == p_symbol.upper():
                            innerer_wert = e.get("Innerer Wert", 0)
                            break

                    perf = (kurs - p_einstand) / p_einstand * 100
                    abw  = (kurs - innerer_wert) / innerer_wert * 100 if innerer_wert > 0 else None

                    # Empfehlung
                    if innerer_wert > 0:
                        if abw > 40:      empfehlung = "🔴 Dringend verkaufen"
                        elif abw > 20:    empfehlung = "🟠 Verkaufen"
                        elif abw > 0:     empfehlung = "🟡 Halten"
                        elif abw > -20:   empfehlung = "🟡 Halten"
                        elif abw > -40:   empfehlung = "🟢 Nachkaufen"
                        else:             empfehlung = "🟢 Stark nachkaufen"
                    else:
                        empfehlung = "⚠️ Erst analysieren"

                    position = {
                        "Symbol":        p_symbol.upper(),
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

                    symbole = [p["Symbol"] for p in st.session_state.portfolio]
                    if p_symbol.upper() in symbole:
                        st.session_state.portfolio[symbole.index(p_symbol.upper())] = position
                        st.success(f"✅ {name} aktualisiert!")
                    else:
                        st.session_state.portfolio.append(position)
                        st.success(f"✅ {name} hinzugefügt!")
            else:
                st.warning("Bitte Symbol, Einstandskurs und Stückzahl angeben.")

    # Portfolio anzeigen
    if st.session_state.portfolio:
        df_p = pd.DataFrame(st.session_state.portfolio)

        # Gesamtübersicht
        gesamt_invest = df_p["Invest ($)"].sum()
        gesamt_wert   = df_p["Wert ($)"].sum()
        gesamt_perf   = (gesamt_wert - gesamt_invest) / gesamt_invest * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Positionen", len(df_p))
        col2.metric("Investiert", f"${gesamt_invest:,.2f}")
        col3.metric("Aktueller Wert", f"${gesamt_wert:,.2f}")
        col4.metric("Performance", f"{gesamt_perf:+.1f}%",
                    delta_color="normal")

        st.divider()

        # Tabelle
        st.dataframe(df_p, use_container_width=True, hide_index=True)

        # Charts
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

        # Export
        csv = df_p.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Portfolio exportieren", csv,
                           "portfolio.csv", "text/csv")
    else:
        st.info("Noch keine Positionen. Füge deine erste Position oben hinzu.")

# ================================================================
# SEITE 4: ANLEITUNG
# ================================================================
elif seite == "ℹ️ Anleitung":
    st.title("Anleitung")

    st.markdown("""
    ## Wie du das Tool nutzt

    ### 1. Einzelanalyse
    Gib ein Aktien-Symbol ein (z.B. `AAPL` für Apple, `SAP.DE` für SAP)
    und stelle die Annahmen ein. Klick auf **Analysieren** und speichere
    das Ergebnis in die Datenbank.

    ### 2. Datenbank
    Alle gespeicherten Aktien auf einen Blick – filterbar nach Sektor
    und Abweichung vom inneren Wert. Exportierbar als CSV.

    ### 3. Portfolio
    Trage deine echten Positionen mit Einstandskurs und Stückzahl ein.
    Das Tool zeigt dir Performance und Handlungsempfehlung.

    ---

    ## Wichtige Hinweise

    **Value-Titel** (Konsumgüter, Industrie, Gesundheit):
    DCF voll vertrauen, Wachstum 4–8%

    **Wachstumstitel** (Technologie, ASML, etc.):
    Wachstum manuell auf 12–20% erhöhen, Value Score ignorieren

    **Banken & Versorger:**
    Nur Kennzahlen nutzen, DCF ignorieren

    ---

    ## Symbole finden
    - Deutsche Aktien: Symbol + `.DE` (z.B. `SAP.DE`)
    - Niederländische Aktien: Symbol + `.AS` (z.B. `ASML.AS`)
    - US-Aktien: direkt das Symbol (z.B. `AAPL`, `MSFT`)
    """)
