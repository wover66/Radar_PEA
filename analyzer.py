"""
GARP PEA Analyzer — moteur de données et de scoring.
Score 0-100 : 50 pts fondamentaux + 50 pts techniques.
"""

import json
import os
import warnings
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from typing import Optional

warnings.filterwarnings("ignore")

# ── Universe européen PEA-éligible ────────────────────────────────────────────

UNIVERSE = {
    # France — Large Cap (CAC 40)
    "Air Liquide":            "AI.PA",
    "Airbus":                 "AIR.PA",
    "AXA":                    "CS.PA",
    "Bouygues":               "EN.PA",
    "Capgemini":              "CAP.PA",
    "Carrefour":              "CA.PA",
    "Crédit Agricole":        "ACA.PA",
    "Danone":                 "BN.PA",
    "Dassault Systèmes":      "DSY.PA",
    "Engie":                  "ENGI.PA",
    "EssilorLuxottica":       "EL.PA",
    "Eurofins Scientific":    "ERF.PA",
    "Hermès":                 "RMS.PA",
    "Kering":                 "KER.PA",
    "Legrand":                "LR.PA",
    "L'Oréal":                "OR.PA",
    "LVMH":                   "MC.PA",
    "Michelin":               "ML.PA",
    "Orange":                 "ORA.PA",
    "Pernod Ricard":          "RI.PA",
    "Publicis Groupe":        "PUB.PA",
    "Safran":                 "SAF.PA",
    "Saint-Gobain":           "SGO.PA",
    "Sanofi":                 "SAN.PA",
    "Schneider Electric":     "SU.PA",
    "Société Générale":       "GLE.PA",
    "STMicroelectronics":     "STMPA.PA",
    "Teleperformance":        "TEP.PA",
    "Thales":                 "HO.PA",
    "TotalEnergies":          "TTE.PA",
    "Veolia":                 "VIE.PA",
    "Vinci":                  "DG.PA",
    "Vivendi":                "VIV.PA",
    # France — Mid Cap (SBF 120)
    "Alstom":                 "ALO.PA",
    "Amundi":                 "AMUN.PA",
    "Arkema":                 "AKE.PA",
    "Biomerieux":             "BIM.PA",
    "Bureau Veritas":         "BVI.PA",
    "Covivio":                "COV.PA",
    "Edenred":                "EDEN.PA",
    "Elis":                   "ELIS.PA",
    "Forvia":                 "FRVIA.PA",
    "Gaztransport (GTT)":     "GTT.PA",
    "Getlink":                "GET.PA",
    "Imerys":                 "NK.PA",
    "Ipsen":                  "IPN.PA",
    "Klepierre":              "LI.PA",
    "Nexans":                 "NEX.PA",
    "Rémy Cointreau":         "RCO.PA",
    "Rubis":                  "RUI.PA",
    "Sartorius Stedim":       "DIM.PA",
    "SEB":                    "SK.PA",
    "Sodexo":                 "SW.PA",
    "Soitec":                 "SOI.PA",
    "Sopra Steria":           "SOP.PA",
    "Spie":                   "SPIE.PA",
    "Trigano":                "TRI.PA",
    "Vallourec":              "VK.PA",
    "Worldline":              "WLN.PA",
    # Allemagne
    "SAP":                    "SAP.DE",
    "Siemens":                "SIE.DE",
    "Allianz":                "ALV.DE",
    "BASF":                   "BAS.DE",
    "Bayer":                  "BAYN.DE",
    "Beiersdorf":             "BEI.DE",
    "Adidas":                 "ADS.DE",
    "Continental":            "CON.DE",
    "Deutsche Telekom":       "DTE.DE",
    "Fresenius":              "FRE.DE",
    "Hannover Re":            "HNR1.DE",
    "Henkel":                 "HEN3.DE",
    "Infineon":               "IFX.DE",
    "Merck KGaA":             "MRK.DE",
    "MTU Aero Engines":       "MTX.DE",
    "Munich Re":              "MUV2.DE",
    "Porsche AG":             "P911.DE",
    "Puma":                   "PUM.DE",
    "RWE":                    "RWE.DE",
    "Vonovia":                "VNA.DE",
    "Volkswagen":             "VOW3.DE",
    "BMW":                    "BMW.DE",
    # Pays-Bas
    "ASML":                   "ASML.AS",
    "ArcelorMittal":          "MT.AS",
    "Philips":                "PHIA.AS",
    "Akzo Nobel":             "AKZA.AS",
    "IMCD":                   "IMCD.AS",
    "NN Group":               "NN.AS",
    "Randstad":               "RAND.AS",
    "Wolters Kluwer":         "WKL.AS",
    "DSM-Firmenich":          "DSFIR.AS",
    # Espagne
    "Inditex":                "ITX.MC",
    "Iberdrola":              "IBE.MC",
    "Repsol":                 "REP.MC",
    "Telefonica":             "TEF.MC",
    "Amadeus IT":             "AMS.MC",
    "Ferrovial":              "FER.MC",
    "Aena":                   "AENA.MC",
    "Cellnex":                "CLNX.MC",
    "Naturgy":                "NTGY.MC",
    # Italie
    "ENI":                    "ENI.MI",
    "Enel":                   "ENEL.MI",
    "Ferrari":                "RACE.MI",
    "Leonardo":               "LDO.MI",
    "Moncler":                "MONC.MI",
    "Prysmian":               "PRY.MI",
    "Recordati":              "REC.MI",
    "Amplifon":               "AMP.MI",
    "Brunello Cucinelli":     "BC.MI",
    # Belgique
    "AB InBev":               "ABI.BR",
    "UCB":                    "UCB.BR",
    "Ageas":                  "AGS.BR",
    "Bekaert":                "BEKB.BR",
    "Elia":                   "ELI.BR",
    "Sofina":                 "SOF.BR",
    "Solvay":                 "SOLB.BR",
    "WDP":                    "WDP.BR",
    # Danemark
    "Novo Nordisk":           "NOVO-B.CO",
    "Vestas":                 "VWS.CO",
    "DSV":                    "DSV.CO",
    "Coloplast":              "COLO-B.CO",
    "Genmab":                 "GMAB.CO",
    "Orsted":                 "ORSTED.CO",
    "Pandora":                "PNDORA.CO",
    # Suède
    "Ericsson":               "ERIC-B.ST",
    "Atlas Copco":            "ATCO-A.ST",
    "Hexagon":                "HEXA-B.ST",
    "H&M":                    "HM-B.ST",
    "Sandvik":                "SAND.ST",
    "Essity":                 "ESSITY-B.ST",
    "Investor AB":            "INVE-B.ST",
    "Evolution Gaming":       "EVO.ST",
    "Nibe Industrier":        "NIBE-B.ST",
    "SKF":                    "SKF-B.ST",
    # Finlande
    "Nokia":                  "NOKIA.HE",
    "Kone":                   "KNEBV.HE",
    "Neste":                  "NESTE.HE",
    "Wartsila":               "WRT1V.HE",
    "UPM-Kymmene":            "UPM.HE",
    # Norvège (EEA — PEA-éligible)
    "Equinor":                "EQNR.OL",
    "Mowi":                   "MOWI.OL",
    "Yara International":     "YAR.OL",
    "Tomra Systems":          "TOM.OL",
    "Kongsberg Gruppen":      "KOG.OL",
    # Portugal
    "Galp":                   "GALP.LS",
    "EDP":                    "EDP.LS",
    "Jerónimo Martins":       "JMT.LS",
    # Irlande
    "Kerry Group":            "KYGA.IR",
    "Ryanair":                "RYA.IR",
    "Flutter Entertainment":  "FLTR.IR",
    # Autriche
    "OMV":                    "OMV.VI",
    "Verbund":                "VER.VI",
    # ETFs PEA
    "ETF Amundi MSCI World":  "CW8.PA",
    "ETF Amundi CAC 40":      "C40.PA",
    "ETF Amundi MSCI Europe": "PCEU.PA",
    "ETF Amundi MSCI EM":     "PAEEM.PA",
}

