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
    cash              = info.get("totalCash", 0) or
