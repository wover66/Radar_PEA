"""Gestion du portefeuille PEA — stockage, enrichissement, signaux, simulation."""

import json
import os
from typing import List, Dict

import pandas as pd

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")

MAX_SECTOR_PCT  = 40   # seuil d'alerte concentration sectorielle (%)
MAX_COUNTRY_PCT = 65   # seuil d'alerte concentration géographique (%)


# ── Persistance ────────────────────────────────────────────────────────────────

def load_portfolio() -> List[Dict]:
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    with open(PORTFOLIO_FILE) as f:
        return json.load(f).get("positions", [])


def save_portfolio(positions: List[Dict]) -> None:
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump({"positions": positions}, f, indent=2, ensure_ascii=False)


def add_position(positions: List[Dict], ticker: str, name: str,
                 quantity: float, pru: float) -> List[Dict]:
    """Ajoute ou fusionne une position (moyenne pondérée du PRU)."""
    for pos in positions:
        if pos["ticker"] == ticker:
            total_qty   = pos["quantity"] + quantity
            pos["pru"]  = (pos["quantity"] * pos["pru"] + quantity * pru) / total_qty
            pos["quantity"] = total_qty
            return positions
    positions.append({"ticker": ticker, "name": name,
                       "quantity": quantity, "pru": pru})
    return positions


def remove_position(positions: List[Dict], ticker: str) -> List[Dict]:
    return [p for p in positions if p["ticker"] != ticker]


# ── Enrichissement live ────────────────────────────────────────────────────────

LIVE_COLS = ["Ticker", "Pays", "Secteur", "Devise", "Prix",
             "Score Total", "Score Fond.", "Score Tech.",
             "RSI", "PER", "PER Secteur", "D/E", "Beta",
             "% MM200", "MM200", "Var 1J %", "Var 1S %"]


def enrich_portfolio(positions: List[Dict], df_analysis: pd.DataFrame) -> pd.DataFrame:
    """Joint les positions avec les données live et calcule P&L, poids."""
    if not positions or df_analysis.empty:
        return pd.DataFrame()

    port_df = pd.DataFrame(positions)
    live    = df_analysis[[c for c in LIVE_COLS if c in df_analysis.columns]].copy()
    live    = live.rename(columns={"Ticker": "ticker"})

    merged = port_df.merge(live, on="ticker", how="left")

    price = merged["Prix"].fillna(merged["pru"])
    merged["Valeur actuelle"] = merged["quantity"] * price
    merged["Valeur investie"]  = merged["quantity"] * merged["pru"]
    merged["P&L €"]            = merged["Valeur actuelle"] - merged["Valeur investie"]
    merged["P&L %"]            = (price - merged["pru"]) / merged["pru"] * 100

    total = merged["Valeur actuelle"].sum()
    merged["Poids %"] = merged["Valeur actuelle"] / total * 100 if total > 0 else 0

    return merged


# ── Métriques globales ─────────────────────────────────────────────────────────