# ── Référentiels sectoriels ────────────────────────────────────────────────────

SECTOR_PER = {
    "Technology":              28,
    "Consumer Cyclical":       22,
    "Consumer Defensive":      22,
    "Healthcare":              24,
    "Financial Services":      14,
    "Energy":                  13,
    "Utilities":               18,
    "Industrials":             20,
    "Basic Materials":         14,
    "Real Estate":             20,
    "Communication Services":  20,
}

SECTOR_DE_MAX = {
    "Financial Services": 4.0,
    "Real Estate":        2.5,
    "Utilities":          2.0,
}

EXCHANGE_COUNTRY = {
    ".PA": "France",      ".AS": "Pays-Bas",  ".DE": "Allemagne",
    ".MC": "Espagne",     ".MI": "Italie",     ".BR": "Belgique",
    ".CO": "Danemark",    ".ST": "Suède",      ".HE": "Finlande",
    ".OL": "Norvège",     ".LS": "Portugal",   ".IR": "Irlande",
    ".VI": "Autriche",
}

EXCLUDED_INDUSTRIES = frozenset({
    "Banks—Regional", "Banks—Diversified", "Banks", "Mortgage Finance",
    "Credit Services", "Auto Manufacturers",
})

LUXURY_AUTO_OK = frozenset({"Ferrari", "Porsche AG"})

