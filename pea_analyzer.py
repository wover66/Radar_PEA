import time
from datetime import datetime

import pandas as pd
import yfinance as yf

TICKERS = {
    # ── CAC 40 ────────────────────────────────────────────────
    "Air Liquide":            "AI.PA",
    "Airbus":                 "AIR.PA",
    "AXA":                    "CS.PA",
    "BNP Paribas":            "BNP.PA",
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
    "Renault":                "RNO.PA",
    "Safran":                 "SAF.PA",
    "Saint-Gobain":           "SGO.PA",
    "Sanofi":                 "SAN.PA",
    "Schneider Electric":     "SU.PA",
    "Société Générale":       "GLE.PA",
    "STMicroelectronics":     "STMPA.PA",
    "Teleperformance":        "TEP.PA",
    "Thales":                 "HO.PA",
    "TotalEnergies":          "TTE.PA",
    "Unibail-Rodamco":        "URW.AS",
    "Veolia":                 "VIE.PA",
    "Vinci":                  "DG.PA",
    "Vivendi":                "VIV.PA",
    "Worldline":              "WLN.PA",
    # ── SBF 120 / Mid-caps françaises ─────────────────────────
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
    "OVH Groupe":             "OVH.PA",
    "Plastic Omnium":         "POM.PA",
    "Rémy Cointreau":         "RCO.PA",
    "Rubis":                  "RUI.PA",
    "Sartorius Stedim":       "DIM.PA",
    "SEB":                    "SK.PA",
    "Sodexo":                 "SW.PA",
    "Soitec":                 "SOI.PA",
    "Sopra Steria":           "SOP.PA",
    "Spie":                   "SPIE.PA",
    "Trigano":                "TRI.PA",
    "Ubisoft":                "UBI.PA",
    "Vallourec":              "VK.PA",
    # ── Grandes valeurs européennes PEA-éligibles ─────────────
    "ASML":                   "ASML.AS",
    "ArcelorMittal":          "MT.AS",
    "ING Groep":              "INGA.AS",
    "Philips":                "PHIA.AS",
    "SAP":                    "SAP.DE",
    "Siemens":                "SIE.DE",
    "Allianz":                "ALV.DE",
    "BASF":                   "BAS.DE",
    "Bayer":                  "BAYN.DE",
    "BMW":                    "BMW.DE",
    "Deutsche Telekom":       "DTE.DE",
    "Volkswagen":             "VOW3.DE",
    "Adidas":                 "ADS.DE",
    "Infineon":               "IFX.DE",
    "Inditex":                "ITX.MC",
    "Iberdrola":              "IBE.MC",
    "BBVA":                   "BBVA.MC",
    "Santander":              "SAN.MC",
    "Repsol":                 "REP.MC",
    "Telefonica":             "TEF.MC",
    "ENI":                    "ENI.MI",
    "Enel":                   "ENEL.MI",
    "AB InBev":               "ABI.BR",
    "UCB":                    "UCB.BR",
    # ── ETFs PEA ──────────────────────────────────────────────
    "Amundi MSCI World PEA":  "CW8.PA",
    "Amundi CAC 40":          "C40.PA",
    "Amundi MSCI Europe":     "PCEU.PA",
    "Amundi MSCI EM PEA":     "PAEEM.PA",
}

PER_MAX  = 22
MA_DAYS  = 50
INTERVAL = 86_400  # secondes (24 h)


def compute_score(per, momentum_pct, is_etf):
    """Score 0-100 : 50% valeur (PER), 50% momentum (% au-dessus MM50, cap 20%)."""
    if is_etf:
        return round(min(momentum_pct / 20, 1.0) * 100, 1)
    per_score      = (PER_MAX - per) / PER_MAX * 50          # 0-50 pts
    momentum_score = min(momentum_pct / 20, 1.0) * 50        # 0-50 pts
    return round(per_score + momentum_score, 1)


def analyze():
    print(f"\n{'=' * 65}")
    print(f"  Radar PEA — {datetime.now().strftime('%d/%m/%Y  %H:%M:%S')}")
    print(f"{'=' * 65}\n")

    eligible = []

    for name, ticker in TICKERS.items():
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="120d")

            if hist.empty or len(hist) < MA_DAYS:
                print(f"  [{ticker}] Données insuffisantes, ignoré.")
                continue

            current_price = float(hist["Close"].iloc[-1])
            ma50          = float(hist["Close"].tail(MA_DAYS).mean())
            is_etf        = info.get("quoteType", "").upper() == "ETF"
            per           = info.get("trailingPE") or info.get("forwardPE")

            # Critère 1 : 0 < PER < PER_MAX  (ETF → ignoré ; PER négatif = société en perte → exclu)
            per_ok = is_etf or (per is not None and 0 < per < PER_MAX)

            # Critère 2 : prix > MM50
            price_ok = current_price > ma50

            per_label    = "ETF" if is_etf else (f"{per:.1f}" if per else "N/A")
            momentum_pct = (current_price - ma50) / ma50 * 100

            if per_ok and price_ok:
                score = compute_score(per if not is_etf else 0, momentum_pct, is_etf)
                eligible.append({
                    "Nom":      name,
                    "Ticker":   ticker,
                    "Prix":     f"{current_price:.2f}",
                    "% MM50":   f"+{momentum_pct:.1f}%",
                    "PER":      per_label,
                    "Score":    score,
                    "_score":   score,
                })
            else:
                reasons = []
                if not is_etf:
                    if per is None:
                        reasons.append("PER indisponible")
                    elif per <= 0:
                        reasons.append(f"société en perte (PER {per:.1f})")
                    elif per >= PER_MAX:
                        reasons.append(f"PER trop élevé ({per:.1f})")
                if not price_ok:
                    reasons.append(f"sous MM50 ({current_price:.2f} < {ma50:.2f})")
                print(f"  ✗ {name:<28} — {', '.join(reasons)}")

        except Exception as exc:
            print(f"  [Erreur] {name} ({ticker}): {exc}")

    print()
    if eligible:
        eligible.sort(key=lambda x: x["_score"], reverse=True)
        for i, row in enumerate(eligible, 1):
            row["#"] = i
            del row["_score"]

        cols = ["#", "Nom", "Ticker", "Prix", "% MM50", "PER", "Score"]
        df = pd.DataFrame(eligible)[cols]
        print("  Classement — du plus au moins attractif (Score = 50% valeur + 50% momentum) :\n")
        print(df.to_string(index=False))
    else:
        print("  Aucune action ne remplit les deux critères aujourd'hui.")
    print()


def main():
    while True:
        analyze()
        print(f"  Prochaine analyse dans 24 h.  Ctrl+C pour quitter.\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