def portfolio_metrics(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {}
    tv  = df["Valeur actuelle"].sum()
    ti  = df["Valeur investie"].sum()
    pnl = tv - ti
    garp = float(
        (df["Score Total"] * df["Valeur actuelle"]).sum() / tv
    ) if "Score Total" in df.columns and tv > 0 else 0

    return {
        "total_value":    tv,
        "total_invested": ti,
        "total_pnl":      pnl,
        "total_pnl_pct":  pnl / ti * 100 if ti > 0 else 0,
        "garp_score":     garp,
        "n_positions":    len(df),
    }


# ── Signaux d'arbitrage ────────────────────────────────────────────────────────

def _safe(val):
    try:
        return None if val is None or (isinstance(val, float) and val != val) else float(val)
    except Exception:
        return None


def get_signals(df: pd.DataFrame) -> List[Dict]:
    signals = []
    for _, r in df.iterrows():
        rsi        = _safe(r.get("RSI"))
        per        = _safe(r.get("PER"))
        per_sect   = _safe(r.get("PER Secteur"))
        de         = _safe(r.get("D/E"))
        score      = _safe(r.get("Score Total")) or 0
        pct_mm200  = _safe(r.get("% MM200"))
        name       = r.get("name", r.get("Nom", ""))
        ticker     = r.get("ticker", "")

        kind, reasons = "🔵 CONSERVER", []

        # ── Signaux de vente ──────────────────────────────────────────────────
        if rsi and rsi > 75:
            kind = "🔴 VENDRE"
            reasons.append(f"RSI en surachat sévère ({rsi:.1f} > 75)")
        elif per and per_sect and per > per_sect * 1.5 and score < 55:
            kind = "🔴 ALLÉGER"
            reasons.append(f"PER ({per:.1f}) très au-dessus moyenne secteur ({per_sect:.0f})")

        # ── Signaux d'alerte ──────────────────────────────────────────────────
        if kind not in ("🔴 VENDRE", "🔴 ALLÉGER"):
            if rsi and 65 < rsi <= 75:
                kind = "⚠️ SURVEILLER"
                reasons.append(f"RSI élevé ({rsi:.1f}), approche zone surachat")
            if de and de > 2.5:
                kind = "⚠️ SURVEILLER"
                reasons.append(f"Endettement élevé (D/E = {de:.2f})")
            if score < 40:
                kind = "🟡 SURVEILLER"
                reasons.append(f"Score GARP faible ({score:.0f}/100)")

        # ── Signaux d'achat / renforcement ────────────────────────────────────
        if kind == "🔵 CONSERVER":
            if score >= 70 and rsi and rsi < 45:
                kind = "🟢 RENFORCER"
                reasons.append(f"Score excellent ({score:.0f}/100) + RSI favorable ({rsi:.1f})")
            elif pct_mm200 is not None and -5 <= pct_mm200 <= 3 and score >= 60:
                kind = "🟢 POINT D'ENTRÉE"
                reasons.append(f"Prix près de la MM200 ({pct_mm200:+.1f}%) — zone de support")
            elif score >= 60:
                reasons.append(f"Score sain ({score:.0f}/100), fondamentaux corrects")
            else:
                kind = "🟡 SURVEILLER"
                reasons.append(f"Score modéré ({score:.0f}/100)")

        signals.append({
            "name":   name,
            "ticker": ticker,
            "kind":   kind,
            "reason": " — ".join(reasons) if reasons else "Aucune alerte particulière",
            "score":  score,
            "rsi":    rsi,
        })

    signals.sort(key=lambda x: (
        0 if "VENDRE" in x["kind"] or "ALLÉGER" in x["kind"] else
        1 if "RENFORCER" in x["kind"] or "ENTRÉE" in x["kind"] else
        2 if "SURVEILLER" in x["kind"] else 3
    ))
    return signals


# ── Simulation What-If ─────────────────────────────────────────────────────────

def simulate_buy(positions: List[Dict], df_analysis: pd.DataFrame,
                 ticker: str, name: str, quantity: float, price: float) -> Dict:
    """Calcule les métriques du portefeuille après un achat simulé."""
    sim = add_position([p.copy() for p in positions], ticker, name, quantity, price)
    sim_df = enrich_portfolio(sim, df_analysis)
    metrics = portfolio_metrics(sim_df)

    sector_alloc  = sim_df.groupby("Secteur")["Poids %"].sum().sort_values(ascending=False)
    country_alloc = sim_df.groupby("Pays")["Poids %"].sum().sort_values(ascending=False)

    warnings = []
    for sect, pct in sector_alloc.items():
        if pct > MAX_SECTOR_PCT:
            warnings.append(f"Secteur **{sect}** à {pct:.1f}% (seuil : {MAX_SECTOR_PCT}%)")
    for country, pct in country_alloc.items():
        if pct > MAX_COUNTRY_PCT:
            warnings.append(f"Pays **{country}** à {pct:.1f}% (seuil : {MAX_COUNTRY_PCT}%)")

    return {
        "metrics":       metrics,
        "sector_alloc":  sector_alloc,
        "country_alloc": country_alloc,
        "warnings":      warnings,
        "sim_df":        sim_df,
    }