SECTOR_FR = {
    "Technology":             "Technologie",
    "Consumer Cyclical":      "Conso. Cyclique",
    "Consumer Defensive":     "Conso. Défensive",
    "Healthcare":             "Santé",
    "Financial Services":     "Services Financiers",
    "Energy":                 "Énergie",
    "Utilities":              "Services Publics",
    "Industrials":            "Industrie",
    "Basic Materials":        "Matières Premières",
    "Real Estate":            "Immobilier",
    "Communication Services": "Communication",
    "ETF":                    "ETF",
    "N/A":                    "N/D",
}

CAP_FR = {
    "Large Cap": "Grande Cap.",
    "Mid Cap":   "Moyenne Cap.",
    "Small Cap": "Petite Cap.",
    "N/A":       "N/D",
    "ETF":       "ETF",
}

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache.json")
CACHE_TTL_H = 23


# ── Helpers ───────────────────────────────────────────────────────────────────

def _f(val):
    """Safe cast to float; returns None on failure."""
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def get_country(ticker: str) -> str:
    for suffix, country in EXCHANGE_COUNTRY.items():
        if ticker.endswith(suffix):
            return country
    return "Autre"


def get_cap(market_cap) -> str:
    mc = _f(market_cap)
    if mc is None:
        return "N/A"
    if mc >= 10e9:
        return "Large Cap"
    if mc >= 2e9:
        return "Mid Cap"
    return "Small Cap"


def calc_rsi(closes: pd.Series, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs = gain / loss
    return float((100 - 100 / (1 + rs)).iloc[-1])


# ── Scoring fondamental (50 pts) ──────────────────────────────────────────────

def fund_score(info: dict) -> dict:
    sector      = info.get("sector", "")
    avg_per     = SECTOR_PER.get(sector, 20)
    de_max      = SECTOR_DE_MAX.get(sector, 1.5)

    # PER vs moyenne sectorielle (0-20 pts)
    per = _f(info.get("trailingPE")) or _f(info.get("forwardPE"))
    if per and per > 0:
        ratio = per / avg_per
        per_s = 20 if ratio <= 0.50 else 16 if ratio <= 0.75 else \
                12 if ratio <= 1.00 else  6 if ratio <= 1.25 else 0
    else:
        per_s = 0

    # Dette / Capitaux propres (0-15 pts)
    dte_raw = _f(info.get("debtToEquity"))
    if dte_raw is not None and dte_raw > 20:
        dte_raw /= 100
    if dte_raw is None or dte_raw < 0:
        debt_s = 7
    else:
        ratio_d = dte_raw / de_max
        debt_s = 15 if ratio_d < 0.20 else 12 if ratio_d < 0.50 else \
                  8 if ratio_d < 1.00 else  3 if ratio_d < 1.50 else 0

    # Dividende (bonus 0-5 pts)
    dy = _f(info.get("dividendYield")) or 0
    td = _f(info.get("trailingAnnualDividendRate")) or 0
    div_s = (5 if dy >= 0.030 else 3 if dy >= 0.015 else 1) if td > 0 else 0

    # Croissance CA (0-5 pts)
    rg = _f(info.get("revenueGrowth"))
    rev_s = (5 if rg > 0.05 else 3 if rg > 0 else 0) if rg is not None else 2

    # Croissance BNC (0-5 pts)
    eg = _f(info.get("earningsGrowth"))
    bnc_s = (5 if eg > 0.05 else 3 if eg > 0 else 0) if eg is not None else 2

    total = min(per_s + debt_s + div_s + rev_s + bnc_s, 50)

    return {
        "PER":          round(per, 1) if per else None,
        "PER Secteur":  avg_per,
        "D/E":          round(dte_raw, 2) if dte_raw is not None and dte_raw >= 0 else None,
        "Div %":        round(dy * 100, 2),
        "Croiss. CA %": round(rg * 100, 1) if rg is not None else None,
        "Croiss. BNC %":round(eg * 100, 1) if eg is not None else None,
        "Score Fond.":  total,
        "_fb":          {"PER": per_s, "Dette": debt_s, "Div.": div_s,
                         "CA": rev_s, "BNC": bnc_s},
    }


# ── Scoring technique (50 pts) ────────────────────────────────────────────────

def tech_score(hist: pd.DataFrame) -> dict:
    closes  = hist["Close"]
    volumes = hist["Volume"]
    price   = float(closes.iloc[-1])

    mm50  = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    mm200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else None
    rsi   = calc_rsi(closes)

    vol_ratio = None
    if len(volumes) >= 50:
        rv = float(volumes.tail(10).mean())
        bv = float(volumes.tail(50).mean())
        vol_ratio = rv / bv if bv > 0 else None

    # Variations de prix
    var_1d = round((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] * 100, 2) \
             if len(closes) >= 2 else None
    var_1w = round((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6] * 100, 2) \
             if len(closes) >= 6 else None

    # MM200 (0-15 pts)
    if mm200:
        p200 = (price - mm200) / mm200 * 100
        mm200_s = 15 if p200 > 10 else 12 if p200 > 5 else \
                   8 if p200 > 0  else  4 if p200 > -5 else 0
    else:
        p200 = None
        mm200_s = 5

    # MM50 (0-10 pts)
    if mm50:
        p50 = (price - mm50) / mm50 * 100
        mm50_s = 10 if p50 > 5 else 8 if p50 > 2 else 6 if p50 > 0 else 0
    else:
        p50 = None
        mm50_s = 3

    # RSI (0-15 pts) — idéal 40-60, pénalise sur-achat > 70
    if rsi is not None:
        rsi_s = (10 if rsi < 30 else 13 if rsi < 40 else 15 if rsi <= 60
                 else 8 if rsi <= 70 else 3 if rsi <= 75 else 0)
    else:
        rsi_s = 7

    # Volume (0-10 pts)
    if vol_ratio is not None:
        vol_s = 10 if vol_ratio >= 1.5 else 8 if vol_ratio >= 1.2 else \
                 6 if vol_ratio >= 1.0 else 3 if vol_ratio >= 0.7 else 1
    else:
        vol_s = 3

    total = min(mm200_s + mm50_s + rsi_s + vol_s, 50)

    return {
        "Prix":          price,
        "MM50":          round(mm50, 2)  if mm50  else None,
        "MM200":         round(mm200, 2) if mm200 else None,
        "% MM200":       round(p200, 1)  if p200 is not None else None,
        "RSI":           round(rsi, 1)   if rsi  else None,
        "Vol Ratio":     round(vol_ratio, 2) if vol_ratio else None,
        "Score Tech.":   total,
        "Var 1J %":      var_1d,
        "Var 1S %":      var_1w,
        "_tb":           {"MM200": mm200_s, "MM50": mm50_s,
                          "RSI": rsi_s, "Volume": vol_s},
    }


# ── Analyse principale ────────────────────────────────────────────────────────

def run_analysis(force: bool = False, progress_cb=None) -> pd.DataFrame:
    """Charge le cache si < 23 h, sinon refetch tout l'univers."""
    if not force and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as fh:
            cached = json.load(fh)
        age = datetime.now() - datetime.fromisoformat(cached["timestamp"])
        data_ok = cached.get("data") and "Var 1J %" in cached["data"][0]
        if age < timedelta(hours=CACHE_TTL_H) and data_ok:
            return pd.DataFrame(cached["data"])

    rows = []
    total = len(UNIVERSE)
    for i, (name, ticker) in enumerate(UNIVERSE.items()):
        if progress_cb:
            progress_cb(i / total, f"{name}…")
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="300d")

            if hist.empty or len(hist) < 50:
                continue

            is_etf    = str(info.get("quoteType", "")).upper() == "ETF"
            industry  = info.get("industry", "")
            sector    = info.get("sector", "N/A")
            currency  = info.get("currency", "")

            # Filtre banques + auto généraliste
            if industry in EXCLUDED_INDUSTRIES and name not in LUXURY_AUTO_OK:
                continue

            # Filtre sociétés en perte (PER négatif) sauf ETF
            per_raw = _f(info.get("trailingPE")) or _f(info.get("forwardPE"))
            if not is_etf and per_raw is not None and per_raw <= 0:
                continue

            ts = tech_score(hist)

            if is_etf:
                fs = {
                    "PER": None, "PER Secteur": None, "D/E": None,
                    "Div %": 0, "Croiss. CA %": None, "Croiss. BNC %": None,
                    "Score Fond.": 25,
                    "_fb": {"PER": 0, "Dette": 0, "Div.": 0, "CA": 0, "BNC": 0},
                }
            else:
                fs = fund_score(info)

            beta    = _f(info.get("beta"))
            mktcap  = _f(info.get("marketCap"))
            country = get_country(ticker)
            cap_cat = get_cap(mktcap)
            total_s = fs["Score Fond."] + ts["Score Tech."]

            alerts = []
            if beta is not None and beta > 1.5:
                alerts.append("⚠️ Vol.")
            if ts["RSI"] is not None and ts["RSI"] > 70:
                alerts.append("🔴 RSI>70")

            rows.append({
                "Nom":           name,
                "Ticker":        ticker,
                "Pays":          country,
                "Secteur":       "ETF" if is_etf else SECTOR_FR.get(sector, sector),
                "Taille":        "ETF" if is_etf else CAP_FR.get(cap_cat, cap_cat),
                "Devise":        currency,
                "Prix":          ts["Prix"],
                "MM50":          ts["MM50"],
                "MM200":         ts["MM200"],
                "% MM200":       ts["% MM200"],
                "RSI":           ts["RSI"],
                "Vol Ratio":     ts["Vol Ratio"],
                "PER":           fs["PER"],
                "PER Secteur":   fs["PER Secteur"],
                "D/E":           fs["D/E"],
                "Div %":         fs["Div %"],
                "Croiss. CA %":  fs["Croiss. CA %"],
                "Croiss. BNC %": fs["Croiss. BNC %"],
                "Score Fond.":   fs["Score Fond."],
                "Score Tech.":   ts["Score Tech."],
                "Score Total":   total_s,
                "Var 1J %":      ts.get("Var 1J %"),
                "Var 1S %":      ts.get("Var 1S %"),
                "Beta":          round(beta, 2) if beta else None,
                "Alertes":       " ".join(alerts),
                "_fb":           fs["_fb"],
                "_tb":           ts["_tb"],
            })

        except Exception as exc:
            print(f"[Erreur] {name} ({ticker}): {exc}")

    rows.sort(key=lambda r: r["Score Total"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["#"] = rank

    with open(CACHE_FILE, "w") as fh:
        json.dump({"timestamp": datetime.now().isoformat(), "data": rows},
                  fh, default=str)

    if progress_cb:
        progress_cb(1.0, "Terminé")

    return pd.DataFrame(rows)
